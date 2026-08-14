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
| `aindaNaCategoriaAntigaSemEstarNoPlano` | na antiga e fora do plano | Alguem mexeu por fora, ou a varredura achou algo que o plano nao tinha. Replaneje |
| `amostraConferida` | deep-diff campo a campo | Ver abaixo |
| `alteracaoColateral` | amostras com `camposAlemDaCategoria` ou `divergenteDoPatch` | **Pare e investigue** |

Sai com **codigo 1** quando algo tentado falhou.

### 4.1 Existe um segundo no-op silencioso, e NAO e recorrencia

Quando o `verify` acusa `falhaSilenciosa`, ele imprime que aquilo e "a assinatura
do no-op silencioso (FNC-184)". **Nem sempre e.** Medido em staging, 2026-08-14:

- `recurrentInSweep: 0` no plano inteiro, e as contas afetadas **nao tem campo de
  recorrencia nenhum**. Nao e o FNC-184.
- **Determinismo confirmado em 3 rodadas** com os mesmos payloads: as mesmas
  contas falham sempre, e as outras sempre passam.
- Nao e latencia de indexacao (relidas muito depois, continuam na antiga), nem
  concorrencia (falham igual com `--concurrency 1`), nem a categoria de destino
  (o mesmo destino funciona para outras contas), nem fechamento financeiro
  (`INACTIVE` nesta fazenda).
- **Nao e a migracao.** Um `aegro financial update-bill <chave> --body
  '{"financialCategoryKey":"..."}'` na mesma conta tambem devolve sucesso e nao
  persiste. E a conta, nao o comando.
- Unico correlato encontrado: **todas** as afetadas tem `financialApportion`
  (rateio de custo) preenchido — mas so 31% das que passaram tem. Rateio e
  condicao **necessaria e nao suficiente**; o gatilho exato segue desconhecido.
- Taxa observada: **5 falhas em 41 escritas (12%)** em amostra estratificada.

O que isso muda na sua conduta:

1. **`verify` nao e opcional, e `--sample` nao substitui.** A prova e a diferenca
   de conjunto; sem ela, o ledger diz que 3 mil contas migraram e elas nao
   migraram.
2. **Nao repasse a explicacao do CLI como se fosse a causa.** Diga "N contas
   nao persistiram; parte pode ser recorrencia (FNC-184) e parte e uma segunda
   causa em aberto ligada a rateio de custo" — e cheque `recurrentInSweep` antes
   de culpar recorrencia.
3. **Nao adianta reaplicar.** E deterministico: a segunda tentativa falha igual.
   Reaplicar so gasta tempo e polui o ledger.
4. **Escale.** Uma conta afetada e reproducao completa: chave + PATCH minimo +
   200 OK + nada gravado.

### 4.2 O canario de 20 pode nao ver nada disso

`--limit N` pega as **N primeiras do plano**, e a ordem do plano nao e aleatoria.
Medido: num plano com 95,6% de contas com rateio, as sem rateio ficaram todas na
frente — a primeira com rateio caiu no **indice 14**. Um `--limit 14` teria
fechado 20/20 verde num lote que falha silenciosamente em ~12%.

Enquanto o `apply` nao estratificar a amostra, **nao trate canario verde como
prova**. Antes de liberar o lote:

- rode o `verify` do canario **e** confira se a amostra pegou as classes que
  dominam o plano (rateio, nivel de item, receita);
- se o canario so pegou conta simples, rode um segundo canario maior, ou
  monte um plano so com `overrides` de contas escolhidas a dedo, uma por classe.
  Foi assim que a segunda classe apareceu.

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
