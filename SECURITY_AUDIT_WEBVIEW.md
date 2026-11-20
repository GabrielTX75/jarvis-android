# Auditoria de segurança da WebView

## Escopo desta alteração

- O documento privilegiado aceito pela Activity fica limitado a `https://appassets.androidplatform.net/assets/index.html`.
- Recursos no host reservado são servidos somente pelo `WebViewAssetLoader`; caminhos inexistentes recebem 404 local, sem fallback para a rede.
- Navegação para outros documentos do mesmo host é bloqueada.
- Links externos só podem abrir no navegador do sistema quando usam HTTPS; HTTP e esquemas personalizados são bloqueados como navegação.
- A CSP bloqueia scripts remotos, frames, objetos incorporados e formulários para outras origens. Mantém scripts e estilos inline porque a interface atual é um único HTML legado.
- Cookies de terceiros, acesso a arquivos locais e janelas múltiplas permanecem desativados; Safe Browsing é habilitado explicitamente.

## Limitação que permanece

O projeto ainda usa `addJavascriptInterface` para preservar ferramentas existentes de voz, captura de tela, WhatsApp, armazenamento seguro e geração de código. A CSP e o bloqueio de navegação reduzem a superfície de ataque, mas não tornam um XSS inline inofensivo. O próximo passo de segurança deve migrar gradualmente essa ponte para `WebMessageListener` com origem e frame principal validados, sem remover as ferramentas atuais antes de implementar e testar equivalentes.

## Permissões sensíveis preservadas

Esta alteração não remove permissões porque o código atual usa funcionalidades correspondentes: acesso a arquivos para transcrição/arquivos gerados, sobreposição para alertas, listener de notificações para WhatsApp, acessibilidade para ações de tela e MediaProjection para captura de tela. Elas devem continuar sendo habilitadas pelo usuário somente quando a função correspondente for necessária. Uma revisão separada deve avaliar alternativas de menor privilégio.

## Validação

`tools/verify_webview_security.py` verifica a política CSP, ausência de scripts remotos/frames/handlers inline, restrição de origem e a política de cleartext. O workflow Android executa essa auditoria antes de compilar o APK.
