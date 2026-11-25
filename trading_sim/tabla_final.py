"""
Tabla final del informe: compara el algoritmo elegido y los otros dos finalistas
con las dos referencias que pide el enunciado (no operar y comprar y mantener),
en todas las series de tb/ y tb/reservadas/.

Por cada serie y trader reporta las cuatro métricas del enunciado:
patrimonio final, órdenes, comisiones pagadas y pérdida máxima desde un peak.
Después agrega un resumen por trader y la prueba de estrés (series cortadas en
su mínimo, el peor final posible para quien mantiene acciones).

Uso (desde trading_sim/):
    python tabla_final.py
Escribe resultados/python/candidatos/tabla_final.md y tabla_final.csv (la carpeta se crea si no existe).
"""
from pathlib import Path

from market import Market
from trader import Trader
from algorithms.rsi_fijo import RSIFijo
from algorithms.cruce_medias import CruceMedias
from algorithms.toma_ganancia import TomaGanancia

CAJA0 = 10000                                                     # caja inicial
COMISION = 5                                                      # comisión por orden
RAIZ = Path(__file__).resolve().parent.parent                     # raíz del repositorio
TB = RAIZ / "tb"                                                  # series de calibración
RESERVADAS = TB / "reservadas"                                    # series reservadas
SALIDA = RAIZ / "resultados" / "python" / "candidatos"            # carpeta donde se guardan las tablas

FINALISTAS = [                                                    # (nombre en la tabla, clase, parámetros elegidos)
    ("CruceMedias 8/32 m2 (elegido)", CruceMedias, dict(N_corta=8, N_larga=32, margen=2)),
    ("TomaGanancia 7/5/10", TomaGanancia, dict(umbral=7, caida=5, recompra=10)),
    ("RSIFijo 46 4/14", RSIFijo, dict(N=46, bajo=4, alto=14)),
]


def encontrar_series(carpeta: Path) -> list[Path]:  # CSV con encabezado "tick,price"
    return [r for r in sorted(carpeta.glob("*.csv"))
            if open(r).readline().strip().replace(" ", "") == "tick,price"]


def cargar(ruta: Path) -> list[int]:  # precios de una serie
    return [int(l.split(",")[1]) for l in open(ruta).read().split()[1:]]


def metricas_trader(clase, params: dict, precios: list[int]) -> dict:  # corre un trader y devuelve sus métricas
    m = Market(COMISION, CAJA0)
    t = clase("t", CAJA0, COMISION, **params) if clase is not Trader else Trader("t", CAJA0, COMISION)
    m.insert_trader(t)
    m.stock_prices = precios
    m.run_sim()
    return {"patrimonio": t.wealth, "ordenes": t.orders,
            "comisiones": t.orders * COMISION, "perdida_max": t.max_wealth_drop}


def metricas_bh(precios: list[int]) -> dict:  # comprar y mantener con la fórmula del testbench (compra todo lo que alcanza en el tick 0)
    q = (CAJA0 - COMISION) // precios[0]                          # acciones compradas al inicio
    caja = CAJA0 - COMISION - q * precios[0]
    peak, perdida = CAJA0, 0
    for p in precios:
        w = caja + q * p
        peak = max(peak, w)
        perdida = max(perdida, peak - w)
    return {"patrimonio": caja + q * precios[-1], "ordenes": 1, "comisiones": COMISION, "perdida_max": perdida}


def evaluar(precios: list[int]) -> dict:  # métricas de las referencias y los finalistas en una serie
    filas = {"No operar": metricas_trader(Trader, {}, precios), "Comprar y mantener": metricas_bh(precios)}
    for nombre, clase, params in FINALISTAS:
        filas[nombre] = metricas_trader(clase, params, precios)
    return filas


def main() -> None:  # arma las tablas, las imprime y las guarda
    SALIDA.mkdir(parents=True, exist_ok=True)
    grupos = [("calibración", encontrar_series(TB)), ("reservada", encontrar_series(RESERVADAS))]
    nombres = ["No operar", "Comprar y mantener"] + [n for n, _, _ in FINALISTAS]

    csv = ["serie,tipo,trader,patrimonio,ordenes,comisiones,perdida_max,vs_bh,vs_no_operar"]
    md = ["# Tabla final", "", "Patrimonio final / órdenes / comisiones / pérdida máxima desde un peak.", ""]
    resumen = {n: {"vs_bh": [], "vs_no": [], "gana_bh": 0, "perdida": []} for n in nombres}

    for tipo, series in grupos:
        for ruta in series:
            filas = evaluar(cargar(ruta))
            bh, no = filas["Comprar y mantener"]["patrimonio"], filas["No operar"]["patrimonio"]
            md += [f"## {ruta.stem} ({tipo})", "",
                   "| Trader | Patrimonio | Órdenes | Comisiones | Pérdida máx. | vs B&H | vs no operar |",
                   "|---|---|---|---|---|---|---|"]
            for n in nombres:
                f = filas[n]
                vs_bh, vs_no = f["patrimonio"] - bh, f["patrimonio"] - no
                md.append(f"| {n} | {f['patrimonio']} | {f['ordenes']} | {f['comisiones']} | "
                          f"{f['perdida_max']} | {vs_bh:+d} | {vs_no:+d} |")
                csv.append(f"{ruta.stem},{tipo},{n},{f['patrimonio']},{f['ordenes']},{f['comisiones']},"
                           f"{f['perdida_max']},{vs_bh},{vs_no}")
                r = resumen[n]
                r["vs_bh"].append(vs_bh); r["vs_no"].append(vs_no); r["perdida"].append(f["perdida_max"])
                r["gana_bh"] += vs_bh > 0
            md.append("")

    total = len(resumen[nombres[0]]["vs_bh"])                     # cantidad de series
    md += ["## Resumen en las " + str(total) + " series", "",
           "| Trader | Gana a B&H | Promedio vs B&H | Promedio vs no operar | Pérdida máx. promedio |",
           "|---|---|---|---|---|"]
    for n in nombres:
        r = resumen[n]
        md.append(f"| {n} | {r['gana_bh']}/{total} | {sum(r['vs_bh']) / total:+.0f} | "
                  f"{sum(r['vs_no']) / total:+.0f} | {sum(r['perdida']) / total:.0f} |")

    # Prueba de estrés: cada serie cortada en su mínimo global (si está después del tick 2000)
    md += ["", "## Prueba de estrés: series cortadas en su mínimo", "",
           "Peor final posible para un algoritmo que mantiene acciones. Diferencia contra no operar.", "",
           "| Serie | Corte | " + " | ".join(n for n, _, _ in FINALISTAS) + " |",
           "|---|---|" + "---|" * len(FINALISTAS)]
    estres = {n: [] for n, _, _ in FINALISTAS}
    for _, series in grupos:
        for ruta in series:
            precios = cargar(ruta)
            corte = precios.index(min(precios))
            if corte < 2000:
                continue
            filas = evaluar(precios[:corte + 1])
            celdas = []
            for n, _, _ in FINALISTAS:
                d = filas[n]["patrimonio"] - CAJA0
                estres[n].append(d)
                celdas.append(f"{d:+d} ({filas[n]['ordenes']} órd.)")
            md.append(f"| {ruta.stem} | {corte} | " + " | ".join(celdas) + " |")
    md.append("| **Promedio** | | " + " | ".join(f"**{sum(v) / len(v):+.0f}**" for v in estres.values()) + " |")

    (SALIDA / "tabla_final.csv").write_text("\n".join(csv) + "\n")
    (SALIDA / "tabla_final.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    print(f"\nGuardado en {SALIDA / 'tabla_final.md'} y {SALIDA / 'tabla_final.csv'}")


if __name__ == "__main__":
    main()