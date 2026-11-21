from collections import deque

from trader import Trader, MANTENER, COMPRAR, VENDER
from algorithms.herramientas import a_orden


class CruceMedias(Trader):
    """
    Seguimiento de tendencia: cruce de medias móviles (SMA).
    Compara el promedio de los últimos N_corta precios (el precio "reciente")
    con el de los últimos N_larga (el "nivel de fondo"). Si la media corta está
    sobre la larga, el precio viene subiendo: compra. Si está bajo, vende.
    El margen crea una zona muerta (histéresis) para no entrar y salir seguido.
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int,
                 N_corta: int = 8, N_larga: int = 32, margen: float = 0.5) -> None:  # crea el trader con su ventana de precios
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
