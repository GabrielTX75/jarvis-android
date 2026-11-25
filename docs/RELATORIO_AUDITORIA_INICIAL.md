# Relatório de auditoria inicial — JARVIS

**Escopo desta rodada:** inspeção estática do repositório na branch `main`, manifest, Gradle, workflow de CI e arquivos Kotlin/HTML.  
**Não executado:** compilação, testes automatizados, execução em emulador ou teste físico no Galaxy A06. Portanto, este documento não certifica que o aplicativo compila ou funciona.

## Correção de uma observação anterior
A classe `PedirCapturaActivity` **existe** dentro de `NucleoJarvis.kt`. A declaração no Manifest não é uma referência órfã. A primeira leitura isolada do arquivo principal não mostrou que a classe estava no arquivo do núcleo; a árvore completa e o conteúdo de `NucleoJarvis.kt` confirmaram sua existência.

## Achados prioritários

### P0 — publicação de APK
- O workflow `.github/workflows/build-apk.yml` executa `assembleDebug` e, na branch principal, publica esse APK de depuração em uma GitHub Release.
- Isso não equivale a um APK de produção assinado. A publicação deve ser separada: artefato debug para testes; release com `assembleRelease`, assinatura protegida por GitHub Secrets e validação da assinatura.
- O workflow não contém etapa explícita de testes unitários, lint ou análise estática antes da publicação.
- O workflow concede `contents: write` no nível global. Reduzir permissões por job e conceder escrita apenas ao job que realmente publica release.

### P1 — permissões e privacidade Android
- O Manifest declara `MANAGE_EXTERNAL_STORAGE`, `SYSTEM_ALERT_WINDOW`, acesso a notificações, acessibilidade e serviços de microfone/captura. Cada permissão precisa de justificativa de produto, solicitação contextual e alternativa menos invasiva.
- Avaliar Storage Access Framework/MediaStore em vez de acesso amplo a todos os arquivos, especialmente para Downloads e áudios.
- Acessibilidade e Notification Listener podem revelar conteúdo sensível. Limitar coleta ao comando/escopo escolhido, filtrar dados sensíveis, não persistir conteúdo desnecessário e oferecer desligamento claro.
- A captura de tela via MediaProjection precisa de consentimento Android, indicador visível, escopo temporal e encerramento imediato quando o usuário parar.
- Verificar compatibilidade real do serviço de microfone em segundo plano com Android 14/15/16 e restrições do fabricante; não prometer escuta permanente.

### P1 — ponte WebView e execução de ações
- `MainActivity` habilita JavaScript e expõe `NativeBridge` via `addJavascriptInterface`. O WebViewAssetLoader e a origem local dedicada são boas medidas, mas é necessário garantir que conteúdo remoto nunca seja carregado na mesma WebView privilegiada.
- Revisar todos os métodos expostos na ponte: validação de argumentos, tamanho de entradas, permissões, confirmação por risco, tratamento de exceções e chamadas fora da thread principal.
- Revisar `Acoes.kt` e `JarvisAcessibilidade.kt`: ações de ler tela, tocar, digitar e responder mensagens devem ter escopo, visibilidade, cancelamento e confirmação apropriados. Não tratar texto de página ou mensagem como instrução confiável.
- O WebView está configurado com mixed content em modo de compatibilidade; avaliar se é necessário e restringir ao mínimo. A política de cleartext e a configuração de rede devem ser testadas.

### P1 — mensagens automáticas
- `WhatsAppNotificationService` pode responder automaticamente em segundo plano quando a configuração `auto` está ativa.
- Antes de expandir, criar controles por contato/grupo, limite de assuntos, pausa global, histórico auditável e escalonamento de mensagens sensíveis (dinheiro, localização, compromissos, saúde, assuntos legais ou baixa confiança).
- Não usar conteúdo de notificações como autorização para ações financeiras ou outras operações externas importantes.

### P1 — armazenamento e geração de código
- `Gerador.kt` grava arquivos em Downloads e mantém estado em SharedPreferences; verificar atomicidade, retomada, codificação, limites de tamanho, tratamento de resposta truncada e validação do arquivo final.
- A geração por blocos não garante por si só que o código final compila ou é coerente. Adicionar validação por linguagem em ambiente isolado e nunca executar código gerado automaticamente.
- `Organizador.kt` depende de acesso amplo ao armazenamento e move arquivos; testar colisões, interrupção no meio do processo, rollback parcial e caminhos inesperados.

### P2 — versões e documentação
- `app/build.gradle.kts` declara `versionCode = 17` e `versionName = 0.17.0`.
- O README descreve a evolução 0.7.0. Corrigir a documentação ou alinhar a versão, mantendo changelog verificável.
- Gradle usa Android Gradle Plugin 8.7.3 e Kotlin 2.0.21; workflow instala Gradle 8.10 e Java 17. Confirmar a combinação em CI com build limpo.
- O modelo Vosk é baixado durante o workflow para dentro de assets. Registrar origem, versão, checksum/licença e impacto no tamanho do APK; não depender de download não verificado.

## Pontos positivos observados
- WebViewAssetLoader usa origem HTTPS local em vez de `file://`.
- `allowFileAccess` e `allowContentAccess` estão desativados.
- Links externos são encaminhados ao navegador em vez de navegar na WebView privilegiada.
- Há controles de cancelamento para voz e timeouts em chamadas de IA em partes do código.
- Ações externas de ligação/mensagem são descritas como fluxo que abre a tela apropriada para confirmação, embora o fluxo completo ainda precise de testes.
- O gerador de código grava incrementalmente e oferece interrupção/retomada, mas ainda precisa de validação real.

## Plano de validação antes de declarar APK pronto
1. Build limpo debug e release.
2. Lint Android e testes unitários.
3. Testes instrumentados de permissões, voz, TTS, rotação, ciclo de vida, rede e armazenamento.
4. Testes de segurança da ponte WebView e origem de conteúdo.
5. Testes de acessibilidade, Notification Listener e MediaProjection com consentimento e revogação.
6. Testes de falhas, retomada, arquivos grandes, pouco armazenamento e bateria.
7. Instalação/execução no Galaxy A06; registrar Android/One UI, RAM, consumo, logs e limitações.
8. Assinatura, verificação do APK final e publicação apenas após todos os gates.

## Estado
- Auditoria estática inicial: EM ANDAMENTO.
- Build/execução real: NÃO TESTADO.
- APK de produção: NÃO PRONTO.
- Correções de código: ainda não iniciadas nesta branch; esta branch contém documentação de especificação e auditoria.


## Reauditoria de segurança — 25/11/2026
A implementação inicial da branch de trabalho agora inclui CSP, restrição da origem privilegiada da WebView, transporte nativo de IA e aprovação da URL remota completa. A chave de IA deixou de ser retornada por `getSecret`; a interface recebe apenas um booleano de presença. Consulte `SECURITY_AUDIT_WEBVIEW.md` e `tools/verify_webview_security.py` para os controles e verificações automatizadas.

O relatório inicial continua descrevendo a fotografia da branch `main` auditada originalmente. A reauditoria não substitui build, teste instrumentado ou validação física no Galaxy A06.
