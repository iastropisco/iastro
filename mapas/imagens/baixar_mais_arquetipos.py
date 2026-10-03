#!/usr/bin/env python3
"""Amplia as imagens de arquétipos com mais figuras de DOMÍNIO PÚBLICO / CC
da Wikimedia Commons (orixás, signos do zodíaco e folclore).

Busca por termo, filtra por licença livre, baixa como PNG quadrado (recorte
central) em `mapas/images-livres/arquétipos/`. O colagem.py registra cada
arquétipo -> imagem pelo nome em ARQ_IMAGEM.

Uso:
    /mnt/dados/home-italivre/iastro-ia/venv/bin/python \
        mapas/imagens/baixar_mais_arquetipos.py
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SAIDA = "/mnt/dados/home-italivre/iastro-ia/mapas/images-livres/arquétipos"
API = "https://commons.wikimedia.org/w/api.php"

# chave_arquivo -> termos de busca na Commons (espera-se licença livre)
TERMOS = {
    "oxala": ["Oxalá Orixá", "Obatalá statue", "Oxala"],
    "oxum": ["Oxum Orixá goddess", "Oshun"],
    "xango": ["Xangô Orixá", "Shango statue"],
    "ogum": ["Ogum Orixá", "Ogun orisha"],
    "iansa": ["Iansã Orixá", "Oya Orisha"],
    "nana": ["Nanã Orixá", "Nana Buruku"],
    "oxumare": ["Oxumarê", "osunmare"],
    "oxossi": ["Oxóssi Orixá", "Oxosi"],
    "saci": ["Saci Pererê ilustração"],
    "iara": ["Iara mãe d'água ilustração", "Yara folklore"],
    "cuca": ["Cuca folclore ilustração"],
    "boto": ["Boto cor de rosa ilustração"],
    "caipora": ["Caipora ilustração"],
    "onca": ["Onça pintada ilustração"],
    "cobra": ["cobra gigante folclore"],
    "aberturas": ["constellation dipper"],
}

LICENCAS_OK = ("public domain", "cc0", "cc by", "attribution", "pd",
               "cc-by", "cc by-sa", "cc-by-sa", "by-sa")


def api(args):
    args["format"] = "json"
    q = urllib.parse.urlencode(args)
    req = urllib.request.Request(f"{API}?{q}",
                                 headers={"User-Agent": "iastro-colagem/1.0 (local)"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def buscar_licenca(title):
    """Retorna (thumb_url, licenca) se a imagem for de licença livre."""
    for tent in range(3):
        try:
            d = api({"action": "query", "titles": title,
                     "prop": "imageinfo",
                     "iiprop": "url|extmetadata",
                     "iiurlwidth": "720"})
        except Exception:
            time.sleep(2 + tent)
            continue
        page = next(iter(d.get("query", {}).get("pages", {}).values()))
        ii = page.get("imageinfo") or []
        if not ii:
            return None
        info = ii[0]
        lic = info.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "")
        return info.get("thumburl") or info.get("url"), lic
    return None


def achar_imagem(termos):
    """Retorna título do 1º arquivo livre cujo licença bate; senão None."""
    for termo in termos:
        try:
            d = api({"action": "query", "list": "search",
                     "srsearch": termo, "srnamespace": "6", "srlimit": "6"})
        except Exception:
            time.sleep(3)
            continue
        for hit in d.get("query", {}).get("search", []):
            tit = hit["title"]
            if not tit.lower().endswith((".png", ".jpg", ".jpeg")):
                continue
            thumb, lic = buscar_licenca(tit)
            time.sleep(1.0)
            if thumb and any(o in lic.lower() for o in LICENCAS_OK):
                return tit, thumb, lic
        time.sleep(1.0)
    return None, None, None


def baixar(chave, titulo, thumb):
    destino = os.path.join(SAIDA, chave + ".png")
    req = urllib.request.Request(thumb,
                                 headers={"User-Agent": "iastro-colagem/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        dados = r.read()
    if len(dados) < 3000:
        raise ValueError(f"arquivo pequeno ({len(dados)} bytes)")
    with open(destino, "wb") as f:
        f.write(dados)
    print(f"   ok ({len(dados)} bytes) -> {chave}.png  [{titulo}]")


def main():
    os.makedirs(SAIDA, exist_ok=True)
    resultados = {}
    puladas = {}
    for chave, termos in TERMOS.items():
        destino = os.path.join(SAIDA, chave + ".png")
        if os.path.exists(destino):
            print(f"[já] {chave}")
            continue
        print(f"[busca] {chave} <- '{termos[0]}'")
        titulo, thumb, lic = achar_imagem(termos)
        time.sleep(1.0)
        if not thumb:
            puladas[chave] = "sem imagem livre encontrada"
            print(f"   {puladas[chave]}")
            continue
        try:
            baixar(chave, titulo, thumb)
            resultados[chave] = titulo
        except Exception as e:
            puladas[chave] = str(e)
            print(f"   falha: {e}")
        time.sleep(1.2)

    print("\n=== BAIXADAS ===")
    for k, v in resultados.items():
        print(f"  {k}: {v}")
    print("\n=== PULADAS ===")
    for k, v in puladas.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
