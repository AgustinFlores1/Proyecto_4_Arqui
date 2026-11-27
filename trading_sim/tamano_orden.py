"""
Compara cómo decidir la cantidad q de cada orden, con CruceMedias 8/32 margen 2 fijo.

Estrategias:
  "q o nada"  compra q acciones solo si no tiene; vende todas (la que usa el proyecto con q = 63)
  "acumular"  compra 63 en cada tick con señal de compra mientras alcance la caja; vende todas
Para cada una: promedio en las 8 series de la diferencia contra comprar y mantener, contra no
operar, órdenes y pérdida máxima; y la prueba de estrés (series cortadas en su mínimo).

Uso (desde trading_sim/):  python tamano_orden.py
"""
from pathlib import Path

import algorithms.cruce_medias as cruce_medias
from algorithms.cruce_medias import CruceMedias
from market import Market
from trader import COMPRAR, VENDER, MANTENER

CAJA0, COMISION = 10000, 5
RAIZ = Path(__file__).resolve().parent.parent
SERIES = sorted((RAIZ / "tb").glob("practica*.csv")) + sorted((RAIZ / "tb" / "reservadas").glob("practica*.csv"))


def regla(modo: str, q: int):  # devuelve una función a_orden con la regla de cantidad pedida
    def a_orden(accion: int, stocks: int) -> tuple[int, int]:
        if accion == COMPRAR and (stocks == 0 or modo == "acumular"):
            return COMPRAR, q
        if accion == VENDER and stocks > 0:
            return VENDER, 63
        return MANTENER, 0
    return a_orden


def correr(precios: list[int]) -> CruceMedias:  # simula CruceMedias 8/32 m2 con la regla activa
    m = Market(COMISION, CAJA0)
    t = CruceMedias("c", CAJA0, COMISION, N_corta=8, N_larga=32, margen=2)
    m.insert_trader(t)
    m.stock_prices = precios
    m.run_sim()
    return t


def main() -> None:
    estrategias = [("16 o nada", "nada", 16), ("32 o nada", "nada", 32),
                   ("63 o nada (proyecto)", "nada", 63), ("acumular 63", "acumular", 63)]
    series = {r.stem: [int(l.split(",")[1]) for l in r.read_text().split()[1:]] for r in SERIES}
    print(f"{'estrategia':22s} {'vs B&H':>8s} {'vs no op.':>10s} {'órdenes':>8s} {'pérd. máx':>10s} {'estrés':>8s}")
    for nombre, modo, q in estrategias:
        cruce_medias.a_orden = regla(modo, q)
        vs_bh, vs_no, ordenes, perdida, estres = [], [], [], [], []
        for precios in series.values():
            t = correr(precios)
            q0 = (CAJA0 - COMISION) // precios[0]
            bh = CAJA0 - COMISION - q0 * precios[0] + q0 * precios[-1]
            vs_bh.append(t.wealth - bh); vs_no.append(t.wealth - CAJA0)
            ordenes.append(t.orders); perdida.append(t.max_wealth_drop)
            corte = precios.index(min(precios))
            if corte >= 2000:
                estres.append(correr(precios[:corte + 1]).wealth - CAJA0)
        n = len(series)
        print(f"{nombre:22s} {sum(vs_bh) / n:+8.0f} {sum(vs_no) / n:+10.0f} {sum(ordenes) / n:8.0f} "
              f"{sum(perdida) / n:10.0f} {sum(estres) / len(estres):+8.0f}")


if __name__ == "__main__":
    main()
