# JARVIS para computador

Versão de computador do JARVIS (Python, português). Tem janela (tkinter). Também funciona no terminal. Voz é opcional.

## Como rodar

Abrir a janela:

```bash
python3 -m jarvis --janela
```

No modo terminal: `python3 -m jarvis`. O `JARVIS-PC.exe` abre a janela direto.
Na janela, o botão **Configurações** guarda o endereço, o modelo e as chaves no `config.json`.

Precisa de Python 3.10 ou mais novo. O núcleo não usa nenhuma biblioteca extra.
Para testar: `pip install -r requirements-dev.txt` e depois `python -m pytest`.

## Configurar a IA e a busca

Crie o arquivo `config.json` dentro da pasta `JARVIS` na sua pasta de usuário:
no Windows, `C:\Users\SEU_NOME\JARVIS\config.json`. Use o modelo `config.exemplo.json`.

| Campo | O que colocar |
|---|---|
| `ia_url` | Endereço **completo** do seu servidor, como `https://seu-servidor/v1/chat/completions`. |
| `ia_modelo` | Nome do modelo no seu servidor. |
| `ia_chave` | Chave do servidor, se ele pedir. Fica só no seu computador. |
| `busca_url` | Endereço do seu servidor de busca (o Worker do app Android). |
| `busca_token` | Senha do servidor de busca. |

Variáveis de ambiente (`JARVIS_IA_URL`, `JARVIS_IA_MODEL`, `JARVIS_IA_KEY`, `JARVIS_BUSCA_URL`,
`JARVIS_BUSCA_TOKEN`) têm prioridade sobre o arquivo. `JARVIS_PASTA` troca a pasta `JARVIS`.
`JARVIS_VOSK_MODELO` ativa a entrada por voz.

Nunca coloque chaves dentro do código nem no repositório.

Quando você faz um pedido que a regras não entendem, a IA responde. Ela lembra das últimas
12 trocas da conversa. Diga "esquece a conversa" para começar do zero.

## Gerar, ver e testar código

- Peça um código, por exemplo: "faz um código que soma dois números".
  O JARVIS abre o arquivo no VS Code (precisa do comando `code` no sistema) e vai
  escrevendo nele enquanto gera. O VS Code atualiza sozinho.
- "Testa o código" roda o último arquivo com o Python, depois de conferir a sintaxe.
  Mostra a saída ou o erro. Programas que ficam abertos são interrompidos depois de 10 segundos.
- Atenção: o teste roda o código no seu computador. Só teste código que você entende.

## Funções do computador

- **Projetos completos**: "faz um site de loja", "cria um programa que ...", "faz um código ...".
  O JARVIS cria uma pasta de projeto com todos os arquivos (HTML, CSS, JavaScript, Python etc.)
  e só para quando o projeto estiver pronto. Erros de rede não param a geração: ele espera e tenta de novo.
- **Área de transferência**: "copia <texto>", "o que está copiado". No Linux precisa do xclip.
- **Sites e pastas**: "abre o google.com", "abre a pasta downloads", "abre a pasta jarvis".
- **Arquivos**: "procura o arquivo relatorio", "resume o arquivo ata" (usa a sua IA).
- **Sistema**: "informações do sistema" (disco, memória e bateria se o psutil estiver instalado).
- **Print**: "tira um print da tela" (precisa do pillow).
- **Desligar**: "desliga o computador" pede confirmação. Diga "confirma desligar" para desligar em 1 minuto,
  ou "cancela o desligamento".

Para as funções opcionais: `pip install psutil pillow`. O `.exe` já inclui as duas.

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
- **Conversa com a IA**: se o pedido não for reconhecido e a IA estiver configurada,
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
- `jarvis/editor.py`: abre no VS Code e testa o código rodando-o
- `jarvis/calc.py`: calculadora segura (sem `eval`)
- `jarvis/config.py`: lê o `config.json` e as variáveis de ambiente
- `jarvis/ia.py`, `jarvis/busca.py`: conversa com os seus servidores
- `jarvis/interface.py`: janela (tkinter) e tela de configurações
- `jarvis/configurar.py`: grava as configurações sem mostrar chaves
- `jarvis/main.py`: terminal, com voz opcional
- `tests/`: testes automáticos (rodam também no GitHub Actions)
