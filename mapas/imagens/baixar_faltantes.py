#!/usr/bin/env python3
"""Tenta baixar xango e cobra_grande que falharam por 429."""
import json, os, sys, time, urllib.parse, urllib.request

SAIDA = "/mnt/dados/home-italivre/iastro-ia/mapas/images-livres/arquétipos"
API = "https://commons.wikimedia.org/w/api.php"
LICENCAS_OK = ("public domain", "cc0", "cc by", "attribution", "pd",
               "cc-by", "cc by-sa", "cc-by-sa", "by-sa", "pdm",
               "creative commons zero", "public-domain")

TERMOS = {
    "xango": ["Shango orisha", "Xango deity", "Chango santeria", "Shango Yoruba statue"],
    "cobra_grande": ["anaconda folklore", "sucia snake", "giant snake legend", "boitata", "water boa"],
}

def api_call(args):
    args["format"] = "json"
    q = urllib.parse.urlencode(args)
    req = urllib.request.Request(f"{API}?{q}",
        headers={"User-Agent": "iastro-colagem/1.0 (local; educational project)"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)

def buscar_licenca(title):
    try:
        d = api_call({"action": "query", "titles": title, "prop": "imageinfo",
                       "iiprop": "url|extmetadata", "iiurlwidth": "720"})
    except:
        return None, ""
    page = next(iter(d.get("query", {}).get("pages", {}).values()))
    ii = page.get("imageinfo") or []
    if not ii:
        return None, ""
    info = ii[0]
    lic = info.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "")
    return info.get("thumburl") or info.get("url"), lic

def achar_imagem(termos):
    for termo in termos:
        print(f"  busca: '{termo}'", flush=True)
        try:
            d = api_call({"action": "query", "list": "search",
                          "srsearch": termo, "srnamespace": "6", "srlimit": "10"})
        except Exception as e:
            print(f"  erro: {e}")
            time.sleep(5)
            continue
        hits = d.get("query", {}).get("search", [])
        print(f"  {len(hits)} hits")
        for hit in hits:
            tit = hit["title"]
            ext = tit.lower().rsplit(".", 1)[-1] if "." in tit else ""
            if ext not in ("png", "jpg", "jpeg", "svg"):
                continue
            thumb, lic = buscar_licenca(tit)
            time.sleep(1.5)
            if thumb and any(o in lic.lower() for o in LICENCAS_OK):
                return tit, thumb, lic
        time.sleep(2)
    return None, None, None

for chave, termos in TERMOS.items():
    destino = os.path.join(SAIDA, chave + ".png")
    if os.path.exists(destino):
        print(f"[já existe] {chave}")
        continue
    print(f"\n=== {chave} ===")
    time.sleep(5)
    titulo, thumb, lic = achar_imagem(termos)
    if not thumb:
        print(f"  ❌ sem imagem livre")
        continue
    req = urllib.request.Request(thumb, headers={"User-Agent": "iastro-colagem/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        dados = r.read()
    with open(destino, "wb") as f:
        f.write(dados)
    print(f"  💾 {len(dados)} bytes → {chave}.png  [{titulo}]  {lic}")
