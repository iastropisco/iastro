#!/usr/bin/env python3
"""Versão INTERATIVA (HTML+SVG) da colagem do planetário.

Gera uma página única e auto-contida (sem dependência de internet pra rodar —
as imagens são embutidas em base64) que combina:

  • roda do zodíaco em SVG puro (hover mostra o signo, seus arquétipos e os
    planetas que ali passam);
  • fotos REAIS dos telescópios com lupa/zoom (JWST, Hubble, Euclid...);
  • a linha do tempo da história recente da cosmologia;
  • o verso derivado do tema/sentimento;
  • o traço à mão (se o usuário desenhou);
  • botão de BAIXAR o PNG (reusa o colagem.py) e impressão.

Uso:
    /mnt/dados/home-italivre/iastro-ia/venv/bin/python interativo.py \
        --data 1982-11-20 --hora 01:30 --local "belo horizonte" \
        --cultura folclore --tema "maré de estrelas" --feeling esperanca \
        --saida mapas/obra-interativa.html
"""
import argparse
import base64
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import colagem  # noqa: E402
import mapa_astral  # noqa: E402

SIGNOS = colagem.SIGNOS


def b64(arq):
    if not arq or not os.path.exists(arq):
        return None
    with open(arq, "rb") as f:
        return base64.b64encode(f.read()).decode()


def ver(src):
    if not src:
        return "data:"
    ext = "png" if ".png" in src else "jpg"
    return f"data:image/{ext};base64,{b64(src)}"


def gerar_html(form, saida=None):
    data = form["data"]
    hora = form.get("hora", "12:00")
    local = form.get("local")
    local_c = colagem._local_canonico(local)
    _base = (mapa_astral.LOCALIDADES.get(local_c) or (None, None))
    lat = form.get("lat") or _base[0]
    lon = form.get("lon") or _base[1]
    if lat is None:
        lat, lon = mapa_astral.LOCALIDADES.get("belo horizonte")
    tz = mapa_astral.tz_do_local(local_c)
    m = mapa_astral.calc(data, hora, lat, lon, tz_horas=tz)

    cultura = form.get("cultura")
    # rótulo legível: lista de culturas → "afro + folclore + indígena"
    _culturas_txt = {
        "afro": "afro-brasileira", "folclore": "folclore",
        "indigena": "indígena", "capixaba": "capixaba",
        "carioca": "carioca", "mapuche": "mapuche", "nordestino": "nordestino",
        "zodiaco": "zodíaco",
    }
    if isinstance(cultura, (list, tuple)):
        _cultura_txt = " + ".join(_culturas_txt.get(c, c) for c in cultura)
    elif cultura:
        _cultura_txt = _culturas_txt.get(cultura, cultura)
    else:
        _cultura_txt = "afro + folclore + indígena (multi-cultura)"
    import sqlite3
    conn = sqlite3.connect(colagem.DB)
    cur = conn.cursor()
    verso = colagem.gerar_verso(form.get("tema"), form.get("feeling"),
                                m["asc"].split(" ")[0], m["planetas"]["Sol"]["signo"])

    fotos = colagem.fotos_mapa()

    # ---- roda em SVG (mesma orientação da obra: ASC à esquerda no
    # horizonte leste, DESC à direita, MC no alto do meridiano, IC embaixo)
    CX, CY, R_EXT, R_INT = 380, 380, 332, 254
    R_PL = R_INT - 22          # anel dos planetas
    asc_lon = m["casas"][0]["lon"]
    mc_lon = (m["casas"][9]["lon"] if len(m.get("casas", [])) > 9 else 83)
    al = (mc_lon - asc_lon + 180) % 360  # papel do MC após a virada

    def obra_pt(R, lon):
        # ângulo no papel (0=este/direita, 90=alto) igual ao do colagem.py
        a = math.radians((lon + 180 - asc_lon) % 360)
        return (CX + R * math.cos(a), CY - R * math.sin(a))

    segs = []
    for z, nome in enumerate(SIGNOS):
        cor = "#%02x%02x%02x" % tuple(colagem.COR_SIGNO[nome])
        l0, l1 = z * 30, (z + 1) * 30
        x0, y0 = obra_pt(R_EXT, l0)
        x1, y1 = obra_pt(R_INT, l0)
        x2, y2 = obra_pt(R_INT, l1)
        x3, y3 = obra_pt(R_EXT, l1)
        mx, my = obra_pt((R_INT + R_EXT) / 2, (l0 + l1) / 2)
        # planetas que caem nesse signo
        pls = [p for p, v in m["planetas"].items() if v["signo"] == nome]
        arquetipos = colagem.buscar_arquetipos_do_signo(cur, nome, cultura)
        ar_nomes = ", ".join(a[1].split(" (")[0] for a in arquetipos) or "—"
        segs.append(f"""
<path d="M{x0:.1f},{y0:.1f} L{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f} L{x3:.1f},{y3:.1f} Z"
      fill="{cor}" opacity="0.38" stroke="#7f93c9" stroke-width="1">
   <title>{nome} · {'+'.join(pls) if pls else 'sem planetas'} · ark: {ar_nomes}</title></path>
<text x="{mx:.1f}" y="{my-14:.1f}" font-size="56" text-anchor="middle"
      dominant-baseline="central" fill="#f5f8ff" class="sgn">{colagem.SIMB[nome]}</text>
<text x="{mx:.1f}" y="{my+44:.1f}" font-size="20" text-anchor="middle"
      fill="#d7e2fb" class="sgn">{nome}</text>""")

    # planetas: bolas suaves + SÓ o símbolo (os nomes ficam na tabela abaixo)
    grupos = {}
    for _n, _v in m["planetas"].items():
        grupos.setdefault(_v["signo"], []).append(_n)
    pts = ""
    for nome, pl in m["planetas"].items():
        sg = pl["signo"]
        idx = grupos[sg].index(nome)
        r_pl = R_PL - idx * 26   # empilha para dentro se houver conjunção
        x, y = obra_pt(r_pl, pl["lon"])
        cor = "#%02x%02x%02x" % tuple(colagem.COR_PLANETA.get(nome, (200, 200, 200)))
        glifo = colagem.GLIFO.get(nome, "★")
        retro = " R" if pl.get("retrogrado") else ""
        graus = f'{pl["signo"]} {pl["graus"]}°{pl["min"]:02d}′{pl["seg"]:02d}″{retro}'
        pts += (f'<g class="pl">'
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="15" fill="#040711" opacity=".5"/>'
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="13" fill="{cor}" stroke="#fff" stroke-width="2">'
                f'<title>{nome} · {graus}</title></circle>'
                f'<text x="{x:.1f}" y="{y:.1f}" font-size="17" text-anchor="middle" '
                f'paint-order="stroke" stroke="#0a0d18" stroke-width="2" font-weight="bold" '
                f'dominant-baseline="central" fill="#fff" class="sgn">{glifo}</text>'
                f'</g>')

    # linhas do horizonte (ASC–DESC) e do meridiano (MC–IC), como na obra
    hx0, hy0 = obra_pt(R_EXT + 8, asc_lon)
    hx1, hy1 = obra_pt(R_EXT + 8, (asc_lon + 180) % 360)
    mx0, my0 = obra_pt(R_EXT + 8, mc_lon)
    mx1, my1 = obra_pt(R_EXT + 8, (mc_lon + 180) % 360)
    # linhas do horizonte (ASC–DESC) e do meridiano (MC–IC), como na obra
    hx0, hy0 = obra_pt(R_EXT + 8, asc_lon)
    hx1, hy1 = obra_pt(R_EXT + 8, (asc_lon + 180) % 360)
    mx0, my0 = obra_pt(R_EXT + 8, mc_lon)
    mx1, my1 = obra_pt(R_EXT + 8, (mc_lon + 180) % 360)
    eixos = (f'<line x1="{hx0:.1f}" y1="{hy0:.1f}" x2="{hx1:.1f}" y2="{hy1:.1f}" '
             f'class="eixo" stroke="#ffe4a3" opacity=".55"/>'
             f'<line x1="{mx0:.1f}" y1="{my0:.1f}" x2="{mx1:.1f}" y2="{my1:.1f}" '
             f'class="eixo" stroke="#ffe4a3" opacity=".35"/>')

    # cartões do horizonte/meridiano fixados nas beiradas do quadro, com os
    # eixos desenhados na roda (mesma leitura da obra)
    mcx, mcy = obra_pt(R_EXT + 26, mc_lon)
    icx, icy = obra_pt(R_EXT + 26, (mc_lon + 180) % 360)
    marcas = (f'<text x="6" y="{CY:.0f}" font-size="24" text-anchor="start" '
              f'font-weight="bold" fill="#ff6a5e" class="sgn">ASC</text>'
              f'<text x="6" y="{CY+20:.0f}" font-size="14" text-anchor="start" '
              f'fill="#d7e2fb" class="sgn">leste</text>'
              f'<text x="754" y="{CY:.0f}" font-size="24" text-anchor="end" '
              f'font-weight="bold" fill="#ff6a5e" class="sgn">DESC</text>'
              f'<text x="754" y="{CY+20:.0f}" font-size="14" text-anchor="end" '
              f'fill="#d7e2fb" class="sgn">oeste</text>'
              f'<text x="{mcx:.1f}" y="{mcy+7:.1f}" font-size="24" text-anchor="middle" '
              f'font-weight="bold" fill="#6f9bff" class="sgn">MC</text>'
              f'<text x="{icx:.1f}" y="{icy+7:.1f}" font-size="24" text-anchor="middle" '
              f'font-weight="bold" fill="#6f9bff" class="sgn">IC</text>')

    roda = ('<svg class="roda" viewBox="0 0 760 760" role="img" '
            'aria-label="roda do zodíaco">' + eixos + "".join(segs) + pts
            + marcas + "</svg>")

    # ---- fotos dos telescópios (lightbox zoom) ----
    galeria = ""
    corpos = ["jupiter", "saturno", "lua", "marte", "urano", "netuno"]
    for corpo in corpos:
        p, info = colagem.ler_marco(fotos, corpo)
        if not p:
            continue
        b = b64(p)
        if not b:
            continue
        tel = "jwst" if "jwst" in p else ("hubble" if "hubble" in p else
              "euclid" if "euclid" in p else "nasa")
        galeria += f'''
<figure class="astro">
  <img src="data:image/png;base64,{b}" alt="{corpo}" class="zoom"
       onclick="abre(this)" loading="lazy">
  <figcaption>{corpo} <small>· {info.get("telescopio","NASA")} · {info.get("ano","")}</small></figcaption>
</figure>'''

    # ---- linha do tempo ----
    telj = colagem._carrega_json("telescopios.json")
    tl = "".join(f'<div class="tono"><b>{t["ano"]}</b> {t["titulo"]} — {t["texto"]}</div>'
                 for t in telj.get("linha_tempo", []))

    # nomes dos arquétipos (Sol e Asc) para o cartão
    sol_signo = m["planetas"]["Sol"]["signo"]
    asc_signo = m["asc"].split(" ")[0]
    def _nomes(signo):
        return ", ".join(a[1].split(" (")[0]
                         for a in colagem.buscar_arquetipos_do_signo(cur, signo, cultura)) or "—"
    sol_texto = _nomes(sol_signo)
    asc_texto = _nomes(asc_signo)

    # ── explorador de arquétipos (CLICÁVEL → modal com descrição/associação) ──
    def _detalhes(signo):
        chave = colagem._sem_acentos(signo)
        cur.execute(
            "SELECT ar.nome, ar.cultura, ar.elemento, ar.simbolo, ar.historia, "
            "ar.corresponde_a, ar.regiao "
            "FROM correspondencia c JOIN arquetipo ar ON ar.id=c.id_arquetipo "
            "WHERE lower(c.chave)=?", (chave,))
        return cur.fetchall()

    def _galeria_arquetipos(signo, rotulo, cor_hex):
        dets = _detalhes(signo)
        blocos = []
        for nome, cultura, elem, simb, hist, corr, regiao in dets:
            n_curto = nome.split(" (")[0]
            img_pd = colagem.ARQ_IMAGEM.get(colagem._sem_acentos(n_curto))
            if img_pd:
                p = os.path.join(colagem.DIR_PD, img_pd + ".png")
                thumb = f'<div class="tilla-thumb"><img src="{ver(p)}" alt=""></div>'
            else:
                thumb = f'<div class="tilla-thumb padrao">{colagem.SIMB.get(signo,"✦")}</div>'
            elem_html = f"<span class='chip'>{cultura or ''} · {elem or ''}</span>"
            bloco = f'''<div class="tilla" data-nome="{nome}" onclick="abreArq(this)" role="button" tabindex="0">
              {thumb}
              <div class="tilla-body"><b>{n_curto}</b>
                <div class="tilla-meta">{elem_html} <span>→ {corr or '—'}</span></div>
              </div>
            </div>
            <div class="modal" data-nome="{nome}">
              <div class="modal-card">
                <button class="x" onclick="this.parentNode.parentNode.style.display='none'">✕</button>
                <h3>{nome}</h3>
                <div class="mod-info">
                  <span class="chip">{cultura or 'cultura'}</span>
                  <span class="chip">{elem or ''}</span>
                  <span class="chip">responde a: <b>{corr or '—'}</b></span>
                </div>
                <p class="mod-simb"><b>Símbolo:</b> {simb or '—'}</p>
                <p class="mod-hist">{hist or '—'}</p>
                <p class="mod-reg"><b>Região:</b> {regiao or '—'}</p>
              </div>
            </div>'''
            blocos.append(bloco)
        return (f'<div class="cartao"><h2>{rotulo}</h2>'
                f'<div class="tillas">{"".join(blocos) or "<p>sem dados</p>"}</div></div>')

    explosol = _galeria_arquetipos(sol_signo, f"Sol em {sol_signo}",
                                   colagem.COR.get(sol_signo) or (200, 200, 200))
    expasc = _galeria_arquetipos(asc_signo, f"Ascendente em {asc_signo}",
                                 colagem.COR.get(asc_signo) or (200, 200, 200))

    # ── referências bibliográficas/etnográficas (para o botão 'Referências') ──
    refs = []
    chaves = ["sol", "lua", "mercurio", "venus", "marte", "jupiter",
              "saturno", colagem._sem_acentos(sol_signo),
              colagem._sem_acentos(asc_signo)]
    for chv in chaves:
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='correspondencia'")
        if cur.fetchone() is None:
            break
        cur.execute(
            "SELECT c.nome, c.fonte, c.certeza FROM correspondencia c "
            "WHERE lower(c.chave)=? AND c.fonte IS NOT NULL AND c.fonte<>'' "
            "ORDER BY c.certeza", (chv,))
        for nm, fonte, certeza in cur.fetchall():
            refs.append((nm, fonte, certeza))
    vistos = set()
    refs_uni = []
    for nm, fonte, certeza in refs:
        ch = (nm, fonte)
        if ch in vistos:
            continue
        vistos.add(ch)
        refs_uni.append((nm, fonte, certeza))
    refs_html = "".join(
        f'<div class="ref"><span class="ref-nome">{nm}</span>'
        f'<span class="ref-fonte">{fonte or "—"}</span>'
        f'<span class="chip">{certeza or ""}</span></div>'
        for nm, fonte, certeza in refs_uni[:40]) or "<p>sem referências</p>"

    logo_b64 = ""
    if os.path.exists(colagem.LOGO_PLANETARIO):
        _b = b64(colagem.LOGO_PLANETARIO)
        if _b:
            logo_b64 = f"data:image/webp;base64,{_b}"
    logo_el = (f'<div class="logo-seal"><img src="{logo_b64}" alt="logo,Planetário" '
               f'class="logo-img"></div>' if logo_b64 else "")

    modal_refs = f"""
<div class="modal" id="modal-ref">
  <div class="modal-card">
    <button class="x" onclick="document.getElementById('modal-ref').style.display='none'">✕</button>
    <h3>📚 Referências & sugestões</h3>
    <p class="refs-intro">Cada figura e cada frase deste mapa tem raiz em fontes
      respeitadas (tradição oral, etnoastronomia, obras citadas). Se você conhece
      uma fonte melhor, uma correção ou uma frase — sugira abaixo, nós aprimoramos:
      cada uso do planetário ajuda a melhorar o arsenal.</p>
    <div class="refs">{refs_html}</div>
    <textarea id="sugestao" rows="4"
      placeholder="Escreva aqui sua sugestão de alteração ou nova referência..."></textarea>
    <div class="refs-actions">
      <button onclick="salvaSugestao()">💾 Salvar sugestão (neste dispositivo)</button>
      <button class="ghost" onclick="exportaSugestoes()">📤 Exportar sugestões</button>
    </div>
    <div id="sugok" class="sugok"></div>
  </div>
</div>"""

    def _hex(cor):
        return "#%02x%02x%02x" % tuple(cor[:3])

    # ── Tabela do céu (a parte de baixo: símbolo · nome · signo · aspectos · elementos)
    linhas_tab = ""
    ordem_pl = [n for n in (colagem.PLANETAS_10 + ["Quíron", "Lilith",
                 "Ceres", "Pallas", "Juno", "Vesta"]) if n in m["planetas"]]
    for nome in ordem_pl:
        pl = m["planetas"][nome]
        glif = colagem.GLIFO.get(nome, "★")
        retr = (' <span class="retr" title="retrógrado">R</span>' if pl.get("retrogrado") else "")
        linhas_tab += (
            f'<tr><td class="tab-g">{glif}</td><td class="tab-n">{nome}{retr}</td>'
            f'<td>{colagem.SIMB.get(pl["signo"], "")} {pl["signo"]}</td>'
            f'<td>{pl["graus"]}°{pl["min"]:02d}′{pl["seg"]:02d}″</td>'
            f'<td class="tab-e">{colagem.ELEM.get(pl["signo"], "")}</td></tr>')

    asp_pares = []
    try:
        asp_pares = colagem._aspectos(m) or []
    except Exception:
        asp_pares = []
    asp_html = "".join(
        f'<span class="asp-chip" style="color:{_hex(cor)};border-color:{_hex(cor)}">'
        f'{colagem.GLIFO.get(a, a)}–{colagem.GLIFO.get(b, b)} {tipo} · {ang:.0f}°</span>'
        for a, b, tipo, cor, ang, _, _ in asp_pares) or (
        '<p class="asp-p">nenhum aspecto dentro da orbe de 7°</p>')

    elem_qtd = {}
    for e in ("fogo", "terra", "ar", "água"):
        elem_qtd[e] = sum(
            1 for n in ordem_pl if colagem.ELEM.get(m["planetas"][n]["signo"]) == e)
    _max = max(elem_qtd.values()) or 1
    _simb_e = {"fogo": "△", "terra": "▽", "ar": "△", "água": "▽"}
    _nome_e = {"fogo": "Fogo", "terra": "Terra", "ar": "Ar", "água": "Água"}
    elem_html = "".join(
        f'<div class="elemrow"><span class="elem-ico" style="color:{_hex(colagem.ELEM_COR[e])}">'
        f'{_simb_e[e]}</span><span class="elem-name">{_nome_e[e]}</span>'
        f'<span class="elembar"><span class="elemfill" style="width:{100 * n / _max:.0f}%;'
        f'background:{_hex(colagem.ELEM_COR[e])}"></span></span>'
        f'<span class="elem-n">{n}</span></div>'
        for e, n in elem_qtd.items())

    tabla = f"""<div class="cartao" style="margin-top:32px">
      <h2>Tabela do céu · símbolo, nome e signo de cada planeta</h2>
      <table class="astrotab"><thead><tr><th></th><th>planeta</th><th>signo</th>
      <th>grau</th><th>elemento</th></tr></thead><tbody>{linhas_tab}</tbody></table>
      <div class="bloco2">
        <div class="bloco-asp"><h2>Aspectos</h2><div class="asps">{asp_html}</div></div>
        <div class="bloco-elem"><h2>Equilíbrio dos elementos</h2>{elem_html}</div>
      </div>
    </div>"""

    html = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mapa Astral Interativo · Planetário</title>
<style>
  :root{{--bg:#05080f;--az:#7f93c9;--doura:#ffe4a3;--vidro:rgba(255,255,255,.045);}}
  *{{box-sizing:border-box}}
  body{{margin:0;color:#e8eefb;background:
      radial-gradient(circle at 50% 0%,#26305e 0%,#0d1220 45%,#05080f 100%);
     font-family:'Georgia',serif;min-height:100vh;
     background-image:
       radial-gradient(1px 1px at 12% 22%, #fff, transparent),
       radial-gradient(1px 1px at 34% 58%, #fff, transparent),
       radial-gradient(2px 2px at 61% 14%, #fff3, transparent),
       radial-gradient(1px 1px at 78% 36%, #fff, transparent),
       radial-gradient(1px 1px at 51% 76%, #ffff, transparent),
       radial-gradient(2px 2px at 88% 62%, #fff3, transparent),
       radial-gradient(1px 1px at 22% 84%, #fff, transparent),
       radial-gradient(1px 1px at 96% 22%, #fff, transparent),
       radial-gradient(circle at 50% 0%,#26305e 0%,#0d1220 45%,#05080f 100%);
     background-blend-mode:screen}}
h1{{font-weight:500;letter-spacing:.12em;color:#f7faff;text-align:center;
      margin:44px 8px 2px;text-shadow:0 2px 18px rgba(127,147,201,.45);
      font-size:clamp(34px,6vw,60px)}}
  .nome-plan{{background:linear-gradient(92deg,#ffe4a3,#ffb37a,#d39aff,#7fd4ff,
             #c6ffb0,#ffe4a3);background-size:300% 100%;
             -webkit-background-clip:text;background-clip:text;color:transparent;
             text-decoration:none;letter-spacing:.12em;
             animation:titulo 9s linear infinite}}
  .nome-plan:hover{{filter:drop-shadow(0 0 20px rgba(255,228,163,.55))}}
  @keyframes titulo{{0%{{background-position:0% 50%}}
                    100%{{background-position:300% 50%}}}}
  .sub{{text-align:center;color:#b9c9f2;margin:6px 8px 24px;font-size:14px;
        line-height:1.9}}
  .link-chip{{display:inline-block;margin-left:10px;padding:6px 14px;border-radius:30px;
             border:1px solid rgba(127,147,201,.55);color:#ffe4a3;text-decoration:none;
             font-weight:bold;letter-spacing:.04em;font-size:13px;
             background:rgba(127,147,201,.12);transition:transform .12s, background .12s}}
  .link-chip:hover{{transform:translateY(-1px);background:rgba(127,147,201,.26)}}
  .wrap{{max-width:1120px;margin:0 auto;padding:16px 20px 40px}}
  .grid{{display:grid;grid-template-columns:680px 1fr;gap:28px;align-items:start}}
  @media(max-width:1000px){{.grid{{grid-template-columns:1fr}}}}
  .roda{{width:100%;height:auto;display:block}}
.cartao{{background:var(--vidro);border:1px solid rgba(127,147,201,.25);
          border-radius:20px;padding:20px;backdrop-filter:blur(6px);
          box-shadow:0 12px 30px rgba(0,0,0,.35)}}
  h2{{font-size:15px;letter-spacing:.2em;color:#d8e4ff;text-transform:uppercase;
      border-bottom:1px solid rgba(127,147,201,.25);padding-bottom:12px;margin-top:0}}
.verso{{font-style:italic;color:#e2eaff;line-height:1.7;margin:14px 0;font-size:15px}}
  .galeria{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
  .astro img{{width:100%;height:150px;object-fit:cover;border-radius:14px;
              cursor:zoom-in;transition:transform .2s ease, box-shadow .2s ease;
              border:1px solid rgba(127,147,201,.3);box-shadow:0 6px 16px rgba(0,0,0,.3)}}
  .astro img:hover{{transform:scale(1.03);box-shadow:0 10px 24px rgba(0,0,0,.45)}}
  .astro figcaption{{font-size:12px;color:#a4b6e2;margin-top:6px}}
  .tono{{font-size:15px;color:#c3d1f5;margin:10px 0;line-height:1.6;
        border-left:3px solid var(--doura);padding-left:12px}}
  .tono b{{color:var(--doura)}}
  .btns{{text-align:center;margin:20px 0;display:flex;gap:10px;justify-content:center;
        flex-wrap:wrap}}
  button{{background:linear-gradient(135deg,#ffe4a3,#f3c96b);color:#221a05;border:none;
         padding:12px 22px;border-radius:30px;font-weight:bold;cursor:pointer;
         box-shadow:0 6px 16px rgba(255,228,163,.25);transition:transform .12s}}
  button:hover{{transform:translateY(-2px)}}
  button.ghost{{background:none;border:1px solid rgba(127,147,201,.6);color:#d8e4ff;
               box-shadow:none}}
  .lupa{{position:fixed;inset:0;background:rgba(0,0,0,.88);display:none;
        align-items:center;justify-content:center;z-index:9;cursor:zoom-out;
        backdrop-filter:blur(4px)}}
  .lupa img{{max-width:92vw;max-height:88vh;border-radius:12px;border:2px solid var(--doura)}}
  .rodape{{text-align:center;color:#8fa0cc;font-size:13px;margin-top:28px;line-height:1.7}}
  .sgn{{pointer-events:none}}
  .eixo{{pointer-events:none}}
  .tillas{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));
          gap:12px;margin-top:10px}}
.tilla{{display:flex;gap:12px;align-items:center;text-align:left;
          background:rgba(255,255,255,.05);border:1px solid rgba(127,147,201,.25);
          border-radius:16px;padding:12px;cursor:pointer;color:#e8eefb;font-family:inherit;
          transition:transform .14s ease, border-color .14s ease}}
  .tilla:hover{{transform:translateY(-3px);border-color:var(--doura)}}
  .tilla-thumb{{width:64px;height:64px;border-radius:12px;overflow:hidden;flex:0 0 64px;
                border:1px solid var(--doura)}}
  .tilla-thumb img{{width:100%;height:100%;object-fit:cover}}
  .tilla-thumb.padrao{{display:flex;align-items:center;justify-content:center;
                       font-size:32px;background:linear-gradient(135deg,#2a3558,#141b30)}}
  .tilla-body b{{display:block;font-size:15px;color:#f5f8ff}}
  .tilla-meta{{font-size:12px;color:#a4b6e2;margin-top:4px;line-height:1.4}}
  .chip{{display:inline-block;background:rgba(127,147,201,.18);border-radius:20px;
        padding:3px 10px;font-size:11px;margin:2px 4px 0 0}}
  .modal{{display:none;position:fixed;inset:0;background:rgba(3,5,10,.85);
         align-items:center;justify-content:center;z-index:20;padding:18px;
         backdrop-filter:blur(4px)}}
  .modal-card{{background:linear-gradient(160deg,#1a2340,#0c1120);border:1px solid var(--doura);
              border-radius:20px;max-width:560px;width:100%;max-height:86vh;overflow:auto;
              padding:28px;position:relative;box-shadow:0 18px 50px rgba(0,0,0,.55)}}
  .modal-card h3{{color:var(--doura);margin:0 0 12px;letter-spacing:.04em;font-size:18px}}
  .mod-info{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}}
  .mod-simb{{color:#cfe0ff;font-size:14px;margin:10px 0}}
  .mod-hist{{color:#dce6ff;line-height:1.7;font-size:14px}}
  .mod-reg{{color:#a4b6e2;font-size:13px;margin-top:14px;border-top:1px solid rgba(127,147,201,.25);padding-top:12px}}
  .x{{position:absolute;top:10px;right:14px;background:none;border:none;color:var(--doura);
     font-size:22px;cursor:pointer}}
  .logo-seal{{width:178px;height:178px;border-radius:50%;overflow:hidden;margin:28px auto 24px;
             border:4px solid var(--doura);background:#0a0f1e;
             box-shadow:0 0 44px rgba(255,228,163,.45)}}
  .logo-img{{width:100%;height:100%;object-fit:cover}}
  .card-gene{{background:var(--vidro);border:1px dashed rgba(127,147,201,.35);
             border-radius:16px;padding:12px 16px;font-size:13px;color:#c3d1f5;
             line-height:1.6;margin-top:14px}}
  .bloco2{{display:grid;grid-template-columns:1.4fr 1fr;gap:18px;margin-top:6px}}
  @media(max-width:720px){{.bloco2{{grid-template-columns:1fr}}}}
.astrotab{{width:100%;border-collapse:collapse;font-size:16px;margin:8px 0 18px}}
  .astrotab th{{color:#a4b6e2;font-weight:normal;font-size:12px;letter-spacing:.18em;
                text-align:left;text-transform:uppercase;padding:8px 10px;
                border-bottom:1px solid rgba(127,147,201,.3)}}
  .astrotab td{{padding:9px 10px;border-bottom:1px solid rgba(127,147,201,.16);
                color:#e2eaff}}
  .astrotab tr:hover td{{background:rgba(127,147,201,.08)}}
  .tab-g{{font-size:20px;color:var(--doura)}}
  .tab-n{{font-weight:bold;color:#f5f8ff}}
  .tab-e{{color:#a4b6e2;font-style:italic}}
  .retr{{color:#ff9a7d;font-size:11px;font-weight:bold;margin-left:3px}}
  .asps{{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}}
  .asp-chip{{border:1px solid;border-radius:20px;padding:4px 11px;font-size:12px;
            background:rgba(255,255,255,.04)}}
  .asp-p{{color:#a4b6e2;font-size:12px}}
  .elems{{display:flex;flex-direction:column;gap:9px;margin-top:10px}}
  .elemrow{{display:flex;align-items:center;gap:10px}}
  .elem-ico{{width:18px;text-align:center;font-size:16px}}
  .elem-name{{width:56px;font-size:12px;color:#d8e4ff}}
  .elembar{{flex:1;height:10px;border-radius:6px;background:rgba(255,255,255,.08);
           overflow:hidden}}
  .elemfill{{display:block;height:100%;border-radius:6px;min-width:2px;
            transition:width .4s ease}}
  .elem-n{{width:18px;text-align:right;font-size:12px;color:#a4b6e2}}
  .nome-plan{{color:var(--doura);text-decoration:none;letter-spacing:.12em}}
  .nome-plan:hover{{text-shadow:0 0 14px rgba(255,228,163,.6)}}
.refs{{max-height:200px;overflow:auto;border:1px solid rgba(127,147,201,.3);
        border-radius:14px;padding:12px;margin:14px 0;font-size:14px}}
  .ref{{padding:8px 6px;border-bottom:1px dashed rgba(127,147,201,.3);display:flex;gap:10px;
        align-items:first baseline;flex-wrap:wrap}}
  .ref-nome{{color:var(--doura);font-weight:bold;min-width:150px}}
  .ref-fonte{{color:#c3d1f5;flex:1}}
  .refs-intro{{color:#a4b6e2;font-size:14px;line-height:1.6}}
  textarea{{width:100%;background:#0c1120;color:#e8eefb;border:1px solid rgba(127,147,201,.35);
            border-radius:14px;padding:12px;font-family:inherit;font-size:14px}}
  .refs-actions{{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}}
  .sugok{{color:#7fe3a7;font-size:12px;margin-top:8px}}
</style></head><body>
<div class="lupa" id="lupa" onclick="this.style.display='none'"><img id="lupaimg" src=""></div>
{logo_el}
<h1><a class="nome-plan" href="{colagem.LINK_PLANETARIO}" target="_blank" rel="noopener">
{colagem.NOME_PLANETARIO}</a></h1>
<div class="sub">{data} · {hora} · {local} &nbsp;·&nbsp; cultura <b>{_cultura_txt}</b>
&nbsp;·&nbsp; tema <i>“{form.get('tema') or 'o teu nome'}”</i>
<a class="link-chip" href="{colagem.LINK_MAPS}" target="_blank" rel="noopener"
   title="{colagem.LINK_MAPS_LABEL}">📍 Ver no Google Maps</a></div>
<div class="btns">
  <button onclick="imprime()">🖨 Imprimir / PDF</button>
  <button class="ghost" onclick="baixaPng()">⬇ Baixar PNG</button>
  <button class="ghost" onclick="abreRefs()">📚 Referências</button>
</div>
<div class="wrap"><div class="grid">
  <div class="cartao">{roda}</div>
  <div>
    <div class="cartao"><h2>Céu · expressões deste mapa</h2>
      <div class="verso">{'<br>'.join(verso)}</div>
      <div class="tono"><b>Sol</b> em {sol_signo} · {sol_texto}</div>
      <div class="tono"><b>Asc</b> em {asc_signo} · {asc_texto}</div>
      <div class="tono"><b>Meio do Céu</b> {m['mc']}</div>
    </div>
    {explosol}
    {expasc}
    <div class="cartao"><h2>Os telescópios que subiram ao céu</h2>
      <div class="galeria">{galeria}</div></div>
    <div class="cartao"><h2>História recente da cosmologia</h2>{tl}</div>
  </div>
<div class="card-gene">💡 Para ler os desenhos da roda, do jeito da obra: o <b>ASC</b> sobe
no horizonte leste (à esquerda) e o <b>Descendente</b> desce a oeste (à
direita); o <b>MC</b> fica no alto do meridiano (em cima) e o <b>IC</b>
embaixo. O símbolo em cada bolinha é o planeta — o nome, o signo, o grau e o
equilíbrio dos elementos estão todos na <b>tabela abaixo</b>.</div>
</div>
{tabla}
<div class="rodape">Imagens: figuras em domínio público / CC (Wikimedia Commons);
NASA/ESA/CSA (telescópios, CC). Posições: Swiss Ephemeris · zodíaco tropical.
<br><a class="nome-plan" href="{colagem.LINK_PLANETARIO}" target="_blank" rel="noopener">
{colagem.LINK_LABEL}</a> · cada mapa é uma pintura única que nunca se repete.</div>
{modal_refs}
</div>
<script>
function abre(el){{document.getElementById('lupaimg').src=el.src;
  document.getElementById('lupa').style.display='flex';}}
function imprime(){{window.print();}}
function baixaPng(){{const u='{os.path.basename(png_esperado(form))}'; try{{window.open(u,'_blank');}}catch(e){{alert('gere o PNG com colagem.py primeiro');}}}}
function abreRefs(){{document.getElementById('modal-ref').style.display='flex';}}
function salvaSugestao(){{
  var t=document.getElementById('sugestao').value.trim();
  if(!t){{return;}}
  var s=JSON.parse(localStorage.getItem('planetario_sugestoes')||'[]');
  s.push({{data:new Date().toISOString().slice(0,10),texto:t}});
  localStorage.setItem('planetario_sugestoes',JSON.stringify(s));
  var ok=document.getElementById('sugok');
  ok.textContent='💾 Sugestão salva neste dispositivo ('+s.length+' no total). Boa parte do arsenal cresce assim.';
}}
function exportaSugestoes(){{
  var s=JSON.parse(localStorage.getItem('planetario_sugestoes')||'[]');
  var blob=new Blob([JSON.stringify(s,null,2)],{{type:'application/json'}});
  var a=document.createElement('a');
  a.href=URL.createObjectURL(blob);a.download='sugestoes-planetario.json';a.click();
}}
function abreArq(el){{
  var nome=el.getAttribute('data-nome');
  var mds=document.querySelectorAll('.modal');
  for(var i=0;i<mds.length;i++){{
    if(mds[i].getAttribute('data-nome')===nome){{mds[i].style.display='flex';}}
  }}
}}
document.addEventListener('click',function(e){{
  if(e.target.classList && e.target.classList.contains('modal')){{e.target.style.display='none';}}
}});
</script></body></html>"""

    if saida is None:
        saida = f"/mnt/dados/home-italivre/iastro-ia/mapas/obra-interativa.html"
    with open(saida, "w", encoding="utf-8") as f:
        f.write(html)
    return {"caminho": saida, "dados": m}


def p_is_signo(v, nome):
    return v["signo"] == nome


def arq_sol(form, cur):
    nomes = colagem.buscar_arquetipos_do_signo(cur, form["sol_signo"] if "sol_signo" in form else "Escorpião", form.get("cultura"))
    return ", ".join(a[1].split(" (")[0] for a in nomes) or "—"


def arq_asc(form, cur, m):
    asc = m["asc"].split(" ")[0]
    nomes = colagem.buscar_arquetipos_do_signo(cur, asc, form.get("cultura"))
    return ", ".join(a[1].split(" (")[0] for a in nomes) or "—"


def png_esperado(form):
    return f"obra-{form['data']}.png"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--hora", default="12:00")
    ap.add_argument("--local", default="belo horizonte")
    ap.add_argument("--cultura", default=None)
    ap.add_argument("--tema", default="o teu nome")
    ap.add_argument("--feeling", default="encantamento")
    ap.add_argument("--traco", default=None)
    ap.add_argument("--saida", default=None)
    a = ap.parse_args()
    r = gerar_html(vars(a), saida=a.saida)
    print("Gerado:", r["caminho"])