import pytest


@pytest.fixture(autouse=True)
def pasta_isolada(tmp_path, monkeypatch):
    """Cada teste usa uma pasta própria, para não ler o config.json de quem roda os testes."""
    monkeypatch.setenv("JARVIS_PASTA", str(tmp_path / "JARVIS"))
    for nome in ["JARVIS_IA_URL", "JARVIS_IA_MODEL", "JARVIS_IA_KEY", "JARVIS_BUSCA_URL", "JARVIS_BUSCA_TOKEN"]:
        monkeypatch.delenv(nome, raising=False)
