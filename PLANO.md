# Plano de construção

Ordem de implementação da `SPEC.md`. A spec não muda — só a sequência.

Construção em **fatias verticais**: cada fatia atravessa o sistema inteiro e termina em
algo que roda. A alternativa (terminar uma camada de cada vez) obrigaria a escrever as 12
fichas contra um esquema que nenhum código consumiu ainda; um ajuste no esquema custaria
a reescrita das 12.

---

## Estado atual

| Etapa | Situação |
|---|---|
| 0 — Esqueleto do projeto | ✅ concluída |
| 1 — `praticas.json` com 4 fichas | ✅ concluída |
| 2 — `base.py` | ✅ concluída |
| 3 — `nucleo.py` | ✅ concluída |
| 4 — `servidor.py` | ✅ concluída |
| **Fatia 1** | **✅ o MCP roda, com 11 operações e 4 práticas** |
| 5 — `indexar.py` e `rag.py` | ⛔ bloqueada: `literatura/` vazia |
| 6 — Ligar o RAG ao servidor | ⏳ depende da 5 |
| 7 — As outras 8 fichas | ⏳ |
| 8 — Fechamento | ⏳ |

Fatia 1 integrada ao `master` pelo PR #1. Etapas seguintes em branch novo a partir dele.

```
pyproject.toml    uv, requires-python >=3.12
uv.lock           versões travadas
.venv/            365 MB, Python 3.12.14
.gitignore        indice/ .venv/ __pycache__/ *.pyc
praticas.json     4 fichas, 5 ajustes, cobertura "parcial"
base.py           carrega e valida
nucleo.py         a regra
servidor.py       as 11 operações
literatura/       vazia, com .gitkeep
```

`mcp 2.2.0` · `chromadb 1.5.9` · `pypdf 6.19.0`.

O Python do sistema é 3.14.7, e o projeto foi fixado em 3.12 porque `chromadb` e
`tokenizers` ainda não publicam wheel para 3.14. O `uv` baixou o 3.12 sozinho.

---

# Fatia 1 — Esqueleto vivo ✅

Objetivo: **o servidor completo funcionando com 4 práticas**. Sem RAG, sem literatura.

**Resultado:** as 11 operações respondem por stdio a um cliente MCP real, e o
encadeamento `identificar_contexto → selecionar_praticas → priorizar_praticas →
gerar_plano_acao` produz o mesmo plano que as funções do `nucleo.py` chamadas direto.

Duas divergências apareceram e estão em `DECISOES.md`: o campo `pergunta` (item 7) e
`MCPServer` no lugar de `FastMCP`, renomeado no SDK 2.x (item 8).

**Não verificado:** o Inspector em si (`uv run mcp dev servidor.py`), que precisa de Node
e de interação no navegador. O teste por stdio exercita o mesmo protocolo, mas se a
demonstração for pelo Inspector, vale abrir uma vez antes de contar com ele.

## Etapa 1 — `praticas.json` com 4 fichas ✅

**Feito.** As 4 fichas batem linha a linha com a Tabela 3 (RP1 12 · RP6 6 · DD1 12 · DD4 9),
os 5 ajustes estão transcritos da Tabela 4, e cada referência carrega o marcador
`[portfólio PBL1, 4.x]` para o grupo conferir uma a uma contra o próprio PDF.

**Pendente de revisão do grupo:** `orientacao` e `proxima_acao` de RP1, RP6 e DD4 (o de
DD1 é literal dos PDFs), e o mapeamento artigo → prática nas `referencias`.

As quatro não são quaisquer quatro:

| id | nome | por que esta |
|---|---|---|
| RP1 | Definir o objetivo do sistema | maior pontuação do grupo de requisitos; dispara o ajuste 1 |
| RP6 | Registrar decisões do projeto | única do grupo com `documental_extensa`; dispara o ajuste 3 |
| DD1 | Identificar a fonte dos dados | tem exemplo de saída completo nos dois PDFs; dispara os ajustes 2 e 4 |
| DD4 | Verificar a qualidade dos dados | dispara o ajuste 5 |

Juntas exercitam **os 5 ajustes da Tabela 4**. É o conjunto mínimo que prova a regra inteira.

Escrever também o cabeçalho completo do arquivo: `criterios`, `escala`, `formula`,
`faixas` e os 5 `ajustes` — nada disso depende de quantas práticas existem.

Pontuações, nomes e ajustes são transcrição da Tabela 3 e da Tabela 4. Os campos que não
existem em nenhum PDF (`descricao`, `condicoes`, `pergunta`, `orientacao`, `proxima_acao`,
`termos_busca`, `referencias`) saem ancorados nos artigos do portfólio do PBL1, usando o
exemplo de DD1 como molde de tom e tamanho.

**Regra dura:** só entram em `referencias` artigos que estão de fato no portfólio do grupo.

**Pronto quando:** as 4 fichas estão completas e as pontuações batem com a Tabela 3.

Tamanho: médio. Risco: baixo.

## Etapa 2 — `base.py` ✅

**Feito.** Quebrando o arquivo com 4 erros de uma vez, acusa os 4 nomeando o culpado:
nota fora da escala, id repetido, campo obrigatório ausente e campo de entrada duplicado.
Testados também: faixas com buraco e sobreposição, ajuste com critério inexistente,
`quando` com dois operadores, `delta` zero, `alvo.grupo` inválido, JSON malformado (com
linha e coluna) e arquivo ausente.

`uv run base.py` imprime o resumo da base — é como alguém do grupo confere o arquivo
depois de editar, sem precisar do servidor.

A validação estrita acende pelo campo `cobertura` do próprio JSON, não por flag no código.

Carrega o `praticas.json` e valida conforme `SPEC.md` §8.1, acumulando **todos** os
problemas antes de falhar, com mensagem apontando prática e campo.

A validação de "12 práticas, ids RP1..RP6 e DD1..DD6" fica desligada por ora — o arquivo
tem 4 de propósito. Entra na etapa 7, quando o arquivo estiver completo.

**Pronto quando:** um `praticas.json` quebrado de propósito — nota 5, id repetido, campo
faltando — produz as três mensagens de uma vez, cada uma nomeando a prática.

Tamanho: pequeno. Risco: nenhum.

## Etapa 3 — `nucleo.py` ✅

**Feito.** Os 4 casos de aceite passam, mais 3 que se mostraram necessários: ordem estável,
o ajuste 5 disparando por `problemas_limitacoes` preenchido, e determinismo (mesma entrada
→ saída idêntica). `uv run nucleo.py` roda um projeto de exemplo e imprime o registro.

Duas decisões que valem saber:

- **As ferramentas passam ids, não blobs.** `priorizar_praticas` recebe uma lista de ids e
  recalcula o contexto. Se exigisse o resultado inteiro de `selecionar_praticas`, bastaria
  o assistente resumir o JSON no caminho para corromper a análise.
- **Concordância de gênero na justificativa** ("impacto alto", "necessidade alta"). Duas
  linhas de mapa; sem isso a saída que a banca lê erra o português em toda prática.

Onde mora a regra. Quatro responsabilidades:

1. **Contexto** — normaliza os 4 campos de contexto e devolve quais ajustes se aplicam.
2. **Seleção** — para cada prática, lê `ficha.campo` e aplica a tabela de §2.3, incluindo
   as negações reconhecidas. Devolve as três listas e as perguntas das indeterminadas.
3. **Priorização** — soma os ajustes, limita cada critério a 1–3, calcula
   `P = I + N + D + (4 − E)`, classifica pela faixa, monta a justificativa por regra.
   Devolve os intermediários: referência, ajustes aplicados, final, `P`, nível.
4. **Renderização** — plano de ação e registro do processo em markdown.

Ordenação por `P` decrescente, desempate por id, para a saída ser estável.

**Pronto quando:** chamando as funções direto, sem subir o MCP, um projeto de exemplo
produz plano correto e verificável à mão, e estes casos se comportam:

- equipe de 3 em concepção → ajustes 1 e 3 aparecem nos intermediários;
- campo omitido → indeterminada com a pergunta, não pendente;
- `"não temos"` em texto livre → pendente, não atendida;
- um critério que passaria de 3 com o ajuste → limitado em 3.

Tamanho: médio. Risco: **médio-alto** — é o coração da regra. Conferir uma priorização na mão.

## Etapa 4 — `servidor.py` ✅

**Feito.** Um cliente MCP real, por stdio, lista as 11 operações (3 recursos, 4 ferramentas,
4 prompts) e o encadeamento produz o mesmo plano da etapa 3. `proximo_passo` presente em
todas as ferramentas; `praticas://XX9` devolve erro legível em vez de estourar.

Os 16 campos viraram um modelo Pydantic `Projeto`, com a instrução da §7.2 (texto /
`false` / omitir) na descrição de cada campo — ou seja, dentro do schema JSON que o
assistente enxerga, não só no texto do prompt.

As 11 operações da §7 como camada fina sobre `base.py` e `nucleo.py`. Nenhuma regra de
negócio aqui. Cada ferramenta retorna `proximo_passo`.

Escrever os 4 prompts, com a instrução explícita da §7.2 sobre como preencher os campos
(texto / `false` / omitir) — é dela que depende a qualidade da classificação.

A fundamentação pela literatura ainda não existe: onde ela entraria, a saída simplesmente
não traz nada. A checagem de índice na subida também não existe ainda — ela chega na
fatia 2, junto com o RAG que ela protege.

**Pronto quando:** `uv run mcp dev servidor.py` abre o Inspector, as 11 operações aparecem
listadas, e o encadeamento `identificar_contexto → selecionar_praticas →
priorizar_praticas → gerar_plano_acao` produz o mesmo plano da etapa 3.

Tamanho: médio. Risco: baixo — se a etapa 3 estiver certa, aqui é fiação.

> **Fim da fatia 1: existe um MCP demonstrável.** Incompleto em conteúdo, mas completo
> em funcionamento. Daqui em diante nada é construído no escuro.

**O que falta da fatia 1:** abrir o Inspector uma vez. O teste por stdio exercita o mesmo
protocolo, mas ninguém viu a tela ainda — e é por ela que a demonstração vai passar.

---

# Fatia 2 — Fundamentação pela literatura

Objetivo: **a citação aparece na saída, com fonte e página.**

**Pré-requisito:** os PDFs escolhidos pelo grupo em `literatura/`. É a única dependência
externa do projeto inteiro, e a fatia 1 roda sem ela.

## Etapa 5 — `indexar.py` e `rag.py`

`indexar.py` conforme §5.1: varre `literatura/`, extrai texto com `pypdf`, pica em ~800
caracteres com 150 de sobreposição preferindo fim de frase, grava no ChromaDB com
`{arquivo, pagina}`, recria a coleção a cada execução.

`rag.py` conforme §5.2: `buscar(termos_busca, k=2)`, truncando em 400 caracteres e
descartando o que estiver acima do limiar.

**Calibrar o limiar aqui.** Nasce em `0.6` e é chute até ver os PDFs reais. O teste é
rodar as `termos_busca` das 4 fichas contra o índice e olhar o que volta: se práticas não
relacionadas puxam o mesmo trecho, está frouxo; se quase tudo volta vazio, está apertado.

**Pronto quando:** `uv run indexar.py` reporta quantos pedaços gerou por arquivo, e a busca
por DD1 devolve trecho sobre dados — não sobre requisitos.

Tamanho: médio. Risco: **o mais alto do projeto** — primeira vez com ChromaDB e o formato
real dos PDFs é desconhecido. A primeira execução baixa o modelo de embedding (~100 MB).

## Etapa 6 — Ligar o RAG ao servidor

Injetar a fundamentação na saída das práticas pendentes, no formato da §5.3. Ligar a
checagem de índice na subida (§8.2), com a mensagem que diz o que fazer.

**Pronto quando:** o plano sai com `📚 Fundamentação` e `Fonte: arquivo.pdf, p. N`; e
apagando `indice/`, o servidor recusa subir com a mensagem certa em vez de stack trace.

Tamanho: pequeno. Risco: baixo.

---

# Fatia 3 — Conteúdo completo

## Etapa 7 — As outras 8 fichas

RP2, RP3, RP4, RP5, DD2, DD3, DD5, DD6 — agora contra um esquema já provado por código
que roda, e com o retorno real do RAG à vista para escolher `termos_busca` que funcionem.

Ligar em `base.py` a validação de arquivo completo: 12 práticas, ids `RP1..RP6` e
`DD1..DD6` sem repetição, cada `campo` usado por uma única prática.

Marcar `documental_extensa` em DD2, DD3 e DD6 (RP6 já veio na fatia 1).

**Pronto quando:** as 12 passam na validação e uma análise completa produz plano com as
12 práticas distribuídas entre atendidas, pendentes e indeterminadas.

Tamanho: grande — é o maior volume de escrita do projeto. Risco: baixo tecnicamente,
alto em conteúdo: é o que a banca lê.

**Precisa da revisão de vocês:** as referências de cada prática e o texto de `orientacao`
e `proxima_acao`. As pontuações não — são transcrição.

---

# Fatia 4 — Fechamento

## Etapa 8

`README.md` com o caminho completo: instalar, colocar PDF em `literatura/`, rodar
`indexar.py`, abrir o Inspector, e o trecho de `claude_desktop_config.json` já com
`uv --directory`.

`DECISOES.md` revisado com o que de fato ficou de pé.

Commits em português, um por etapa.

Tamanho: pequeno.

---

## Visão geral

```
✅ ──── FATIA 1 ────✅
0 ──▶ 1 ──▶ 2 ──▶ 3 ──▶ 4 ──┐
                             │
                             ├──▶ 7 ──▶ 8
PDFs ⛔ ──▶ 5 ──▶ 6 ─────────┘
        └─ FATIA 2 ─┘   └FATIA 3┘ └F4┘
```

A fatia 1 terminou. **A etapa 5 é agora o caminho crítico e está bloqueada:** `literatura/`
continua vazia. É a de maior risco do projeto, então quanto antes os PDFs chegarem, antes
se descobre problema de ChromaDB ou de formato de PDF.

A etapa 7 não depende do RAG para começar, mas depende dele para escolher `termos_busca`
com o retorno real à vista — por isso vem depois da 6.

---

## O que vocês precisam fazer

| Quando | O quê | Situação |
|---|---|---|
| **Agora — destrava a etapa 5** | escolher e colocar os PDFs em `literatura/` | ⛔ pendente |
| Quando der | revisar `orientacao`, `proxima_acao` e referências das 4 fichas já escritas | ⏳ |
| Quando der | confirmar o `documental_extensa` de RP6 | ⏳ |
| Depois da etapa 6 | olhar as citações e ajustar `termos_busca` no JSON onde vierem ruins | ⏳ |
| Depois da etapa 7 | revisar as 8 fichas novas e o `documental_extensa` de DD2, DD3 e DD6 | ⏳ |

---

## Depois deste plano

A fase de teste, definida como escopo separado. Fica registrado para não se perder: o
Inspector serve para evidência por operação, o Claude Desktop para a sessão de ponta a
ponta da §5.4 do `mcp-engenharia-ia.md`.
