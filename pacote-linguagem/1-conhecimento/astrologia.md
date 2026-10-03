# Astrologia — Base de Dados de Efemérides

Agora temos um **banco de dados astronômico completo e confiável** para a
astrologia, gerado por mim com a **Swiss Ephemeris** (o mesmo motor que o
astro.com usa), via a biblioteca `pyswisseph`.

## Onde estão os dados

Local: `/mnt/dados/ephemeris/`

- **Efemérides por dia**: `YYYY-MM.json` (1900 até 2100 = 201 anos completos)
- **Dataset de ML**: `dataset_planetas.csv` e `dataset_planetas.parquet`
- **Gerador**: `gerador.py` (regenera as efemérides + aspectos)
- **Conversor p/ ML**: `dataset.py` (monta a tabela de treino)
- **Treino de ML**: `aprendizado.py` (demonstra machine learning na prática)

## O que cada arquivo de dia contém

Para cada data, os 10 corpos (Sol, Lua, Mercúrio, Vênus, Marte, Júpiter,
Saturno, Urano, Netuno, Plutão) com:

- `lon` — longitude eclíptica em graus (0 a 360) → base para TUDO
- `z` — índice do signo (0=Áries ... 11=Peixes)
- `d` — grau dentro do signo
- `r` — se retrógrado (bool)
- `sp` — velocidade (graus/dia)
- `ph` — fase da Lua (emoji)

E a chave `aspects`:

- para cada PAR de planetas em aspecto (ex.: `"Sun-Venus"`), o nome do
  aspecto (`conjuncao`, `sextil`, `quadratura`, `trino`, `oposicao`) e o
  ângulo exato em graus.

## Como calcular "aspectos" (ângulo entre planetas)

Aspectos NÃO vêm prontos de lugar nenhum — são **calculados** a partir das
longitudes. A fórmula é: menor ângulo entre duas longitudes (0–180°).

Ex.: Sol a 281° e Vênus a 279° → diferença de 2° → CONJUNÇÃO (orbe curto).
Ex.: Júpiter a 112° e Saturno a 357° → diferença de 115° → próximo de 120°
     → TRINO.

Aspectos clássicos e suas orbes (tolerâncias):
quantos graus de diferença antes de o aspecto "valer":
- conjunção 0° (orbe 8°)
- sextil 60° (orbe 6°)
- quadratura 90° (orbe 6°)
- trino 120° (orbe 6°)
- oposição 180° (orbe 8°)

## Como usar quando o usuário perguntar astrologia

1. Leia o arquivo do mês/ano da data pedida em `/mnt/dados/ephemeris/`.
2. Para POSIÇÕES: leia `lon`/`z`/`d` de cada planeta e traduza para o signo.
3. Para ASPECTOS do dia: leia a chave `aspects` (já vem calculada).
4. NUNCA invente posições — use sempre os números reais do arquivo.
   Se a data pedida não estiver nos arquivos, diga que não tem os dados
   e ofereça regenerar (rode `gerador.py`).

## Para o aprendizado de máquina

O `aprendizado.py` mostra o fluxo completo de ML na prática (no seu PC, só
com CPU): carregar → separar treino/teste no tempo → treinar
(Regressão Logística, Random Forest) → avaliar → prever.

Lição importante que o experimento ensinou:
- Prever o signo da Lua usando SÓ os outros planetas = ~11% (pior que chutar).
- Usando a PRÓPRIA posição da Lua (sin/cos da longitude) = 99,6%.
- Moral: em ML, **escolher as características certas importa mais do que
  o modelo**. A posição de cada planeta determina seu signo; os outros
  planetas não "mandam" no signo um do outro nessas escalas.
