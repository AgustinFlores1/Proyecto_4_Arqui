"""
Gráfico del mercado y del desempeño de los traders.

Dos paneles que comparten el eje de los ticks:
  arriba  el precio de la acción (la "línea de mercado")
  abajo   el patrimonio de cada trader en cada tick
Las referencias (no operar, comprar y mantener) van en gris punteado para que
no compitan con los algoritmos; cada algoritmo tiene un color fijo.
"""

from pathlib import Path

import matplotlib.pyplot as plt

from trader import Trader

# Colores categóricos en orden fijo (validados para daltonismo); uno por algoritmo
COLORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
GRIS_REFERENCIA = "#8a8a85"      # referencias (no operar, comprar y mantener)
ESTILOS_REFERENCIA = [":", "--", "-."]   # un tipo de línea distinto por referencia, en orden
GRIS_PRECIO = "#3d3d3a"          # línea del precio
TEXTO = "#3d3d3a"                # color de textos y ejes
TEXTO_SECUNDARIO = "#77776f"     # etiquetas secundarias
GRILLA = "#e6e6e1"               # grilla recesiva


def _separar_etiquetas(valores: list[float], separacion: float) -> list[float]:  # mueve las etiquetas finales para que no se encimen
    orden = sorted(range(len(valores)), key=lambda i: valores[i])   # índices de menor a mayor valor
    posiciones = list(valores)                                      # posición vertical de cada etiqueta
    for a, b in zip(orden, orden[1:]):                              # empuja hacia arriba la que choca con la de abajo
        if posiciones[b] - posiciones[a] < separacion:
            posiciones[b] = posiciones[a] + separacion
    return posiciones


def graficar(precios: list[int], traders: list[Trader], referencias: set[str], capital_inicial: int,
             ruta: str | Path, mostrar: bool = True) -> None:  # dibuja los dos paneles y guarda la imagen en 'ruta'
    """
    precios          serie de precios (uno por tick)
    traders          traders ya simulados (cada uno con su wealth_history)
    referencias      nombres de los traders que son referencia (se dibujan en gris)
    capital_inicial  caja inicial, para la línea horizontal de "no ganar ni perder"
    ruta             dónde guardar el PNG
    mostrar          si True, además abre la ventana del gráfico
    """
    ticks = range(len(precios))                                      # eje x común
    fig, (ax_precio, ax_patrimonio) = plt.subplots(
        2, 1, figsize=(13, 8), sharex=True, gridspec_kw={"height_ratios": [1, 2]})

    # --- Panel 1: línea de mercado ---------------------------------------
    ax_precio.plot(ticks, precios, color=GRIS_PRECIO, linewidth=0.8)
    ax_precio.set_title("Precio de la acción", loc="left", color=TEXTO, fontsize=11)
    ax_precio.set_ylabel("Precio", color=TEXTO_SECUNDARIO)

    # --- Panel 2: patrimonio de cada trader -------------------------------
    ax_patrimonio.axhline(capital_inicial, color=GRILLA, linewidth=1.5, zorder=0)
    finales, colores_finales, nombres_finales = [], [], []          # datos para las etiquetas al final de cada línea
    color_siguiente = 0                                              # próximo color categórico libre
    estilo_siguiente = 0                                             # próximo estilo de referencia libre
    for trader in traders:
        if trader.name in referencias:
            color, grosor = GRIS_REFERENCIA, 1.2                     # referencia: gris, con su propio tipo de línea
            estilo = ESTILOS_REFERENCIA[estilo_siguiente % len(ESTILOS_REFERENCIA)]
            estilo_siguiente += 1
        else:
            color, estilo, grosor = COLORES[color_siguiente % len(COLORES)], "-", 1.4
            color_siguiente += 1
        ax_patrimonio.plot(ticks, trader.wealth_history, color=color, linestyle=estilo,
                           linewidth=grosor, label=trader.name)
        finales.append(trader.wealth_history[-1])
        colores_finales.append(color)
        nombres_finales.append(trader.name)

    # Valor final al lado de cada línea (el color va en un marcador, el texto en gris)
    rango = max(max(t.wealth_history) for t in traders) - min(min(t.wealth_history) for t in traders)
    posiciones = _separar_etiquetas(finales, separacion=rango * 0.045)
    x_final = len(precios) - 1                                       # último tick
    for valor, y, color in zip(finales, posiciones, colores_finales):
        ax_patrimonio.plot([x_final], [valor], marker="o", markersize=4, color=color)
        ax_patrimonio.annotate(f"{valor:,}".replace(",", "."), xy=(x_final, y),
                               xytext=(8, 0), textcoords="offset points",
                               va="center", fontsize=9, color=TEXTO)

    ax_patrimonio.set_title("Patrimonio de cada trader", loc="left", color=TEXTO, fontsize=11)
    ax_patrimonio.set_ylabel("Patrimonio ($)", color=TEXTO_SECUNDARIO)
    ax_patrimonio.set_xlabel("Tick", color=TEXTO_SECUNDARIO)
    ax_patrimonio.legend(loc="upper left", bbox_to_anchor=(1.06, 1), frameon=False, fontsize=9)

    # Estilo recesivo: grilla suave, sin bordes superiores ni derechos
    for ax in (ax_precio, ax_patrimonio):
        ax.grid(axis="y", color=GRILLA, linewidth=0.8)
        ax.set_axisbelow(True)
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)
        for lado in ("left", "bottom"):
            ax.spines[lado].set_color(GRILLA)
        ax.tick_params(colors=TEXTO_SECUNDARIO, labelsize=9)
    ax_patrimonio.set_xlim(0, len(precios) * 1.06)                  # espacio a la derecha para las etiquetas

    fig.tight_layout()
    fig.savefig(ruta, dpi=150)
    if mostrar:
        plt.show()
    plt.close(fig)
