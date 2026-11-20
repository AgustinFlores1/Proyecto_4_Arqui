"""
Las tres variantes a comparar comparten el mismo esqueleto por tick:

    1. actualizar el RSI con el precio nuevo y obtener el nivel
    2. actualizar los umbrales A2 (solo en las variantes que usan A2)
    3. traducir el nivel a una "casilla" de la tabla (nivel 0–16, o zona 0–2)
    4. guardar precio y casilla en los historiales
    5. APRENDER: entregar a la tabla la muestra que ya tiene resultado     <-- TODO
    6. DECIDIR: comprar / vender / nada                                     <-- TODO
    7. traducir la intención a un byte respetando la posición (ya implementado)

Variantes:
    BCalentamiento   casilla = nivel; si la casilla no es confiable, no opera
    A2BRespaldo      casilla = nivel; si no es confiable, decide con los umbrales A2
    A2BReagrupada    casilla = zona respecto a los umbrales A2 (bajo / medio / alto)
"""

from mercado import BYTE_MANTENER, byte_comprar, byte_vender
from rsi import RSIVentana, SIN_INFO
from estrategias.componentes import Historial, CuantilEstocastico, TablaResultados

QUIERO_COMPRAR = 1
QUIERO_VENDER = -1
NADA = 0


class BaseRSIAprende:
    nombre = "base"

    def __init__(self, N=32, h=8, M=512, C_min=20,
                 entrada=(1, 5), salida=(0, 1), n_casillas=17):
        """
        N         ventana del RSI (potencia de 2)
        h         horizonte del retorno que se aprende
        M         cuántas muestras recuerda la tabla (potencia de 2)
        C_min     muestras mínimas para confiar en una casilla
        entrada   margen de entrada como fracción (num, den): comprar si promedio > num/den
                  (1, 5) = 0,2 puntos, aprox. lo que cuesta la comisión de ida y vuelta
        salida    margen de salida (num, den): vender si promedio < num/den
        """
        self.rsi = RSIVentana(N)
        self.h = h
        self.C_min = C_min
        self.entrada = entrada
        self.salida = salida
        self.tabla = TablaResultados(n_casillas, M)
        # Historiales: de largo suficiente para mirar h+1 ticks atrás (potencia de 2).
        tam = 1
        while tam < h + 2:
            tam *= 2
        self.precios = Historial(tam)
        self.casillas = Historial(tam, inicial=SIN_INFO)
        self.dentro = False   # copia propia de la posición: ¿tenemos acciones?

    # ---- ganchos que cambian según la variante ----------------------------

    def actualizar_umbrales(self, nivel):
        """Variantes con A2: actualizar θ_bajo y θ_alto. B puro: no hace nada."""
        pass

    def casilla(self, nivel):
        """Índice de la tabla para este nivel. B puro: el nivel mismo."""
        return nivel

    def decidir_sin_datos(self, nivel):
        """Qué hacer si la casilla actual todavía no es confiable."""
        return NADA

    # ---- el tick ------------------------------------------------------------

    def tick(self, p):
        self.rsi.actualizar(p)
        nivel = self.rsi.nivel()
        self.actualizar_umbrales(nivel)
        c = self.casilla(nivel)
        self.precios.guardar(p)
        self.casillas.guardar(c)
        self.aprender()
        return self.a_byte(self.decidir(c, nivel))

    def aprender(self):
        """
        TODO(B): entregar a self.tabla la muestra cuyo resultado ya se conoce.

        Recordatorio del desfase. Si la casilla se observó en el tick t:
            - la decisión tomada en t se ejecuta a p[t+1]
            - su retorno a horizonte h es r = p[t+1+h] − p[t+1]
        Ese retorno se conoce recién en el tick n = t+1+h.

        Preguntas para resolverlo con los historiales (hace(0) es el tick actual n):
            - ¿cuántos ticks atrás está la casilla de t?   self.casillas.hace(?)
            - ¿qué precio es p[t+1]?                         self.precios.hace(?)
            - ¿qué hace si esa casilla es SIN_INFO?
            - ¿qué hace si todavía no hay suficiente historia? (Historial.tiene)

        Si se equivoca en uno de estos índices, el simulador no le avisa: la
        estrategia simplemente aprende otra cosa. Revise su respuesta con un
        ejemplo en papel, con h = 2 y unos 6 precios.
        """
        pass

    def decidir(self, c, nivel):
        """
        TODO(B): devolver QUIERO_COMPRAR, QUIERO_VENDER o NADA.

        Ideas a decidir ustedes:
            - si c es SIN_INFO, ¿qué hace?
            - si la casilla no es confiable (C_min), delegar en self.decidir_sin_datos(nivel)
            - fuera de mercado: comprar si el promedio supera self.entrada
            - dentro: vender si el promedio está bajo self.salida
              (entrada > salida da histéresis)
        """
        return NADA

    # ---- intención -> byte ---------------------------------------------------

    def a_byte(self, intencion):
        """
        Traduce la intención a un byte y mantiene la copia de la posición.
        Siempre devuelve MANTENER salvo en el tick en que cambia la posición:
        así la decisión no se repite en el tick siguiente.

        Pregunta abierta: con precio < ~158, 63 acciones no alcanzan para invertir
        toda la caja, y si se tienen más de 63, una venta de 63 no vende todo.
        ¿Les importa? Si sí, ¿cómo lo resolverían sin conocer la caja exacta?
        """
        if intencion == QUIERO_COMPRAR and not self.dentro:
            self.dentro = True
            return byte_comprar(63)
        if intencion == QUIERO_VENDER and self.dentro:
            self.dentro = False
            return byte_vender(63)
        return BYTE_MANTENER


class BCalentamiento(BaseRSIAprende):
    nombre = "B + calentamiento"


class A2BRespaldo(BaseRSIAprende):
    """Mientras la casilla no es confiable, decide con los umbrales A2 (lectura de reversión)."""
    nombre = "A2 + B (respaldo)"

    def __init__(self, K=64, theta_bajo0=5, theta_alto0=11, **kw):
        super().__init__(**kw)
        self.bajo = CuantilEstocastico(paso_arriba=3, paso_abajo=17, K=K, theta_inicial=theta_bajo0)
        self.alto = CuantilEstocastico(paso_arriba=17, paso_abajo=3, K=K, theta_inicial=theta_alto0)

    def actualizar_umbrales(self, nivel):
        self.bajo.actualizar(nivel)
        self.alto.actualizar(nivel)

    def decidir_sin_datos(self, nivel):
        # TODO(A2): regla de respaldo con self.bajo.theta y self.alto.theta.
        return NADA


class A2BReagrupada(A2BRespaldo):
    """La tabla tiene 3 casillas: bajo θ_bajo, entre ambos, sobre θ_alto."""
    nombre = "A2 + B (reagrupada)"

    def __init__(self, **kw):
        super().__init__(n_casillas=3, **kw)

    def casilla(self, nivel):
        # TODO(reagrupada): devolver 0, 1 o 2 según los umbrales actuales (o SIN_INFO).
        # Nota: el esqueleto guarda la zona en el tick en que se observó. ¿Por qué
        # sería un error recalcularla en aprender() con los umbrales de ese momento?
        return SIN_INFO

    def decidir_sin_datos(self, nivel):
        # Con calentamiento: no opera hasta que la zona sea confiable.
        # (Si quieren, prueben también usar el respaldo A2 aquí.)
        return NADA
