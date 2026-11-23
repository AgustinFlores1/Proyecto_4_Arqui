from collections import deque

from trader import Trader, MANTENER, COMPRAR, VENDER
from algorithms.herramientas import a_orden


class DesviacionMedia(Trader):
    """
    Desviación de la media: comprar cuando el precio está "barato".

    Qué es y qué hace
    -----------------
    Estrategia de reversión a la media: supone que el precio oscila alrededor
    de su promedio reciente y que, si se aleja mucho, tiende a volver.

    Calcula la media de los últimos N precios y mide cuánto se alejó el precio
    actual de ella (desviación = precio - media). Si el precio está 'umbral'
    puntos o más por debajo de la media, lo considera barato y compra. Vende
    cuando el precio vuelve a la media, o la supera por 'salida' puntos.

    El umbral es un número fijo de puntos. BandasDesviacion es la versión que
    lo ajusta según qué tanto se mueve el precio.

    Su punto débil: si el precio cae y no vuelve, sigue comprado esperando un
    rebote que no llega, porque no tiene una regla para vender con pérdida.

    Variables
    ---------
    N       ticks de la ventana de la media. Más chico: la media sigue al
            precio de cerca y las desviaciones son pequeñas.
    umbral  puntos bajo la media para comprar. Más grande: compra menos
            veces, solo en caídas fuertes.
    salida  vende cuando el precio supera la media por esta cantidad de
            puntos. 0 = vende apenas vuelve a la media.
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
