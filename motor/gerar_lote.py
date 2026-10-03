#!/usr/bin/env python3
"""Gera um LOTE pequeno de mapas de demonstração (sul do ES + locais do banco)
de uma só vez, com um índice HTML único que lista todos. Respeita o disco:
número pequeno e controlado; os artefatos vão para `mapas/exemplos/`.

Uso:
    venv/bin/python /mnt/dados/ephemeris/gerar_lote.py
"""
import os
import sys

sys.path.insert(0, "/mnt/dados/ephemeris")
from gerar_mapa import gerar_tudo
import argparse

MAPAS = "/mnt/dados/home-italivre/iastro-ia/mapas"
EX = os.path.join(MAPAS, "exemplos")

# (nome, data, hora, local, cultura, tema, feeling)
LOTE = [
    # (nome, data, hora, local, cultura, tema, feeling)
    # Exemplos do sul do ES: só arquétipos LOCAIS capixabas (lista que começou).
    # Mapuche é cultura autônoma (Chile/Argentina) — não entra aqui como local ES.
    ("isis-marataizes", "1990-01-15", "08:00", "itapemirim", "capixaba",
     "a princesa das águas", "esperanca"),
    ("mae-ba-guarapari", "1968-05-12", "06:20", "vitória", "capixaba",
     "lagoa e raiz", "esperanca"),
    ("iracema-piuma", "1995-12-25", "14:30", "piúma", "folclore-brasileiro",
     "lua sobre a barra", "saudade"),
    ("tupi-vitoria", "1987-09-03", "11:45", "vitória", "indigena",
     "ema no horizonte", "esperanca"),
    ("cruz-muribeca", "1910-08-19", "02:00", "itapemirim", "capixaba",
     "a raiz-fundadora do sul", "esperanca"),
]


def _link(name, base):
    return f"<li><a href='{name}'>{base}</a></li>"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", default=EX)
    args = ap.parse_args()
    os.makedirs(args.saida, exist_ok=True)

    itens = []
    total_kb = 0
    for nome, data, hora, local, cultura, tema, feeling in LOTE:
        base = os.path.join(args.saida, nome)
        # os itens já recebem --saida base; basta um "objeto args" simples
        class A: pass
        a = A()
        a.data, a.hora, a.local = data, hora, local
        a.cultura, a.tema, a.feeling = cultura, tema, feeling
        pacote, tam = gerar_tudo(a, base)
        print(f"[OK] {nome}: {tam}")
        total_kb += sum(tam.values())
        itens.append((nome, tam, pacote["sol_signo"], pacote.get("asc_signo")))

    # índice único
    html = []
    html.append("<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
                "<title>iastro — exemplos (mapa multi-cultura)</title>"
                "<style>body{font-family:system-ui;max-width:800px;margin:2rem auto;"
                "padding:0 1rem;color:#222}li{margin:.6rem 0}</style></head><body>"
                "<h1>iastro · exemplos da obra</h1><ul>")
    for nome, tam, sol, asc in itens:
        t_png = tam.get(nome + ".png", 0)
        t_html = tam.get(nome + ".html", 0)
        t_json = tam.get(nome + ".json", 0)
        html.append(f"<li><strong>{nome}</strong> — Sol em {sol}, Asc em {asc}"
                    f"<br><a href='{nome}.html'>obra interativa</a> · "
                    f"<a href='{nome}.png'>PNG</a> · "
                    f"<a href='{nome}.json'>dados (JSON)</a>"
                    f"<br><small>PNG {t_png} KB · HTML {t_html} KB · JSON {t_json} KB</small></li>")
    html.append("</ul><p>Mapas gerados automaticamente pelo iastro fico "
                "(pipeline único: mapa tradicional → plantas → céu da cultura → colagem)."
                "</p></body></html>")
    idx = os.path.join(args.saida, "indice.html")
    open(idx, "w", encoding="utf-8").write("\n".join(html))
    print(f"\nÍndice: {idx}")
    print(f"Total na rodada: {round(total_kb,1)} KB")


if __name__ == "__main__":
    main()