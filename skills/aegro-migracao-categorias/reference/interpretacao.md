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
| `kept` | Override com `keep: true`: fica na antiga de proposito | **nao** |
| `blocked` | Nao deve ser escrito; ver secao 2 | **nao** |

`unresolved` **nao e erro**. E o desenho: sem regra e sem override, o CLI nunca
chuta. O trabalho e transformar `unresolved` em `planned` ou em `kept` pela tela.

---

## 2. Motivos de bloqueio

### `recurrence` — o unico que espera backend

O lancamento e recorrente. O PATCH da API publica em bill recorrente **responde
200 e nao salva** (FNC-184: `updateBillWithRecurrences` devolve a bill antiga do
banco). Numa base de folha isso significaria "migrei 3 mil contas" com zero
persistido.

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

---

## 3. Classes no ledger (`<plano>.ledger.jsonl`)

Uma linha por tentativa, append-only. Rodar o `apply` de novo **retoma**: ele
pula o que tem `ok: true`.

| `class` | Significa | O que fazer |
|---|---|---|
| `ok` | Escreveu | — |
| `structural` | 422 de payload malformado (`financial-category.with-inputs`, `input-order.required`, `cost-apportion`, `financial-category.not-found`, `financial-category.type`) | **O lote aborta no primeiro.** E bug de plano: conserte o de/para e replaneje. Nao suba `--max-failures` |
| `noop-suspected` | Respondeu 200 com a categoria **antiga** no corpo | Assinatura do FNC-184. Rode o `verify` |
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
| `falhaSilenciosa` | ledger diz **ok** e a conta continua na antiga | **A mais grave.** O CLI culpa o FNC-184, mas existe uma segunda classe — ver secao 4.1. **Nao siga para o lote** |
| `aindaNaCategoriaAntigaSemEstarNoPlano` | **nao leia direto — o numero infla.** Ver 4.3 | desconte a cauda antes de concluir qualquer coisa |
| `amostraConferida` | deep-diff campo a campo | Ver abaixo |
| `alteracaoColateral` | amostras com `camposAlemDaCategoria` ou `divergenteDoPatch` | **Pare e investigue** |

Sai com **codigo 1** quando algo tentado falhou.

### 4.1 Sao TRES as causas de `falhaSilenciosa`, e o CLI so nomeia uma

A mensagem do `verify` diz que `falhaSilenciosa` e "a assinatura do no-op
silencioso (FNC-184)". Hoje isso esta errado em dois tercos dos casos conhecidos:

| Causa | Sintoma | O plano bloqueia? |
|---|---|---|
| **FNC-184** — bill recorrente | 200 com a bill antiga | sim (`recurrence`) |
| **Receita com itens e rateio de safra** | resposta **vazia** | sim (`revenue-item-apportioned-noop`) |
| **Rateio apontando para local de estoque FECHADO** | 200 com o corpo da conta | **nao ainda** — [tool-aegro-cli#100](https://github.com/aegro/tool-aegro-cli/issues/100) |

A terceira e a unica que ainda chega a ser escrita. Enquanto o guard nao subir, e
com ela que voce tem de se preocupar.

**A regra, medida em staging 2026-08-14 com separacao perfeita em 23 contas:** o
PATCH publico nao persiste quando `costApportionSummary.stockLocationEntries[]`
referencia um **local de estoque fechado** — local que responde ao
`stock location get` mas **nao aparece** no `stock locations list`.

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

- **Nao reaplique.** E deterministico: confirmado em 3 rodadas com os mesmos
  payloads, e tambem com `--concurrency 1`. Reaplicar so polui o ledger.
- **A UI grava.** Medido: abrir a conta em
  `<host>/farm/<farmId>?billId=<billId>#farm-finance`, trocar a categoria e salvar
  funciona, e persiste. Para um punhado de contas, esse e o caminho hoje.
- **Para muitas, espere o guard.** Migrar dezenas na mao pela UI e o problema
  original de volta.
- **Diga a EV o que aconteceu**, sem culpar recorrencia: "N contas nao gravaram
  porque o rateio delas aponta para um local de estoque que foi fechado. E bug
  conhecido do backend, ja registrado. As outras migraram normalmente."

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

Enquanto o `apply` nao estratificar, **monte a amostra voce**:

1. Leia o `plano.jsonl` e agrupe os `planned` por
   `(before.financialApportion.type, level, cashFlow)` — sao poucas combinacoes.
2. **Mostre a composicao a EV**: "o plano e 90% ASSET_PRORATE/item, 4%
   STOCK_INPUTS/item, 4% sem rateio, 2% CROP_PRORATE/conta".
3. Escolha **2 a 3 contas de cada** combinacao e monte um de/para so com
   `overrides` para elas (mais uma regra que nao casa com nada, porque `rules`
   nao pode ser vazio — ex.
   `{"when": {"descriptionContains": "zzz-nada-casa-zzz"}}`).
4. `plan` -> `apply --execute` -> `verify`. Custa uma varredura, e e a unica forma
   de canario verde significar alguma coisa.
5. **So depois** rode o canario normal e o lote sobre o plano de verdade.

Foi exatamente assim que a terceira causa apareceu. Se a EV achar o passo caro,
compare com o custo de descobrir na conta 9.000 de 23.583.

### 4.3 `aindaNaCategoriaAntigaSemEstarNoPlano` conta a cauda como se fosse colateral

O campo compara a varredura contra **so as contas `planned`**. Entao todo
`unresolved`, `kept` e `blocked` — que por desenho **continuam** na categoria
antiga — entra nessa conta e parece alteracao por fora.

**Medido:** um plano com `unresolved: 457` e `planned: 3163` devolveu
`aindaNaCategoriaAntigaSemEstarNoPlano: 457`. Exatamente o `unresolved`. Zero
colateral de verdade.

Isso importa porque a leitura ingenua ("alguem mexeu por fora, replaneje") vira
**laco infinito**: voce replaneja, a cauda continua sendo cauda, o numero volta
igual.

**Como ler de verdade:** desconte do valor os status que nao deviam ter saido, que
estao no `counts` do `<plano>.meta.json`:

```
colateral real = aindaNaCategoriaAntigaSemEstarNoPlano
                 - (counts.unresolved + counts.kept + counts.blocked)
```

- **Resultado 0 ou negativo** → nao houve colateral. Nao replaneje por causa
  disso; o numero e a cauda, e a cauda e o trabalho que falta decidir.
- **Resultado positivo** → aquilo sim e conta que o plano nunca viu. Ai
  replanejar e o certo: apareceu lancamento novo na categoria antiga, ou alguem
  editou pela UI durante a corrida.

Ja esta reportado como bug de contagem no CLI. Enquanto nao subir, faca a
subtracao **antes** de dizer qualquer coisa a EV — e diga o resultado da conta,
nao o campo cru.

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
