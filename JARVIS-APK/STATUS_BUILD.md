# Build do APK Android

Este diretório acompanha a entrega Android em primeiro lugar.

- Saída CI: APK de depuração para instalação e validação inicial.
- Compatibilidade declarada: Android 8.0 (API 26) ou superior.
- Dispositivo-alvo de validação: Samsung Galaxy A06.
- Estado: `assembleDebug` e testes unitários confirmados no CI do commit `0b54fdbe`; upload do artefato bloqueado pela cota de armazenamento; ainda não validado em dispositivo físico.


## Verificação CI — 25/11/2026 (commit `0b54fdbe`)
- Auditoria estática da WebView/transporte de IA: SUCESSO.
- Verificação de sintaxe do `app.js`: SUCESSO.
- `testDebugUnitTest`: SUCESSO.
- `assembleDebug`: SUCESSO.
- Upload do APK: FALHOU porque a cota de armazenamento de artifacts do GitHub Actions foi atingida. O runner confirmou que havia 1 APK para upload, mas o GitHub recusou criar o artifact. Portanto, o APK foi compilado, porém não ficou disponível para baixar nesta execução.
- Execução: https://github.com/GabrielTX75/jarvis-android/actions/runs/45713933161
- A retenção foi reduzida para 1 dia. A publicação manual na `main` recompila e publica diretamente, sem depender de artifacts. A cota atual ainda precisa ser liberada pelo GitHub ou por exclusão de artifacts antigos.
- Instalação e validação no Galaxy A06: PENDENTES.
