# Licenças do acervo — Iastro

Este arquivo existe porque **o programa Stellarium e os dados das culturas do
céu têm licenças diferentes**, e só uma das duas se aplica a você.

Gerado a partir dos `description.md` oficiais de cada cultura em
`skycultures/` do repositório do Stellarium. As 69 culturas do banco
(`cultura_ceu`, coluna `licenca`) foram classificadas em 2026-10-02.

---

## A regra em uma frase

Stellarium é **GPL v2** e libera uso comercial. **Os dados de cada cultura do
céu são de autores diferentes**, e 5 delas são **não comerciais** — essas
não podem entrar em nada que você venda.

---

## As três situações

### 1. Livre para vender e adaptar — 42 culturas

`GPL v2` · `CC BY` · `CC BY-SA` · `CC BY-SA 2.0/3.0`

Pode usar, adaptar, traduzir e vender. **Obrigatório: creditar o autor** e,
nos `CC BY-SA`, manter a mesma licença no que for derivado.

```
anutan               chinese             inuit              modern
arabic_al-sufi*      chinese_chenzhuo    japanese           modern_chinese
aztec                chinese_manchu      korean             modern_hlad
babylonian_mulapin*  chinese_song_dyn    macedonian         modern_iau
babylonian_seleucid* chinese_xianglin    maori              modern_rey
balinese*            chinese_yuan_dyn    mongolian          modern_st
belarusian           hawaiian_starlines  navajo             norse
boorong              indian              norse_edda         northern_andes
                     indian_nakshatras   romanian           russian_siberian
                     sami                samoan             tibetan
                     seri                tongan             tikuna
                     tukano              vanuatu_netwar
                     tupi
```

### 2. Uso comercial, mas SEM adaptar — 12 culturas

`CC BY-ND 4.0` — "NoDerivatives"

Pode vender, **mas não pode modificar os dados**. Se precisar traduzir,
redesenhar ou editar, tem que pedir permissão por escrito ao autor.
Usar como está, com crédito.

```
egyptian_dendera  greek_leidenAratea  khoi-san  xhosa
greek_almagest    greek_dante          zulu
greek_farnese     babylonian_mulapin   balinese
                  arabic_al-sufi       babylonian_seleucid
```

### 3. NÃO COMERCIAL — 5 culturas  ·  fora de qualquer produto pago

`CC BY-NC-ND 4.0` — "NonCommercial, NoDerivatives"

**Não podem entrar em nada que você venda.** Podem constar na versão
grátis, sempre com crédito.

```
arabic_arabian_peninsula   lokono
arabic_indigenous          modern_journey_to_the_west
kamilaroi
```

---

## O que isso significa na prática

| Cenário | Culturas disponíveis |
|---|---|
| Versão **grátis** (site, app, material impresso) | todas as 59 |
| Versão **paga**, sem adaptar nada | 42 livres + 12 ND = **54** |
| Versão **paga**, com desenho próprio por cima | **42** |

As duas que mais importam para o Itapemirim estão livres:

| Cultura | Licença | Autor |
|---|---|---|
| **tupi** | GNU GPL v2.0 | Paulo Marcelo Pontes |
| **tukano** | CC BY-SA 4.0 | — |
| northern_andes | GNU GPL v2.0 | — |
| seri | CC BY-SA 4.0 | — |

**khoi-san, xhosa e zulu são CC BY-ND**: uso comercial liberado, mas
sem adaptação. Se o seu mapa redesenha a linha das figuras, essas três
precisam sair.

---

## Alerta técnico: o código hoje não olha isso

`/mnt/dados/ephemeris/ceu_catalogo.py` monta o mapa **sem consultar a coluna
`licenca`**. Ou seja, hoje ele pode montar um produto vendido com uma
cultura NC dentro, sem avisar.

**Pendência de código:** antes de gerar qualquer mapa pago, o catálogo tem
que filtrar por licença. É a item 2 da ordem de trabalho.

---

## Licenças de terceiros que não são do Stellarium

| Recurso | Licença | Observação |
|---|---|---|
| Medalhões zodiacais (`arquetipos/medalhoes/*.svg`) | CC0 / domínio público | Wikimedia Commons, sem atribuição obrigatória |
| Swiss Ephemeris | AGPL v3 | **atenção**: o motor de efemérides tem licença copyleft própria |
| astropisco (IA local) | Apache 2.0 | derivada do qwen3 |
| qwen3, nomic-embed-text | Apache 2.0 | modelos Ollama |
| Imagens em `arquetipos/referencias/` | variadas | ver `arquetipos/REFERENCIAS.md` |

**O ponto delicado é o Swiss Ephemeris: ele é AGPL.** Se o app virar
software fechado e distribuído, há risco de copyleft. Como o projeto é
livre por natureza e a ETAPA 6 já prevê F-Droid, isso se resolve — mas
decida conscientemente, não por omissão.

---

## Como creditar

Toda cultura exibida precisa mostrar: nome da cultura, autor, licença.
O formato sugerido:

```
Tupi — constelações do povo originário do Brasil
Paulo Marcelo Pontes · GNU GPL v2.0
```

Texto em português, licença no formato original dela. Um exemplo completo
está no rodapé de `ROTEIRO.md` e deve entrar no site.

---

## Manutenção

Quando atualizar o Stellarium, estas licenças podem mudar. Reverificar:

```bash
cd skycultures/
for d in */; do
  d=${d%/}
  [ -f "$d/description.md" ] && \
    printf "%-32s %s\n" "$d" \
    "$(awk '/^## *Licen[sc]e/{f=1;next} f&&NF{print;exit}' $d/description.md)"
done
```

Reatualizar a coluna `licenca` de `cultura_ceu` e revisar este arquivo.
Última verificação: **2026-10-02**.