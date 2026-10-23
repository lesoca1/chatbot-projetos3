"""Mede a taxa de acerto do assistente em perguntas escritas como um apostador escreveria.

- perguntas_apostador.json: conjunto usado para guiar a ampliação da base.
- perguntas_novas.json: conjunto de controle, escrito depois e não usado para ajustar a base.

Executar na raiz do repositório: python docs/avaliacao/avaliar.py
"""

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from assistente.assistente import Assistente  # noqa: E402


CONJUNTOS = ["perguntas_apostador.json", "perguntas_novas.json"]


def avaliar(assistente: Assistente, arquivo: str = CONJUNTOS[0]) -> tuple[int, int, list[str]]:
    dados = json.loads((RAIZ / "docs" / "avaliacao" / arquivo).read_text(encoding="utf-8"))
    erros = []
    for pergunta, esperado in dados["perguntas"]:
        r = assistente.responder(pergunta)
        achado = r.registro["id"] if r.registro and r.tipo not in ("seguranca", "glossario") else r.tipo
        if achado != esperado:
            erros.append(f"{pergunta} -> {achado} (esperado {esperado})")
    return len(dados["perguntas"]) - len(erros), len(dados["perguntas"]), erros


if __name__ == "__main__":
    a = Assistente()
    for arquivo in CONJUNTOS:
        certas, total, erros = avaliar(a, arquivo)
        print(f"{arquivo}: {certas} de {total} certas ({certas / total:.0%})")
        for e in erros:
            print("  " + e)
