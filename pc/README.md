# JARVIS para computador

Versão de computador do JARVIS (Python, português). Funciona pelo teclado, no terminal.
Voz é opcional.

## Como rodar

```bash
python3 -m jarvis
```

Precisa de Python 3.10 ou mais novo. O núcleo não usa nenhuma biblioteca extra.
Para testar: `pip install -r requirements-dev.txt` e depois `python -m pytest`.

## Configuração (variáveis de ambiente)

Nenhuma chave fica no código. Defina só o que você for usar:

| Variável | Para quê |
|---|---|
| `JARVIS_IA_URL` | Endereço do seu servidor de IA (compatível com a API da OpenAI). Sem isso, a IA fica desligada. |
| `JARVIS_IA_MODEL` | Nome do modelo no seu servidor. |
| `JARVIS_IA_KEY` | Chave do seu servidor, se ele pedir. |
| `JARVIS_BUSCA_URL` | Endereço do seu servidor de busca (o mesmo Worker do app Android). |
| `JARVIS_BUSCA_TOKEN` | Senha do servidor de busca. |
| `JARVIS_PASTA` | Onde guardar anotações e códigos. Padrão: `~/JARVIS`. |
| `JARVIS_VOSK_MODELO` | Pasta do modelo de voz Vosk pt-BR (ativa a entrada por voz). |

No Windows, use `set NOME=valor` no CMD ou `$env:NOME="valor"` no PowerShell.
No Linux e no macOS, use `export NOME=valor`.

## O que já faz

- **Calculadora**: "quanto é 25 por cento de 80", "raiz de 16", "2 mais 2 vezes 3".
- **Pesquisa**: "pesquisa receita de bolo" (precisa do servidor de busca).
- **Abrir programas**: "abre o bloco de notas". Procura os atalhos do sistema.
- **Anotações**: "anota que comprar pão", "ler anotações", "apagar anotações".
- **Lembretes**: "me lembra em 10 minutos de tomar remédio". Só dispara com o JARVIS aberto.
- **Música**: "toca Evidências" abre a busca no YouTube no navegador.
- **Hora e data**: "que horas são", "qual é a data de hoje".
- **Organizar Downloads**: "organiza os downloads" separa por tipo, sem apagar nada.
  "desfazer organização" devolve tudo ao lugar.
- **Código longo**: "faz um código de 3 mil linhas de ...". Roda em segundo plano e salva
  cada parte em `~/JARVIS/codigos/`. Use "como está o código", "para o código" e
  "continua o código" para acompanhar, parar e retomar. Com meta de linhas, mostra a porcentagem.
- **Conversa com a IA**: se o pedido não for reconhecido e `JARVIS_IA_URL` estiver configurada,
  a IA responde. Ela pode pedir uma ação em JSON, e o JARVIS executa só ações conhecidas.

## Limites

- Ler a tela, controle de volume, lanterna e bateria são recursos do celular.
  Não existem nesta versão.
- O código gerado é salvo, mas não há garantia de que funcione. Teste antes de usar.
- Limite de tamanho: cada resposta da IA é limitada pelo seu servidor. Um código de
  milhão de linhas leva muitas horas e muitas chamadas. O tempo máximo é de 72 horas.
- Voz não foi testada automaticamente. Teclado é o modo garantido.

## Estrutura

- `jarvis/comandos.py`: entende o pedido (regras simples e leitura do JSON da IA)
- `jarvis/nucleo.py`: decide a ação e devolve a resposta
- `jarvis/ferramentas.py`: anotações, lembretes, programas, música e Downloads
- `jarvis/codigo.py`: geração de código em segundo plano, com retomada
- `jarvis/calc.py`: calculadora segura (sem `eval`)
- `jarvis/ia.py`, `jarvis/busca.py`: conversa com os seus servidores
- `jarvis/main.py`: terminal, com voz opcional
- `tests/`: testes automáticos (rodam também no GitHub Actions)
