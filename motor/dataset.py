#!/usr/bin/env python3
"""Constrói o dataset de aprendizado de máquina a partir das efemérides.

Lê os arquivos JSON mensais de /mnt/dados/ephemeris e monta uma tabela
(CSV + Parquet) com UMA LINHA POR DIA. Cada linha contém características
numéricas úteis para machine learning:

  - longitude de cada planeta (graus 0..360, variável circular)
  - seno e cosseno da longitude (codificação circular, ideal p/ ML)
  - signo de cada planeta (índice 0..11)
  - velocidade de cada planeta
  - presença de cada aspecto clássico (1/0)

Saída:
  /mnt/dados/ephemeris/dataset_planetas.csv
  /mnt/dados/ephemeris/dataset_planetas.parquet (se pyarrow estiver presente)

Uso:
  python3 dataset.py                 # usa todo o intervalo existente
  python3 dataset.py 2020 2022       # só um intervalo de anos
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

EPHEMERIS_DIR = "/mnt/dados/ephemeris"
PLANETAS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter",
            "Saturn", "Uranus", "Neptune", "Pluto"]
NAMES_ASPECTOS = ["conjuncao", "sextil", "quadratura", "trino", "oposicao"]
PARES_ASPECTOS = []  # preenchido abaixo

for i in range(len(PLANETAS)):
    for j in range(i + 1, len(PLANETAS)):
        PARES_ASPECTOS.append(f"{PLANETAS[i]}-{PLANETAS[j]}")


def ler_arquivos(anos):
    padroes = []
    if anos:
        for ano in range(anos[0], anos[1] + 1):
            padroes.append(f"{EPHEMERIS_DIR}/{ano}-*.json")
    else:
        padroes.append(f"{EPHEMERIS_DIR}/*-*.json")
    arquivos = []
    for p in padroes:
        arquivos.extend(sorted(glob.glob(p)))
    return arquivos


def main():
    anos = None
    if len(sys.argv) > 1:
        anos = (int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2
                else int(sys.argv[1]))

    arquivos = ler_arquivos(anos)
    linhas = []

    for arquivo in arquivos:
        with open(arquivo, encoding="utf-8") as f:
            dados = json.load(f)
        for data_str, dia in dados["daily"].items():
            linha = {"data": data_str}
            for p in PLANETAS:
                rec = dia.get(p, {})
                lon = rec.get("lon", 0.0)
                linha[f"{p}_lon"] = round(lon, 4)
                linha[f"{p}_sin"] = round(np.sin(np.radians(lon)), 4)
                linha[f"{p}_cos"] = round(np.cos(np.radians(lon)), 4)
                linha[f"{p}_signo"] = rec.get("z", 0)
                linha[f"{p}_vel"] = round(rec.get("sp", 0.0), 4)
                linha[f"{p}_retro"] = 1 if rec.get("r") else 0
            # Aspectos
            asp = dia.get("aspects", {})
            for par in PARES_ASPECTOS:
                linha[f"asp_{par}"] = 0
            for par, rec in asp.items():
                nome = rec.get("aspecto")
                if nome and f"asp_{par}" in linha:
                    linha[f"asp_{par}"] = 1
            linhas.append(linha)

    df = pd.DataFrame(linhas)
    df["data"] = pd.to_datetime(df["data"])
    df = df.sort_values("data").reset_index(drop=True)

    csv_path = os.path.join(EPHEMERIS_DIR, "dataset_planetas.csv")
    df.to_csv(csv_path, index=False)
    print(f"CSV salvo em: {csv_path}  ({len(df)} linhas x {df.shape[1]} colunas)")

    try:
        import pyarrow  # noqa
        parquet_path = os.path.join(EPHEMERIS_DIR, "dataset_planetas.parquet")
        df.to_parquet(parquet_path, index=False)
        print(f"Parquet salvo em: {parquet_path}")
    except ImportError:
        pass

    print("\nPrévia (3 primeiras linhas, Sol e seus aspectos):")
    cols = [c for c in df.columns if c.startswith("Sun") or c.startswith("asp_Sun")]
    print(df[["data"] + cols].head(3).to_string(index=False))


if __name__ == "__main__":
    main()
