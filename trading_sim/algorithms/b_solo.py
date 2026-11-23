from collections import deque

from trader import Trader, MANTENER
from algorithms.herramientas import nivel_rsi, muestra_completa, aprender, decidir_con_tabla, a_orden


class BSolo(Trader):
    """
    B solo: la tabla de BCalentamiento, pero sin calentamiento.

    Qué es y qué hace
    -----------------
    Aprende igual que BCalentamiento: para cada nivel del RSI (0 a 16) guarda
    cuánto se movió el precio, en promedio, en los h ticks siguientes, y compra
    o vende según ese promedio.

    La diferencia es que opera apenas el nivel actual tiene una sola muestra,
    aunque ese promedio sea muy poco confiable. Existe para comparar: la
    diferencia entre BSolo y BCalentamiento muestra cuánto aporta esperar a
    tener suficientes datos.

    Variables
    ---------
    N        ticks de la ventana del RSI.
    h        horizonte: cuántos ticks después se mide el resultado de cada muestra.
    M        memoria: la tabla usa solo las últimas M muestras.
    entrada  compra si el retorno promedio del nivel supera este valor
             (puntos por acción).
    salida   vende si el retorno promedio del nivel baja de este valor.
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int,
                 N: int = 32, 
                 h: int = 8, 
                 M: int = 512,
                 entrada: float = 0.2, 
                 salida: float = 0.0) -> None:  # crea el trader con su RSI, su historia y su tabla vacía
        
        super().__init__(_name, _initial_capital, _market_comission)
        
        self.entrada = entrada                   # compra si el promedio del nivel supera esto (puntos por acción)
        self.salida = salida                     # vende si el promedio del nivel baja de esto
        # RSI
        self.deltas = deque(maxlen=N)            # últimos N cambios de precio (ventana del RSI)
        self.precio_anterior = None              # precio del tick anterior
        # Historia para conectar cada casilla con su resultado h ticks después
        self.precios = deque(maxlen=h + 1)       # últimos h+1 precios
        self.casillas = deque(maxlen=h + 2)      # últimas h+2 casillas (aquí, niveles)
        # Tabla de B
        self.S = [0] * 17                        # suma de retornos por nivel
        self.C = [0] * 17                        # cantidad de muestras por nivel
        self.ventana = deque(maxlen=M)           # últimas M muestras (nivel, retorno), para olvidar las viejas

    def make_decision(self, price: int) -> tuple[int, int]:  # actualiza el RSI, aprende y decide con la tabla desde la primera muestra
        # 1. RSI
        if self.precio_anterior is not None:
            self.deltas.append(price - self.precio_anterior)
        self.precio_anterior = price
        nivel = nivel_rsi(self.deltas)           # RSI de este tick, de 0 a 16 (o None)

        # 2. Historia y aprendizaje (la casilla es el nivel)
        self.precios.append(price)
        self.casillas.append(nivel)
        muestra = muestra_completa(self.casillas, self.precios)   # (casilla, retorno) de hace h+1 ticks, o None
        if muestra is not None:
            aprender(self.S, self.C, self.ventana, *muestra)

        # 3. Decisión: basta con 1 muestra (C_min = 1); sin muestras, mantiene
        if nivel is None:
            return MANTENER, 0
        accion = decidir_con_tabla(self.S, self.C, nivel, self.stocks > 0,
                                   1, self.entrada, self.salida)    # acción según la tabla (None si el nivel no tiene muestras)
        if accion is None:
            accion = MANTENER
        return a_orden(accion, self.stocks)
