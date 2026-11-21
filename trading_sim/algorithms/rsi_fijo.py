from collections import deque

from trader import Trader, MANTENER, COMPRAR, VENDER
from algorithms.herramientas import nivel_rsi, a_orden


class RSIFijo(Trader):
    """
    RSI clásico con umbrales fijos (lectura de reversión): compra cuando el RSI
    está bajo y vende cuando está alto. Es la referencia sin aprendizaje.

    Umbrales en niveles (0-16, cada nivel ≈ 6,25 puntos de RSI):
      bajo = 4  ->  RSI < 31,25   ("sobreventa", ~30)
      alto = 11 ->  RSI ≥ 68,75   ("sobrecompra", ~70)
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int,
                 N: int = 32, 
                 bajo: int = 4, 
                 alto: int = 11) -> None:  # crea el trader con su ventana de RSI y sus umbrales
        
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
