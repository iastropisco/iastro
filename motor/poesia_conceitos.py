#!/usr/bin/env python3
"""CONCEITOS — famílias semânticas da poesia do mapa astral.

Quando o tema do consultante toca um conceito (ex.: "perda", "recomeço",
"cura", "mar"), a família inteira de palavras entra no mundo semântico da
estrofe — e o corpus do Astro Pisco é varrido por essas palavras, puxando
cláusulas que conversam com o assunto. É a camada poética: nenhum fato é
inventado aqui, são apenas palavras da língua que "chamam" a colagem.

Cada família é um conjunto de palavras em minúsculas (sem acento sensível
ao casamento: o tokenizador do colagem.py já normaliza). A detecção usa só
palavras de 4+ letras do tema; as palavras curtas da família servem apenas
de semente para a busca no corpus.
"""

CONCEITOS = {
    "perda": {
        "perda", "perder", "perdido", "luto", "adeus", "ausência", "ausencia",
        "falta", "saudade", "partida", "despedida", "vazio", "perdida",
        "perdidos", "perdidas", "esquecimento", "esquecer",
    },
    "recomeco": {
        "recomeço", "recomeco", "recomeçar", "recomecar", "renascer",
        "renascimento", "ciclo", "esperança", "esperanca", "amanhecer",
        "volta", "retorno", "renovar", "renovação", "renovacao", "reerguer",
        "recomeços", "recomecos",
    },
    "cura": {
        "cura", "curar", "banho", "banhar", "remédio", "remedio", "remédios",
        "remedios", "ervas", "folhas", "sarar", "chá", "cha", "infusão",
        "infusao", "defumação", "defumacao", "limpeza", "descanso",
        "restaurar", "cicatriz", "ferida", "bálsamo", "balsamo",
    },
    "mar": {
        "mar", "oceano", "onda", "vaga", "sereia", "maré", "mare", "sal",
        "praia", "navegar", "barco", "jangada", "pescador", "rede", "duna",
        "areia", "concha", "marés", "mares", "ondas", "vagas", "salgado",
        "sereias", "pescadores", "jangadeiro", "marujo",
    },
    "rio": {
        "rio", "ribeirão", "ribeirao", "córrego", "corrego", "nascente",
        "cachoeira", "água", "agua", "lagoa", "igarapé", "igarape", "banhado",
        "várzea", "varzea", "rios", "ribeirinhos", "enchente", "vazante",
    },
    "mata": {
        "mata", "floresta", "selva", "árvore", "arvore", "raiz", "semente",
        "folha", "verde", "cerrado", "caatinga", "pantanal", "amazônia",
        "amazonia", "trilha", "vereda", "matas", "florestas", "árvores",
        "arvores", "raízes", "raizes", "sementes", "folhas", "galho", "tronco",
    },
    "folclore": {
        "folclore", "lenda", "lendas", "mito", "mitos", "saci", "curupira",
        "iara", "boitatá", "boitata", "caipora", "cuca", "boto", "lobisomem",
        "mula", "cobra-grande", "mapinguari", "vitória-régia", "vitoria-regia",
        "uirapuru", "lendário", "lendaria", "mítica", "mitico", "assombração",
        "assombracao",
    },
    "indigena": {
        "indígena", "indigena", "indígenas", "indigenas", "tupi", "guarani",
        "tukano", "yanomami", "xavante", "krenak", "cocar", "oca", "canoa",
        "arco", "flecha", "ayahuasca", "rapé", "rape", "tribo", "aldeia",
        "pajé", "paje", "curumim", "cunhã", "cunha", "tribos", "aldeias",
        "pajés", "pajes", "floresta", "cocar", "cocares",
    },
    "afro": {
        "orixá", "orixa", "orixás", "orixas", "axé", "axe", "umbanda",
        "candomblé", "candomble", "terreiro", "gira", "atabaque", "berimbau",
        "capoeira", "samba", "afoxé", "afoxe", "ijexá", "ijexa", "maculelê",
        "maculele", "ponto", "firmeza", "preto-velho", "preta-velha",
        "caboclo", "cabocla", "boiadeiro", "marinheiro", "pombagira", "exu",
        "ogum", "oxum", "iansã", "iansa", "xangô", "xango", "oxóssi", "oxossi",
        "nanã", "nana", "iemanjá", "iemanja", "terreiros", "atabaques",
        "capoeirista", "sambista",
    },
    "mapuche": {
        "mapuche", "mapu", "araucária", "araucaria", "pehuén", "pehuen",
        "antü", "antu", "küyen", "kuyen", "wenu", "pillán", "pillan",
        "lafken", "winka", "mapuches", "araucárias", "araucarias",
    },
    "amor": {
        "amor", "amar", "paixão", "paixao", "coração", "coracao", "beijo",
        "abraço", "abraco", "afeto", "querer", "desejo", "encontro",
        "namoro", "casamento", "amores", "amada", "amado", "apaixonado",
        "corações", "coracoes", "beijos", "abraços", "abracos",
    },
    "medo": {
        "medo", "pavor", "terror", "assombro", "susto", "angústia",
        "angustia", "pesadelo", "fantasma", "escuro", "escuridão",
        "escuridao", "medos", "temer", "temido", "assustador", "assustadora",
    },
    "esperanca": {
        "esperança", "esperanca", "amanhã", "amanha", "futuro", "sonho",
        "sonhos", "desejo", "fé", "fe", "confiança", "confianca", "luz",
        "esperanças", "esperancas", "otimismo", "acreditar",
    },
    "trabalho": {
        "trabalho", "trabalhar", "ofício", "oficio", "colheita", "plantar",
        "semear", "lavoura", "roça", "roca", "enxada", "foice", "trator",
        "plantação", "plantacao", "trabalhador", "trabalhadora", "colher",
        "plantio", "safra",
    },
    "caminho": {
        "caminho", "estrada", "jornada", "rumo", "trilha", "vereda", "norte",
        "atalho", "descaminho", "encruzilhada", "porteira", "caminhos",
        "estradas", "jornadas", "trilhas", "veredas", "rumos", "atalhos",
    },
    "casa": {
        "casa", "lar", "morada", "porto", "abrigo", "acolhida", "família",
        "familia", "quintal", "varanda", "cômodo", "comodo", "casas",
        "lares", "moradas", "abrigos", "famílias", "familias", "quintais",
        "varandas", "porta", "janela", "telhado",
    },
    "tempo": {
        "tempo", "horas", "relógio", "relogio", "passado", "futuro",
        "memória", "memoria", "lembrança", "lembranca", "história",
        "historia", "eterno", "instante", "tempos", "horário", "horario",
        "memórias", "memorias", "lembranças", "lembrancas", "eternidade",
    },
    "noite": {
        "noite", "lua", "luar", "estrela", "estrelas", "sonho", "sonhos",
        "escuro", "escuridão", "escuridao", "madrugada", "constelação",
        "constelacao", "céu", "ceu", "noites", "luas", "estrelado",
        "estrelada", "constelações", "constelacoes",
    },
    "dia": {
        "dia", "sol", "amanhecer", "alvorada", "luz", "clarear", "madrugada",
        "meio-dia", "entardecer", "crepúsculo", "crepusculo", "dias",
        "amanheceres", "alvoradas", "clareira", "luminoso", "luminosa",
    },
    "festa": {
        "festa", "dança", "danca", "cantar", "música", "musica", "alegria",
        "celebrar", "roda", "forró", "forro", "quadrilha", "fogueira",
        "junina", "congo", "tambor", "viola", "sanfona", "zabumba",
        "pandeiro", "cuíca", "cuica", "festas", "danças", "dancas",
        "músicas", "musicas", "cantoria", "celebração", "celebracao",
    },
    "saudade": {
        "saudade", "falta", "lembrança", "lembranca", "memória", "memoria",
        "distância", "distancia", "longe", "volta", "retorno", "reencontro",
        "saudades", "distante", "longínquo", "longinquo", "ausência",
        "ausencia",
    },
    "sonho": {
        "sonho", "sonhos", "imaginação", "imaginacao", "fantasia", "desejo",
        "utopia", "visão", "visao", "devaneio", "quimera", "sonhar",
        "imaginário", "imaginario", "fantástico", "fantastico", "utopias",
    },
    "luta": {
        "luta", "lutar", "batalha", "guerra", "força", "forca",
        "resistência", "resistencia", "coragem", "bravura", "guerreiro",
        "guerreira", "batalhar", "lutas", "batalhas", "guerras", "forças",
        "forcas", "resistir", "vencer", "vitória", "vitoria",
    },
    "paz": {
        "paz", "calma", "sossego", "silêncio", "silêncio", "tranquilidade",
        "tranquilidade", "descanso", "serenidade", "harmonia", "pacífico",
        "pacifica", "sossegada", "sossegado", "sereno", "serena",
    },
    "sabedoria": {
        "sabedoria", "saber", "conhecimento", "sábio", "sabio", "sábia",
        "sabia", "ensinamento", "aprender", "escola", "mestre", "mentor",
        "conselho", "sábios", "sabios", "sábias", "sabias", "conhecimentos",
        "ensinamentos", "conselhos", "aprendizado",
    },
    "vida": {
        "vida", "nascer", "nascimento", "viver", "existir", "alma",
        "essência", "essencia", "criação", "criacao", "germe", "vidas",
        "nascimentos", "existência", "existencia", "almas", "viveres",
    },
    "morte": {
        "morte", "morrer", "fim", "adeus", "despedida", "luto", "sepultura",
        "cova", "espírito", "espirito", "alma", "passagem", "mortes",
        "falecido", "falecida", "eterno", "descanso",
    },
    "viagem": {
        "viagem", "viajar", "estrada", "mundo", "horizonte", "partir",
        "chegar", "destino", "rumo", "mapa", "bússola", "bussola", "navegar",
        "voo", "vôo", "viagens", "viajante", "horizontes", "destinos",
        "partida", "chegada",
    },
    "encontro": {
        "encontro", "encontrar", "reencontro", "chegada", "abraço", "abraco",
        "beijo", "conversa", "roda", "mesa", "fogueira", "encontros",
        "reencontros", "conversas", "encontrão", "encontrao",
    },
    "solidao": {
        "solidão", "solidao", "sozinho", "sozinha", "vazio", "ausência",
        "ausencia", "isolamento", "ermo", "deserto", "solitário", "solitario",
        "solitária", "solitaria", "sozinhos", "sozinhas",
    },
    "alegria": {
        "alegria", "festa", "riso", "sorriso", "cantar", "dança", "danca",
        "brincar", "celebrar", "gratidão", "gratidao", "alegrias", "risos",
        "sorrisos", "cantoria", "brincadeira", "celebração", "celebracao",
    },
    "tristeza": {
        "tristeza", "triste", "choro", "chorar", "lágrima", "lagrima",
        "dor", "mágoa", "magoa", "pesar", "melancolia", "tristezas",
        "tristes", "choros", "lágrimas", "lagrimas", "dores", "mágoas",
        "magoas", "melancólico", "melancolica",
    },
    "fe": {
        "fé", "fe", "crença", "crenca", "rezar", "oração", "oracao",
        "igreja", "santo", "santa", "milagre", "devoção", "devocao",
        "romaria", "promessa", "festa", "crenças", "crencas", "orações",
        "oracoes", "santos", "santas", "milagres", "devoto", "devota",
        "romeiro", "romeira",
    },
    "capixaba": {
        "capixaba", "itapemirim", "piúma", "piuma", "marataízes",
        "marataizes", "anchieta", "guarapari", "cachoeiro", "colatina",
        "linhares", "são mateus", "sao mateus", "domingos martins",
        "pedra azul", "venda nova", "alegre", "conceição da barra",
        "conceicao da barra", "forró", "forro", "congo", "tambor",
        "paneleiras", "panelas", "barro", "mucuri", "itabapoana",
        "capixabas", "cachoeiro de itapemirim", "serra", "vil velha",
        "vila velha", "cariacica", "fundão", "fundao", "santa leopoldina",
        "santa maria de jetibá", "santa maria de jetiba", "afonso cláudio",
        "afonso claudio", "laranja da terra", "são roque do canaa",
        "sao roque do canaa", "itaguaçu", "itaguacu", "itarana", "ibiraçu",
        "ibiracu", "joão neiva", "joao neiva", "aracruz", "ibiraçu",
        "ibiracu", "sooretama", "jaguaré", "jaguare", "são gabriel da palha",
        "sao gabriel da palha", "nova venécia", "nova veneccia", "boi",
        "boizinho", "tambor de congo", "congo capixaba",
    },
}