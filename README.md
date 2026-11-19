# JARVIS Android — projeto nativo inicial

Este projeto combina a interface web JARVIS com uma camada Android nativa em Kotlin.

## O que já está implementado

- Interface JARVIS em `app/src/main/assets/index.html` (tema âmbar original).
- Ponte JavaScript/Kotlin `JarvisAndroid`.
- Reconhecimento de fala nativo Android em português (`pt-BR`), com preferência por reconhecimento no dispositivo quando o serviço do aparelho oferece suporte.
- Síntese de voz nativa Android (`TextToSpeech`) com controle de velocidade e tom.
- Permissão de microfone solicitada em tempo de execução.
- Interrupção da fala e cancelamento do reconhecimento.
- Memória explícita local, notas, tarefas e histórico na interface.
- Backup completo em JSON e restauração validada com limites de tamanho e confirmação antes de substituir dados.
- Proteção do contexto: memórias são tratadas como dados do usuário, não como instruções privilegiadas.
- Retentativas nativas de reconhecimento com espera progressiva e pausa após seis falhas consecutivas, evitando ciclos infinitos de erro.
- WebViewAssetLoader para servir os arquivos locais em uma origem HTTPS local, evitando `file://`.
- Links externos são abertos no navegador; a ponte nativa fica disponível apenas na interface empacotada.

## O que ainda não está implementado

- APK pronto/assinado.
- Escuta com a tela apagada ou serviço de palavra de ativação permanente.
- Garantia de reconhecimento offline: o app tenta usar o serviço on-device se o Android disser que ele está disponível; caso contrário, usa o serviço de reconhecimento padrão. O pacote de idioma e o mecanismo instalado no aparelho determinam se funciona sem internet.
- Modelo de IA local embutido no APK. O campo de provedor continua aceitando um servidor compatível configurado pelo usuário. A integração Claude Artifact só existe dentro do Artifact e não acompanha o APK.
- Pesquisa web nativa, automação geral do Android ou execução de comandos arbitrários.

A API `SpeechRecognizer` do Android pode transmitir áudio para servidores remotos e a documentação oficial alerta que ela não foi projetada para reconhecimento contínuo ilimitado. Esta versão reinicia a captura após cada fala enquanto o app está em primeiro plano; não mantém microfone ligado em segundo plano.

## Como compilar

1. Abra a pasta `JARVIS_ANDROID` no Android Studio com suporte a Kotlin e Android Gradle Plugin 8.7.3.
2. Aguarde a sincronização do Gradle e a instalação do SDK Android 35.
3. Conecte um aparelho Android e execute `app`.
4. Autorize o microfone quando solicitado.
5. Toque no núcleo do JARVIS para iniciar a conversa por voz.

O projeto requer acesso à internet para baixar dependências Gradle na primeira compilação. Este ambiente de geração não contém Android SDK/Gradle e, portanto, não foi possível gerar ou testar um APK aqui.

## Configuração da IA

- Claude Artifact: disponível somente quando aberto dentro do Claude Artifact; não está presente no APK nativo. Ao iniciar no APK, o provedor muda automaticamente para “servidor compatível”, mas nenhum modelo de IA vem embutido.
- Servidor local: informe o endpoint e o modelo nas configurações. No Android, `localhost` significa o próprio telefone, não um computador remoto.
- Servidor remoto: prefira um backend HTTPS que mantenha as chaves de API no servidor. Não publique chaves secretas no HTML ou no APK.
- Para endpoint HTTP local, a configuração de segurança libera texto claro somente para `localhost` e `127.0.0.1`; o servidor ainda precisa permitir CORS para a origem `https://appassets.androidplatform.net`.

## Privacidade e segurança

- Notas, tarefas e memórias ficam no armazenamento local do WebView (`localStorage`). Limpar dados do app pode apagá-las; exporte um backup.
- O reconhecimento pode depender de serviços instalados pelo Android e suas políticas de privacidade.
- O app não escuta quando está em segundo plano; ao sair da tela, o reconhecimento é cancelado.
- O Modo Sério é um modo de planejamento com ferramentas limitadas, não uma autorização para controlar todo o dispositivo.


## Evolução 05
- Timeout de 45 segundos nas chamadas ao servidor de IA, com cancelamento preservado pelo botão Parar e mensagem específica quando o servidor demora demais.
- Mensagens de erro HTTP limitadas e higienizadas antes de serem exibidas.
- A interface explica o limite de tempo da chamada.
- Esta versão ainda precisa ser testada no navegador e no Galaxy A06; o APK não foi compilado nesta etapa.


## Evolução 06 — ferramentas Android limitadas (versão 0.6.0)

Esta versão adiciona duas ferramentas nativas, disponíveis apenas no APK Android:

- **Abrir aplicativos permitidos:** YouTube, Spotify, Chrome, WhatsApp, Google Maps, Play Store e YouTube Music. A lista é fechada no código Kotlin; não é possível informar um pacote arbitrário.
- **Pesquisar na web:** comandos como `pesquisar na internet notícias de tecnologia` abrem uma pesquisa Google no navegador padrão. O JARVIS não lê nem resume automaticamente os resultados; isso ainda exigirá um serviço de pesquisa/backend com fontes.

Exemplos de voz: `abrir Spotify`, `abrir WhatsApp`, `pesquisar na internet linguagem Python`. Se um app não estiver instalado, o JARVIS informa que não conseguiu abri-lo.

**Segurança:** as chamadas retornam por callback com tempo limite; apps são selecionados por allowlist. A função de pesquisa apenas abre uma URL HTTPS de pesquisa e não executa comandos arbitrários.

**Limitações de validação:** o HTML pode ser validado estaticamente, mas este ambiente não possui Android SDK/Gradle Wrapper para compilar o APK nem um Galaxy A06 para testar a abertura dos aplicativos.

- **Confirmação destrutiva reforçada:** apagar memórias, notas, tarefas ou histórico exige a frase específica “confirmo a exclusão”; respostas genéricas não autorizam a operação.


## Evolução 07 — diagnóstico de conexão da IA (0.7.0)

- Adicionado o botão **Testar conexão com a IA** nas configurações.
- O teste verifica se o endpoint tem formato de URL válido, exige HTTPS para servidores remotos e permite HTTP somente para `localhost`/`127.0.0.1`.
- O teste envia uma mensagem curta e mostra se o servidor respondeu.
- Melhorado o tratamento de respostas cujo campo `content` vem como texto ou como lista de blocos de texto.
- A chave permanece somente na sessão atual do app; ela não é gravada no histórico, nas preferências nem no backup.
- O provedor do APK continua sendo um endpoint compatível com a API de chat no formato OpenAI (`/v1/chat/completions`). Uma chave de Gemini ou Claude não funciona automaticamente nesse formato: é necessário endpoint compatível ou um backend que faça a adaptação.

**Importante:** o botão de teste não cria uma API nem corrige credenciais inválidas. Ele ajuda a identificar endpoint, modelo, autenticação, CORS e erros HTTP. Não coloque uma chave secreta em um APK que será compartilhado. Para um app distribuído, use um backend HTTPS com a chave guardada no servidor.


---

# Plano de evolução do JARVIS

A especificação completa está em [docs/ESPECIFICACAO_MESTRA.md](docs/ESPECIFICACAO_MESTRA.md). A ordem de entrega é:

1. **[JARVIS-APK](JARVIS-APK/README.md)** — Android, com prioridade para o Galaxy A06.
2. **[JARVIS-EXE](JARVIS-EXE/README.md)** — Windows, incluindo agente visual e modo Hacker defensivo autorizado.
3. **[JARVIS-COMPARTILHADO](JARVIS-COMPARTILHADO/README.md)** — backend, IA multi-provedor, memória, sincronização, autenticação e serviços comuns.

O desenvolvimento será feito em etapas e nesta branch de trabalho, preservando a branch principal. A ordem acima define a sequência de entrega; contratos temporários permitirão que o APK seja desenvolvido antes da implementação completa dos serviços compartilhados. Recursos só serão marcados como prontos depois de compilação e testes verificáveis.
