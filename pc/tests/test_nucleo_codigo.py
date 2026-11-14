from jarvis.codigo import Gerador
from jarvis.nucleo import Nucleo


def _nucleo(tmp_path, gerador=None, abrir=False):
    return Nucleo(pasta=tmp_path, downloads=tmp_path / "dl",
                  gerador=gerador or Gerador(tmp_path), aviso=lambda m: None, abrir_editor=abrir)


def test_testar_sem_codigo_avisa(tmp_path):
    assert _nucleo(tmp_path).processar("testa o código") == ("Não há código para testar. Peça um código primeiro.", False)


def test_gerar_projeto_abre_no_editor_e_testa(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_IA_URL", "https://exemplo.test/v1/chat/completions")
    abertos = []
    monkeypatch.setattr("jarvis.nucleo.editor.abrir_no_vscode", lambda pasta: abertos.append(pasta) or None)
    resposta_modelo = "=== ARQUIVO: main.py ===\nprint(1)\nFIM_DO_PROJETO"
    gerador = Gerador(tmp_path, chamar=lambda msgs, max_tokens=0: (resposta_modelo, "stop"))
    n = _nucleo(tmp_path, gerador, abrir=True)
    resposta, _ = n.processar("faz um programa que imprime 1")
    assert resposta.startswith("Comecei a gerar o código.")
    assert "Abri o arquivo no VS Code" in resposta
    gerador._thread.join(5)
    assert len(abertos) == 1 and abertos[0].is_dir()
    assert n.processar("testa o código")[0].startswith("Rodou sem erros.")
