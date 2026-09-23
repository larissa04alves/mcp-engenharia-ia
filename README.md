# MCP de apoio a Engenharia de IA

Servidor MCP que transforma informações soltas sobre um projeto de ML em um **plano de
ação priorizado**, fundamentado na literatura. Feito para equipes pequenas, dentro do
assistente de IA que elas já usam.

- **12 práticas** em dois grupos: requisitos e planejamento (RP1–RP6) e dados e
  documentação (DD1–DD6).
- **Prioridade por regra fixa:** `P = I + N + D + (4 − E)`, com ajustes de contexto.
  Nenhum modelo de linguagem participa do cálculo — a mesma entrada dá sempre o mesmo plano.
- **Fundamentação por RAG:** cada orientação vem com trecho da literatura, arquivo e página.
  O RAG não altera a pontuação.

Projeto do PBL4 (PUCPR, Grupo 8, tema Engenharia de IA).

---

## Instalar

Precisa de [uv](https://docs.astral.sh/uv/). O Python 3.12 o próprio `uv` baixa.

```bash
uv sync
```

Os PDFs dos artigos vão em `literatura/` (aceita `.pdf`, `.md` e `.txt`). Depois, gerar
o índice **uma vez**:

```bash
uv run indexar.py
```

Lê a literatura, pica em pedaços e grava em `indice/`. A primeira execução baixa o modelo
de embedding (~80 MB) e depois roda offline. `indice/` não vai para o git — cada pessoa
gera o seu; rodar de novo recria do zero.

**Sem o índice o servidor não sobe**, porque a fundamentação pela literatura é parte do
que ele promete entregar.

---

## Como usar

O servidor não tem interface própria. Quem usa é o **assistente de IA** da equipe —
Claude Desktop, Claude Code ou Cursor — e a equipe só conversa com ele.

### 1. Conectar o servidor ao assistente

O servidor sobe por stdio com `uv run servidor.py`. Use o **caminho absoluto do `uv`**
(`which uv`), porque apps de desktop não herdam o `PATH` do terminal.

**Claude Desktop** — em `claude_desktop_config.json` (Linux: `~/.config/Claude/`;
macOS: `~/Library/Application Support/Claude/`; Windows: `%APPDATA%\Claude\`):

```json
{
  "mcpServers": {
    "engenharia-ia": {
      "command": "/caminho/para/uv",
      "args": ["--directory", "/caminho/para/mcp-engenharia-ia", "run", "servidor.py"]
    }
  }
}
```

**Cursor** — mesmo JSON em `~/.cursor/mcp.json` (global) ou `.cursor/mcp.json` na raiz
do projeto da equipe.

**Claude Code** — um comando, vale para todos os projetos:

```bash
claude mcp add --scope user engenharia-ia -- /caminho/para/uv --directory /caminho/para/mcp-engenharia-ia run servidor.py
```

Reinicie o app. `engenharia-ia` aparece no menu de ferramentas com 4 prompts, 4 tools e
3 resources. Se não aparecer, o mais comum é caminho errado ou índice não gerado — o
servidor recusa subir e escreve o motivo no log do cliente.

### 2. Pedir a análise

Abra uma conversa nova e escolha o prompt **`conduzir_analise`** no menu de anexos (`+`)
do assistente. Ou simplesmente peça:

> Quero uma análise de práticas de Engenharia de IA do nosso projeto.

O assistente assume a condução. Ele vai perguntar, em linguagem simples, sobre três
blocos — o projeto, os requisitos e os dados — num total de 16 perguntas. Exemplos:

- Qual problema o sistema precisa resolver, e para quem?
- Que métrica e que valor contam como sucesso?
- Onde as decisões do projeto ficam registradas?
- De onde vêm os dados? Existe documentação deles?

**Como responder.** Com o que a equipe sabe, sem enfeitar:

| Se a equipe… | Responda assim | O servidor entende |
|---|---|---|
| já faz ou já tem | descreva em uma frase | prática **atendida** — sai do plano |
| não faz ou não tem | diga claramente: "não temos", "ainda não fizemos" | prática **pendente** — entra no plano |
| não sabe | "não sei" | pendente |

Quando uma resposta fica ambígua ("não temos processo formal, mas anotamos no Notion"),
o servidor devolve a pergunta e o assistente a refaz. Isso é esperado: ele prefere
perguntar de novo a chutar.

Nos bastidores, o assistente chama quatro ferramentas nesta ordem, e cada uma diz a ele
qual é a próxima:

```
identificar_contexto → selecionar_praticas → priorizar_praticas → gerar_plano_acao
```

### 3. Receber o plano

O assistente apresenta as práticas pendentes **em ordem de prioridade**, cada uma com:

- nível — **Essencial**, **Recomendada** ou **Evolução** — e a pontuação aberta
  (`I + N + D + (4 − E)`), com os ajustes de contexto que dispararam;
- justificativa, orientação prática e a próxima ação concreta;
- até dois trechos da literatura, com arquivo e página.

A prioridade vem só da regra do servidor. Se a equipe discordar, o assistente é instruído
a dizer isso em vez de reordenar.

### 4. Guardar o registro e retomar depois

Junto com o plano vem um **registro em markdown** com tudo: contexto, ajustes, práticas
atendidas, plano e lacunas. O assistente oferece salvá-lo num arquivo do repositório da
equipe, por exemplo `docs/engenharia-ia.md`.

**O servidor não guarda nada entre sessões.** Esse arquivo é a memória da análise: para
retomar, basta abrir a conversa com ele — "aqui está a análise anterior, o que mudou é
que agora documentamos os dados" — e o assistente refaz a análise com os campos
atualizados.

### Consultar a base sem fazer análise

Três resources ficam disponíveis no menu de anexos, ou por pedido direto ao assistente
("mostra a ficha da DD2"):

| Resource | O que devolve |
|---|---|
| `praticas://catalogo` | as 12 práticas, por grupo |
| `praticas://RP3` | a ficha completa de uma prática: condições, pontuações, orientação, referências |
| `criterios://priorizacao` | critérios, escala, fórmula, faixas e os 5 ajustes de contexto |

Os prompts `coletar_projeto`, `coletar_requisitos` e `coletar_dados` são os três blocos
de perguntas separados, para quem quer conduzir um bloco de cada vez.

---

## Para quem desenvolve

### Inspector

```bash
uv run mcp dev servidor.py
```

Abre uma interface web para testar cada resource, ferramenta e prompt isoladamente,
preenchendo os campos à mão.

### Comandos

| Comando                      | O que faz                                                    |
| ---------------------------- | ------------------------------------------------------------ |
| `uv run base.py`             | confere o `praticas.json` e imprime o resumo da base         |
| `uv run nucleo.py [x.json]`  | imprime o registro de um projeto de exemplo, ou do JSON dado |
| `uv run rag.py`              | mostra o que cada prática recupera da literatura             |
| `uv run indexar.py`          | gera o índice a partir de `literatura/`                      |
| `uv run pytest`              | roda a suíte de testes                                       |
| `uv run mcp dev servidor.py` | abre o Inspector                                             |

### Editando a base de conhecimento

Quase tudo é **arquivo, não código**. Acrescentar prática, mudar pontuação ou ajustar
uma orientação é editar `praticas.json`.

Depois de editar, rode `uv run base.py`: a validação acusa **todos** os problemas de uma
vez, nomeando prática e campo.

```
praticas.json: RP3 — pontuacoes.esforco = 5 (esperado 1 a 3)
```

Duas coisas travadas de propósito pelos testes:

- **As pontuações são transcrição da Tabela 3** do artigo do grupo. Alterar uma quebra
  `test_pontuacoes_batem_com_a_tabela_3`, que é o ponto: aquilo é decisão do grupo, não
  de implementação.
- **Toda referência precisa estar em `literatura/`** e terminar com o marcador
  `[literatura/]`. Senão a ficha citaria uma bibliografia e o RAG outra.

Se uma citação vier fora de contexto, o conserto é editar `termos_busca` da ficha —
sem tocar em código. Eles estão em inglês porque a literatura e o modelo de embedding
também estão (ver `DECISOES.md`, item 9).

### Arquivos

```
praticas.json    base de conhecimento: 12 fichas, critérios, faixas, ajustes
literatura/      PDFs dos artigos
indexar.py       literatura/ → indice/
indice/          banco vetorial gerado (fora do git)
base.py          carrega e valida o praticas.json
nucleo.py        a regra: contexto, seleção, priorização, renderização
rag.py           consulta ao índice
servidor.py      as 11 operações MCP (camada fina)
test_*.py        suíte de testes
roteiros/        entradas e oráculos dos testes ponta a ponta
```

| Documento              | O que é                                                      |
| ---------------------- | ------------------------------------------------------------ |
| `mcp-engenharia-ia.md` | visão e justificativa do artefato                            |
| `SPEC.md`              | especificação: o que o servidor faz e sob quais regras       |
| `PLANO.md`             | ordem de construção e estado de cada etapa                   |
| `DECISOES.md`          | divergências em relação ao `mcp-engenharia-ia.md`, e por quê |
| `TESTES.md`            | plano de testes, roteiros e resultado de cada execução       |
