"""Calculadora segura: entende contas, porcentagem e raiz, sem usar eval."""
import math
import re


class _Parser:
    def __init__(self, s: str):
        self.s = s
        self.i = 0

    def resolver(self) -> float:
        v = self._expr()
        if self.i != len(self.s):
            raise ValueError("sobrou texto")
        return v

    def _expr(self) -> float:
        v = self._termo()
        while self.i < len(self.s) and self.s[self.i] in "+-":
            op = self.s[self.i]
            self.i += 1
            r = self._termo()
            v = v + r if op == "+" else v - r
        return v

    def _termo(self) -> float:
        v = self._fator()
        while self.i < len(self.s) and self.s[self.i] in "*/":
            op = self.s[self.i]
            self.i += 1
            r = self._fator()
            v = v * r if op == "*" else v / r
        return v

    def _fator(self) -> float:
        base = self._unario()
        if self.i < len(self.s) and self.s[self.i] == "^":
            self.i += 1
            return base ** self._fator()
        return base

    def _unario(self) -> float:
        if self.i < len(self.s) and self.s[self.i] == "-":
            self.i += 1
            return -self._unario()
        return self._primario()

    def _primario(self) -> float:
        if self.s.startswith("sqrt(", self.i):
            self.i += 5
            v = self._expr()
            self._consumir(")")
            return math.sqrt(v)
        if self.i < len(self.s) and self.s[self.i] == "(":
            self.i += 1
            v = self._expr()
            self._consumir(")")
            return v
        inicio = self.i
        while self.i < len(self.s) and (self.s[self.i].isdigit() or self.s[self.i] == "."):
            self.i += 1
        if inicio == self.i:
            raise ValueError("número esperado")
        return float(self.s[inicio:self.i])

    def _consumir(self, c: str) -> None:
        if self.i < len(self.s) and self.s[self.i] == c:
            self.i += 1
        else:
            raise ValueError("faltou " + c)


def normalizar_expressao(texto: str) -> str:
    s = texto.lower()
    s = re.sub(r"raiz (quadrada )?de (\d+(?:[.,]\d+)?)",
               lambda m: "sqrt(" + m.group(2).replace(",", ".") + ")", s)
    s = re.sub(r"(\d+(?:[.,]\d+)?) ?(?:%|por cento) ?de (\d+(?:[.,]\d+)?)",
               lambda m: "(" + m.group(1).replace(",", ".") + "/100*" + m.group(2).replace(",", ".") + ")", s)
    for antigo, novo in [(" elevado a ", "^"), (" dividido por ", "/"), (" vezes ", "*"),
                         (" mais ", "+"), (" menos ", "-"), (" x ", "*")]:
        s = s.replace(antigo, novo)
    s = re.sub(r"(\d),(\d)", r"\1.\2", s)
    return s.replace(" ", "")


def calcular(expressao: str) -> float | None:
    """Devolve o resultado, ou None se a expressão não puder ser calculada."""
    try:
        valor = _Parser(normalizar_expressao(expressao)).resolver()
    except (ValueError, ZeroDivisionError, OverflowError):
        return None
    if math.isnan(valor) or math.isinf(valor):
        return None
    return valor


def formatar(valor: float) -> str:
    if valor == int(valor) and abs(valor) < 1e15:
        return str(int(valor))
    return f"{valor:.2f}".replace(".", ",")
