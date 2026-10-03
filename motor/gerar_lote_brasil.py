#!/usr/bin/env python3
"""Gera um lote de mapas pelo novo catálogo nacional de municípios (IBGE),
mostrando o seletor estado→município em ação: um mapa por cidade, em várias
culturas arquétipas. Artefatos vão para `mapas/brasil/`.

Uso:
    venv/bin/python /mnt/dados/ephemeris/gerar_lote_brasil.py
"""
import os
import sys

sys.path.insert(0, "/mnt/dados/ephemeris")
import localidades_brasil as lb
from gerar_mapa import gerar_tudo

MAPAS = "/mnt/dados/home-italivre/iastro-ia/mapas"
EX = os.path.join(MAPAS, "brasil")

# (chave canônica cidade|uf, data, hora, cultura, tema, feeling)
LOTE = [
    ("itapemirim|es", "1982-11-20", "01:30", "capixaba",
     "a raiz do sul", "esperanca"),
    ("guarapari|es", "1990-12-25", "15:00", "capixaba",
     "praia e horizonte aberto", "encantamento"),
    ("vitoria|es", "1987-09-03", "11:45", "indigena",
     "ema sobre a baía", "serenidade"),
    ("rio de janeiro|rj", "1968-05-12", "06:20", "carioca",
     "cidade maravilhosa", "paixao"),
    ("salvador|ba", "1975-02-02", "05:10", "afro",
     "axé da primeira luz", "esperanca"),
    ("sao paulo|sp", "1980-04-08", "19:30", "folclore-brasileiro",
     "gigante urbana", "coragem"),
    ("belo horizonte|mg", "1979-06-16", "12:00", "mapuche",
     "horizonte das montanhas", "melancolia"),
    ("curitiba|pr", "1993-10-05", "22:10", "zodiaco",
     "serra e pinheirais", "curiosidade"),
    ("brasilia|df", "1977-08-21", "09:00", "zodiaco",
     "capital do planalto", "esperanca"),
    ("manaus|am", "1998-07-07", "21:20", "indigena",
     "rio e floresta", "encantamento"),
    ("rio branco|ac", "2001-03-14", "06:00", "folclore-brasileiro",
     "seringal e aurora", "serenidade"),
    ("fortaleza|ce", "1972-05-30", "16:45", "afro",
     "jangada ao vento", "paixao"),
]


def main():
    os.makedirs(EX, exist_ok=True)
    itens, total_kb = [], 0.0
    for chave, data, hora, cultura, tema, feeling in LOTE:
        m = lb.MUNICIPIOS.get(chave)
        if not m:
            print(f"[!!] local desconhecido: {chave}")
            continue
        nome = f"{m['nome'].lower().replace(' ', '-')}-{m['uf'].lower()}"
        base = os.path.join(EX, nome)

        class A:
            pass
        a = A()
        a.data, a.hora = data, hora
        a.local, a.cultura = chave, cultura
        a.tema, a.feeling, a.mensaje = tema, feeling, None
        pacote, tam = gerar_tudo(a, base)
        sol = pacote.get("sol_signo") or "?"
        asc = pacote.get("asc_signo") or "?"
        print(f"[OK] {nome} — {lb.exibir(chave)} · Sol {sol} · Asc {asc}")
        total_kb += sum(tam.values())
        itens.append((nome, tam, sol, asc))

    html = []
    html.append("<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
                "<title>iastro — mapa do Brasil (estado → município)</title>"
                "<style>body{font-family:system-ui;max-width:840px;margin:2rem auto;"
                "padding:0 1rem;color:#222}li{margin:.8rem 0}</style></head><body>"
                "<h1>iastro · lote Brasil (catálogo IBGE)</h1>"
                "<p>Um mapa por cidade, escolhendo estado → município no app. "
                f"Fusos: {len(lb.MUNICIPIOS)} municípios catalogados.</p><ul>")
    for nome, tam, sol, asc in itens:
        html.append(f"<li><strong>{nome}</strong> — Sol em {sol}, Asc em {asc}"
                    f"<br><a href='{nome}.html'>obra interativa</a> · "
                    f"<a href='{nome}.png'>PNG</a> · "
                    f"<a href='{nome}.json'>dados (JSON)</a></li>")
    html.append("</ul></body></html>")
    idx = os.path.join(EX, "indice.html")
    with open(idx, "w", encoding="utf-8") as f:
        f.write("\n".join(html))
    print(f"\nÍndice: {idx}")
    print(f"Total da rodada: {round(total_kb, 1)} KB")


if __name__ == "__main__":
    main()