"""
Tests de los componentes. Los de Historial pasan desde ya; los de
CuantilEstocastico y TablaResultados verifican SU implementación de los TODO.
"""

import random
import unittest

from estrategias.componentes import Historial, CuantilEstocastico, TablaResultados


class TestHistorial(unittest.TestCase):
    def test_hace_devuelve_los_ultimos(self):
        h = Historial(4)
        for v in [10, 20, 30]:
            h.guardar(v)
        self.assertEqual((h.hace(0), h.hace(1), h.hace(2)), (30, 20, 10))
        self.assertFalse(h.tiene(3))

    def test_da_la_vuelta(self):
        h = Historial(4)
        for v in range(10):
            h.guardar(v)
        self.assertEqual([h.hace(k) for k in range(4)], [9, 8, 7, 6])

    def test_no_mira_mas_alla_de_lo_guardado(self):
        h = Historial(4)
        h.guardar(1)
        with self.assertRaises(AssertionError):
            h.hace(1)


class TestCuantilEstocastico(unittest.TestCase):
    """A2: con niveles uniformes en 0..16, P(nivel ≤ θ) = (θ+1)/17."""

    def _promedio_theta(self, paso_arriba, paso_abajo, theta0, n=40000, K=64):
        rnd = random.Random(7)
        q = CuantilEstocastico(paso_arriba, paso_abajo, K, theta0)
        suma = 0
        for i in range(n):
            q.actualizar(rnd.randint(0, 16))
            self.assertTrue(0 <= q.theta <= 16, "θ salió de [0, 16]")
            if i >= n // 2:
                suma += q.theta
        return suma / (n - n // 2)

    def test_converge_al_percentil_85(self):
        # (θ+1)/17 = 0,85  ->  θ ≈ 13,45
        t = self._promedio_theta(17, 3, theta0=8)
        self.assertTrue(12.5 <= t <= 14.5, f"θ promedio = {t:.2f}, esperado ≈ 13,45")

    def test_converge_al_percentil_15(self):
        # (θ+1)/17 = 0,15  ->  θ ≈ 1,55
        t = self._promedio_theta(3, 17, theta0=8)
        self.assertTrue(0.8 <= t <= 2.5, f"θ promedio = {t:.2f}, esperado ≈ 1,55")

    def test_no_se_sale_de_rango_con_niveles_extremos(self):
        q = CuantilEstocastico(17, 3, 4, 8)
        for _ in range(2000):
            q.actualizar(16)
        self.assertEqual(q.theta, 16)
        for _ in range(4000):
            q.actualizar(0)
        self.assertEqual(q.theta, 0)


class TestTablaResultados(unittest.TestCase):
    def test_aprende_suma_y_conteo(self):
        t = TablaResultados(3, M=8)
        for r in (2, 4, -1):
            t.aprender(1, r)
        self.assertEqual((t.S[1], t.C[1]), (5, 3))
        self.assertEqual((t.S[0], t.C[0]), (0, 0))

    def test_confiable(self):
        t = TablaResultados(3, M=8)
        t.aprender(2, 1)
        self.assertFalse(t.confiable(2, 2))
        t.aprender(2, 1)
        self.assertTrue(t.confiable(2, 2))

    def test_comparaciones_sin_dividir(self):
        t = TablaResultados(3, M=8)
        for r in (1, 0, 0):           # promedio 1/3
            t.aprender(0, r)
        self.assertTrue(t.promedio_supera(0, 1, 5))     # 1/3 > 0,2
        self.assertFalse(t.promedio_supera(0, 1, 2))    # 1/3 > 0,5 es falso
        self.assertTrue(t.promedio_bajo(0, 1, 2))
        self.assertFalse(t.promedio_bajo(0, 0, 1))      # 1/3 < 0 es falso
        for r in (-5, -5):            # promedio (1-10)/5 = -1,8
            t.aprender(1, r)
        self.assertTrue(t.promedio_bajo(1, -1, 1))      # -5 < -1
        self.assertTrue(t.promedio_supera(1, -6, 1))    # -5 > -6 (num negativo)

    def test_olvido_por_ventana(self):
        # Con M = 4 la tabla debe valer lo mismo que sumar solo las últimas 4 muestras.
        rnd = random.Random(3)
        t = TablaResultados(3, M=4)
        muestras = []
        for _ in range(50):
            m = (rnd.randint(0, 2), rnd.randint(-5, 5))
            muestras.append(m)
            t.aprender(*m)
            ventana = muestras[-4:]
            for c in range(3):
                self.assertEqual(t.S[c], sum(r for cc, r in ventana if cc == c))
                self.assertEqual(t.C[c], sum(1 for cc, _ in ventana if cc == c))


if __name__ == "__main__":
    unittest.main()
