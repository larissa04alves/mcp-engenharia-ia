# Consulta o índice da literatura. Fundamenta a orientação das práticas

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import chromadb
from chromadb.config import Settings

PASTA_INDICE = Path(__file__).parent / "indice"
COLECAO = "literatura"

LIMIAR = 0.45
MAX_TRECHOS = 2
MAX_CARACTERES = 400

# O ChromaDB avisa no stderr coisas que não interessam a quem usa o servidor.
logging.getLogger("chromadb").setLevel(logging.ERROR)


@dataclass(frozen=True)
class Trecho:
    texto: str
    arquivo: str
    pagina: int
    distancia: float

    def fonte(self) -> str:
        return f"{self.arquivo}, p. {self.pagina}"


def _cliente() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(path=str(PASTA_INDICE), settings=Settings(anonymized_telemetry=False))


@cache
def _colecao() -> chromadb.Collection:
    # Aberta uma vez por processo: o servidor consulta várias práticas por chamada.
    return _cliente().get_collection(COLECAO)


def recriar_colecao() -> chromadb.Collection:
    # Apaga e recria a coleção: indexar duas vezes dá o mesmo índice.
    cliente = _cliente()
    if COLECAO in [c.name for c in cliente.list_collections()]:
        cliente.delete_collection(COLECAO)
    return cliente.create_collection(COLECAO, metadata={"hnsw:space": "cosine"})


def indice_disponivel() -> bool:
    if not PASTA_INDICE.exists():
        return False
    try:
        return _cliente().get_collection(COLECAO).count() > 0
    except Exception:
        return False


def _truncar(texto: str) -> str:
    if len(texto) <= MAX_CARACTERES:
        return texto
    corte = texto[:MAX_CARACTERES].rsplit(" ", 1)[0]
    return corte + "…"


def buscar(termos_busca: list[str], k: int = MAX_TRECHOS) -> list[Trecho]:
    # Até k trechos abaixo do limiar. Lista vazia é resposta válida
    resultado = _colecao().query(query_texts=[" ".join(termos_busca)], n_results=k)
    return [
        Trecho(_truncar(texto), meta["arquivo"], meta["pagina"], distancia)
        for texto, meta, distancia in zip(
            resultado["documents"][0], resultado["metadatas"][0], resultado["distances"][0]
        )
        if distancia <= LIMIAR
    ]


if __name__ == "__main__":
    # Roda a busca de cada prática da base e mostra o que volta
    from base import carregar

    for pratica in carregar().praticas:
        trechos = buscar(pratica["termos_busca"])
        print(f"\n{pratica['id']}  {pratica['nome']}")
        print(f"     termos: {', '.join(pratica['termos_busca'])}")
        if not trechos:
            print("     (nenhum trecho abaixo do limiar)")
        for t in trechos:
            print(f"     {t.distancia:.2f}  {t.fonte()}\n           {t.texto[:160]}")
