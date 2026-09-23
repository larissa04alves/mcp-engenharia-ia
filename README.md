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

## Como rodar

Precisa de [uv](https://docs.astral.sh/uv/). O Python 3.12 o próprio `uv` baixa.

### 1. Instalar

```bash
uv sync
```

### 2. Colocar a literatura

Os PDFs dos artigos vão em `literatura/`. A pasta aceita `.pdf`, `.md` e `.txt`.

### 3. Gerar o índice

```bash
uv run indexar.py
```

Roda **uma vez**. Lê a literatura, pica em pedaços e grava em `indice/`.
A primeira execução baixa o modelo de embedding (~80 MB) e depois roda offline.

`indice/` não vai para o git — cada pessoa gera o seu. Rodar de novo recria do zero.

**Sem esse passo o servidor não sobe**, porque a fundamentação pela literatura é
parte do que ele promete entregar.

### 4. Abrir no Inspector

```bash
uv run mcp dev servidor.py
```

Abre uma interface web para testar cada recurso, ferramenta e prompt isoladamente.

---

## Como usar

O assistente faz as perguntas, chama as ferramentas na ordem e devolve o plano:

```
conduzir_analise
      ↓
identificar_contexto → selecionar_praticas → priorizar_praticas → gerar_plano_acao
```

Cada ferramenta devolve um campo `proximo_passo` dizendo qual chamar em seguida.

Cada prática é classificada lendo **um único campo** da entrada:

| Resposta da equipe                        | Estado            | O que acontece                        |
| ----------------------------------------- | ----------------- | ------------------------------------- |
| informou algo                             | **atendida**      | sai da priorização                    |
| "não temos", "ainda não fizemos", `false` | **pendente**      | entra no plano                        |
| ninguém perguntou ainda                   | **indeterminada** | o servidor devolve a pergunta a fazer |

No fim, `gerar_plano_acao` devolve o registro em markdown. **O servidor não grava arquivo**
— quem salva é o assistente. Como não há memória entre sessões, esse arquivo é o que
permite retomar a análise depois.

---

## Comandos

| Comando                      | O que faz                                                |
| ---------------------------- | -------------------------------------------------------- |
| `uv run base.py`             | confere o `praticas.json` e imprime o resumo da base     |
| `uv run nucleo.py`           | roda um projeto de exemplo e imprime o registro completo |
| `uv run rag.py`              | mostra o que cada prática recupera da literatura         |
| `uv run indexar.py`          | gera o índice a partir de `literatura/`                  |
| `uv run pytest`              | roda a suíte de testes                                   |
| `uv run mcp dev servidor.py` | abre o Inspector                                         |

---

## Editando a base de conhecimento

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

---

## Arquivos

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
```

| Documento              | O que é                                                      |
| ---------------------- | ------------------------------------------------------------ |
| `mcp-engenharia-ia.md` | visão e justificativa do artefato                            |
| `SPEC.md`              | especificação: o que o servidor faz e sob quais regras       |
| `PLANO.md`             | ordem de construção e estado de cada etapa                   |
| `DECISOES.md`          | divergências em relação ao `mcp-engenharia-ia.md`, e por quê |
