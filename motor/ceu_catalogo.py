#!/usr/bin/env python3
"""Catálogo unificado das CULTURAS DO CÉU para o mapa iastro.

Centraliza todo o acervo nas camadas pedidas:

  1. CÉU REAL — TODAS as culturas que Stellarium disponibiliza (59, livres/GPL)
     + as nossas (projeto) já com LEITURA signo→asterismo (tupi, tukano,
     mapuche, capixaba-sul, indigena, folclore, orixa...). vive na tabela
     `cultura_ceu` do banco (ver construir_banco.py).

  2. ARQUÉTIPOS POR CORRESPONDENCIA — para cada signo/planeta, o arquétipo
     MAIS FORTE de cada cultura segundo `certeza` (ver correspondencia.db).

  3. PLANTAS POR SABER POPULAR — do nascimento → signo → orixá → planta(s),
     com uso medicinal e enciclopédia de domínio público (ver flora.py).

Este módulo é a ÚNICA porta de entrada para "extrair um mapa do iastro":
    venv/bin/python ceu_catalogo.py \\
        --data 1990-01-15 --hora 08:00 --local "itapemirim"
que devolve um JSON completo (tradicional + céu de todas + arquétipos +
plantas) em `--saida` (default mapa-iastro.json).
"""
import argparse
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import caminhos

DB = caminhos.DB
EPH = caminhos.MOTOR

_ORDEN = {"alta": 0, "media": 1, "baixa": 2}
CERTS = {"alta", "media", "baixa"}

_ASSIMILACAO = os.path.join(EPH, "assimilacao_ceu.json")


def _signo_key(s):
    """'Capricórnio'/'Capricornio' -> 'capricornio' (chave canónica sem acento)."""
    return _sem_acentos(s or "")


def _cargar_assimilacao():
    """Capa GEOMÉTRICA: asterismos de cada cultura clássica ligados ao signo
    ocidental pela POSIÇÃO real das estrelas (ver assemelhar_ceu.py).

    Retorna {cultura: {signo_es: [{asterismo, ingles, lon_eclip}, ...]}}.
    Distinta das correspondências etnográficas; fala só de "onde está",
    jamais de "que é". Nunca se funde com arquetipos_por_signo."""
    try:
        with open(_ASSIMILACAO, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _sem_acentos(t):
    mapa = str.maketrans(
        "áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
        "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC")
    return (t or "").translate(mapa).lower()


def _local_canonico(local):
    import mapa_astral
    alvo = _sem_acentos(local)
    for chave in mapa_astral.LOCALIDADES:
        if _sem_acentos(chave) == alvo:
            return chave
    return None


def catalogar_culturas(cur):
    """Todas as culturas céu da DB (Stellarium + projeto), com nº asterismos."""
    cur.execute("SELECT id,nome,origem,region,classification,n_asterismos FROM cultura_ceu ORDER BY origem,nome")
    return [tuple(r) for r in cur.fetchall()]


def culturas_stellarium(cur):
    cur.execute("SELECT id FROM cultura_ceu WHERE origem='stellarium' ORDER BY nome")
    return [r[0] for r in cur.fetchall()]


def leitura_por_cultura(cur, id_ceu):
    cur.execute("SELECT leitura_signos FROM cultura_ceu WHERE id=?", (id_ceu,))
    r = cur.fetchone()
    if not r or not r[0]:
        return {}
    try:
        return json.loads(r[0])
    except Exception:
        return {}


def arquetipos_fuertes(cur, chave=None):
    """O arquétipo MAIS FORTE por (chave, cultura) segundo certeza.

    chave = signo (e.g. 'escorpiao') ou planeta. Sem chave: todo; con chave: só ese.
    Retorna lista de dicts {chave,cultura,nome,id,certeza,fonte} ordenado.
    """
    sql = ("SELECT chave,cultura,nome,id_arquetipo,certeza,fonte "
           "FROM correspondencia")
    args = ()
    if chave:
        sql += " WHERE chave=?"
        args = (_sem_acentos(chave),)
    rows = cur.execute(sql, args).fetchall()
    # por cultura, quedamos com o + forte (mejor certeza)
    melhor = {}
    for c, cultura, nome, ida, certeza, fonte in rows:
        cl = _ORDEN.get(certeza, 9)
        key = (c, cultura)
        if key not in melhor or cl < _ORDEN.get(melhor[key][4], 9):
            melhor[key] = (c, cultura, nome, ida, certeza, fonte)
    out = []
    for (c, cultura), v in sorted(melhor.items(), key=lambda kv: (kv[0][0], _ORDEN.get(kv[1][4], 9))):
        out.append({
            "chave": c, "cultura": cultura, "nome": v[2],
            "id_arquetipo": v[3], "certeza": v[4], "fonte": v[5],
        })
    return out


def arquetipos_del_signo(cur, signo):
    """Arquetipos de TODAS as culturas para um signo, ordenado por força."""
    return [a for a in arquetipos_fuertes(cur, signo)]


def plantas_por_saber(cur, signo):
    import flora
    r = flora.planta_regente(cur, signo)
    return {
        "orixa": r["orixa"], "certeza": r["certeza"], "fonte": r["fonte"],
        "plantas": [{"nome": p[0], "cientifico": p[1], "uso_medicinal": p[2],
                     "elemento": p[4], "fonte_etno": p[5], "enciclopedia_pd": p[6]}
                    for p in r["plantas"]],
    }


def leitura_geometrica(assim, cultura, chave_signo):
    """Para uma cultura Stellarium, o asterismo cujas estrelas se situan num
    primeiro lugar no signo ocidental `chave_signo` (longitude eclíptica).
    Fala só de "onde está", não de "que é"."""
    por_signo = assim.get(cultura, {})
    lista = por_signo.get(chave_signo)
    if not lista:
        return None
    return lista[0].get("asterismo")


def mapa_iastro(data, hora, local, cultura_principal="folclore-brasileiro"):
    """Extrai o mapa iastro completo: todas as camadas unificadas."""
    sys.path.insert(0, EPH)
    import mapa_astral, ceu

    con = sqlite3.connect(DB)
    cur = con.cursor()
    assim = _cargar_assimilacao()

    local_c = _local_canonico(local) or local
    coords = mapa_astral.LOCALIDADES.get(local_c)
    if not coords:
        raise ValueError("Local desconhecido: " + str(local))
    lat, lon = coords[0], coords[1]
    astros = mapa_astral.calc(data, hora, lat, lon,
                              tz_horas=mapa_astral.tz_do_local(local_c))

    signos = [p["signo"] for p in astros["planetas"].values()]
    asc_bruto = str(astros.get("asc", ""))
    asc = asc_bruto.split(" ")[0] if asc_bruto else ""

    def res(p):
        return {"signo": p.get("signo"), "graus": f"{p.get('graus',0)}°{p.get('min',0):02d}'",
                "retrogrado": p.get("retrogrado", False)}

    planetas = {n: res(p) for n, p in astros["planetas"].items()}

    # 1) céu: por TODAS as culturas (Stellarium + projeto), o asterismo de Sol/Asc/Lua
    cielos = {}
    geof = {}
    for (cid, nome, origem, region, clasif, n_aster) in catalogar_culturas(cur):
        tab = leitura_por_cultura(cur, cid)
        def _sig(p):
            return p.get("signo", "") if isinstance(p, dict) else str(p)
        sol_sig, asc_sig, lua_sig = (_sig(planetas.get("Sol", {})),
                                     asc, _sig(planetas.get("Lua", {})))
        if not tab:
            # só Stellarium, ainda sem leitura etnográfica: damos o asterismo
            # GEOMÉTRICO (onde está), nunca o significado.
            geo = assim.get(cid, {})
            def _g(ch):
                lista = geo.get(_signo_key(ch))
                return lista[0].get("asterismo") if lista else None
            geo_sol, geo_asc, geo_lua = _g(sol_sig), _g(asc_sig), _g(lua_sig)
            tiene_geo = any(x for x in (geo_sol, geo_asc, geo_lua))
            cielos[cid] = {
                "origen": origem, "asterismos": n_aster,
                "por_pesquisar": not tiene_geo,
                "ligacao": "geometrica" if tiene_geo else None,
                "Sol": {"signo": sol_sig, "asterismo": geo_sol or "—"},
                "Asc": {"signo": asc_sig, "asterismo": geo_asc or "—"},
                "Lua": {"signo": lua_sig, "asterismo": geo_lua or "—"},
            }
            if tiene_geo:
                geof[cid] = {s: [a["asterismo"] for a in l]
                             for s, l in geo.items()}
            continue
        cielos[cid] = {
            "origen": origem,
            "por_pesquisar": False,
            "ligacao": "etnografica",
            "Sol": {"signo": sol_sig, "asterismo": tab.get(sol_sig, "—")},
            "Asc": {"signo": asc_sig, "asterismo": tab.get(asc_sig, "—")},
            "Lua": {"signo": lua_sig, "asterismo": tab.get(lua_sig, "—")},
        }

    # 2) arquétipos mais fortes por signo (todas as culturas)
    fuertes = {}
    for s in sorted(set(signos + [asc])):
        fuertes[s] = arquetipos_del_signo(cur, s)

    # 3) plantas por saber popular (por regente)
    plantas = {}
    for n in ("Sol", "Lua", "Mercúrio", "Vênus", "Marte"):
        signo = planetas[n]["signo"] if isinstance(planetas.get(n), dict) else "?"
        plantas[n] = {"signo": signo, **plantas_por_saber(cur, signo)}

    con.close()

    return {
        "nascimento": {"data": data, "hora": hora, "local": local_c,
                       "lat": lat, "lon": lon},
        "mapa_tradicional": {"planetas": planetas, "asc": asc},
        "ceu_todas_culturas": cielos,
        "assimilacao_geometrica": geof,
        "arquetipos_por_signo": fuertes,
        "plantas_por_saber": plantas,
        "cultura_principal": cultura_principal,
        "aviso": ("Vínculos são hipóteses do projeto com certeza+fonte, "
                  "não doutrina. Asterismos Stellarium sem leitura "
                  "etnográfica: a assimilação GEOMÉTRICA (onde está cada "
                  "asterismo no zodíaco) é posicional e confiável; o "
                  "significado cultural continua por_pesquisar."),
    }


def cmd():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--hora", default="12:00")
    ap.add_argument("--local", required=True)
    ap.add_argument("--cultura", default="folclore-brasileiro")
    ap.add_argument("--saida", default="/mnt/dados/home-italivre/iastro-ia/mapas/mapa-iastro.json")
    args = ap.parse_args()

    m = mapa_iastro(args.data, args.hora, args.local, args.cultura)
    os.makedirs(os.path.dirname(os.path.abspath(args.saida)), exist_ok=True)
    with open(args.saida, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)

    import sqlite3
    con = sqlite3.connect(DB); cur = con.cursor()
    print("=== CULTURAS DO CÉU (catálogo unificado) ===")
    print(f"  {len(culturas_stellarium(cur))} Stellarium + proyecto (ver arquetipos_por_signo)")
    print("\n=== Mapa tradicional ===")
    for n, v in m["mapa_tradicional"]["planetas"].items():
        print(f"  {n:9} {v['signo']:12} {v['graus']}" + ("  retro" if v["retrogrado"] else ""))
    print("  Asc:", m["mapa_tradicional"]["asc"])
    print("\n=== Arquétipos mais fortes por signo (por cultura) ===")
    for s, lista in m["arquetipos_por_signo"].items():
        top = [f"{a['cultura']}:{a['nome']} ({a['certeza']})" for a in lista[:3]]
        print(f"  {s:12} → " + " | ".join(top if top else ["—"]))
    print("\n=== Plantas por saber popular (Sol→planta) ===")
    for n, b in m["plantas_por_saber"].items():
        noms = " · ".join(p["nome"] for p in b["plantas"]) or "—"
        print(f"  {n:8} {b['signo']:12} → {b['orixa']} :: {noms}")
    print(f"\nGravado: {args.saida}")


if __name__ == "__main__":
    cmd()