#!/usr/bin/env python3
"""Constrói o banco de arquétipos (SQLite) a partir dos JSON por cultura.

Lê todos os arquivos JSON de /mnt/dados/home-italivre/iastro-ia/arquetipos/
e grava o banco relacional normalizado em arquetipos.db.

Tabelas (esquema relacional):
  arquetipo     — uma ficha por arquétipo (com historia mínima e fonte)
  correspondencia— vínculo chave(planeta/signo) <-> arquétipo (certeza, fonte)
  planta        — planta medicinal/sagrada <-> orixá(s), uso e fonte
  corpo         — melotesia: signo <-> parte do corpo
  fonte         — referências bibliográficas deduplicadas

Uso:
  python3 construir_banco.py
"""
import json
import os
import sqlite3
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(DIR, "arquetipos.db")
CULTURAS = ["zodiaco", "folclore-brasileiro", "afro-brasileiro",
            "indigena", "mapuche", "capixaba", "capixaba-sul", "carioca"]


def _texto(v):
    if v is None:
        return None
    if isinstance(v, (list, tuple)):
        return ", ".join(v)
    return str(v)


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    for t in ("arquetipo", "correspondencia", "planta", "corpo", "fonte", "toponimo", "partido", "telescopio", "imagem_livre", "cultura_ceu"):
        cur.execute(f"DROP TABLE IF EXISTS {t}")

    cur.execute("""
        CREATE TABLE arquetipo (
            id TEXT PRIMARY KEY,
            nome TEXT,
            cultura TEXT,
            elemento TEXT,
            polaridade TEXT,
            modo TEXT,
            tema TEXT,
            simbolo TEXT,
            regiao TEXT,
            regionalismo TEXT,
            historia TEXT,
            fonte TEXT,
            nota TEXT,
            corresponde_a TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE correspondencia (
            chave TEXT,
            cultura TEXT,
            id_arquetipo TEXT,
            nome TEXT,
            certeza TEXT,
            fonte TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE cultura_ceu (
            id TEXT PRIMARY KEY,
            nome TEXT,
            origem TEXT,
            region TEXT,
            classification TEXT,
            n_asterismos INTEGER,
            leitura_signos TEXT,
            comentario TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE planta (
            id TEXT PRIMARY KEY,
            nome TEXT,
            nome_cientifico TEXT,
            nome_ioruba TEXT,
            elemento TEXT,
            orixa TEXT,
            orixa_nota TEXT,
            uso TEXT,
            uso_medicinal TEXT,
            efeito TEXT,
            tradicao TEXT,
            folclore TEXT,
            saber TEXT,
            fonte TEXT,
            link TEXT,
            observacao TEXT,
            enciclopedia TEXT,
            parte_utilizada TEXT,
            preparo TEXT,
            territorio TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE corpo (
            signo TEXT PRIMARY KEY,
            parte TEXT,
            detalhe TEXT,
            fonte TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE fonte (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            texto TEXT UNIQUE
        )
    """)
    cur.execute("""
        CREATE TABLE toponimo (
            id TEXT PRIMARY KEY,
            nome TEXT,
            tipo TEXT,
            territorio TEXT,
            lingua TEXT,
            historia TEXT,
            regiao TEXT,
            fonte TEXT,
            link TEXT,
            corresponde_a TEXT,
            nota TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE partido (
            id TEXT PRIMARY KEY,
            sigla TEXT,
            nome TEXT,
            territorio TEXT,
            signo_chave TEXT,
            planeta_chave TEXT,
            elemento TEXT,
            justificativa TEXT,
            certeza TEXT,
            fonte TEXT,
            corresponde_a TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE telescopio (
            corpo TEXT PRIMARY KEY,
            arquivo TEXT,
            telescopio TEXT,
            ano TEXT,
            marco TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE imagem_livre (
            id TEXT PRIMARY KEY,
            arquivo TEXT,
            titulo TEXT,
            tipo TEXT,
            tema TEXT,
            dominio_publico INTEGER,
            licenca TEXT,
            autor TEXT,
            criador_ref TEXT,
            fonte_url TEXT,
            obra_origem TEXT,
            nota TEXT
        )
    """)

    arquetipos = []
    for cultura in CULTURAS:
        caminho = os.path.join(DIR, f"{cultura}.json")
        if not os.path.exists(caminho):
            print(f"[salta] {cultura}.json não existe")
            continue
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
        for a in dados.get("arquetipos", []):
            arquetipos.append({
                "id": a.get("id"),
                "nome": a.get("nome"),
                "cultura": a.get("cultura", cultura),
                "elemento": a.get("elemento"),
                "polaridade": a.get("polaridade"),
                "modo": a.get("modo"),
                "tema": _texto(a.get("tema")),
                "simbolo": a.get("simbolo"),
                "regiao": a.get("regiao"),
                "regionalismo": a.get("regionalismo"),
                "historia": a.get("historia"),
                "fonte": a.get("fonte"),
                "nota": a.get("nota"),
                "corresponde_a": a.get("corresponde_a"),
            })

    with open(os.path.join(DIR, "correspondencias.json"), encoding="utf-8") as f:
        corr_dict = json.load(f).get("correspondencias", {})
    correspondencias = []
    for chave, lista in corr_dict.items():
        for c in lista:
            correspondencias.append({
                "chave": chave,
                "cultura": c.get("cultura"),
                "id_arquetipo": c.get("id"),
                "nome": c.get("nome"),
                "certeza": c.get("certeza"),
                "fonte": c.get("fonte"),
            })

    plantas = []
    cam = os.path.join(DIR, "plantas.json")
    if os.path.exists(cam):
        with open(cam, encoding="utf-8") as f:
            for p in json.load(f).get("plantas", []):
                plantas.append({
                    "id": p.get("id"),
                    "nome": p.get("nome"),
                    "nome_cientifico": p.get("nome_cientifico"),
                    "nome_ioruba": p.get("nome_ioruba"),
                    "elemento": p.get("elemento"),
                    "orixa": _texto(p.get("orixa")),
                    "orixa_nota": p.get("orixa_nota"),
                    "uso": p.get("uso"),
                    "uso_medicinal": p.get("uso_medicinal"),
                    "efeito": p.get("efeito"),
                    "tradicao": p.get("tradicao"),
                    "folclore": p.get("folclore"),
                    "saber": p.get("saber"),
                    "fonte": p.get("fonte"),
                    "link": p.get("link"),
                    "observacao": p.get("observacao"),
                    "enciclopedia": p.get("enciclopedia"),
                    "parte_utilizada": p.get("parte_utilizada"),
                    "preparo": p.get("preparo"),
                    "territorio": p.get("territorio"),
                })
    # Catálogo ampliado: ervas dos orixás (gerado por gerar_ervas_orixas.py)
    cam = os.path.join(DIR, "ervas-orixas.json")
    if os.path.exists(cam):
        with open(cam, encoding="utf-8") as f:
            for e in json.load(f).get("ervas", []):
                plantas.append({
                    "id": e.get("id"),
                    "nome": e.get("nome"),
                    "nome_cientifico": e.get("nome_cientifico"),
                    "nome_ioruba": e.get("nome_ioruba"),
                    "elemento": e.get("elemento"),
                    "orixa": _texto(e.get("orixa")),
                    "orixa_nota": e.get("orixa_nota"),
                    "uso": e.get("uso"),
                    "uso_medicinal": e.get("uso_medicinal"),
                    "efeito": e.get("efeito"),
                    "tradicao": e.get("tradicao"),
                    "folclore": e.get("folclore"),
                    "saber": e.get("saber"),
                    "fonte": e.get("fonte"),
                    "link": e.get("link"),
                    "observacao": e.get("observacao"),
                    "enciclopedia": e.get("enciclopedia"),
                    "parte_utilizada": e.get("parte_utilizada"),
                    "preparo": e.get("preparo"),
                    "territorio": e.get("territorio"),
                })

    corpos = []
    cam = os.path.join(DIR, "corpo-humano.json")
    if os.path.exists(cam):
        with open(cam, encoding="utf-8") as f:
            for c in json.load(f).get("corpos", []):
                corpos.append({
                    "signo": c.get("signo"),
                    "parte": c.get("parte"),
                    "detalhe": c.get("detalhe"),
                    "fonte": c.get("fonte"),
                })

    toponimos = []
    cam = os.path.join(DIR, "toponimos.json")
    if os.path.exists(cam):
        with open(cam, encoding="utf-8") as f:
            for t in json.load(f).get("toponimos", []):
                toponimos.append({
                    "id": t.get("id"),
                    "nome": t.get("nome"),
                    "tipo": t.get("tipo"),
                    "territorio": t.get("territorio"),
                    "lingua": t.get("lingua"),
                    "historia": t.get("historia"),
                    "regiao": t.get("regiao"),
                    "fonte": t.get("fonte"),
                    "link": t.get("link"),
                    "corresponde_a": t.get("corresponde_a"),
                    "nota": t.get("nota"),
                })

    partidos = []
    cam = os.path.join(DIR, "partidos.json")
    if os.path.exists(cam):
        with open(cam, encoding="utf-8") as f:
            for p in json.load(f).get("partidos", []):
                partidos.append({
                    "id": p.get("id"),
                    "sigla": p.get("sigla"),
                    "nome": p.get("nome"),
                    "territorio": p.get("territorio"),
                    "signo_chave": p.get("signo_chave"),
                    "planeta_chave": p.get("planeta_chave"),
                    "elemento": p.get("elemento"),
                    "justificativa": p.get("justificativa"),
                    "certeza": p.get("certeza"),
                    "fonte": p.get("fonte"),
                    "corresponde_a": p.get("corresponde_a"),
                })

    telescopios = []
    cam = os.path.join(DIR, "telescopios.json")
    if os.path.exists(cam):
        with open(cam, encoding="utf-8") as f:
            data = json.load(f)
            for corpo, info in data.get("imagens_por_corpo", {}).items():
                telescopios.append({
                    "corpo": corpo,
                    "arquivo": info.get("arquivo"),
                    "telescopio": info.get("telescopio"),
                    "ano": info.get("ano"),
                    "marco": info.get("marco"),
                })

    cur.executemany(
        """INSERT INTO arquetipo VALUES
           (:id,:nome,:cultura,:elemento,:polaridade,:modo,:tema,:simbolo,
            :regiao,:regionalismo,:historia,:fonte,:nota,:corresponde_a)""",
        arquetipos)
    cur.executemany(
        """INSERT INTO correspondencia VALUES
           (:chave,:cultura,:id_arquetipo,:nome,:certeza,:fonte)""",
        correspondencias)
    cur.executemany(
        """INSERT INTO planta VALUES
           (:id,:nome,:nome_cientifico,:nome_ioruba,:elemento,:orixa,:orixa_nota,
            :uso,:uso_medicinal,:efeito,:tradicao,:folclore,:saber,:fonte,:link,
            :observacao,:enciclopedia,:parte_utilizada,:preparo,:territorio)""",
        plantas)
    cur.executemany(
        """INSERT INTO corpo VALUES
           (:signo,:parte,:detalhe,:fonte)""",
        corpos)
    cur.executemany(
        """INSERT INTO toponimo VALUES
           (:id,:nome,:tipo,:territorio,:lingua,:historia,:regiao,
            :fonte,:link,:corresponde_a,:nota)""",
        toponimos)
    cur.executemany(
        """INSERT INTO partido VALUES
           (:id,:sigla,:nome,:territorio,:signo_chave,:planeta_chave,
            :elemento,:justificativa,:certeza,:fonte,:corresponde_a)""",
        partidos)
    cur.executemany(
        """INSERT INTO telescopio VALUES
           (:corpo,:arquivo,:telescopio,:ano,:marco)""",
        telescopios)

    imagens_livres = []
    cam_imagens = os.path.join(DIR, "imagens-arquetipos.json")
    if os.path.exists(cam_imagens):
        with open(cam_imagens, encoding="utf-8") as f:
            dados_img = json.load(f)
            for im in dados_img.get("imagens", []):
                imagens_livres.append({
                    "id": im.get("id"),
                    "arquivo": im.get("arquivo"),
                    "titulo": im.get("titulo"),
                    "tipo": im.get("tipo"),
                    "tema": _texto(im.get("tema")),
                    "dominio_publico": 1 if im.get("dominio_publico") else 0,
                    "licenca": im.get("licenca"),
                    "autor": im.get("autor"),
                    "criador_ref": im.get("criador_ref"),
                    "fonte_url": im.get("fonte_url"),
                    "obra_origem": im.get("obra_origem"),
                    "nota": im.get("nota"),
                })

    cur.executemany(
        """INSERT INTO imagem_livre VALUES
           (:id,:arquivo,:titulo,:tipo,:tema,:dominio_publico,:licenca,
            :autor,:criador_ref,:fonte_url,:obra_origem,:nota)""",
        imagens_livres)

    # ---- Catálogo unificado de CULTURAS DO CÉU ----
    # Todas: (a) as 59 que Stellarium já traz (livres/GPL), e (b) as NOSSAS,
    # já com LEITURA signo→asterismo (tupi, tukano, mapuche, capixaba-sul) +
    # as que derivamos dos arquétipos (indigena, folclore, orixa — via
    # correspondencias). Tudo em UMA tabela: consultable ao fazer o mapa.
    sys.path.insert(0, "/mnt/dados/ephemeris")
    import ceu as _ceu
    culturas_ceu = []
    ni = 0
    for nome in _ceu.listar_culturas():
        ni += 1
        try:
            ident, lista = _ceu.extrair_asterismos(nome)
        except Exception:
            ident, lista = nome, []
        culturas_ceu.append({
            "id": nome,
            "nome": nome,
            "origem": "stellarium",
            "region": "",
            "classification": "livre (GPL)",
            "n_asterismos": len(lista),
            "leitura_signos": "",
            "comentario": "Catálogo estelar livre do Stellarium (HIP/GPL); signo→asterismo por pesquisar s/dados.",
        })
    # NOSSAS: LEITURA signo→asterismo documentada (ver ceu.LEITURA) + arquétipos
    for cultura, tabela in _ceu.LEITURA.items():
        signos_abertos = [s for s, a in tabela.items() if a and not str(a).startswith(("—", "("))]
        culturas_ceu.append({
            "id": f"nossa:{cultura}",
            "nome": cultura,
            "origem": "projeto",
            "region": "Brasil" if "capixaba" in cultura else "",
            "classification": "ethnographic",
            "n_asterismos": len(signos_abertos),
            "leitura_signos": json.dumps(tabela, ensure_ascii=False),
            "comentario": "Leitura signo→asterismo do projeto (Hipóteses, certeza baixa/media).",
        })
    # arquétipos do banco (indigena, folclore, orixa...) contam como leitura de
    # céu SÍMBÓLICA: derivada das correspondências signo→arquétipo (cadastro).
    SIGNOS_CANONICOS = ["aries","touro","gemeos","cancer","leao","virgem",
                        "libra","escorpiao","sagitario","capricornio","aquario","peixes"]
    def _sin_acentos(t):
        _m = str.maketrans("áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
                           "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC")
        return (t or "").translate(_m).lower()
    forte_por_cultura = {}
    for c in correspondencias:
        cl = c.get("chave") or ""
        if _sin_acentos(cl) not in SIGNOS_CANONICOS:
            continue
        cult = c.get("cultura") or ""
        force = {"alta": 0, "media": 1, "baixa": 2}.get(c.get("certeza"), 9)
        key = (cult, _sin_acentos(cl))
        if key not in forte_por_cultura or force < forte_por_cultura[key][0]:
            forte_por_cultura[key] = (force, c.get("nome") or c.get("id_arquetipo", ""))
    LEITURA_COM_ACCENTO = {"aries":"Áries","touro":"Touro","gemeos":"Gêmeos",
                           "cancer":"Câncer","leao":"Leão","virgem":"Virgem",
                           "libra":"Libra","escorpiao":"Escorpião","sagitario":"Sagitário",
                           "capricornio":"Capricórnio","aquario":"Aquário","peixes":"Peixes"}
    leituras_derivadas = {}
    for cult in sorted({c["cultura"] for c in correspondencias if c.get("cultura")}):
        tab = {}
        for sig in SIGNOS_CANONICOS:
            f = forte_por_cultura.get((cult, sig))
            tab[LEITURA_COM_ACCENTO[sig]] = (f[1] if f else "—")
        leituras_derivadas[cult] = tab
    for cult, tab in leituras_derivadas.items():
        if any(c["id"] == f"nossa:{cult}" for c in culturas_ceu):
            continue
        signos_abiertos = [s for s, a in tab.items() if a and a != "—"]
        culturas_ceu.append({
            "id": f"nossa:{cult}",
            "nome": cult,
            "origem": "projeto",
            "region": "",
            "classification": "arquetipos",
            "n_asterismos": len(signos_abiertos),
            "leitura_signos": json.dumps(tab, ensure_ascii=False),
            "comentario": "Leitura simbólica signo→arquétipo derivada das correspondencias (Hipóteses, certeza).",
        })
    cur.executemany(
        """INSERT OR REPLACE INTO cultura_ceu VALUES
           (:id,:nome,:origem,:region,:classification,:n_asterismos,
            :leitura_signos,:comentario)""",
        culturas_ceu)

    # deduplica fontes
    textos = {a["fonte"] for a in arquetipos if a.get("fonte")}
    textos |= {c["fonte"] for c in correspondencias if c.get("fonte")}
    textos |= {p["fonte"] for p in plantas if p.get("fonte")}
    textos |= {c["fonte"] for c in corpos if c.get("fonte")}
    textos |= {t["fonte"] for t in toponimos if t.get("fonte")}
    textos |= {p["fonte"] for p in partidos if p.get("fonte")}
    cur.executemany(
        "INSERT OR IGNORE INTO fonte (texto) VALUES (?)",
        [(t,) for t in sorted(t for t in textos if t)])

    # valida ids das correspondências
    ids = {a["id"] for a in arquetipos}
    sumiu = [c for c in correspondencias if c["id_arquetipo"] not in ids]
    for c in sumiu:
        print(f"[aviso] correspondência aponta p/ id inexistente: {c['id_arquetipo']}")

    conn.commit()
    cur.execute("SELECT cultura, COUNT(*) FROM arquetipo GROUP BY cultura")
    print("Arquétipos por cultura:")
    for cultura, n in cur.fetchall():
        print(f"  {cultura:24s} {n}")
    print(f"Correspondências : {len(correspondencias)}")
    print(f"Plantas          : {len(plantas)}")
    print(f"Melotesia (corpo): {len(corpos)}")
    print(f"Topônimos/hist.  : {len(toponimos)}")
    print(f"Partidos (panor. ): {len(partidos)}")
    print(f"Telescópios/fotos : {len(telescopios)}")
    print(f"Imagens livres    : {len(imagens_livres)}")
    cur.execute("SELECT COUNT(*) FROM cultura_ceu WHERE origem='stellarium'")
    print(f"Culturas de céu   : {cur.fetchone()[0]} (Stellarium)")
    cur.execute("SELECT COUNT(*) FROM cultura_ceu WHERE origem='projeto'")
    print(f"                     + {cur.fetchone()[0]} (projeto/arquétipos)")
    cur.execute("SELECT COUNT(*) FROM fonte")
    print(f"Fontes únicas    : {cur.fetchone()[0]}")
    if sumiu:
        print(f"AVISOS (ids órfãos): {len(sumiu)}")
    conn.close()
    print(f"\nBanco salvo em: {DB}")


if __name__ == "__main__":
    main()