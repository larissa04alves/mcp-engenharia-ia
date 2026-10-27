"""A regra de análise: contexto, seleção, priorização e registro. Puro, sem IO nem modelo de linguagem."""

import unicodedata
from collections.abc import Callable
from datetime import date

from base import CRITERIOS, SITUACOES, Base, carregar

ESTAGIOS = ("concepcao", "desenvolvimento", "evolucao")

ATENDIDA, PENDENTE, INDETERMINADA = "atendida", "pendente", "indeterminada"
SUFICIENTE, INEXISTENTE, NAO_VERIFICADO = "suficiente", "inexistente", "nao_verificado"
EXISTE = {"suficiente", "insuficiente"}

ROTULO_SITUACAO = {
    "suficiente": "existe e é suficiente",
    "insuficiente": "existe, mas não é suficiente",
    "inexistente": "não existe",
    "nao_verificado": "ainda não verificado",
}
LEVANTAR = "Levantar o que ainda não foi verificado e registrar o resultado. Depois: "

CRITERIOS_FEMININOS = {"necessidade", "dependencia"}
FEMININO = {"baixo": "baixa", "médio": "média", "alto": "alta"}

# Identificadores são sem acento; o que o usuário lê, não.
ACENTO = {"dependencia": "dependência", "esforco": "esforço"}
ROTULO_ESTAGIO = {"concepcao": "concepção", "desenvolvimento": "desenvolvimento", "evolucao": "evolução"}

LIMITE_MIN, LIMITE_MAX = 1, 3

# Recebe a ficha e devolve trechos {"texto", "fonte"}.
Fundamentar = Callable[[dict], list[dict]]


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().split())


def situacao_do_campo(valor) -> str | None:
    """A situação que a equipe declarou num campo de prática; None se o campo não traz uma válida."""
    situacao = valor.get("situacao") if isinstance(valor, dict) else None
    return situacao if situacao in SITUACOES else None


def _resposta(valor) -> str | None:
    resposta = valor.get("resposta") if isinstance(valor, dict) else None
    if not isinstance(resposta, str):
        return None
    return resposta.strip() or None


def estado_do_campo(valor) -> str:
    """Só suficiente atende. Existir sem bastar, não existir e não saber vão para o plano."""
    situacao = situacao_do_campo(valor)
    if situacao is None:
        return INDETERMINADA
    return ATENDIDA if situacao == SUFICIENTE else PENDENTE


# Os tipos dos campos de contexto vêm garantidos pelo servidor (SPEC §2.2); aqui só se descarta o que fugir deles.
def _inteiro(valor) -> int | None:
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else None


def _booleano(valor) -> bool | None:
    return valor if isinstance(valor, bool) else None


def _estagio(valor) -> str | None:
    estagio = _normalizar(str(valor or ""))
    return estagio if estagio in ESTAGIOS else None


# campo de contexto → (rótulo no registro, normalizador), na ordem em que aparecem na saída.
CONTEXTO = {
    "tipo_problema": ("Tipo de problema", lambda valor: valor or None),
    "tamanho_equipe": ("Tamanho da equipe", _inteiro),
    "estagio": ("Estágio", _estagio),
    "dados_sensiveis": ("Dados pessoais ou sensíveis", _booleano),
}


def identificar_contexto(base: Base, entrada: dict) -> dict:
    """Normaliza os campos de contexto e devolve os ajustes que se aplicam a esta análise."""
    atributos = {campo: normalizar(entrada.get(campo)) for campo, (_, normalizar) in CONTEXTO.items()}
    valores = {**entrada, **atributos}
    ajustes = [a for a in base.ajustes if _ajuste_dispara(a, valores)]
    return {"atributos": atributos, "ajustes": ajustes}


def _ajuste_dispara(ajuste: dict, valores: dict) -> bool:
    quando = ajuste["quando"]
    valor = valores.get(quando["campo"])

    if "igual" in quando:
        alvo = quando["igual"]
        if isinstance(alvo, bool):
            return valor is alvo
        return valor is not None and _normalizar(str(valor)) == _normalizar(str(alvo))
    if "ate" in quando:
        numero = _inteiro(valor)
        return numero is not None and numero <= quando["ate"]
    return (situacao_do_campo(valor) in EXISTE) == quando["preenchido"]


def _ajuste_atinge(ajuste: dict, pratica: dict) -> bool:
    alvo = ajuste["alvo"]
    if "grupo" in alvo:
        return pratica["grupo"] == alvo["grupo"]
    if "ids" in alvo:
        return pratica["id"] in alvo["ids"]
    return pratica["documental_extensa"] is alvo["documental_extensa"]


def selecionar_praticas(base: Base, entrada: dict) -> dict:
    """Classifica cada prática lendo o único campo que a determina."""
    selecao = {ATENDIDA: [], PENDENTE: [], INDETERMINADA: []}

    for pratica in base.praticas:
        valor = entrada.get(pratica["campo"])
        situacao = situacao_do_campo(valor)
        item = {
            "id": pratica["id"],
            "nome": pratica["nome"],
            "campo": pratica["campo"],
            "motivo": pratica["condicoes"][situacao or INDETERMINADA],
        }
        if situacao is None:
            item["pergunta"] = pratica["pergunta"]
        else:
            item.update(situacao=situacao, resposta=_resposta(valor))
        selecao[estado_do_campo(valor)].append(item)

    return {
        "atendidas": selecao[ATENDIDA],
        "pendentes": selecao[PENDENTE],
        "indeterminadas": selecao[INDETERMINADA],
        "a_verificar": [p for p in selecao[PENDENTE] if p["situacao"] == NAO_VERIFICADO],
    }


def priorizar_praticas(
    base: Base, ids: list[str], contexto: dict, fundamentar: Fundamentar | None = None, entrada: dict | None = None
) -> list[dict]:
    """Aplica os ajustes, calcula P = I + N + D + (4 - E), classifica e ordena por P decrescente."""
    entrada = entrada or {}
    priorizadas = []
    for pratica in (base.por_id[i] for i in ids if i in base.por_id):
        item = _priorizar_uma(base, pratica, contexto["ajustes"], entrada.get(pratica["campo"]))
        if fundamentar:
            item["fundamentacao"] = fundamentar(pratica)
        priorizadas.append(item)
    return sorted(priorizadas, key=lambda item: (-item["pontuacao"], item["id"]))


def _priorizar_uma(base: Base, pratica: dict, ajustes: list[dict], valor) -> dict:
    # Sem situação declarada, prioriza-se como prática que não existe.
    situacao = situacao_do_campo(valor) or INEXISTENTE
    proxima_acao = pratica["proxima_acao"]
    if situacao == NAO_VERIFICADO:
        proxima_acao = LEVANTAR + proxima_acao[0].lower() + proxima_acao[1:]

    referencia = pratica["pontuacoes"]
    aplicados = [a for a in ajustes if _ajuste_atinge(a, pratica)]

    final = dict(referencia)
    for ajuste in aplicados:
        bruto = final[ajuste["criterio"]] + ajuste["delta"]
        final[ajuste["criterio"]] = max(LIMITE_MIN, min(LIMITE_MAX, bruto))

    pontuacao = final["impacto"] + final["necessidade"] + final["dependencia"] + (4 - final["esforco"])
    nivel = base.nivel(pontuacao)

    return {
        "id": pratica["id"],
        "nome": pratica["nome"],
        "situacao": situacao,
        "resposta": _resposta(valor),
        "pontuacoes_referencia": referencia,
        "ajustes_aplicados": [
            {
                "id": a["id"],
                "descricao": a["descricao"],
                "criterio": a["criterio"],
                "de": referencia[a["criterio"]],
                "para": final[a["criterio"]],
            }
            for a in aplicados
        ],
        "pontuacoes_finais": final,
        "pontuacao": pontuacao,
        "nivel": nivel,
        "justificativa": _justificar(base, pratica, situacao, final, pontuacao, nivel, aplicados),
        "orientacao": pratica["orientacao"],
        "proxima_acao": proxima_acao,
        "referencias": pratica["referencias"],
    }


def _justificar(
    base: Base, pratica: dict, situacao: str, final: dict, pontuacao: int, nivel: str, aplicados: list[dict]
) -> str:
    partes = [pratica["condicoes"][situacao], f"Pontuação {pontuacao} ({nivel}): {_frase_criterios(base, final)}."]
    if aplicados:
        partes.append("Ajustes de contexto: " + "; ".join(a["descricao"] for a in aplicados) + ".")
    return " ".join(partes)


def _frase_criterios(base: Base, final: dict) -> str:
    termos = []
    for criterio in CRITERIOS:
        rotulo = base.escala[str(final[criterio])].lower()
        if criterio in CRITERIOS_FEMININOS:
            rotulo = FEMININO.get(rotulo, rotulo)
        termos.append(f"{ACENTO.get(criterio, criterio)} {rotulo}")
    return ", ".join(termos[:-1]) + " e " + termos[-1]


def analisar(base: Base, entrada: dict, fundamentar: Fundamentar | None = None) -> dict:
    """Contexto, seleção e plano priorizado das pendentes, numa chamada."""
    contexto = identificar_contexto(base, entrada)
    selecao = selecionar_praticas(base, entrada)
    plano = priorizar_praticas(base, [p["id"] for p in selecao["pendentes"]], contexto, fundamentar, entrada)
    return {"contexto": contexto, "selecao": selecao, "plano": plano}


def render_registro(base: Base, analise: dict, quando: date | None = None) -> str:
    """Registro do processo em markdown. O servidor devolve o texto; quem grava o arquivo é o assistente."""
    contexto, selecao, plano = analise["contexto"], analise["selecao"], analise["plano"]
    linhas = [
        "# Registro de análise — Engenharia de IA",
        "",
        f"Gerado em {(quando or date.today()).strftime('%d/%m/%Y')}. Base de práticas v{base.versao}.",
        "",
        f"## Pontos a verificar ({len(selecao['a_verificar'])})",
        "",
    ]
    # No topo, para que quem retomar a análise por este arquivo comece pelo que ficou em aberto.
    if selecao["a_verificar"]:
        linhas += ["A equipe ainda não sabe ou não analisou estes pontos. Eles estão no plano de ação:", ""]
        linhas += [
            f"- **{p['id']} {p['nome']}** — {_citar(p['resposta']) or p['motivo']}" for p in selecao["a_verificar"]
        ]
    else:
        linhas.append("Nenhum.")

    linhas += ["", "## Contexto do projeto", ""]
    for campo, (rotulo, _) in CONTEXTO.items():
        linhas.append(f"- **{rotulo}:** {_legivel(campo, contexto['atributos'][campo])}")

    linhas += ["", "## Ajustes de contexto aplicáveis", ""]
    linhas += [
        f"- {a['descricao']} → {a['delta']:+d} em {ACENTO.get(a['criterio'], a['criterio'])}"
        for a in contexto["ajustes"]
    ] or ["Nenhum."]

    linhas += ["", f"## Práticas atendidas ({len(selecao['atendidas'])})", ""]
    linhas += [
        " ".join(filter(None, [f"- **{p['id']} {p['nome']}** — {p['motivo']}", _citar(p["resposta"])]))
        for p in selecao["atendidas"]
    ] or ["Nenhuma."]

    linhas += ["", f"## Plano de ação ({len(plano)} prática(s) pendente(s))", ""]
    for posicao, item in enumerate(plano, start=1):
        linhas += _bloco_pratica(posicao, item)
    if not plano:
        linhas.append("Nenhuma prática pendente.")

    linhas += ["", f"## Lacunas ({len(selecao['indeterminadas'])})", ""]
    if selecao["indeterminadas"]:
        linhas += ["Estas práticas não puderam ser classificadas. Perguntas a fazer à equipe:", ""]
        linhas += [f"- **{p['id']} {p['nome']}** — {p['pergunta']}" for p in selecao["indeterminadas"]]
    else:
        linhas.append("Nenhuma.")

    return "\n".join(linhas) + "\n"


def _citar(resposta: str | None) -> str:
    return f"“{resposta}”" if resposta else ""


def _legivel(campo: str, valor) -> str:
    if valor is None:
        return "não informado"
    if isinstance(valor, bool):
        return "sim" if valor else "não"
    if campo == "estagio":
        return ROTULO_ESTAGIO.get(valor, valor)
    return str(valor)


def _bloco_pratica(posicao: int, item: dict) -> list[str]:
    final = item["pontuacoes_finais"]
    calculo = (
        f"{final['impacto']} + {final['necessidade']} + {final['dependencia']} "
        f"+ (4 − {final['esforco']}) = {item['pontuacao']}"
    )
    linhas = [
        f"### {posicao}. {item['id']} {item['nome']} — {item['nivel']} ({item['pontuacao']})",
        "",
        " — ".join(filter(None, [f"**Situação:** {ROTULO_SITUACAO[item['situacao']]}", _citar(item["resposta"])])),
        "",
        f"**Justificativa:** {item['justificativa']}",
        "",
        f"**Orientação:** {item['orientacao']}",
        "",
        f"**Próxima ação:** {item['proxima_acao']}",
        "",
        f"**Cálculo:** I + N + D + (4 − E) = {calculo}",
    ]
    for ajuste in item["ajustes_aplicados"]:
        criterio = ACENTO.get(ajuste["criterio"], ajuste["criterio"])
        efeito = f"{ajuste['de']} → {ajuste['para']}"
        if ajuste["de"] == ajuste["para"]:
            efeito = f"{ajuste['de']} (sem efeito: já no {'máximo' if ajuste['de'] == LIMITE_MAX else 'mínimo'})"
        linhas.append(f"**Ajuste:** {ajuste['descricao']} — {criterio} {efeito}")

    for trecho in item.get("fundamentacao", []):
        linhas += ["", f"**Fundamentação:** “{trecho['texto']}”", f"   Fonte: {trecho['fonte']}"]

    linhas += ["", f"**Referências:** {'; '.join(item['referencias'])}", ""]
    return linhas


EXEMPLO = {
    # contexto
    "tipo_problema": "classificação",
    "tamanho_equipe": 3,
    "estagio": "concepcao",
    "dados_sensiveis": True,
    # campos de prática
    "objetivo": {
        "situacao": "suficiente",
        "resposta": "Prever quais alunos correm risco de evasão no semestre seguinte.",
    },
    "registro_decisoes": {"situacao": "inexistente", "resposta": "não temos"},
    "documentacao_dados": {"situacao": "insuficiente", "resposta": "só o README"},
    "problemas_limitacoes": {"situacao": "nao_verificado", "resposta": "não analisei se o banco tem alguma limitação"},
}


if __name__ == "__main__":
    # uv run nucleo.py [entrada.json] — sem argumento, roda o EXEMPLO.
    import json
    import sys
    from pathlib import Path

    entrada = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")) if len(sys.argv) > 1 else EXEMPLO
    base = carregar()
    print(render_registro(base, analisar(base, entrada)))
