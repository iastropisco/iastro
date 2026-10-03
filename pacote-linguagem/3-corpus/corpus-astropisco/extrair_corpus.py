#!/usr/bin/env python3
"""Extrai os posts do blog Astro Pisco (feed RSS) e monta o CORPUS de textos.

Gera:
  corpus-bruto.json   -> metadados + texto limpo de cada post
  corpus-astropisco.md -> texto corrido, pronto para leitura/treino
  corpus-astropisco.txt -> versão simples, sem título/marcação pesada

Uso: python3 extrair_corpus.py [arquivo.rss]
"""
import html
import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RSS_PATH = os.path.join(AQUI, "feeds_posts.rss")
if len(sys.argv) > 1:
    RSS_PATH = sys.argv[1]


def limpar_texto(conteudo):
    """Remove HTML e devolve o texto limpo de um post."""
    texto = html.unescape(conteudo)
    # Remove scripts e estilos
    texto = re.sub(r"<(script|style).*?</\1>", " ", texto, flags=re.S | re.I)
    # Marca imagens e iframes como [imagem] / [video]
    texto = re.sub(r"<iframe.*?</iframe>", " [video] ", texto, flags=re.S | re.I)
    texto = re.sub(r"<img[^>]*>", " [imagem] ", texto, flags=re.I)
    # Remove todas as outras tags
    texto = re.sub(r"<[^>]+>", " ", texto)
    # Decodifica entidades restantes
    texto = html.unescape(texto)
    # Normaliza espaços e quebras de linha
    texto = re.sub(r"[ \t\xa0]+", " ", texto)
    texto = re.sub(r" ?\n ?", "\n", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    texto = texto.strip()
    return texto


def main():
    with open(RSS_PATH, encoding="utf-8") as f:
        dados = f.read()

    # Separa cada item do feed
    itens = re.findall(r"<item>.*?</item>", dados, re.S)
    posts = []

    for item in itens:
        def pega(tag):
            m = re.search(rf"<{tag}>(.*?)</{tag}>", item, re.S)
            return html.unescape(m.group(1)).strip() if m else ""

        titulo = pega("title")
        data = pega("pubDate")
        link = re.search(r"<link>(.*?)</link>", item, re.S)
        link = html.unescape(link.group(1)).strip() if link else ""

        # Conteúdo no <description>
        m = re.search(r"<description>(.*?)</description>", item, re.S)
        conteudo_html = m.group(1) if m else ""
        texto = limpar_texto(conteudo_html)

        posts.append({
            "titulo": titulo,
            "data": data,
            "link": link,
            "texto": texto,
        })

    # 1) JSON bruto
    with open(os.path.join(AQUI, "corpus-bruto.json"), "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

    # 2) Markdown
    md = ["# Corpus do Astro Pisco", "",
          "Textos extraídos do blog astropisco.blogspot.com.",
          f"Total: {len(posts)} posts.\n"]
    for p in posts:
        md.append(f"## {p['titulo']}")
        md.append(f"*{p['data']}*  ")
        md.append(p["link"])
        md.append("")
        md.append(p["texto"])
        md.append("")
        md.append("---")
        md.append("")
    with open(os.path.join(AQUI, "corpus-astropisco.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    # 3) TXT simples
    txt = []
    for p in posts:
        txt.append(f"[{p['titulo']} — {p['data']}]")
        txt.append(p["texto"])
        txt.append("")
    with open(os.path.join(AQUI, "corpus-astropisco.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(txt))

    print(f"Extraídos {len(posts)} posts.")
    print("Arquivos gerados em", AQUI)
    for nome in ["corpus-bruto.json", "corpus-astropisco.md", "corpus-astropisco.txt"]:
        print(f"  - {nome}: {os.path.getsize(os.path.join(AQUI, nome))} bytes")


if __name__ == "__main__":
    main()
