MANTENER = 0
COMPRAR = 1
VENDER = 2

class Trader:
    """
    Un trader es el equivalente a nuestra FPGA: recibe un precio por tick,
    lleva sus propias métricas y escribe su decisión en self.decision
    (el "registro DECISION"), que el mercado lee en el tick siguiente.

    La clase base siempre mantiene, así que funciona como la referencia
    "no operar". Las subclases solo sobrescriben make_decision().
    """
    def __init__(self, _name: str, _initial_capital: int, _market_comission: int) -> None:
        self.name = _name
        self.cash = _initial_capital       # Cash to buy stocks
        self.commision = _market_comission
        self.stocks: int = 0
        self.orders: int = 0
        self.decision: int = 0x00                 # Byte that reads the market
        self.wealth: int = _initial_capital       # Wealth = cash + stocks * price
        self.peak_wealth: int = _initial_capital  # Highest wealth achieved
        self.max_wealth_drop: int = 0             # Highest drop in money from peak

    def recieve_price(self, stock_price: int) -> int:
        self.update_stats(stock_price)

        action, stock_quantity = self.make_decision(stock_price)
        self.decision = self.action_to_bytes(action, stock_quantity)

    def apply_purchase(self, purchased_stocks: int, price: int) -> None:
        self.cash -= purchased_stocks * price + self.commision
        self.stocks += purchased_stocks
        self.orders += 1
        return

    def apply_sell(self, sold_stocks: int, price: int) -> None:
        self.cash += sold_stocks * price - self.commision
        self.stocks -= sold_stocks
        self.orders += 1
        return

    def update_stats(self, price: int) -> None:
        self.wealth = self.cash + self.stocks * price

        if self.wealth > self.peak_wealth:
            self.peak_wealth = self.wealth

        price_drop = self.peak_wealth - self.wealth
        if price_drop > self.max_wealth_drop:
            self.max_wealth_drop = price_drop

    def make_decision(self) -> tuple[int, int]:
        """
        Cambia en cada subclase. Recibe el precio del tick y devuelve la
        intención (accion, cantidad), con accion en MANTENER/COMPRAR/VENDER
        y cantidad entre 0 y 63. No toca self.decision.
        """
        return (MANTENER, 0)

    @staticmethod
    def _action_to_bytes(action: int, stock_quantity: int) -> int:
        """Arma el byte de decisión: bits [7:6] = acción, bits [5:0] = cantidad."""
        if not (0 <= action <= 3):
            raise ValueError(f"acción inválida: {action} (debe estar entre 0 y 3)")
        
        if not (0 <= stock_quantity <= 63):
            raise ValueError(f"cantidad inválida: {stock_quantity} (debe estar entre 0 y 63)")
        
        return (action << 6) | stock_quantity

    def print_stats(self) -> None:
        print(f"{self.name}: patrimonio {self.wealth} | caja {self.cash} | acciones {self.stocks} | "
              f"órdenes {self.orders} | comisiones {self.orders * self.commision} | "
              f"pérdida máx {self.max_wealth_drop}")
