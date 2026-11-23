from collections import deque

from trader import Trader, MANTENER
from algorithms.herramientas import (nivel_rsi, mover_umbral, muestra_completa,
                                     aprender, decidir_con_tabla, a_orden)


class A2BReagrupada(Trader):
    """
    A2 + B (reagrupada): aprende cuánto gana comprando en cada zona del RSI.

    Qué es y qué hace
    -----------------
    Combina dos ideas:
      - A2: umbrales de RSI que se ajustan solos (ver A2Solo). Con ellos, el
        nivel del RSI (0 a 16) se clasifica en 3 zonas:
          0 = baja   (nivel <= theta_bajo)
          1 = media
          2 = alta   (nivel >= theta_alto)
      - B: una tabla que aprende de la experiencia. Para cada zona guarda cuánto
        subió o bajó el precio, en promedio, en los h ticks siguientes a haberla
        visto. Si en esa zona comprar históricamente ganó, compra; si perdió,
        vende.

    Usar 3 zonas en vez de 17 niveles hace que cada casilla de la tabla junte
    muchas más muestras y aprenda más rápido. Mientras la zona actual no tenga
    C_min muestras, no opera.

    La zona se anota en el tick en que se observa. Como los umbrales se mueven,
    recalcularla después podría asignarla a una zona distinta.

    Variables
    ---------
    N           ticks de la ventana del RSI.
    h           horizonte: cuántos ticks después se mide el resultado de cada
                muestra. Debería parecerse a cuánto tiempo se mantiene una compra.
    M           memoria: la tabla usa solo las últimas M muestras y olvida las
                más antiguas. Más grande: promedios más estables, adaptación lenta.
    C_min       muestras mínimas en una zona para confiar en su promedio.
    entrada     compra si el retorno promedio de la zona supera este valor
                (puntos de precio por acción). Debería ser mayor que el costo
                de las comisiones (~0,19).
    salida      vende si el retorno promedio de la zona baja de este valor.
                La diferencia entre entrada y salida evita comprar y vender seguido.
    K           lentitud de los umbrales A2 (ver A2Solo).
    theta_bajo  valor inicial del umbral que separa la zona baja.
    theta_alto  valor inicial del umbral que separa la zona alta.
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int,
                 N: int = 32, 
                 h: int = 8, 
                 M: int = 512, 
                 C_min: int = 20,
                 entrada: float = 0.2, 
                 salida: float = 0.0,
                 K: int = 64, 
                 theta_bajo: int = 5, 
                 theta_alto: int = 11) -> None:  # crea el trader con RSI, umbrales A2 y tabla de 3 zonas
        
        super().__init__(_name, _initial_capital, _market_comission)
        
        self.C_min = C_min                       # muestras mínimas para confiar en una zona
        self.entrada = entrada                   # compra si el promedio de la zona supera esto (puntos por acción)
        self.salida = salida                     # vende si el promedio de la zona baja de esto
        # RSI
        self.deltas = deque(maxlen=N)            # últimos N cambios de precio (ventana del RSI)
        self.precio_anterior = None              # precio del tick anterior
        # A2
        self.K = K                               # velocidad de los umbrales (más grande = más lento)
        self.theta_bajo = theta_bajo             # umbral bajo; converge al percentil 15 de los niveles
        self.acc_bajo = 0                        # acumulador del umbral bajo
        self.theta_alto = theta_alto             # umbral alto; converge al percentil 85
        self.acc_alto = 0                        # acumulador del umbral alto
        # Historia y tabla de B con 3 zonas
        self.precios = deque(maxlen=h + 1)       # últimos h+1 precios
        self.casillas = deque(maxlen=h + 2)      # últimas h+2 casillas (aquí, zonas)
        self.S = [0] * 3                         # suma de retornos por zona
        self.C = [0] * 3                         # cantidad de muestras por zona
        self.ventana = deque(maxlen=M)           # últimas M muestras (zona, retorno)

    def zona(self, nivel: int | None) -> int | None:  # traduce el nivel a zona (0 baja, 1 media, 2 alta) con los umbrales actuales
        if nivel is None:
            return None
        if nivel <= self.theta_bajo:
            return 0
        if nivel >= self.theta_alto:
            return 2
        return 1

    def make_decision(self, price: int) -> tuple[int, int]:  # decide con la tabla de zonas; sin datos suficientes no opera
        # 1. RSI
        if self.precio_anterior is not None:
            self.deltas.append(price - self.precio_anterior)
        self.precio_anterior = price
        nivel = nivel_rsi(self.deltas)           # RSI de este tick, de 0 a 16 (o None)

        # 2. A2 (antes de calcular la zona, para usar los umbrales de este tick)
        self.theta_bajo, self.acc_bajo = mover_umbral(self.theta_bajo, self.acc_bajo, nivel, 3, 17, self.K)
        self.theta_alto, self.acc_alto = mover_umbral(self.theta_alto, self.acc_alto, nivel, 17, 3, self.K)
        zona = self.zona(nivel)                  # zona de este tick (o None)

        # 3. Historia y aprendizaje de B (la casilla es la zona)
        self.precios.append(price)
        self.casillas.append(zona)
        muestra = muestra_completa(self.casillas, self.precios)   # (zona, retorno) de hace h+1 ticks, o None
        if muestra is not None:
            aprender(self.S, self.C, self.ventana, *muestra)

        # 4. Decisión: solo con la tabla; sin datos suficientes, no opera
        if zona is None:
            return MANTENER, 0
        accion = decidir_con_tabla(self.S, self.C, zona, self.stocks > 0,
                                   self.C_min, self.entrada, self.salida)   # acción según la tabla (None si no es confiable)
        if accion is None:
            accion = MANTENER
        return a_orden(accion, self.stocks)
