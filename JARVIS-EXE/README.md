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

## Central holográfica de comando — interface atualizada

A tela inicial foi reorganizada como uma central de comando em preto/azul/ciano: cabeçalho de estado, navegação, lista de módulos, núcleo visual animado, chat, atalhos e painel de sistema. CPU, memória, disco e bateria só são exibidos quando obtidos do Windows via psutil; localização permanece não configurada até o usuário informar um rótulo. O núcleo é uma animação 2D de interface, não uma projeção holográfica física.

- Navegação para projetos, auditoria, Security Lab, Money, Drive, Hologram Lab, arquivos e configurações.
- Ferramentas rápidas: calculadora, bloco de notas, navegador, mapa, pasta de projetos e captura de tela com confirmação.
- Comando de voz por reconhecimento de fala opcional (SpeechRecognition/PyAudio) e leitura em voz alta opcional (pyttsx3). Não existe identificação biométrica do locutor.
- JARVIS Drive abre uma rota do destino informado no Google Maps; não obtém posição GPS, não dirige e não controla o veículo.
- O chat IA usa o endpoint configurado e não executa automaticamente comandos do computador.

## Lembretes e notificações (implementação inicial)
- O chat aceita comandos simples como “JARVIS, me avisa da reunião às 15h” e “me lembra da consulta amanhã às 9:30”.
- O lembrete é salvo localmente e o JARVIS agenda uma notificação 10 minutos antes.
- O monitor local verifica os lembretes enquanto o JARVIS EXE está aberto; mantenha o programa aberto e o Windows acordado para receber o aviso.
- Mensagens para contatos e chamadas automáticas ainda não estão integradas. O envio deve usar serviço autorizado e confirmação; uma chamada deve abrir o discador/Phone Link para o usuário confirmar.

## Interface e módulos planejados (novembro de 2026)

- Interface desktop reorganizada em central de comando, navegação lateral e chat, com paleta preto/azul-marinho/ciano; não usa laranja como cor de destaque.
- **JARVIS MONEY:** painel inicial transparente para análise de mercado. A arquitetura planejada inclui fontes de cotações identificadas e datadas, análise de tendência/volume/volatilidade/notícias, cenários probabilísticos, backtesting, simulação com cotações reais, custos e controles de risco, além de histórico auditável. O painel atual é apenas a estrutura visual: ainda não está conectado a cotações, não produz sinais e não executa ordens, apostas ou movimentações financeiras.
- **JARVIS DRIVE:** módulo futuro para localização autorizada, mapas, trânsito, planejamento de rotas e abertura de navegação compatível. O botão atual apenas informa o escopo; não acessa localização nem controla veículos. Direção autônoma não será improvisada por integração de API.

## JARVIS Security Lab — Blue Team e Red Team

- **Blue Team — auditoria local:** análise estática básica da pasta escolhida pelo usuário, com confirmação de escopo e ocorrências para revisão manual. Não certifica segurança.
- **Blue Team — monitoramento de eventos:** acompanha novas linhas de um arquivo JSONL exportado pelo próprio projeto. Detecta sequência de falhas de autenticação, eventos sensíveis de privilégio/política e eventos suspeitos reportados pelo serviço. Trata eventos normalizados e mantém as respostas em simulação até existir um adaptador oficial do provedor.
- **Formato de evento esperado:** um objeto JSON por linha, com `event_type` e `actor_id`; opcionalmente `timestamp` (ISO 8601) e `project_id`. Exemplos de tipos reconhecidos: `login_failed`, `auth_failed`, `admin_role_granted`, `privilege_escalation`, `security_policy_changed`, `rate_limit_triggered` e `suspicious_access`. O serviço conectado é responsável por exportar esses eventos; o JARVIS não consegue observar sozinho os registros privados de um provedor.
- **Red Team:** permanece um roteiro educativo em cenários fictícios locais. Não envia tráfego, não testa hosts reais nem executa exploração. A evolução técnica deverá usar escopo próprio/autorizado, ambiente de teste, limites e validação não destrutiva.
- **Contenção automática real:** ainda não está ligada. Para bloquear sessões ou contas, será necessário implementar e testar um adaptador específico (por exemplo, Supabase Auth ou provedor de hospedagem), com credenciais de menor privilégio, lista de ações permitidas, auditoria e mecanismo de reversão. O monitor atual não bloqueia usuários nem "contra-ataca" a origem.

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


## Navegador interno do JARVIS

O JARVIS EXE possui uma janela própria de navegação baseada em WebView2/Edge Chromium. Pesquisas, páginas, rotas do Maps e buscas de vídeos no YouTube são abertas nessa janela do JARVIS, sem enviar o usuário ao navegador padrão do Windows. O conteúdo de sites e vídeos depende da conexão, das políticas do site e do Microsoft Edge WebView2 Runtime instalado no Windows. O JARVIS não contorna paywalls, logins, DRM ou restrições dos sites. Para ações sensíveis (entrar em contas, enviar mensagens, publicar ou comprar), a implementação deve solicitar confirmação explícita e manter o usuário no controle.
