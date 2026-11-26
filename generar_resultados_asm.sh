#!/bin/bash
# Genera la evidencia de la versión en assembly en resultados/assembly/:
#   - sim_practica.txt          salida del testbench (patrimonio, IC, ciclos, CPI, tests)
#   - decisiones.csv            decisiones del RTL tick a tick
#   - ciclos_por_tick.csv       IC y ciclos de cada tick, medidos en el RTL
#   - decisiones_python.csv     las mismas columnas, calculadas por la versión de referencia
#   - diff_decisiones.txt       comparación de los dos CSV (vacío + "idénticas" = iguales)
#   - emulador_practica.txt     IC, ciclos y CPI del emulador, para contrastar con el RTL
#   - lo mismo para el testbench del botón de reset (*_reset.*)
#
# Correr desde la raíz del repositorio: bash generar_resultados_asm.sh
# NTICKS en tb/tb_proyecto_4.sv debe ser igual a TICKS (20000 = la serie completa).

ASM=resultados/assembly      # carpeta de resultados del assembly
SERIE=tb/practica.csv        # la misma serie que usa el testbench
TICKS=20000                  # igual a NTICKS de tb/tb_proyecto_4.sv
mkdir -p $ASM

# 1. Testbench del curso + comparación con Python
echo "===== Testbench (make sim) ====="
make sim | tee $ASM/sim_practica.txt
cp decisiones.csv ciclos_por_tick.csv $ASM/ 2>/dev/null

echo "===== Emulador y referencia en Python ====="
python3 trading_sim/emular.py sw/trade.hex $SERIE --ticks $TICKS --perfil sw/trade.s | tee $ASM/emulador_practica.txt
mv decisiones_python.csv $ASM/decisiones_python.csv

if diff $ASM/decisiones.csv $ASM/decisiones_python.csv > $ASM/diff_decisiones.txt; then
    echo "Decisiones idénticas en los $TICKS ticks" | tee -a $ASM/diff_decisiones.txt
else
    echo "HAY DIFERENCIAS: revisa $ASM/diff_decisiones.txt"
fi

# 2. Testbench del botón de reset + comparación con Python
echo "===== Testbench del reset (make sim_reset) ====="
make sim_reset | tee $ASM/sim_reset.txt
cp decisiones_reset.csv $ASM/ 2>/dev/null

python3 trading_sim/emular.py sw/trade.hex $SERIE --ticks 2000 --reset 500 > $ASM/emulador_reset.txt
mv decisiones_python.csv $ASM/decisiones_python_reset.csv

if diff $ASM/decisiones_reset.csv $ASM/decisiones_python_reset.csv > $ASM/diff_decisiones_reset.txt; then
    echo "Decisiones con reset idénticas" | tee -a $ASM/diff_decisiones_reset.txt
else
    echo "HAY DIFERENCIAS CON RESET: revisa $ASM/diff_decisiones_reset.txt"
fi

echo "Listo: resultados en $ASM/"
