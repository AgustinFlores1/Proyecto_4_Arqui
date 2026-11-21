from collections import deque

from trader import Trader, MANTENER, COMPRAR, VENDER
from algorithms.herramientas import muestra_completa, a_orden


class LMS(Trader):
    """
    Aprende del mercado: predictor lineal adaptativo (LMS).
    Predice el retorno de los próximos h ticks como una suma ponderada de las
    direcciones de los últimos k movimientos (+1 sube, 0 igual, -1 baja), más un
    término constante (sesgo). Cada vez que conoce el resultado real, corrige los
    pesos en la dirección que habría reducido el error.

    Los pesos son el diagnóstico del mercado: si el peso del último movimiento
    termina positivo, aprendió momentum; si termina negativo, aprendió reversión.
    Es el mismo algoritmo que usan los canceladores de eco de los teléfonos.
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int,
                 k: int = 8, h: int = 8, mu: float = 0.002,
                 entrada: float = 0.2, salida: float = 0.0) -> None:  # crea el trader con sus pesos en cero
        super().__init__(_name, _initial_capital, _market_comission)
        self.mu = mu                             # tasa de aprendizaje: cuánto se corrigen los pesos por cada error
        self.entrada = entrada                   # compra si la predicción supera esto (puntos por acción)
        self.salida = salida                     # vende si la predicción baja de esto
        self.pesos = [0.0] * (k + 1)             # un peso por movimiento pasado, más el sesgo al final
        self.direcciones = deque(maxlen=k)       # últimas k direcciones: +1, 0 o -1 (la más reciente al final)
        self.precio_anterior = None              # precio del tick anterior
        # Historia para conectar cada entrada con su resultado h ticks después
        self.precios = deque(maxlen=h + 1)       # últimos h+1 precios
        self.entradas = deque(maxlen=h + 2)      # últimas h+2 entradas del predictor (las "casillas" de B)

    def predecir(self, x: list[float]) -> float:  # retorno esperado = suma de pesos × entradas
        return sum(w * xi for w, xi in zip(self.pesos, x))

    def make_decision(self, price: int) -> tuple[int, int]:  # actualiza las entradas, corrige los pesos y decide con la predicción
        # 1. Dirección de este tick y vector de entrada
        if self.precio_anterior is not None:
            delta = price - self.precio_anterior                         # cambio de precio de este tick
            self.direcciones.append((delta > 0) - (delta < 0))           # +1, 0 o -1
        self.precio_anterior = price
        if len(self.direcciones) == self.direcciones.maxlen:
            x = list(self.direcciones) + [1.0]                           # entradas: k direcciones + 1 para el sesgo
        else:
            x = None                                                     # todavía no hay k movimientos

        # 2. Aprendizaje: corrige los pesos con la entrada de hace h+1 ticks y su retorno real
        self.precios.append(price)
        self.entradas.append(x)
        muestra = muestra_completa(self.entradas, self.precios)          # (entrada vieja, retorno real) o None
        if muestra is not None:
            x_vieja, r = muestra
            error = r - self.predecir(x_vieja)                           # cuánto se equivocó la predicción
            self.pesos = [w + self.mu * error * xi for w, xi in zip(self.pesos, x_vieja)]

        # 3. Decisión con la predicción actual
        if x is None:
            return MANTENER, 0
        prediccion = self.predecir(x)                                    # retorno esperado de comprar ahora
        if prediccion > self.entrada:
            accion = COMPRAR                                             # acción que quiere hacer este tick
        elif prediccion < self.salida:
            accion = VENDER
        else:
            accion = MANTENER
        return a_orden(accion, self.stocks)
