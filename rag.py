"""Confere no índice da literatura as citações que fundamentam as práticas. Nunca altera a pontuação."""

import logging
import unicodedata
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import chromadb
from chromadb.config import Settings
from chromadb.errors import NotFoundError

PASTA_INDICE = Path(__file__).parent / "indice"
COLECAO = "literatura"

TAMANHO_EMENDA = 60

# O ChromaDB avisa no stderr coisas que não interessam a quem usa o servidor.
logging.getLogger("chromadb").setLevel(logging.ERROR)


@dataclass(frozen=True)
class Trecho:
    texto: str
    arquivo: str
    pagina: int

    def fonte(self) -> str:
        return f"{self.arquivo}, p. {self.pagina}"


@cache
def _cliente() -> chromadb.ClientAPI:
    """Um cliente por processo: o servidor consulta várias práticas por chamada."""
    return chromadb.PersistentClient(path=str(PASTA_INDICE), settings=Settings(anonymized_telemetry=False))


def _colecao() -> chromadb.Collection:
    return _cliente().get_collection(COLECAO)


def recriar_colecao() -> chromadb.Collection:
    """Apaga e recria a coleção, para que indexar duas vezes dê o mesmo índice."""
    cliente = _cliente()
    if COLECAO in [c.name for c in cliente.list_collections()]:
        cliente.delete_collection(COLECAO)
    return cliente.create_collection(COLECAO, metadata={"hnsw:space": "cosine"})


def indice_disponivel() -> bool:
    # Checar a pasta antes: abrir o cliente a criaria vazia.
    if not PASTA_INDICE.exists():
        return False
    try:
        return _colecao().count() > 0
    except NotFoundError:
        return False


def _comparavel(texto: str) -> str:
    """Só letras e números, em minúsculas: o PDF lido por outra ferramenta difere em espaço, hífen e ligadura."""
    return "".join(c for c in unicodedata.normalize("NFKC", texto).lower() if c.isalnum())


def _texto_da_pagina(arquivo: str, pagina: int) -> str:
    """Remonta a página a partir dos pedaços do índice, desfazendo a sobreposição entre um e o seguinte."""
    resultado = _colecao().get(where={"$and": [{"arquivo": arquivo}, {"pagina": pagina}]}, include=["documents"])
    pedacos = [
        texto
        for _, texto in sorted(zip(resultado["ids"], resultado["documents"], strict=True), key=lambda par: int(par[0]))
    ]

    texto = ""
    for pedaco in pedacos:
        emenda = texto.rfind(pedaco[:TAMANHO_EMENDA])
        texto = texto[:emenda] + pedaco if emenda != -1 else f"{texto} {pedaco}"
    return texto


def localizar(citacao: dict) -> Trecho | None:
    """O trecho curado, se ele está de fato na página citada do índice; None se não está."""
    pagina = _texto_da_pagina(citacao["arquivo"], citacao["pagina"])
    if _comparavel(citacao["trecho"]) not in _comparavel(pagina):
        return None
    return Trecho(citacao["trecho"], citacao["arquivo"], citacao["pagina"])


def citacoes_ausentes(praticas: list[dict]) -> list[str]:
    """As citações que o índice não confirma, uma linha por citação."""
    return [
        f"{pratica['id']} — {citacao['arquivo']}, p. {citacao['pagina']}: “{citacao['trecho'][:60]}”"
        for pratica in praticas
        for citacao in pratica["citacoes"]
        if localizar(citacao) is None
    ]


if __name__ == "__main__":
    from base import carregar

    ausentes = citacoes_ausentes(carregar().praticas)
    print("\n".join(ausentes) or "Todas as citações estão no índice.")
