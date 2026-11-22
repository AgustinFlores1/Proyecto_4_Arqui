"""
Funciones para probar parámetros sin sobreajustar.

Uso típico (desde otro archivo o una consola de Python en trading_sim/):

    from barrido import cargar_serie, dividir, barrido, validar, evaluar_en_series
    from algorithms.b_calentamiento import BCalentamiento

    precios = cargar_serie("../tb/practica.csv")
    calibracion, validacion = dividir(precios)

    resultados = barrido(BCalentamiento, {"entrada": [0.2, 0.5, 1, 2], "h": [4, 8, 16, 32]}, calibracion)
    validar(BCalentamiento, resultados[:5], validacion)

    evaluar_en_series(BCalentamiento, {"entrada": 1, "h": 16}, ["../tb/series/META_1d_2022.csv", ...])
"""

from itertools import product
from pathlib import Path

from market import Market

CAPITAL = 10000     # caja inicial de cada trader (igual que en main.py)
COMISION = 5        # comisión por orden ejecutada


def cargar_serie(ruta: str | Path) -> list[int]:  # lee un CSV "tick,price" y devuelve la lista de precios
    mercado = Market(COMISION, CAPITAL)
    mercado.fill_stock_prices(ruta)
    return mercado.stock_prices


def dividir(precios: list[int], fraccion: float = 0.5) -> tuple[list[int], list[int]]:  # parte la serie en calibración y validación
    corte = int(len(precios) * fraccion)          # tick donde termina la calibración
    return precios[:corte], precios[corte:]


def correr(clase, precios: list[int], **params) -> dict:  # corre UN trader nuevo sobre un tramo y devuelve sus resultados
    """
    clase    clase del algoritmo (por ejemplo BCalentamiento)
    precios  tramo de la serie
    params   parámetros del algoritmo (por ejemplo h=16, entrada=1.0)
    Siempre crea un mercado y un trader nuevos: nada de lo aprendido pasa de una corrida a otra.
    """
    mercado = Market(COMISION, CAPITAL)
    mercado.stock_prices = list(precios)
    trader = clase("barrido", CAPITAL, COMISION, **params)
    mercado.insert_trader(trader)
    mercado.run_sim()
    referencia = mercado.buy_and_hold_reference()              # comprar y mantener en ESTE tramo
    return {
        "params": params,                                      # parámetros usados
        "patrimonio": trader.wealth,                           # patrimonio final
        "vs_bh": trader.wealth - referencia,                   # diferencia con comprar y mantener (lo que pesa en la nota)
        "vs_no_operar": trader.wealth - CAPITAL,               # diferencia con no operar
        "ordenes": trader.orders,                              # órdenes ejecutadas
        "perdida_max": trader.max_wealth_drop,                 # mayor caída desde un peak
    }


def barrido(clase, grilla: dict[str, list], precios: list[int], mostrar: int = 10) -> list[dict]:  # prueba todas las combinaciones de la grilla; devuelve de mejor a peor
    """
    grilla   nombre del parámetro -> lista de valores a probar, por ejemplo {"h": [4, 8, 16]}
    precios  tramo donde se prueba (normalmente la calibración)
    mostrar  cuántos de los mejores imprimir (0 = no imprimir)
    Ordena por la diferencia con comprar y mantener.
    """
    nombres = list(grilla)                                     # nombres de los parámetros, en orden
    resultados = [correr(clase, precios, **dict(zip(nombres, valores)))
                  for valores in product(*grilla.values())]
    resultados.sort(key=lambda r: r["vs_bh"], reverse=True)

    if mostrar:
        print(f"\n{clase.__name__}: {len(resultados)} combinaciones en {len(precios)} ticks")
        for r in resultados[:mostrar]:
            print(f"  vs B&H {r['vs_bh']:>+7} | patrimonio {r['patrimonio']:>6} | "
                  f"órdenes {r['ordenes']:>5} | pérdida máx {r['perdida_max']:>5} | {r['params']}")
    return resultados


def validar(clase, candidatos: list[dict], precios: list[int]) -> list[dict]:  # corre los candidatos del barrido en otro tramo (normalmente la validación)
    """
    candidatos  resultados de barrido() que se quieren verificar (por ejemplo los 5 mejores)
    precios     tramo de validación
    Imprime, para cada candidato, cómo le fue en calibración y en validación.
    """
    salida = []                                                # resultados en validación
    print(f"\n{clase.__name__}: validación en {len(precios)} ticks")
    for cand in candidatos:
        r = correr(clase, precios, **cand["params"])
        salida.append(r)
        print(f"  calibración {cand['vs_bh']:>+7} ({cand['ordenes']:>4} órd.) | "
              f"validación {r['vs_bh']:>+7} ({r['ordenes']:>4} órd.) | {cand['params']}")
    return salida


def evaluar_en_series(clase, params: dict, rutas: list[str | Path]) -> list[dict]:  # corre una configuración en varias series y resume
    """
    params  una sola configuración de parámetros
    rutas   CSV "tick,price" (por ejemplo los que genera generar_series.py)
    Imprime el resultado en cada serie y cuántas veces superó a comprar y mantener.
    """
    salida = []                                                # resultados por serie
    print(f"\n{clase.__name__} {params}")
    for ruta in rutas:
        r = correr(clase, cargar_serie(ruta), **params)
        r["serie"] = Path(ruta).name
        salida.append(r)
        print(f"  {r['serie']:32} vs B&H {r['vs_bh']:>+7} | vs no operar {r['vs_no_operar']:>+7} | "
              f"órdenes {r['ordenes']:>5}")
    ganadas = sum(1 for r in salida if r["vs_bh"] > 0)         # series donde superó a comprar y mantener
    promedio = sum(r["vs_bh"] for r in salida) / len(salida)   # diferencia promedio con comprar y mantener
    print(f"  -> supera a comprar y mantener en {ganadas}/{len(salida)} series | promedio vs B&H {promedio:+.0f}")
    return salida
