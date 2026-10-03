#!/usr/bin/env python3
"""Consulta efemérides planetárias 2026 - Swiss Ephemeris data"""
import json
import sys
import os

SIGNOS = {
    0: "Áries", 1: "Touro", 2: "Gêmeos", 3: "Câncer",
    4: "Leão", 5: "Virgem", 6: "Libra", 7: "Escorpião",
    8: "Sagitário", 9: "Capricórnio", 10: "Aquário", 11: "Peixes"
}

SIGNOS_EN = {
    0: "Aries", 1: "Taurus", 2: "Gemini", 3: "Cancer",
    4: "Leo", 5: "Virgo", 6: "Libra", 7: "Scorpio",
    8: "Sagittarius", 9: "Capricorn", 10: "Aquarius", 11: "Pisces"
}

PLANETAS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
PLANETAS_PT = {
    "Sun": "Sol", "Moon": "Lua", "Mercury": "Mercúrio", "Venus": "Vênus",
    "Mars": "Marte", "Jupiter": "Júpiter", "Saturn": "Saturno",
    "Uranus": "Urano", "Neptune": "Netuno", "Pluto": "Plutão"
}

EPHEMERIS_DIR = "/mnt/dados/ephemeris"

def get_positions(date_str):
    """Busca posições planetárias para uma data (YYYY-MM-DD)"""
    year, month, day = date_str.split("-")
    month_file = f"{EPHEMERIS_DIR}/{year}-{month.zfill(2)}.json"
    
    if not os.path.exists(month_file):
        return None
    
    with open(month_file) as f:
        data = json.load(f)
    
    daily = data.get("daily", {})
    day_data = daily.get(date_str)
    
    if not day_data:
        return None
    
    result = {"data": date_str, "planetas": {}}
    
    for planet in PLANETAS:
        p = day_data.get(planet, {})
        zodiac_idx = p.get("z", 0)
        degree = p.get("d", 0)
        retro = p.get("r", False)
        speed = p.get("sp", 0)
        
        signo_pt = SIGNOS.get(zodiac_idx, "?")
        retro_txt = " (R)" if retro else ""
        
        result["planetas"][PLANETAS_PT[planet]] = {
            "signo": signo_pt,
            "graus": degree,
            "retrogrado": retro,
            "velocidade": round(speed, 3)
        }
    
    return result

def format_result(data):
    """Formata resultado em texto legível"""
    if not data:
        return "Data não encontrada na efemérides."
    
    lines = [f"Posições planetárias em {data['data']}:"]
    lines.append("")
    
    for nome, info in data["planetas"].items():
        retro = " ℞" if info["retrogrado"] else ""
        lines.append(f"  {nome}: {info['signo']} {info['graus']}°{retro}")
    
    return "\n".join(lines)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 efemeris.py YYYY-MM-DD")
        print("Exemplo: python3 efemeris.py 2026-08-25")
        sys.exit(1)
    
    date_str = sys.argv[1]
    result = get_positions(date_str)
    
    if result:
        print(format_result(result))
    else:
        print(f"Data {date_str} não encontrada.")
