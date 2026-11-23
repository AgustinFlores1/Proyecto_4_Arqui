"""
Prueba los algoritmos en todas las series de práctica de tb/.

    python probar.py                          panorama: todos los algoritmos, parámetros por defecto
    python probar.py --barrido Breakout       busca parámetros de un algoritmo entre varias series
    python probar.py --barrido Breakout --reservar 2
                                              deja las 2 últimas series fuera del barrido y las usa
                                              solo para verificar (por defecto se reserva 1)
    python probar.py --barrido Breakout --graficar
                                              además grafica las 5 mejores combinaciones en cada
                                              serie (--graficar 3 para graficar 3)
    python probar.py --barrido Breakout --reservar 0 --series --graficar 5
                                              elige con las series de tb/ y verifica y grafica las
                                              5 mejores en todas las series de tb/reservadas/

Los gráficos quedan en graficos_barrido/<algoritmo>/<serie>.png.

El barrido siempre elige con los CSV de tb/ cuyo encabezado sea "tick,price".
Todo se compara contra comprar y mantener EN CADA SERIE (lo que pesa en la nota).
"""

import argparse
from itertools import product
from pathlib import Path

from barrido import CAPITAL, COMISION, cargar_serie, correr, evaluar_en_series
from market import Market
from trader import Trader
from grafico import graficar_serie
from algorithms.referencias import ComprarYMantener
from algorithms.rsi_fijo import RSIFijo
# from algorithms.a2_solo import A2Solo
# from algorithms.b_solo import BSolo
# from algorithms.b_calentamiento import BCalentamiento
# from algorithms.a2b_respaldo import A2BRespaldo
# from algorithms.a2b_reagrupada import A2BReagrupada
from algorithms.cruce_medias import CruceMedias
# from algorithms.breakout import Breakout
# from algorithms.desviacion_media import DesviacionMedia
# from algorithms.bandas_desviacion import BandasDesviacion
# from algorithms.patrones import Patrones
# from algorithms.lms import LMS
# from algorithms.rachas import Rachas
from algorithms.toma_ganancia import TomaGanancia
# from algorithms.lotes import Lotes

TB = Path(__file__).resolve().parent.parent / "tb"     # carpeta con las series de práctica
RESERVADAS = TB / "reservadas"                          # series apartadas, solo para verificar al final
GRAFICOS = Path(__file__).resolve().parent / "graficos_barrido"   # carpeta de los gráficos de --graficar

ALGORITMOS = {                                          # nombre en la línea de comandos -> clase
    "NoOperar": Trader,
    "RSIFijo": RSIFijo, 
    # "A2Solo": A2Solo, 
    # "BSolo": BSolo, 
    # "BCalentamiento": BCalentamiento,
    # "A2BRespaldo": A2BRespaldo, 
    # "A2BReagrupada": A2BReagrupada,
    "CruceMedias": CruceMedias, 
    # "Breakout": Breakout,
    # "DesviacionMedia": DesviacionMedia, 
    # "BandasDesviacion": BandasDesviacion,
    # "Patrones": Patrones, 
    # "LMS": LMS,
    # "Rachas": Rachas, 
    "TomaGanancia": TomaGanancia, 
    #"Lotes": Lotes
}

GRILLAS = {                                             # valores a probar en --barrido, por algoritmo
    "RSIFijo":          {"bajo": [4], "alto": [14], "N": [46, 48]},
    # "A2Solo":           {"K": [256, 512, 1024], "N": [48, 64, 80]},
    # "BSolo":            {"entrada": [2, 3, 4], "h": [4, 5, 6], "salida": [-1, -0.5], "N": [48]},
    # "BCalentamiento":   {"entrada": [4, 8], "h": [4, 8, 16], "C_min": [25, 50]},
    # "A2BRespaldo":      {"entrada": [4, 6, 8], "h": [16, 32, 64], "K": [128, 192, 256]},
    # "A2BReagrupada":    {"entrada": [4, 6, 8], "h": [16, 32], "K": [16, 32, 64, 96]},
    "CruceMedias":      {"margen": [2], "N_corta": [8], "N_larga": [32]},
    # "Breakout":         {"N_entrada": [32, 64, 128], "N_salida": [16, 32, 64]},
    # "DesviacionMedia":  {"umbral": [4, 5, 6], "N": [8, 12, 16]},
    # "BandasDesviacion": {"k": [4, 5, 6], "N": [2, 4, 8]},
    # "Patrones":         {"entrada": [2, 3, 4], "h": [8, 16], "k": [2, 3]},
    # "LMS":              {"entrada": [2, 3], "mu": [0.005, 0.01], "h": [4, 8]},
    # "Rachas":       {"n_bajas": [2, 3, 5, 6, 7], "n_subidas": [2, 3, 6, 7]},
    "TomaGanancia": {"umbral": [6, 7, 8], "caida": [4, 5, 6], "recompra": [9, 10, 11]},
    # "Lotes":        {"q": [16, 32, 63], "bajada": [1, 2, 4, 6, 8, 10, 12, 16, 32, 64, 128, 256, 512], "subida": [7, 8, 9]},
}


def encontrar_series(carpeta: Path = TB) -> list[Path]:  # CSV de la carpeta con encabezado "tick,price", ordenados por nombre
    series = []                                         # rutas de las series encontradas
    for ruta in sorted(carpeta.glob("*.csv")):
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


def texto_params(params: dict) -> str:  # {"N": 16, "k": 2} -> "N=16 k=2" (para las leyendas)
    return " ".join(f"{k}={v}" for k, v in params.items()) or "por defecto"


def graficar_mejores(clase, resultados: list[tuple], series: list[Path], reservadas: list[Path],
                     cantidad: int) -> None:  # grafica las mejores combinaciones del barrido en cada serie
    """
    Un gráfico por serie, con el precio arriba y abajo el patrimonio de las 'cantidad'
    mejores combinaciones (en color) junto a no operar y comprar y mantener (en gris).
    """
    carpeta = GRAFICOS / clase.__name__                 # una subcarpeta por algoritmo
    mejores = [params for *_, params in resultados[:cantidad]]   # parámetros de las mejores combinaciones
    print(f"\nGráficos de las {len(mejores)} mejores combinaciones:")
    for ruta in series:
        mercado = Market(COMISION, CAPITAL)
        mercado.stock_prices = cargar_serie(ruta)
        referencias = [Trader("No operar", CAPITAL, COMISION),
                       ComprarYMantener("Comprar y mantener", CAPITAL, COMISION)]
        traders = [clase(f"#{i} {texto_params(p)}", CAPITAL, COMISION, **p)
                   for i, p in enumerate(mejores, start=1)]
        for t in referencias + traders:
            mercado.insert_trader(t)
        mercado.run_sim()

        tipo = "reservada" if ruta in reservadas else "elección"   # si la serie se usó para elegir o solo para verificar
        destino = carpeta / f"{ruta.stem}.png"
        graficar_serie(mercado.stock_prices, f"{clase.__name__} en {ruta.stem} ({tipo})",
                       traders, referencias, CAPITAL, destino)
        print(f"  {destino}")


def main():  # panorama por defecto, o barrido de un algoritmo con series reservadas para verificar
    ap = argparse.ArgumentParser(description="Prueba los algoritmos en las series de tb/.")
    ap.add_argument("--barrido", choices=list(GRILLAS), help="algoritmo cuyos parámetros buscar")
    ap.add_argument("--reservar", type=int, default=1,
                    help="cuántas series (las últimas) se dejan fuera del barrido para verificar")
    ap.add_argument("--series", action="store_true",
                    help="verificar y graficar las mejores en las series de tb/reservadas/ (con --barrido)")
    ap.add_argument("--graficar", type=int, nargs="?", const=5, default=0, metavar="N",
                    help="graficar las N mejores combinaciones en cada serie (sin número: 5)")
    args = ap.parse_args()

    series = encontrar_series()                         # series de tb/, con las que se elige
    if not series:
        raise SystemExit(f"No encontré series 'tick,price' en {TB}")
    print("Series:", ", ".join(r.name for r in series))

    if not args.barrido:
        if args.graficar or args.series:
            ap.error("--graficar y --series se usan junto con --barrido")
        panorama(series)
        return

    if not 0 <= args.reservar < len(series):
        raise SystemExit(f"--reservar tiene que estar entre 0 y {len(series) - 1}")
    corte = len(series) - args.reservar                 # las primeras eligen, las últimas verifican
    calibracion, verificacion = series[:corte], series[corte:]
    reservadas = []                                     # series de tb/reservadas/ (solo con --series)
    if args.series:
        reservadas = encontrar_series(RESERVADAS) if RESERVADAS.is_dir() else []
        if not reservadas:
            raise SystemExit(f"No encontré series 'tick,price' en {RESERVADAS}")
        print("Reservadas:", ", ".join(r.name for r in reservadas))
        verificacion = verificacion + reservadas
    clase = ALGORITMOS[args.barrido]
    resultados = barrido_en_series(clase, GRILLAS[args.barrido], calibracion, mostrar=15)
    if verificacion:
        cuantos = args.graficar or 3                    # se verifican las mismas que se grafican (o 3)
        print(f"\nVerificación de los {cuantos} mejores en las series reservadas:")
        for _, _, _, params in resultados[:cuantos]:
            evaluar_en_series(clase, params, verificacion)
    if args.graficar:
        donde = reservadas if args.series else series   # con --series, solo en las de reserva
        graficar_mejores(clase, resultados, donde, verificacion, args.graficar)


if __name__ == "__main__":
    main()
