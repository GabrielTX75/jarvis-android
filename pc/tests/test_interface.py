import pytest

tk = pytest.importorskip("tkinter")

from jarvis.codigo import Gerador  # noqa: E402
from jarvis.interface import Janela  # noqa: E402
from jarvis.nucleo import Nucleo  # noqa: E402


def _raiz():
    try:
        raiz = tk.Tk()
    except (tk.TclError, ImportError):
        pytest.skip("sem tela ou sem tkinter neste ambiente")
    raiz.withdraw()
    return raiz


def test_envia_pedido_e_mostra_resposta(tmp_path, monkeypatch):
    raiz = _raiz()
    try:
        monkeypatch.setenv("JARVIS_PASTA", str(tmp_path))
        nucleo = Nucleo(pasta=tmp_path, downloads=tmp_path / "dl", gerador=Gerador(tmp_path), aviso=lambda m: None)
        janela = Janela(raiz, nucleo)
        janela.campo.insert(0, "quanto é 2 mais 2")
        janela.enviar()
        for _ in range(100):
            raiz.update()
            if not janela.ocupado:
                break
            raiz.after(50)
            raiz.update()
        texto = janela.log.get("1.0", "end")
        assert "quanto é 2 mais 2" in texto
        assert "JARVIS: 4." in texto
        assert janela.ocupado is False
    finally:
        raiz.destroy()


def test_pedido_vazio_nao_faz_nada(tmp_path):
    raiz = _raiz()
    try:
        janela = Janela(raiz, Nucleo(pasta=tmp_path, downloads=tmp_path / "dl", gerador=Gerador(tmp_path), aviso=lambda m: None))
        janela.campo.insert(0, "   ")
        janela.enviar()
        assert janela.ocupado is False
    finally:
        raiz.destroy()
