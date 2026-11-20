# JARVIS EXE — Windows

## Implementado nesta etapa (código enviado)
- Aplicativo desktop em português com chat usando endpoint compatível com OpenAI Chat Completions (inclui Groq).
- Configuração de endpoint/modelo; chave da API armazenada pelo Windows Credential Manager via pacote keyring.
- Histórico de conversa em memória durante a sessão.
- Abertura confirmada de Bloco de Notas e Calculadora; pesquisa web confirmada pelo usuário.
- Criação de pastas de projeto e gravação de arquivos dentro de uma área dedicada, com validação contra path traversal. Arquivos gerados não são executados automaticamente.
- Captura de tela somente por ação explícita do usuário; OCR local opcional depende de Tesseract instalado pelo usuário.
- Auditoria estática offline de pasta escolhida pelo usuário, com ocorrências para revisão manual; não declara vulnerabilidades automaticamente.
- Workflow Windows que executa testes unitários e empacota JARVIS.exe como artefato temporário.

## Configuração Groq
Endpoint: https://api.groq.com/openai/v1/chat/completions
Modelo: use um modelo atualmente habilitado na sua conta.
Chave: informe dentro do aplicativo. Não a coloque no GitHub.

## Como obter o EXE
Abra a aba Actions do repositório, selecione Build JARVIS EXE e execute Run workflow. Quando o job terminar com sucesso, baixe o artefato JARVIS-Windows-EXE. O artefato expira após 14 dias. Ainda não há instalador assinado nem release permanente.

## Ainda pendente — não fingir que está pronto
- Controle genérico e seguro do mouse/teclado, com plano visível, confirmação por ação, pausa e botão de assumir controle.
- OCR totalmente integrado ao chat e interpretação contextual de janelas.
- Voz bidirecional contínua e interrupção por voz.
- Agentes especializados de pesquisa, estudo, escrita, planejamento e análise.
- Memória persistente criptografada, sincronização entre APK/EXE, múltiplos perfis realmente isolados e permissões por perfil.
- Modo Hacker técnico completo para Red Team/Blue Team em ativos próprios/autorizados, com escopo, evidência mínima, laboratório, correção e reteste. A auditoria local atual é apenas estática e básica.
- Atualizador com assinatura, backup, validação de integridade e rollback.
- Testes de segurança, privacidade, desempenho e compatibilidade em Windows real.

## Limites de segurança
O JARVIS não deve invadir terceiros, roubar credenciais, persistir ocultamente, evadir detecção, extrair dados pessoais nem apagar rastros. Ações de risco (pagamento, compra, publicação, exclusão, instalação, privilégios elevados) exigem confirmação explícita. Não contornar autenticação bancária ou controles do Windows.

## Estado de validação
Código e workflow adicionados ao branch de desenvolvimento. A compilação e os testes ainda precisam concluir com sucesso no GitHub Actions e o EXE precisa ser testado em Windows antes de ser considerado pronto.
