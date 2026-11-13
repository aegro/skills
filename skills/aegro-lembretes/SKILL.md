---
name: aegro-lembretes
description: >-
  Agenda lembretes do Aegrozap no WhatsApp das pessoas da fazenda pela CLI
  aegro, para quem acompanha a implantacao do cliente: revisa a carteira,
  acha as tarefas do onboarding paradas, propoe o lembrete certo para a pessoa
  certa e so cria o que for aprovado; tambem agenda o que ficou combinado numa
  reuniao. Use quando pedirem "revisar minha carteira", "quais clientes estao
  com o onboarding parado", "cobrar o cliente pelo WhatsApp", "agendar um
  lembrete para o produtor", "lembrar o cliente do que combinamos"; EN
  "review my portfolio", "schedule a reminder for the customer". NAO use para
  o cliente criar lembrete para si pela conversa (isso e no proprio Aegrozap)
  nem para registrar a atividade da tarefa (use /aegro-agronomo).
---

# Lembretes do Aegrozap

## Objetivo

Fazer o aviso certo chegar no WhatsApp da pessoa certa da fazenda, na hora
combinada, sem cobrar duas vezes a mesma coisa. O lembrete sai no Aegrozap com o
nome de quem criou: "chegou a hora do lembrete que <seu nome> agendou para voce
no Aegrozap na <fazenda>".

## Pre-requisitos

- Login OAuth: `aegro auth login`. Os comandos `reminders` e `guided-setup` usam
  rota interna e recusam API key (exit 2, `OAUTH_REQUIRED`). Se a fazenda estiver
  tambem em `AEGRO_FARMS`, esses dois comandos usam o login OAuth sozinhos: nao
  precisa tirar a API key nem relogar. O exit 2 so aparece quando a fazenda nao
  esta no login OAuth.
- Voce precisa estar entre as pessoas da fazenda do cliente. Se nao estiver, a
  criacao e recusada; nao contorne, peca o acesso a fazenda.
- `--farm` explicito em todo comando, uma fazenda por vez.
- Versao: `reminders` e `guided-setup` sao comandos novos da CLI. Se
  `aegro reminders --help` disser que o comando nao existe, a CLI instalada
  ainda nao agenda lembretes. **Pare e diga isso a quem pediu**, sem instalar
  nada por conta propria, e peca a atualizacao pelo gerenciador que instalou o
  `aegro`: `uv tool install aegro@latest --force` (o `uv tool upgrade` nao sobe
  instalacao com pin), `pipx upgrade aegro`, `brew upgrade aegro` ou
  `pip install -U aegro`. Depois confira `aegro --version` e
  `aegro reminders --help`. Se o comando continuar faltando com a CLI
  atualizada, a release ainda nao saiu: nao agende por outro caminho.

## Vocabulario

- **Lembrete**: recado de uma linha, ate 60 caracteres, sem ponto final, com dia
  e hora de Brasilia, de uma vez ou repetindo.
- **Canal**: `AEGROZAP` (a pessoa usa o Aegrozap) ou `REGISTERED_PHONE` (nunca
  logou, recebe no telefone do cadastro do Aegro). Sem canal, a pessoa nao
  recebe.
- **Tarefa do onboarding**: item da implantacao guiada da fazenda, com
  responsavel e status.

## Sequencia de passos

### Revisao da carteira

A lista de fazendas da carteira vem de quem pediu (ou do HubSpot); esta skill
nao descobre a carteira sozinha.

1. Para cada fazenda, uma por vez:
   - `aegro guided-setup tasks --farm "<fazenda>"`: tarefas pendentes e o
     responsavel (`user::...`). Se vier o aviso de que a fazenda nao esta na
     rota do onboarding (status `unknown`), o servidor nao sabe o que esta feito:
     nao proponha cobranca por tarefa nessa fazenda, diga isso a quem pediu. A
     mesma regra vale para o erro `UNKNOWN_SETUP_TREE_SHAPE` (exit 1): a CLI nao
     reconheceu a resposta e nao leu tarefa nenhuma; nao trate como "nada
     pendente".
   - `aegro reminders recipients --farm "<fazenda>"`: quem pode receber e por
     qual canal; cruze o responsavel com o nome.
   - `aegro reminders list --farm "<fazenda>" --scope created-by-me` (saida
     JSON, a padrao): o que voce ja criou ali, inclusive o que ja disparou. O
     `createdAt` de cada lembrete so vem no JSON; a tabela e o CSV nao o trazem.
2. Monte a proposta: fazenda, tarefa, pessoa, data e hora, recado. Gere o texto
   exato de cada aviso com `--dry-run` (passo abaixo).
3. Mostre **tudo numa lista so** para quem pediu e espere a aprovacao. Nada e
   criado antes disso.
4. Para cada item aprovado, releia a tarefa (`guided-setup tasks`): se deixou
   de estar pendente, nao crie e diga isso. Depois crie com `--execute`.

### Depois da reuniao

1. `aegro reminders recipients --farm "<fazenda>"` para achar quem recebe.
2. `--dry-run` e mostre o texto do aviso e quem fica de fora.
3. Com o ok, `--execute`.

### Criar

```bash
aegro reminders create --farm "<fazenda>" --to "<nome>" \
  --message "Cadastrar os talhoes da safra" --date 14-11-2026 --time 08:00 --dry-run
aegro reminders create --farm "<fazenda>" --to "<nome>" \
  --message "Cadastrar os talhoes da safra" --date 14-11-2026 --time 08:00 --execute
```

Para repetir, `--repeat daily|weekdays|weekly|monthly` (padrao `once`), com
`--weekday` so em `weekly`, `--day-of-month` so em `monthly` e `--until dd-MM-yyyy`
para o ultimo dia. `--until` so vale com recorrencia: com `once` (o padrao) a
CLI recusa com exit 4.

A saida traz `idempotencyKey`. Se a criacao falhar sem resposta clara (5xx,
timeout), o lembrete PODE ter sido gravado: repita o MESMO comando, com
exatamente os mesmos argumentos, acrescentando `--idempotency-key <chave>` (a
chave sai em `error.idempotencyKey` no envelope de erro, em todo 5xx do
`--execute`, com ou sem `reason`). Se ele foi gravado, o servidor
devolve o existente (`created: false`) e nao cria outro. Nunca repita sem a
chave: sem ela a CLI gera outra e o lembrete pode sair duplicado. Nao confira
pela `reminders list`: ela nao mostra a chave, e dois lembretes iguais nao se
distinguem ali.

Leia o stderr nos dois passos. Quem fica de fora (sem canal) sai em
`aegro: aviso:` com o motivo; mostre isso na proposta. Se o aviso disser que
NINGUEM recebe, no `--dry-run` nao rode o `--execute`: resolva o canal em
`reminders recipients` primeiro. No `--execute` o lembrete ja foi gravado (exit
0, de proposito, para nao ser repetido): o aviso traz o comando `delete` pronto;
diga a quem pediu e exclua, salvo se for para mante-lo. Se o aviso disser
`nao conferido` (o servidor nao disse quem recebe), nao trate como "ninguem
recebe" nem como "todos recebem": confira os destinatarios em
`reminders list --farm "<fazenda>" --scope created-by-me` antes de dar por feito.

### Excluir

So quem criou exclui.

```bash
aegro reminders delete <reminderId> --farm "<fazenda>" --dry-run
aegro reminders delete <reminderId> --farm "<fazenda>" --execute
```

## Regras de negocio

- Recado sempre ligado a uma tarefa ou a algo combinado com o cliente. Nada de
  propaganda nem texto generico: o template e de utilidade.
- No maximo **um lembrete novo por fazenda por dia**, e nenhum novo para a mesma
  tarefa se ja ha um seu agendado ou criado nos ultimos 7 dias. Confira pelo
  `createdAt` no JSON de `reminders list --scope created-by-me`: o scope padrao
  (`active`) esconde o lembrete de uma vez que ja disparou. Lembrete excluido
  nao aparece em nenhum scope e nao conta: excluir para trocar recado ou
  horario libera a recriacao. `isActive: false` NAO e excluido: e lembrete
  pausado ou desativado (por quem criou, ou porque quem criou perdeu o acesso
  a fazenda), e conta nas duas regras.
- O lembrete nao guarda a tarefa; o unico vinculo e o recado. Escreva o recado
  nomeando a tarefa e compare pelo recado ao procurar o que ja foi criado.
- Ate 5 pessoas por lembrete.
- Prefira mandar para o responsavel da tarefa. Sem responsavel, pergunte a quem
  pediu para quem vai.
- `reminders list` mostra so o que voce criou ou recebe. Um lembrete que o
  proprio cliente ou outra pessoa do time agendou nao aparece: diga isso ao
  apresentar a proposta.

## Validacoes e erros comuns

Recusa do servidor sai como `REMINDER_REFUSED` com o motivo em `reason`; decida
pelo `reason`, nao pela frase. O que a propria CLI recusa antes de enviar sai sem
`reason`, pelo `code`:

- `INVALID_INPUTS` (exit 4): recado vazio, com quebra de linha ou acima de 60
  caracteres, data e hora fora do formato, `--to` vazio, `--until` sem
  recorrencia (`--repeat once`), `--weekday` fora de `weekly` ou
  `--day-of-month` fora de `monthly`. Nada foi enviado; corrija e rode o
  `--dry-run` de novo.
- `RECIPIENT_NOT_FOUND` (exit 4): `--to` nao e pessoa da fazenda; os nomes
  proximos saem em `candidates`. Confira em `reminders recipients`; quem nao
  esta la precisa ser convidado para a fazenda antes.
- `AMBIGUOUS_RECIPIENT` (exit 4): mais de uma pessoa casa com `--to`; os
  candidatos saem em `candidates`. Pergunte qual. `--to` aceita nome ou
  `user::...`, nao e-mail.

Recusas do servidor, pelo `reason`:

- `AEGROZAP_NOT_CONFIGURED` (exit 1): os lembretes nao estao ligados neste
  ambiente. Nada foi agendado; reporte, nao tente de novo.
- `CREATOR_NOT_IN_FARM` (exit 2): voce nao e pessoa da fazenda; peca o acesso.
- `USER_REQUIRED` (exit 2): rode `aegro auth login`.
- `NO_REACHABLE_RECIPIENT`: ninguem da lista recebe (sem Aegrozap e sem telefone
  no cadastro). Diga quem e por que; o cliente precisa cadastrar o telefone.
- `TEMPLATE_UNAVAILABLE`: o modelo de mensagem nao esta aprovado no ambiente.
  Nada foi agendado; reporte, nao tente de novo.
- `RECIPIENT_NOT_IN_FARM` (exit 4): alguem em `--to` nao e pessoa da fazenda.
  Aparece com `--to user::...` (por exemplo, o responsavel vindo do
  `guided-setup`), que pula a conferencia local. Nada foi agendado. Confira em
  `reminders recipients`; quem nao esta la precisa ser convidado para a
  fazenda antes.
- `FIRST_OCCURRENCE_IN_PAST`, `TOO_MANY_RECIPIENTS`, `INVALID_MESSAGE`: corrija o
  dado e rode o `--dry-run` de novo.
- `NO_UPCOMING_OCCURRENCE` (exit 4): a repeticao nao tem nenhum aviso entre
  agora e o `--until`. `INVALID_SCHEDULE` (exit 4): a agenda nao fecha (data,
  hora ou combinacao de `--repeat`, `--weekday`, `--day-of-month` e
  `--until`). Nada foi agendado; ajuste a agenda com quem pediu e rode o
  `--dry-run` de novo.
- Qualquer outro `reason` que nao esteja nesta lista (fora do 503 abaixo):
  mostre a `message` a quem pediu e pare. Nao adivinhe a correcao.
- `AEGROZAP_UNAVAILABLE` (exit 1), e qualquer outro `reason` que venha num
  503: o Aegrozap esta fora agora. Nao repita em laco; reporte e tente mais
  tarde. Em `list`, `recipients` e no `--dry-run` nada foi gravado. No
  `delete`, o 503 pode vir depois de a exclusao ter sido aplicada (o Aegrozap
  demorou a responder): confira com
  `reminders list --farm "<fazenda>" --scope created-by-me` antes de repetir;
  se o lembrete sumiu, ja foi excluido. Ao repetir, `ITEM_NOT_FOUND` (exit 3)
  tambem quer dizer que ja saiu.
  No `create --execute` o lembrete PODE ter sido gravado: o envelope traz a
  `idempotencyKey`; quando o Aegrozap voltar, repita o MESMO comando com ela,
  pela regra do 5xx acima, nunca sem ela.
- `IDEMPOTENCY_KEY_REUSED` (exit 4): a chave ja foi usada com outro pedido, ou
  o lembrete dela foi excluido. Nada foi agendado. Rode sem
  `--idempotency-key` (a CLI gera uma nova) ou repita a chave so com
  exatamente os mesmos `--to`, `--message`, `--date`, `--time` e `--repeat`.
  Depois de excluir um lembrete, a chave dele nunca mais serve.
- `NOT_CREATOR` ao excluir: o lembrete nao e seu. `ITEM_NOT_FOUND` (exit 3): ja
  foi excluido ou nao e um lembrete que voce cria ou recebe.
- Erro sem `reason` dizendo que o lembrete PODE ter sido gravado (5xx ou queda
  de conexao no `--execute`, `API_ERROR` exit 1): repita o MESMO comando com a
  mesma `--idempotency-key`, que vem em `error.idempotencyKey` no envelope;
  nunca sem ela. No `--dry-run` a chave nao vem: a mesma falha diz que a previa
  nao grava, e pode repetir o `--dry-run`.

A CLI tambem recusa uma resposta que nao prova o que foi pedido:

- `NOT_CONFIRMED` (exit 1) no `--dry-run`: o servidor nao confirmou que tratou
  como previa, entao o lembrete PODE ter sido criado de verdade, sem aprovacao.
  Nunca rode o `--execute` antes de conferir
  `reminders list --farm "<fazenda>" --scope created-by-me` e mostrar a quem
  pediu. Se o lembrete esta la e e para mante-lo, nao rode mais nada: repetir
  com a mesma chave so devolve o mesmo. Se nao era para existir, exclua
  (`reminders delete <reminderId> --farm "<fazenda>" --execute`). Se voce o
  excluiu, ou ele nao esta la, crie com `--execute` SEM `--idempotency-key`: a
  chave de lembrete excluido e recusada (`IDEMPOTENCY_KEY_REUSED`).
- `NOT_CONFIRMED` (exit 1) no `--execute`: a resposta veio sem `reminderId`, e
  o lembrete PODE ter sido gravado. A chave sai em `error.idempotencyKey`. Olhe
  `reminders list --farm "<fazenda>" --scope created-by-me` para mostrar a quem
  pediu o que existe, mas nao decida pela lista se repete (ela nao mostra a
  chave e nao distingue lembretes iguais): repita o MESMO comando, com
  exatamente os mesmos argumentos, acrescentando `--idempotency-key <chave>`.
  Se ele ja existe, volta `created: false` e nada se duplica. Se o
  `NOT_CONFIRMED` voltar, pare e reporte.

## Limitacoes

- O lembrete nao sabe da tarefa: se ela for concluida antes da hora, o aviso sai
  mesmo assim.
- Se voce sair da fazenda, seus lembretes param de avisar.
- Mudar recado ou horario de um lembrete existente: exclua e crie outro.
