"""
Prueba los algoritmos en todas las series de práctica de tb/.

    python probar.py                          panorama: todos los algoritmos, parámetros por defecto
    python probar.py --barrido Breakout       busca parámetros de un algoritmo entre varias series
    python probar.py --barrido Breakout --reservar 2
                                              deja las 2 últimas series fuera del barrido y las usa
                                              solo para verificar (por defecto se reserva 1)

Usa como serie cualquier CSV de tb/ cuyo encabezado sea "tick,price".
Todo se compara contra comprar y mantener EN CADA SERIE (lo que pesa en la nota).
"""

import argparse
from itertools import product
from pathlib import Path

from barrido import cargar_serie, correr, evaluar_en_series
from trader import Trader
from algorithms.rsi_fijo import RSIFijo
from algorithms.a2_solo import A2Solo
from algorithms.b_solo import BSolo
from algorithms.b_calentamiento import BCalentamiento
from algorithms.a2b_respaldo import A2BRespaldo
from algorithms.a2b_reagrupada import A2BReagrupada
from algorithms.cruce_medias import CruceMedias
from algorithms.breakout import Breakout
from algorithms.desviacion_media import DesviacionMedia
from algorithms.bandas_desviacion import BandasDesviacion
from algorithms.patrones import Patrones
from algorithms.lms import LMS

TB = Path(__file__).resolve().parent.parent / "tb"     # carpeta con las series de práctica

ALGORITMOS = {                                          # nombre en la línea de comandos -> clase
    "NoOperar": Trader,
    "RSIFijo": RSIFijo, 
    "A2Solo": A2Solo, 
    "BSolo": BSolo, 
    "BCalentamiento": BCalentamiento,
    "A2BRespaldo": A2BRespaldo, 
    "A2BReagrupada": A2BReagrupada,
    "CruceMedias": CruceMedias, 
    "Breakout": Breakout,
    "DesviacionMedia": DesviacionMedia, 
    "BandasDesviacion": BandasDesviacion,
    "Patrones": Patrones, 
    "LMS": LMS,
}

GRILLAS = {                                             # valores a probar en --barrido, por algoritmo
    "RSIFijo":          {"bajo": [2, 3, 4, 5], "alto": [11, 12, 13, 14], "N": [16, 32, 64]},
    "A2Solo":           {"K": [16, 64, 256], "N": [16, 32, 64]},
    "BSolo":            {"entrada": [0.2, 0.5, 1, 2], "h": [4, 8, 16, 32], "salida": [-1, -0.5, 0]},
    "BCalentamiento":   {"entrada": [0.2, 0.5, 1, 2], "h": [4, 8, 16, 32], "C_min": [10, 20, 50]},
    "A2BRespaldo":      {"entrada": [0.2, 0.5, 1, 2], "h": [4, 8, 16, 32], "K": [16, 64, 256]},
    "A2BReagrupada":    {"entrada": [0.2, 0.5, 1, 2], "h": [4, 8, 16, 32], "K": [16, 64, 256]},
    "CruceMedias":      {"margen": [0, 0.5, 1, 2], "N_corta": [4, 8, 16], "N_larga": [32, 64, 128]},
    "Breakout":         {"N_entrada": [32, 64, 128, 256], "N_salida": [16, 32, 64]},
    "DesviacionMedia":  {"umbral": [2, 3, 5, 8], "N": [16, 32, 64]},
    "BandasDesviacion": {"k": [1, 1.5, 2, 3], "N": [16, 32, 64]},
    "Patrones":         {"entrada": [0.2, 0.5, 1, 2], "h": [4, 8, 16, 32], "k": [2, 3, 4]},
    "LMS":              {"entrada": [0.2, 0.5, 1, 2], "mu": [0.0005, 0.002, 0.01], "h": [4, 8, 16]},
}


def encontrar_series() -> list[Path]:  # CSV de tb/ con encabezado "tick,price", ordenados por nombre
    series = []                                         # rutas de las series encontradas
    for ruta in sorted(TB.glob("*.csv")):
        with open(ruta) as f:
            if f.readline().strip().replace(" ", "") == "tick,price":
                series.append(ruta)
    return series


def panorama(series: list[Path]) -> None:  # tabla: cada algoritmo (por defecto) contra comprar y mantener en cada serie
    precios = {r: cargar_serie(r) for r in series}      # cada serie se lee una sola vez
    ancho = max(8, max(len(r.stem) for r in series))    # ancho de cada columna
    print(f"\nDiferencia con comprar y mantener (parámetros por defecto), {len(series)} series")
    print(f"{'algoritmo':18}" + "".join(f"{r.stem[:ancho]:>{ancho + 2}}" for r in series)
          + f"{'gana':>7}{'promedio':>10}")
    for nombre, clase in ALGORITMOS.items():
        corridas = [correr(clase, precios[r]) for r in series]   # una corrida nueva por serie
        ganadas = sum(1 for c in corridas if c["vs_bh"] > 0)     # series donde superó a comprar y mantener
        promedio = sum(c["vs_bh"] for c in corridas) / len(corridas)
        print(f"{nombre:18}" + "".join(f"{c['vs_bh']:>+{ancho + 2}}" for c in corridas)
              + f"{f'{ganadas}/{len(series)}':>7}{promedio:>+10.0f}")


def barrido_en_series(clase, grilla: dict[str, list], series: list[Path], mostrar: int = 10) -> list[tuple]:  # prueba cada combinación en todas las series
    """
    Ordena primero por en cuántas series supera a comprar y mantener, y después por la
    diferencia promedio: ganar por poco en muchas series es más confiable que ganar
    mucho en una sola.
    """
    precios = [cargar_serie(r) for r in series]         # cada serie se lee una sola vez
    nombres = list(grilla)                              # nombres de los parámetros, en orden
    resultados = []                                     # (ganadas, promedio, órdenes promedio, params)
    for valores in product(*grilla.values()):
        params = dict(zip(nombres, valores))
        corridas = [correr(clase, p, **params) for p in precios]
        ganadas = sum(1 for c in corridas if c["vs_bh"] > 0)
        promedio = sum(c["vs_bh"] for c in corridas) / len(corridas)
        ordenes = sum(c["ordenes"] for c in corridas) / len(corridas)
        resultados.append((ganadas, promedio, ordenes, params))
    resultados.sort(key=lambda r: (r[0], r[1]), reverse=True)

    print(f"\n{clase.__name__}: {len(resultados)} combinaciones en {len(series)} series "
          f"({', '.join(r.stem for r in series)})")
    for ganadas, promedio, ordenes, params in resultados[:mostrar]:
        print(f"  gana en {ganadas}/{len(series)} | promedio vs B&H {promedio:>+7.0f} | "
              f"órdenes promedio {ordenes:>6.0f} | {params}")
    return resultados


def main():  # panorama por defecto, o barrido de un algoritmo con series reservadas para verificar
    ap = argparse.ArgumentParser(description="Prueba los algoritmos en las series de tb/.")
    ap.add_argument("--barrido", choices=list(GRILLAS), help="algoritmo cuyos parámetros buscar")
    ap.add_argument("--reservar", type=int, default=1,
                    help="cuántas series (las últimas) se dejan fuera del barrido para verificar")
    args = ap.parse_args()

    series = encontrar_series()
    if not series:
        raise SystemExit(f"No encontré series 'tick,price' en {TB}")
    print("Series:", ", ".join(r.name for r in series))

    if not args.barrido:
        panorama(series)
        return

    if not 0 <= args.reservar < len(series):
        raise SystemExit(f"--reservar tiene que estar entre 0 y {len(series) - 1}")
    corte = len(series) - args.reservar                 # las primeras eligen, las últimas verifican
    calibracion, verificacion = series[:corte], series[corte:]
    clase = ALGORITMOS[args.barrido]
    resultados = barrido_en_series(clase, GRILLAS[args.barrido], calibracion)
    if verificacion:
        print("\nVerificación de los 3 mejores en las series reservadas:")
        for _, _, _, params in resultados[:3]:
            evaluar_en_series(clase, params, verificacion)


if __name__ == "__main__":
    main()
