# JARVIS EXE — Windows depois do APK

## Objetivo
Entregar a versão Windows após estabilizar o APK e o núcleo compartilhado. O EXE terá recursos próprios de desktop, sem duplicar regras de negócio que pertencem ao núcleo comum.

## Capacidades previstas
- Agente visual de computador: abrir aplicativos e páginas, clicar, digitar, rolar, navegar, pesquisar, comparar e baixar arquivos autorizados.
- Mostrar plano, progresso, ações realizadas e resultados no chat; permitir “ASSUMIR CONTROLE” para o usuário interromper e operar manualmente.
- Detectar mudanças inesperadas, falhas, telas desconhecidas e risco de ação incorreta; pausar, explicar e pedir autorização antes de continuar.
- Visão de tela sob comando explícito, OCR e interpretação de janelas/documentos; captura visível e controlável.
- Modo Código compartilhando o mesmo formato de projetos do APK: múltiplos arquivos e linguagens, geração por etapas, testes, correções, documentação e versionamento. Sem limite artificial de linhas, mas com limites técnicos transparentes.
- Modo Hacker exclusivo do EXE para Red Team/Blue Team e pesquisa defensiva em sistemas próprios ou com autorização documentada: auditoria web/API/rede/autenticação/configuração/banco, evidências não sensíveis, reprodução em laboratório, avaliação de impacto, correções e reteste.
- Biometria opcional para identificar perfis locais, com alternativa por PIN/senha, proteção contra spoofing, armazenamento de templates protegidos e permissões por perfil.
- Suporte a múltiplos usuários e perfis, com separação de memória, projetos, histórico e permissões.

## Limites de segurança
- O modo Hacker não pode invadir terceiros, roubar credenciais, persistir ocultamente, evadir detecção, extrair dados pessoais de usuários ou apagar rastros.
- Testes devem usar escopo definido, contas fictícias/de teste e dados não sensíveis. Relatórios devem priorizar prova mínima e correção.
- O agente de computador deve pedir confirmação para pagamentos, compras, publicação, envio sensível, exclusão, instalação, elevação de privilégio e alterações irreversíveis.
- Biometria não será o único fator para operações críticas.
- Nenhum recurso deve contornar controles do Windows ou de outros serviços.

## Atualização segura
Verificar assinatura/integridade, baixar de origem confiável, fazer backup, testar a versão, instalar com autorização necessária, validar saúde e permitir rollback. Não modificar silenciosamente o próprio núcleo nem remover proteções.

## Critérios de aceite
1. Instalador e executável assináveis/reproduzíveis.
2. Testes em Windows suportado, incluindo automação interrompível e recuperação de falhas.
3. Logs auditáveis sem segredos.
4. Modo Hacker testado somente em laboratório/ambiente autorizado.
5. Testes de isolamento multiusuário, biometria opcional e recuperação de conta.
6. Documentar o que exige permissões administrativas ou interação do usuário.

## Estado atual
A versão EXE ainda não foi implementada. Este documento define escopo e critérios, não uma entrega pronta.
