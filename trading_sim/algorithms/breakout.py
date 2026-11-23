from collections import deque

from trader import Trader, MANTENER, COMPRAR, VENDER
from algorithms.herramientas import a_orden


class Breakout(Trader):
    """
    Breakout (canal de Donchian): comprar cuando el precio rompe su rango.

    Qué es y qué hace
    -----------------
    Estrategia de seguimiento de tendencia: supone que si el precio sale de su
    rango reciente, va a seguir en esa dirección.

    Mira el precio más alto de los últimos N_entrada ticks. Si el precio actual
    lo supera, el precio "rompió" su techo y compra. Para salir mira el precio
    más bajo de los últimos N_salida ticks; si el precio cae bajo ese piso,
    vende.

    El canal de salida suele ser más corto que el de entrada: le cuesta entrar
    (tiene que superar el máximo de un período largo) y sale rápido (le basta
    con romper el mínimo de un período corto). Es la estrategia de los "Turtle
    Traders" de los años 80.

    Variables
    ---------
    N_entrada  ticks del canal de entrada: compra si el precio supera el máximo
               de estos ticks anteriores. Más grande: entra menos veces y más
               tarde, solo con movimientos claros.
    N_salida   ticks del canal de salida: vende si el precio cae bajo el mínimo
               de estos ticks anteriores. Más chico: sale antes, pero lo sacan
               más seguido por pequeñas correcciones. Debería ser <= N_entrada.
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int,
                 N_entrada: int = 64,
                   N_salida: int = 32) -> None:  # crea el trader con su ventana de precios anteriores
    
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
