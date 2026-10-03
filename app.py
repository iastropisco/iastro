"""Iastro — o mapa do céu, gratuito.

Esta é a mesma obra do app da sua máquina, sem as camadas que não pagam o
peso na hospedagem: nada de Ollama, nada de ChromaDB, nada de difusão de
imagem, nada de upload de fonte desenhada. O motor (`motor/colagem.py`) é o
de sempre e o mapa sai idêntico — verificado pixel a pixel.

Por que tirar essas camadas: cada uma delas sozinha passa de 300 MB de
dependência e exige serviço rodando (Ollama) ou base vetorial (ChromaDB).
O motor do mapa, sozinho, é PIL + numpy + scipy + pyswisseph, e produz o
planetário inteiro em ~20 s.

O mapa é o completo, de graça: todas as camadas culturais, os planetas
externos, os asteróides, o saber das plantas e os céus das tradições. Não
existe versão curta.

Sobre as licenças: o acervo do céu tem 5 culturas de uso **não comercial**
(ver `site/LICENCAS.md`). Isso impede a venda, nunca a distribuição gratuita
— por isso o app é gratuito, e por isso ele pode usar o acervo inteiro.
O que continua obrigatório é creditar os autores, e a página de licenças faz
isso.

Nada é gravado. O mapa é desenhado, entregue e esquecido.
"""
import os
import sys
import tempfile
import time

import numpy as np
import streamlit as st

RAIZ = os.path.dirname(os.path.abspath(__file__))
MOTOR = os.path.join(RAIZ, "motor")
if MOTOR not in sys.path:
    sys.path.insert(0, MOTOR)

# Onde está o código. A AGPL (§13) exige que quem usa o site por
# rede possa chegar no fonte de graça — este é o caminho.
LINK_CODIGO = "https://github.com/SEU-USUARIO/iastro"

LOGO_SVG = os.path.join(RAIZ, "mapas", "iastro-logo.svg")
LOGO_CAB = os.path.join(RAIZ, "mapas", "logo-cabecalho.png")
LOGO_ICO = os.path.join(RAIZ, "mapas", "logo-icone.png")

def _b64(caminho):
    import base64
    try:
        with open(caminho, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return ""

st.set_page_config(page_title="iastro — o mapa do seu céu",
                    page_icon=LOGO_ICO if os.path.exists(LOGO_ICO) else "🔭",
                    layout="centered")
if os.path.exists(LOGO_CAB):
    st.logo(LOGO_CAB, icon_image=LOGO_ICO)

# CSS do universo — fundo estrelado, tipografia, cartões
LOGO_B64 = _b64(os.path.join(RAIZ, "mapas", "iastro-logo.png"))
st.markdown(f"""
<style>
:root {{
  --bg:#05080f; --az:#7f93c9; --doura:#ffe4a3; --vidro:rgba(255,255,255,.06);
  --borda:rgba(127,147,201,.3); --texto:#e8eefb; --muted:#9ab0d8; --muted2:#7a8db0;
}}
html, body, [data-testid="stAppViewContainer"] {{
  background:
    radial-gradient(circle at 50% 0%,#1a2540 0%,#0a0f1e 45%,#05080f 100%),
    radial-gradient(1px 1px at 12% 22%, #fff, transparent),
    radial-gradient(1px 1px at 34% 58%, #fff, transparent),
    radial-gradient(2px 2px at 61% 14%, #fff3, transparent),
    radial-gradient(1px 1px at 78% 36%, #fff, transparent),
    radial-gradient(2px 2px at 88% 62%, #fff3, transparent),
    radial-gradient(1px 1px at 22% 84%, #fff, transparent),
    radial-gradient(1px 1px at 96% 22%, #fff, transparent);
  background-blend-mode:screen;
  color:var(--texto);
  font-family:Georgia,'Times New Roman',serif;
  font-size:15px;
  line-height:1.55;
}}
[data-testid="stHeader"] {{background:transparent}}
.block-container {{padding-top:1rem;padding-bottom:2rem;max-width:760px}}
h1,h2,h3,h4 {{color:#f7faff;font-weight:500;letter-spacing:.06em;margin:0.6rem 0 0.4rem}}

/* Inputs e selects - texto CLARO em fundo ESCURO */
.stTextInput input, 
.stSelectbox div[data-baseweb="select"] > div,
.stSelectbox div[data-baseweb="select"] div[aria-selected="true"],
.stSelectbox div[data-baseweb="single-value"],
.stSelectbox div[data-baseweb="select"] input,
.stTextArea textarea {{
  background:#0b1020 !important;
  border:1px solid var(--borda) !important;
  color:#e8eefb !important;
  border-radius:10px !important;
  font-size:15px !important;
  font-family:inherit !important;
}}
.stTextInput input::placeholder,
.stSelectbox div[data-baseweb="select"] span,
.stSelectbox div[data-baseweb="single-value"],
.stSelectbox div[data-baseweb="select"] input::placeholder {{
  color:#7a8db0 !important;
}}
.stTextInput input:focus, 
.stSelectbox div[data-baseweb="select"] > div:focus-within {{
  border-color:var(--doura) !important;
  box-shadow:0 0 0 3px rgba(255,228,163,.18) !important;
  outline:none !important;
}}

/* Força texto CLARO em TODOS os elementos do selectbox */
div[data-baseweb="select"] * {{
  color:#e8eefb !important;
}}
div[data-baseweb="select"] div[role="option"] {{
  color:#e8eefb !important;
}}

/* Selectbox dropdown */
div[data-baseweb="popover"] ul li,
div[data-baseweb="popover"] ul li * {{
  background:#0b1020 !important;
  color:#e8eefb !important;
  padding:10px 14px !important;
  font-size:14px !important;
}}
div[data-baseweb="popover"] ul li:hover {{
  background:#141a30 !important;
}}

/* Radio buttons */
.stRadio label {{
  color:#e8eefb !important;
  font-size:14px !important;
}}
.stRadio div[role="radiogroup"] label {{
  background:var(--vidro) !important;
  border:1px solid var(--borda) !important;
  border-radius:10px !important;
  padding:10px 16px !important;
  margin:4px !important;
  transition:all .2s;
}}
.stRadio div[role="radiogroup"] label * {{
  color:#e8eefb !important;
}}
.stRadio div[role="radiogroup"] label:hover {{
  border-color:var(--doura) !important;
}}
.stRadio div[role="radiogroup"] label:has(input:checked) {{
  border-color:var(--doura) !important;
  background:rgba(255,228,163,.15) !important;
}}
.stRadio input[type="radio"] {{
  accent-color:var(--doura) !important;
}}
.stRadio input:checked + div {{
  border-color:var(--doura) !important;
  background:rgba(255,228,163,.12) !important;
}}

/* Botões */
.stButton > button[kind="primary"] {{
  background:linear-gradient(135deg,var(--doura),#f3c96b) !important;
  color:#1a1402 !important;
  border:none !important;
  border-radius:28px !important;
  padding:.75rem 2rem !important;
  font-weight:600 !important;
  font-size:15px !important;
  font-family:inherit !important;
  box-shadow:0 6px 20px rgba(255,228,163,.3) !important;
  transition:transform .12s, box-shadow .12s;
}}
.stButton > button[kind="primary"]:hover {{
  transform:translateY(-2px);
  box-shadow:0 10px 28px rgba(255,228,163,.45) !important;
}}
.stButton > button[kind="secondary"] {{
  background:var(--vidro) !important;
  border:1px solid var(--borda) !important;
  color:var(--texto) !important;
  border-radius:28px !important;
}}

/* Form e cards */
.stForm {{
  background:var(--vidro);
  border:1px solid var(--borda);
  border-radius:18px;
  padding:1.25rem;
  backdrop-filter:blur(8px);
  box-shadow:0 10px 28px rgba(0,0,0,.35);
}}
.stExpander {{
  border:1px solid var(--borda) !important;
  border-radius:14px !important;
  background:var(--vidro) !important;
}}
.stExpander summary {{
  color:var(--doura) !important;
  font-weight:500 !important;
}}

/* Textos auxiliares */
.stCaption, .stMarkdown p, .stAlert p {{color:var(--muted) !important;line-height:1.6}}
.stMarkdown h3 {{color:var(--doura) !important;font-size:16px !important;margin:1rem 0 0.5rem}}

/* Imagens */
[data-testid="stImage"] img {{
  border-radius:14px;
  border:1px solid var(--borda);
  box-shadow:0 8px 24px rgba(0,0,0,.3);
}}

/* Logo */
.logo-seal {{width:96px;height:96px;border-radius:50%;overflow:hidden;border:3px solid var(--doura);background:#0a0f1e;box-shadow:0 0 24px rgba(255,228,163,.35)}}
.logo-seal img {{width:100%;height:100%;object-fit:cover}}

/* Canvas de desenho */
canvas {{border-radius:12px !important;border:1px solid var(--borda) !important}}

/* Divisores */
hr {{border-color:var(--borda) !important;margin:1.5rem 0}}

/* Scrollbar */
::-webkit-scrollbar {{width:8px;height:8px}}
::-webkit-scrollbar-track {{background:#05080f}}
::-webkit-scrollbar-thumb {{background:var(--borda);border-radius:4px}}
::-webkit-scrollbar-thumb:hover {{background:var(--doura)}}
</style>
""", unsafe_allow_html=True)

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]
SENTIDOS = ["esperanca", "serenidade", "paixão", "pertencimento"]

# Culturas do céu - removidas regionais específicas (futuro)
CULTURAS = {
    "Todas as culturas": "todas",
    "Afro-brasileira / Orixás": "afro",
    "Folclore brasileiro": "folclore",
    "Indígena (Tupi, Tukano, Guarani…)": "indigena",
    "Mapuche (Chile)": "mapuche",
    "Nordestino (sertão)": "nordestino",
    "Zodíaco Ocidental": "zodiaco",
}


def _rotulo_cultura(valor):
    for r, v in CULTURAS.items():
        if v == valor:
            return r
    return valor


@st.cache_resource
def _motor():
    """Importa uma vez só: o Streamlit reexecuta o script a cada interação."""
    import caminhos
    caminhos.registrar_no_path()
    import colagem
    import localidades_brasil as lb
    return colagem, lb


def _ufs(lb):
    """Estados com município na base local."""
    ufs = {}
    for chave in lb.MUNICIPIOS:
        uf = (lb.MUNICIPIOS[chave].get("uf") or "").upper()
        if uf:
            ufs.setdefault(uf, []).append(chave)
    return {k: sorted(v) for k, v in sorted(ufs.items())}


def _sem_acentos(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", t)
                   if unicodedata.category(c) != "Mn").lower()


def _nome_mun(chave):
    return chave.split("|")[0]


def _procurar(ufs, uf, termo):
    """Municípios do estado que casam com o termo, sem levar em conta o
    acento. 'belo horizonte' acha BH mesmo escrito sem o 's' e sem acento.

    A lista inteira entra na busca. Uma versão anterior usava
    `ufs[uf][:800]` para caber no selectbox, e isso descartava de silêncio os
    últimos 53 municípios de Minas Gerais: quem nascesse em um deles não
    conseguia gerar o mapa, sem mensagem nenhuma."""
    todos = ufs[uf]
    if not (termo or "").strip():
        return todos, len(todos)
    alvo = _sem_acentos(termo.strip())
    achados = [c for c in todos if alvo in _sem_acentos(_nome_mun(c))]
    # começa pelo que começa com o termo, que é o que a pessoa está procurando
    achados.sort(key=lambda c: (not _sem_acentos(_nome_mun(c)).startswith(alvo),
                                _nome_mun(c)))
    return achados, len(achados)


def _logotipo():
    return os.path.join(RAIZ, "mapas", "iastro-logo.png")


def _tinta_do_desenho(arr):
    """Separa a tinta do fundo do canvas (rgb 10,15,30) e grava um PNG
    transparente — é esse PNG limpo que vira o selo na obra.
    Devolve (caminho, dataURL) ou (None, None) se não houver nada escrito."""
    import base64
    import io as _io

    import numpy as np
    from PIL import Image
    if arr is None:
        return None, None
    try:
        ar = np.asarray(arr)
    except Exception:
        return None, None
    if ar.ndim < 3 or ar.shape[2] < 3 or not ar.size:
        return None, None
    dist = (np.abs(ar[..., 0].astype(int) - 10)
            + np.abs(ar[..., 1].astype(int) - 15)
            + np.abs(ar[..., 2].astype(int) - 30))
    if not (dist > 90).any():
        return None, None
    alfa = np.clip(dist, 0, 255).astype(np.uint8)
    out = np.dstack([ar[..., 0], ar[..., 1], ar[..., 2], alfa]).astype(np.uint8)
    _fd, caminho = tempfile.mkstemp(suffix=".png", prefix="traco-")
    os.close(_fd)
    img = Image.fromarray(out, "RGBA")
    img.save(caminho)
    buf = _io.BytesIO()
    img.save(buf, format="PNG")
    b64 = "data:image/png;base64," + base64.b64encode(
        buf.getvalue()).decode("ascii")
    return caminho, b64


ESTILOS_TINTA = ["Tinta", "Lápis", "Carvão", "Caligráfico", "Estrelas",
                 "Constelação"]


def _pincel():
    """Lousa de desenho simples — seu selo na obra (opcional)."""
    with st.expander("🖌️ Desenho livre — seu selo na obra (opcional)", expanded=True):
        st.caption("Desenhe seu selo: símbolo, assinatura, traço livre.")
        
        uploaded = st.file_uploader("Ou envie imagem", type=["png", "jpg", "jpeg", "webp"], key="pincel_upload")

    if uploaded is not None:
        _fd, caminho = tempfile.mkstemp(suffix=".png", prefix="traco-")
        os.close(_fd)
        with open(caminho, "wb") as _f:
            _f.write(uploaded.getvalue())
        return caminho, "upload"

    try:
        from streamlit_drawable_canvas import st_canvas
    except Exception:
        st.caption("Pincel indisponível — o mapa sai sem selo.")
        return None, None

    # Canvas centralizado, sem controles extras
    c_canvas = st_canvas(
        height=220, width=600, background_color="#0a0f1e",
        stroke_width=8, stroke_color="#ffe4a3",
        fill_color="#ffe4a3",
        drawing_mode="freedraw",
        key="pincel_canvas",
        display_toolbar=True,
    )
    
    if c_canvas is None:
        return None, None
    arr = None
    if hasattr(c_canvas, "image_data"):
        arr = getattr(c_canvas, "image_data", None)
    elif isinstance(c_canvas, dict):
        from PIL import Image
        import base64
        import io as _io
        d = c_canvas.get("data")
        if isinstance(d, str) and d.startswith("data:image"):
            try:
                arr = np.asarray(Image.open(_io.BytesIO(
                    base64.b64decode(d.split(";base64,", 1)[1]))).convert("RGBA"))
            except Exception:
                arr = None
    
    caminho, _b64 = _tinta_do_desenho(arr)
    return caminho, "freedraw"


# ── Cabeçalho com logo embutida ─────────────────────────────────────────
st.markdown(
    f'<div style="display:flex;align-items:center;gap:1.1rem;margin:0 0 .4rem 0">'
    f'<div class="logo-seal"><img src="data:image/png;base64,{LOGO_B64}" alt="iastro"/></div>'
    f'<div><div style="font-family:Georgia,\'Times New Roman\',serif;'
    f'font-size:3.1rem;line-height:1;color:#f7faff">iastro</div>'
    f'<div style="font-size:.86rem;letter-spacing:.20em;text-transform:'
    f'uppercase;color:var(--doura);margin-top:.35rem">'
    f'mapa do seu céu</div></div></div>', unsafe_allow_html=True)

st.caption("Um mapa do céu do seu nascimento, lido por muitas culturas. "
           "Gratuito, sem cadastro e sem guardar seus dados.")

try:
    colagem, lb = _motor()
except Exception as e:  # pragma: no cover
    st.error(f"Não consegui carregar o motor: {e}")
    st.stop()

ufs = _ufs(lb)

# ── Busca de cidade FORA do formulário (para filtrar em tempo real) ────────
st.markdown("### 📍 Onde")
# Default para MG (Minas Gerais) - mais populoso
estados_lista = list(ufs.keys())
idx_mg = estados_lista.index("MG") if "MG" in estados_lista else 0

c_uf, _ = st.columns([1, 2])
uf = c_uf.selectbox(" ", estados_lista, index=idx_mg, key="uf_busca",
                    help="Estado onde nasceu ou ocorreu o evento",
                    label_visibility="collapsed")

# Busca de município com filtro em tempo real
termo = st.text_input(" ", 
                      placeholder="Cidade / Município — digite para buscar (ex: belo horizonte, itapemirim...)", 
                      key="termo_busca",
                      help="Digite parte do nome — a lista filtra automaticamente. Ignora acentos.",
                      label_visibility="collapsed")
achados, quantos = _procurar(ufs, uf, termo or "")
if quantos == 0:
    st.warning("Nenhum município encontrado neste estado. Tente outro estado ou digite sem acento.")
    cidade_selecionada = None
else:
    mostrados = achados[:100]
    if quantos > len(mostrados):
        st.caption(f"Mostrando {len(mostrados)} de {quantos} — digite mais para refinar.")
    # Sempre começa vazio (índice 0 = primeira cidade da lista filtrada)
    mun = st.selectbox(" ", mostrados,
                       format_func=lambda k: f"{_nome_mun(k)} — {k.split('|')[1] if '|' in k else uf}",
                       key="mun_busca",
                       index=0,
                       label_visibility="collapsed")
    cidade_selecionada = st.session_state.mun_busca
    st.success(f"✓ Cidade: **{_nome_mun(cidade_selecionada)}** ({uf})")

# ── Formulário principal ──────────────────────────────────────────────────
with st.form("entrada"):
    st.markdown("### 📋 Tipo de mapa")
    tipo = st.radio("O que deseja gerar?", 
                    ["🌱 Carta Natal (nascimento)", "🌍 Mapa de Evento (astrologia mundana)"],
                    horizontal=True,
                    help="Carta Natal: seu mapa de nascimento pessoal. Mapa de Evento: para datas especiais, inaugurações, casamentos, perguntas (horária), etc.")
    tipo_valor = "nascimento" if "Natal" in tipo else "evento"

    st.markdown("### 📅 Quando")
    c1, c2, c3 = st.columns(3)
    dia_opcoes = [""] + [str(d) for d in range(1, 32)]
    dia = c1.selectbox(" ", dia_opcoes, format_func=lambda x: x if x else "Dia", index=0, label_visibility="collapsed")
    mes_opcoes = [""] + MESES
    mes = c2.selectbox(" ", mes_opcoes, format_func=lambda x: x if x else "Mês", index=0, label_visibility="collapsed")
    ano_opcoes = [""] + [str(a) for a in range(1920, 2031)]
    ano = c3.selectbox(" ", ano_opcoes, format_func=lambda x: x if x else "Ano", index=0, label_visibility="collapsed")
    h1, h2 = st.columns(2)
    hh_opcoes = [""] + [f"{h:02d}" for h in range(0, 24)]
    hh = h1.selectbox(" ", hh_opcoes, format_func=lambda x: f"{x}h" if x else "Hora", index=0, label_visibility="collapsed")
    mm_opcoes = [""] + [f"{m:02d}" for m in range(0, 60, 5)]
    mm = h2.selectbox(" ", mm_opcoes, format_func=lambda x: f"{x}m" if x else "Min", index=0, label_visibility="collapsed")

    st.markdown("### 🎨 Personalização do mapa")
    c4, c5 = st.columns(2)
    cultura = c4.selectbox(" ", list(CULTURAS.values()),
                           format_func=lambda v: _rotulo_cultura(v),
                           help="Como o céu será lido: cada cultura tem seus próprios arquétipos e nomes para os signos.",
                           label_visibility="collapsed")
    feeling_opcoes = [""] + SENTIDOS
    feeling = c5.selectbox(" ", feeling_opcoes, format_func=lambda x: x if x else "Sentimento",
                           help="O sentimento guia o poema que acompanha o mapa.",
                           label_visibility="collapsed")

    apelido = st.text_input(" ", 
                            placeholder="Como quer ser chamado no planetário (opcional)",
                            help="Apelido ou nome que aparece na dedicatória do mapa. Vazio = sem nome.",
                            label_visibility="collapsed")

    st.markdown("#### 📝 Palavras que vão no mapa")
    
    tema = st.text_input(
        " ",
        placeholder="Tema da obra (ex: maré de estrelas, novo ciclo, colheita...)",
        help="Uma palavra ou frase curta que inspire a imagem e o verso.",
        label_visibility="collapsed"
    )

    mensaje = st.text_input(
        " ",
        placeholder="Frase secreta (opcional) — algo seu, do coração, que fica escondido na obra",
        max_chars=90,
        help="Uma frase íntima — não aparece visualmente, fica nos metadados. Só você sabe.",
        label_visibility="collapsed"
    )

    st.markdown("### 🖌️ Desenho livre — seu selo na obra (opcional)")
    st.caption("Desenhe algo que vire a marca da obra: um símbolo, sua assinatura, um traço livre. O pincel tem estilos: Tinta, Lápis, Carvão, Caligráfico, Estrelas, Constelação.")
    traco_path, traco_estilo = _pincel()

    st.markdown("---")
    enviado = st.form_submit_button("🌌 Gerar o meu mapa", type="primary", use_container_width=True)

if enviado:
    local = cidade_selecionada
    if local is None:
        st.error("Escolha o município antes de gerar o mapa.")
        st.stop()
    # Valida campos obrigatórios
    faltando = []
    if not dia: faltando.append("Dia")
    if not mes: faltando.append("Mês")
    if not ano: faltando.append("Ano")
    if not hh: faltando.append("Hora")
    if not mm: faltando.append("Minuto")
    if not feeling: faltando.append("Sentimento")
    if faltando:
        st.error("Preencha: " + ", ".join(faltando))
        st.stop()
    if not apelido and not st.session_state.get("LGPD_avisou"):
        st.info("O apelido é opcional: sem ele o mapa sai sem a dedicatória.")
        st.session_state["LGPD_avisou"] = True
    mes_idx = MESES.index(mes) + 1 if mes else 1
    form = {"data": f"{ano}-{mes_idx:02d}-{int(dia):02d}",
            "hora": f"{int(hh):02d}:{int(mm):02d}", "local": local,
            "nome": apelido or "",
            "tipo": tipo_valor,
            "cultura": None if cultura == "todas" else cultura,
            "tema": tema or "maré de estrelas",
            "feeling": feeling or "esperanca",
            "mensaje": (mensaje or "").strip(),
            "figura": "gravura",
            "traco": traco_path, "traco_estilo": traco_estilo,
            "modo": "completo", "salvar_pesquisa": False}
    t0 = time.time()
    with st.spinner("Desenhando o seu planetário…"):
        # `gerar_obra` chama os.path.abspath(saida) e registra o caminho no
        # banco de privacidade — um BytesIO quebraria os dois. Vai para disco.
        fd, caminho = tempfile.mkstemp(suffix=".png", prefix="iastro-")
        os.close(fd)
        try:
            colagem.gerar_obra(form, caminho)
            with open(caminho, "rb") as f:
                dados = f.read()
        except Exception as e:
            st.error(f"Falhou ao desenhar: {e}")
            st.stop()
        finally:
            if os.path.exists(caminho):
                os.unlink(caminho)
    st.success(f"Pronto em {time.time() - t0:.0f} s.")
    st.image(dados, caption=None, use_container_width=True)
    st.download_button("Baixar o meu mapa", data=dados,
                       file_name=f"iastro-{form['data']}.png",
                       mime="image/png", type="primary")
    st.caption("Mapa gerado com iastro — software livre (AGPL-3.0). "
               "Cada mapa é único e não guarda seus dados.")


# --- rodapé: copyright, código e site do projeto --------------
st.markdown("---")
st.markdown(
    "Iastro \u00a9 Iastro. Software livre sob **AGPL-3.0** \u2014 "
    "voc\u00ea pode rodar, estudar, mudar e redistribuir. "
    "[Código fonte](%s) \u00b7 "
    "[Planetário Astrológico Reciclável](https://sites.google.com/view/mapadaspancs/planet%C3%A1rio-astrol%C3%B3gico)" % LINK_CODIGO
)
