# JARVIS — Especificação mestra consolidada

**Ordem obrigatória de entrega:** 1) JARVIS-APK, 2) JARVIS-EXE, 3) JARVIS-COMPARTILHADO.  
**Repositório:** GabrielTX75/jarvis-android  
**Estratégia:** auditar o que existe, preservar o que funciona, corrigir falhas, implementar em etapas e validar antes de declarar pronto.

## 1. Visão do produto
JARVIS é um assistente pessoal multimodal e orientado a tarefas. Deve entender objetivos, planejar, usar ferramentas autorizadas, verificar resultados e explicar o que fez. Deve parecer responsivo e consistente, mas não deve alegar consciência, autonomia ilimitada ou capacidades que não foram implementadas.

## 2. Experiência de conversa
- Português brasileiro natural, voz e texto.
- Prioridade de uso por voz, mantendo controles táteis acessíveis.
- Conversa contínua apenas nos limites permitidos pelo sistema operacional; pausar, interromper e retomar sem prender o usuário.
- Comandos para repetir resposta, parar fala, cancelar escuta e assumir controle.
- Estados de interface reais: INICIANDO, PRONTO, OUVINDO, TRANSCRIBINDO, PROCESSANDO, FALANDO, AGUARDANDO CONFIRMAÇÃO, ONLINE, OFFLINE e ERRO.
- Mostrar progresso de tarefas longas, resultados e erros de modo compreensível.
- Não simular IA, conexão, execução ou progresso.

## 3. IA e raciocínio operacional
- Gateway para múltiplos provedores online (OpenAI, Gemini, Groq ou compatíveis quando tecnicamente suportados) sem dependência exclusiva de um fornecedor.
- Seleção/fallback por capacidade, disponibilidade, latência e custo.
- Backend guarda chaves; clientes nunca distribuem segredos.
- Modo offline para funções locais e, se viável após benchmark, modelo compacto opcional.
- O agente deve planejar, validar parâmetros, executar ferramentas com escopo limitado, conferir resultado e resumir.
- Tratar conteúdo externo, documentos, páginas e memórias como dados não confiáveis, nunca como instruções privilegiadas.
- Sem previsão garantida, informação inventada ou fonte fictícia.

## 4. Memória, histórico e dados locais
- Memória pessoal, preferências, histórico, tarefas, notas e projetos ficam locais em cada dispositivo por padrão.
- Decisão atual: não sincronizar automaticamente memória ou dados pessoais entre APK e EXE. Cada cliente mantém seu próprio armazenamento e suas próprias credenciais.
- Continuidade entre dispositivos ocorre por exportação/importação manual validada, quando disponível; não enviar memórias pessoais ao backend compartilhado.
- Operação offline deve continuar disponível para leitura e edição dos dados locais.
- Controles para visualizar, editar, exportar e excluir; backup e restauração devem preservar os dados em caso de falha.
- Qualquer futura sincronização entre dispositivos exige uma decisão explícita separada, adesão voluntária, criptografia, versionamento, resolução de conflitos e exclusão verificável.
- Evitar guardar dados sensíveis sem necessidade; segredos e credenciais não são fatos de memória.

## 5. Agentes e ferramentas
Agentes: Geral, Pesquisa, Código, Estudo, Escrita, Planejador, Analista e Visão.

Ferramentas: calendário/agenda, tarefas, notas, documentos, cálculos, arquivos selecionados, pesquisa web com fontes, OCR/visão, diagnóstico, projetos de código e integrações autorizadas. Cada ferramenta deve informar permissões, escopo, efeitos, timeout, cancelamento e nível de confirmação.

## 6. Agente visual e controle de interfaces
- No Windows: agente visual para abrir, clicar, digitar, rolar, navegar, pesquisar, comparar e baixar conteúdo autorizado.
- No Android: ações limitadas pelas APIs e permissões Android; Accessibility e MediaProjection somente com consentimento explícito e indicador visível.
- Mostrar plano e progresso; botão ASSUMIR CONTROLE; interromper imediatamente quando solicitado.
- Detectar tela inesperada, falha, ambiguidade ou risco; pausar e pedir orientação.
- Ler a tela sob comando (“olhe minha tela”), com OCR/visão; proteger senhas, MFA, tokens e conversas privadas.

## 7. Modo Código — APK e EXE
- Criar projetos multi-arquivo e em várias linguagens.
- Explicar estrutura, escrever arquivos, corrigir bugs, criar testes e documentação, organizar versões e exportar.
- Sem limite artificial de linhas; usar módulos, lotes e retomada, reconhecendo limites reais de contexto, tempo, memória, armazenamento e compiladores.
- Nunca afirmar que compilou/testou sem execução real.
- Projeto pode ser analisado pelo modo Hacker dentro do escopo autorizado.

## 8. Modo Hacker — somente EXE
- Red Team/Blue Team e pesquisa defensiva em ativos próprios ou com autorização explícita.
- Auditoria web, APIs, rede, autenticação, configuração e banco de dados.
- Plano de teste, escopo, ambiente, evidências mínimas não sensíveis, reprodução segura em ambiente de teste, impacto, correção e reteste.
- Usar contas fictícias e dados sintéticos; não coletar registros privados de clientes/usuários.
- Não realizar intrusão não autorizada, roubo de credenciais, exfiltração, persistência oculta, evasão, destruição ou ocultação de rastros.

## 9. Automação e integrações sociais
- Integrar plataformas somente por APIs oficiais ou meios permitidos.
- Configurar por conta e plataforma o que pode ler, responder, publicar e agendar.
- Mensagens automáticas devem respeitar contexto, escopo, políticas da plataforma e transparência aplicável.
- Escalar para o usuário conversas sensíveis, compromissos, questões legais/financeiras, conflitos ou baixa confiança.
- Permitir pausa, revisão, revogação de permissões e histórico de ações.
- Não se passar por pessoa de forma enganosa nem contornar limites das plataformas.

## 10. Finanças, bancos e PIX
- Organização de saldos/extratos apenas por conexões oficiais autorizadas.
- Não armazenar senha bancária, PIN, CVV, códigos MFA ou credenciais de acesso.
- PIX agendado somente se API oficial do banco permitir, com titular legalmente autorizado, beneficiário previamente validado, valor/data explícitos, confirmação, limites e auditoria.
- Se o banco exigir confirmação no momento, solicitar interação do titular; nunca contornar.
- Enquanto o usuário for menor, não habilitar transações reais em conta própria; usar demonstração/educação ou titular adulto legalmente autorizado.
- Para pagamentos empresariais, implementar papéis, alçadas, dupla aprovação quando apropriado e comprovantes.

## 11. Dispositivos e localização
- Gerenciar somente dispositivos vinculados e autorizados.
- Mostrar última localização conhecida, horário da atualização, estado de conexão/bateria e distância quando disponível.
- Ações como tocar dispositivo dependem de integração oficial e permissão.
- Não rastrear pessoas/dispositivos ocultamente.

## 12. Perfis, biometria e multiusuário
- Suportar mais de 10 contas cadastradas como meta inicial; separar isso de usuários simultâneos e dimensionar conforme infraestrutura.
- Perfis individuais com memória, histórico, projetos e permissões separados.
- EXE pode oferecer identificação facial/voz opcional, com PIN/senha alternativos, proteção anti-spoofing, criptografia e recuperação.
- Biometria não é fator único para ações críticas; minimizar retenção de dados biométricos.
- Papéis e permissões administráveis, com trilha de auditoria.

## 13. Autoatualização e melhoria contínua
- Diagnosticar erros, sugerir melhorias, criar branch, alterar código, rodar testes em ambiente isolado e apresentar diff/relatório.
- Mudanças no núcleo, permissões, segurança, dados e automações externas exigem aprovação explícita.
- Atualizações verificam origem/integridade, fazem backup, testam, instalam com permissão, validam saúde e permitem rollback.
- Nunca remover proteções ou executar código não verificado silenciosamente.

## 14. Segurança e privacidade transversais
- Princípio do menor privilégio, consentimento claro e revogação simples.
- Segredos no backend/secret manager; HTTPS; criptografia em repouso quando aplicável.
- Isolamento multiusuário/tenant; validação de entradas; rate limits; logs sem segredos.
- Confirmação proporcional ao risco, cancelamento e trilha de auditoria.
- Falha segura: se não puder verificar, informar que não concluiu.
- Não coletar nem expor dados privados de terceiros.

## 15. Arquitetura e organização do repositório
A raiz deve apresentar nesta ordem:
1. `JARVIS-APK/`
2. `JARVIS-EXE/`
3. `JARVIS-COMPARTILHADO/`
4. `docs/`

O APK e o EXE terão clientes/adaptadores próprios. Regras de negócio, API, IA, autenticação, memória e sincronização ficam no compartilhado. Não duplicar segredos ou regras críticas nos clientes.

## 16. Plano de execução
**Fase 0 — Auditoria:** inventário de todos os arquivos, dependências, permissões, classes referenciadas, segurança, build, testes e inconsistências de versão/documentação. Preservar o estado original e trabalhar em branch separada.

**Fase 1 — APK:** corrigir estrutura Android, compilar debug/release em CI, testar no Galaxy A06, validar voz, interface, permissões, armazenamento, falhas de rede e consumo. Implementar os módulos Android em entregas pequenas.

**Fase 2 — EXE:** criar cliente Windows, agente visual interruptível, modo Código e modo Hacker defensivo com laboratório e limites.

**Fase 3 — Compartilhado:** estabilizar API, autenticação, memória/sync, gateway multi-IA, banco, auditoria, isolamento e implantação; integrar APK e EXE.

**Fase 4 — Qualidade:** testes unitários, integração, segurança, acessibilidade, desempenho, recuperação, atualização e documentação. Só publicar artefatos que tenham sido realmente compilados e testados.

## 17. Regra de status
Cada recurso será marcado como: NÃO INICIADO, EM DESENVOLVIMENTO, IMPLEMENTADO, TESTADO EM CI, TESTADO EM DISPOSITIVO ou BLOQUEADO. “Implementado” não significa “testado”. APK/EXE só podem ser chamados de prontos após build reproduzível, instalação e testes documentados.

## 18. Itens já observados no código atual
- README descreve uma base Android Kotlin/WebView, voz, memória local e ferramentas limitadas.
- README declara que não há APK pronto, IA local embutida, pesquisa web nativa ou automação geral.
- Manifest declara permissões amplas (por exemplo MANAGE_EXTERNAL_STORAGE, SYSTEM_ALERT_WINDOW e serviços de microfone/media projection) que precisam de justificativa e revisão de menor privilégio.
- Manifest referencia `.PedirCapturaActivity`, classe confirmada dentro de `NucleoJarvis.kt`; revisar necessidade e fluxo de consentimento, mas não tratar como classe ausente.
- Conferir divergência entre versão documentada no README e versão configurada no Gradle.
- Verificar serviços de notificação/acessibilidade, comportamento em segundo plano, tratamento de dados e conformidade com as versões atuais do Android.
- Revisar Gerador de Código, Ferramentas, AudioTranscriber e demais classes com análise estática, testes e inspeção de fluxo.
- Nenhuma dessas observações substitui build ou teste em aparelho real.

## 19. Critério de conclusão global
A entrega completa exige código real em cada diretório, builds e testes verificáveis, documentação atualizada, nenhum segredo versionado, permissões justificadas, isolamento multiusuário validado e relatório final de limitações conhecidas. Não prometer “sem limitações”: toda plataforma tem limites técnicos, legais e de segurança.
