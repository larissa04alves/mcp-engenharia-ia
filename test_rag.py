"""Testes da conferência das citações no índice, sem ChromaDB real."""

import rag
from rag import Trecho, citacoes_ausentes, localizar

PRIMEIRO = (
    "Datasets should be documented before use. Every dataset should be accompanied by a datasheet that "
    "documents its motivation, composition, collection process and recommended uses."
)
SEGUNDO = (
    "documents its motivation, composition, collection process and recommended uses. Datasheets also "
    "help dataset consumers decide whether the dataset suits their specific task."
)


class ColecaoFalsa:
    def get(self, where, include):
        arquivo, pagina = (
            condicao[chave] for condicao, chave in zip(where["$and"], ("arquivo", "pagina"), strict=True)
        )
        if (arquivo, pagina) != ("gebru.pdf", 3):
            return {"ids": [], "documents": []}
        return {"ids": ["11", "10"], "documents": [SEGUNDO, PRIMEIRO]}  # fora de ordem, como o get pode devolver


def citacao(trecho: str, arquivo: str = "gebru.pdf", pagina: int = 3) -> dict:
    return {"arquivo": arquivo, "pagina": pagina, "trecho": trecho}


def test_fonte_traz_arquivo_e_pagina():
    assert Trecho("t", "artigo.pdf", 7).fonte() == "artigo.pdf, p. 7"


def test_localiza_trecho_que_atravessa_dois_pedacos(monkeypatch):
    monkeypatch.setattr(rag, "_colecao", ColecaoFalsa)
    texto = (
        "Every dataset should be accompanied by a datasheet that documents its motivation, composition, "
        "collection process and recommended uses. Datasheets also help"
    )
    assert localizar(citacao(texto)) == Trecho(texto, "gebru.pdf", 3)


def test_localiza_ignorando_espaco_hifenizacao_caixa_e_ligadura(monkeypatch):
    monkeypatch.setattr(rag, "_colecao", ColecaoFalsa)
    # Como sai do pdftotext: quebra de linha, hifenização, caixa diferente e a ligadura "ﬁ" num caractere só.
    assert localizar(citacao("EVERY DATA-\nSET should be accompanied   by a datasheet"))
    assert localizar(citacao("whether the dataset suits their speciﬁc task."))


def test_nao_localiza_trecho_de_outra_pagina_ou_inventado(monkeypatch):
    monkeypatch.setattr(rag, "_colecao", ColecaoFalsa)
    assert localizar(citacao("Every dataset should be accompanied by a datasheet", pagina=4)) is None
    assert localizar(citacao("Every dataset must be audited by a lawyer")) is None


def test_citacoes_ausentes_nomeia_pratica_e_fonte(monkeypatch):
    monkeypatch.setattr(rag, "_colecao", ColecaoFalsa)
    praticas = [
        {"id": "DD2", "citacoes": [citacao("Every dataset should be accompanied by a datasheet")]},
        {"id": "RP6", "citacoes": [citacao("We will keep a collection of records", arquivo="nygard.pdf", pagina=2)]},
    ]
    assert citacoes_ausentes(praticas) == ["RP6 — nygard.pdf, p. 2: “We will keep a collection of records”"]
