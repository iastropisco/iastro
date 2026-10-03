#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Revisa que o texto dos ficheiros do proxecto estea en portugues.

Salta os campos de cita (fonte, referencia, ref) porque poden
conter titulos orixinais en castelan, e salta o seu propio ficheiro.
"""
import json
import re
import sys
from pathlib import Path

# Palabras galegas ou castelas que se adoitan colar no portugues.
BLACKLIST = [
    "augas", "camiño", "desexo", "proxecto", "reloxo",
    "hipótesis", "estrellas", "posición", "guardado",
    "queres", "xente", "xornada", "xogar", "nodo", "cartografía",
]

# Campos do JSON que son prosa en portugues (obrigan a portugues).
PROSA = {
    "nome", "elemento", "polaridade", "modo", "tema",
    "simbolo", "regiao", "regionalismo", "historia",
    "descricao", "dominio", "curiosidade", "uso", "parte",
    "signo", "corpo", "planta", "toponimo", "deidade", "_descricao",
}

# Campos do JSON que son cita ou ligazon (permiten titulos orixinais).
CITA = {"fonte", "fonte_geral", "referencia", "ref", "refs", "ligazon"}

RE_WORD = re.compile(r"\b(" + "|".join(BLACKLIST) + r")\b", re.I)

# Cita entre comiñas dobres: titulo orixinal (pode ir en castelan).
RE_COMIÑAS = re.compile(r'"[^"]*"', re.S)

EXTS = ("*.json", "*.md", "*.py", "*.txt")


def quitar_citas(text):
    """Substitúe por baleiro o texto entre comiñas dobres."""
    return RE_COMIÑAS.sub("", text)


def scan_string(text):
    return sorted(set(w.lower() for w in RE_WORD.findall(text)))


def scan_json(obj):
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in CITA:
                continue
            hits.extend(scan_json(v))
    elif isinstance(obj, list):
        for v in obj:
            hits.extend(scan_json(v))
    elif isinstance(obj, str):
        hits.extend(scan_string(obj))
    return hits


def scan_file(path):
    if path.name == "verificar_pt.py":
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []
    if path.suffix == ".json":
        try:
            return scan_json(json.loads(text))
        except Exception:
            text = str(text)
    return scan_string(quitar_citas(text))


def files_paths(rutas):
    out = []
    for r in rutas:
        p = Path(r)
        if p.is_dir():
            for e in EXTS:
                out.extend(p.glob(e))
        elif p.is_file():
            out.append(p)
    return out


def main():
    targets = sys.argv[1:] or ["."]
    errores = 0
    for f in sorted(files_paths(targets)):
        hits = scan_file(f)
        if hits:
            errores += 1
            print("  MARCADOR", hits, "en", f)
    if errores:
        print(f"\nErrores: {errores}.")
        sys.exit(1)
    print("OK: portugues limpo.")


if __name__ == "__main__":
    main()