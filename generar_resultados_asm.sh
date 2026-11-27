#!/bin/bash
# Genera la evidencia de una versión del assembly:
#   - sim_practica.txt          salida del testbench (patrimonio, IC, ciclos, CPI, tests)
#   - decisiones.csv            decisiones del RTL tick a tick
#   - ciclos_por_tick.csv       IC y ciclos de cada tick, medidos en el RTL
#   - sim_reset.txt             salida del testbench del botón de reset
#   - yosys.log, nextpnr.log    síntesis y place & route
#   - recursos.txt              celdas lógicas, BRAM y frecuencia máxima
#   - metricas.txt              IC, ciclos, CPI, tiempo, decisiones/s, MIPS y uso del plazo de cada ronda
#   Solo para la versión base (sw/trade.s), la comparación con Python:
#   - decisiones_python.csv     las mismas columnas, calculadas por la versión de referencia
#   - diff_decisiones.txt       comparación de los dos CSV (vacío + "idénticas" = iguales)
#   - emulador_practica.txt     IC, ciclos, CPI y perfil por sección del emulador
#   - lo mismo con reset (*_reset.*)
#
# Correr desde la raíz del repositorio:
#   bash generar_resultados_asm.sh                                              -> solo software
#   bash generar_resultados_asm.sh sw/trade_sma.s resultados/variante_a         -> variante A
#   bash generar_resultados_asm.sh sw/trade_custom.s resultados/variante_b      -> variante B
# NTICKS en tb/tb_proyecto_4.sv debe ser igual a TICKS (20000 = la serie completa).

PROGRAMA=${1:-sw/trade.s}         # primer argumento, o sw/trade.s si no se da
ASM=${2:-resultados/assembly}     # segundo argumento, o resultados/assembly si no se da
HEX=${PROGRAMA%.s}.hex            # sw/trade.s -> sw/trade.hex, sw/trade_sma.s -> sw/trade_sma.hex
SERIE=tb/practica.csv             # la misma serie que usa el testbench
TICKS=20000                       # igual a NTICKS de tb/tb_proyecto_4.sv

case $PROGRAMA in                 # el hardware que necesita cada programa
    sw/trade_sma.s)    DEF=-DUSAR_SMA ;;      # variante A
    sw/trade_custom.s) DEF=-DUSAR_CUSTOM ;;   # variante B
    *)                 DEF= ;;                # solo software
esac
mkdir -p $ASM

# 0. Ensamblar el programa
python3 tools/assembler.py $PROGRAMA -o $HEX

# 1. Testbench del curso
echo "===== Testbench (make sim) ====="
make sim SS=$PROGRAMA HEX=$HEX DEF=$DEF | tee $ASM/sim_practica.txt
mv decisiones.csv ciclos_por_tick.csv $ASM/ 2>/dev/null

if [ "$PROGRAMA" = "sw/trade.s" ]; then
    echo "===== Emulador y referencia en Python ====="
    python3 trading_sim/emular.py $HEX $SERIE --ticks $TICKS --perfil $PROGRAMA | tee $ASM/emulador_practica.txt
    mv decisiones_python.csv $ASM/decisiones_python.csv

    if diff $ASM/decisiones.csv $ASM/decisiones_python.csv > $ASM/diff_decisiones.txt; then
        echo "Decisiones idénticas en los $TICKS ticks" | tee -a $ASM/diff_decisiones.txt
    else
        echo "HAY DIFERENCIAS: revisa $ASM/diff_decisiones.txt"
    fi
fi

# 2. Testbench del botón de reset
echo "===== Testbench del reset (make sim_reset) ====="
make sim_reset SS=$PROGRAMA HEX=$HEX DEF=$DEF | tee $ASM/sim_reset.txt
mv decisiones_reset.csv $ASM/ 2>/dev/null

if [ "$PROGRAMA" = "sw/trade.s" ]; then
    python3 trading_sim/emular.py $HEX $SERIE --ticks 2000 --reset 500 > $ASM/emulador_reset.txt
    mv decisiones_python.csv $ASM/decisiones_python_reset.csv

    if diff $ASM/decisiones_reset.csv $ASM/decisiones_python_reset.csv > $ASM/diff_decisiones_reset.txt; then
        echo "Decisiones con reset idénticas" | tee -a $ASM/diff_decisiones_reset.txt
    else
        echo "HAY DIFERENCIAS CON RESET: revisa $ASM/diff_decisiones_reset.txt"
    fi
fi

# 3. Síntesis y place & route
echo "===== Síntesis (yosys) y place & route (nextpnr) ====="
rm -f pochoco_soc.json pochoco_soc.asc       # obliga a sintetizar de nuevo
make pochoco_soc.json SS=$PROGRAMA HEX=$HEX DEF=$DEF > $ASM/yosys.log 2>&1
make pochoco_soc.asc SS=$PROGRAMA HEX=$HEX DEF=$DEF > $ASM/nextpnr.log 2>&1

grep -E "SB_LUT4|SB_DFF|SB_CARRY|SB_RAM40_4K" $ASM/yosys.log | tail -9 > $ASM/recursos.txt
grep -E "ICESTORM_LC:|ICESTORM_RAM:" $ASM/nextpnr.log | tail -2 >> $ASM/recursos.txt
grep -E "Max frequency for clock" $ASM/nextpnr.log | tail -1 >> $ASM/recursos.txt
cat $ASM/recursos.txt

# 4. Métricas calculadas a partir del testbench (reloj de 25 MHz = 40 ns por ciclo)
awk '
/IC por tick/     { gsub(",", "", $5); ic_prom = $5; ic_peor = $8 }
/Ciclos por tick/ { gsub(",", "", $5); cy_prom = $5; cy_peor = $8 }
/^CPI/            { cpi = $2 }
END {
    printf "IC por tick:              promedio %s, peor caso %s\n", ic_prom, ic_peor
    printf "Ciclos por tick:          promedio %s, peor caso %s\n", cy_prom, cy_peor
    printf "CPI:                      %s\n", cpi
    printf "Tiempo por tick:          promedio %.2f us, peor caso %.2f us\n", cy_prom * 0.04, cy_peor * 0.04
    printf "Decisiones por segundo:   %.0f (25 MHz / ciclos promedio)\n", 25000000 / cy_prom
    printf "MIPS del core:            %.2f (25 MHz / CPI)\n", 25 / cpi
    printf "Uso del plazo, peor caso: ronda 1 %.3f%%, ronda 2 %.2f%%, ronda 3 %.1f%%\n", \
           100 * cy_peor / 249762, 100 * cy_peor / 24762, 100 * cy_peor / 2262
}' $ASM/sim_practica.txt | tee $ASM/metricas.txt

echo "Listo: resultados en $ASM/"