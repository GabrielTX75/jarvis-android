from jarvis.comandos import da_ia, reconhecer


def test_pesquisa():
    assert reconhecer("pesquisa receita de bolo") == ("pesquisar", {"termo": "receita de bolo"})


def test_calculo_por_pergunta():
    assert reconhecer("quanto é 25 por cento de 80?") == ("calcular", {"expressao": "25 por cento de 80"})


def test_hora_e_data():
    assert reconhecer("Que horas são?") == ("hora", {})
    assert reconhecer("qual é a data de hoje") == ("data", {})


def test_lembrete_converte_para_segundos():
    acao = reconhecer("me lembra em 10 minutos de tomar remédio")
    assert acao == ("lembrete", {"segundos": 600, "texto": "tomar remedio"})


def test_anotar_remove_acentos():
    assert reconhecer("anota que comprar pão") == ("anotar", {"texto": "comprar pao"})


def test_abrir_programa():
    assert reconhecer("abre o bloco de notas") == ("abrir_app", {"consulta": "bloco de notas"})


def test_musica():
    assert reconhecer("toca a música Evidências") == ("tocar_musica", {"termo": "evidencias"})


def test_codigo_comandos():
    pedido = "faz um código de 300 linhas de um jogo da velha"
    assert reconhecer(pedido) == ("gerar_codigo", {"pedido": pedido})
    assert reconhecer("continua o código") == ("continuar_codigo", {})
    assert reconhecer("como está o código?") == ("status_codigo", {})
    assert reconhecer("para o código") == ("parar_codigo", {})


def test_gerar_codigo_que_menciona_continuar_nao_vira_continuacao():
    pedido = "faz um jogo que continua pedindo o código ao usuário"
    assert reconhecer(pedido)[0] == "gerar_codigo"


def test_sair_e_frase_sem_regra():
    assert reconhecer("sair") == ("sair", {})
    assert reconhecer("oi, tudo bem com você") is None
    assert reconhecer("   ") is None


def test_da_ia_aceita_json_de_acao_conhecida():
    assert da_ia('{"acao": "hora", "args": {}}') == ("hora", {})
    assert da_ia('```json\n{"acao": "calcular", "args": {"expressao": "2+2"}}\n```') == ("calcular", {"expressao": "2+2"})


def test_da_ia_ignora_texto_e_acao_desconhecida():
    assert da_ia("Olá! Tudo bem?") is None
    assert da_ia('{"acao": "apagar_tudo", "args": {}}') is None
    assert da_ia("{isto não é json") is None


def test_ler_anotacoes():
    assert reconhecer("ler anotações") == ("ler_anotacoes", {})
    assert reconhecer("mostra minhas anotações") == ("ler_anotacoes", {})
