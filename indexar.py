# Lê a literatura, divide em pedaços e grava no índice vetorial (ChromaDB). Roda uma vez, fora do servidor.

from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

import rag

PASTA_LITERATURA = Path(__file__).parent / "literatura"
EXTENSOES = (".pdf", ".md", ".txt")

TAMANHO_PEDACO = 800
SOBREPOSICAO = 150
LOTE = 500  # quantos pedaços por chamada ao ChromaDB

logging.getLogger("pypdf").setLevel(logging.ERROR)

# titulo das referências, com ou sem número, com ou sem acento, com ou sem plural, em inglês ou português
TITULO_REFERENCIAS = re.compile(
    r"^\s*(\d+\.?\s*)?(references|bibliography|referências|referências bibliográficas)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _limpar(texto: str) -> str:
    texto = unicodedata.normalize("NFKC", texto)
    texto = texto.replace("\u200b", "")  # espaço invisível que alguns PDFs carregam
    texto = re.sub(r"(\w)-\n(\w)", r"\1\2", texto)
    return " ".join(texto.split())


def _paginas(arquivo: Path) -> list[tuple[int, str]]:
    # Devolve (número da página, texto bruto), parando na seção de referências.
    if arquivo.suffix == ".pdf":
        brutas = [pagina.extract_text() or "" for pagina in PdfReader(arquivo).pages]
    else:
        brutas = [arquivo.read_text(encoding="utf-8")]

    paginas = []
    for numero, texto in enumerate(brutas, start=1):
        if titulo := TITULO_REFERENCIAS.search(texto):
            paginas.append((numero, texto[: titulo.start()]))
            break
        paginas.append((numero, texto))
    return paginas


def _dividir(texto: str) -> list[str]:
    #divide o texto em pedaços de tamanho máximo TAMANHO_PEDACO, tentando cortar em pontos finais.
    pedacos = []
    inicio = 0
    while inicio < len(texto):
        fim = min(inicio + TAMANHO_PEDACO, len(texto))
        if fim < len(texto):
            ponto = texto.rfind(". ", inicio + TAMANHO_PEDACO // 2, fim)
            if ponto != -1:
                fim = ponto + 1
        pedacos.append(texto[inicio:fim].strip())
        if fim >= len(texto):
            break
        inicio = max(fim - SOBREPOSICAO, inicio + 1)
    return [p for p in pedacos if p]


def indexar() -> None:
    # indexa todos os arquivos de PASTA_LITERATURA no índice vetorial (ChromaDB).
    arquivos = sorted(a for a in PASTA_LITERATURA.iterdir() if a.suffix.lower() in EXTENSOES)
    if not arquivos:
        raise SystemExit(f"Nenhum arquivo {', '.join(EXTENSOES)} em {PASTA_LITERATURA}/")

    colecao = rag.recriar_colecao()

    documentos, metadados = [], []
    for arquivo in arquivos:
        antes = len(documentos)
        for numero, texto in _paginas(arquivo):
            for pedaco in _dividir(_limpar(texto)):
                documentos.append(pedaco)
                metadados.append({"arquivo": arquivo.name, "pagina": numero})
        gerados = len(documentos) - antes
        aviso = "sem texto extraível (PDF escaneado?)" if gerados == 0 else ""
        print(f"{gerados:5d}  {arquivo.name}{aviso}")

    print(f"\nGravando {len(documentos)} pedaços em {rag.PASTA_INDICE.name}/ ...")
    for i in range(0, len(documentos), LOTE):
        colecao.add(
            ids=[str(n) for n in range(i, i + len(documentos[i : i + LOTE]))],
            documents=documentos[i : i + LOTE],
            metadatas=metadados[i : i + LOTE],
        )
    print(f"Pronto: {len(arquivos)} arquivo(s), {colecao.count()} pedaços.")


if __name__ == "__main__":
    indexar()
