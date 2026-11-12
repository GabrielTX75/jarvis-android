from pathlib import Path

import pytest

from jarvis.codigo import Gerador, alvo_do_pedido, limpar_parte, processar_resposta


@pytest.fixture(autouse=True)
def ia_configurada(monkeypatch):
    monkeypatch.setenv("JARVIS_IA_URL", "https://exemplo.test/v1")
    monkeypatch.setenv("JARVIS_IA_MODEL", "modelo-teste")


def _esperar(g: Gerador):
    if g._thread is not None:
        g._thread.join(5)


def test_alvo_do_pedido():
    assert alvo_do_pedido("faz com 3 mil linhas") == 3000
    assert alvo_do_pedido("gera 500 linhas") == 500
    assert alvo_do_pedido("gera 1.500 linhas") == 1500
    assert alvo_do_pedido("gera 5 milhões de linhas") == 0
    assert alvo_do_pedido("gera 9999999 linhas") == 1_000_000
    assert alvo_do_pedido("um jogo simples") == 0


def test_limpar_cercas_de_markdown():
    assert limpar_parte("```python\nx = 1\n```") == "x = 1\n"


def test_marcador_de_fim_e_removido():
    assert processar_resposta("print(1)\nFIM_DO_CODIGO") == ("print(1)\n", True)
    assert processar_resposta("print(1)\n") == ("print(1)\n", False)


def test_gera_ate_o_marcador(tmp_path):
    respostas = iter([("linha1\nlinha2\n", "stop"), ("linha3\nFIM_DO_CODIGO", "stop")])
    g = Gerador(tmp_path, chamar=lambda msgs, max_tokens=0: next(respostas))
    assert g.iniciar("faz um script") == "Comecei a gerar o código."
    _esperar(g)
    assert Path(g.dados["arquivo"]).read_text(encoding="utf-8") == "linha1\nlinha2\nlinha3\n"
    assert g.dados["estado"] == "concluido"
    assert g.listar()[0]["pronto"] is True


def test_para_ao_atingir_a_meta_de_linhas(tmp_path):
    g = Gerador(tmp_path, chamar=lambda msgs, max_tokens=0: ("a\n" * 4, "stop"))
    g.iniciar("gera 12 linhas de código")
    _esperar(g)
    assert g.dados["linhas"] == 12
    assert g.dados["estado"] == "concluido"
    assert g.listar()[0]["percentual"] == 100
    assert "12 linhas de 12 linhas, 100 por cento" in g.status()


def test_erro_da_ia_para_e_guarda_o_que_ja_foi_escrito(tmp_path):
    chamadas = iter([("a\n" * 4, "stop"), None])
    g = Gerador(tmp_path, chamar=lambda msgs, max_tokens=0: next(chamadas))
    g.iniciar("gera 8 linhas")
    _esperar(g)
    assert g.dados["estado"] == "parado por erro na IA"
    assert g.dados["linhas"] == 4


def test_retoma_depois_de_reabrir(tmp_path):
    chamadas = iter([("a\n" * 4, "stop"), None])
    g1 = Gerador(tmp_path, chamar=lambda msgs, max_tokens=0: next(chamadas))
    g1.iniciar("gera 8 linhas")
    _esperar(g1)

    g2 = Gerador(tmp_path, chamar=lambda msgs, max_tokens=0: ("a\n" * 4, "stop"))
    assert "parado por erro na IA" in g2.status()
    assert g2.iniciar(None) == "Comecei a gerar o código."
    _esperar(g2)
    assert g2.dados["linhas"] == 8


def test_respostas_vazias_param(tmp_path):
    g = Gerador(tmp_path, chamar=lambda msgs, max_tokens=0: ("```\n```", "stop"))
    g.iniciar("faz algo")
    _esperar(g)
    assert g.dados["estado"] == "parado por respostas vazias"


def test_sem_ia_configurada_avisa(tmp_path, monkeypatch):
    monkeypatch.delenv("JARVIS_IA_URL")
    g = Gerador(tmp_path)
    assert "Configure a IA" in g.iniciar("faz algo")
