---
name: aegro-conciliacao-bancaria
requires-cli: 0.30.1
description: >-
  Concilia o extrato bancario com o financeiro do Aegro pela CLI: importa o
  OFX, casa entradas do extrato com os movimentos internos, confirma em lote e
  fecha o saldo Aegro x banco no periodo. Use quando pedirem "conciliar o
  banco", "importar OFX", "o saldo nao bate com o extrato", "conciliacao
  bancaria", "baixar o que ja foi pago no banco"; EN "bank reconciliation",
  "import OFX". NAO use para lancar conta nova (use
  /aegro-lancamento-financeiro) nem para divergencia de estoque (use
  /aegro-reconciliacao-estoque).
---

# Aegro Conciliacao Bancaria

Skill para conciliar o extrato bancario com o financeiro do Aegro pela CLI. O
objetivo real da conciliacao e de **saldo**: no fechamento do periodo, o saldo de
cada conta bancaria no Aegro deve bater com o saldo do extrato do banco. Casar
lancamento a lancamento e o meio; fechar o saldo e o fim.

Aja como um **copiloto que puxa a conciliacao pra frente**: proponha lotes
concretos, mostre o progresso, e **sempre termine sugerindo o proximo passo**. O
usuario deve conseguir avancar respondendo em uma palavra.

> **Requer login OAuth.** A conciliacao usa APIs internas do Aegro. Rode
> `aegro auth login`. Em modo API key os comandos falham com exit 2.
>
> **Identifique a fazenda com `--farm "<nome|farm::key>"`** em cada comando. O
> `farms select` grava num state global por maquina: com varias sessoes abertas
> (uma por fazenda), a selecao de uma troca o alvo das outras. Em safe mode, a
> escrita recusa fazenda implicita e falha com `IMPLICIT_FARM_BLOCKED`.
>
> **Fluxo critico (dados financeiros).** O agente **propoe**, o humano **confirma**.
> Nunca concilie nem baixe uma parcela em silencio. Toda escrita suporta
> `--dry-run` (previa) e so executa com `--execute`.

---

## 1. Vocabulario

| Termo | CLI | Descricao |
|---|---|---|
| Entrada do extrato | `bank-reconciliation entries` | Movimentacao importada do OFX (a conciliar). Status PENDING/CONFIRMED/IGNORED. O memo geralmente traz **o nome do fornecedor/pessoa** — use como ancora. |
| Movimento interno | `bank-reconciliation candidates` | Lancamento na conta (carrega a parcela e o **fornecedor** via `bill.company`). E o que se casa com a entrada. |
| Conciliar | `bank-reconciliation confirm` | Vincula entrada(s) do extrato a movimento(s) interno(s). |
| Ignorar | `bank-reconciliation ignore` | Marca entrada como IGNORADA. **Ultimo recurso** (§ guardrails). |
| Desfazer | `bank-reconciliation undo` | Reverte uma conciliacao ja registrada. |
| Baixar simples | `financial realize` | Baixa a parcela pelo valor, na data e na **conta agendados** (API publica). Sem desconto/juros/data/conta: se o extrato difere em qualquer um deles, e `settle-installments`. |
| Baixar ajustado | `financial settle-installments` | Baixa UMA ou VARIAS parcelas com **data, desconto, juros e conta** do extrato, sem alterar a despesa (§7). Atomico, com previa do servidor. E o caminho quando o extrato difere do agendado. |
| Baixar com valor livre | `financial settle` | UMA parcela com `--realized-amount` (valor pago que nao e `valor + juros - desconto`). So para esse caso. |
| Banda | (filtros) | Janela de valor (±%) e data (±dias) para achar candidatos de uma entrada. |

**Resolucao de chave da conta (gotcha):** `accounts --farm-id <idLegado>` devolve o
`id` cru (ObjectId). Comandos com `--account` exigem a **key** `bankAccount::<id>` —
obtenha em `aegro bank-accounts list` (campo `key`) ou prefixe o id com
`bankAccount::`. Ja `import-ofx` e `clear-pending` usam o id cru (`--account-id`).

---

## 2. Fluxo

```text
1. Selecionar conta        -> --farm "<fazenda>" em cada comando; pegar a key bankAccount::...
2. Importar OFX            -> bank-reconciliation import-ofx --execute
3. Listar entradas PENDING -> bank-reconciliation entries
4. Casar (matching)        -> bank-reconciliation candidates (banda ±%/±dias) + cruzamento
5. APRESENTAR + PLACAR     -> tabela lado a lado com fornecedor (§3) + proximo passo
6. Baixar o que esta aberto -> financial settle-installments (data/desconto/juros/conta, em lote) (§7)
7. Conciliar / ignorar     -> confirm --execute / ignore --execute (duplicatas: §8)
8. Fechar: conferir saldo  -> placar; saldo do periodo == saldo do extrato
```

---

## 3. Como apresentar (isto faz a conversa fluir)

A forma de mostrar os matches **importa tanto quanto o algoritmo**. Regras:

1. **Tabela lado a lado, sempre.** Nunca despeje chaves cruas nem paragrafos. Use:

   | Data | Extrato (memo) | Lancamento (Aegro) | **Fornecedor** | Δdias | Diferenca | Valor | Conf. |
   |---|---|---|---|--:|--:|--:|:--:|

2. **Fornecedor e coluna de 1a classe.** O memo do banco quase sempre traz o
   fornecedor/pessoa; o lado Aegro tem `bill.company`. Compare os dois:
   - servem para o humano **reconhecer** o lancamento num relance;
   - **fornecedor divergente** (valor/data batem, mas empresas diferentes) e
     forte sinal de **falso-positivo** → rebaixe a confianca, nao concilie.

3. **Placar de saldo a cada passo.** Termine mostrando o progresso rumo ao fim
   (fechar saldo): `N conciliadas · M pendentes · saldo banco R$X × Aegro R$Y ·
   falta R$Z para fechar <periodo>`. Isso da direcao e incentivo.

4. **Linguagem natural.** Ex.: *"Saida de R$ 1.234,56 em 12/03 (memo 'FORNECEDOR
   X') → parcela nº2 de 'Compra de insumos', vence 10/03, fornecedor FORNECEDOR X
   LTDA. Diferenca R$ 0,00. Confirmar?"*

---

## 4. Escada de confianca (caminhe nela com o usuario)

Nao jogue todas as bandas de uma vez. Comece **estreito** (alta confianca) e
**alargue sob demanda**, resumindo cada degrau e sugerindo o proximo.

| Degrau | Banda (valor / data) | Postura |
|---|---|---|
| 🟢 Verde | exato / exata, **1** candidato, fornecedor coerente | lote unico, `confirm` direto |
| 🟢 Verde-data | **valor exato** / ±3 dias | lote, `confirm` direto se o movimento ja existe (so a data liquidou fora); parcela NAO PAGA → `settle-installments` antes (§6) |
| 🟡 Amarelo | ±10% valor / ±3–7 dias | item-a-item; diferenca costuma ser **desconto/juros** → `settle-installments` antes de conciliar |
| 🟠 Largo | ±10% / ±15 dias | so sob pedido; **alerta de falso-positivo** (afrouxar valor gera par semanticamente errado) |
| 🔴 Sem match | fora da banda, ou fornecedor diverge | criar lancamento/transferencia (§10), ou em ultimo caso `ignore` |

Observacoes praticas:
- **Afrouxar data** (mantendo valor exato) e seguro e produtivo. **Afrouxar
  valor** (±10%) e arriscado: traz falso-positivo e ainda esbarra na regra de
  **soma exata** do `confirm` — so vale se a diferenca for desconto/juros real.
- A cada degrau, informe: quantos 🟢, quantos 🟡, quantas **colisoes** (§8), e
  quantos **so-no-banco** (sem contrapartida — precisam de lancamento, nao de
  busca).

---

## 5. Postura de dialogo (motor de proximos passos)

- **Propor → confirmar.** Apresente um lote concreto e pergunte. O humano decide.
- **Todo turno termina com 1–3 proximos passos** de maior valor, ex.:
  *"Posso: (1) conciliar os 3 verdes agora; (2) abrir a proxima banda; (3)
  resolver as duplicatas que poluem os resultados. Qual?"*
- **Incentive com progresso**, nao com jargao: "faltam 3 lancamentos e R$ X pra
  fechar junho" > "restam N external movements PENDING".
- **Comemore fechamentos** e ofereca continuar: "4 conciliadas ✅; sigo pros
  amarelos de junho?".
- Lote para 🟢; **item-a-item** para 🟡/🟠, PDF (§11) e qualquer coisa com colisao.

---

## 6. Regras de negocio (guardrails — alerta, nao bloqueio)

1. **Confirmar exige soma exata.** A soma dos movimentos internos selecionados
   deve ser **exatamente igual** ao total das entradas do extrato. Valide ANTES
   de `confirm` (o servidor rejeita se diferir). Se difere por pouco → e
   desconto/juros: use `settle-installments` (§7).
2. **Baixar != conciliar (dois atos).** Se a parcela certa esta **NAO PAGA**,
   primeiro **baixe** na data do extrato e **na conta do extrato** (cria o
   movimento onde o OFX esta), depois **concilie**. Avise que sao duas acoes e
   confirme ambas. Nunca baixe em silencio.
3. **Fornecedor deve fazer sentido.** Valor+data batendo mas fornecedor/memo
   divergente = provavel falso-positivo. Nao concilie so por coincidencia
   numerica.
4. **Evitar `ignore`.** Ignorar **descasa o saldo** Aegro x banco. Sempre alerte
   e ofereca a alternativa antes. Uso legitimo: entrada que realmente NAO deve
   refletir no Aegro (ex.: **duplicata de OFX**, §8).
5. **Nem toda entrada/saida e receita/despesa.** Contrapartida em conta do
   proprio cliente → **transferencia** (§10), nao receita/despesa.

---

## 7. Baixa ajustada — data, desconto, juros e conta (`financial settle-installments`)

Quando a parcela esta **NAO PAGA** e o extrato difere do agendado, baixe com
ajuste **sem alterar a despesa** (o valor do lancamento e preservado; a
diferenca entra como desconto ou juros na baixa):

- **Banco < agendado** → **desconto** (`discount`).
- **Banco > agendado** → **juros** (`interest`).
- Baixe na **data do extrato** (`--date` ou coluna `realizedDate`).
- Baixe na **conta do extrato**: `--bank-account bankAccount::<id>`, a mesma key
  do `--account` da conciliacao. Sem isso a parcela fica na conta agendada, o
  movimento nasce em outra conta e nao aparece como candidato no OFX.

**Varias parcelas pagas juntas** (um PIX, um boleto agrupado, uma linha do
extrato para N contas) sao **um comando so**, nao N baixas (a excecao e a
parcela paga parcialmente, abaixo). Monte o arquivo com uma linha por parcela.
Separador `;`, sempre: com `,`, sob `key,discount,interest`, a linha
`installment::a,115,36` vira desconto 115 e juros 36 sem recusa nenhuma. Arquivo
em UTF-8, data em `AAAA-MM-DD`, valor sem milhar ambiguo (`1500` ou `1.500,00`,
nunca `1.500`) e cabecalhos exatos, com esta grafia: `key`, `realizedDate`,
`discount`, `interest`, `bankAccount`. O resto das regras de arquivo esta em
`/aegro-financeiro` ("Baixa com data, desconto, juros ou conta"):

```text
key;discount;interest
installment::<id1>;115,36;
installment::<id2>;;
installment::<id3>;;12,50
```

```bash
# previa: o SERVIDOR calcula o valor pago de cada parcela e o total
aegro financial settle-installments --farm "<fazenda>" --map baixas.csv \
  --date 2026-06-18 --bank-account bankAccount::<id> --dry-run
# so apos o usuario aprovar, o MESMO comando com --execute
aegro financial settle-installments --farm "<fazenda>" --map baixas.csv \
  --date 2026-06-18 --bank-account bankAccount::<id> --execute
# uma parcela so: flags no lugar do arquivo — tambem previa antes
aegro financial settle-installments --farm "<fazenda>" --key installment::<id> \
  --date 2026-06-18 --discount 115,36 --bank-account bankAccount::<id> --dry-run
aegro financial settle-installments --farm "<fazenda>" --key installment::<id> \
  --date 2026-06-18 --discount 115,36 --bank-account bankAccount::<id> --execute
```

`--bank-account` aqui nao e opcional: e a key da conta do extrato. Celula vazia
na coluna `bankAccount` (ou `realizedDate`) usa o valor da flag; `realizedDate`
vazia sem `--date` recusa o lote (exit 4) e nada e gravado.

Antes do `--execute`, confira no `--dry-run`:

- **o total do servidor** — `resumoDoServidor.netAmount`, o numero esta em
  `losslessAmountRepresentation` — bate com a linha do extrato: e o que o
  `confirm` vai exigir depois (§6.1). Use esse total, nao a soma das linhas: a
  lista `baixas` traz so as 20 primeiras (`baixasOmitidas` diz quantas faltam).
  Nao bateu: o desconto/juros de alguma linha esta errado; corrija antes de
  gravar;
- `conta.muda` e `conta.nome` de cada linha — e a conta do extrato? Se a conta
  agendada da parcela nao e a do extrato e `conta.muda` veio `false`, **pare**:
  a parcela seria paga na conta agendada e o movimento nasceria fora do OFX.
  Confira o `--bank-account` antes de gravar;
- `naoConseguiLerEstadoAtual` vazio. Preenchido: **pare** e repita o
  `--dry-run` depois; gravar assim perde o registro da conta de antes.

Os movimentos a conciliar nascem da baixa. Pegue as keys deles com
`bank-reconciliation candidates` na janela da data do extrato (o movimento
traz a parcela de origem): sao elas que vao em `--movement`, nao as keys das
parcelas. Antes do `confirm`, confira que a parcela de origem de cada
movimento escolhido e uma das chaves do lote que voce baixou, e que o numero de
movimentos e o numero de parcelas do lote. Movimento de outra parcela com o
mesmo valor concilia o extrato com o lancamento errado.

Depois concilie a entrada do extrato com os movimentos gerados (1 entrada : N
movimentos quando foi um pagamento so):

```bash
aegro bank-reconciliation confirm --farm "<fazenda>" --account bankAccount::<id> \
  --external <ext> --movement <mov1> --movement <mov2> --dry-run
aegro bank-reconciliation confirm --farm "<fazenda>" --account bankAccount::<id> \
  --external <ext> --movement <mov1> --movement <mov2> --execute
```

Regras do lote:

- **Tudo-ou-nada.** Uma linha invalida recusa o lote inteiro e nada e gravado. A
  leitura previa do CLI nomeia de uma vez as parcelas **ja pagas** ou com
  **conciliacao confirmada**; tire-as do arquivo e repita. Recusa que vem do
  servidor para na primeira parcela: tire a nomeada e repita o `--dry-run`.
- **Fechamento financeiro.** Data do extrato dentro de um fechamento financeiro
  ativo e recusada (exit 4). Confira em `aegro financial closes`; o periodo so
  reabre pela tela.
- **Desconto/juros em branco mantem** o que a parcela ja tinha; `0` zera.
  `--discount`/`--interest` por flag so valem com UMA parcela — com varias, use
  as colunas.
- **Parcela ja paga com data ou valor errado:** reabra antes (`financial
  reopen-installments --dry-run`, depois `--execute --confirm-undo`). Reabrir
  **apaga desconto e juros** e **nao devolve a conta** anterior — a conta de antes
  esta em `baixas[].conta.de` na saida do comando que baixou. O campo
  `desfazer` dessa saida traz o `reopen-installments ... --dry-run` do lote
  inteiro; para aplicar, troque `--dry-run` por `--execute --confirm-undo`.
- **Parcela com conciliacao CONFIRMADA** nao reabre: desfaca a conciliacao
  antes. `bank-reconciliation undo --account <key> --key <reconKey>` e escrita:
  `--dry-run` primeiro, `--execute` so com o sim do usuario. Avise antes que o
  conserto tem 3 passos (desfazer a conciliacao, reabrir, baixar de novo) e
  depois um `confirm` novo; parar no meio deixa a entrada do extrato pendente e
  a parcela em aberto.

  ```bash
  aegro bank-reconciliation undo --farm "<fazenda>" --account bankAccount::<id> \
    --key <reconKey> --dry-run
  aegro bank-reconciliation undo --farm "<fazenda>" --account bankAccount::<id> \
    --key <reconKey> --execute
  ```
- **`NOT_PERSISTED` depois do `--execute`:** o lote FOI aceito e as parcelas
  estao pagas; o que divergiu foi um campo (data, conta, desconto, juros ou
  valor pago). **Nao repita** — a repeticao e recusada como ja paga. Leia a
  divergencia e confira em `financial installments`. O conserto e reabrir **so
  as parcelas nomeadas na divergencia** e baixa-las de novo com os valores
  certos (desconto e juros informados outra vez). Nunca reabra o lote inteiro:
  reabrir apaga desconto e juros de todas e nao devolve a conta.
- **Erro de rede ou 5xx no `--execute`: nao repita.** O CLI rele antes de
  reportar e diz "NAO repita" quando o lote foi aplicado; se nem a releitura
  funcionou, confira em `financial installments` antes de qualquer tentativa.
- **Valor pago que nao e `valor + juros - desconto`** (pagamento parcial, valor
  negociado sem desconto): o lote nao aceita. Use `financial settle`, uma parcela
  por vez, com `--realized-amount`. Uma linha do extrato que quitou varias contas,
  uma delas parcial: `settle-installments` para as cheias e `settle
  --realized-amount` para a parcial, e depois o `confirm` 1:N com todos os
  movimentos. Nunca force desconto na parcial para ela caber no lote. Avise
  antes o que o `settle --realized-amount` faz: **quita a parcela INTEIRA** pelo
  valor menor (o saldo nao fica em aberto), grava desconto e juros com o valor
  das flags (0 se omitidas, apagando os de antes) e **nao troca a conta**:
  parcial saindo de conta diferente da agendada, por enquanto, so pela tela do
  Aegro.
- **Teto de 500 parcelas por lote**; acima disso, divida.
- **`realize` so serve aqui** quando a conta e a data agendadas ja sao as do
  extrato; fora isso o movimento nasce no lugar errado.

**Versao:** `settle-installments` existe a partir da CLI 0.29.0; as recusas de
nome parcial de conta e de coluna `valor`, a partir da 0.30.1. Em CLI anterior a
0.29.0, a baixa ajustada e `financial settle`, uma parcela por vez, sem troca de
conta — e o movimento de uma parcela agendada em outra conta nao vira candidato
deste extrato.

---

## 8. Duplicatas de OFX (caso recorrente)

Duas ou mais entradas do extrato com **mesmo valor+data** (as vezes memos
parecidos, ou vindas de **importacoes de OFX diferentes**) disputando **1** unico
movimento interno = **colisao**. So uma pode conciliar.

- **Detecte e avise**: "ha 2 entradas identicas de R$ X em DD/MM apontando para o
  mesmo lancamento — provavel duplicata na importacao".
- **Concilie uma** (a que casa com o OFX corrente / memo verdadeiro) e **ignore a
  outra** (uso legitimo de `ignore`), ou investigue a origem da duplicata.
- **Nunca auto-confirme** em colisao: apresente e deixe o humano escolher qual.
- Cheque o **FITID** no OFX para confirmar se e a mesma transacao repetida.

---

## 9. Banda de candidatos — traducao para o CLI

Para cada entrada do extrato:
- **Valor:** `[|v| * (1 - 0.10), |v| * (1 + 0.10)]` — ±10% (ajustavel).
- **Data:** `[data - diasAtras, data + diasFrente]` — comece **±0**, alargue ate ±15.
- **Fluxo:** OUTFLOW se `v < 0`, senao INFLOW. **Conta:** a mesma da entrada.

```text
candidates --account bankAccount::<id> --start-date <d-> --end-date <d+> \
  --min-amount <min> --max-amount <max> --flow <INFLOW|OUTFLOW>
```

**Split** (varios movimentos → 1 entrada) e **agrupamento** (varias entradas → 1
conjunto): em ambos, **valide soma == total** antes do `confirm`.

---

## 10. Casos especiais (usar transferencia, nao receita/despesa)

Quando a contrapartida e uma conta do proprio cliente, o certo e transferencia:

- **Pagamento de fatura de cartao:** NAO lance como despesa. Faca uma
  **transferencia** (`aegro bank-transfers create`) para a conta que simula o
  cartao e **baixe as despesas da fatura**. Concilie a saida com a transferencia.
- **Aplicacao / resgate em conta investimento:** use **transferencias** corrente
  <-> investimento; concilie contra elas.
- Regra geral: contrapartida em conta do proprio cliente → **transferencia**.

### A moeda da transferencia: `BRL`, exatamente assim

**Nao passe `--currency` com nada alem de `BRL` maiusculo.** O servidor nao
valida esse campo e nao recusa o que nao entende — ele grava e responde
sucesso. Criando transferencia de 77,77 e lendo o registro de volta:

| Moeda enviada | O que ficou gravado |
|---|---|
| `BRL` | `{BRL, 77.77}` — certo |
| `USD`, `EUR` | `{BRL, 77.77}` — moeda trocada em silencio |
| `brl`, `XYZ` | **`{BRL, 0}` — valor zerado**, com resposta de sucesso |

Ou seja: um erro de caixa (`brl` em vez de `BRL`) grava uma transferencia de
**R$ 0,00** dizendo que deu certo, e o buraco so aparece quando o saldo nao
fecha no fim do periodo — que e exatamente o que esta conciliacao existe para
evitar.

Desde a 0.27.0 o CLI recusa localmente qualquer valor fora de `BRL`, antes de
enviar. Em versao anterior a recusa nao existe: ali a unica protecao e nao
escrever `--currency` (o default e `BRL`) e **reler a transferencia depois de
criar**, conferindo o valor.

O mesmo vale na leitura: no `bank-movements list`, moeda diferente de `BRL`
exato faz o servidor **descartar a faixa `--min-amount`/`--max-amount`** e
devolver tudo. Quem filtrou le a base inteira achando que e o recorte pedido.

---

## 11. Extrato so em PDF (baixa assistida — menor fidelidade)

Sem OFX nao ha movimentacoes externas, entao **nao ha conciliacao registrada**.
1. Extraia as transacoes do PDF (data, valor, descricao).
2. Case contra parcelas com as mesmas bandas (§9), via `aegro financial
   installments` (skill `aegro-financeiro`).
3. Revise cada match com o usuario (item-a-item, abaixo). So os aprovados
   entram na baixa: `financial settle-installments` com um arquivo em que cada
   linha traz a sua `realizedDate` (as transacoes do PDF tem datas diferentes —
   nao use `--date` unico) e a conta de onde o dinheiro saiu (`bankAccount` ou
   `--bank-account`). Sem OFX nao ha `--account` para copiar: pergunte a conta.

Limitacoes (explicite): e **baixa assistida**, nao conciliacao com vinculo
formal; toda entrada de PDF e 🟡/🔴 por padrao (revise item-a-item).

---

## 12. Referencia de comandos

Conciliacao sob `aegro bank-reconciliation`; baixa sob `aegro financial`.
Leituras nao precisam de `--execute`; escritas usam `--dry-run` / `--execute`.

| Comando | Params principais | Tipo |
|---|---|---|
| `bank-reconciliation import-ofx` | `--account-id <id>` `--file <ofx>` `--execute` | escrita |
| `bank-reconciliation entries` | `--account bankAccount::<id>` `[--status PENDING]` `[--start-date --end-date]` | leitura |
| `bank-reconciliation candidates` | `--account <key>` `--start-date --end-date` `--min-amount --max-amount` `[--flow]` | leitura |
| `bank-reconciliation confirm` | `--account <key>` `--external <key>...` `--movement <key>...` `--execute` | escrita |
| `bank-reconciliation ignore` | `--account <key>` `--external <key>...` `--execute` | escrita |
| `bank-reconciliation undo` | `--account <key>` `--key <reconKey>` `--dry-run`/`--execute` | escrita |
| `bank-reconciliation history` | `--account <key>` `[--start-date --end-date --status]` | leitura |
| `bank-reconciliation accounts` | `--farm-id <idLegado>` (devolve `id` cru → prefixe `bankAccount::`) | leitura |
| `bank-accounts list` | (contexto) — traz a **key** `bankAccount::...` | leitura |
| `bank-transfers create` | `--source-key --target-key --amount --entry-date` `[--description --tag]` `--execute` | escrita |
| `bank-transfers list` | `[--start-date --end-date --source-key --target-key -s]` | leitura |
| `bank-movements list` | `[--bank-account-key --start-date --end-date]` `[--min-amount --max-amount]` | leitura |
| `financial settle-installments` | `--key <inst>...` ou `--map <csv\|json>` `--date` `--bank-account` (na conciliacao, obrigatorio: a conta do extrato) `[--discount\|--interest]` (so 1 parcela) `--dry-run`/`--execute` | escrita |
| `financial settle` | `--key installment::<id>` `--date` `--realized-amount` `--execute` (valor pago livre, 1 parcela) | escrita |
| `financial realize` | `--key <inst>...` `--execute` (baixa simples, sem ajuste) | escrita |
| `bank-reconciliation clear-pending` | `--account-id <id>` `--execute` (destrutivo) | escrita |

---

## 13. Anti-padroes

- NAO confirmar sem conferir a **previa** (`--dry-run`) e a **soma** (deve fechar).
- NAO conciliar so por coincidencia de valor+data se o **fornecedor divergir**.
- NAO baixar/realizar parcela em silencio — avise que sao duas acoes.
- NAO baixar uma a uma o que saiu num pagamento so: um `settle-installments` com o lote. A excecao e a parcela paga parcialmente, que vai por `settle --realized-amount`; nunca force um desconto falso para ela caber no lote.
- NAO auto-confirmar 🟡/🟠, PDF ou **colisoes** (duplicatas): sempre item-a-item.
- NAO usar `ignore` como atalho: descasa o saldo. Uso legitimo = duplicata de OFX / entrada que nao reflete no Aegro.
- NAO alterar a despesa (`value`) para "fechar a conta": use **desconto/juros** na baixa (`settle-installments`).
- NAO lancar fatura de cartao como despesa, nem resgate como receita — use **transferencia**.
- NAO mandar `--currency` com outra coisa alem de `BRL` maiusculo: o servidor aceita calado e pode gravar **valor zero** (ver §10).
- NAO terminar um turno sem um **placar** e um **proximo passo** sugerido.

---

## Skills relacionadas

- `aegro-financeiro` — lancamentos, parcelas, contas, baixar/realizar, transferencias.
- `aegro-lancamento-financeiro` — decidir como registrar contas a pagar/receber.
- Conciliacao de **saldo por periodo** (macro, multi-conta/mensal): ao fechar o mes, confira o saldo final de cada conta no Aegro contra o extrato.
