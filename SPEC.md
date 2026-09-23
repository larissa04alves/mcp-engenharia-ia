# Especificação — MCP de apoio a Engenharia de IA

Documento operacional. Define o que o servidor faz, com quais dados e sob quais regras,
no nível de detalhe necessário para implementar sem tomar decisão nova.

Complementa `mcp-engenharia-ia.md` (visão e justificativa) e `DECISOES.md`
(onde esta especificação diverge daquele documento e por quê).

Fontes de verdade externas:

- **Tabela 3** do artigo do grupo (`G08_6A_Engenharia_de_IA_PBL4.pdf`) — as 12 práticas e suas pontuações de referência.
- **Tabela 4** do mesmo artigo — os 5 ajustes de contexto.
- **Seção 6** de `PBL4-MCP-Referencia.pdf` — os 4 critérios e suas perguntas orientadoras.

Pontuações, nomes de práticas e ajustes são **transcrição literal** dessas fontes.
Nada aqui reescreve valor que já foi decidido pelo grupo.

---

## 1. Estrutura do repositório

```
mcp-engenharia-ia/
  pyproject.toml       gerenciado por uv
  praticas.json        base de conhecimento: 12 fichas, critérios, faixas, ajustes
  literatura/          PDFs fornecidos pelo grupo (nasce vazia)
  indexar.py           literatura/ → pedaços → indice/
  indice/              banco vetorial gerado (ChromaDB). No .gitignore
  base.py              carrega e valida praticas.json
  nucleo.py            contexto, seleção, priorização, renderização
  rag.py               consulta ao índice
  servidor.py          as 11 operações MCP (camada fina)
  README.md            como rodar
  SPEC.md              este arquivo
  PLANO.md             ordem de construção
  DECISOES.md          divergências em relação ao mcp-engenharia-ia.md
```

**Dependências:** `mcp[cli]`, `chromadb`, `pypdf`. Python 3.10+. Ambiente via `uv`.

Não usamos `sentence-transformers`: o ChromaDB traz a própria função de embedding
(ONNX, ~100 MB, offline), e a alternativa arrastaria o PyTorch (~2,5 GB) sem ganho
que justifique o custo neste projeto.

---

## 2. Entradas

Dezesseis campos. Nenhum é obrigatório — informação ausente vira lacuna, não erro.

### 2.1 Campos de prática (12) — relação 1 para 1

Cada prática é determinada por exatamente um campo. A regra de classificação lê
apenas esse campo. Isso torna a decisão trivial de auditar: para qualquer resultado,
existe um único campo que o explica.

| Campo | Prática | O que a equipe informa |
|---|---|---|
| `objetivo` | RP1 | o que o sistema deve fazer |
| `requisitos` | RP2 | requisitos identificados |
| `criterios_sucesso` | RP3 | métrica e valor que contam como sucesso |
| `restricoes` | RP4 | prazo, custo, regulatório, técnico |
| `responsabilidades` | RP5 | quem faz o quê na equipe |
| `registro_decisoes` | RP6 | onde as decisões do projeto ficam registradas |
| `fonte_dados` | DD1 | de onde os dados vêm |
| `documentacao_dados` | DD2 | documentação existente dos dados |
| `caracteristicas_dados` | DD3 | volume, formato, período, variáveis |
| `qualidade_dados` | DD4 | verificações de qualidade já feitas |
| `problemas_limitacoes` | DD5 | problemas conhecidos nos dados |
| `organizacao_infos` | DD6 | como as informações dos dados estão organizadas |

### 2.2 Campos de contexto (4)

Não determinam prática nenhuma. Alimentam os ajustes da seção 4.2.

| Campo | Tipo | Valores |
|---|---|---|
| `tipo_problema` | texto | classificação, regressão, agrupamento, geração, outro |
| `tamanho_equipe` | inteiro | número de integrantes |
| `estagio` | enum | `concepcao`, `desenvolvimento`, `evolucao` |
| `dados_sensiveis` | booleano | dados pessoais ou sensíveis envolvidos |

### 2.3 Como um campo expressa cada estado

Os 12 campos de prática aceitam `str | bool | None`:

| Valor recebido | Significa | Estado da prática |
|---|---|---|
| `true`, ou texto que não nega | a equipe informou algo | **atendida** |
| `false`, texto vazio, ou uma negação limpa | a equipe declarou que não faz | **pendente** |
| chave ausente, `null`, ou texto que nega e emenda conteúdo | não dá para saber | **indeterminada** |

Isto existe porque quem preenche os campos é um modelo de linguagem, e ele tende a
escrever "não temos" em vez de passar `false`. Uma negação lida como conteúdo faz a
prática virar *atendida* e sumir do plano — o erro mais grave que o servidor pode cometer.

**Uma negação é reconhecida pela forma, não por lista fechada.** A comparação é feita sem
acento e sem diferenciar maiúsculas, e o texto é uma negação limpa quando:

1. começa com marca de negação — `nao`, `nenhum(a/s)`, `nunca`, `jamais`, `inexistente`,
   `ausente` — opcionalmente precedida de `ainda`, `por enquanto`, `ate agora`,
   `ate o momento`, `no momento`, `atualmente` ou `hoje`;
2. tem no máximo **6 palavras**;
3. não contém adversativa — `mas`, `porem`, `contudo`, `entretanto`, `todavia`,
   `apesar`, `embora`, `so que`.

Também contam como vazio, e portanto pendente: `""`, `-`, `--`, `n/a`, `na`, `nada`.

**Quando o texto abre negando mas continua falando** — "não temos processo formal, mas
registramos tudo no Notion" — o servidor devolve **indeterminada** e faz a pergunta de
novo. Chutar qualquer um dos dois lados seria pior do que assumir que não deu para saber:
é exatamente para isso que o terceiro estado existe.

> Uma lista fechada foi a primeira implementação e se mostrou insuficiente: `"não temos"`
> era reconhecido e `"não fizemos"` não, então a mesma resposta em outro tempo verbal
> mudava o resultado da análise. Oito de treze formulações realistas escapavam.

---

## 3. Base de conhecimento (`praticas.json`)

### 3.1 Forma do arquivo

```json
{
  "versao": "1.0",
  "criterios": {
    "impacto":     { "pergunta": "O quanto deixar essa prática de lado pode prejudicar o projeto?" },
    "necessidade": { "pergunta": "O quanto essa prática é necessária para o desenvolvimento continuar?" },
    "dependencia": { "pergunta": "Outras atividades dependem da realização dessa prática?" },
    "esforco":     { "pergunta": "Quanto trabalho é necessário para realizar essa prática?" }
  },
  "escala": { "1": "Baixo", "2": "Médio", "3": "Alto" },
  "formula": "P = I + N + D + (4 - E)",
  "faixas": [
    { "nivel": "Essencial",   "min": 9, "max": 12 },
    { "nivel": "Recomendada", "min": 6, "max": 8 },
    { "nivel": "Evolução",    "min": 4, "max": 5 }
  ],
  "ajustes": [ /* seção 4.2 */ ],
  "praticas": [ /* 12 fichas */ ]
}
```

As perguntas orientadoras são transcrição literal da seção 6 do documento de referência.
Os PDFs do grupo definem a escala apenas como Baixo/Médio/Alto — **não inventamos
rubrica por critério**. O recurso `criterios://priorizacao` expõe exatamente isso.

### 3.2 Forma de uma ficha

```json
{
  "id": "DD1",
  "grupo": "dados_documentacao",
  "nome": "Identificar a fonte dos dados",
  "campo": "fonte_dados",
  "descricao": "...",
  "condicoes": {
    "atendida": "...",
    "pendente": "...",
    "indeterminada": "..."
  },
  "pergunta": "De onde vêm os dados que vocês usam?",
  "pontuacoes": { "impacto": 3, "necessidade": 3, "dependencia": 3, "esforco": 1 },
  "documental_extensa": false,
  "orientacao": "Registrar a fonte, o período de coleta e as principais características dos dados.",
  "proxima_acao": "Criar o registro de documentação da fonte dos dados.",
  "termos_busca": ["fonte de dados", "proveniência", "coleta de dados", "data provenance"],
  "referencias": ["..."]
}
```

- `pergunta` é o que o servidor devolve quando a prática fica **indeterminada**.
- `documental_extensa` marca as práticas que o ajuste 3 atinge.
- `termos_busca` é a consulta que a prática faz ao índice da literatura (seção 5).
  Está no JSON de propósito: quando uma citação vier fora de contexto, o conserto é
  editar esta linha, sem tocar em código.

### 3.3 As 12 práticas

Transcrição da Tabela 3. `I`, `N`, `D`, `E` são os valores de referência antes de ajuste.

**Requisitos e planejamento** (`requisitos_planejamento`)

| id | nome | campo | I | N | D | E | P | nível |
|---|---|---|---|---|---|---|---|---|
| RP1 | Definir o objetivo do sistema | `objetivo` | 3 | 3 | 3 | 1 | 12 | Essencial |
| RP2 | Identificar os requisitos | `requisitos` | 3 | 3 | 3 | 2 | 11 | Essencial |
| RP3 | Definir critérios de sucesso | `criterios_sucesso` | 3 | 2 | 2 | 2 | 9 | Essencial |
| RP4 | Identificar restrições | `restricoes` | 2 | 2 | 2 | 2 | 8 | Recomendada |
| RP5 | Definir responsabilidades da equipe | `responsabilidades` | 2 | 2 | 1 | 1 | 8 | Recomendada |
| RP6 | Registrar decisões do projeto | `registro_decisoes` | 2 | 1 | 1 | 2 | 6 | Recomendada |

**Dados e documentação** (`dados_documentacao`)

| id | nome | campo | I | N | D | E | P | nível |
|---|---|---|---|---|---|---|---|---|
| DD1 | Identificar a fonte dos dados | `fonte_dados` | 3 | 3 | 3 | 1 | 12 | Essencial |
| DD2 | Documentar os dados | `documentacao_dados` | 3 | 2 | 2 | 2 | 9 | Essencial |
| DD3 | Registrar características dos dados | `caracteristicas_dados` | 2 | 2 | 2 | 2 | 8 | Recomendada |
| DD4 | Verificar a qualidade dos dados | `qualidade_dados` | 3 | 3 | 2 | 3 | 9 | Essencial |
| DD5 | Identificar problemas e limitações | `problemas_limitacoes` | 3 | 2 | 1 | 2 | 8 | Recomendada |
| DD6 | Organizar as informações dos dados | `organizacao_infos` | 1 | 1 | 1 | 2 | 5 | Evolução |

`documental_extensa: true` proposto para **RP6, DD2, DD3, DD6**. É julgamento nosso,
não vem dos PDFs — o grupo revisa (ver `DECISOES.md`, item aberto 2).

---

## 4. Processamento

### 4.1 Seleção

Para cada prática, lê o campo declarado em `ficha.campo` e aplica a tabela da seção 2.3.
Sem inferência, sem modelo de linguagem. A mesma entrada produz sempre a mesma saída.

Resultado em três listas:

- **atendidas** — saem da priorização, aparecem no plano como reconhecimento.
- **pendentes** — vão para a priorização.
- **indeterminadas** — o servidor devolve `ficha.pergunta` para o assistente perguntar
  à equipe. A equipe responde, o assistente chama `selecionar_praticas` de novo com o
  campo preenchido. A ferramenta é idempotente; não existe operação separada para isso.

### 4.2 Ajustes de contexto

Aplicados **antes** do cálculo, sobre as pontuações de referência. Transcrição da Tabela 4:

| # | Condição | Efeito | Alvo |
|---|---|---|---|
| 1 | `estagio == "concepcao"` | +1 necessidade | grupo `requisitos_planejamento` |
| 2 | `estagio == "evolucao"` | +1 impacto | grupo `dados_documentacao` |
| 3 | `tamanho_equipe <= 3` | −1 esforço | práticas com `documental_extensa: true` |
| 4 | `dados_sensiveis == true` | +1 impacto | DD1, DD2, DD5 |
| 5 | `problemas_limitacoes` preenchido | +1 necessidade | DD4, DD5 |

Após somar todos os ajustes aplicáveis, cada critério é **limitado ao intervalo 1 a 3**.
Isso preserva a faixa final de 4 a 12 e impede que o acúmulo de ajustes descaracterize
a escala — é a regra que o artigo declara textualmente.

> **Consequência observada, não é erro:** o ajuste 5 dispara quando `problemas_limitacoes`
> está preenchido — e nesse caso DD5 já está *atendida*, portanto fora da priorização.
> Na prática o ajuste 5 só afeta DD4. Está registrado em `DECISOES.md` (item aberto 3)
> para o grupo decidir se era essa a intenção.

### 4.3 Cálculo

```
P = I + N + D + (4 − E)
```

com `I`, `N`, `D`, `E` já ajustados e limitados. Faixa resultante: 4 a 12.
Classificação por `faixas`: Essencial 9–12, Recomendada 6–8, Evolução 4–5.

A saída da priorização carrega, para cada prática: pontuações de referência, ajustes
aplicados (com o identificador de cada um), pontuações finais, `P` e nível.
Sem esses intermediários a classificação não é verificável, que é o requisito central
da seção 4.2 de `mcp-engenharia-ia.md`.

### 4.4 Justificativa

Montada por regra a partir de dados que já existem: o estado do campo, os ajustes que
dispararam e a posição na faixa. Não é texto gerado por modelo.

---

## 5. Fundamentação pela literatura (RAG)

O RAG **não participa da pontuação**. A prioridade vem exclusivamente da regra da seção 4.

### 5.1 Indexação (`indexar.py`)

Roda uma vez, fora do servidor.

1. Varre `literatura/` por `.pdf`, `.md` e `.txt`.
2. PDF: extrai texto página a página com `pypdf`.
3. Pica em pedaços de ~800 caracteres com 150 de sobreposição, preferindo cortar em
   fim de frase quando houver um dentro da janela.
4. Guarda cada pedaço no ChromaDB (`PersistentClient` em `indice/`, coleção `literatura`,
   espaço `cosine`) com os metadados `{ arquivo, pagina }`.
5. É idempotente: recria a coleção do zero a cada execução.

Embeddings pela função padrão do ChromaDB. Baixa o modelo uma vez e depois roda offline.

### 5.2 Consulta (`rag.py`)

`buscar(termos_busca: list[str], k: int = 2) -> list[Trecho]`

- Consulta o índice com os termos da ficha unidos por espaço.
- Devolve no máximo **2** trechos, cada um truncado em **400 caracteres**.
- Descarta o que estiver acima do limiar de distância. **Se nada passar, devolve lista
  vazia e a prática sai sem fundamentação** — citação fora de contexto pesa contra numa
  avaliação, ausência de citação não.
- O limiar nasce em `0.6` (distância cosseno) e **precisa ser calibrado** com os PDFs
  reais. Está em constante nomeada no topo de `rag.py`.

### 5.3 Saída

```
📚 Fundamentação: "<trecho>"
   Fonte: portfolio_PBL1.pdf, p. 4
```

O identificador é `arquivo, p. N` — funciona com qualquer PDF que o grupo colocar na pasta,
sem exigir que ele siga formato nenhum.

---

## 6. Saídas

### 6.1 Por prática pendente

Formato fixado pelo exemplo que aparece nos dois PDFs do grupo:

```
Prática:      Identificar a fonte dos dados
Prioridade:   Essencial (12)
Justificativa: A origem dos dados ainda não está registrada e outras práticas de
               documentação dependem dessa informação.
Orientação:   Registrar a fonte, o período de coleta e as principais características dos dados.
Próxima ação: Criar o registro de documentação da fonte dos dados.
📚 Fundamentação: ...   (quando houver)
```

### 6.2 Plano de ação

Conjunto ordenado por `P` decrescente. Desempate por id, para a ordem ser estável
entre execuções.

### 6.3 Registro do processo

Markdown contendo: informações recebidas, práticas atendidas, plano priorizado com os
intermediários do cálculo, lacunas das indeterminadas e os ajustes que dispararam.

`gerar_plano_acao` **devolve esse markdown como texto**. Quem grava o arquivo é o
assistente. O servidor não escreve em disco — mantém a decisão de execução sem efeitos
colaterais e evita tratar caminho inválido, pasta inexistente e permissão.

Como o servidor não tem memória entre sessões, esse registro é o que permite retomar
a análise depois.

---

## 7. Superfície MCP

As 11 operações da tabela 4.1 de `mcp-engenharia-ia.md`, preservadas integralmente.
A seção 10 do documento de referência exige que todos os itens do PBL4 descrevam o mesmo
artefato — divergir aqui faria a implementação brigar com os modelos conceituais,
a arquitetura e os casos de uso escritos pelos outros integrantes.

`servidor.py` é **camada fina**: cada operação valida a entrada, chama `nucleo.py` ou
`base.py` e formata. Nenhuma regra de negócio mora nela.

| Primitiva | Identificador | Entrada | Saída |
|---|---|---|---|
| Recurso | `praticas://catalogo` | — | as 12 fichas agrupadas |
| Recurso | `praticas://{id}` | id | ficha completa com referências |
| Recurso | `criterios://priorizacao` | — | critérios, perguntas, escala, fórmula, faixas, ajustes |
| Ferramenta | `identificar_contexto` | 4 campos de contexto | atributos e ajustes aplicáveis |
| Ferramenta | `selecionar_praticas` | contexto + 12 campos | atendidas, pendentes, indeterminadas, perguntas |
| Ferramenta | `priorizar_praticas` | pendentes + contexto | pontuações, ajustes, P, nível, justificativa |
| Ferramenta | `gerar_plano_acao` | priorização + atendidas + lacunas | plano e registro em markdown |
| Prompt | `coletar_projeto` | — | roteiro: objetivo, tipo, equipe, estágio |
| Prompt | `coletar_requisitos` | — | roteiro: requisitos, critérios, restrições, responsabilidades, decisões |
| Prompt | `coletar_dados` | — | roteiro: fonte, características, qualidade, problemas, organização, sensibilidade |
| Prompt | `conduzir_analise` | — | roteiro que encadeia tudo |

### 7.1 Encadeamento

Toda ferramenta retorna, junto com o resultado, um campo `proximo_passo` dizendo qual
chamar em seguida e com quê. O prompt `conduzir_analise` descreve a ordem completa.

É orientação, não trava: se o assistente chamar fora de ordem, a ferramenta ainda
responde. Erro no meio de uma demonstração é pior que etapa pulada.

### 7.2 Texto dos prompts

Os prompts de coleta instruem explicitamente o assistente sobre a seção 2.3: passar o
texto da equipe quando houver, `false` quando a equipe disser que não faz, e **omitir
o campo** quando ainda não perguntou. É dessa instrução que depende a qualidade da
classificação.

---

## 8. Robustez

### 8.1 Validação do `praticas.json` na subida

Várias pessoas do grupo vão editar esse arquivo. A validação roda ao subir e falha
com mensagem que aponta prática e campo — não com stack trace:

```
praticas.json: RP3 — pontuacoes.esforco = 5 (esperado 1 a 3)
```

Confere: JSON válido · 12 práticas · ids `RP1..RP6` e `DD1..DD6`, sem repetição ·
cada `campo` conhecido e usado por uma única prática · pontuações inteiras de 1 a 3 ·
todo campo obrigatório presente e não vazio · ajustes referenciando critérios e
ids existentes · faixas cobrindo 4 a 12 sem buraco nem sobreposição.

### 8.2 Índice ausente

Se `indice/` não existir ou a coleção estiver vazia, o servidor **recusa subir**:

```
Índice da literatura não encontrado.
Coloque os PDFs em literatura/ e rode: uv run indexar.py
```

Decisão deliberada: a fundamentação pela literatura é exigência do professor, e um
servidor que sobe sem ela pode ser demonstrado por engano sem a parte que foi pedida.

**Consequência operacional:** nada roda antes de `literatura/` receber conteúdo.
A literatura será fornecida antes da construção.

---

## 9. Fora de escopo

- **Teste.** Fase separada, definida depois de o servidor estar pronto.
- **Publicação no GitHub.** Repositório local por enquanto.
- Treinamento, integração, implantação, monitoramento e manutenção — a base foi desenhada
  para receber essas etapas depois sem alteração do servidor.
