import json

from jarvis import config
from jarvis.configurar import configurar


def test_grava_arquivo_sem_imprimir_segredo(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_PASTA", str(tmp_path))
    comuns = iter([
        "https://exemplo.test/v1/chat/completions",
        "modelo-x",
        "",  # busca_url pulada
    ])
    segredos = iter(["chave-secreta-123", ""])
    mensagem = configurar(perguntar=lambda texto: next(comuns), esconder=lambda texto: next(segredos))

    dados = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert dados["ia_url"] == "https://exemplo.test/v1/chat/completions"
    assert dados["ia_modelo"] == "modelo-x"
    assert dados["ia_chave"] == "chave-secreta-123"
    assert "chave-secreta-123" not in mensagem
    assert config.valor("ia_chave") == "chave-secreta-123"


def test_enter_mantem_valor_salvo(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_PASTA", str(tmp_path))
    (tmp_path / "config.json").write_text(json.dumps({"ia_url": "https://antigo.test/v1", "ia_chave": "antiga"}), encoding="utf-8")
    configurar(perguntar=lambda texto: "", esconder=lambda texto: "")
    dados = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert dados["ia_url"] == "https://antigo.test/v1"
    assert dados["ia_chave"] == "antiga"
