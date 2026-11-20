"""
Test de ida y vuelta del assembler para cualquier programa .s
(versión general de test_game.py del Proyecto 2).

Toma cada palabra que generó el assembler y la DECODIFICA con las mismas
fórmulas que usa el procesador (espino_decoder.v y espino_id_stage.v). Si lo
decodificado coincide con lo que dice el .s, el hardware ejecuta exactamente
lo que escribimos. El decodificador de aquí es independiente de los encode_*
del assembler: si un encoder tiene un bug, este test lo detecta.

Uso (desde la raíz del repo):
    python3 tools/test_roundtrip.py sw/trade.s
    python3 tools/test_roundtrip.py sw/blink.s sw/7seg.s     # varios a la vez

Si agregan instrucciones con un formato nuevo (por ejemplo custom-0), el test
verifica su opcode/funct3/funct7 y avisa que los operandos no se revisaron,
hasta que agreguen su caso en verificar_operandos().
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # assembler.py está en tools/

from assembler import (first_pass, second_pass, read_source, expand_pseudo,
                       parse_immediate, INSTRUCTIONS, AsmError)


# ---------------------------------------------------------------------------
# Decodificador: copia en Python de lo que hace el hardware
# ---------------------------------------------------------------------------

def bits(w, hi, lo):
    """instr[hi:lo] en Verilog."""
    return (w >> lo) & ((1 << (hi - lo + 1)) - 1)


def sext(value, n_bits):
    """Extensión de signo: lo que hace {{20{instr[31]}}, ...} en el decoder."""
    if value & (1 << (n_bits - 1)):
        return value - (1 << n_bits)
    return value


def decode(w):
    """Campos de la instrucción, tal como los ve el core."""
    d = {
        "opcode": bits(w, 6, 0),
        "funct3": bits(w, 14, 12),
        "funct7": bits(w, 31, 25),
        "rd":     bits(w, 11, 7),
        "rs1":    bits(w, 19, 15),
        "rs2":    bits(w, 24, 20),
    }
    d["imm_i"] = sext(bits(w, 31, 20), 12)
    d["imm_s"] = sext((bits(w, 31, 25) << 5) | bits(w, 11, 7), 12)
    d["imm_b"] = sext((bits(w, 31, 31) << 12) | (bits(w, 7, 7) << 11)
                      | (bits(w, 30, 25) << 5) | (bits(w, 11, 8) << 1), 13)
    d["imm_u"] = bits(w, 31, 12)
    d["imm_j"] = sext((bits(w, 31, 31) << 20) | (bits(w, 19, 12) << 12)
                      | (bits(w, 20, 20) << 11) | (bits(w, 30, 21) << 1), 21)
    return d


# Qué registros usa cada formato (para el chequeo de RV32E)
REGISTROS_POR_FORMATO = {
    "R": ("rd", "rs1", "rs2"), "I": ("rd", "rs1"), "IL": ("rd", "rs1"),
    "S": ("rs1", "rs2"), "B": ("rs1", "rs2"), "U": ("rd",), "J": ("rd",),
}


# ---------------------------------------------------------------------------
# Helpers para leer los operandos del .s (independientes del assembler)
# ---------------------------------------------------------------------------

def reg(tok):
    return int(tok.strip()[1:])


def mem(tok, line_no, labels):
    off, r = tok.strip().rstrip(")").split("(")
    return parse_immediate(off, line_no, labels), reg(r)


# ---------------------------------------------------------------------------
# Verificación
# ---------------------------------------------------------------------------

def verificar_operandos(tipo, d, ops, pc, labels, line_no, check):
    if tipo == "R":
        check(d["rd"] == reg(ops[0]),  f"rd = x{d['rd']}")
        check(d["rs1"] == reg(ops[1]), f"rs1 = x{d['rs1']}")
        check(d["rs2"] == reg(ops[2]), f"rs2 = x{d['rs2']}")
    elif tipo == "I":
        imm = parse_immediate(ops[2], line_no, labels)
        check(d["rd"] == reg(ops[0]),  f"rd = x{d['rd']}")
        check(d["rs1"] == reg(ops[1]), f"rs1 = x{d['rs1']}")
        check(d["imm_i"] == imm,       f"imm = {d['imm_i']}, esperado {imm}")
    elif tipo == "IL":
        off, base = mem(ops[1], line_no, labels)
        check(d["rd"] == reg(ops[0]), f"rd = x{d['rd']}")
        check(d["rs1"] == base,       f"rs1 = x{d['rs1']}")
        check(d["imm_i"] == off,      f"offset = {d['imm_i']}, esperado {off}")
    elif tipo == "S":
        off, base = mem(ops[1], line_no, labels)
        check(d["rs2"] == reg(ops[0]), f"rs2 = x{d['rs2']}")
        check(d["rs1"] == base,        f"rs1 = x{d['rs1']}")
        check(d["imm_s"] == off,       f"offset = {d['imm_s']}, esperado {off}")
    elif tipo == "B":
        destino = pc + d["imm_b"]
        check(d["rs1"] == reg(ops[0]), f"rs1 = x{d['rs1']}")
        check(d["rs2"] == reg(ops[1]), f"rs2 = x{d['rs2']}")
        check(destino == labels[ops[2]], f"salta a {destino:#x}, '{ops[2]}' está en {labels[ops[2]]:#x}")
    elif tipo == "U":
        imm = parse_immediate(ops[1], line_no, labels)
        check(d["rd"] == reg(ops[0]), f"rd = x{d['rd']}")
        check(d["imm_u"] == (imm & 0xFFFFF), f"imm = {d['imm_u']:#x}, esperado {imm & 0xFFFFF:#x}")
    elif tipo == "J":
        destino = pc + d["imm_j"]
        check(d["rd"] == reg(ops[0]), f"rd = x{d['rd']}")
        check(destino == labels[ops[1]], f"salta a {destino:#x}, '{ops[1]}' está en {labels[ops[1]]:#x}")
    else:
        return False   # formato desconocido: operandos sin revisar
    return True


def probar(ruta):
    """Devuelve (ok, mensaje)."""
    try:
        labels, instrs = first_pass(read_source(ruta))
        words = second_pass(instrs, labels)
    except AsmError as e:
        return False, f"{ruta}: el assembler rechazó el programa: {e}"

    errores, avisos = [], []

    if len(words) != len(instrs):
        return False, f"{ruta}: {len(words)} palabras para {len(instrs)} instrucciones"

    for (line_no, pc, mnem_src, ops_src), w in zip(instrs, words):
        texto = f"{mnem_src} {', '.join(ops_src)}"

        def check(cond, msg):
            if not cond:
                errores.append(f"  línea {line_no:4d} (PC {pc:#06x})  {texto:<30} → {msg}")

        check(0 <= w < 2**32, f"palabra fuera de 32 bits: {w:#x}")
        mnem, ops = expand_pseudo(mnem_src, ops_src, line_no)
        tipo, opcode, f3, f7 = INSTRUCTIONS[mnem]
        d = decode(w)

        check(d["opcode"] == opcode, f"opcode {d['opcode']:07b}, esperado {opcode:07b}")
        if f3 is not None:
            check(d["funct3"] == f3, f"funct3 {d['funct3']:03b}, esperado {f3:03b}")
        if f7 is not None:
            check(d["funct7"] == f7, f"funct7 {d['funct7']:07b}, esperado {f7:07b}")

        if not verificar_operandos(tipo, d, ops, pc, labels, line_no, check):
            avisos.append(f"  línea {line_no:4d}  {texto}: formato '{tipo}' sin verificación de operandos")

        # Ningún registro fuera de RV32E (x16 en adelante no existe)
        for campo in REGISTROS_POR_FORMATO.get(tipo, ()):
            check(d[campo] <= 15, f"{campo} = x{d[campo]} no existe en RV32E")

    if errores:
        return False, f"{ruta}: {len(errores)} error(es) al decodificar:\n" + "\n".join(errores)

    saltos = sum(1 for line_no, _, m, o in instrs
                 if INSTRUCTIONS[expand_pseudo(m, o, line_no)[0]][0] in ("B", "J"))
    msg = f"{ruta} OK: {len(words)} instrucciones decodificadas correctamente ({saltos} saltos llegan a su etiqueta)"
    if avisos:
        msg += "\nAvisos:\n" + "\n".join(avisos)
    return True, msg


def main(rutas):
    if not rutas:
        print(__doc__)
        return 2
    todo_ok = True
    for ruta in rutas:
        ok, msg = probar(ruta)
        print(msg)
        todo_ok &= ok
    return 0 if todo_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
