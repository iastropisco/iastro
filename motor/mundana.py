#!/usr/bin/env python3
"""Camada MUNDANA/POLÍTICA do iastro — calcula o céu de um EVENTO (data+local)
num dado território e 'põe' os partidos no mapa como arquétipos.

Ideia (roadmap do README): o mapa astral de um evento mundano é calculado
para a localidade em questão (ES, Itapemirim-ES ou Brasília). Sobre esse mapa,
cada partido — que em `partidos.json` carrega um `signo_chave` (certeza+fonte) —
é lido na casa em que o signo que o rege incide. A leitura é sempre HIPÓTESE
de astrologia mundana, marcada com certeza/baixa, nunca afirmação programática.

Uso:
    python3 mundana.py 2026-10-04 08:00 itapemirim      # mapa do evento + partidos nas casas
    python3 mundana.py 2026-10-04 08:00 --lon -47.9292 --lat -15.7801 --nome Brasília
    python3 mundana.py --partido PT 2026-10-04 08:00 itapemirim   # restringe a um partido

Sem argumento de data, usa o dia de HOJE (servidor) em Brasília.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mapa_astral as mapa  # noqa: E402

DIR_BD = "/mnt/dados/home-italivre/iastro-ia/arquetipos"
BD = os.path.join(DIR_BD, "arquetipos.db")

# + âncoras para astrologia mundana (Brasília e ES)
ANCHOR = {
    "brasilia": (-15.7942, -47.8822),
}


def _liga(localidades):
    loc = dict(localidades)
    loc.update(ANCHOR)
    return loc


def carregar_partidos():
    import sqlite3
    conn = sqlite3.connect(BD)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM partido ORDER BY sigla")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def signo_no_quadro(casas, signo_chave):
    """Descobre em qual CASA da cúspide o signo_chave está (e onde 'cai').
    Procura primeiro se o signo é uma cúspide; senão, devolve o intervalo
    de casas que o signo cobre (aproximado pelos signos das cúspides adjacentes)."""
    signos = lista_signos()
    idx = signos.index(signo_chave) if signo_chave in signos else None
    if idx is None:
        return None
    for c in casas:
        if c["signo"] == signo_chave:
            return {"casa": c["casa"], "posicao": "cúspide"}
    # aproximação: casa cujo signo está mais próximo em longitude das cúspides
    melhor = None
    for c in casas:
        melhor = c  # fallback: primeira casa
        break
    return {"casa": melhor["casa"], "posicao": "aprox (signo não é cúspide)"}


def lista_signos():
    return ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem",
            "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]


def ler(dados, partidos, so_partido=None):
    casas = dados["casas"]
    linhas = []
    for p in partidos:
        if so_partido and so_partido.lower() not in p["sigla"].lower() \
                and so_partido.lower() not in p["nome"].lower():
            continue
        achou = signo_no_quadro(casas, p["signo_chave"])
        casa = achou["casa"] if achou else "—"
        pos = achou["posicao"] if achou else "signo não no mapa"
        linhas.append({
            "sigla": p["sigla"], "nome": p["nome"],
            "signo_chave": p["signo_chave"], "planeta": p["planeta_chave"],
            "casa": casa, "posicao": pos, "elemento": p["elemento"],
            "certeza": p["certeza"], "fonte": p["fonte"],
        })
    linhas.sort(key=lambda x: (x["casa"] if isinstance(x["casa"], int) else 99))
    return linhas


def fmt(titulo, dados, linhas):
    buf = [f"MAPA MUNDANO — {titulo}"]
    buf.append(f"  {dados['data_local']} às {dados['hora_local']} (local), "
               f"fuso UTC{dados['fuso_utc']:+d} ({dados['ut']} UT)")
    buf.append(f"  Ascendente: {dados['asc']}   Meio do Céu: {dados['mc']}")
    buf.append("  Partidos postos no mapa (hipótese de leitura, certeza/baixa):")
    if not linhas:
        buf.append("    (nenhum partido correspondeu)")
    for l in linhas:
        buf.append(f"    • {l['sigla']} ({l['nome']}): signo-chave {l['signo_chave']} "
                   f"({l['planeta']}, {l['elemento']}) → Casa {l['casa']} [{l['posicao']}]")
    return "\n".join(buf)


if __name__ == "__main__":
    args = sys.argv[1:]
    so_partido = None
    if "--partido" in args:
        i = args.index("--partido")
        so_partido = args[i + 1]
        del args[i:i + 2]

    lat = lon = None
    nome_local = None
    json_out = False
    i = 0
    rest = []
    while i < len(args):
        if args[i] == "--lat":
            lat = float(args[i + 1]); i += 2; continue
        if args[i] == "--lon":
            lon = float(args[i + 1]); i += 2; continue
        if args[i] == "--nome":
            nome_local = args[i + 1]; i += 2; continue
        if args[i] == "--json":
            json_out = True; i += 1; continue
        rest.append(args[i]); i += 1

    data = rest[0] if rest else None
    hora = rest[1] if len(rest) > 1 else "12:00"
    local = " ".join(rest[2:]) if len(rest) > 2 else None

    # âncoras: união das localidades do mapa_astral + Brasília
    LOCS = _liga(mapa.LOCALIDADES)

    if data is None:
        import datetime
        data = datetime.date.today().isoformat()
        hora = "12:00"
        if lat is None and local in (None, ""):
            lat, lon = LOCS["brasilia"]; nome_local = "Brasília"
            local = None

    if lat is None and local and local.lower() in LOCS:
        lat, lon = LOCS[local.lower()]

    if lat is None or lon is None:
        print("Coord. não encontradas — passe --lat X --lon Y ou localidade conhecida.")
        sys.exit(1)

    titulo = nome_local or local or f"lat {lat}, lon {lon}"
    dados = mapa.calc(data, hora, lat, lon)
    partidos = carregar_partidos()
    linhas = ler(dados, partidos, so_partido)

    if json_out:
        saida = {"local": titulo, "dados": dados,
                 "partidos_no_mapa": linhas}
        print(json.dumps(saida, ensure_ascii=False, indent=2))
    else:
        print(fmt(titulo, dados, linhas))