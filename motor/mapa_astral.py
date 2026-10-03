#!/usr/bin/env python3
"""Calcula um Mapa Astral completo (posições exatas + casas + Ascendente).

Uso:
    python3 mapa_astral.py 1982-11-20 01:30 BH    (localidade curta conhecida)
    python3 mapa_astral.py 1982-11-20 01:30 --lat -19.9167 --lon -43.9333 --tz -3 --num BH
    python3 mapa_astral.py --json ...

Fuso: o script aceita --tz (offset UTC). Se não dado, usa -3 (Brasília).
Sistema de casas: Placidus.
"""
import json
import math
import sys

try:
    import swisseph as swe
    TEM_SWE = True
    # efemérides de asteróides (Quíron: seas_18/sepl_18), se baixadas
    import os as _os
    for _p in ("/mnt/dados/swisseph-ephe", "/usr/share/swisseph"):
        if _os.path.isdir(_p):
            try:
                swe.set_ephe_path(_p)
                break
            except Exception:
                continue
except Exception:
    TEM_SWE = False

try:
    import localidades_brasil as _lb
    TEM_LB = True
except Exception:
    _lb = None
    TEM_LB = False

SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem",
          "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]

PLANETAS_ID = ["Sol", "Lua", "Mercúrio", "Vênus", "Marte",
               "Júpiter", "Saturno", "Urano", "Netuno", "Plutão"]

LOCALIDADES = {
    "belo horizonte": (-19.9167, -43.9333),
    "bh": (-19.9167, -43.9333),
    "itapemirim": (-21.0083, -40.8470),
    "itaipava": (-20.9384, -40.8508),
    "piúma": (-20.8333, -40.7333),
    "vitória": (-20.3194, -40.3378),
    "vix": (-20.3194, -40.3378),
    "rio de janeiro": (-22.9068, -43.1729),
    "rj": (-22.9068, -43.1729),
    "são paulo": (-23.5505, -46.6333),
    "sp": (-23.5505, -46.6333),
}

if TEM_LB:
    _lb_nome = {_lb.sem_acentos(k): k for k in LOCALIDADES}
    for _ch, _m in _lb.MUNICIPIOS.items():
        LOCALIDADES[_ch] = (_m["lat"], _m["lon"])
        # aliases de nome único (sem UF) só quando não conflitam
        _n = _m["nome"]
        _nb = _lb.sem_acentos(_n).lower()
        if _nb not in _lb_nome:
            LOCALIDADES[_nb] = (_m["lat"], _m["lon"])
            _lb_nome[_nb] = _ch
    del _lb_nome


def tz_do_local(chave):
    """Desvio UTC (+?) para um local: usa o estado (lei atual), senão -3."""
    if TEM_LB:
        t = _lb.coords_e_fuso(chave) if chave else None
        if t:
            return t[2]
    return -3


def lon2signo(lon):
    lon = lon % 360
    z = int(lon // 30)
    d = lon - z * 30
    g = int(d)
    m = int((d - g) * 60)
    s = int(round(((d - g) * 60 - m) * 60))
    if s == 60:
        s = 0; m += 1
    if m == 60:
        m = 0; g += 1
    return SIGNOS[z], g, m, s


def _casa_do_lon(lon, cusps):
    """Casa (1–12) de uma longitude eclíptica, dadas as 12 cúspides.

    A casa i vai da cúspide i até a cúspide i+1 (circular: a casa 12
    atravessa o 0°). Usada para anotar cada planeta com a casa onde está
    (terreno pronto para correspondências 'planeta no signo na casa')."""
    lon = lon % 360
    for i in range(12):
        a = cusps[i] % 360
        b = cusps[(i + 1) % 12] % 360
        if a <= b:
            if a <= lon < b:
                return i + 1
        else:  # cúspide atravessa o 0° (casa 12)
            if lon >= a or lon < b:
                return i + 1
    return 1


def calc(data, hora, lat, lon, tz_horas=-3, sistema=b"P"):
    """data 'YYYY-MM-DD', hora 'HH:MM', lat/lon em graus decimais."""
    if not TEM_SWE:
        raise RuntimeError("py swisseph não disponível no venv")
    ano, mes, dia = map(int, data.split("-"))
    hh, mm = map(int, hora.split(":"))
    ut = hh + mm / 60.0 - tz_horas
    jdut = swe.julday(ano, mes, dia, ut, swe.GREG_CAL)

    # cúspides primeiro: cada planeta recebe a casa onde está
    cusps, ascmc = swe.houses_ex(jdut, lat, lon, sistema)

    planetas = {}
    for i, nome in enumerate(PLANETAS_ID):
        p = swe.calc_ut(jdut, i, swe.FLG_SWIEPH | swe.FLG_SPEED)
        plon = p[0][0]
        signo, g, m, s = lon2signo(plon)
        planetas[nome] = {
            "lon": round(plon % 360, 4),
            "signo": signo,
            "graus": g, "min": m, "seg": s,
            "retrogrado": p[0][3] < 0,
            "vel": round(p[0][3], 4),
            "casa": _casa_do_lon(plon, cusps),
        }

    # ── asteróides arquetípicos ────────────────────────────────────────────
    # (cada um segue a mandala zodiacal: tem signo, grau, retrogradação)
    # índices do pyswisseph instalado: 12=apogeu médio da Lua (Lua Negra/
    # Lilith), 15=Quíron, 17=Ceres, 18=Pallas, 19=Juno, 20=Vesta.
    # FLG_MOSEPH calcula todos sem depender de arquivos de efeméride.
    for _nome, _idx in (("Lilith", 12), ("Quíron", 15),
                        ("Ceres", 17), ("Pallas", 18),
                        ("Juno", 19), ("Vesta", 20)):
        try:
            q = swe.calc_ut(jdut, _idx, swe.FLG_MOSEPH | swe.FLG_SPEED)
            qlon = q[0][0]
            sq, gq, mq, sesseg = lon2signo(qlon)
            planetas[_nome] = {
                "lon": round(qlon % 360, 4),
                "signo": sq, "graus": gq, "min": mq, "seg": sesseg,
                "retrogrado": q[0][3] < 0,
                "vel": round(q[0][3], 4),
                "casa": _casa_do_lon(qlon, cusps),
            }
        except Exception:
            pass

    casas = []
    for i, c in enumerate(cusps):
        signo, g, m, s = lon2signo(c)
        casas.append({"casa": i + 1, "lon": round(c, 4), "signo": signo,
                      "graus": g, "min": m, "seg": s})
    asc_ss, asc_g, asc_m, asc_seg = lon2signo(ascmc[0])
    mc_ss, mc_g, mc_m, mc_seg = lon2signo(ascmc[1])

    return {
        "data_local": data, "hora_local": hora,
        "fuso_utc": tz_horas, "ut": f"{int(ut)}h{int((ut % 1) * 60)}m",
        "local": {"lat": lat, "lon": lon},
        "asc": f"{asc_ss} {asc_g}°{asc_m:02d}'{asc_seg:02d}\"",
        "mc": f"{mc_ss} {mc_g}°{mc_m:02d}'{mc_seg:02d}\"",
        "planetas": planetas,
        "casas": casas,
    }


def fmt_texto(m):  # compreensível para o agente/usuário
    linhas = [f"Mapa Astral — {m['data_local']} às {m['hora_local']} (local), "
              f"fuso UTC{m['fuso_utc']:+d} ({m['ut']} UT)",
              f"  Ascendente: {m['asc']}   Meio do Céu: {m['mc']}",
              "  Planetas:"]
    for nome, pl in m["planetas"].items():
        retro = "  (retrógrado)" if pl["retrogrado"] else ""
        linhas.append(f"    {nome}: {pl['signo']} {pl['graus']}°{pl['min']:02d}'{pl['seg']:02d}\""
                      f"  casa {pl.get('casa', '?')}{retro}")
    linhas.append("  Casas (cúspides, Placidus):")
    for c in m["casas"]:
        linhas.append(f"    Casa {c['casa']:2d}: {c['signo']} {c['graus']}°{c['min']:02d}'{c['seg']:02d}\"")
    return "\n".join(linhas)


if __name__ == "__main__":
    args = sys.argv[1:]

    lat = lon = None
    tz = -3
    json_out = False
    args_rest = []
    i = 0
    while i < len(args):
        if args[i] == "--lat":
            lat = float(args[i + 1]); i += 2; continue
        if args[i] == "--lon":
            lon = float(args[i + 1]); i += 2; continue
        if args[i] == "--tz":
            tz = int(args[i + 1]); i += 2; continue
        if args[i] == "--json":
            json_out = True; i += 1; continue
        args_rest.append(args[i]); i += 1

    data = args_rest[0] if args_rest else None
    hora = args_rest[1] if len(args_rest) > 1 else "12:00"
    local = " ".join(args_rest[2:]) if len(args_rest) > 2 else None

    if data is None:
        print(__doc__); sys.exit(1)

    if lat is None and local and local.lower() in LOCALIDADES:
        lat, lon = LOCALIDADES[local.lower()]

    if lat is None or lon is None:
        print("Coord. não encontradas — passe --lat X --lon Y ou localidade conhecida.")
        sys.exit(1)

    mapa = calc(data, hora, lat, lon, tz)
    if json_out:
        print(json.dumps(mapa, ensure_ascii=False, indent=2))
    else:
        print(fmt_texto(mapa))