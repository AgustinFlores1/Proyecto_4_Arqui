"""
Gráfico roofline del kernel de media móvil en las tres versiones.

Todos los números están aquí abajo, con su cuenta, para poder cambiarlos o
rehacer el gráfico a mano. Uso (desde trading_sim/):
    python roofline.py
Guarda resultados/roofline.png en la raíz del repositorio.

Definiciones:
  - Operación útil: cada suma o resta del kernel de media móvil. Por tick son 7:
    S_c += p - viejo8 (2), S_l += p - viejo32 (2) y D = 4*S_c - S_l (2 sumas y 1 resta).
    No cuentan las instrucciones de direcciones, índices, saltos ni esperas.
  - Bytes de memoria: los que el kernel lee o escribe en memoria por tick.
"""
from pathlib import Path

from grafico import graficar_roofline

F_MHZ = 25                        # frecuencia del reloj (MHz)
OPS = 7                           # operaciones útiles del kernel por tick

# Techos del core Espino
PICO_OPS = F_MHZ / 2              # 1 instrucción cada 2 ciclos como máximo -> 12,5 MOps/s
ANCHO_BANDA = 4 * F_MHZ / 3       # 1 carga de 4 bytes cada 3 ciclos -> 33,3 MB/s

# Kernel en cada versión: (nombre, intensidad op/B, rendimiento MOps/s, nota)
#   intensidad  = OPS / bytes movidos por tick
#   rendimiento = F_MHZ * OPS / ciclos que toma el kernel
KERNELS = [
    # Solo software: actualizar (28 ciclos) + cálculo de D (6) = 34 ciclos; 2 lw + 1 sw de 4 bytes = 12 B
    ("Solo software", OPS / 12, F_MHZ * OPS / 34, ""),
    # Variante B: actualizar con circ (24 ciclos) + dif (2) = 26 ciclos; mismos 12 B
    ("Variante B (custom-0)", OPS / 12, F_MHZ * OPS / 26, ""),
    # Variante A: el periférico hace las 7 operaciones en 3 ciclos; 2 lecturas + 1 escritura de 1 byte en su BRAM = 3 B
    ("Variante A (periférico)", OPS / 3, F_MHZ * OPS / 3, "hardware propio: fuera del techo del core"),
]

if __name__ == "__main__":
    ruta = Path(__file__).resolve().parent.parent / "resultados" / "roofline.png"
    graficar_roofline(PICO_OPS, ANCHO_BANDA, KERNELS, ruta)
    for nombre, intensidad, rendimiento, _ in KERNELS:
        print(f"{nombre:26s} intensidad {intensidad:5.2f} op/B   rendimiento {rendimiento:5.1f} MOps/s")
    print(f"Techo de cómputo {PICO_OPS:g} MOps/s, techo de memoria {ANCHO_BANDA:.1f} MB/s, "
          f"quiebre {PICO_OPS / ANCHO_BANDA:.3f} op/B")
    print(f"Guardado en {ruta}")
