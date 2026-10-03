"""Caminhos do projeto — relativos, para o Iastro rodar em qualquer máquina.

Antes os scripts apontavam para `/mnt/dados/ephemeris` e
`/mnt/dados/home-italivre/iastro-ia` com o caminho escrito à mão. Isso
funcionava numa máquina só: trocar de computador, ou clonar o repositório,
quebrava tudo.

Agora a raiz do projeto é deduzida a partir da localização deste arquivo.
Para instalar em outro lugar, ou define IASTRO_HOME, ou edita
`detectar_raiz()`.

Os caminhos que realmente dependem do sistema (fontes do Linux, Stellarium,
efemérides do Swiss Ephemeris) continuam absolutos, mas cada um tem uma
variante de ambiente para quem não os tiver no lugar padrão.
"""
import os
import sys

__all__ = ["RAIZ", "EPHEMERIS", "ARQ", "MAPAS", "DB", "FONTS_PERG",
           "CULTURAS", "IMAGENS_LIVRES", "RECICLAVEIS", "JSONL",
           "LIXO", "EPISTEM", "STEL", "PASTA_LINGUAGEM"]


def _detectar_raiz():
    """Sobe a árvore até achar a pasta que tem o app.py (ou o .gitignore)."""
    env = os.environ.get("IASTRO_HOME")
    if env and os.path.isdir(env):
        return os.path.abspath(env)

    aqui = os.path.dirname(os.path.abspath(__file__))
    alvos = ("app.py", ".gitignore", os.path.join("arquetipos", "arquetipos.db"))

    # o motor pode estar em <raiz>/motor/, ou ser um diretório irmão da raiz
    for base in (aqui, os.path.dirname(aqui)):
        if any(os.path.exists(os.path.join(base, t)) for t in alvos):
            return os.path.abspath(base)

    # instalação real: <algum>/<home>/iastro-ia é a raiz e o motor é irmão.
    # Sobe até achar uma pasta chamada iastro-* com app.py dentro.
    base = aqui
    for _ in range(5):
        base = os.path.dirname(base)
        if not base or base == os.path.sep:
            break
        for nome in os.listdir(base) if os.path.isdir(base) else []:
            if not nome.lower().startswith("iastro"):
                continue
            cand = os.path.join(base, nome)
            if os.path.isdir(cand) and any(
                    os.path.exists(os.path.join(cand, t)) for t in alvos):
                return os.path.realpath(cand)

    # último recurso: o pai do motor
    return os.path.dirname(aqui)


RAIZ = _detectar_raiz()

# ── dentro do projeto (relativos, sempre presentes) ─────────────────────────
MOTOR = os.path.dirname(os.path.abspath(__file__))
EPHEMERIS = MOTOR
ARQ = os.path.join(RAIZ, "arquetipos")
MAPAS = os.path.join(RAIZ, "mapas")
CULTURAS = os.path.join(ARQ, "cultures")
IMAGENS_LIVRES = os.path.join(MAPAS, "images-livres")
RECICLAVEIS = os.path.join(MAPAS, "reciclaveis")
FONTS_PERG = os.path.join(MAPAS, "fonts")
PASTA_LINGUAGEM = os.path.join(RAIZ, "pacote-linguagem")
DB = os.path.join(ARQ, "arquetipos.db")
JSONL = os.path.join(RAIZ, "mapas_solicitados.jsonl")
LIXO = os.path.join(MOTOR, ".cache-medalhoes")
DATASET = os.path.join(MOTOR, "dataset_planetas.csv")

# ── fora do projeto: dependências do sistema ───────────────────────────────
# cada uma aceita variável de ambiente antes do caminho padrão
# Prioridade 1: variável de ambiente
# Prioridade 2: pasta swisseph-ephe dentro do motor (para Streamlit Cloud / Docker)
# Prioridade 3: /usr/share/swisseph (Linux padrão)
# Prioridade 4: pasta antiga /mnt/dados/swisseph-ephe (compatibilidade)
EPISTEM = os.environ.get("IASTRO_EFEM")
if not EPISTEM:
    # Tenta achar swisseph-ephe relativo ao motor (para Cloud)
    cand = os.path.join(MOTOR, "swisseph-ephe")
    if os.path.isdir(cand):
        EPISTEM = cand
    elif os.path.isdir("/usr/share/swisseph"):
        EPISTEM = "/usr/share/swisseph"
    else:
        EPISTEM = "/mnt/dados/swisseph-ephe"

STEL = os.environ.get("IASTRO_STEL", "/usr/share/stellarium/skycultures")
HF = os.environ.get("HF_HOME", os.path.join(os.path.expanduser("~"), ".cache/huggingface"))


def registrar_no_path():
    """Põe o motor no sys.path, para os módulos se importarem entre si."""
    if MOTOR not in sys.path:
        sys.path.insert(0, MOTOR)


def describe():
    """Diagnóstico: mostra os caminhos resolvidos e o que falta no sistema."""
    linhas = [
        "Iastro — caminhos resolvidos",
        f"  RAIZ        {RAIZ}",
        f"  MOTOR       {MOTOR}",
        f"  ARQ         {ARQ}",
        f"  MAPAS       {MAPAS}",
        f"  DB          {DB}",
    ]
    for nome, caminho, obrig in (
            ("efemerides swisseph", EPISTEM, True),
            ("stellarium skycultures", STEL, False),
            ("fontes pergaminho", FONTS_PERG, False),
    ):
        ok = "ok " if os.path.isdir(caminho) else "FALTA"
        linhas.append(f"  [{ok}] {nome}: {caminho}")
    return "\n".join(linhas)


if __name__ == "__main__":
    print(describe())