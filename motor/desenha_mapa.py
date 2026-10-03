#!/usr/bin/env python3
"""Mapa Astral poético — nascimento 20/11/1982, Belo Horizonte (01:30).

Roda do zodíaco com planetas em longitudes REAIS (Swiss Ephemeris).
Destaque para o CASIMI: Sol + Mercúrio em Escorpião (27°19'56" + 27°28'00",
~8' de arco) — o "sol no coração do sol".

Estética Astro Pisco: céu-noturna-océano, anel zodiacal bonito, legenda
clara dos planetas, verso poético capixaba, o mapa como segundo poema.

Os planetas do aglomerado Escorpião/Sagitário são desenhados no anel com
glifos pequenos (sem rótulo longo) e detalhados na legenda, para não se
sobreporem.
"""
import math
import random
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ... dados ---------------------------------------------------------------
SIGNOS = [
    ("Áries", "♈", (229, 83, 61)), ("Touro", "♉", (107, 168, 107)),
    ("Gêmeos", "♊", (224, 195, 65)), ("Câncer", "♋", (184, 204, 224)),
    ("Leão", "♌", (232, 163, 61)), ("Virgem", "♍", (159, 191, 125)),
    ("Libra", "♎", (217, 139, 168)), ("Escorpião", "♏", (166, 50, 84)),
    ("Sagitário", "♐", (122, 79, 176)), ("Capricórnio", "♑", (122, 90, 58)),
    ("Aquário", "♒", (79, 168, 200)), ("Peixes", "♓", (78, 127, 192)),
]

# (id, nome, glifo, longitude real, cor)  — posições exatas do nascimento (04:30 UT)
PLANETAS = [
    ("Sun", "Sol", "☉", 237.5214, (255, 214, 92)),
    ("Moon", "Lua", "☽", 287.8140, (205, 220, 240)),
    ("Mercury", "Mercúrio", "☿", 237.7636, (180, 220, 210)),
    ("Venus", "Vênus", "♀", 241.5381, (240, 180, 200)),
    ("Mars", "Marte", "♂", 284.5136, (230, 100, 90)),
    ("Jupiter", "Júpiter", "♃", 232.3292, (222, 180, 120)),
    ("Saturn", "Saturno", "♄", 208.9942, (200, 180, 150)),
    ("Uranus", "Urano", "♅", 244.4389, (120, 220, 230)),
    ("Neptune", "Netuno", "♆", 265.7033, (120, 160, 230)),
    ("Pluto", "Plutão", "♇", 208.0508, (190, 140, 200)),
]

# Cúspides das casas (Placidus, Swiss Ephemeris) no nascimento — longitudes
ASC_LON = 170.2372
MC_LON = 83.0511
CASAS_LON = [170.2372, 206.9083, 237.1803, 263.0511, 288.0883, 315.9856,
             350.2372, 26.9083, 57.1803, 83.0511, 108.0883, 135.9856]

# signo correspondente a cada longitude (índice no zodíaco)
def signo_de(lon):
    return int(lon // 30) % 12

def detectar_signo_indice(planeta_lon):
    return int(planeta_lon // 30) % 12

W = H = 1800
CX, CY = W // 2, 878

R_SIGNO_EXT = 742
R_SIGNO_INT = 596
R_TICKS_EXT = 568
R_TICKS_INT = 561
R_PLANETA = 518          # anel onde ficam os pontos dos planetas
ANEL_INTERNO = 478

FONTS = "/usr/share/fonts/truetype/dejavu"
def font(size, bold=True):
    p = f"{FONTS}/DejaVuSerif-Bold.ttf" if bold else f"{FONTS}/DejaVuSerif.ttf"
    if os.path.exists(p):
        return ImageFont.truetype(p, size)
    return ImageFont.truetype(f"{FONTS}/DejaVuSerif.ttf", size)
def font_sans(size):
    return ImageFont.truetype(f"{FONTS}/DejaVuSans-Bold.ttf", size)

def polar(R, lon):
    a = math.radians(lon)   # lon 0 = esquerda, cresce anti-horário
    return (CX - R * math.cos(a), CY - R * math.sin(a))

# ================================================================ base
img = Image.new("RGB", (W, H), (5, 9, 20))
d = ImageDraw.Draw(img)

for i in range(800, 0, -1):
    t = i / 800
    cor = (int(28 + 30 * (1 - t)), int(20 + 15 * (1 - t)), int(54 + 26 * (1 - t)))
    rr = R_SIGNO_EXT + 90
    d.ellipse([CX - rr * t, CY - rr * t, CX + rr * t, CY + rr * t], outline=cor, width=3)

random.seed(1982)
for _ in range(320):
    x, y = random.randint(0, W - 1), random.randint(0, H - 1)
    r2 = (x - CX) ** 2 + (y - CY) ** 2
    if r2 > (R_SIGNO_EXT + 70) ** 2:
        b = random.randint(45, 135); d.point((x, y), fill=(b, b, b + 24))
    elif r2 > 320000:
        if random.random() < 0.25:
            b = random.randint(32, 95); d.point((x, y), fill=(b, b - 5, b + 18))

# ================================================================ zodíaco
for z, (nome, glifo, cor) in enumerate(SIGNOS):
    lon0, lon1 = z * 30, (z + 1) * 30
    a0, b0 = polar(R_SIGNO_INT, lon0), polar(R_SIGNO_EXT, lon0)
    a1, b1 = polar(R_SIGNO_INT, lon1), polar(R_SIGNO_EXT, lon1)
    for i in range(28):
        interm = lon0 + (lon1 - lon0) * (i / 28)
        p0 = polar(R_SIGNO_INT, interm)
        p1 = polar(R_SIGNO_EXT, interm)
        br = 0.5 + 0.5 * (i / 28)
        d.line([p0, p1], fill=(
            int(cor[0] * br * 0.30), int(cor[1] * br * 0.30), int(cor[2] * br * 0.34)), width=2)
    d.line([a0, b0], fill=(38, 60, 92), width=1)
    d.line([a1, b1], fill=(38, 60, 92), width=1)
    mid = lon0 + 15
    pg = polar((R_SIGNO_INT + R_SIGNO_EXT) / 2, mid)
    d.text((pg[0], pg[1] - 30), glifo, font=font_sans(46), fill=cor, anchor="mm")
    d.text((pg[0], pg[1] + 26), nome, font=font(22), fill=(240, 245, 255), anchor="mm")

for deg in range(0, 360, 5):
    p0 = polar(R_TICKS_EXT, deg)
    p1 = polar(R_TICKS_INT, deg)
    d.line([p0, p1], fill=(64, 88, 132), width=2)

# ================================================================ casas (cúspides radiais + números)
for i, clon in enumerate(CASAS_LON):
    p0 = polar(8, clon)          # do centro
    p1 = polar(R_TICKS_EXT + 6, clon)   # até o anel
    cor_casa = (200, 150, 60) if clon == ASC_LON else (110, 130, 170)
    d.line([p0, p1], fill=cor_casa, width=3 if clon == ASC_LON else 2)
    # número da casa perto do anel interno (evita sobrepor planetas)
    pn = polar(R_SIGNO_INT - 24, clon + 8)
    d.text((pn[0], pn[1]), str(i + 1), font=font(26, bold=True),
           fill=(220, 230, 250), anchor="mm")

# marcação do ASC
pa = polar(R_SIGNO_EXT + 26, ASC_LON)
d.text((pa[0], pa[1]), "ASC", font=font(26, bold=True), fill=(255, 214, 92), anchor="mm")

# ================================================================ planetas no anel
for pid, nome, glifo, lon, cor in PLANETAS:
    x, y = polar(R_PLANETA, lon)
    for h in range(28, 7, -3):
        d.ellipse([x - h, y - h, x + h, y + h], outline=(cor[0], cor[1], cor[2]))
    d.ellipse([x - 11, y - 11, x + 11, y + 11], fill=(18, 22, 38))
    d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=cor)
    d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(252, 253, 255))
    # glifo pequeno ao lado do ponto
    d.text((x + 12, y - 2), glifo, font=font_sans(34), fill=(250, 252, 255), anchor="lm")

# ================================================================ disco central / CASIMI
glow_rad = ANEL_INTERNO
sol_centro = Image.new("RGB", (W, H), (0, 0, 0))
sd = ImageDraw.Draw(sol_centro)
cg = (255, 205, 95)
for rr in range(glow_rad, 8, -4):
    t = rr / glow_rad
    sd.ellipse([CX - rr, CY - rr, CX + rr, CY + rr],
               fill=(int(cg[0]), int(cg[1] * (0.5 + 0.5 * t)), int(cg[2] * (0.22 + 0.28 * t))))
glow_img = sol_centro.filter(ImageFilter.GaussianBlur(60))
img = Image.blend(img, glow_img, 0.60)
d = ImageDraw.Draw(img)

d.ellipse([CX - ANEL_INTERNO, CY - ANEL_INTERNO, CX + ANEL_INTERNO, CY + ANEL_INTERNO],
          outline=(72, 100, 150), width=2)

r_emb = 320
d.ellipse([CX - r_emb, CY - r_emb, CX + r_emb, CY + r_emb], outline=(255, 214, 92), width=6)
d.ellipse([CX - r_emb - 9, CY - r_emb - 9, CX + r_emb + 9, CY + r_emb + 9], outline=(120, 90, 30), width=2)

d.text((CX, CY - 96), "☉", font=font_sans(185), fill=(255, 228, 140), anchor="mm")
d.text((CX, CY - 96), "☿", font=font_sans(100), fill=(255, 249, 208), anchor="mm")

d.text((CX, CY + 66), "CASIMI", font=font(54), fill=(255, 238, 168), anchor="mm")
d.text((CX, CY + 122), "sol no coração do sol", font=font(33), fill=(224, 234, 252), anchor="mm")
d.text((CX, CY + 160), "☉ 27°31'17\"  +  ☿ 27°45'49\"  ·  Escorpião  ·  orbe 14'32\"",
       font=font(24), fill=(198, 212, 242), anchor="mm")

# ================================================================ cabeçalho
d.text((CX, 74), "MAPA ASTRAL", font=font(64), fill=(240, 244, 255), anchor="mm")
d.text((CX, 126), "20 · 11 · 1982   —   Belo Horizonte   —   01:30",
       font=font(32), fill=(182, 200, 234), anchor="mm")

# ================================================================ legenda (canto superior esquerdo)
LX, LY = 40, 160
LEG_ALT = 560
d.rounded_rectangle([LX, LY, LX + 470, LY + LEG_ALT], radius=26, fill=(12, 16, 32))
d.rounded_rectangle([LX, LY, LX + 470, LY + LEG_ALT], radius=26, outline=(80, 105, 150), width=2)
d.text((LX + 20, LY + 10), "os planetas", font=font(26, bold=True), fill=(255, 238, 168), anchor="lm")
d.text((LX + 20, LY + 36), "ASC Virgem 20°14'  ·  MC Gêmeos 23°03'",
       font=font(21), fill=(255, 214, 92), anchor="lm")

# legendas em duas colunas
col_x = [LX + 24, LX + 250]
linha_inicio = LY + 76
y = linha_inicio

ordem = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter",
         "Saturn", "Uranus", "Neptune", "Pluto"]
linhas_por_col = 5
for i, pid in enumerate(ordem):
    _, nome, glifo, lon, cor = next(p for p in PLANETAS if p[0] == pid)
    z = detectar_signo_indice(lon)
    nome_signo = SIGNOS[z][0]
    dentro = lon - z * 30
    g = int(dentro)
    resto = (dentro - g) * 60
    m = int(resto)
    s = int(round((resto - m) * 60))
    if s == 60:
        s = 0; m += 1
    if m == 60:
        m = 0; g += 1
    col = i // linhas_por_col
    lin = i % linhas_por_col
    cx0 = col_x[col]
    cy0 = y + lin * 88
    destaque = (pid == "Sun" or pid == "Mercury")
    dc = (255, 238, 160) if destaque else (245, 248, 255)
    d.text((cx0, cy0), f"{glifo} {nome}", font=font(28), fill=dc, anchor="lm")
    d.text((cx0, cy0 + 32), f"{nome_signo}  {g}°{m:02d}'{s:02d}\"", font=font(22),
           fill=(198, 212, 242), anchor="lm")
    if destaque:
        d.line([cx0, cy0 + 58, cx0 + 220, cy0 + 58], fill=(120, 100, 40), width=1)

# nota do cazimi no rodapé da legenda
d.text((LX + 24, y + 5 * 88 + 14), "☉ Sol conj. ☿ Mercúrio  =  CASIMI", font=font(21),
       fill=(255, 214, 92), anchor="lm")

# ================================================================= versão poética
verso = [
    "lua em capricórnio sobe a pedra devagar,",
    "o coração de escorpião guarda a água toda do mar —",
    "e quando o sol abraça mercúrio no mesmo grau, o verbo arde em ti, puro.",
]
fy = H - 150
for linha in verso:
    d.text((CX, fy), linha, font=font(30), fill=(206, 216, 240), anchor="mm")
    fy += 44

d.text((CX, H - 22), "posições Swiss Ephemeris · zodíaco tropical · 00:00 UTC",
       font=font(20), fill=(114, 129, 162), anchor="mm")

out = "/mnt/dados/home-italivre/iastro-ia/mapas/cazimi-1982-11-20.png"
img.save(out, quality=95)
print("Salvo:", out, img.size)
