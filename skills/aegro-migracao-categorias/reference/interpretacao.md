# Interpretar o plano, o ledger e o verify

O que cada status, motivo e classe significa — e **o que dizer a EV**. Traduzir
errado aqui e pior que nao traduzir: "312 bloqueados" soa como estrago quando na
verdade e um conjunto que migra depois.

---

## 1. Status de cada linha do plano

| Status | Significa | Escreve? |
|---|---|---|
| `planned` | Casou com regra ou override; o payload esta pronto | sim, no `apply` |
| `unresolved` | Nenhuma regra casou | **nao** — vai para a cauda |
| `kept` | Override com `keep: true`: fica na antiga de proposito — inclusive o que a tela chama "resolver manualmente", que vai para o relatorio final | **nao** |
| `blocked` | Nao deve ser escrito; ver secao 2 | **nao** |

`unresolved` **nao e erro**. E o desenho: sem regra e sem override, o CLI nunca
chuta. O trabalho e transformar `unresolved` em `planned` ou em `kept` pela tela.

---

## 2. Motivos de bloqueio

### `recurrence` — CORRIGIDO no servidor; o bloqueio agora e precaucao

O lancamento e recorrente. O PATCH da API publica em bill recorrente **respondia
200 e nao salvava** (FNC-184: `updateBillWithRecurrences` devolvia a bill antiga do
banco). Numa base de folha isso significaria "migrei 3 mil contas" com zero
persistido.

**Isso foi corrigido** por serv-core#5304 (commit `cf73a8dff5`), e o fix esta em
**producao desde a release `v2026.08.17-114950`** (17/08/2026), em staging desde
13/08 — conferido por conteudo de branch, e a gravacao provada em staging por
releitura direta de um recorrente migrado.

Desde 20/08/2026 o `plan` **migra recorrente por default**. `--no-allow-recurrent`
volta a bloquear, e serve para um caso so: servidor mais antigo que aquela release
(o CLI nao sabe a versao do que esta chamando). O que fica de fora e o recorrente
**com parcela paga E itens** (`settled-recurrence-inputs`); no nivel da conta ele
migra, e a maioria e de nivel conta.

O plano bloqueia de proposito, em vez de mandar uma escrita que a gente sabe que
nao persiste. **Como dizer a EV:**

> Esses N lancamentos sao recorrentes. Tem um bug conhecido no backend em que
> salvar categoria de lancamento recorrente pela API nao grava — e responde
> "deu certo". Preferimos nao mexer neles agora a fingir que migrou. Quando o
> fix subir, eles migram com o mesmo comando, sem trabalho novo seu.

O numero e a evidencia que prioriza o fix: **reporte-o**. Cuidado com dois campos
diferentes no `meta.json`, de proposito:

- `recurrentInSweep` — quantos recorrentes existem no recorte;
- `recurrentBlocked` — quantos o plano de fato bloqueou.

Recorrente que nao casa com regra nenhuma fica `unresolved`, nao `blocked`.
Somar os dois infla a evidencia — nao some.

### `override-multi-source` — a decisao conta a conta nao alcanca duas origens

O lancamento tem itens em **duas ou mais categorias de origem diferentes**, e o
override e decisao por CONTA: um destino unico seria escrito em todos os itens,
colapsando duas categorias antigas numa so — com status `planned` e ninguem
percebendo.

**Como isso aparece na pratica:** quando a cauda vira override em massa. Em
campo (14/08/2026), o contorno para recortar por data de pagamento gerou **305
overrides**, e a verificacao de que nenhum deles tinha itens em mais de uma
origem foi feita **a mao, conta a conta**. Naquele recorte deu zero; numa base
onde ocorra, seria valor gravado errado em silencio.

**Caminho:** troque o override por **regra**, que decide item a item (a regra
cuja origem e a categoria daquele item). Nao contorne com mais override, e nao
peca para o CLI ignorar: o bloqueio existe porque a intencao e ambigua, e
chutar qual das duas origens vence e exatamente o que esta migracao nao faz.

### `operation-type-mismatch`

Receita apontada para categoria devedora (ou despesa para credora). O servidor
recusaria. **Aconteceu de verdade**: 142 receitas bloqueadas numa rodada, zero
escritas. A regra do de/para esta errada, nao o dado. Conserte o `to`.

### `account-and-items`

A categoria antiga aparece no nivel da conta **e** nos itens do mesmo
lancamento. Dado legado incoerente: nao da para decidir mecanicamente qual
trocar. Leve para a EV com uma amostra concreta.

### `input-without-category`

Item sem categoria propria. Nao ha o que trocar naquele item.

### `element-without-category`

Regra `@element`, mas o elemento nao tem categoria oficial cadastrada.
**Nao se chuta.** Aconteceu: 93 bloqueadas numa rodada de 126. Caminho: a EV
cadastra a categoria oficial do elemento (`aegro elements set-categories`) e o
plano roda de novo, ou aquele grupo vira regra explicita.

### `element-rule-on-account-level`

Regra `@element` numa conta **sem itens**. `@element` so existe no nivel de item.
Aquela categoria precisa de destino explicito.

### `element-category-not-postable`

A categoria oficial do elemento esta arquivada ou e sintetica. Guard que existe
porque, sem ele, o destino de `@element` escaparia dos guards do `resolve_map`,
viraria 422 `financial-category.type` no meio da corrida — e 422 estrutural
**aborta o lote inteiro**. Descobrir isso na conta 9.000 de 23.583 seria caro.

### `revenue-item-apportioned-noop` — o segundo no-op medido

Conta de **receita** com itens **e** rateio de safra: o PATCH publico responde
**vazio** e nao grava nada. Medido 0 de 8, enquanto todas as combinacoes vizinhas
gravaram (receita item sem rateio 3/3, receita no nivel da conta 12/12, despesa
item com rateio 5/5 e sem rateio 15/15). `recurrence` era nulo nas 8, entao **nao
e o FNC-184**.

Como a resposta vem vazia, o `apply` nao tem como flagrar — sem este bloqueio
elas seriam contadas como migradas e so o `verify` descobriria depois. O bloqueio
existe para que nem cheguem a ser escritas.

Mesma conversa com a EV que o `recurrence`: nao e erro dela, e um conjunto que
migra quando o backend consertar.

### `stock-location-closed` — o terceiro no-op, e o que travava o cliente

O rateio de custo da conta aponta para um **local de estoque fechado**: local que
responde ao `stock location get` mas **nao aparece** no `stock locations list`. O
PATCH publico responde 200 **com o corpo da conta** e nao grava.

Separacao perfeita em 23 contas (staging, 2026-08-14): 15 de 15 falharam apontando
para o local fora da listagem, 0 de 8 nos locais que aparecem. Detalhe completo,
incluindo o que foi descartado, na secao 4.1.

**Nao existe campo de status** — a listagem publica traz so `key`, `name` e
`farmKey`. O discriminante e "aparece na listagem?", uma inferencia, nao um
contrato da API. Se o endpoint um dia expuser status, o guard muda.

### `apportion-per-item` — recusa limpa, e nao no-op

Conta com `apportionMode = PER_ITEM` tem o custo apropriado item por item, e a API
**recusa alterar `inputs`** com 422 explicito:

> O campo 'inputs' nao pode ser alterado neste lancamento: ele possui apropriacao
> de custo por item (apportionMode=PER_ITEM) vinculada aos itens atuais. Edite os
> itens na tela do Aegro.

Diferente dos tres no-ops: aqui a API **diz** que recusou, e nada e corrompido. O
bloqueio existe para nao gastar a escrita e, sobretudo, para essa recusa nao
aparecer no meio de mil escritas confundida com falha de verdade.

**So vale no nivel do ITEM.** No nivel da conta o payload nao toca `inputs`, e a
mesma conta migra normalmente.

Medido: **1 lancamento em 1.272** (19/08/2026), encontrado pelo canario
estratificado — um `--limit 50` seco nao o tocaria. Para a EV: *"esse tem o custo
dividido item por item, e o Aegro so deixa mexer nele pela tela"*.

Caso classico: o local foi **substituido por um novo de nome quase identico** e as
contas antigas continuaram apontando para o fechado. Suspeite sempre que a fazenda
tiver reorganizado o estoque.

---

## 3. Classes no ledger (`<plano>.ledger.jsonl`)

Uma linha por tentativa, append-only. Rodar o `apply` de novo **retoma**: ele
pula o que tem `ok: true`.

| `class` | Significa | O que fazer |
|---|---|---|
| `ok` | Escreveu | — |
| `structural` | 422 de payload malformado (`financial-category.with-inputs`, `input-order.required`, `cost-apportion`, `financial-category.not-found`, `financial-category.type`) | **O lote aborta no primeiro.** E bug de plano: conserte o de/para e replaneje. Nao suba `--max-failures` |
| `noop-suspected` | Respondeu 200 com a categoria **antiga** no corpo | Era a assinatura do FNC-184, hoje corrigido; num servidor atualizado isto aponta para a quarta causa, sem causa conhecida (4.1). Rode o `verify` |
| `financial-close` | Fechamento financeiro recusou | Inesperado: o guard so reprova mudanca de saldo, e trocar categoria nao muda saldo. Reporte |
| `not-found` | 404 | A conta sumiu entre o plano e a escrita. Replaneje |
| `server` | 5xx | Ja teve retry com backoff. Se persistir, pare |
| `rejected` | Outro 4xx | Leia a mensagem; provavelmente dado especifico daquela conta |

O lote tambem aborta depois de `--max-failures` falhas (25 por padrao). **Nao
apague o ledger** para "comecar limpo" — ele e o que evita reescrever o que ja
foi.

---

## 4. Ler o `verify`

O `verify` prova por **diferenca de conjunto**: re-varre as categorias de origem
e compara. Nao faz um GET por conta.

| Campo | Leitura | Acao |
|---|---|---|
| `planejados` | quantas linhas o plano mandava migrar | — |
| `migrados` | saiu da categoria antiga | — |
| `naoTentados` | planejadas **sem linha no ledger** | **Nao e falha.** E o que falta aplicar. Depois de um canario de 20 em 64, esperar 44 aqui e o certo |
| `falharam` | tentadas e ainda na antiga | Investigue pela classe no ledger |
| `falhaSilenciosa` | ledger diz **ok** e a conta continua na antiga | **A mais grave.** Com os guards atuais deve ser **0**; se nao for, e CLI sem guard ou causa nova — ver 4.1. **Nao siga para o lote** |
| `naCaudaAindaNaAntiga` | cauda + bloqueado + mantido: o plano sabe que ficam | **informativo**, nao e falha (4.3) |
| `colateralDeVerdade` | chave que o plano nunca viu | > 0 e o unico caso que pede replanejar (4.3) |
| `amostraConferida` | deep-diff campo a campo | Ver abaixo |
| `alteracaoColateral` | amostras com `camposAlemDaCategoria` ou `divergenteDoPatch` | **Pare e investigue** |

Sai com **codigo 1** quando algo tentado falhou.

### 4.1 Sao TRES as causas de `falhaSilenciosa`, e o `plan` bloqueia as tres

| Causa | Sintoma na API | `blockedReason` |
|---|---|---|
| **FNC-184** — bill recorrente (**corrigido no servidor**, em producao desde 17/08/2026; desde 20/08 o CLI migra por default, e `--no-allow-recurrent` bloqueia contra servidor antigo) | 200 com a bill antiga | `recurrence` |
| Receita com itens e rateio de safra | resposta **vazia** | `revenue-item-apportioned-noop` |
| Rateio para **local de estoque fechado** | 200 com o corpo da conta | `stock-location-closed` |

E existe uma **quarta**, sem causa identificada: 38 de 1.234 contas (19/08/2026)
responderam 200 e nao gravaram, sendo estruturalmente identicas a centenas que
gravaram. Reproduzivel com concorrencia 1. **Nao ha guard para ela** — quem pega e
o `verify`, e o que fazer esta na SKILL.md 9.1: perguntar a pessoa, e entregar a
lista com link.

As tres sao bloqueadas **antes** da escrita, entao em CLI atual elas aparecem em
`blocked` e **nao** em `falhaSilenciosa`. Confira o numero por motivo em
`meta.blockedByReason`.

> **`override-multi-source` nao entra nesta lista, e a diferenca importa.** Ele
> nao e um no-op da API: a escrita **funcionaria** — e e justamente esse o
> problema, porque gravaria o destino errado em metade dos itens. Nao procure
> sintoma na resposta do servidor; a causa esta no arquivo de/para (secao 2).

**Se `falhaSilenciosa` vier > 0 mesmo assim**, e uma destas duas coisas — e a
distincao importa:

1. **CLI sem um dos guards.** O `stock-location-closed` e recente; skill nova
   contra CLI antigo escreve essas contas. Confira `meta.blockedByReason`: se a
   chave nao existe, o guard nao rodou. Diagnostique como abaixo e atualize o CLI.
2. **Causa nova.** Nenhum dos tres motivos explica, e ai e achado nao mapeado:
   junte as chaves e anexe em
   [tool-aegro-cli#100](https://github.com/aegro/tool-aegro-cli/issues/100), que e
   onde o dossie vive.

**A regra do local fechado, medida em staging 2026-08-14 com separacao perfeita em
23 contas:** o PATCH publico nao persiste quando
`costApportionSummary.stockLocationEntries[]` referencia um **local de estoque
fechado** — local que responde ao `stock location get` mas **nao aparece** no
`stock locations list`.

- 15 de 15 contas apontando para o local fechado falharam;
- 0 de 8 apontando para locais que aparecem na listagem falharam;
- as falhas vao de 2023-08 a 2024-10, com 1 a 7 itens, em L/kg/un/m — **nenhuma**
  dessas dimensoes separa, so o local.

Naquela fazenda o local fechado havia sido **substituido por um novo de nome quase
identico** (so sem um ponto). As contas antigas continuaram apontando para o
fechado. Suspeite disso sempre que a fazenda tiver reorganizado o estoque.

#### Como diagnosticar em 2 minutos

```bash
# 1. os locais ABERTOS da fazenda
aegro stock locations --farm "<fazenda>" --env <env> -o json
```

Depois cruze: para cada `billKey` em `chavesQueFalharam`, pegue no `plano.jsonl` o
`before.costApportionSummary.stockLocationEntries[].stockLocationKey` e veja se
aquela chave esta na lista acima. Se **nao** estiver, e esta causa — confirmado,
sem precisar de mais nenhuma escrita.

**Cuidado:** o `stock locations` nao traz campo de status (vem tudo `None`); o
sinal e a **ausencia na listagem**, nao um campo. Um `stock location get` na
chave responde normalmente e nao prova nada.

#### O que fazer com elas

Com o guard ativo elas nunca sao escritas — chegam como `blocked` e o que resta e
**explicar e decidir**:

- **A UI grava.** Medido: abrir a conta em
  `<host>/farm/<farmId>?billId=<billId>#farm-finance`, trocar a categoria e salvar
  funciona e persiste. Para um punhado de contas, esse e o caminho hoje.
- **Para muitas, espere o fix do backend.** Migrar dezenas na mao pela UI e o
  problema original de volta. Bloqueado sai da migracao automatica e **volta para
  a UI** — isso muda a conta do projeto, entao reporte o tamanho do balde.
- **Se escaparam** (CLI sem guard): **nao reaplique.** E deterministico —
  confirmado em 3 rodadas com os mesmos payloads e tambem com `--concurrency 1`.
  Reaplicar so polui o ledger.
- **Diga a EV o que aconteceu**, sem culpar recorrencia: "N contas ficaram de
  fora porque o rateio delas aponta para um local de estoque que foi fechado. E
  bug conhecido do backend, ja registrado. As outras migraram normalmente."

#### O que esta descartado (cada um com teste)

Latencia de indexacao (relidas 1h depois), concorrencia, categoria de destino (o
mesmo destino grava em outras contas), fechamento financeiro (`INACTIVE`), formato
do payload (falha igual com `{"financialCategoryKey"}` minimo, que nao toca em
rateio), quantidade de itens (26, 13, 9 e 2 gravam), data do lancamento (2024 tem
falha e sucesso), e categoria oficial do elemento (mesmo elemento em falha e em
sucesso).

**Resto em aberto:** sobraram 3 falhas com rateio de **patrimonio** que esta regra
nao explica (os patrimonios existem e estao normais). Se as chaves que falharam
nao casarem com local fechado nenhum, e esse resto — anexe a amostra na issue #100
em vez de tentar explicar.

### 4.2 Canario verde NAO e prova. Estratifique voce mesmo

`--limit N` pega as **N primeiras pendentes do plano**, e a ordem do plano nao e
aleatoria. Medido: num plano com **95,6%** de contas com rateio, as sem rateio
ficaram todas na frente — a primeira com rateio caiu no **indice 14**. O canario
de 20 saiu 19 sem rateio + 1 com, e pegou o no-op por **uma posicao**. Um
`--limit 14` teria fechado 20/20 verde e liberado o lote inteiro.

**O CLI resolve isso agora — use a flag:**

```bash
aegro financial migrate-category apply --farm "<fazenda>" --env staging \
  --plan plano.jsonl --approve sha256:... \
  --limit 20 --stratify-by apportion,level,cashFlow --execute
```

Ela distribui as N do `--limit` pelas classes presentes, em vez de pegar as N
primeiras. As dimensoes sao exatamente `apportion`, `level` e `cashFlow`;
dimensao desconhecida e **erro**, nao silencio.

`--limit` **sem** `--stratify-by` agora imprime aviso dizendo quais classes a
amostra deixou de fora. Nao ignore esse aviso: ele e a diferenca entre canario
verde que significa algo e canario verde que nao significa nada.

Foi assim que a terceira causa apareceu — na epoca a estratificacao era manual,
com um de/para so de `overrides`. Se algum dia precisar da versao manual (CLI sem
a flag), a receita e essa: 2 a 3 contas por combinacao em `overrides`, mais uma
regra que nao casa com nada, porque `rules` nao pode ser vazio.

### 4.3 Cauda e colateral sao campos diferentes — nao confunda

O `verify` antigo tinha um campo so
(`aindaNaCategoriaAntigaSemEstarNoPlano`) que comparava a varredura contra **so as
`planned`**. Todo `unresolved`, `kept` e `blocked` — que por desenho **continuam**
na categoria antiga — caia nele e parecia alteracao por fora. Medido: plano com
`unresolved: 457` reportou 457 "colaterais", zero de verdade. E a doc mandava
replanejar, o que virava laco infinito.

Hoje sao dois campos, e a leitura e direta:

| Campo | O que e | Acao |
|---|---|---|
| `naCaudaAindaNaAntiga` | cauda, bloqueado e mantido — o plano **sabe** que ficam | **informativo.** E o trabalho que falta decidir, nao um problema |
| `colateralDeVerdade` | chave que o plano **nunca viu** | > 0 e o unico caso que pede replanejar |
| `chavesColaterais` | as chaves, para conferir | investigue antes de replanejar |

`colateralDeVerdade > 0` significa lancamento novo na categoria antiga, ou alguem
editando pela UI durante a corrida. **Nao replaneje por causa de
`naCaudaAindaNaAntiga`** — ele nao encolhe replanejando, encolhe decidindo a cauda.

Se o CLI ainda devolver o campo antigo, e versao anterior ao conserto: subtraia
`counts.unresolved + kept + blocked` do valor antes de concluir qualquer coisa.

Sobre `divergenteDoPatch`: e a checagem mais importante do nivel de item. Migrar
item exige reenviar o array `inputs` inteiro, e o risco e atropelar o item que
ninguem pediu para mexer. O `verify` compara o resultado **contra o payload que
o plano enviou** — cada item tem que ter a categoria que o patch pediu, e todo o
resto igual ao `before`. Qualquer coisa aqui e um defeito real.

Tres campos sao ignorados no diff generico **por medicao, nao por conveniencia**:
referencias sao comparadas pela chave (a listagem e o GET serializam `company`
de forma diferente) e `installmentsCount` diverge entre as duas representacoes
para a mesma conta intacta. Alarme que sempre soa e nunca e verdade ensina a
ignorar o alarme.

**Criterio de pronto do trabalho inteiro:**

```bash
aegro financial category-usage --farm "<fazenda>" --from "<categoria antiga>"
```

devolver **0** — ou so o que foi conscientemente bloqueado ou mantido.

---

## 5. Codigos de saida

| Codigo | Quando |
|---|---|
| 0 | tudo certo |
| 1 | o lote abortou (estrutural ou `--max-failures`), ou o `verify` achou falha |
| 2 | falta OAuth (`aegro auth login`) |
| 4 | entrada invalida: de/para com erro, `--approve` divergente, plano editado depois de gerado, plano com mais de 24h, `meta.json` ilegivel |

Exit 4 quase sempre traz na mensagem exatamente o que fazer. Repasse a mensagem
do CLI **como veio**.
