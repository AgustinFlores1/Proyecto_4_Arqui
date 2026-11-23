from pathlib import Path

from market import Market
from trader import Trader
from grafico import graficar_serie
from algorithms.referencias import ComprarYMantener
from algorithms.rsi_fijo import RSIFijo
from algorithms.cruce_medias import CruceMedias
from algorithms.toma_ganancia import TomaGanancia

INITIAL_CAPITAL_PER_TRADER = 10000   # caja inicial de cada trader
COMISSION_PER_TRADE = 5              # comisión por orden ejecutada

# Rutas armadas desde la ubicación de este archivo: funcionan desde cualquier carpeta
TB = Path(__file__).resolve().parent.parent / "tb"          # series de práctica
RESERVADAS = TB / "reservadas"                               # series apartadas para verificar
GRAFICOS = Path(__file__).resolve().parent / "graficos"      # carpeta donde se guarda un gráfico por serie


def encontrar_series(carpeta: Path) -> list[Path]:  # CSV de la carpeta con encabezado "tick,price", ordenados por nombre
    series = []                                      # rutas de las series encontradas
    for ruta in sorted(carpeta.glob("*.csv")):
        with open(ruta) as f:
            if f.readline().strip().replace(" ", "") == "tick,price":
                series.append(ruta)
    return series


def crear_traders(c: int, k: int) -> tuple[list[Trader], list[Trader]]:  # traders nuevos para una serie: (referencias, candidatos)
    referencias = [                                  # se comparan contra todos, en gris
        Trader("No operar", c, k),
        ComprarYMantener("Comprar y mantener", c, k),
    ]
    candidatos = [                                   # los tres candidatos con sus parámetros elegidos
        RSIFijo("RSI fijo (N 46, 4/14)", c, k, N=46, bajo=4, alto=14),
        CruceMedias("Cruce de medias (8/32, margen 2)", c, k, N_corta=8, N_larga=32, margen=2),
        TomaGanancia("Toma de ganancia (7/5/10)", c, k, umbral=7, caida=5, recompra=10),
    ]
    return referencias, candidatos


def simular_serie(ruta: Path, carpeta_graficos: Path) -> list[Trader]:  # corre una serie, guarda su gráfico y devuelve los traders
    market = Market(COMISSION_PER_TRADE, INITIAL_CAPITAL_PER_TRADER)
    market.fill_stock_prices(ruta)

    referencias, candidatos = crear_traders(market.capital_per_trader, market.commision)
    for trader in referencias + candidatos:
        market.insert_trader(trader)
    market.run_sim()

    graficar_serie(market.stock_prices, ruta.stem, candidatos, referencias,
                   capital_inicial=INITIAL_CAPITAL_PER_TRADER,
                   ruta=carpeta_graficos / f"{ruta.stem}.png")
    return referencias + candidatos


def main():  # simula los candidatos en cada serie de tb/ y tb/reservadas/, imprime una tabla y guarda un gráfico por serie
    grupos = [                                       # (título, series, carpeta donde van sus gráficos)
        ("Series de calibración (tb/)", encontrar_series(TB), GRAFICOS),
        ("Series reservadas (tb/reservadas/)", encontrar_series(RESERVADAS), GRAFICOS),
    ]

    for titulo, series, carpeta in grupos:
        if not series:
            continue
        print(f"\n===== {titulo}")
        for ruta in series:
            traders = simular_serie(ruta, carpeta)
            print(f"\n{ruta.stem}")
            for trader in traders:
                trader.print_stats()             # patrimonio, caja, acciones, órdenes, comisiones y pérdida máxima
        print(f"\nGráficos en {carpeta}")


if __name__ == "__main__":
    main()