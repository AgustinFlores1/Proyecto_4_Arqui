# Resumen de la versión solo software (CruceMedias 8/32, margen 2)

Valores **medidos** (testbench del RTL, emulador, yosys/nextpnr) junto a los **teóricos**
(calculados a partir del código de `trade.s` y del modelo de ciclos de Espino).

## 1. Modelo de ciclos de Espino (del RTL)

| Instrucción | Ciclos | Por qué |
|---|---|---|
| Cualquiera | 2 | 1 ciclo esperando los operandos del banco de registros (lectura sincrónica) + 1 ejecutando |
| Carga (`lw`) | 3 | +1: la RAM y el SPI responden un ciclo después |
| Salto tomado (`beq`/`bne`/`blt`/`bge` que salta, `j`) | 3 | +1: se descarta la instrucción ya buscada |
| Salto no tomado, `sw`, aritmética | 2 | — |

    ciclos = 2·IC + cargas + saltos_tomados        CPI = 2 + (cargas + saltos_tomados) / IC

## 2. Costo de cada sección de `trade.s` (teórico)

| Sección | Instrucciones | Cargas | Saltos tomados | Ciclos |
|---|---|---|---|---|
| esperar, vuelta sin precio | 5 | 2 | 1 (`beq`) | 13 |
| esperar, vuelta con precio (+ leer PRICE + display) | 7 | 3 | 0 | 17 |
| actualizar | 13 | 2 | 0 | 28 |
| calentar, durante el calentamiento | 5 | 0 | 1 (`blt`) | 11 |
| calentar, después del calentamiento | 3 | 0 | 1 (`bge`) | 7 |
| decidir, sin acciones → mantener | 6 | 0 | 2 | 14 |
| decidir, sin acciones → comprar | 8 | 0 | 1 | 17 |
| decidir, con acciones → mantener | 6 | 0 | 1 | 13 |
| decidir, con acciones → vender | 9 | 0 | 1 (`j`) | 19 |
| escribir | 3 | 0 | 1 (`j`) | 7 |

## 3. Costo de cada camino completo por tick (teórico)

Desde el primer `lw` de la espera hasta el `j esperar`, con el precio detectado en la primera vuelta:

| Camino | IC | Ciclos | CPI |
|---|---|---|---|
| Calentamiento (primeros 31 ticks) | 28 | 63 | 2,25 |
| Sin acciones → mantener (el más común) | 32 | 73 | 2,28 |
| Con acciones → mantener | 32 | 72 | 2,25 |
| Comprar | 34 | 76 | 2,24 |
| Vender (el más largo) | 35 | 78 | 2,23 |

## 4. Teórico vs medido por tick

| Valor | Teórico | Emulador | RTL (testbench) |
|---|---|---|---|
| IC promedio | ~32 (casi todos los ticks mantienen) | 32,0 | 31,2 |
| IC máximo | 35 (vender) + hasta 2 de una vuelta perdida = 37 | 35 | **37** |
| Ciclos promedio | 72–73 menos la parte de la espera ya hecha | 72,5 | **69,5** |
| Ciclos peor caso | 78 (vender) + ~5 de una vuelta perdida ≈ 83 | 78 | **81** |
| CPI | 2,23–2,28 según el camino | 2,27 | **2,23** |

- El emulador entrega el precio siempre al inicio de la espera: coincide exactamente con los caminos teóricos.
- En el RTL el precio llega en cualquier punto de la vuelta de espera. Si llega justo antes de leer STATUS, el tick cuesta hasta 5 ciclos menos (promedio más bajo). Si llega justo después, hay que terminar la vuelta y dar otra (peor caso más alto).
- Todo lo que no es espera (55,5 ciclos en promedio) es idéntico en el RTL; la espera en el RTL promedia 69,5 − 55,5 = 14 ciclos.

## 5. Plazo de cada ronda

| Ronda | T | Plazo = (T − 9,5 µs) / 40 ns | Instrucciones posibles (plazo / CPI 2,23) | Uso medido promedio (69,5 ciclos = 2,78 µs) | Uso medido peor caso (81 ciclos = 3,24 µs) |
|---|---|---|---|---|---|
| 1 | 10 ms | 249 762 ciclos | ~112 000 | 0,028 % | 0,032 % |
| 2 | 1 ms | 24 762 ciclos | ~11 100 | 0,28 % | 0,33 % |
| 3 | 0,1 ms | 2 262 ciclos | ~1 014 | 3,1 % | **3,6 %** |

El enunciado estima ~1 060 instrucciones en la ronda 3 con CPI 2,35 y sin descontar la transacción SPI.
El peor tick usa 37 de las ~1 014 posibles: un margen de ~28 veces.

## 6. Rendimiento del core

| Valor | Teórico | Medido |
|---|---|---|
| Instrucciones por segundo, máximo (CPI = 2) | 25 MHz / 2 = 12,5 MIPS | — |
| Instrucciones por segundo mientras calcula | 25 MHz / CPI | 25 / 2,23 = 11,2 MIPS |

## 7. Perfil por sección (emulador, promedio por tick)

| Sección | IC | Ciclos | % |
|---|---|---|---|
| esperar | 7,0 | 17,0 | 23,4 % |
| **actualizar** | 13,0 | 28,0 | **38,6 %** |
| calentar | 3,0 | 7,0 | 9,7 % |
| decidir | 6,0 | 13,5 | 18,6 % |
| escribir | 3,0 | 7,0 | 9,7 % |
| total | 32,0 | 72,5 | |

Coincide con los valores teóricos de la sección 2 (actualizar 28, calentar 7, escribir 7,
decidir 13–14 según si tiene acciones).

## 8. Recursos de la FPGA (iCE40 HX1K)

| Recurso | Teórico mínimo | Medido | Libre |
|---|---|---|---|
| Celdas lógicas (`ICESTORM_LC`) | — | **1 068 / 1 280 (83 %)** | 212 |
| BRAM (`SB_RAM40_4K`) | RAM 512 × 32 bits = 16 Kbit = 4 bloques | 12 / 16 (75 %) | 4 |
| LUTs (yosys) | — | 891 | — |
| Flip-flops (yosys) | — | 258 | — |
| Cadenas de acarreo (yosys) | — | 153 | — |
| Frecuencia máxima | ≥ 25 MHz | **44,14 MHz** | margen del 77 % |

## 9. Algoritmo (versión de referencia en Python, 8 series)

| Trader | Gana a B&H | Promedio vs B&H | Promedio vs no operar | Pérdida máx. promedio | Estrés (vs no operar) |
|---|---|---|---|---|---|
| **CruceMedias (elegido)** | **8/8** | **+3 873** | **+3 553** | 4 282 | **−133** |
| TomaGanancia 7/5/10 | 8/8 | +3 536 | +3 216 | 3 652 | −773 |
| RSIFijo 46 4/14 | 8/8 | +660 | +340 | 8 976 | −3 462 |
| No operar | 6/8 | +321 | 0 | 0 | — |

En `practica.csv` (RTL = Python): patrimonio 13 881, 124 órdenes, 620 de comisiones,
pérdida máxima 3 950. Comprar y mantener: 9 695.

## 10. Verificación

| Prueba | Resultado |
|---|---|
| RTL vs Python, 20 000 ticks | decisiones idénticas (`diff` vacío) |
| Testbench del curso | 4/4 PASS |
| Testbench del reset | 5/5 PASS (primera orden tras el reset: comprar, `7f`) |
| Prueba con la FPGA maestra | funcionó |

## 11. Predicciones de Amdahl para el co-diseño (teóricas)

    speedup = 1 / ((1 − f) + f / s)        máximo = 1 / (1 − f)

| Variante | Qué acelera | f | Ciclos predichos | Speedup predicho | Máximo |
|---|---|---|---|---|---|
| A: periférico de media móvil | actualizar (28) + cálculo de D (6); agrega 1 `lw` (3) | 0,47 | ~41,5 | ~1,75× | 1,88× |
| B: custom-0 (`upd`, `dif`) | 2 pares sub+add (8 → 4) + cálculo de D (6 → 2) | 0,19 | ~64,5 | ~1,12× | — |

Ninguna de las dos acelera la espera, la decisión ni la escritura: el tick no baja de ~38 ciclos.
