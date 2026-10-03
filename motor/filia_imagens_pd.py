# -*- coding: utf-8 -*-
"""Busca imagens de DOMÍNIO PÚBLICO no Wikimedia Commons p/ os arquétipos
que ainda são desenho procedural (12 signos via atlas de Hevelius + astrônomos
Crux e Plêiades). Salva em images-livres/arquetipos/<chave>.png (máx. 900px).
"""
import json, urllib.request, urllib.parse, os, sys, io, time

sys.path.insert(0, "/mnt/dados/ephemeris")

UA = {"User-Agent": "iastro/1.0 (projeto de colagem astral; single-user)"}
DIR_PD = "/mnt/dados/home-italivre/iastro-ia/mapas/images-livres/arquetipos"


def api(params):
    params = {**params, "action": "query", "format": "json", "formatversion": "2"}
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def achar_arquivo(termo):
    data = api({"generator": "search",
                "gsrsearch": f"{termo} filetype:bitmap",
                "gsrnamespace": "6", "gsrlimit": "8",
                "prop": "imageinfo",
                "iiprop": "url|mime|extmetadata|size", "iiurlwidth": "900"})
    cands = []
    for p in data.get("query", {}).get("pages", []):
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        lic = (ii.get("extmetadata") or {}).get("LicenseShortName", {}).get("value", "")
        if not lic:
            continue
        livre = any(k in lic.lower() for k in
                    ("public domain", "pd-", "pdold", "cc0", "cc-0"))
        if not livre:
            continue
        titulo = p.get("title", "")
        cands.append((titulo, lic, ii.get("thumburl") or ii["url"], ii.get("width", 0)))
    if not cands:
        return None
    # prioriza o padrão "<Sign> Hevelius.jpg" (série coesa)
    for c in cands:
        if pref_serie.lower() in c[0].lower() and len(c[0]) < 45:
            return c
    return cands[0]


def baixar(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


TARIFAS = [
    # (termo_busca, nome_pt, chave_pd)
    ("Aries Hevelius", "Áries", "aries"),
    ("Taurus Hevelius", "Touro", "touro"),
    ("Gemini Hevelius", "Gêmeos", "gemeos"),
    ("Cancer Hevelius", "Câncer", "cancer"),
    ("Leo Hevelius", "Leão", "leao"),
    ("Virgo Hevelius", "Virgem", "virgem"),
    ("Libra Hevelius", "Libra", "libra"),
    ("Scorpius Hevelius", "Escorpião", "escorpiao"),
    ("Sagittarius Hevelius", "Sagitário", "sagitario"),
    ("Capricornus Hevelius", "Capricórnio", "capricornio"),
    ("Aquarius Hevelius", "Aquário", "aquario"),
    ("Pisces Hevelius", "Peixes", "peixes"),
    # objetos celestes (foto/atlas PD)
    ("Pleiades Seven Sisters", "as Plêiades", "pleiades"),
    ("Crux Southern Cross", "o Cruzeiro do Sul", "cruz_do_sul"),
]

if __name__ == "__main__":
    os.makedirs(DIR_PD, exist_ok=True)
    for termo, nome_pt, chave in TARIFAS:
        arquivo = os.path.join(DIR_PD, f"{chave}.png")
        if os.path.exists(arquivo):
            print("  já existe:", chave)
            continue
        try:
            achei = achar_arquivo(termo)
            if not achei:
                print("  SEM resultado livre:", termo)
                continue
            titulo, lic, url, w = achei
            blob = baixar(url)
            from PIL import Image
            im = Image.open(io.BytesIO(blob)).convert("RGB")
            w, h = im.size
            esc = 1.0
            if max(w, h) > 900:
                esc = 900 / max(w, h)
                im = im.resize((int(w * esc), int(h * esc)), Image.LANCZOS)
            im.save(arquivo)
            print(f"  OK {chave:10s} <- {titulo[:50]} ({lic}, {w}px)")
        except Exception as e:
            print("  FALHOU", termo, "->", repr(e)[:120])
        time.sleep(0.4)
    print("\nnovas imagens instaladas em", DIR_PD)