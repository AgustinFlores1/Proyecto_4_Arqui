"""
Funciones auxiliares compartidas por varios algoritmos.

Varios algoritmos usan las mismas piezas: calcular el RSI, mover un umbral
adaptativo o llevar la tabla de aprendizaje de B. En vez de repetir ese código
en cada clase, está aquí una sola vez.

Cada función hace una sola cosa y no guarda nada entre llamadas: recibe el
estado que necesita (ventanas, tablas, umbrales) y lo devuelve o lo modifica.
El estado de cada algoritmo vive en su propio trader.

Funciones
---------
nivel_rsi          RSI de una ventana de cambios de precio, como nivel entero
                   de 0 a 16 (None si el precio no se movió).
mover_umbral       A2: mueve un umbral un pequeño paso para que converja a un
                   percentil de los niveles del RSI.
muestra_completa   B: devuelve la muestra (casilla, retorno) cuyo resultado se
                   acaba de conocer, h ticks después de observarla.
aprender           B: agrega una muestra a la tabla y olvida la más antigua si
                   la memoria está llena.
decidir_con_tabla  B: decide comprar o vender según el retorno promedio de la
                   casilla actual (None si todavía no hay datos suficientes).
a_orden            convierte "quiero comprar o vender" en una orden concreta:
                   compra 63 solo si no tiene acciones, vende todas solo si
                   tiene (todo o nada).
"""

from collections import deque

from trader import MANTENER, COMPRAR, VENDER


def nivel_rsi(deltas: deque) -> int | None:  # RSI de la ventana, cuantizado en niveles de 0 a 16 (None si no hubo movimiento)
    """
    nivel = floor(16·U / (U+D)). Cada nivel equivale a ~6,25 puntos de RSI.
    Devuelve None si la ventana no tuvo movimiento (U + D = 0).
    """
    U = sum(d for d in deltas if d > 0)       # suma de las subidas de la ventana
    D = sum(-d for d in deltas if d < 0)      # suma de las bajadas de la ventana, en positivo
    if U + D == 0:
        return None
    return (16 * U) // (U + D)


def mover_umbral(theta: int, acc: int, nivel: int | None,
                 paso_arriba: int, paso_abajo: int, K: int) -> tuple[int, int]:  # A2: un paso del cuantil estocástico; devuelve (theta, acc) nuevos
    """
    theta converge al percentil  paso_arriba / (paso_arriba + paso_abajo)  de los niveles.

    theta        umbral actual, entre 0 y 16
    acc          acumulador de empujones; cuando llega a ±K, theta se mueve un paso
    nivel        nivel del RSI en este tick (None se ignora)
    paso_arriba  cuánto suma al acumulador si el nivel quedó sobre theta
    paso_abajo   cuánto resta si el nivel quedó bajo o igual a theta
    K            cuánto hay que acumular para mover theta (más grande = más lento)
    """
    if nivel is None:
        return theta, acc
    if nivel > theta:
        acc += paso_arriba
    else:
        acc -= paso_abajo
    if acc >= K:                       # suficientes empujones hacia arriba
        acc -= K                       # se conserva el exceso para el próximo paso
        theta = min(16, theta + 1)
    elif acc <= -K:                    # suficientes empujones hacia abajo
        acc += K
        theta = max(0, theta - 1)
    return theta, acc


def muestra_completa(casillas: deque, precios: deque) -> tuple[int, int] | None:  # B: muestra (casilla, retorno) que se completa en este tick, o None
    """
    casillas tiene largo máximo h+2 y precios h+1, con el tick actual al final.
    Cuando están llenos:
      casillas[0] = casilla de hace h+1 ticks (t = n-h-1), la que se evalúa
      precios[0]  = p[n-h] = p[t+1], precio al que se habría ejecutado la compra
      precios[-1] = p[n]   = p[t+1+h], precio h ticks después
    """
    if len(casillas) < casillas.maxlen:
        return None                      # todavía no hay suficiente historia
    casilla = casillas[0]                # casilla observada hace h+1 ticks
    if casilla is None:
        return None                      # esa casilla no tenía información
    return casilla, precios[-1] - precios[0]   # retorno por acción de haber entrado en t


def aprender(S: list, C: list, ventana: deque, casilla: int, r: int) -> None:  # B: agrega una muestra a la tabla y olvida la más antigua si está llena
    """
    S        suma de retornos por casilla
    C        cantidad de muestras por casilla
    ventana  últimas M muestras (casilla, retorno), en orden de llegada
    casilla  casilla de la muestra nueva
    r        retorno de la muestra nueva
    """
    if len(ventana) == ventana.maxlen:            # ventana llena: hay que olvidar la más antigua
        c_vieja, r_vieja = ventana[0]             # casilla y retorno de la muestra que sale
        S[c_vieja] -= r_vieja
        C[c_vieja] -= 1
    ventana.append((casilla, r))                  # deque con maxlen descarta sola la más antigua
    S[casilla] += r
    C[casilla] += 1


def decidir_con_tabla(S: list, C: list, casilla: int, dentro: bool,
                      C_min: int, entrada: float, salida: float) -> int | None:  # B: decide con el promedio de la casilla; None si no es confiable
    """
    S, C      tabla de B
    casilla   casilla actual
    dentro    True si el trader tiene acciones
    C_min     muestras mínimas para confiar en la casilla
    entrada   compra si el promedio supera este valor (puntos de precio por acción)
    salida    vende si el promedio baja de este valor
    El promedio S/C se compara sin dividir: S/C > x  <=>  S > x·C  (con C > 0).
    """
    if C[casilla] < C_min:
        return None
    if not dentro and S[casilla] > entrada * C[casilla]:   # promedio > entrada
        return COMPRAR
    if dentro and S[casilla] < salida * C[casilla]:        # promedio < salida
        return VENDER
    return MANTENER


def a_orden(accion: int, stocks: int) -> tuple[int, int]:  # convierte una acción en una orden (acción, cantidad) sin repetir órdenes
    """
    accion  lo que quiere hacer el algoritmo
    stocks  acciones que tiene ahora el trader
    Compra solo si no tiene acciones y vende solo si tiene; así nunca se
    repite una orden en ticks seguidos.
    """
    if accion == COMPRAR and stocks == 0:
        return COMPRAR, 63
    if accion == VENDER and stocks > 0:
        return VENDER, min(63, stocks)
    return MANTENER, 0
