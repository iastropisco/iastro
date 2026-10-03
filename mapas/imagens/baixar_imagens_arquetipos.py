#!/usr/bin/env python3
"""Baixa IMAGENS DE DOMÍNIO PÚBLICO / CC dos arquétipos (boitatá, curupira,
iemanja, exu, omolu/obaluaiê, osanyin...) da Wikimedia Commons para
`mapas/images-livres/arquétipos/`.

Cada entrada associa um arquétipo (chave usada por colagem.py) a um arquivo
da Commons. Antes de usar, valida-se a licença via API (PD/CC permitidas);
arquivos muito restritivos são pulados. Pacing de 1s entre chamadas para não
estourar o rate-limit.

Uso:
    /mnt/dados/home-italivre/iastro-ia/venv/bin/python \
        mapas/imagens/baixar_imagens_arquetipos.py
"""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import baixar_imagens as bk

SAIDA = "/mnt/dados/home-italivre/iastro-ia/mapas/images-livres/arquétipos"

# arquétipo(chave) -> título real na Commons (curadoria manual, licenças livres)
CURADORIA = {
    "boitata": "File:Boitata.png",
    "curupira": "File:Curupira.jpg",
    "omolu": "File:Omolu.jpg",
    "iemanja": "File:Orixa Yemanja Orossi.JPG",
    "iemanja2": "File:Yemoja Nigeria.jpg",
    "exu": "File:Eshu.jpg",
    "osanyin": "File:Ossanha.jpg",
    "osanyin2": "File:Osanyin Staff.jpg",
}

LICENCAS_OK = ("public domain", "cc0", "cc by", "attribution",
               "pd", "cc-by", "cc by-sa", "cc-by-sa")


def main():
    os.makedirs(SAIDA, exist_ok=True)
    baixadas, puladas, falhas = [], [], []
    for chave, titulo in CURADORIA.items():
        destino = os.path.join(SAIDA, chave + ".png")
        if os.path.exists(destino):
            baixadas.append(chave)
            print(f"[já] {chave}")
            time.sleep(0.6)
            continue
        print(f"[consulta] {chave} <- {titulo}")
        thumb, meta = bk.resolve_url(titulo, width=700, tentativas=4)
        time.sleep(1.0)
        if not thumb:
            falhas.append(chave)
            print("   sem URL")
            continue
        lic = (meta or {}).get("licenca", "").lower()
        if not any(o in lic for o in LICENCAS_OK):
            puladas.append(chave)
            print(f"   licença não-livre, pulada: {meta.get('licenca')}")
            continue
        try:
            req = urllib.request.Request(thumb,
                                         headers={"User-Agent": "iastro/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                dados = r.read()
            if len(dados) < 3000:
                puladas.append(chave)
                print(f"   muito pequena ({len(dados)}), pulada")
                continue
            with open(destino, "wb") as f:
                f.write(dados)
            baixadas.append(chave)
            print(f"   ok ({len(dados)} bytes) licença={meta.get('licenca')}")
        except Exception as e:
            falhas.append(chave)
            print("   falha:", e)
        time.sleep(1.0)

    print("\nBaixadas:", baixadas)
    print("Puladas (licença/pequena):", puladas)
    print("Falhas:", falhas)
    print("Pasta:", SAIDA)


if __name__ == "__main__":
    main()
