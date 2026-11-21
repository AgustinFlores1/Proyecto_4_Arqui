from collections import deque

from trader import Trader, MANTENER, COMPRAR, VENDER
from algorithms.herramientas import a_orden


class BandasDesviacion(Trader):
    """
    Reversión a la media con umbral adaptativo (Bollinger sin cuadrados).
    Igual que DesviacionMedia, pero el umbral no es fijo: es k veces la
    desviación absoluta media (MAD) de los últimos N precios. En un mercado
    tranquilo la banda se angosta; en uno volátil se ensancha y exige una
    caída más grande para comprar. Usa la MAD en vez de la desviación estándar
    para no necesitar cuadrados ni raíces.
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int,
                 N: int = 32, k: float = 2.0, salida: float = 0.0) -> None:  # crea el trader con su ventana de precios
        super().__init__(_name, _initial_capital, _market_comission)
        self.k = k                           # ancho de la banda, en unidades de MAD
        self.salida = salida                 # vende cuando la desviación llega a este valor (0 = vuelve a la media)
        self.precios = deque(maxlen=N)       # últimos N precios

    def make_decision(self, price: int) -> tuple[int, int]:  # compra bajo la banda inferior, vende al volver a la media
        self.precios.append(price)
        if len(self.precios) < self.precios.maxlen:
            return MANTENER, 0                                              # todavía no hay N precios

        media = sum(self.precios) / len(self.precios)                       # nivel "justo"
        mad = sum(abs(p - media) for p in self.precios) / len(self.precios) # dispersión típica alrededor de la media
        desviacion = price - media                                          # cuánto se alejó el precio

        if mad > 0 and desviacion <= -self.k * mad:
            accion = COMPRAR                                                # acción que quiere hacer este tick
        elif desviacion >= self.salida:
            accion = VENDER
        else:
            accion = MANTENER
        return a_orden(accion, self.stocks)
