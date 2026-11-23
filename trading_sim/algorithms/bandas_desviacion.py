from collections import deque

from trader import Trader, MANTENER, COMPRAR, VENDER
from algorithms.herramientas import a_orden


class BandasDesviacion(Trader):
    """
    Bandas de desviación: comprar cuando el precio cae "más de lo normal".

    Qué es y qué hace
    -----------------
    Estrategia de reversión a la media: supone que el precio tiende a volver a
    su promedio reciente. Calcula la media de los últimos N precios y compra
    cuando el precio actual está muy por debajo. Vende cuando vuelve a la media
    (o un poco más arriba, según salida).

    "Muy por debajo" no es un número fijo de puntos. Se mide en relación a qué
    tanto se mueve el precio normalmente: la desviación absoluta media (MAD),
    que es el promedio de qué tan lejos de la media estuvieron los últimos N
    precios. En un mercado tranquilo la MAD es chica y basta una caída pequeña
    para comprar; en uno agitado la MAD es grande y exige una caída mayor.

    Es parecido a las bandas de Bollinger, pero usa la MAD en vez de la
    desviación estándar para no necesitar cuadrados ni raíces (más fácil en
    hardware).

    Variables
    ---------
    N       ticks de la ventana con que se calculan la media y la MAD.
    k       ancho de la banda: compra si el precio está k·MAD o más bajo la
            media. Más grande: compra menos veces, solo en caídas fuertes.
    salida  vende cuando el precio supera la media por esta cantidad de puntos.
            0 = vende apenas vuelve a la media. Positivo: espera más ganancia.
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int,
                 N: int = 32, 
                 k: float = 2.0, 
                 salida: float = 0.0) -> None:  # crea el trader con su ventana de precios
        
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
