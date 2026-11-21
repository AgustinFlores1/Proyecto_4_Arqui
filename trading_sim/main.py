from pathlib import Path

from market import Market
from trader import Trader
from grafico import graficar
from algorithms.referencias import ComprarYMantener
# Familia RSI
from algorithms.rsi_fijo import RSIFijo
from algorithms.a2_solo import A2Solo
from algorithms.b_solo import BSolo
from algorithms.b_calentamiento import BCalentamiento
from algorithms.a2b_respaldo import A2BRespaldo
from algorithms.a2b_reagrupada import A2BReagrupada
# Seguimiento de tendencia
from algorithms.cruce_medias import CruceMedias
from algorithms.breakout import Breakout
# Reversión a la media
from algorithms.desviacion_media import DesviacionMedia
from algorithms.bandas_desviacion import BandasDesviacion
# Aprenden del mercado
from algorithms.patrones import Patrones
from algorithms.lms import LMS

INITIAL_CAPITAL_PER_TRADER = 10000   # caja inicial de cada trader
COMISSION_PER_TRADE = 5              # comisión por orden ejecutada

# Rutas armadas desde la ubicación de este archivo: funcionan desde cualquier carpeta
SERIE = Path(__file__).resolve().parent.parent / "tb" / "practica.csv"
GRAFICOS = Path(__file__).resolve().parent / "graficos"      # carpeta donde se guarda un gráfico por familia


def main():  # arma el mercado, inserta los traders, corre la simulación, imprime los resultados y grafica
    market = Market(COMISSION_PER_TRADE, INITIAL_CAPITAL_PER_TRADER)
    market.fill_stock_prices(SERIE)

    c, k = market.capital_per_trader, market.commision   # capital y comisión con que se crea cada trader

    referencias = [                                       # se comparan contra todos
        Trader("No operar", c, k),
        ComprarYMantener("Comprar y mantener", c, k),
    ]
    grupos = {                                            # nombre de la familia -> sus traders
        "RSI y combinaciones": [
            RSIFijo("RSI solo (umbrales fijos)", c, k),
            A2Solo("A2 solo", c, k),
            BSolo("B solo", c, k),
            BCalentamiento("B + calentamiento", c, k),
            A2BRespaldo("A2 + B respaldo", c, k),
            A2BReagrupada("A2 + B reagrupada", c, k),
        ],
        "Seguimiento de tendencia": [
            CruceMedias("Cruce de medias", c, k),
            Breakout("Breakout (Donchian)", c, k),
        ],
        "Reversión a la media": [
            DesviacionMedia("Desviación de la media", c, k),
            BandasDesviacion("Bandas de desviación", c, k),
        ],
        "Aprenden del mercado": [
            Patrones("Tabla de patrones", c, k),
            LMS("Predictor LMS", c, k),
        ],
    }

    for trader in referencias + [t for ts in grupos.values() for t in ts]:
        market.insert_trader(trader)

    market.run_sim()

    print(f"{len(market.stock_prices)} ticks | comprar y mantener (fórmula del testbench): "
          f"{market.buy_and_hold_reference()}")
    print("\n== Referencias")
    for trader in referencias:
        trader.print_stats()
    for familia, traders in grupos.items():
        print(f"\n== {familia}")
        for trader in traders:
            trader.print_stats()

    rutas = graficar(market.stock_prices, grupos, referencias,
                     capital_inicial=INITIAL_CAPITAL_PER_TRADER, carpeta=GRAFICOS, mostrar=False)
    print("\nGráficos guardados:")
    for ruta in rutas:
        print(f"  {ruta}")


if __name__ == "__main__":
    main()
