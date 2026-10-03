#!/usr/bin/env python3
"""Baixa imagens públicas (NASA/JWST/Hubble/ESA, via Wikimedia Commons) para a
biblioteca local do iastro. Uso:

    /mnt/dados/home-italivre/iastro-ia/venv/bin/python baixar_imagens.py

Gera:
    mapas/imagens/sistema-solar/   -> Júpiter, Saturno, Marte, Lua, Sol, etc.
    mapas/imagens/cosmologico/     -> galáxias, nebulosas, campo profundo (JWST/Hubble)
    mapas/imagens/jwst/            -> destaques James Webb
    mapas/imagens/hubble/          -> destaques Hubble
    mapas/imagens/euclid/          -> destaques Euclid (ESA)
    mapas/imagens/manifest.json    -> créditos/licenças de cada arquivo

Licença: imagens NASA (inclusive JWST/Hubble) via ESA/CSA são de domínio
público / CC-BY quando na Commons; cada entrada guarda autoria+licença para
atribuição correta no rodapé das obras. Fonte: Wikimedia Commons API.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

# (destino, nome do arquivo na Commons, telescópio, ano, marco)
# Marcos condensados: sol, lua e os planetas que importam à astrologia + galáxias.
catálogo = [
    # ---- Sol e Lua ----
    ("sistema-solar/sol.png",        "File:The Sun by the Atmospheric Imaging Assembly of NASA's Solar Dynamics Observatory - 20100819.jpg", "SDO (NASA)", "2010", "Atividade solar em ultravioleta (Solar Dynamics Observatory)"),
    ("sistema-solar/lua.png",        "File:FullMoon2010.jpg", "foto lunar", "2010", "A Lua em luz visível, superfície próxima"),

    # ---- Planetas ----
    ("sistema-solar/mercurio.png",   "File:Mercury in true color.jpg", "MESSENGER (NASA)", "2010", "Mercúrio em cor verdadeira"),
    ("sistema-solar/venus.png",      "File:Venus-real color.jpg", "Mariner 10/Messenger (NASA)", "1974-2010", "Vênus, véu encoberto"),
    ("sistema-solar/marte.png",      "File:OSIRIS Mars true color.jpg", "Rosetta (ESA)", "2007", "Marte em cor aproximada"),
    ("sistema-solar/jupiter.png",    "File:Jupiter and its shrunken Great Red Spot.jpg", "Hubble (NASA/ESA)", "2014", "Júpiter e a Grande Mancha Vermelha"),
    ("sistema-solar/saturno.png",    "File:Saturn from Cassini Orbiter (2004-10-06).jpg", "Cassini (NASA/ESA)", "2004", "Saturno em luz visível, Cartes"),
    ("sistema-solar/urano.png",      "File:Uranus2.jpg", "Voyager 2 (NASA)", "1986", "Urano, o planeta deitado"),
    ("sistema-solar/netuno.png",     "File:Neptune Full.jpg", "Voyager 2 (NASA)", "1989", "Netuno, azul profundo"),

    # ---- JWST (telescópios recentes) ----
    ("jwst/jwst-saturno.png",        "File:Saturn (NIRCam) (01H3X9BMPCX165ZK9RA49J2416).png", "JWST NIRCam (NASA/ESA/CSA)", "2022", "Saturno em infravermelho — anéis brilhantes e detalhes atmosféricos"),
    ("jwst/jwst-jupiter.png",        "File:Jupiter Showcases Auroras, Hazes (NIRCam Widefield View).png", "JWST NIRCam (NASA/ESA/CSA)", "2022", "Júpiter em infravermelho — auroras e Grande Mancha Vermelha"),
    ("jwst/jwst-nebulosa.png",       "File:“Cosmic Cliffs” in the Carina Nebula (NIRCam and MIRI Composite Image).png", "JWST NIRCam/MIRI (NASA/ESA/CSA)", "2022", "Cosmic Cliffs (Nebulosa de Carina) — berçário de estrelas"),
    ("jwst/jwst-campo.png",          "File:Webb's First Deep Field.jpg", "JWST NIRCam (NASA/ESA/CSA)", "2022", "Primeiro campo profundo do JWST (aglomerado SMACS 0723)"),
    ("jwst/jwst-epsindi.png",        "File:Epsilon Indi Ab (MIRI Image).png", "JWST MIRI (NASA/ESA/CSA)", "2024", "Exoplaneta Epsilon Indi Ab diretamente fotografado"),

    # ---- Hubble ----
    ("hubble/hubble-urano.png",      "File:Uranus (Nov 2014 and Nov 2022) (2023-007).png", "Hubble (NASA/ESA)", "2023", "Urano em 2014 e 2022 — anéis e calota polar"),
    ("hubble/hubble-saturno2.png",   "File:Saturn - NASA ESA Hubble Space Telescope (53419613950).png", "Hubble (NASA/ESA)", "2023", "Saturno em luz visível — bandas suaves e anéis"),

    # ---- Euclid (ESA 2023-) ----
    ("euclid/euclid-perseus.jpg",    "File:Euclid’s view of the Perseus cluster of galaxies ESA25170535.jpg", "Euclid VIS (ESA)", "2023", "Aglomerado de galáxias de Perseu — primeira luz"),
    ("euclid/euclid-n6744.jpg",      "File:Euclid’s new image of spiral galaxy NGC 6744 ESA497254.jpg", "Euclid VIS/NISP (ESA)", "2025", "Galáxia espiral NGC 6744 — mapeando matéria escura"),
]


def resolve_url(title, width=900, tentativas=4):
    """Pergunta à API da Commons o endereço REAL do thumb (não adivinhar caminho).
    Com retry/backoff contra rate-limit (HTTP 429)."""
    import urllib.parse
    q = urllib.parse.urlencode({
        "action": "query", "titles": title,
        "prop": "imageinfo", "iiprop": "url|extmetadata|commonmetadata",
        "iiurlwidth": str(width), "format": "json",
    })
    url = f"https://commons.wikimedia.org/w/api.php?{q}"
    for tent in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "iastro-colagem/1.0 (contact: local)"})
            with urllib.request.urlopen(req, timeout=40) as r:
                d = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(3 + 4 * tent)
                continue
            raise
        except Exception:
            time.sleep(3)
            continue
    else:
        return None, None
    pages = d["query"]["pages"]
    page = pages[list(pages)[0]]
    if "imageinfo" not in page:
        # --- fallback: busca e usa o 1º resultado do namespace Arquivos ---
        import urllib.parse as up
        s = title[len("File:"):].split(".")[0]
        sq = up.urlencode({"action": "query", "list": "search",
                           "srsearch": s, "srnamespace": "6",
                           "srlimit": "1", "format": "json"})
        try:
            req = urllib.request.Request(
                f"https://commons.wikimedia.org/w/api.php?{sq}",
                headers={"User-Agent": "iastro-colagem/1.0 (local)"})
            with urllib.request.urlopen(req, timeout=40) as r:
                sd = json.load(r)
            hits = sd.get("query", {}).get("search", [])
            if hits:
                ntitle = hits[0]["title"]
                del req
                thumb, meta = resolve_url(ntitle, width, tentativas=2)
                return thumb, meta
        except Exception:
            pass
        return None, None
    info = page["imageinfo"][0]
    thumb = info.get("thumburl") or info.get("url")
    meta = info.get("extmetadata", {})
    lic = meta.get("LicenseShortName", {}).get("value", "?")
    artista = meta.get("Artist", {}).get("value", "?")
    return thumb, {"licenca": lic, "autor": artista, "fonte": info.get("url")}


def baixar(destino, title):
    thumb, meta = resolve_url(title)
    if not thumb:
        print(f"   [falha] sem URL: {title}")
        return None
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    req = urllib.request.Request(thumb, headers={"User-Agent": "iastro-colagem/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        dados = r.read()
    if len(dados) < 2000:
        print(f"   [falha] arquivo pequeno ({len(dados)}): {title}")
        return None
    with open(destino, "wb") as f:
        f.write(dados)
    return meta


def main():
    base = os.path.join("/mnt/dados/home-italivre/iastro-ia", "mapas", "imagens")
    # --- se README mostrar (--manifest) só refaz o JSON de créditos sem baixar ---
    if "--manifest" in sys.argv:
        manifest = {}
        for destino, title, tel, ano, marco in catálogo:
            path = os.path.join(base, destino)
            if not os.path.exists(path):
                print(f"[falta] {destino}"); continue
            _, meta = resolve_url(title)
            manifest[destino] = {"telescópio": tel, "ano": ano, "marco": marco,
                                 "licença": (meta or {}).get("licenca", "?"),
                                 "autor": (meta or {}).get("autor", "?"),
                                 "fonte": (meta or {}).get("fonte", "?")}
            print(f"[meta ] {destino}")
            time.sleep(0.4)
        with open(os.path.join(base, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print(f"\nManifesto com {len(manifest)} entradas.")
        return

    manifest = {}
    ok = 0
    for destino, title, tel, ano, marco in catálogo:
        path = os.path.join(base, destino)
        if os.path.exists(path):
            print(f"[já] {destino}"); ok += 1; continue
        print(f"[   ] {destino}  <-  {title}")
        thumb, meta = resolve_url(title)
        if not thumb:
            print(f"   [falha] sem URL: {title}"); continue
        req = urllib.request.Request(thumb, headers={"User-Agent": "iastro-colagem/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            dados = r.read()
        if len(dados) < 2000:
            print(f"   [falha] arquivo pequeno ({len(dados)}): {title}"); continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(dados)
        manifest[destino] = {"telescópio": tel, "ano": ano, "marco": marco,
                             "licença": (meta or {}).get("licenca", "?"),
                             "autor": (meta or {}).get("autor", "?"),
                             "fonte": (meta or {}).get("fonte", "?")}
        ok += 1
        print(f"   ok ({len(dados)} bytes)")
        time.sleep(0.6)
    with open(os.path.join(base, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\nPronto: {ok}/{len(catálogo)} baixadas. Manifesto: {len(manifest)}.")


if __name__ == "__main__":
    main()