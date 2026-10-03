"""assemelhar_ceu.py — assimilação geométrica dos céus de Stellarium.

Por que
-------
Stellarium traz dezenas de culturas de céu; cada asterismo liga estrelas por
número HIP, mas NÃO diz a qual signo ocidental corresponde. Este módulo
calcula essa ponte a partir da posição celeste real:

  1. Carga o catálogo HYG (HIP -> RA/Dec J2000), licencia MIT.
  2. Para cada asterismo de cada cultura, resolve os HIP em longitude
     eclíptica (obliquidade J2000).
  3. Atribue o asterismo ao SIGNO do zodíaco que reúne mais das suas
     estrelas (votação por pluralidade na longitude eclíptica).

Honestidade
-----------
- O vínculo posição -> signo é geométrico e verificável: um asterismo situado
  no Escorpião fica no Escorpião. Certeza ALTA para a posição.
- O SIGNIFICADO cultural desse asterismo é outra coisa: permanece hipótese
  (certeza baixa, `por_pesquisar=True` para o sentido) até fontes
  etnográficas.
- Nunca inventamos correspondências; separamos "onde está" de "que é".

Uso
---
    venv/bin/python assemelhar_ceu.py --cat /tmp/opencode/hyg.csv.gz
    venv/bin/python assemelhar_ceu.py --cat ... --cultura inuit
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os

import numpy as np

SKY = "/snap/stellarium-daily/2491/usr/share/stellarium/skycultures"

# chaves canónicas (iguales a SIGNOS_CANONICOS de construir_banco)
SIGNOS_ES = ["aries", "touro", "gemeos", "cancer", "leao", "virgem",
             "libra", "escorpiao", "sagitario", "capricornio", "aquario", "peixes"]
SIGNOS_TXT = ["Aries", "Touro", "Gémeos", "Câncer", "Leão", "Virgem",
              "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]
EPS = math.radians(23.4392911)  # obliquidade eclíptica J2000


def _ecl_media(lams):
    """Media circular de longitudes eclípticas  (graus), evitando o salto 0/360."""
    x = np.mean(np.cos(np.radians(lams)))
    y = np.mean(np.sin(np.radians(lams)))
    return math.degrees(math.atan2(y, x)) % 360.0


def _assinar_por_voto(lams):
    """Signo = o que reúne mais estrelas do asterismo (pluralidade).

    Mais estável que a média circular: Escorpião (lon ~240°) ainda que suas
    estrelas se espalam; aqui conta em que signo se situam mais estrelas.
    """
    if not lams:
        return None, None
    votos = {}
    for lam in lams:
        idx = int(lam // 30) % 12
        votos[idx] = votos.get(idx, 0) + 1
    idx = max(votos, key=votos.get)
    return SIGNOS_TXT[idx], SIGNOS_ES[idx]


class Catalogo:
    """Índice HIP -> (ra, dec), desde HYG (J2000)."""

    def __init__(self, arquivo):
        self.hip = {}
        with gzip.open(arquivo, "rt") as f:
            cabeçalho = None
            for i, linea in enumerate(f):
                if i == 0:
                    cabeçalho = linea.split(",")
                    continue
                c = dict(zip(cabeçalho, linea.split(",")))
                try:
                    h = int(float(c.get("hip") or 0))
                    r = float(c.get("ra") or 0) * 15.0  # HYG: ra en HORAS (0-24)
                    d = float(c.get("dec") or 0)       # dec en GRADOS
                except (ValueError, KeyError):
                    continue
                if h:
                    self.hip[h] = (r, d)

    def pos(self, hip):
        try:
            return self.hip.get(int(hip))
        except (TypeError, ValueError):
            # referências não numéricas (DSO:NGC…, etc.) não se resolvem por HIP
            return None


def _asterismos_de(camiño):
    indice = os.path.join(camiño, "index.json")
    if not os.path.isfile(indice):
        return []
    with open(indice, "r", encoding="utf-8") as f:
        data = json.load(f)
    out = []
    for c in data.get("constellations", []):
        nomes = c.get("common_name", {})
        nativo = nomes.get("native") or nomes.get("english") or c.get("id")
        ingles = nomes.get("english")
        hips = [h for li in c.get("lines", []) for h in li]
        out.append({"id": c.get("id"), "nativo": nativo,
                    "ingles": ingles, "hips": hips})
    return out


def assimilar_cultura(nombre, cat, asterismos=None, detalhe=False):
    """Retorna os asterismos de uma cultura com a sua ponte geométrica ao signo."""
    if asterismos is None:
        asterismos = _asterismos_de(os.path.join(SKY, nombre))
    resu = []
    for a in asterismos:
        posiciones = [cat.pos(h) for h in a["hips"] if cat.pos(h)]
        if not posiciones:
            continue
        lams = []
        for rr, dd in posiciones:
            rr, dd = math.radians(rr), math.radians(dd)
            lam = math.degrees(math.atan2(
                math.sin(rr) * math.cos(EPS) + math.tan(dd) * math.sin(EPS),
                math.cos(rr))) % 360.0
            lams.append(lam)
        signo, signo_es = _assinar_por_voto(lams)
        if signo is None:
            continue
        fila = {"asterismo": a["nativo"], "ingles": a["ingles"],
                "signo": signo, "signo_es": signo_es,
                "hip": a["hips"][:2], "n_estrelas": len(lams),
                "lon_eclip": round(_ecl_media(lams), 2)}
        if detalhe:
            fila["estrelas"] = [{"hip": h, "lon_eclip": round(l, 2)}
                                for h, l in zip(a["hips"], lams)]
        resu.append(fila)
    return resu


def assimilar_todo(cat, culturas=None):
    """Totes les cultures: {cultura: [asterismos con liga]}."""
    if culturas is None:
        culturas = sorted(
            n for n in os.listdir(SKY)
            if os.path.isdir(os.path.join(SKY, n)) and not n.startswith("_"))
    total = {}
    for c in culturas:
        lista = assimilar_cultura(c, cat)
        if lista:
            total[c] = lista
    return total


def assimilados_por_signo(todo, cultura=None):
    """{cultura: {signo_es: [{asterismo, ingles, lon_eclip}, ...]}}."""
    culturas = [cultura] if cultura else sorted(todo)
    out = {}
    for c in culturas:
        por_signo = {}
        for f in todo.get(c, []):
            por_signo.setdefault(f["signo_es"], []).append(
                {"asterismo": f["asterismo"], "ingles": f["ingles"],
                 "lon_eclip": f["lon_eclip"]})
        out[c] = por_signo
    return out


def cmd():
    ap = argparse.ArgumentParser(description=__doc__.strip())
    ap.add_argument("--cat", required=True, help="caminho ao catálogo hyg*.csv.gz")
    ap.add_argument("--cultura", default=None)
    ap.add_argument("--saida", default=None)
    args = ap.parse_args()
    cat = Catalogo(args.cat)
    if args.cultura:
        for f in assimilar_cultura(args.cultura, cat, detalhe=True):
            print(f"  {f['asterismo']:42} -> {f['signo']:12} "
                  f"(lon {f['lon_eclip']}°, {f['n_estrelas']} estrelas)")
        return
    todo = assimilar_todo(cat)
    n_total = sum(len(v) for v in todo.values())
    for c, lista in sorted(todo.items()):
        signos = sorted({f["signo_es"] for f in lista})
        print(f"{c:32} {len(lista):3} asterismos  signos: {', '.join(signos)}")
    print(f"\nTotal asterismos asimilados: {n_total}")
    if args.saida:
        with open(args.saida, "w", encoding="utf-8") as f:
            json.dump(assimilados_por_signo(todo), f, ensure_ascii=False, indent=2)
        print("gravado:", args.saida)


if __name__ == "__main__":
    cmd()