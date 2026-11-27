"""
Verifica trade.s contra la versión de referencia en Python (CruceMedias).

Hace dos cosas con cada serie:
  1. Emula trade.s en un modelo de Espino (RV32E sin shifts) con el SPI slave,
     y reporta lo mismo que el testbench: patrimonio, órdenes, pérdida máxima,
     peor caso de ciclos, más IC y CPI por tick.
  2. Corre CruceMedias en Python y escribe sus decisiones en un CSV con el
     mismo formato que decisiones.csv del testbench, para compararlos con diff.

Uso (desde la raíz del repo):
    python trading_sim/emular.py sw/trade.hex tb/practica.csv
    diff decisiones.csv decisiones_python.csv          # sin salida = idénticos

Para probar el botón de reset (mismo escenario que tb/tb_reset.sv):
    python trading_sim/emular.py sw/trade.hex tb/practica.csv --ticks 2000 --reset 500
    diff decisiones_reset.csv decisiones_python.csv

Con varias series escribe un CSV por serie: decisiones_python_<serie>.csv

Perfil por sección (ciclos e instrucciones por etiqueta de trade.s):
    python trading_sim/emular.py sw/trade.hex tb/practica.csv --perfil sw/trade.s
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # para importar market y algorithms desde cualquier carpeta
from market import Market
from algorithms.cruce_medias import CruceMedias

CAJA0 = 10000          # caja inicial (igual que el testbench)
COMISION = 5           # comisión por orden ejecutada
SPI = 0x80010000       # base del SPI slave: STATUS +0, PRICE +4, DECISION +8
PERIODO_NS = 100000    # ronda 3, para calcular los ciclos disponibles
SPI_NS = 9500          # duración de una transacción SPI en el testbench
DISPONIBLES = (PERIODO_NS - SPI_NS) // 40   # ciclos de 40 ns entre el precio y el siguiente tick (2262)


# ---------------------------------------------------------------------------
# Modelo de Espino
# ---------------------------------------------------------------------------

def sx(v: int, bits: int) -> int:  # extiende el signo de un campo de 'bits' bits
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


def u32(v: int) -> int:  # valor como entero sin signo de 32 bits
    return v & 0xFFFFFFFF


def s32(v: int) -> int:  # valor como entero con signo de 32 bits
    return sx(u32(v), 32)


class Espino:
    """CPU RV32E + RAM de 512 palabras + registros del SPI slave.

    Cuenta los ciclos con las reglas del RTL: 2 por instrucción, 3 en cargas
    (la RAM y el SPI responden un ciclo después) y 3 en saltos tomados
    (se descarta la instrucción ya buscada). Los shifts ejecutan ADD, como en el ALU.
    """

    def __init__(self, hexfile: str) -> None:  # carga el programa en la RAM y deja la CPU en reset
        prog = [int(l, 16) for l in open(hexfile) if l.strip()]   # una instrucción por línea del .hex
        self.mem = [0] * 512          # RAM unificada (programa + datos), en palabras
        self.mem[:len(prog)] = prog
        self.r = [0] * 32             # banco de registros (solo x0-x15 existen; los campos de inmediato pueden indexar más allá)
        self.pc = 0                   # contador de programa
        self.price = 0                # registro PRICE del SPI
        self.new = 0                  # bit 0 de STATUS: hay un precio sin leer
        self.decision = None          # último byte escrito en DECISION en este tick (None = todavía no)
        self.botones = 0              # estado de los 4 botones (bits 3:0), se lee en 0x8000_0008
        self.sma_limpiar()            # periférico de media móvil (variante A): se limpia al encender
        self.instr = 0                # instrucciones ejecutadas en total
        self.cyc = 0                  # ciclos en total
        self.por_pc = defaultdict(lambda: [0, 0])   # por dirección: [veces ejecutada, ciclos]

    def sma_limpiar(self) -> None:  # periférico de media móvil: buffer y sumas en 0 (como pochoco_sma.v)
        self.sma_mem = [0] * 32       # los últimos 32 precios
        self.sma_idx = 0              # posición del más viejo
        self.sma_sl = 0               # suma de 32 (13 bits)
        self.sma_sc = 0               # suma de 8 (11 bits)

    def sma_precio(self, p: int) -> None:  # lo que hace pochoco_sma.v al llegar un precio, con sus anchos de bits
        viejo32 = self.sma_mem[self.sma_idx]
        viejo8 = self.sma_mem[(self.sma_idx + 24) % 32]
        self.sma_mem[self.sma_idx] = p
        self.sma_sl = (self.sma_sl + p - viejo32) & 0x1FFF
        self.sma_sc = (self.sma_sc + p - viejo8) & 0x7FF
        self.sma_idx = (self.sma_idx + 1) % 32

    def sma_d(self) -> int:  # D = 4*s_c - s_l en 14 bits con signo, extendido a 32
        return u32(sx(((self.sma_sc << 2) - self.sma_sl) & 0x3FFF, 14))

    def load(self, a: int) -> int:  # lectura de memoria o de un registro del SPI
        if a == SPI:
            return self.new                       # STATUS (cs_active se toma como 0)
        if a == SPI + 4:
            self.new = 0                          # leer PRICE baja new_price
            return self.price
        if a == SPI + 12:
            return self.sma_d()                   # D del periférico de media móvil
        if a == 0x80000008:
            return self.botones                   # botones de la placa
        assert a < 2048 and a % 4 == 0, f"lectura fuera de la RAM: {a:#x}"
        return self.mem[a // 4]

    def store(self, a: int, v: int) -> None:  # escritura en memoria, en DECISION o en los periféricos
        if a == SPI + 8:
            self.decision = v & 0xFF              # DECISION: solo el byte bajo
            return
        if a == SPI + 12:
            self.sma_limpiar()                    # escribir en 0x0C reinicia el periférico
            return
        if a >= 0x80000000:
            return                                # display y LEDs: se ignoran
        assert a < 2048 and a % 4 == 0, f"escritura fuera de la RAM: {a:#x}"
        self.mem[a // 4] = u32(v)

    def step(self) -> None:  # ejecuta una instrucción
        i = self.mem[self.pc // 4]                                # instrucción actual
        op, rd, f3 = i & 0x7F, (i >> 7) & 0x1F, (i >> 12) & 7     # opcode, destino, funct3
        rs1, rs2, f7 = (i >> 15) & 0x1F, (i >> 20) & 0x1F, i >> 25
        a, b = self.r[rs1], self.r[rs2]                           # operandos
        nxt, wr, c = self.pc + 4, None, 2                         # siguiente PC, valor a escribir, ciclos
        if op == 0x33:      # tipo R
            wr = {0: (a - b) if f7 else (a + b), 2: int(s32(a) < s32(b)), 3: int(u32(a) < u32(b)),
                  4: a ^ b, 6: a | b, 7: a & b}.get(f3, a + b)   # shifts (f3 = 1, 5) -> ADD
        elif op == 0x13:    # tipo I aritméticas
            im = sx(i >> 20, 12)
            wr = {0: a + im, 2: int(s32(a) < im), 3: int(u32(a) < u32(im)),
                  4: a ^ im, 6: a | im, 7: a & im}.get(f3, a + im)
        elif op == 0x03:    # lw
            wr, c = self.load(u32(a + sx(i >> 20, 12))), 3
        elif op == 0x23:    # sw
            self.store(u32(a + sx(((i >> 25) << 5) | ((i >> 7) & 0x1F), 12)), b)
        elif op == 0x63:    # saltos condicionales
            im = sx(((i >> 31) << 12) | (((i >> 7) & 1) << 11) | (((i >> 25) & 0x3F) << 5) | (((i >> 8) & 0xF) << 1), 13)
            salta = {0: a == b, 1: a != b, 4: s32(a) < s32(b), 5: s32(a) >= s32(b),
                     6: u32(a) < u32(b), 7: u32(a) >= u32(b)}[f3]
            if salta:
                nxt, c = self.pc + im, 3
        elif op == 0x0B:    # custom-0 (variante B)
            if f3 == 0:     # dif rd, rs1, rs2: rd = 4*rs1 - rs2
                wr = 4 * a - b
            elif f3 == 1:   # circ rd, rs1, imm: rd = (rs1 + imm) & 0x7C
                wr = (a + sx(i >> 20, 12)) & 0x7C
            else:
                raise ValueError(f"custom-0 no soportada: {i:08x} en {self.pc:#x}")
        elif op == 0x37:    # lui
            wr = i & 0xFFFFF000
        elif op == 0x6F:    # jal (y j)
            im = sx(((i >> 31) << 20) | (((i >> 12) & 0xFF) << 12) | (((i >> 20) & 1) << 11) | (((i >> 21) & 0x3FF) << 1), 21)
            wr, nxt, c = self.pc + 4, self.pc + im, 3
        else:
            raise ValueError(f"instrucción no soportada por el emulador: {i:08x} en {self.pc:#x}")
        if wr is not None and rd:
            self.r[rd] = u32(wr)                  # x0 nunca se escribe
        e = self.por_pc[self.pc]                  # perfil de esta instrucción
        e[0] += 1
        e[1] += c
        self.pc = nxt
        self.instr += 1
        self.cyc += c

    def arrancar(self) -> None:  # corre la inicialización hasta la primera lectura de STATUS
        while True:
            i = self.mem[self.pc // 4]
            if i & 0x7F == 0x03 and self.r[(i >> 15) & 0x1F] == SPI:
                return
            self.step()

    def presionar_reset(self, ciclos: int = 500) -> None:  # mantiene un botón presionado unos ciclos y lo suelta
        self.botones = 1
        c0 = self.cyc
        while self.cyc - c0 < ciclos:
            self.step()
        self.botones = 0
        self.arrancar()                           # termina la reinicialización y queda esperando el precio

    def tick(self, precio: int) -> tuple[int, int, int]:  # entrega un precio y corre hasta que se escribe DECISION
        self.price, self.new, self.decision = precio, 1, None
        self.sma_precio(precio)                   # el periférico termina 3 ciclos después de byte_done, antes de que la CPU lea D
        i0, c0 = self.instr, self.cyc                              # contadores al llegar el precio
        while self.decision is None:
            self.step()
            assert self.instr - i0 < 10000, "trade.s no escribió DECISION"
        return self.decision, self.instr - i0, self.cyc - c0      # (byte, IC del tick, ciclos del tick)


# ---------------------------------------------------------------------------
# Referencia en Python y contabilidad del testbench
# ---------------------------------------------------------------------------

def decisiones_python(precios: list[int]) -> list[int]:  # byte que CruceMedias escribe después de cada precio
    m = Market(COMISION, CAJA0)
    t = CruceMedias("CruceMedias", CAJA0, COMISION, N_corta=8, N_larga=32, margen=2)
    m.insert_trader(t)
    salida = []                                   # decisión calculada después de p[n]
    for p in precios:
        m.execute_decision(t, p)
        t.receive_price(p)
        salida.append(t.decision)
    return salida


def contabilidad(escritas: list[int], precios: list[int]) -> tuple[list[tuple], dict]:  # replica ejecutar() del testbench
    """escritas[n] es el byte escrito después de p[n]. La maestra lo lee en la
    transacción n+1 y lo ejecuta a p[n+1]; en la transacción 0 lee el valor de reset (0x00)."""
    caja, acciones, peak, max_dd, ordenes = CAJA0, 0, CAJA0, 0, 0
    filas = []                                    # filas del CSV: (tick, precio, decision, caja, acciones, patrimonio)
    for n, p in enumerate(precios):
        d = escritas[n - 1] if n > 0 else 0x00    # byte que la maestra lee en el tick n
        q = d & 0x3F                              # cantidad pedida
        if d >> 6 == 1:                           # comprar lo que alcance
            q = min(q, (caja - COMISION) // p)
            if q > 0:
                caja -= q * p + COMISION; acciones += q; ordenes += 1
        elif d >> 6 == 2:                         # vender lo que se tenga
            q = min(q, acciones)
            if q > 0 and caja + q * p >= COMISION:
                caja += q * p - COMISION; acciones -= q; ordenes += 1
        w = caja + acciones * p                   # patrimonio en el tick n
        peak = max(peak, w)
        max_dd = max(max_dd, peak - w)
        filas.append((n, p, d, caja, acciones, w))
    q0 = (CAJA0 - COMISION) // precios[0]         # referencia comprar y mantener (fórmula del testbench)
    resumen = {"patrimonio": w, "ordenes": ordenes, "perdida_max": max_dd,
               "bh": CAJA0 - COMISION - q0 * precios[0] + q0 * precios[-1]}
    return filas, resumen


def escribir_csv(ruta: Path, filas: list[tuple]) -> None:  # mismo formato que decisiones.csv del testbench
    with open(ruta, "w") as f:
        f.write("tick,precio,decision,caja,acciones,patrimonio\n")
        for n, p, d, caja, acc, w in filas:
            f.write(f"{n},{p},{d:02x},{caja},{acc},{w}\n")


def imprimir(titulo: str, r: dict) -> None:  # resumen con las mismas líneas que el testbench
    print(f"  {titulo}")
    print(f"    Patrimonio final:          {r['patrimonio']}")
    print(f"    Ordenes ejecutadas:        {r['ordenes']}")
    print(f"    Perdida maxima:            {r['perdida_max']}")


# ---------------------------------------------------------------------------
# Perfil por sección
# ---------------------------------------------------------------------------

AGRUPAR = {"con_acciones": "decidir", "sin_acciones": "decidir", "limpiar": "inicio"}   # etiquetas que se suman a otra sección


def etiquetas(ruta_s: str) -> list[tuple[int, str]]:  # (dirección, etiqueta) de cada etiqueta de trade.s
    salida, direccion = [], 0                     # etiquetas encontradas, dirección de la próxima instrucción
    for linea in open(ruta_s):
        linea = linea.split("#")[0].strip()       # sin comentarios
        if not linea:
            continue
        if ":" in linea.split()[0]:               # "etiqueta:" o "etiqueta: instrucción"
            nombre, _, resto = linea.partition(":")
            salida.append((direccion, nombre.strip()))
            linea = resto.strip()
        if linea:
            direccion += 4                        # cada instrucción (también j, mv, nop) ocupa una palabra
    return salida


def seccion(pc: int, marcas: list[tuple[int, str]]) -> str:  # sección a la que pertenece una dirección
    nombre = "?"
    for direccion, etiqueta in marcas:
        if direccion <= pc:
            nombre = etiqueta
    return AGRUPAR.get(nombre, nombre)


def imprimir_perfil(cpu: "Espino", marcas: list[tuple[int, str]], ticks: int) -> None:  # ciclos e IC por sección, por tick
    tabla = defaultdict(lambda: [0, 0])           # sección -> [instrucciones, ciclos]
    for pc, (veces, ciclos) in cpu.por_pc.items():
        t = tabla[seccion(pc, marcas)]
        t[0] += veces
        t[1] += ciclos
    total = sum(c for _, c in tabla.values())
    print("  Perfil por sección (promedio por tick, sin la inicialización):")
    print(f"    {'sección':12s} {'IC':>6s} {'ciclos':>8s} {'% ciclos':>9s}")
    orden = [e for _, e in marcas]                # mismo orden que en el programa
    for nombre in sorted(tabla, key=lambda n: orden.index(n) if n in orden else 99):
        ic, cy = tabla[nombre]
        print(f"    {nombre:12s} {ic / ticks:6.1f} {cy / ticks:8.1f} {100 * cy / total:8.1f}%")
    print(f"    {'total':12s} {sum(i for i, _ in tabla.values()) / ticks:6.1f} {total / ticks:8.1f}")


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------

def main() -> None:  # emula trade.s y Python en cada serie, imprime el resumen y escribe los CSV
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    args = sys.argv[1:]
    reset = None                                  # tick después del cual se presiona el botón (None = sin reset)
    if "--reset" in args:
        i = args.index("--reset")
        reset = int(args[i + 1])
        del args[i:i + 2]
    ticks = None                                  # usar solo los primeros N ticks (como NTICKS del testbench)
    if "--ticks" in args:
        i = args.index("--ticks")
        ticks = int(args[i + 1])
        del args[i:i + 2]
    perfil = None                                 # ruta de trade.s para el perfil por sección (None = sin perfil)
    if "--perfil" in args:
        i = args.index("--perfil")
        perfil = args[i + 1]
        del args[i:i + 2]
    hexfile, series = args[0], args[1:]

    for ruta in map(Path, series):
        precios = [int(l.split(",")[1]) for l in open(ruta).read().split()[1:]]   # salta el encabezado
        precios = precios[:ticks] if ticks else precios

        cpu = Espino(hexfile)
        cpu.arrancar()
        cpu.por_pc.clear()                        # el perfil cuenta solo los ticks, no la inicialización
        asm, ics, ciclos = [], [], []             # bytes escritos, IC y ciclos de cada tick
        for n, p in enumerate(precios):
            d, ic, cy = cpu.tick(p)
            asm.append(d); ics.append(ic); ciclos.append(cy)
            if n == reset:
                cpu.decision = None
                cpu.presionar_reset()
                if cpu.decision is not None:
                    asm[-1] = cpu.decision        # inicio volvió a escribir DECISION: eso es lo que lee la maestra
        if reset is None:
            py = decisiones_python(precios)
        else:                                     # Python equivalente: un trader nuevo desde el tick siguiente al reset
            py = decisiones_python(precios[:reset + 1]) + decisiones_python(precios[reset + 1:])
            py[reset] = 0x00                      # al reiniciar, trade.s deja DECISION en mantener

        filas_asm, r_asm = contabilidad(asm, precios)
        filas_py, r_py = contabilidad(py, precios)
        iguales = sum(a == b for a, b in zip(asm, py))            # ticks con el mismo byte

        titulo = f"{ruta.stem} ({len(precios)} ticks" + (f", reset después del tick {reset})" if reset is not None else ")")
        print(f"\n=== {titulo}")
        imprimir("trade.s (emulado)", r_asm)
        print(f"    Peor caso precio->decision: {max(ciclos)} ciclos (disponibles: {DISPONIBLES})")
        print(f"    IC por tick:               promedio {sum(ics) / len(ics):.1f}, máximo {max(ics)}")
        print(f"    Ciclos por tick:           promedio {sum(ciclos) / len(ciclos):.1f}, máximo {max(ciclos)}")
        print(f"    CPI:                       {sum(ciclos) / sum(ics):.2f}")
        if perfil:
            imprimir_perfil(cpu, etiquetas(perfil), len(precios))
        imprimir("Python (CruceMedias)", r_py)
        print(f"  No operar:                   {CAJA0}")
        print(f"  Comprar y mantener:          {r_py['bh']}")
        print(f"  Decisiones iguales:          {iguales}/{len(precios)} ticks")

        nombre = "decisiones_python.csv" if len(series) == 1 else f"decisiones_python_{ruta.stem}.csv"
        escribir_csv(Path(nombre), filas_py)
        print(f"  Decisiones de Python en {nombre}")


if __name__ == "__main__":
    main()
