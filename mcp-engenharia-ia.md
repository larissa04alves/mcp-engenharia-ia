# MCP de apoio a Engenharia de IA para equipes pequenas

Documento de orientação para o grupo. Explica o que é o MCP, o que o nosso servidor precisa fazer, por que ele foi escolhido como artefato e como a implementação está organizada.

## 1. O que é o MCP

O Model Context Protocol (MCP) é um protocolo aberto que padroniza a forma como assistentes de IA (Claude, Cursor, Copilot) acessam conteúdo e funcionalidades externas. Ele funciona no modelo cliente-servidor: o assistente é o cliente e o nosso programa é o servidor. O assistente descobre o que o servidor oferece, chama o que precisa e recebe o resultado.

Um servidor MCP expõe três tipos de coisa, chamados primitivas:

| Primitiva | O que é | Quem controla | Exemplo no nosso projeto |
|---|---|---|---|
| Recurso | conteúdo que o assistente pode ler | a aplicação | catálogo das 12 práticas |
| Ferramenta | função que o assistente pode executar | o modelo, com confirmação do usuário | calcular a prioridade das práticas |
| Prompt | roteiro de conversa pronto | o usuário | perguntas para coletar informações do projeto |

A comunicação acontece por JSON-RPC 2.0 sobre stdio, ou seja, o assistente inicia o nosso programa como um processo filho e conversa com ele pela entrada e saída padrão. Não há porta de rede, não há servidor web, não há nada exposto.

## 2. Por que o MCP é o nosso artefato

A pesquisa pergunta como apoiar equipes pequenas na adoção de práticas de Engenharia de IA. Essas equipes já usam assistentes de IA no dia a dia de desenvolvimento, e é nesse ambiente que as decisões sobre objetivo, requisitos e dados acontecem. Colocar o conhecimento dentro do assistente faz com que ele seja consultado no momento da decisão, sem que a equipe precise parar e procurar um guia em PDF.

O MCP é o guia. A base de práticas, a regra de priorização e as orientações só existem e só são acessíveis por meio das operações do servidor. Ele não é um meio de distribuição de um guia escrito à parte.

## 3. O que o servidor precisa fazer

O servidor transforma informações soltas sobre um projeto de ML em um plano de ação priorizado. O fluxo é este:

```
informações do projeto
        ↓
identificar contexto (tamanho da equipe, estágio, natureza dos dados)
        ↓
selecionar práticas (atendida, pendente ou indeterminada)
        ↓
priorizar as pendentes  P = I + N + D + (4 − E)
        ↓
classificar (Essencial 9 a 12, Recomendada 6 a 8, Evolução 4 a 5)
        ↓
gerar plano de ação + registro do processo
```

### 3.1 Entradas

Três conjuntos de informação, nenhum campo obrigatório. Informação ausente vira lacuna, não erro.

- Projeto: objetivo do sistema, tipo de problema, tamanho da equipe, estágio (concepção, em desenvolvimento, em evolução).
- Requisitos: requisitos identificados e pendentes, critérios de sucesso, restrições, responsabilidades, registro de decisões.
- Dados: dados utilizados, fonte, características, problemas conhecidos, documentação existente, natureza (pessoais ou sensíveis).

### 3.2 Base de práticas

Doze práticas em dois grupos: requisitos e planejamento (RP1 a RP6) e dados e documentação (DD1 a DD6). Cada prática tem descrição, condições de atendimento, pontuações de referência nos quatro critérios, orientação, próxima ação e referências bibliográficas.

### 3.3 Seleção

Cada prática recebe um de três estados:

- Atendida: as entradas mostram que a equipe já faz isso. Sai da priorização.
- Pendente: as entradas mostram que não faz. Vai para a priorização.
- Indeterminada: não dá para saber. O servidor devolve a pergunta que o assistente deve fazer à equipe.

### 3.4 Priorização

Quatro critérios de 1 a 3: impacto, necessidade, dependência e esforço. O esforço entra invertido porque esforço menor favorece a prioridade. Antes do cálculo, aplicam-se ajustes de contexto (por exemplo, +1 em necessidade nas práticas de requisitos quando o projeto está em concepção). Cada critério fica limitado a 1 a 3 mesmo após o ajuste. O servidor devolve as pontuações intermediárias e os ajustes aplicados, para que a classificação seja explicável.

### 3.5 Saídas

Para cada prática pendente: prática, prioridade, justificativa, orientação e próxima ação. O conjunto ordenado por prioridade decrescente é o plano de ação. Junto vai a lista das práticas atendidas, as lacunas das indeterminadas e o registro do processo em markdown, que a equipe guarda no próprio repositório. Como o servidor não tem memória entre sessões, esse registro é o que permite retomar a análise depois.

### 3.6 Fundamentação pela literatura (RAG)

A pedido do professor, as orientações e justificativas passam a ser fundamentadas por trechos dos artigos levantados no PBL1. Os fichamentos são indexados por embeddings em um banco vetorial local. Quando o servidor monta a orientação de uma prática, consulta o índice e anexa os trechos mais próximos, com a fonte. O RAG não participa da pontuação. A prioridade continua vindo exclusivamente da regra estruturada.

## 4. Arquitetura

Quatro camadas:

```
┌──────────────────────────────────────────────┐
│  Consumo      assistente de IA + equipe        │
└──────────────────────┬───────────────────────┘
                       │ stdio, JSON-RPC 2.0
┌──────────────────────┴───────────────────────┐
│  Protocolo    recursos, ferramentas, prompts   │
├──────────────────────────────────────────────┤
│  Processamento  entrada, seleção,             │
│                 priorização, geração          │
├──────────────────────────────────────────────┤
│  Conhecimento   praticas.json + índice        │
│                 da literatura                 │
└──────────────────────────────────────────────┘
```

A decisão estruturante é separar conhecimento de processamento. Acrescentar uma prática, mudar uma pontuação ou incluir as demais etapas do ciclo de vida é editar arquivo, não código.

### 4.1 Operações expostas

| Primitiva | Identificador | Entrada | Saída |
|---|---|---|---|
| Recurso | `praticas://catalogo` | nenhuma | todas as práticas por grupo |
| Recurso | `praticas://{id}` | id da prática | registro completo com referências |
| Recurso | `criterios://priorizacao` | nenhuma | critérios, fórmula, faixas e ajustes |
| Ferramenta | `identificar_contexto` | informações do projeto | atributos de contexto e ajustes aplicáveis |
| Ferramenta | `selecionar_praticas` | contexto, requisitos e dados | práticas atendidas, pendentes e indeterminadas |
| Ferramenta | `priorizar_praticas` | práticas pendentes e contexto | pontuações, ajustes, nível e justificativa |
| Ferramenta | `gerar_plano_acao` | resultado da priorização | plano de ação e registro do processo |
| Prompt | `coletar_projeto` | nenhuma | roteiro sobre objetivo, tipo, equipe e estágio |
| Prompt | `coletar_requisitos` | nenhuma | roteiro sobre requisitos, critérios e restrições |
| Prompt | `coletar_dados` | nenhuma | roteiro sobre fonte, características e problemas |
| Prompt | `conduzir_analise` | nenhuma | roteiro que encadeia tudo |

### 4.2 Decisões

- Regra estruturada, não inferência: a classificação precisa ser justificável e verificável na avaliação.
- Sem estado: nada de banco, usuários ou sessões. O registro fica com a equipe.
- Execução local: sem hospedagem, sem rede, informações do projeto não saem da máquina.
- Índice vetorial embutido (ChromaDB), não pgvector: pgvector exige um PostgreSQL rodando, o que contradiz a decisão anterior. O índice é conhecimento gerado uma vez, versionado junto ao projeto, e a troca de motor afetaria só a camada de armazenamento.

## 5. Implementação

### 5.1 Ferramentas

| Ferramenta | Papel |
|---|---|
| Python 3.10+ | linguagem do servidor |
| `mcp` (SDK oficial, FastMCP) | transforma funções decoradas em recursos, ferramentas e prompts; cuida do protocolo |
| `chromadb` | banco vetorial embutido, grava em pasta local |
| `sentence-transformers` | embeddings locais dos fichamentos |
| MCP Inspector (`mcp dev servidor.py`) | interface web para testar e capturar evidências |
| Claude Desktop ou Cursor | cliente para a demonstração |

Instalação: `pip install "mcp[cli]" chromadb sentence-transformers`

### 5.2 Estrutura do repositório

```
mcp-engenharia-ia/
  praticas.json      12 práticas, condições, pontuações, ajustes
  literatura/        fichamentos do PBL1 em .md
  indexar.py         lê literatura/, gera embeddings, salva em indice/
  indice/            banco vetorial gerado (ChromaDB)
  servidor.py        recursos, ferramentas e prompts (FastMCP)
```

### 5.3 Como o assistente enxerga o servidor

Configuração no Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "engenharia-ia": {
      "command": "python",
      "args": ["/caminho/absoluto/servidor.py"]
    }
  }
}
```

A partir daí o assistente lista as ferramentas, recursos e prompts automaticamente.

### 5.4 Sessão completa

1. A equipe pede ao assistente uma análise do projeto.
2. O assistente usa `conduzir_analise` e faz as perguntas dos prompts de coleta.
3. Chama `identificar_contexto`, depois `selecionar_praticas`.
4. Se houver práticas indeterminadas, pergunta à equipe e repete a seleção.
5. Chama `priorizar_praticas` e `gerar_plano_acao`.
6. Apresenta o plano em linguagem acessível e entrega o registro em markdown para a equipe salvar.

## 6. Fora do escopo

Treinamento de modelos, integração, implantação, monitoramento e manutenção. A base de práticas foi desenhada para receber essas etapas depois sem alteração do servidor.
