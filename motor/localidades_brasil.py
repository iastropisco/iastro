#!/usr/bin/env python3
"""Catálogo local completo de municípios brasileiros (IBGE).

Fonte: API/geometria do IBGE (via kelvins/Municipios-Brasileiros),
salvo em `localidades_brasil.json` para uso 100% offline.

Estruturas:
  UFS        { "ES": {"nome": "Espírito Santo", "codigo": 32}, ... }
  MUNICIPIOS { "cidade|uf": {"nome", "uf", "codigo", "lat", "lon", "fuso"},
               ... }
              A chave é o nome sem acentos em minúsculas + "|" + sigla da UF
              (ex.: "guarapari|es"), única mesmo quando duas cidades no país
              têm o mesmo nome.
  POR_UF     { "ES": ["cidade|es", ...], ... }  (chaves ordenadas por nome)

Fusos: o universo atual (2019 em diante) está em 4 zonas:
  UTC-2 Fernando de Noronha, UTC-3 (a maior parte), UTC-4 (AM amazônico,
  MT, MS, RO, RR e oeste do PA) e UTC-5 (Acre). Para não depender de
  timezoneinfo, usamos a regra por estado em `offset_utc(uf)`.
"""
import json
import os
import unicodedata

_ARQ = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "localidades_brasil.json")

_CARGA = None


def _carregar():
    global _CARGA
    if _CARGA is None:
        with open(_ARQ, encoding="utf-8") as _f:
            _CARGA = json.load(_f)
    return _CARGA


def sem_acentos(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


UFS = _carregar()["ufs"]
MUNICIPIOS = _carregar()["municipios"]
POR_UF = _carregar()["por_uf"]

# UFs cujo fuso atual é UTC-5 / UTC-4 (regra por unidade da federação,
# desde a unificação de 2019; o Pará voltou todo a UTC-3).
_UF_UTC5 = {"ac"}
_UF_UTC4 = {"am", "mt", "ms", "ro", "rr"}


def offset_utc(uf=None, fuso=None):
    """Desvio UTC (horas) atual para uma UF/município.

    Usa a regra por estado (lei atual) e ignora o `fuso` antigo do arquivo,
    que reflete o mapa pré-2019.
    """
    u = (uf or "").lower()
    if u in _UF_UTC5:
        return -5
    if u in _UF_UTC4:
        return -4
    return -3


def chave(s):
    """Chave canônica (nome|uf) a partir de um nome ou chave qualquer."""
    s = sem_acentos(s).strip().lower()
    if "|" in s:
        nome, uf = s.rsplit("|", 1)
        return f"{nome}|{uf.strip()[:2]}" if uf else None
    return s


def buscar(nome, uf=None):
    """Resolve descrição livre -> chave de um município.

    Se `uf` for dado, restringe a esse estado. Retorna a chave canônica
    (ex.: "guarapari|es") ou None se não achar.
    """
    alvo = sem_acentos(nome).strip().lower()
    if not alvo:
        return None
    if "|" in alvo:
        return alvo if alvo in MUNICIPIOS else None
    ufs = [uf.upper()] if uf else list(POR_UF)
    for u in ufs:
        for ch in POR_UF.get(u, []):
            base = ch.rsplit("|", 1)[0]
            if base == alvo:
                return ch
    return None


def origem(chave_):
    """Ficha do município (dict) a partir da chave canônica."""
    return MUNICIPIOS.get(chave_)


def lista_uf():
    """Siglas das UFs em ordem alfabética pelo nome."""
    return sorted(UFS, key=lambda u: UFS[u]["nome"])


def lista_cidades(uf):
    """Chaves dos municípios do estado, ordenadas pelo nome."""
    return list(POR_UF.get((uf or "").upper(), []))


def exibir(chave_):
    """Nome bonito para mostrar no app: 'Guarapari (ES)'."""
    m = MUNICIPIOS.get(chave_)
    if not m:
        return chave_
    return f"{m['nome']} ({m['uf']})"


def coords_e_fuso(chave_):
    """(lat, lon, offset_utc) para a chave de um município."""
    m = MUNICIPIOS.get(chave_)
    if not m:
        return None
    return m["lat"], m["lon"], offset_utc(m["uf"], m.get("fuso"))


if __name__ == "__main__":
    import sys
    alvo = sys.argv[1] if len(sys.argv) > 1 else "guarapari"
    uf = sys.argv[2] if len(sys.argv) > 2 else None
    c = buscar(alvo, uf)
    print("chave:", c)
    if c:
        print("ficha:", MUNICIPIOS[c])
        print("exibir:", exibir(c))
        print("coords/fuso:", coords_e_fuso(c))
    print("municípios cadastrados:", len(MUNICIPIOS), "em",
          len(UFS), "UFs")