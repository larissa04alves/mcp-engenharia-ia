"""Testes da consulta ao índice, sem ChromaDB real."""

import rag
from rag import LIMIAR, MAX_CARACTERES, Trecho, _truncar, buscar


def test_truncar_corta_em_espaco_e_marca():
    texto = "palavra " * 100
    truncado = _truncar(texto)
    assert len(truncado) <= MAX_CARACTERES + 1
    assert truncado.endswith("palavra…")
    assert _truncar("curto") == "curto"


def test_fonte_traz_arquivo_e_pagina():
    assert Trecho("t", "artigo.pdf", 7, 0.3).fonte() == "artigo.pdf, p. 7"


class ColecaoFalsa:
    def query(self, query_texts, n_results):
        return {
            "documents": [["perto do assunto", "longe do assunto"]],
            "metadatas": [[{"arquivo": "a.pdf", "pagina": 3}, {"arquivo": "b.pdf", "pagina": 1}]],
            "distances": [[LIMIAR - 0.1, LIMIAR + 0.1]],
        }


def test_buscar_descarta_trechos_acima_do_limiar(monkeypatch):
    monkeypatch.setattr(rag, "_colecao", ColecaoFalsa)
    trechos = buscar(["qualquer termo"])
    assert [t.fonte() for t in trechos] == ["a.pdf, p. 3"]
