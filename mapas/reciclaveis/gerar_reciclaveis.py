#!/usr/bin/env python3
"""Gera IMAGENS DE RECICLÁVEIS (papeis, latas, vidro, plástico, papelão...)
como assets PNG reutilizáveis para a colagem 'Planetário Astrológico Recicle'.

Saída: mapas/reciclaveis/*.png  (cada material sozinho, fundo transparente,
pronto para a colagem compor sobre a obra: molduras, etiquetas, latinhas).

Uso:
    /mnt/dados/home-italivre/iastro-ia/venv/bin/python \
        mapas/reciclaveis/gerar_reciclaveis.py

O padrão de nomenclatura é usado por colagem.py para buscar os assets.
"""
import os
import random
import math

from PIL import Image, ImageDraw, ImageFilter, ImageChops

SAIDA = "/mnt/dados/home-italivre/iastro-ia/mapas/reciclaveis"
rng = random.Random(7)


def novo(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def papel_craft(w, h, tom=(199, 179, 142), rugosidade=12):
    """Folha de papel kraft/kraft reciclado com fibras suaves."""
    im = Image.new("RGB", (w, h), tom)
    # variação difusa (blobs) — sem pontinhos
    masc = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(masc)
    for _ in range(rng.randint(12, 22)):
        x, y = rng.randint(-w, 2 * w) // 2, rng.randint(-h, 2 * h) // 2
        r = rng.randint(60, 220)
        md.ellipse([x - r, y - r, x + r, y + r], fill=rng.randint(90, 170))
    masc = masc.filter(ImageFilter.GaussianBlur(60))
    claro = Image.new("RGB", (w, h), tuple(min(255, c + 40) for c in tom))
    escuro = Image.new("RGB", (w, h), tuple(max(0, c - 50) for c in tom))
    var = ImageChops.composite(claro, escuro, masc)
    im = ImageChops.blend(im, var, 0.5)
    # fibras finas (riscos leves)
    d = ImageDraw.Draw(im)
    for _ in range(rng.randint(60, 140)):
        x0, y0 = rng.randint(0, w), rng.randint(0, h)
        ln = rng.randint(20, 140)
        ang = rng.uniform(-0.4, 0.4)
        x1 = x0 + ln * math.cos(ang)
        y1 = y0 + ln * math.sin(ang) * 0.2
        d.line([x0, y0, x1, y1], fill=tuple(max(0, c - rng.randint(6, 16)) for c in tom),
               width=1)
    # borda desgastada
    out = novo(w, h)
    im = im.convert("RGBA")
    out.paste(im, (0, 0), im)
    return out


def papel_jornal(w, h, tom=(206, 202, 190)):
    """Recorte de jornal: colunas de texto regulares + foto cinza."""
    im = Image.new("RGB", (w, h), tom)
    d = ImageDraw.Draw(im)
    col_w = 58
    n = w // col_w
    for c in range(n + 1):
        for _ in range(rng.randint(20, 40)):
            y = rng.randint(0, h - 6)
            ln = rng.randint(12, 40)
            d.line([(c * col_w + 3, y), (c * col_w + 3 + ln, y)],
                   fill=(90, 88, 84), width=rng.randint(1, 2))
    # cabeçalho ruidoso
    d.rectangle([w // 2 - 90, 12, w // 2 + 90, 40], fill=(55, 52, 48))
    # foto cinza
    fx = rng.randint(0, w - 90)
    d.rectangle([fx, h - 78, fx + 130, h - 14], fill=(120, 118, 112))
    for _ in range(60):
        x = rng.randint(fx, fx + 130)
        y = rng.randint(h - 78, h - 14)
        d.rectangle([x, y, x + 3, y + 3], fill=(95, 92, 86))
    out = novo(w, h)
    out.paste(Image.new("RGBA", (w, h), (0, 0, 0, 0)), (0, 0))
    oi = im.convert("RGBA")
    out.paste(oi, (0, 0), oi)
    return out


def papelao_ondulado(w, h, tom=(156, 132, 92)):
    """Papelão ondulado (caixa) com ondas verticais visíveis na borda."""
    im = Image.new("RGB", (w, h), tom)
    d = ImageDraw.Draw(im)
    # listras de corrugado
    for x in range(0, w, 9):
        c = tuple(max(0, v - 26) for v in tom)
        d.rectangle([x, 0, x + 3, h], fill=c)
        cc = tuple(min(255, v + 22) for v in tom)
        d.rectangle([x + 5, 0, x + 8, h], fill=cc)
    # ondulações
    for y in range(0, h, 14):
        d.line([(0, y), (w, y + 4)], fill=tuple(max(0, v - 12) for v in tom), width=1)
    out = novo(w, h)
    out.paste(im.convert("RGBA"), (0, 0), im.convert("RGBA"))
    return out


def lata_aluminio(w, h, cor=(188, 194, 198)):
    """Lata de alumínio (refrigerante) com brilho metálico e topo escuro."""
    im = novo(w, h)
    d = ImageDraw.Draw(im)
    modo = Image.new("L", (w, h), 0)
    ImageDraw.Draw(modo).rectangle([4, 4, w - 5, h - 5], fill=255)
    # corpo metálico (gradiente horizontal)
    for x in range(4, w - 4):
        t = (x - 4) / max(1, w - 8)
        b = int(cor[0] * (0.4 + 0.6 * math.sin(t * math.pi)))
        d.line([(x, 8), (x, h - 8)], fill=(b, b, b))
    # topo/boca
    d.ellipse([w // 2 - 14, 2, w // 2 + 14, 18], fill=(150, 155, 158))
    d.ellipse([w // 2 - 6, 5, w // 2 + 6, 14], fill=(110, 113, 115))
    # base
    d.rectangle([4, h - 8, w - 5, h - 4], fill=(120, 124, 126))
    # faixa de cor (rótulo)
    d.rectangle([4, h // 2 - 14, w - 5, h // 2 + 14], fill=(rng.randint(160, 230),
                                                           rng.randint(30, 120),
                                                           rng.randint(30, 130)))
    im.paste(Image.new("RGBA", (w, h), (255, 0, 0, 0)), (0, 0), modo)
    return im


def garrafa_vidro(w, h, cor=(96, 124, 84), rolha=True):
    """Garrafa de vidro (verde/âmbar) translúcida."""
    im = novo(w, h)
    d = ImageDraw.Draw(im)
    # corpo
    d.rounded_rectangle([w // 2 - 14, 20, w // 2 + 14, h - 6], radius=10,
                        fill=cor)
    # gargalo
    d.rectangle([w // 2 - 6, 6, w // 2 + 6, 26], fill=tuple(max(0, c - 20) for c in cor))
    # rolha
    if rolha:
        d.rectangle([w // 2 - 6, 0, w // 2 + 6, 9], fill=(122, 88, 52))
    # brilho (reflexo)
    d.line([(w // 2 - 8, 30), (w // 2 - 8, h - 12)], fill=(255, 255, 255, 90), width=3)
    # rótulo
    d.rectangle([w // 2 - 12, h // 2 - 16, w // 2 + 12, h // 2 + 16],
                fill=(238, 233, 220))
    d.rectangle([w // 2 - 12, h // 2 - 16, w // 2 + 12, h // 2 + 6],
                fill=(rng.randint(40, 80), rng.randint(80, 120), rng.randint(170, 220)))
    return im


def saco_plastico(w, h, cor=(210, 216, 220)):
    """Saco/embalagem plástica translúcida amassada."""
    im = novo(w, h)
    d = ImageDraw.Draw(im)
    # contorno irregular (amassado)
    pts = []
    for i in range(0, 361, 12):
        ang = math.radians(i)
        rr = rng.randint(min(w, h) // 2 - 14, min(w, h) // 2 + 10)
        x = w // 2 + rr * math.cos(ang)
        y = h // 2 + rr * math.sin(ang) * 0.9
        pts.append((x, y))
    # preenchimento translúcido
    poly = Image.new("L", (w, h), 0)
    ImageDraw.Draw(poly).polygon(pts, fill=90)
    poly = poly.filter(ImageFilter.GaussianBlur(2))
    im.paste(Image.new("RGBA", (w, h), (*cor, 200)), (0, 0), poly)
    # dobras/vincos
    d = ImageDraw.Draw(im)
    for _ in range(8):
        x0 = rng.randint(w // 2 - 30, w // 2 + 30)
        y0 = rng.randint(h // 2 - 30, h // 2 + 30)
        ln = rng.randint(24, 70)
        ang = rng.uniform(0, math.pi)
        d.line([x0, y0, x0 + ln * math.cos(ang), y0 + ln * math.sin(ang)],
               fill=(255, 255, 255, 90), width=2)
    return im


def papel_recorte(w, h, base=(240, 236, 224)):
    """Recorte de papel liso com fita adesiva num canto."""
    im = novo(w, h)
    im.paste(Image.new("RGBA", (w, h), (*base, 255)), (0, 0))
    d = ImageDraw.Draw(im)
    # fita amarronzada no canto
    d.polygon([(0, 0), (w // 4, 0), (w // 4 - 10, 26), (0, 26)], fill=(176, 160, 112, 160))
    d.polygon([(0, 0), (w // 4, 0), (w // 4 - 10, 20), (0, 22)], fill=(176, 160, 112, 90))
    return im


def caixa_leite(w, h, base=(226, 220, 208)):
    """Embalagem longa-vida (caixa de leite/suco) com topo tetra."""
    im = novo(w, h)
    d = ImageDraw.Draw(im)
    d.polygon([(8, 10), (w - 8, 10), (w // 2 + 10, 0), (w // 2 - 10, 0)],
              fill=(140, 130, 118))
    d.rectangle([8, 10, w - 8, h - 6], fill=base)
    # faixa de marca
    d.rectangle([8, h // 3, w - 8, h // 3 + 40],
                fill=(rng.randint(160, 220), rng.randint(40, 90), rng.randint(30, 80)))
    d.rectangle([w // 2 - 30, h // 3 + 10, w // 2 + 30, h // 3 + 30],
                fill=(245, 240, 228))
    return im


ASSETS = [
    ("papel-kraft", lambda: papel_craft(360, 260)),
    ("papel-kraft-2", lambda: papel_craft(400, 300, tom=(188, 168, 130), rugosidade=18)),
    ("jornal", lambda: papel_jornal(420, 300)),
    ("papelao-ondulado", lambda: papelao_ondulado(380, 280)),
    ("lata-aluminio", lambda: lata_aluminio(120, 200)),
    ("lata-aluminio-2", lambda: lata_aluminio(110, 210, cor=(170, 176, 166))),
    ("garrafa-vidro-verde", lambda: garrafa_vidro(100, 240)),
    ("garrafa-vidro-ambar", lambda: garrafa_vidro(100, 240, cor=(150, 105, 52))),
    ("saco-plastico", lambda: saco_plastico(200, 150)),
    ("recorte-papel", lambda: papel_recorte(240, 180)),
    ("caixa-longa-vida", lambda: caixa_leite(160, 220)),
]


def main():
    os.makedirs(SAIDA, exist_ok=True)
    for nome, fn in ASSETS:
        im = fn()
        p = os.path.join(SAIDA, nome + ".png")
        im.save(p)
        print(f"{nome}.png  {im.size}  ({os.path.getsize(p)} bytes)")
    print("\nPasta:", SAIDA, f"({len(ASSETS)} assets)")


if __name__ == "__main__":
    main()
