"""
Compara estrategias sobre la serie de práctica.

    python3 comparar.py                     # serie completa + mitades
    python3 comparar.py --ticks 2000        # igual que el testbench por defecto
    python3 comparar.py --csv sim.csv       # además escribe decisiones de la primera estrategia

La serie se divide en calibración (primera mitad) y validación (segunda mitad).
Ajusten parámetros SOLO mirando calibración; validación dice si generaliza.
"""

import argparse
import itertools

from mercado import simular, comprar_y_mantener, leer_serie, escribir_decisiones, serie_por_defecto, CAJA0
from estrategias.referencias import NoOperar, CompraInicial
from estrategias.rsi_aprende import BCalentamiento, A2BRespaldo, A2BReagrupada

# Cada entrada: (fábrica sin argumentos). Se crea una instancia nueva por corrida.
ESTRATEGIAS = [
    NoOperar,
    CompraInicial,
    BCalentamiento,
    A2BRespaldo,
    A2BReagrupada,
]


def tabla(precios, fabricas, titulo):
    bh = comprar_y_mantener(precios)
    print(f"\n== {titulo}: {len(precios)} ticks | comprar y mantener (fórmula TB) = {bh}")
    print(f"{'estrategia':32} {'patrimonio':>10} {'vs B&H':>8} {'órdenes':>8} {'comisiones':>10} {'pérdida máx':>11}")
    resultados = []
    for fab in fabricas:
        r = simular(fab(), precios)
        resultados.append(r)
        print(f"{r.nombre:32} {r.patrimonio_final:>10} {r.patrimonio_final - bh:>+8} "
              f"{r.ordenes:>8} {r.comisiones:>10} {r.max_dd:>11}")
    return resultados


def barrido(clase, grilla, precios):
    """
    Prueba todas las combinaciones de parámetros en 'grilla' (dict nombre -> lista).
    Devuelve [(patrimonio, params)] ordenado de mejor a peor.
    Úsenlo sobre calibración y verifiquen el ganador sobre validación.
    """
    nombres = list(grilla)
    salida = []
    for valores in itertools.product(*(grilla[n] for n in nombres)):
        params = dict(zip(nombres, valores))
        r = simular(clase(**params), precios)
        salida.append((r.patrimonio_final, params))
    salida.sort(key=lambda x: -x[0])
    return salida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serie", default=None, help="por defecto, tb/practica.csv del repo")
    ap.add_argument("--ticks", type=int, default=None)
    ap.add_argument("--csv", default=None, help="escribe un decisiones.csv para comparar con el del testbench")
    ap.add_argument("--cual", type=int, default=2, help="índice en ESTRATEGIAS de la que se escribe con --csv")
    args = ap.parse_args()

    precios = leer_serie(args.serie or serie_por_defecto())
    if args.ticks:
        precios = precios[: args.ticks]
    mitad = len(precios) // 2

    tabla(precios[:mitad], ESTRATEGIAS, "Calibración")
    tabla(precios[mitad:], ESTRATEGIAS, "Validación")
    tabla(precios, ESTRATEGIAS, "Serie completa")
    print(f"\n(No operar siempre termina en {CAJA0}.)")

    if args.csv:
        r = simular(ESTRATEGIAS[args.cual](), precios, guardar_filas=True)
        escribir_decisiones(r, args.csv)
        print(f"Decisiones de '{r.nombre}' escritas en {args.csv}")


if __name__ == "__main__":
    main()
