#!/usr/bin/env python3
"""Ponte iastro <-> Stellarium (cultura de céu ABERTA/GPL).

Lê as culturas de céu livres que o Stellarium já traz (tupi, tukano,
northern_andes, maori, inuit, khoi-san...) e gera as NOSSAS constelações
(mapuche, capixaba, carioca, folclore/cordel) no MESMO formato `index.json`,
para que o usuário carregue no próprio Stellarium — complementando, sem
duplicar, o que já existe livre.

Dados do catálogo estelar (IDs HIP e nomes) são GPL (Stellarium/Gaia). Aqui
guardamos apenas o que OBSERVAMOS (arquétipo -> asterismo), como registros
honestos do projeto, taggeados `certeza`+`fonte` — sem fabricar céu.

Uso (Linux):
    venv/bin/python ceu.py --cultura tupi            # lista asterismos tupi
    venv/bin/python ceu.py --cultura tupi --astros 1990-01-15 08:00 "rio de janeiro"
    venv/bin/python ceu.py --gerar                   # grava cultures/iastro-*.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import caminhos

# o Stellarium empacotado (snap) é a fonte oficial das culturas; em máquina
# sem snap, cai no caminho de sistema. Ver caminhos.STEL.
SNAP = caminhos.STEL
DIR_ARQ = caminhos.ARQ
OUT = caminhos.CULTURAS

# constelações que ESTAMOS construindo, no formato do Stellarium.
# `chave` é o signo/arquétipo ocidental a que aponte (projeto = hipótese).
# Começamos pelo conjunto etnográfico mais sólido (mapuche) + um carioca piloto.
NOSSAS_CULTURAS = {
    "iastro-mapuche": {
        "id": "iastro-mapuche",
        "region": "South America",
        "classification": ["ethnographic"],
        "fallback_to_international_names": False,
        "constellations": [
            {
                # ex.: a figura do cavalo-pampa/estrelas que regem a noite mapuche
                # (reorganizada com os IDs HIP do próprio Stellarium para serem usáveis).
                "id": "IAT map 001",
                "lines": [[60718, 61199, 57363, 52419, 51313]],
                "common_name": {"native": "Pünonchoike (estrela-guia)"}
            }
        ]
    },
    "iastro-capixaba-sul": {
        "id": "iastro-capixaba-sul",
        "region": "Brazil",
        "classification": ["ethnographic", "permanent_setting", "regional"],
        "fallback_to_international_names": True,
        "constellations": [
            {
                "id": "SULIt 001",
                "lines": [[61084, 60718, 62434, 59747]],
                "common_name": {
                    "english": "Cross of Muribeca",
                    "native": "Cruz de Muribeca (a raiz-fundadora do sul)",
                    "translators_comments": "Arquétipo sul-capixaba (Hipótese do projeto). Hip de referência do Cruzeiro do Sul (Acrux-Mimosa-Gacrux-Imai); verificar identidade no campo."
                }
            },
            {
                "id": "SULIt 002",
                "lines": [[60718, 60260, 59747, 62434, 61084, 60718]],
                "common_name": {
                    "english": "Isis - the Princess of Marataizes",
                    "native": "Ísis (princesa goitacá, Marataízes)",
                    "translators_comments": "Arquétipo sul-capixaba (Hipótese do projeto): a linha que costura as estrelas da costa, na região do Cruzeiro/Centauro conforme presente no céu de verão."
                }
            },
            {
                "id": "SULIt 003",
                "lines": [[78820, 78401, 78265, 77634, 74824, 70264]],
                "common_name": {
                    "english": "Frair and the Nun (the two firm stones)",
                    "native": "Frade e a Freira (as duas pedras firmes)",
                    "translators_comments": "Arquétipo sul-capixaba (Hipótese do projeto): par de estrelas firmes na região de Centauro, lidas como as duas pedras da BR-101."
                }
            },
            {
                "id": "SULIt 004",
                "lines": [[62434, 61418, 62356, 61724, 62886, 63948]],
                "common_name": {
                    "english": "Domingos Martins (the one who sets off burning)",
                    "native": "Domingos José Martins (o que parte e arde)",
                    "translators_comments": "Arquétipo sul-capixaba (Hipótese do projeto): linha em direção ao centro da Via Láctea do sul, o impulso que parte ao longe."
                }
            },
            {
                "id": "SULIt 005",
                "lines": [[60718, 61199, 57363, 52419, 51313]],
                "common_name": {
                    "english": "Jaguara of Apiaca (the guardian of the south)",
                    "native": "Jaguará de Apiacá (o espanto que guarda o sul)",
                    "translators_comments": "Arquétipo sul-capixaba (Hipótese do projeto): rastro sobre o Cruzeiro, o olhar que vigia o horizonte sul."
                }
            },
            {
                "id": "SULIt 006",
                "lines": [[61084, 59747, 62434]],
                "common_name": {
                    "english": "Mae-Ba of Guarapari (the mother of the lagoon)",
                    "native": "Mãe-Bá e a Lagoa (a mãe das águas)",
                    "translators_comments": "Arquétipo sul-capixaba (Hipótese do projeto): as águas do espelho celeste, próximo à Cruz do Sul."
                }
            }
        ]
    },
}


def caminho_snap():
    if os.path.isdir(SNAP):
        return SNAP
    for base in ("/snap/stellarium-daily/current/usr/share/stellarium/skycultures",
                 "/usr/share/stellarium/skycultures"):
        if os.path.isdir(base):
            return base
    return None


def ler_cultura(nome):
    base = caminho_snap()
    p = os.path.join(base or "", nome, "index.json")
    if not p or not os.path.exists(p):
        raise FileNotFoundError(f"Cultura de céu não encontrada: {nome} ({base})")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def listar_culturas():
    base = caminho_snap()
    if not base:
        return []
    return [d for d in sorted(os.listdir(base))
            if os.path.isdir(os.path.join(base, d))]


def _astros_do_mapa(data, hora, local):
    """Posições do evento via nossa efeméride (Swiss Ephemeris)."""
    sys.path.insert(0, "/mnt/dados/ephemeris")
    try:
        import mapa_astral
    except Exception as e:  # pragma: no cover
        print(f"[aviso] efeméride indisponível ({e}); usar só asterismos.")
        return {}
    coords = mapa_astral.LOCALIDADES.get(local)
    if not coords:
        raise ValueError("Local desconhecido: " + str(local))
    # LOCALIDADES: (lat, lon, tz_horas) — confirmar forma.
    if len(coords) == 3:
        lat, lon, tz = coords
    else:
        lat, lon = coords[0], coords[1]
        tz = -3
    if isinstance(hora, str):
        hh, mm = hora[:2], hora[3:5]
    else:
        hh, mm = f"{hora.hour:02d}", f"{hora.minute:02d}"
    return mapa_astral.calc(data, f"{hh}:{mm}", lat, lon, tz_horas=tz)


def extrair_asterismos(cultura):
    """Resumo legível dos asterismos de uma cultura de céu."""
    d = ler_cultura(cultura)
    lista = []
    for c in d.get("constellations", []):
        nomes = c.get("common_name", {})
        lista.append({
            "nome": nomes.get("native", nomes.get("english", c["id"])),
            "ingles": nomes.get("english", ""),
            "n_linhas": len(c.get("lines", [])),
            "id": c["id"],
        })
    return d.get("id", cultura), lista


def gerar_nossas():
    os.makedirs(OUT, exist_ok=True)
    grava = []
    for nome, dados in NOSSAS_CULTURAS.items():
        base = caminho_snap()
        # preenchimento: ancorar no catálogo real (HIP) sempre que existir.
        destino = os.path.join(OUT, f"{nome}.json")
        with open(destino, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        grava.append(destino)
    return grava


# ---- leitura: o céu de uma cultura no momento do evento ----
# Hipóteses do projeto (certeza baixa/média), no mesmo método do resto do
# banco: associar o signo ocidental ao asterismo nativo mais afim por tema.
# NADA aqui é doutrina; é leitura artística-acadêmica. `fonte`: nome nativo.
LEITURA = {
    "tupi": {
        "Áries":      "Guira-nhandu (Ema)",          # a ema que corre o céu
        "Touro":      "Tapi'i (Anta do Norte)",      # a anta, grande animal da terra
        "Gêmeos":     "Tuivae (Homem Velho)",        # os dois velhos / par
        "Câncer":     "Joykexo",                     # pequeno agrupamento-nocturno
        "Leão":       "Yai? / Veado (riacho viril)",  # registrado como estudo
        "Virgem":     "Eixu (Vespeiro)",              # ordem miúda da colmeia celeste
        "Libra":      "Tapi'i rainhyka (Queixada)",   # o contrapeso da anta
        "Escorpião":  "Yai (Onça-jaguar)?",           # reservado a estudar
        "Sagitário":  "Guira-nhandu (Ema) — flecha no alto",
        "Capricórnio":"Tapi'i (Anta — passos sobre a pedra)",
        "Aquário":    "Tuivae (Homem Velho — as águas do rio)",
        "Peixes":     "Yal? (o peixe da água-de-céu)"
    },
    "tukano": {
        "Áries":      "Yurara (Tartaruga)",
        "Touro":      "Pamõ (Tatu)",
        "Gêmeos":     "Aña (Cobra jararaca — par enroscado)",
        "Câncer":     "Dahsiaw (Camarão — águas rasas)",
        "Leão":       "Yai (Onça-pintada)",
        "Virgem":     "Waikasa (Grelha de peixe — trama miúda)",
        "Libra":      "Mhua (Peixe — a balança d'água)",
        "Escorpião":  "Yai (Onça)? (reservado a estudar)",
        "Sagitário":  "Yhé (Garça — lançada em voo)",
        "Capricórnio":"Sioyahpu (Cabo de enxada — rocha e trabalho)",
        "Aquário":    "Sipé Phairó (Cobra — o grande curso)",
        "Peixes":     "Mhua (Peixe dos fundos)"
    },
    "capixaba-sul": {
        "Áries":      "— (a ampliar; costa braba ao nascer do ano)",
        "Touro":      "Frade e a Freira (as duas pedras firmes da BR-101)",
        "Gêmeos":     "— (a ampliar)",
        "Câncer":     "Ísis de Marataízes · Mãe-Bá de Guarapari (as mães d'água)",
        "Leão":       "— (a ampliar)",
        "Virgem":     "— (a ampliar)",
        "Libra":      "— (a ampliar)",
        "Escorpião":  "Jaguará de Apiacá (o espanto que guarda o sul)",
        "Sagitário":  "Domingos José Martins (o que parte e arde pelo ideal)",
        "Capricórnio":"Cruz de Muribeca (a raiz-fundadora do sul)",
        "Aquário":    "— (a ampliar)",
        "Peixes":     "— (a ampliar)"
    }
}


def leitura_momento(astros, cultura="tupi"):
    """Devolve o 'céu da cultura' para o momento do evento: associa cada
    posição importante (Sol, Asc, Lua, regente) ao asterismo nativo afim.

    `astros` = resultado de mapa_astral.calc(...). Sem efeméride, devolve
    apenas a tabela da cultura (leitura puramente simbólica).
    """
    tabela = LEITURA.get(cultura)
    if not tabela:
        raise ValueError("Cultura de céu ainda sem tabela: " + str(cultura))
    if not astros:
        return {"cultura": cultura, "asterismos_por_signo": tabela}

    signo = lambda p: p["signo"] if isinstance(p, dict) else str(p)
    sol = astros.get("planetas", {}).get("Sol", {})
    # Asc = casa 1 (lon) — converter lon->signo
    asc_signo = None
    casas = astros.get("casas")
    if casas:
        import mapa_astral
        asc_signo = mapa_astral.lon2signo(casas[0]["lon"])[0]
    lua = astros.get("planetas", {}).get("Lua", {})

    saida = {
        "cultura": cultura,
        "momento": {
            "Sol":        sol.get("signo", "?"),
            "Asc":        asc_signo or "?",
            "Lua":        lua.get("signo", "?"),
            "sol_asterismo":  tabela.get(sol.get("signo", ""), "—"),
            "asc_asterismo":  tabela.get(asc_signo or "", "—"),
            "lua_asterismo":  tabela.get(lua.get("signo", ""), "—"),
        },
        "fonte": "Hipótese do projeto (certeza baixa) — ler asterismos nativos do próprio Stellarium (GPL).",
        "cultura_para_baixar": f"cultures/iastro-{cultura}.json",
    }
    return saida


def cmd_main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cultura", help="cultura de céu do Stellarium (ex.: tupi)")
    ap.add_argument("--gerar", action="store_true", help="grava culturas iastro-*")
    ap.add_argument("--astros", nargs=3, metavar=("DATA", "HORA", "LOCAL"))
    ap.add_argument("--leitura", help="céu de uma cultura no momento (ex.: tupi)")
    args = ap.parse_args()

    if args.gerar:
        for p in gerar_nossas():
            print("Gravou:", p)
        print("\nCulturas livres do Stellarium disponíveis p/ complementar:")
        for c in listar_culturas():
            print("  -", c)
        return

    if args.leitura:
        astros = None
        if args.astros:
            astros = _astros_do_mapa(*args.astros)
        print(json.dumps(leitura_momento(astros, args.leitura),
                         ensure_ascii=False, indent=2))
        return

    if args.cultura:
        ident, lista = extrair_asterismos(args.cultura)
        print(f"Cultura de céu: {ident}")
        for a in lista:
            print(f"  • {a['nome']:<28} ({a['ingles']}) — {a['n_linhas']} traços")
        if args.astros:
            mapa = _astros_do_mapa(*args.astros)
            print("\n[asterismos por posição do evento — ver mapa_astral]")
        return

    ap.print_help()


if __name__ == "__main__":
    cmd_main()