from jarvis.busca import buscar
from jarvis.ia import chamar, configurado


def test_ia_sem_configuracao(monkeypatch):
    monkeypatch.delenv("JARVIS_IA_URL", raising=False)
    assert configurado() is False
    assert chamar([{"role": "user", "content": "oi"}]) is None


def test_busca_sem_configuracao(monkeypatch):
    monkeypatch.delenv("JARVIS_BUSCA_URL", raising=False)
    monkeypatch.delenv("JARVIS_BUSCA_TOKEN", raising=False)
    assert buscar("algo").startswith("Configure")


def test_busca_recusa_url_sem_https(monkeypatch):
    monkeypatch.setenv("JARVIS_BUSCA_URL", "http://exemplo.test")
    monkeypatch.setenv("JARVIS_BUSCA_TOKEN", "x")
    assert buscar("algo").startswith("Configure")
