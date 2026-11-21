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
