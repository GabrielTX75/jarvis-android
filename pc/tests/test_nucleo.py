from jarvis.codigo import Gerador
from jarvis.nucleo import Nucleo


def _nucleo(tmp_path):
    return Nucleo(pasta=tmp_path, downloads=tmp_path / "dl",
                  gerador=Gerador(tmp_path, chamar=lambda *a, **k: None), aviso=lambda m: None)


def test_calcula_pela_frase(tmp_path):
    assert _nucleo(tmp_path).processar("quanto é 2 mais 2") == ("4.", False)


def test_sair_encerra(tmp_path):
    assert _nucleo(tmp_path).processar("sair") == ("Até logo.", True)


def test_sem_regra_e_sem_ia(tmp_path, monkeypatch):
    monkeypatch.delenv("JARVIS_IA_URL", raising=False)
    resposta, encerrar = _nucleo(tmp_path).processar("oi, tudo bem?")
    assert resposta.startswith("Não entendi")
    assert encerrar is False


def test_pesquisa_sem_servidor_configurado(tmp_path, monkeypatch):
    monkeypatch.delenv("JARVIS_BUSCA_URL", raising=False)
    monkeypatch.delenv("JARVIS_BUSCA_TOKEN", raising=False)
    resposta, _ = _nucleo(tmp_path).processar("pesquisa receita de bolo")
    assert resposta.startswith("Configure")


def test_ia_responde_em_json_executa_acao(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_IA_URL", "https://exemplo.test/v1")
    monkeypatch.setattr("jarvis.nucleo.ia.chamar",
                        lambda msgs, max_tokens=0: ('{"acao": "calcular", "args": {"expressao": "3 vezes 3"}}', "stop"))
    assert _nucleo(tmp_path).processar("quanto dá três vezes três, pensando bem") == ("9.", False)
