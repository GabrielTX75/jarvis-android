from pathlib import Path

from jarvis.codigo import Gerador
from jarvis.nucleo import Nucleo


def test_testar_sem_codigo_avisa(tmp_path):
    n = Nucleo(pasta=tmp_path, downloads=tmp_path / "dl", gerador=Gerador(tmp_path), aviso=lambda m: None, abrir_editor=False)
    assert n.processar("testa o código") == ("Não há código para testar. Peça um código primeiro.", False)


def test_gerar_codigo_abre_no_editor(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_IA_URL", "https://exemplo.test/v1/chat/completions")
    abertos = []
    monkeypatch.setattr("jarvis.nucleo.editor.abrir_no_vscode", lambda arq: abertos.append(arq) or None)
    gerador = Gerador(tmp_path, chamar=lambda msgs, max_tokens=0: ("print(1)\nFIM_DO_CODIGO", "stop"))
    n = Nucleo(pasta=tmp_path, downloads=tmp_path / "dl", gerador=gerador, aviso=lambda m: None)
    resposta, _ = n.processar("faz um código que imprime 1")
    assert resposta.startswith("Comecei a gerar o código.")
    assert "Abri o arquivo no VS Code" in resposta
    gerador._thread.join(5)
    assert len(abertos) == 1 and Path(abertos[0]).name.endswith(".py")
    assert n.processar("testa o código")[0].startswith("Rodou sem erros.")
