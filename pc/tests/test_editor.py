import subprocess

from jarvis import editor


def _arquivo(tmp_path, texto):
    arq = tmp_path / "codigo.py"
    arq.write_text(texto, encoding="utf-8")
    return arq


def test_codigo_que_funciona_mostra_a_saida(tmp_path):
    arq = _arquivo(tmp_path, 'print("olá, mundo")\n')
    resposta = editor.testar_arquivo(arq)
    assert resposta.startswith("Rodou sem erros.")
    assert "olá, mundo" in resposta


def test_erro_de_sintaxe_e_pego_antes_de_rodar(tmp_path):
    arq = _arquivo(tmp_path, "def f(:\n    pass\n")
    assert "erro de sintaxe na linha 1" in editor.testar_arquivo(arq)


def test_erro_em_tempo_de_execucao(tmp_path):
    arq = _arquivo(tmp_path, "print(1/0)\n")
    resposta = editor.testar_arquivo(arq)
    assert resposta.startswith("Deu erro")
    assert "ZeroDivisionError" in resposta


def test_programa_que_nao_para_e_interrompido(tmp_path):
    arq = _arquivo(tmp_path, "while True:\n    pass\n")
    resposta = editor.testar_arquivo(arq, tempo=1)
    assert "Rodou por 1 segundo(s) sem erro" in resposta


def test_pedido_de_digitacao_nao_trava(tmp_path):
    arq = _arquivo(tmp_path, "nome = input('nome? ')\nprint(nome)\n")
    resposta = editor.testar_arquivo(arq)
    assert resposta.startswith("Deu erro")
    assert "EOFError" in resposta


def test_arquivo_vazio_ou_ausente(tmp_path):
    assert editor.testar_arquivo(tmp_path / "nao_existe.py") == "Não encontrei o arquivo do código."
    assert editor.testar_arquivo(_arquivo(tmp_path, "   \n")) == "O arquivo do código está vazio."


def test_sem_vscode_avisa(tmp_path, monkeypatch):
    monkeypatch.setattr(editor.shutil, "which", lambda nome: None)
    assert "VS Code não foi encontrado" in editor.abrir_no_vscode(tmp_path / "codigo.py")


def test_abre_com_o_comando_code(tmp_path, monkeypatch):
    chamadas = []
    monkeypatch.setattr(editor.shutil, "which", lambda nome: "/usr/bin/code")
    monkeypatch.setattr(editor.subprocess, "Popen", lambda args, **kw: chamadas.append(args))
    assert editor.abrir_no_vscode(tmp_path / "codigo.py") is None
    assert chamadas == [["/usr/bin/code", str(tmp_path / "codigo.py")]]


def test_projeto_com_main_roda_o_main(tmp_path):
    (tmp_path / "main.py").write_text('print("projeto ok")\n', encoding="utf-8")
    assert "projeto ok" in editor.testar_projeto(tmp_path)


def test_projeto_html_abre_no_navegador(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<h1>oi</h1>", encoding="utf-8")
    abertos = []
    monkeypatch.setattr(editor.webbrowser, "open", lambda url: abertos.append(url))
    assert "Abri index.html" in editor.testar_projeto(tmp_path)
    assert abertos[0].startswith("file://")


def test_projeto_sem_jeito_de_rodar(tmp_path):
    (tmp_path / "estilo.css").write_text("body{}", encoding="utf-8")
    assert "não tem um jeito automático" in editor.testar_projeto(tmp_path)
