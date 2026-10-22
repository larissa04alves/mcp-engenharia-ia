# MCP de apoio a Engenharia de IA

Servidor MCP que transforma informações soltas sobre um projeto de ML em um **plano de
ação priorizado**, fundamentado na literatura. Feito para equipes pequenas, dentro do
assistente de IA que elas já usam.

- **12 práticas** em dois grupos: requisitos e planejamento (RP1–RP6) e dados e
  documentação (DD1–DD6).
- **Prioridade por regra fixa:** `P = I + N + D + (4 − E)`, com ajustes de contexto.
  Nenhum modelo de linguagem participa do cálculo — a mesma entrada dá sempre o mesmo plano.
- **Fundamentação pela literatura:** cada orientação vem com os trechos que a sustentam,
  escolhidos pela equipe e conferidos no índice da literatura, com arquivo e página. A
  fundamentação não altera a pontuação.

Projeto de Pesquisa Aplicada (PUCPR, Grupo 8, tema Engenharia de IA).

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
      "args": [
        "--directory",
        "/caminho/para/mcp-engenharia-ia",
        "run",
        "servidor.py"
      ]
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

**Como responder.** Com o que a equipe sabe, sem enfeitar. Para cada resposta, o
assistente registra o texto da equipe e uma de quatro situações:

| Se a equipe…                       | Situação         | O servidor entende                                                |
| ---------------------------------- | ---------------- | ----------------------------------------------------------------- |
| já faz ou já tem, e isso basta     | `suficiente`     | prática **atendida** — sai do plano                               |
| tem algo, mas mínimo ou incompleto | `insuficiente`   | prática **pendente** — entra no plano, dizendo que algo já existe |
| não faz ou não tem                 | `inexistente`    | prática **pendente** — entra no plano                             |
| não sabe ou não analisou           | `nao_verificado` | prática **pendente** — entra no plano como algo a levantar        |

Quando a equipe diz que algo existe ("só o README"), o assistente pergunta se ela o
considera suficiente antes de registrar. Um "não sei" nunca vira atendida. O ponto entra
no plano, abre o registro na seção **Pontos a verificar** e o assistente volta a lembrá-lo
ao apresentar o plano.

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
- os trechos da literatura que sustentam a orientação, com arquivo e página.

A prioridade vem só da regra do servidor. Se a equipe discordar, o assistente é instruído
a dizer isso em vez de reordenar.

### 4. Guardar o registro e retomar depois

Junto com o plano vem um **registro em markdown** com tudo: pontos a verificar, contexto,
ajustes, práticas atendidas, plano e lacunas, com a resposta da equipe em cada prática e a
versão da base de práticas. O assistente oferece salvá-lo num arquivo do repositório da
equipe, por exemplo `docs/engenharia-ia.md`.

**O servidor não guarda nada entre sessões.** Esse arquivo é a memória da análise: para
retomar, basta abrir a conversa com ele — "aqui está a análise anterior, o que mudou é
que agora documentamos os dados" — e o assistente refaz a análise com os campos
atualizados.

### As 11 operações do servidor

Tudo o que o assistente consegue chamar. As **tools** são as funções que ele executa na
ordem do fluxo; os **resources** são conteúdo só de leitura; os **prompts** são roteiros
de perguntas que o usuário escolhe no menu de anexos.

| Tipo     | Nome                      | O que recebe                        | O que faz e devolve                                                                                                  |
| -------- | ------------------------- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| tool     | `identificar_contexto`    | os campos do projeto                | normaliza tipo de problema, tamanho da equipe, estágio e dados sensíveis; diz quais dos 5 ajustes de contexto se aplicam |
| tool     | `selecionar_praticas`     | os campos do projeto                | classifica cada uma das 12 práticas em **atendida**, **pendente** ou **indeterminada** pela situação informada; para as indeterminadas, devolve a pergunta a fazer à equipe, e em `a_verificar` lista o que ela ainda não verificou |
| tool     | `priorizar_praticas`      | ids das pendentes + campos          | aplica os ajustes, calcula `P = I + N + D + (4 − E)`, classifica em Essencial / Recomendada / Evolução, ordena e anexa os trechos da literatura de cada prática, conferidos no índice |
| tool     | `gerar_plano_acao`        | os campos do projeto                | roda as três etapas acima de uma vez e devolve o plano completo mais o **registro em markdown** para a equipe salvar    |
| resource | `praticas://catalogo`     | nada                                | as 12 práticas, por grupo                                                                                             |
| resource | `praticas://{id}`         | id da prática (ex.: `RP3`)          | a ficha completa: condições, pontuações, orientação, próxima ação, referências                                        |
| resource | `criterios://priorizacao` | nada                                | critérios, escala, fórmula, faixas e os 5 ajustes de contexto                                                         |
| prompt   | `coletar_projeto`         | nada                                | roteiro com as 4 perguntas sobre o projeto: objetivo, tipo, equipe, estágio                                           |
| prompt   | `coletar_requisitos`      | nada                                | roteiro com as 5 perguntas sobre requisitos, critérios de sucesso, restrições, responsabilidades e decisões           |
| prompt   | `coletar_dados`           | nada                                | roteiro com as 7 perguntas sobre fonte, documentação, características, qualidade, problemas, organização e sensibilidade |
| prompt   | `conduzir_analise`        | nada                                | roteiro completo: encadeia os três blocos de perguntas e as quatro tools, na ordem, até o plano de ação               |

Cada tool devolve também um campo `proximo_passo` dizendo ao assistente o que chamar em
seguida. Os resources ficam no menu de anexos ou saem por pedido direto ("mostra a ficha
da DD2"). Os três prompts `coletar_*` servem para quem quer conduzir um bloco de cada vez.

---

## Para quem desenvolve

### Tecnologias

| Tecnologia                           | Versão | Para que serve aqui                                                                                   |
| ------------------------------------ | ------ | ----------------------------------------------------------------------------------------------------- |
| Python                               | 3.12   | linguagem do servidor                                                                                 |
| [uv](https://docs.astral.sh/uv/)     | —      | instala o Python e as dependências e roda os scripts; é o comando que o assistente usa para subir o servidor |
| `mcp` (SDK oficial, `MCPServer`)     | 2.2.0  | transforma as funções de `servidor.py` em tools, resources e prompts e cuida do protocolo JSON-RPC por stdio |
| `pydantic`                           | 2.13   | define os 16 campos de entrada (`Projeto`) e gera o schema que o assistente vê                       |
| `chromadb`                           | 1.5.9  | banco vetorial embutido: guarda os trechos da literatura em `indice/`; o servidor confere ali cada citação |
| `onnxruntime` + all-MiniLM-L6-v2     | 1.30   | modelo de embedding padrão do ChromaDB; baixado uma vez (~80 MB) e roda offline                      |
| `pypdf`                              | 6.19   | extrai o texto dos PDFs em `literatura/` na hora de indexar                                           |
| `pytest`                             | 9.1    | suíte de testes (`uv run pytest`)                                                                     |
| `ruff`                               | 0.16   | lint e formatação (`uv run ruff check .`)                                                             |
| MCP Inspector (`mcp dev`)            | —      | interface web para testar cada operação isoladamente                                                  |

Não há framework web, banco de dados externo nem chamada a modelo de linguagem: a
priorização é regra fixa em `nucleo.py`, e o único modelo que roda é o de embedding.

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
| `uv run rag.py`              | confere se todas as citações estão no índice                 |
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

Cada ficha traz em `citacoes` os trechos que sustentam a orientação: arquivo, página
física do PDF e o texto copiado do artigo. Os trechos são escolhidos pela equipe, não
pela busca: medido em 22/10/2026, a busca por similaridade trazia trecho do tema certo,
mas quase nunca o que sustentava a instrução. Ao subir, o servidor confere cada citação
no índice, comparando só letras e números, e não sobe se alguma não estiver na página
citada. Para trocar uma citação, edite a ficha e rode `uv run rag.py`.

### Arquivos

```
praticas.json    base de conhecimento: 12 fichas, critérios, faixas, ajustes
literatura/      PDFs dos artigos
indexar.py       literatura/ → indice/
indice/          banco vetorial gerado (fora do git)
base.py          carrega e valida o praticas.json
nucleo.py        a regra: contexto, seleção, priorização, renderização
rag.py           conferência das citações no índice
servidor.py      as 11 operações MCP (camada fina)
test_*.py        suíte de testes
roteiros/        entradas e oráculos dos testes ponta a ponta
```

| Documento              | O que é                                                |
| ---------------------- | ------------------------------------------------------ |
| `mcp-engenharia-ia.md` | visão e justificativa do artefato                      |
| `TESTES.md`            | plano de testes, roteiros e resultado de cada execução |
