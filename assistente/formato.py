"""Formatação de números no padrão brasileiro."""


def reais(v: float, casas: int = 2) -> str:
    texto = f"{abs(v):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("− " if v < -0.005 else "") + "R$ " + texto


def numero(v: float, casas: int = 0) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v: float, casas: int = 1) -> str:
    texto = f"{v * 100:.{casas}f}".replace(".", ",")
    if "," in texto:
        texto = texto.rstrip("0").rstrip(",")
    return texto + "%"


def anos_texto(anos: float) -> str:
    if anos < 1:
        meses = round(anos * 12)
        return f"{meses} {'mês' if meses == 1 else 'meses'}"
    inteiro = abs(anos - round(anos)) < 1e-9
    a = numero(anos, 0 if inteiro else 1)
    return f"{a} {'ano' if anos == 1 else 'anos'}"
