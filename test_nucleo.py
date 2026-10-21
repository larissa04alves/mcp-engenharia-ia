"""Testes da regra de análise."""

from datetime import date

import pytest

from base import CAMPOS_CONTEXTO, carregar
from nucleo import (
    CONTEXTO,
    analisar,
    estado_do_campo,
    identificar_contexto,
    priorizar_praticas,
    render_registro,
    selecionar_praticas,
)

BASE = carregar()


def r(situacao: str, resposta: str | None = None) -> dict:
    """Resposta de um campo de prática, como o servidor a entrega ao núcleo."""
    return {"situacao": situacao} if resposta is None else {"situacao": situacao, "resposta": resposta}


@pytest.mark.parametrize(
    "situacao, estado",
    [
        ("suficiente", "atendida"),
        ("insuficiente", "pendente"),
        ("inexistente", "pendente"),
        ("nao_verificado", "pendente"),
    ],
)
def test_situacao_define_o_estado(situacao, estado):
    assert estado_do_campo(r(situacao, "qualquer texto")) == estado


@pytest.mark.parametrize("valor", [None, "não temos", "só o README", True, False, {"situacao": "talvez"}, {}])
def test_sem_situacao_valida_vira_indeterminada(valor):
    # O texto livre não decide mais nada: quem decide é a situacao.
    assert estado_do_campo(valor) == "indeterminada"


def test_campo_omitido_nao_vira_pendente():
    selecao = selecionar_praticas(BASE, {})
    assert selecao["pendentes"] == []
    assert len(selecao["indeterminadas"]) == len(BASE.praticas)
    assert all(p["pergunta"] for p in selecao["indeterminadas"])


def test_toda_pratica_cai_em_exatamente_um_estado():
    selecao = selecionar_praticas(BASE, {"objetivo": r("suficiente", "prever evasão"), "fonte_dados": r("inexistente")})
    total = sum(len(selecao[chave]) for chave in ("atendidas", "pendentes", "indeterminadas"))
    assert total == len(BASE.praticas)


def test_existe_mas_insuficiente_vai_para_o_plano_dizendo_que_existe():
    selecao = selecionar_praticas(BASE, {"documentacao_dados": r("insuficiente", "só o README")})
    [dd2] = selecao["pendentes"]
    assert dd2["id"] == "DD2"
    assert dd2["situacao"] == "insuficiente"
    assert dd2["resposta"] == "só o README"
    assert dd2["motivo"] == BASE.por_id["DD2"]["condicoes"]["insuficiente"]


def test_nao_verificado_vira_etapa_do_plano():
    entrada = {"problemas_limitacoes": r("nao_verificado", "não analisei se o banco tem limitação")}
    analise = analisar(BASE, entrada)

    assert [p["id"] for p in analise["selecao"]["a_verificar"]] == ["DD5"]
    [dd5] = analise["plano"]
    assert dd5["situacao"] == "nao_verificado"
    assert dd5["resposta"] == "não analisei se o banco tem limitação"
    assert dd5["proxima_acao"].startswith("Levantar o que ainda não foi verificado")
    assert dd5["proxima_acao"].endswith(
        "Depois: listar os problemas já percebidos nos dados e registrar a lista junto à documentação."
    )
    assert dd5["justificativa"].startswith(BASE.por_id["DD5"]["condicoes"]["nao_verificado"])


def test_so_nao_verificado_entra_em_a_verificar():
    entrada = {"requisitos": r("inexistente"), "documentacao_dados": r("insuficiente"), "objetivo": r("suficiente")}
    assert selecionar_praticas(BASE, entrada)["a_verificar"] == []


# verifica pontuações e níveis de prioridade

TABELA_3 = {
    "RP1": (3, 3, 3, 1, 12, "Essencial"),
    "RP2": (3, 3, 3, 2, 11, "Essencial"),
    "RP3": (3, 2, 2, 2, 9, "Essencial"),
    "RP4": (2, 2, 2, 2, 8, "Recomendada"),
    "RP5": (2, 2, 1, 1, 8, "Recomendada"),
    "RP6": (2, 1, 1, 2, 6, "Recomendada"),
    "DD1": (3, 3, 3, 1, 12, "Essencial"),
    "DD2": (3, 2, 2, 2, 9, "Essencial"),
    "DD3": (2, 2, 2, 2, 8, "Recomendada"),
    "DD4": (3, 3, 2, 3, 9, "Essencial"),
    "DD5": (3, 2, 1, 2, 8, "Recomendada"),
    "DD6": (1, 1, 1, 2, 5, "Evolução"),
}


@pytest.mark.parametrize("id_pratica", TABELA_3)
def test_pontuacoes_batem_com_a_tabela_3(id_pratica):
    impacto, necessidade, dependencia, esforco, pontuacao, nivel = TABELA_3[id_pratica]
    ficha = BASE.por_id[id_pratica]
    assert ficha["pontuacoes"] == {
        "impacto": impacto,
        "necessidade": necessidade,
        "dependencia": dependencia,
        "esforco": esforco,
    }

    sem_contexto = identificar_contexto(BASE, {})
    item = priorizar_praticas(BASE, [id_pratica], sem_contexto)[0]
    assert item["pontuacao"] == pontuacao == impacto + necessidade + dependencia + (4 - esforco)
    assert item["nivel"] == nivel


def test_faixas_cobrem_todas_as_pontuacoes_possiveis():
    assert [BASE.nivel(p) for p in range(9, 13)] == ["Essencial"] * 4
    assert [BASE.nivel(p) for p in range(6, 9)] == ["Recomendada"] * 3
    assert [BASE.nivel(p) for p in range(4, 6)] == ["Evolução"] * 2


# verifica ajustes e contexto


def test_campos_de_contexto_batem_com_a_base():
    assert tuple(CONTEXTO) == CAMPOS_CONTEXTO


def test_contexto_descarta_tipo_errado_sem_quebrar():
    atributos = identificar_contexto(BASE, {"tamanho_equipe": "três", "dados_sensiveis": "sim", "estagio": "MVP"})
    assert atributos["atributos"] == {
        "tipo_problema": None,
        "tamanho_equipe": None,
        "estagio": None,
        "dados_sensiveis": None,
    }


AJUSTES = [
    ("concepcao", {"estagio": "concepcao"}, {"estagio": "desenvolvimento"}),
    ("evolucao", {"estagio": "evolucao"}, {"estagio": "concepcao"}),
    ("equipe_pequena", {"tamanho_equipe": 3}, {"tamanho_equipe": 4}),
    ("dados_sensiveis", {"dados_sensiveis": True}, {"dados_sensiveis": False}),
    (
        "problemas_relatados",
        {"problemas_limitacoes": r("suficiente", "muitos ausentes")},
        {"problemas_limitacoes": r("inexistente", "nenhum")},
    ),
]


@pytest.mark.parametrize("id_ajuste, dispara, nao_dispara", AJUSTES)
def test_ajuste_dispara_so_na_condicao_certa(id_ajuste, dispara, nao_dispara):
    assert id_ajuste in {a["id"] for a in identificar_contexto(BASE, dispara)["ajustes"]}
    assert id_ajuste not in {a["id"] for a in identificar_contexto(BASE, nao_dispara)["ajustes"]}


@pytest.mark.parametrize(
    "situacao, dispara",
    [("suficiente", True), ("insuficiente", True), ("inexistente", False), ("nao_verificado", False)],
)
def test_problemas_relatados_exige_que_a_equipe_tenha_relatado_algo(situacao, dispara):
    ajustes = identificar_contexto(BASE, {"problemas_limitacoes": r(situacao, "texto")})["ajustes"]
    assert ("problemas_relatados" in {a["id"] for a in ajustes}) is dispara


def test_ajuste_atinge_apenas_o_alvo_declarado():
    contexto = identificar_contexto(BASE, {"estagio": "concepcao"})
    plano = priorizar_praticas(BASE, list(BASE.por_id), contexto)
    atingidas = {i["id"] for i in plano if i["ajustes_aplicados"]}
    assert atingidas == {p["id"] for p in BASE.praticas if p["grupo"] == "requisitos_planejamento"}


def test_criterio_ajustado_fica_limitado_entre_1_e_3():
    contexto = identificar_contexto(BASE, {"estagio": "evolucao", "dados_sensiveis": True})
    item = priorizar_praticas(BASE, ["DD1"], contexto)[0]
    assert item["pontuacoes_finais"]["impacto"] == 3
    assert item["pontuacao"] == 12


def test_intermediarios_do_calculo_sao_devolvidos():
    contexto = identificar_contexto(BASE, {"estagio": "concepcao", "tamanho_equipe": 2})
    item = priorizar_praticas(BASE, ["RP6"], contexto)[0]
    assert item["pontuacoes_referencia"] == BASE.por_id["RP6"]["pontuacoes"]
    assert {a["id"] for a in item["ajustes_aplicados"]} == {"concepcao", "equipe_pequena"}
    assert item["pontuacoes_finais"]["necessidade"] == 2  # 1 + 1
    assert item["pontuacoes_finais"]["esforco"] == 1  # 2 - 1
    assert item["pontuacao"] == 8


# verifica a saída do servidor


def test_ordem_por_pontuacao_decrescente_com_desempate_por_id():
    plano = priorizar_praticas(BASE, list(BASE.por_id), identificar_contexto(BASE, {}))
    chaves = [(-i["pontuacao"], i["id"]) for i in plano]
    assert chaves == sorted(chaves)


def test_mesma_entrada_produz_saida_identica():
    entrada = {
        "estagio": "concepcao",
        "tamanho_equipe": 2,
        "objetivo": r("suficiente", "prever evasão"),
        "requisitos": r("inexistente"),
    }
    assert analisar(BASE, entrada) == analisar(BASE, entrada)


def test_rag_nao_altera_a_pontuacao():
    entrada = {"requisitos": r("inexistente")}
    sem = analisar(BASE, entrada)
    com = analisar(BASE, entrada, fundamentar=lambda ficha: [{"texto": "t", "fonte": "f.pdf, p. 1"}])
    assert [(i["id"], i["pontuacao"]) for i in sem["plano"]] == [(i["id"], i["pontuacao"]) for i in com["plano"]]
    assert com["plano"][0]["fundamentacao"] == [{"texto": "t", "fonte": "f.pdf, p. 1"}]


def test_registro_traz_as_secoes_e_o_calculo_aberto():
    entrada = {
        "estagio": "concepcao",
        "tamanho_equipe": 3,
        "objetivo": r("suficiente", "prever evasão"),
        "requisitos": r("inexistente"),
    }
    registro = render_registro(BASE, analisar(BASE, entrada), quando=date(2026, 1, 15))

    for secao in (
        "## Contexto do projeto",
        "## Ajustes de contexto",
        "## Práticas atendidas",
        "## Plano de ação",
        "## Lacunas",
    ):
        assert secao in registro
    assert "15/01/2026" in registro
    assert "concepção" in registro
    assert "**Cálculo:**" in registro
    assert "RP2 Identificar os requisitos" in registro


def test_registro_marca_ajuste_sem_efeito():
    entrada = {
        "estagio": "concepcao",
        "tamanho_equipe": 2,
        "requisitos": r("inexistente"),
        "registro_decisoes": r("inexistente"),
    }
    registro = render_registro(BASE, analisar(BASE, entrada))
    assert "necessidade 3 (sem efeito: já no máximo)" in registro  # RP2 já tem necessidade 3
    assert "necessidade 1 → 2" in registro  # RP6 sobe de verdade
    assert "esforço 2 → 1" in registro


def test_justificativa_concorda_em_genero():
    contexto = identificar_contexto(BASE, {})
    justificativa = priorizar_praticas(BASE, ["RP1"], contexto)[0]["justificativa"]
    assert "impacto alto" in justificativa
    assert "necessidade alta" in justificativa
    assert "dependência alta" in justificativa


def test_registro_abre_com_os_pontos_a_verificar():
    entrada = {
        "problemas_limitacoes": r("nao_verificado", "não analisei se o banco tem limitação"),
        "requisitos": r("inexistente"),
    }
    registro = render_registro(BASE, analisar(BASE, entrada))
    secao = registro.index("## Pontos a verificar (1)")
    assert secao < registro.index("## Contexto do projeto")
    assert "**DD5 Identificar problemas e limitações** — “não analisei se o banco tem limitação”" in registro


def test_registro_sem_pontos_a_verificar_diz_nenhum():
    registro = render_registro(BASE, analisar(BASE, {"requisitos": r("inexistente")}))
    assert "## Pontos a verificar (0)\n\nNenhum." in registro


def test_registro_guarda_situacao_resposta_e_versao():
    entrada = {
        "objetivo": r("suficiente", "prever faltas para confirmar por WhatsApp"),
        "documentacao_dados": r("insuficiente", "só o README"),
    }
    registro = render_registro(BASE, analisar(BASE, entrada))
    assert f"Base de práticas v{BASE.versao}" in registro
    assert "“prever faltas para confirmar por WhatsApp”" in registro
    assert "**Situação:** existe, mas não é suficiente — “só o README”" in registro
