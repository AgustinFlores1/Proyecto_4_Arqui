# Registros:
#   x5:  Contador de precios en ventana de aprendizaje (0 -> 32)
#   x6:  Flag si tiene acciones (comprado = 0 o 1)
#   x7:  Temporal
#   x8:  Temporal
#   x9:  Temporal
#   x10: Base del SPI slave (0x8001_0000)
#   x11: Base del buffer (0x400 -> 0x47F)
#   x12: Idx de posicion en buffer
#   x13: Precio recibido en el tick
#   x14: S_c -> Suma de los ultimos 8 precios
#   x15: S_l -> Suma de los ultimos 32 precios

# Mapa de memoria (README de Pochoco):
#   0x8001_0000 [0(x10)] SPI STATUS    bit 0 = hay precio nuevo, bit 1 = CS activo
#   0x8001_0004 [4(x10)] SPI PRICE     leerlo baja el bit "precio nuevo"
#   0x8001_0008 [8(x10)] SPI DECISION  byte que la maestra lee en la próxima transacción
#   0x8000_0000  7 segmentos   (depuración: muestra el precio en hexadecimal)

inicio:
        lui   x1, 0x80000        # x1 = base de periféricos (display +0, LEDs +4)
        lui   x10, 0x80010       # spi = 0x8001_0000
        addi  x11, x0, 0x400     # buf = 0x400

        sw    x0, 8(x10)         # DECISION = mantener
        addi  x5, x0, 0          # cont = 0
        addi  x6, x0, 0          # comprado = 0
        addi  x7, x0, 128        # límite de limpiar: 32 posiciones × 4 bytes
        addi  x12, x0, 0         # idx = 0
        addi  x13, x0, 0         # p = 0
        addi  x14, x0, 0         # S_c = 0
        addi  x15, x0, 0         # S_l = 0

limpiar:
        add   x8, x11, x12       # dirección = buf + idx
        sw    x0, 0(x8)          # buffer[idx] = 0
        addi  x12, x12, 4        # siguiente posición
        bne   x12, x7, limpiar   # hasta llegar a 128
        addi  x12, x0, 0         # idx vuelve a 0

esperar:
        lw    x7, 8(x1)          # botones
        bne   x7, x0, inicio     # cualquier botón presionado: reiniciar todo

        lw    x7, 0(x10)         # STATUS
        andi  x7, x7, 1          # bit 0: new_price
        beq   x7, x0, esperar    # sin precio nuevo: seguir esperando
        lw    x13, 4(x10)        # p = PRICE (new_price vuelve a 0)

        sw    x13, 0(x1)         # display = precio en hexadecimal

actualizar:
        add   x7, x11, x12       # dirección del más viejo = buf + idx
        lw    x8, 0(x7)          # viejo32 = buffer[idx]

        addi  x9, x12, 96        # idx + 96 ...
        andi  x9, x9, 124        # ... AND 124 = posición de hace 8 ticks
        add   x9, x11, x9        # dirección = buf + esa posición
        lw    x9, 0(x9)          # viejo8

        sw    x13, 0(x7)         # buffer[idx] = new_price
        addi  x12, x12, 4        # idx + 4
        andi  x12, x12, 124      # idx = 0 si es que se da la vuelta (128)

        sub   x14, x14, x9       # S_c -= viejo8
        add   x14, x14, x13      # S_c += precio

        sub   x15, x15, x8       # S_l -= viejo32
        add   x15, x15, x13      # S_l += precio

calentar:
        addi x7, x0, 32          # Tamaño maximo de buffer
        addi x9, x0, 0x00        # DECISION mantenerse
        bge  x5, x7, decidir     # Si el tamaño de buffer (x5) es mayor a 32 ya puede decidir

        addi x5, x5, 1           # Sumar 1 al tamaño del buffer
        blt  x5, x7, escribir    # Escribir DECISION mantenerse directamente

decidir:
        add x7, x14, x14         # S_c + S_c
        add x7, x7, x7           # (S_c + S_c) * 2
        sub x7, x7, x15          # D = 4 * S_c - S_l 

        beq  x6, x0, sin_acciones # Si comprado (x6) = 0, va a comprar

con_acciones:
        addi x8, x0, -64
        bge  x7, x8, escribir    # D >= −64: no vender → mantener (x9 ya es 0)
        addi x9, x0, 0xBF        # vender 63
        addi x6, x0, 0           # comprado = 0
        j escribir

sin_acciones:
        addi x8, x0, 64
        bge  x8, x7, escribir    # D <= 64: no comprar → mantener (x9 ya es 0)
        addi x9, x0, 0x7F        # comrpar 63
        addi x6, x0, 1           # comprado = 1

escribir:
        sw    x6, 4(x1)          # LED 1 encendido = tienes acciones

        sw   x9, 8(x10)          # Escribir decision en la ram
        j    esperar
