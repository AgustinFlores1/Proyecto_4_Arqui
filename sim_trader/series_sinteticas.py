"""
Series artificiales con un comportamiento conocido, para revisar que la tabla
aprende lo que debería. Ejemplo:

    from series_sinteticas import oscilante, tendencias
    from mercado import simular
    from estrategias.rsi_aprende import BCalentamiento
    print(simular(BCalentamiento(), oscilante()).patrimonio_final)

Si B está bien implementado, en 'oscilante' debería aprender que los niveles
altos anticipan bajadas, y en 'tendencias' lo contrario.
"""

import random


def _acotar(p):
    return max(1, min(255, p))


def oscilante(n=20000, centro=170, amplitud=40, periodo=80, ruido=2, semilla=1):
    """Sube y baja en forma triangular alrededor de 'centro': régimen de reversión."""
    rnd = random.Random(semilla)
    serie = []
    for t in range(n):
        fase = t % periodo
        tri = fase if fase < periodo // 2 else periodo - fase   # 0 .. periodo/2 .. 0
        base = centro - amplitud + (2 * amplitud * tri) // (periodo // 2)
        serie.append(_acotar(base + rnd.randint(-ruido, ruido)))
    return serie


def tendencias(n=20000, inicio=150, largo_tramo=400, ruido=1, semilla=2):
    """Tramos largos de subida o bajada sostenida: régimen de tendencia."""
    rnd = random.Random(semilla)
    serie, p, direccion = [], inicio, 1
    for t in range(n):
        if t % largo_tramo == 0:
            direccion = 1 if p < 130 else (-1 if p > 210 else rnd.choice((-1, 1)))
        if rnd.random() < 0.4:
            p = _acotar(p + direccion + rnd.randint(-ruido, ruido))
        serie.append(p)
    return serie
