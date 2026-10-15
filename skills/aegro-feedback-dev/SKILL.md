---
name: aegro-feedback-dev
description: >-
  Fecha a sessao de trabalho na CLI `aegro` reportando o que nao saiu como o
  usuario queria: parte do resultado esperado, percorre o caminho tentado e por
  que, o que deu errado, as voltas que o agente deu e o desfecho de cada uma,
  decide de quem e o problema (CLI, skill ou API/dominio) e entrega como Ticket
  de Suporte - abre a issue no GitHub quando a sessao tem `gh` autenticado e,
  quando nao tem, deixa o bloco pronto para o Suporte ou para o espaco do time,
  com PII mascarada e sem credenciais. A fonte e a propria sessao - o que foi
  pedido e o que o agente executou. Use quando o usuario pedir "manda isso pro
  time", "reporta esse erro", "abre um ticket disso", "isso nao funcionou, avisa
  o pessoal", "compila o feedback da sessao"; EN "report this to the dev team",
  "open a ticket", "send session feedback". Use tambem por conta propria, sem
  esperar o pedido, quando um comando `aegro` falhar e nem o caminho documentado
  nem as voltas tentadas entregarem o resultado: registre o item na hora,
  enquanto o contexto existe, e ofereca o envio ao fim. NAO use para suporte a
  cliente final nem para bug do app Aegro fora do fluxo CLI/API/skill (segue o
  fluxo normal de bug), e nao use no lugar de resolver: primeiro entregue o
  resultado ao usuario, depois reporte.
---

# Feedback da sessao -> ticket

O usuario tentou fazer alguma coisa no Aegro pela CLI e nao conseguiu, ou
conseguiu por uma volta. Esta skill transforma essa sessao em um **Ticket de
Suporte** que a squad certa consegue agir: o que tinha de sair, o que voce
tentou, o que quebrou, as voltas, o desfecho e de quem e o problema.

Voce estava la. **Nao va procurar o erro em arquivo** - a sessao e a fonte, e e a
unica que tem o *por que* de cada escolha.

## Regra dura: ticket, nunca repositorio

Esta skill **nao faz commit, nao abre PR e nao escreve em repositorio nenhum**.
A unica escrita permitida fora da maquina e **abrir a issue do ticket**, e so
quando a sessao tem `gh` autenticado (ver "Entrega"). Quem opera (EV de campo,
time de Servicos, cliente) normalmente nao tem isso - para essas sessoes o doc
fica **local** e a entrega e o **bloco pronto** para o Suporte ou para o espaco
do time. Nunca mensagem privada para uma pessoa: o destino e sempre o ticket ou
a fila que vira ticket.

## Quando usar

**Gatilho 1 - o usuario pede.** No fim da sessao, ou logo depois de algo falhar:
"manda isso pro time", "abre um ticket disso". Compile o que atritou na sessao.

**Gatilho 2 - voce chega aqui sozinho.** Um comando `aegro` falhou, voce tentou
as voltas que sabia e o resultado pedido nao saiu - ou so saiu por fora, na mao,
no app. Carregue esta skill **no momento em que isso fica claro**, enquanto o
contexto esta inteiro.

**Registre na hora, entregue no fim.** O trabalho do usuario vem antes do
relatorio: termine o que da para terminar (ou desista junto com ele) e so entao
mostre o item e ofereca o envio. Carregar a skill nao autoriza parar a tarefa
para escrever documento. Excecao unica: **dado de cliente gravado errado em
producao** - escale na hora, com o que tiver, com prioridade `Urgente`. A
urgencia encurta a espera pelo "sim" de confirmacao antes do envio - nao a
dispensa.

**Nao reporte** quando o tropeco foi seu e nao custou nada ao usuario: erro que
voce corrigiu na sequencia, comando que funcionou na segunda tentativa depois de
ler o `--help`. Vira item quando custou retrabalho, tempo ou o resultado, **ou**
quando voce so achou o caminho certo por tentativa e erro - isso e lacuna de
instrucao, e e exatamente o que o dono da skill precisa saber.

**Nao use** para suporte a cliente final, para bug do app Aegro sem relacao com
CLI, API publica ou skill (fluxo normal de bug), nem no meio do lancamento como
desculpa para nao tentar a proxima volta.

## Modo da sessao: time Aegro vs. cliente (ler primeiro)

Identifique quem esta na sessao pelo **e-mail do usuario** no contexto:

- **Interno - `@aegro.com.br`**: doc local + ticket (pelo `gh` quando houver,
  senao bloco pronto para o espaco do time). Ver "Entrega no modo interno".
- **Externo - outro dominio** (cliente): bloco pronto para o cliente colar no
  chat do Suporte. Ver "Entrega no modo externo".

Sem e-mail identificavel, trate como **externo**.

## Sequencia de passos

### 1. Reconstituir o item a partir da sessao

Cada parte tem fonte direta na conversa, nesta ordem - ela e o formato, nao uma
sugestao de redacao:

1. **Resultado esperado** - o que o usuario pediu, em termos de negocio: "a nota
   do fornecedor_x lancada, com as 3 parcelas a prazo nas datas do boleto". Se o
   pedido foi vago, **pergunte agora**, antes de fechar a sessao: "o que tinha de
   estar no Aegro no fim?". Uma pergunta, nao um formulario.
2. **Caminho tentado e por que** - o comando que voce rodou e o que te levou ate
   ele: a instrucao da skill, um campo da nota, a saida do comando anterior. O
   *por que* e a parte que so voce tem; sem ele o dev nao consegue julgar se a
   instrucao induziu ao erro.
3. **O que deu errado** - resposta e efeito observado, com ambiente e versao.
4. **Contornos** - cada volta depois da falha, **com o desfecho de cada uma**:
   funcionou, pela metade, nao funcionou. Inclua as que nao funcionaram: e o que
   impede o proximo agente de repetir o mesmo caminho.
5. **Desfecho** - o resultado saiu? Por qual volta, e a que custo (tempo,
   lancamento manual no app). "Nao saiu" tambem e desfecho.
6. **Diagnostico** - hipotese do que aconteceu, **dita como hipotese**. Sem
   hipotese, escreva `sem hipotese`: hipotese inventada custa mais caro que
   nenhuma, porque a triagem passa a investigar a hipotese em vez do sintoma.

Comecar pelo erro inverte a leitura: o dev recebe um payload recusado sem saber o
que a pessoa queria lancar, e nao tem como julgar se a recusa estava certa.

### 2. Relatar a sua propria conduta sem maquiar

Metade da sessao foi voce, e o relato e sobre a sessao inteira. Duas regras:

- **Nao promova erro seu a bug da plataforma.** Se voce inventou um campo, errou
  a flag ou chamou o comando de outro fluxo, o item diz isso com todas as letras.
  A recusa da API estava certa; o que falhou foi a instrucao que te deixou
  escolher errado. Mandado como bug de API, o item volta fechado como "funciona
  como esperado" e a instrucao ambigua fica de pe.
- **Nao esconda as voltas erradas.** Elas parecem constrangedoras e sao o dado
  mais util do doc: todo caminho errado que pareceu razoavel na hora e uma linha
  que falta em alguma skill.

### 3. Decidir de quem e o problema

**O CLI e canal, nao dominio.** O que decide o dono e **onde esta o codigo que
precisa mudar**, e sao tres lugares possiveis:

| Dono | Quando | Exemplos |
|---|---|---|
| `CLI` | autenticacao, selecao de fazenda, saida, paginacao, flag, comando que nao existe, tratamento de erro, versao | `--dry-run` aplicou; pagina repetida; comando sai com sucesso e nao grava |
| `skill` | existia caminho certo e a instrucao te levou ao errado, omitiu um passo ou descreveu regra que nao existe | a skill mandou lancar a parcela antes da conta; nao dizia que `--farm` era obrigatorio |
| `API/dominio: <squad>` | o endpoint recusou um pedido **valido**, gravou errado, devolveu sucesso sem persistir, ou falta campo que a tela tem | 500 com payload valido; `PATCH` responde 200 e nada muda; total da nota invertido |

Regras de desempate:

- **Payload errado que o endpoint recusou com razao e `CLI` ou `skill`**, nunca
  `API/dominio`.
- **Nao da para saber** -> `a investigar`, dizendo o que falta para decidir. E
  resposta legitima; chutar `API/dominio` nao e. Nesse caso o ticket nasce com a
  squad do CLI, que rerota quando achar a causa.
- **Dois lados precisam mudar** (o CLI manda um opcional que o endpoint trata
  errado): dono principal e o que o usuario sente primeiro; o outro vai como
  mencao no item, nao como segundo ticket.

Combinacao vale, indicando a ordem (ex.: `skill, depois API/dominio: Fiscal`).

A **squad** do dono `API/dominio` sai do grupo de comando que falou com o
endpoint:

| Grupo de comando `aegro ...` | Squad |
|---|---|
| `financial`, `bills`, `installments`, `bank-accounts`, `bank-movements`, `bank-reconciliation`, `bank-transfers`, `cash-flow`, `cashbook`, `financial-migration` | Financeiro |
| `activities`, `crops`, `glebes`, `assets`, `asset-events`, `stock`, `harvest-logs`, `sale-contracts`, `purchase-orders`, `elements`, `livestock`, `weather`, `pest-monitoring` | Agricola |
| `invoices`, `received-fiscal-documents`, `nfe`, `rural-properties` | Fiscal |
| `farms`, `users`, `tags`, `files`, `auth`, `skills` | CLI (Agentes) |

Grupo fora da tabela: escreva `API/dominio: a confirmar` e deixe o grupo no item.
O ticket nasce com a squad do CLI e e rerroteado na triagem.

### 4. Juntar o repetido

Mesmo sintoma varias vezes na sessao = **um item**, com `ocorrencias: N`. Se o
mesmo sintoma bloqueou resultados esperados diferentes, mantenha um item so e
liste os resultados esperados - e essa lista que mostra o alcance do fix.
Sintomas iguais com donos diferentes sao **dois itens**: a correcao nao e a
mesma.

Se ja houver doc de sessao anterior nesta maquina com o mesmo sintoma, nao cale
nem reescreva a historia toda: acrescente `ja reportado em <arquivo>` no item.
Com `gh` disponivel, procure tambem ticket aberto com o mesmo sintoma (ver
"Referencia de comandos"): existindo, a entrega vira **comentario nesse ticket**,
nao ticket novo. Repeticao e sinal de prioridade.

### 5. Limpar a evidencia

A evidencia mora dentro do caminho tentado, do que deu errado e de cada contorno
- cada um leva o comando executado e a resposta resumida; o item leva ambiente
(staging/prod) e versao do CLI uma vez. Contorno sem comando nao e
reaproveitavel por quem ler.

**Nunca** credenciais, nem mascaradas; nunca CPF/CNPJ nem chave de acesso de
NF-e. O que entra depende do destino:

- **No ticket (modo interno):** e-mail do usuario e link da fazenda **ficam** -
  sao os campos "Usuario afetado" e "Link da Fazenda" do ticket, e sem eles
  ninguem reproduz. Nome de terceiro (fornecedor, cliente da fazenda) vira
  `fornecedor_x`, `cliente_x`.
- **No bloco para o Suporte (modo externo):** so o e-mail do proprio cliente, que
  ele mesmo informa. Mascare nome de terceiro e dado comercial sensivel que nao
  seja PII (preco negociado, configuracao interna, numero financeiro).

Prefira shape e agregado a dado bruto.

### 6. Sugerir a prioridade

Use a matriz que o Suporte usa, cruzando duas perguntas - afeta uma
funcionalidade-chave? existe paliativo? - e anote como **sugestao**: quem decide
e quem tria.

| | Funcionalidade-chave nao afetada | Funcionalidade-chave afetada |
|---|---|---|
| **Com paliativo** | `Baixa` | `Alta` |
| **Sem paliativo** | `Media` | `Alta`; `Urgente` se para a operacao ou grava dado errado em producao |

Funcionalidade-chave, para o CLI: lancamento de NF-e e de conta, baixa de
parcela, conciliacao bancaria, atividade e romaneio. Lacuna de instrucao da skill
e `Baixa`, salvo quando induz a gravar errado.

### 7. Escrever o doc da sessao

Salve em `$AEGRO_LEARNING_DIR/feedback-AAAA-MM-DD-<tema>.md` - o doc e a fonte da
entrega e o registro para a proxima sessao. Sanitize `<tema>` antes de montar o
caminho: slug curto (letras, numeros, hifen), rejeitando vazio, barra, contrabarra
e `..` - o valor sai do relato e nao e confiavel como esta. Se ja existir arquivo
do mesmo tema e dia, acrescente a hora (`feedback-AAAA-MM-DD-HHmm-<tema>.md`) em
vez de sobrescrever. Grave com criacao exclusiva (falha se o nome ja existir,
nunca substitui o arquivo); em colisao mesmo com a hora, acrescente um sufixo
curto extra e tente de novo, sem repetir o nome que colidiu. Sem
`$AEGRO_LEARNING_DIR` definida, use o diretorio atual e registre no doc que foi
essa a pasta; se nem isso for possivel, diga que o registro nao foi persistido -
nunca siga em silencio.

```markdown
# Feedback da sessao - <tema> (AAAA-MM-DD)

> Sessao encerrada <HH:MM> BRT | CLI vX | staging|prod | N itens
> Entrega: pendente

## 1. <o resultado esperado que nao saiu, em uma linha>
- resultado esperado: <o que tinha de existir no Aegro no fim>
- caminho tentado: `<comando>` - escolhido porque <o que levou ate ele>
- o que deu errado: <resposta e efeito observado>
- contornos:
  1. `<comando>` -> <o que aconteceu> - funcionou | pela metade | nao funcionou
  2. ...
- desfecho: saiu pelo contorno N (custo: <tempo/retrabalho>) | so no app, fora do
  CLI | nao saiu
- diagnostico: <hipotese, dita como hipotese> | sem hipotese
- dono: CLI | skill | API/dominio: <squad> | a investigar
- prioridade sugerida: Baixa | Media | Alta | Urgente - <paliativo? chave?>
- ocorrencias: N na sessao (ja reportado em <arquivo> | ticket #N, se aplicavel)
- sugestao: <a menor melhoria que entrega o resultado esperado pelo caminho certo>
```

### 8. Montar o ticket

Cada item vira **um ticket**, no formato do Ticket de Suporte. O titulo e o
**resultado esperado que nao saiu**, prefixado por `[CLI]` - nunca a mensagem de
erro, que descreve a tentativa e nao o que ficou faltando.

```markdown
Titulo: [CLI] <resultado esperado que nao saiu, em uma linha>

### Usuario afetado
<e-mail do usuario da sessao>

### Link da Fazenda
<https://app.aegro.com.br/farm/...>

### Versao do aplicativo
CLI aegro <X.Y.Z> | <staging|prod> | skill <nome, se houver>

### Descricao completa
**Resultado esperado:** <o que tinha de existir no Aegro no fim>

**Passos para reproduzir:**
- `<comando>` - escolhido porque <o que levou ate ele>
- <resposta resumida>

**Comportamento esperado x atual**
- Esperado: <...>
- Atual: <...>

**Erro observado:** <codigo do envelope de erro e mensagem, se houver>

**Contornos:** 1) `<comando>` -> funcionou | 2) `<comando>` -> nao funcionou

**Desfecho:** <saiu por qual volta e a que custo, ou nao saiu>

**Diagnostico (hipotese):** <...> | sem hipotese

**Dono sugerido:** CLI | skill | API/dominio: <squad> | a investigar
**Prioridade sugerida:** <...> - <motivo em meia linha>
**Sugestao:** <a menor melhoria que entrega o esperado pelo caminho certo>

Campos do painel: Produto = CLI aegro | Plataforma = CLI | Squad = <Agentes ou a
squad do dono> | Prioridade = <sugerida>
```

A linha "Campos do painel" existe porque o form nao preenche os campos da
direita; quem abre (voce, pelo `gh`, ou o Suporte) copia dali.

### 9. Entregar

Mostre o ticket ao usuario antes de qualquer envio. Modo interno -> "Entrega no
modo interno"; modo externo -> "Entrega no modo externo". Depois, atualize a
linha `> Entrega:` (`ticket #N AAAA-MM-DD`, `bloco enviado AAAA-MM-DD (N itens)`
ou `pendente - <motivo>`).

## Entrega no modo interno (ticket pelo `gh`, senao bloco para a fila)

**Caminho 1 - `gh` autenticado com acesso ao `aegro/workspace`.** Teste antes
(ver "Referencia de comandos"); sem acesso, va ao Caminho 2 sem tentar de novo.

1. **Procure duplicata**: ticket aberto com o mesmo sintoma. Existindo, a entrega
   e um **comentario** nele com o bloco do item - repeticao sobe a prioridade.
2. **Confirme antes de abrir**: mostre o titulo e o corpo exatos e abra so com um
   "sim" explicito. Ticket em nome de alguem nao sai sem confirmacao.
3. **Abra a issue** no `aegro/workspace` com o issue type `Ticket de Suporte`
   (mutation `createIssue` - o `gh issue create` nao aceita type). Um ticket por
   item.
4. **Preencha os campos do painel** que a sessao alcancar (`Produto`,
   `Plataforma`, `Squad`, `Prioridade`); os que nao alcancar ficam na linha
   "Campos do painel" do corpo, e a automacao do ticket cobra o que faltar.
5. **Registre o numero** no doc local (`> Entrega: ticket #N`) e diga ao usuario
   o link.

**Caminho 2 - sem `gh`.** Entregue o bloco pronto na **fila do time** - o espaco
do Google Chat do CLI que o seu time usa - com um item por mensagem, todos na
mesma thread, cabecalho primeiro. Quem tem acesso ao repositorio abre o ticket
a partir dali. Nunca mensagem privada para uma pessoa; nunca espaco que o
usuario nao escolheu. Confirme o texto exato antes de enviar; se o envio falhar
no meio, marque `> Entrega: pendente - envio parcial (itens enviados: <lista>)`
antes de tentar de novo.

O Chat aceita Markdown, mas **nao aceita tabela**: mande o bloco do passo 8 sem
a tabela, em linhas `rotulo: valor`. Item acima de ~3500 caracteres: corte pelos
contornos que nao funcionaram - esperado, desfecho e o contorno que funcionou
ficam sempre - e cite o caminho do doc local.

Nunca deixe a sessao em "pendente" silencioso: sem nenhum caminho disponivel,
diga o caminho do doc local, peca ao usuario para levar o bloco a fila do time e
marque `> Entrega: pendente - <motivo>`.

## Entrega no modo externo (bloco para o Suporte)

O cliente reporta ao **Suporte da Aegro** pelo canal que ja usa (chat do app ou
WhatsApp), e o Suporte abre o ticket. Deixe a um clique:

- Apresente, por item, um bloco copiavel com o `Titulo:` e a `Descricao completa`
  do passo 8, sem a linha "Campos do painel" (e do Suporte) e com a PII de
  terceiros mascarada.
- Diga ao cliente que o unico dado de contato que sai e o e-mail dele.
- Com varios itens, liste e deixe o cliente escolher quais enviar.

Preparar o bloco nao e entrega: mantenha `> Entrega: pendente - aguardando envio
do cliente` enquanto so o conteudo foi montado. So registre `bloco enviado
AAAA-MM-DD (N itens)` depois que o cliente confirmar que mandou.

## Anti-padroes

- **Parar a tarefa para escrever o relatorio.** Registre, termine o trabalho,
  reporte no fim.
- **Reportar todo 4xx.** Erro que voce causou e corrigiu sem custo nao e item.
- **Mandar a mensagem de erro como titulo.** O dev fica sem saber o que deveria
  ter ficado pronto.
- **Item guarda-chuva** ("a CLI esta instavel") - nao gera acao.
- **Hipotese inventada** para o campo diagnostico nao ficar vazio.
- **Chutar `API/dominio`** para o item sair da fila do CLI. Sem prova de pedido
  valido recusado, o dono e `a investigar`.
- **Reportar como bug o que a skill ja avisava** e voce nao leu: leia o aviso e
  siga. Se o aviso existia mas era ambiguo, ai sim e item de `skill`.
- **Mensagem privada para uma pessoa.** O destino e o ticket ou a fila do time.

## Limitacoes

- Sem commit, sem PR, sem alterar repositorio. A unica escrita remota e a issue
  do ticket, e so com `gh` autenticado.
- O ticket nasce com os campos que a sessao alcanca; a triagem do Suporte e a
  automacao completam e rerroteiam.
- A sessao e a unica fonte com o *por que* de cada escolha. Se a conversa foi
  compactada e voce nao recupera o motivo de um caminho, escreva `motivo da
  escolha nao recuperado` em vez de racionalizar depois do fato.
- Diario (`$AEGRO_LEARNING_DIR/journal-*.md`) e telemetria
  (`$AEGRO_TELEMETRY_DIR/*.jsonl`), quando existirem, servem para conferir
  comando e resposta exatos - nunca como substituto do relato da sessao, e
  sempre passando pela limpeza do passo 5.

## Validacoes e erros comuns

- **Dado de cliente gravado errado em producao** -> nao espere o fim da sessao:
  abra (ou mande) na hora, com `Urgente` e o item parcial.
- **Mais de 5 itens numa sessao** -> algo maior quebrou. Agrupe por fluxo: ate 5
  itens seguem o formato normal (um ticket ou mensagem por item); o que exceder
  vira um unico item de panorama, sem detalhe enviado depois.
- **O usuario nao sabe dizer o que esperava** (assumiu a tarefa no meio) -> nao
  promova o erro a bug: registre com `resultado esperado: nao reconstituido` e
  diga que falta isso.
- **Usuario recusa o envio** -> guarde o doc, diga o caminho e pare. Nao mande
  mesmo assim.
- **`gh` autenticado, mas sem acesso ao `aegro/workspace`** -> Caminho 2, sem
  insistir.

## Referencia de comandos

| Objetivo | Comando |
|---|---|
| Versao do CLI (para a evidencia) | `aegro --version` |
| Docs de sessoes anteriores nesta maquina | `ls ${AEGRO_LEARNING_DIR:-.}/feedback-*.md` |
| Ver se o sintoma ja foi reportado localmente | `grep -il "<sintoma>" ${AEGRO_LEARNING_DIR:-.}/feedback-*.md` |
| Diario da sessao (complemento) | `ls ${AEGRO_LEARNING_DIR:-.}/journal-*.md` |
| Ha `gh` com acesso ao workspace? | `gh auth status && gh api repos/aegro/workspace --jq .full_name` |
| Ticket aberto com o mesmo sintoma | `gh issue list --repo aegro/workspace --state open --search "<sintoma> in:title,body type:\"Ticket de Suporte\"" --json number,title,url` |
| Id do issue type e do repo (para a mutation) | `gh api graphql -f query='{ organization(login:"aegro"){ issueTypes(first:30){ nodes{ id name } } } repository(owner:"aegro", name:"workspace"){ id } }'` |
| Abrir o ticket | `gh api graphql -f query='mutation($repo:ID!,$tipo:ID!,$titulo:String!,$corpo:String!){ createIssue(input:{repositoryId:$repo, issueTypeId:$tipo, title:$titulo, body:$corpo}){ issue{ number url } } }' -f repo=<id> -f tipo=<id do "Ticket de Suporte"> -f titulo="<titulo>" -f corpo="$(cat <arquivo do corpo>)"` |
| Comentar num ticket existente | `gh issue comment <numero> --repo aegro/workspace --body-file <arquivo do bloco>` |
