from trader import Trader, MANTENER, COMPRAR, VENDER
from algorithms.herramientas import a_orden


class TomaGanancia(Trader):
    """
    Toma de ganancia con stop móvil: vender solo cuando ya se ganó, y dejar
    que la ganancia crezca.

    Qué es y qué hace
    -----------------
    Compra en el primer tick y anota el precio al que se ejecutó la compra
    (la referencia). Después funciona en tres pasos:

      1. Esperar: mientras el precio no supere referencia + umbral, no hace
         nada, aunque el precio baje.
      2. Armarse: cuando el precio supera referencia + umbral, ya hay
         ganancia asegurada. Desde ahí sigue el precio más alto alcanzado.
      3. Vender: si el precio cae 'caida' puntos desde ese máximo, vende todo.
         Esto se llama stop móvil: el punto de venta sube junto con el precio,
         así que mientras siga subiendo no vende.

    Después de vender espera a que el precio baje 'recompra' puntos bajo el
    precio de venta, y vuelve a comprar con todo lo que tiene. Así vuelve a
    entrar más barato de lo que salió.

    Nunca vende con pérdida. Eso funciona bien si el precio termina volviendo,
    pero si cae y no se recupera, se queda comprado hasta el final y pierde
    igual que comprar y mantener.

    Variables
    ---------
    umbral    puntos sobre el precio de compra para armar la venta. Más
              grande: busca ganancias más grandes por operación, pero se arma
              menos veces.
    caida     puntos bajo el máximo para vender. Más chico: vende ante la
              primera bajada (1 = "la primera bajada"). Más grande: aguanta
              las correcciones y deja crecer la ganancia, pero devuelve más
              al final.
    recompra  puntos bajo el precio de venta para volver a comprar. Más
              grande: recompra más barato, pero puede quedarse mucho tiempo
              fuera del mercado si el precio no baja.
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int,
                 umbral: int = 7, 
                 caida: int = 5, 
                 recompra: int = 10) -> None:  # crea el trader sin posición
        
        super().__init__(_name, _initial_capital, _market_comission)
        self.umbral = umbral                     # puntos sobre la referencia para armar la venta
        self.caida = caida                       # puntos bajo el máximo para vender (1 = "la primera bajada")
        self.recompra = recompra                 # puntos bajo el precio de venta para volver a comprar
        self.referencia = None                   # precio al que se ejecutó la última compra
        self.armado = False                      # True cuando el precio ya superó referencia + umbral
        self.maximo = 0                          # máximo alcanzado desde que se armó
        self.precio_venta = None                 # precio al que se ejecutó la última venta (None: nunca vendió)
        self.stocks_anterior = 0                 # acciones del tick anterior, para detectar compras y ventas ejecutadas

    def make_decision(self, price: int) -> tuple[int, int]:  # detecta lo que se ejecutó y decide según la fase
        # 1. ¿Se ejecutó algo en este tick? El mercado ejecuta al precio actual antes de llamar aquí.
        if self.stocks > 0 and self.stocks_anterior == 0:
            self.referencia = price              # se compró: este es el precio de compra
            self.armado = False
        elif self.stocks == 0 and self.stocks_anterior > 0:
            self.precio_venta = price            # se vendió: desde aquí se mide la recompra
            self.referencia = None
        self.stocks_anterior = self.stocks

        # 2. Sin acciones: comprar al principio, o cuando el precio bajó lo suficiente desde la venta
        if self.stocks == 0:
            if self.precio_venta is None or price <= self.precio_venta - self.recompra:
                return a_orden(COMPRAR, self.stocks)
            return MANTENER, 0

        # 3. Con acciones: armar al superar el umbral y vender al caer desde el máximo
        if not self.armado and price >= self.referencia + self.umbral:
            self.armado = True
            self.maximo = price
        if self.armado:
            self.maximo = max(self.maximo, price)                 # el stop sube junto con el precio
            if price <= self.maximo - self.caida:
                return a_orden(VENDER, self.stocks)
        return MANTENER, 0
