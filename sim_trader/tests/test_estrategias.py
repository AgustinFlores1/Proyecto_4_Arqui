"""
Tests de contrato para las estrategias, y el test más importante: que aprender()
entregue a la tabla exactamente las muestras correctas (el desfase bien hecho).

El test de alineación espía la tabla y compara cada muestra (casilla, r) con la
que corresponde según la definición

    casilla observada en t  ->  r = p[t+1+h] − p[t+1]

Para las casillas SIN_INFO acepta que las ignoren (se filtran en ambos lados).
"""

import os
import unittest

from mercado import leer_serie, serie_por_defecto, simular
from rsi import SIN_INFO
from estrategias.rsi_aprende import BCalentamiento, A2BRespaldo, A2BReagrupada

SERIE = serie_por_defecto()
VARIANTES = [BCalentamiento, A2BRespaldo, A2BReagrupada]


def espiar(estrategia):
    """Registra las casillas que guarda la estrategia y las muestras que aprende."""
    casillas, muestras = [], []
    guardar_original = estrategia.casillas.guardar
    aprender_original = estrategia.tabla.aprender

    def guardar(c):
        casillas.append(c)
        guardar_original(c)

    def aprender(c, r):
        muestras.append((c, r))
        aprender_original(c, r)

    estrategia.casillas.guardar = guardar
    estrategia.tabla.aprender = aprender
    return casillas, muestras


def muestras_esperadas(casillas, precios, h):
    """Muestras que deberían haberse aprendido hasta el último tick."""
    n_ticks = len(precios)
    salida = []
    for t, c in enumerate(casillas):
        if t + 1 + h < n_ticks and c != SIN_INFO:
            salida.append((c, precios[t + 1 + h] - precios[t + 1]))
    return salida


class TestContrato(unittest.TestCase):
    def setUp(self):
        self.precios = leer_serie(SERIE)[:3000]

    def test_devuelven_bytes_y_son_deterministas(self):
        for clase in VARIANTES:
            a = simular(clase(), self.precios, guardar_filas=True)
            b = simular(clase(), self.precios, guardar_filas=True)
            self.assertEqual(a.filas, b.filas, f"{clase.nombre} no es determinista")

    def test_no_repiten_una_orden_en_ticks_seguidos(self):
        for clase in VARIANTES:
            r = simular(clase(), self.precios, guardar_filas=True)
            bytes_ = [f[2] for f in r.filas]
            for i in range(1, len(bytes_)):
                if bytes_[i] != 0 and bytes_[i] == bytes_[i - 1]:
                    self.fail(f"{clase.nombre} repite la orden {bytes_[i]:02x} en los ticks {i-1} y {i}")


class TestAlineacion(unittest.TestCase):
    """Verifica su implementación de aprender(). Falla mientras sea TODO."""

    def _verificar(self, clase, h):
        precios = leer_serie(SERIE)[:2000]
        e = clase(h=h)
        casillas, muestras = espiar(e)
        simular(e, precios)
        esperadas = muestras_esperadas(casillas, precios, h)
        obtenidas = [m for m in muestras if m[0] != SIN_INFO]
        self.assertTrue(obtenidas, f"{clase.nombre}: aprender() no entregó ninguna muestra")
        for i, (o, esp) in enumerate(zip(obtenidas, esperadas)):
            self.assertEqual(o, esp, f"{clase.nombre}, h={h}: la muestra #{i} es {o}, debería ser {esp}")
        self.assertEqual(len(obtenidas), len(esperadas),
                         f"{clase.nombre}, h={h}: aprendió {len(obtenidas)} muestras, debían ser {len(esperadas)}")

    def test_b_calentamiento(self):
        for h in (1, 4, 8):
            self._verificar(BCalentamiento, h)

    def test_a2b_respaldo(self):
        self._verificar(A2BRespaldo, 8)

    def test_a2b_reagrupada(self):
        self._verificar(A2BReagrupada, 8)


if __name__ == "__main__":
    unittest.main()
