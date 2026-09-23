"""Servidor MCP: as 11 operações (3 resources, 4 tools, 4 prompts) como camada fina sobre o núcleo. Sem estado."""

import json
import sys

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, Field

import nucleo
import rag
from base import BaseInvalida, carregar

try:
    BASE = carregar()
except BaseInvalida as erro:
    print(erro, file=sys.stderr)
    raise SystemExit(1) from None

# A fundamentação é exigência do professor: sem índice, o servidor não sobe (SPEC §8.2).
if not rag.indice_disponivel():
    print(
        "Índice da literatura não encontrado.\nColoque os PDFs em literatura/ e rode: uv run indexar.py",
        file=sys.stderr,
    )
    raise SystemExit(1)


servidor = MCPServer(
    name="engenharia-ia",
    instructions=(
        "Apoia equipes pequenas na adoção de práticas de Engenharia de IA. "
        "Fluxo: use o prompt conduzir_analise, colete as informações do projeto, "
        "chame identificar_contexto, selecionar_praticas, priorizar_praticas e "
        "gerar_plano_acao nessa ordem. Cada ferramenta diz qual é o próximo passo."
    ),
)

PREENCHIMENTO = (
    "Passe o texto que a equipe informou; false se ela declarou que não faz ou não tem; "
    "OMITA o campo se ainda não perguntou — vira lacuna, e o servidor devolve a pergunta. Não chute."
)


class Projeto(BaseModel):
    """Os 16 campos de entrada. Nenhum é obrigatório: informação ausente vira lacuna."""

    tipo_problema: str | None = Field(None, description="Classificação, regressão, agrupamento, geração, outro.")
    tamanho_equipe: int | None = Field(None, description="Número de integrantes da equipe.")
    estagio: str | None = Field(None, description="concepcao, desenvolvimento ou evolucao.")
    dados_sensiveis: bool | None = Field(None, description="O projeto envolve dados pessoais ou sensíveis?")

    objetivo: str | bool | None = Field(None, description=f"Objetivo do sistema. {PREENCHIMENTO}")
    requisitos: str | bool | None = Field(None, description=f"Requisitos identificados. {PREENCHIMENTO}")
    criterios_sucesso: str | bool | None = Field(
        None, description=f"Métrica e valor que contam como sucesso. {PREENCHIMENTO}"
    )
    restricoes: str | bool | None = Field(None, description=f"Prazo, custo, regulatório, técnico. {PREENCHIMENTO}")
    responsabilidades: str | bool | None = Field(None, description=f"Quem faz o quê na equipe. {PREENCHIMENTO}")
    registro_decisoes: str | bool | None = Field(
        None, description=f"Onde as decisões ficam registradas. {PREENCHIMENTO}"
    )

    fonte_dados: str | bool | None = Field(None, description=f"De onde os dados vêm. {PREENCHIMENTO}")
    documentacao_dados: str | bool | None = Field(
        None, description=f"Documentação existente dos dados. {PREENCHIMENTO}"
    )
    caracteristicas_dados: str | bool | None = Field(
        None, description=f"Volume, formato, período, variáveis. {PREENCHIMENTO}"
    )
    qualidade_dados: str | bool | None = Field(
        None, description=f"Verificações de qualidade já feitas. {PREENCHIMENTO}"
    )
    problemas_limitacoes: str | bool | None = Field(
        None, description=f"Problemas conhecidos nos dados. {PREENCHIMENTO}"
    )
    organizacao_infos: str | bool | None = Field(
        None, description=f"Como as informações dos dados estão organizadas. {PREENCHIMENTO}"
    )

    def entrada(self) -> dict:
        return self.model_dump(exclude_none=True)


def _fundamentar(pratica: dict) -> list[dict]:
    return [{"texto": t.texto, "fonte": t.fonte()} for t in rag.buscar(pratica["termos_busca"])]


def _resumo_ajuste(ajuste: dict) -> dict:
    return {chave: ajuste[chave] for chave in ("id", "descricao", "criterio", "delta")}


def _json(dados) -> str:
    return json.dumps(dados, ensure_ascii=False, indent=2)


# --- resources: a base de práticas, para leitura ---


@servidor.resource(
    "praticas://catalogo",
    name="Catálogo de práticas",
    description="As práticas da base, agrupadas por grupo.",
    mime_type="application/json",
)
def catalogo() -> str:
    grupos: dict[str, list[dict]] = {}
    for pratica in BASE.praticas:
        grupos.setdefault(pratica["grupo"], []).append(
            {"id": pratica["id"], "nome": pratica["nome"], "descricao": pratica["descricao"], "campo": pratica["campo"]}
        )
    return _json({"versao": BASE.versao, "cobertura": "completa" if BASE.completa else "parcial", "grupos": grupos})


@servidor.resource(
    "praticas://{id}",
    name="Ficha de uma prática",
    description="Registro completo de uma prática, com condições, pontuações e referências.",
    mime_type="application/json",
)
def ficha(id: str) -> str:
    pratica = BASE.por_id.get(id.upper())
    if pratica is None:
        return _json({"erro": f"prática {id!r} não existe", "disponiveis": sorted(BASE.por_id)})
    return _json(pratica)


@servidor.resource(
    "criterios://priorizacao",
    name="Critérios de priorização",
    description="Critérios, escala, fórmula, faixas e ajustes de contexto.",
    mime_type="application/json",
)
def criterios() -> str:
    return _json(
        {
            "criterios": BASE.criterios,
            "escala": BASE.escala,
            "formula": BASE.formula,
            "faixas": BASE.faixas,
            "ajustes": BASE.ajustes,
            "observacao": "A prioridade vem só desta regra. Nenhum modelo de linguagem participa do cálculo.",
        }
    )


# --- tools: o fluxo de análise, na ordem ---


@servidor.tool(description="Normaliza o contexto do projeto e diz quais ajustes de pontuação se aplicam.")
def identificar_contexto(projeto: Projeto) -> dict:
    contexto = nucleo.identificar_contexto(BASE, projeto.entrada())
    return {
        "atributos": contexto["atributos"],
        "ajustes_aplicaveis": [_resumo_ajuste(a) for a in contexto["ajustes"]],
        "proximo_passo": "Chame selecionar_praticas com o mesmo projeto.",
    }


@servidor.tool(
    description=(
        "Classifica cada prática em atendida, pendente ou indeterminada, lendo o único campo que a determina. "
        "Decisão por regra, sem inferência."
    )
)
def selecionar_praticas(projeto: Projeto) -> dict:
    selecao = nucleo.selecionar_praticas(BASE, projeto.entrada())
    pendentes = [p["id"] for p in selecao["pendentes"]]

    if selecao["indeterminadas"]:
        proximo = (
            "Há lacunas. Faça à equipe as perguntas listadas em indeterminadas e chame selecionar_praticas "
            "de novo com os campos preenchidos. Quando não restar lacuna que importe, chame priorizar_praticas "
            f"com ids={pendentes}."
        )
    else:
        proximo = f"Chame priorizar_praticas com ids={pendentes} e o mesmo projeto."

    return {**selecao, "proximo_passo": proximo}


@servidor.tool(
    description=(
        "Calcula a prioridade das práticas pendentes: aplica os ajustes de contexto, "
        "calcula P = I + N + D + (4 - E) e classifica em Essencial, Recomendada ou Evolução."
    )
)
def priorizar_praticas(ids: list[str], projeto: Projeto) -> dict:
    ids = [i.upper() for i in ids]
    contexto = nucleo.identificar_contexto(BASE, projeto.entrada())
    return {
        "plano": nucleo.priorizar_praticas(BASE, ids, contexto, _fundamentar),
        "ids_desconhecidos": [i for i in ids if i not in BASE.por_id],
        "proximo_passo": "Chame gerar_plano_acao com o mesmo projeto para receber o registro em markdown.",
    }


@servidor.tool(
    description=(
        "Monta o plano de ação completo e o registro do processo em markdown. "
        "Devolve o texto do registro; quem grava o arquivo é o assistente."
    )
)
def gerar_plano_acao(projeto: Projeto) -> dict:
    analise = nucleo.analisar(BASE, projeto.entrada(), _fundamentar)
    return {
        "contexto": analise["contexto"]["atributos"],
        "ajustes_aplicados": [_resumo_ajuste(a) for a in analise["contexto"]["ajustes"]],
        "atendidas": analise["selecao"]["atendidas"],
        "lacunas": analise["selecao"]["indeterminadas"],
        "plano": analise["plano"],
        "registro_markdown": nucleo.render_registro(BASE, analise),
        "proximo_passo": (
            "Apresente o plano à equipe em linguagem acessível e salve registro_markdown num arquivo "
            "do repositório dela. Como o servidor não guarda estado, esse arquivo é o que permite retomar depois."
        ),
    }


# --- prompts: roteiros de coleta ---


def _roteiro(*perguntas: str) -> str:
    numeradas = "\n".join(f"{n}. {pergunta}" for n, pergunta in enumerate(perguntas, start=1))
    return (
        f"Pergunte à equipe, uma de cada vez e em linguagem simples:\n{numeradas}\n\n"
        f"Ao chamar as ferramentas: {PREENCHIMENTO}"
    )


@servidor.prompt(description="Roteiro para coletar as informações gerais do projeto.")
def coletar_projeto() -> str:
    return _roteiro(
        "Qual problema o sistema precisa resolver, e para quem? (objetivo)",
        "Que tipo de problema é: classificação, regressão, agrupamento, geração? (tipo_problema)",
        "Quantas pessoas trabalham no projeto? (tamanho_equipe)",
        "Em que estágio ele está: concepcao, desenvolvimento ou evolucao? (estagio)",
    )


@servidor.prompt(description="Roteiro para coletar requisitos, critérios, restrições e responsabilidades.")
def coletar_requisitos() -> str:
    return _roteiro(
        "Quais requisitos já foram identificados? (requisitos)",
        "Que métrica e que valor contam como sucesso? (criterios_sucesso)",
        "Que restrições existem: prazo, custo, regulatório, técnico? (restricoes)",
        "Quem faz o quê na equipe? (responsabilidades)",
        "Onde as decisões do projeto ficam registradas? (registro_decisoes)",
    )


@servidor.prompt(description="Roteiro para coletar informações sobre os dados.")
def coletar_dados() -> str:
    return _roteiro(
        "De onde vêm os dados? (fonte_dados)",
        "Existe documentação dos dados? (documentacao_dados)",
        "Qual o volume, formato, período e quais são as variáveis? (caracteristicas_dados)",
        "Que verificações de qualidade já foram feitas? (qualidade_dados)",
        "Que problemas ou limitações vocês já conhecem? (problemas_limitacoes)",
        "Como essas informações estão organizadas hoje? (organizacao_infos)",
        "Há dados pessoais ou sensíveis envolvidos? (dados_sensiveis)",
    )


@servidor.prompt(description="Roteiro completo: conduz a análise do início ao plano de ação.")
def conduzir_analise() -> str:
    return (
        "Conduza uma análise de práticas de Engenharia de IA com a equipe, nesta ordem:\n\n"
        "1. Colete as informações usando os roteiros coletar_projeto, coletar_requisitos e coletar_dados. "
        "Pergunte em linguagem simples, sem jargão, e não invente resposta que a equipe não deu.\n"
        "2. Chame identificar_contexto.\n"
        "3. Chame selecionar_praticas.\n"
        "4. Se houver indeterminadas, faça as perguntas devolvidas e chame selecionar_praticas de novo.\n"
        "5. Chame priorizar_praticas com os ids das pendentes.\n"
        "6. Chame gerar_plano_acao.\n"
        "7. Apresente o plano em linguagem acessível, na ordem de prioridade, e ofereça salvar "
        "registro_markdown num arquivo do repositório da equipe.\n\n"
        "A prioridade vem de uma regra fixa do servidor. Não recalcule, não reordene e não invente "
        "pontuação — se discordar do resultado, diga isso à equipe em vez de alterar a saída.\n\n"
        f"Ao chamar as ferramentas: {PREENCHIMENTO}"
    )


# `mcp dev` e `mcp run` procuram um objeto chamado `mcp`, `server` ou `app` (DECISOES.md, item 12).
server = servidor


if __name__ == "__main__":
    servidor.run()
