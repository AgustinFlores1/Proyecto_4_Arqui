# Simulador Pochoco Trader (Proyecto 4)

Versión de referencia en Python del agente de inversión. Replica la contabilidad
de `tb_proyecto_4.sv` regla por regla, así que el patrimonio de aquí y el de la
simulación RTL deben coincidir tick a tick. Solo usa la biblioteca estándar de
Python 3 (probado con 3.13).

## Estructura

| Archivo | Qué es | Estado |
|---|---|---|
| `mercado.py` | La FPGA maestra: desfase de un tick, comisión, límites de compra/venta, métricas | listo |
| `rsi.py` | RSI con ventana deslizante y nivel 0–16, solo enteros | listo |
| `estrategias/referencias.py` | No operar y comprar-y-mantener | listo |
| `estrategias/componentes.py` | `Historial` (listo), `CuantilEstocastico` (A2), `TablaResultados` (B) | **TODO** |
| `estrategias/rsi_aprende.py` | Esqueleto común + las 3 variantes | **TODO** |
| `comparar.py` | Tabla de resultados en calibración / validación / serie completa, y `barrido()` de parámetros | listo |
| `comparar_csv.py` | Compara el `decisiones.csv` del simulador con el del testbench RTL | listo |
| `series_sinteticas.py` | Series artificiales (reversión y tendencia) para revisar que B aprende | listo |
| `tests/` | Tests del simulador, del RSI, de los componentes y de la alineación de `aprender()` | listo |
| (serie) | Se lee de `tb/practica.csv` del repo, la misma que usa el testbench. Si `sim_trader/` está suelto, de `sim_trader/datos/practica.csv` | — |

## Uso

Todo se corre desde la carpeta `sim_trader/`:

```bash
python3 -m unittest discover -s tests -t . -v   # tests
python3 comparar.py                              # compara las estrategias
python3 comparar.py --ticks 2000                 # mismos ticks que el testbench por defecto
python3 comparar.py --csv sim.csv --cual 2       # escribe decisiones de ESTRATEGIAS[2]
python3 comparar_csv.py sim.csv decisiones.csv   # contra la salida de vvp
```

## Qué verifican los tests

- `test_mercado.py`: cada regla del testbench (compra limitada por la caja,
  venta limitada por las acciones, venta que no paga comisión, código `11`,
  desfase de un tick, decisión que se repite, pérdida máxima, fórmula de
  comprar y mantener).
- `test_rsi.py`: el ejemplo con N = 4 (U = 7, D = 1, nivel 14) y U/D comparados
  contra una suma de fuerza bruta en 3000 ticks de la serie.
- `test_componentes.py`: `Historial`; que `CuantilEstocastico` converja a los
  percentiles 85 y 15 y no se salga de [0, 16]; que `TablaResultados` sume,
  cuente, compare sin dividir y olvide exactamente las muestras fuera de la ventana.
- `test_estrategias.py`: contrato (determinismo, no repetir órdenes en ticks
  seguidos) y **alineación**: espía la tabla y verifica que cada muestra sea
  `(casilla en t, p[t+1+h] − p[t+1])`. Si falla, la estrategia aprende con el
  desfase equivocado.

Mientras los TODO no estén implementados, fallan 10 tests (los de
`CuantilEstocastico`, `TablaResultados` y alineación). Las estrategias corren
igual: simplemente mantienen.

## Reglas para que la versión en Python sea traducible a `trade.s`

- Solo enteros: nada de `float`, `/` ni `math`.
- Multiplicaciones solo por constantes (en assembly son sumas repetidas).
- Buffers de tamaño potencia de 2, con índice `& mascara` (`andi`).
- Calibrar parámetros mirando solo la mitad de calibración.
