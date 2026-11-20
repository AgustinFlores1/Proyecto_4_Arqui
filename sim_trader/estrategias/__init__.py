"""
Toda estrategia es una clase con:

    nombre: str
    def tick(self, precio: int) -> int     # devuelve el byte que queda en DECISION

Se crea una instancia nueva por cada simulación (ver comparar.py), así que el
estado puede vivir en atributos sin preocuparse de reiniciarlo.

Reglas para que la versión en Python sea traducible a trade.s:
  - solo enteros: nada de float, '/' ni math
  - multiplicaciones solo por constantes (en assembly serán sumas repetidas)
  - buffers de tamaño potencia de 2, índice con '& mascara'
"""
