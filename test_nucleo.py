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

NEGACOES = [
    "não",
    "NÃO",
    "nao",
    "não temos",
    "não fazemos",
    "não fizemos",
    "não definimos",
    "não há",
    "não existe",
    "não possui",
    "não foi feito",
    "não sei",
    "ainda não",
    "ainda não fizemos",
    "por enquanto não",
    "até agora não fizemos",
    "no momento não temos",
    "nunca fizemos isso",
    "jamais foi registrado",
    "nenhum",
    "nenhuma",
    "nenhumas",
    "inexistente",
    "ausente",
]

VAZIOS = ["", "   ", "-", "--", "n/a", "N/A", "nada"]

CONTEUDOS = [
    "Prever quais alunos correm risco de evasão",
    "Sistema acadêmico da universidade, matrículas de 2019 a 2025",
    "Notion, uma página por decisão",
    "F1 acima de 0,80 na classe minoritária",
    "Ainda estamos coletando, mas já temos o esquema definido",
]

AMBIGUOS = [
    "não temos processo formal, mas registramos tudo no Notion",
    "não temos documentação escrita, usamos um README com origem e período",
    "não existe um documento único, porem cada tabela tem um dicionário de dados",
]


@pytest.mark.parametrize("texto", NEGACOES)
def test_negacao_vira_pendente(texto):
    assert estado_do_campo(texto) == "pendente"


@pytest.mark.parametrize("texto", VAZIOS)
def test_vazio_vira_pendente(texto):
    assert estado_do_campo(texto) == "pendente"


@pytest.mark.parametrize("texto", CONTEUDOS)
def test_conteudo_vira_atendida(texto):
    assert estado_do_campo(texto) == "atendida"


@pytest.mark.parametrize("texto", AMBIGUOS)
def test_nega_e_emenda_vira_indeterminada(texto):
    assert estado_do_campo(texto) == "indeterminada"


def test_booleanos_e_ausencia():
    assert estado_do_campo(True) == "atendida"
    assert estado_do_campo(False) == "pendente"
    assert estado_do_campo(None) == "indeterminada"


def test_campo_omitido_nao_vira_pendente():
    selecao = selecionar_praticas(BASE, {})
    assert selecao["pendentes"] == []
    assert len(selecao["indeterminadas"]) == len(BASE.praticas)
    assert all(p["pergunta"] for p in selecao["indeterminadas"])


def test_toda_pratica_cai_em_exatamente_um_estado():
    selecao = selecionar_praticas(BASE, {"objetivo": "prever evasão", "fonte_dados": "não temos"})
    total = sum(len(selecao[chave]) for chave in ("atendidas", "pendentes", "indeterminadas"))
    assert total == len(BASE.praticas)


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
    ("problemas_relatados", {"problemas_limitacoes": "muitos ausentes"}, {"problemas_limitacoes": "nenhum"}),
]


@pytest.mark.parametrize("id_ajuste, dispara, nao_dispara", AJUSTES)
def test_ajuste_dispara_so_na_condicao_certa(id_ajuste, dispara, nao_dispara):
    assert id_ajuste in {a["id"] for a in identificar_contexto(BASE, dispara)["ajustes"]}
    assert id_ajuste not in {a["id"] for a in identificar_contexto(BASE, nao_dispara)["ajustes"]}


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
    entrada = {"estagio": "concepcao", "tamanho_equipe": 2, "objetivo": "prever evasão", "requisitos": False}
    assert analisar(BASE, entrada) == analisar(BASE, entrada)


def test_rag_nao_altera_a_pontuacao():
    entrada = {"requisitos": False}
    sem = analisar(BASE, entrada)
    com = analisar(BASE, entrada, fundamentar=lambda ficha: [{"texto": "t", "fonte": "f.pdf, p. 1"}])
    assert [(i["id"], i["pontuacao"]) for i in sem["plano"]] == [(i["id"], i["pontuacao"]) for i in com["plano"]]
    assert com["plano"][0]["fundamentacao"] == [{"texto": "t", "fonte": "f.pdf, p. 1"}]


def test_registro_traz_as_secoes_e_o_calculo_aberto():
    entrada = {"estagio": "concepcao", "tamanho_equipe": 3, "objetivo": "prever evasão", "requisitos": False}
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
    entrada = {"estagio": "concepcao", "tamanho_equipe": 2, "requisitos": False, "registro_decisoes": False}
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
