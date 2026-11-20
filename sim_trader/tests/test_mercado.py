"""Tests del simulador de mercado: cada regla del testbench tiene su caso."""

import unittest

from mercado import (Contabilidad, simular, comprar_y_mantener, div_trunc,
                     byte_comprar, byte_vender, BYTE_MANTENER, CAJA0, COMISION)


class Guion:
    """Estrategia que devuelve una lista fija de bytes (y luego MANTENER)."""
    nombre = "guion"

    def __init__(self, bytes_):
        self.bytes_ = list(bytes_)
        self.vistos = []

    def tick(self, p):
        self.vistos.append(p)
        return self.bytes_.pop(0) if self.bytes_ else BYTE_MANTENER


class TestDivTrunc(unittest.TestCase):
    def test_trunca_hacia_cero(self):
        self.assertEqual(div_trunc(7, 2), 3)
        self.assertEqual(div_trunc(-7, 2), -3)   # Python con // daría -4
        self.assertEqual(div_trunc(0, 5), 0)


class TestContabilidad(unittest.TestCase):
    def test_compra_cobra_precio_y_comision(self):
        c = Contabilidad()
        c.ejecutar(byte_comprar(10), 100)
        self.assertEqual(c.caja, CAJA0 - 10 * 100 - COMISION)
        self.assertEqual(c.acciones, 10)
        self.assertEqual(c.ordenes, 1)

    def test_compra_limitada_por_la_caja(self):
        c = Contabilidad(caja=1000)
        c.ejecutar(byte_comprar(63), 100)          # alcanza para (1000-5)//100 = 9
        self.assertEqual(c.acciones, 9)
        self.assertEqual(c.caja, 1000 - 900 - 5)

    def test_compra_sin_caja_no_es_orden(self):
        c = Contabilidad(caja=50)
        c.ejecutar(byte_comprar(5), 100)
        self.assertEqual((c.caja, c.acciones, c.ordenes), (50, 0, 0))

    def test_compra_de_cero_no_cobra(self):
        c = Contabilidad()
        c.ejecutar(byte_comprar(0), 100)
        self.assertEqual((c.caja, c.ordenes), (CAJA0, 0))

    def test_venta_entrega_menos_comision(self):
        c = Contabilidad(caja=0, acciones=20)
        c.ejecutar(byte_vender(5), 100)
        self.assertEqual(c.caja, 500 - COMISION)
        self.assertEqual(c.acciones, 15)

    def test_venta_limitada_a_las_acciones(self):
        c = Contabilidad(caja=0, acciones=3)
        c.ejecutar(byte_vender(63), 100)
        self.assertEqual((c.acciones, c.caja), (0, 300 - COMISION))

    def test_venta_sin_acciones_no_es_orden(self):
        c = Contabilidad()
        c.ejecutar(byte_vender(10), 100)
        self.assertEqual((c.caja, c.ordenes), (CAJA0, 0))

    def test_venta_que_no_paga_la_comision_se_rechaza(self):
        c = Contabilidad(caja=0, acciones=1)
        c.ejecutar(byte_vender(1), 4)              # 0 + 4 < 5
        self.assertEqual((c.caja, c.acciones, c.ordenes), (0, 1, 0))

    def test_reservado_11_es_mantener(self):
        c = Contabilidad()
        c.ejecutar(0b11_000101, 100)
        self.assertEqual((c.caja, c.acciones, c.ordenes), (CAJA0, 0, 0))

    def test_patrimonio_y_perdida_maxima(self):
        c = Contabilidad()
        c.ejecutar(byte_comprar(50), 100)          # caja 4995, 50 acc -> W 9995
        c.ejecutar(BYTE_MANTENER, 120)             # W 10995 (nuevo peak)
        c.ejecutar(BYTE_MANTENER, 90)              # W 9495  -> caída 1500
        c.ejecutar(BYTE_MANTENER, 110)             # W 10495
        self.assertEqual(c.patrimonio, 4995 + 50 * 110)
        self.assertEqual(c.peak, 4995 + 50 * 120)
        self.assertEqual(c.max_dd, 1500)


class TestSimular(unittest.TestCase):
    def test_la_estrategia_ve_un_precio_por_tick_en_orden(self):
        g = Guion([])
        simular(g, [5, 6, 7])
        self.assertEqual(g.vistos, [5, 6, 7])

    def test_desfase_de_un_tick(self):
        # La decisión que devuelve tras ver p[0]=100 se ejecuta a p[1]=200.
        r = simular(Guion([byte_comprar(10)]), [100, 200, 200], guardar_filas=True)
        tick1 = r.filas[1]
        self.assertEqual(tick1[2], byte_comprar(10))           # byte leído en el tick 1
        self.assertEqual(tick1[3], CAJA0 - 10 * 200 - COMISION)  # comprado a 200, no a 100

    def test_el_primer_tick_ejecuta_el_valor_de_reset(self):
        r = simular(Guion([]), [100], guardar_filas=True)
        self.assertEqual(r.filas[0][2], BYTE_MANTENER)

    def test_una_decision_que_no_se_reemplaza_se_repite(self):
        # Devuelve comprar 1 dos veces: compra dos veces (dos comisiones).
        r = simular(Guion([byte_comprar(1), byte_comprar(1)]), [100, 100, 100, 100])
        self.assertEqual(r.ordenes, 2)
        self.assertEqual(r.comisiones, 2 * COMISION)

    def test_rechaza_valores_que_no_son_byte(self):
        with self.assertRaises(ValueError):
            simular(Guion([256]), [100, 100])

    def test_comprar_y_mantener_igual_que_el_testbench(self):
        p = [165, 170, 160]
        q = (CAJA0 - COMISION) // 165
        self.assertEqual(comprar_y_mantener(p), CAJA0 - COMISION - q * 165 + q * 160)


if __name__ == "__main__":
    unittest.main()
