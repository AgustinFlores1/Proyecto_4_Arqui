from collections import deque

from trader import Trader, MANTENER, COMPRAR, VENDER
from algorithms.herramientas import a_orden


class DesviacionMedia(Trader):
    """
    Reversión a la media con umbral fijo.
    Supone que el precio oscila alrededor de su promedio reciente: si cae más de
    'umbral' puntos bajo la media de los últimos N, compra (está "barato"), y
    vende cuando el precio vuelve a la media (desviación ≥ salida).
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int,
                 N: int = 32, umbral: float = 3.0, salida: float = 0.0) -> None:  # crea el trader con su ventana de precios
        super().__init__(_name, _initial_capital, _market_comission)
        self.umbral = umbral                 # cuántos puntos bajo la media tiene que estar para comprar
        self.salida = salida                 # vende cuando la desviación llega a este valor (0 = vuelve a la media)
        self.precios = deque(maxlen=N)       # últimos N precios

    def make_decision(self, price: int) -> tuple[int, int]:  # compra muy bajo la media, vende al volver a ella
        self.precios.append(price)
        if len(self.precios) < self.precios.maxlen:
            return MANTENER, 0                                  # todavía no hay N precios

        media = sum(self.precios) / len(self.precios)           # nivel "justo" según los últimos N ticks
        desviacion = price - media                              # cuánto se alejó el precio de ese nivel

        if desviacion <= -self.umbral:
            accion = COMPRAR                                    # acción que quiere hacer este tick
        elif desviacion >= self.salida:
            accion = VENDER
        else:
            accion = MANTENER
        return a_orden(accion, self.stocks)
