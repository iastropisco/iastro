#!/usr/bin/env python3
"""Cruzamento nascimento <-> planta regente (base pronta e funcionando).

A ideia do projeto (multi-cultura): do dia/hora/local do nascimento tiramos o
mapa (efeméride Swiss Ephemeris); do signo/planeta chegamos ao ORIXÁ (nossa
tabela afro-brasileiro, certeza+fonte); do orixá chegamos às PLANTAS que o
regem (tabela `planta`) — com o nome científico e os usos na medicina popular.
Cada planta vem de enciclopédias/obras de referência de domínio público e
tradição; ver `planta.fonte` no banco.

Honestidade: as associações orixá<->signo e orixá<->planta seguem a "linguagem"
do projeto — hipóteses com `certeza`+`fonte`, não dogmas. Nada aqui substitui
o cuidado médico; é memória cultural e etnobotânica.

Uso:
    venv/bin/python flora.py --data 1990-01-15 --hora 08:00 --local "rio de janeiro"
"""
import argparse
import os
import sqlite3
import sys

sys.path.insert(0, "/mnt/dados/ephemeris")
DB = "/mnt/dados/home-italivre/iastro-ia/arquetipos/arquetipos.db"


def _con():
    if not os.path.exists(DB):
        raise FileNotFoundError("banco não existe: " + DB)
    return sqlite3.connect(DB)


def _sem_acentos(t):
    """Normaliza acentos: 'Capricórnio'->'capricornio' (chave do banco)."""
    mapa = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
        "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC")
    return t.translate(mapa).lower()


def orixa_do_signo(cur, signo):
    """O(orixá) do signo via correspondências afro-brasileiras do banco."""
    chave = _sem_acentos(signo)
    cur.execute(
        """SELECT ar.nome, co.certeza, co.fonte FROM correspondencia co
           JOIN arquetipo ar ON ar.id = co.id_arquetipo
           WHERE co.chave=? AND ar.cultura LIKE '%afro%'""",
        (chave,))
    linha = cur.fetchone()
    return linha or ("Oxalá", "baixa", "Hipótese do projeto (regência geral do Sol)")


def plantas_do_orixa(cur, orixa):
    """Plantas associadas ao orixá (campo `orixa` da tabela planta)."""
    # o banco guarda o nome canônico (ex.: 'Osanyin'); o archetype afro pode
    # trazer 'Osanyin (Ossaim)'. Normalizamos e tentamos vários termos.
    termos = [orixa, orixa.split(" (")[0]]
    for termo in termos:
        cur.execute(
            "SELECT nome, nome_cientifico, uso_medicinal, uso, elemento, fonte, enciclopedia, saber, parte_utilizada, preparo, territorio "
            "FROM planta WHERE orixa LIKE ? ORDER BY nome",
            (f"%{termo.strip()}%",))
        rows = cur.fetchall()
        if rows:
            # deduplica por nome: o banco tem a MESMA planta em mais de uma
            # linha (orixás/descrições ligeiramente diferentes) — sem isso a
            # lista repete nomes e fica sem sentido no mapa
            vistos, unicos = set(), []
            for r in rows:
                chave = (r[0] or "").strip().lower()
                if chave in vistos:
                    continue
                vistos.add(chave)
                unicos.append(r)
            return unicos
    return []


def planta_regente(cur, signo):
    """Vínculo nascimento->planta: do signo ao orixá e à(s) planta(s)."""
    orixa, certeza, fonte = orixa_do_signo(cur, signo)
    plantas = plantas_do_orixa(cur, orixa)
    return {"orixa": orixa, "certeza": certeza, "fonte": fonte,
            "plantas": plantas}


def cmd():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--hora", default="12:00")
    ap.add_argument("--local", required=True)
    args = ap.parse_args()

    sys.path.insert(0, "/mnt/dados/ephemeris")
    import mapa_astral
    coords = mapa_astral.LOCALIDADES.get(args.local)
    if not coords:
        raise ValueError("Local desconhecido: " + args.local)
    lat, lon = coords[0], coords[1]
    chart = mapa_astral.calc(args.data, args.hora, lat, lon, tz_horas=-3)

    # pontos do mapa que "regem" a pessoa: Sol, Lua e regentes clássicos
    pontos = ["Sol", "Lua", "Mercúrio", "Vênus", "Marte"]
    con = _con()
    cur = con.cursor()
    for pnome in pontos:
        signo = chart["planetas"][pnome]["signo"]
        r = planta_regente(cur, signo)
        print(f"\n===== {pnome} em {signo} =====")
        print(f"Orixá regente : {r['orixa']}  ({r['certeza']})")
        print(f"Fonte         : {r['fonte']}")
        plantas = r["plantas"] or []
        if not plantas:
            print("  (nenhuma planta cadastrada para este orixá — a ampliar)")
        for p in plantas:
            nome, sci, uso_med, uso, elem, fonte, enc, saber = p
            print(f"  • {nome}")
            if sci: print(f"      científico: {sci}")
            if uso_med: print(f"      medicina popular: {uso_med}")
            if elem: print(f"      elemento: {elem}")
            if enc: print(f"      enciclopédia (PD): {enc}")
            if saber: print(f"      saber: {saber}")
    con.close()


if __name__ == "__main__":
    cmd()