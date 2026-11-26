# trade_sma.s: CruceMedias 8/32 (margen 2) usando el periférico de media móvil (variante A).
#
# El periférico (pochoco_sma.v, dentro del SPI slave) actualiza el buffer de 32 precios
# y las sumas S_c y S_l cada vez que llega un precio, y entrega D = 4·S_c − S_l en 0x0C.
# Este programa ya no tiene buffer ni sumas: lee D y decide.
#
# Registros:
#   x1:  Base de periféricos de la placa (0x8000_0000): display +0, LEDs +4, botones +8
#   x5:  Contador de precios del calentamiento (0 -> 32)
#   x6:  Flag si tiene acciones (comprado = 0 o 1)
#   x7:  Temporal
#   x8:  Temporal (umbral ±64)
#   x9:  Decisión a escribir
#   x10: Base del SPI slave (0x8001_0000)
#   x13: Precio recibido en el tick (solo para el display)
#   x14: D = 4·S_c − S_l, leído del periférico
#
# Mapa del SPI slave:
#   0x8001_0000 [0(x10)]  STATUS    bit 0 = hay precio nuevo, bit 1 = CS activo, bit 2 = periférico ocupado
#   0x8001_0004 [4(x10)]  PRICE     leerlo baja el bit "precio nuevo"
#   0x8001_0008 [8(x10)]  DECISION  byte que la maestra lee en la próxima transacción
#   0x8001_000C [12(x10)] SMA       leer = D; escribir (cualquier valor) = reiniciar el periférico

inicio:
        lui   x1, 0x80000        # x1 = base de periféricos (display +0, LEDs +4, botones +8)
        lui   x10, 0x80010       # spi = 0x8001_0000

        sw    x0, 8(x10)         # DECISION = mantener
        sw    x0, 12(x10)        # reiniciar el periférico: borra buffer y sumas
        addi  x5, x0, 0          # cont = 0
        addi  x6, x0, 0          # comprado = 0

esperar:
        lw    x7, 8(x1)          # botones
        bne   x7, x0, inicio     # cualquier botón presionado: reiniciar todo

        lw    x7, 0(x10)         # STATUS
        andi  x7, x7, 1          # bit 0: new_price
        beq   x7, x0, esperar    # sin precio nuevo: seguir esperando
        lw    x13, 4(x10)        # p = PRICE (new_price vuelve a 0)

        sw    x13, 0(x1)         # display = precio en hexadecimal

leer_d:
        lw    x14, 12(x10)       # D = 4·S_c − S_l (el periférico ya lo actualizó con este precio)

calentar:
        addi  x7, x0, 32         # precios necesarios antes de decidir
        addi  x9, x0, 0x00       # decisión por defecto: mantener
        bge   x5, x7, decidir    # ya hay 32 precios: decidir

        addi  x5, x5, 1          # un precio más
        blt   x5, x7, escribir   # todavía no hay 32: mantener

decidir:
        beq   x6, x0, sin_acciones # comprado = 0 → solo puede comprar

con_acciones:
        addi  x8, x0, -64
        bge   x14, x8, escribir  # D >= −64: no vender → mantener (x9 ya es 0)
        addi  x9, x0, 0xBF       # vender 63
        addi  x6, x0, 0          # comprado = 0
        j     escribir

sin_acciones:
        addi  x8, x0, 64
        bge   x8, x14, escribir  # D <= 64: no comprar → mantener (x9 ya es 0)
        addi  x9, x0, 0x7F       # comprar 63
        addi  x6, x0, 1          # comprado = 1

escribir:
        sw    x6, 4(x1)          # LED 1 encendido = tienes acciones
        sw    x9, 8(x10)         # DECISION
        j     esperar
