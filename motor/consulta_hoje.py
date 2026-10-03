#!/usr/bin/env python3
"""Consulta astrológica do dia (ou de uma data) — posições + aspectos.

Uso:
    python3 consulta_hoje.py                # hoje (data atual)
    python3 consulta_hoje.py 2026-08-30     # data específica
    python3 consulta_hoje.py --json 2026-08-30   # saída JSON

Fonte: efemérides geradas em /mnt/dados/ephemeris (Swiss Ephemeris),
zodíaco tropical, 00:00 UTC. Saída pensada para o agente iastro ler e
usar como contexto em suas respostas.
"""
import json
import os
import sys
from datetime import datetime

EPH = "/mnt/dados/ephemeris"

SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem",
          "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]

PLANETAS = ["Sun", "Moon", "Mercury", "Venus", "Mars",
            "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
PLANETAS_PT = {
    "Sun": "Sol", "Moon": "Lua", "Mercury": "Mercúrio", "Venus": "Vênus",
    "Mars": "Marte", "Jupiter": "Júpiter", "Saturn": "Saturno",
    "Uranus": "Urano", "Neptune": "Netuno", "Pluto": "Plutão",
}

# normalização dos nomes de aspecto conforme salvo pelo gerador
ASPECTO_NOME = {
    "conjuncao": "conjunção",
    "sextil": "sextil",
    "quadratura": "quadratura",
    "trino": "trino",
    "oposicao": "oposição",
}


def get_day(date_str):
    year, month, _ = date_str.split("-")
    path = os.path.join(EPH, f"{year}-{month.zfill(2)}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("daily", {}).get(date_str)


def build(date_str):
    day = get_day(date_str)
    if day is None:
        return None

    # fases da lua e dados
    moon = day.get("Moon", {})

    planetas = {}
    for en, pt in PLANETAS_PT.items():
        p = day.get(en) or {}
        z = p.get("z", 0)
        grau = int(p.get("d", 0))
        minu = int(round((p.get("d", 0) - int(p.get("d", 0))) * 60))
        retro = p.get("r", False)
        planetas[pt] = {
            "signo": SIGNOS[z] if 0 <= z < 12 else "?",
            "graus": grau,
            "minutos": minu,
            "retrogrado": retro,
            "velocidade": round(p.get("sp", 0), 3),
        }

    aspectos = []
    for par, info in (day.get("aspects") or {}).items():
        a_en = info.get("aspecto", "")
        aspectos.append({
            "planetas": par,  # ex: "Sun-Mercury"
            "aspecto": ASPECTO_NOME.get(a_en, a_en),
            "angulo": round(info.get("angulo", 0), 1),
        })

    return {"data": date_str, "fase_lua": moon.get("ph", ""), "planetas": planetas,
            "aspectos": aspectos}


def format_texto(bloco):
    linhas = []
    linhas.append(f"EFEMÉRIDES DE {bloco['data']} (00:00 UTC, zodíaco tropical, fonte: Swiss Ephemeris)")
    if bloco["fase_lua"]:
        linhas.append(f"Fase da Lua: {bloco['fase_lua']}")
    linhas.append("")
    linhas.append("POSIÇÕES:")
    for nome, info in bloco["planetas"].items():
        retro = " (retrógrado)" if info["retrogrado"] else ""
        linhas.append(f"- {nome}: {info['signo']} {info['graus']}°{info['minutos']}'{retro}")
    linhas.append("")
    linhas.append("ASPECTOS (ângulos entre planetas):")
    if bloco["aspectos"]:
        for a in bloco["aspectos"]:
            en = a["planetas"]
            pt = " e ".join(PLANETAS_PT.get(x, x) for x in en.split("-"))
            linhas.append(f"- {pt}: {a['aspecto']} (ângulo {a['angulo']}°)")
    else:
        linhas.append("- (nenhum aspecto no orbe no dia)")
    linhas.append("")
    linhas.append("Nota: use SOMENTE estes dados para afirmar posições/aspectos do dia; nunca invente.")
    return "\n".join(linhas)


if __name__ == "__main__":
    fmt = "texto"
    args = sys.argv[1:]
    if args and args[0] == "--json":
        fmt = "json"
        args = args[1:]

    date_str = args[0] if args else datetime.now().strftime("%Y-%m-%d")

    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print(f"Data inválida: {date_str} (use YYYY-MM-DD)")
        sys.exit(1)

    bloco = build(date_str)
    if bloco is None:
        print(f"Sem dados de efemérides para {date_str} (cobertura: 1900–2100).")
        sys.exit(0)

    if fmt == "json":
        print(json.dumps(bloco, ensure_ascii=False, indent=2))
    else:
        print(format_texto(bloco))
