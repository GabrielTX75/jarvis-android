# JARVIS Compartilhado — núcleo e serviços comuns

## Objetivo
Manter uma única lógica de produto para Android e Windows. APK e EXE serão clientes diferentes que consomem serviços comuns, com capacidades específicas isoladas em adaptadores de plataforma.

## Arquitetura-alvo
- API HTTPS com backend Python/FastAPI.
- PostgreSQL/Supabase para autenticação, dados estruturados e isolamento por usuário/tenant; Storage para arquivos selecionados.
- Núcleo de orquestração: intenção → plano → ferramentas permitidas → execução → verificação → relatório.
- Adaptadores de IA no servidor para provedores distintos; chaves em secrets do backend, rotação e limites de uso.
- Camada de memória com escopo pessoal/projeto, histórico, preferências, tarefas e documentos selecionados; controles de retenção, exportação e exclusão.
- Sincronização offline-first nos clientes: fila local, IDs idempotentes, timestamps/versionamento, resolução explícita de conflitos e criptografia em trânsito.
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
- Memória, histórico, preferências, tarefas e projetos.
- Gateway multi-provedor de IA e limites de custo.
- Pesquisa web com fontes e data de consulta.
- Visão/OCR processada conforme consentimento.
- Sincronização, backup e restauração.
- Registro de ações, aprovações, auditoria e diagnóstico.
- Gerenciamento de dispositivos vinculados, com consentimento e possibilidade de desvincular.

## Dados financeiros
O núcleo pode oferecer organização financeira e integração futura com APIs bancárias oficiais. Não deve guardar credenciais bancárias nem códigos MFA. PIX agendado ou pagamento só poderá ser executado se o banco oferecer API oficial, o titular tiver autorização legal, beneficiário/valor/data forem confirmados e as regras do banco forem atendidas. Caso o banco exija nova autenticação na hora, o JARVIS deve solicitar a interação do titular; nunca contornar esse requisito.

## Multiusuário e empresa
Separar usuários registrados de sessões simultâneas. Permitir múltiplos perfis e tenants, com RBAC, isolamento de dados, limites configuráveis e trilha de auditoria. Escalabilidade depende da infraestrutura e não deve ser prometida como ilimitada.

## Critérios de aceite
- Testes automatizados de autenticação, isolamento, autorização e sincronização.
- Testes de contrato para cada provedor de IA.
- Testes de falha de rede, repetição idempotente, conflitos e recuperação.
- Testes de vazamento de segredos e dados entre usuários.
- Documentação de implantação, backups, restauração, custos e limites.
