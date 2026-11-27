# Variante B: instrucciones custom-0

## 1. Qué cambió

| | Solo software | Variante B |
|---|---|---|
| Cálculo de `D = 4·S_c − S_l` | `add` + `add` + `sub` (3 instrucciones) | `dif x7, x14, x15` (1 instrucción) |
| Índice del buffer circular (2 veces por tick) | `addi` + `andi` (2 instrucciones) | `circ rd, rs1, imm` (1 instrucción) |
| Programa | `trade.s`, 57 instrucciones | `trade_custom.s`, 53 instrucciones |
| Hardware | — | decodificador: opcode custom-0 (`0x0B`); ALU: `ALU_DIF` y `ALU_CIRC`; operador de 4 a 5 bits |

| Instrucción | Formato | Codificación | Operación |
|---|---|---|---|
| `dif rd, rs1, rs2` | R | opcode `0x0B`, funct3 `000`, funct7 `0000000` | `rd = 4·rs1 − rs2` |
| `circ rd, rs1, imm` | I | opcode `0x0B`, funct3 `001` | `rd = (rs1 + imm) AND 0x7C` |

La primera idea (`upd rd, rs1, rs2`: `rd = rd + rs1 − rs2`) se descartó porque necesita leer
tres registros, y el banco de registros de Espino solo tiene dos puertos de lectura.

## 2. Costo de las secciones que cambian (teórico)

| Sección | Solo software | Variante B |
|---|---|---|
| actualizar | 13 instrucciones, 28 ciclos | 11 instrucciones, 24 ciclos |
| decidir (cálculo de D) | 3 instrucciones, 6 ciclos | 1 instrucción, 2 ciclos |
| resto del tick | igual | igual |

## 3. Caminos completos por tick (teórico)

| Camino | IC | Ciclos | Solo software (ciclos) |
|---|---|---|---|
| Calentamiento | 26 | 59 | 63 |
| Sin acciones → mantener | 28 | 65 | 73 |
| Con acciones → mantener | 28 | 64 | 72 |
| Comprar | 30 | 68 | 76 |
| Vender (el más largo) | 31 | 70 | 78 |

## 4. Predicción de Amdahl vs medido

    speedup = 1 / ((1 − f) + f / s)

Parte afectada: 2 pares `addi`+`andi` (8 ciclos → 4) y el cálculo de D (6 ciclos → 2): 14 ciclos → 6.

| | Base emulador (72,5) | Base RTL (69,5) |
|---|---|---|
| f | 14 / 72,5 = 0,19 | 14 / 69,5 = 0,20 |
| s | 14 / 6 = 2,33 | 2,33 |
| Ciclos predichos | 64,5 | **61,5** |
| Speedup predicho | 1,12× | 1,13× |
| **Medido** | 64,5 (emulador) | **61,5 (RTL)** |

**El RTL coincide exactamente con la predicción**, igual que en la variante A.

## 5. Valores medidos en el RTL (testbench, 20 000 ticks)

| Valor | Solo software | Variante B | Cambio |
|---|---|---|---|
| IC promedio | 31,2 | **27,2** | −4 instrucciones |
| IC peor caso | 37 | **33** | −4 |
| Ciclos promedio | 69,5 | **61,5** | −8 (1,13×) |
| Ciclos peor caso | 81 | **73** | −8 (1,11×) |
| CPI | 2,23 | **2,26** | se eliminaron instrucciones de 2 ciclos |
| Tiempo promedio por tick | 2,78 µs | 2,46 µs | |
| Tiempo peor caso por tick | 3,24 µs | 2,92 µs | |
| Patrimonio / órdenes / pérdida máx. | 13 881 / 124 / 3 950 | 13 881 / 124 / 3 950 | igual |

Teórico vs medido: el ahorro es exactamente 4 instrucciones y 8 ciclos en todos los caminos
después del calentamiento, así que el promedio y el peor caso bajan los dos en 8 ciclos.

## 6. Plazo de cada ronda (peor caso)

| Ronda | Plazo | Solo software | Variante B |
|---|---|---|---|
| 1 (10 ms) | 249 762 ciclos | 0,032 % | 0,029 % |
| 2 (1 ms) | 24 762 ciclos | 0,33 % | 0,29 % |
| 3 (0,1 ms) | 2 262 ciclos | 3,6 % | **3,2 %** |

## 7. Recursos (iCE40 HX1K)

| Recurso | Solo software | Variante B | Diferencia |
|---|---|---|---|
| Celdas lógicas | 1 068 (83 %) | **1 112 (86 %)** | **+44** |
| BRAM | 12 | 12 | 0 |
| LUTs (yosys) | 891 | 943 | +52 |
| Flip-flops (yosys) | 258 | 254 | ≈ igual |
| Cadenas de acarreo | 153 | 183 | +30 (el restador de 32 bits de `dif`) |
| Frecuencia máxima | 44,14 MHz | 44,04 MHz | igual |

- `circ` reutiliza el sumador de `add` (yosys une las dos sumas iguales): solo agrega la máscara.
- `dif` necesita un restador propio, porque resta `4·a − b` y no `a − b`: son las 30 cadenas de acarreo extra.
- **Costo por ciclo ahorrado:** 44 celdas / 8 ciclos = 5,5 celdas por ciclo.

## 8. Verificación

| Prueba | Resultado |
|---|---|
| `tb_custom.sv`: `dif` en 20 000 casos (incluye resultados negativos) | PASS |
| `tb_custom.sv`: `circ` en los 32 índices × 7 inmediatos (incluye negativos) | PASS |
| `tb_custom.sv`: funct3 no usado es ilegal; `add` sigue igual | PASS |
| Testbench del curso | 4/4 PASS, mismo patrimonio y órdenes que la versión base |
| Testbench del reset | 5/5 PASS |
| Emulador vs Python | decisiones idénticas en las 8 series |

## 9. Comparación de las tres versiones

| | Solo software | Variante A (periférico) | Variante B (custom-0) |
|---|---|---|---|
| Ciclos promedio / peor caso | 69,5 / 81 | **38,5 / 50** | 61,5 / 73 |
| Speedup medido (promedio) | 1× | **1,81×** | 1,13× |
| Speedup predicho por Amdahl | — | 1,81× | 1,13× |
| CPI | 2,23 | 2,37 | 2,26 |
| Instrucciones del programa | 57 | 32 | 53 |
| Celdas lógicas | 1 068 (83 %) | 1 241 (96 %) | 1 112 (86 %) |
| BRAM | 12 | 13 | 12 |
| Frecuencia máxima | 44,1 MHz | 45,5 MHz | 44,0 MHz |
| Celdas por ciclo ahorrado | — | 5,7 | 5,5 |
| Decisiones por segundo (máx.) | 360 mil | 649 mil | 407 mil |
| Uso del plazo, ronda 3 (peor caso) | 3,6 % | 2,2 % | 3,2 % |
| Patrimonio (practica.csv) | 13 881 | 13 881 | 13 881 |

- Las dos predicciones de Amdahl se cumplieron exactamente.
- Las dos variantes cuestan casi lo mismo por ciclo ahorrado (~5,5 celdas): A ahorra más
  ciclos porque acelera una fracción mayor del tick (49 % contra 20 %).
- Ninguna cambia la ganancia: las tres cumplen el plazo con mucho margen y toman las mismas decisiones.
