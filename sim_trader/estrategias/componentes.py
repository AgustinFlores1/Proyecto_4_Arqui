"""
Piezas compartidas por las tres variantes.

  Historial            buffer circular genérico (ya implementado)
  CuantilEstocastico   A2: umbral que converge al percentil τ        <-- TODO
  TablaResultados      B:  suma y conteo de retornos por casilla     <-- TODO

Los tests en tests/test_componentes.py verifican sus implementaciones de
CuantilEstocastico y TablaResultados. Hasta que las escriban, esos tests fallan
y las estrategias simplemente mantienen (devuelven 0x00).
"""


class Historial:
    """
    Buffer circular de tamaño potencia de 2.
    hace(0) es el último valor guardado, hace(1) el anterior, etc.
    En trade.s es un arreglo en RAM + un índice que avanza con addi/andi.
    """

    def __init__(self, tam: int, inicial: int = 0):
        assert tam > 0 and (tam & (tam - 1)) == 0, "tam debe ser potencia de 2"
        self.buf = [inicial] * tam
        self.mascara = tam - 1
        self.idx = 0        # dónde se escribe el próximo valor
        self.cuenta = 0     # cuántos valores se han guardado en total (para saber si ya hay historia)

    def guardar(self, valor: int) -> None:
        self.buf[self.idx] = valor
        self.idx = (self.idx + 1) & self.mascara
        self.cuenta += 1

    def hace(self, k: int) -> int:
        assert 0 <= k <= self.mascara, "no se puede mirar más atrás que el tamaño del buffer"
        assert k < self.cuenta, "todavía no hay tanta historia"
        return self.buf[(self.idx - 1 - k) & self.mascara]

    def tiene(self, k: int) -> bool:
        """True si ya existe hace(k)."""
        return k < self.cuenta


class CuantilEstocastico:
    """
    A2: umbral θ que converge al percentil τ de los niveles observados (Robbins–Monro).

        θ ← θ + η·(τ − 1[nivel ≤ θ])

    Versión entera con acumulador:
        si nivel > θ:  acc += paso_arriba      (τ      escalado, ej. 17 para τ = 0,85)
        si no:         acc −= paso_abajo       (1 − τ  escalado, ej. 3)
        si acc ≥  K:   θ += 1, acc −= K
        si acc ≤ −K:   θ −= 1, acc += K

    Para el umbral bajo (τ = 0,15) basta invertir los pasos: paso_arriba = 3, paso_abajo = 17.
    θ debe quedarse dentro de [0, 16].
    """

    def __init__(self, paso_arriba: int, paso_abajo: int, K: int, theta_inicial: int):
        self.paso_arriba = paso_arriba
        self.paso_abajo = paso_abajo
        self.K = K
        self.theta = theta_inicial
        self.acc = 0

    def actualizar(self, nivel: int) -> None:
        # TODO(A2): implementar la regla de arriba.
        # Preguntas para pensar antes de escribirlo:
        #   - ¿qué hace con nivel == SIN_INFO (-1)? ¿Lo cuenta como "bajo θ" o lo ignora?
        #   - ¿por qué conviene "acc −= K" en vez de "acc = 0" al mover θ?
        pass


class TablaResultados:
    """
    B: para cada casilla (nivel 0–16, o zona 0–2 en la variante reagrupada) guarda

        S[c] = suma de los retornos que siguieron a esa casilla
        C[c] = cuántas muestras hay

    con olvido por ventana: se recuerdan solo las últimas M muestras. Cuando entra
    la muestra número M+1, la más antigua se resta de su casilla. Para eso hay que
    guardar (casilla, retorno) de cada muestra en un buffer de tamaño M.

    Nunca se divide S/C: toda comparación con el promedio se hace multiplicando
    por constantes, ej. 'promedio > num/den'  <=>  den·S > num·C   (C > 0).
    """

    def __init__(self, n_casillas: int, M: int):
        assert (M & (M - 1)) == 0, "M debe ser potencia de 2"
        self.S = [0] * n_casillas
        self.C = [0] * n_casillas
        self.M = M
        # TODO(B): buffers para el olvido por ventana (casilla y retorno de cada muestra).
        # Sugerencia: dos Historial(M), o uno solo que empaquete ambos valores.

    def aprender(self, casilla: int, r: int) -> None:
        """Agrega la muestra (casilla, r). Si ya había M muestras, olvida la más antigua."""
        # TODO(B)
        pass

    def confiable(self, casilla: int, C_min: int) -> bool:
        """True si la casilla tiene al menos C_min muestras."""
        # TODO(B)
        return False

    def promedio_supera(self, casilla: int, num: int, den: int) -> bool:
        """True si S/C > num/den, sin dividir. num puede ser negativo."""
        # TODO(B)
        return False

    def promedio_bajo(self, casilla: int, num: int, den: int) -> bool:
        """True si S/C < num/den, sin dividir."""
        # TODO(B)
        return False
