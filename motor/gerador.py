#!/usr/bin/env python3
"""Gerador de efemérides planetárias + aspectos (Swiss Ephemeris / pyswisseph).

Gera um arquivo JSON por mês, no mesmo formato usado pelo astropisco,
acrescentando agora a seção "aspects" (ângulos entre planetas).

Fonte dos dados: Swiss Ephemeris (o MESMO motor que o astro.com usa),
via biblioteca pyswisseph. Dados astronômicos precisos, sem inventar nada.

Convenção:
  - 00:00 UTC de cada dia (posição ao meio-dia GMT efetivo de início do dia).
  - Tropico (zodíaco tropical), mesmo padrão da astrologia ocidental ocidental
    usada pelo astro.com.
  - 10 corpos: Sol, Lua, Mercúrio, Vênus, Marte, Júpiter, Saturno, Urano,
    Netuno e Plutão.

Uso:
  python3 gerador.py 2026 2026        # ano inicial e final (inclusive)
  python3 gerador.py 1900 2100        # 201 anos completos
  python3 gerador.py 2026             # só um ano
"""
import json
import os
import sys
import datetime

import swisseph as swe

EPHEMERIS_DIR = "/mnt/dados/ephemeris"
PLANETAS = [
    ("Sun", swe.SUN), ("Moon", swe.MOON), ("Mercury", swe.MERCURY),
    ("Venus", swe.VENUS), ("Mars", swe.MARS), ("Jupiter", swe.JUPITER),
    ("Saturn", swe.SATURN), ("Uranus", swe.URANUS), ("Neptune", swe.NEPTUNE),
    ("Pluto", swe.PLUTO),
]

# Asteróides arquetípicos (msg. mitol. atrás deles), calculados com o mesmo
# Swiss Ephemeris (FLG_MOSEPH não precisa de arquivos extras).
# índices do pyswisseph instalado: 12=apogeu médio/Lilith, 15=Quíron,
# 17=Ceres, 18=Pallas, 19=Juno, 20=Vesta.
ASTEROIDES = [
    ("Quíron", 15), ("Lilith", 12), ("Ceres", 17),
    ("Pallas", 18), ("Juno", 19), ("Vesta", 20),
]

# Aspectos clássicos: nome, ângulo exato, orbe (tolerância) em graus
ASPECTOS = [
    ("conjuncao", 0, 8),
    ("sextil", 60, 6),
    ("quadratura", 90, 6),
    ("trino", 120, 6),
    ("oposicao", 180, 8),
]

# Símbolos de fase da Lua
FASES_LUA = {0: "\U0001f311", 1: "\U0001f312", 2: "\U0001f313", 3: "\U0001f314",
             4: "\U0001f315", 5: "\U0001f316", 6: "\U0001f317", 7: "\U0001f318"}


def angulo_menor(a, b):
    """Menor ângulo entre duas longitudes (0..180)."""
    diff = abs(a - b) % 360
    return diff if diff <= 180 else 360 - diff


def fase_lua(elongacao):
    """Índice de fase da Lua (0..7) a partir da elongação Sol-Lua em graus."""
    return int(round(elongacao / 45.0)) % 8


def calcular_aspectos(planetas):
    """Calcula os aspectos entre pares de planetas do dia.

    planetas: dict nome -> {'lon': float, ...}
    Retorna: dict nome_par -> {'aspecto': str, 'angulo': float}
    """
    resultado = {}
    nomes = list(planetas.keys())
    for i in range(len(nomes)):
        for j in range(i + 1, len(nomes)):
            a, b = nomes[i], nomes[j]
            lon_a = planetas[a]["lon"]
            lon_b = planetas[b]["lon"]
            menor = angulo_menor(lon_a, lon_b)
            for nome_aspecto, angulo_exato, orbe in ASPECTOS:
                if abs(menor - angulo_exato) <= orbe:
                    chave = f"{a}-{b}"
                    resultado[chave] = {
                        "aspecto": nome_aspecto,
                        "angulo": round(menor, 2),
                    }
                    break
    return resultado


def posicoes_do_dia(jd):
    """Calcula posições e velocidade dos corpos (10 + asteróides) p/ o dia."""
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    planetas = {}
    for nome, pid in PLANETAS:
        pos = swe.calc_ut(jd, pid, flags)
        lon = pos[0][0]
        velocidade = pos[0][3]
        signo_idx = int(lon // 30)
        grau_no_signo = int(lon % 30)
        retrogrado = velocidade < 0
        planetas[nome] = {
            "lon": round(lon, 6),
            "z": signo_idx,
            "d": grau_no_signo,
            "r": retrogrado,
            "sp": round(velocidade, 6),
        }
    for nome, pid in ASTEROIDES:
        pos = swe.calc_ut(jd, pid, swe.FLG_MOSEPH | swe.FLG_SPEED)
        lon = pos[0][0]
        velocidade = pos[0][3]
        planetas[nome] = {
            "lon": round(lon, 6),
            "z": int(lon // 30),
            "d": int(lon % 30),
            "r": velocidade < 0,
            "sp": round(velocidade, 6),
        }
    # Fase da Lua pela elongação Sol-Lua
    elongacao = angulo_menor(planetas["Moon"]["lon"], planetas["Sun"]["lon"])
    planetas["Moon"]["ph"] = FASES_LUA[fase_lua(elongacao)]
    return planetas


def gerar_mes(ano, mes):
    """Gera o arquivo JSON de um mês inteiro."""
    planetas_do_ano = {}
    primeiro_dia = datetime.date(ano, mes, 1)
    if mes == 12:
        ultimo_dia = datetime.date(ano, 12, 31)
    else:
        ultimo_dia = datetime.date(ano, mes + 1, 1) - datetime.timedelta(days=1)

    data = datetime.date(ano, mes, 1)
    while data <= ultimo_dia:
        jd = swe.julday(data.year, data.month, data.day, 0, swe.GREG_CAL)
        planetas_do_ano[data.isoformat()] = posicoes_do_dia(jd)
        data += datetime.timedelta(days=1)

    # Calcula aspectos para cada dia
    dias = {}
    for data_str, planetas in planetas_do_ano.items():
        rec = dict(planetas)
        rec["aspects"] = calcular_aspectos(planetas)
        dias[data_str] = rec

    conteudo = {
        "version": "2.5.7",
        "fonte": "Swiss Ephemeris (Swiss Ephemeris via pyswisseph)",
        "convencao": "00:00 UTC, zodíaco tropical",
        "month": {"year": ano, "month": mes},
        "daily": dias,
    }

    nome_arquivo = f"{EPHEMERIS_DIR}/{ano}-{mes:02d}.json"
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        json.dump(conteudo, f, ensure_ascii=False, indent=2)
    return nome_arquivo, len(dias)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    ano0 = int(args[0])
    ano1 = int(args[1]) if len(args) > 1 else ano0

    if not os.path.exists(EPHEMERIS_DIR):
        os.makedirs(EPHEMERIS_DIR)

    total_dias = 0
    for ano in range(ano0, ano1 + 1):
        for mes in range(1, 13):
            nome_arquivo, ndias = gerar_mes(ano, mes)
            total_dias += ndias
            print(f"Gerado: {os.path.basename(nome_arquivo)} ({ndias} dias)")
    print(f"\nConcluído: {ano0}-{ano1+1}... {total_dias} dias no total.")


if __name__ == "__main__":
    main()
