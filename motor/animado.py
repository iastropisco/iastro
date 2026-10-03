# -*- coding: utf-8 -*-
"""Versão ANIMADA (WebP/GIF) da obra do planetário — 100% gerada por nós,
leve e sem assets externos.

O que anima (procedural, domínio público do projeto):
- Estrelas/faíscas piscando suavemente por toda a cena (mágica de encarte);
- A faixa d'água do cartão terra-e-céu "balançando" (ondulações que passam);
- Um "sopro" luminoso na mandala (respiração da roda do céu).

Uso:
    python animado.py --data 1982-11-20 --hora 01:30 --local "belo horizonte"
        --saida /caminho/obra-animada-1982-11-20.webp
"""
from __future__ import annotations

import argparse
import math
import os
import random

from PIL import Image, ImageDraw
import numpy as np


def _radial_glow(size, cor=(255, 205, 130), alpha_max=70):
    """Overlay RGBA de brilho radial suave (para o 'sopro' da mandala)."""
    W, H = size
    cx, cy = W / 2, H / 2
    R = min(W, H) / 2
    xx, yy = np.meshgrid(np.arange(W), np.arange(H))
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / R
    a = np.clip(1 - d, 0, 1) ** 1.6
    an = (a * alpha_max).astype(np.uint8)
    ov = Image.new("RGBA", size, (0, 0, 0, 0))
    ov.paste((*cor, 0), (0, 0))
    arr = np.asarray(ov).copy()
    arr[..., 0] = cor[0]
    arr[..., 1] = cor[1]
    arr[..., 2] = cor[2]
    arr[..., 3] = an
    return Image.fromarray(arr, "RGBA")


def gerar_obra_animada(form, saida=None, largura=900, quadros=16, fps=12,
                       semente=None):
    """Renderiza a obra e anima em WebP (fallback GIF). Retorna dict."""
    import colagem
    rng = random.Random(semente if semente is not None
                        else random.Random().randrange(1 << 30))
    # 1) obra estática em PNG de referência
    base_png = saida.replace(".webp", "").replace(".gif", "") + "-base.png"
    res = colagem.gerar_obra(form, saida=base_png)
    img = Image.open(res["caminho"]).convert("RGB")
    w, h = img.size
    if w > largura:
        img = img.resize((largura, int(h * largura / w)), Image.LANCZOS)
    W, H = img.size

    # 2) pasta d'água do cartão terra-e-céu (inferida: faixa inferior da
    #    colagem, acima do verso)
    band_y = int(H * 0.84)
    band_h = max(20, int(H * 0.06))

    # 3) pontos de faísca (fixos, alpha varia por quadro)
    n_sp = 46
    sp_x = [rng.randrange(0, W) for _ in range(n_sp)]
    sp_y = [rng.randrange(0, H) for _ in range(n_sp)]
    sp_f = [rng.uniform(0.6, 1.6) for _ in range(n_sp)]
    sp_p = [rng.uniform(0, math.tau) for _ in range(n_sp)]

    glow = _radial_glow((W, H))
    quadros_out = []
    for k in range(quadros):
        t = k / quadros
        fr = img.copy().convert("RGBA")
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        # faíscas
        for i in range(n_sp):
            a = 0.5 + 0.5 * math.sin(sp_f[i] * 2 * math.pi * t + sp_p[i])
            alfa = int(70 + 130 * a)
            if alfa < 12:
                continue
            r = rng.choice((1, 1, 2))
            od.ellipse([sp_x[i] - r, sp_y[i] - r, sp_x[i] + r, sp_y[i] + r],
                       fill=(255, 240, 200, alfa))
        # ondulação da água (linhas de brilho que passam)
        for x in range(0, W, 26):
            off = math.sin((x / W) * math.tau * 2.6 + t * math.tau)
            yy = band_y + band_h * (0.5 + 0.42 * off)
            a_w = int(26 + 34 * (0.5 + 0.5 * math.sin(x * 0.13 + t * math.tau)))
            od.line([x, yy, x + 14, yy], fill=(190, 225, 255, a_w), width=1)
        fr.paste(ov, (0, 0), ov)
        # sopro da mandala (muito sutil)
        alfa_g = 30 + 26 * math.sin(math.pi * t * 2)
        g = glow.copy()
        ga = np.asarray(g)
        ga[..., 3] = (ga[..., 3] * alfa_g / 70).astype(np.uint8)
        g = Image.fromarray(ga)
        fr.paste(g, (0, 0), g)
        quadros_out.append(fr.convert("RGB"))

    if saida is None:
        saida = f"/mnt/dados/home-italivre/iastro-ia/mapas/" \
                f"obra-animada-{form['data']}.webp"
    if os.path.exists(base_png):
        try:
            os.remove(base_png)
        except OSError:
            pass
    # WebP animado (leve); se a lib não tiver, cai para GIF
    try:
        quadros_out[0].save(
            saida, save_all=True, append_images=quadros_out[1:],
            duration=int(1000 / fps), loop=0, format="WEBP", method=6,
            quality=82)
    except Exception as _e_webp:
        saida_gif = saida.replace(".webp", ".gif")
        quadros_out[0].save(
            saida_gif, save_all=True, append_images=quadros_out[1:],
            duration=int(1000 / fps), loop=0, format="GIF", optimize=True)
        saida = saida_gif
    kb = os.path.getsize(saida) / 1024
    return {"caminho": saida, "quadros": quadros, "fps": fps,
            "largura": W, "altura": H, "kb": round(kb, 1)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Obra animada (WebP/GIF, leve)")
    ap.add_argument("--data", required=True)
    ap.add_argument("--hora", default="12:00")
    ap.add_argument("--local", required=True)
    ap.add_argument("--cultura", default=None)
    ap.add_argument("--tema", default="o teu nome")
    ap.add_argument("--feeling", default="encantamento")
    ap.add_argument("--nome", default="")
    ap.add_argument("--figura", default="gravura", choices=["gravura", "ascii"])
    ap.add_argument("--largura", type=int, default=900)
    ap.add_argument("--quadros", type=int, default=16)
    ap.add_argument("--fps", type=int, default=12)
    ap.add_argument("--saida", default=None)
    a = ap.parse_args()
    form = {"data": a.data, "hora": a.hora, "local": a.local,
            "cultura": a.cultura, "tema": a.tema, "feeling": a.feeling,
            "nome": a.nome.strip(), "figura": a.figura}
    out = gerar_obra_animada(form, saida=a.saida, largura=a.largura,
                             quadros=a.quadros, fps=a.fps)
    print("obra animada em:", out["caminho"],
          f"({out['largura']}x{out['altura']}, {out['quadros']} quadros, "
          f"{out['fps']} fps, {out['kb']} KB)")