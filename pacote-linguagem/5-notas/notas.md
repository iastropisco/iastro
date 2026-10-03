# 5-notas — registros e decisões

## Nota 1 — "Modelo de linguagem própria": o que é viável e o que não é

Data: 30/ago/2026

O usuário perguntou se dava para "condensar um modelo de linguagem própria"
e se os dados de efemérides ocupam muito espaço. Resumo honesto:

- **Espaço:** não é problema. 201 anos de posições+aspectos = 188 MB.
  Swiss Ephemeris cobre ~2.000 anos (< 2 GB). Há 130 GB livres.
- **Treinar um LLM do zero:** inviável na máquina (CPU 12 núcleos, 15 GB
  RAM, sem GPU). Os modelos sérios exigem dezenas de GPUs. NÃO tentar.
- **O caminho certo:** modelo de base (qwen3, já instalado) + memória
  curada (`1-conhecimento`) + corpus da voz (`3-corpus`). Isso é o que
  "faz" a linguagem própria, sem treinar nada.
- **Se um dia quiser condensar de verdade:** fine-tuning LoRA num qwen3
  pequeno, usando `3-corpus/corpus-astropisco.txt`, numa GPU alugada na
  nuvem (alguns dólares, poucas horas). Corpus já pronto.
- **Online hoje → offline amanhã:** trabalhar online (nuvem/modelos grandes)
  para gerar conteúdo e enriquecer `1-conhecimento` e `3-corpus` é o fluxo
  ideal; o download ficará leve (conhecimento + corpus + modelo 1.7B–4B).

Conclusão: **a ideia NÃO é absurda** — ela só se concretiza como
"modelo de base + memória própria" (e, opcionalmente, fine-tuning leve),
não como treinar do zero.

## Nota 2 — Limites de coleta de conteúdo

- **Instagram (`@astro_pisco`)**: acesso automatizado retornou só imagens
  base64, sem texto. Perfil essencialmente visual. Para gravar conteúdo,
  o usuário deve descrever ou colar.
- **Google Sites** (mapadaspancs): o corpo é carregado via JS; o webfetch
  só devolvia a navegação. O conhecimento foi gravado a partir da navegação
  + títulos + imagens, mas pode haver corpo extenso não capturado. Se o
  usuário tiver o texto, colar em `1-conhecimento/`.
- **Blog**: o feed RSS funciona bem — 100 posts extraídos com sucesso.

## Nota 3 — Próximos passos sugeridos

1. Ligar o agente `iastro` aos dados de efemérides (para ele calcular
   posições/aspectos ao responder).
2. Converter `3-corpus/corpus-astropisco.txt` em
   `corpus-astropisco.token.jsonl` (passo 1 de qualquer fine-tuning futuro).
3. Trânsitos diários (comparar planetas de hoje com um mapa natal).
4. Geração de imagens/mapas astrais.
5. Publicar o iastro no site (acoplar ao site do planetário).
