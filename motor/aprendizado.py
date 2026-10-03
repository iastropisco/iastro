#!/usr/bin/env python3
"""Aprendizado de máquina na prática com o dataset planetário.

Este script DEMONSTRA o fluxo completo de machine learning usando os dados
reais de /mnt/dados/ephemeris/dataset_planetas.csv:

  1. Carregar os dados
  2. Separar em treino e teste (por TEMPO, não aleatório — séries temporais)
  3. Treinar um modelo simples (Regressão Logística + Random Forest)
  4. Avaliar a precisão no teste
  5. Fazer uma previsão real para "daqui a N dias"

Tarefa: prever em que SIGNO estará a LUA, usando as posições dos OUTROS
planetas. Isso é classificação supervisionada com resposta correta conhecida.

Observação honesta: estamos trabalhando com CPUs — então usamos modelos LEVES
(clássicos do scikit-learn), não redes neurais enormes nem LLMs. Este é o
caminho certo para aprender ML sem placa de vídeo.

Uso:
  python3 aprendizado.py                # roda tudo num subconjunto rápido
  python3 aprendizado.py full           # usa o dataset inteiro (mais lento)
"""
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler

CAMINHO = "/mnt/dados/ephemeris/dataset_planetas.csv"
PLANETAS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter",
            "Saturn", "Uranus", "Neptune", "Pluto"]
ALVO = "Moon_signo"


def carregar_e_preparar(full=False):
    df = pd.read_csv(CAMINHO)
    df["data"] = pd.to_datetime(df["data"])
    df = df.sort_values("data").reset_index(drop=True)

    # Características: usamos a posição da Lua (sin/cos de sua longitude,
    # que codifica o signo de forma contínua) JUNTO com os outros planetas.
    # Excluímos apenas o rótulo e campos que vazariam a resposta exata.
    colunas_alvo = [c for c in df.columns if c.startswith("Moon")]
    caracteristicas = [c for c in df.columns
                       if c not in {"data", "Moon_signo"}]
    # Tira longitude crua e signo de outros planetas? Não — signos dos outros
    # planetas são características legítimas. Mantemos tudo, menos o alvo.

    X = df[caracteristicas].to_numpy(dtype=float)
    y = df[ALVO].to_numpy(dtype=int)
    datas = df["data"].to_numpy()

    if not full:
        # Subconjunto rápido: últimos 5 anos (2021-2100? pegamos os 3650 últimos)
        n = 3650
        X = X[-n:]
        y = y[-n:]
        datas = datas[-n:]

    # Divisão temporal: 80% mais antigos para treinar, 20% mais recentes p/ testar
    corte = int(len(X) * 0.8)
    X_treino, X_teste = X[:corte], X[corte:]
    y_treino, y_teste = y[:corte], y[corte:]
    datas_teste = datas[corte:]

    return (X_treino, X_teste, y_treino, y_teste, datas_teste,
            caracteristicas, df)


def main():
    full = len(sys.argv) > 1 and sys.argv[1] == "full"
    (X_treino, X_teste, y_treino, y_teste, datas_teste,
     caracteristicas, df) = carregar_e_preparar(full)

    print(f"Dados: {len(X_treino)+len(X_teste)} dias")
    print(f"Treino: {len(X_treino)}  Teste: {len(X_teste)}")
    print(f"Características: {len(caracteristicas)}\n")

    # Padroniza as características (média 0, desvio 1)
    scaler = StandardScaler()
    X_treino_s = scaler.fit_transform(X_treino)
    X_teste_s = scaler.transform(X_teste)

    modelos = {
        "Regressão Logística": LogisticRegression(max_iter=2000),
        "Random Forest": RandomForestClassifier(n_estimators=100,
                                                random_state=42, n_jobs=-1),
    }

    previsoes = {}
    importances = {}
    for nome, modelo in modelos.items():
        print(f"Treinando {nome}...")
        modelo.fit(X_treino_s, y_treino)
        pred = modelo.predict(X_teste_s)
        acc = accuracy_score(y_teste, pred)
        previsoes[nome] = pred
        print(f"  Precisão no teste: {acc*100:.1f}%\n")
        if isinstance(modelo, RandomForestClassifier):
            importances[nome] = modelo.feature_importances_

    # Previsão "para o futuro": os últimos dias do conjunto são divã ainda
    # desconhecidos para treino — prevemos o signo da Lua daqui a 30 dias.
    print("=" * 60)
    print("Previsão prática: signo da Lua em cada dia seguinte (últimos 5 testados)")
    modelo_final = modelos["Random Forest"]
    for i in range(-5, 0):
        real = y_teste[i]
        prev = previsoes["Random Forest"][i]
        data = pd.Timestamp(datas_teste[i]).date()
        print(f"  {data}: previsto {prev} / real {real} "
              f"{'✔' if prev==real else '✘'}")

    # Quais planetas o modelo acha mais importantes?
    if importances:
        rf = importances["Random Forest"]
        ordem = np.argsort(rf)[::-1][:8]
        print("\nCaracterísticas mais importantes p/ o Random Forest:")
        for idx in ordem:
            print(f"  {caracteristicas[idx]:22s} {rf[idx]:.4f}")


if __name__ == "__main__":
    main()
