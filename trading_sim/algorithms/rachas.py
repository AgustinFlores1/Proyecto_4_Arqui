from trader import Trader, MANTENER, COMPRAR, VENDER
from algorithms.herramientas import a_orden


class Rachas(Trader):
    """
    Rachas: comprar después de varias bajadas seguidas, vender después de
    varias subidas.

    Qué es y qué hace
    -----------------
    Estrategia de reversión a la media: supone que después de varias bajadas
    seguidas el precio tiende a rebotar.

    Lleva un contador de la racha actual: cuántos movimientos seguidos van en
    la misma dirección. Es positivo si vienen subidas y negativo si vienen
    bajadas. Cuando el precio cambia de dirección, la racha vuelve a empezar
    desde 1.

    Los ticks en que el precio no cambia se ignoran: no cortan ni alargan la
    racha. Así, "3 bajadas seguidas" significa 3 bajadas sin una subida
    entremedio, aunque haya ticks quietos en el medio.

    Compra después de n_bajas bajadas seguidas, esperando el rebote. Vende
    después de n_subidas subidas seguidas, tomando la ganancia. Opera con
    todo o nada.

    Variables
    ---------
    n_bajas    bajadas seguidas necesarias para comprar. Más grande: compra
               menos veces, solo después de caídas más largas.
    n_subidas  subidas seguidas necesarias para vender. Más grande: vende
               menos veces y mantiene más tiempo las acciones. Con valores
               muy altos casi nunca vende y se parece a comprar y mantener.
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int,
                 n_bajas: int = 3, n_subidas: int = 2) -> None:  # crea el trader con la racha en cero
        super().__init__(_name, _initial_capital, _market_comission)
        self.n_bajas = n_bajas                   # bajadas seguidas necesarias para comprar
        self.n_subidas = n_subidas               # subidas seguidas necesarias para vender
        self.racha = 0                           # >0: subidas seguidas, <0: bajadas seguidas
        self.precio_anterior = None              # precio del tick anterior

    def make_decision(self, price: int) -> tuple[int, int]:  # actualiza la racha y decide con ella
        if self.precio_anterior is not None:
            delta = price - self.precio_anterior                  # cambio de este tick
            if delta > 0:
                self.racha = self.racha + 1 if self.racha > 0 else 1    # sigue subiendo, o empieza una racha de subidas
            elif delta < 0:
                self.racha = self.racha - 1 if self.racha < 0 else -1   # sigue bajando, o empieza una racha de bajadas
            # delta == 0: la racha queda igual
        self.precio_anterior = price

        if self.racha <= -self.n_bajas:
            accion = COMPRAR                     # acción que quiere hacer este tick
        elif self.racha >= self.n_subidas:
            accion = VENDER
        else:
            accion = MANTENER
        return a_orden(accion, self.stocks)
