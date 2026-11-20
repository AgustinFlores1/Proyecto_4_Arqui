from mercado import BYTE_MANTENER, byte_comprar


class NoOperar:
    nombre = "No operar"

    def tick(self, precio):
        return BYTE_MANTENER


class CompraInicial:
    """
    'Comprar y mantener' jugado a través del protocolo (con el desfase de un tick).
    Difiere un poco de la fórmula del testbench, que compra a p[0] directamente.
    """
    nombre = "Comprar y mantener (protocolo)"

    def __init__(self):
        self.ticks = 0

    def tick(self, precio):
        self.ticks += 1
        # Dos órdenes por si el precio es bajo y 63 acciones no alcanzan para invertir todo.
        return byte_comprar(63) if self.ticks <= 2 else BYTE_MANTENER
