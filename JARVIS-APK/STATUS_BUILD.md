# Build do APK Android

Este diretório acompanha a entrega Android em primeiro lugar.

- Saída CI: APK de depuração para instalação e validação inicial.
- Compatibilidade declarada: Android 8.0 (API 26) ou superior.
- Dispositivo-alvo de validação: Samsung Galaxy A06.
- Estado: aguardando compilação automatizada; ainda não validado em dispositivo físico.


## Verificação CI — 25/11/2026
- Na execução anterior (commit `b8ab940`), `testDebugUnitTest` e `assembleDebug` concluíram com sucesso.
- O upload do APK falhou por cota de armazenamento de artifacts do GitHub Actions. Portanto, houve compilação, mas não houve arquivo de artifact disponível para baixar.
- A retenção foi reduzida para 1 dia. A publicação manual na `main` agora compila e publica diretamente, sem depender do armazenamento de artifacts.
- Instalação e validação no Galaxy A06: PENDENTES.
