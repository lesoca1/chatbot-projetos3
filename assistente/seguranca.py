"""Detecção de sinais de risco. Roda antes da busca e tem prioridade sobre ela.

Segue o Conteúdo IV: dívida, dinheiro essencial, perda de controle ou tentativa
de recuperar prejuízos interrompem o fluxo normal e levam ao conteúdo de proteção.
"""

import re

from .texto import sem_acento

# Ordem importa: o primeiro grupo que casar define a resposta.
GATILHOS = [
    ("crise", [
        r"suicid", r"me matar", r"tirar (a )?minha (propria )?vida", r"nao quero mais viver",
        r"acabar com (a minha vida|tudo)", r"me machucar", r"sem saida",
    ]),
    ("divida_essencial", [
        r"(minha|minhas|tenho|estou com|to com|fiz|fazer) (uma )?dividas?", r"\bdevendo\b",
        r"emprestimo", r"emprestad", r"agiota", r"cheque especial",
        r"dinheiro (do|da|das|dos) (aluguel|mercado|comida|contas?|luz|escola|faculdade)",
        r"(aluguel|conta de luz|bolsa familia).{0,40}(aposta|apostar|bet)",
        r"(aposta|apostar|apostei|bet).{0,40}(aluguel|conta de luz|bolsa familia)",
        # Salário só é sinal de risco quando já foi usado; "quanto do salário posso gastar" é dúvida de orçamento.
        r"(usei|gastei|aposto|apostei|torrei|perdi|coloquei|joguei|botei) (o |meu |todo o |metade do )?(dinheiro do )?salario",
    ]),
    ("recuperar_perdas", [
        r"recuperar (o que |tudo o que |o dinheiro que )?(eu )?perdi", r"(quero|preciso|tenho que|vou) recuperar",
        r"como (eu )?recupero", r"recuperar (meu|minha|meus|minhas|o meu)", r"tirar o prejuizo",
        r"zerar o prejuizo", r"ganhar de volta",
    ]),
    ("perda_controle", [
        r"nao consigo (parar|controlar|largar|sair)", r"perdi o controle", r"perdi tudo",
        r"(?<!se )(sou|estou|to|fiquei) viciad", r"escondo (as )?apostas", r"minto sobre",
        r"nao paro de apostar",
    ]),
]

_COMPILADOS = [(nome, [re.compile(p) for p in padroes]) for nome, padroes in GATILHOS]


def detectar_risco(pergunta: str) -> str | None:
    """Devolve o nome do fluxo de segurança ou None."""
    texto = sem_acento(pergunta.lower())
    for nome, padroes in _COMPILADOS:
        if any(p.search(texto) for p in padroes):
            return nome
    return None
