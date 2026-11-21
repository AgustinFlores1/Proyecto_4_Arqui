from collections import deque

from trader import Trader, MANTENER, COMPRAR, VENDER
from algorithms.herramientas import nivel_rsi, mover_umbral, a_orden


class A2Solo(Trader):
    """
    A2 solo: RSI con umbrales que se adaptan solos (lectura de reversión).
    Es igual al RSI fijo, pero θ_bajo y θ_alto no son constantes: siguen al
    percentil 15 y 85 de los niveles recientes. No aprende de la ganancia,
    solo de qué tan "raro" es el RSI actual.
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int,
                 N: int = 32, 
                 K: int = 64, 
                 theta_bajo: int = 5, 
                 theta_alto: int = 11) -> None:  # crea el trader con su RSI y sus dos umbrales A2
        
        super().__init__(_name, _initial_capital, _market_comission)
        # RSI
        self.deltas = deque(maxlen=N)            # últimos N cambios de precio (ventana del RSI)
        self.precio_anterior = None              # precio del tick anterior
        # A2
        self.K = K                               # velocidad de los umbrales (más grande = más lento)
        self.theta_bajo = theta_bajo             # umbral bajo; converge al percentil 15 de los niveles
        self.acc_bajo = 0                        # acumulador del umbral bajo
        self.theta_alto = theta_alto             # umbral alto; converge al percentil 85
        self.acc_alto = 0                        # acumulador del umbral alto

    def make_decision(self, price: int) -> tuple[int, int]:  # actualiza el RSI y los umbrales; compra bajo θ_bajo, vende sobre θ_alto
        # 1. RSI
        if self.precio_anterior is not None:
            self.deltas.append(price - self.precio_anterior)
        self.precio_anterior = price
        nivel = nivel_rsi(self.deltas)           # RSI de este tick, de 0 a 16 (o None)

        # 2. A2: percentil 15 (pasos 3/17) y percentil 85 (pasos 17/3)
        self.theta_bajo, self.acc_bajo = mover_umbral(self.theta_bajo, self.acc_bajo, nivel, 3, 17, self.K)
        self.theta_alto, self.acc_alto = mover_umbral(self.theta_alto, self.acc_alto, nivel, 17, 3, self.K)

        # 3. Decisión con los umbrales de este tick
        if nivel is None:
            accion = MANTENER                    # acción que quiere hacer este tick
        elif nivel <= self.theta_bajo:
            accion = COMPRAR
        elif nivel >= self.theta_alto:
            accion = VENDER
        else:
            accion = MANTENER
        return a_orden(accion, self.stocks)
