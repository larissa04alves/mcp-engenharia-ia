"""Testes do carregamento e da validação da base de conhecimento."""

import copy
import json
from pathlib import Path

import pytest

from base import CRITERIOS, IDS_COMPLETOS, BaseInvalida, carregar

ARQUIVO = Path(__file__).parent / "praticas.json"
ORIGINAL = json.loads(ARQUIVO.read_text(encoding="utf-8"))


@pytest.fixture
def quebrar(tmp_path):
    def _quebrar(mutacao) -> list[str]:
        dados = copy.deepcopy(ORIGINAL)
        mutacao(dados)
        alvo = tmp_path / "praticas.json"
        alvo.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        with pytest.raises(BaseInvalida) as erro:
            carregar(alvo)
        return erro.value.problemas

    return _quebrar


def test_arquivo_real_carrega():
    base = carregar()
    assert base.completa
    assert [p["id"] for p in base.praticas] == list(IDS_COMPLETOS)
    assert len(base.ajustes) == 5


def test_indice_por_id():
    assert carregar().por_id["DD1"]["campo"] == "fonte_dados"


def test_toda_ficha_tem_os_campos_que_a_saida_usa():
    for pratica in carregar().praticas:
        for chave in ("descricao", "condicoes", "pergunta", "orientacao", "proxima_acao"):
            assert pratica[chave], f"{pratica['id']} — {chave} vazio"
        assert pratica["citacoes"]
        assert pratica["referencias"]


def test_referencias_vem_todas_da_pasta_literatura():
    # As citações do RAG e a lista de referências precisam falar da mesma bibliografia.
    for pratica in carregar().praticas:
        for referencia in pratica["referencias"]:
            assert referencia.endswith("[literatura/]"), f"{pratica['id']} — referência fora da pasta: {referencia}"


# validação das práticas


def test_acusa_todos_os_problemas_de_uma_vez(quebrar):
    def mutacao(dados):
        dados["praticas"][0]["pontuacoes"]["esforco"] = 5
        dados["praticas"][1]["id"] = dados["praticas"][0]["id"]
        del dados["praticas"][2]["orientacao"]
        dados["praticas"][3]["campo"] = dados["praticas"][0]["campo"]

    texto = "\n".join(quebrar(mutacao))
    assert "pontuacoes.esforco = 5 (esperado 1 a 3)" in texto
    assert "id repetido" in texto
    assert "orientacao ausente ou vazio" in texto
    assert "já é usado por" in texto
    assert "práticas ausentes: RP2" in texto


def test_mensagem_nomeia_a_pratica(quebrar):
    problemas = quebrar(
        lambda d: d["praticas"][3].__setitem__("pontuacoes", {**d["praticas"][3]["pontuacoes"], "impacto": 0})
    )
    assert problemas == ["RP4 — pontuacoes.impacto = 0 (esperado 1 a 3)"]


def test_grupo_desconhecido(quebrar):
    problemas = quebrar(lambda d: d["praticas"][0].__setitem__("grupo", "outro"))
    assert "grupo = 'outro'" in problemas[0]


def test_condicoes_incompletas(quebrar):
    problemas = quebrar(lambda d: d["praticas"][0]["condicoes"].pop("indeterminada"))
    assert problemas == ["RP1 — condicoes.indeterminada ausente ou vazio"]


def test_condicoes_exigem_um_texto_por_situacao(quebrar):
    problemas = quebrar(lambda d: d["praticas"][0]["condicoes"].pop("nao_verificado"))
    assert problemas == ["RP1 — condicoes.nao_verificado ausente ou vazio"]


def test_citacao_sem_pagina_valida(quebrar):
    problemas = quebrar(lambda d: d["praticas"][0]["citacoes"][0].__setitem__("pagina", 0))
    assert problemas == ["RP1 — citacoes[1].pagina = 0 (esperado inteiro a partir de 1)"]


def test_pratica_sem_citacao(quebrar):
    problemas = quebrar(lambda d: d["praticas"][0].__setitem__("citacoes", []))
    assert problemas == ["RP1 — citacoes deveria ser uma lista não vazia"]


def test_cobertura_completa_exige_as_doze(quebrar):
    problemas = quebrar(lambda d: d.__setitem__("praticas", d["praticas"][:4]))
    assert any("práticas ausentes" in p for p in problemas)


def test_cobertura_parcial_aceita_menos(tmp_path):
    dados = copy.deepcopy(ORIGINAL)
    dados["cobertura"] = "parcial"
    dados["praticas"] = dados["praticas"][:2]
    alvo = tmp_path / "praticas.json"
    alvo.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    assert len(carregar(alvo).praticas) == 2


# validação das faixas e ajustes


def test_faixas_com_buraco_e_sobreposicao(quebrar):
    problemas = quebrar(
        lambda d: d.__setitem__("faixas", [{"nivel": "A", "min": 4, "max": 7}, {"nivel": "B", "min": 7, "max": 10}])
    )
    texto = "\n".join(problemas)
    assert "sobrepõe as pontuações [7]" in texto
    assert "sem faixa: [11, 12]" in texto


def test_ajuste_com_criterio_inexistente(quebrar):
    problemas = quebrar(lambda d: d["ajustes"][0].__setitem__("criterio", "velocidade"))
    assert "criterio = 'velocidade'" in problemas[0]


def test_ajuste_com_delta_zero(quebrar):
    problemas = quebrar(lambda d: d["ajustes"][0].__setitem__("delta", 0))
    assert "delta = 0" in problemas[0]


def test_ajuste_com_dois_operadores(quebrar):
    problemas = quebrar(lambda d: d["ajustes"][0].__setitem__("quando", {"campo": "estagio", "igual": "x", "ate": 3}))
    assert "exatamente um de igual, ate, preenchido" in problemas[0]


def test_ajuste_com_alvo_invalido(quebrar):
    problemas = quebrar(lambda d: d["ajustes"][0].__setitem__("alvo", {"grupo": "inexistente"}))
    assert "alvo.grupo = 'inexistente'" in problemas[0]


def test_ajuste_apontando_para_id_que_nao_existe(quebrar):
    problemas = quebrar(lambda d: d["ajustes"][3].__setitem__("alvo", {"ids": ["DD1", "ZZ9"]}))
    assert "alvo.ids desconhecido(s): ZZ9" in problemas[0]


# validação do arquivo


def test_json_malformado_aponta_linha_e_coluna(tmp_path):
    alvo = tmp_path / "praticas.json"
    alvo.write_text('{"versao": "1.0",,}', encoding="utf-8")
    with pytest.raises(BaseInvalida) as erro:
        carregar(alvo)
    assert "JSON malformado na linha 1, coluna 18" in erro.value.problemas[0]


def test_arquivo_inexistente(tmp_path):
    with pytest.raises(BaseInvalida) as erro:
        carregar(tmp_path / "nao_existe.json")
    assert "arquivo não encontrado" in erro.value.problemas[0]


def test_chave_de_topo_ausente(quebrar):
    problemas = quebrar(lambda d: d.pop("faixas"))
    assert problemas == ["chave de topo ausente: faixas"]


def test_criterios_precisam_ser_os_quatro(quebrar):
    problemas = quebrar(lambda d: d["criterios"].pop("esforco"))
    assert f"criterios deveria ter exatamente {', '.join(CRITERIOS)}" in problemas[0]
