# JARVIS APK — Android primeiro

## Objetivo
Construir a primeira versão utilizável do JARVIS para Android, priorizando o Samsung Galaxy A06 e fluxos de desenvolvimento/uso pelo celular. O APK deve compartilhar identidade, conta, memória e projetos com a futura versão Windows por meio do backend comum, sem depender de um computador para uso diário.

## Capacidades previstas
- Conversa em português brasileiro por voz e texto, com interrupção, repetição da resposta, controle de velocidade/voz e estados reais (iniciando, pronto, ouvindo, transcrevendo, processando, falando, aguardando confirmação, online, offline e erro).
- IA online por endpoint compatível com OpenAI; o APK agora sugere Groq (`https://api.groq.com/openai/v1/chat/completions`) e o modelo `openai/gpt-oss-120b` como configuração inicial. A chave é inserida pelo usuário e guardada no armazenamento criptografado do Android; não está embutida no APK. Fallback automático entre provedores ainda não foi implementado.
- Modo local/offline para funções que realmente possam rodar no aparelho: notas, tarefas, cálculos, histórico local e, após avaliação de desempenho, modelo compacto opcional. O A06 não deve ser tratado como capaz de executar modelos grandes.
- Memória e histórico locais neste aparelho, com controles para visualizar, exportar e apagar dados. Não sincroniza com outros dispositivos.
- Visão de tela sob comando explícito (“olhe minha tela”), usando APIs Android adequadas, OCR/acessibilidade e captura autorizada; indicador visível durante captura e botão de parar.
- Ferramentas Android com permissões mínimas: abrir apps por allowlist, pesquisar, calendário/lembretes, arquivos escolhidos pelo usuário e compartilhamento.
- Notas, tarefas, documentos, leitura/OCR de imagens, pesquisa com fontes, estudo, escrita, planejamento, análise e ajuda com código.
- Modo Código no APK: criar e organizar projetos multi-arquivo e linguagens, explicar, testar quando houver ambiente compatível e exportar arquivos; sem limite artificial de linhas, respeitando limites reais de memória/contexto/armazenamento.
- Integrações sociais apenas por APIs oficiais ou mecanismos permitidos, com escopos por plataforma, transparência e controles para pausar/revogar automações.
- Acessibilidade e operação em segundo plano somente quando a plataforma permitir e com consentimentos explícitos; não prometer escuta permanente nem execução impossível em versões do Android.

## Segurança obrigatória
- Não capturar ou enviar senhas, códigos MFA, tokens, dados bancários ou conversas privadas indiscriminadamente.
- Não armazenar senhas bancárias, PINs, CVVs ou códigos de uso único.
- Ações destrutivas, pagamentos, mensagens sensíveis e alterações externas importantes exigem confirmação adequada.
- Não executar comandos arbitrários vindos da IA sem validação e autorização.
- Permissões explicadas no momento de uso, revogáveis e limitadas ao necessário.
- HTTPS para tráfego remoto; segredos somente no backend; logs sem conteúdo sensível.
- Para menores de idade, não habilitar transferências financeiras reais em contas próprias; funcionalidades financeiras ficam em modo de demonstração/educacional ou sob titular adulto legalmente autorizado.

## Critérios de aceite
1. Compilar APK debug e release reproduzivelmente em CI.
2. Instalar e testar em aparelho Android real, incluindo Galaxy A06.
3. Testar voz, interrupção, falhas de rede, modo offline e restauração local.
4. Verificar permissões, privacidade, consumo de RAM/bateria e comportamento com tela apagada.
5. Cada ferramenta deve reportar sucesso somente após confirmação do sistema/serviço.
6. Documentar limitações reais; não exibir estados falsos nem alegar ações não realizadas.

## Lembretes e notificações (implementação inicial)
- Comandos em português para compromissos com horário, por exemplo: “JARVIS, me avise da reunião às 15h” ou “amanhã às 9:30”.
- O alarme é programado para 10 minutos antes; se faltarem menos de 10 minutos, o aviso é programado para o momento atual.
- O Android exibe uma notificação local. A permissão de notificações precisa estar autorizada.
- O Android pode exigir a permissão especial “Alarmes e lembretes” para precisão; sem ela o sistema usa alarme sujeito a atrasos. O comportamento após reinicialização do aparelho ainda precisa ser implementado/testado.
- Envio de mensagens para contatos e chamadas automáticas ainda não estão implementados. Ações de chamada devem abrir o discador e deixar o usuário confirmar.

## Estado atual
Este diretório é a organização-alvo. A implementação existente ainda precisa ser migrada/revisada e testada; este documento não afirma que as funções acima já estejam prontas.


## Cofre local de APIs — implementação em desenvolvimento
- A tela Configurações > Chaves e Senhas passa a oferecer campos para Groq, Gemini, Tavily e brapi.
- No APK instalado, as credenciais são gravadas pelo bridge nativo em EncryptedSharedPreferences (chaves e valores criptografados com AndroidX Security).
- Os campos são limpos após salvar e o status mostra apenas se existe uma credencial; os valores não são colocados no localStorage, settings JSON, HTML ou Git.
- Há testes de conexão individuais para Groq, Gemini, Tavily e brapi. Os testes consultam os endpoints oficiais e mostram apenas sucesso ou código HTTP/erro resumido.
- O botão de apagar remove as quatro credenciais de API e a chave legada da IA; a opção de redefinir o cofre continua apagando também o PIN do cofre.
- A chave Groq continua compatível com o campo de IA existente. As chaves Gemini, Tavily e brapi são armazenadas e testáveis; a integração funcional de cada serviço com os módulos de IA/pesquisa/finanças é uma etapa separada.
- O cofre e a memória são locais a este APK/aparelho. Não haverá sincronização automática com Windows ou outros dispositivos.


## Evolução 09 — IA nativa e isolamento da WebView

No APK, a interface envia as mensagens ao bridge nativo, mas não recebe a chave da IA. O Kotlin consulta o endpoint e o modelo salvos no Android, lê a chave do `EncryptedSharedPreferences` e faz a chamada HTTPS diretamente. A URL remota completa precisa ser aprovada em um diálogo nativo; HTTP é aceito somente em localhost/127.0.0.1. O transporte recusa redirecionamentos e limita contexto, resposta, concorrência e tempo.

A interface visual foi preservada. O JavaScript agora é um arquivo local `app.js`, protegido por CSP sem scripts inline/remotos. A entrada da chave ainda passa temporariamente pelo JavaScript do campo; uma entrada nativa e um gateway HTTPS são melhorias futuras. Não há teste físico no Galaxy A06 nesta etapa.


## Evolução 10 — credenciais nativas e confiabilidade da escuta

- A interface WebView não lê mais o token do servidor de busca nem as chaves Gemini, Tavily, brapi ou Picovoice. A pesquisa autenticada usa o contrato existente (GET /busca?q=... com o cabeçalho X-Jarvis-Token), executado pelo Kotlin com o token vindo do armazenamento criptografado.
- O transporte de pesquisa exige endpoint HTTPS remoto (HTTP apenas em localhost/127.0.0.1), recusa redirecionamentos, limita a resposta a 256 KB e retorna no máximo cinco resultados com campos limitados.
- A escuta em segundo plano só inicia depois que o Android concede a permissão de microfone. Se a permissão for negada, a preferência é revertida para desligada; se o serviço não puder iniciar, o app não mantém um estado falso de escuta ativa.
- A notificação persistente não exibe mais trechos de fala reconhecidos. Erros de leitura do microfone provocam tentativa limitada de recuperação; após três falhas consecutivas, a escuta é pausada.
- Foram adicionados testes unitários para a classificação de resultados de leitura de áudio e verificações estáticas para o isolamento das credenciais.
- Build e testes desta evolução: aguardando execução do GitHub Actions. Instalação e validação no Galaxy A06 continuam pendentes.
