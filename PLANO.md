# Plano de construção

Ordem de implementação da `SPEC.md`. Construção em um único esforço, com um pré-requisito
bloqueante antes de começar.

---

## Pré-requisito bloqueante

**Colocar os PDFs escolhidos pelo grupo em `literatura/`.**

O servidor recusa subir sem índice (`SPEC.md` §8.2), e a etapa 5 não tem o que indexar.
Nada é construído antes disso. Quando os arquivos estiverem lá, a construção corre de
ponta a ponta sem outra dependência externa.

---

## Etapa 1 — Esqueleto do projeto

Criar `pyproject.toml` com `uv`, adicionar `mcp[cli]`, `chromadb` e `pypdf`, inicializar
o repositório git e escrever o `.gitignore` (`indice/`, `.venv/`, `__pycache__/`).
Criar `literatura/` com um `.gitkeep`.

**Pronto quando:** `uv run python -c "import mcp, chromadb, pypdf"` executa sem erro.

Tamanho: pequeno. Risco: nenhum.

---

## Etapa 2 — `praticas.json`

A maior parte do trabalho, e a única que não é código.

Transcrever da Tabela 3 os ids, nomes, grupos e as pontuações `I/N/D/E` das 12 práticas;
da Tabela 4 os 5 ajustes; da seção 6 do documento de referência os 4 critérios com as
perguntas orientadoras. Nada disso é reescrito.

Escrever, para cada uma das 12, os campos que não existem em nenhum PDF: `descricao`,
`condicoes`, `pergunta`, `orientacao`, `proxima_acao`, `termos_busca` e `referencias` —
ancorados nos 10 artigos fichados no portfólio do PBL1, usando o exemplo completo de DD1
(presente nos dois PDFs) como molde de tom e tamanho.

Marcar `documental_extensa` em RP6, DD2, DD3 e DD6.

**Regra dura:** só entram em `referencias` artigos que estão de fato no portfólio do
grupo. Referência que vocês não leram é o tipo de coisa que queima numa banca.

**Pronto quando:** o arquivo tem 12 fichas completas, cada `campo` aparece uma única vez,
e as pontuações batem linha a linha com a Tabela 3.

**Precisa da revisão de vocês:** as referências de cada prática e o texto de `orientacao`
e `proxima_acao`. As pontuações não — são transcrição.

Tamanho: grande. Risco: baixo tecnicamente, alto em conteúdo — é o que a banca lê.

---

## Etapa 3 — `base.py`

Carregar o `praticas.json` e validar conforme `SPEC.md` §8.1, acumulando **todos** os
problemas antes de falhar (não parar no primeiro), com mensagem apontando prática e campo.
Expor as fichas indexadas por id e por campo.

**Pronto quando:** um `praticas.json` propositalmente quebrado — nota 5, id repetido,
campo faltando — produz as três mensagens de uma vez, cada uma nomeando a prática.

Tamanho: pequeno. Risco: nenhum.

---

## Etapa 4 — `nucleo.py`

Onde mora a regra. Quatro responsabilidades:

1. **Contexto** — normaliza os 4 campos de contexto e devolve quais ajustes se aplicam.
2. **Seleção** — para cada prática, lê `ficha.campo` e aplica a tabela de §2.3, incluindo
   a lista de negações reconhecidas. Devolve as três listas e as perguntas das indeterminadas.
3. **Priorização** — soma os ajustes, limita cada critério a 1–3, calcula
   `P = I + N + D + (4 − E)`, classifica pela faixa e monta a justificativa por regra.
   Devolve os intermediários: referência, ajustes aplicados, final, `P`, nível.
4. **Renderização** — plano de ação e registro do processo em markdown.

Ordenação por `P` decrescente com desempate por id, para a saída ser estável entre execuções.

**Pronto quando:** rodando as funções diretamente (sem subir o MCP) com um projeto de
exemplo, o plano sai correto e verificável à mão — e estes três casos se comportam:

- equipe de 3 em concepção → ajustes 1 e 3 aparecem nos intermediários;
- campo omitido → indeterminada com a pergunta, não pendente;
- `"não temos"` em texto livre → pendente, não atendida.

Tamanho: médio. Risco: médio — é o coração da regra. Vale conferir uma priorização na mão.

---

## Etapa 5 — `indexar.py` e `rag.py`

`indexar.py` conforme §5.1: varre `literatura/`, extrai texto com `pypdf`, pica em ~800
caracteres com 150 de sobreposição preferindo fim de frase, grava no ChromaDB com
`{arquivo, pagina}`, recria a coleção a cada execução.

`rag.py` conforme §5.2: `buscar(termos_busca, k=2)`, truncando em 400 caracteres e
descartando o que estiver acima do limiar.

**Calibrar o limiar aqui.** Nasce em `0.6` e é chute até ver os PDFs reais. O teste é
rodar as `termos_busca` das 12 práticas contra o índice e olhar o que volta: se práticas
não relacionadas puxam o mesmo trecho, o limiar está frouxo; se quase tudo volta vazio,
está apertado.

**Pronto quando:** `uv run indexar.py` reporta quantos pedaços gerou por arquivo, e uma
busca por DD1 devolve trecho sobre dados — não sobre requisitos.

Tamanho: médio. Risco: **o mais alto do projeto** — primeira vez com ChromaDB e com o
formato real dos PDFs. Primeira execução baixa o modelo de embedding (~100 MB).

---

## Etapa 6 — `servidor.py`

As 11 operações da §7 como camada fina sobre `base.py`, `nucleo.py` e `rag.py`. Nenhuma
regra de negócio aqui. Cada ferramenta retorna `proximo_passo`. A checagem de índice da
§8.2 roda na subida.

Escrever os 4 prompts, com a instrução explícita da §7.2 sobre como preencher os campos
(texto / `false` / omitir) — é dela que depende a qualidade da classificação.

**Pronto quando:** `uv run mcp dev servidor.py` abre o Inspector, as 11 operações aparecem
listadas, e o encadeamento `identificar_contexto → selecionar_praticas →
priorizar_praticas → gerar_plano_acao` produz o mesmo plano da etapa 4.

Tamanho: médio. Risco: baixo — se a etapa 4 estiver certa, aqui é fiação.

---

## Etapa 7 — Fechamento

`README.md` com o caminho completo: instalar, colocar PDF em `literatura/`, rodar
`indexar.py`, abrir o Inspector, e o trecho de `claude_desktop_config.json` já com
`uv --directory`.

`DECISOES.md` revisado com o que de fato ficou de pé.

Commits em português, um por etapa.

Tamanho: pequeno.

---

## Ordem e paralelismo

```
literatura/ ──▶ 1 ──▶ 2 ──▶ 3 ──▶ 4 ──┐
                                       ├──▶ 6 ──▶ 7
                      └──────▶ 5 ──────┘
```

A etapa 5 só depende da etapa 1, então pode sair junto com a 2, 3 e 4. É a de maior
risco — vale encostar nela cedo para descobrir problema de ChromaDB enquanto ainda
sobra tempo.

---

## O que vocês precisam fazer

| Quando | O quê |
|---|---|
| Antes de tudo | escolher e colocar os PDFs em `literatura/` |
| Depois da etapa 2 | revisar as referências, `orientacao` e `proxima_acao` das 12 fichas |
| Depois da etapa 2 | confirmar o `documental_extensa` de RP6, DD2, DD3 e DD6 |
| Depois da etapa 5 | olhar as citações e ajustar `termos_busca` no JSON onde vierem ruins |

---

## Depois deste plano

A fase de teste, que você definiu como escopo separado. Fica registrado aqui para não se
perder: o Inspector serve para evidência por operação, o Claude Desktop para a sessão de
ponta a ponta da §5.4 do `mcp-engenharia-ia.md`.
