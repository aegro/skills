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

### `recurrence` — so com `--no-allow-recurrent`

O `plan` **migra recorrente por padrao**. Este motivo so aparece quando o plano
foi gerado com `--no-allow-recurrent`, o escape para servidor mais antigo que a
correcao — la o PATCH em recorrente responde 200 com a conta antiga e nao grava.

- Gerado **com** a flag contra producao ou staging: foi engano. Rode o `plan` de
  novo sem ela.
- Gerado **sem** a flag e mesmo assim com `recurrence`: CLI anterior a 0.20.0,
  que bloqueava por padrao. Atualize e rode o `plan` de novo.

Mesmo no padrao fica de fora o recorrente **com parcela paga E itens**
(`settled-recurrence-inputs`): o Aegro recusa alterar os itens dele. No nivel da
conta ele migra, e a maioria e de nivel conta.

**Como dizer a EV**, quando o escape foi usado de proposito:

> Esses N lancamentos sao recorrentes, e o servidor desta rodada ainda nao grava
> alteracao neles. Ficaram de fora para nao fingir que migraram; rodando contra o
> Aegro atualizado, entram com o mesmo comando, sem trabalho novo seu.

Cuidado com dois campos diferentes no `meta.json`, de proposito:

- `recurrentInSweep` — quantos recorrentes existem no recorte;
- `recurrentBlocked` — quantos o plano bloqueou como `recurrence` (zero sem o
  escape; o `settled-recurrence-inputs` conta a parte, em `blockedByReason`).

Recorrente que nao casa com regra nenhuma fica `unresolved`, nao `blocked`.
Nao some os dois.

### `override-multi-source` — a decisao conta a conta nao alcanca duas origens

O lancamento tem itens em **duas ou mais categorias de origem diferentes**, e o
override e decisao por CONTA: um destino unico seria escrito em todos os itens,
colapsando duas categorias antigas numa so — com status `planned` e ninguem
percebendo.

**Como isso aparece na pratica:** quando a cauda vira override em massa. O
contorno de recortar por data de pagamento gera override as centenas, e conferir
que nenhum deles tem itens em mais de uma origem so da para fazer **a mao, conta
a conta**. Onde ocorrer, e valor gravado errado em silencio.

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
**aborta o lote inteiro**. Descobrir isso no meio de um lote grande seria caro.

### `revenue-item-apportioned-noop` — so com `--no-allow-revenue-item-apportioned`

Conta de **receita** com itens **e** rateio de safra. Em servidor sem a correcao,
o PATCH responde **vazio** e nao grava; o Aegro atual grava, e o `plan` **migra
por padrao**. O motivo aparece em dois casos:

- plano gerado com `--no-allow-revenue-item-apportioned` — o escape para servidor
  antigo. Contra producao ou staging foi engano: rode o `plan` de novo sem ela;
- CLI anterior a 0.25.0, que bloqueava por padrao sem flag para soltar. Atualize
  e rode o `plan` de novo.

Contra servidor antigo **sem** o escape, o CLI atual nao conta a resposta vazia
como sucesso: a linha cai no ledger como falha com `status: 204`. Falha
concentrada nesta classe e esse caso — replaneje com o escape.

Conversa com a EV igual a do `recurrence`: nao e erro dela, e um conjunto que
migra contra o Aegro atualizado, sem trabalho novo.

### `stock-location-closed` — so com `--no-allow-closed-stock-location`

O rateio de custo da conta aponta para um local de estoque **fora da listagem**:
responde ao `stock location get` mas **nao aparece** no `stock locations list`.
Em servidor sem a correcao, o PATCH recusava calado, com **204 sem corpo**, toda
conta cujo rateio apontasse para **cadastro excluido** — local de estoque,
patrimonio, safra ou fornecedor. O Aegro atual preserva o vinculo ja gravado e a
conta segue editavel, e o `plan` **migra por padrao**. O motivo aparece em dois
casos:

- plano gerado com `--no-allow-closed-stock-location` — o escape para servidor
  antigo. Contra producao ou staging foi engano: rode o `plan` de novo sem ela;
- CLI anterior a 0.25.0, que bloqueava por padrao sem flag para soltar. Atualize
  e rode o `plan` de novo.

Com o escape, uma listagem de locais **vazia** bloqueia toda conta com rateio de
estoque, e o `plan` avisa no stderr. Antes de concluir que o cadastro tem local
fechado, confira com `aegro stock locations` — pode ser falha de leitura.

**Nao existe campo de status** — a listagem publica traz so `key`, `name`,
`farmKey` e as datas de auditoria. O discriminante do guard e "aparece na
listagem?", uma inferencia, nao um contrato da API.

Caso classico: o local foi **substituido por um novo de nome quase identico** e as
contas antigas continuaram apontando para o fechado.

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

E raro a ponto de so aparecer em canario estratificado — amostra seca nao o
toca. Para a EV: *"esse tem o custo dividido item por item, e o Aegro so deixa
mexer nele pela tela"*.

---

## 3. Classes no ledger (`<plano>.ledger.jsonl`)

Uma linha por tentativa, append-only. Rodar o `apply` de novo **retoma**: ele
pula o que tem `ok: true`.

| `class` | Significa | O que fazer |
|---|---|---|
| `ok` | Escreveu | — |
| `structural` | 422 de payload malformado (`financial-category.with-inputs`, `input-order.required`, `cost-apportion`, `financial-category.not-found`, `financial-category.type`) | **O lote aborta no primeiro.** E bug de plano: conserte o de/para e replaneje. Nao suba `--max-failures` |
| `noop-suspected` | Respondeu 200 com a categoria **antiga** no corpo | Concentrado em recorrentes: servidor sem a correcao de recorrente — pare e replaneje com `--no-allow-recurrent` (4.1). Fora delas, e a causa sem nome (4.1). Rode o `verify` |
| falha com `status: 204` | Resposta **sem corpo**: nada gravou. O CLI atual registra como falha (em geral `rejected`); antes da 0.25.0 entrava como `ok` | Concentrado em receita com itens + rateio de safra, ou em rateio de local fora da listagem: servidor antigo — pare e replaneje com o escape da classe (4.1). Fora delas, e causa nova: **pare** e junte as chaves |
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
| `falhaSilenciosa` | ledger diz **ok** e a conta continua na antiga | **A mais grave.** As tres causas conhecidas nao chegam aqui num CLI atual; o que aparecer e CLI anterior a 0.25.0, a causa sem nome ou achado novo — ver 4.1. **Nao siga para o lote** |
| `naCaudaAindaNaAntiga` | cauda + bloqueado + mantido: o plano sabe que ficam | **informativo**, nao e falha (4.3) |
| `colateralDeVerdade` | chave que o plano nunca viu | > 0 e o unico caso que pede replanejar (4.3) |
| `amostraConferida` | deep-diff campo a campo | Ver abaixo |
| `alteracaoColateral` | amostras com `camposAlemDaCategoria` ou `divergenteDoPatch` | **Pare e investigue** |

Sai com **codigo 1** quando algo tentado falhou.

### 4.1 As tres causas conhecidas de no-op migram por padrao

Tres classes ja responderam sucesso sem gravar. O Aegro atual grava as tres, e o
`plan` as **migra por padrao**; cada uma tem um escape que volta a bloquea-la,
para usar **so** contra servidor sem a correcao:

| Classe | Sintoma em servidor sem a correcao | Escape | `blockedReason` |
|---|---|---|---|
| Lancamento recorrente | 200 com a conta antiga | `--no-allow-recurrent` | `recurrence` |
| Receita com itens e rateio de safra | **204 sem corpo** | `--no-allow-revenue-item-apportioned` | `revenue-item-apportioned-noop` |
| Rateio apontando para cadastro excluido (o guard olha local de estoque fora da listagem) | **204 sem corpo** | `--no-allow-closed-stock-location` | `stock-location-closed` |

No Aegro atual o cadastro excluido que a conta **ja referenciava** e preservado e
a conta segue editavel; referencia inexistente volta **422 nomeando a chave**.

**No CLI atual nenhuma delas passa calada, nem contra servidor antigo**: o 200 com
a categoria antiga vira `noop-suspected` e o 204 vira falha com `status: 204` no
ledger. Entao elas aparecem em `falharam`, nao em `falhaSilenciosa`. Lote que
falha concentrado numa dessas classes e servidor antigo: pare, gere o plano de
novo com o escape da classe e leve o hash novo para aprovacao.

E existe uma **quarta**, sem causa identificada: cerca de 3% das contas
respondem "200" e nao gravam, sendo estruturalmente identicas as que gravaram.
Reproduzivel com concorrencia 1. **Nao ha guard para ela** — quem pega e o
`verify`, e o que fazer esta na SKILL.md 9.1: perguntar a pessoa, e entregar a
lista com link.

> **`override-multi-source` nao entra nesta lista, e a diferenca importa.** Ele
> nao e um no-op da API: a escrita **funcionaria** — e e justamente esse o
> problema, porque gravaria o destino errado em metade dos itens. Nao procure
> sintoma na resposta do servidor; a causa esta no arquivo de/para (secao 2).

**Se `falhaSilenciosa` vier > 0**, alem da quarta causa, confira estas duas — e
a distincao importa:

1. **CLI anterior a 0.25.0.** Ele contava a resposta sem corpo como sucesso: conta
   de receita com itens e rateio de safra, ou com rateio em cadastro excluido,
   escrita contra servidor antigo, caia aqui. Cruze as chaves com a tabela acima e
   atualize o CLI antes do proximo lote.
2. **Causa nova.** Nenhuma das classes acima explica, e ai e achado nao mapeado:
   junte as chaves e anexe em
   [tool-aegro-cli#100](https://github.com/aegro/tool-aegro-cli/issues/100), que e
   onde o dossie vive.

**A regra do guard de local fechado** (so roda com
`--no-allow-closed-stock-location`): o plano bloqueia quando
`costApportionSummary.stockLocationEntries[]` referencia um local de estoque que
responde ao `stock location get` mas **nao aparece** no `stock locations list`.
Em servidor sem a correcao, toda conta assim falhava, e nenhuma das que apontam
para locais listados. Suspeite dela sempre que a fazenda tiver reorganizado o
estoque.

#### Como diagnosticar em 2 minutos

Para confirmar que falhas concentradas sao esta classe (servidor antigo):

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

- **CLI atual contra o Aegro atual:** elas migram. Nao ha o que fazer alem de
  repassar o aviso do `plan`.
- **Bloqueadas sem o escape na linha de comando:** CLI anterior a 0.25.0. Atualize
  e rode o `plan` de novo. **Nao mande a EV migrar na mao** — dezenas pela tela e o
  problema original de volta.
- **Bloqueadas com o escape (servidor antigo):** para um punhado, a tela grava —
  abrir a conta em `<host>/farm/<farmId>?billId=<billId>#farm-finance`, trocar a
  categoria e salvar. Para muitas, reporte o tamanho do balde e deixe para a
  rodada contra o servidor atualizado.
- **Diga a EV o que aconteceu**, sem culpar recorrencia: "N contas ficaram de fora
  porque o rateio delas aponta para um cadastro que foi excluido, e o servidor
  desta rodada ainda nao aceita essa alteracao. Elas entram contra o Aegro
  atualizado, sem trabalho novo seu. As outras migraram normalmente."

**Rateio de patrimonio excluido tem a mesma causa.** Para conferir uma chave,
`aegro assets get` traz `isDeleted` — olhe ele, nao `status` (SKILL.md 9.0).

Se as chaves que falharam nao casarem com local fechado nem com cadastro
excluido, e achado novo — anexe a amostra na issue #100 em vez de tentar
explicar.

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
