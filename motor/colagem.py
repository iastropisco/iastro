#!/usr/bin/env python3
"""PLANETÁRIO ASTROLÓGICO RECICLE — v4

Mosaico artístico em estética de "reciclagem": papel kraft de fundo, molduras
e texturas de materiais recicláveis (papelão, jornal, latas, vidro, plástico),
arquétipos desenhados proceduralmente OU a partir de imagens de domínio
público (Wikimedia Commons), e MESMO layout dinâmico — cada seção ocupa uma
zona própria, calculada de ponta a ponta, sem sobreposição de imagens/texto.

Bancos de assets:
  • mapas/reciclaveis/           -> materiais recicláveis (gerar_reciclaveis.py)
  • mapas/images-livres/arquétipos/ -> imagens PD/CC por arquétipo

Uso CLI:
    venv/bin/python colagem.py --data 1982-11-20 --hora 01:30 \
        --local "belo horizonte" --nome "Cristiano"

Importável por app.py: gerar_obra(form, saida)
"""
import math
import os
import random
import re
import sqlite3
import sys
import unicodedata
import zlib
import colorsys

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

# scipy só entra para os filtros de morfologia (a erosão da "borda úmida" da
# aguada): o MinFilter do PIL é O(k²) por pixel e, na obra 2800×9400, custava
# ~3 s por chamada. O minimum_filter do scipy dá o mesmo resultado (mode
# 'nearest' reproduz o preenchimento de borda do PIL) em ~0,05 s.
try:
    from scipy.ndimage import minimum_filter as _minimum_filter
except Exception:                                    # pragma: no cover
    _minimum_filter = None

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mapa_astral

# famílias semânticas da poesia: tema → conceito → família de palavras
try:
    from poesia_conceitos import CONCEITOS as _CONCEITOS
except Exception:
    _CONCEITOS = {}

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mapa_astral
import caminhos

# caminhos relativos à raiz do projeto (ver caminhos.py): o motor roda em
# qualquer máquina sem editar caminho escrito à mão
DIR_ARQ = caminhos.ARQ
DIR_IMG = os.path.join(caminhos.MAPAS, "imagens")
DIR_REC = caminhos.RECICLAVEIS
DIR_PD = os.path.join(caminhos.IMAGENS_LIVRES, "arquétipos")
DB = caminhos.DB

# ── identidade do planetário (logo + link p/ compartilhar/avaliar) ───────
NOME_PLANETARIO = "PLANETÁRIO ASTROLÓGICO RECICLE"
LOGO_PLANETARIO = "/home/italivre/Documentos/iastro/logoplanetario.webp"
LINK_PLANETARIO = ("https://sites.google.com/view/mapadaspancs/"
                   "planet%C3%A1rio-astrol%C3%B3gico")
LINK_LABEL = "Planetário Astrológico · Recicle"
LINK_MAPS = "https://share.google/v3vK81uuUedWZo5Sp"
LINK_MAPS_LABEL = "Ver a página do Planetário no Google Maps"

SIGNOS = ["Áries", "Touro", "Gêmeos", "Câncer", "Leão", "Virgem",
          "Libra", "Escorpião", "Sagitário", "Capricórnio", "Aquário", "Peixes"]
SIMB = {"Áries": "♈", "Touro": "♉", "Gêmeos": "♊", "Câncer": "♋",
        "Leão": "♌", "Virgem": "♍", "Libra": "♎", "Escorpião": "♏",
        "Sagitário": "♐", "Capricórnio": "♑", "Aquário": "♒", "Peixes": "♓"}
SIGNOS_ANG = {s: i * 30 for i, s in enumerate(SIGNOS)}

COR = {
    "Áries": (196, 72, 51), "Touro": (86, 142, 86), "Gêmeos": (192, 167, 51),
    "Câncer": (146, 172, 196), "Leão": (196, 137, 52), "Virgem": (131, 162, 106),
    "Libra": (182, 117, 142), "Escorpião": (137, 42, 72),
    "Sagitário": (102, 66, 146), "Capricórnio": (106, 77, 47),
    "Aquário": (62, 142, 172), "Peixes": (62, 106, 166),
}
COR_P = {"Sol": (255, 205, 82), "Lua": (198, 213, 232),
         "Mercúrio": (167, 207, 197), "Vênus": (226, 167, 188),
         "Marte": (212, 87, 78), "Júpiter": (207, 167, 108),
         "Saturno": (188, 172, 143), "Urano": (107, 207, 218),
         "Netuno": (107, 147, 212), "Plutão": (178, 128, 188),
         "Quíron": (150, 196, 178), "Lilith": (204, 152, 204),
         "Ceres": (186, 192, 118), "Pallas": (148, 184, 206),
         "Juno": (206, 162, 128), "Vesta": (172, 172, 214)}
COR_SIGNO = COR
COR_PLANETA = COR_P
# paleta de cores para o nome do consultante (varia de pessoa p/ pessoa)
COR_NOME = [(40, 96, 60), (146, 50, 38), (52, 72, 142), (108, 44, 120),
            (38, 118, 108), (150, 100, 32)]
# tons claros do nome p/ a placa escura do cabeçalho (leitura sobre o fundo)
COR_NOME_CLARO = [(118, 206, 142), (240, 120, 86), (148, 178, 246),
                  (222, 132, 238), (104, 216, 196), (250, 200, 110)]
GLIFO = {"Sol": "☉", "Lua": "☽", "Mercúrio": "☿", "Vênus": "♀",
         "Marte": "♂", "Júpiter": "♃", "Saturno": "♄",
         "Urano": "♅", "Netuno": "♆", "Plutão": "♇",
         "Quíron": "⚷", "Lilith": "⚸",
         "Ceres": "⚳", "Pallas": "⚴", "Juno": "⚵", "Vesta": "⚶"}

FONTS = "/usr/share/fonts/truetype/dejavu"
FONTS_PERG = caminhos.FONTS_PERG
LIBERTINE = "/usr/share/fonts/opentype/linux-libertine"
# 1 = tamanho original; >1 = tudo maior (tipografia mais legível no papel)
FONT_K = 1.40

ELEM = {"Áries": "fogo", "Leão": "fogo", "Sagitário": "fogo",
        "Touro": "terra", "Virgem": "terra", "Capricórnio": "terra",
        "Gêmeos": "ar", "Libra": "ar", "Aquário": "ar",
        "Câncer": "água", "Escorpião": "água", "Peixes": "água"}
ELEM_COR = {"fogo": (214, 92, 54), "terra": (118, 140, 74),
            "água": (66, 118, 178), "ar": (196, 172, 62)}
ELEM_SIMB = {"fogo": "△", "terra": "▽", "água": "▽", "ar": "△"}
PLANETAS_10 = ["Sol", "Lua", "Mercúrio", "Vênus", "Marte", "Júpiter",
               "Saturno", "Urano", "Netuno", "Plutão"]
# asteróides arquetípicos que PODEM ser marcados ao gerar o mapa (opção).
# o Quíron já vem sempre; estes entram quando "asteroides" = True.
ASTEROIDES_EXTRA = ["Lilith", "Ceres", "Pallas", "Juno", "Vesta"]
CORPOS_ASTEROIDES = {"Quíron", "Lilith", "Ceres", "Pallas", "Juno", "Vesta"}

# ── aspectos planetários (ângulo, nome, cor) ─────────────────────────────
ASPECTOS_DEF = [
    (0, "Conjunção", (210, 70, 70)),
    (60, "Sextil", (120, 170, 120)),
    (90, "Quadratura", (200, 60, 60)),
    (120, "Trígono", (70, 120, 205)),
    (180, "Oposição", (150, 90, 180)),
]
ORB = 7.0  # orbe padrão (graus) para os aspectos


def _angulo_entre(a, b):
    """Menor ângulo (0..180) entre duas longitudes eclípticas."""
    d = abs(a - b) % 360
    return min(d, 360 - d)


def _aspectos(m, orbe=ORB):
    """Lista de aspectos entre os planetas do mapa.

    Cada item: (nome_a, nome_b, tipo, cor, angulo, lon_a, lon_b)
    """
    pls = m["planetas"]
    nomes = [n for n in PLANETAS_10 if n in pls]
    out = []
    for i in range(len(nomes)):
        for j in range(i + 1, len(nomes)):
            a, b = nomes[i], nomes[j]
            lon_a, lon_b = pls[a]["lon"], pls[b]["lon"]
            ang = _angulo_entre(lon_a, lon_b)
            for alvo, tipo, cor in ASPECTOS_DEF:
                if abs(ang - alvo) <= orbe:
                    out.append((a, b, tipo, cor, ang, lon_a, lon_b))
                    break
    out.sort(key=lambda x: x[4])
    return out


def _computa_transitos(form, lat, lon, hoje=None):
    """Posições atuais (trânsitos) no local do nascimento.

    Retorna o mapa de hoje (mesma função Swiss Ephemeris) ou None.
    """
    try:
        import datetime
        h = hoje or datetime.date.today()
        agora = datetime.datetime.now()
        data = h.strftime("%Y-%m-%d")
        hora = f"{agora.hour:02d}:{agora.minute:02d}"
        return mapa_astral.calc(data, hora, lat, lon, tz_horas=-3)
    except Exception:
        return None


def _linha_mao(d, p0, p1, cor, lw, rng, jitter=1.6, passos=6):
    """Linha 'à mão': segmenta e ondula levemente os traços (menos chapado)."""
    x0, y0 = p0
    x1, y1 = p1
    pts = []
    for i in range(passos + 1):
        t = i / passos
        bx = x0 + (x1 - x0) * t
        by = y0 + (y1 - y0) * t
        if 0 < i < passos:
            bx += rng.uniform(-jitter, jitter)
            by += rng.uniform(-jitter, jitter)
        pts.append((bx, by))
    for i in range(1, len(pts)):
        d.line([pts[i - 1], pts[i]], fill=cor, width=lw)


PAPEL_KRAFT = (201, 181, 142)
PAPEL_KRAFT_ESC = (154, 134, 100)
PAPELAO = (168, 146, 106)
TINTA_FORTE = (34, 28, 18)
TINTA = (56, 47, 30)
VERMELHO = (196, 56, 40)
AZUL = (48, 74, 140)
# cor de base dos cartões (espelha a placa escura do cabeçalho/rodapé, para
# a letra clara destacar SEM brigar com a textura do papel)
CARD_ESC = (58, 46, 32)
# tinta escura p/ desenhar POR CIMA dos painéis claros (discos e gravuras)
TINTA_ESC = (36, 28, 18)
# dourado claro usado na placa (letras e filetes)
DOURADO = (216, 186, 108)
# tinta CLARA p/ texto sobre os cartões escuros (placa do cabeçalho/rodapé)
TINTA_CARD = (250, 246, 232)
LINHA_CARD = (214, 192, 148)

# arquétipo -> imagem PD (sem extensão)
ARQ_IMAGEM = {
    "boitata": "boitata", "boitatá": "boitata",
    "curupira": "curupira", "omolu": "omolu", "obaluaiê": "omolu",
    "iemanja": "iemanja", "iemanjá": "iemanja", "yemanjá": "iemanja",
    "exu": "exu", "osanyin": "osanyin", "ossanha": "osanyin", "osanyn": "osanyin",
    "oxalá": "oxala", "oxala": "oxala", "obatalá": "oxala",
    "oxum": "oxum", "oxumare": "oxumare", "oxumarê": "oxumare",
    "oxóssi": "oxossi", "oxossi": "oxossi", "oxosi": "oxossi",
    "iansã": "iansa", "iansa": "iansa", "oya": "iansa", "oyá": "iansa",
    "nanã": "nana", "nana": "nana", "nană": "nana",
    "saci": "saci", "saci-perere": "saci",
    "iara": "iara", "cuca": "cuca",
    "boto": "boto", "boto-cor-de-rosa": "boto",
    "caipora": "caipora",
    "mula sem cabeça": "mula_sem_cabeca",
    "lobisomem": "lobisomem", "mapinguari": "mapinguari",
    "xangô": "xango", "xango": "xango", "xango (orixa)": "xango",
    "ogum": "ogum",
    "anta": "anta", "ema": "ema", "ema ": "ema",
    "onça": "onca", "onca": "onca", "onça-rei": "onca",
    "cobra": "cobra_grande", "cobra grande": "cobra_grande",
    "jaguar": "onca", "jaguará": "onca",
    # ── lote novo (busca na Wikimedia Commons, 2026) ───────────────────────
    "matinta pereira": "matinta-pereira", "matinta": "matinta-pereira",
    "cabeça de cuia": "cabeca-de-cuia", "cabeça-de-cuia": "cabeca-de-cuia",
    "negrinho do pastoreio": "negrinho-do-pastoreio",
    "o jangadeiro": "jangadeiro", "jangadeiro": "jangadeiro",
    "tutu marambá": "tutu-maramba", "tutu maramba": "tutu-maramba",
    "comadre fulozinha": "comadre-fulozinha",
    "frade e a freira": "frade-e-a-freira",
    "domingos josé martins": "domingos-jose-martins",
    "domingos jose martins": "domingos-jose-martins",
    "mãe-bá e a lagoa": "mae-ba-lagoa", "mae-ba e a lagoa": "mae-ba-lagoa",
    "índia ísis e o nome marataízes": "india-isis-marataizes",
    "india isis e o nome marataizes": "india-isis-marataizes",
    "marataízes": "india-isis-marataizes",
    "rio itapemirim": "rio-itapemirim",
    "gavião / ave de rapina": "gaviao", "gaviao / ave de rapina": "gaviao",
    "gavião": "gaviao", "gaviao": "gaviao",
    "grande baleia": "grande-baleia",
    "iandutí": "ianduti-teia", "ianduti": "ianduti-teia",
    "jaó / inambu": "jao-inambu", "jao / inambu": "jao-inambu",
    "inambu": "jao-inambu",
    "o caçador que mira as plêiades": "cacador-plesiades",
    "cacador que mira as pleiades": "cacador-plesiades",
    "o caçador": "cacador-plesiades",
    "os dois carregadores do céu": "dois-carregadores",
    "dois carregadores do ceu": "dois-carregadores",
    "rio-do-céu e a piracema das estrelas": "rio-do-ceu-via-lactea",
    "rio do céu": "rio-do-ceu-via-lactea", "via láctea": "rio-do-ceu-via-lactea",
    "tatu": "tatu", "veado": "veado",
    "a flecha que guarda a região do escorpião": "flecha-escorpiao",
    "flecha que guarda a regiao do escorpiao": "flecha-escorpiao",
    "memória puris e goytacá": "memoria-puris-goytaca",
    "memoria puris e goytaca": "memoria-puris-goytaca",
    "criatura do rio itapemirim": "criatura-rio-itapemirim",
    "minotauro de itapemirim": "minotauro-itapemirim",
    # ── lote 2026-09: figuras PD (Wikimedia Commons) p/ medalhões sem imagem ──
    "homem velho": "homem-velho", "velho": "homem-velho",
    "wetripantu": "wetripantu", "ano novo mapuche": "wetripantu",
    "melipal": "melipal", "quatro azadões": "melipal", "quatro azadoes": "melipal",
    "wüñellfe": "wunellfe", "wunellfe": "wunellfe", "wünelfe": "wunellfe",
    "lucero do amanhecer": "wunellfe", "lucero": "wunellfe",
    "antü": "antu", "antu": "antu",
    "küyen": "kuyen", "kuyen": "kuyen",
    "pünonchoike": "punonchoike", "punonchoike": "punonchoike",
    "rastro do avestruz": "punonchoike",
    "wenu leufü": "wenu-leufu", "wenu leufu": "wenu-leufu",
    "trarinmansun": "trarinmansun", "bois enjogados": "trarinmansun",
    "witran": "witran", "weluwitraw": "witran",
    "capeta da garrafa": "capeta-garrafa",
    "mão pelada": "mao-pelada", "mao pelada": "mao-pelada",
    "boi de reis": "boi-de-reis", "folia de reis": "boi-de-reis",
    "gigante adormecido": "gigante-adormecido",
    "gigante adormecido da guanabara": "gigante-adormecido",
    "tamoios": "tamoios", "tamoios e a memoria da guanabara": "tamoios",
    # ── horóscopo nordestino (2026-09, ensinado pelo usuário) ───────────────
    "calango": "calango",
    "asa branca": "asa-branca",
    "rasga-mortalha": "rasga-mortalha",
    "soim": "soim", "sagui": "soim",
    "cágado": "cagado", "cagado": "cagado",
    "carcará": "carcara", "carcara": "carcara",
    "maribondo": "maribondo",
    "cururu": "cururu",
    "bode": "bode",
    "jumento": "jumento",
    "siri": "siri",
    "teju": "teju",
    "raposa": "raposa",
    "preá": "prea", "prea": "prea",
}


def _font(sz, bold=True):
    p = (f"{LIBERTINE}/LinLibertine_RB.otf" if bold
         else f"{LIBERTINE}/LinLibertine_R.otf")
    if os.path.exists(p):
        return ImageFont.truetype(p, int(sz * FONT_K))
    p = f"{FONTS}/DejaVuSerif-"
    return ImageFont.truetype(f"{p}Bold.ttf" if bold else f"{p}.ttf",
                              int(sz * FONT_K))


def _font_it(sz):
    # LinLibertine_I.otf está corrompida (renderiza ilegível no PIL);
    # usamos a Roman Italic (RI), que tem os mesmos glifos e funciona.
    p = f"{LIBERTINE}/LinLibertine_RI.otf"
    if os.path.exists(p):
        return ImageFont.truetype(p, int(sz * FONT_K))
    return ImageFont.truetype(f"{FONTS}/DejaVuSerif-Italic.ttf",
                              int(sz * FONT_K))


def _sans(sz):
    return ImageFont.truetype(f"{FONTS}/DejaVuSans-Bold.ttf", int(sz * FONT_K))


def _sans_reg(sz):
    """DejaVu Sans regular — tem TODOS os glifos astronômicos (☉☽☿⚷♈…)
    que a LinLibertine (o _font) não tem; evita os 'quadradinhos'."""
    return ImageFont.truetype(f"{FONTS}/DejaVuSans.ttf", int(sz * FONT_K))


_MEDALHOES = os.path.join(DIR_ARQ, "medalhoes")
_MED_CACHE = {}
# arquivos baixados do Wikimedia Commons (série CC0 de Filippos Fragkogiannis)
# Largura por signo, normalizada pela ÁREA DE TINTA e não pela largura.
# Antes todos recebiam 96px de largura, e como cada desenho tem proporção
# diferente, a altura saía de 62px (Virgem) a 121px (Touro): o Touro quase
# dobrava de tamanho e o peso óptico dos 12 ficava todo desigual.
# Medindo a cobertura real de cada SVG e dividindo por ela, os 12 passam a
# ter a mesma massa de tinta na roda. A média geométrica das larguras foi
# re-normalizada para 96px, preservando a pegada que o anel já usava.
MEDALHAO_W = {
    "Áries": 108, "Touro": 77, "Gêmeos": 95, "Câncer": 87,
    "Leão": 91, "Virgem": 108, "Libra": 84, "Escorpião": 107,
    "Sagitário": 101, "Capricórnio": 112, "Aquário": 108, "Peixes": 84,
}

MEDALHAO_ARQ = {"Áries": "Aries", "Touro": "Taurus", "Gêmeos": "Gemini",
                "Câncer": "Cancer", "Leão": "Leo", "Virgem": "Virgo",
                "Libra": "Libra", "Escorpião": "Scorpio",
                "Sagitário": "Sagittarius", "Capricórnio": "Capricorn",
                "Aquário": "Aquarius", "Peixes": "Pisces"}


def _medalhao_signo(nome, cor, largura):
    """Medalhão do signo (Wikimedia Commons, CC0 — domínio público).

    O símbolo é um VETOR (`medalhoes/<Signo>.svg`) e é renderizado na
    resolução pedida, com supersampling, em vez de partir do PNG de 512px
    reduzido com upscale — que é o que fazia o Astro Pisco sair serrilhado no
    anel dos signos. Sem SVG, cai no PNG; sem nenhum dos dois, devolve None e
    o desenho cai no glifo Unicode (♈…), como sempre foi.
    """
    arq = MEDALHAO_ARQ.get(nome, nome)
    svg = os.path.join(_MEDALHOES, f"{arq}.svg")
    png = os.path.join(_MEDALHOES, f"{arq}.png")
    chave = (arq, int(largura))
    if chave not in _MED_CACHE:
        im = None
        try:
            import io
            import medalhao_svg as MS
            dados = MS.render(svg, png, largura * MS.ESCALA)
            if dados:
                im = Image.open(io.BytesIO(dados)).convert("RGBA")
        except Exception:
            im = None
        if im is None and os.path.exists(png):
            try:
                im = Image.open(png).convert("RGBA")
            except Exception:
                im = None
        _MED_CACHE[chave] = im
    im = _MED_CACHE.get(chave)
    if im is None:
        return None
    # pinta o símbolo (preto) com a cor do signo, preservando o alfa
    a = np.asarray(im)[..., 3]
    saida = np.empty_like(np.asarray(im))
    saida[..., 0] = cor[0]
    saida[..., 1] = cor[1]
    saida[..., 2] = cor[2]
    saida[..., 3] = a
    novo = Image.fromarray(saida, "RGBA")
    # reduz do supersampling com antialias
    w, h = novo.size
    return novo.resize((largura, max(1, int(h * largura / w))), Image.LANCZOS)


def _perg(sz, bold=True):
    """Fonte de pergaminho (Cinzel, clássico/celestial) — uso no título."""
    p = (f"{FONTS_PERG}/Cinzel-OFL-Bold.ttf" if bold
         else f"{FONTS_PERG}/Cinzel-OFL-Regular.ttf")
    if os.path.exists(p):
        return ImageFont.truetype(p, sz)
    return _font(sz, bold)


def _texto_traco(d, xy, texto, font, fill=TINTA_FORTE,
                 contorno=None, sw=2, sombra=None, desloc=(2, 2),
                 anchor="lm"):
    """Texto com contorno fino e sombra curta (letreiro enxuto p/ cartões)."""
    x, y = xy
    if sombra is not None:
        d.text((x + desloc[0], y + desloc[1]), texto, font=font,
               fill=(*sombra, 200), anchor=anchor)
    if contorno is not None:
        d.text((x, y), texto, font=font, fill=(*contorno, 255),
               stroke_width=sw, stroke_fill=contorno, anchor=anchor)
    d.text((x, y), texto, font=font, fill=fill, anchor=anchor)


def _letreiro(img, xy, texto, font, fill=TINTA_FORTE,
              stroke=TINTA, sombra=None, stroke_w=3,
              desloc_sombra=(4, 5), rota=0, rng=None, anchor="mm",
              spray=None):
    """Texto estilo letreiro popular / grafite: contorno + sombra deslocada
    + leve rotação manual + respingo de spray nas bordas."""
    import random as _r
    rng = rng or _r
    lay = _layer(img.size)
    ld = ImageDraw.Draw(lay)
    bb = ld.textbbox((0, 0), texto, font=font, stroke_width=stroke_w)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad = max(24, stroke_w * 4 + 18)
    cw, ch = tw + pad * 2, th + pad * 2
    txt = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    td = ImageDraw.Draw(txt)
    ox, oy = pad - bb[0], pad - bb[1]
    if sombra is not None:
        td.text((ox + desloc_sombra[0], oy + desloc_sombra[1]), texto,
                font=font, fill=(*sombra, 235), stroke_width=stroke_w,
                stroke_fill=sombra)
    # contorno, depois preenchimento por cima
    td.text((ox, oy), texto, font=font, fill=stroke,
            stroke_width=stroke_w, stroke_fill=stroke)
    td.text((ox, oy), texto, font=font, fill=fill)
    bbx = ImageDraw.Draw(txt).textbbox((0, 0), "·", font=font)
    if spray and spray[0] > 0:
        pts = []
        n = spray[0]
        for _ in range(n):
            px = rng.uniform(8, cw - 8)
            py = rng.uniform(8, ch - 8)
            # concentra o spray na horizontal perto do texto
            if abs(px - cw / 2) < tw / 2 + 26:
                pts.append((px, py))
        for px, py in pts:
            r_mancha = int(rng.uniform(1, 3))
            td.ellipse([px - r_mancha, py - r_mancha, px + r_mancha,
                        py + r_mancha], fill=(*spray[1], rng.randint(90, 200)))
    if rota:
        txt = txt.rotate(rota, resample=Image.BICUBIC,
                         fillcolor=(0, 0, 0, 0))
    cx, cy = xy
    x0, y0 = int(cx - txt.width / 2), int(cy - txt.height / 2)
    lay.paste(txt, (x0, y0), txt)
    _blit(img, lay)



def _sem_acentos(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()


def _local_canonico(local):
    if not local:
        return None
    alvo = _sem_acentos(local)
    for chave in mapa_astral.LOCALIDADES:
        if _sem_acentos(chave) == alvo:
            return chave
    return None


# ── território → cultura regional ─────────────────────────────────────────
# Municípios do sul do Espírito Santo cobertos pelo banco capixaba-sul
# (microrregião sul capixaba, IBGE). Fora daqui, o banco capixaba NÃO é
# aplicado — um nascido em Belo Horizonte não recebe Sul Capixaba.
_SUL_CAPIXABA = {
    "alfredo chaves", "anchieta", "apiaca", "atilio vivacqua",
    "cachoeiro de itapemirim", "castelo", "guarapari", "iconha",
    "itapemirim", "jerônimo monteiro", "marataizes", "mimoso do sul",
    "muniz freire", "piuma", "presidente kennedy", "rio novo do sul",
    "vargem alta",
}


def _cultura_do_territorio(local_c):
    """Cultura REGIONAL do local de nascimento, ou None.

    Só devolve banco regional quando o território tem pesquisa própria:
    sul do ES → 'capixaba'; Rio de Janeiro → 'carioca'. Qualquer outro
    território → None (nunca aplicamos um banco regional a um território
    que não foi pesquisado)."""
    if not local_c:
        return None
    chave = _sem_acentos(local_c)
    nome = chave.split("|")[0].strip()
    uf = chave.split("|")[1] if "|" in chave else ""
    if uf == "rj":
        return "carioca"
    if uf == "es" and nome in _SUL_CAPIXABA:
        return "capixaba"
    # chaves antigas sem UF (mapa_astral.LOCALIDADES)
    if not uf:
        if nome in _SUL_CAPIXABA:
            return "capixaba"
        if nome in ("rio de janeiro", "niteroi", "sao goncalo",
                    "duque de caxias", "nova iguacu", "petropolis",
                    "teresopolis", "campos dos goytacazes", "angra dos reis"):
            return "carioca"
    return None


def fotos_mapa():
    out = {}
    for root, _, files in os.walk(DIR_IMG):
        if "baixar_imagens" in root or "__pycache__" in root:
            continue
        for f in files:
            if f.endswith(".png"):
                rel = os.path.relpath(os.path.join(root, f), DIR_IMG)
                # filtra os aneis dos corpos (não nebulosas/cosmologicas)
                if rel.startswith(("sistema-solar", "jwst", "hubble", "euclid")):
                    out[rel.replace(os.sep, "/")] = os.path.join(DIR_IMG, rel)
    return out


def _carrega_json(nome):
    p = os.path.join(DIR_ARQ, nome)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            import json
            return json.load(f)
    return {}


_RODA_FOTOS_CACHE = None


def _fotos_roda():
    """Foto real de cada corpo (preferindo sistema-solar/) para a mandala."""
    global _RODA_FOTOS_CACHE
    if _RODA_FOTOS_CACHE is not None:
        return _RODA_FOTOS_CACHE
    corpo_map = {"Sol": "sol", "Lua": "lua", "Mercúrio": "mercurio",
                 "Vênus": "venus", "Marte": "marte", "Júpiter": "jupiter",
                 "Saturno": "saturno", "Urano": "urano", "Netuno": "netuno"}
    _RODA_FOTOS_CACHE = {}
    for nome, corpo in corpo_map.items():
        for k in sorted(fotos_mapa()):
            if k.startswith("sistema-solar/") and \
                    corpo in k.split("/")[-1]:
                _RODA_FOTOS_CACHE[nome] = fotos_mapa()[k]
                break
    return _RODA_FOTOS_CACHE


def ler_marco(fotos, corpo):
    """Retorna (caminho, meta) da foto de um corpo celeste, se existir."""
    for k, p in fotos.items():
        if corpo in k.split("/")[-1]:
            return p, {}
    return None, {}


def _culturas_para_filtro(cultura, territorio=None):
    """Normaliza o pedido de cultura(s) para uma lista de padrões LIKE.

    `None` (multi-cultura padrão) = as PRINCIPAIS: afro-brasileira, folclore
    brasileiro e indígena — mais a regional do território de nascimento
    quando houver. Culturas específicas (mapuche, etc.) só entram se a
    pessoa escolher explicitamente (string ou lista)."""
    if isinstance(cultura, str):
        return [cultura]
    if isinstance(cultura, (list, tuple, set)):
        return list(cultura)
    _base = ["afro", "folclore", "indigena"]
    if territorio:
        _base.append(f"regional-{territorio}")
    return _base


def buscar_arquetipos_do_signo(cur, signo, cultura, territorio=None,
                               excluir_nomes=()):
    """Arquétipos de um signo na(s) cultura(s) pedida(s). Se a cultura exata
    (ex.: capixaba) ainda não tem cadastro para aquele signo, NUNCA devolve
    vazio: cai para o folclore brasileiro, depois afro-brasileiro, depois
    indígena — assim todo signo tem correspondência, como deve ser.

    `cultura`: None (multi-cultura padrão: afro + folclore + indígena, mais
    a regional do território), uma string (cultura única, ex.: 'mapuche') ou
    uma lista (combinação escolhida na hora de fazer o mapa).

    `territorio`: cultura regional do local de nascimento ('capixaba',
    'carioca' ou None). Só filtra quando `cultura` é None (multi-cultura):
    os bancos regionais entram apenas se o território é compatível — nunca
    aplicamos Sul Capixaba a quem nasceu fora do sul do ES.

    `excluir_nomes`: nomes (normalizados) de arquétipos que já apareceram em
    outras posições do mesmo mapa — evita repetir o mesmo personagem em
    vários cartões. Regra: relevância/coerência primeiro, variedade depois —
    se TODOS os candidatos já foram usados, mantém a lista original (nunca
    devolve vazio por obrigação de variedade).

    O zodíaco (o próprio signo como 'correspondência') NUNCA entra aqui:
    o signo já é mostrado no mapa como signo da posição — a correspondência
    precisa acrescentar uma camada cultural, não repetir o que já se vê."""
    chave = _sem_acentos(signo)
    q_base = ("SELECT ar.id, ar.nome, ar.cultura, ar.simbolo, ar.historia "
              "FROM correspondencia c JOIN arquetipo ar ON ar.id = c.id_arquetipo "
              "WHERE lower(c.chave)=? AND ar.cultura != 'zodiaco'")
    q = q_base
    params = [chave]
    _cults = _culturas_para_filtro(cultura, territorio)
    if _cults:
        q += " AND (" + " OR ".join(["ar.cultura LIKE ?"] * len(_cults)) + ")"
        params += [f"%{c}%" for c in _cults]
    cur.execute(q, params)
    rows = cur.fetchall()
    if not rows and cultura:
        # escalada de garantia: nenhum signo pode ficar sem correspondência
        # (a cultura pedida não tem cadastro p/ o signo → cai nas principais)
        for _alt in ("folclore-brasileiro", "afro-brasileiro", "indigena"):
            cur.execute(q_base, [chave])
            rows = [r for r in cur.fetchall()
                    if r[2] and _alt in r[2].lower()]
            if rows:
                break
    elif not cultura:
        # multi-cultura: os bancos REGIONAIS só entram pelo território do
        # nascimento; fora dele, ficam de fora (não são "todas as culturas")
        _reg = f"regional-{territorio}" if territorio else None
        rows = [r for r in rows
                if not (r[2] or "").lower().startswith("regional-")
                or (_reg and _reg in (r[2] or "").lower())]

    def _nome_norm(r):
        return _sem_acentos(r[1].split(" (")[0])

    # variedade com relevância: filtra os já usados, mas nunca esvazia
    if excluir_nomes:
        _bloqueados = {_sem_acentos(n) for n in excluir_nomes}
        _novos = [r for r in rows if _nome_norm(r) not in _bloqueados]
        if _novos:
            rows = _novos

    def _rank(r):
        # prioriza arquétipos com imagem PD (mais realista); depois as
        # culturas brasileiras (afro/folclore/indígena/regionais) antes das
        # de fora (mapuche etc. — termos específicos entram só quando
        # pertinentes); mantém o resto por id estável.
        img = 1 if (r[1].split(" (")[0] and
                    _sem_acentos(r[1].split(" (")[0]) in ARQ_IMAGEM) else 0
        _cult = (r[2] or "").lower()
        _brasil = 0 if (_cult.startswith(("afro", "folclore", "indigena",
                                          "regional"))) else 1
        return (img, -_brasil, r[0])
    return sorted(rows, key=_rank, reverse=True)


_PLANETA_CHAVE = {"Sol": "sol", "Lua": "lua", "Mercúrio": "mercurio",
                  "Vênus": "venus", "Marte": "marte", "Júpiter": "jupiter",
                  "Saturno": "saturno"}


def arquétipo_por_planeta(cur, nome_planeta, signo, cultura, territorio=None,
                          excluir_nomes=()):
    """Arquétipo de correspondência do POSICIONAMENTO (planeta no signo).

    A associação é feita com o signo onde o planeta está — ex.: 'Marte em
    Capricórnio' → os arquétipos de Capricórnio — e não com o planeta solto.
    O arquétipo do próprio planeta (ex.: Ogum para Marte) entra como leitura
    complementar, DEPOIS dos do signo, quando existir no catálogo.
    `excluir_nomes`: nomes já usados em outras posições do mapa (variedade
    com relevância — nunca esvazia a lista)."""
    arqs = buscar_arquetipos_do_signo(cur, signo, cultura, territorio,
                                      excluir_nomes)
    chave = _PLANETA_CHAVE.get(nome_planeta)
    if chave:
        q = ("SELECT ar.id, ar.nome, ar.cultura, ar.simbolo, ar.historia, "
             "c.certeza, c.fonte FROM correspondencia c "
             "JOIN arquetipo ar ON ar.id = c.id_arquetipo "
             "WHERE lower(c.chave)=? AND ar.cultura != 'zodiaco'")
        params = [chave]
        _cults = _culturas_para_filtro(cultura, territorio)
        if _cults:
            q += " AND (" + " OR ".join(
                ["ar.cultura LIKE ?"] * len(_cults)) + ")"
            params += [f"%{c}%" for c in _cults]
        cur.execute(q, params)
        rows = cur.fetchall()
        if rows:
            ordem = {"alta": 0, "media": 1, "baixa": 2}
            rows = sorted(rows, key=lambda r: (ordem.get(r[5], 9), r[0]))
            # não repete arquétipo que já veio pelo signo (ex.: âncora)
            ja = {r[1].split(" (")[0].lower() for r in arqs}
            if excluir_nomes:
                ja |= {_sem_acentos(n) for n in excluir_nomes}
            arqs = arqs + [r for r in rows
                           if r[1].split(" (")[0].lower() not in ja]
    return arqs


def _contexto_curto(a, limite=60):
    """Linha curta de contexto para arquétipos de culturas de termos
    específicos (ex.: mapuche — 'Melipal — α, β, δ e π de Escorpião').
    Culturas brasileiras (afro/folclore/indígena/regionais) já falam por si;
    as de fora ganham o contexto do campo `simbolo` (que é a descrição
    curta registrada no banco) para o nome não ficar solto no mapa."""
    _cult = (a[2] or "").lower() if len(a) > 2 else ""
    if _cult.startswith(("afro", "folclore", "indigena", "regional")):
        return ""
    _ctx = (a[3] if len(a) > 3 else "") or ""
    _ctx = " ".join(str(_ctx).split())
    if not _ctx:
        _ctx = (a[4] if len(a) > 4 else "") or ""
        _ctx = " ".join(str(_ctx).split())
    if len(_ctx) > limite:
        _ctx = _ctx[:limite].rsplit(" ", 1)[0].rstrip(",-— ") + "…"
    return _ctx


def _mascarar_redondo(im, lado):
    m = Image.new("L", (lado, lado), 0)
    ImageDraw.Draw(m).ellipse((0, 0, lado, lado), fill=255)
    out = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    out.paste(im, (0, 0), m)
    return out


_PD_INDEX = None


def _pd_index():
    """Índice normalizado das chaves de ARQ_IMAGEM: cada chave vira uma
    forma canônica (sem acento, sem pontuação, espaços simples) → arquivo.
    Une também as variações de acento/underscore/hífen que vêm da tabela."""
    global _PD_INDEX
    if _PD_INDEX is None:
        _PD_INDEX = {}
        for k, fn in ARQ_IMAGEM.items():
            nrm = re.sub(r"[\W_]+", " ", _sem_acentos(k)).strip()
            if nrm:
                _PD_INDEX[nrm] = fn
    return _PD_INDEX


def _arq_figura(nome):
    """Nome do arquivo (sem extensão) com a figura PD de um arquétipo, ou
    None. Busca exata primeiro (nome normalizado); senão casa por palavra
    inteira entre aspas de uma chave curta (ex.: 'jaguará' encontra a figura
    da onça, mas 'ema' não acerta dentro de 'piracema')."""
    if not nome:
        return None
    chv = re.sub(r"[\W_]+", " ", _sem_acentos(str(nome).strip().lower())).strip()
    if not chv:
        return None
    idx = _pd_index()
    if chv in idx:
        return idx[chv]
    for kn, fn in idx.items():
        if kn and re.search(r"(?:^|\s)%s(?:\s|$)" % re.escape(kn), chv):
            return fn
    return None


def _imagen_pd(nome):
    """Caminho da imagem em domínio público de um arquétipo/asterismo (ou
    None): casa por nome normalizado e por palavra inteira (evitando
    colagens curtas)."""
    fn = _arq_figura(nome)
    if fn:
        return os.path.join(DIR_PD, fn + ".png")
    return None


def _crop_circular(path, cx, cy, r):
    """Recorta a imagem na íntegra em círculo (zoom-to-fill centrado)."""
    try:
        im = Image.open(path).convert("RGB")
    except Exception:
        return None
    lado = r * 2
    w, h = im.size
    scale = max(lado / w, lado / h)
    nw, nh = int(w * scale) + 1, int(h * scale) + 1
    im = im.resize((nw, nh), Image.LANCZOS)
    left = (nw - lado) // 2
    top = (nh - lado) // 2
    im = im.crop((left, top, left + lado, top + lado))
    return _mascarar_redondo(im.convert("RGBA"), lado)


# ── verso ──
FRASES = {
    "serenidade": ["cala o mar dentro do peito,",
                   "a água não tem pressa de chegar,",
                   "o silêncio pousa devagar no quarto,"],
    "paixão": ["o fogo acorda e pede nome,",
               "o corpo inteiro vira brasa no escuro,",
               "o desejo desenha trilhas de carvão,"],
    "curiosidade": ["quero ler o céu por dentro do olho,",
                    "pergunto às estrelas que horas elas são,",
                    "o mapa é uma pergunta sem resposta pronta,"],
    "esperança": ["um nascer-do-dia atravessa a retina,",
                  "amanhã chega sempre com as mãos abertas,",
                  "o que parece fim é curva do caminho,"],
    "verdade": ["o céu desce devagar até a prova,",
                "tudo que é firme um dia se confessa,",
                "a verdade mora do lado de dentro do nome,"],
    "melancolia": ["as estrelas se apagam com mágoa,",
                   "a memória guarda o que o vento apagou,",
                   "o luar hoje tem gosto de quem parte,"],
    "coragem": ["meu passo não treme diante do abismo,",
                "o medo é só uma nuvem antes da tempestade,",
                "quem nasceu pra ir não volta sem estrada,"],
    "encantamento": ["tudo aqui se explica por encanto,",
                     "o mundo é o que a gente escolhe acreditar,",
                     "há um feitiço fino costurado no dia,"],
}
TEMAS_MAR = ["mar", "maré", "onda", "oceano", "rio", "água", "peixe", "vaga"]
TEMAS_FOGO = ["fogo", "brasa", "sol", "chama", "lumiar", "aurora", "estrela"]
TEMAS_TERRA = ["terra", "raiz", "chão", "pedra", "semente", "campo", "flor"]
TEMAS_AR = ["vento", "céu", "viagem", "asas", "nuvem", "horizonte", "voo"]


# ── florilégio do caderno do Astro Pisco: versos verdadeiros puxados à mão
# do corpus-astropisco — são a matéria da estrofe-colagem de cada mapa ─────
_FLORILEGIO = [
    "assisto o hiato passar contra o vento",
    "musgo doutrinas que descolam de sismas",
    "cerco de copas embaralho respostas",
    "azucrino o mar que em neptuno floresço",
    "leio universos, descubro buracos de silêncio",
    "desfilo o fluxo de super novas adentro",
    "finco bandeiras de partidos fictícios",
    "rumino o lado oculto dos signos, conheço",
    "sondar os venenos que o mato deprime",
    "buscar tempestades que se desfazem nos mitos",
    "surto o relógio que decora a memória",
    "sigo contas que no chato silêncio",
    "frago na mente um tanto de espinhos",
    "cultivo o saber no canto, eu animo",
    "transformo sentimento em objeto indireto",
    "ligo humanos ao animal extinto",
    "meço palavras, jorro quimeras de um átimo",
    "nado de frente e de costas, abro o timo",
    "rodo no áries para além do esqueço",
    "enrolo tubos de textos, momentos",
    "põe a palavra a serviço da pira e pinta um lado menos realista",
    "novos mundos pra explorar na mente, novos rumos pra despencar na corrente",
    "são os sonhos misturados com o espelho",
    "os astros estão dando uma volta na minha cabeça",
    "girar o mundo tão falado, eclipse efêmero",
    "e agora pois que ressurge o tempo das coisas",
    "esferas de poder, esferas do ser",
    "somos de líquido e ar, solva, faz rodar, eu sei",
    "firmão deus que sabe ocultar palavras das sensações",
    "dos escombros reciclo as arestas",
    "sou o mesmo alvo do trago, vestígios",
    "calcular ondas que propagam células cuidadosas",
    "nem puderam o bote abrir o fundamento estava para se cumprir",
    "agora o espetáculo estava para começar",
    "dos mistérios de não poder dizer",
    "já se tem por mente um propósito",
    "tinta de terra e colagem sobre tecido",
]


def _linha_destaques(destaques, rng):
    """Verso que sublinha os destaques do mapa (signos com mais corpos na
    última fileira — informação nova, nunca repete Sol/Lua/Asc)."""
    if not destaques:
        return None
    _sg1, _cs1 = destaques[0]
    _cs1 = [c for c in _cs1 if c][:3]
    if len(destaques) >= 2:
        _sg2 = destaques[1][0]
        return rng.choice([
            f"no alto, {_sg1} e {_sg2} acendem o destaque do mapa,",
            f"{_sg1} e {_sg2} — o céu sublinha o que pede atenção,",
            f"o céu acende {_sg1} e {_sg2} no alto da folha,"])
    if len(_cs1) >= 2:
        _c = ", ".join(_cs1)
        return rng.choice([
            f"no alto, {_sg1} em destaque — {_c},",
            f"{_sg1} acende no alto com {_c},",
            f"o céu destaca {_sg1}: {_c} em chama,"])
    _c = _cs1[0] if _cs1 else "os astros"
    return rng.choice([
        f"no alto, {_sg1} em destaque com {_c},",
        f"{_sg1} acende no alto com {_c},",
        f"o céu sublinha {_sg1} com {_c},"])


def gerar_verso(tema, feeling, signo_asc, signo_sol, mensaje=None, rng=None,
                nome=None, sementes=(), destaques=(), referencias=None):
    """COMPOR ESTROFE: poema único do mapa, em colagem com o caderno do
    Astro Pisco. Regra de composição: a estrofe abre com uma cláusula do
    caderno que conversa com o tema (tema → conceitos → corpus), amarra os
    signos do consultante no segundo verso, sublinha os destaques do mapa,
    intercala mais uma cláusula do caderno e fecha com a imagem do elemento
    do tema — nunca a mesma costura entre obras e sem linhas repetidas
    dentro do próprio poema. `referencias` (lista) recebe (titulo, link)
    dos posts de origem de cada cláusula do caderno usada na estrofe."""
    import random as _r
    rng = rng or _r
    t = (tema or "").lower()

    # elemento da estrofe: o do tema quando o mapa vier com tema, senão o do
    # signo solar do consultante (cada mapa carrega o seu próprio elemento)
    _fogo = set(TEMAS_FOGO)
    _terra = set(TEMAS_TERRA)
    _ar = set(TEMAS_AR)
    _mar = set(TEMAS_MAR)
    if any(m in t for m in _mar):
        elem = "mar"
    elif any(f in t for f in _fogo):
        elem = "fogo"
    elif any(x in t for x in _terra):
        elem = "terra"
    elif any(x in t for x in _ar):
        elem = "ar"
    else:
        _sg = (signo_sol or signo_asc or "").lower()
        if _sg in ("câncer", "cancer", "escorpião", "escorpiao", "peixes"):
            elem = "mar"
        elif _sg in ("áries", "aries", "leão", "leao", "sagitário", "sagitario"):
            elem = "fogo"
        elif _sg in ("touro", "virgem", "capricórnio", "capricornio"):
            elem = "terra"
        else:
            elem = "ar"

    # cláusulas do caderno que conversam com o mapa (tema → conceitos →
    # corpus); o florilégio fica de reserva quando o corpus não achar nada
    _linhas_blog, _refs_blog = _estrofe_do_blog(tema, nome, rng, sementes,
                                                n_linhas=2)
    _esta = list(_FLORILEGIO)
    _rng2 = random.Random(rng.randint(0, 2 ** 31) ^ hash(_esta[0]))
    _rng2.shuffle(_esta)
    cad1 = _linhas_blog[0] if _linhas_blog else _esta[0]
    if len(_linhas_blog) > 1:
        cad2 = _linhas_blog[1]
    else:
        cad2 = next((c for c in _esta[1:] if c != cad1), _esta[0])
    _refs = list(_refs_blog)
    if not _linhas_blog:
        _refs = [None, None]

    # verso-âncora dos signos (varia de mapa p/ mapa)
    _meio = rng.choice([
        f"{signo_asc} sobe o horizonte, {signo_sol} aquece o meio-dia do coração,",
        f"{signo_asc} abre a porta, {signo_sol} acende a casa do fundo,",
        f"{signo_asc} vigia a chegada, {signo_sol} guarda a brasa do meio,",
        f"{signo_sol} guarda o meio-dia, {signo_asc} segura a tua porta,",
        f"{signo_asc} vem primeiro, {signo_sol} segura a tua brasa,",
        f"{signo_asc} sustenta o teu nascer, {signo_sol} aquece o coração,"])

    # verso dos destaques do mapa (só quando há destaque além das fileiras)
    _destaque_linha = _linha_destaques(destaques, rng)

    # fecho do elemento da estrofe (repertório maior p/ variar)
    if elem == "mar":
        cauda = rng.choice([
            "a maré guarda o mapa no fundo do sal.",
            "o rio carrega teu nome até onde o mar começa.",
            "a água devolve no espelho o que a boca não disse.",
            "o fundo guarda, devagar, o que a pressa não leu."])
    elif elem == "fogo":
        cauda = rng.choice([
            "a brasa escreve o mapa na cara do vento.",
            "o fogo acende a rota e apaga o medo.",
            "a chama guarda o caminho pra quem volta.",
            "a brasa alumia a volta de quem arriscou."])
    elif elem == "terra":
        cauda = rng.choice([
            "a raiz segura teu mapa no meio do chão.",
            "a terra escreve devagar o que a pressa não lê.",
            "a semente sabe o nome do que vai nascer.",
            "o chão guarda o passo que o vento não apaga."])
    elif elem == "ar":
        cauda = rng.choice([
            "o vento carrega teu mapa pra qualquer norte.",
            "as asas desenham no céu o atalho de casa.",
            "a nuvem guarda a chuva que o teu passo precisa.",
            "o vento leva o nome, o céu devolve o rumo."])
    else:
        cauda = f"{tema or 'o teu nome'} feito constelação no caminho de volta."

    # imagem do elemento no meio da estrofe
    if elem == "mar":
        imagem = rng.choice([
            "a vaga levanta e devolve, a aresta aprende a ceder,",
            "o sal escreve tua rota no dorso da onda,",
            "a maré sobe devagar e ensina a espera,",
            "cada onda guarda um nome que volta pra casa,"])
    elif elem == "fogo":
        imagem = rng.choice([
            "a brasa acesa não pergunta o caminho,",
            "o fogo queimava o medo na entrada da tarde,",
            "a chama ensina a arder sem gastar a pessoa,",
            "o lume abre a noite e corta o frio do nome,"])
    elif elem == "terra":
        imagem = rng.choice([
            "a semente no chão não tem pressa de flor,",
            "a raiz escreve no escuro o mapa da seiva,",
            "o campo guarda as estações no mesmo lugar,",
            "a terra não nega a colheita a quem chega,"])
    elif elem == "ar":
        imagem = rng.choice([
            "o vento muda a frase mas guarda o sentido,",
            "as asas aprendem no céu o nome do retorno,",
            "a nuvem passa e a paisagem continua tua,",
            "o ar sustenta tudo que o peito ainda sonha,"])
    else:
        imagem = rng.choice([
            "o céu guarda o mapa no lugar de onde veio,",
            "a estrela mais alta anota o teu começo,",
            "a lua empresta o rumo a quem não tem farol,",
            "o horizonte é a costura da tua volta,"])

    def _verso(_x):
        _x = str(_x).strip()
        _x = _x.rstrip(".,;: ")
        return _x[0].upper() + _x[1:] if _x else _x

    verso = [_verso(cad1) + ",",
             _meio]
    if _destaque_linha:
        verso.append(_verso(_destaque_linha).rstrip(",").rstrip(".") + ",")
    verso += [_verso(imagem).rstrip(",").rstrip(".") + ",",
              _verso(cad2).rstrip(",").rstrip(".") + ",",
              _verso(cauda).rstrip(",")
              + ("." if not _verso(cauda).rstrip(",").endswith(".") else "")]
    if mensaje and str(mensaje).strip():
        mj = str(mensaje).strip().rstrip(".")
        verso.append(f"{mj} — e fica, baixo, guardado na borda do mapa.")
    if referencias is not None:
        referencias[:] = [r for r in _refs if r]
    return verso


# ── frase do caderno do autor (blog) com termos próximos do tema/nome ────
_BLOG_CORPUS = None
_BLOG_CLAUSES = None
_BLOG_CLAUSE_REF = None   # cláusula normalizada → (titulo, link) do post


def _norm_clausula(cl):
    """Normaliza uma cláusula p/ casar com a referência do post de origem
    (tira marcadores [imagem]/[video] e cabeçalhos '[titulo — data]')."""
    cl = re.sub(r"\[\s*(imagem|video)\s*\]", " ", cl, flags=re.I)
    cl = re.sub(r"^\[[^\]]*\]\s*", "", cl)
    return " ".join(cl.split()).strip(" ,.;:").lower()


def _carregar_corpus_blog():
    """Carrega uma vez o texto do caderno do Astro Pisco: frases inteiras
    (30..220 chars) e cláusulas menores (24..100 chars) para a costura de
    uma estrofe-colagem com o mapa. Também monta o mapa cláusula → post de
    origem (titulo + link) a partir do corpus-bruto.json, para registrar
    de onde veio cada linha da estrofe."""
    global _BLOG_CORPUS, _BLOG_CLAUSES, _BLOG_CLAUSE_REF
    if _BLOG_CORPUS is not None:
        return
    _BLOG_CORPUS = []
    _BLOG_CLAUSES = []
    # regex de lixo: timestamps, [imagem], urls, badges; filtra linhas sujas
    _JUNK = re.compile(
        r"\[\s*imagem\s*\]|http|^\d{2}\s\w{3}\s\d{4}|"
        r"\d{2}:\d{2}:\d{2}\s\+\d{4}|badge|comment|json|"
        r"^\s*\[.*\]\s*$|^[^\w]{3,}",
        re.IGNORECASE)
    for _path in (
            "/mnt/dados/home-italivre/iastro-ia/pacote-linguagem/"
            "3-corpus/corpus-astropisco/corpus-astropisco.txt",
            "/mnt/dados/home-italivre/iastro-ia/pacote-linguagem/"
            "3-corpus/corpus-astropisco.txt"):
        if os.path.exists(_path):
            try:
                with open(_path, encoding="utf-8") as _f:
                    txt = _f.read()
                for _par in re.split(r"[.!?»](?:\s|\n)", txt):
                    _par = " ".join(_par.split())
                    if not _JUNK.search(_par) and 30 <= len(_par) <= 220:
                        _BLOG_CORPUS.append(_par.strip())
                    for _cl in re.split(r"[.,;:–—](?:\s)", _par):
                        _cl = " ".join(_cl.split()).strip(" ,.;:")
                        if not _JUNK.search(_cl) and 24 <= len(_cl) <= 100:
                            _BLOG_CLAUSES.append(_cl.strip())
            except Exception:
                pass

    # referências: cláusula → post de origem (titulo + link) p/ registrar
    # de onde veio cada linha da estrofe (corpus-bruto.json)
    _BLOG_CLAUSE_REF = {}
    for _path in (
            "/mnt/dados/home-italivre/iastro-ia/pacote-linguagem/"
            "3-corpus/corpus-astropisco/corpus-bruto.json",
            "/mnt/dados/home-italivre/iastro-ia/pacote-linguagem/"
            "3-corpus/corpus-bruto.json"):
        if os.path.exists(_path):
            try:
                import json as _json
                with open(_path, encoding="utf-8") as _f:
                    _posts = _json.load(_f)
                for _p in _posts:
                    _tit = str(_p.get("titulo", "")).strip()
                    _lnk = str(_p.get("link", "")).strip()
                    if not _tit:
                        continue
                    for _par in re.split(r"[.!?»](?:\s|\n)",
                                         str(_p.get("texto", ""))):
                        for _cl in re.split(r"[.,;:–—](?:\s)", _par):
                            _cl = _norm_clausula(_cl)
                            if 24 <= len(_cl) <= 100 and not _JUNK.search(_cl):
                                _BLOG_CLAUSE_REF.setdefault(_cl, (_tit, _lnk))
            except Exception:
                pass


def _mundo_semantico(tema, nome, sementes=(), rng=None):
    """Conjunto de palavras que 'chamam' a poesia: tema + nome + arquétipos
    do mapa + a família de palavras do elemento do tema + variações."""
    def _tokens(s):
        return {w for w in re.findall(r"[a-zà-úâ-û]{4,}", (s or "").lower())}

    mundo = (_tokens(tema) | _tokens(nome)) - _tokens("astropisco planetário")
    for _s in sementes or ():
        mundo |= _tokens(_s)
    _t = _tokens(tema)
    import random as _r
    rng = rng or _r
    for _fam in (TEMAS_MAR, TEMAS_FOGO, TEMAS_TERRA, TEMAS_AR):
        _fs = set(_fam)
        if _t & _fs:
            mundo |= _fs
    # famílias de conceitos: quando o tema toca um conceito (perda, cura,
    # mar, folclore...), a família inteira entra no mundo semântico — a
    # poesia passa a conversar com o assunto de verdade (poesia_conceitos)
    for _fam in _CONCEITOS.values():
        if _t & set(_fam):
            mundo |= set(_fam)
    # sinônimos simples p/ ampliar a colagem sem trocar de assunto
    sinon = {"ver": "olho olhar ver olhos", "céu": "céu estrela estrelas noite",
             "mar": "mar água onda oceano vaga", "nome": "nome letra ser chamar",
             "terra": "terra chão raiz solo semente", "fogo": "fogo brasa chama"}
    for _n, _toks in sinon.items():
        if _n in mundo:
            mundo |= set(_toks.split())
    mundo -= _tokens("astropisco planetário")
    return mundo


def _frase_do_blog(tema, nome, rng=None, sementes=()):
    """Puxa do arquivo de textos do blog uma frase que compartilhe palavras
    com o tema, o nome do consultante e os ARQUÉTIPOS do mapa (sementes).
    Quando várias frases empatam, embaralha entre elas (a obra muda) — e se
    der, costura uma colagem poética de duas delas. Trunca p/ caber na obra.
    Devolve (frase, ref) — ref = (titulo, link) do post de origem, ou None."""
    _carregar_corpus_blog()
    import random as _r
    rng = rng or _r

    def _tokens(s):
        return {w for w in re.findall(r"[a-zà-úâ-û]{4,}", (s or "").lower())}

    mundo = _mundo_semantico(tema, nome, sementes, rng)
    melhores = []
    if mundo:
        for fr in _BLOG_CORPUS:
            sc = len(mundo & _tokens(fr))
            if sc > 0:
                melhores.append((sc, fr))
    melhores.sort(key=lambda t: -t[0])
    if not melhores:
        if not _BLOG_CORPUS:
            return None, None
        best = rng.choice(_BLOG_CORPUS)
    else:
        topo = melhores[0][0]
        piso = max(topo - 2, 1)
        bacia = [fr for sc, fr in melhores if sc >= piso][:6]
        best = rng.choice(bacia)
        # colagem poética: se há uma segunda boa, costura com travessão
        if len(bacia) >= 3:
            seg = bacia[rng.randint(1, min(2, len(bacia) - 1))]
            seg = seg.split(", ")[-1] if len(seg) > 40 else seg
            best = f"{best} — {seg}"
    _ref = (_BLOG_CLAUSE_REF or {}).get(_norm_clausula(best))
    if len(best) > 160:
        corte = best[:160].rsplit(" ", 1)[0]
        best = corte.rstrip(",. ") + "…"
    # corta cabeçalhos tipo "Nome da lenda: ..." — fica só a poesia
    best = re.sub(r"^[A-ZÁ-ÚÀ-Û][^\n:—–]*?[:–—]\s+", "", best, count=1)
    best = (best[0].upper() + best[1:]) if best else best
    return best.strip(), _ref


def _estrofe_do_blog(tema, nome, rng=None, sementes=(), n_linhas=3):
    """ESTAMPAR ESTROFE: pega cláusulas do caderno do Astro Pisco que
    conversem com o mapa e as costura em linhas poéticas (colagem de
    várias frases — cada obra costura de um jeito). Cada linha é uma
    cláusula distinta, sem cortar no meio de palavra; se o mundo semântico
    não achar nada, devolve linhas vazias p/ o verso atual assumir.
    Devolve (linhas, refs) — refs = [(titulo, link)] de cada linha."""
    _carregar_corpus_blog()
    if not _BLOG_CLAUSES:
        return [], []
    import random as _r
    rng = rng or _r

    def _tokens(s):
        return {w for w in re.findall(r"[a-zà-úâ-û]{4,}", (s or "").lower())}

    mundo = _mundo_semantico(tema, nome, sementes, rng)
    clas = []
    if mundo:
        for cl in _BLOG_CLAUSES:
            sc = len(mundo & _tokens(cl))
            if sc > 0:
                clas.append((sc, cl))
    if not clas:
        clas = [(0, cl) for cl in rng.sample(
            sorted(set(_BLOG_CLAUSES), key=len)[:220], min(36, len(set(_BLOG_CLAUSES))))]
    clas.sort(key=lambda t: -t[0])
    topo = clas[0][0]
    bacia = [cl for sc, cl in clas if sc >= max(topo - 2, 0)][:12]
    escolhidas = rng.sample(bacia, min(n_linhas, len(bacia)))
    linhas = []
    refs = []
    for cl in escolhidas:
        _ref = (_BLOG_CLAUSE_REF or {}).get(_norm_clausula(cl))
        cl = re.sub(r"^\[[^\]]*\]\s*", "", cl)  # cabeçalho '[titulo — data]'
        cl = re.sub(r"^[A-ZÁ-ÚÀ-Û][^\n:—–]*?[:–—]\s+", "", cl, count=1)
        cl = cl.strip()
        if len(cl) > 96:
            cl = cl[:96].rsplit(" ", 1)[0].rstrip(",. ") + "…"
        if not linhas or cl != linhas[-1]:
            linhas.append(cl)
            refs.append(_ref)
    return linhas, refs


def _polar(cx, cy, R, lon):
    a = math.radians(lon % 360)
    return (cx + R * math.cos(a), cy - R * math.sin(a))


def _layer(size):
    return Image.new("RGBA", size, (0, 0, 0, 0))


def _blit(img, layer):
    """Compõe a camada por cima de `img`, mutando `img` no lugar.

    `img.paste(layer, (0,0), layer)` usa o alfa da própria camada como máscara,
    o que dá src*a + dst*(1-a) — exatamente o mesmo resultado do antigo
    `paste(alpha_composite(fundo_transparente, layer), (0,0), layer)`, já que
    compor sobre um fundo totalmente transparente devolve a própria camada.
    A vantagem é não alocar uma tela RGBA cheia por chamada: na obra de 26 MP
    eram centenas de MB de tráfego em cada uma das dezenas de colagens.
    Vale para base RGB e RGBA.
    """
    img.paste(layer, (0, 0), layer)


def _bbox_com_pads(mask, pad):
    """Caixa envolvente da região pintada, dilatada por `pad` px e presa à
    borda da imagem. Devolve None quando a máscara está vazia.

    As máscaras da aguada são desenhos com pouca tinta (um setor do zodíaco,
    um disco, uma letra) desenhados sobre uma tela de 26 MP: pintar, borrar e
    corroer só na caixa envolvente dá o mesmo resultado por uma fração do
    custo.
    """
    if pad <= 0:
        return mask.getbbox()
    w, h = mask.size
    bx = mask.getbbox()
    if not bx:
        return None
    x0 = max(0, bx[0] - pad)
    y0 = max(0, bx[1] - pad)
    x1 = min(w, bx[2] + pad)
    y1 = min(h, bx[3] + pad)
    return (x0, y0, x1, y1)


def _placa(img, box, cor=(45, 36, 22), radius=30, borda=(214, 190, 134),
           bl=3):
    """Garante contraste entre o texto claro e o papel texturizado: um
    painel escuro com borda desenhada por trás de um bloco de texto (cara
    de placa gravada — as 'bolas' do papel não disputam mais com a letra)."""
    lay = _layer(img.size)
    dl = ImageDraw.Draw(lay)
    dl.rounded_rectangle(box, radius=radius, fill=cor)
    if borda:
        dl.rounded_rectangle(box, radius=radius, outline=borda, width=bl)
        dl.rounded_rectangle([box[0] + bl * 3, box[1] + bl * 3,
                              box[2] - bl * 3, box[3] - bl * 3],
                             radius=max(radius - bl * 3, 6),
                             outline=(*borda, 120), width=1)
    _blit(img, lay)


# ══════════════════════════════════════════════════════════════════════
#  AGUADA / PINTURA a úmido (pigmento translúcido sobre máscara)
# ══════════════════════════════════════════════════════════════════════

def _claro(cor, fator=0.62):
    """Clareia uma cor para texto sobre fundo escuro (legibilidade): mistura
    com branco — cores de signo escuras (Escorpião, Capricórnio...) viram
    tons pastéis que leem bem na aguada escura dos cartões."""
    r, g, b = cor[:3]
    return tuple(int(c + (255 - c) * fator) for c in (r, g, b))


def _variar(cor, rng, sat=None, lum=None):
    """Deriva um tom vizinho da cor (aguada faz a cor sangrar)."""
    r, g, b = [c / 255.0 for c in cor[:3]]
    h, s, l = colorsys.rgb_to_hls(r, g, b)
    if sat is None:
        sat = max(0.0, min(1.0, s + rng.uniform(-0.22, 0.18)))
    if lum is None:
        lum = max(0.04, min(0.94, l + rng.uniform(-0.16, 0.14)))
    r, g, b = colorsys.hls_to_rgb(h, sat, lum)
    return (int(r * 255), int(g * 255), int(b * 255))


def _aguada(mask, cor_base, rng, tons=120, r0=7, r1=95, blur=5,
            alpha=(16, 48), corno=None):
    """Pinta a região da máscara como aguada translúcida (camadas de
    pigmento com borda macia) e devolve um layer RGBA na medida da mask.

    Otimização: a pintura acontece só dentro da caixa envolvente da máscara
    (com margem para os pincéis e para os borrões). Antes, cada uma das 26
    aguadas da obra pintava e borrava os 26 MP inteiros, sendo que um setor
    do zodíaco ocupa ~4% da tela. O RNG é semeado por aguada a partir do
    estado do `rng` recebido, então a sequência de manchas continua a mesma
    dentro da caixa — só o trabalho fora dela deixou de existir.
    """
    import random as _r
    rng = rng or _r
    W, H = mask.size
    # A amostragem continua sobre a tela INTEIRA, como sempre foi: é dela que
    # sai a densidade da aguada (a maioria das tentativas cai fora da máscara
    # e é descartada — é esse descarte que dá a transparência da lavagem).
    # Só o desenho, o borrão e a borda úmida ficam restritos à caixa envolvente
    # da tinta; a margem cobre o alcance do pincel e do borrão, de modo que
    # nenhuma mancha é cortada.
    pad = int(r1 + blur * 3 + 10)
    box = _bbox_com_pads(mask, pad)
    if box is None:
        return _layer((W, H))
    x0, y0, x1, y1 = box
    sub = mask.crop(box)
    w, h = sub.size

    blanco = mask.filter(ImageFilter.GaussianBlur(blur))
    lay = _layer((w, h))
    d = ImageDraw.Draw(lay)
    al0, al1 = alpha
    for _ in range(tons):
        a = 0
        for _t in range(10):
            x = rng.randint(0, W - 1)
            y = rng.randint(0, H - 1)
            a = blanco.getpixel((x, y))
            if a > 70:
                break
        if a <= 70:
            continue
        r = rng.randint(r0, r1)
        cor = _variar(cor_base, rng) if corno is None else corno(rng)
        alfa = int(a / 255 * rng.uniform(al0, al1))
        d.ellipse([x - r - x0, y - r - y0, x + r - x0, y + r - y0],
                  fill=(*cor, alfa))
    lay = lay.filter(ImageFilter.GaussianBlur(1.5))
    op = lay.getchannel("A")
    op = ImageChops.multiply(op, sub)
    lay.putalpha(op)
    bb = _borda_umida(sub, cor_base, rng, larg=6, alpha=60)
    if bb is not None:
        lay = Image.alpha_composite(bb, lay)
        lay.putalpha(ImageChops.multiply(lay.getchannel("A"), sub))

    out = _layer((W, H))
    out.alpha_composite(lay, (x0, y0))
    return out


def _pincelada(d, p0, p1, cor, largura, rng, n=7):
    """Pincelada orgânica: linha formada por N tramos trapezoidais com
    ponta afinada e leve variação — parece traço de pincel, não pixel."""
    x0, y0 = p0
    x1, y1 = p1
    for i in range(n):
        t = i / (n - 1)
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        jx = rng.uniform(-1.5, 1.5)
        jy = rng.uniform(-1.5, 1.5)
        rt = rng.uniform(0.75, 1.05)
        lw = max(1.0, largura * rt * min(1.0, math.sin(math.pi * t) + 0.35))
        d.ellipse([x + jx - lw / 2, y + jy - lw / 2,
                   x + jx + lw / 2, y + jy + lw / 2], fill=cor)


def _ramo_tinta(d, p0, p1, cor, rng):
    """Raminho desenhado à mão: caule fino levemente torto + folhas ovais/
    lanceoladas alternadas — usado nas 'plantas regentes' do cartão TERRA &
    CÉU. Folhas em forma de gota (contorno + interior), não blocos."""
    x0, y0 = p0
    x1, y1 = p1
    _linha_mao(d, p0, p1, cor, 2, rng, jitter=1.2, passos=10)
    n = max(3, int(abs(x1 - x0) // 26))
    for i in range(1, n):
        t = i / n
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        lado = 1 if i % 2 else -1
        dl = rng.uniform(14, 20)   # comprimento da folha
        ang = rng.uniform(-0.55, 0.55) + lado * 1.15
        # ponto da folha: sai do caule, em linha ao longo do ramo
        fx = x + math.cos(ang) * dl * 0.55
        fy = y + math.sin(ang) * dl * 0.55
        _folha(d, (x, y), (fx, fy), cor, rng)
    _folha(d, (x1, y1), (x1 + 18, y1 - 2), cor, rng)


def _folha(d, base, ponta, cor, rng):
    """Uma folha em forma de amêndoa/lança, preenchida (sem contornos que
    pareçam 'quadradinhos'): perfil arredondado no meio e afiado nas pontas,
    com nervura central. O luzidio vem de uma mancha clara interna."""
    bx, by = base
    px, py = ponta
    dx, dy = px - bx, py - by
    ln = math.hypot(dx, dy)
    if ln < 1:
        ln = 1
    nx, ny = -dy / ln, dx / ln          # normal (largura da folha)
    lw = max(2.5, ln * rng.uniform(0.16, 0.24))
    # perfil da folha: mais largo no meio, estreito nas pontas
    npt = 14
    perfil = []
    for i in range(npt + 1):
        t = i / npt
        w = math.sin(math.pi * t) * lw
        perfil.append((bx + dx * t + nx * w, by + dy * t + ny * w))
    for i in range(npt, -1, -1):
        t = i / npt
        w = math.sin(math.pi * t) * lw
        perfil.append((bx + dx * t - nx * w, by + dy * t - ny * w))
    sombra = tuple(max(0, int(c * 0.82)) for c in cor[:3])
    luz = tuple(min(255, int(c + (255 - c) * 0.28)) for c in cor[:3])
    # corpo + contorno leve + nervura central torta
    d.polygon(perfil, fill=(*cor, 160))
    d.line(perfil + [perfil[0]], fill=(*sombra, 200), width=1, joint="curve")
    _linha_mao(d, base, ponta, (*sombra, 200), 1, rng, jitter=0.8, passos=4)
    # luzinha interna ao longo da frente da folha
    mc = (bx + px) / 2 + nx * lw * 0.42, (by + py) / 2 + ny * lw * 0.42
    d.ellipse([mc[0] - lw * 0.34, mc[1] - lw * 0.22,
               mc[0] + lw * 0.34, mc[1] + lw * 0.22],
              fill=(*luz, 110))


def _grano_papel(img, rng, forca=26, fibras=220):
    """Grunido de papel/canvas por cima da obra inteira: ruído fino +
    fibras de papel levemente alongadas. É o que tira o "aspecto digital"
    e dá cara de pintura (o pigmento assenta no grão do papel)."""
    import numpy as np
    w, h = img.size
    rs = np.random.RandomState(abs(rng.randint(0, 2 ** 31)))
    tile = rs.normal(0, 9, (256, 256)).astype(np.float32)
    ruido = np.asarray(Image.fromarray(
        (tile * 255 / 20).clip(-128, 128) + 128).convert("L")
        .resize((w, h), Image.BILINEAR)).astype(np.float32)
    # satura/escurece alternando: granulado de pigmento
    arr = np.asarray(img).astype(np.float32)
    forde = forca / 255.0
    arr += (ruido[..., None] - 128) * forde * 0.55
    # fibras do papel: poeira alongada clara (+1) e escura (-1)
    fib = rs.normal(0, 16, (h, w)).astype(np.float32) / 2
    arr += fib[..., None] * 0.5 * forde * 0.4
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    img2 = Image.fromarray(arr, "RGB" if img.mode == "RGB" else "RGBA")
    img.paste(img2, (0, 0))


def _borda_umida(mask, cor, rng, larg=5, alpha=70):
    """Borda 'úmida' da aguada: anel escuro onde o pigmento seca molhado
    (backwater edge) — um dos sinais mais reconhecíveis de aquarela.

    A erosão usa `scipy.ndimage.minimum_filter` quando disponível: é a mesma
    conta que o `ImageFilter.MinFilter` do PIL (mode 'nearest' = preenchimento
    de borda do PIL, verificado pixel a pixel), mas com implementação
    separável em C. No PIL, um MinFilter(13) sobre a tela de 26 MP da obra
    levava ~3 s e era sozinho ~75% dos 105 s de uma pintura.
    """
    sz = max(3, int(larg * 2) | 1)
    try:
        if _minimum_filter is not None:
            arr = np.asarray(mask)
            ero = _minimum_filter(arr, size=sz, mode="nearest")
            bord = Image.fromarray(np.clip(
                arr.astype(np.int16) - ero.astype(np.int16),
                0, 255).astype(np.uint8))
        else:
            bord = ImageChops.subtract(mask, mask.filter(
                ImageFilter.MinFilter(sz)))
        bord = bord.filter(ImageFilter.GaussianBlur(1.0))
        if not bord.getbbox():
            return None
    except Exception:
        return None
    c3 = cor[:3]
    r, g, b = int(c3[0] * 0.82), int(c3[1] * 0.82), int(c3[2] * 0.82)
    lay = _layer(mask.size)
    m = Image.new("L", mask.size, 255)
    m.putalpha(ImageChops.multiply(bord, m))
    lay.paste(Image.new("RGBA", mask.size, (r, g, b, alpha)), (0, 0), m)
    return lay



# ══════════════════════════════════════════════════════════════════════
#  RECICLÁVEIS (carregar assets gerados)
# ══════════════════════════════════════════════════════════════════════

_CACHE_REC = {}


def _carregar_recilaveis():
    if _CACHE_REC:
        return _CACHE_REC
    for f in sorted(os.listdir(DIR_REC)) if os.path.isdir(DIR_REC) else []:
        if f.endswith(".png"):
            try:
                im = Image.open(os.path.join(DIR_REC, f)).convert("RGBA")
                _CACHE_REC[f[:-4]] = im
            except Exception:
                pass
    return _CACHE_REC


def _afixar_reciclavel(img, asset, cx, cy, escala=1.0, ang=None, rng=None):
    """Cola um asset reciclável sobre img centrado em (cx, cy)."""
    if asset not in _CACHE_REC:
        return
    rng = rng or random
    im = _CACHE_REC[asset]
    w, h = im.size
    nw, nh = int(w * escala), int(h * escala)
    im = im.resize((nw, nh), Image.LANCZOS)
    if ang is None:
        ang = rng.uniform(-25, 25)
    if ang:
        im = im.rotate(ang, expand=True, resample=Image.BICUBIC)
    x = int(cx - im.width / 2)
    y = int(cy - im.height / 2)
    img.paste(im, (x, y), im)


def _moldura_reciclavel(img, W, H, rng):
    """Moldura completa: faixa de papelão + recicláveis colados nas bordas."""
    _CACHE_REC and None
    b = 46
    ov = _layer(img.size)
    d = ImageDraw.Draw(ov)
    d.rectangle([0, 0, W, b], fill=(*PAPELAO, 255))
    d.rectangle([0, H - b, W, H], fill=(*PAPELAO, 255))
    d.rectangle([0, 0, b, H], fill=(*PAPELAO, 255))
    d.rectangle([W - b, 0, W, H], fill=(*PAPELAO, 255))
    # faixa interna (fita/hastes)
    d.rectangle([b - 8, 0, b, H], fill=(*PAPEL_KRAFT_ESC, 255))
    d.rectangle([W - b, 0, W - b + 8, H], fill=(*PAPEL_KRAFT_ESC, 255))
    d.rectangle([0, b - 8, W, b], fill=(*PAPEL_KRAFT_ESC, 255))
    d.rectangle([0, H - b, W, H - b + 8], fill=(*PAPEL_KRAFT_ESC, 255))
    _blit(img, ov)

    # recicláveis colados ao longo das bordas (nas faixas laterais)
    items = ["lata-aluminio", "lata-aluminio-2", "garrafa-vidro-verde",
             "garrafa-vidro-ambar", "saco-plastico", "caixa-longa-vida"]
    # cantos: latinhas/garrafas
    _afixar_reciclavel(img, "lata-aluminio", b // 2 + 10, H - b // 2 - 20,
                       escala=0.12, ang=20, rng=rng)
    _afixar_reciclavel(img, "lata-aluminio-2", W - b // 2 - 10, b // 2 + 20,
                       escala=0.12, ang=-15, rng=rng)
    _afixar_reciclavel(img, "garrafa-vidro-verde", W - b // 2 - 6, b + 40,
                       escala=0.09, ang=8, rng=rng)
    _afixar_reciclavel(img, "garrafa-vidro-ambar", b // 2 + 6, H - b - 60,
                       escala=0.09, ang=-10, rng=rng)
    # papéis/jornal colados nas faixas laterais
    for i in range(4):
        yy = b + 90 + i * (H - 2 * b) / 4
        _afixar_reciclavel(img, "jornal", b + 24, yy, escala=0.10,
                           ang=rng.uniform(-8, 8), rng=rng)
        _afixar_reciclavel(img, "recorte-papel", W - b - 24, yy + 60,
                           escala=0.10, ang=rng.uniform(-8, 8), rng=rng)


# ══════════════════════════════════════════════════════════════════════
#  DESENHOS PROCEDURAIS DOS ARQUÉTIPOS
# ══════════════════════════════════════════════════════════════════════

def _hachura(d, cx, cy, qx, qy, cor, passo, rng, anglo=0.7):
    """Preenche a elipse (metade maior qx, metade menor qy) com hachuras
    paralelas à mão — efeito 'tinta' em vez de cor chapada."""
    n = int(qy * 2 / passo)
    import math as _m
    s, c = _m.sin(anglo), _m.cos(anglo)
    for i in range(-(n // 2), (n // 2) + 1):
        y = cy + i * passo
        defx = _m.sqrt(max(0.0, 1 - ((y - cy) / qy) ** 2)) * qx
        x0, x1 = cx - defx, cx + defx
        # rotação rígida (aproxima hachura inclinada)
        ox = (x0 - cx) * c - (y - cy) * s
        oy = (x0 - cx) * s + (y - cy) * c
        ox2 = (x1 - cx) * c - (y - cy) * s
        oy2 = (x1 - cx) * s + (y - cy) * c
        _linha_mao(d, (cx + ox, cy + oy), (cx + ox2, cy + oy2), cor, 1, rng,
                   jitter=0.7, passos=8)


def _elipse_tinta(d, cx, cy, qx, qy, cor, lw, rng, hatch=None):
    """Contorno de elipse à mão + hachura ('tinta') no interior."""
    import math as _m
    esc = (52, 44, 32)
    pts = []
    for i in range(48):
        a = _m.radians(i * 7.5)
        rx = qx + rng.uniform(-0.8, 0.8)
        ry = qy + rng.uniform(-0.8, 0.8)
        pts.append((cx + rx * _m.cos(a), cy + ry * _m.sin(a)))
    for i in range(48):
        j = (i + 1) % 48
        d.line([pts[i], pts[j]], fill=cor, width=lw)
    if hatch:
        _hachura(d, cx, cy, qx * 0.86, qy * 0.86, hatch, max(2, int(qy / 7)),
                 rng)


def _desenhar_arquétipo(d, cx, cy, r, nome, cor, rng):
    """Desenha a figura do arquétipo (fallback quando não há imagem PD).

    Estilo 'tinta': contornos ondulados + hachuras + textura, menos chapado.
    """
    c = _sem_acentos(nome)
    q = r * 0.72
    base = cor
    tinta = (52, 44, 32)
    lw = max(2, int(r * 0.06))

    if c == "omolu" or "obaluai" in c:
        # palha de Omolu: feixes de canudos inclinados (traços), não blocos
        for i in range(-3, 4):
            x0 = cx + i * q * 0.16
            x1 = cx + i * q * 0.30
            _linha_mao(d, (x0, cy - q * 0.55), (x1 - i * 2, cy + q * 0.72),
                       base, 1, rng, jitter=1.5, passos=8)
        _elipse_tinta(d, cx, cy - q * 0.40, q * 0.26, q * 0.22, tinta, lw, rng,
                      hatch=tinta)
        _elipse_tinta(d, cx, cy + q * 0.42, q * 0.42, q * 0.26, tinta, lw, rng,
                      hatch=tinta)

    elif "boitata" in c:
        # cobra de fogo enrolada: traço sinuoso com escamas + olhos
        _elipse_tinta(d, cx, cy, q*0.62, q*0.62, (14, 12, 16), lw, rng)
        pts = []
        for t in range(0, 49):
            x = cx - q * 0.5 + (q) * t / 48
            y = cy + math.sin(t * 1.15) * q * 0.5
            pts.append((x, y))
        for i in range(1, len(pts)):
            _linha_mao(d, pts[i - 1], pts[i], base, lw, rng, jitter=1.0,
                       passos=5)
            if i % 3 == 0:
                fx, fy = pts[i]
                cr = rng.uniform(2, 5)
                d.ellipse([fx - cr, fy - cr, fx + cr, fy + cr],
                          fill=(255, 190, 60))
        # olhos de fogo acesos
        for ex, ey in [(-q*0.2, -q*0.34), (q*0.05, -q*0.34)]:
            d.ellipse([cx+ex, cy+ey, cx+ex+q*0.12, cy+ey+q*0.12],
                      fill=(255, 230, 120))
        for ex, ey in [(-q*0.18, -q*0.33), (q*0.07, -q*0.33)]:
            d.ellipse([cx+ex, cy+ey, cx+ex+q*0.04, cy+ey+q*0.04],
                      fill=(255, 250, 200))

    elif "curupira" in c:
        # corpo + cabeça com hachura, membros com pés para trás (traço)
        _elipse_tinta(d, cx, cy - q*0.52, q*0.30, q*0.24, tinta, lw, rng,
                      hatch=tinta)
        _elipse_tinta(d, cx, cy + q*0.06, q*0.42, q*0.34, tinta, lw, rng,
                      hatch=tinta)
        for s in (-1, 1):
            _linha_mao(d, (cx, cy + q*0.32), (cx + s*q*0.15, cy + q*0.75),
                       base, lw, rng, jitter=1.4, passos=8)
            _linha_mao(d, (cx + s*q*0.15, cy + q*0.75),
                       (cx - s*q*0.42, cy + q*0.72), base, lw, rng,
                       jitter=1.4, passos=8)  # pés voltados p/ trás

    elif c == "exu":
        # tridente com hachura na haste e base
        _elipse_tinta(d, cx, cy - q*0.40, q*0.32, q*0.24, tinta, lw, rng,
                      hatch=tinta)
        _elipse_tinta(d, cx, cy + q*0.18, q*0.22, q*0.36, tinta, lw, rng,
                      hatch=tinta)
        for i in (-1, 0, 1):
            _linha_mao(d, (cx + i*q*0.12, cy - q*0.52),
                       (cx + i*q*0.18, cy - q*0.95), base, lw, rng, jitter=1.3,
                       passos=8)

    elif "iemanja" in c or "yemanja" in c:
        # ondas do mar com traços, concha/estrela ao centro (mais livre)
        for i in range(6):
            yy = cy - q*0.3 + i * q * 0.16
            _arco_mao(d, cx, yy, q * 0.9, 0, 180, base, lw, rng)
        # rosto/concha ao meio (pequeno arco claro)
        d.arc([cx - q*0.35, cy - q*0.55, cx + q*0.35, cy + q*0.25],
              start=200, end=340, fill=(238, 224, 208), width=lw + 2)

    elif "osanyin" in c or "ossanha" in c:
        # opa (bastão de Osanyin) com ave empoleirada (traço)
        _linha_mao(d, (cx, cy - q*0.5), (cx, cy + q*0.85), tinta, lw, rng,
                   jitter=1.4, passos=12)
        _elipse_tinta(d, cx, cy - q*0.4, q*0.3, q*0.24, tinta, lw, rng,
                      hatch=tinta)
        _linha_mao(d, (cx, cy - q*0.55), (cx + q*0.5, cy - q*0.8), base, lw,
                   rng, jitter=1.3, passos=6)
        d.polygon([(cx + q*0.4, cy - q*0.85), (cx + q*0.62, cy - q*0.6),
                   (cx + q*0.3, cy - q*0.58)], fill=base)  # bico

    elif "anta" in c or "tapi" in c:
        # Anta (Tapi'i, constelação tupi do céu do sul): corpo, cabeça com
        # focinho característico, pernas e orelhas — traço de tinta + hachura
        _elipse_tinta(d, cx, cy + q*0.10, q*0.52, q*0.30, tinta, lw, rng,
                      hatch=(*base[:3], 120))
        # cabeça baixa com focinho esticado (para o lado)
        _elipse_tinta(d, cx + q*0.30, cy - q*0.18, q*0.26, q*0.22, tinta, lw,
                      rng, hatch=(*base[:3], 120))
        _linha_mao(d, (cx + q*0.44, cy - q*0.12), (cx + q*0.92, cy - q*0.02),
                   base, lw, rng, jitter=1.4, passos=8)
        # pernas
        for sx in (-0.4, -0.1, 0.2, 0.42):
            _linha_mao(d, (cx + sx*q, cy + q*0.28),
                       (cx + sx*q, cy + q*0.72), tinta, lw, rng, jitter=1.3,
                       passos=6)
        # orelhas
        for sx in (0.18, 0.28):
            _linha_mao(d, (cx + sx*q, cy - q*0.30),
                       (cx + sx*q, cy - q*0.52), tinta, lw, rng, jitter=1.2,
                       passos=5)

    elif "veado" in c or "cervo" in c or "wynelfe" in c or "wunellfe" in c:
        # Veado (Vênus/Estrela d'Alva): galhada + cabeça + corço — traço
        _elipse_tinta(d, cx, cy + q * 0.14, q * 0.38, q * 0.26, tinta, lw, rng,
                      hatch=(*base[:3], 130))
        _elipse_tinta(d, cx, cy - q * 0.20, q * 0.24, q * 0.20, tinta, lw, rng,
                      hatch=(*base[:3], 130))
        for sd in (-1, 1):
            _linha_mao(d, (cx + sd * q * 0.14, cy - q * 0.30),
                       (cx + sd * q * 0.42, cy - q * 0.72), base, lw, rng,
                       jitter=1.4, passos=8)
            _linha_mao(d, (cx + sd * q * 0.30, cy - q * 0.62),
                       (cx + sd * q * 0.10, cy - q * 0.80), base, lw, rng,
                       jitter=1.4, passos=6)

    elif "gaviao" in c or "gavião" in c or "aguia" in c:
        # Gavião/Águia (Sagitário): asas abertas + cabeça com bico
        _elipse_tinta(d, cx, cy - q * 0.28, q * 0.26, q * 0.22, tinta, lw, rng,
                      hatch=(*base[:3], 130))
        _linha_mao(d, (cx + q * 0.2, cy - q * 0.34),
                   (cx + q * 0.72, cy - q * 0.78), base, lw, rng, jitter=1.3,
                   passos=8)
        _linha_mao(d, (cx - q * 0.2, cy - q * 0.34),
                   (cx - q * 0.72, cy - q * 0.78), base, lw, rng, jitter=1.3,
                   passos=8)
        _linha_mao(d, (cx + q * 0.12, cy + q * 0.30),
                   (cx + q * 0.82, cy + q * 0.62), base, lw, rng, jitter=1.3,
                   passos=8)
        _linha_mao(d, (cx - q * 0.12, cy + q * 0.30),
                   (cx - q * 0.82, cy + q * 0.62), base, lw, rng, jitter=1.3,
                   passos=8)
        # bico
        d.polygon([(cx - q * 0.08, cy - q * 0.34), (cx + q * 0.32, cy - q * 0.26),
                   (cx - q * 0.04, cy - q * 0.16)], fill=base)

    elif "tatu" in c or "boi" in c or "trarinmansun" in c:
        # Tatu/Boi (Touro): casco/armadura curva com traços
        _elipse_tinta(d, cx, cy, q * 0.60, q * 0.40, tinta, lw, rng,
                      hatch=(*base[:3], 140))
        _linha_mao(d, (cx - q * 0.55, cy - q * 0.12),
                   (cx + q * 0.55, cy - q * 0.12), base, lw, rng, jitter=1.2,
                   passos=8)
        _linha_mao(d, (cx - q * 0.42, cy + q * 0.28),
                   (cx - q * 0.42, cy + q * 0.70), tinta, lw, rng, jitter=1.2,
                   passos=6)
        _linha_mao(d, (cx + q * 0.42, cy + q * 0.28),
                   (cx + q * 0.42, cy + q * 0.70), tinta, lw, rng, jitter=1.2,
                   passos=6)

    elif "homem velho" in c or "anam" in c or "velho" in c or "wetripantu" in c:
        # Homem Velho (Saturno): figura curvada com bastão, hachura
        _elipse_tinta(d, cx, cy - q * 0.40, q * 0.24, q * 0.22, tinta, lw, rng,
                      hatch=tinta)
        _elipse_tinta(d, cx, cy + q * 0.02, q * 0.34, q * 0.36, tinta, lw, rng,
                      hatch=tinta)
        _linha_mao(d, (cx, cy - q * 0.22), (cx, cy + q * 0.40), tinta, lw, rng,
                   jitter=1.4, passos=8)
        _linha_mao(d, (cx, cy + q * 0.36), (cx + q * 0.52, cy + q * 0.90),
                   base, lw, rng, jitter=1.3, passos=8)
        _linha_mao(d, (cx + q * 0.15, cy - q * 0.10),
                   (cx + q * 0.55, cy - q * 0.48), base, lw, rng, jitter=1.3,
                   passos=8)  # bastão

    elif "ianduti" in c or "teia" in c or "aranha" in c or "aranha-do-ceu" in c:
        # Iandutí (aranha-do-céu / teia): teia radial + aranhinha
        for i in range(8):
            a = math.radians(i * 45)
            _linha_mao(d, (cx, cy), (cx + q * 0.9 * math.cos(a),
                                     cy + q * 0.9 * math.sin(a)),
                       (172, 150, 110), max(1, lw - 1), rng, jitter=0.8,
                       passos=5)
        for k in range(1, 4):
            rr = q * 0.3 * k
            for i in range(16):
                a0 = math.radians(i * 22.5)
                a1 = math.radians((i + 1) * 22.5)
                p0 = (cx + rr * math.cos(a0), cy + rr * math.sin(a0))
                p1 = (cx + rr * math.cos(a1), cy + rr * math.sin(a1))
                _linha_mao(d, p0, p1, (172, 150, 110), 1, rng, jitter=0.8,
                           passos=3)
        _elipse_tinta(d, cx, cy, q * 0.16, q * 0.16, tinta, lw, rng, hatch=None)
        for sd in (-1, 1):
            _linha_mao(d, (cx, cy), (cx + sd * q * 0.3, cy + q * 0.24), base,
                       lw, rng, jitter=1.0, passos=4)

    elif "melipal" in c or "escada" in c or "quadrado" in c or "quatro" in c:
        # Melipal (ursa/quatro de Escorpião): losango/quadrado de quatro
        pts = [(-0.55, -0.45), (0.55, -0.40), (0.50, 0.50), (-0.50, 0.45)]
        for i in range(4):
            x0 = cx + pts[i][0] * q
            y0 = cy + pts[i][1] * q
            x1 = cx + pts[(i + 1) % 4][0] * q
            y1 = cy + pts[(i + 1) % 4][1] * q
            _linha_mao(d, (x0, y0), (x1, y1), base, lw, rng, jitter=1.3,
                       passos=6)
        _elipse_tinta(d, cx, cy, q * 0.14, q * 0.14, tinta, lw, rng, hatch=None)

    elif "onca" in c or "jaguara" in c or "jaguar" in c or "onça" in c:
        # Onça/Jaguará: corpo + cabeça manchada com traço
        _elipse_tinta(d, cx, cy + q * 0.1, q * 0.5, q * 0.28, tinta, lw, rng,
                      hatch=(*base[:3], 130))
        _elipse_tinta(d, cx + q * 0.34, cy - q * 0.16, q * 0.24, q * 0.2, tinta,
                      lw, rng, hatch=(*base[:3], 130))
        for sd in (-1, 1):
            _linha_mao(d, (cx + sd * q * 0.2, cy + q * 0.28),
                       (cx + sd * q * 0.28, cy + q * 0.7), tinta, lw, rng,
                       jitter=1.3, passos=6)
        for mxy in [(0.2, -0.2), (-0.18, -0.05), (0.1, 0.2), (-0.1, -0.3)]:
            mx_, my_ = cx + mxy[0] * q, cy + mxy[1] * q
            d.ellipse([mx_ - 4, my_ - 4, mx_ + 4, my_ + 4], fill=(0, 0, 0))

    elif "cuca" in c or "lobisomem" in c or "corpo-seco" in c or "tutu" in c:
        # Cuca/lobisomem (assombração): boca/janela + olhos acesos
        _elipse_tinta(d, cx, cy, q * 0.6, q * 0.55, tinta, lw, rng,
                      hatch=tinta)
        for sd in (-1, 1):
            _linha_mao(d, (cx + sd * q * 0.1, cy - q * 0.2),
                       (cx + sd * q * 0.42, cy - q * 0.55), base, lw, rng,
                       jitter=1.3, passos=6)
            _linha_mao(d, (cx + sd * q * 0.1, cy + q * 0.2),
                       (cx + sd * q * 0.42, cy + q * 0.55), base, lw, rng,
                       jitter=1.3, passos=6)
        d.ellipse([cx - q * 0.16, cy - q * 0.2, cx - q * 0.04, cy - q * 0.08],
                  fill=(255, 210, 90))
        d.ellipse([cx + q * 0.04, cy - q * 0.2, cx + q * 0.16, cy - q * 0.08],
                  fill=(255, 210, 90))
        d.ellipse([cx - q * 0.22, cy + q * 0.22, cx + q * 0.22, cy + q * 0.5],
                  fill=(90, 20, 20))

    elif "flecha" in c or "arqueiro" in c or "seta" in c:
        # Flecha (A Flecha que guarda a região do Escorpião, Sol do usuário):
        # haste com pena, ponta e arco
        _linha_mao(d, (cx - q * 0.5, cy + q * 0.28),
                   (cx + q * 0.72, cy - q * 0.52), base, lw, rng, jitter=1.2,
                   passos=10)
        _linha_mao(d, (cx + q * 0.62, cy - q * 0.6), (cx + q * 0.8, cy - q * 0.4),
                   base, lw, rng, jitter=0.8, passos=4)  # ponta
        _linha_mao(d, (cx - q * 0.45, cy + q * 0.22), (cx - q * 0.2, cy + q * 0.5),
                   (196, 140, 60), max(1, lw - 1), rng, jitter=1.0, passos=5)
        _linha_mao(d, (cx - q * 0.4, cy + q * 0.4), (cx - q * 0.1, cy + q * 0.34),
                   (196, 140, 60), max(1, lw - 1), rng, jitter=1.0, passos=5)

    else:
        # emblema genérico VARIÁVEL por semente do nome (evita a estrela
        # repetida); a forma vem do hash do nome, então cada arquétipo sem
        # imagem tem a SUA forma — escala e traço também variam por nome
        semente = abs(zlib.crc32(_sem_acentos(nome).encode("utf-8"))) % 12
        s2 = abs(zlib.crc32((_sem_acentos(nome) + "·tinta").encode("utf-8")))
        q = q * (0.86 + (s2 % 100) / 260.0)
        lw = max(2, int(lw * (0.9 + (s2 % 31) / 93.0)))
        semente = (semente + (s2 // 7) % 12) % 12
        if semente == 0:
            # estrela de 5 pontas
            pts = []
            for i in range(10):
                ang = math.radians(-90 + i * 36)
                rr = q * (0.7 if i % 2 == 0 else 0.42)
                pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
            for i in range(10):
                j = (i + 1) % 10
                _linha_mao(d, pts[i], pts[j], base, lw, rng, jitter=1.1, passos=6)
        elif semente == 1:
            # sol com raios (astro)
            _elipse_tinta(d, cx, cy, q * 0.5, q * 0.5, base, lw, rng,
                          hatch=base)
            for i in range(12):
                a = math.radians(i * 30)
                p0 = (cx + q * 0.42 * math.cos(a), cy + q * 0.42 * math.sin(a))
                p1 = (cx + q * 0.85 * math.cos(a), cy + q * 0.85 * math.sin(a))
                _linha_mao(d, p0, p1, base, max(1, lw - 1), rng, jitter=0.9,
                           passos=4)
        elif semente == 2:
            # losango/ferrão (em retro) emoldurado
            pts = [(0, -0.85), (0.5, 0), (0, 0.85), (-0.5, 0)]
            for i in range(4):
                x0 = cx + pts[i][0] * q
                y0 = cy + pts[i][1] * q
                x1 = cx + pts[(i + 1) % 4][0] * q
                y1 = cy + pts[(i + 1) % 4][1] * q
                _linha_mao(d, (x0, y0), (x1, y1), base, lw, rng, jitter=1.2,
                           passos=6)
            _linha_mao(d, (cx, cy - q * 0.85), (cx, cy + q * 0.85), base,
                       max(1, lw - 1), rng, jitter=1.0, passos=6)
        elif semente == 3:
            # estrela de 6 pontas (duas espirais contornadas)
            for i in range(6):
                a = math.radians(i * 60)
                p0 = (cx + q * 0.28 * math.cos(a), cy + q * 0.28 * math.sin(a))
                p1 = (cx + q * 0.92 * math.cos(a), cy + q * 0.92 * math.sin(a))
                _linha_mao(d, p0, p1, base, lw, rng, jitter=1.2, passos=6)
                p0b = (cx + q * 0.92 * math.cos(a + math.radians(30)),
                       cy + q * 0.92 * math.sin(a + math.radians(30)))
                _linha_mao(d, p1, p0b, base, lw - 1, rng, jitter=1.0, passos=4)
            _elipse_tinta(d, cx, cy, q * 0.18, q * 0.18, tinta, lw, rng,
                          hatch=None)
        elif semente == 4:
            # flor: 8 pétalas de contorno ondulado + centro
            for i in range(8):
                a = math.radians(i * 45)
                _elipse_tinta(d, cx + q * 0.52 * math.cos(a),
                              cy + q * 0.52 * math.sin(a),
                              q * 0.24, q * 0.36, tinta, max(1, lw - 1), rng)
            _elipse_tinta(d, cx, cy, q * 0.22, q * 0.22, base, lw, rng,
                          hatch=base)
        elif semente == 5:
            # montanha com sol nascente (linhas de horizonte)
            pts = [(-0.9, 0.55), (-0.45, -0.2), (0.0, 0.5), (0.45, -0.35),
                   (0.9, 0.55)]
            for i in range(4):
                x0 = cx + pts[i][0] * q
                y0 = cy + pts[i][1] * q
                x1 = cx + pts[(i + 1) % 5][0] * q
                y1 = cy + pts[(i + 1) % 5][1] * q
                _linha_mao(d, (x0, y0), (x1, y1), base, lw, rng, jitter=1.3,
                           passos=6)
            d.arc([cx - q * 0.4, cy - q * 0.55, cx + q * 0.05, cy - q * 0.1],
                  start=0, end=180, fill=base, width=lw + 1)
            _linha_mao(d, (cx - q * 0.7, cy + q * 0.7),
                       (cx + q * 0.7, cy + q * 0.7), tinta, 1, rng, jitter=1.0,
                       passos=10)
        elif semente == 6:
            # ondas do mar (3 arcos sobrepostos + gota)
            for i in range(3):
                _arco_mao(d, cx, cy + q * 0.3 + i * q * 0.18, q * 0.75 - i * 6,
                          0, 180, base, max(1, lw - 1), rng, n=20)
            d.ellipse([cx - q * 0.12, cy - q * 0.55, cx + q * 0.12,
                       cy - q * 0.31], outline=base, width=lw)
        elif semente == 7:
            # lua crescente (dois arcos concêntricos deslocados)
            d.arc([cx - q * 0.5, cy - q * 0.5, cx + q * 0.5, cy + q * 0.5],
                  start=-90, end=90, fill=base, width=lw + 1)
            d.arc([cx - q * 0.2, cy - q * 0.55, cx + q * 0.55, cy + q * 0.45],
                  start=-90, end=90, fill=(238, 224, 200), width=lw)
            _linha_mao(d, (cx + q * 0.1, cy + q * 0.5), (cx + q * 0.1, cy + q * 0.7),
                       tinta, 1, rng, jitter=1.0, passos=4)
        elif semente == 8:
            # mão/pata estendida: 4 dedos e palma
            for i in range(4):
                px = cx - q * 0.24 + i * q * 0.16
                _linha_mao(d, (px, cy + q * 0.35), (px, cy - q * 0.5), base,
                           lw, rng, jitter=1.4, passos=7)
            _elipse_tinta(d, cx, cy + q * 0.35, q * 0.34, q * 0.26, tinta, lw,
                          rng, hatch=base)
        elif semente == 9:
            # triângulo/vulcão com forro interno
            pts = [(0, -0.85), (0.72, 0.8), (-0.72, 0.8)]
            for i in range(3):
                x0 = cx + pts[i][0] * q
                y0 = cy + pts[i][1] * q
                x1 = cx + pts[(i + 1) % 3][0] * q
                y1 = cy + pts[(i + 1) % 3][1] * q
                _linha_mao(d, (x0, y0), (x1, y1), base, lw, rng, jitter=1.2,
                           passos=6)
            _hachura(d, cx, cy + q * 0.25, q * 0.4, q * 0.35, tinta,
                     max(2, int(q / 8)), rng, anglo=0.5)
        else:
            # nós/trança entrelaçada: curva em S com entrelaçamentos
            pts = []
            for t in range(0, 20):
                a = math.radians(t * 18)
                x = cx + q * 0.8 * math.cos(a)
                y = cy + q * 0.35 * math.sin(a * 1.4)
                pts.append((x, y))
            for i in range(1, len(pts)):
                _linha_mao(d, pts[i - 1], pts[i], base, lw, rng, jitter=1.2,
                           passos=4)
            for i in range(1, len(pts) - 3, 3):
                _linha_mao(d, pts[i], (cx, cy), base, max(1, lw - 1), rng,
                           jitter=1.0, passos=4)


# ── arte feita de CARACTERES (letterpress/tipografia popular) ───────────────
# Cada arquétipo vira uma gravura tipográfica: a silhueta (foto de domínio
# público OU o desenho procedural) é convertida em uma rede de caracteres,
# onde a densidade dos glifos produz as sombras — como os velhos cartazes
# impressos com tipos de madeira.

_CHAR_RAMP = "·:;+=*%#@W$"  # do mais vazio ao mais cheio (densidade)

# Semente do mapa atual. Uma lista de um elemento só porque `gerar_obra` a
# preenche; a figura sorteada para cada arquétipo precisa da data/hora/nome de
# quem está nascendo, e `_silhueta_arquetipo` não tem acesso ao formulário.
_SEMENTE_MAPA = [""]


def _glyph_fonte(size):
    try:
        return ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", size)
    except Exception:
        return _font(size, True)


def _silhueta_arquetipo(nome, lado, rng, variante=None):
    """Fonte em tons de cinza (lado×lado) com a figura do arquétipo.

    Usa a imagem de domínio público quando há — uma de 12 variantes
    (3 enquadramentos × 4 tratamentos de tinta, em `figuras_arquetipo`), para
    que duas pessoas com o mesmo signo nunca vejam a mesma figura. Sem
    `variante`, sorteia-se uma. Senão bora o desenho procedural.
    """
    im = Image.new("L", (lado, lado), 255)
    # 1) tenta a figura PD (retrato 'de verdade'), em uma das 12 variantes
    try:
        import figuras_arquetipo as FA
        if _arq_figura(nome):
            v = variante
            if v is None:
                v = FA.indice_para_o_mapa(nome, _SEMENTE_MAPA[0], rng)
            m = FA.mascarar(nome, lado, int(v) % FA.N_VARIANTES, _arq_figura)
            if m is not None:
                # `mascarar` devolve tinta em BRANCO (255). Todos os
                # consumidores daqui esperam o contrário — a chapa de antes,
                # figura escura em fundo claro — e invertem com `255 - x`.
                # Devolver o branco como tinta fazia `_arte_medalhao` pintar
                # o fundo e apagar a figura: os 4 tratamentos davam a mesma
                # imagem. Inverte aqui, uma vez só.
                a = 255 - np.asarray(m)
                return Image.fromarray(a.astype(np.uint8))
    except Exception:
        pass
    # 2) senão: silhueta do desenho procedural (máscara de tinta)
    ov = _layer((lado, lado))
    od = ImageDraw.Draw(ov)
    lw_proc = max(2, int(lado * 0.05))
    _desenhar_arquétipo(od, lado // 2, lado // 2, int(lado * 0.44),
                        nome, (0, 0, 0, 255), rng)
    arr = np.asarray(ov)[..., 3] > 28  # onde há tinta
    a = 255 * (1 - arr).astype(np.uint8)  # figura escura, fundo claro
    a = a.astype(np.float32)
    a = cv2_blurry(a, lado // 10)  # borra p/ carácter bem posto
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def cv2_blurry(a, k):
    try:
        return np.asarray(Image.fromarray(a.astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(max(1, k))))
    except Exception:
        return a


def _arte_caracteres(img, cx, cy, r, nome, cor, rng):
    """Gravura tipográfica do arquétipo dentro do medalhão: caracteres de
    densidade formam a figura; cada medalhão tem seu próprio punção."""
    lado = int(r * 2)
    N = max(18, min(30, lado // 7))  # linhas de caracteres (~célula de 7px)
    fonte_g = _silhueta_arquetipo(nome, lado, rng)
    grade = np.asarray(fonte_g.resize((N, N), Image.BILINEAR)).astype(np.float32)
    cel = lado / N
    ink = cor[:3] if len(cor) >= 3 else (240, 220, 170)
    pilha = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    pd2 = ImageDraw.Draw(pilha)
    fmono = _glyph_fonte(max(int(cel * 1.18), 6))
    bb = fmono.getbbox("W#@")
    char_w = (bb[2] - bb[0]) if bb else int(cel)
    # inclina levemente cada linha (composição popular, não-régua)
    for y in range(N):
        linha = ""
        for x in range(N):
            sombra = grade[y, x]
            dens = (255 - sombra) / 255.0  # 1 = tinta cheia
            dens = max(0.0, min(0.86, dens + rng.uniform(-0.05, 0.05)))
            if dens < 0.14:
                linha += " "
                continue
            i = int(dens * (len(_CHAR_RAMP) - 1) + 0.5)
            i = min(len(_CHAR_RAMP) - 1, max(0, i))
            linha += _CHAR_RAMP[i]
        lx = (lado - len(linha) * char_w) / 2
        pd2.text((lx, y * cel + rng.uniform(-1.5, 1.5)), linha, font=fmono,
                 fill=(*ink, 255), anchor="lm")
    # envelhece: borra miolo de alguns glifos (tinta seca) e cola
    pilha = pilha.filter(ImageFilter.GaussianBlur(0.3))
    img.paste(pilha, (int(cx - lado / 2), int(cy - lado / 2)), pilha)
    # leve realce: poucos pontos de tinta por fora (respingo do punção)
    for _ in range(4):
        a_ = rng.uniform(0, 2 * math.pi)
        ra_ = rng.uniform(0, r * 0.9)
        xp = cx + ra_ * math.cos(a_)
        yp = cy + ra_ * math.sin(a_) * 0.82
        d_tmp = ImageDraw.Draw(img)
        d_tmp.ellipse([xp - 2, yp - 2, xp + 2, yp + 2],
                      fill=(*ink, rng.randint(90, 160)))


def _arte_medalhao(img, cx, cy, r, nome, rng):
    """FIGURA limpa dentro do medalhão (imagem PD ou silhueta procedural em
    tinta escura aveludada) — nada de ASCII/código. Escurece o miolo p/ a
    figura parecer gravada no papel claro."""
    lado = int(r * 2)
    sil = _silhueta_arquetipo(nome, lado, rng)
    # isola o desenho (vale escuro) e usa como carimbo de tinta
    arr = np.asarray(sil).astype(np.float32)
    masc = Image.fromarray(np.clip(255 - arr, 0, 255).astype(np.uint8)).convert("L")
    masc = masc.filter(ImageFilter.GaussianBlur(1.1))
    pilha = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    pilha.paste((52, 42, 30, 235), (0, 0), masc)
    img.paste(pilha, (int(cx - lado / 2), int(cy - lado / 2)), pilha)


def _arco_mao(d, cx, cy, rx, a0, a1, cor, lw, rng, n=24):
    """Arco ondulado à mão (para ondas de Iemanjá e ornamentos)."""
    import math as _m
    for i in range(n):
        a = _m.radians(a0 + (a1 - a0) * i / n)
        a2 = _m.radians(a0 + (a1 - a0) * (i + 1) / n)
        defx = rx + rng.uniform(-1.0, 1.0)
        p0 = (cx + defx * _m.cos(a), cy + defx * _m.sin(a))
        p1 = (cx + defx * _m.cos(a2), cy + defx * _m.sin(a2))
        d.line([p0, p1], fill=cor, width=lw)


# ══════════════════════════════════════════════════════════════════════
#  RODA ZODIACAL
# ══════════════════════════════════════════════════════════════════════

def _planeta_pos(m, cx, cy, nome, r_int, rng=None):
    """Posição do planeta na mandala, afastando concretamente planetas que
    caem no MESMO grau (conjunção), distribuindo-os em arco ao redor do grau
    para não ficarem 'embolados'."""
    lat = m.get("lat_mandala") or {}
    if nome in lat:
        return lat[nome]
    # sem dados extras, usa a posição simples
    pl = m["planetas"][nome]
    return _polar(cx, cy, r_int - 42, pl["lon"])


def _arte_ascii(img, cx, cy, rad, nome, rng):
    """Retrato do arquétipo em ASCII art clássico — sombras de caracteres
    comuns (·, :, =, *, %, @...) em vez de blocos sólidos █▀▄ que pareciam
    'caracteres estranhos'. Tinta escura sobre disco claro."""
    lado = max(28, int(rad * 2))
    sil = _silhueta_arquetipo(nome, lado, rng)
    arr = np.asarray(sil).astype(np.float32)
    h, w = arr.shape
    nc = max(14, int(rad * 0.52))          # caracteres na horizontal
    nlin = int(nc * 1.9)                   # linhas
    fmono = _glyph_fonte(max(8, int(2 * rad / nc * 2.0)))
    ink = (54, 42, 30, 255)
    ramp = _CHAR_RAMP
    ch_w = 2 * rad / nc
    ch_h = ch_w * 2.0 / 1.9
    ov = _layer(img.size)
    pd2 = ImageDraw.Draw(ov)
    for lin in range(nlin):
        yi = min(h - 1, int((lin + 0.5) * (h / nlin)))
        for col in range(nc):
            xi = min(w - 1, int((col + 0.5) * (w / nc)))
            s = (255.0 - arr[yi, xi]) / 255.0
            if s < 0.06:
                continue
            i = int(s * (len(ramp) - 1) + 0.5)
            i = min(len(ramp) - 1, max(0, i))
            x = cx + (col + 0.5 - nc / 2) * ch_w
            y = cy + (lin + 0.5 - nlin / 2) * ch_h
            pd2.text((x, y), ramp[i], font=fmono, fill=ink, anchor="mm")
    img.paste(ov, (0, 0), ov)


def _medalhao(d, img, cx, cy, rad, nome, cor, rng):
    """Medalhão colado à borda: placa CLARA de papel + gravura de caracteres
    (tinta escura) + aro colorido + rótulo. Leve de ler (xilogravura)."""
    d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(238, 224, 190))
    d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad],
              outline=(*cor, 255), width=4)
    # aguada leve de fundo (pinta o papel, sem esconder a figura)
    mar = Image.new("L", img.size, 0)
    ImageDraw.Draw(mar).ellipse([cx - rad + 2, cy - rad + 2,
                                 cx + rad - 2, cy + rad - 2], fill=255)
    _blit(img, _aguada(mar, cor, rng, tons=40, r0=4, r1=16, blur=4,
                       alpha=(14, 44)))
    ra = rad - 7
    nome_limpo = nome.split(" (")[0]
    # figura = carimbo de tinta (imagem PD ou silhueta procedural) sobre o
    # papel claro — sem ASCII, sem "código"
    _arte_medalhao(img, cx, cy, ra, nome_limpo, rng)
    nn = nome_limpo if len(nome_limpo) <= 14 else nome_limpo[:12] + "…"
    _texto_traco(d, (cx, cy + rad + 14), nn, _font(13, True),
                 fill=(250, 240, 210), contorno=(60, 48, 30), sw=2,
                 desloc=(1, 1), anchor="mm")


def _medalhoes_arquetipos(img, m, cx, cy, r_rime, rng, sol_signo, asc_signo,
                          arq_sol, arq_asc, arqs_planetas=None):
    """Costura os medalhões de arquétipo à beira da roda: o do Ascendente, o
    do Sol e, quando há nosso catálogo, os de TODOS os planetas — cada um na
    sua longitude, com separação angular para não colarem. Cada medalhão usa
    imagem PD (se houver) ou desenho procedural próprio (não repete a mesma
    estrela), fazendo 'sair junto da mandala' os arquétipos."""
    d = ImageDraw.Draw(img)
    pares = []  # (lon, nome, signo, cor)
    if arq_asc:
        lon = m["casas"][0]["lon"]
        pares.append((lon, arq_asc[0][1], asc_signo,
                      COR.get(asc_signo, (180, 140, 110))))
    if arq_sol:
        lon = m["planetas"]["Sol"]["lon"]
        pares.append((lon, arq_sol[0][1], sol_signo, COR_P["Sol"]))
    if arqs_planetas:
        for nome, arqs in arqs_planetas.items():
            if not arqs:
                continue
            # pula a duplicata Sol (já medalhonada) e o âncora do zodíaco
            nm = arqs[0][1].split(" (")[0]
            if nome == "Sol" or (arqs[0][2] or "").lower() == "zodiaco":
                continue
            pl = m["planetas"].get(nome, {})
            if not pl:
                continue
            pares.append((pl["lon"], nm, pl.get("signo", ""),
                          COR_P.get(nome, (150, 150, 150))))
    if not pares:
        return
    # separa medalhões que ficariam colados no mesmo setor
    pares.sort(key=lambda p: p[0])
    RAD = 84
    if len(pares) > 1:
        for k in range(len(pares) - 1):
            lon_k, lon_n = pares[k][0], pares[k + 1][0]
            da = (lon_n - lon_k) % 360
            if da > 180:
                da = 360 - da
            if da < 70:
                push = (70 - da) / 2
                pares[k] = (pares[k][0] - push, *pares[k][1:])
                pares[k + 1] = (pares[k + 1][0] + push, *pares[k + 1][1:])
    for lon, nome, signo, cor in pares:
        px, py = _polar(cx, cy, r_rime, lon)
        _medalhao(d, img, px, py, RAD, nome, cor, rng)


def _bioconstrucao_da_roda(img, W, H, cx, cy, r_ext, rng):
    """Cola 'matérias de construção' recicláveis nas gutas laterais da roda
    (biotintas, pedaços de papelão, latinhas, garrafas) — reforça a ideia de
    que o planetário é montado com o que se descarta."""
    _CACHE_REC and None
    gut_esq = [(cx - r_ext - 230, cy - r_ext * 0.5),
               (cx - r_ext - 210, cy + r_ext * 0.55)]
    gut_dir = [(cx + r_ext + 230, cy - r_ext * 0.4),
               (cx + r_ext + 210, cy + r_ext * 0.5)]
    spots = []
    assets = ["lata-aluminio", "lata-aluminio-2",
              "garrafa-vidro-verde", "garrafa-vidro-ambar", "saco-plastico",
              "caixa-longa-vida", "papelao-ondulado", "jornal", "recorte-papel"]
    for i, (x, y) in enumerate(gut_esq + gut_dir):
        asset = rng.choice(assets)
        esc = rng.uniform(0.07, 0.13)
        _afixar_reciclavel(img, asset, x, y, escala=esc,
                           ang=rng.uniform(-30, 30), rng=rng)
    return img


def _roda(img, m, cx, cy, r_ext, r_int, rng, aspectos=None, transitos=None,
          asc_lon=None, corpos=None):
    _LEGENDA_TRANSITO = None
    ov = _layer(img.size)
    d = ImageDraw.Draw(ov)
    # ── aguada de fundo: lavagem de tinta escura no interior da roda ──────
    masc_int = Image.new("L", img.size, 0)
    md = ImageDraw.Draw(masc_int)
    md.ellipse([cx - r_ext, cy - r_ext, cx + r_ext, cy + r_ext], fill=255)
    _blit(ov, _aguada(masc_int, (34, 40, 58), rng, tons=260, r0=30, r1=160,
                      blur=14, alpha=(10, 26)))

    # ── faixas dos signos pintadas a aguada (pigmento translúcido) ────────
    for z, nome in enumerate(SIGNOS):
        a0, a1 = z * 30, (z + 1) * 30
        cor = COR[nome]
        masc = Image.new("L", img.size, 0)
        md = ImageDraw.Draw(masc)
        pts = []
        for g in range(a0, a1 + 2, 2):
            pts.append(_polar(cx, cy, r_int, g))
        for g in range(a1, a0 - 2, -2):
            pts.append(_polar(cx, cy, r_ext, g))
        md.polygon(pts, fill=255)
        _blit(ov, _aguada(masc, cor, rng, tons=60, r0=16, r1=120, blur=12,
                          alpha=(14, 42)))
        # pincelada na divisória do setor (traço de tinta separando)
        p0 = _polar(cx, cy, r_int, a0)
        p1 = _polar(cx, cy, r_ext, a0)
        _pincelada(d, p0, p1, (46, 40, 30, 150), 4, rng, n=6)

    # ── anéis com traço de pincel (não pixel chapado) ─────────────────────
    for rad, col, lw in [(r_ext, (224, 210, 168), 5),
                         (r_int, (214, 200, 158), 4)]:
        for g in range(0, 360, 4):
            p0 = _polar(cx, cy, rad + rng.uniform(-0.4, 0.4), g)
            p1 = _polar(cx, cy, rad + rng.uniform(-0.4, 0.4), g + 4)
            _pincelada(d, p0, p1, (*col, 200), lw, rng, n=3)
    # ticks de graus (traço seco)
    for g in range(0, 360, 5):
        p0 = _polar(cx, cy, r_ext - 2, g)
        p1 = _polar(cx, cy, r_ext - (12 if g % 30 == 0 else 5), g)
        d.line([p0, p1], fill=(192, 180, 142), width=2)
    # (os glifos e nomes dos signos são desenhados DEPOIS da rotação, em
    # pé e legíveis — ver o bloco de glifos após o paste da roda)
    # cúspides das casas (as linhas giram com a roda; os NÚMEROS são
    # desenhados por fora, em pé — ver bloco pós-rotação)
    _casa_post = []
    for i, c in enumerate(m.get("casas", [])):
        p0 = _polar(cx, cy, 16, c["lon"])
        p1 = _polar(cx, cy, r_int - 8, c["lon"])
        d.line([p0, p1], fill=(202, 190, 152), width=2)
        _casa_post.append((c["lon"] + 4, i + 1))
    # ASC / MC — traços brilhantes nas posições reais (os nomes ficam na
    # linha do horizonte, desenhada em _eixos_horizonte)
    asc_lon = m["casas"][0]["lon"] if asc_lon is None else asc_lon
    mc_lon = m["casas"][9]["lon"] if len(m.get("casas", [])) > 9 else 83
    for lon, cm, lw in [(asc_lon, (206, 58, 40), 6),
                        (mc_lon, (52, 84, 160), 4)]:
        pe = _polar(cx, cy, r_ext + 14, lon)
        pi = _polar(cx, cy, r_int - 6, lon)
        d.line([pi, pe], fill=(*cm, 230), width=lw)

    # ── LINHAS DOS ASPECTOS (cordas dentro da roda) ─────────────────────
    r_asp = r_int - 190  # raio das pontas dos planetas (para as cordas)
    if aspectos:
        pts_asp = {}
        for nome, pl in m["planetas"].items():
            x, y = _polar(cx, cy, r_asp, pl["lon"])
            pts_asp[nome] = (x, y)
        for a, b, tipo, cor, ang, lon_a, lon_b in aspectos:
            if a in pts_asp and b in pts_asp:
                lw = 1 if abs(ang - 60) < 1 and abs(ang - 120) < 1 else \
                     max(1, int(6 - abs(ang - 90) / 30))
                lw = 2
                _linha_mao(d, pts_asp[a], pts_asp[b], (*cor, 170), lw, rng,
                           jitter=1.2, passos=10)

    # ── PLANETAS (espaçados por signo, evitando embolar as conjunções) ──
    # agrupa por grau aproximado dentro de cada signo; desloca ao longo do arco
    signos_plan = {}
    for nome, pl in m["planetas"].items():
        if corpos is not None and nome not in corpos:
            continue
        chave = pl["signo"]
        signos_plan.setdefault(chave, []).append(nome)
    pos_plan = {}
    ang_final = {}
    for signo, nomes in signos_plan.items():
        a0 = SIGNOS_ANG.get(signo, 0)
        sub = sorted(nomes, key=lambda n: m["planetas"][n]["lon"])
        n = len(sub)
        if n == 1:
            r = r_int - 42
            pos_plan[sub[0]] = _polar(cx, cy, r, m["planetas"][sub[0]]["lon"])
            ang_final[sub[0]] = m["planetas"][sub[0]]["lon"] % 360
        else:
            # espalha os planetas do mesmo signo em arco ao redor do centro
            largura = 12.0  # graus de folga para espalhar
            for i, nome in enumerate(sub):
                off = (i - (n - 1) / 2) * (largura / max(n - 1, 1))
                lon = m["planetas"][nome]["lon"] + off
                r = r_int - 42
                pos_plan[nome] = _polar(cx, cy, r, lon % 360)
                ang_final[nome] = lon % 360
    m["lat_mandala"] = {nome: pxy for nome, pxy in pos_plan.items()}
    # cada planeta guarda (raio, ângulo final) p/ o crachá ser desenhado EM
    # PÉ, na posição exata do agrupamento (a roda gira, o texto não gira)
    _planet_post = []
    for nome, pl in m["planetas"].items():
        if corpos is not None and nome not in corpos:
            continue
        if nome not in PLANETAS_10:
            _r = r_int - 50 if nome == "Quíron" else r_int - 56
        else:
            _r = r_int - 58
        _planet_post.append((nome, _r, ang_final.get(nome, pl.get("lon", 0)),
                             pl.get("retrogrado", False)))

    # ── TRÂNSITOS (anel EXTERNO em ROXO; CONJUNÇÕES viram um grupinho só,
    # com UMA legenda conjunta — etiquetas não se misturam) ───────────────
    if transitos:
        roxa = (168, 92, 216)      # cor própria dos trânsitos (hoje)
        lista = []
        for nome, pl in transitos["planetas"].items():
            if nome in PLANETAS_10 and pl:
                lista.append((pl["lon"] % 360, nome, pl.get("graus", 0)))
        lista.sort(key=lambda t: t[0])
        # agrupa planetas em conjunção (separação < 12°)
        grupos, atual = [], []
        for item in lista:
            if atual and (item[0] - atual[-1][0]) % 360 < 12:
                atual.append(item)
            else:
                if atual:
                    grupos.append(atual)
                atual = [item]
        if atual:
            grupos.append(atual)
        rT = r_ext + 116
        for grupo in grupos:
            lon_m = sum(g[0] for g in grupo) / len(grupo)
            gx, gy = _polar(cx, cy, rT, lon_m)
            if len(grupo) == 1:
                nome, g = grupo[0][1], grupo[0][2]
                cor = COR_P.get(nome, (190, 190, 190))
                s = 7
                d.rectangle([gx - s, gy - s, gx + s, gy + s],
                            outline=(*roxa, 240), width=2)
                d.rectangle([gx - s + 2, gy - s + 2, gx + s - 2, gy + s - 2],
                            fill=(*cor, 220))
                _texto_traco(d, (gx, gy + 22), f"{nome[:3]} {g}°",
                             _font(15, True), fill=(*roxa, 245),
                             contorno=(30, 22, 44), sw=2, desloc=(1, 1),
                             anchor="mm")
            else:
                n = len(grupo)
                for k, (lon, nome, g) in enumerate(grupo):
                    cor = COR_P.get(nome, (190, 190, 190))
                    qy = gy - (n - 1) * 8 + k * 16
                    d.rectangle([gx - 8, qy - 8, gx + 8, qy + 8],
                                outline=(*roxa, 240), width=1)
                    d.rectangle([gx - 6, qy - 6, gx + 6, qy + 6],
                                fill=(*cor, 230))
                nomes = " + ".join(g[1][:3] for g in grupo)
                _texto_traco(d, (gx, gy + (n - 1) * 8 + 26), f"{nomes} "
                             f"{grupo[0][2]}°", _font(14, True),
                             fill=(*roxa, 245), contorno=(30, 22, 44), sw=2,
                             desloc=(1, 1), anchor="mm")
        # legenda do anel de hoje (fora da roda, na horizontal)
        d.arc([cx - (rT + 14), cy - (rT + 14),
               cx + (rT + 14), cy + (rT + 14)],
              start=0, end=360, fill=(*roxa, 150), width=1)
        _LEGENDA_TRANSITO = (cx, cy + rT + 64,
                             "anel roxo = céu de hoje (trânsitos atuais)")

    # ── gira a roda p/ o ASC ficar à ESQUERDA (posição clássica: ASC no
    # horizonte leste, DESC no oeste; MC no topo, IC na base) ──────────────
    if asc_lon is not None:
        ov = ov.rotate(180 - asc_lon,
                       center=(cx, cy), resample=Image.BICUBIC)

    _blit(img, ov)

    # ── tudo que tem LETRA/SÍMBOLO é desenhado agora, JÁ na posição final
    # da rotação: EM PÉ e com o tamanho certo para a roda (nada de texto
    # torturado junto com a rotação) ───────────────────────────────────────
    d2 = ImageDraw.Draw(img)
    gt = (180 - asc_lon) if asc_lon is not None else 0
    # glifos dos signos (os NOMES não precisam: a legenda da tabela traz todos)
    for z, nome in enumerate(SIGNOS):
        mid = z * 30 + 15
        cor = COR[nome]
        pg = _polar(cx, cy, r_int + (r_ext - r_int) * 0.48, mid + gt)
        med = _medalhao_signo(nome, cor, MEDALHAO_W.get(nome, 96))
        if med is not None:
            # medalhão (domínio público) no lugar do glifo — sombra + imagem
            _sombra = Image.new("RGBA", med.size, (0, 0, 0, 0))
            _sd = ImageDraw.Draw(_sombra)
            _sd.ellipse([4, 6, med.size[0] - 4, med.size[1] - 2],
                        fill=(30, 26, 16, 150))
            img.paste(_sombra, (int(pg[0] - med.size[0] / 2) + 3,
                                int(pg[1] - med.size[1] / 2) + 3), _sombra)
            img.paste(med, (int(pg[0] - med.size[0] / 2),
                            int(pg[1] - med.size[1] / 2)), med)
        else:
            d2.text((pg[0] + 3, pg[1] + 3), SIMB[nome], font=_sans(88),
                    fill=(30, 26, 16, 150), anchor="mm")
            d2.text(pg, SIMB[nome], font=_sans(88), fill=(*cor, 255),
                    anchor="mm")
    # números das casas (fica ao lado da cúspide, sem girar)
    for _ln, _i in _casa_post:
        pn = _polar(cx, cy, r_int - 42, _ln + gt)
        d2.text(pn, str(_i), font=_font(28, True), fill=(30, 26, 18),
                anchor="mm")
    # crachás dos planetas EM PÉ + retrôgrafo (as FOTOS do corpo ficam na
    # galeria do fim da obra, com nome e posição — ver _cartao_galeria_planetas)
    for _nm, _r, _lf, _retro in _planet_post:
        x, y = _polar(cx, cy, _r, _lf + gt)
        cor = COR_P.get(_nm, (180, 180, 180))
        if _nm == "Quíron":
            # o glifo ⚷ é fino e pequeno demais em 28px — parece "??";
            # em fonte maior (36) e disco maior fica legível na roda
            rb, fsz = 24, 36
        elif _nm in ASTEROIDES_EXTRA:
            rb, fsz = 24, 30
        else:
            rb, fsz = 37, 52
        escura = tuple(max(22, int(c * 0.40)) for c in cor)
        # sombra + disco + símbolo claro (tudo reto)
        d2.ellipse([x - rb - 7, y - rb - 7, x + rb + 7, y + rb + 7],
                   fill=(10, 10, 16, 90))
        d2.ellipse([x - rb, y - rb, x + rb, y + rb], fill=escura,
                   outline=(*cor, 255), width=6)
        d2.ellipse([x - rb, y - rb, x + rb, y + rb],
                   outline=(255, 250, 235, 210), width=1)
        d2.text((x, y + 2), GLIFO.get(_nm, "★"), font=_sans(fsz),
                fill=(255, 252, 243), anchor="mm",
                stroke_width=2, stroke_fill=(20, 20, 30))
        if _retro:
            d2.ellipse([x + rb - 11, y - rb - 11, x + rb - 3, y - rb - 3],
                       fill=(206, 70, 66, 235))

    # legenda do anel de trânsitos (desenhada por fora da roda girada p/
    # ficar na horizontal e legível)
    if _LEGENDA_TRANSITO is not None:
        lx, ly, lt = _LEGENDA_TRANSITO[0], _LEGENDA_TRANSITO[1] + 4, _LEGENDA_TRANSITO[2]
        _texto_traco(d2, (lx, ly), lt, _font(21, True),
                     fill=(*roxa, 255), contorno=(30, 22, 44), sw=3,
                     desloc=(2, 2), anchor="mm")


def _eixos_horizonte(img, cx, cy, r_ext, rng, asc_lon, mc_lon):
    """Linha do horizonte (ASC–DESC, horizontal, à esquerda no papel) e o
    meridiano MC–IC, com os nomes — o mapa é apresentado do jeito clássico."""
    asc_lon = asc_lon % 360
    mc_lon = mc_lon % 360
    al = (mc_lon - asc_lon + 180) % 360  # papel do MC depois da rotação

    d = ImageDraw.Draw(img)
    L, R = _polar(cx, cy, r_ext + 14, 180), _polar(cx, cy, r_ext + 12, 0)
    T, B = _polar(cx, cy, r_ext + 12, al), _polar(cx, cy, r_ext + 12, (al + 180) % 360)
    # linha do horizonte (cruz do mapa, bem presente — eixo da mandala)
    for p0, p1, col, lw in [(L, R, (206, 178, 122), 6),
                            (T, B, (178, 196, 228), 5)]:
        _linha_mao(d, p0, p1, (*col, 255), lw, rng, jitter=1.4, passos=30)
    # marcas nos quatro rumos + nomes legíveis (fora do aro)
    rx = r_ext + 42
    d.text((cx - rx, cy), "ASC", font=_sans(38), fill=(206, 58, 40), anchor="rm")
    d.text((cx - rx, cy + 34), "leste", font=_font(18, True), fill=TINTA_FORTE,
           anchor="rm")
    d.text((cx + rx, cy), "DESC", font=_sans(38), fill=(206, 58, 40), anchor="lm")
    d.text((cx + rx, cy + 34), "oeste", font=_font(18, True), fill=TINTA_FORTE,
           anchor="lm")
    mx, my = _polar(cx, cy, r_ext + 60, al)
    bx, by = _polar(cx, cy, r_ext + 60, (al + 180) % 360)
    if abs(al % 180 - 90) > 20:
        d.text((mx, my), "MC", font=_sans(38), fill=(52, 84, 160), anchor="mm")
        d.text((bx, by), "IC", font=_sans(38), fill=(52, 84, 160), anchor="mm")
    else:
        d.text((mx, my), "MC", font=_sans(38), fill=(52, 84, 160), anchor="lm")
        d.text((bx, by), "IC", font=_sans(38), fill=(52, 84, 160), anchor="rm")
    d.text((cx, cy + r_ext + 96),
           "linha do horizonte · leste–oeste (ASC–DESC) · meio do céu (MC–IC)",
           font=_font(20, True), fill=(90, 74, 52), anchor="mm")


def _anel_mao(d, cx, cy, rad, col, lw, rng, n_passos=72):
    """Círculo com leve ondulação (efeito de desenho à mão/tinta)."""
    pts = []
    for i in range(n_passos):
        a = 360 * i / n_passos
        r = rad + rng.uniform(-1.2, 1.2)
        pts.append(_polar(cx, cy, r, a))
    for i in range(n_passos):
        p0 = pts[i]
        p1 = pts[(i + 1) % n_passos]
        d.line([p0, p1], fill=col, width=lw)


# ══════════════════════════════════════════════════════════════════════
#  CARTÕES (cada um é um layer próprio com fundo)
# ══════════════════════════════════════════════════════════════════════

def _borda_pintada(d, x0, y0, x1, y1, cor, lw, rng, n=36):
    """Perímetro do quadro desenhado à mão (traço de pincel/caneta), com
    cantos arredondados por jitter — nada de régua reta."""
    per = [(x0, y0, x1, y0), (x1, y0, x1, y1),
           (x1, y1, x0, y1), (x0, y1, x0, y0)]
    pts = []
    for a, b, c, e in per:
        seg = max(3, int(n / 4))
        for i in range(seg + 1):
            t = i / seg
            pts.append((a + (c - a) * t + rng.uniform(-1.6, 1.6),
                        b + (e - b) * t + rng.uniform(-1.6, 1.6)))
    for i in range(1, len(pts)):
        _linha_mao(d, pts[i - 1], pts[i], cor, lw, rng, jitter=1.7,
                   passos=5)


def _fita(d, x, y, w=110, h=24, rng=None):
    """Fita adesiva com ponta rasgada e leve inclinação (rng p/ variar)."""
    if rng is None:
        import random as _r
        rng = _r.Random()
    tor = rng.randint(-3, 4)
    d.polygon([(x, y + tor), (x + w, y - tor), (x + w - h * 0.32, y + h),
               (x, y + h)], fill=(178, 160, 118, 160))


def _fio(img, x0, y, x1, y1, rng=None):
    """Linha de ligação entre os cartões de medalhões (o 'fio do colar'):
    um traço fino dourado-papel que costura os cartões da fileira, com um
    pequeno nó no meio de cada cartão. Discreto: não compete com o texto."""
    if rng is None:
        import random as _r
        rng = _r.Random()
    d = ImageDraw.Draw(img)
    _n = 3
    _passo = (x1 - x0) / _n
    for i in range(_n):
        _a = x0 + i * _passo
        _b = _a + _passo
        _meio = (_a + _b) / 2
        # fio com leve ondulação à mão
        _pts = []
        for _t in range(0, 9):
            _x = _a + (_b - _a) * _t / 8
            _yy = y + rng.uniform(-1.2, 1.2)
            _pts.append((_x, _yy))
        d.line(_pts, fill=(196, 170, 128, 150), width=2)
        # nó no centro de cada cartão
        _nr = 4
        d.ellipse([_meio - _nr, y - _nr, _meio + _nr, y + _nr],
                  fill=(196, 170, 128, 170))
        d.ellipse([_meio - _nr + 1, y - _nr + 1, _meio + _nr - 1,
                   y + _nr - 1], fill=(46, 36, 22, 200))


def _base_cartao(vw, vh, rng=None):
    """Layer de cartão ESCURO PINTADO (mesma lógica da placa do cabeçalho):
    corpo em aguada organicamente, sem retângulo chapado, com borda dupla
    dourada desenhada à mão — a letra clara destaca por cima."""
    if rng is None:
        import random as _r
        rng = _r.Random()
    lay = _layer((vw, vh))
    masc = Image.new("L", (vw, vh), 0)
    md = ImageDraw.Draw(masc)
    md.rounded_rectangle([12, 12, vw - 12, vh - 12], radius=26, fill=255)
    _blit(lay, _aguada(masc, CARD_ESC, rng, tons=150, r0=12, r1=230, blur=7,
                       alpha=(150, 245)))
    d = ImageDraw.Draw(lay)
    _borda_pintada(d, 16, 16, vw - 16, vh - 16, (210, 184, 128, 210), 2,
                   rng)
    _borda_pintada(d, 26, 26, vw - 26, vh - 26, (150, 128, 84, 120), 2, rng,
                   n=28)
    return lay, d


def _cartao_elementos(elem_qtd, asc_signo, vw, vh, rng=None):
    """Cartão com a proporção dos 4 elementos (fogo/terra/água/ar).
    O balanço é pintado como faixas de aguada, não barras chapadas."""
    lay, d = _base_cartao(vw, vh, rng)
    if rng is None:
        import random as _r
        rng = _r.Random()
    _fita(d, vw - 130, 4, rng=rng)
    _texto_traco(d, (24, 22), "EQUILÍBRIO DOS ELEMENTOS", _font(20, True),
                 contorno=(250, 245, 225), sw=3, sombra=TINTA_FORTE)
    d.text((vw - 26, 22),
           f"Asc · {asc_signo}", font=_font(12, True), fill=TINTA,
           anchor="rm")

    total = max(sum(elem_qtd.values()), 1)
    cx0, cy0 = 60, 92
    lw_total = vw - 120
    x = cx0
    ordem = [("fogo", "FOGO"), ("terra", "TERRA"), ("água", "ÁGUA"), ("ar", "AR")]
    for ekey, ename in ordem:
        qtd = elem_qtd.get(ekey, 0)
        larg = int(lw_total * qtd / total)
        cor = ELEM_COR[ekey]
        if larg > 0:
            d.rectangle([x, cy0, x + larg, cy0 + 34], fill=(*cor, 235))
            d.text((x + larg / 2, cy0 + 17), f"{qtd}", font=_sans(16),
                   fill=(255, 250, 240), anchor="mm")
            # pinceladas de tinta por cima (quebra o bloco chapado)
            for k in range(rng.randint(0, 6), max(larg, 1), 16):
                _pincelada(d, (x + k, cy0 + 34), (x + k + 9, cy0 + 1),
                           (250, 244, 228, 95), 2, rng, n=5)
        x += larg + 3
    d.rectangle([cx0, cy0, cx0 + lw_total, cy0 + 34], outline=(*TINTA_FORTE, 120),
                width=2)
    # legenda
    ly = cy0 + 52
    x = cx0
    for ekey, ename in ordem:
        cor = ELEM_COR[ekey]
        d.rectangle([x, ly, x + 16, ly + 16], fill=(*cor, 235))
        d.text((x + 24, ly + 8), f"{ename}", font=_font(13, True), fill=TINTA,
               anchor="lm")
        x += vw // 4
    d.text((vw - 30, ly + 34), "os 4 elementos no mapa (planetas + Asc)",
           font=_font(11, False), fill=TINTA, anchor="rm")
    return lay


def _badge_cazimi(img, m, cazimi, cx, cy, r_ext, rng):
    """Etiqueta de destaque para a conjunção cazimi (Sol c/ Mercúrio)."""
    if not cazimi:
        return
    d = ImageDraw.Draw(img)
    ov = _layer(img.size)
    od = ImageDraw.Draw(ov)
    # balão destacado (fundo escuro + borda dourada)
    txt = "OUTROS"
    x0, y0 = cx - 540, cy + r_ext + 4
    x1, y1 = cx + 540, cy + r_ext + 74
    od.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=(38, 26, 16, 220))
    od.rounded_rectangle([x0, y0, x1, y1], radius=16,
                         outline=(*VERMELHO, 240), width=3)
    _blit(img, ov)
    d = ImageDraw.Draw(img)
    linha = (f"☉ SOL em conjunção CAZIMI com ☿ MERCÚRIO "
             f"({cazimi['graus']:.1f}° {cazimi['signo']}) — "
             f"separados por {cazimi['separa']*60:.0f}′ · raro, marca a mente do Sol")
    d.text((cx, (y0 + y1) / 2), linha, font=_sans(16),
           fill=(255, 225, 150), anchor="mm")


def _quebra_txt(texto, largura, font):
    """Quebra `texto` em linhas que cabem na largura (por palavra)."""
    palavras = str(texto).split()
    linhas, atual = [], ""
    for p in palavras:
        teste = f"{atual} {p}".strip()
        if font.getlength(teste) <= largura or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def _foto_corpo(nome):
    """Caminho da foto real (NASA/ESA) de um corpo celeste, ou None."""
    _f = _fotos_roda()
    if nome in _f:
        return _f[nome]
    chave = _sem_acentos(nome)
    for k in sorted(fotos_mapa()):
        if chave in k.split("/")[-1]:
            return fotos_mapa()[k]
    return None


def _cartao_arquetipos(m, titulo, signo, arqs, vw, vh, rng, ascii_mode=False,
                       subtitulo=None, corpo=None, compact=False):
    """Cartão das CORRESPONDÊNCIAS de um signo: gravura limpa do arquétipo
    (foto PD ou desenho) OU ASCII art — + nome + o que ele guarda/significa
    em texto legível (nada de discos de glifos 'só para preencher').
    `corpo`: nome do astro (Sol, Vênus...) — a FOTO real dele entra no
    canto do cartão (no lugar da galeria do fim da obra). `compact`: cartão
    da fileira de análise — medalhões e fontes reduzidos. Cartões estreitos
    (<700px) usam UMA coluna: os medalhões grandes em 2 colunas espremem o
    texto e os nomes ficam picados."""
    lay, d = _base_cartao(vw, vh, rng)
    cor_s = COR.get(signo, (150, 150, 150))
    _fita(d, vw - 130, 4, rng=rng)
    # título (a expressão do corpo no signo) e o subtítulo embaixo dele
    # (o grau do corpo, ou os astros que estão no signo em destaque).
    # A fonte do título se ajusta sozinha: títulos longos (ex.: "EXPRESSÕES
    # DO ASCENDENTE EM AQUÁRIO") encolhem para nunca encostar na foto do
    # corpo no canto direito.
    _f_tit = _font(26 if not compact else 22, True)
    _tit_w = d.textlength(titulo, font=_f_tit)
    # à direita: a foto do corpo (raio 28 + folga) ou o signo no canto
    _tit_max = vw - 78 - (60 if corpo else 150)
    while _tit_w > _tit_max and _f_tit.size > 15 * FONT_K:
        _f_tit = _font(int(_f_tit.size / FONT_K) - 1, True)
        _tit_w = d.textlength(titulo, font=_f_tit)
    d.text((24, 26), titulo, font=_f_tit,
           fill=TINTA_CARD, anchor="lm")
    d.text((24, 58), subtitulo or "as correspondências do signo",
           font=_font(16 if not compact else 14), fill=LINHA_CARD,
           anchor="lm")
    if corpo:
        # foto real do astro no canto superior direito (sem texto por baixo:
        # o subtítulo já diz "Sol em Escorpião")
        _fr = 28 if not compact else 24
        _fx, _fy = vw - 26 - _fr, 30
        _foto = _foto_corpo(corpo)
        if _foto:
            try:
                _pc = _mascarar_redondo(
                    Image.open(_foto).convert("RGB").resize(
                        (_fr * 2, _fr * 2), Image.LANCZOS), _fr * 2)
                lay.paste(_pc, (int(_fx - _fr), int(_fy - _fr)), _pc)
            except Exception:
                _foto = None
        if not _foto:
            cor_p = COR_P.get(corpo, (150, 150, 150))
            d.ellipse([_fx - _fr, _fy - _fr, _fx + _fr, _fy + _fr],
                      fill=tuple(max(24, int(c * 0.35)) for c in cor_p),
                      outline=(*cor_p, 255), width=4)
            d.text((_fx, _fy + 2), GLIFO.get(corpo, "★"), font=_sans(34),
                   fill=(255, 252, 243), anchor="mm")
        d.ellipse([_fx - _fr, _fy - _fr, _fx + _fr, _fy + _fr],
                  outline=(255, 240, 200, 210), width=3)
    else:
        # o GLIFO do signo no canto (nunca o nome — o título já diz o signo,
        # e o nome aqui faria o cartão parecer do zodíaco, não do arquétipo)
        d.text((vw - 26, 30), SIMB.get(signo, "✦"), font=_sans(30),
               fill=(*_claro(cor_s), 235), anchor="rm")

    arqs = arqs[:4]
    if not arqs:
        d.text((vw // 2, vh // 2 - 8),
               "este signo ainda não tem correspondência no catálogo "
               "desta cultura", font=_font(16, True), fill=LINHA_CARD,
               anchor="mm")
        d.text((vw // 2, vh // 2 + 26),
               "o arquivo cresce a cada mapa — e o teu registra por onde ",
               font=_font(14), fill=TINTA_CARD, anchor="mm")
        d.text((vw // 2, vh // 2 + 48),
               "o catálogo vai se completando.", font=_font(14),
               fill=TINTA_CARD, anchor="mm")
        return lay
    n = max(len(arqs), 1)
    cols = 1 if (compact or vw < 700) else 2
    pad = 40
    disp = (vw - 2 * pad) / cols
    top = 82
    rows = (n + cols - 1) // cols
    rh = (vh - top - 26) / max(rows, 1)
    f_nome = _font(20 if not compact else 17, True)
    f_simb = _font(17 if not compact else 15)
    # mito em tom claro DOURADO-PAPEL: cartão é escuro, e o texto do mito
    # ganha destaque (maior e mais claro) sem competir com o nome
    cor_mito = (232, 210, 168) if not compact else (222, 200, 158)
    for j, a in enumerate(arqs):
        col = j % cols
        row = j // cols
        nome = a[1].split(" (")[0]
        simb = (a[3] if len(a) > 3 else "") or ""
        simb = str(simb).strip()
        if not simb and len(a) > 4:
            simb = " ".join(str(a[4]).split())
        rad = min(96, max(52, int(rh * 0.40)))
        if compact:
            rad = max(44, int(rad * 0.78))
        cy_a = top + rh * row + rh / 2
        x_d = pad + disp * col + rad
        # ── disco de papel claro com a FIGURA do arquétipo ────────────────
        d.ellipse([x_d - rad, cy_a - rad, x_d + rad, cy_a + rad],
                  fill=(244, 232, 200))
        d.ellipse([x_d - rad, cy_a - rad, x_d + rad, cy_a + rad],
                  outline=(*cor_s, 255), width=5)
        if ascii_mode:
            _arte_ascii(lay, x_d, cy_a, rad - 6, nome, rng)
        else:
            # FIGURA GRAVADA (não a foto recortada). Era aqui que entrava
            # `_crop_circular`: uma única imagem estática por arquétipo, o
            # elemento mais repetido do mapa e o único que ignorava as 12
            # variantes. A gravura é sorteada por pessoa, mantém o disco e o
            # anel, e deixa o cartão no mesmo registro do resto da obra.
            _arte_medalhao(lay, x_d, cy_a, rad - 6, nome, rng)
        # ── nome (negrito) + MITO em destaque ao lado ─────────────────────
        tx = x_d + rad + 18
        tw = max(60, disp - rad * 2 - 38)
        ln_nome = _quebra_txt(nome, tw, f_nome)[:2]
        for li, ln in enumerate(ln_nome):
            d.text((tx, cy_a - 22 + li * 24), ln, font=f_nome,
                   fill=TINTA_CARD, anchor="lm")
        ty = cy_a + 14
        if len(ln_nome) > 1:
            ty += 8
        # mito: usa TODO o espaço vertical da célula — a fonte encolhe se a
        # descrição for longa, e só corta (com reticências) se ainda assim
        # não couber. Nada de frase cortada no meio sem aviso.
        _esp_mito = (top + rh * (row + 1)) - ty - 10
        _f_mito = f_simb
        _linhas_mito = _quebra_txt(simb, tw, _f_mito)
        while (len(_linhas_mito) * 22 > _esp_mito
               and _f_mito.size > 12 * FONT_K):
            _f_mito = _font(int(_f_mito.size / FONT_K) - 1)
            _linhas_mito = _quebra_txt(simb, tw, _f_mito)
        _n_mito = min(len(_linhas_mito), max(1, int(_esp_mito / 22)))
        for li, ln in enumerate(_linhas_mito[:_n_mito]):
            d.text((tx, ty + li * 22), ln, font=_f_mito, fill=cor_mito,
                   anchor="lm")
        if len(_linhas_mito) > _n_mito:
            d.text((tx, ty + _n_mito * 22), "…", font=_f_mito,
                   fill=cor_mito, anchor="lm")
    return lay


def _cartao_tabela(m, vw, vh, rng, aspectos=None, asp_h_block=150,
                   arqs_planetas=None, elem_qtd=None, asc_signo=None,
                   nomes_corpos=None, dignidades=None):
    """Tabela dos planetas em COLUNA LARGURA-COMPLETA (esquerda) + painéis
    de elementos, aspectos e cúspides à DIREITA — nada fica espremido num
    canto, o espaço ocioso da folha é ocupado com a informação organizada.
    `dignidades`: dict signo → (domicílio, exaltação, exílio, queda) — a
    coluna "dignidade" mostra em que estado essencial cada planeta está."""
    lay, d = _base_cartao(vw, vh, rng)
    _fita(d, 8, vh - 34, rng=rng)
    _texto_traco(d, (24, 22), "PLANETAS · ELEMENTOS · ASPECTOS · CÚSPIDES",
                 _font(28, True), fill=TINTA_CARD, contorno=(36, 28, 18), sw=3,
                 sombra=(24, 18, 10))
    if asc_signo:
        d.text((vw - 26, 24), f"Ascendente · {asc_signo}",
               font=_font(17, True), fill=LINHA_CARD, anchor="rm")

    margem_c = 46           # coluna direita (painéis) fica a partir daqui
    col_dir_x = vw - 640    # largura fixa dos painéis direitos
    left_w = col_dir_x - margem_c - 40

    casas_map = {}
    for c in m.get("casas", []):
        casas_map.setdefault(c.get("signo", ""), []).append(c["casa"])

    ox = 24
    yy = 60
    # ── tabela de planetas (lado esquerdo, largura completa) ──────────────
    # colunas ESPAÇADAS: há folga até os painéis da direita (col_dir_x), e
    # signo/grau não podem se atropelar — cada coluna tem sua faixa própria
    cols_x = [0, 360, 580, 740, 880, 1020, 1180]
    hs = ["planeta", "signo", "grau", "casa", "retr.", "dignidade",
          "expressão cultural (posicionamento)"]
    for hx, txt in zip(cols_x, hs):
        d.text((ox + hx, yy), txt, font=_font(19, True), fill=LINHA_CARD,
               anchor="lm")
    d.line([ox, yy + 22, ox + left_w - 20, yy + 22], fill=(*LINHA_CARD, 130),
           width=1)
    yy += 36

    cor_dir = (*TINTA, 180)

    def _resumo_arq(lista):
        if not lista:
            return None
        a = lista[0]
        nome = a[1].split(" (")[0]
        fonte = a[6] if len(a) >= 7 else ""
        fonte = re.sub(r"\s+", " ", fonte or "").strip()
        # culturas de termos específicos (mapuche etc.) ganham contexto
        # curto ao lado do nome — o nome não fica solto na tabela
        _ctx = _contexto_curto(a, limite=44)
        if _ctx:
            nome = f"{nome} — {_ctx}"
        return nome, fonte

    def _graus_str(pl):
        g, mn, sg = pl.get("graus", 0), pl.get("min", 0), pl.get("seg", 0)
        return f"{g}°{mn:02d}'{sg:02d}\""

    # regente clássico de cada signo (para priorizar associações)
    _REGENTES = {"Áries": "Marte", "Touro": "Vênus", "Gêmeos": "Mercúrio",
                 "Câncer": "Lua", "Leão": "Sol", "Virgem": "Mercúrio",
                 "Libra": "Vênus", "Escorpião": "Plutão",
                 "Sagitário": "Júpiter", "Capricórnio": "Saturno",
                 "Aquário": "Urano", "Peixes": "Netuno"}
    _destaque_arq = {"Sol", "Lua"}
    if asc_signo:
        _destaque_arq.add(_REGENTES.get(asc_signo.split(" ")[0], ""))

    linhas_tab = []
    nomes_corpos = nomes_corpos or (PLANETAS_10 + ["Quíron"])
    for nome in nomes_corpos:
        pl = m["planetas"].get(nome, {})
        signo = pl.get("signo", "")
        retro = "R" if pl.get("retrogrado") else ""
        casas = casas_map.get(signo, [])
        casa_str = ", ".join(str(c) for c in casas) if casas else "—"
        cor = COR_P.get(nome, (150, 150, 150))
        _parte = (CORPO_MAP.get(signo, ("", ""))[0] or "").split(" /")[0]
        if _parte and signo in ("Virgem", "Áries", "Gêmeos", "Capricórnio",
                                "Aquário", "Peixes"):
            _parte = _parte.split(",")[0]
        # arquétipo do POSICIONAMENTO: o do signo onde o corpo está (ex.:
        # Marte em Capricórnio → arquétipos de Capricórnio), com o do
        # próprio planeta como leitura complementar — prioridade ao primeiro
        arq_txt = None
        _aq = _resumo_arq((arqs_planetas or {}).get(nome, []))
        if _aq:
            name_arq, fonte = _aq
            arq_txt = name_arq if len(name_arq) <= 44 else name_arq[:42] + "…"
        linhas_tab.append((nome, signo, _parte, _graus_str(pl), casa_str,
                           retro, cor, arq_txt))
    rh = 58
    for (nome, signo, _parte, grau_s, casa_s, retro, cor, arq_txt) in linhas_tab:
        # glifo do corpo em destaque (o ⚷ do Quíron é pequeno e parece
        # "??" — por isso vai em fonte maior, separado do nome)
        gl = GLIFO.get(nome, "?")
        if nome == "Quíron":
            d.text((ox + 0, yy), gl, font=_sans_reg(30), fill=(*cor, 255),
                   anchor="lm", stroke_width=2, stroke_fill=(255, 250, 235))
            d.text((ox + 34, yy), nome, font=_sans_reg(22), fill=(*cor, 255),
                   anchor="lm")
        else:
            d.text((ox + 0, yy), f"{gl}  {nome}", font=_sans_reg(22),
                   fill=(*cor, 255))
        if signo:
            d.text((ox + 360, yy), f"{SIMB.get(signo, '?')} {signo}",
                   font=_sans_reg(19), fill=_claro(COR.get(signo, TINTA_CARD)))
        else:
            d.text((ox + 360, yy), "—", font=_sans_reg(19),
                   fill=LINHA_CARD)
        if _parte:
            # parte do corpo (melotesia) ABAIXO do signo, sem sobrepor nem
            # encostar na linha divisória: anchor 'la' em yy+29, fonte 10
            # (14px) → termina em yy+43; a linha fica em yy+48 (5px de folga)
            d.text((ox + 360, yy + 29), _parte, font=_font_it(10),
                   fill=LINHA_CARD, anchor="la")
        if signo:
            d.text((ox + 580, yy), grau_s, font=_font(21, False),
                   fill=TINTA_CARD)
        else:
            d.text((ox + 580, yy), "—", font=_font(21, False),
                   fill=LINHA_CARD)
        d.text((ox + 740, yy), casa_s, font=_font(21, False), fill=TINTA_CARD)
        d.text((ox + 880, yy), retro, font=_font(21, True), fill=(240, 110, 90),
               stroke_width=2, stroke_fill=(30, 24, 16))
        # dignidade essencial: em que estado o planeta está no signo
        # (cores claras + contorno escuro: o fundo do cartão é aguada escura)
        _dg = (dignidades or {}).get(signo, (None, None, None, None))
        _dig, _dig_cor = None, None
        if nome == _dg[0]:
            _dig, _dig_cor = "Domicílio", (240, 200, 120)
        elif nome == _dg[1]:
            _dig, _dig_cor = "Exaltado", (170, 225, 150)
        elif nome == _dg[2]:
            _dig, _dig_cor = "Exílio", (250, 140, 120)
        elif nome == _dg[3]:
            _dig, _dig_cor = "Queda", (225, 160, 190)
        if _dig:
            d.text((ox + 1020, yy), _dig, font=_font(19, True),
                   fill=_dig_cor, stroke_width=2, stroke_fill=(30, 24, 16))
        else:
            d.text((ox + 1020, yy), "·", font=_font(20, True),
                   fill=LINHA_CARD)
        if arq_txt:
            d.text((ox + 1180, yy), arq_txt, font=_font(19, True),
                   fill=(240, 200, 120), stroke_width=2,
                   stroke_fill=(30, 24, 16))
        else:
            d.text((ox + 1180, yy), "·", font=_font(20, True),
                   fill=LINHA_CARD)
        d.line([ox, yy + rh - 10, ox + left_w - 20, yy + rh - 10],
               fill=(*LINHA_CARD, 92), width=1)
        yy += rh

    # ── painéis à DIREITA: elementos (maior), aspectos, cúspides ──────────
    px = col_dir_x
    pw = vw - col_dir_x - 24
    # ▸ 4 elementos, grandes, sem símbolos estranhos
    d.text((px, 52), "OS 4 ELEMENTOS", font=_font(22, True),
           fill=TINTA_CARD, anchor="lm")
    d.text((px, 80), "planetas + Ascendente · a água, o fogo, a terra, o ar",
           font=_font(14), fill=LINHA_CARD, anchor="lm")
    total = max(sum((elem_qtd or {}).values()), 1)
    eyy = 106
    for ekey, ename in [("fogo", "Fogo"), ("terra", "Terra"),
                        ("água", "Água"), ("ar", "Ar")]:
        qtd = elem_qtd.get(ekey, 0)
        cor_e = ELEM_COR[ekey]
        d.rectangle([px, eyy, px + pw, eyy + 30], fill=(*cor_e, 235),
                    outline=cor_dir, width=1)
        d.text((px + 12, eyy + 15), f"{ename}", font=_font(19, True),
               fill=(255, 250, 240), anchor="lm")
        d.text((px + pw - 14, eyy + 15), f"{qtd}", font=_sans(22),
               fill=(255, 250, 240), anchor="rm")
        for k in range(rng.randint(0, 4), max(pw, 1), 22):
            _pincelada(d, (px + k, eyy + 30), (px + k + 8, eyy + 1),
                       (250, 244, 228, 95), 2, rng, n=4)
        eyy += 38
    d.line([px, eyy + 4, px + pw, eyy + 4], fill=(*VERMELHO, 160), width=2)

    # ▸ aspectos
    eyy += 18
    d.text((px, eyy), "ASPECTOS (cordas na mandala)", font=_font(21, True),
           fill=(240, 140, 90), anchor="lm")
    eyy += 32
    if aspectos:
        for a, b, tipo, cor, ang, lon_a, lon_b in aspectos[:7]:
            corA = COR_P.get(a, (150, 150, 150))
            corB = COR_P.get(b, (150, 150, 150))
            sim = {0: "☌", 60: "⚹", 90: "□", 120: "△", 180: "☍"}.get(
                min(ASPECTOS_DEF, key=lambda x: abs(x[0] - ang))[0], "·")
            d.ellipse([px, eyy + 5, px + 18, eyy + 23], fill=(*corA, 235))
            d.text((px + 26, eyy + 14),
                   f"{GLIFO.get(a,'?')} {a[:3]} — {GLIFO.get(b,'?')} {b[:3]}",
                   font=_sans_reg(18), fill=(*corB, 255), anchor="lm")
            d.text((px + 240, eyy + 14), f"{tipo} {ang:.1f}°",
                   font=_font(16, False), fill=LINHA_CARD, anchor="lm")
            d.text((px + pw - 22, eyy + 14), sim, font=_sans(20),
                   fill=(*cor, 255), anchor="rm")
            eyy += 30
    else:
        d.text((px, eyy), "nenhum aspecto em orbe (7°)",
               font=_font(15), fill=LINHA_CARD, anchor="lm")
        eyy += 26
    d.line([px, eyy + 4, px + pw, eyy + 4], fill=(*LINHA_CARD, 160), width=1)

    # ▸ cúspides das casas
    eyy += 18
    d.text((px, eyy), "CÚSPIDES DAS CASAS (Placidus)", font=_font(21, True),
           fill=TINTA_CARD, anchor="lm")
    eyy += 34
    casas = m.get("casas", [])
    ccw = pw / 2
    for i, c in enumerate(casas):
        col = i % 2
        lx = px + col * ccw
        ly = eyy + (i // 2) * 28
        d.text((lx, ly),
               f"{c['casa']:>2}: {SIMB.get(c['signo'],'')} {c['signo']} "
               f"{c['graus']}°{c['min']:02d}'",
               font=_font(16, False), fill=TINTA_CARD, anchor="lm")
    return lay


def _cartao_galeria_planetas(m, vw, vh, rng):
    """Galeria final: foto real de cada corpo celeste com NOME e posição,
    para as fotos terem contexto (não ficam mais soltas na mandala)."""
    lay, d = _base_cartao(vw, vh, rng)
    _fita(d, vw - 130, 4, rng=rng)
    _texto_traco(d, (24, 24), "OS ASTROS DO TEU MAPA",
                 _font(30, True), fill=TINTA_CARD, contorno=(36, 28, 18), sw=3,
                 sombra=(24, 18, 10))
    d.text((vw - 30, 26), "o céu de hoje, trazido para perto",
           font=_font(15, True), fill=LINHA_CARD, anchor="rm")

    fotos = {}
    for k in sorted(fotos_mapa()):
        if k.startswith("sistema-solar/"):
            corpo = k.split("/")[-1].split(".")[0]
            fotos.setdefault(corpo, fotos_mapa()[k])
    corpo_map = {"sol": "Sol", "lua": "Lua", "mercurio": "Mercúrio",
                 "venus": "Vênus", "marte": "Marte", "jupiter": "Júpiter",
                 "saturno": "Saturno", "urano": "Urano", "netuno": "Netuno"}
    # TODOS os corpos do mapa na galeria: os 10 planetas + Quíron sempre;
    # os demais asteróides arquetípicos quando presentes no mapa
    ordem = ["Sol", "Lua", "Mercúrio", "Vênus", "Marte", "Júpiter",
             "Saturno", "Urano", "Netuno", "Plutão", "Quíron"]
    ordem += [n for n in ASTEROIDES_EXTRA if n in m["planetas"]]
    itens = []
    for n in ordem:
        pl = m["planetas"].get(n)
        if not pl:
            continue
        corpo = next((c for c, nm in corpo_map.items() if nm == n), None)
        path = fotos.get(corpo) if corpo else None
        itens.append((n, pl, path))
    if not itens:
        return lay

    n = len(itens)          # 10 planetas + asteróides arquetípicos
    cols = 5
    rows = (n + cols - 1) // cols
    pad = 20
    disp = (vw - 2 * pad) / cols
    top = 90
    rh = (vh - top - 24) / rows
    for i, (nm, pl, path) in enumerate(itens):
        col = i % cols
        row = i // cols
        cx = pad + disp * col + disp / 2
        cy = top + rh * row + rh / 2
        raio = min(56, int(rh * 0.40), int(disp * 0.30))
        cor = COR_P.get(nm, (150, 150, 150))
        d.ellipse([cx - raio - 6, cy - raio - 6, cx + raio + 6, cy + raio + 6],
                  fill=(20, 18, 24))
        if path and os.path.exists(path):
            try:
                _pc = _mascarar_redondo(
                    Image.open(path).convert("RGB").resize(
                        (raio * 2, raio * 2), Image.LANCZOS), raio * 2)
                lay.paste(_pc, (int(cx - raio), int(cy - raio)), _pc)
            except Exception:
                esc = tuple(max(24, int(c * 0.35)) for c in cor)
                d.ellipse([cx - raio, cy - raio, cx + raio, cy + raio],
                          fill=esc)
        else:
            esc = tuple(max(24, int(c * 0.35)) for c in cor)
            d.ellipse([cx - raio, cy - raio, cx + raio, cy + raio], fill=esc)
            d.text((cx, cy), GLIFO.get(nm, "★"), font=_sans(44),
                   fill=(255, 252, 243), anchor="mm",
                   stroke_width=2, stroke_fill=(20, 20, 30))
        d.ellipse([cx - raio, cy - raio, cx + raio, cy + raio],
                  outline=(255, 240, 200, 210), width=3)
        sg = pl.get("signo", "?")
        d.text((cx, cy + raio + 12), f"{GLIFO.get(nm, '?')} {nm}",
               font=_sans_reg(19), fill=TINTA_CARD, anchor="mm")
        d.text((cx, cy + raio + 32),
               f"{SIMB.get(sg, '')} {sg} · {pl.get('graus', 0)}°"
               f"{pl.get('min', 0):02d}'",
               font=_sans_reg(15), fill=LINHA_CARD, anchor="mm")
    return lay


def _cartao_aspectos(m, vw, vh, rng, aspectos=None):
    lay, d = _base_cartao(vw, vh, rng)
    _fita(d, vw - 130, 4, rng=rng)
    _texto_traco(d, (24, 20), "ASPECTOS PLANETÁRIOS", _perg(19, True),
                 contorno=(250, 245, 225), sw=2, sombra=TINTA_FORTE)
    d.text((vw - 26, 22), "cordas na mandala", font=_font(10, False),
           fill=TINTA, anchor="rm")
    if not aspectos:
        d.text((vw // 2, vh // 2), "nenhum aspecto em orbe (7°)",
               font=_font(13, False), fill=TINTA, anchor="mm")
        return lay

    ox = 24
    yy = 48
    cols_x = [0, 150, 300, 430]
    hs = ["aspecto", "tipo", "orbe", "símbolo"]
    for hx, txt in zip(cols_x, hs):
        d.text((ox + hx, yy), txt, font=_font(11, True), fill=TINTA, anchor="lm")
    d.line([ox, yy + 14, ox + 520, yy + 14], fill=(*TINTA, 150), width=1)
    yy += 24
    # mostra até ~9 aspectos principais (menor orbe primeiro)
    for a, b, tipo, cor, ang, lon_a, lon_b in aspectos[:9]:
        pa, pb = m["planetas"][a], m["planetas"][b]
        corA = COR_P.get(a, (150, 150, 150))
        corB = COR_P.get(b, (150, 150, 150))
        linha = f"{GLIFO.get(a,'?')} {a[:3]} — {GLIFO.get(b,'?')} {b[:3]}"
        d.rectangle([ox, yy, ox + 12, yy + 12], fill=(*corA, 235))
        d.text((ox + 20, yy), linha, font=_font(12, True), fill=(*corB, 255),
               anchor="lm")
        # tipo
        d.text((ox + 150, yy), tipo, font=_font(12, False), fill=(*cor, 235),
               anchor="lm")
        # orbe (distância do ângulo exato)
        d.text((ox + 300, yy), f"{ang:.1f}°", font=_font(12, False),
               fill=TINTA, anchor="lm")
        # símbolo do aspecto
        sim = {0: "☌", 60: "⚹", 90: "□", 120: "△", 180: "☍"}.get(
            min(ASPECTOS_DEF, key=lambda x: abs(x[0] - ang))[0], "·")
        d.text((ox + 430, yy), sim, font=_font(14, True), fill=(*cor, 255),
               anchor="lm")
        yy += 17
    d.line([ox, yy + 6, ox + 520, yy + 6], fill=(*TINTA, 120), width=1)
    yy += 14
    d.text((ox, yy), "linhas coloridas cruzando a roda = os aspectos do seu céu",
           font=_font(10, False), fill=TINTA, anchor="lm")
    return lay


def _cartao_plantas(m, vw, vh, rng, plantas_destaque):
    """Cartão 'A FLORA DO TEU MAPA': camada própria das plantas regentes dos
    SIGNOS em destaque (posicionamento), agrupadas por signo e sem repetir —
    cada signo uma vez, com os astros que estão nele. Cada planta mostra:
    nome popular (grande), nome científico, elemento, uso popular e
    científico, e o saber poético — com o raminho desenhado à tinta.
    Só campos que existem no banco; nada inventado."""
    lay, d = _base_cartao(vw, vh, rng)
    _fita(d, vw - 130, 4, rng=rng)
    _texto_traco(d, (24, 26), "A FLORA DO TEU MAPA", _font(30, True),
                 fill=TINTA_CARD, contorno=(36, 28, 18), sw=3,
                 sombra=(24, 18, 10))
    d.text((vw - 30, 26), "plantas regentes · saber popular e ciência",
           font=_font(15, True), fill=LINHA_CARD, anchor="rm")
    d.text((24, 66), "a flora de cada signo em destaque — "
           "e as tuas folhas de cura", font=_font(16), fill=LINHA_CARD,
           anchor="lm")

    if not plantas_destaque:
        d.text((vw // 2, vh // 2), "plantas não localizadas — o cadastro "
               "cresce a cada mapa", font=_font(16), fill=LINHA_CARD,
               anchor="mm")
        return lay

    # deduplica as plantas no cartão INTEIRO: a mesma erva rege vários
    # orixás (Alfavaca, Arruda...) e não pode repetir de bloco em bloco
    _vistas = set()
    _blocos = []
    for bloco in plantas_destaque:
        _sg = bloco["signo"]
        _corpos = bloco.get("corpos", [])
        _orix = bloco.get("orixa", "?")
        _plantas = []
        for p in bloco.get("plantas", []):
            _ch = (p[0] or "").strip().lower()
            if not _ch or _ch in _vistas:
                continue
            _vistas.add(_ch)
            _plantas.append(p)
            if len(_plantas) >= 2:
                break
        if _plantas:
            _blocos.append({"signo": _sg, "corpos": _corpos,
                            "orixa": _orix, "plantas": _plantas})
    _blocos = _blocos[:3]

    pad = 40
    n_cols = len(_blocos)
    col_w = (vw - 2 * pad - (n_cols - 1) * 28) / max(n_cols, 1)
    top = 104
    for bi, bloco in enumerate(_blocos):
        _sg = bloco["signo"]
        _corpos = bloco.get("corpos", [])
        _orix = bloco.get("orixa", "?")
        _plantas = bloco.get("plantas", [])
        cor_s = COR.get(_sg, (150, 150, 150))
        x = pad + bi * (col_w + 28)
        # ── cabeçalho do bloco: signo + astros que estão nele ──
        _rot = f"{SIMB.get(_sg, '')} {_sg}"
        if _corpos:
            _rot += "  ·  " + ", ".join(_corpos)
        d.text((x, top), _rot, font=_font(22, True), fill=(*_claro(cor_s), 255),
               anchor="lm")
        d.text((x, top + 30), f"regência: {_orix}",
               font=_font(16, True), fill=DOURADO, anchor="lm")
        yy = top + 62
        tw_pl = col_w - 92
        for pi, p in enumerate(_plantas):
            pltxt = p[0] if len(p) > 0 else ""
            _desc = p[1] if len(p) > 1 else ""
            _uso_med = p[2] if len(p) > 2 else ""
            _uso_pop = p[3] if len(p) > 3 else ""
            _elem = p[4] if len(p) > 4 else ""
            hy = yy + pi * 150
            cor_pl = (138, 206, 148)
            # ── raminho + folhas desenhados à tinta, por planta ──
            _ramo_tinta(d, (x, hy + 24), (x + 78, hy + 24), cor_pl, rng)
            # nome da planta em destaque (maior)
            for ln in _quebra_txt(pltxt, tw_pl, _font(20, True))[:2]:
                d.text((x + 92, hy), ln, font=_font(20, True),
                       fill=TINTA_CARD, anchor="lm")
                hy += 28
            # nome científico (itálico)
            if _desc:
                for ln in _quebra_txt(_desc, tw_pl, _font(15))[:1]:
                    d.text((x + 92, hy), ln, font=_font_it(15),
                           fill=LINHA_CARD, anchor="lm")
                    hy += 24
            # elemento (característica registrada no banco)
            if _elem:
                d.text((x + 92, hy), f"elemento {_elem}",
                       font=_font(14, True), fill=LINHA_CARD,
                       anchor="lm")
                hy += 22
            # saber POPULAR e CIENTÍFICO, um embaixo do outro (tons CLAROS:
            # o cartão é escuro — texto escuro sobre aguada escura não lê)
            if _uso_pop:
                for ln in _quebra_txt("popular: " + _uso_pop, tw_pl,
                                      _font(14))[:2]:
                    d.text((x + 92, hy), ln, font=_font(14),
                           fill=(232, 210, 168), anchor="lm")
                    hy += 22
            if _uso_med:
                for ln in _quebra_txt("ciência: " + _uso_med, tw_pl,
                                      _font(14))[:2]:
                    d.text((x + 92, hy), ln, font=_font(14),
                           fill=(200, 230, 190), anchor="lm")
                    hy += 22
            # verso do saber poético (1 linha)
            _saber_v = p[7] if len(p) > 7 else ""
            if _saber_v:
                for ln in _quebra_txt(_saber_v, tw_pl, _font(14))[:1]:
                    d.text((x + 92, hy), ln, font=_font_it(14),
                           fill=(232, 210, 168), anchor="lm")
                    hy += 22
    # ── banho de ervas: o orixá/arquétipo com MAIS corpos no mapa ──
    # (seção de PREPARO distinta: não repete os nomes das folhas nem o
    # saber poético que já apareceram nos blocos acima — mostra o uso
    # tradicional e o preparo, que são informação nova)
    if _blocos:
        _top = max(_blocos, key=lambda b: len(b.get("corpos", [])))
        _orix_b = _top["orixa"]
        _sg_b = _top["signo"]
        _corpos_b = _top.get("corpos", [])
        _plantas_b = _top.get("plantas", [])
        # uso tradicional do banho (campo `uso` do banco)
        _uso_b = next((p[3] for p in _plantas_b if len(p) > 3 and p[3]), "")
        # preparo (campo novo do banco) quando existir; senão o saber
        # poético de uma planta que NÃO apareceu nos blocos — nunca repete
        _prep_b = next((p[9] for p in _plantas_b if len(p) > 9 and p[9]), "")
        if not _prep_b:
            _saberes = [p[7] for p in _plantas_b if len(p) > 7 and p[7]]
            _prep_b = _saberes[0] if _saberes else ""
        yy = vh - 150
        d.text((24, yy), f"BANHO DE ERVAS · {_orix_b.upper()}",
               font=_font(20, True), fill=(206, 178, 122), anchor="lm")
        yy += 28
        _rot_b = f"para a figura que mais se repete no teu mapa — {_sg_b}"
        if _corpos_b:
            _rot_b += " (" + ", ".join(_corpos_b) + ")"
        for ln in _quebra_txt(_rot_b, vw - 48, _font(15)):
            d.text((24, yy), ln, font=_font(15), fill=LINHA_CARD, anchor="lm")
            yy += 22
        if _uso_b:
            for ln in _quebra_txt("uso tradicional: " + _uso_b, vw - 48,
                                  _font(15, True))[:2]:
                d.text((24, yy), ln, font=_font(15, True),
                       fill=TINTA_CARD, anchor="lm")
                yy += 22
        if _prep_b:
            for ln in _quebra_txt("como preparar: " + _prep_b, vw - 48,
                                  _font(14))[:2]:
                d.text((24, yy), ln, font=_font_it(14),
                       fill=(196, 178, 140), anchor="lm")
                yy += 22
    return lay


def _historias_arquetipos(cur, ceu_multis, luzes):
    """Histórias (resumo mínimo) dos arquétipos apontados no cartão
    'TERRA & CÉU ANCESTRAL': os asterismos de Sol/Asc/Lua nas culturas
    mostradas. Devolve lista de (nome, cultura, resumo) na ordem das luzes,
    sem repetir o mesmo arquétipo duas vezes."""
    vistos, out = set(), []
    for _nm, _sg in luzes:
        for _rot, _leitura in ceu_multis:
            _nome = str(_leitura.get(_sg, "") or "").strip()
            if not _nome or _nome in ("—", "?") or _nome.startswith("—"):
                continue
            _chv = _sem_acentos(_nome.split(" (")[0]).strip().lower()
            if not _chv or _chv in vistos:
                continue
            vistos.add(_chv)
            _hist = ""
            try:
                cur.execute("SELECT historia FROM arquetipo WHERE nome=?",
                            (_nome,))
                _r = cur.fetchone()
                if not _r:
                    cur.execute("SELECT historia FROM arquetipo WHERE nome LIKE ?",
                                (f"%{_nome.split(' (')[0]}%",))
                    _r = cur.fetchone()
                if not _r:
                    # fallback: palavra-chave do parêntese (ex.: 'Anta' em
                    # "Tapi'i (Anta — passos sobre a pedra)" → 'Anta (Veado)')
                    _par = _nome.split("(", 1)[-1].split(")", 1)[0]
                    _kw = re.sub(r"[\W_]+", " ", _sem_acentos(_par)).strip()
                    for _p in _kw.split()[:2]:
                        if len(_p) < 3:
                            continue
                        cur.execute(
                            "SELECT historia FROM arquetipo WHERE nome LIKE ? "
                            "OR nome LIKE ? "
                            "ORDER BY (nome = ?) DESC, id LIMIT 1",
                            (f"% {_p} %", f"{_p} %", _nome))
                        _r = cur.fetchone()
                        if _r:
                            break
                if _r:
                    _hist = _r[0] or ""
            except Exception:
                _hist = ""
            out.append((_nome, _rot, _hist))
    return out


def _resumo_mito(hist, limite=240):
    """Resumo mínimo de um mito: primeiras frases completas até `limite`
    caracteres (sem cortar palavra no meio)."""
    if not hist:
        return ""
    _t = " ".join(str(hist).split())
    if len(_t) <= limite:
        return _t
    _corte = _t[:limite]
    _ult = max(_corte.rfind(". "), _corte.rfind("! "), _corte.rfind("? "),
               _corte.rfind("; "))
    if _ult > limite // 2:
        return _t[:_ult + 1]
    _esp = _corte.rfind(" ")
    return _t[:_esp] + "…"


def _cartao_terra_ceu(m, vw, vh, rng, ceu_multis, asc_signo, historias=None):
    """Cartão 'TERRA & CÉU ANCESTRAL': o céu de VÁRIAS tradições (asterismos
    de Sol/Asc/Lua por cultura), agora ocupando o cartão inteiro com mais
    respiro — as plantas ganharam camada própria ('A FLORA DO TEU MAPA')."""
    lay, d = _base_cartao(vw, vh, rng)
    _fita(d, vw - 130, 4, rng=rng)
    _texto_traco(d, (24, 26), "TERRA & CÉU ANCESTRAL", _font(30, True),
                 fill=TINTA_CARD, contorno=(36, 28, 18), sw=3,
                 sombra=(24, 18, 10))
    d.text((vw - 30, 26), "o céu dos que vieram antes",
           font=_font(15, True), fill=LINHA_CARD, anchor="rm")
    d.text((24, 66), "o asterismo de Sol, Ascendente e Lua em várias leituras"
           " — uma ao lado da outra",
           font=_font(16), fill=LINHA_CARD, anchor="lm")

    luzes = [("Sol", m["planetas"]["Sol"]["signo"]),
             ("Asc", asc_signo),
             ("Lua", m["planetas"].get("Lua", {}).get("signo", ""))]
    # 3 colunas (uma por luz) quando há espaço; senão empilha
    n_luz = len(luzes)
    pad = 40
    col_w = (vw - 2 * pad - (n_luz - 1) * 40) / n_luz
    yy = 116
    col_alturas = []
    for li, (_nm, _sg) in enumerate(luzes):
        x = pad + li * (col_w + 40)
        d.text((x, yy), f"{_nm} em {_sg}",
               font=_font(21, True), fill=(150, 214, 130), anchor="lm")
        yy2 = yy + 34
        for _rot, _leitura in ceu_multis:
            _nome = str(_leitura.get(_sg, "") or "").strip()
            if not _nome or _nome in ("—", "?"):
                continue
            label = f"{_rot}:"
            lw_l = d.textlength(label, font=_font(15, True))
            d.text((x, yy2), label, font=_font(15, True),
                   fill=LINHA_CARD, anchor="lm")
            wide = col_w - lw_l - 10
            # no máximo 2 linhas por nome (com "…" na última se cortar):
            # coluna curta, sem invadir a seção de mitos nem a próxima luz
            _lns = _quebra_txt(_nome, wide, _font(15))
            if len(_lns) > 2:
                _lns = _lns[:2]
                _ult = _lns[-1]
                while (_ult and d.textlength(_ult + "…", font=_font(15))
                       > wide):
                    _ult = _ult[:-1]
                _lns[-1] = _ult + "…"
            for ln in _lns:
                d.text((x + lw_l + 8, yy2), ln, font=_font(15),
                       fill=TINTA_CARD, anchor="lm")
                yy2 += 25
            yy2 += 4
        col_alturas.append(yy2)

    # ── os mitos por trás dos nomes: histórias mínimas dos arquétipos que
    # estão sendo apontados aqui (preenche o respiro do cartão) ──
    if historias:
        # começa DEPOIS da coluna de asterismos mais alta (nada embolado)
        _hy = max(col_alturas) + 22
        _fita(d, vw - 130, _hy - 14, rng=rng)
        _texto_traco(d, (24, _hy), "OS MITOS POR TRÁS DOS NOMES", _font(22, True),
                     fill=TINTA_CARD, contorno=(36, 28, 18), sw=2,
                     sombra=(24, 18, 10))
        d.text((vw - 30, _hy), "o que cada figura conta",
               font=_font(13, True), fill=LINHA_CARD, anchor="rm")
        _hy += 34
        _wide = vw - 48
        # quantos mitos cabem no espaço restante (cada um com resumo de até
        # 3 linhas ≈ 100px; os sem história ocupam menos) — preenche o
        # cartão sem embolar nada
        _esp_mitos = vh - _hy - 30
        _n_mitos = min(len(historias), max(1, _esp_mitos // 100))
        for _nome, _rot, _hist in historias[:_n_mitos]:
            _res = _resumo_mito(_hist)
            _cab = f"{_nome}  ·  {_rot}"
            d.text((24, _hy), _cab, font=_font(16, True),
                   fill=(216, 186, 108), anchor="lm")
            _hy += 24
            if _res:
                for _ln in _quebra_txt(_res, _wide, _font(15))[:3]:
                    d.text((24, _hy), _ln, font=_font(15),
                           fill=TINTA_CARD, anchor="lm")
                    _hy += 22
            else:
                d.text((24, _hy), "(história ainda não registrada)",
                       font=_font_it(14), fill=(150, 130, 100), anchor="lm")
                _hy += 22
            _hy += 10
    return lay


CORPO_MAP = {
    "Áries": ("Cabeça", "face, olhos"),
    "Touro": ("Pescoço / garganta", "nuca, colar cervical"),
    "Gêmeos": ("Braços / peito", "ombros, mãos, pulmões"),
    "Câncer": ("Peito / estômago", "tórax, seios, abdômen alto"),
    "Leão": ("Coração / costas", "coluna dorsal, coração"),
    "Virgem": ("Abdômen / intestinos", "ventre, digestão"),
    "Libra": ("Rins / lombos", "região lombar, rins"),
    "Escorpião": ("Órgãos genitais", "região pélvica, bexiga, reto"),
    "Sagitário": ("Quadris / coxas", "coxas, fígado"),
    "Capricórnio": ("Joelhos", "ossos, pele, articulações"),
    "Aquário": ("Panturrilhas / tornozelos", "pernas, canelas"),
    "Peixes": ("Pés", "dedos, plantas, calcanhares"),
}


def _cartao_vinculos(m, vw, vh, rng, planta_por_signo):
    """Cartão 'VÍNCULOS DO CORPO E DA CURA': cada signo com a parte do corpo,
    onde o Quíron (asteróide da autocura) está hoje, e a planta regente de
    cura daquele signo."""
    lay, d = _base_cartao(vw, vh, rng)
    _fita(d, vw - 130, 4, rng=rng)
    _texto_traco(d, (24, 26), "VÍNCULOS DO CORPO E DA CURA", _font(26, True),
                 contorno=(250, 245, 225), sw=3, sombra=TINTA_FORTE)
    d.text((vw - 30, 26), "signo · parte do corpo · Quíron · planta",
           font=_font(13, True), fill=TINTA, anchor="rm")
    q_signo = (m["planetas"].get("Quíron", {}) or {}).get("signo", "")

    pad = 24
    col_w = (vw - 2 * pad) / 2
    top = 88
    rows = 6
    rh = (vh - top - 20) / rows
    for i, nome in enumerate(SIGNOS):
        col = i // rows
        row = i % rows
        x = pad + col * col_w
        y = top + row * rh
        culprit = nome == q_signo
        d.text((x, y), SIMB[nome], font=_sans(22), fill=(*COR[nome], 255),
               anchor="lm")
        parte, det = CORPO_MAP.get(nome, ("", ""))
        tx = x + 34
        ln1 = _quebra_txt(f"{nome}" + (f" — {parte}" if parte else ""),
                          col_w - 40, _font(15, True))
        for k, ln in enumerate(ln1[:2]):
            d.text((tx, y + k * 20), ln, font=_font(15, True),
                   fill=TINTA_FORTE, anchor="lm")
        y2 = y + (20 * len(ln1[:2]) + 2)
        if det:
            lin = f"região: {det}"
            if culprit:
                lin += "  ✦ Quíron aqui — sinal de autocura"
            for k, ln in enumerate(_quebra_txt(lin, col_w - 40, _font(13))[:2]):
                d.text((tx, y2 + k * 18), ln, font=_font(13),
                       fill=(150, 50, 30) if culprit else TINTA, anchor="lm")
            y2 += 18 * min(2, len(_quebra_txt(lin, col_w - 40, _font(13))))
        elif culprit:
            d.text((tx, y2), "✦ Quíron aqui — sinal de autocura",
                   font=_font(13, True), fill=(150, 50, 30), anchor="lm")
            y2 += 18
        pl = planta_por_signo.get(nome, "")
        if pl:
            d.text((tx, y2), f"planta da cura: {pl}",
                   font=_font_it(13), fill=(96, 66, 28), anchor="lm")
    return lay


def _fotos_planetas(m, vw, rng):
    """Cartão 'OS CORPOS CELESTES': as FOTOS REAIS (NASA/ESA) de todos os
    corpos, grandes e nítidas, com nome + grau + signo por baixo."""
    ordem = ["Sol", "Lua", "Mercúrio", "Vênus", "Marte",
             "Júpiter", "Saturno", "Urano", "Netuno", "Plutão"]
    corpo_map = {"Sol": "sol", "Lua": "lua", "Mercúrio": "mercurio",
                 "Vênus": "venus", "Marte": "marte", "Júpiter": "jupiter",
                 "Saturno": "saturno", "Urano": "urano", "Netuno": "netuno"}
    fotos = fotos_mapa()
    raio = 72
    total = len(ordem)
    espaco = min(250, (vw - 160) // total)
    inicio_x = vw // 2 - (total * espaco) // 2 + espaco // 2
    y_base = 74 + raio
    vh = y_base + raio + 74

    lay, d = _base_cartao(vw, vh, rng)
    _fita(d, 8, vh - 36, rng=rng)
    _texto_traco(d, (vw // 2, 30), "OS CORPOS CELESTES · fotos reais dos "
                 "telescópios (NASA/ESA)", _font(22, True),
                 contorno=(250, 245, 225), sw=3, anchor="mm")

    for i, nome in enumerate(ordem):
        pl = m["planetas"].get(nome, {})
        corpo = corpo_map.get(nome)
        path = None
        if corpo:
            for k, p in fotos.items():
                if corpo in k.split("/")[-1]:
                    path = p
                    break
        cxx = inicio_x + i * espaco
        cyy = y_base
        cor = COR_P.get(nome, (150, 150, 150))
        if path:
            try:
                fo = Image.open(path).convert("RGBA")
                fo = fo.resize((raio * 2, raio * 2), Image.LANCZOS)
                fo = _mascarar_redondo(fo, raio * 2)
                lay.paste(fo, (cxx - raio, cyy - raio), fo)
                d2 = ImageDraw.Draw(lay)
                d2.ellipse([cxx - raio - 4, cyy - raio - 4, cxx + raio + 4,
                            cyy + raio + 4], outline=PAPELAO, width=5)
            except Exception:
                d.ellipse([cxx - raio, cyy - raio, cxx + raio, cyy + raio],
                          fill=(*cor, 130))
        else:
            escura = tuple(max(22, int(c * 0.34)) for c in cor)
            d.ellipse([cxx - raio, cyy - raio, cxx + raio, cyy + raio],
                      fill=escura, outline=(*cor, 255), width=4)
            d.text((cxx, cyy + 2), GLIFO.get(nome, "★"), font=_sans(56),
                   fill=(255, 252, 243), anchor="mm")
        ret = " R" if pl.get("retrogrado") else ""
        sg = SIMB.get(pl.get("signo", ""), "")
        d.text((cxx, cyy + raio + 16), f"{GLIFO.get(nome, '?')} {nome}{ret}",
               font=_font(17, True), fill=TINTA_FORTE, anchor="mm")
        d.text((cxx, cyy + raio + 40),
               f"{sg} {pl.get('signo', '?')} · {pl.get('graus', 0):02d}° "
               f"{pl.get('min', 0):02d}'",
               font=_font(14), fill=(96, 66, 28), anchor="mm")
    return lay


# ══════════════════════════════════════════════════════════════════════
#  COMPOSIÇÃO PRINCIPAL (layout dinâmico)
# ══════════════════════════════════════════════════════════════════════

def gerar_obra(form, saida=None):
    data = form["data"]
    hora = form.get("hora", "12:00")
    local = form.get("local")
    lat = form.get("lat")
    lon = form.get("lon")
    nome = form.get("nome", "")
    cultura = form.get("cultura")
    tema = form.get("tema")
    feeling = form.get("feeling")
    figura = (form.get("figura") or "gravura").lower()
    traco = form.get("traco")
    mostrar_aspectos = bool(form.get("aspectos", True))
    mostrar_transitos = bool(form.get("transitos", False))
    mostrar_asteroides = bool(form.get("asteroides", False))

    local_c = _local_canonico(local)
    if lat is None and local_c:
        lat, lon = mapa_astral.LOCALIDADES.get(local_c, (None, None))
    if lat is None:
        raise ValueError("Local não reconhecido: " + str(local))
    tz = mapa_astral.tz_do_local(local_c)
    m = mapa_astral.calc(data, hora, lat, lon, tz_horas=tz)
    asc_signo = m["asc"].split(" ")[0]
    sol_signo = m["planetas"]["Sol"]["signo"]

    aspectos = _aspectos(m) if mostrar_aspectos else []
    transitos = _computa_transitos(form, lat, lon) if mostrar_transitos else None

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    # cultura REGIONAL do território de nascimento (sul do ES → capixaba;
    # RJ → carioca; outro lugar → None). Filtra os bancos regionais quando
    # a cultura é multi (None): nunca aplicamos Sul Capixaba a quem nasceu
    # fora do sul do ES.
    cultura_territorio = _cultura_do_territorio(local_c)
    # ── anti-repetição entre posições: cada arquétipo entra uma vez no mapa
    # (relevância primeiro; variedade quando há alternativa). A ordem de
    # busca é Asc → Sol → Lua → Mercúrio/Vênus/Marte → destaques → tabela.
    _usados = set()
    arq_asc = buscar_arquetipos_do_signo(cur, asc_signo, cultura,
                                         cultura_territorio, _usados)
    _usados |= {a[1].split(" (")[0] for a in arq_asc}
    arq_sol = buscar_arquetipos_do_signo(cur, sol_signo, cultura,
                                         cultura_territorio, _usados)
    _usados |= {a[1].split(" (")[0] for a in arq_sol}
    arq_lua = buscar_arquetipos_do_signo(
        cur, m["planetas"].get("Lua", {}).get("signo", ""), cultura,
        cultura_territorio, _usados)
    _usados |= {a[1].split(" (")[0] for a in arq_lua}
    # arquétipos dos signos de Mercúrio, Vênus e Marte (fileira principal)
    _arqs_principais = {}
    for _nm in ("Mercúrio", "Vênus", "Marte"):
        _sg = m["planetas"].get(_nm, {}).get("signo", "")
        _arqs_principais[_nm] = (buscar_arquetipos_do_signo(
            cur, _sg, cultura, cultura_territorio, _usados) if _sg else [])
        _usados |= {a[1].split(" (")[0]
                    for a in _arqs_principais[_nm]}

    # ── corpos: os 10 planetas + Quíron + os asteróides arquetípicos
    # (Lilith, Ceres, Pallas, Juno, Vesta) SEMPRE na tabela — todos têm
    # posição na efeméride; na roda, os asteróides extras só quando
    # assinalado, para a mandala não ficar cheia ──
    nomes_corpos = PLANETAS_10 + ["Quíron"]
    nomes_corpos += [n for n in ASTEROIDES_EXTRA if n in m["planetas"]]
    corpos_roda = PLANETAS_10 + ["Quíron"]
    if mostrar_asteroides:
        corpos_roda += [n for n in ASTEROIDES_EXTRA if n in m["planetas"]]

    # ── arquétipos por POSICIONAMENTO (planeta no signo, catálogo nosso) ──
    arqs_planetas = {}
    for _nm in nomes_corpos:
        _pl = m["planetas"].get(_nm, {})
        _sg = _pl.get("signo", "")
        arqs_planetas[_nm] = arquétipo_por_planeta(cur, _nm, _sg, cultura,
                                                    cultura_territorio,
                                                    _usados)
        _usados |= {a[1].split(" (")[0] for a in arqs_planetas[_nm]}

    # ── signos em destaque para a fileira de 4 cartões: escolha por ANÁLISE
    # do mapa — stelliums (3+ corpos), signo da Lua, dignidades planetárias
    # (domicílio/exaltação), Meio do Céu e regências (do Ascendente e do
    # Sol). Cada mapa sai com uma combinação diferente ──
    _corpos_por_signo = {}
    for _nm in nomes_corpos:
        _sg = m["planetas"].get(_nm, {}).get("signo", "")
        if _sg:
            _corpos_por_signo.setdefault(_sg, []).append(_nm)
    # signos que já aparecem nas fileiras de cima (Sol/Lua/Asc + Mercúrio/
    # Vênus/Marte) — não se repetem nos destaques
    _linha1_signos = {sol_signo, asc_signo,
                      m["planetas"].get("Lua", {}).get("signo", ""),
                      m["planetas"].get("Mercúrio", {}).get("signo", ""),
                      m["planetas"].get("Vênus", {}).get("signo", ""),
                      m["planetas"].get("Marte", {}).get("signo", "")}
    _linha1_signos.discard("")
    # dignidades essenciais (domicílio, exaltação, exílio, queda) — tabela
    # clássica no banco `dignidade`; se faltar, usa a tabela padrão embutida
    _DIGNIDADES = {}
    try:
        cur.execute("SELECT signo, domicilio, exaltacao, exilio, queda "
                    "FROM dignidade")
        for _sg, _dom, _exal, _exil, _queda in cur.fetchall():
            _DIGNIDADES[_sg] = (_dom, _exal, _exil, _queda)
    except sqlite3.Error:
        _DIGNIDADES = {}
    if not _DIGNIDADES:
        _DIGNIDADES = {"Áries": ("Marte", "Sol", "Vênus", "Saturno"),
                       "Touro": ("Vênus", "Lua", "Plutão", None),
                       "Gêmeos": ("Mercúrio", None, "Júpiter", None),
                       "Câncer": ("Lua", "Júpiter", "Saturno", "Marte"),
                       "Leão": ("Sol", None, "Urano", None),
                       "Virgem": ("Mercúrio", "Mercúrio", "Netuno", "Vênus"),
                       "Libra": ("Vênus", "Saturno", "Marte", "Sol"),
                       "Escorpião": ("Plutão", None, "Vênus", "Lua"),
                       "Sagitário": ("Júpiter", None, "Mercúrio", None),
                       "Capricórnio": ("Saturno", "Marte", "Lua", "Júpiter"),
                       "Aquário": ("Urano", None, "Sol", None),
                       "Peixes": ("Netuno", "Vênus", "Mercúrio", None)}
    _REGENTES = {"Áries": "Marte", "Touro": "Vênus", "Gêmeos": "Mercúrio",
                 "Câncer": "Lua", "Leão": "Sol", "Virgem": "Mercúrio",
                 "Libra": "Vênus", "Escorpião": "Plutão",
                 "Sagitário": "Júpiter", "Capricórnio": "Saturno",
                 "Aquário": "Urano", "Peixes": "Netuno"}
    _mc_signo = (m.get("mc") or "").split(" ")[0]
    _asc_regente = _REGENTES.get(asc_signo, "")
    _sol_regente = _REGENTES.get(sol_signo, "")
    _pontos = {}
    _motivos = {}
    for _sg, _cs in _corpos_por_signo.items():
        # a última fileira NÃO repete as posições principais: signos de
        # Sol/Lua/Asc/Mercúrio/Vênus/Marte ficam de fora — ela deve
        # acrescentar informação nova, não repetir o que já se viu
        if _sg in _linha1_signos:
            continue
        _p = len(_cs)
        _m = []
        if len(_cs) >= 3:
            _p += 2                       # stellium
            _m.append(f"stellium de {len(_cs)}")
        if "Lua" in _cs:
            _p += 2                       # a Lua é sempre relevante
            _m.append("Lua no signo")
        _dom, _exal, _exil, _queda = _DIGNIDADES.get(_sg, (None, None, None, None))
        for _c in _cs:
            if _c == _dom:
                _p += 2                   # domicílio
                _m.append(f"{_c} em domicílio")
            elif _c == _exal:
                _p += 2                   # exaltação
                _m.append(f"{_c} em exaltação")
        if _sg == _mc_signo:
            _p += 1                       # Meio do Céu
            _m.append("Meio do Céu")
        if _asc_regente in _cs or _sol_regente in _cs:
            _p += 1                       # regência do Asc/Sol
            if _asc_regente in _cs:
                _m.append(f"{_asc_regente} rege o Ascendente em {asc_signo}")
            else:
                _m.append(f"{_sol_regente} rege o Sol em {sol_signo}")
        # Sol nos últimos graus do signo (cúspide): o signo SEGUINTE recebe
        # a luz do Sol que já está "chegando" — informação nova e honesta
        _sg_sol = m["planetas"].get("Sol", {}).get("signo", "")
        _gr_sol = m["planetas"].get("Sol", {}).get("graus", 0)
        if _sg == _sg_sol and _gr_sol >= 27:
            _prox = SIGNOS[(SIGNOS.index(_sg_sol) + 1) % 12]
            _p += 1
            _m.append(f"Sol na cúspide de {_prox} ({_gr_sol}°)")
        # planetas exteriores e asteroides trazem informação nova à última
        # fileira (o usuário já viu os seis primeiros nas fileiras de cima)
        if any(c in _cs for c in ("Júpiter", "Saturno", "Urano", "Netuno",
                                  "Plutão")):
            _p += 1
            _m.append("planetas exteriores")
        if any(c in _cs for c in ASTEROIDES_EXTRA):
            _p += 1
            _m.append("asteroides arquetípicos")
        _pontos[_sg] = _p
        _motivos[_sg] = _m
    _rank = sorted(((sg, cs) for sg, cs in _corpos_por_signo.items()
                    if sg not in _linha1_signos),
                   key=lambda t: (-_pontos.get(t[0], 0), -len(t[1]), t[0]))
    _destaques = _rank[:4]
    _arqs_destaques = {sg: buscar_arquetipos_do_signo(cur, sg, cultura,
                                                      cultura_territorio,
                                                      _usados)
                       for sg, _ in _destaques}
    _usados |= {a[1].split(" (")[0]
                for _l in _arqs_destaques.values() for a in _l}

    # ── plantas regentes dos SIGNOS em destaque (posicionamento, sem
    # repetir: cada signo aparece uma vez, com os astros que estão nele) ──
    plantas_destaque = []
    try:
        import flora as _flora
        _corpos_por_signo = {}
        for _nm in nomes_corpos:
            _sg = m["planetas"].get(_nm, {}).get("signo", "")
            if _sg:
                _corpos_por_signo.setdefault(_sg, []).append(_nm)
        # ordem: Sol, Asc, Lua; depois os stelliums (mais corpos primeiro)
        _ordem = [sol_signo, asc_signo,
                  m["planetas"].get("Lua", {}).get("signo", "")]
        _resto = sorted(
            [(sg, cs) for sg, cs in _corpos_por_signo.items()
             if sg not in _ordem],
            key=lambda t: (-len(t[1]), t[0]))
        _candidatos = [(sg, _corpos_por_signo.get(sg, [])) for sg in _ordem
                       if _corpos_por_signo.get(sg)] + _resto
        _vistos = set()
        for _sg, _corpos in _candidatos:
            if _sg in _vistos or len(plantas_destaque) >= 3:
                continue
            _vistos.add(_sg)
            try:
                _r = _flora.planta_regente(cur, _sg)
            except Exception:
                _r = None
            if not _r or not _r.get("plantas"):
                continue
            plantas_destaque.append({
                "signo": _sg, "corpos": _corpos,
                "orixa": _r["orixa"], "plantas": _r["plantas"],
            })
    except Exception:
        pass

    # ── céus de várias tradições (asterismos de Sol/Asc/Lua por cultura) ──
    ceu_multis = []
    try:
        import json as _json
        cur.execute("SELECT id, leitura_signos FROM cultura_ceu "
                    "WHERE origem='projeto'")
        _cand = []
        for _rid, _leitura in cur.fetchall():
            if _leitura and _leitura.strip():
                try:
                    _d = _json.loads(_leitura)
                except Exception:
                    continue
                _rot = {"nossa:indigena": "indígena",
                        "nossa:tukano": "tukano",
                        "nossa:tupi": "tupi",
                        "nossa:afro-brasileiro": "afro-brasileiro",
                        "nossa:capixaba-sul": "capixaba-sul",
                        "nossa:mapuche": "mapuche",
                        "nossa:zodiaco": "zodíaco",
                        "nossa:regional-capixaba": "regional capixaba",
                        "nossa:regional-carioca": "regional carioca",
                        "nossa:folclore-brasileiro": "folclore brasileiro"}.get(
                    _rid, _rid.split(":")[-1])
                _cand.append((_rot, _d))
        pref = ["indígena", "tukano", "tupi", "afro-brasileiro"]
        _cand.sort(key=lambda t: (pref.index(t[0])
                                  if t[0] in pref else 99, t[0]))
        ceu_multis = _cand[:4]
    except Exception:
        ceu_multis = []
    # histórias dos asterismos apontados no cartão terra & céu (busca com o
    # banco ainda aberto; o desenho usa o resumo depois do close)
    _luzes_tc = [("Sol", m["planetas"]["Sol"]["signo"]),
                 ("Asc", asc_signo),
                 ("Lua", m["planetas"].get("Lua", {}).get("signo", ""))]
    _hist_tc = _historias_arquetipos(cur, ceu_multis, _luzes_tc)
    conn.close()

    W = 2800
    rng = random.Random(hash(data) + hash(nome))
    # a figura de cada arquétipo é sorteada com esta semente: o mesmo mapa sai
    # sempre igual, mapas de pessoas diferentes saem diferentes
    _SEMENTE_MAPA[0] = "%s|%s|%s|%s" % (data, hora, nome, str(local_c))
    _sementes_verso = tuple(
        a[1].split(" (")[0]
        for a in list(arq_asc) + list(arq_sol) if a)
    _sementes_verso += ("Sol", "Lua", asc_signo, sol_signo)
    _refs_verso = []
    verso = gerar_verso(tema, feeling, asc_signo, sol_signo,
                        form.get("mensaje"), rng=rng, nome=nome,
                        sementes=_sementes_verso,
                        destaques=[(sg, cs) for sg, cs in _destaques],
                        referencias=_refs_verso)

    # ── detecção de conjunção cazimi (rara): Sol + Mercúrio no mesmo grau ──
    cazimi = None
    if "Mercúrio" in m["planetas"]:
        sol = m["planetas"]["Sol"]
        mer = m["planetas"]["Mercúrio"]
        sep = abs(sol["lon"] - mer["lon"]) % 360
        sep = min(sep, 360 - sep)
        if sep < 0.4:  # ~24 arcmin, dentro do cazimi (17')
            cazimi = {"separa": sep, "signo": sol["signo"],
                      "graus": (sol["graus"] + sol["min"] / 60.0)}

    # ── proporção dos elementos (fogo/terra/água/ar) ──
    elem_qtd = {"fogo": 0, "terra": 0, "água": 0, "ar": 0}
    for nm in PLANETAS_10:
        e = ELEM.get(m["planetas"].get(nm, {}).get("signo", ""))
        if e:
            elem_qtd[e] += 1
    elem_qtd[ELEM.get(asc_signo, "terra")] += 1  # inclui o Ascendente

    _carregar_recilaveis()

    MOL = 56          # moldura reciclável (espessura)
    gap = 66
    # ── bloco de título (abaixo da moldura p/ não cortar) ──
    titulo_h = 470
    # ── roda (maior p/ as lacunas de informação serem legíveis) ──
    r_ext, r_int = 835, 662
    # folga abaixo/ao redor da roda p/ medalhões (r_ext+84) e o anel roxo de
    # trânsitos (r_ext+116, com legenda em r_ext+180) NÃO encostarem no que
    # vem depois (nem no título); a folga também abriga a cruz do horizonte
    roda_h = r_ext * 2 + 560

    # ── cartões ──
    margem = 160
    card_w = W - 2 * margem
    # alturas equilibradas: os arquétipos não podem ocupar mais que a tabela
    # fileira 1 (Sol/Lua/Asc) mais alta — cartões largos, texto com respiro
    arq_h = 640
    arq2_h = 560
    arq3_h = 500
    # plantas ganharam camada própria (entre os destaques e a tabela)
    plantas_h = 920
    # elementos + planetas + aspectos vivem no MESMO cartão ("tabela");
    # altura justa: a coluna da direita termina em ~750 com aspectos, ~660 sem
    # com asteróides extras a lista cresce (16 corpos) → cartão mais alto
    # com os asteróides sempre na tabela (16 corpos × 58px = 928px + cabeçalho
    # ≈ 1024px) o cartão precisa ser mais alto que antes
    tab_h = 1060 if (mostrar_aspectos and aspectos) else 1040
    asp_h = 0  # aspectos são mesclados no card da tabela de planetas

    # ── verso ──
    # 3 linhas da estrofe-colagem do caderno + rótulo + versos + colofon
    verso_h = 56 * (len(verso) + 8) + 360

    # total (empilha do topo com margem da moldura)
    terra_ceu_h = 1150
    order = ["titulo", "roda"]
    order += ["arq", "arq2", "arq3", "tabela", "plantas", "terra_ceu", "verso"]
    heights = {"titulo": titulo_h, "roda": roda_h,
               "aspectos": asp_h, "arq": arq_h, "arq2": arq2_h,
               "arq3": arq3_h, "plantas": plantas_h,
               "tabela": tab_h, "terra_ceu": terra_ceu_h,
               "verso": verso_h}
    y_positions = {}
    ycur = MOL + 16
    for seg in order:
        y_positions[seg] = ycur
        ycur += heights[seg] + gap
    H_total = ycur + 60

    img = _papel_kraft(W, H_total, rng)
    d = ImageDraw.Draw(img)
    # folha central mais clara (recorte de papel) — feita como aguada,
    # com borda úmida e contorno à mão (não é um retângulo chapado)
    fol = _layer(img.size)
    mascF = Image.new("L", img.size, 0)
    ImageDraw.Draw(mascF).rounded_rectangle(
        [margem - 24, MOL + 6, W - margem + 24, H_total - 80],
        radius=42, fill=255)
    _blit(fol, _aguada(mascF, (216, 198, 158), rng, tons=240, r0=16, r1=290,
                       blur=9, alpha=(80, 132)))
    _borda_pintada(ImageDraw.Draw(fol), margem - 18, MOL + 10,
                   W - margem + 18, H_total - 74, (*PAPEL_KRAFT_ESC, 170), 2,
                   rng, n=48)
    _blit(img, fol)
    d = ImageDraw.Draw(img)

    def desenha_cabecalho(img, d):
        Y = y_positions["titulo"]
        # ── cabeçalho: placa escura com borda gravada; texto claro por cima
        # (contraste real com o papel texturizado) e bastante ar entre o
        # RECICLE e o nome do consultante, que não se atropelam ──────────
        _placa(img, (margem - 24, Y + 8, W - margem + 24, Y + 372),
               cor=(46, 36, 22), radius=34)
        # três estrelas douradas flanqueando o título
        for sx, sim in [(W // 2 - 96, "☉"), (W // 2 + 96, "✶"),
                        (W // 2, "✦")]:
            d.text((sx, Y + 58), sim, font=_sans(54), fill=(216, 186, 108),
                   anchor="mm")
        _letreiro(img, (W // 2, Y + 62), "PLANETÁRIO  ASTROLÓGICO",
                  _perg(82, True), fill=(255, 251, 236),
                  stroke=(38, 28, 16), sombra=(190, 74, 50),
                  stroke_w=6, desloc_sombra=(6, 7), rota=0, rng=rng,
                  spray=(10, (38, 28, 16)))
        _letreiro(img, (W // 2, Y + 132), "·  R E C I C L E  ·", _sans(50),
                  fill=(248, 242, 224), stroke=(120, 54, 36),
                  sombra=None, stroke_w=4, rota=0, rng=rng)
        # filete duplo sob o RECICLE, separando do nome
        _r1 = Y + 180
        d.line([W // 2 - 470, _r1, W // 2 - 150, _r1],
               fill=(196, 60, 44, 230), width=4)
        d.line([W // 2 + 150, _r1, W // 2 + 470, _r1],
               fill=(196, 60, 44, 230), width=4)
        d.line([W // 2 - 440, _r1 + 7, W // 2 - 180, _r1 + 7],
               fill=(216, 186, 108, 210), width=2)
        d.line([W // 2 + 180, _r1 + 7, W // 2 + 440, _r1 + 7],
               fill=(216, 186, 108, 210), width=2)
        yy = Y + 248
        if nome:
            _cor_nome = COR_NOME_CLARO[abs(hash((data, nome))) % len(
                COR_NOME_CLARO)]
            # ornamentos laterais do nome (pequenos, fora do texto)
            for sx, sim in [(W // 2 + 320, "☉"), (W // 2 - 320, "✶")]:
                d.text((sx, yy), sim, font=_sans(34), fill=(216, 186, 108),
                       anchor="mm")
                d.line([sx - 100, yy, sx - 40, yy],
                       fill=(*TINTA_FORTE, 160), width=3)
                d.line([sx + 40, yy, sx + 100, yy],
                       fill=(*TINTA_FORTE, 160), width=3)
            _letreiro(img, (W // 2, yy), nome.upper(), _font(46, True),
                      fill=_cor_nome, stroke=(38, 28, 16),
                      sombra=None, stroke_w=3, rota=0, rng=rng)
            yy += 60
        elif tema:
            d.text((W // 2, yy), f"«{tema.upper()}»", font=_font(40, True),
                   fill=(250, 246, 230), anchor="mm")
            yy += 64
        else:
            d.text((W // 2, yy), "MAPA DO CÉU DE NASCIMENTO",
                   font=_font(40, True), fill=(250, 246, 230), anchor="mm")
            yy += 64
        sub = f"{data}  ·  {hora}  ·  {local}"
        if lat is not None:
            sub += (f"  ·  {abs(lat):.4f}° {'S' if lat < 0 else 'N'}, "
                    f"{abs(lon):.4f}° {'W' if lon < 0 else 'E'}")
        d.text((W // 2, yy), sub, font=_font(28), fill=(228, 206, 150),
               anchor="mm")
        yy += 44
        d.text((W // 2, yy),
               f"Ascendente {m['asc']}  ·  Meio do Céu {m['mc']}",
               font=_font(24, True), fill=(238, 122, 88), anchor="mm")
    desenha_cabecalho(img, d)

    # roda (virada p/ o ASC ficar no horizonte leste, à esquerda)
    cy_roda = y_positions["roda"] + roda_h / 2
    _roda(img, m, W // 2, cy_roda, r_ext, r_int, rng,
          aspectos=aspectos, transitos=transitos,
          asc_lon=m["casas"][0]["lon"], corpos=set(corpos_roda))
    _eixos_horizonte(img, W // 2, cy_roda, r_ext, rng,
                     m["casas"][0]["lon"],
                     m["casas"][9]["lon"] if len(m.get("casas", [])) > 9 else 83)
    _badge_cazimi(img, m, cazimi, W // 2, cy_roda, r_ext, rng)
    _bioconstrucao_da_roda(img, W, H_total, W // 2, cy_roda, r_ext, rng)

    # ── fileira 1: as 3 luzes (Sol, Lua, Ascendente) — cartões largos, com
    # as correspondências do signo onde cada um está (posicionamento) e a
    # FOTO do corpo no canto. Título LIMPO: "Sol em Capricórnio" (sem a
    # palavra 'arquétipo' e sem 'expressões do' — o subtítulo da seção diz
    # que são cartões de expressões culturais) ──
    def _grau_curto(_nm):
        _pl = m["planetas"].get(_nm, {})
        if not _pl:
            return ""
        return f"{_pl.get('graus', 0)}°{_pl.get('min', 0):02d}′"

    ay = y_positions["arq"]
    card_h_arq = arq_h - 8
    # legenda discreta da seção (acima da fileira, no respiro da roda)
    d.text((margem, ay - 34), "cartões de expressões culturais",
           font=_font(17, True), fill=(196, 170, 128), anchor="lm")
    _luzes = [
        ("Sol", sol_signo, arq_sol),
        ("Lua", m["planetas"].get("Lua", {}).get("signo", ""), arq_lua),
        ("Ascendente", asc_signo, arq_asc),
    ]
    w3 = (card_w - 2 * 12) // 3
    for i, (_nm, _sg, _arqs) in enumerate(_luzes):
        _tit = f"{_nm} em {_sg}"
        lay_c = _cartao_arquetipos(m, _tit, _sg, _arqs, w3, card_h_arq, rng,
                                   ascii_mode=(figura == "ascii"),
                                   subtitulo=_grau_curto(_nm) or _sg,
                                   corpo=_nm)
        img.paste(lay_c, (margem + i * (w3 + 12), ay), lay_c)
    # linha de ligação entre os cartões (fio do colar de medalhões)
    _fio(img, margem, ay, margem + 2 * (w3 + 12) + w3, ay, rng)

    # ── fileira 2: Mercúrio, Vênus e Marte (3 cartões médios) ──
    ay2 = y_positions["arq2"]
    card_h_arq2 = arq2_h - 8
    for i, _nm in enumerate(("Mercúrio", "Vênus", "Marte")):
        _sg = m["planetas"].get(_nm, {}).get("signo", "")
        _arqs = _arqs_principais.get(_nm, [])
        _tit = f"{_nm} em {_sg}"
        lay_c = _cartao_arquetipos(m, _tit, _sg, _arqs, w3, card_h_arq2, rng,
                                   ascii_mode=(figura == "ascii"),
                                   subtitulo=_grau_curto(_nm) or _sg,
                                   corpo=_nm)
        img.paste(lay_c, (margem + i * (w3 + 12), ay2), lay_c)
    _fio(img, margem, ay2, margem + 2 * (w3 + 12) + w3, ay2, rng)

    # ── fileira 3: os SIGNOS que a análise do mapa escolheu (stelliums,
    # dignidades, regências, MC): até 4 cartões compactos, medalhões menores ──
    if _destaques:
        ay3 = y_positions["arq3"]
        card_h_arq3 = arq3_h - 8
        n_st = len(_destaques)
        w_st = (card_w - (n_st - 1) * 12) // n_st
        for i, (_sg2, _corpos2) in enumerate(_destaques):
            _arqs2 = _arqs_destaques.get(_sg2, [])
            # o subtítulo mostra POR QUE o signo entrou na fileira (stellium,
            # dignidade, regência com nome do planeta e signo, Meio do Céu...)
            # e, se sobrar espaço, os astros nele — explicação honesta
            _mot = _motivos.get(_sg2, [])[:3]
            _plan = ", ".join(_corpos2)
            _sub = " · ".join(_mot)
            if _sub and _plan and len(_sub) + len(_plan) + 3 <= 64:
                _sub = f"{_sub} — {_plan}"
            elif not _sub:
                _sub = _plan
            _corpo2 = _corpos2[0] if _corpos2 else None
            lay_t = _cartao_arquetipos(m, _sg2,
                                       _sg2, _arqs2, w_st, card_h_arq3, rng,
                                       ascii_mode=(figura == "ascii"),
                                       subtitulo=_sub, corpo=_corpo2,
                                       compact=(n_st > 1))
            img.paste(lay_t, (margem + i * (w_st + 12), ay3), lay_t)
        _fio(img, margem, ay3, margem + (n_st - 1) * (w_st + 12) + w_st,
             ay3, rng)

    # ── tabela (elementos + planetas + aspectos, juntos) — a "planilha" ──
    ty = y_positions["tabela"]
    lay_tab = _cartao_tabela(m, card_w, tab_h - 8, rng,
                             aspectos=aspectos if (mostrar_aspectos and aspectos) else None,
                             arqs_planetas=arqs_planetas,
                             elem_qtd=elem_qtd, asc_signo=asc_signo,
                             nomes_corpos=nomes_corpos,
                             dignidades=_DIGNIDADES)
    img.paste(lay_tab, (margem, ty), lay_tab)

    # ── plantas regentes (flora) JUNTO ao terra & céu ancestral, logo
    # depois da planilha: a natureza do teu mapa e os céus das tradições
    # formam o mesmo bloco de encerramento ──
    py = y_positions["plantas"]
    lay_pl = _cartao_plantas(m, card_w, plantas_h - 8, rng, plantas_destaque)
    img.paste(lay_pl, (margem, py), lay_pl)

    # terra & céu ancestral (os céus de várias tradições, agora com espaço)
    tcy = y_positions["terra_ceu"]
    lay_tc = _cartao_terra_ceu(m, card_w, terra_ceu_h - 8, rng,
                               ceu_multis, asc_signo, historias=_hist_tc)
    img.paste(lay_tc, (margem, tcy), lay_tc)

    # verso — a estrofe única do mapa, em placa escura (texto claro sobre o
# papel texturizado, e a estrofe ocupa a folga com respiro de letra)
    vy = y_positions["verso"]
    _plaque_b = (margem - 24, vy + 12, W - margem + 24, vy + 420)
    _placa(img, _plaque_b, cor=(46, 36, 22), radius=34)
    yy = vy + 52
    d.text((W // 2, yy), "a poesia do teu mapa", font=_font(26, True),
           fill=(216, 186, 108), anchor="mm")
    d.text((W // 2, yy + 30), "colagem do caderno do Astro Pisco",
           font=_font(16, True), fill=(196, 170, 128), anchor="mm")
    yy += 76
    _n_linhas = len(verso)
    _pitch = 60 if _n_linhas <= 5 else (52 if _n_linhas <= 6 else 46)
    for linha in verso:
        d.text((W // 2, yy), linha, font=_font(30), fill=(250, 246, 232),
               anchor="mm")
        yy += _pitch
    yy += 20
    d.text((W // 2, vy + 452),
           "posições Swiss Ephemeris · zodíaco tropical · "
           "imagens NASA/ESA e Wikimedia Commons (domínio público / CC)",
           font=_font(15), fill=TINTA_FORTE, anchor="mm")
    yy = vy + 520
    # ── identidade: logo ao centro, com a faixa de créditos logo abaixo,
    # descendo até quase a borda do papel (ocupa a folga do fim da página)
    _logo_ok = False
    _lr = 120  # raio do selo da logo (bom tamanho, centralizado)
    if os.path.exists(LOGO_PLANETARIO):
        try:
            _crop = _crop_circular(LOGO_PLANETARIO, 0, 0, _lr)
            if _crop:
                _fx = W // 2
                _fy = yy + _lr + 40
                d.ellipse([_fx - _lr, _fy - _lr, _fx + _lr, _fy + _lr],
                          fill=(30, 26, 18))
                d.ellipse([_fx - _lr, _fy - _lr, _fx + _lr, _fy + _lr],
                          outline=(224, 210, 168, 255), width=7)
                img.paste(_crop, (int(_fx - _lr), int(_fy - _lr)), _crop)
                d = ImageDraw.Draw(img)
                d.ellipse([_fx - _lr, _fy - _lr, _fx + _lr, _fy + _lr],
                          outline=(255, 240, 200, 200), width=3)
                _logo_ok = True
        except Exception:
            _logo_ok = False
    if _logo_ok:
        _ty = yy + _lr * 2 + 118
        d.text((W // 2, _ty), LINK_LABEL, font=_font(44, True),
               fill=AZUL, anchor="mm")
        _ty += 56
        d.text((W // 2, _ty),
               "pintura única desta configuração — os desenhos não se repetem, "
               "como cada mapa é uma imagem só.", font=_font(24),
               fill=TINTA_FORTE, anchor="mm")
        _ty += 54
        d.text((W // 2, _ty),
               "· desenvolvido com software livre de código aberto ·",
               font=_font(20, True), fill=(104, 76, 42), anchor="mm")
        _ty += 40
        d.text((W // 2, _ty),
               "« coletei dos astros o que coubesse no teu nome »",
               font=_font(17, True), fill=(150, 118, 66), anchor="mm")

    # traço à mão → selo no canto do cabeçalho, sobre papel que garante
    # contraste (claro para tinta escura, escuro para tinta clara)
    if traco and os.path.exists(traco):
        try:
            _ti = Image.open(traco).convert("RGBA")
            _ti = _ti.resize((max(16, int(W * 0.14)),
                              max(16, int(_ti.height / max(_ti.width, 1)
                                          * W * 0.14))), Image.LANCZOS)
            # estilo de tinta do traço (lápis, carvão, caligráfico, ...)
            _ti = _aplicar_estilo_traco(_ti, form.get("traco_estilo"), rng)
            _ta = np.asarray(_ti)
            _tm = _ta[..., 3] > 60
            if _tm.any():
                _luz = int(_ta[_tm][:, :3].mean())
                _esc = _luz > 150
                _papel = (56, 44, 30) if _esc else (233, 217, 177)
                _borda = (206, 180, 128) if _esc else (146, 116, 72)
                L, H = _ti.width + 44, _ti.height + 44
                _nota = Image.new("RGBA", (L, H), (0, 0, 0, 0))
                _nd = ImageDraw.Draw(_nota)
                _nd.rounded_rectangle([6, 6, L - 7, H - 7], radius=16,
                                      fill=(*_papel, 244))
                _nd.rounded_rectangle([6, 6, L - 7, H - 7], radius=16,
                                      outline=(*_borda, 200), width=2)
                _nota.paste(_ti, (22, 22), _ti)
                _nota = _nota.rotate(rng.uniform(-2.5, 2.5), expand=True,
                                     resample=Image.BICUBIC)
                _nx = (W - margem + 24) - _nota.width - 14
                _ny = y_positions["titulo"] + 54
                img.paste(_nota, (_nx, _ny), _nota)
        except Exception:
            pass

    # moldura reciclável por cima
    _moldura_reciclavel(img, W, H_total, rng)
    _carregar_recilaveis()

    # granulado do papel por cima de tudo (cara de pintura, não de pixel)
    _grano_papel(img, rng, forca=10, fibras=130)

    if saida is None:
        saida = f"{DIR_ARQ}/../mapas/obra-{data}.png"
    os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
    img.save(saida, quality=95)

    # ── registro LEVE do mapa (sem imagem): dados do pedido + posições,
    # para relatórios e o futuro site — nunca pode quebrar a geração ──
    try:
        import json as _json
        import time as _time
        _log_p = "/mnt/dados/home-italivre/iastro-ia/mapas_solicitados.jsonl"
        _reg = {
            "quando": _time.strftime("%Y-%m-%d %H:%M:%S"),
            "data": data, "hora": hora, "local": local_c,
            "lat": lat, "lon": lon, "tz": tz,
            "nome": nome, "cultura": cultura, "tema": tema,
            "figura": figura, "traco": bool(traco),
            "aspectos": mostrar_aspectos, "transitos": mostrar_transitos,
            "asteroides": mostrar_asteroides,
            "asc": m["asc"], "mc": m.get("mc", ""),
            "sol": m["planetas"]["Sol"]["signo"],
            "lua": m["planetas"].get("Lua", {}).get("signo", ""),
            "planetas": {k: {"signo": v.get("signo", ""),
                             "graus": v.get("graus", 0),
                             "min": v.get("min", 0),
                             "retrogrado": bool(v.get("retrogrado"))}
                         for k, v in m["planetas"].items()},
            "destaques": [sg for sg, _ in _destaques],
            "verso": verso,
            "verso_refs": _refs_verso,
        }
        with open(_log_p, "a", encoding="utf-8") as _lf:
            _lf.write(_json.dumps(_reg, ensure_ascii=False) + "\n")
    except Exception:
        pass

    return {
        "caminho": saida,
        "dados": m,
        "asc_signo": asc_signo,
        "sol_signo": sol_signo,
        "verso": verso,
        "verso_refs": _refs_verso,
        "arquetipos_asc": [a[1].split(" (")[0] for a in arq_asc],
        "arquetipos_sol": [a[1].split(" (")[0] for a in arq_sol],
    }


# ══════════════════════════════════════════════════════════════════════

def _erodir_alfa(alfa, r=1):
    """Afina a tinta (lápis): erosão morfológica de r px no canal alfa."""
    from PIL import ImageFilter as _IF
    _f = _IF.MinFilter(3) if r <= 1 else _IF.MinFilter(5)
    return np.asarray(Image.fromarray(alfa).filter(_f))


def _dilatar_alfa(alfa, r=2):
    """Engrossa a tinta (carvão): dilatação morfológica de r px."""
    from PIL import ImageFilter as _IF
    _f = _IF.MaxFilter(5) if r <= 2 else _IF.MaxFilter(7)
    return np.asarray(Image.fromarray(alfa).filter(_f))


def _estrela_4(d, cx, cy, r, cor):
    """Estrela de 4 pontas (dois losangos finos cruzados) — pincel estrelas."""
    d.line([cx, cy - r, cx + r * 0.28, cy, cx, cy + r, cx - r * 0.28, cy,
            cx, cy - r], fill=cor, width=1)
    d.line([cx - r, cy, cx, cy - r * 0.28, cx + r, cy, cx, cy + r * 0.28,
            cx - r, cy], fill=cor, width=1)


def _cadeia_vizinho(pts):
    """Encadeia pontos pelo vizinho mais próximo (pincel constelação)."""
    pts = list(pts)
    if not pts:
        return []
    cadeia = [pts.pop(0)]
    while pts:
        ux, uy = cadeia[-1]
        melhor, mi = None, 0
        for i, (px, py) in enumerate(pts):
            d2 = (ux - px) ** 2 + (uy - py) ** 2
            if melhor is None or d2 < melhor:
                melhor, mi = d2, i
        cadeia.append(pts.pop(mi))
    return cadeia


def _aplicar_estilo_traco(img, estilo, rng):
    """Pós-processa o traço do usuário com um estilo de tinta: lápis,
    carvão, tinta, caligráfico, estrelas ou constelação. img é RGBA.
    Devolve uma nova RGBA (nunca altera a original)."""
    estilo = (estilo or "tinta").strip().lower()
    if estilo in ("", "tinta", "nenhum"):
        return img
    _nrng = np.random.default_rng(rng.randint(0, 2 ** 31))
    a = np.asarray(img).copy()
    alfa = a[..., 3].astype(np.uint8)
    masc = alfa > 60
    if not masc.any():
        return img
    cor = a[masc][:, :3].mean(axis=0).astype(int)

    if estilo == "lapis":
        # tinta acinzentada (dessaturada) + grão fino nas bordas + afina 1px
        _cinza = int(cor.mean())
        a[..., :3] = (_cinza, _cinza, min(255, _cinza + 6))
        ruido = _nrng.normal(0, 26, alfa.shape).astype(int)
        alfa2 = np.clip(alfa.astype(int) + ruido, 0, 255).astype(np.uint8)
        a[..., 3] = _erodir_alfa(alfa2, 1)
    elif estilo == "carvao":
        # tinta quase preta + grão pesado + leve engrossamento
        a[..., :3] = (38, 34, 30)
        ruido = _nrng.normal(0, 30, alfa.shape).astype(int)
        alfa2 = np.clip(alfa.astype(int) + ruido, 0, 255).astype(np.uint8)
        a[..., 3] = _dilatar_alfa(alfa2, 1)
    elif estilo == "caligrafico":
        # pincel: desfoque + curva de potência — pontas afinam, miolo firma
        _b = Image.fromarray(alfa).filter(ImageFilter.GaussianBlur(2.2))
        _ba = np.asarray(_b).astype(float) / 255.0
        _ba = np.clip(_ba ** 1.6, 0, 1)
        a[..., 3] = (_ba * 255).astype(np.uint8)
        a[..., :3] = np.clip(cor * 0.92, 0, 255).astype(int)
    elif estilo in ("estrelas", "constelacao"):
        ys, xs = np.where(masc)
        if len(xs) < 4:
            return img
        n = min(90, max(8, len(xs) // 12))
        idx = np.linspace(0, len(xs) - 1, n).astype(int)
        pts = list(zip(xs[idx].tolist(), ys[idx].tolist()))
        nova = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(nova)
        _cor = tuple(int(c) for c in cor)
        if estilo == "constelacao":
            cadeia = _cadeia_vizinho(pts)
            for p1, p2 in zip(cadeia, cadeia[1:]):
                d.line([p1, p2], fill=(*_cor, 150), width=1)
            for (x, y) in cadeia:
                d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(*_cor, 255))
        else:  # estrelas
            for (x, y) in pts:
                _estrela_4(d, x, y, rng.randint(3, 7), (*_cor, 255))
        return nova
    return Image.fromarray(a)


# ══════════════════════════════════════════════════════════════════════

def _papel_kraft(W, H, rng):
    img = Image.new("RGB", (W, H), PAPEL_KRAFT)
    masc = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(masc)
    for _ in range(rng.randint(50, 90)):
        x, y = rng.randint(0, W), rng.randint(0, H)
        r = rng.randint(90, 340)
        md.ellipse([x - r, y - r, x + r, y + r], fill=rng.randint(80, 150))
    masc = masc.filter(ImageFilter.GaussianBlur(130))
    tinge = Image.new("RGB", (W, H), (236, 219, 180))
    aux = Image.new("RGB", (W, H), (58, 49, 30))
    var = ImageChops.composite(tinge, aux, masc)
    img = ImageChops.blend(img, var, 0.30)
    # vinheta SÓ nas bordas (máscara: borda escura, miolo claro) —
    # antes a máscara estava invertida e escurecia o papel INTEIRO
    vig = Image.new("L", (W, H), 180)
    vd = ImageDraw.Draw(vig)
    for rr, t in [(40, 40), (150, 70)]:
        vd.rectangle([rr, rr, W - rr, H - rr], fill=max(0, 180 - t), width=0)
    vig = vig.filter(ImageFilter.GaussianBlur(110))
    esc = Image.new("RGB", (W, H), (48, 40, 26))
    img = ImageChops.composite(ImageChops.blend(img, esc, 0.72), img, vig)
    return img


# ══════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Planetário Astrológico Recicle")
    ap.add_argument("--data", required=True)
    ap.add_argument("--hora", default="12:00")
    ap.add_argument("--local", default=None)
    ap.add_argument("--nome", default="")
    ap.add_argument("--cultura", default=None)
    ap.add_argument("--tema", default="o teu nome")
    ap.add_argument("--feeling", default="encantamento")
    ap.add_argument("--traco", default=None)
    ap.add_argument("--traco-estilo", default="tinta",
                    choices=["tinta", "lapis", "carvao", "caligrafico",
                             "estrelas", "constelacao"],
                    help="estilo de tinta aplicado ao traço do usuário")
    ap.add_argument("--figura", default="gravura",
                    choices=["gravura", "ascii"],
                    help="estilo das figuras dos cartões (gravura/ascii)")
    ap.add_argument("--asteroides", action="store_true",
                    help="inclui Lilith, Ceres, Pallas, Juno e Vesta na "
                         "mandala e na tabela (Quíron já vem sempre)")
    ap.add_argument("--saida", default=None)
    ap.add_argument("--prompt", action="store_true",
                    help="grava um prompt de imagem artística derivado do mapa")
    ap.add_argument("--ia", action="store_true",
                    help="repinta a obra com Stable Diffusion local (img2img)")
    ap.add_argument("--ia-forca", type=float, default=0.42)
    ap.add_argument("--ia-foco", default="mandala",
                    choices=["mandala", "detalhe"])
    ap.add_argument("--ia-estilo", default=None,
                    help="traço do desenho (sorteado se ausente)")
    ap.add_argument("--ia-semente", type=int, default=None)
    a = ap.parse_args()
    res = gerar_obra(vars(a), saida=a.saida)
    print("obra em:", res["caminho"])
    if a.ia:
        try:
            import img_ia
            _dir = os.path.dirname(os.path.abspath(res["caminho"]))
            _ia_out = f"{_dir}/obra-ia-{a.data}.png"
            _o = img_ia.gerar_ia(res, vars(a), _ia_out, forca=a.ia_forca,
                                 foco=a.ia_foco, semente=a.ia_semente,
                                 estilo=a.ia_estilo)
            print("reintura IA em:", _o["caminho"])
            print("semente:", _o["semente"], "| estilo:", _o["estilo"],
                  "| controlnet:", _o["controlnet"])
        except Exception as _e:  # pragma: no cover
            print("(repintura IA falhou:", _e, ")")
    if a.prompt:
        try:
            import prompt_arte as _pa
            _txt = _pa.gerar_prompt_resource(res, cultura=a.cultura, tema=a.tema,
                                             feeling=a.feeling, nome=a.nome)
            _arq = (f"{os.path.dirname(os.path.abspath(res['caminho']))}/"
                    f"prompt-arte-{a.data}.txt")
            with open(_arq, "w", encoding="utf-8") as _f:
                _f.write(_txt + "\n")
            print("prompt de arte em:", _arq)
        except Exception as _e:
            print("(prompt de arte não gerado:", _e, ")")
    print("ASC:", res["asc_signo"], "| Sol:", res["sol_signo"])
    print("arquétipos ASC:", res["arquetipos_asc"])
    print("arquétipos SOL:", res["arquetipos_sol"])
    for l in res["verso"]:
        print("  ", l)
