# Variante A: periférico de media móvil (MMIO)

## 1. Qué cambió

| | Solo software | Variante A |
|---|---|---|
| Buffer de 32 precios | RAM (`0x400–0x47F`), manejado por `trade.s` | BRAM propia dentro del periférico |
| Sumas `S_c`, `S_l` | registros `x14`, `x15`, actualizados en `actualizar` | registros del periférico, actualizados al llegar cada precio |
| `D = 4·S_c − S_l` | 3 instrucciones en `decidir` | combinacional en el periférico; la CPU lo lee en `0x8001_000C` |
| Decisión (umbrales ±64, flag, DECISION) | CPU | CPU (igual) |
| Programa | `trade.s`, 57 instrucciones | `trade_sma.s`, 32 instrucciones |
| Hardware | — | `pochoco_sma.v` + registro `0x0C` en `pochoco_spi_slave.v`; LEDs eliminados |

El periférico tarda 3 ciclos desde `byte_done` (REPOSO → LEER32 → LEER8). La CPU lee `D` al menos ~10 ciclos después, así que siempre está listo.

## 2. Modelo de ciclos (igual que en la versión solo software)

    ciclos = 2·IC + cargas + saltos_tomados

## 3. Costo de cada sección de `trade_sma.s` (teórico)

| Sección | Instrucciones | Cargas | Saltos tomados | Ciclos |
|---|---|---|---|---|
| esperar, vuelta sin precio | 5 | 2 | 1 | 13 |
| esperar, vuelta con precio (+ PRICE + display) | 7 | 3 | 0 | 17 |
| leer_d | 1 | 1 | 0 | 3 |
| calentar, durante el calentamiento | 5 | 0 | 1 | 11 |
| calentar, después del calentamiento | 3 | 0 | 1 | 7 |
| decidir, sin acciones → mantener | 3 | 0 | 2 | 8 |
| decidir, sin acciones → comprar | 5 | 0 | 1 | 11 |
| decidir, con acciones → mantener | 3 | 0 | 1 | 7 |
| decidir, con acciones → vender | 6 | 0 | 1 | 13 |
| escribir | 3 | 0 | 1 | 7 |

## 4. Caminos completos por tick (teórico)

| Camino | IC | Ciclos | CPI | Solo software (ciclos) |
|---|---|---|---|---|
| Calentamiento | 16 | 38 | 2,38 | 63 |
| Sin acciones → mantener (el más común) | 17 | 42 | 2,47 | 73 |
| Con acciones → mantener | 17 | 41 | 2,41 | 72 |
| Comprar | 19 | 45 | 2,37 | 76 |
| Vender (el más largo) | 20 | 47 | 2,35 | 78 |

## 5. Predicción de Amdahl vs medido

    speedup = 1 / ((1 − f) + f / s)        máximo = 1 / (1 − f)

Parte acelerada: `actualizar` (28 ciclos) + cálculo de `D` (6 ciclos) = 34 ciclos. Se agrega 1 `lw` (3 ciclos).

| | Base emulador (72,5 ciclos) | Base RTL (69,5 ciclos) |
|---|---|---|
| f | 34 / 72,5 = 0,47 | 34 / 69,5 = 0,49 |
| Ciclos predichos (72,5 − 34 + 3) | 41,5 | **38,5** |
| Speedup predicho | 1,75× | 1,81× |
| Máximo teórico (s → ∞, sin el `lw` extra) | 1,88× | 1,96× |
| **Ciclos medidos** | 41,5 (emulador) | **38,5 (RTL)** |
| **Speedup medido** | 1,75× | **1,81×** |

**El RTL coincide exactamente con la predicción (38,5 ciclos).** La parte que no es espera
vale 41,5 − 17 = 24,5 ciclos; la espera en el RTL promedia 38,5 − 24,5 = 14 ciclos,
lo mismo que en la versión solo software: el periférico no cambia la espera.

## 6. Valores medidos en el RTL (testbench, 20 000 ticks)

| Valor | Solo software | Variante A | Cambio |
|---|---|---|---|
| IC promedio | 31,2 | **16,2** | −48 % |
| IC peor caso | 37 | **22** | −41 % |
| Ciclos promedio | 69,5 | **38,5** | −45 % (1,81×) |
| Ciclos peor caso | 81 | **50** | −38 % (1,62×) |
| CPI | 2,23 | **2,37** | +6 % |
| Tiempo promedio por tick | 2,78 µs | **1,54 µs** | |
| Tiempo peor caso por tick | 3,24 µs | **2,00 µs** | |
| Patrimonio final (practica.csv) | 13 881 | 13 881 | igual |
| Decisiones iguales a Python | 20 000 / 20 000 | 20 000 / 20 000 | igual |

**Teórico vs medido:** IC peor caso = 20 (vender) + 2 de una vuelta de espera perdida = 22 ✓.
Ciclos peor caso ≈ 47 (vender) + ~5 de una vuelta perdida ≈ 52; medido 50 ✓.

**Por qué el CPI subió:** se eliminaron casi solo instrucciones de 2 ciclos (sumas, restas,
cálculo de direcciones). Las que quedan tienen más cargas y saltos de 3 ciclos en proporción.
Menos instrucciones no implica mejor CPI.

## 7. Plazo de cada ronda

| Ronda | Plazo (ciclos) | Solo software, peor caso | Variante A, peor caso |
|---|---|---|---|
| 1 (10 ms) | 249 762 | 0,032 % | 0,020 % |
| 2 (1 ms) | 24 762 | 0,33 % | 0,20 % |
| 3 (0,1 ms) | 2 262 | 3,6 % | **2,2 %** |

Las dos variantes cumplen el plazo con mucho margen. Como la decisión se ejecuta en el tick
siguiente, responder antes **no cambia la ganancia** (13 881 en ambas).

## 8. Recursos (iCE40 HX1K)

| Recurso | Solo software | Variante A | Diferencia |
|---|---|---|---|
| Celdas lógicas (`ICESTORM_LC`) | 1 068 (83 %) | **1 241 (96 %)** | +173 |
| BRAM | 12 | 13 | +1 |
| LUTs (yosys) | 891 | 1 046 | +155 |
| Flip-flops (yosys) | 258 | 316 | +58 |
| Cadenas de acarreo | 153 | 198 | +45 |
| Frecuencia máxima | 44,14 MHz | 45,49 MHz | ≈ igual (variación del place & route) |

- El periférico cuesta ~178 celdas (las +173 más ~5 que se liberaron al eliminar los LEDs).
- La primera versión del periférico no cabía (1 295 / 1 280). Se optimizó: sin copia del precio
  (usa `price_q` del SPI slave), sin registro para el precio viejo, y un solo restador compartido
  por las dos sumas. Además se eliminaron los LEDs.
- Quedan 39 celdas libres (3 %).
- **Costo por ciclo ahorrado:** 178 celdas / 31 ciclos ≈ 5,7 celdas por ciclo.

## 9. Ops/s

Definiciones:
- **Decisiones por segundo (máximo):** f / ciclos por tick, si los precios llegaran sin pausa.
- **Operaciones útiles del kernel de media móvil:** 7 por tick (2 restas y 2 sumas para
  actualizar `S_c` y `S_l`, y 2 sumas y 1 resta para `D`). Las instrucciones de direcciones,
  índices y esperas no cuentan.

| Valor | Solo software | Variante A |
|---|---|---|
| Decisiones por segundo (promedio) | 25 MHz / 69,5 = 360 mil | 25 MHz / 38,5 = **649 mil** (1,81×) |
| MIPS del core | 25 / 2,23 = 11,2 | 25 / 2,37 = 10,5 |
| Kernel: ciclos para las 7 operaciones | 34 (en la CPU) | 3 (en el periférico, en paralelo a la espera) |
| Kernel: operaciones por segundo | 25 MHz × 7 / 34 = 5,1 MOps/s | 25 MHz × 7 / 3 = 58 MOps/s |

Los MIPS bajan y aun así se toman más decisiones por segundo: los MIPS no miden trabajo útil.

## 10. Roofline del core

- **Techo de cómputo:** 1 instrucción cada 2 ciclos = 12,5 MOps/s.
- **Techo de memoria (cargas de datos):** 4 bytes cada 3 ciclos = 33,3 MB/s.
- **Punto de quiebre:** 12,5 / 33,3 = 0,375 operaciones por byte.

| Kernel | Operaciones | Bytes movidos | Intensidad (op/B) | Logrado | Límite |
|---|---|---|---|---|---|
| Solo software (`actualizar` + `D`) | 7 | 12 (2 `lw` + 1 `sw` de 4 B) | 0,58 | 5,1 MOps/s (41 % del techo) | cómputo (a la derecha del quiebre) |
| Variante A (periférico) | 7 | 3 (2 lecturas + 1 escritura de 1 B en su BRAM) | 2,33 | 58 MOps/s | fuera del roofline del core |

En software el kernel está limitado por cómputo, pero solo alcanza el 41 % del techo:
de sus 13 instrucciones, solo 7 operaciones son útiles; el resto calcula direcciones e índices.
El periférico saca el kernel del core: lo ejecuta con su propio hardware, en paralelo con la
espera del core, a un ritmo que el core no puede alcanzar.

## 11. Verificación

| Prueba | Resultado |
|---|---|
| `tb_sma.sv`: D igual al modelo en 20 000 precios | PASS |
| `tb_sma.sv`: D listo 3 ciclos después de cada precio | PASS |
| `tb_sma.sv`: el reinicio borra las sumas y dura 32 ciclos | PASS (32 al encender y al reiniciar) |
| `tb_sma.sv`: precios extremos (D entre −6 096 y +6 096) | PASS |
| Testbench del curso | 4/4 PASS |
| RTL vs Python | decisiones idénticas en los 20 000 ticks |

## 12. Conclusiones

1. La predicción de Amdahl se cumplió exactamente en el RTL: 38,5 ciclos, 1,81×.
2. El periférico cuesta 178 celdas (14 % del chip) y obligó a optimizarlo y a eliminar los LEDs.
3. No cambia la ganancia: las dos variantes cumplen el plazo con margen y toman las mismas decisiones.
4. Lo que queda en la CPU (espera, decisión, escritura) es ahora el 100 % del tick: para seguir
   acelerando habría que reducir la espera (por ejemplo, con interrupciones) o subir la frecuencia.