from pathlib import Path

from market import Market
from trader import Trader
from algorithms.referencias import ComprarYMantener
from algorithms.rsi_fijo import RSIFijo
from algorithms.a2_solo import A2Solo
from algorithms.b_solo import BSolo
from algorithms.b_calentamiento import BCalentamiento
from algorithms.a2b_respaldo import A2BRespaldo
from algorithms.a2b_reagrupada import A2BReagrupada

INITIAL_CAPITAL_PER_TRADER = 10000   # caja inicial de cada trader
COMISSION_PER_TRADE = 5              # comisión por orden ejecutada

# Ruta del CSV armada desde la ubicación de este archivo: funciona desde cualquier carpeta
SERIE = Path(__file__).resolve().parent.parent / "tb" / "practica.csv"


def main():  # arma el mercado, inserta los traders, corre la simulación e imprime los resultados
    market = Market(COMISSION_PER_TRADE, INITIAL_CAPITAL_PER_TRADER)
    market.fill_stock_prices(SERIE)

    capital, comision = market.capital_per_trader, market.commision   # valores con que se crea cada trader
    traders = [                                                       # un trader por algoritmo
        Trader("No operar", capital, comision),
        ComprarYMantener("Comprar y mantener", capital, comision),
        # Componentes por separado
        RSIFijo("RSI solo (umbrales fijos)", capital, comision),
        A2Solo("A2 solo", capital, comision),
        BSolo("B solo", capital, comision),
        # Combinaciones
        BCalentamiento("B + calentamiento", capital, comision),
        A2BRespaldo("A2 + B respaldo", capital, comision),
        A2BReagrupada("A2 + B reagrupada", capital, comision),
    ]
    for trader in traders:
        market.insert_trader(trader)

    market.run_sim()

    print(f"{len(market.stock_prices)} ticks | comprar y mantener (fórmula del testbench): "
          f"{market.buy_and_hold_reference()}")
    for trader in traders:
        trader.print_stats()


if __name__ == "__main__":
    main()
