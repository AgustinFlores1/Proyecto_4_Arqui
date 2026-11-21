from collections import deque

from trader import Trader, MANTENER
from algorithms.herramientas import muestra_completa, aprender, decidir_con_tabla, a_orden


class Patrones(Trader):
    """
    Aprende del mercado: tabla de patrones (tipo cadena de Markov).
    Codifica los últimos k movimientos del precio (baja / igual / sube) como un
    patrón, y para cada patrón aprende cuánto se movió el precio después, con la
    misma tabla de B. Es la idea de un predictor de saltos de un procesador,
    aplicada a precios: "después de [sube, sube, baja], ¿qué suele pasar?".

    Hay 3^k patrones posibles (con k = 3, 27 casillas).
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int,
                 k: int = 3, h: int = 8, M: int = 512, C_min: int = 20,
                 entrada: float = 0.2, salida: float = 0.0) -> None:  # crea el trader con su historia de movimientos y su tabla vacía
        super().__init__(_name, _initial_capital, _market_comission)
        self.C_min = C_min                       # muestras mínimas para confiar en un patrón
        self.entrada = entrada                   # compra si el promedio del patrón supera esto (puntos por acción)
        self.salida = salida                     # vende si el promedio del patrón baja de esto
        self.movimientos = deque(maxlen=k)       # últimos k movimientos: 0 baja, 1 igual, 2 sube
        self.precio_anterior = None              # precio del tick anterior
        # Historia y tabla (igual que B, pero la casilla es el patrón)
        self.precios = deque(maxlen=h + 1)       # últimos h+1 precios
        self.casillas = deque(maxlen=h + 2)      # últimas h+2 casillas (aquí, patrones)
        self.S = [0] * (3 ** k)                  # suma de retornos por patrón
        self.C = [0] * (3 ** k)                  # cantidad de muestras por patrón
        self.ventana = deque(maxlen=M)           # últimas M muestras (patrón, retorno)

    def patron(self) -> int | None:  # convierte los últimos k movimientos en un número de 0 a 3^k - 1 (None si aún no hay k)
        if len(self.movimientos) < self.movimientos.maxlen:
            return None
        indice = 0                               # número en base 3: cada movimiento es un dígito
        for mov in self.movimientos:
            indice = indice * 3 + mov
        return indice

    def make_decision(self, price: int) -> tuple[int, int]:  # actualiza el patrón, aprende la muestra que se completó y decide con la tabla
        # 1. Movimiento de este tick
        if self.precio_anterior is not None:
            delta = price - self.precio_anterior                 # cambio de precio de este tick
            self.movimientos.append(0 if delta < 0 else (1 if delta == 0 else 2))
        self.precio_anterior = price
        patron = self.patron()                                   # patrón actual (o None)

        # 2. Historia y aprendizaje (la casilla es el patrón)
        self.precios.append(price)
        self.casillas.append(patron)
        muestra = muestra_completa(self.casillas, self.precios)  # (patrón, retorno) de hace h+1 ticks, o None
        if muestra is not None:
            aprender(self.S, self.C, self.ventana, *muestra)

        # 3. Decisión
        if patron is None:
            return MANTENER, 0
        accion = decidir_con_tabla(self.S, self.C, patron, self.stocks > 0,
                                   self.C_min, self.entrada, self.salida)   # acción según la tabla (None si no es confiable)
        if accion is None:
            accion = MANTENER
        return a_orden(accion, self.stocks)
