"""Tests del RSI con ventana: el ejemplo de la clase y comparación con fuerza bruta."""

import os
import unittest

from mercado import leer_serie, serie_por_defecto
from rsi import RSIVentana, SIN_INFO

SERIE = serie_por_defecto()


def u_d_fuerza_bruta(precios, N):
    """U y D sumando explícitamente los últimos N cambios."""
    deltas = [precios[i] - precios[i - 1] for i in range(1, len(precios))][-N:]
    return sum(d for d in deltas if d > 0), sum(-d for d in deltas if d < 0)


class TestRSI(unittest.TestCase):
    def test_ejemplo_N4(self):
        # El ejemplo de la conversación: precios 100,102,101,101,104,103,107 con N = 4.
        esperado = [(0, 0), (2, 0), (2, 1), (2, 1), (5, 1), (3, 2), (7, 1)]
        r = RSIVentana(4)
        for p, (U, D) in zip([100, 102, 101, 101, 104, 103, 107], esperado):
            r.actualizar(p)
            self.assertEqual((r.U, r.D), (U, D))
        self.assertEqual(r.nivel(), 14)          # floor(16·7/8)

    def test_sin_movimiento_es_sin_info(self):
        r = RSIVentana(4)
        for p in [150, 150, 150, 150, 150]:
            r.actualizar(p)
        self.assertEqual(r.nivel(), SIN_INFO)

    def test_solo_subidas_es_16_y_solo_bajadas_es_0(self):
        r = RSIVentana(4)
        for p in [100, 101, 102]:
            r.actualizar(p)
        self.assertEqual(r.nivel(), 16)
        r = RSIVentana(4)
        for p in [100, 99, 98]:
            r.actualizar(p)
        self.assertEqual(r.nivel(), 0)

    def test_N_debe_ser_potencia_de_2(self):
        with self.assertRaises(AssertionError):
            RSIVentana(14)

    def test_coincide_con_fuerza_bruta_en_la_serie(self):
        precios = leer_serie(SERIE)[:3000]
        for N in (4, 16, 64):
            r = RSIVentana(N)
            for i, p in enumerate(precios):
                r.actualizar(p)
                self.assertEqual((r.U, r.D), u_d_fuerza_bruta(precios[: i + 1], N),
                                 f"N={N}, tick {i}")
                nivel = r.nivel()
                self.assertTrue(nivel == SIN_INFO or 0 <= nivel <= 16)


if __name__ == "__main__":
    unittest.main()
