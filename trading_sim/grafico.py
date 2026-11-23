"""
Gráficos del mercado y del desempeño de los traders.

Genera un archivo por familia de algoritmos. Cada archivo tiene:
  arriba  el precio de la acción (la "línea de mercado"), igual en todos
  abajo   el patrimonio de cada trader de esa familia en cada tick, junto a las
          referencias (no operar, comprar y mantener) en gris
Todos los archivos usan la misma escala de patrimonio, así se pueden comparar.
"""

import unicodedata
from pathlib import Path

import matplotlib.pyplot as plt

from trader import Trader

# Colores categóricos en orden fijo (validados para daltonismo); dentro de cada gráfico se asignan en este orden
COLORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
GRIS_REFERENCIA = "#8a8a85"              # referencias (no operar, comprar y mantener)
ESTILOS_REFERENCIA = [":", "--", "-."]   # un tipo de línea distinto por referencia, en orden
GRIS_PRECIO = "#3d3d3a"                  # línea del precio
TEXTO = "#3d3d3a"                        # color de títulos y valores
TEXTO_SECUNDARIO = "#77776f"             # etiquetas de ejes
GRILLA = "#e6e6e1"                       # grilla recesiva


def _nombre_archivo(familia: str) -> str:  # convierte "Reversión a la media" en "reversion_a_la_media"
    sin_tildes = unicodedata.normalize("NFKD", familia).encode("ascii", "ignore").decode()
    return "_".join(sin_tildes.lower().split())


def _separar_etiquetas(valores: list[float], separacion: float) -> list[float]:  # mueve las etiquetas finales para que no se encimen
    orden = sorted(range(len(valores)), key=lambda i: valores[i])   # índices de menor a mayor valor
    posiciones = list(valores)                                      # posición vertical de cada etiqueta
    for a, b in zip(orden, orden[1:]):                              # empuja hacia arriba la que choca con la de abajo
        if posiciones[b] - posiciones[a] < separacion:
            posiciones[b] = posiciones[a] + separacion
    return posiciones


def _estilo_recesivo(ax) -> None:  # grilla suave y sin bordes superior ni derecho
    ax.grid(axis="y", color=GRILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(GRILLA)
    ax.tick_params(colors=TEXTO_SECUNDARIO, labelsize=9)


def _grafico_familia(precios: list[int], familia: str, traders: list[Trader], referencias: list[Trader],
                     capital_inicial: int, limites: tuple[float, float]):  # arma la figura de una familia y la devuelve
    n_ticks = len(precios)                                           # largo de la serie
    minimo, maximo = limites                                         # escala de patrimonio común a todos los gráficos
    rango = maximo - minimo

    fig, (ax_precio, ax_patrimonio) = plt.subplots(
        2, 1, figsize=(13, 8), sharex=True, gridspec_kw={"height_ratios": [1, 2]})
    fig.suptitle(familia, x=0.01, ha="left", color=TEXTO, fontsize=13)

    # --- Línea de mercado ------------------------------------------------
    ax_precio.plot(range(n_ticks), precios, color=GRIS_PRECIO, linewidth=0.8)
    ax_precio.set_title("Precio de la acción", loc="left", color=TEXTO, fontsize=11)
    ax_precio.set_ylabel("Precio", color=TEXTO_SECUNDARIO)

    # --- Patrimonio ------------------------------------------------------
    ax_patrimonio.axhline(capital_inicial, color=GRILLA, linewidth=1.5, zorder=0)
    lineas = []                                                      # (trader, color, estilo, grosor) de cada línea
    for i, ref in enumerate(referencias):
        lineas.append((ref, GRIS_REFERENCIA, ESTILOS_REFERENCIA[i % len(ESTILOS_REFERENCIA)], 1.1))
    for i, trader in enumerate(traders):
        lineas.append((trader, COLORES[i % len(COLORES)], "-", 1.4))

    for trader, color, estilo, grosor in lineas:
        ax_patrimonio.plot(range(n_ticks), trader.wealth_history, color=color, linestyle=estilo,
                           linewidth=grosor, label=trader.name)

    # Valor final al lado de cada línea (el color va en un marcador, el texto en gris)
    finales = [t.wealth_history[-1] for t, *_ in lineas]             # patrimonio final de cada línea
    posiciones = _separar_etiquetas(finales, separacion=rango * 0.045)
    for (trader, color, *_), valor, y in zip(lineas, finales, posiciones):
        ax_patrimonio.plot([n_ticks - 1], [valor], marker="o", markersize=4, color=color)
        ax_patrimonio.annotate(f"{valor:,}".replace(",", "."), xy=(n_ticks - 1, y), xytext=(8, 0),
                               textcoords="offset points", va="center", fontsize=9, color=TEXTO)

    ax_patrimonio.set_title("Patrimonio de cada trader", loc="left", color=TEXTO, fontsize=11)
    ax_patrimonio.set_ylabel("Patrimonio ($)", color=TEXTO_SECUNDARIO)
    ax_patrimonio.set_xlabel("Tick", color=TEXTO_SECUNDARIO)
    ax_patrimonio.set_ylim(minimo - rango * 0.04, maximo + rango * 0.06)
    ax_patrimonio.legend(loc="upper left", bbox_to_anchor=(1.07, 1), frameon=False, fontsize=9)

    for ax in (ax_precio, ax_patrimonio):
        _estilo_recesivo(ax)
    ax_patrimonio.set_xlim(0, n_ticks * 1.06)                       # espacio a la derecha para las etiquetas

    fig.tight_layout()
    return fig


def graficar(precios: list[int], grupos: dict[str, list[Trader]], referencias: list[Trader],
             capital_inicial: int, carpeta: str | Path, mostrar: bool = True) -> list[Path]:  # un PNG por familia en 'carpeta'; devuelve las rutas
    """
    precios          serie de precios (uno por tick)
    grupos           nombre de cada familia -> sus traders ya simulados
    referencias      traders de referencia, que se repiten en gris en cada gráfico
    capital_inicial  caja inicial, para la línea horizontal de "no ganar ni perder"
    carpeta          dónde guardar los PNG (se crea si no existe)
    mostrar          si True, además abre una ventana por gráfico (todas a la vez, al final)
    """
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)

    todos = referencias + [t for ts in grupos.values() for t in ts]  # todos los traders, para fijar la escala común
    limites = (min(min(t.wealth_history) for t in todos),            # patrimonio mínimo y máximo de todos
               max(max(t.wealth_history) for t in todos))

    rutas = []                                                       # archivos generados
    figuras = []                                                     # figuras abiertas, para mostrarlas al final
    for familia, traders in grupos.items():
        fig = _grafico_familia(precios, familia, traders, referencias, capital_inicial, limites)
        ruta = carpeta / f"{_nombre_archivo(familia)}.png"
        fig.savefig(ruta, dpi=150)
        rutas.append(ruta)
        figuras.append(fig)

    if mostrar:
        plt.show()
    for fig in figuras:
        plt.close(fig)
    return rutas


def graficar_serie(precios: list[int], titulo: str, traders: list[Trader], referencias: list[Trader],
                   capital_inicial: int, ruta: str | Path) -> None:  # guarda un gráfico con el precio y el patrimonio de unos traders en una serie
    """
    precios          serie de precios (uno por tick)
    titulo           título del gráfico
    traders          traders ya simulados que se dibujan en color
    referencias      traders de referencia, en gris
    capital_inicial  caja inicial, para la línea horizontal de "no ganar ni perder"
    ruta             dónde guardar el PNG
    """
    todos = referencias + traders                                    # todos los traders del gráfico
    limites = (min(min(t.wealth_history) for t in todos),            # escala de patrimonio de este gráfico
               max(max(t.wealth_history) for t in todos))
    fig = _grafico_familia(precios, titulo, traders, referencias, capital_inicial, limites)
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta, dpi=150, bbox_inches="tight")                  # bbox_inches: que no se corte la leyenda
    plt.close(fig)
