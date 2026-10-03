#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Busca e baixa, da Wikimedia Commons, imagens de domínio público / CC para
os ARQUÉTIPOS do mapa que ainda não têm retrato (figura no medalhão).

Uso:
    python3 buscar_arquetipos.py                # roda todos os alvos
    python3 buscar_arquetipos.py tatu matinta   # só estes (nome/chave)

Resultado:
  * grava <chave>.png em mapas/images-livres/arquétipos/
  * registra a licença/fonte em arquetipos/arquetipos.db (tabela imagem_livre)
  * imprime o trecho de ARQ_IMAGEM para colar em colagem.py
"""
import argparse
import io
import json
import os
import sqlite3
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

API = "https://commons.wikimedia.org/w/api.php"
UA = "iastro-arquetipos/1.0 (pesquisa de imagens livres para mapa astrológico)"
DIR_PD = os.path.join("/mnt/dados/home-italivre/iastro-ia",
                      "mapas", "images-livres", "arquétipos")
DB = os.path.join("/mnt/dados/home-italivre/iastro-ia",
                  "arquetipos", "arquetipos.db")


def sem_acentos(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn").lower()


def http_json(url, timeout=20, tentativas=5):
    for _ in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            code = getattr(getattr(e, "code", None), "real", None) or getattr(
                e, "code", None)
            espera = 5.0 if code == 429 else 1.5
            time.sleep(espera)
            last = e
    raise RuntimeError(f"HTTP/JSON falhou: {last}")


def buscar(query, limit=10):
    url = (API + "?action=query&list=search&srnamespace=6&srlimit=%d&"
           "srsearch=%s&format=json" % (limit, urllib.parse.quote(query)))
    d = http_json(url)
    return [r["title"] for r in d.get("query", {}).get("search", [])]


def imageinfo(titulo):
    """imageinfo de UM título (imageminfo: url, size, mime, extmetadata)."""
    url = (API + "?action=query&titles=%s&prop=imageinfo&iiprop="
           "url|size|mime|extmetadata&iiurlwidth=900&format=json"
           % urllib.parse.quote(titulo))
    d = http_json(url)
    for page in d.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {}) or {}
        lic = meta.get("LicenseShortName", {}).get("value", "")
        artista = (meta.get("Artist", {}).get("value", "") or "")
        artista = re_html(artista)
        return {
            "mime": info.get("mime", ""),
            "url": info.get("url", ""),
            "thumb": info.get("thumburl", info.get("url", "")),
            "w": info.get("width", 0),
            "h": info.get("height", 0),
            "licenca": lic,
            "artista": artista,
        }
    return None


def re_html(t):
    import re
    t = re.sub(r"<[^>]+>", "", t or "")
    return re.sub(r"\s+", " ", t).strip()[:120]


def pontuacao(info, indice, query):
    """Nota o candidato: raster + licença livre + tamanho + relevância."""
    pts = 0.0
    mime = info.get("mime", "")
    if "png" in mime or "jpeg" in mime or "webp" in mime:
        pts += 40
    elif "svg" in mime or "tiff" in mime or "pdf" in mime:
        pts -= 100  # exclui na prática
    lic = (info.get("licenca") or "").lower()
    if "pdm" in lic or "cc0" in lic or "public domain" in lic:
        pts += 30
    elif lic.startswith("cc-by") or "cc by" in lic:
        pts += 15
    elif "fair" in lic or "nonfree" in lic or lic in ("", "unknown"):
        pts -= 40
    area = (info.get("w", 0) or 1) * (info.get("h", 0) or 1)
    if area >= 1200 * 800:
        pts += 20
    elif area >= 700 * 500:
        pts += 12
    elif area <= 200 * 200:
        pts -= 15
    pts -= 2.5 * indice          # mais cedo = melhor
    return pts


def baixar_png(url, destino, max_lado=1000):
    """Baixa a imagem (usa o thumb quando doi) e grava PNG RGB."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        dados = r.read()
    from PIL import Image
    im = Image.open(io.BytesIO(dados)).convert("RGB")
    w, h = im.size
    esc = min(1.0, max_lado / max(w, h))
    if esc < 1.0:
        im = im.resize((int(w * esc), int(h * esc)), Image.LANCZOS)
    im.save(destino, "PNG")
    return im.size


def consultar_alvo(nome, queries):
    """Menor 'busca, nota, baixa' para um arquétipo. Devolve dict ou None."""
    melhores = []  # (pts, titulo, info)
    for qi, q in enumerate(queries):
        try:
            titulos = buscar(q, limit=8)
        except Exception as e:
            print(f"   [aviso] busca '{q}' falhou: {e}")
            continue
        time.sleep(0.6)
        for ind, tit in enumerate(titulos):
            if tit.lower().endswith((".pdf", ".svg", ".tif", ".tiff",
                                     ".xcf", ".djvu", ".webm",
                                     ".ogv", ".mp4", ".avi")):
                continue
            try:
                info = imageinfo(tit)
            except Exception:
                continue
            time.sleep(0.35)
            if not info:
                continue
            pts = pontuacao(info, ind, q)
            if pts > 0:
                melhores.append((pts, tit, info))
    if not melhores:
        return None
    melhores.sort(key=lambda t: -t[0])
    pts, tit, info = melhores[0]
    return {"titulo": tit, "info": info, "pts": pts,
            "candidatos": len(melhores)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("filtro", nargs="*")
    args = ap.parse_args()

    # (nome do arquétipo, chave p/ ARQ_IMAGEM (sem acento), buscas)
    alvos = [
        ("Matinta Pereira", "matinta-pereira",
         ["Matinta Pereira folclore", "Matinta Perera", "Matinta Perera folclore"]),
        ("Corpo-seco", "corpo-seco",
         ["Corpo seco folclore brasileiro", "Corpo seco lenda"]),
        ("Comadre Fulozinha", "comadre-fulozinha",
         ["Comadre Fulozinha", "Comadre Fulorinha"]),
        ("Cabeça de Cuia", "cabeca-de-cuia",
         ["Cabeça de Cuia folclore", "Cabeça de Cuia Parnaíba"]),
        ("Mãe do Ouro", "mae-do-ouro",
         ["Mãe do Ouro folclore brasileiro", "Mae do Ouro lenda"]),
        ("Negrinho do Pastoreio", "negrinho-do-pastoreio",
         ["Negrinho do Pastoreio", "Negrinho do Pastoreio folclore"]),
        ("O Jangadeiro", "jangadeiro",
         ["jangadeiro", "jangadeiro nordeste", "jangada nordeste"]),
        ("Tutu Marambá", "tutu-maramba",
         ["Tutu Maramba bicho-papão", "Tutu Marambá"]),
        ("Capeta da Garrafa", "capeta-da-garrafa",
         ["Capeta da Garrafa folclore capixaba", "Capeta da Garrafa"]),
        ("Mão Pelada", "mao-pelada",
         ["Mão Pelada folclore capixaba", "Mão Pelada lenda"]),
        ("Frade e a Freira", "frade-e-a-freira",
         ["Pedra do Frade e a Freira Itapemirim", "Frade e a Freira Espírito Santo"]),
        ("Mãe-Bá e a Lagoa", "mae-ba-lagoa",
         ["Mãe-Bá Lagoa Itapemirim", "curandeira goytacaz", "Lagoa Itapemirim"]),
        ("Índia Ísis e o nome Marataízes", "india-isis-marataizes",
         ["Marataízes praia", "Marataizes", "Índia Ísis Marataízes"]),
        ("Cruz de Muribeca", "cruz-de-muribeca",
         ["Muribeca aldeamento jesuíta", "Missão jesuíta Muribeca"]),
        ("Domingos José Martins", "domingos-jose-martins",
         ["Domingos José Martins retrato", "Domingos José Martins gravura",
          "Revolução Pernambucana 1817"]),
        ("Rio Itapemirim" "(território)", "rio-itapemirim",
         ["Rio Itapemirim", "Itapemirim rio"]),
        ("Gavião / ave de rapina", "gaviao",
         ["gavião ave", "gavião real ave", "accipiter"]),
        ("Grande Baleia", "grande-baleia",
         ["baleia jubarte", "baleia", "Megaptera novaeangliae"]),
        ("Iandutí (teia de aranha do céu)", "ianduti-teia",
         ["teia de aranha orvalho", "spider web dew", "Araneae teia"]),
        ("Jaó / Inambu (tinamou)", "jao-inambu",
         ["tinamou", "inambu ave", "Jaó ave"]),
        ("O Caçador que mira as Plêiades", "cacador-plesiades",
         ["Órion constelação", "Orion constellation"]),
        ("Os Dois Carregadores do Céu", "dois-carregadores",
         ["Gêmeos Castor Pólux constelação", "Gemini constellation"]),
        ("Rio-do-Céu e a piracema das estrelas", "rio-do-ceu-via-lactea",
         ["Via Láctea", "Via Lactea noite", "Milky Way night"]),
        ("Tatu", "tatu",
         ["tatu tatu-peba", "tatu galinha", "tatu lenda brasileira"]),
        ("Veado", "veado",
         ["veado", "veado-mateiro", "deer cervus", "Mazama"]),
        ("A Flecha que guarda a região do Escorpião", "flecha-escorpiao",
         ["Escorpião constelação", "Scorpius constellation",
          "Scorpius star chart"]),
        ("Homem Velho / Velho", "homem-velho",
         ["Homem Velho constelação céu austral", "ancião estrelas céu ao sul"]),
        ("Memória Puris e Goytacá", "memoria-puris-goytaca",
         ["Rio Itapemirim paisagem", "Itapemirim ES"]),
        ("Criatura do rio Itapemirim (a verificar)", "criatura-rio-itapemirim",
         ["jacaré crocodilo rio", "arraia gigante", "Rio Itapemirim"]),
        ("Minotauro de Itapemirim (a verificar)", "minotauro-itapemirim",
         ["Minotauro lenda", "Creta minotauro"]),
        ("Sumé (capixaba)", "sume",
         ["Sumé Tapirema", "Tupã", "Sumé civilizador Brasil"]),
    ]

    bd = sqlite3.connect(DB)
    bd.execute("""CREATE TABLE IF NOT EXISTS imagem_livre (
        id TEXT PRIMARY KEY, arquivo TEXT, titulo TEXT, tipo TEXT,
        tema TEXT, dominio_publico INTEGER, licenca TEXT, autor TEXT,
        criador_ref TEXT, fonte_url TEXT, obra_origem TEXT, nota TEXT)""")

    ok, falha = [], []
    for nome, chave, queries in alvos:
        chv_u = sem_acentos(chave).replace(" ", "-")
        if args.filtro and not any(f in chave.lower() or f in nome.lower()
                                   for f in [x.lower() for x in args.filtro]):
            continue
        if os.path.exists(os.path.join(DIR_PD, chv_u + ".png")):
            print(f"▸ {nome}: já tem imagem, pula.")
            continue
        print(f"▸ {nome} …", flush=True)
        res = consultar_alvo(nome, queries)
        if not res:
            print(f"   ✗ nenhuma imagem razoável encontrada.")
            falha.append(chave)
            continue
        destino = os.path.join(DIR_PD, chv_u + ".png")
        try:
            tam = baixar_png(res["info"].get("thumb") or res["info"]["url"],
                             destino)
        except Exception as e:
            print(f"   ✗ download falhou: {e}")
            falha.append(chave)
            continue
        lic = res["info"].get("licenca", "")
        dp = 1 if ("pdm" in lic.lower() or "cc0" in lic.lower()
                   or "public domain" in lic.lower()) else 0
        rid = "img." + sem_acentos(chave)
        bd.execute(
            "INSERT OR REPLACE INTO imagem_livre "
            "(id, arquivo, titulo, tipo, tema, dominio_publico, licenca, "
            " autor, criador_ref, fonte_url, obra_origem, nota) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (rid, chv_u + ".png",
             f"'{res['titulo']}' para o arquétipo '{chave}'",
             "arquetipo", sem_acentos(chave).replace("-", " "), dp, lic,
             res["info"].get("artista", ""), "Wikimedia Commons",
             res["info"]["url"], None,
             f"arquétipo de correspondência: {chave}"))
        bd.commit()
        print(f"   ✓ {res['titulo']}  [{lic}]  {tam}")
        print(f"     ARQ_IMAGEM['{sem_acentos(chave)}'] = '{chv_u}'")
        ok.append((chave, chv_u))
        time.sleep(0.3)

    bd.close()
    print("\n── resumo ──")
    print("com imagem:", ", ".join(n for n, _ in ok) or "nenhum")
    print("sem ainda :", ", ".join(falha) or "todos encontrados")


if __name__ == "__main__":
    main()