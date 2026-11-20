"""
Compara el decisiones.csv del simulador con el que escribe el testbench RTL.
Sirve para demostrar que trade.s toma exactamente las mismas decisiones.

    python3 comparar_csv.py sim.csv decisiones.csv
"""

import sys


def leer(ruta):
    with open(ruta) as f:
        next(f)
        return [linea.strip().split(",") for linea in f if linea.strip()]


def main(a, b):
    fa, fb = leer(a), leer(b)
    n = min(len(fa), len(fb))
    columnas = ["tick", "precio", "decision", "caja", "acciones", "patrimonio"]
    for i in range(n):
        if fa[i] != fb[i]:
            print(f"Primera diferencia en la fila {i}:")
            for col, x, y in zip(columnas, fa[i], fb[i]):
                marca = "  <--" if x != y else ""
                print(f"  {col:10} {x:>8} {y:>8}{marca}")
            sys.exit(1)
    if len(fa) != len(fb):
        print(f"Iguales en las primeras {n} filas, pero los largos difieren ({len(fa)} vs {len(fb)}).")
        sys.exit(1)
    print(f"Idénticos: {n} ticks.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
