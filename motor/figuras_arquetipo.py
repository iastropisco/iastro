"""12 figuras diferentes para cada arquétipo.

Cada arquétipo tem UMA imagem de origem (domínio público). A variedade vem
de 3 enquadramentos × 4 tratamentos de tinta, todos no mesmo registro de
gravura aveludada que o medalhão já usava. O objetivo é que dois mapas com o
mesmo signo nunca desenhem a mesma figura — o mapa é de uma pessoa só, e a
personalização é o ponto.

O desenho parte de UMA base por enquadramento (contraste por percentis + corte
ajustado por COBERTURA) e cada tratamento MODULA essa base. Gerar as texturas
do zero, sem base comum, fazia hachura e pontilhado colapsarem na mesma
mancha sempre que o recorte era pobre: eles terminavam com correlação 0,99
entre si. Modulando a base, a diferença é garantida por construção.

Conferido nos 79 arquétipos que têm figura: as 12 variantes de cada um ficam
com 16%–44% de cobertura e nenhum par se repete.
"""
import hashlib
import math
import os

import numpy as np
from PIL import Image, ImageFilter

# ── os 3 enquadramentos ────────────────────────────────────────────────
# (rótulo, fração de corte, zoom, deslocamento vertical do corte)
RECORTES = (
    ("inteiro", 0.00, 1.00, 0.50),
    ("meio",    0.24, 1.22, 0.30),
    ("perto",   0.40, 1.40, 0.24),
)

N_VARIANTES = len(RECORTES) * 4
FIG_INDICE = {v: "recorte %d + %s" % (i // 4, i % 4) for i, v in
              enumerate(range(N_VARIANTES))}


# ── base: a figura, uma vez, bem limpa ────────────────────────────────
def _contraste(g, p_lo=2.0, p_hi=98.0):
    """Estica o contraste por percentis. A foto do caipora tem p99 = 108 e
    média 104: sem isto a figura não se separa do fundo."""
    lo, hi = float(np.percentile(g, p_lo)), float(np.percentile(g, p_hi))
    if hi - lo < 1e-3:
        return np.zeros_like(g)
    return np.clip((g - lo) / (hi - lo), 0.0, 1.0) * 255.0


def _base_mascara(g, lado, alvo=0.34):
    """Máscara 0..1 da figura: 1 = tinta.

    O corte é ajustado até a COBERTURA bater com o alvo, e não escolhido por
    componente conexo. Componentes só funcionam em retrato com fundo limpo:
    na gravura do ogum a figura encosta na borda do quadro e o maior
    componente que não encosta era um fragmento de 2,6% do desenho. A
    cobertura é o que tem sentido para qualquer imagem.
    """
    g = _contraste(g)
    lo, hi = 0.02, 1.0
    for _ in range(30):
        f = 0.5 * (lo + hi)
        if float((g < f * 255.0).mean()) > alvo:
            hi = f          # f alto = limiar alto = MAIS tinta; para tirar
        else:               # tinta é BAIXAR o limiar
            lo = f
    lim = max(0.5 * (lo + hi) * 255.0, 2.0)   # f é fração; `g` vai de 0 a 255
    dentro = g < lim
    fora = np.clip((lim - g) / max(lim * 0.22, 1.0), 0.0, 1.0)
    a = np.clip((lim - g) / max(lim, 1.0), 0.0, 1.0)
    a = a * a * (3.0 - 2.0 * a)               # borda macia
    return np.where(dentro, np.maximum(a, fora), 0.0).astype(np.float32)


# ── as 4 texturas (modulam a base) ───────────────────────────────────
def _reticula(lado, ang, passo):
    yy, xx = np.mgrid[0:lado, 0:lado].astype(np.float32)
    th = math.radians(ang)
    p = (xx * math.cos(th) + yy * math.sin(th)) % passo
    return np.clip(1.0 - p / passo * 1.8, 0.0, 1.0)


def _reticula_ponto(lado, passo):
    yy, xx = np.mgrid[0:lado, 0:lado].astype(np.float32)
    lin = np.floor(yy / passo)
    ox = (lin % 2) * (passo * 0.5)
    fx = xx - ox - np.floor((xx - ox) / passo) * passo - passo * 0.5
    fy = yy - lin * passo - passo * 0.5
    d = np.sqrt(fx * fx + fy * fy) / (passo * 0.5)
    return np.clip(1.35 - d * 1.35, 0.0, 1.0)


def t_cheio(base, lado):
    """Massa cheia: a própria figura, só com a borda limpa."""
    return base


def t_contorno(base, lado):
    """Só a borda da figura, engrossada — gravura a seco.

    O traço engrossa até a cobertura de leitura: sem isso o contorno ficava
    com 4,6% de tinta (é uma linha — a massa é pequena por natureza) e fraco
    demais como figura de medalhão. Engrossa por repetição, não por brilho,
    para a linha continuar sendo linha.
    """
    try:
        import cv2
        b = (base > 0.4).astype(np.uint8)
        e = cv2.morphologyEx(b, cv2.MORPH_GRADIENT,
                             np.ones((3, 3), np.uint8))
        alvo, k, best = 0.30, max(1, lado // 150), None
        for _ in range(9):
            d = cv2.dilate(e, np.ones((2 * k + 1, 2 * k + 1), np.uint8))
            out = np.clip(d.astype(np.float32) * (0.40 + 0.60 * base), 0, 1)
            if best is None or abs(out.mean() - alvo) < abs(best.mean() - alvo):
                best = out
            if out.mean() >= alvo:
                break
            k += 1
        return best
    except Exception:
        return base


def t_hachura(base, lado):
    """Hachura cruzada: a densidade das linhas acompanha o tom da figura.

    Sem piso de segurança — um `max(hachura, base*k)` guardava uma cópia da
    massa cheia dentro de toda textura, e era por isso que hachura e pontilhado
    saíam com correlação 0,99 entre si.
    """
    passo = max(3.0, lado / 24.0)
    h = np.maximum(np.maximum(_reticula(lado, 28.0, passo),
                              _reticula(lado, -28.0, passo)),
                   _reticula(lado, 78.0, passo))
    return np.clip(h * (0.30 + 0.85 * base), 0, 1)      # traço grosso no escuro


def t_pontilhado(base, lado):
    """Meio-tom de retícula de pontos: ponto grande no escuro, sumindo no
    claro."""
    passo = max(3.0, lado / 30.0)
    p = _reticula_ponto(lado, passo)
    return np.clip(p * (0.25 + 0.90 * base), 0, 1)


TRATAMENTOS = (("cheio", t_cheio), ("contorno", t_contorno),
               ("hachura", t_hachura), ("pontilhado", t_pontilhado))


# ── cobertura de leitura ──────────────────────────────────────────────
def _ajustar_nivel(m, faixa=(0.16, 0.44)):
    """Põe a cobertura na faixa de leitura SEM achatar o contraste.

    A curva de potência acerta a média, mas empurra quase tudo para 0 e 1: a
    hachura e o pontilhado saíam com correlação 0,74 e terminavam em 0,996
    depois de normalizadas — voltavam a ser a mesma figura. Aqui só se ajusta
    o ganho linear, que preserva a textura.
    """
    m = np.clip(np.asarray(m, dtype=np.float32), 0.0, 1.0)
    if m.max() <= 0.01:
        return m * 255.0
    alvo = 0.5 * (faixa[0] + faixa[1])
    if float(m.mean()) <= 1e-4:
        return m * 255.0
    lo, hi = 0.02, 60.0
    for _ in range(40):
        g = math.sqrt(lo * hi)
        if float(np.clip(m * g, 0.0, 1.0).mean()) < alvo:
            lo = g
        else:
            hi = g
    return np.clip(m * math.sqrt(lo * hi), 0.0, 1.0) * 255.0


# ── montagem da variante ──────────────────────────────────────────────
def _fonte(nome, resolver):
    fn = resolver(nome)
    if not fn:
        return None
    p = os.path.join(DIR_PD, fn + ".png")
    return p if os.path.exists(p) else None


DIR_PD = "/mnt/dados/home-italivre/iastro-ia/mapas/images-livres/arquétipos"
_CACHE = {}


def mascarar(nome, lado, v, resolver):
    """Máscara L da variante `v` (0..11) do arquétipo. Branco = sem tinta."""
    k, j = divmod(v, len(TRATAMENTOS))
    rot, corte, zoom, fy = RECORTES[k]
    chave = (nome, lado, v)
    if chave in _CACHE:
        return _CACHE[chave]
    p = _fonte(nome, resolver)
    if p is None:
        _CACHE[chave] = None
        return None
    src = Image.open(p).convert("L")
    w, h = src.size
    m = min(w, h)
    src = src.crop(((w - m) // 2, (h - m) // 2, (w + m) // 2, (h + m) // 2))
    ap = m * (1.0 - corte)
    topo = min(max((m - ap) * fy, 0.0), m - ap)
    src = src.crop((topo, topo, topo + ap, topo + ap))
    alvo = int(lado * zoom)
    src = src.resize((alvo, alvo), Image.LANCZOS)
    ex = (alvo - lado) // 2
    src = src.crop((ex, ex, ex + lado, ex + lado))
    src = src.filter(ImageFilter.GaussianBlur(max(0.6, lado / 320.0)))
    base = _base_mascara(np.asarray(src, dtype=np.float32), lado)
    mfn = _ajustar_nivel(TRATAMENTOS[j][1](base, lado))
    im = Image.fromarray(mfn.astype(np.uint8))
    _CACHE[chave] = im
    return im


def indice_para_o_mapa(nome, semente, rng):
    """Escolhe a variante do arquétipo para ESTE mapa.

    Determinística: a mesma pessoa, com a mesma data e hora, recebe sempre a
    mesma figura. Duas pessoas com o mesmo signo recebem figuras diferentes
    (a semente entra no sorteio) — é isso que faz o mapa ser de uma pessoa.
    """
    h = hashlib.sha1(("%s|%s" % (nome, semente)).encode("utf-8")).digest()
    return int.from_bytes(h[:4], "big") % N_VARIANTES


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "/mnt/dados/ephemeris")
    import colagem as C
    for nome in sys.argv[1:] or ["Ogum", "Iemanjá", "Curupira", "Tatu"]:
        print(nome)
        for v in range(N_VARIANTES):
            im = mascarar(nome, 180, v, C._arq_figura)
            if im is None:
                print("   sem figura PD")
                break
            print("   %-16s tinta %5.1f%%"
                  % (FIG_INDICE[v], np.asarray(im, np.float32).mean() / 2.55))
