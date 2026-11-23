from trader import Trader, MANTENER, COMPRAR, VENDER


class Lotes(Trader):
    """
    Lotes (grid trading): comprar por partes en las bajadas y vender cada parte
    con ganancia.

    Qué es y qué hace
    -----------------
    En vez de comprar o vender todo de una vez, divide la inversión en lotes
    de q acciones. Compra un lote al principio, y después otro cada vez que el
    precio baja 'bajada' puntos desde la compra más reciente. Así va
    comprando más barato a medida que el precio cae.

    Cada lote recuerda a qué precio se compró y se vende por separado, solo
    cuando el precio lo supera en 'subida' puntos. Por eso cada venta
    individual siempre gana.

    Ojo: eso no significa que el algoritmo siempre gane. Si el precio cae y no
    se recupera, los lotes se quedan sin vender con una pérdida que no aparece
    en las ventas, pero sí en el patrimonio (efectivo + acciones · precio).

    Solo compra lotes completos: si no alcanza el dinero para q acciones, no
    compra.

    Variables
    ---------
    q       acciones por lote (1 a 63). Lotes chicos permiten comprar en más
            escalones, pero la comisión pesa más por acción (10/q puntos ida y
            vuelta). Con q cercano a 63 casi nunca alcanza para un segundo lote.
    bajada  puntos que tiene que bajar el precio desde la última compra para
            comprar otro lote.
    subida  puntos sobre el precio de compra de un lote para venderlo.
            Debería superar el costo de comisión por acción.
    """

    def __init__(self, _name: str, _initial_capital: int, _market_comission: int,
                 q: int = 16, bajada: int = 3, subida: int = 3) -> None:  # crea el trader sin lotes
        super().__init__(_name, _initial_capital, _market_comission)
        self.q = q                               # acciones por lote (1 a 63)
        self.bajada = bajada                     # puntos bajo la última compra para comprar otro lote
        self.subida = subida                     # puntos sobre el precio de compra de un lote para venderlo
        self.lotes = []                          # lotes que se tienen: [precio_compra, cantidad], en orden de compra
        self.vendiendo = []                      # lotes incluidos en la orden de venta pendiente
        self.stocks_anterior = 0                 # acciones del tick anterior, para detectar lo que se ejecutó

    def make_decision(self, price: int) -> tuple[int, int]:  # actualiza la lista de lotes y decide la orden
        # 1. ¿Se ejecutó algo? El mercado ejecuta al precio actual antes de llamar aquí.
        cambio = self.stocks - self.stocks_anterior
        if cambio > 0:
            self.lotes.append([price, cambio])   # se compró un lote a este precio
        elif cambio < 0:
            for lote in self.vendiendo:          # se vendieron los lotes de la orden pendiente
                self.lotes.remove(lote)
        self.vendiendo = []
        self.stocks_anterior = self.stocks

        # 2. Vender los lotes que llegaron a su objetivo, los más baratos primero (máximo 63 acciones)
        listos = sorted((l for l in self.lotes if price >= l[0] + self.subida), key=lambda l: l[0])
        cantidad = 0
        for lote in listos:
            if cantidad + lote[1] > 63:
                break                            # no cabe en la orden; queda para el tick siguiente
            self.vendiendo.append(lote)
            cantidad += lote[1]
        if cantidad > 0:
            return VENDER, cantidad

        # 3. Comprar un lote si no hay ninguno o si el precio bajó desde la última compra
        alcanza = self.cash >= self.q * price + self.commision      # solo lotes completos, nunca uno parcial
        if alcanza and (not self.lotes or price <= self.lotes[-1][0] - self.bajada):
            return COMPRAR, self.q
        return MANTENER, 0
