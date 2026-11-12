from jarvis.codigo import Gerador
from jarvis.nucleo import Nucleo


def test_ia_recebe_o_historico_da_conversa(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_IA_URL", "https://exemplo.test/v1/chat/completions")
    enviados = []

    def falsa(mensagens, max_tokens=0):
        enviados.append(mensagens)
        return ("Resposta " + str(len(enviados)), "stop")

    monkeypatch.setattr("jarvis.nucleo.ia.chamar", falsa)
    n = Nucleo(pasta=tmp_path, downloads=tmp_path / "dl", gerador=Gerador(tmp_path), aviso=lambda m: None)

    assert n.processar("qual a capital da França?") == ("Resposta 1", False)
    assert n.processar("e da Itália?") == ("Resposta 2", False)

    segunda = enviados[1]
    conteudos = [m["content"] for m in segunda]
    assert "qual a capital da França?" in conteudos
    assert "Resposta 1" in conteudos
    assert conteudos[-1] == "e da Itália?"


def test_esquece_a_conversa(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_IA_URL", "https://exemplo.test/v1/chat/completions")
    monkeypatch.setattr("jarvis.nucleo.ia.chamar", lambda m, max_tokens=0: ("ok", "stop"))
    n = Nucleo(pasta=tmp_path, downloads=tmp_path / "dl", gerador=Gerador(tmp_path), aviso=lambda m: None)
    n.processar("oi")
    assert len(n.historico) == 2
    assert n.processar("esquece a conversa") == ("Conversa esquecida. Podemos começar de novo.", False)
    assert len(n.historico) == 0


def test_falha_da_ia_nao_entra_no_historico(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_IA_URL", "https://exemplo.test/v1/chat/completions")
    monkeypatch.setattr("jarvis.nucleo.ia.chamar", lambda m, max_tokens=0: None)
    n = Nucleo(pasta=tmp_path, downloads=tmp_path / "dl", gerador=Gerador(tmp_path), aviso=lambda m: None)
    resposta, _ = n.processar("oi")
    assert resposta.startswith("Não consegui falar com a IA")
    assert len(n.historico) == 0
