# Banco de Arquétipos — "ponte entre céu e território"

Coração do **iastro** multi-cultura: um banco de dados que vincula os
arquétipos da astrologia ocidental aos arquétipos de outras culturas —
indígenas (tupi-guarani, puris/goytacá), folclore brasileiro, orixás
afro-brasileiros, astronomia mapuche e regionalismos (capixaba, carioca,
fluminense...). É a fundação para o **mapa astral de várias culturas**
(ex.: "Sol em Curupira, Mercúrio em Oxalá, Ascendente em Velho").

## Modelo de dados (esquema relacional)

Cada **arquétipo** (uma ficha) tem os campos:

| campo | o que é |
|---|---|
| `id` | identificador único (ex.: `signo.aries`, `folclore.curupira`, `orixa.oxala`) |
| `nome` | nome do arquétipo |
| `cultura` | de qual cosmologia veio (zodiaco, folclore-brasileiro, afro-brasileiro, indigena, mapuche, regional-capixaba, regional-carioca...) |
| `elemento` | fogo / terra / ar / água / não-aplicável |
| `polaridade` | positivo / negativo (yang/yin, ativo/receptivo) |
| `modo` | cardinal / fixo / mutável (quando se aplica) |
| `tema` | palavras-chave centrais (lista curta) |
| `simbolo` | símbolo ou imagem |
| `regiao` | território/estado vinculado (ex.: ES, RJ) |
| `regionalismo` | nota cultural regional (quando houver) |
| `historia` | "história mínima" do arquétipo (2–4 frases fiéis à tradição) |
| `fonte` | referência (livro, autor, trabalho acadêmico) — honesta, sem inventar |
| `nota` | observações livres, incluindo avisos de correspondência *hipotética* |
| `corresponde_a` | signo/planeta ocidental afinado (quando houver base) |

O banco é **relacional** — além de `arquetipo` há tabelas dedicadas para
os outros temas, evitando encher o arquétipo de colunas soltas:

| tabela | fonte (JSON) | conteúdo |
|---|---|---|
| `arquetipo` | `zodiaco.json`, `folclore-brasileiro.json`, `afro-brasileiro.json`, `indigena.json`, `mapuche.json`, `capixaba.json`, `carioca.json` | as fichas de cada cultura |
| `correspondencia` | `correspondencias.json` | vínculo signo/planeta ocidental <-> arquétipo (certeza + fonte) |
| `correspondencia.casa` | (coluna `casa`, INTEGER NULL) | terreno pronto para vínculos *"planeta no signo na casa"*: `mapa_astral.calc` já anota cada planeta com a casa onde está (chave `casa`); uma futura correspondência pode preencher `casa` e a busca priorizará `chave+casa` (índice `idx_corresp_chave_casa`) antes de cair no vínculo geral do signo |
| `planta` | `plantas.json` | planta medicinal/sagrada <-> orixá(s) e tradição (com uso, folclore, link, fonte) |
| `corpo` | `corpo-humano.json` | melotesia clássica: signo <-> parte do corpo |
| `toponimo` | `toponimos.json` | etno-história e toponímia do território (Puri, Aghá, Itaipava, Itaoca...) |
| `partido` | `partidos.json` | panorama de partidos como "arquétipos postos no mapa" (signo/planeta-chave, certeza+fonte) |
| `fonte` | (deduzida de todos) | referências bibliográficas deduplicadas |

## Correspondências (o vínculo) e Avisos

As correspondências planeta/signo <-> arquétipo são uma **criação/hipótese
do projeto** (a "nova linguagem"), não fato acadêmico — por isso cada
vínculo leva `certeza` (alta/média/baixa) e `fonte` quando existir.

Atenção metodológica importante (pesquisa com fontes):

- **Plantas ↔ orixá**: correspondências variam conforme a *nação*
  (Ketu, Jeje, Angola), o terreiro e a casa. Não há vínculo universal.
  Na tradição afro-brasileira as folhas se classificam por **elemento**
  (ar/fogo/água/terra), polaridade e efeito (gùn / èrò). **Não há base
  bibliográfica para mapear planta ↔ signo ocidental** — não fazemos isso.
- **Mão Pelada (ES)** e a **Cuca** têm fontes que documentam a lenda em
  nível nacional; a atribuição ao Espírito Santo está marcada *a verificar*.
- **Capeta da Garrafa (ES)** tem fonte regional capixaba (A Gazeta/Capixapédia).
- **Mapuche**: agora preenchido a partir do livro real *Wenumapu: Astronomía
  y Cosmología Mapuche* (Pozo Menares & Canio Llanquinao, Ocho Libros, 2014),
  texto extraído de `referencias/astronomiamapuche.pdf`. As estrelas antigas
  fora da linha das constelações de Coña têm `corresponde_a` marcado como
  *vínculo em estudo* (pesquisa, não dogma).

## Como usar

1. Edite os JSON por cultura em `/mnt/dados/home-italivre/iastro-ia/arquetipos/`.
2. Rode `python3 construir_banco.py` para agregar tudo num SQLite único
   (`arquetipos.db`).
3. Consulte com `python3 consultar.py`.

```
python3 consultar.py                      # lista culturas/contagens
python3 consultar.py --signo aries        # arquétipos correspondentes a Áries
python3 consultar.py --cultura folclore   # arquétipos do folclore
python3 consultar.py --regiao es          # arquétipos do Espírito Santo
python3 consultar.py --arquetipo curupira # a ficha completa de um arquétipo
python3 consultar.py --planta arruda      # planta <-> orixá
python3 consultar.py --corpo aries        # melotesia: parte do corpo do signo
python3 consultar.py --toponimo itaipava  # etno-história/toponímia (Puri, ES)
python3 consultar.py --partido pt         # partido como arquétipo posto no mapa
```

#### Obra completa (pipeline único)

Do nascimento/evento → o mapa inteiro em uma rodada (tradicional + plantas +
céu da cultura + colagem PNG/HTML/JSON):

```
venv/bin/python /mnt/dados/ephemeris/gerar_mapa.py \
  --data 1990-01-15 --hora 08:00 --local "rio de janeiro" \
  --cultura indigena --tema "maré de estrelas" --feeling esperanca \
  --saida "mapas/exemplos/meu-mapa"
```

Lote noturno (exemplos + índice): `/mnt/dados/ephemeris/gerar_lote.py`.
Esquema de trabalho: **`TRABALHO.md`**.

#### Camada mundana/política

O módulo `/mnt/dados/ephemeris/mundana.py` põe os partidos no mapa de um evento:

```
# mapa do evento eleitoral em Itapemirim-ES, partidos nas casas
/mnt/dados/home-italivre/iastro-ia/venv/bin/python \
    /mnt/dados/ephemeris/mundana.py 2026-10-04 08:00 itapemirim

# mesmo mapa restrito a um partido
/mnt/dados/home-italivre/iastro-ia/venv/bin/python \
    /mnt/dados/ephemeris/mundana.py --partido PT 2026-10-04 08:00 itapemirim

# por coordenadas (Brasília) e com saída JSON
/mnt/dados/home-italivre/iastro-ia/venv/bin/python \
    /mnt/dados/ephemeris/mundana.py 2026-11-15 12:00 --lat -15.7942 --lon -47.8822 --nome Brasília --json
```

Precisa do Python com `swisseph` (no venv do iastro) e do `arquetipos.db`
(atualize com `construir_banco.py`, que lê `partidos.json`).
```

## Pendências
- [x] **Mapuche** preenchido a partir do livro real (PDF em `referencias/`).
- [x] **Mapuche → signos**: vínculos em 5 signos (Melipal→Escorpião alta;
      Antü→Leão, Küyen→Câncer, Wüñellfe→Libra, Wetripantu→Capricórnio media;
      Pünonchoike→Leão baixa). Demais signos ficam vazios (honestidade: os
      `corresponde_a` são "vínculo em estudo").
- [x] **Plantas ↔ orixá** com fontes (e aviso metodológico).
- [x] **Melotesia** (signo ↔ parte do corpo) com fontes clássicas.
- [ ] Revisar *a verificar*: Mão Pelada (ES), hortelã/Iansã, alfazema,
      folha-da-costa/Iansã, babosa/Iemanjá.
- [x] **Afro-brasileiro**: lacuna fechada — adicionados Oxum (→Touro),
      Osanyin/Ossaim (→Virgem), Nanã (→Capricórnio) e Oxumarê (→Peixes);
      cobre agora os 12 signos. Fontes: tradição iorubá/Candomblé (PRANDI).
- [x] **Regional carioca** (`carioca.json`): Gigante Adormecido da Guanabara
      (→Capricórnio), Boi de Reis da Folia de Reis (→Touro), Tamoios e a
      memória da Guanabara — território-memória (→Câncer). Mesma metodologia
      honesta dos arquétipos capixaba (região + fonte + vínculo em estudo).
- [ ] Levar `historia` para todos os arquétipos (todos os 50 preenchidos;
      `puris_goytaca` é ficha aberta/reserva de pesquisa honesta).
- [ ] Incluir mais regionalismos (outros estados; o modelo carioca/capixaba
      é o padrão a replicar: um `.json` por região + entradas em
      `correspondencias.json` + nome em `CULTURAS` de `construir_banco.py`).
- [ ] Vincular desenhos/imagens (figuras dos arquétipos e constelações).

### Lógica territorial na colagem (mapa astral)

No mapa (`colagem.py`), o **território do nascimento** escolhe sozinho a
cultura regional — sem o usuário precisar pedir:

- Sul do Espírito Santo (17 municípios, `_SUL_CAPIXABA`) → `capixaba`
- Qualquer município do RJ → `carioca`
- Demais lugares → nenhuma cultura regional (só as universais)

Regras:
- O filtro territorial vale apenas quando a cultura é **multi** (nenhuma
  escolhida). Se o usuário escolhe uma cultura explícita (ex.: `capixaba`
  para alguém nascido em BH), a escolha é respeitada sem filtro.
- Para adicionar um território novo: criar o `.json` da região, registrar
  em `construir_banco.py` e acrescentar a regra em
  `_cultura_do_territorio()` (e a lista de municípios, se for recorte
  regional como o Sul Capixaba).

### Guia de expansão: culturas do céu (`cultura_ceu`)

A tabela `cultura_ceu` é o catálogo unificado de **culturas do céu** — como
cada povo recorta as estrelas em constelações próprias. Ela junta três
origens numa consulta só (é o que alimenta o cartão "céu da cultura" do
mapa, `_cartao_terra_ceu` em `colagem.py`):

| origem | o que é | onde vive |
|---|---|---|
| `stellarium` | as ~59 culturas que o Stellarium já traz (livres/GPL) | diretório `skycultures` do Stellarium (snap ou `/usr/share/stellarium`) |
| `projeto` (nossa:) | leituras **signo → asterismo** documentadas do projeto | dicionário `LEITURA` em `/mnt/dados/ephemeris/ceu.py` |
| `projeto` (arquétipos) | leitura simbólica derivada das correspondências do banco (indígena, folclore, orixá...) | gerada automaticamente em `construir_banco.py` a partir de `correspondencias.json` |

**Como ampliar:**

1. **Nova leitura signo → asterismo** (ex.: completar `capixaba-sul`, criar
   `guarani`): edite `LEITURA` em `ceu.py` — um dicionário com os 12 signos;
   onde não houver estudo, use `"— (a ampliar)"` (honestidade, nunca chute).
   Depois rode `construir_banco.py` para a linha `nossa:<cultura>` entrar na
   tabela.
2. **Nova cultura inteira do Stellarium**: instale a cultura no diretório
   `skycultures` — `listar_culturas()` a encontra sozinha no próximo build.
3. **Cultura própria do projeto** (como `tupi`/`tukano`): além do `LEITURA`,
   há `NOSSAS_CULTURAS` em `ceu.py` (definições de asterismos próprias) e o
   comando `gerar_nossas()` que materializa os JSONs.
4. **Regra de ouro**: `leitura_signos` vazio ou `"—"` significa "ainda não
   estudado" — o mapa mostra a cultura mesmo assim (asterismos), mas não
   inventa vínculo signo→asterismo.

### Guia de expansão: banco brasileiro (arquétipos)

O banco brasileiro é a prioridade do projeto (indígena, afro-brasileiro,
folclore e regionalismos) — no mapa, essas culturas **ranqueiam primeiro**
na escolha de arquétipos (`buscar_arquetipos_do_signo` em `colagem.py`:
brasileiras antes de mapuche/outras). O padrão para acrescentar uma região
nova (o modelo `capixaba`/`carioca` é o molde):

1. **`<regiao>.json`** — as fichas dos arquétipos da região (campos da
   tabela `arquetipo`: nome, cultura, elemento, tema, simbolo, regiao,
   historia, fonte, nota, corresponde_a...). Fonte honesta, sem inventar.
2. **`correspondencias.json`** — os vínculos signo/planeta ↔ arquétipo,
   cada um com `certeza` (alta/média/baixa) e `fonte`. Vínculo sem base
   bibliográfica fica marcado como *hipótese/em estudo*.
3. **`CULTURAS`** em `construir_banco.py` — incluir o nome da cultura para
   o build ler o JSON novo.
4. **Regra territorial** em `_cultura_do_territorio()` (`colagem.py`) — o
   território do nascimento escolhe sozinho a cultura regional (ex.: sul do
   ES → `capixaba`; RJ → `carioca`). Se for recorte regional, liste os
   municípios (como `_SUL_CAPIXABA`).
5. **Plantas da região** — em `plantas.json`/`ervas-orixas.json`, com os
   campos novos `parte_utilizada`, `preparo` e `territorio` (o rodapé do
   banho no mapa usa "uso tradicional:" + "como preparar:" sem repetir o
   que já foi listado). Campo sem fonte fica vazio — nunca inventado.

Depois: `python3 construir_banco.py` (reconstrói `arquetipos.db`) e teste
com `python3 consultar.py --cultura <cultura>`.

## Roadmap: astrologia mundana e política

Meta futura do iastro: além do mapa de céu-de-natal por cultura, produzir mapas
**mundanos** (de partes/eclipses/ingressos) e **políticos** (de governos,
partidos e cidades), com a mesma base de arquétipos multi-cultura.

Plano (a desenvolver):
1. **feito (base)**: `mapa_astral.py` (já existia) ganhou a camada `mundana.py`,
   que calcula Asc/meio-céu e as casas por local — ES, Itapemirim-ES e Brasília
   como âncoras iniciais (âncoras: `LOCALIDADES` em `mapa_astral.py` +
   `ANCHOR` em `mundana.py`).
2. **feito (base)**: `partidos.json` + tabela `partido` — panorama de partidos
   (ES e Brasil) cada um com `signo_chave`/`planeta_chave`, `certeza=baixa` e
   `fonte`, lidos sobre as casas do mapa do evento em `mundana.py` (partidos
   como "arquétipos postos no mapa").
3. **Leitura pós-outubro-2026**: quando houver resultados eleitorais, assinalar
   quais arquétipos dominaram os ingressos (novo ciclo nacional/regional).
4. Sempre exibir os **links das fontes** ao lado de cada arquétipo/correspondência
   na interface, nunca escondê-los (transparência metodológica).

Onde registrar: este `arquetipos/` continua a única fonte de verdade dos dados;
a camada mundana é só o cálculo (`/mnt/dados/ephemeris/mapa_astral.py`) + a
leitura textual, sem duplicar pesos/interpretações em outro lugar.

## Colagem do planetário (visual interativo + PNG)

Em `mapas/`, o mapa do céu de uma pessoa recebe imagens reais dos telescópios
(JWST/Hubble/Euclid/NASA — domínio público/CC via Wikimedia, ver
`mapas/imagens/manifest.json`) e os arquétipos por signo/cultura como camada
educativa e poética. Duas saídas:

1. **PNG** (`colagem.py`, `mapas/obra-teste.png`):
   `venv/bin/python /mnt/dados/ephemeris/colagem.py --data 1982-11-20 --hora 01:30
   --local "belo horizonte" --cultura folclore --tema "maré de estrelas"
   --feeling esperanca`
2. **HTML interativo** (`interativo.py`, `mapas/obra-interativa.html`) — página
   única auto-contida: roda do zodíaco em SVG com hover (arquétipos + planetas
   por signo), lupa nas fotos dos telescópios, linha do tempo da cosmologia,
   verso do tema/sentimento e botão de imprimir/PDF. Mesmos argumentos, `--saida`.
   Sol/Asc do mapa são mostrados junto aos seus arquétipos na cultura escolhida.

O verso derivado (tema + sentimento) e o traço à mão do usuário entram na
colagem; a versão do formulário web (Streamlit, `app.py`) é o passo seguinte.
O formulário **`app.py` → sidebar → 🪐 Planetário · colagem** já está pronto:
data/hora/local + cultura + tema + sentimento + traço à mão (canvas de desenho
embutido *ou* upload de imagem — o arquivo tem prioridade), gerando o PNG com
botão de download. Requer a dependência extra `streamlit-drawable-canvas`.
`app.py` roda com o venv: `./iniciar.sh`.