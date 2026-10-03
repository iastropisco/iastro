#!/usr/bin/env python3
"""Converte o corpus do blog em linhas {"text": ...} para fine-tuning.

Gera corpus-astropisco.token.jsonl, usado como entrada de LoRA/fine-tune
num modelo de base (ex. qwen3). Rode quando quiser preparar o treino:
    python3 fazer_token_corpus.py

Formato de saída (uma linha por post):
    {"text": "Título\n<texto do post>"}
"""
import json
import os
import re

AQUI = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(AQUI, "corpus-astropisco.token.jsonl")


def main():
    with open(os.path.join(AQUI, "corpus-bruto.json"), encoding="utf-8") as f:
        posts = json.load(f)

    linhas = []
    n_uteis = 0
    for p in posts:
        texto = (p.get("texto") or "").strip()
        # remove marcadores de mídia (ruído para treino de linguagem)
        texto = re.sub(r"\[(imagem|video)(| \d+)\]", " ", texto)
        texto = re.sub(r"\s{2,}", " ", texto).strip()
        # ignora posts sem texto útil (só imagem/vídeo)
        corpo = re_palavras(texto)
        if corpo < 3:
            continue
        bloco = f"{p['titulo']}\n{texto}".strip()
        linhas.append(json.dumps({"text": bloco}, ensure_ascii=False))
        n_uteis += 1

    with open(DESTINO, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))

    print(f"Convertidos {n_uteis} posts uteis de {len(posts)}.")
    print(f"Gerado: {DESTINO}  ({os.path.getsize(DESTINO)} bytes)")


def re_palavras(texto):
    return len(re.findall(r"\S+", texto))


if __name__ == "__main__":
    main()
