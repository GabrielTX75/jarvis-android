import pytest

from jarvis.calc import calcular, formatar


@pytest.mark.parametrize("expressao, esperado", [
    ("2 mais 2 vezes 3", 8),
    ("25 por cento de 80", 20),
    ("raiz de 16", 4),
    ("(3 + 4) x 2", 14),
    ("2 elevado a 3", 8),
    ("-5 + 2", -3),
])
def test_calcula(expressao, esperado):
    assert calcular(expressao) == pytest.approx(esperado)


@pytest.mark.parametrize("expressao", ["1 / 0", "abc", "raiz de -1", "2 +", ""])
def test_entrada_invalida_devolve_none(expressao):
    assert calcular(expressao) is None


def test_formatar_usa_virgula():
    assert formatar(10 / 4) == "2,50"
    assert formatar(4.0) == "4"
