from pathlib import Path

from jarvis.ferramentas import (
    anotar, apagar_anotacoes, casar, desfazer_organizacao, ler_anotacoes,
    lembrete, organizar_downloads,
)


def test_anotacoes(tmp_path):
    assert anotar(tmp_path, "comprar pao").startswith("Anotado")
    assert "comprar pao" in ler_anotacoes(tmp_path)
    assert apagar_anotacoes(tmp_path) == "Apaguei as anotações."
    assert ler_anotacoes(tmp_path) == "Você não tem anotações."


def test_casar_por_nome_exato_e_trecho():
    candidatos = {"bloco de notas": "notepad", "calculadora": "calc"}
    assert casar("Bloco de Notas", candidatos) == "notepad"
    assert casar("notas", candidatos) == "notepad"
    assert casar("planilhas", candidatos) is None


def test_lembrete_com_tempo_zero_nao_agenda():
    assert lembrete(0, "x", aviso=lambda m: None) == "Diga um tempo maior que zero."


def test_organiza_e_desfaz(tmp_path):
    dl = tmp_path / "Downloads"
    dl.mkdir()
    (dl / "foto.jpg").write_text("x")
    (dl / "manual.pdf").write_text("y")
    (dl / "estranho.xyz").write_text("z")
    base = tmp_path / "JARVIS"

    msg = organizar_downloads(dl, base)
    assert msg.startswith("Organizei 3 arquivos em 3 pastas")
    assert (dl / "Imagens" / "foto.jpg").exists()
    assert (dl / "Documentos" / "manual.pdf").exists()
    assert (dl / "Outros" / "estranho.xyz").exists()

    assert desfazer_organizacao(base).startswith("Desfiz a organização. 3 arquivos")
    assert (dl / "foto.jpg").exists()
    assert not (dl / "Imagens" / "foto.jpg").exists()


def test_organizar_nao_sobrescreve(tmp_path):
    dl = tmp_path / "Downloads"
    (dl / "Documentos").mkdir(parents=True)
    (dl / "Documentos" / "manual.pdf").write_text("antigo")
    (dl / "manual.pdf").write_text("novo")

    organizar_downloads(dl, tmp_path / "JARVIS")
    assert (dl / "Documentos" / "manual.pdf").read_text() == "antigo"
    assert (dl / "Documentos" / "manual (1).pdf").read_text() == "novo"


def test_organizar_sem_arquivos_soltos(tmp_path):
    dl = tmp_path / "Downloads"
    dl.mkdir()
    assert organizar_downloads(dl, tmp_path / "JARVIS") == "Não encontrei arquivos soltos na pasta Downloads."
