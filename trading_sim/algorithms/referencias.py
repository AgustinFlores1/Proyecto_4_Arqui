from trader import Trader, MANTENER, COMPRAR


class ComprarYMantener(Trader):
    """Invierte toda la caja apenas puede y no vuelve a operar."""

    def make_decision(self, price: int) -> tuple[int, int]:  # compra mientras le alcance para al menos una acción
        alcanza = (self.cash - self.commision) // price      # acciones que puede pagar con la caja actual
        if alcanza > 0:
            return COMPRAR, min(63, alcanza)
        return MANTENER, 0
