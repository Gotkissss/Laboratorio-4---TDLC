"""
Uso:
    python main.py expresiones.txt

Formato del archivo de entrada (una expresion por linea):
    (a*|b*)+ ; aaabbb
    ((eps|a)|b*)*
    (a|b)*abb(a|b)* ; babba
    0?(1?)?0*

- Todo lo que va antes del ';' es la expresion regular r.
- Todo lo que va despues del ';' (opcional) es la cadena w a evaluar.
  Si no se incluye w en el archivo, el programa la pide por consola.
- 'eps' dentro de la regex se interpreta como epsilon.

Por cada linea se genera un archivo <n>_afn.png con el dibujo del AFN
y se imprime "si"/"no" indicando si w pertenece al lenguaje.
"""

import sys
import os
from thompson import regex_to_nfa, simulate, draw_nfa


def parse_line(line: str):
    line = line.strip()
    if not line:
        return None
    if ";" in line:
        regex, w = line.split(";", 1)
        return regex.strip(), w.strip()
    return line, None


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 main.py <archivo_expresiones.txt> [carpeta_salida]")
        sys.exit(1)

    filepath = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else "salida"
    os.makedirs(outdir, exist_ok=True)

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for i, raw_line in enumerate(lines, start=1):
        parsed = parse_line(raw_line)
        if parsed is None:
            continue
        regex, w = parsed

        print("=" * 60)
        print(f"Linea {i}: r = {regex}")

        try:
            frag = regex_to_nfa(regex)
        except Exception as e:
            print(f"  [ERROR] No se pudo procesar la expresion: {e}")
            continue

        img_path = os.path.join(outdir, f"linea{i}_afn")
        png = draw_nfa(frag, img_path, regex_label=regex)
        print(f"  AFN dibujado en: {png}")

        if w is None:
            w = input(f"  Ingrese la cadena w a evaluar para '{regex}': ").strip()

        aceptada = simulate(frag, w)
        print(f"  w = '{w}'  ->  {'si' if aceptada else 'no'}")


if __name__ == "__main__":
    main()
