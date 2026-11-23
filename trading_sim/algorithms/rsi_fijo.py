from collections import deque

from trader import Trader, MANTENER, COMPRAR, VENDER
from algorithms.herramientas import nivel_rsi, a_orden


class RSIFijo(Trader):
    """
    RSI fijo: comprar cuando el RSI está bajo, vender cuando está alto.

    Qué es y qué hace
    -----------------
    El RSI (índice de fuerza relativa) mide si en los últimos N ticks el precio
    subió más de lo que bajó. Con U = suma de las subidas y D = suma de las
    bajadas de la ventana:

        RSI = 100 · U / (U + D)

    RSI 0 significa que solo bajó, 100 que solo subió y 50 que subió y bajó
    lo mismo. Aquí se usa como un nivel entero de 0 a 16
    (nivel = 16 · U / (U + D), sin decimales), donde cada nivel equivale a
    6,25 puntos de RSI. Así se evita trabajar con porcentajes.

    Es la versión clásica de reversión a la media: un RSI bajo indica que el
    precio cayó mucho ("sobreventa") y se espera un rebote, así que compra; un
    RSI alto indica que subió mucho ("sobrecompra"), así que vende. Los
    umbrales son constantes: no aprende nada. Sirve de referencia para los
    algoritmos que sí aprenden (A2, B).

    Si el precio no se movió en toda la ventana (U + D = 0), el RSI no está
    definido y no hace nada.

    Variables
    ---------
    N     ticks de la ventana del RSI. Más grande: RSI más suave, que llega
          menos veces a los extremos.
    bajo  umbral de compra (nivel 0-16): compra si nivel <= bajo, o sea si
          RSI < 6,25 · (bajo + 1). Con bajo = 4: RSI < 31,25 (el clásico ~30).
    alto  umbral de venta (nivel 0-16): vende si nivel >= alto, o sea si
          RSI >= 6,25 · alto. Con alto = 11: RSI >= 68,75 (el clásico ~70).
          Con alto = 14: RSI >= 87,5, que casi nunca pasa, así que casi nunca
          vende.
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int,
                 N: int = 46, 
                 bajo: int = 4, 
                 alto: int = 14) -> None:  # crea el trader con su ventana de RSI y sus umbrales
        
        super().__init__(_name, _initial_capital, _market_comission)
        self.bajo = bajo                   # compra si el nivel es ≤ este valor
        self.alto = alto                   # vende si el nivel es ≥ este valor
        self.deltas = deque(maxlen=N)      # últimos N cambios de precio (ventana del RSI)
        self.precio_anterior = None        # precio del tick anterior, para calcular el cambio

    def make_decision(self, price: int) -> tuple[int, int]:  # compra con RSI bajo, vende con RSI alto
        if self.precio_anterior is not None:
            self.deltas.append(price - self.precio_anterior)
        self.precio_anterior = price
        nivel = nivel_rsi(self.deltas)     # RSI de este tick, de 0 a 16 (o None)

        if nivel is None:
            accion = MANTENER              # acción que quiere hacer este tick
        elif nivel <= self.bajo:
            accion = COMPRAR
        elif nivel >= self.alto:
            accion = VENDER
        else:
            accion = MANTENER
        return a_orden(accion, self.stocks)
