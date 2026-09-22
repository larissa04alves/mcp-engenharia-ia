# Decisões e divergências

`mcp-engenharia-ia.md` fica **intocado**. Este arquivo registra onde a implementação
diverge dele e por quê, para o grupo decidir o que incorporar ao documento.

Importa porque a seção 10 de `PBL4-MCP-Referencia.pdf` exige que todos os itens do PBL4
descrevam o mesmo artefato — os modelos conceituais, a arquitetura e os casos de uso
escritos pelos outros integrantes precisam bater com o que existe de verdade.

---

## Divergências

### 1. Sem `sentence-transformers`

**Documento (§5.1):** `pip install "mcp[cli]" chromadb sentence-transformers`
**Implementação:** `mcp[cli]`, `chromadb`, `pypdf`.

O ChromaDB traz a própria função de embedding (ONNX, ~100 MB, offline).
`sentence-transformers` arrastaria o PyTorch junto — cerca de 2,5 GB — sem ganho que
justifique o custo aqui. Menos dependência e menos código: não escrevemos nada de
embedding, o ChromaDB faz.

**Efeito colateral aceito:** o modelo padrão é treinado em inglês e os fichamentos estão
em português. Como a consulta e o texto estão os dois em português, o ranking relativo
continua funcionando — só não é ótimo. A alternativa multilíngue exige o PyTorch.

### 2. `literatura/` recebe PDF, não markdown

**Documento (§5.2):** `literatura/  fichamentos do PBL1 em .md`
**Implementação:** `literatura/` recebe `.pdf` (também aceita `.md` e `.txt`), lido com `pypdf`.

Ninguém precisa converter nada: o grupo joga o PDF na pasta e roda `indexar.py`.
Por isso `pypdf` entrou nas dependências.

### 3. `indice/` fora do git

**Documento (§4.2):** "O índice é conhecimento gerado uma vez, versionado junto ao projeto"
**Implementação:** `indice/` no `.gitignore`; cada pessoa roda `uv run indexar.py` uma vez.

É um banco SQLite binário. No git, incha o repositório e dá conflito impossível de
resolver toda vez que duas pessoas reindexarem.

O argumento do documento — "a troca de motor afetaria só a camada de armazenamento" —
continua valendo e é o que de fato importa na justificativa do ChromaDB contra o pgvector.
Só a parte do versionamento muda.

### 4. Entradas são campos estruturados, em relação 1 para 1 com as práticas

**Documento (§3.1):** descreve três conjuntos de informação em prosa.
**Implementação:** 16 campos nomeados. Doze são 1 para 1 com as práticas
(`objetivo`→RP1, `fonte_dados`→DD1, …); quatro são contexto e alimentam os 5 ajustes.

Decorre direto de "regra estruturada, não inferência" (§4.2). Para a classificação ser
verificável, ela precisa ler campo nomeado, não texto livre. O mapeamento 1 para 1 faz
com que todo resultado tenha um único campo que o explica.

### 5. Termos de busca declarados na ficha

Cada prática declara `termos_busca` no `praticas.json`, e é isso que consulta o índice.

Não está no documento porque o documento não chega nesse nível. Fica no JSON, e não no
código, pelo mesmo princípio da §4.2: quando uma citação vier fora de contexto, o conserto
é editar uma linha do arquivo.

### 6. O servidor recusa subir sem índice

Sem `indice/` gerado, o servidor não sobe e explica o que fazer.

A fundamentação pela literatura é exigência do professor (§3.6). Um servidor que sobe sem
ela pode ser demonstrado por engano sem a parte que foi pedida.

A checagem é implementada junto com o RAG que ela protege (fatia 2 do `PLANO.md`), não no
primeiro dia. No produto final ela existe; durante a fatia 1 não há índice a proteger
porque não há fundamentação na saída. Isso é o que permite construir e demonstrar o
servidor antes de o grupo escolher os PDFs.

### 7. Campo `pergunta` em cada ficha

A Tabela 2 do artigo lista os campos de uma prática e **não inclui `pergunta`**.
A implementação adicionou esse campo.

Ele é o que o servidor devolve quando a prática fica *indeterminada*, e é o que faz o
passo 4 da §5.4 de `mcp-engenharia-ia.md` existir ("se houver práticas indeterminadas,
pergunta à equipe e repete a seleção"). Sem ele, o assistente teria que inventar a
pergunta, e duas execuções perguntariam coisas diferentes.

### 8. `MCPServer` no lugar de `FastMCP`

**Documento (§5.1):** "`mcp` (SDK oficial, FastMCP)"
**Implementação:** `from mcp.server.mcpserver import MCPServer`

O SDK oficial publicou a versão 2.x e renomeou a classe. Os decoradores `@servidor.tool`,
`@servidor.resource` e `@servidor.prompt` e o `mcp dev` continuam idênticos — é só o nome
da classe que mudou.

A alternativa seria fixar `mcp<2` para manter o nome literal do documento. Não compensa:
seria começar o projeto em uma versão já substituída para preservar uma palavra.

A decisão do documento — usar o SDK oficial e seus decoradores em vez de implementar
JSON-RPC na mão — continua valendo integralmente.

---

## Confirmações (não são divergências)

Ficam registradas porque foram examinadas e mantidas de propósito.

| | |
|---|---|
| As 11 operações da tabela 4.1 | mantidas integralmente — §10 do documento de referência exige consistência entre os itens do PBL4 |
| Pontuações das 12 práticas | transcrição literal da Tabela 3 do artigo do grupo |
| Os 5 ajustes de contexto | transcrição literal da Tabela 4 |
| Critérios e escala | transcrição da §6 do documento de referência: só Baixo/Médio/Alto, sem rubrica inventada |
| Priorização sem modelo de linguagem | a regra estruturada é o único mecanismo, como manda a §11 ("Limites do Protótipo") |
| RAG fora da pontuação | fundamenta a orientação, nunca altera `P` |
| Registro devolvido como texto | o servidor não escreve em disco; quem salva é o assistente |

---

## Itens em aberto

### 1. Quais PDFs entram em `literatura/`

Decisão do grupo. A pasta nasce vazia e nada é adicionado sem essa escolha.
É pré-requisito bloqueante da construção (`PLANO.md`).

### 2. `documental_extensa` em RP6, DD2, DD3 e DD6

O ajuste 3 da Tabela 4 diz "−1 em esforço nas práticas cujo registro indique produção
documental extensa", mas os PDFs não dizem quais são. A proposta acima é julgamento
nosso e precisa do aval do grupo.

### 3. O ajuste 5 só afeta DD4 na prática

A Tabela 4 manda `+1 necessidade em DD4 e DD5` quando há problemas de dados relatados.
Mas o gatilho é o campo `problemas_limitacoes` estar preenchido — e nesse caso DD5 já
está *atendida*, portanto fora da priorização. O ajuste em DD5 nunca chega a ser usado.

Não é erro de implementação, é uma interação entre a Tabela 4 e a regra de seleção.
O grupo decide se era essa a intenção.

### 4. Limiar de relevância do RAG

Nasce em `0.6` (distância cosseno) e é chute até ver os PDFs reais. Calibrado na etapa 5
do `PLANO.md`, rodando as `termos_busca` das 12 práticas contra o índice.

### 5. Prazo e rubrica de avaliação

Não constam em `PBL4-MCP-Referencia.pdf` nem no artigo do grupo. Se existirem, estão em
outro material da disciplina.

### 6. Escopo adiado

Fase de teste e publicação no GitHub — os dois definidos como fora do escopo atual.
