#!/usr/bin/env python3
"""Baixa imagens de arquétipos via Wikimedia Commons — v2 expandida.
Termos otimizados para maximizar imagens livres realistas."""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

SAIDA = "/mnt/dados/home-italivre/iastro-ia/mapas/images-livres/arquétipos"
API = "https://commons.wikimedia.org/w/api.php"

# Chaves que precisamos de imagem (as que já existem ficam de fora)
# Usar termos em inglês aumenta muito a chance de achar PD/CC
TERMOS = {
    # --- Folclore brasileiro ---
    "saci": [
        "Saci Perere drawing",
        "Saci Perere illustration",
        "Saci Perere art",
        "Saci folklore Brazil",
        "caipora saci",
    ],
    "iara": [
        "Iara mermaid Brazil",
        "Yara mermaid folklore",
        "Iara Brazilian folklore",
        "mamae d agua folklore",
        "Iara water spirit",
    ],
    "cuca": [
        "Cuca Brazil folklore",
        "Cuca witch Brazil",
        "Cuca folclore",
        "bicho cuca",
    ],
    "boto": [
        "Boto rosa dolphin Amazon",
        "boto cor de rosa",
        "Inia geoffrensis",
        "Amazon river dolphin pink",
    ],
    "caipora": [
        "Caipora folklore",
        "caipora brazil",
        "caipora mitologia",
        "curupira caipora",
    ],
    "mula_sem_cabeca": [
        "mula sem cabeca",
        "mula sem cabeça folklore",
        "headless mule Brazil",
        "mula da Colombia folklore",
    ],
    "lobisomem": [
        "lobisomem",
        "werewolf folklore",
        "lobisomem brazil",
        "lycanthropy folklore",
    ],
    "mapinguari": [
        "mapinguari",
        "mapinguari folklore",
        "mapinguari amazon",
        "mapinguari criatura",
    ],
    "cobra_grande": [
        "cobra grande folklore",
        "cobra grandona",
        "giant snake folklore brazil",
        "boitata cobra",
        "sucuria folklore",
    ],
    # --- Orixás (faltam xango e ogum) ---
    "xango": [
        "Xango orisha",
        "Shango orisha statue",
        "Chango orisha",
        "Xango Orixá",
        "Shango Yoruba",
    ],
    "ogum": [
        "Ogun orisha",
        "Ogum orisha",
        "Ogun Yoruba deity",
        "Ogun iron deity",
    ],
    # --- Animais constelações indígenas ---
    "anta": [
        "Tapirus terrestris",
        "tapir South America",
        "anta animal",
        "tapir",
        "lowland tapir",
    ],
    "ema": [
        "Rhea americana",
        "ema bird Brazil",
        "greater rhea",
        "rhea americana bird",
    ],
    "onca": [
        "Panthera onca",
        "jaguar animal",
        "onça pintada",
        "jaguar",
        "jaguar face",
    ],
}

LICENCAS_OK = ("public domain", "cc0", "cc by", "attribution", "pd",
               "cc-by", "cc by-sa", "cc-by-sa", "by-sa", "pdm",
               "creative commons zero", "public-domain")


def api_call(args):
    args["format"] = "json"
    q = urllib.parse.urlencode(args)
    req = urllib.request.Request(
        f"{API}?{q}",
        headers={"User-Agent": "iastro-colagem/1.0 (local; educational project)"}
    )
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def buscar_licenca(title):
    """Retorna (thumb_url, licenca) se a imagem for de licença livre."""
    for tent in range(3):
        try:
            d = api_call({
                "action": "query", "titles": title,
                "prop": "imageinfo",
                "iiprop": "url|extmetadata",
                "iiurlwidth": "720"
            })
        except Exception:
            time.sleep(2 + tent)
            continue
        page = next(iter(d.get("query", {}).get("pages", {}).values()))
        ii = page.get("imageinfo") or []
        if not ii:
            return None, ""
        info = ii[0]
        lic = info.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "")
        return info.get("thumburl") or info.get("url"), lic
    return None, ""


def achar_imagem(termos):
    """Retorna (titulo, thumb, lic) do 1º arquivo livre; senão (None, None, None)."""
    for termo in termos:
        print(f"      buscou: '{termo}'", flush=True)
        try:
            d = api_call({
                "action": "query", "list": "search",
                "srsearch": termo, "srnamespace": "6", "srlimit": "10"
            })
        except Exception as e:
            print(f"      erro API: {e}")
            time.sleep(3)
            continue
        hits = d.get("query", {}).get("search", [])
        print(f"      {len(hits)} hits", flush=True)
        for hit in hits:
            tit = hit["title"]
            ext = tit.lower().rsplit(".", 1)[-1] if "." in tit else ""
            if ext not in ("png", "jpg", "jpeg", "svg"):
                continue
            thumb, lic = buscar_licenca(tit)
            time.sleep(0.8)
            if thumb and any(o in lic.lower() for o in LICENCAS_OK):
                print(f"      ✅ {tit} [{lic}]")
                return tit, thumb, lic
        time.sleep(1.0)
    return None, None, None


def baixar(chave, titulo, thumb):
    destino = os.path.join(SAIDA, chave + ".png")
    req = urllib.request.Request(
        thumb,
        headers={"User-Agent": "iastro-colagem/1.0 (local; educational project)"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        dados = r.read()
    if len(dados) < 3000:
        raise ValueError(f"arquivo pequeno ({len(dados)} bytes)")
    with open(destino, "wb") as f:
        f.write(dados)
    print(f"   💾 {len(dados)} bytes → {chave}.png  [{titulo}]")


def main():
    os.makedirs(SAIDA, exist_ok=True)
    resultados = {}
    puladas = {}
    for chave, termos in TERMOS.items():
        destino = os.path.join(SAIDA, chave + ".png")
        if os.path.exists(destino):
            print(f"[já existe] {chave}")
            continue
        print(f"\n{'='*50}")
        print(f"[busca] {chave}")
        titulo, thumb, lic = achar_imagem(termos)
        time.sleep(1.0)
        if not thumb:
            puladas[chave] = "sem imagem livre encontrada"
            print(f"   ❌ {puladas[chave]}")
            continue
        try:
            baixar(chave, titulo, thumb)
            resultados[chave] = {"titulo": titulo, "licenca": lic, "thumb": thumb}
        except Exception as e:
            puladas[chave] = str(e)
            print(f"   ❌ falha: {e}")
        time.sleep(1.2)

    print("\n\n" + "=" * 60)
    print("=== BAIXADAS COM SUCESSO ===")
    for k, v in resultados.items():
        print(f"  {k}: {v['titulo']}  [{v['licenca']}]")
    print(f"\n=== FALHARAM ({len(puladas)}) ===")
    for k, v in puladas.items():
        print(f"  {k}: {v}")
    print("=" * 60)


if __name__ == "__main__":
    main()
