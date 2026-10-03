#!/usr/bin/env python3
"""Consulta o banco de arquétipos (arquetipos.db).

Exemplos:
  python3 consultar.py
  python3 consultar.py --signo aries
  python3 consultar.py --cultura folclore
  python3 consultar.py --regiao es
  python3 consultar.py --arquetipo curupira
  python3 consultar.py --tema fogo          # busca por tema/símbolo/texto
  python3 consultar.py --planta arruda     # planta <-> orixá
  python3 consultar.py --corpo aries       # melotesia: parte do corpo do signo
  python3 consultar.py --toponimo itaipava # etno-história/toponímia (Puri, ES)

A cultura/região aceitam fragmento (ex.: 'afro' acha 'afro-brasileiro').
"""
import sqlite3
import os
import sys

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "arquetipos.db")


def main():
    args = sys.argv[1:]
    if not os.path.exists(DB):
        print(f"Não achei o banco em {DB}\nRode primeiro: python3 construir_banco.py")
        sys.exit(1)

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # --- sem argumentos: visão geral ---
    if not args:
        cur.execute("SELECT cultura, COUNT(*) FROM arquetipo GROUP BY cultura")
        print("Culturas e nº de arquétipos:")
        for c, n in cur.fetchall():
            print(f"  {c:24s} {n}")
        print("\nCorrespondências (chave -> arquétipos):")
        cur.execute(
            "SELECT chave, GROUP_CONCAT(nome, ', ') FROM correspondencia "
            "GROUP BY chave ORDER BY chave")
        for chave, nomes in cur.fetchall():
            print(f"  {chave:12s} -> {nomes}")
        conn.close()
        return

    def pegar(flag):
        for i, a in enumerate(args):
            if a == flag and i + 1 < len(args):
                return args[i + 1]
        return None

    signo = pegar("--signo")
    cultura = pegar("--cultura")
    regiao = pegar("--regiao")
    arq = pegar("--arquetipo")
    tema = pegar("--tema")
    planta = pegar("--planta")
    corpo = pegar("--corpo")
    toponimo = pegar("--toponimo")
    partido = pegar("--partido")
    telescopio = pegar("--telescopio")

    def mostra_arq(linha):
        (id_a, nome, cul, elem, pol, modo, tema_t, simbolo,
         reg, region, hist, fonte, nota, corr) = linha
        print(f"\n▪ {nome}  ({id_a})  [cultura: {cul}]")
        if elem or pol or modo:
            print(f"   elemento: {elem}  polaridade: {pol}  modo: {modo}")
        if simbolo:
            print(f"   símbolo: {simbolo}")
        if tema_t:
            print(f"   temas: {tema_t}")
        if reg:
            print(f"   região: {reg}")
        if region:
            print(f"   regionalismo: {region}")
        if hist:
            print(f"   história: {hist}")
        if fonte:
            print(f"   fonte: {fonte}")
        if corr:
            print(f"   corresponde a (zodíaco): {corr}")
        if nota:
            print(f"   nota: {nota}")

    # --- por planta ---
    if planta:
        cur.execute(
            "SELECT * FROM planta WHERE lower(nome) LIKE ? "
            "OR lower(nome_cientifico) LIKE ? ORDER BY id",
            (f"%{planta.lower()}%", f"%{planta.lower()}%"))
        linhas = cur.fetchall()
        print(f"Planta(s) que contém '{planta}' ({len(linhas)}):")
        for p in linhas:
            (pid, nome, cient, elem, orix, orix_n, uso,
             uso_m, efeito, trad, folcl, fonte, link, obs) = p
            print(f"\n▪ {nome}  ({pid})")
            if cient:
                print(f"   científico: {cient}")
            if trad:
                print(f"   tradição: {trad}")
            if elem:
                print(f"   elemento: {elem}")
            if orix:
                print(f"   orixá(s): {orix}")
            if orix_n:
                print(f"   nota do orixá: {orix_n}")
            if uso:
                print(f"   uso ritual: {uso}")
            if uso_m:
                print(f"   uso medicinal: {uso_m}")
            if efeito:
                print(f"   efeito (gùn/èrò): {efeito}")
            if folcl:
                print(f"   folclore: {folcl}")
            if fonte:
                print(f"   fonte: {fonte}")
            if link:
                print(f"   link: {link}")
            if obs:
                print(f"   observação: {obs}")
        conn.close()
        return

    # --- por corpo (melotesia) ---
    if corpo:
        cur.execute(
            "SELECT * FROM corpo WHERE lower(signo) LIKE ?",
            (f"%{corpo.lower()}%",))
        linhas = cur.fetchall()
        print(f"Parte(s) do corpo para '{corpo}' ({len(linhas)}):")
        for c in linhas:
            (sig, parte, det, fonte) = c
            print(f"\n▪ {sig}: {parte}")
            if det:
                print(f"   detalhe: {det}")
            print(f"   fonte: {fonte}")
        conn.close()
        return

    # --- por topônimo / etno-história ---
    if toponimo:
        cur.execute(
            "SELECT * FROM toponimo WHERE lower(nome) LIKE ? "
            "OR lower(regiao) LIKE ? OR lower(id) LIKE ? ORDER BY id",
            (f"%{toponimo.lower()}%", f"%{toponimo.lower()}%",
             f"%{toponimo.lower()}%"))
        linhas = cur.fetchall()
        print(f"Topônimo(s)/etno-história que contém '{toponimo}' ({len(linhas)}):")
        for t in linhas:
            (tid, nome, tipo, terr, lng, hist, reg, fonte, link, corr, nota) = t
            print(f"\n▪ {nome}  ({tid})  [tipo: {tipo}]")
            if terr:
                print(f"   território: {terr}")
            if lng:
                print(f"   língua/classificação: {lng}")
            if hist:
                print(f"   história: {hist}")
            if reg:
                print(f"   região: {reg}")
            if fonte:
                print(f"   fonte: {fonte}")
            if link:
                print(f"   link: {link}")
            if nota:
                print(f"   nota: {nota}")
        conn.close()
        return

    # --- por partido (panorama mundano/político) ---
    if partido:
        cur.execute(
            "SELECT * FROM partido WHERE lower(sigla) LIKE ? OR lower(nome) LIKE ? "
            "OR lower(signo_chave) LIKE ? OR lower(corresponde_a) LIKE ? ORDER BY sigla",
            (f"%{partido.lower()}%", f"%{partido.lower()}%",
             f"%{partido.lower()}%", f"%{partido.lower()}%"))
        linhas = cur.fetchall()
        print(f"Partido(s)/signo que contém '{partido}' ({len(linhas)}):")
        for p in linhas:
            (pid, sigla, nome, terr, signo_ch, planeta, elem, just, cert, fonte, corr) = p
            print(f"\n▪ {sigla} — {nome}  ({pid})")
            print(f"   território: {terr}")
            print(f"   signo/planeta-chave: {signo_ch} / {planeta}  [elemento: {elem}]")
            print(f"   justificativa: {just}")
            print(f"   certeza: {cert}")
            print(f"   fonte: {fonte}")
            print(f"   corresponde_a: {corr}")
        conn.close()
        return

    # --- por telescópio/imagem (história cosmológica) ---
    if telescopio:
        cur.execute(
            "SELECT * FROM telescopio WHERE lower(corpo) LIKE ? "
            "OR lower(telescopio) LIKE ? OR lower(marco) LIKE ? ORDER BY corpo",
            (f"%{telescopio.lower()}%", f"%{telescopio.lower()}%",
             f"%{telescopio.lower()}%"))
        linhas = cur.fetchall()
        print(f"Telescópio/imagem que contém '{telescopio}' ({len(linhas)}):")
        for t in linhas:
            (corpo, arq, tel, ano, marco) = t
            print(f"\n▪ {corpo}")
            print(f"   telescópio: {tel}  ({ano})")
            print(f"   marco: {marco}")
            print(f"   arquivo: {arq}")
        conn.close()
        return

    # --- por signo: correspondências de todas as culturas ---
    if signo:
        signo = signo.lower()
        cur.execute(
            "SELECT ar.* FROM correspondencia c "
            "JOIN arquetipo ar ON ar.id = c.id_arquetipo "
            "WHERE lower(c.chave)=? ORDER BY c.cultura",
            (signo,))
        linhas = cur.fetchall()
        print(f"Arquétipos correspondentes a '{signo}':")
        if not linhas:
            print("  (nenhum vínculo ainda)")
        for l in linhas:
            mostra_arq(l)
        conn.close()
        return

    # --- por cultura ---
    if cultura:
        cur.execute(
            "SELECT * FROM arquetipo WHERE cultura LIKE ? ORDER BY id",
            (f"%{cultura}%",))
        linhas = cur.fetchall()
        print(f"Arquétipos da cultura que contém '{cultura}' ({len(linhas)}):")
        for l in linhas:
            mostra_arq(l)
        conn.close()
        return

    # --- por região ---
    if regiao:
        cur.execute(
            "SELECT * FROM arquetipo WHERE regiao LIKE ? "
            "OR regionalismo LIKE ? ORDER BY id",
            (f"%{regiao}%", f"%{regiao}%"))
        linhas = cur.fetchall()
        print(f"Arquétipos associados à região '{regiao}' ({len(linhas)}):")
        for l in linhas:
            mostra_arq(l)
        conn.close()
        return

    # --- por nome do arquétipo ---
    if arq:
        cur.execute(
            "SELECT * FROM arquetipo WHERE lower(nome) LIKE ? "
            "OR lower(id) LIKE ? ORDER BY id",
            (f"%{arq.lower()}%", f"%{arq.lower()}%"))
        linhas = cur.fetchall()
        print(f"Arquétipo(s) que contém '{arq}':")
        for l in linhas:
            mostra_arq(l)
        conn.close()
        return

    # --- por tema/símbolo/nota ---
    if tema:
        cur.execute(
            "SELECT * FROM arquetipo WHERE tema LIKE ? OR simbolo LIKE ? "
            "OR nota LIKE ? ORDER BY id",
            (f"%{tema}%", f"%{tema}%", f"%{tema}%"))
        linhas = cur.fetchall()
        print(f"Arquétipos com '{tema}' em tema/símbolo/nota ({len(linhas)}):")
        for l in linhas:
            mostra_arq(l)
        conn.close()
        return

    print(__doc__)
    conn.close()


if __name__ == "__main__":
    main()
