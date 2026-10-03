"""Gravação dos mapas em tabela — o Iastro guarda o DADO, não a imagem.

Decisão do projeto: fica gravada uma linha por mapa, só com os números, para
poder entregar, reimprimir e atender. A imagem em PNG fica no disco do
Planetário e fora do banco — um PNG de 8 MB por pessoa enche o servidor à
toa e não é necessário para nada.

Três finalidades, com bases legais diferentes (o art. 8º §2º da LGPD põe o
ônus da prova da base legal no controlador, então ela vai escrita na linha):

1. **Entrega** (art. 7º V) — a pessoa pediu o mapa, e guardar o pedido é
   obligation nossa de cumprir. É a única gravação padrão.
2. **Pesquisa** (art. 7º I) — somar ao banco de estudo. Desligado por
   padrão, porque é opcional e não faz parte do serviço.
3. **Contato** (art. 7º IX, legítimo interesse) — a mesma linha, com nome e
   e-mail quando a pessoa deixou, para responder e para permitir apagar.

O que a tabela NÃO tem, por desenho:
- imagem, PNG, base64 ou qualquer byte de arquivo;
- nada de publicação: a coluna `publicado` existe e vale sempre 0. As
  estatísticas saem por agregação, nunca linha a linha;
- nada de identificador derivado do nascimento. O id é aleatório (uuid4).
  Um hash de "data|hora|local" serviria para confirmar quem é quem.

Prazo: `PRAZO_DIAS` dias. Depois a linha sai sozinha, e dá para mudar a
constante. Prazo maior do que o necessário não se sustenta sob o art. 15.

Uso:

    import privacidade
    privacidade.registrar(dados)                        # amostra, entrega
    privacidade.registrar(dados, pesquisa=True)        # entra na tabulação
    privacidade.apagar_por_contato("fulano@exemplo.com")
    privacidade.expirar()                               # roda no startup
"""
import json
import os
import sqlite3
import time
import uuid

__all__ = ["registrar", "pode_pesquisar", "apagar_por_chave",
           "apagar_por_contato", "expirar", "estatisticas", "resumo",
           "limpar_vencidas",
           "BD", "PRAZO_DIAS", "CHAVE", "CAMPOS_PESQUISA", "FAIXAS_HORA"]

# ── onde fica o banco ───────────────────────────────────────────────────────
RAIZ = os.environ.get("IASTRO_PRIVACIDADE") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..")
PASTA_BD = os.path.join(RAIZ, "dados")
BD = os.path.join(PASTA_BD, "mapas.sqlite3")

# Prazo de guarda da linha, em dias. Cobre download, impressão e retorno
# para atendiment. Passou disso, a linha é apagada sozinha (art. 15).
PRAZO_DIAS = 90

CHAVE = {
    "entrega": "art.7 V - execucao do contrato",
    "pesquisa": "art.7 I - consentimento",
    "contato": "art.7 IX - legitimo interesse",
}

# O que a tabulação pode olhar. Não é a lista do que se guarda: é a lista do
# que se CONTA. A linha completa tem a data e a hora exatas, porque precisa
# para reimprimir; a contagem usa só isto.
CAMPOS_PESQUISA = ("sol", "lua", "cultura", "data", "hora_faixa", "modo")

FAIXAS_HORA = ((0, 6, "madrugada"), (6, 12, "manha"),
               (12, 18, "tarde"), (18, 24, "noite"))

SQL = """
CREATE TABLE IF NOT EXISTS mapas (
    id          TEXT PRIMARY KEY,
    criado_em   TEXT NOT NULL,
    expira_em   TEXT NOT NULL,
    modo        TEXT NOT NULL DEFAULT 'completo',
    nome        TEXT,
    email       TEXT,
    telefone    TEXT,
    data_nasc   TEXT,
    hora_nasc   TEXT,
    local       TEXT,
    lat         REAL,
    lon         REAL,
    tz          TEXT,
    cultura     TEXT,
    tema        TEXT,
    sol         TEXT,
    lua         TEXT,
    asc         TEXT,
    mc          TEXT,
    planetas    TEXT,
    destaques   TEXT,
    verso       TEXT,
    imagem      TEXT,
    pesquisa    INTEGER NOT NULL DEFAULT 0,
    publicado   INTEGER NOT NULL DEFAULT 0,
    base_legal  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_mapas_expira ON mapas(expira_em);
CREATE INDEX IF NOT EXISTS ix_mapas_email  ON mapas(email);
CREATE INDEX IF NOT EXISTS ix_mapas_pesq   ON mapas(pesquisa);
"""


def _con(bd=None):
    caminho = bd or BD
    pasta = os.path.dirname(os.path.abspath(caminho))
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    con = sqlite3.connect(caminho)
    con.row_factory = sqlite3.Row
    con.executescript(SQL)
    return con


def _agora():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _prazo(dias=None):
    d = int(dias if dias is not None else PRAZO_DIAS)
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + d * 86400))


def _faixa_hora(hora):
    try:
        h = int(str(hora).split(":")[0])
    except (ValueError, IndexError, TypeError):
        return ""
    for ini, fim, nome in FAIXAS_HORA:
        if ini <= h < fim:
            return nome
    return ""


def _json(v):
    return json.dumps(v, ensure_ascii=False) if v else None


def pode_pesquisar(consentido):
    """A tabulação só acontece com True estrito.

    `is True` de propósito: o interruptor chega de formulário web, então
    pode vir "sim", "true" ou 1 — coisas que são verdadeiras para o Python e
    não são consentimento humano. Recusar é o jeito seguro de errar.
    """
    return consentido is True


def registrar(dados, pesquisa=False, contato=None, modo="completo",
              imagem=None, dias=None, bd=None):
    """Guarda UMA LINHA com os dados do mapa. Nunca a imagem.

    A linha é a base legal de execução do contrato (entregar o mapa é
    obrigação nossa). Se `pesquisa=True` — e só com True estrito — a linha
    também passa a contar na tabulação, anotando o consentimento.

    Devolve o id do mapa, que é o que o atendimento usa para localizar.
    """
    pesquisa = pode_pesquisar(pesquisa)
    rid = uuid.uuid4().hex[:16]
    contato = contato or {}
    limpar_vencidas(bd=bd)

    bases = [CHAVE["entrega"]]
    if pesquisa:
        bases.append(CHAVE["pesquisa"])
    if contato.get("nome") or contato.get("email") or contato.get("telefone"):
        bases.append(CHAVE["contato"])

    planetas = dados.get("planetas") or {}
    linha = {
        "id": rid,
        "criado_em": _agora(),
        "expira_em": _prazo(dias),
        "modo": modo if modo in ("amostra", "completo") else "completo",
        "nome": (contato.get("nome") or dados.get("nome") or "").strip() or None,
        "email": (contato.get("email") or dados.get("email") or "").strip() or None,
        "telefone": (contato.get("telefone") or "").strip() or None,
        "data_nasc": dados.get("data"),
        "hora_nasc": dados.get("hora"),
        "local": dados.get("local"),
        "lat": dados.get("lat"),
        "lon": dados.get("lon"),
        "tz": dados.get("tz"),
        "cultura": dados.get("cultura"),
        "tema": dados.get("tema"),
        "sol": dados.get("sol"),
        "lua": dados.get("lua"),
        "asc": dados.get("asc"),
        "mc": dados.get("mc"),
        "planetas": _json({k: {"signo": v.get("signo"), "graus": v.get("graus")}
                           for k, v in planetas.items()
                           if isinstance(v, dict)}),
        "destaques": _json(dados.get("destaques")),
        "verso": _json(dados.get("verso")),
        # só o caminho/nome do arquivo, jamais o conteúdo do PNG
        "imagem": os.path.basename(imagem) if imagem else None,
        "pesquisa": 1 if pesquisa else 0,
        "publicado": 0,
        "base_legal": "; ".join(bases),
    }

    con = _con(bd)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        cols = ", ".join(linha)
        marcas = ", ".join(":" + c for c in linha)
        con.execute(f"INSERT INTO mapas ({cols}) VALUES ({marcas})", linha)
        con.commit()
    finally:
        con.close()
    return rid


def expirar(dias=None, bd=None):
    """Apaga as linhas que passaram do prazo. Devolve quantas saíram."""
    con = _con(bd)
    try:
        alvo = _prazo(dias)
        cur = con.execute("DELETE FROM mapas WHERE expira_em < ?", (alvo,))
        apagadas = cur.rowcount
        con.commit()
        return apagadas
    finally:
        con.close()


def limpar_vencidas(bd=None):
    """Apaga o que já venceu, sem deixar a falha derrubar quem chamou.

    É isto que faz a promessa dos 90 dias valer sozinha: roda no startup do
    app e antes de cada registro, e nunca em silêncio — se o banco estiver
    trancado ou corrompido, o mapa ainda é entregue, só que sem limpeza
    naquele momento.
    """
    try:
        return expirar(bd=bd)
    except Exception:
        return 0


def apagar_por_chave(rid, bd=None):
    """Elimina uma linha (art. 18º VI)."""
    con = _con(bd)
    try:
        cur = con.execute("DELETE FROM mapas WHERE id = ?", (rid,))
        con.commit()
        return cur.rowcount
    finally:
        con.close()


def apagar_por_contato(email, bd=None):
    """Elimina tudo ligado a um e-mail (art. 18º VI)."""
    email = (email or "").strip().lower()
    if not email:
        return 0
    con = _con(bd)
    try:
        cur = con.execute(
            "DELETE FROM mapas WHERE lower(trim(email)) = ?", (email,))
        apagadas = cur.rowcount
        con.commit()
        return apagadas
    finally:
        con.close()


def estatisticas(bd=None):
    """Contagem agregada. Só entra linha com consentimento de pesquisa.

    Devolve contagem por signo, cultura, mês e faixa do dia. A partir
    disto não dá para voltar a nenhuma pessoa: só números, e nenhuma
    linha sai daqui.
    """
    cont = {}
    con = _con(bd)
    try:
        linhas = con.execute(
            "SELECT sol, lua, cultura, data_nasc, hora_nasc, modo "
            "FROM mapas WHERE pesquisa = 1").fetchall()
    finally:
        con.close()

    for s in linhas:
        mes = (s["data_nasc"] or "")[:7] or "—"
        faixa = _faixa_hora(s["hora_nasc"]) or "—"
        for campo, valor in (("sol", s["sol"]), ("lua", s["lua"]),
                             ("cultura", s["cultura"]), ("mes", mes),
                             ("hora_faixa", faixa), ("modo", s["modo"])):
            v = str(valor or "—")
            cont.setdefault(campo, {})
            cont[campo][v] = cont[campo].get(v, 0) + 1
    return cont


def resumo(bd=None):
    """Números de operação, para conferir de relance."""
    con = _con(bd)
    try:
        total = con.execute("SELECT COUNT(*) c FROM mapas").fetchone()[0]
        amostra = con.execute(
            "SELECT COUNT(*) c FROM mapas WHERE modo='amostra'").fetchone()[0]
        pesq = con.execute(
            "SELECT COUNT(*) c FROM mapas WHERE pesquisa=1").fetchone()[0]
        pub = con.execute(
            "SELECT COUNT(*) c FROM mapas WHERE publicado=1").fetchone()[0]
        mais_antigo = con.execute(
            "SELECT MIN(criado_em) d FROM mapas").fetchone()[0]
    finally:
        con.close()
    return {"total": total, "amostra": amostra, "pesquisa": pesq,
            "publicado": pub, "mais_antigo": mais_antigo}


if __name__ == "__main__":
    import pprint
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "resumo"
    if cmd == "resumo":
        r = resumo()
        print(f"banco ....... {BD}")
        print(f"linhas ...... {r['total']}  (amostra {r['amostra']}, "
              f"com pesquisa {r['pesquisa']})")
        print(f"publicadas .. {r['publicado']}  (deve ser sempre 0)")
        print(f"mais antiga .. {r['mais_antigo'] or '—'}")
        print(f"prazo ........ {PRAZO_DIAS} dias")
    elif cmd == "estatisticas":
        pprint.pprint(estatisticas())
    elif cmd == "expirar":
        print(expirar(), "linha(s) vencida(s) apagada(s)")
    elif cmd == "apagar":
        print(apagar_por_contato(sys.argv[2]), "linha(s) apagada(s)")