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
 
Con varias series escribe un CSV por serie: decisiones_python_<serie>.csv
"""
import sys
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
        self.instr = 0                # instrucciones ejecutadas en total
        self.cyc = 0                  # ciclos en total
 
    def load(self, a: int) -> int:  # lectura de memoria o de un registro del SPI
        if a == SPI:
            return self.new                       # STATUS (cs_active se toma como 0)
        if a == SPI + 4:
            self.new = 0                          # leer PRICE baja new_price
            return self.price
        assert a < 2048 and a % 4 == 0, f"lectura fuera de la RAM: {a:#x}"
        return self.mem[a // 4]
 
    def store(self, a: int, v: int) -> None:  # escritura en memoria, en DECISION o en los periféricos
        if a == SPI + 8:
            self.decision = v & 0xFF              # DECISION: solo el byte bajo
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
        elif op == 0x37:    # lui
            wr = i & 0xFFFFF000
        elif op == 0x6F:    # jal (y j)
            im = sx(((i >> 31) << 20) | (((i >> 12) & 0xFF) << 12) | (((i >> 20) & 1) << 11) | (((i >> 21) & 0x3FF) << 1), 21)
            wr, nxt, c = self.pc + 4, self.pc + im, 3
        else:
            raise ValueError(f"instrucción no soportada por el emulador: {i:08x} en {self.pc:#x}")
        if wr is not None and rd:
            self.r[rd] = u32(wr)                  # x0 nunca se escribe
        self.pc = nxt
        self.instr += 1
        self.cyc += c
 
    def arrancar(self) -> None:  # corre la inicialización hasta la primera lectura de STATUS
        while True:
            i = self.mem[self.pc // 4]
            if i & 0x7F == 0x03 and self.r[(i >> 15) & 0x1F] == SPI:
                return
            self.step()
 
    def tick(self, precio: int) -> tuple[int, int, int]:  # entrega un precio y corre hasta que se escribe DECISION
        self.price, self.new, self.decision = precio, 1, None
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
# Programa principal
# ---------------------------------------------------------------------------
 
def main() -> None:  # emula trade.s y Python en cada serie, imprime el resumen y escribe los CSV
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    hexfile, series = sys.argv[1], sys.argv[2:]
 
    for ruta in map(Path, series):
        precios = [int(l.split(",")[1]) for l in open(ruta).read().split()[1:]]   # salta el encabezado
 
        cpu = Espino(hexfile)
        cpu.arrancar()
        asm, ics, ciclos = [], [], []             # bytes escritos, IC y ciclos de cada tick
        for p in precios:
            d, ic, cy = cpu.tick(p)
            asm.append(d); ics.append(ic); ciclos.append(cy)
        py = decisiones_python(precios)
 
        filas_asm, r_asm = contabilidad(asm, precios)
        filas_py, r_py = contabilidad(py, precios)
        iguales = sum(a == b for a, b in zip(asm, py))            # ticks con el mismo byte
 
        print(f"\n=== {ruta.stem} ({len(precios)} ticks)")
        imprimir("trade.s (emulado)", r_asm)
        print(f"    Peor caso precio->decision: {max(ciclos)} ciclos (disponibles: {DISPONIBLES})")
        print(f"    IC por tick:               promedio {sum(ics) / len(ics):.1f}, máximo {max(ics)}")
        print(f"    Ciclos por tick:           promedio {sum(ciclos) / len(ciclos):.1f}, máximo {max(ciclos)}")
        print(f"    CPI:                       {sum(ciclos) / sum(ics):.2f}")
        imprimir("Python (CruceMedias)", r_py)
        print(f"  No operar:                   {CAJA0}")
        print(f"  Comprar y mantener:          {r_py['bh']}")
        print(f"  Decisiones iguales:          {iguales}/{len(precios)} ticks")
 
        nombre = "decisiones_python.csv" if len(series) == 1 else f"decisiones_python_{ruta.stem}.csv"
        escribir_csv(Path(nombre), filas_py)
        print(f"  Decisiones de Python en {nombre}")
 
 
if __name__ == "__main__":
    main()
 