"""Carrega e valida a base de conhecimento (praticas.json)."""

import json
from pathlib import Path

ARQUIVO = Path(__file__).parent / "praticas.json"

CRITERIOS = ("impacto", "necessidade", "dependencia", "esforco")
GRUPOS = ("requisitos_planejamento", "dados_documentacao")
IDS_COMPLETOS = tuple(f"RP{n}" for n in range(1, 7)) + tuple(f"DD{n}" for n in range(1, 7))

CAMPOS_CONTEXTO = ("tipo_problema", "tamanho_equipe", "estagio", "dados_sensiveis")

CHAVES_TOPO = ("versao", "cobertura", "criterios", "escala", "formula", "faixas", "ajustes", "praticas")
TEXTOS_PRATICA = ("id", "grupo", "nome", "campo", "descricao", "pergunta", "orientacao", "proxima_acao")
SITUACOES = ("suficiente", "insuficiente", "inexistente", "nao_verificado")
CONDICOES = (*SITUACOES, "indeterminada")
LISTAS_PRATICA = ("referencias",)

OPERADORES = ("igual", "ate", "preenchido")
SELETORES = ("grupo", "ids", "documental_extensa")

PONTUACAO_MIN, PONTUACAO_MAX = 4, 12


class BaseInvalida(Exception):
    """Reúne todos os problemas encontrados na validação, para acusá-los de uma vez."""

    def __init__(self, problemas: list[str]):
        self.problemas = problemas
        super().__init__(str(self))

    def __str__(self) -> str:
        cabecalho = f"praticas.json inválido ({len(self.problemas)} problema(s)):"
        return "\n".join([cabecalho, *(f"  {p}" for p in self.problemas)])


class Base:
    """Base de conhecimento já validada, com índice por id."""

    def __init__(self, dados: dict):
        self.versao: str = dados["versao"]
        self.completa: bool = dados["cobertura"] == "completa"
        self.criterios: dict[str, str] = dados["criterios"]
        self.escala: dict[str, str] = dados["escala"]
        self.formula: str = dados["formula"]
        self.faixas: list[dict] = dados["faixas"]
        self.ajustes: list[dict] = dados["ajustes"]
        self.praticas: list[dict] = dados["praticas"]

        self.por_id = {p["id"]: p for p in self.praticas}

    def nivel(self, pontuacao: int) -> str:
        for faixa in self.faixas:
            if faixa["min"] <= pontuacao <= faixa["max"]:
                return faixa["nivel"]
        raise ValueError(f"pontuação {pontuacao} fora de todas as faixas")


def carregar(caminho: Path = ARQUIVO) -> Base:
    """Lê, valida e devolve a base. Levanta BaseInvalida com todos os problemas."""
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise BaseInvalida([f"arquivo não encontrado: {caminho}"]) from None
    except json.JSONDecodeError as erro:
        raise BaseInvalida([f"JSON malformado na linha {erro.lineno}, coluna {erro.colno}: {erro.msg}"]) from None

    if problemas := _validar(dados):
        raise BaseInvalida(problemas)
    return Base(dados)


def _texto(valor) -> bool:
    return isinstance(valor, str) and valor.strip() != ""


def _lista_de_texto(valor) -> bool:
    return isinstance(valor, list) and bool(valor) and all(_texto(item) for item in valor)


def _validar(dados) -> list[str]:
    problemas: list[str] = []

    if not isinstance(dados, dict):
        return ["a raiz do arquivo deveria ser um objeto"]

    if faltando := [c for c in CHAVES_TOPO if c not in dados]:
        return [f"chave de topo ausente: {c}" for c in faltando]

    if dados["cobertura"] not in ("parcial", "completa"):
        problemas.append(f'cobertura = {dados["cobertura"]!r} (esperado "parcial" ou "completa")')
    completa = dados["cobertura"] == "completa"

    if set(dados["criterios"]) != set(CRITERIOS):
        problemas.append(f"criterios deveria ter exatamente {', '.join(CRITERIOS)}")
    if set(dados["escala"]) != {"1", "2", "3"}:
        problemas.append('escala deveria ter exatamente as chaves "1", "2" e "3"')

    problemas += _validar_faixas(dados["faixas"])
    problemas += _validar_praticas(dados["praticas"], completa)

    campos = {p["campo"] for p in dados["praticas"] if isinstance(p, dict) and _texto(p.get("campo"))}
    ids = {p["id"] for p in dados["praticas"] if isinstance(p, dict) and _texto(p.get("id"))}
    problemas += _validar_ajustes(dados["ajustes"], campos, ids, completa)

    return problemas


def _validar_faixas(faixas) -> list[str]:
    """As faixas precisam cobrir todas as pontuações possíveis, sem sobreposição."""
    if not isinstance(faixas, list) or not faixas:
        return ["faixas deveria ser uma lista não vazia"]

    problemas = []
    coberto: set[int] = set()
    for faixa in faixas:
        if not (isinstance(faixa, dict) and _texto(faixa.get("nivel"))):
            problemas.append("faixas — item sem nivel")
            continue
        minimo, maximo = faixa.get("min"), faixa.get("max")
        if not (isinstance(minimo, int) and isinstance(maximo, int) and minimo <= maximo):
            problemas.append(f"faixa {faixa['nivel']} — min/max inválidos ({minimo}, {maximo})")
            continue
        intervalo = set(range(minimo, maximo + 1))
        if sobreposto := coberto & intervalo:
            problemas.append(f"faixa {faixa['nivel']} — sobrepõe as pontuações {sorted(sobreposto)}")
        coberto |= intervalo

    esperado = set(range(PONTUACAO_MIN, PONTUACAO_MAX + 1))
    if buracos := esperado - coberto:
        problemas.append(f"faixas — pontuações sem faixa: {sorted(buracos)}")
    if sobrando := coberto - esperado:
        problemas.append(f"faixas — pontuações fora do intervalo {PONTUACAO_MIN} a {PONTUACAO_MAX}: {sorted(sobrando)}")
    return problemas


def _validar_praticas(praticas, completa: bool) -> list[str]:
    if not isinstance(praticas, list) or not praticas:
        return ["praticas deveria ser uma lista não vazia"]

    problemas = []
    vistos_id: set[str] = set()
    vistos_campo: dict[str, str] = {}

    for posicao, pratica in enumerate(praticas, start=1):
        if not isinstance(pratica, dict):
            problemas.append(f"praticas[{posicao}] — deveria ser um objeto")
            continue

        onde = pratica["id"] if _texto(pratica.get("id")) else f"praticas[{posicao}]"

        for chave in TEXTOS_PRATICA:
            if not _texto(pratica.get(chave)):
                problemas.append(f"{onde} — {chave} ausente ou vazio")
        for chave in LISTAS_PRATICA:
            if not _lista_de_texto(pratica.get(chave)):
                problemas.append(f"{onde} — {chave} deveria ser uma lista não vazia de textos")

        problemas += _validar_citacoes(pratica.get("citacoes"), onde)

        if not isinstance(pratica.get("documental_extensa"), bool):
            problemas.append(f"{onde} — documental_extensa deveria ser true ou false")

        if pratica.get("grupo") not in GRUPOS:
            problemas.append(f"{onde} — grupo = {pratica.get('grupo')!r} (esperado um de {', '.join(GRUPOS)})")

        condicoes = pratica.get("condicoes")
        if not isinstance(condicoes, dict):
            problemas.append(f"{onde} — condicoes ausente")
        else:
            for chave in CONDICOES:
                if not _texto(condicoes.get(chave)):
                    problemas.append(f"{onde} — condicoes.{chave} ausente ou vazio")

        pontuacoes = pratica.get("pontuacoes")
        if not isinstance(pontuacoes, dict):
            problemas.append(f"{onde} — pontuacoes ausente")
        else:
            for criterio in CRITERIOS:
                valor = pontuacoes.get(criterio)
                if not (isinstance(valor, int) and not isinstance(valor, bool) and 1 <= valor <= 3):
                    problemas.append(f"{onde} — pontuacoes.{criterio} = {valor!r} (esperado 1 a 3)")
            if extras := set(pontuacoes) - set(CRITERIOS):
                problemas.append(f"{onde} — pontuacoes tem critério desconhecido: {', '.join(sorted(extras))}")

        if _texto(pratica.get("id")):
            if pratica["id"] in vistos_id:
                problemas.append(f"{onde} — id repetido")
            vistos_id.add(pratica["id"])

        if _texto(pratica.get("campo")):
            campo = pratica["campo"]
            if campo in vistos_campo:
                problemas.append(f'{onde} — campo "{campo}" já é usado por {vistos_campo[campo]}')
            else:
                vistos_campo[campo] = onde

    if completa:
        if faltando := [i for i in IDS_COMPLETOS if i not in vistos_id]:
            problemas.append(f'cobertura "completa" — práticas ausentes: {", ".join(faltando)}')
        if extras := vistos_id - set(IDS_COMPLETOS):
            problemas.append(f'cobertura "completa" — ids desconhecidos: {", ".join(sorted(extras))}')

    return problemas


def _validar_citacoes(citacoes, onde: str) -> list[str]:
    """Só a forma: se o trecho está mesmo na página citada, quem confere é o rag.py, contra o índice."""
    if not isinstance(citacoes, list) or not citacoes:
        return [f"{onde} — citacoes deveria ser uma lista não vazia"]

    problemas = []
    for posicao, citacao in enumerate(citacoes, start=1):
        if not isinstance(citacao, dict):
            problemas.append(f"{onde} — citacoes[{posicao}] deveria ser um objeto")
            continue
        for chave in ("arquivo", "trecho"):
            if not _texto(citacao.get(chave)):
                problemas.append(f"{onde} — citacoes[{posicao}].{chave} ausente ou vazio")
        pagina = citacao.get("pagina")
        if not (isinstance(pagina, int) and not isinstance(pagina, bool) and pagina >= 1):
            problemas.append(f"{onde} — citacoes[{posicao}].pagina = {pagina!r} (esperado inteiro a partir de 1)")
    return problemas


def _validar_ajustes(ajustes, campos: set[str], ids: set[str], completa: bool) -> list[str]:
    if not isinstance(ajustes, list):
        return ["ajustes deveria ser uma lista"]

    problemas = []
    vistos: set[str] = set()

    for posicao, ajuste in enumerate(ajustes, start=1):
        if not isinstance(ajuste, dict):
            problemas.append(f"ajustes[{posicao}] — deveria ser um objeto")
            continue

        onde = f"ajuste {ajuste['id']}" if _texto(ajuste.get("id")) else f"ajustes[{posicao}]"

        if not _texto(ajuste.get("descricao")):
            problemas.append(f"{onde} — descricao ausente ou vazia")
        if _texto(ajuste.get("id")):
            if ajuste["id"] in vistos:
                problemas.append(f"{onde} — id repetido")
            vistos.add(ajuste["id"])

        if ajuste.get("criterio") not in CRITERIOS:
            problemas.append(f"{onde} — criterio = {ajuste.get('criterio')!r} (esperado um de {', '.join(CRITERIOS)})")

        delta = ajuste.get("delta")
        if not (isinstance(delta, int) and not isinstance(delta, bool) and delta != 0):
            problemas.append(f"{onde} — delta = {delta!r} (esperado inteiro diferente de zero)")

        problemas += _validar_quando(ajuste.get("quando"), onde, campos, completa)
        problemas += _validar_alvo(ajuste.get("alvo"), onde, ids, completa)

    return problemas


def _validar_quando(quando, onde: str, campos: set[str], completa: bool) -> list[str]:
    if not isinstance(quando, dict):
        return [f"{onde} — quando ausente"]

    problemas = []
    campo = quando.get("campo")
    if not _texto(campo):
        problemas.append(f"{onde} — quando.campo ausente")
    elif completa and campo not in campos and campo not in CAMPOS_CONTEXTO:
        problemas.append(f'{onde} — quando.campo "{campo}" não é campo de prática nem de contexto')

    usados = [op for op in OPERADORES if op in quando]
    if len(usados) != 1:
        problemas.append(f"{onde} — quando deveria ter exatamente um de {', '.join(OPERADORES)} (tem {len(usados)})")
    elif usados[0] == "ate" and not isinstance(quando["ate"], int):
        problemas.append(f"{onde} — quando.ate = {quando['ate']!r} (esperado inteiro)")
    elif usados[0] == "preenchido" and not isinstance(quando["preenchido"], bool):
        problemas.append(f"{onde} — quando.preenchido = {quando['preenchido']!r} (esperado true ou false)")

    return problemas


def _validar_alvo(alvo, onde: str, ids: set[str], completa: bool) -> list[str]:
    if not isinstance(alvo, dict):
        return [f"{onde} — alvo ausente"]

    usados = [s for s in SELETORES if s in alvo]
    if len(usados) != 1:
        return [f"{onde} — alvo deveria ter exatamente um de {', '.join(SELETORES)} (tem {len(usados)})"]

    seletor = usados[0]
    if seletor == "grupo" and alvo["grupo"] not in GRUPOS:
        return [f"{onde} — alvo.grupo = {alvo['grupo']!r} (esperado um de {', '.join(GRUPOS)})"]
    if seletor == "documental_extensa" and not isinstance(alvo["documental_extensa"], bool):
        return [f"{onde} — alvo.documental_extensa deveria ser true ou false"]
    if seletor == "ids":
        if not _lista_de_texto(alvo["ids"]):
            return [f"{onde} — alvo.ids deveria ser uma lista não vazia de ids"]
        if completa and (desconhecidos := [i for i in alvo["ids"] if i not in ids]):
            return [f"{onde} — alvo.ids desconhecido(s): {', '.join(desconhecidos)}"]
    return []


if __name__ == "__main__":
    import sys

    try:
        base = carregar()
    except BaseInvalida as erro:
        print(erro, file=sys.stderr)
        raise SystemExit(1) from None

    cobertura = "completa" if base.completa else "parcial"
    print(f"praticas.json v{base.versao} — cobertura {cobertura}")
    print(f"{len(base.praticas)} prática(s), {len(base.ajustes)} ajuste(s), {len(base.faixas)} faixa(s)")
    for pratica in base.praticas:
        p = sum(pratica["pontuacoes"][c] for c in ("impacto", "necessidade", "dependencia"))
        p += 4 - pratica["pontuacoes"]["esforco"]
        print(f"  {pratica['id']:4} {p:>2}  {base.nivel(p):12} {pratica['nome']}")
