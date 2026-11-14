from pathlib import Path

import pytest

from jarvis.codigo import Gerador, alvo_do_pedido, caminho_seguro, extrair, limpar_cercas


@pytest.fixture(autouse=True)
def ia_configurada(monkeypatch):
    monkeypatch.setenv("JARVIS_IA_URL", "https://exemplo.test/v1")
    monkeypatch.setenv("JARVIS_IA_MODEL", "modelo-teste")


def _esperar(g: Gerador):
    if g._thread is not None:
        g._thread.join(5)


def _sequencia(*respostas):
    fila = list(respostas)

    def falsa(msgs, max_tokens=0):
        if not fila:
            return None
        return fila.pop(0)
    return falsa


def test_alvo_do_pedido():
    assert alvo_do_pedido("faz com 3 mil linhas") == 3000
    assert alvo_do_pedido("gera 500 linhas") == 500
    assert alvo_do_pedido("gera 1.500 linhas") == 1500
    assert alvo_do_pedido("gera 9999999 linhas") == 1_000_000
    assert alvo_do_pedido("um jogo simples") == 0


def test_extrai_varios_arquivos_e_linguagens():
    texto = ("=== ARQUIVO: index.html ===\n<h1>oi</h1>\n"
             "=== ARQUIVO: js/app.js ===\nconsole.log(1)\n")
    inicio, blocos = extrair(texto)
    assert inicio == ""
    assert blocos == [("index.html", "<h1>oi</h1>\n"), ("js/app.js", "console.log(1)\n")]


def test_caminho_nao_sai_da_pasta_do_projeto(tmp_path):
    projeto = tmp_path / "meu-projeto"
    destino = caminho_seguro(projeto, "../../etc/senha.txt")
    assert destino is not None
    assert destino.is_relative_to(projeto)
    assert caminho_seguro(projeto, "C:/Windows/x.txt").is_relative_to(projeto)


def test_limpa_cercas_de_markdown():
    assert limpar_cercas("```python\nx = 1\n```\n") == "x = 1\n"


def test_gera_projeto_com_varios_arquivos_ate_o_marcador(tmp_path):
    respostas = _sequencia(
        ("=== ARQUIVO: main.py ===\nprint(1)\n", "stop"),
        ("=== ARQUIVO: index.html ===\n<h1>oi</h1>\nFIM_DO_PROJETO", "stop"),
    )
    g = Gerador(tmp_path, chamar=respostas)
    assert g.iniciar("faz um site com script") == "Comecei a gerar o código."
    _esperar(g)
    projeto = Path(g.dados["projeto"])
    assert (projeto / "main.py").read_text(encoding="utf-8") == "print(1)\n"
    assert (projeto / "index.html").read_text(encoding="utf-8") == "<h1>oi</h1>\n"
    assert g.dados["estado"] == "concluido"
    assert g.listar()[0]["arquivos"] == 2


def test_erro_de_rede_nao_para_o_projeto(tmp_path):
    respostas = _sequencia(None, None, ("=== ARQUIVO: a.py ===\nx = 1\nFIM_DO_PROJETO", "stop"))
    g = Gerador(tmp_path, chamar=respostas, esperas=[0], max_falhas=5)
    g.iniciar("faz um script")
    _esperar(g)
    assert g.dados["estado"] == "concluido"
    assert (Path(g.dados["projeto"]) / "a.py").exists()


def test_desiste_so_depois_do_limite_de_falhas(tmp_path):
    g = Gerador(tmp_path, chamar=lambda msgs, max_tokens=0: None, esperas=[0], max_falhas=3)
    g.iniciar("faz um script")
    _esperar(g)
    assert g.dados["estado"] == "parado por erro na IA"


def test_para_ao_atingir_a_meta_de_linhas(tmp_path):
    g = Gerador(tmp_path, chamar=lambda msgs, max_tokens=0: ("=== ARQUIVO: a.txt ===\n" + "a\n" * 2, "stop"))
    g.iniciar("gera 4 linhas de texto")
    _esperar(g)
    assert g.dados["linhas"] == 4
    assert g.dados["estado"] == "concluido"
    assert g.listar()[0]["percentual"] == 100


def test_nao_apaga_arquivo_que_ja_existe(tmp_path):
    g = Gerador(tmp_path, chamar=_sequencia(("=== ARQUIVO: a.py ===\nnovo\nFIM_DO_PROJETO", "stop")))
    g.iniciar("faz script")
    _esperar(g)
    projeto = Path(g.dados["projeto"])
    g2 = Gerador(tmp_path, chamar=_sequencia())
    g2._aplicar(projeto, "=== ARQUIVO: a.py ===\nmais\n", "a.py")
    assert (projeto / "a.py").read_text(encoding="utf-8") == "novo\nmais\n"


def test_retoma_depois_de_reabrir(tmp_path):
    g1 = Gerador(tmp_path, chamar=_sequencia(("=== ARQUIVO: a.txt ===\n" + "a\n" * 4, "stop"), None),
                 esperas=[0], max_falhas=1)
    g1.iniciar("gera 8 linhas")
    _esperar(g1)
    assert g1.dados["linhas"] == 4

    g2 = Gerador(tmp_path, chamar=lambda msgs, max_tokens=0: ("b\n" * 4, "stop"))
    assert "parado por erro na IA" in g2.status()
    assert g2.iniciar(None) == "Comecei a gerar o código."
    _esperar(g2)
    assert g2.dados["linhas"] == 8


def test_respostas_vazias_param(tmp_path):
    g = Gerador(tmp_path, chamar=lambda msgs, max_tokens=0: ("```\n```", "stop"))
    g.iniciar("faz algo")
    _esperar(g)
    assert g.dados["estado"] == "parado sem novidades"


def test_sem_ia_configurada_avisa(tmp_path, monkeypatch):
    monkeypatch.delenv("JARVIS_IA_URL")
    g = Gerador(tmp_path)
    assert "Configure a IA" in g.iniciar("faz algo")
