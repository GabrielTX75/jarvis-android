from pathlib import Path

from jarvis import funcoes
from jarvis.comandos import reconhecer
from jarvis.nucleo import Nucleo
from jarvis.codigo import Gerador


def test_abrir_site_monta_https_e_recusa_lixo(monkeypatch):
    abertos = []
    monkeypatch.setattr(funcoes.webbrowser, "open", lambda url: abertos.append(url))
    assert funcoes.abrir_site("google.com") == "Abri google.com."
    assert abertos == ["https://google.com"]
    assert funcoes.abrir_site("isso") == "Esse endereço não parece um site."


def test_procura_arquivo_por_trecho_do_nome(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "Relatorio Final.docx").write_text("x")
    (tmp_path / "outro.txt").write_text("y")
    achados = funcoes.procurar_arquivo("relatorio", raizes=[tmp_path])
    assert [p.name for p in achados] == ["Relatorio Final.docx"]
    assert funcoes.procurar_arquivo("inexistente", raizes=[tmp_path]) == []


def test_resumir_recusa_arquivo_que_nao_e_texto(tmp_path, monkeypatch):
    monkeypatch.setattr(funcoes.Path, "home", lambda: tmp_path)
    (tmp_path / "Documents").mkdir()
    (tmp_path / "Documents" / "foto.png").write_bytes(b"\x89PNG")
    assert "Só consigo resumir arquivos de texto" in funcoes.resumir_arquivo("foto")


def test_resumir_usa_a_ia(tmp_path, monkeypatch):
    monkeypatch.setattr(funcoes.Path, "home", lambda: tmp_path)
    monkeypatch.setenv("JARVIS_IA_URL", "https://exemplo.test/v1")
    (tmp_path / "Documents").mkdir()
    (tmp_path / "Documents" / "ata.txt").write_text("reunião sobre o projeto", encoding="utf-8")
    resposta = funcoes.resumir_arquivo("ata", chamar=lambda msgs, max_tokens=0: ("- reunião do projeto", "stop"))
    assert resposta == "Resumo de ata.txt: - reunião do projeto"


def test_info_do_sistema_tem_os_basicos():
    texto = funcoes.info_sistema()
    assert "Sistema:" in texto and "Disco:" in texto


def test_desligar_pede_confirmacao_em_dois_passos(tmp_path):
    n = Nucleo(pasta=tmp_path, downloads=tmp_path / "dl", gerador=Gerador(tmp_path), aviso=lambda m: None)
    assert n.processar("confirma desligar")[0] == "Não há desligamento pedido. Diga: desliga o computador."
    assert "confirma desligar" in n.processar("desliga o computador")[0]
    assert n._pendente == "desligar"
    n._pendente = None  # sem executar o desligamento de verdade nos testes


def test_comandos_novos_sao_reconhecidos():
    assert reconhecer("copia bom dia pra você") == ("copiar", {"texto": "bom dia pra voce"})
    assert reconhecer("abre pasta downloads") == ("abrir_pasta", {"nome": "downloads"})
    assert reconhecer("abre o google.com")[0] == "abrir_site"
    assert reconhecer("procura o arquivo relatorio") == ("procurar_arquivo", {"termo": "relatorio"})
    assert reconhecer("como está o computador?") == ("info_sistema", {})
    assert reconhecer("tira um print da tela") == ("captura_tela", {})
    assert reconhecer("resume o arquivo ata") == ("resumir_arquivo", {"nome": "ata"})
    assert reconhecer("desliga o computador")[0] == "desligar_pedido"
    assert reconhecer("cancela o desligamento")[0] == "cancelar_desligar"
    assert reconhecer("faz um código que roda o jogo")[0] == "gerar_codigo"


def test_pedido_de_programa_ou_site_vira_projeto():
    assert reconhecer("faz um site de loja")[0] == "gerar_codigo"
    assert reconhecer("cria um jogo de carro")[0] == "gerar_codigo"
    assert reconhecer("abre o google com br") == ("abrir_site", {"endereco": "google.com.br"})
