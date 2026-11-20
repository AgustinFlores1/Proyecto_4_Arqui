"""
RSI con ventana deslizante (versión de Cutler), solo con operaciones enteras.

Está escrito para parecerse a lo que hará trade.s: buffer circular de tamaño
potencia de 2 (el índice da la vuelta con '& mascara', como un andi), U y D
actualizados con lo que entra y lo que sale. Así, al traducirlo a assembly,
la estructura es la misma y los resultados deben coincidir tick a tick.
"""

SIN_INFO = -1  # nivel cuando U + D == 0 (la ventana no tuvo movimiento)


class RSIVentana:
    def __init__(self, N: int = 32):
        assert N > 0 and (N & (N - 1)) == 0, "N debe ser potencia de 2 (para usar andi)"
        self.N = N
        self.mascara = N - 1
        self.buf = [0] * N     # últimos N cambios de precio (Δ)
        self.idx = 0           # posición del Δ más antiguo (el que sale)
        self.U = 0             # suma de subidas en la ventana
        self.D = 0             # suma de bajadas (en valor absoluto) en la ventana
        self.p_prev = None

    def actualizar(self, p: int) -> None:
        if self.p_prev is None:  # primer precio: todavía no hay Δ
            self.p_prev = p
            return
        delta_nuevo = p - self.p_prev
        self.p_prev = p

        delta_viejo = self.buf[self.idx]
        self.buf[self.idx] = delta_nuevo
        self.idx = (self.idx + 1) & self.mascara

        # sale el viejo
        if delta_viejo > 0:
            self.U -= delta_viejo
        else:
            self.D -= -delta_viejo
        # entra el nuevo
        if delta_nuevo > 0:
            self.U += delta_nuevo
        else:
            self.D += -delta_nuevo

    def nivel(self) -> int:
        """
        RSI cuantizado: floor(16·U / (U+D)), de 0 a 16, o SIN_INFO si U+D == 0.

        En trade.s esto es la división restaurativa de 5 pasos; aquí basta '//'.
        Ambas deben dar exactamente lo mismo: úselo para verificar su assembly.
        """
        total = self.U + self.D
        if total == 0:
            return SIN_INFO
        return (16 * self.U) // total
