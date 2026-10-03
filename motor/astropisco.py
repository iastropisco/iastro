#!/usr/bin/env python3
"""Astropisco - Assistente com efemérides integrada"""
import json
import sys
import os
import subprocess
from datetime import datetime

SIGNOS = {
    0: "Áries", 1: "Touro", 2: "Gêmeos", 3: "Câncer",
    4: "Leão", 5: "Virgem", 6: "Libra", 7: "Escorpião",
    8: "Sagitário", 9: "Capricórnio", 10: "Aquário", 11: "Peixes"
}

PLANETAS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
PLANETAS_PT = {
    "Sun": "Sol", "Moon": "Lua", "Mercury": "Mercúrio", "Venus": "Vênus",
    "Mars": "Marte", "Jupiter": "Júpiter", "Saturn": "Saturno",
    "Uranus": "Urano", "Neptune": "Netuno", "Pluto": "Plutão"
}

EPHEMERIS_DIR = "/mnt/dados/ephemeris"

def get_positions(date_str):
    year, month, day = date_str.split("-")
    month_file = f"{EPHEMERIS_DIR}/{year}-{month.zfill(2)}.json"
    if not os.path.exists(month_file):
        return None
    with open(month_file) as f:
        data = json.load(f)
    day_data = data.get("daily", {}).get(date_str)
    if not day_data:
        return None
    result = {}
    for planet in PLANETAS:
        p = day_data.get(planet, {})
        zodiac_idx = p.get("z", 0)
        degree = p.get("d", 0)
        retro = p.get("r", False)
        signo = SIGNOS.get(zodiac_idx, "?")
        retro_txt = " (retrogrado)" if retro else ""
        result[PLANETAS_PT[planet]] = f"{signo} {degree}°{retro_txt}"
    return result

def build_context(date_str, hora=""):
    positions = get_positions(date_str)
    if not positions:
        return ""
    
    ctx = f"Posições planetárias em {date_str}"
    if hora:
        ctx += f" às {hora}"
    ctx += " (UTC, fonte: Swiss Ephemeris):\n"
    
    for planeta, pos in positions.items():
        ctx += f"- {planeta}: {pos}\n"
    
    return ctx

def ask_astropisco(pergunta, date_str=None, hora=""):
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    ephemeris_ctx = build_context(date_str, hora)
    
    system_prompt = f"""Você é o Astropisco, assistente do Planetário Astrológico Reciclável de Itapemirim-ES.

CONTEXTO ASTROLÓGICO (Swiss Ephemeris):
{ephemeris_ctx}

REGRAS:
1. Use as posições planetárias acima para responder perguntas astrológicas.
2. NUNCA invente posições - use apenas os dados fornecidos.
3. Para signos do Sol: Áries (21/03-19/04), Touro (20/04-20/05), Gêmeos (21/05-20/06), Câncer (21/06-22/07), Leão (23/07-22/08), Virgem (23/08-22/09), Libra (23/09-22/10), Escorpião (23/10-21/11), Sagitário (22/11-21/12), Capricórnio (22/12-19/01), Aquário (20/01-18/02), Peixes (19/02-20/03).
4. Para a Lua: posicione conforme os dados fornecidos.
5. Conhecimento PANCs: Erva Baleeira, Chanana, Araçá, Mastruço, Jurubeba, Batata Doce, Amora, Urucum, Crista de Galo, Alfavaca, Melissa, Aroeira, Cúrcuma.
6. Responda em português brasileiro, de forma simples.
7. Se não souber, diga que não sabe. NUNCA invente."""
    
    # Call Ollama API
    payload = {
        "model": "astropisco",
        "prompt": pergunta,
        "system": system_prompt,
        "stream": False,
        "options": {"num_predict": 500}
    }
    
    result = subprocess.run(
        ["curl", "-s", "http://127.0.0.1:11434/api/generate",
         "-d", json.dumps(payload)],
        capture_output=True, text=True, timeout=300
    )
    
    try:
        response = json.loads(result.stdout)
        return response.get("response", "Erro ao obter resposta.")
    except:
        return "Erro ao processar resposta da IA."

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 astropisco.py 'sua pergunta' [YYYY-MM-DD] [HH:MM]")
        sys.exit(1)
    
    pergunta = sys.argv[1]
    date_str = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y-%m-%d")
    hora = sys.argv[3] if len(sys.argv) > 3 else ""
    
    print(f"\nConsulta: {pergunta}")
    print(f"Data: {date_str} {hora}\n")
    
    resposta = ask_astropisco(pergunta, date_str, hora)
    print(f"Astropisco: {resposta}")
