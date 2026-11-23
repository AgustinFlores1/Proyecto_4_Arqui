from collections import deque

from trader import Trader, MANTENER
from algorithms.herramientas import nivel_rsi, muestra_completa, aprender, decidir_con_tabla, a_orden


class BCalentamiento(Trader):
    """
    B con calentamiento: aprende qué niveles del RSI anticipan subidas.

    Qué es y qué hace
    -----------------
    En vez de suponer que un RSI bajo significa "va a rebotar", lo aprende de
    los datos. Cada tick calcula el nivel del RSI (0 a 16) y lo anota. Cuando
    pasan h ticks, mira cuánto se movió el precio desde entonces y suma ese
    resultado a la casilla de ese nivel en una tabla.

    Así la tabla responde: "las veces que el RSI estuvo en el nivel 5, ¿cuánto
    habría ganado comprando?". Si el promedio de la casilla actual es bueno,
    compra; si es malo, vende.

    El calentamiento: mientras el nivel actual no tenga C_min muestras, no
    opera, porque un promedio de pocas muestras es casi puro ruido.

    Variables
    ---------
    N        ticks de la ventana del RSI.
    h        horizonte: cuántos ticks después se mide el resultado de cada muestra.
             Debería parecerse a cuánto tiempo se mantiene una compra.
    M        memoria: la tabla usa solo las últimas M muestras y olvida las
             antiguas. Más grande: más estable, pero se adapta lento si el
             mercado cambia.
    C_min    muestras mínimas en un nivel para confiar en su promedio.
             Más grande: decisiones más confiables, pero más tiempo sin operar.
    entrada  compra si el retorno promedio del nivel supera este valor
             (puntos de precio por acción). Debería superar el costo de las
             comisiones (~0,19).
    salida   vende si el retorno promedio del nivel baja de este valor.
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int,
                 N: int = 32, 
                 h: int = 8, 
                 M: int = 512, 
                 C_min: int = 20,
                 entrada: float = 0.2, 
                 salida: float = 0.0) -> None:  # crea el trader con su RSI, su historia y su tabla vacía
        
        super().__init__(_name, _initial_capital, _market_comission)
        
        self.C_min = C_min                       # muestras mínimas para confiar en un nivel
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

    def make_decision(self, price: int) -> tuple[int, int]:  # actualiza el RSI, aprende la muestra que se completó y decide con la tabla
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

        # 3. Decisión
        if nivel is None:
            return MANTENER, 0
        accion = decidir_con_tabla(self.S, self.C, nivel, self.stocks > 0,
                                   self.C_min, self.entrada, self.salida)   # acción según la tabla (None si no es confiable)
        if accion is None:          # nivel sin datos suficientes: calentamiento
            accion = MANTENER
        return a_orden(accion, self.stocks)
