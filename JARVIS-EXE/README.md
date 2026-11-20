# JARVIS EXE — Windows

## Implementado nesta etapa (código enviado)
- Aplicativo desktop em português com chat usando endpoint compatível com OpenAI Chat Completions (inclui Groq).
- Configuração de endpoint/modelo; chave da API armazenada pelo Windows Credential Manager via pacote keyring.
- Histórico de conversa em memória durante a sessão.
- Abertura confirmada de Bloco de Notas e Calculadora; pesquisa web confirmada pelo usuário.
- Criação de pastas de projeto e gravação de arquivos dentro de uma área dedicada, com validação contra path traversal. Arquivos gerados não são executados automaticamente.
- Captura de tela somente por ação explícita do usuário; OCR local opcional depende de Tesseract instalado pelo usuário.
- Laboratório inicial de hologramas 3D esquemáticos: carros, motos, construções, robôs/máquinas, corpo humano educativo, terrenos e objeto genérico; rotação, zoom, deslocamento e separação visual de componentes.
- Rastreamento opcional de uma mão pela webcam padrão, ativado manualmente e processado localmente com OpenCV/MediaPipe; câmera é desligada ao fechar o laboratório. Nenhuma imagem é gravada ou enviada pela função.
- Auditoria estática offline de pasta escolhida pelo usuário, com ocorrências para revisão manual; não declara vulnerabilidades automaticamente.
- Workflow Windows que executa testes unitários e empacota JARVIS.exe como artefato temporário.

## Laboratório de hologramas (protótipo)
Abra Ferramentas → Laboratório de hologramas 3D. A câmera começa desligada; clique em “Ativar câmera e gestos” para permitir o rastreamento local. Mão aberta move a orientação, movimento da mão desloca o modelo e a pinça entre polegar/indicador controla o zoom. Use os botões para girar e separar/reunir componentes. Fechar a janela desliga e libera a câmera. A primeira versão desenha modelos esquemáticos em arame; não representa carros reais completos, engenharia CAD ou hologramas físicos.

As dependências de câmera são opcionais: OpenCV, MediaPipe e Pillow. O acesso depende das permissões de câmera do Windows e de uma webcam funcional.

## Interface e módulos planejados (novembro de 2026)

- Interface desktop reorganizada em central de comando, navegação lateral e chat, com paleta preto/azul-marinho/ciano; não usa laranja como cor de destaque.
- **JARVIS MONEY:** painel inicial transparente para análise de mercado. A arquitetura planejada inclui fontes de cotações identificadas e datadas, análise de tendência/volume/volatilidade/notícias, cenários probabilísticos, backtesting, simulação com cotações reais, custos e controles de risco, além de histórico auditável. O painel atual é apenas a estrutura visual: ainda não está conectado a cotações, não produz sinais e não executa ordens, apostas ou movimentações financeiras.
- **JARVIS DRIVE:** módulo futuro para localização autorizada, mapas, trânsito, planejamento de rotas e abertura de navegação compatível. O botão atual apenas informa o escopo; não acessa localização nem controla veículos. Direção autônoma não será improvisada por integração de API.

## JARVIS Security Lab — Blue Team e Red Team

- **Blue Team (defensivo):** análise estática local da pasta escolhida pelo usuário, com confirmação de que o escopo é próprio/autorizado, ocorrências para revisão manual e relatório. A análise atual é básica e não certifica segurança.
- **Red Team (atacante em laboratório):** roteiro interativo de simulação em cenários fictícios locais (aplicação web, API ou servidor). Ensina definição de escopo, revisão de autenticação/autorização, uso de dados sintéticos, evidência mínima, correção e reteste.
- O perfil Red Team nesta versão **não** envia tráfego, não testa hosts reais, não explora serviços, não coleta credenciais, não exfiltra dados e não executa persistência/evasão. Testes técnicos futuros devem ficar limitados a laboratório próprio ou autorização documentada, com escopo explícito e ações reversíveis.

## Plano geral de capacidades do JARVIS EXE

Os itens abaixo são metas de desenvolvimento, não recursos já concluídos:

- Voz bidirecional contínua em português, ativação por comando, interrupção por voz e opção de repetir resposta.
- Visão computacional: captura apenas sob comando, OCR local integrado ao chat e interpretação contextual da janela selecionada.
- Controle assistido de mouse/teclado com plano visível, confirmação para ações sensíveis, pausa imediata e botão para o usuário assumir o controle.
- Memória persistente criptografada, com revisão/controle pelo usuário; sincronização segura com o APK e perfis isolados.
- Agentes especializados para pesquisa, programação, estudo, escrita, planejamento e análise.
- JARVIS MONEY: cotações reais com fonte e horário, análise probabilística, backtesting e simulação; sem promessas de lucro nem ordens financeiras automáticas.
- JARVIS DRIVE: localização consentida, mapas, trânsito, rotas e integração de navegação compatível; sem controle improvisado de direção, aceleração ou frenagem.
- Hologramas: evolução de wireframes para modelos 3D detalhados, biblioteca de ativos, gestos calibráveis e edição de componentes.
- Atualizador seguro com assinatura, backup, validação de integridade e rollback.
- Testes automatizados, revisão de privacidade e segurança e validação em Windows real antes de distribuir.

## Configuração Groq
Endpoint: https://api.groq.com/openai/v1/chat/completions
Modelo: use um modelo atualmente habilitado na sua conta.
Chave: informe dentro do aplicativo. Não a coloque no GitHub.

## Como obter o EXE
Abra a aba Actions do repositório, selecione Build JARVIS EXE e execute Run workflow. Quando o job terminar com sucesso, baixe o artefato JARVIS-Windows-EXE. O artefato expira após 14 dias. Ainda não há instalador assinado nem release permanente.

## Ainda pendente — não fingir que está pronto
- Modelos 3D realistas/CAD com peças corretas, materiais, dimensões e bibliotecas de ativos; o laboratório atual usa wireframes procedurais esquemáticos, não réplicas técnicas de veículos/edifícios.
- Calibração de gestos robusta para múltiplas mãos, controles customizáveis e compatibilidade testada com webcams diferentes.
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
