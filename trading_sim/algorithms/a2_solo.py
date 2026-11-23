from collections import deque

from trader import Trader, MANTENER, COMPRAR, VENDER
from algorithms.herramientas import nivel_rsi, mover_umbral, a_orden


class A2Solo(Trader):
    """
    A2 solo: RSI con umbrales que se ajustan solos.

    Qué es y qué hace
    -----------------
    El RSI (índice de fuerza relativa) mide si en los últimos N ticks el precio
    subió más de lo que bajó. Aquí se expresa como un nivel entero de 0 a 16:
    0 significa que solo bajó, 16 que solo subió y 8 que subió y bajó lo mismo.

    La idea es de reversión a la media: si el RSI está muy bajo, el precio cayó
    "demasiado" y se espera un rebote, así que compra. Si está muy alto, vende.

    A diferencia de RSIFijo, los umbrales que definen "muy bajo" y "muy alto" no
    son constantes. Cada tick se mueven un poco según el nivel actual, hasta
    quedar en el percentil 15 y 85 de los niveles recientes. Así se adaptan al
    mercado: "muy bajo" significa "más bajo que el 85 % de lo que se vio
    últimamente". No aprende de las ganancias, solo de qué tan raro es el RSI.

    Variables
    ---------
    N           ticks de la ventana del RSI. Más grande: RSI más suave y lento.
    K           lentitud de los umbrales: cuántos "empujones" se acumulan antes de
                mover un umbral un nivel. Más grande: umbrales más estables pero
                que tardan más en adaptarse.
    theta_bajo  valor inicial del umbral de compra (nivel 0-16). Después se
                mueve solo; compra si nivel <= theta_bajo.
    theta_alto  valor inicial del umbral de venta (nivel 0-16). Después se
                mueve solo; vende si nivel >= theta_alto.
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
