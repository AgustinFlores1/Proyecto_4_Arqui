# Códigos de acción: van en los bits [7:6] del byte de decisión
MANTENER = 0   # 00: no hacer nada
COMPRAR = 1    # 01: comprar q acciones
VENDER = 2     # 10: vender q acciones


class Trader:
    """
    Un trader es el equivalente a nuestra FPGA: recibe un precio por tick,
    lleva sus propias métricas y escribe su decisión en self.decision
    (el "registro DECISION"), que el mercado lee en el tick siguiente.

    La clase base siempre mantiene, así que funciona como la referencia
    "no operar". Las subclases solo sobrescriben make_decision().
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int) -> None:
        self.name = _name                           # nombre para identificarlo en los resultados
        self.cash = _initial_capital                # caja: dinero disponible; es lo que limita las compras
        self.commision = _market_comission          # comisión que cobra el mercado por cada orden ejecutada
        self.stocks: int = 0                        # acciones que tiene el trader
        self.orders: int = 0                        # órdenes que el mercado ejecutó (para el informe)
        self.decision: int = 0x00                   # byte que el mercado lee y ejecuta en el próximo tick (registro DECISION)
        self.wealth: int = _initial_capital         # patrimonio = caja + acciones × precio actual
        self.peak_wealth: int = _initial_capital    # patrimonio más alto que ha tenido
        self.max_wealth_drop: int = 0               # mayor caída del patrimonio desde un peak (pérdida máxima)
        self.wealth_history: list[int] = []         # patrimonio en cada tick, para graficar el desempeño

    def receive_price(self, stock_price: int) -> None:
        self.update_stats(stock_price)
        accion, cantidad = self.make_decision(stock_price)
        self.decision = self.intention_to_byte(accion, cantidad)

    def apply_purchase(self, purchased_stocks: int, price: int) -> None:
        self.cash -= purchased_stocks * price + self.commision
        self.stocks += purchased_stocks
        self.orders += 1

    def apply_sell(self, sold_stocks: int, price: int) -> None:
        self.cash += sold_stocks * price - self.commision
        self.stocks -= sold_stocks
        self.orders += 1

    def update_stats(self, price: int) -> None:
        self.wealth = self.cash + self.stocks * price
        self.wealth_history.append(self.wealth)

        if self.wealth > self.peak_wealth:
            self.peak_wealth = self.wealth

        caida = self.peak_wealth - self.wealth
        if caida > self.max_wealth_drop:
            self.max_wealth_drop = caida

    # ------------------------------------------------------------------
    # Decisión
    # ------------------------------------------------------------------
    def make_decision(self, price: int) -> tuple[int, int]:  # algoritmo de decisión: cada subclase lo sobrescribe
        """
        Recibe el precio del tick y devuelve la intención (accion, cantidad),
        con accion en MANTENER/COMPRAR/VENDER y cantidad entre 0 y 63.
        No toca self.decision. La clase base siempre mantiene ("no operar").
        """
        return (MANTENER, 0)

    @staticmethod
    def intention_to_byte(accion: int, cantidad: int) -> int:  # arma el byte: bits [7:6] = acción, bits [5:0] = cantidad
        if not 0 <= accion <= 3:
            raise ValueError(f"acción inválida: {accion} (debe estar entre 0 y 3)")
        if not 0 <= cantidad <= 63:
            raise ValueError(f"cantidad inválida: {cantidad} (debe estar entre 0 y 63)")
        return (accion << 6) | cantidad

    def get_decision(self) -> int:  # devuelve el byte que el mercado tiene que ejecutar
        return self.decision

    # ------------------------------------------------------------------
    # Resultados
    # ------------------------------------------------------------------
    def print_stats(self) -> None:  # imprime el resumen del trader en una línea
        print(f"{self.name}: patrimonio {self.wealth} | caja {self.cash} | acciones {self.stocks} | "
              f"órdenes {self.orders} | comisiones {self.orders * self.commision} | "
              f"pérdida máx {self.max_wealth_drop}")
