"""
Réplica en Python de la FPGA maestra (tb_proyecto_4.sv).

La contabilidad está copiada regla por regla del testbench para que el
patrimonio de este simulador y el de la simulación RTL coincidan exactamente.
Si el curso publica otros valores de caja inicial o comisión, cámbielos aquí.
"""

from dataclasses import dataclass, field

CAJA0 = 10000
COMISION = 5

MANTENER = 0b00
COMPRAR = 0b01
VENDER = 0b10


def byte_comprar(q: int) -> int:
    """Byte de decisión 'comprar q' (q entre 0 y 63)."""
    assert 0 <= q <= 63
    return (COMPRAR << 6) | q


def byte_vender(q: int) -> int:
    assert 0 <= q <= 63
    return (VENDER << 6) | q


BYTE_MANTENER = 0x00


def div_trunc(a: int, b: int) -> int:
    """División entera que trunca hacia cero, como el '/' de SystemVerilog con int."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


@dataclass
class Contabilidad:
    """Caja, acciones y métricas, con las mismas reglas que la tarea ejecutar() del testbench."""

    caja: int = CAJA0
    acciones: int = 0
    comision: int = COMISION
    ordenes: int = 0
    patrimonio: int = CAJA0
    peak: int = CAJA0
    max_dd: int = 0

    def ejecutar(self, decision: int, p: int) -> None:
        q = decision & 0x3F
        accion = (decision >> 6) & 0b11
        if accion == COMPRAR:
            limite = div_trunc(self.caja - self.comision, p)
            if q > limite:
                q = limite
            if q > 0:
                self.caja -= q * p + self.comision
                self.acciones += q
                self.ordenes += 1
        elif accion == VENDER:
            if q > self.acciones:
                q = self.acciones
            if q > 0 and self.caja + q * p >= self.comision:
                self.caja += q * p - self.comision
                self.acciones -= q
                self.ordenes += 1
        # 00 y 11: mantener
        self.patrimonio = self.caja + self.acciones * p
        if self.patrimonio > self.peak:
            self.peak = self.patrimonio
        if self.peak - self.patrimonio > self.max_dd:
            self.max_dd = self.peak - self.patrimonio


@dataclass
class Resultado:
    nombre: str
    patrimonio_final: int
    ordenes: int
    comisiones: int
    max_dd: int
    filas: list = field(default_factory=list, repr=False)


def simular(estrategia, precios, caja0=CAJA0, comision=COMISION, guardar_filas=False) -> Resultado:
    """
    Corre una estrategia sobre una serie, con el mismo orden de eventos que la placa:

      tick n:  1) transacción SPI: la maestra lee DECISION (escrita tras p[n-1])
                  y la ejecuta al precio p[n]
               2) el CPU recibe p[n] y escribe un nuevo DECISION

    La estrategia solo recibe un precio por llamada, así que no puede mirar el futuro.
    Lo que devuelve es lo que queda en el registro DECISION: si devuelve el mismo
    byte de compra dos veces seguidas, compra dos veces (igual que en la placa).
    """
    c = Contabilidad(caja=caja0, comision=comision, patrimonio=caja0, peak=caja0)
    decision = BYTE_MANTENER  # valor de reset de DECISION: verifíquenlo en pochoco_spi_slave
    filas = []
    for n, p in enumerate(precios):
        c.ejecutar(decision, p)
        if guardar_filas:
            filas.append((n, p, decision, c.caja, c.acciones, c.patrimonio))
        decision = estrategia.tick(p)
        if not (isinstance(decision, int) and 0 <= decision <= 0xFF):
            raise ValueError(f"{type(estrategia).__name__} devolvió {decision!r} en el tick {n}; debe ser un byte")
    return Resultado(
        nombre=getattr(estrategia, "nombre", type(estrategia).__name__),
        patrimonio_final=c.patrimonio,
        ordenes=c.ordenes,
        comisiones=c.ordenes * comision,
        max_dd=c.max_dd,
        filas=filas,
    )


def comprar_y_mantener(precios, caja0=CAJA0, comision=COMISION) -> int:
    """Referencia 'comprar y mantener' con la misma fórmula que imprime el testbench."""
    q = (caja0 - comision) // precios[0]
    return caja0 - comision - q * precios[0] + q * precios[-1]


import os

_AQUI = os.path.dirname(os.path.abspath(__file__))
_CANDIDATAS = [
    os.path.join(_AQUI, "..", "tb", "practica.csv"),   # dentro del repo: Proyecto_4_Arqui/tb/practica.csv
    os.path.join(_AQUI, "datos", "practica.csv"),      # suelto, fuera del repo
]


def serie_por_defecto() -> str:
    """Ruta de la serie de práctica: la misma que usa el testbench (tb/practica.csv)."""
    for ruta in _CANDIDATAS:
        if os.path.exists(ruta):
            return os.path.normpath(ruta)
    raise FileNotFoundError("No encontré la serie. Póngala en tb/practica.csv (raíz del repo) "
                            "o en sim_trader/datos/practica.csv")


def leer_serie(ruta: str) -> list:
    """Lee un CSV 'tick,price' como el que usa el testbench."""
    with open(ruta) as f:
        next(f)  # encabezado
        return [int(linea.split(",")[1]) for linea in f if linea.strip()]


def escribir_decisiones(resultado: Resultado, ruta: str) -> None:
    """Escribe el mismo formato que decisiones.csv del testbench, para compararlos con comparar_csv.py."""
    with open(ruta, "w") as f:
        f.write("tick,precio,decision,caja,acciones,patrimonio\n")
        for n, p, d, caja, acc, w in resultado.filas:
            f.write(f"{n},{p},{d:02x},{caja},{acc},{w}\n")
