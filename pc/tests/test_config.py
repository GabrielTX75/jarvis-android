import json

from jarvis import config
from jarvis.ferramentas import pasta_dados
from jarvis.ia import chamar, configurado


def _gravar(pasta, dados):
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "config.json").write_text(json.dumps(dados), encoding="utf-8")


def test_le_do_arquivo(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_PASTA", str(tmp_path))
    _gravar(tmp_path, {"ia_url": "https://exemplo.test/v1/chat/completions", "ia_modelo": "m1", "ia_chave": "k1"})
    assert config.valor("ia_url") == "https://exemplo.test/v1/chat/completions"
    assert config.valor("ia_modelo") == "m1"
    assert configurado() is True


def test_variavel_de_ambiente_tem_prioridade(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_PASTA", str(tmp_path))
    _gravar(tmp_path, {"ia_url": "https://arquivo.test/v1"})
    monkeypatch.setenv("JARVIS_IA_URL", "https://ambiente.test/v1")
    assert config.valor("ia_url") == "https://ambiente.test/v1"


def test_sem_arquivo_nem_variavel(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_PASTA", str(tmp_path))
    assert config.valor("ia_url") == ""
    assert configurado() is False
    assert chamar([{"role": "user", "content": "oi"}]) is None


def test_arquivo_invalido_nao_quebra(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_PASTA", str(tmp_path))
    (tmp_path / "config.json").write_text("{não é json", encoding="utf-8")
    assert config.valor("ia_url") == ""


def test_pasta_padrao_e_jarvis_na_home(monkeypatch):
    monkeypatch.delenv("JARVIS_PASTA", raising=False)
    assert pasta_dados().name == "JARVIS"
