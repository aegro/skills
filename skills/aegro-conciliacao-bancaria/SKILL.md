---
name: aegro-conciliacao-bancaria
description: Conciliacao bancaria no Aegro - importa OFX, casa entradas do extrato com o financeiro e confirma, fechando o saldo Aegro x banco
version: 0.3.2
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
| Baixar simples | `financial realize` | Baixa a parcela pelo valor/data **agendados** (API publica). Sem desconto/juros/data. |
| Baixar ajustado | `financial settle` | Baixa UMA parcela com **data + desconto/juros** ajustados, sem alterar a despesa (§7). E o caminho quando o extrato difere do agendado. |
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
6. Ajustar se preciso      -> financial settle (desconto/juros/data) quando o valor difere (§7)
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
| 🟢 Verde-data | **valor exato** / ±3 dias | lote, `confirm` direto se o movimento ja existe (so a data liquidou fora); parcela NAO PAGA → `realize`/`settle` antes (§6) |
| 🟡 Amarelo | ±10% valor / ±3–7 dias | item-a-item; diferenca costuma ser **desconto/juros** → `settle` antes de conciliar |
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
   desconto/juros: use `settle` (§7).
2. **Baixar != conciliar (dois atos).** Se a parcela certa esta **NAO PAGA**,
   primeiro **baixe** na data do extrato (cria o movimento), depois **concilie**.
   Avise que sao duas acoes e confirme ambas. Nunca baixe em silencio.
3. **Fornecedor deve fazer sentido.** Valor+data batendo mas fornecedor/memo
   divergente = provavel falso-positivo. Nao concilie so por coincidencia
   numerica.
4. **Evitar `ignore`.** Ignorar **descasa o saldo** Aegro x banco. Sempre alerte
   e ofereca a alternativa antes. Uso legitimo: entrada que realmente NAO deve
   refletir no Aegro (ex.: **duplicata de OFX**, §8).
5. **Nem toda entrada/saida e receita/despesa.** Contrapartida em conta do
   proprio cliente → **transferencia** (§10), nao receita/despesa.

---

## 7. Baixa ajustada — desconto / juros / data (`financial settle`)

Quando a parcela esta **NAO PAGA** e o extrato difere do agendado, baixe com
ajuste **sem alterar a despesa** (o `value` do lancamento e preservado; a
diferenca entra como desconto ou juros na baixa):

- **Banco < agendado** → **desconto** (`--discount`).
- **Banco > agendado** → **juros** (`--interest`).
- Baixe na **data do extrato** (`--date`).

```bash
# parcela agendada R$ 2.359,24; banco pagou R$ 2.243,88 em 18/06 (desconto R$ 115,36)
aegro financial settle --farm "<fazenda>" --key installment::<id> --date 2026-06-18 --discount 115.36 --dry-run
aegro financial settle --farm "<fazenda>" --key installment::<id> --date 2026-06-18 --discount 115.36 --execute
# depois concilie a entrada do extrato com o movimento gerado:
# previa primeiro (confira o par extrato<->movimento e a soma), e so apos o
# usuario aprovar rode o MESMO comando com --execute
aegro bank-reconciliation confirm --farm "<fazenda>" --account bankAccount::<id> \
  --external <ext> --movement <mov> --dry-run
aegro bank-reconciliation confirm --farm "<fazenda>" --account bankAccount::<id> \
  --external <ext> --movement <mov> --execute
```

`settle` faz round-trip na API interna (le a parcela, ajusta baixa, regrava) e
**nao mexe** em fornecedor, categoria nem valor da despesa. Confirme o preview
(`--dry-run` mostra valor realizado, desconto/juros e data) antes do `--execute`.

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

---

## 11. Extrato so em PDF (baixa assistida — menor fidelidade)

Sem OFX nao ha movimentacoes externas, entao **nao ha conciliacao registrada**.
1. Extraia as transacoes do PDF (data, valor, descricao).
2. Case contra parcelas com as mesmas bandas (§9), via `aegro financial
   installments` (skill `aegro-financeiro`).
3. Em cada match, **baixe a parcela** na data do extrato (`financial realize` ou
   `settle` se houver ajuste).

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
| `bank-reconciliation undo` | `--account <key>` `--key <reconKey>` `--execute` | escrita |
| `bank-reconciliation history` | `--account <key>` `[--start-date --end-date --status]` | leitura |
| `bank-reconciliation accounts` | `--farm-id <idLegado>` (devolve `id` cru → prefixe `bankAccount::`) | leitura |
| `bank-accounts list` | (contexto) — traz a **key** `bankAccount::...` | leitura |
| `financial settle` | `--key installment::<id>` `--date` `[--discount\|--interest\|--realized-amount]` `--execute` | escrita |
| `financial realize` | `--key <inst>...` `--execute` (baixa simples, sem ajuste) | escrita |
| `bank-reconciliation clear-pending` | `--account-id <id>` `--execute` (destrutivo) | escrita |

---

## 13. Anti-padroes

- NAO confirmar sem conferir a **previa** (`--dry-run`) e a **soma** (deve fechar).
- NAO conciliar so por coincidencia de valor+data se o **fornecedor divergir**.
- NAO baixar/realizar parcela em silencio — avise que sao duas acoes.
- NAO auto-confirmar 🟡/🟠, PDF ou **colisoes** (duplicatas): sempre item-a-item.
- NAO usar `ignore` como atalho: descasa o saldo. Uso legitimo = duplicata de OFX / entrada que nao reflete no Aegro.
- NAO alterar a despesa (`value`) para "fechar a conta": use **desconto/juros** na baixa (`settle`).
- NAO lancar fatura de cartao como despesa, nem resgate como receita — use **transferencia**.
- NAO terminar um turno sem um **placar** e um **proximo passo** sugerido.

---

## Skills relacionadas

- `aegro-financeiro` — lancamentos, parcelas, contas, baixar/realizar, transferencias.
- `aegro-lancamento-financeiro` — decidir como registrar contas a pagar/receber.
- Conciliacao de **saldo por periodo** (macro, multi-conta/mensal): ao fechar o mes, confira o saldo final de cada conta no Aegro contra o extrato.
