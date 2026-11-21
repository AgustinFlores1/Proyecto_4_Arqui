from collections import deque

from trader import Trader, MANTENER, COMPRAR, VENDER
from algorithms.herramientas import (nivel_rsi, mover_umbral, muestra_completa,
                                     aprender, decidir_con_tabla, a_orden)


class A2BRespaldo(Trader):
    """
    A2 + B (respaldo): igual que B, pero mientras el nivel actual no tiene
    C_min muestras, decide con umbrales A2 que se adaptan solos (lectura de
    reversión: compra bajo θ_bajo, vende sobre θ_alto).
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int,
                 N: int = 32, h: int = 8, M: int = 512, C_min: int = 20,
                 entrada: float = 0.2, salida: float = 0.0,
                 K: int = 64, theta_bajo: int = 5, theta_alto: int = 11) -> None:  # crea el trader con RSI, umbrales A2 y tabla B
        super().__init__(_name, _initial_capital, _market_comission)
        self.C_min = C_min                       # muestras mínimas para confiar en un nivel
        self.entrada = entrada                   # compra si el promedio del nivel supera esto (puntos por acción)
        self.salida = salida                     # vende si el promedio del nivel baja de esto
        # RSI
        self.deltas = deque(maxlen=N)            # últimos N cambios de precio (ventana del RSI)
        self.precio_anterior = None              # precio del tick anterior
        # A2
        self.K = K                               # velocidad de los umbrales (más grande = más lento)
        self.theta_bajo = theta_bajo             # umbral bajo; converge al percentil 15 de los niveles
        self.acc_bajo = 0                        # acumulador del umbral bajo
        self.theta_alto = theta_alto             # umbral alto; converge al percentil 85
        self.acc_alto = 0                        # acumulador del umbral alto
        # Historia y tabla de B
        self.precios = deque(maxlen=h + 1)       # últimos h+1 precios
        self.casillas = deque(maxlen=h + 2)      # últimas h+2 casillas (aquí, niveles)
        self.S = [0] * 17                        # suma de retornos por nivel
        self.C = [0] * 17                        # cantidad de muestras por nivel
        self.ventana = deque(maxlen=M)           # últimas M muestras (nivel, retorno)

    def make_decision(self, price: int) -> tuple[int, int]:  # decide con la tabla de B; si el nivel no es confiable, con los umbrales A2
        # 1. RSI
        if self.precio_anterior is not None:
            self.deltas.append(price - self.precio_anterior)
        self.precio_anterior = price
        nivel = nivel_rsi(self.deltas)           # RSI de este tick, de 0 a 16 (o None)

        # 2. A2: percentil 15 (pasos 3/17) y percentil 85 (pasos 17/3)
        self.theta_bajo, self.acc_bajo = mover_umbral(self.theta_bajo, self.acc_bajo, nivel, 3, 17, self.K)
        self.theta_alto, self.acc_alto = mover_umbral(self.theta_alto, self.acc_alto, nivel, 17, 3, self.K)

        # 3. Historia y aprendizaje de B (la casilla es el nivel)
        self.precios.append(price)
        self.casillas.append(nivel)
        muestra = muestra_completa(self.casillas, self.precios)   # (casilla, retorno) de hace h+1 ticks, o None
        if muestra is not None:
            aprender(self.S, self.C, self.ventana, *muestra)

        # 4. Decisión: B si el nivel es confiable; si no, respaldo A2
        if nivel is None:
            return MANTENER, 0
        accion = decidir_con_tabla(self.S, self.C, nivel, self.stocks > 0,
                                   self.C_min, self.entrada, self.salida)   # acción según la tabla (None si no es confiable)
        if accion is None:
            if nivel <= self.theta_bajo:
                accion = COMPRAR
            elif nivel >= self.theta_alto:
                accion = VENDER
            else:
                accion = MANTENER
        return a_orden(accion, self.stocks)
