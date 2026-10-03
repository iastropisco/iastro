# iastro — esquema de trabalho (pipeline único e automatizado)

Este arquivo é o "mapa do como trabalhar". O iastro monta, num único passo,
um **mapa astral de várias culturas** a partir só de data/hora/local de um
nascimento ou evento. A era, as plantas e o céu entram na mesma roda.

## O fluxo de uma pessoa → uma obra

Entrada: `data`, `hora`, `local` (e opcionalmente cultura/Tema/sentimento).

```
                    ┌──────────────────────────────────────────┐
 data/hora/local →  │ 1. MAPA TRADICIONAL (efeméride Swiss)     │
                    │    planeta em signo/graus + Asc            │
                    │ 2. PLANTAS REGENTES  signo→orixá→planta    │
                    │    (nome científico + usos + enciclop. PD) │
                    │ 3. CÉU DA CULTURA   Sol/Asc/Lua→asterismo  │
                    │    (tupi, tukano, sul-capixaba, +nossas)   │
                    │ 4. COLAGEM          arquétipos+céu+imagens │
                    │    → PNG (obra) + HTML (interativo) + JSON │
                    └──────────────────────────────────────────┘
                             artefatos em  mapas/exemplos/
```

Todo o motor chama módulos pequenos e reutilizáveis; nada duplica base de dados.

## Prioridade dos passos (ordem de construção)

1. **Zodíaco ocidental + mapa pelas efemérides** — é a ESPINHA base, e já está
   correta com grau e minuto (ex.: Sol 25°02', Asc 29°21') via Swiss Ephemeris
   (`mapa_astral.calc`). Confiar primeiro nisto; o resto é camada.
2. **Vínculos com as outras culturas** — os arquétipos de cada saber se
   amarram aos pontos do mapa (Sol/Asc/Lua/planetas). Sempre `certeza`+`fonte`,
   hipóteses, nunca doutrina. Onde não há achado honesto, fica em branco.
3. **Arquétipos locais (sul do ES) começam a lista de "regional"** — não é
   algo exclusivo nem excludente; é só o começo de uma relação mais ampla de
   regionalismos.
4. **Acumular informação** — pesquisar e registrar arquétipos com o máximo de
   fontes por cultura, para ir enriquecendo o banco.

### Cada cultura é autônoma

Mapuche é um **povo da América do Sul (Chile/Argentina)** com astronomia
própria (Wenumapu); **não é um regionalismo do ES nem de Itaipava**. Trata-se
no mesmo nível de autonomia que indígena, orixás, folclore etc. Os arquétipos
"capixabas" são uma **camada regional específica**, separada deles.

## Comandos

### Mapa único
```
venv/bin/python /mnt/dados/ephemeris/gerar_mapa.py \
  --data 1990-01-15 --hora 08:00 --local "rio de janeiro" \
  --cultura indigena --tema "maré de estrelas" --feeling esperanca \
  --saida "mapas/exemplos/meu-mapa"
```
Produz `meu-mapa.{png,html,json}` + imprime no console: posições dos planetas,
plantas regentes e céu de cada cultura. Aceita locais acentuados (`piúma`,
`vitória`).

### Lote noturno (para deixar o PC trabalhando de madrugada)
```
venv/bin/python /mnt/dados/ephemeris/gerar_lote.py --saida mapas/exemplos
```
Gera N mapas (lista `LOTE` no topo do script) e um `indice.html` que lista
todos. Manter `LOTE` pequeno: cada HTML interativo carrega as fotos dos
telescópios em base64 e pesa ~2 MB (self-contained, roda offline — necessário
para publicar no Google Sites).

### Extrair um mapa completo do iastro (todas as culturas + arquétipos + plantas)
```
venv/bin/python /mnt/dados/ephemeris/ceu_catalogo.py \
    --data 1990-01-15 --hora 08:00 --local itapemirim --cultura indigena \
    --saida mapas/mapa-iastro.json
```
Centraliza numa única saída: **mapa tradicional** (efeméride, grau/minuto),
**céu de TODAS as culturas** (as 59 do Stellarium + as nossas — em `cultura_ceu`
do banco), **arquétipo mais forte por signo através das culturas** (por
`correspondencia`/`certeza`) e **plantas por saber popular** (signo→orixá→
planta, via `flora`). O `gerar_mapa.py` já chama este catálogo e ainda produz
o PNG + HTML da obra.

### Cadeiras isoladas, quando ajudar a depurar
- Mapa tradicional: `mapa_astral.calc(data, hora, lat, lon)`.
- Plantas: `flora.py --data ... --hora ... --local ...`.
- Céu da cultura (catálogo unificado): `ceu_catalogo.py` / `ceu.py --leitura` / `ceu.py --gerar`.
- Colagem: `colagem.py ... --cultura ... --tema ... --feeling ...`.

## O que é honesto (método)

Toda correspondência multi-cultura é **hipótese do projeto** com `certeza` +
`fonte`, nunca doutrina. Signos sem achado ficam vazios **de propósito**. As
plantas carregam nome científico, uso da medicina popular, **enciclopédia de
domínio público** (Flora Brasiliensis, Martius — PD) e o **saber poético**
(`saber`): banhos, defumações, sacudimentos e orientações da tradição de
terreiro, na voz do material do usuário (fonte citada por erva). O céu da
cultura usa as culturas livres do Stellarium (GPL) complementadas pelas
nossas.

## Publicação (Google Sites)

O HTML final é self-contained: basta publicar em Drive (unidade pública) e
incorporar no Sites via URL. Cada cultura `iastro-*.json` (incluindo a
sul-capixaba) é baixável para o visitante abrir no Stellarium. Ver
`GOOGLE_SITES.md`.

## Sustentar o disco

- Manter o número de exemplos pequeno (o lote sugere 2).
- Os PNG (~500 KB) são a obra visual; o HTML só onde a interatividade vale.
- Bases (`arquetipos.db`) ficam em `arquetipos/`, não duplicadas.

## Interface interativa (formulário autoexplicativo)

O `app.py` (Streamlit, `./iniciar.sh`) tem a página **🪐 Planetário · colagem
multi-cultura**:

- **Topo**: um "como funciona" em expansor explica o pipeline em camadas.
- **Formulário**: data/hora/local + cultura + tema + sentimento + traço à mão
  (desenho *ou* upload).
- **Resultado em 4 abas** (uma entrada → a obra inteira, explicada):
  - **🖼 Sua obra** — PNG da roda + arquétipos do Sol e do Asc + verso.
  - **🌿 Plantas regentes** — TODOS os corpos do mapa (10 planetas + Quíron,
    Lilith, Ceres, Pallas, Juno, Vesta) → signo → orixá → plantas (nome
    científico, usos, enciclopédia de domínio público e saber poético).
  - **🌌 O céu da cultura** — Sol/Asc/Lua lidos por outra tradição (seletor +
    download da cultura para o Stellarium).
  - **🔍 Como ler** — legenda do que cada camada significa; botão de **baixar o
    pacote completo em JSON** (tudo em camadas autoexplicativas, pronto para
    reusar ou publicar).

Ideal para que um visitante entenda a obra sem instruções externas: cada aba
carrega uma legenda do *que está vendo* e *por que*.
## Ajustes visuais do mapa (set/2026)

- **Arquétipos de TODOS os corpos**: a tabela de planetas agora mostra o
  arquétipo de correspondência de cada um dos 16 corpos (não só Sol/Lua/
  regente do Asc). Cartões "ARQUÉTIPOS DE …" para todos: Sol + Ascendente
  (2 grandes), Mercúrio/Vênus/Marte (3 médios) e Lua/Júpiter/Saturno/Urano/
  Netuno/Plutão/Quíron/Lilith (4 por linha, 2 linhas compactas).
- **Quíron legível**: o glifo ⚷ (U+26B7) é pequeno e parecia "??" — agora é
  desenhado em fonte 30 com contorno claro, separado do nome, e o Quíron
  entrou na galeria "OS ASTROS DO TEU MAPA" (com Plutão e os asteroides:
  16 corpos no total, cada um com signo e grau).
- **Coluna de signos sem sobreposição**: a parte do corpo (melotesia) era
  desenhada com anchor "lm" em yy+21, subindo por cima do signo. Agora vai
  em yy+32 com anchor "la" (topo), abaixo do signo; linha da tabela com
  altura 58.
- **Medalhões de signos (domínio público)**: nos cartões de arquétipos sem
  imagem PD, o círculo mostra o medalhão do signo (série CC0 de Wikimedia
  Commons, `arquetipos/medalhoes/`) no lugar da inicial.
- **Plantas regentes com mais conteúdo**: 4 plantas por regência (Sol,
  Mercúrio, Lua), cada uma com nome científico + uso medicinal em itálico
  pequeno, e o saber poético ao final; cartão TERRA & CÉU mais alto (920).
- **interativo.py**: a tabela do céu do HTML agora inclui Quíron, Lilith,
  Ceres, Pallas, Juno e Vesta (antes só os 10 planetas).
