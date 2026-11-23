from collections import deque

from trader import Trader, MANTENER, COMPRAR, VENDER
from algorithms.herramientas import muestra_completa, a_orden


class LMS(Trader):
    """
    LMS: predictor lineal que aprende a anticipar el precio.

    Qué es y qué hace
    -----------------
    Intenta predecir cuántos puntos va a ganar si compra ahora y vende h ticks
    después. Para eso mira la dirección de los últimos k movimientos del
    precio: +1 si subió, 0 si quedó igual, -1 si bajó.

    La predicción es una suma ponderada: cada dirección se multiplica por un
    peso y se suman, más un término constante llamado sesgo. Si la predicción
    supera 'entrada', compra; si baja de 'salida', vende.

    Los pesos se aprenden solos. Cada vez que pasa el tiempo suficiente para
    saber cuánto se movió realmente el precio, calcula el error de su
    predicción y corrige cada peso un poco en la dirección que lo habría
    reducido. Es el algoritmo LMS (least mean squares), el mismo que usan los
    canceladores de eco de los teléfonos.

    Los pesos finales dicen qué aprendió del mercado:
      - peso del último movimiento positivo: "si subió, sigue subiendo" (momentum).
      - negativo: "si subió, después baja" (reversión).
      - sesgo positivo: el precio viene subiendo en general (tendencia).

    Variables
    ---------
    k        cuántos movimientos pasados mira. Hay k + 1 pesos (uno por
             movimiento más el sesgo). Más grande: puede detectar patrones
             más largos, pero cada peso aprende con más ruido.
    h        horizonte: predice el retorno de los próximos h ticks. Debería
             parecerse a cuánto tiempo se mantiene una compra.
    mu       velocidad de aprendizaje: cuánto se corrige cada peso por cada
             error. Más grande: se adapta rápido pero los pesos persiguen el
             ruido. Más chico: estable pero lento. La memoria es de
             aproximadamente 1 / mu ticks.
    entrada  compra si la predicción supera este valor (puntos por acción en
             h ticks). Debería superar el costo de las comisiones (~0,19).
    salida   vende si la predicción baja de este valor.
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
