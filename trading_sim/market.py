from trader import Trader
from pathlib import Path

class Market:
    def __init__(self, _comission: int, _capital_per_trader: int) -> None:
        self.capital_per_trader = _capital_per_trader
        self.commision = _comission
        self.stock_prices: list[int] = []
        self.traders: list[Trader] = []

    def insert_trader(self, trader: Trader) -> None:
        self.traders.append(trader)
        return

    def fill_stock_prices(self, file_name: str) -> None:
        with open(file_name, "r") as testbench:
            for line in testbench:
                line = line.strip()
                if line == "" or not line[0].isdigit():
                    continue
                price = line.split(",")[1]
                self.stock_prices.append(int(price))

    def _decode_decision(self):
        pass

    def execute_decision(self, trader: Trader, decision: int, price: int):
        # if comprar -> trader.stats.change
        # elif mantener -> price = prices[tick + 1]
        # else --> algo
        pass

    def get_stock_prices_with_tick(self) -> list[tuple[int, int]]:
        prices_with_ticks = [(tick, price) for tick, price in enumerate(self.stock_prices)]
        return prices_with_ticks

    def run_sim(self):
        pass
    