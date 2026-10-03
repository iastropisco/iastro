# -*- coding: utf-8 -*-
"""Gera um PROMPT de imagem artística a partir dos DADOS REAIS do mapa.

Ideia: em vez de deixar uma IA de imagem "inventar" um mapa (elas erram
posições), nós extraímos os FATOS astronômicos corretos (planeta → signo →
grau, ascendente, meio do céu, arquétipos, tema, cultura) e os escrevemos
num prompt bem estruturado. A imagem gerada é um quadro artístico cuja
estrutura (mandala correta) pode ser conferida contra a obra PNG real.

Domínio público / software livre: o texto gerado aqui pode ser usado livre-
mente (CC0); recomenda-se modelos abertos (FLUX.1-schnell / SDXL).
"""

from __future__ import annotations

GRAU_SIGNO = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem",
              "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário",
              "Peixes"]
COR = {"Áries": "vermelho-fogo", "Touro": "verde-terra",
       "Gêmeos": "amarelo-vento", "Câncer": "prata-lua",
       "Leão": "dourado-sol", "Virgem": "castanho-campo",
       "Libra": "rosa-suave", "Escorpião": "vermelho-sangue",
       "Sagitário": "azul-índigo", "Capricórnio": "terno-terra",
       "Aquário": "ciano-relâmpago", "Peixes": "azul-mar profundo"}


def _nome_arq(a):
    """Aceita tupla (nome, fonte, signo) ou string simples."""
    if isinstance(a, (tuple, list)):
        return a[0].split(" (")[0]
    return str(a).split(" (")[0]


def _grau_texto(lon):
    lon = round(float(lon) % 360, 1)
    sg = int(lon // 30)
    g = int(lon % 30)
    m = int(round((lon % 1) * 60))
    return f"{g}º{m:02d}' de {GRAU_SIGNO[sg]}"


def _linha_planeta(dados, nome):
    pl = dados["planetas"].get(nome)
    if not pl:
        return None
    return f"- {nome}: {_grau_texto(pl['lon'])}"


def gerar_prompt(m, asc_signo, sol_signo, arq_asc, arq_sol, verso,
                 cultura=None, tema=None, feeling=None, nome="") -> str:
    """Mapeia o mapa real para um prompt artístico coerente (PT-BR)."""
    sol = m["planetas"]["Sol"]
    lua = m["planetas"].get("Lua", {})
    linhas_planetas = [_linha_planeta(m, n) for n in
                       ("Sol", "Lua", "Mercúrio", "Vênus", "Marte",
                        "Júpiter", "Saturno", "Urano", "Netuno", "Plutão")]
    linhas_planetas = [l for l in linhas_planetas if l]
    asc_xt = _grau_texto(m["casas"][0]["lon"])
    mc = _grau_texto((m["casas"][0]["lon"] + 270) % 360)

    arquetipos = []
    if arq_asc:
        arquetipos.append("Ascendente em " + asc_signo + ": " +
                          ", ".join(_nome_arq(a) for a in arq_asc))
    if arq_sol:
        arquetipos.append("Sol em " + sol_signo + ": " +
                          ", ".join(_nome_arq(a) for a in arq_sol))

    cultura_txt = cultura or ""
    tema_txt = tema or "o teu nome"
    feeling_txt = feeling or "encantamento"

    prompt = f"""Ilustração artística de um MAPA ASTRAL brasileiro, estilo
pintura aquarela + tinta nanquim tipo caligrafia popular (letreiro de
mercado, cartaz de cordel). Momento: quadro emocionante, '{feeling_txt}'.

ESTRUTURA EXATA (não invente posições, obedeça a lista):
- Mandala circular central com os 12 signos do zodíaco em seus setores
  reais, cada signo pintado em sua cor característica (ex.: {COR.get(sol_signo, 'dourado')}).
- Ao redor da mandala, em formato de vitral/gravura, os 10 planetas nas
  POSIÇÕES CORRETAS do mapa:
{chr(10).join(linhas_planetas)}

- Ascendente: {asc_xt} ({asc_signo}).
- Meio do Céu: aproximadamente {mc}.
- Arquétipos para ilustrar junto (personagens/animais):
{chr(10).join('- ' + a for a in arquetipos)}

DECORAÇÃO E CABEÇALHO:
- {{{cultura_txt}}}
- Verso inspirador na base, em letra de pincel: "{verso[0] if verso else tema_txt}"
- Cores {COR.get(sol_signo.lower().capitalize(), 'solares')} {COR.get(asc_signo, 'quentes')}
  com lampos do tema '{tema_txt}'.

TÉCNICA:
- Aquarela com granulação de papel artesanal, respingos de tinta e bordas
  molhadas; nada de bordas quadradas ou retângulos mecânicos.
- Texto em português legível apenas no caso da estética pedir (letreiro
  popular); o resto é imagem.
- Publicação artística vertical (retrato), composição cheia e orgânica.

NOTA DE USO: imagem gerada livremente para fins não comerciais/CC, sempre
conferida contra o mapa real em obra-YY-MM-DD.png.
"""
    return prompt.strip()


def gerar_prompt_curto(m, asc_signo, sol_signo, arq_asc, arq_sol,
                       cultura=None, tema=None, feeling=None,
                       estilo=None) -> str:
    """Prompt CONDENSADO (< 77 tokens, limite do CLIP do Stable Diffusion).

    SD1.5 trunca depois de 77 tokens — aqui só o estilo + os fatos-chave
    (planeta→signo→grau, Asc, tema), sem descrições longas de arquétipos."""
    sol = m["planetas"]["Sol"]
    lua = m["planetas"].get("Lua", {})
    sol_xt = f"Sol {sol['signo']} {sol['graus']}"
    lua_xt = f"Lua {lua.get('signo','?')} {lua.get('graus',0)}" if lua else ""
    tema_x = (tema or "o teu nome").strip()
    if estilo:
        partes = [
            estilo,
            "mandala astral",
            f"{sol_xt}, {lua_xt}, Ascendente {asc_signo}",
            f"tema: {tema_x}" + (f", feeling {feeling}" if feeling else ""),
        ]
    else:
        partes = [
            "aquarela, nanquim e xilogravura de cordel",
            "mandala astral, letreiro de mercado",
            f"{sol_xt}, {lua_xt}, Ascendente {asc_signo}",
            f"tema: {tema_x}" + (f", feeling {feeling}" if feeling else ""),
            "respingos de tinta, ocre e vermelho-terra",
        ]
    return ", ".join(partes).strip()


def gerar_prompt_resource(res, cultura=None, tema=None, feeling=None,
                          nome="") -> str:
    """Façade para usar direto com o retorno de campanha.gerar_obra()."""
    m = res["dados"]
    return gerar_prompt(
        m,
        res.get("asc_signo", ""),
        res.get("sol_signo", ""),
        res.get("arquetipos_asc", []),
        res.get("arquetipos_sol", []),
        res.get("verso", []),
        cultura=cultura,
        tema=tema,
        feeling=feeling,
        nome=nome,
    )