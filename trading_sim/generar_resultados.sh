#!/bin/bash
# Regenera todos los resultados de Python en ../resultados/python/:
#   - barridos/<algoritmo>/   barrido_<algoritmo>.txt + graficos/ (un gráfico por serie reservada)
#   - candidatos/             comparación de RSIFijo, CruceMedias y TomaGanancia + un gráfico por serie
# y el roofline en ../resultados/roofline.png.
# Correr desde trading_sim/, con el .venv activado: bash generar_resultados.sh

BARRIDOS=../resultados/python/barridos
CANDIDATOS=../resultados/python/candidatos

ALGORITMOS="RSIFijo A2Solo BSolo BCalentamiento A2BRespaldo A2BReagrupada CruceMedias Breakout DesviacionMedia BandasDesviacion Patrones LMS Rachas TomaGanancia Lotes"

for alg in $ALGORITMOS; do
    echo "===== Barrido $alg ====="
    rm -rf graficos_barrido/$alg $BARRIDOS/$alg          # borra los gráficos de corridas anteriores
    mkdir -p $BARRIDOS/$alg/graficos
    python -u probar.py --barrido $alg --reservar 0 --series --graficar 6 | tee $BARRIDOS/$alg/barrido_$alg.txt
    cp graficos_barrido/$alg/*.png $BARRIDOS/$alg/graficos/ 2>/dev/null
done

echo "===== Candidatos ====="
rm -rf $CANDIDATOS
mkdir -p $CANDIDATOS
python -u main.py | tee $CANDIDATOS/comparacion_candidatos.txt
python -u tabla_final.py > /dev/null                   # tabla_final.md y .csv

echo "===== Roofline ====="
python -u roofline.py

echo "Listo: resultados en ../resultados/"