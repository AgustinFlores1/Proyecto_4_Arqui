#!/bin/bash
# Regenera todos los resultados del informe en ../resultados/:
#   - un barrido por algoritmo de GRILLAS (resultados/<algoritmo>/barrido_<algoritmo>.txt + gráficos)
#   - la comparación de los tres candidatos (resultados/candidatos/)
# Correr desde trading_sim/, con el .venv activado: bash generar_resultados.sh

BARRIDOS=../resultados/python/barridos
CANDIDATOS=../resultados/python/candidatos

ALGORITMOS="RSIFijo A2Solo BSolo BCalentamiento A2BRespaldo A2BReagrupada CruceMedias Breakout DesviacionMedia BandasDesviacion Patrones LMS Rachas TomaGanancia Lotes"

for alg in $ALGORITMOS; do
    echo "===== Barrido $alg ====="
    mkdir -p $BARRIDOS/$alg
    python -u probar.py --barrido $alg --reservar 0 --series --graficar 6 | tee $BARRIDOS/$alg/barrido_$alg.txt
    cp -r graficos_barrido/$alg $BARRIDOS/$alg/graficos 2>/dev/null
done

echo "===== Candidatos ====="
mkdir -p $CANDIDATOS
python -u main.py | tee $CANDIDATOS/comparacion_candidatos.txt

python -u tabla_final.py > /dev/null

echo "Listo: resultados en ../resultados/"