from collections import deque

from trader import Trader, MANTENER, COMPRAR, VENDER
from algorithms.herramientas import a_orden


class CruceMedias(Trader):
    """
    Cruce de medias móviles: seguir la tendencia comparando dos promedios.

    Qué es y qué hace
    -----------------
    Estrategia de seguimiento de tendencia: supone que si el precio viene
    subiendo, va a seguir subiendo un tiempo.

    Calcula dos promedios del precio:
      - media corta: promedio de los últimos N_corta precios. Reacciona rápido
        y representa el precio "reciente".
      - media larga: promedio de los últimos N_larga precios. Reacciona lento
        y representa el "nivel de fondo".

    Si la media corta está por encima de la larga, el precio reciente es mayor
    que el de fondo, o sea que viene subiendo: compra. Si está por debajo,
    viene bajando: vende, aunque sea con pérdida. Eso último es lo que lo
    protege en las caídas largas.

    El margen crea una zona muerta entre las dos medias. Sin él, cuando las
    medias están casi iguales se cruzan muchas veces por puro ruido y el
    algoritmo compra y vende seguido, pagando comisiones en cada orden.

    Variables
    ---------
    N_corta  ticks de la media corta. Más chico: detecta los cambios antes,
             pero con más ruido.
    N_larga  ticks de la media larga. Define el plazo de la tendencia que
             sigue. Debería ser varias veces N_corta.
    margen   separación mínima entre las medias para actuar, en puntos de
             precio: compra si corta > larga + margen, vende si
             corta < larga - margen. Más grande: menos órdenes, pero entra y
             sale más tarde.
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int,
                 N_corta: int = 8, 
                 N_larga: int = 32, 
                 margen: float = 2) -> None:  # crea el trader con su ventana de precios
        
        super().__init__(_name, _initial_capital, _market_comission)
        self.N_corta = N_corta                    # largo de la media corta (ticks)
        self.margen = margen                      # separación mínima entre medias para actuar (puntos de precio)
        self.precios = deque(maxlen=N_larga)      # últimos N_larga precios (la media corta usa los últimos N_corta)

    def make_decision(self, price: int) -> tuple[int, int]:  # compra si la media corta supera a la larga, vende si queda bajo
        self.precios.append(price)
        if len(self.precios) < self.precios.maxlen:
            return MANTENER, 0                    # todavía no hay N_larga precios

        ultimos = list(self.precios)[-self.N_corta:]               # los N_corta precios más recientes
        media_corta = sum(ultimos) / self.N_corta                  # precio reciente suavizado
        media_larga = sum(self.precios) / len(self.precios)        # nivel de fondo

        if media_corta > media_larga + self.margen:
            accion = COMPRAR                      # acción que quiere hacer este tick
        elif media_corta < media_larga - self.margen:
            accion = VENDER
        else:
            accion = MANTENER
        return a_orden(accion, self.stocks)
