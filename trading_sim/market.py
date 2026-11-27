from trader import Trader, COMPRAR, VENDER

class Market:
    """
    El equivalente a la FPGA maestra: lee la serie, entrega los precios a los
    traders tick a tick y ejecuta sus decisiones con las reglas del testbench.

    Orden por tick, para cada trader:
      1. leer la decisión que el trader escribió en el tick ANTERIOR
      2. ejecutarla al precio de ESTE tick (si es válida y alcanza)
      3. entregarle el precio al trader, que actualiza sus métricas y decide de nuevo
    Lo que el trader decide en el paso 3 se ejecuta en el paso 1 del tick siguiente:
    ese es el desfase del protocolo, sin mirar nunca un precio futuro.
    """

    def __init__(self, _comission: int, _capital_per_trader: int) -> None:
        self.capital_per_trader = _capital_per_trader
        self.commision = _comission
        self.stock_prices: list[int] = []
        self.traders: list[Trader] = []

    def insert_trader(self, trader: Trader) -> None:
        self.traders.append(trader)

    def fill_stock_prices(self, file_name: str) -> None:
        with open(file_name, "r") as testbench:
            for line in testbench:
                line = line.strip()
                if line == "" or not line[0].isdigit():
                    continue
                price = line.split(",")[1]
                self.stock_prices.append(int(price))

    def get_stock_prices_with_tick(self) -> list[tuple[int, int]]:
        return [(tick, price) for tick, price in enumerate(self.stock_prices)]

    @staticmethod
    def _decode_decision(decision: int) -> tuple[int, int]:
        """Separa el byte en (acción, cantidad): bits [7:6] y bits [5:0]."""
        action = (decision >> 6) & 0b11
        stock_quantity = decision & 0b111111
        return action, stock_quantity


    def execute_decision(self, trader: Trader, price: int):
        decision = trader.get_decision()
        if not isinstance(decision, int) or not (0 <= decision <= 0xFF):
            raise ValueError(f"{trader.name} escribió una decisión inválida: {decision!r}")

        action, stock_quantity = self._decode_decision(decision)

        if action == COMPRAR:
            able_to_buy = (trader.cash - self.commision) // price
            stocks_purchased = min(stock_quantity, able_to_buy)

            if stocks_purchased > 0:                   # como el testbench: sin acciones compradas no hay orden ni comisión
                trader.apply_purchase(stocks_purchased, price)

        elif action == VENDER:
            stocks_sold = min(stock_quantity, trader.stocks)
            wealth_gained = trader.cash + stocks_sold * price

            if stocks_sold > 0 and wealth_gained >= self.commision:
                trader.apply_sell(stocks_sold, price)

    def run_sim(self) -> None:
        for tick, price in self.get_stock_prices_with_tick():
            for trader in self.traders:
                self.execute_decision(trader, price)
                trader.receive_price(price)

    def buy_and_hold_reference(self) -> int:
        """Referencia 'comprar y mantener' con la misma fórmula que imprime el testbench."""
        primero, ultimo = self.stock_prices[0], self.stock_prices[-1]
        q = (self.capital_per_trader - self.commision) // primero
        return self.capital_per_trader - self.commision - q * primero + q * ultimo