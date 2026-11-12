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
  rota interna e recusam API key (exit 2).
- Voce precisa estar entre as pessoas da fazenda do cliente. Se nao estiver, a
  criacao e recusada; nao contorne, peca o acesso a fazenda.
- `--farm` explicito em todo comando, uma fazenda por vez.

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
     nao proponha cobranca por tarefa nessa fazenda, diga isso a quem pediu.
   - `aegro reminders recipients --farm "<fazenda>"`: quem pode receber e por
     qual canal; cruze o responsavel com o nome.
   - `aegro reminders list --farm "<fazenda>"`: o que voce ja agendou ali.
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

A saida traz `idempotencyKey`. Se a criacao falhar sem resposta clara (503,
timeout), repita com a mesma chave (`--idempotency-key <chave>`): o servidor nao
cria um segundo lembrete.

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
  tarefa se ja ha um seu agendado ou criado nos ultimos 7 dias
  (`reminders list --scope created-by-me`).
- Ate 5 pessoas por lembrete.
- Prefira mandar para o responsavel da tarefa. Sem responsavel, pergunte a quem
  pediu para quem vai.
- `reminders list` mostra so o que voce criou ou recebe. Um lembrete que o
  proprio cliente ou outra pessoa do time agendou nao aparece: diga isso ao
  apresentar a proposta.

## Validacoes e erros comuns

Recusa do servidor sai como `REMINDER_REFUSED` com o motivo em `reason`; decida
pelo `reason`, nao pela frase.

- `AEGROZAP_NOT_CONFIGURED` (exit 1): os lembretes nao estao ligados neste
  ambiente. Nada foi agendado; reporte, nao tente de novo.
- `CREATOR_NOT_IN_FARM` (exit 2): voce nao e pessoa da fazenda; peca o acesso.
- `USER_REQUIRED` (exit 2): rode `aegro auth login`.
- `NO_REACHABLE_RECIPIENT`: ninguem da lista recebe (sem Aegrozap e sem telefone
  no cadastro). Diga quem e por que; o cliente precisa cadastrar o telefone.
- `TEMPLATE_UNAVAILABLE`: o modelo de mensagem nao esta aprovado no ambiente.
  Nada foi agendado; reporte, nao tente de novo.
- `FIRST_OCCURRENCE_IN_PAST`, `TOO_MANY_RECIPIENTS`, `INVALID_MESSAGE`: corrija o
  dado e rode o `--dry-run` de novo.
- `NOT_CREATOR` ao excluir: o lembrete nao e seu. `ITEM_NOT_FOUND` (exit 3): ja
  foi excluido ou nao e um lembrete que voce cria ou recebe.
- Erro sem `reason` dizendo que o lembrete PODE ter sido gravado (503, queda de
  conexao): confira com `reminders list` e, se nao estiver la, repita com a
  mesma `--idempotency-key`.
- Nome ambiguo em `--to`: a CLI lista os candidatos; pergunte qual. `--to`
  aceita nome ou `user::...`, nao e-mail.

## Limitacoes

- O lembrete nao sabe da tarefa: se ela for concluida antes da hora, o aviso sai
  mesmo assim.
- Se voce sair da fazenda, seus lembretes param de avisar.
- Mudar recado ou horario de um lembrete existente: exclua e crie outro.
