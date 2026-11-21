from collections import deque

from trader import Trader, MANTENER, COMPRAR, VENDER
from algorithms.herramientas import a_orden


class Breakout(Trader):
    """
    Seguimiento de tendencia: breakout (canal de Donchian).
    Compra cuando el precio supera el máximo de los N_entrada ticks anteriores
    (rompió su rango hacia arriba) y vende cuando cae bajo el mínimo de los
    N_salida ticks anteriores. Usar un canal de salida más corto hace que salga
    antes de lo que entra, como en la estrategia original de los "Turtle Traders".
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int,
                 N_entrada: int = 64, N_salida: int = 32) -> None:  # crea el trader con su ventana de precios anteriores
        super().__init__(_name, _initial_capital, _market_comission)
        self.N_salida = N_salida                       # ticks del canal de salida
        self.anteriores = deque(maxlen=N_entrada)      # últimos N_entrada precios, SIN contar el actual

    def make_decision(self, price: int) -> tuple[int, int]:  # compra al romper el máximo, vende al romper el mínimo
        if len(self.anteriores) < self.anteriores.maxlen:
            self.anteriores.append(price)
            return MANTENER, 0                         # todavía no hay un rango completo

        maximo = max(self.anteriores)                                  # techo del canal de entrada
        minimo = min(list(self.anteriores)[-self.N_salida:])           # piso del canal de salida
        self.anteriores.append(price)                                  # el precio actual entra después de comparar

        if price > maximo:
            accion = COMPRAR                           # acción que quiere hacer este tick
        elif price < minimo:
            accion = VENDER
        else:
            accion = MANTENER
        return a_orden(accion, self.stocks)
