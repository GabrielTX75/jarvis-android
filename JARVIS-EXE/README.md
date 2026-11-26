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
- Escuta contínua iniciada e encerrada manualmente pelo usuário, com pausa automática enquanto a IA processa e enquanto o JARVIS fala. Reconhecimento pt-BR via serviço online do Google; o áudio é enviado para transcrição e não é salvo pelo módulo. Não há palavra de ativação, escuta em segundo plano após fechar o EXE ou identificação biométrica do locutor.
- JARVIS Drive abre uma rota do destino informado no Google Maps; não obtém posição GPS, não dirige e não controla o veículo.
- O chat IA usa o endpoint configurado e não executa automaticamente comandos do computador.

## Voz contínua (sessão manual)

- Clique em “INICIAR ESCUTA” e confirme o aviso de privacidade para abrir uma sessão de microfone; clique em “PARAR ESCUTA” para encerrá-la.
- O JARVIS reconhece frases em português do Brasil, envia cada transcrição ao chat e aguarda a resposta antes de voltar a ouvir.
- A escuta fica pausada durante o processamento da IA e durante a fala sintetizada, evitando que o microfone trate a própria resposta como novo comando.
- O reconhecimento usa o serviço online do Google por meio do SpeechRecognition. Antes de cada sessão, o JARVIS informa e pede confirmação de que o áudio capturado será enviado ao Google para transcrição; o JARVIS não o armazena em arquivo. É necessária internet.
- O encerramento pode levar alguns segundos se uma transcrição online já estiver em andamento. Fechar o JARVIS solicita o encerramento da sessão.
- Ainda não há palavra de ativação (“Jarvis”), interrupção por voz, reconhecimento offline nem escuta com o aplicativo fechado.

## Lembretes e notificações (implementação inicial)
- O chat aceita comandos simples como “JARVIS, me avisa da reunião às 15h” e “me lembra da consulta amanhã às 9:30”.
- O lembrete é salvo localmente e o JARVIS agenda uma notificação 10 minutos antes.
- O monitor local verifica os lembretes enquanto o JARVIS EXE está aberto; mantenha o programa aberto e o Windows acordado para receber o aviso.
- Mensagens para contatos e chamadas automáticas ainda não estão integradas. O envio deve usar serviço autorizado e confirmação; uma chamada deve abrir o discador/Phone Link para o usuário confirmar.

## Interface e módulos planejados (novembro de 2026)

- Interface desktop reorganizada em central de comando, navegação lateral e chat, com paleta preto/azul-marinho/ciano; não usa laranja como cor de destaque.
- **JARVIS MONEY:** painel inicial transparente para análise de mercado. A arquitetura planejada inclui fontes de cotações identificadas e datadas, análise de tendência/volume/volatilidade/notícias, cenários probabilísticos, backtesting, simulação com cotações reais, custos e controles de risco, além de histórico auditável. O painel atual é apenas a estrutura visual: ainda não está conectado a cotações, não produz sinais e não executa ordens, apostas ou movimentações financeiras.
- **JARVIS DRIVE:** módulo futuro para localização autorizada, mapas, trânsito, planejamento de rotas e abertura de navegação compatível. O botão atual apenas informa o escopo; não acessa localização nem controla veículos. Direção autônoma não será improvisada por integração de API.

## Agentes especializados e memória local

- O seletor do chat oferece nove perfis: Geral, Pesquisa, Programação, Flutter/Dart, Estudos, Escrita, Planejamento, Análise e Visão.
- O perfil **Flutter/Dart** é especializado em criar projetos Flutter completos: estrutura de arquivos, pubspec.yaml, telas/widgets, navegação, estado, serviços, tratamento de erros e testes. O JARVIS deve indicar os caminhos de cada arquivo e comandos para validar/compilar.
- A geração de código não significa que o Flutter SDK esteja instalado ou que o EXE consiga compilar APK/EXE sozinho. A compilação depende do Flutter SDK, Dart SDK, Android SDK e ferramentas da plataforma instalados no computador; o JARVIS não deve afirmar que compilou sem executar e verificar o resultado.
- Os perfis orientam o estilo e o foco da resposta; não concedem permissões extras nem executam ações locais por conta própria.
- A memória local salva apenas fatos solicitados explicitamente pelo usuário, permite listar e apagar itens e não sincroniza com o APK.
- A memória atual é um arquivo JSON local e **não é criptografada**. Não guarde informações sensíveis nela; credenciais e tokens são recusados pelo módulo.
- O fluxo Visão captura a tela somente após autorização, extrai texto localmente via OCR e envia o texto extraído ao histórico. Isso ainda não é compreensão geral de imagens nem observação contínua da tela.

## JARVIS Security Lab — Blue Team e Red Team

- **Blue Team — auditoria local:** análise estática básica da pasta escolhida pelo usuário, com confirmação de escopo e ocorrências para revisão manual. Não certifica segurança.
- **Blue Team — monitoramento de eventos:** acompanha novas linhas de um arquivo JSONL exportado pelo próprio projeto. Detecta sequência de falhas de autenticação, eventos sensíveis de privilégio/política e eventos suspeitos reportados pelo serviço. Trata eventos normalizados e mantém as respostas em simulação até existir um adaptador oficial do provedor.
- **Formato de evento esperado:** um objeto JSON por linha, com `event_type` e `actor_id`; opcionalmente `timestamp` (ISO 8601) e `project_id`. Exemplos de tipos reconhecidos: `login_failed`, `auth_failed`, `admin_role_granted`, `privilege_escalation`, `security_policy_changed`, `rate_limit_triggered` e `suspicious_access`. O serviço conectado é responsável por exportar esses eventos; o JARVIS não consegue observar sozinho os registros privados de um provedor.
- **Red Team:** permanece um roteiro educativo em cenários fictícios locais. Não envia tráfego, não testa hosts reais nem executa exploração. A evolução técnica deverá usar escopo próprio/autorizado, ambiente de teste, limites e validação não destrutiva.
- **Contenção automática real:** ainda não está ligada. Para bloquear sessões ou contas, será necessário implementar e testar um adaptador específico (por exemplo, Supabase Auth ou provedor de hospedagem), com credenciais de menor privilégio, lista de ações permitidas, auditoria e mecanismo de reversão. O monitor atual não bloqueia usuários nem "contra-ataca" a origem.

## Plano geral de capacidades do JARVIS EXE

Os itens abaixo são metas de desenvolvimento, não recursos já concluídos:

- Palavra de ativação (“Jarvis”), interrupção por voz, reconhecimento offline e retomada da sessão após reinicialização.
- Visão computacional: captura apenas sob comando, OCR local integrado ao chat e interpretação contextual da janela selecionada.
- Controle assistido de mouse/teclado com plano visível, confirmação para ações sensíveis, pausa imediata e botão para o usuário assumir o controle.
- Memória persistente local e protegida, com revisão e controle pelo usuário; sem sincronização com o APK.
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
- Interpretação multimodal real de imagens e janelas selecionadas; o fluxo atual integra OCR local de texto capturado.
- Voz bidirecional contínua e interrupção por voz.
- Evoluir os oito perfis existentes com ferramentas especializadas e testes de qualidade por tarefa.
- Criptografia da memória local em repouso, múltiplos perfis realmente isolados e permissões por perfil.
- Modo Hacker técnico completo para Red Team/Blue Team em ativos próprios/autorizados, com escopo, evidência mínima, laboratório, correção e reteste. A auditoria local atual é apenas estática e básica.
- Atualizador com assinatura, backup, validação de integridade e rollback.
- Testes de segurança, privacidade, desempenho e compatibilidade em Windows real.

## Limites de segurança
O JARVIS não deve invadir terceiros, roubar credenciais, persistir ocultamente, evadir detecção, extrair dados pessoais nem apagar rastros. Ações de risco (pagamento, compra, publicação, exclusão, instalação, privilégios elevados) exigem confirmação explícita. Não contornar autenticação bancária ou controles do Windows.

## Estado de validação
O workflow do Windows executa testes unitários, empacota o EXE com PyInstaller e publica o executável na Release `exe-latest` quando o job termina com sucesso. Uma compilação bem-sucedida no CI confirma testes e empacotamento automatizados, mas ainda não substitui o teste manual do executável em um Windows real com microfone, áudio e credenciais configurados.


## Navegador interno do JARVIS

O JARVIS EXE possui uma janela própria de navegação baseada em WebView2/Edge Chromium. Pesquisas, páginas, rotas do Maps e buscas de vídeos no YouTube são abertas nessa janela do JARVIS, sem enviar o usuário ao navegador padrão do Windows. O conteúdo de sites e vídeos depende da conexão, das políticas do site e do Microsoft Edge WebView2 Runtime instalado no Windows. O JARVIS não contorna paywalls, logins, DRM ou restrições dos sites. Para ações sensíveis (entrar em contas, enviar mensagens, publicar ou comprar), a implementação deve solicitar confirmação explícita e manter o usuário no controle.


## Cofre de APIs — Windows
- Configurações abre campos para Groq, Gemini, Tavily e brapi.
- As credenciais são armazenadas pelo pacote `keyring` no Gerenciador de Credenciais do Windows; não são gravadas em `settings.json` nem no repositório.
- Os campos secretos abrem vazios; deixar um campo vazio preserva a credencial já salva.
- Há testes de conexão individuais. Os testes fazem chamadas HTTPS e exibem apenas o resultado/código HTTP, sem imprimir a chave.
- A chave Groq é usada pelo chat compatível com OpenAI. Gemini, Tavily e brapi ficam guardadas e podem ser testadas; a integração funcional desses provedores aos módulos ainda precisa ser feita separadamente.
- As credenciais do Windows são independentes das do APK; cada dispositivo mantém seu próprio cofre.

## APIs gratuitas — integração funcional no EXE
- **Groq:** provedor principal do chat, usando o modelo configurado.
- **Gemini:** provedor reserva automático quando Groq falha e a chave Gemini está cadastrada. A versão atual usa Gemini 3.8 Flash; disponibilidade e cota dependem da conta Google.
- **Tavily:** comandos "pesquise [assunto]" e perguntas como "qual o clima em [cidade]" consultam a web e exibem resposta e fontes quando a chave está salva. Sem Tavily, a pesquisa abre o Google no navegador interno.
- **brapi:** JARVIS Money permite consultar cotações pelo código do ativo usando o token guardado. Valores são informativos, podem atrasar e não geram ordens.
- **Cofre:** Configurações > Cofre de APIs. Windows Credential Manager via keyring. Campos vazios preservam credenciais; apagar credenciais remove Groq, Gemini, Tavily e brapi.
- **Sem sincronização de memória ou credenciais:** configurações, lembretes e memória ficam locais. APK e EXE mantêm dados e cofres separados.
- **Testes:** `python -m unittest discover -s JARVIS-EXE/tests -v`. Testes de API usam respostas simuladas; não validam disponibilidade externa nem substituem testes reais com as chaves do usuário.

## Integração de projetos com Visual Studio Code

- O JARVIS reconhece comandos como **"abra o VS Code"** e pede confirmação antes de abrir o editor na pasta de projetos.
- Quando o usuário pede explicitamente a criação de um projeto/arquivos, a IA pode devolver um manifesto estruturado. O JARVIS pede confirmação, valida o nome e os caminhos e grava os arquivos dentro de `Documents/JarvisProjects`; em seguida, pergunta se deve abrir o projeto no VS Code.
- O manifesto aceita até 40 arquivos, 500 KB por arquivo e 2 MB no total. Caminhos absolutos, travessia de diretórios, duplicatas e extensões executáveis comuns são recusados.
- O conteúdo gerado **não é executado automaticamente**. O JARVIS agora oferece tarefas limitadas e confirmadas: `flutter analyze --no-pub`, `flutter test --no-pub`, `dart analyze`, compilação sintática Python e descoberta de testes Python. Testes executam código do projeto e exigem confirmação explícita.
- O JARVIS não executa comandos livres do terminal nem aceita texto da IA como comando de shell. No painel Controle avançado do Windows, o usuário pode instalar um pacote PyPI em um ambiente virtual `.venv` dentro de uma pasta de projeto escolhida; o JARVIS EXE não instala pacotes em seu próprio runtime empacotado.
- Depois da instalação, no VS Code use `Python: Select Interpreter` e escolha `.venv\\Scripts\\python.exe` (Windows). O JARVIS não troca o interpretador do editor nem altera o `.gitignore`; mantenha `.venv/` fora do controle de versão.
- É necessário ter o Visual Studio Code instalado no Windows. O JARVIS procura `Code.exe` nos locais padrão ou no PATH; se não encontrar, informa a dependência.
- O recurso foi desenhado para trabalhar com qualquer linguagem de texto, incluindo Python, HTML/CSS/JavaScript, Dart e Flutter. A compilação Flutter ainda depende dos SDKs e ferramentas instalados no computador.


## Controle operacional do Windows — perfil Pessoal

O painel **Controle avançado do Windows** está disponível em Controle do computador > Controle avançado do Windows, somente no perfil Pessoal. Cada operação pede confirmação e registra um resumo no log de permissões.

- Abrir um executável .exe escolhido pelo usuário, sem usar shell.
- Abrir arquivos e pastas escolhidos pelo usuário; copiar ou mover um arquivo para uma pasta selecionada, sempre com confirmação.
- Abrir Configurações do Windows e Gerenciador de Tarefas.
- Consultar processos em execução e solicitar o encerramento normal de um processo selecionado. Processos críticos e o próprio JARVIS são protegidos; não há encerramento forçado automático.
- Controlar mouse e teclado na sessão visível: clique em coordenadas da tela, digitação na janela em foco e atalhos de uma lista permitida. O PyAutoGUI mantém o failsafe ativo; mover o mouse para o canto superior esquerdo interrompe suas ações.
- Instalar um pacote PyPI por nome validado em um `.venv` local à pasta de projeto escolhida. No EXE empacotado, exige Python 3 externo (`py` ou `python`); não altera o ambiente interno do JARVIS. O comando não usa shell e a instalação exige confirmação, pois pacotes de terceiros podem executar código.
- Solicitar instalação de aplicativo por ID exato do WinGet. O instalador pode solicitar permissões próprias do Windows.

**Limites deliberados:** não há terminal livre, execução arbitrária de PowerShell/CMD, elevação administrativa, acesso a credenciais, desativação de antivírus/firewall, persistência oculta ou contorno de políticas. Ações destrutivas e financeiras não são automatizadas. O painel não transforma o JARVIS em administrador do Windows: as permissões da conta, UAC, antivírus, ACLs e políticas da organização continuam valendo. O perfil Escola bloqueia todo esse painel avançado.
## Perfis de acesso ao computador

O JARVIS EXE possui dois perfis configuráveis em **Configurações > Perfil de acesso ao computador**:

- **Pessoal:** libera as ações locais implementadas, incluindo o painel de controle operacional do Windows. Abrir programas, copiar/mover arquivos, instalar pacotes e controlar mouse/teclado exigem confirmações por ação. Não significa shell irrestrito, elevação de administrador ou acesso oculto.
- **Escola:** perfil restrito para uso em computadores da instituição. Limita a abertura de aplicativos a uma lista básica (VS Code, Bloco de Notas e Calculadora), restringe leitura/escrita/abertura de projetos à pasta `Documents/JarvisProjects`, permite somente análises estáticas aprovadas e navegação sujeita aos filtros da rede. Bloqueia captura de tela, auditoria fora da pasta de projetos, execução de testes de código, instalação de dependências e ações administrativas.
- **Registro:** decisões de permissão são registradas em `%APPDATA%/Jarvis/access_audit.jsonl`, sem guardar caminhos completos de arquivos.
- **Limite fundamental:** esses perfis são controles internos do aplicativo, não uma sandbox nem um substituto das políticas de TI. A conta do Windows, permissões NTFS, UAC, antivírus, filtros de rede e gerenciamento da escola continuam mandando. O JARVIS não tenta elevar privilégios nem contornar restrições impostas pela instituição.
- **Ainda não implementado:** controle visual inteligente que reconheça elementos de qualquer janela, execução arbitrária de comandos, instalação automática sem confirmação e acesso irrestrito a todo o disco. O controle atual é explícito, por coordenadas/atalhos permitidos e seletores do Windows.

## Evolução — fluxo de desenvolvimento por voz

- Durante uma sessão de voz ativa, o JARVIS fala as respostas sem exigir que a opção geral de leitura em voz esteja ligada.
- Ao pedir a criação de um projeto, o JARVIS prepara o manifesto, solicita confirmação por voz (“confirmar” ou “cancelar”) e grava os arquivos somente em `Documents/JarvisProjects`.
- Se o projeto criado contiver `main.py`, o JARVIS pode oferecer a execução por voz. A execução exige confirmação explícita, usa `shell=False`, limita o tempo a 30 segundos e captura a saída.
- O executor Python usa o `.venv` do projeto quando disponível; caso contrário, procura Python 3 instalado no Windows. Não instala dependências automaticamente.
- Comandos de voz: “rode python NOME_DO_PROJETO”, “teste python NOME_DO_PROJETO”, “analise python NOME_DO_PROJETO”, “analise dart NOME_DO_PROJETO” e “analise flutter NOME_DO_PROJETO”.
- Confirmações expiram após 60 segundos. “cancelar” não executa nada.
- **Limite de segurança:** executar um programa Python não é uma sandbox. O código roda com as permissões normais da conta do Windows e pode acessar recursos permitidos a essa conta. Execute apenas projetos em que confia. O perfil Escola continua bloqueando a execução.
- O reconhecimento de voz desta versão usa o serviço de transcrição do Google pela internet; a escuta é iniciada manualmente e pode ser interrompida pelo usuário.
- O fluxo automatiza a criação e a execução simples por voz, mas não transforma qualquer comando falado em shell livre. Flutter/Dart ainda oferecem análise/testes permitidos, não execução automática genérica.
