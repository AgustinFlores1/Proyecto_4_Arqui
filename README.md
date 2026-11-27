# Pochoco Trader

Agente de inversión para el Proyecto 4 de Arquitectura de Computadores: un programa en
assembly RV32E que corre en el **Pochoco SoC** (core **Espino**) sobre la **Nandland Go Board**
(iCE40HX1K). Una FPGA maestra envía por SPI el precio de una acción en cada tick, y el
programa responde si compra, vende o mantiene.

El proyecto parte del [repositorio base del curso](https://github.com/nic0villegasc/pochoco_soc).
La descripción original del SoC está en la sección [Pochoco SoC y Espino Core](#pochoco-soc-y-espino-core).

## Algoritmo: cruce de medias móviles

Se eligió **CruceMedias 8/32 con margen 2** después de comparar 15 algoritmos en Python
(`trading_sim/`), calibrando con 5 series y verificando con 3 series reservadas.

- `S_c` = suma de los últimos 8 precios, `S_l` = suma de los últimos 32.
- `D = 4·S_c − S_l` (equivale a `32 · (media corta − media larga)`, sin divisiones).
- Compra 63 acciones si `D > 64` y no tiene acciones; vende todas si `D < −64` y tiene.
- Los primeros 32 ticks solo mantiene (calentamiento).

En `tb/practica.csv`: patrimonio final **13 881** (comprar y mantener: 9 695; no operar: 10 000),
124 órdenes, pérdida máxima 3 950.

## Versiones del hardware

Se implementaron dos alternativas de co-diseño, además de la versión solo software.
Cada una se activa con una macro de Verilog (`DEF`) al sintetizar o simular:

| Versión | Programa | `DEF` | Ciclos por tick (prom. / peor) | Celdas lógicas | Speedup |
|---|---|---|---|---|---|
| **Solo software (versión final)** | `sw/trade.s` | (vacío) | 69,5 / 81 | 1 068 / 1 280 (83 %) | 1× |
| A: periférico de media móvil | `sw/trade_sma.s` | `-DUSAR_SMA` | 38,5 / 50 | 1 241 / 1 280 (96 %) | 1,81× |
| B: instrucciones custom-0 | `sw/trade_custom.s` | `-DUSAR_CUSTOM` | 61,5 / 73 | 1 112 / 1 280 (86 %) | 1,13× |

**Versión final: solo software.** Las tres toman exactamente las mismas decisiones y cumplen el
plazo de la ronda más exigente (0,1 ms = 2 262 ciclos) con mucho margen: el peor tick de la
versión solo software usa el 3,6 % del plazo. Como la maestra ejecuta cada decisión en el tick
siguiente, responder más rápido no cambia la ganancia, así que se mantiene el Pochoco sin cambios.

- **Variante A** (`rtl/pochoco_sma.v`): un periférico dentro del SPI slave que, al llegar cada
  precio, actualiza en hardware el buffer de 32 precios (en un bloque BRAM) y las dos sumas, y
  entrega `D` en el registro `0x8001_000C`. La CPU solo lee `D` y decide.
- **Variante B** (`rtl/espino_core/espino_decoder.v`, `espino_alu.v`): dos instrucciones nuevas
  en el opcode custom-0 (`0x0B`):

  | Instrucción | Formato | Operación | Reemplaza |
  |---|---|---|---|
  | `dif rd, rs1, rs2` | R, funct3 `000` | `rd = 4·rs1 − rs2` | `add` + `add` + `sub` |
  | `circ rd, rs1, imm` | I, funct3 `001` | `rd = (rs1 + imm) AND 0x7C` | `addi` + `andi` |

Los resultados completos están en `resultados/assembly/resumen.md`,
`resultados/variante_a/resumen.md` y `resultados/variante_b/resumen.md`.

## Estructura del repositorio

```
rtl/                    Pochoco SoC y core Espino (Verilog)
  pochoco_sma.v           variante A: periférico de media móvil
  pochoco_spi_slave.v     SPI slave (incluye el periférico con USAR_SMA)
  pochoco_periph.v        display, LEDs (eliminados) y botones
  espino_core/            core Espino (decoder y ALU con las instrucciones de la variante B)
sw/
  trade.s                 versión final (solo software)
  trade_sma.s             variante A
  trade_custom.s          variante B
tb/
  tb_proyecto_4.sv        testbench del curso (emula a la FPGA maestra) + IC y ciclos por tick
  tb_reset.sv             botón de reset a mitad de la serie
  tb_sma.sv               variante A: periférico de media móvil
  tb_custom.sv            variante B: decodificador + ALU de las instrucciones custom-0
  practica*.csv           series de calibración; reservadas/ = series de verificación
tools/assembler.py      ensamblador RV32E (incluye dif y circ)
trading_sim/            versión de referencia en Python (algoritmos, mercado, emulador)
resultados/             evidencia del informe (salidas, gráficos, resúmenes)
generar_resultados_asm.sh   genera la evidencia de una versión del assembly
```

## Herramientas

Versiones usadas (macOS, Apple Silicon):

| Herramienta | Versión |
|---|---|
| [OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build) | Yosys 0.68+130 (git sha1 dd83bbad2) |
| nextpnr-ice40 | nextpnr-0.11.1-13-gbc1aec33 |
| Icarus Verilog | 14.0 (devel) (s20260301-391-g64f13540a) |
| Python | 3.11.6 (con matplotlib, ver `requirements.txt`) |

### Instalación

1. **OSS CAD Suite** (yosys, nextpnr, icepack, iceprog, iverilog): descargar la versión para
   el sistema desde la página de releases, extraerla y cargar su entorno en cada terminal:
   ```bash
   source <ruta>/oss-cad-suite/environment
   ```
   En macOS, la primera vez hay que quitar la cuarentena con `./activate` dentro de la carpeta.

2. **Python** (solo para `trading_sim/`): desde la raíz del repositorio,
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   Si el entorno de OSS CAD Suite está cargado, `python3` es el de ese paquete: crear el `.venv`
   con el Python del sistema (`/usr/bin/python3 -m venv .venv`). Una vez activado el `.venv`,
   sus `python` y `pip` tienen prioridad.

## Ensamblar

```bash
python3 tools/assembler.py sw/trade.s -o sw/trade.hex      # o: make asm
```

El ensamblador (`tools/assembler.py`) acepta registros `x0`–`x15`, las pseudoinstrucciones
`j`, `mv` y `nop`, y las instrucciones `dif` y `circ` de la variante B. No acepta shifts:
en Espino están deshabilitados y ejecutan una suma.

## Sintetizar y programar la placa

Versión final (solo software):
```bash
make all
```

Otra versión: indicar el programa, su `.hex` y el `DEF`, y borrar la síntesis anterior para
que `make` no la reutilice:
```bash
rm -f pochoco_soc.json pochoco_soc.asc
make all SS=sw/trade_sma.s HEX=sw/trade_sma.hex DEF=-DUSAR_SMA          # variante A
make all SS=sw/trade_custom.s HEX=sw/trade_custom.hex DEF=-DUSAR_CUSTOM # variante B
```

`make all` ensambla, sintetiza (yosys), hace place and route (nextpnr, a 25 MHz), genera el
bitstream (icepack) y programa la placa (iceprog). El programa queda dentro del bitstream y se
guarda en la flash de la Go Board.

**Conexión con la maestra** (PMOD, ver `goboard.pcf`): CS_n pin 65, MOSI 64, MISO 63, SCLK 62,
y **tierra común**. El display muestra el último precio en hexadecimal.

**Botón de reset:** cualquier botón reinicia el programa (buffer, sumas, calentamiento y flag
de acciones). Hay que presionarlo entre rondas, porque la maestra reinicia su contabilidad
pero el SoC no se entera.

## Testbenches

Desde la raíz del repositorio:

| Comando | Qué prueba |
|---|---|
| `make sim` | Testbench del curso con `tb/practica.csv`: patrimonio, órdenes, IC, ciclos y CPI por tick, y 4 tests. Escribe `decisiones.csv` y `ciclos_por_tick.csv` |
| `make sim_reset` | Presiona un botón en el tick 500 y revisa que el programa olvide su estado (5 tests) |
| `make sim_sma` | Variante A: el periférico solo, comparado con un modelo de referencia en 20 000 precios (4 tests) |
| `make sim_custom` | Variante B: `dif` y `circ` en el decodificador y la ALU (3 tests) |

`make sim` y `make sim_reset` aceptan las mismas variables que la síntesis. Por ejemplo:
```bash
make sim SS=sw/trade_sma.s HEX=sw/trade_sma.hex DEF=-DUSAR_SMA
```

La simulación de la serie completa (`NTICKS = 20000` en `tb/tb_proyecto_4.sv`) simula 2 s de
funcionamiento (50 millones de ciclos) y tarda varios minutos.

### Generar toda la evidencia de una versión

```bash
bash generar_resultados_asm.sh                                          # solo software -> resultados/assembly
bash generar_resultados_asm.sh sw/trade_sma.s resultados/variante_a     # variante A
bash generar_resultados_asm.sh sw/trade_custom.s resultados/variante_b  # variante B
```

Corre los dos testbenches, la síntesis y el place and route, y guarda las salidas, los CSV por
tick, los logs y `recursos.txt` (celdas lógicas, BRAM y frecuencia máxima). En la versión solo
software además compara las decisiones del RTL con las de Python
(`diff_decisiones.txt`: idénticas en los 20 000 ticks).

## Versión de referencia en Python

Con el `.venv` activado, desde `trading_sim/`:

| Comando | Qué hace |
|---|---|
| `python main.py` | Corre los tres candidatos finales (RSIFijo, CruceMedias, TomaGanancia) y las referencias en todas las series, y guarda un gráfico por serie |
| `python probar.py` | Compara todos los algoritmos con sus parámetros por defecto en las series de calibración |
| `python probar.py --barrido CruceMedias --reservar 0 --series --graficar 5` | Barrido de parámetros (grilla en `GRILLAS`) en las series de calibración, y verificación de los 5 mejores en `tb/reservadas/` |
| `python tabla_final.py` | Tabla final: patrimonio, órdenes, comisiones y pérdida máxima de los candidatos en las 8 series, más una prueba de estrés |
| `python emular.py ../sw/trade.hex ../tb/practica.csv --perfil ../sw/trade.s` | Emula `trade.s` en un modelo de Espino, compara sus decisiones con Python y muestra el perfil de ciclos por sección |
| `python roofline.py` | Gráfico roofline del kernel de media móvil en las tres versiones (`resultados/roofline.png`) |
| `bash generar_resultados.sh` | Regenera todos los barridos y la comparación de candidatos en `resultados/python/` |

El algoritmo elegido está en `trading_sim/algorithms/cruce_medias.py`. `emular.py` también
acepta `--ticks N` (solo los primeros N ticks) y `--reset T` (presiona el botón después del tick T).

---

## Pochoco SoC y Espino Core

Descripción del SoC base del curso, con los cambios de este proyecto.

### Mapa de memoria

* **`0x0000_0000` - RAM unificada** (512 palabras): programa y datos.
* **`0x8000_0000` - Periféricos de la placa**
  * `Offset 0x00`: display de 7 segmentos (muestra un byte en hexadecimal)
  * `Offset 0x04`: LEDs (eliminados en este proyecto para liberar celdas lógicas; siempre apagados)
  * `Offset 0x08`: botones
* **`0x8001_0000` - SPI slave**
  * `Offset 0x00`: STATUS. Bit 0: precio nuevo sin leer; bit 1: CS activo; bit 2: periférico de media móvil ocupado
  * `Offset 0x04`: PRICE, el último precio recibido (leerlo baja el bit "precio nuevo")
  * `Offset 0x08`: DECISION, el byte que la maestra lee en la próxima transacción
  * `Offset 0x0C`: SMA (variante A). Leer: `D = 4·S_c − S_l` con signo; escribir: reiniciar el periférico. Sin `USAR_SMA` se lee como 0

### Espino Core

Implementa [RV32E](https://docs.riscv.org/reference/isa/v20260120/unpriv/rv32.html): 16 registros,
sin multiplicación ni división. Las instrucciones de desplazamiento (`SLL`/`SRL`/`SRA`/`SLLI`/`SRLI`/`SRAI`)
se decodifican pero están deshabilitadas en la ALU para ahorrar LUTs, y ejecutan `ADD`.
Cada instrucción toma 2 ciclos (el banco de registros tiene lectura sincrónica); las cargas y
los saltos tomados, 3.

Con `USAR_CUSTOM` el core acepta además `dif` y `circ` (variante B).
