# Auditoria de segurança da WebView

## Escopo desta alteração

- O documento privilegiado aceito pela Activity fica limitado a `https://appassets.androidplatform.net/assets/index.html`.
- Recursos no host reservado são servidos somente pelo `WebViewAssetLoader`; caminhos inexistentes recebem 404 local, sem fallback para a rede.
- Navegação para outros documentos do mesmo host é bloqueada.
- Links externos só podem abrir no navegador do sistema quando usam HTTPS; HTTP e esquemas personalizados são bloqueados como navegação.
- O JavaScript principal foi movido, sem alterar seu conteúdo, para `app.js` e é carregado da mesma origem empacotada. A CSP usa `script-src 'self'`, sem `unsafe-inline`; estilos inline permanecem por compatibilidade com a interface legada.
- A CSP bloqueia frames, objetos incorporados e formulários para outras origens. O JavaScript da página não pode carregar scripts remotos.
- Cookies de terceiros, acesso a arquivos locais e janelas múltiplas permanecem desativados; Safe Browsing é habilitado explicitamente.

## Limitações que permanecem

O projeto ainda usa `addJavascriptInterface` para preservar ferramentas existentes de voz, captura de tela, WhatsApp, armazenamento seguro e geração de código. A CSP impede a execução de scripts inline injetados, mas não substitui a correção de possíveis XSS em pontos de inserção de HTML nem elimina o risco da ponte privilegiada.

A diretiva `connect-src` ainda permite HTTPS e os endpoints locais configuráveis pelo usuário, pois o app oferece provedores e servidores personalizados. Isso é flexível, mas não equivale a uma lista restrita de domínios. Uma arquitetura futura deve encaminhar chamadas e segredos pelo backend, em vez de expor chaves ao JavaScript da WebView.

O próximo passo de segurança deve migrar gradualmente a ponte para `WebMessageListener` com origem e frame principal validados, sem remover ferramentas antes de implementar e testar equivalentes.

## Permissões sensíveis preservadas

Esta alteração não remove permissões porque o código atual usa funcionalidades correspondentes: acesso a arquivos para transcrição/arquivos gerados, sobreposição para alertas, listener de notificações para WhatsApp, acessibilidade para ações de tela e MediaProjection para captura de tela. Elas devem continuar sendo habilitadas pelo usuário somente quando a função correspondente for necessária. Uma revisão separada deve avaliar alternativas de menor privilégio.

## Validação

`tools/verify_webview_security.py` verifica a política CSP sem `unsafe-inline`, o carregamento exclusivo de `app.js` local, a ausência de `eval`/`new Function`/`document.write`, frames e handlers inline, a restrição de origem e a política de cleartext. O workflow Android executa essa auditoria antes de compilar o APK.


## Transporte nativo da IA (Android)

- A chave `ai_key` continua armazenada em `EncryptedSharedPreferences`, mas `getSecret("ai_key")` agora retorna vazio. O JavaScript não carrega mais a chave para `S.apiKey`.
- As solicitações OpenAI-compatible são enviadas por `HttpURLConnection` no Android. O endpoint/modelo são lidos das preferências nativas; o segredo é lido no processo nativo e enviado somente no cabeçalho Authorization.
- Endpoints remotos exigem HTTPS e aprovação em diálogo nativo, com a origem aprovada armazenada no cofre criptografado. HTTP é permitido somente para `localhost` e `127.0.0.1`.
- Redirecionamentos HTTP são recusados para impedir que o cabeçalho Authorization seja encaminhado a outro host. Há limites de tamanho, quantidade de mensagens, tempo de conexão/resposta e número de solicitações pendentes.
- Cancelar no cliente desconecta a conexão nativa quando possível; ao colocar o app em segundo plano, as solicitações da WebView também são canceladas e recebem um erro de interrupção. Isso não garante que o provedor remoto interrompa processamento já recebido.
- Limite residual: o campo da chave ainda é digitado em uma página WebView e seu valor passa transitoriamente pelo JavaScript para ser salvo no cofre. A chave de busca também continua acessível ao JavaScript. Uma migração completa para entrada nativa e WebMessageListener permanece necessária.
- A mudança de host remoto exige confirmação nativa. A alteração de caminho dentro da mesma origem aprovada não pede nova confirmação.
- A interface aguarda a conclusão da configuração/aprovação nativa antes de enviar a primeira solicitação, evitando uma corrida entre salvar o endpoint e iniciar a chamada.

## Armazenamento de artifacts de CI

O APK de depuração é temporário e agora tem retenção de 1 dia; execuções duplicadas da mesma branch são canceladas. Isso reduz acúmulo futuro, mas não libera imediatamente a cota já ocupada: artifacts antigos ainda precisam expirar ou ser removidos pelo administrador do repositório.
