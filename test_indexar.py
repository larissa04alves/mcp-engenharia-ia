"""Testes da leitura e divisão da literatura."""

from indexar import SOBREPOSICAO, TAMANHO_PEDACO, TITULO_REFERENCIAS, _dividir, _limpar, _paginas


def test_limpar_junta_hifenacao_e_espacos():
    assert _limpar("machine learn-\ning  systems\n\nare​ hard") == "machine learning systems are hard"


def test_texto_curto_vira_um_pedaco():
    assert _dividir("Frase única.") == ["Frase única."]


def test_pedacos_respeitam_tamanho_e_sobrepoem():
    texto = " ".join(f"Frase número {n} do texto de exemplo." for n in range(200))
    pedacos = _dividir(texto)

    assert len(pedacos) > 1
    assert all(len(p) <= TAMANHO_PEDACO for p in pedacos)
    assert all(p.endswith(".") for p in pedacos[:-1])  # cortou em fim de frase
    assert pedacos[0][-SOBREPOSICAO:].split(" ", 1)[1] in pedacos[1]  # o começo do próximo repete o fim do anterior
    assert texto.endswith(pedacos[-1])


def test_pedacos_nao_cortam_palavra_no_meio():
    palavras = [f"palavra{n}" for n in range(400)]
    texto = " ".join(palavras)  # sem ponto final: força o corte por espaço
    vocabulario = set(palavras)

    pedacos = _dividir(texto)

    assert len(pedacos) > 1
    for pedaco in pedacos:
        assert set(pedaco.split(" ")) <= vocabulario, pedaco[:40]


def test_titulo_de_referencias_em_linha_propria():
    for titulo in ("References", "REFERENCES", "7. References", "Bibliography", "Referências Bibliográficas"):
        assert TITULO_REFERENCIAS.search(f"corpo\n{titulo}\n[1] Alguém"), titulo
    assert not TITULO_REFERENCIAS.search("see the references in section 7 for details")


def test_paginas_param_na_secao_de_referencias(tmp_path):
    arquivo = tmp_path / "artigo.md"
    arquivo.write_text("Introdução.\n\nMétodo.\n\nReferences\n\n[1] Alguém (2020).", encoding="utf-8")

    paginas = _paginas(arquivo)

    assert len(paginas) == 1
    numero, texto = paginas[0]
    assert numero == 1
    assert "Método." in texto
    assert "Alguém" not in texto
