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

**Efeito colateral aceito:** o modelo padrão (`all-MiniLM-L6-v2`) é treinado em inglês.
A literatura que o grupo escolheu também está em inglês, então o custo recai só sobre a
consulta — resolvido escrevendo `termos_busca` em inglês (item 9).

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

### 9. `termos_busca` em inglês

**Documento:** não trata do idioma da consulta.
**Implementação:** os `termos_busca` de cada ficha são escritos em inglês; o resto da
ficha continua em português.

Os artigos em `literatura/` estão em inglês e o modelo de embedding só entende bem inglês.
Medido na etapa 5 com as 4 fichas: com os termos em português, 3 voltaram sem nenhum
trecho e a quarta trouxe um trecho genérico (distância 0,48); em inglês, as 4 trazem
trechos do assunto, entre 0,25 e 0,39.

### 10. Limiar de relevância em `0.45`

**SPEC (§5.2):** nasce em `0.6`, a calibrar.
**Implementação:** `LIMIAR = 0.45` em `rag.py`.

Medido com os 17 arquivos da literatura: trechos do assunto ficam entre 0,25 e 0,44;
consultas sem relação nenhuma (controle) ficam entre 0,78 e 0,86; o trecho genérico e
fora de contexto que apareceu ficou em 0,48. `0.6` deixaria esse passar.

Distância baixa não garante trecho bom — a revisão humana das citações continua
necessária (ver `PLANO.md`, "O que vocês precisam fazer").

### 11. Seção de referências fora do índice

**SPEC (§5.1):** indexa o texto de todas as páginas.
**Implementação:** `indexar.py` para de ler um arquivo ao encontrar o título da seção de
referências ("References", "Bibliography", "Referências") numa linha própria.

No teste com o índice completo, a busca por RP2 devolveu a página 39 do Kalinowski — a
lista bibliográfica. Citar uma lista de referências como fundamentação não faz sentido.
Custo aceito: apêndices que vêm depois das referências também ficam de fora.

### 12. Apelido `server` em `servidor.py`

`servidor.py` termina com uma linha que parece supérflua:

```python
server = servidor
```

`mcp dev` e `mcp run` procuram um objeto global chamado `mcp`, `server` ou `app`. Como o
nosso se chama `servidor`, o comando que o próprio `mcp-engenharia-ia.md` documenta —
`mcp dev servidor.py` — falhava com *"No server object found"*, e só funcionava na forma
`servidor.py:servidor`.

O apelido faz o comando documentado funcionar sem renomear o objeto nem obrigar o grupo a
decorar uma sintaxe extra. Descoberto ao abrir o Inspector pela primeira vez: o teste por
stdio não pegava, porque ele executa `uv run servidor.py` direto e não passa pela
descoberta do objeto.

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

### 1. Referências das fichas ✅ resolvido

**Decisão: as `referencias` refletem `literatura/`.** As 12 fichas citam apenas artigos
que estão na pasta, todas com o marcador `[literatura/]`. O marcador `[portfólio PBL1, 4.x]`
não existe mais no arquivo, e `test_base.py` trava a regra: qualquer referência que não
termine em `[literatura/]` quebra a suíte.

Três das citações antigas na verdade já estavam na pasta, só marcadas errado — Kalinowski
(`naming_the_pain…`), Paleyes (`challenges_in_deploying…`) e Kreuzberger (`…MLOps…`).
As lacunas reais eram quatro autorias, trocadas assim:

| ficha | antes (fora da pasta) | agora |
|---|---|---|
| RP1 | Martínez-Fernández, Nahar | Romao, Kalinowski, Peng |
| RP6 | Nazir, Nahar, Wu | **Nygard**, Serban, Kalinowski |
| DD1 | Nahar | Gebru, Roh, Holland |
| DD4 | Martínez-Fernández, Nahar | Breck, Polyzotis, Holland |

Isso importava porque o mesmo bloco de saída trazia `Fonte:` vindo da pasta e
`Referências:` vindo do portfólio — duas bibliografias sem relação entre si.

**Consequência:** o portfólio do PBL1 deixa de ser a fonte das referências das fichas.
Ele continua sendo o levantamento bibliográfico do grupo; quem quiser um artigo dele
citado numa ficha precisa colocar o PDF em `literatura/` e reindexar.

**Sobra um arquivo sem uso:** `an_architectural_risk_analysis_of_machine_learning.pdf`
está indexado mas nenhuma ficha o cita — é o único da pasta nessa situação. O tema
(risco e segurança) não tem prática correspondente entre as 12.

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

### 4. RP5 com fundamentação fraca

Nenhum arquivo da literatura é dedicado a papéis e responsabilidades na equipe. A busca
de RP5 encontra trechos do Kreuzberger (MLOps, p. 11, sobre os papéis de um time de ML)
e do Romao — relacionados, mas de passagem. Se o grupo quiser uma fonte dedicada, o
candidato é Nahar et al. (2022), *Collaboration Challenges in Building ML-Enabled Systems*.

### 5. Prazo e rubrica de avaliação

Não constam em `PBL4-MCP-Referencia.pdf` nem no artigo do grupo. Se existirem, estão em
outro material da disciplina.

### 6. Escopo adiado

Fase de teste e publicação no GitHub — os dois definidos como fora do escopo atual.
