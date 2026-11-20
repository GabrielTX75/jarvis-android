# JARVIS EXE — Windows

## Primeira versão funcional adicionada
- Interface desktop em português.
- Chat com API compatível com OpenAI Chat Completions, incluindo Groq.
- Configuração de endpoint, modelo e chave.
- Histórico de conversa durante a sessão.
- Ferramentas confirmadas para abrir Bloco de Notas, Calculadora, navegador e pesquisa web.
- Modo Hacker informativo/defensivo, sem executar varreduras.

## Configuração Groq
Endpoint: https://api.groq.com/openai/v1/chat/completions
Modelo: informe um modelo habilitado na sua conta.
Chave: configure no aplicativo. Não coloque a chave no GitHub.

A chave desta primeira versão fica em arquivo local de configurações do usuário do Windows. Não compartilhe esse arquivo. Migrar para Windows Credential Manager é obrigatório antes de distribuir amplamente.

## Compilação
O workflow .github/workflows/build-exe.yml compila em runner Windows e publica JARVIS.exe como artefato do GitHub Actions por 14 dias. A alteração em JARVIS-EXE deve disparar a compilação; acompanhe em Actions.

## Ainda não implementado
Controle genérico de mouse/teclado, leitura de tela/OCR, voz contínua, biometria, múltiplos perfis isolados, memória sincronizada, automação de navegador com verificação de estado, atualizador assinado com rollback e auditoria técnica automatizada. Não são simulados nesta versão.

## Segurança
Ações disponíveis são limitadas e pedem confirmação. O modo Hacker permanece defensivo; não oferece invasão, roubo de credenciais, persistência, evasão ou extração de dados.
