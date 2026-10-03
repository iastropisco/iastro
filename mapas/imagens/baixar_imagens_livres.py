#!/usr/bin/env python3
"""Baixa o LOTE PILOTO de imagens livres por arquétipo (domínio público/CC).

Lê `arquetipos/imagens-arquetipos.json` e baixa, das entradas com
`fonte_url` = Wikimedia Commons, a imagem real para `mapas/images-livres/`
(reaproveitando a função resolve_url de baixar_imagens.py). Entradas de
cordel/literatura/cantigas de domínio público precisam de arquivo validado
manualmente (Gutenberg/Commons) e são LISTADAS mas não baixadas aqui.

Uso:
    /mnt/dados/home-italivre/iastro-ia/venv/bin/python \
        /mnt/dados/home-italivre/iastro-ia/mapas/imagens/baixar_imagens_livres.py
"""
import json
import os
import subprocess
import sys

ARQ = "/mnt/dados/home-italivre/iastro-ia/arquetipos/imagens-arquetipos.json"
IMGS = "/mnt/dados/home-italivre/iastro-ia/mapas/images-livres"
BAIXAR = "/mnt/dados/home-italivre/iastro-ia/mapas/imagens/baixar_imagens.py"

# entradas que têm nome real na Commons e podem ser baixadas agora (pilotar).
_BAIXAVEL = {
    # arquivo(destino) -> título na Commons
    "images-livres/nebula-orion.jpg": "File:Nebula de Orion (ESA-Hubble).jpg",
}


def main():
    with open(ARQ, encoding="utf-8") as f:
        dados = json.load(f)

    # 1) baixa o que é possível (Commons/NASA), reusando resolve_url
    sys.path.insert(0, os.path.dirname(BAIXAR))
    try:
        import baixar_imagens as bk
    except Exception as e:  # pragma: no cover
        print("[aviso] não consegui reusar baixar_imagens:", e)
        bk = None

    os.makedirs(IMGS, exist_ok=True)
    baixadas, pendentes = [], []
    for im in dados.get("imagens", []):
        arq = im.get("arquivo")
        base = os.path.basename(arq)
        destino = os.path.join(IMGS, base)
        if im.get("tipo") == "externo" and im.get("licenca") and "PD" in (im.get("licenca") or ""):
            chave = im.get("arquivo")
            titulo = _BAIXAVEL.get(chave)
            if bk and titulo and not os.path.exists(destino):
                print(f"[baixa] {base} <- {titulo}")
                try:
                    thumb, meta = bk.resolve_url(titulo)
                    if thumb:
                        import urllib.request
                        req = urllib.request.Request(thumb, headers={"User-Agent": "iastro/1.0"})
                        with urllib.request.urlopen(req, timeout=60) as r:
                            dadosb = r.read()
                        if len(dadosb) >= 2000:
                            with open(destino, "wb") as f:
                                f.write(dadosb)
                            baixadas.append(base)
                            print(f"   ok ({len(dadosb)} bytes)")
                        else:
                            pendentes.append(base)
                    else:
                        pendentes.append(base)
                except Exception as e:  # pragma: no cover
                    print("   falha:", e); pendentes.append(base)
            else:
                if os.path.exists(destino):
                    baixadas.append(base)
                else:
                    pendentes.append(base)
        else:
            pendentes.append(base)

    print("\nPendentes (requerem arquivo público validado, ex.: Gutenberg/Commons):")
    for p in pendentes:
        print("  -", p)
    print(f"\nBaixadas: {len(baixadas)} · Pendentes: {len(pendentes)}")
    print("Ver manifest atualizado em:", os.path.join(os.path.dirname(IMGS), "manifest.json"))


if __name__ == "__main__":
    main()