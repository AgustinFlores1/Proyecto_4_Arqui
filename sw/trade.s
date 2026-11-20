# trade.s: loop mínimo del Pochoco Trader.
#
# Espera cada precio que llega por SPI, lo lee y responde siempre "mantener"
# (DECISION = 0x00). Sirve para probar el protocolo con la FPGA maestra y el
# testbench antes de implementar el algoritmo.
#
# Mapa de memoria (README de Pochoco):
#   0x8001_0000  SPI STATUS    bit 0 = hay precio nuevo, bit 1 = CS activo
#   0x8001_0004  SPI PRICE     leerlo baja el bit "precio nuevo"
#   0x8001_0008  SPI DECISION  byte que la maestra lee en la próxima transacción
#   0x8000_0000  7 segmentos   (depuración: muestra el precio en hexadecimal)
#
# Registros:
#   x10  base del SPI slave
#   x11  base de los periféricos (7 segmentos)
#   x12  STATUS leído
#   x13  precio recibido

        lui   x10, 0x80010          # x10 = 0x8001_0000
        lui   x11, 0x80000          # x11 = 0x8000_0000

esperar:
        lw    x12, 0(x10)           # STATUS
        andi  x12, x12, 1           # ¿hay precio nuevo?
        beq   x12, x0, esperar      # no: seguir esperando

        lw    x13, 4(x10)           # precio (baja el bit "precio nuevo")
        sw    x13, 0(x11)           # 7 segmentos = precio en hex

        sw    x0, 8(x10)            # DECISION = 0x00 (mantener)
        j     esperar
