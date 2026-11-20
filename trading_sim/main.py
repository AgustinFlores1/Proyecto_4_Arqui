INITIAL_CAPITAL_PER_TRADER = 10000
COMISSION_PER_TRADE = 5

from market import Market
from trader import Trader

def main():
    market = Market(COMISSION_PER_TRADE, INITIAL_CAPITAL_PER_TRADER)
    algorythm_1_trader = Trader(
        "algoritmo_1",
        market.capital_per_trader,
        market.commision
    )

    algorythm_2_trader = Trader(
        "algoritmo_2",
        market.capital_per_trader,
        market.commision
    )

    algorythm_3_trader = Trader(
        "algoritmo_3",
        market.capital_per_trader,
        market.commision
    )

    market.fill_stock_prices("../tb/practica.csv")

    for tick, price in market.stock_prices:
        ...