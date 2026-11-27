# JARVIS Compartilhado — núcleo e serviços comuns

## Objetivo
Manter uma única lógica de produto para Android e Windows. APK e EXE serão clientes diferentes que consomem serviços comuns, com capacidades específicas isoladas em adaptadores de plataforma.

## Arquitetura-alvo
- API HTTPS com backend Python/FastAPI.
- PostgreSQL/Supabase para autenticação, dados estruturados e isolamento por usuário/tenant; Storage para arquivos selecionados.
- Núcleo de orquestração: intenção → plano → ferramentas permitidas → execução → verificação → relatório.
- Adaptadores de IA no servidor para provedores distintos; chaves em secrets do backend, rotação e limites de uso.
- Contratos e formatos de dados comuns para projetos e ferramentas, com adaptadores de armazenamento locais por plataforma.
- Memória pessoal, histórico, notas e tarefas permanecem no dispositivo; não há sincronização automática APK↔EXE nem envio dessas memórias ao backend.
- Exportação/importação manual validada pode transportar dados escolhidos pelo usuário. Uma sincronização futura só será projetada após decisão explícita e opt-in, com criptografia, versionamento, conflitos e exclusão verificável.
- Catálogo de ferramentas com permissões, escopos, confirmação, timeout, cancelamento e trilha de auditoria.
- Agentes especializados: Geral, Pesquisa, Código, Estudo, Escrita, Planejamento, Analista e Visão.
- Serviços de atualização, telemetria mínima opt-in, diagnóstico e observabilidade sem conteúdo privado.

## Regras de execução
1. O modelo não recebe acesso irrestrito ao sistema operacional ou banco.
2. Toda ferramenta declara entradas, permissões, efeitos e política de confirmação.
3. Operações repetíveis devem ser idempotentes quando possível.
4. O agente verifica o resultado real antes de declarar sucesso.
5. Falhas e estados desconhecidos interrompem ações potencialmente perigosas.
6. Dados de usuários diferentes são isolados no servidor e nos clientes.
7. Segredos nunca são colocados no repositório, APK, EXE ou logs.

## Serviços compartilhados previstos
- Autenticação, perfis, papéis e sessões.
- Gateway multi-provedor de IA e limites de custo.
- Gateway multi-provedor de IA e limites de custo.
- Pesquisa web com fontes e data de consulta.
- Visão/OCR processada conforme consentimento.
- Contratos de exportação/importação e backup/restauração locais, sem sincronização automática de dados pessoais.
- Registro de ações, aprovações, auditoria e diagnóstico.
- Gerenciamento de dispositivos vinculados, com consentimento e possibilidade de desvincular.

## Dados financeiros
O núcleo pode oferecer organização financeira e integração futura com APIs bancárias oficiais. Não deve guardar credenciais bancárias nem códigos MFA. PIX agendado ou pagamento só poderá ser executado se o banco oferecer API oficial, o titular tiver autorização legal, beneficiário/valor/data forem confirmados e as regras do banco forem atendidas. Caso o banco exija nova autenticação na hora, o JARVIS deve solicitar a interação do titular; nunca contornar esse requisito.

## Multiusuário e empresa
Separar usuários registrados de sessões simultâneas. Permitir múltiplos perfis e tenants, com RBAC, isolamento de dados, limites configuráveis e trilha de auditoria. Escalabilidade depende da infraestrutura e não deve ser prometida como ilimitada.

## Critérios de aceite
- Testes automatizados de autenticação, isolamento e autorização.
- Testes de backup/restauração local e confirmação de que memórias pessoais não são enviadas ao backend por padrão.
- Testes de contrato para cada provedor de IA.
- Testes de falha de rede, repetição idempotente, conflitos e recuperação.
- Testes de vazamento de segredos e dados entre usuários.
- Documentação de implantação, backups, restauração, custos e limites.
