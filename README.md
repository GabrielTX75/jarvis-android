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
3. **[JARVIS-COMPARTILHADO](JARVIS-COMPARTILHADO/README.md)** — serviços opcionais e integrações de IA. Memória e dados pessoais permanecem locais em cada dispositivo; não haverá sincronização de memória APK/EXE.

O desenvolvimento será feito em etapas e nesta branch de trabalho, preservando a branch principal. A ordem acima define a sequência de entrega; contratos temporários permitirão que o APK seja desenvolvido antes da implementação completa dos serviços compartilhados. Recursos só serão marcados como prontos depois de compilação e testes verificáveis.

## Interface Android
A interface do APK usa agora a paleta azul-marinho e ciano, alinhada à identidade visual do JARVIS EXE. A alteração visual não significa que os recursos holográficos do EXE estejam disponíveis no Android.


## Evolução 08 — autorização de ferramentas e proteção da ponte Android

- Respostas JSON do modelo que pedem uma ferramenta são tratadas como propostas, não como autorização automática.
- Ações propostas pela IA exigem confirmação por voz, exceto consultas locais de baixo risco (bateria, hora, data, cálculo, status do código e descrição dos módulos).
- Toques na tela, digitação, exclusão de memórias/anotações e organização/desfazimento de arquivos exigem confirmação mesmo quando reconhecidos diretamente pela voz.
- A confirmação aceita “confirmar” ou “cancelar” e expira em 20 segundos. Silêncio, resposta ambígua ou expiração não executam a ação.
- Conteúdo de telas, páginas, notificações, documentos e mensagens é tratado no prompt como dado não confiável, nunca como instrução privilegiada.
- A ponte JavaScript não pode mais ler as chaves Gemini, Tavily, brapi ou Picovoice. A leitura pela interface fica limitada aos valores usados pelos fluxos atuais (Groq/IA, busca e PIN).
- O endpoint de IA é validado antes do envio: HTTPS é obrigatório para servidores remotos; HTTP só é aceito em `localhost`/`127.0.0.1`, e URLs com usuário/senha embutidos são recusadas. A regra também vale para as chamadas nativas do núcleo e do respondedor do WhatsApp.
- **Evolução 09:** o transporte de IA do APK foi movido para Kotlin. `getSecret("ai_key")` e `getSecret("groq_key")` não devolvem a chave à WebView; o segredo é lido no armazenamento criptografado e enviado pelo cabeçalho Authorization. A chave ainda passa temporariamente pelo JavaScript quando é digitada no campo da interface; uma entrada nativa e um backend HTTPS continuam sendo melhorias futuras para distribuição pública.

## CI Android — artefato separado de publicação

- Push em qualquer branch executa auditoria estática da WebView, verificação de sintaxe JavaScript, testes unitários e compilação do APK de depuração. O artefato fica retido por 1 dia quando a cota do GitHub Actions permite; build concluído não significa que o arquivo foi disponibilizado.
- O workflow não publica mais uma Release a cada push nem concede permissão de escrita ao job de build.
- Publicação da Release `apk-latest` exige execução manual do workflow, opção `publish_release=true` e branch `main`; esse job recompila o APK e não depende do armazenamento de artifacts.
- O arquivo publicado por esse fluxo é um APK de depuração para validação, não um instalador de produção assinado.


## Evolução 09 — isolamento da WebView e transporte nativo da IA

- A WebView só aceita o documento empacotado `/assets/index.html` na origem HTTPS local. Recursos ausentes nessa origem recebem 404 local; outras páginas dessa origem não podem navegar dentro da WebView privilegiada.
- Links externos só abrem no navegador do sistema quando usam HTTPS. HTTP externo e esquemas personalizados são bloqueados como navegação.
- O JavaScript foi extraído sem alterar a interface para `app/src/main/assets/app.js`. A CSP permite scripts somente da origem empacotada, bloqueia frames/objetos e impede scripts remotos. Estilos inline foram mantidos por compatibilidade com a interface existente.
- No APK, a chave de IA não é mais lida pelo JavaScript. A ponte oferece apenas o estado booleano `hasSecret`; o transporte nativo lê `ai_key` (ou a chave legada `groq_key`) do cofre criptografado.
- O endpoint é normalizado e validado. HTTPS remoto exige aprovação nativa para a URL completa; HTTP só é aceito em localhost/127.0.0.1. Credenciais embutidas, query, fragmento e redirecionamentos são recusados.
- O transporte limita tamanho do contexto/resposta, número de solicitações pendentes e tempo de rede; cancelamento desconecta a requisição. A lógica de continuação de respostas longas permanece na interface.
- O workflow agora executa auditoria estática da WebView, verificação de sintaxe do JavaScript, testes unitários e compilação. Artefatos temporários ficam retidos por 1 dia. A publicação manual na `main` recompila o APK e não depende do armazenamento de artifacts do Actions.
- Limitação residual: a chave ainda é digitada em um campo da WebView e passa transitoriamente pelo JavaScript para ser salva. A ponte `addJavascriptInterface` permanece para ferramentas legadas; migrá-la para `WebMessageListener` com origem/frame principal validados é uma etapa futura.

**Validação física:** esta evolução ainda precisa ser instalada e testada no Galaxy A06. Build em CI não substitui teste de microfone, voz, consumo, permissões e rede no aparelho.
