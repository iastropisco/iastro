# -*- coding: utf-8 -*-
"""Repintura artística do MAPA REAL com Stable Diffusion (local, CPU).

Como funciona (e por que não "erra"):
1. A obra PNG do planetário já tem as POSIÇÕES certas (Swiss Ephemeris) e a
   diagramação final — ela é a base (init image) do img2img.
2. O `prompt_arte` gera um prompt com os FATOS do mapa (planeta → signo →
   grau, Asc, arquétipos, cultura, tema).
3. O SD apenas "repinta" por cima com o estilo pedido (tinta nanquim,
   aquarela, realista...), com força controlada: força baixa ≈ mantém a
   estrutura; força alta ≈ mais liberdade do modelo.

Modelo: open-weights (CreativeML OpenRAIL-M). 100% local, sem internet para
os dados do usuário. Licenças de pesos do modelo à parte do código (que é
software livre de código aberto).
"""

from __future__ import annotations

import os
import random

_cache = os.environ.get("HF_HOME") or "/mnt/dados/hf"
os.environ.setdefault("HF_HOME", _cache)

MODELO = os.environ.get("IA_MODELO", "Lykon/dreamshaper-8")
CONTROLNET = os.environ.get("IA_CONTROLNET", "lllyasviel/sd-controlnet-canny")
_pipe = None
_pipe_cc = None

# estilos VARIÁVEIS: cada mapa pode sair com um traço diferente (mais vida).
# a lista é sorteada se o usuário não escolher — cada nascimento ≠ desenho.
ESTILOS = [
    "aquarela vintage e colorida, cores quentes de terra, papel envelhecido",
    "guache vibrante do cordel, vermelho-terra e ocre, traço grosso",
    "aquarela translúcida e leve, aguadas que vazam, verde e laranja",
    "nanquim + lavagem de aquarela, muito contraste de tinta seca",
    "gouache de cartaz de feira, recortes de papelão, xilogravura",
    "incisão em linóleo, cores chapadas, brasilidade de cordel",
]

_NEGATIVO = (
    "desenho infantil, pixel art, clip-art, marca d'água, assinatura, "
    "texto legível, palavras, números, distorção, membros tortos, "
    "retângulos mecânicos, borda chapada, render 3d barato, brilho neon"
)


def _estilo_sorteado(rng=None):
    return (rng or random).choice(ESTILOS)


def _carregar():
    global _pipe
    if _pipe is None:
        import torch
        torch.set_num_threads(int(os.environ.get("IA_THREADS", "8")))
        from diffusers import StableDiffusionImg2ImgPipeline
        _pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
            MODELO, torch_dtype=torch.float32)
        _pipe.enable_attention_slicing()
        _pipe.set_progress_bar_config(disable=True)
    return _pipe


def _carregar_com_controle():
    """Pipe com ControlNet canny (mantém as arestas da obra: a roda e as
    gravuras dos arquétipos NÃO somem na repintura). Guardado em cache."""
    global _pipe_cc
    if _pipe_cc is None:
        import torch
        torch.set_num_threads(int(os.environ.get("IA_THREADS", "8")))
        from diffusers import (ControlNetModel,
                               StableDiffusionControlNetImg2ImgPipeline)
        ctrl = ControlNetModel.from_pretrained(
            CONTROLNET, torch_dtype=torch.float32)
        _pipe_cc = StableDiffusionControlNetImg2ImgPipeline.from_pretrained(
            MODELO, controlnet=ctrl, torch_dtype=torch.float32)
        _pipe_cc.enable_attention_slicing()
        _pipe_cc.set_progress_bar_config(disable=True)
    return _pipe_cc


def _bordas_canny(img, rng):
    import numpy as np
    import cv2
    arr = np.asarray(img.convert("L"))
    arr = cv2.GaussianBlur(arr, (5, 5), 0)
    lim = rng.randint(55, 90)
    return cv2.Canny(arr, max(10, lim - 35), lim)


def _recorte_mandala(img, lado_frac=0.56):
    """Recorte quadrado centrado na roda (onde está a mandala)."""
    W, H = img.size
    lado = int(H * lado_frac)
    x0 = (W - lado) // 2
    y0 = (H - lado) // 2
    return img.crop((x0, y0, x0 + lado, y0 + lado))


def gerar_ia(res, form, saida, forca=0.42, passos=22, foco="mandala",
             semente=None, estilo=None, usar_controle=True):
    """Repinta a obra real (`res` = retorno de `colagem.gerar_obra()`).

    res: dict com "caminho", "dados", "asc_signo", "sol_signo", "verso"...
    form: dict com cultura/tema/feeling/nome (para o prompt).
    saida: caminho PNG de saída.
    usar_controle: ControlNet canny preserva a roda e os arquétipos (padrão);
      em memória apertada passe False (volta ao img2img puro).
    """
    import prompt_arte
    rng = random.Random(semente if semente is not None
                        else random.Random().randrange(1 << 30))
    seed = rng.randrange(1 << 30)
    estilo = estilo or _estilo_sorteado(rng)

    # CLIP do SD1.5 trunca após 77 tokens: o prompt da GERAÇÃO é o curto
    # (estilo + fatos na frente). O longo fica salvo p/ documentação.
    prompt_curto = prompt_arte.gerar_prompt_curto(
        res["dados"], res.get("asc_signo", ""), res.get("sol_signo", ""),
        res.get("arquetipos_asc", []), res.get("arquetipos_sol", []),
        cultura=form.get("cultura"), tema=form.get("tema"),
        feeling=form.get("feeling"), estilo=estilo)
    if foco == "detalhe":
        prompt_curto += (
            "\nFoco na mandala central gigante, planeta em destaque, "
            "detalhes das constelações.")
    prompt_longo = prompt_arte.gerar_prompt_resource(
        res, cultura=form.get("cultura"), tema=form.get("tema"),
        feeling=form.get("feeling"), nome=form.get("nome", ""))

    from PIL import Image
    img = Image.open(res["caminho"]).convert("RGB")
    if foco == "mandala":
        img = _recorte_mandala(img)
    img = img.resize((512, 512), Image.LANCZOS)

    import torch
    g = torch.Generator("cpu")
    g.manual_seed(seed)

    usar_cc = bool(usar_controle and int(os.environ.get("IA_USAR_CC", "1")))
    if usar_cc:
        try:
            pipe = _carregar_com_controle()
            bordas = Image.fromarray(_bordas_canny(img, rng), mode="L")
            extra = dict(control_image=bordas,
                         controlnet_conditioning_scale=0.6)
        except Exception as _ecc:  # pragma: no cover — memória/baixa
            print("(sem ControlNet:", _ecc, ")")
            pipe = _carregar()
            extra = {}
    else:
        pipe = _carregar()
        extra = {}

    image = pipe(
        prompt=prompt_curto, negative_prompt=_NEGATIVO, image=img,
        strength=forca, num_inference_steps=passos, guidance_scale=7.5,
        generator=g, **extra,
    ).images[0].save(saida)

    return {"caminho": saida, "prompt": prompt_curto,
            "prompt_longo": prompt_longo, "semente": seed,
            "estilo": estilo, "forca": forca, "foco": foco,
            "controlnet": usar_cc}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Repintura IA da obra (CPU)")
    ap.add_argument("--data", required=True)
    ap.add_argument("--hora", default="12:00")
    ap.add_argument("--local", required=True)
    ap.add_argument("--cultura", default=None)
    ap.add_argument("--tema", default=None)
    ap.add_argument("--feeling", default=None)
    ap.add_argument("--nome", default="")
    ap.add_argument("--forca", type=float, default=0.42)
    ap.add_argument("--passos", type=int, default=22)
    ap.add_argument("--foco", default="mandala", choices=["mandala", "detalhe"])
    ap.add_argument("--estilo", default=None,
                    help="traço do desenho (sorteado se ausente)")
    ap.add_argument("--semente", type=int, default=None)
    ap.add_argument("--sem-controlnet", action="store_true",
                    help="não baixa/usa o ControlNet (padrão: usa)")
    ap.add_argument("--saida", default=None)
    a = ap.parse_args()
    saida = a.saida or f"/mnt/dados/home-italivre/iastro-ia/mapas/obra-ia-{a.data}.png"
    obra = f"/mnt/dados/home-italivre/iastro-ia/mapas/obra-{a.data}.png"
    # recarrega o mapa real para o prompt (mesma entrada do colagem)
    import colagem
    form = {"data": a.data, "hora": a.hora, "local": a.local,
            "cultura": a.cultura, "feeling": a.feeling, "nome": a.nome}
    _r = colagem.gerar_obra(form, saida=obra)
    out = gerar_ia(_r, {**form, "tema": a.tema}, saida, forca=a.forca,
                   passos=a.passos, foco=a.foco, semente=a.semente,
                   estilo=a.estilo, usar_controle=not a.sem_controlnet)
    print("imagem IA em:", out["caminho"])
    print("semente:", out["semente"], "| força:", out["forca"],
          "| estilo:", out["estilo"], "| controlnet:", out["controlnet"])