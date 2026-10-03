#!/usr/bin/env python3
"""Orquestrador único do iastro.

Recebe data/hora/local de um NASCIMENTO ou EVENTO e produz, numa única rodada:

  1. MAPA TRADICIONAL  — posições dos planetas e o signo/graus de cada um
                         (efeméride Swiss Ephemeris via mapa_astral.calc).
  2. PLANTAS REGENTES  — nascimento → signo → orixá → planta(s) com nome
                         científico + usos + enciclopédia de domínio público
                         (módulo flora), para cada regente (Sol, Lua, Mercúrio,
                         Vênus, Marte).
  3. CÉU DA CULTURA    — leitura do Sol/Asc/Lua por asterismo de cada cultura
                         de céu (ceu.LEITURA; Stellarium + as nossas).
  4. COLAEM            — o mapa tradicional vira uma colagem de arquétipos
                         (PNG) + uma página HTML interativa autossuficiente.

Tudo é escrito em artefatos pequenos e self-contained em `mapas/`, sem duplicar
bases de dados nem acumular lixo no disco. Uso:

    venv/bin/python /mnt/dados/ephemeris/gerar_mapa.py \\
        --data 1990-01-15 --hora 08:00 --local "rio de janeiro" \\
        --cultura indigena --tema "maré de estrelas" --feeling esperanca \\
        --saida "mapas/mapa-meu"
"""
import argparse
import json
import os
import sqlite3
import sys

# Ensure motor directory is FIRST in path so we import local modules
MOTOR_DIR = os.path.dirname(os.path.abspath(__file__))
if MOTOR_DIR not in sys.path:
    sys.path.insert(0, MOTOR_DIR)

# Import path resolver first
import caminhos
caminhos.registrar_no_path()

# Now import our modules (will use paths from caminhos)
import mapa_astral, flora, ceu, colagem, interativo

ARQ = caminhos.ARQ
MAPAS = caminhos.MAPAS
DB = caminhos.DB
CULTURAS_DE_CEU = ["tupi", "tukano", "capixaba-sul"]

SIGNOS = ["Áries","Touro","Gêmeos","Câncer","Leão","Virgem",
          "Libra","Escorpião","Sagitário","Capricórnio","Aquário","Peixes"]


def _sem_acentos(t):
    mapa = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
        "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC")
    return t.translate(mapa).lower()


def _local_canonico(local):
    """resolve nome local (aceitando acentos) para a chave do banco."""
    if not local:
        return None
    alvo = _sem_acentos(local)
    for chave in mapa_astral.LOCALIDADES:
        if _sem_acentos(chave) == alvo:
            return chave
    return None


def form_arg(ap, args, name, default=None):
    return getattr(args, name, default)


def mapa_tradicional(data, hora, local):
    """Posições dos planetas + asc, legíveis. Devolve dict limpo."""
    coords = mapa_astral.LOCALIDADES.get(_local_canonico(local))
    if not coords:
        raise ValueError("Local desconhecido: " + str(local))
    lat, lon = coords[0], coords[1]
    m = mapa_astral.calc(data, hora, lat, lon,
                         tz_horas=mapa_astral.tz_do_local(_local_canonico(local)))
    return {
        "data": data, "hora": hora, "local": local, "lat": lat, "lon": lon,
        "planetas": {nome: _resumo(pm) for nome, pm in m["planetas"].items()},
        "asc": m["asc"],
        "casa1_lon": m["casas"][0]["lon"],
    }


def _resumo(pm):
    return {
        "signo": pm.get("signo"),
        "graus": f"{pm.get('graus',0)}°{pm.get('min',0):02d}'",
        "retrogrado": pm.get("retrogrado", False),
    }


def mapa_plantas(data, hora, local):
    """nascimento → signo → orixá → plantas, para CADA corpo do mapa.

    Vale para todos os planetas clássicos e também para os asteróides
    arquetípicos (Quíron, Lilith, Ceres, Pallas, Juno, Vesta): cada corpo
    está num signo, e cada signo tem o seu orixá regente (tabela
    `correspondencia` afro-brasileira — hipótese com certeza + fonte).
    """
    coords = mapa_astral.LOCALIDADES.get(_local_canonico(local))
    lat, lon = coords[0], coords[1]
    m = mapa_astral.calc(data, hora, lat, lon,
                         tz_horas=mapa_astral.tz_do_local(_local_canonico(local)))
    con = sqlite3.connect(DB)
    cur = con.cursor()
    saida = {}
    for nome, pm in m["planetas"].items():
        signo = pm["signo"]
        r = flora.planta_regente(cur, signo)
        saida[nome] = {
            "signo": signo,
            "orixa": r["orixa"], "certeza": r["certeza"],
            "plantas": [{
                "nome": p[0], "cientifico": p[1],
                "uso_medicinal": p[2], "elemento": p[4],
                "fonte_etno": p[5], "enciclopedia_pd": p[6],
                "saber": p[7] if len(p) > 7 else None,
            } for p in r["plantas"]],
        }
    con.close()
    return saida


def mapa_ceu(data, hora, local):
    """Céu de TODAS as culturas (Stellarium + projeto) no momento do evento.

    Usa o catálogo unificado (ceu_catalogo): cada cultura → asterismo de
    Sol/Asc/Lua, e o arquétipo MÁS FORTE por signo (por correspondencias).
    """
    import ceu_catalogo
    m = ceu_catalogo.mapa_iastro(data, hora, local)
    return {
        "ceu_todas_culturas": m["ceu_todas_culturas"],
        "arquetipos_por_signo": m["arquetipos_por_signo"],
        "plantas_por_saber": m["plantas_por_saber"],
    }


def gerar_tudo(args, saida_base):
    """Roda as quatro camadas e grava artefatos pequenos em saida_base.*"""
    data, hora, local = args.data, args.hora, args.local
    cultura = args.cultura
    local = _local_canonico(local) or local

    # 1) mapa tradicional (JSON)
    mt = mapa_tradicional(data, hora, local)
    # 2) plantas (JSON)
    mp = mapa_plantas(data, hora, local)
    # 3) céu da cultura (JSON, pequeno)
    mc = mapa_ceu(data, hora, local)

    # 4) colagem (PNG) + HTML interativo (usa o form padrão do colagem)
    form = {
        "data": data, "hora": hora, "local": local,
        "cultura": cultura, "tema": args.tema, "feeling": args.feeling,
        "mensaje": getattr(args, "mensaje", None),
    }
    png_res = colagem.gerar_obra(form, saida_base + ".png")
    png = png_res["caminho"] if isinstance(png_res, dict) else png_res
    html_res = interativo.gerar_html(form, saida_base + ".html")
    html_path = html_res["caminho"] if isinstance(html_res, dict) else html_res

    # artefatos
    pacote = {
        "nascimento/evento": {"data": data, "hora": hora, "local": local},
        "mapa_tradicional": mt,
        "plantas_regentes": mp,
        "ceu_das_culturas": mc,
        "cultura_arquétipa": cultura,
        "sol_signo": png_res.get("sol_signo") if isinstance(png_res, dict) else None,
        "asc_signo": png_res.get("asc_signo") if isinstance(png_res, dict) else None,
        "arquivos": {"png": os.path.basename(png), "html": os.path.basename(html_path)},
    }
    json_path = saida_base + ".json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(pacote, f, ensure_ascii=False, indent=2)

    # tamanhos para não encher disco
    tam = {os.path.basename(b): round(os.path.getsize(b) / 1024, 1)
           for b in (png, html_path, json_path)}
    return pacote, tam


def cmd():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--hora", default="12:00")
    ap.add_argument("--local", required=True)
    ap.add_argument("--cultura", default="folclore-brasileiro")
    ap.add_argument("--tema", default="maré de estrelas")
    ap.add_argument("--feeling", default="esperanca")
    ap.add_argument("--mensaje", default=None,
                    help="frase própria para entrar suave na obra (opcional)")
    ap.add_argument("--saida", default=os.path.join(MAPAS, "mapa-iastro"))
    args = ap.parse_args()
    if not os.path.isdir(os.path.dirname(os.path.abspath(args.saida))):
        os.makedirs(os.path.dirname(os.path.abspath(args.saida)), exist_ok=True)
    pacote, tam = gerar_tudo(args, args.saida)

    print("\n=== Mapa tradicional ===")
    for nome, v in pacote["mapa_tradicional"]["planetas"].items():
        print(f"  {nome:9} {v['signo']:12} {v['graus']}"
              + ("  retro" if v["retrogrado"] else ""))
    print("Asc:", pacote["mapa_tradicional"]["asc"])
    print("\n=== Plantas regentes (todos os corpos → orixá) ===")
    for nome, b in pacote["plantas_regentes"].items():
        noms = " · ".join(p["nome"] for p in b["plantas"]) or "—"
        print(f"  {nome:10} {b['signo']:12} → {b['orixa']} :: {noms}")
    print("\n=== Céu das culturas (catálogo unificado) ===")
    ceu_c = pacote["ceu_das_culturas"]
    n_ceu = len(ceu_c.get("ceu_todas_culturas", {}))
    n_corr = len(ceu_c.get("arquetipos_por_signo", {}))
    print(f"  {n_ceu} culturas de céu (Stellarium + projeto)")
    print(f"  {n_corr} signos com arquétipo más forte por cultura")
    for s, lista in ceu_c.get("arquetipos_por_signo", {}).items():
        top = [f"{a['cultura']}:{a['nome']} ({a['certeza']})" for a in lista[:3]]
        print(f"    {s:12} → " + " | ".join(top if top else ["—"]))
    print("\n=== Artefatos (pequenos) ===")
    for b, kb in tam.items():
        print(f"  {b:28} {kb} KB")
    print("\nPronto. Abra o HTML no navegador para a obra interativa.")


if __name__ == "__main__":
    cmd()