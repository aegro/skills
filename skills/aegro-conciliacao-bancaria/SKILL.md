---
name: aegro-conciliacao-bancaria
description: Conciliacao bancaria no Aegro - importa OFX, casa entradas do extrato com o financeiro e confirma, fechando o saldo Aegro x banco
version: 0.1.0
---

# Aegro Conciliacao Bancaria

Skill para conciliar o extrato bancario com o financeiro do Aegro pela CLI. O
objetivo real da conciliacao e de **saldo**: no fechamento do periodo, o saldo de
cada conta bancaria no Aegro deve bater com o saldo do extrato do banco. Casar
lancamento a lancamento e o meio; fechar o saldo e o fim.

> **Requer login OAuth.** A conciliacao usa APIs internas do Aegro. Rode
> `aegro auth login` e selecione a fazenda (`aegro farms select`). Em modo API
> key os comandos falham com exit 2.
>
> **Fluxo critico (dados financeiros).** O agente **propoe**, o humano **confirma**.
> Nunca concilie em silencio. Toda escrita suporta `--dry-run` (previa) e so
> executa com `--execute`.

---

## 1. Vocabulario

| Termo | CLI | Descricao |
|---|---|---|
| Entrada do extrato | `entries` | Movimentacao importada do OFX (a conciliar). Status PENDING/CONFIRMED/IGNORED. |
| Movimento interno | `candidates` | Lancamento ja refletido na conta (carrega a parcela/installment). E o que se casa com a entrada. |
| Conciliar | `confirm` | Vincula entrada(s) do extrato a movimento(s) interno(s). |
| Ignorar | `ignore` | Marca entrada como IGNORADA. **Ultimo recurso** (ver Regras). |
| Desfazer | `undo` | Reverte uma conciliacao ja registrada. |
| Realizar/baixar | `financial realize` | Marca parcela como paga (skill `aegro-financeiro`). Cria o movimento interno. |
| Banda | (filtros) | Janela de valor (±%) e data (±dias) para achar candidatos de uma entrada. |

---

## 2. Fluxo

```
1. Selecionar conta        -> aegro farms select / (contexto)
2. Importar OFX            -> bank-reconciliation import-ofx --execute
3. Listar entradas PENDING -> bank-reconciliation entries
4. Por entrada: candidatos -> bank-reconciliation candidates (banda ±%/±dias)
5. Casar e confirmar       -> bank-reconciliation confirm --execute
6. Fechar: conferir saldo  -> (ver skill de conciliacao macro / saldo do periodo)
```

---

## 3. Regras de negocio (guardrails — alerta, nao bloqueio)

1. **Confirmar exige soma exata.** A soma dos valores dos movimentos internos
   selecionados deve ser **exatamente igual** ao total das entradas do extrato
   selecionadas. Valide isso ANTES de `confirm` (o servidor rejeita se diferir).
2. **Marcar como paga != conciliar (dois atos).** Candidatos so existem para
   parcelas **ja baixadas**. Se a parcela certa esta **NAO PAGA**, e preciso
   antes **realiza-la** (baixa) na data do extrato — o que cria o movimento — e
   so entao conciliar. Avise o usuario que sao **duas** acoes e confirme ambas.
   Nunca baixe uma parcela em silencio.
3. **Evitar `ignore`.** Ignorar uma movimentacao **descasa o saldo** Aegro x
   banco. Sempre alerte ("ignorar vai deixar o saldo do mes divergente do
   banco") e ofereca a alternativa correta antes. Use `ignore` so quando a
   movimentacao realmente NAO deve refletir no Aegro.
4. **Nem toda entrada/saida e receita/despesa.** Quando a contrapartida e outra
   conta do proprio cliente, o correto e **transferencia** (ver §6), nao
   lancamento de receita/despesa.

---

## 4. Referencia de comandos

Todos sob `aegro bank-reconciliation`. Leituras nao precisam de `--execute`;
escritas usam `--dry-run` / `--execute`.

| Comando | Params principais | Tipo |
|---|---|---|
| `import-ofx` | `--account-id <id>` `--file <ofx>` `--execute` | escrita |
| `entries` | `--account <key>` `[--status PENDING]` `[--start-date --end-date]` | leitura |
| `candidates` | `--account <key>` `--start-date --end-date` `--min-amount --max-amount` `[--flow INFLOW\|OUTFLOW]` | leitura |
| `confirm` | `--account <key>` `--external <key>...` `--movement <key>...` `--execute` | escrita |
| `ignore` | `--account <key>` `--external <key>...` `--execute` | escrita |
| `undo` | `--account <key>` `--key <reconKey>` `--execute` | escrita |
| `history` | `--account <key>` `[--start-date --end-date --status]` | leitura |
| `accounts` | `--farm-id <id>` | leitura |
| `clear-pending` | `--account-id <id>` `--execute` (destrutivo) | escrita |

> `--account` usa a `key` da conta; `--account-id`/`--farm-id` usam o id legado
> (obtidos em `accounts`). Prefira `--dry-run` antes de qualquer `--execute`.

---

## 5. Algoritmo de matching (o coracao da skill)

Espelha o comportamento do client-web. Defaults **tunaveis**.

### 5.1 Banda de candidatos (por entrada)
Para cada entrada do extrato:
- **Valor:** `[|v| * (1 - 0.10), |v| * (1 + 0.10)]` — banda **±10%**.
- **Data:** `[data - diasAtras, data + diasFrente]` — default **±0 dias**
  (so a data exata), ajustavel ate **±15 dias** cada lado.
- **Fluxo:** OUTFLOW se `v < 0`, senao INFLOW.
- **Conta:** a mesma da entrada.

Traduza a banda em: `candidates --account <key> --start-date <d-> --end-date <d+>
--min-amount <min> --max-amount <max> --flow <INFLOW|OUTFLOW>`.

### 5.2 Niveis de confianca
- **Automatico (verde):** existe **exatamente 1** candidato com valor **exato**
  + data **exata** + fluxo compativel + nao vinculado. Entra num **lote de
  aprovacao** (nunca confirma sozinho).
- **Sugerido (amarelo):** dentro da banda mas nao exato, ou multiplos candidatos.
  Apresente ranqueado; o humano escolhe.
- **Sem correspondencia (vermelho):** nada na banda. Criar lancamento/
  transferencia (ver §6) ou, em ultimo caso, `ignore`.

### 5.3 Postura de confirmacao (hibrida)
- **Lote unico** para os verdes (match exato).
- **Item-a-item** para amarelos e para qualquer coisa vinda de PDF (§7).
- Apresente sempre em **linguagem natural** (data / valor / fornecedor /
  parcela), nunca chaves cruas. Ex.: *"Saida de R$ 1.234,56 em 12/03 (memo
  'FORNECEDOR X') -> parcela #2 de 'Compra de insumos', vence 10/03,
  R$ 1.234,56. Diferenca R$ 0,00. Confirmar?"*

### 5.4 Split e agrupamento
- **Split:** varios movimentos internos para 1 entrada (a soma deve fechar).
- **Agrupamento:** varias entradas para 1 conjunto de movimentos.
- Em ambos, **valide soma == total** antes do `confirm`.

---

## 6. Casos especiais (usar transferencia, nao receita/despesa)

Quando a contrapartida e uma conta do proprio cliente, o certo e transferencia:

- **Pagamento de fatura de cartao de credito:** NAO lance como despesa. Faca uma
  **transferencia** (`aegro bank-transfers create`) para a conta que simula o
  cartao e **de baixa em todas as despesas vinculadas aquela fatura**. A saida do
  extrato = a transferencia; concilie a saida com o movimento da transferencia.
- **Aplicacao / resgate em conta investimento:** NAO lance resgate como receita
  (nem aplicacao como despesa). Use **transferencias** conta corrente <->
  investimento e concilie contra elas.
- Regra geral: contrapartida em conta do proprio cliente -> **transferencia**.

Esses padroes sao **orientados pelo agente** (alerta + recomendacao); a criacao
usa os comandos comuns (`bank-transfers`, `financial`), depois concilia pelo
`confirm` normal.

---

## 7. Extrato so em PDF (baixa assistida — menor fidelidade)

Sem OFX nao ha importacao de movimentacoes externas, entao **nao ha registro
formal de conciliacao bancaria**. Fluxo:
1. Extraia as transacoes do PDF (data, valor, descricao).
2. Case contra as parcelas com as **mesmas bandas** (§5.1), usando
   `aegro financial installments` (skill `aegro-financeiro`) para achar candidatas.
3. Em cada match confirmado, **realize a parcela** na data do extrato:
   `aegro financial realize ...`.

Limitacoes (deixe explicito ao usuario):
- E **baixa assistida**, nao conciliacao bancaria registrada — o saldo do Aegro
  reflete a baixa, mas nao ha o vinculo formal extrato<->movimento.
- Toda entrada de PDF e **amarela/vermelha** por padrao: revise **item-a-item**;
  extracao de PDF tem menor precisao.

---

## 8. Exemplos

```bash
# 1) Importar o extrato (previa e depois execucao)
aegro bank-reconciliation import-ofx --account-id 5f1a --file ./extrato.ofx --dry-run
aegro bank-reconciliation import-ofx --account-id 5f1a --file ./extrato.ofx --execute

# 2) Entradas pendentes
aegro bank-reconciliation entries --account bankAccount::abc --status PENDING

# 3) Candidatos de uma entrada de -R$ 1.234,56 em 2026-03-12 (banda ±10%, ±0 dia)
aegro bank-reconciliation candidates --account bankAccount::abc \
  --start-date 2026-03-12 --end-date 2026-03-12 \
  --min-amount 1111.10 --max-amount 1358.02 --flow OUTFLOW

# 4) Conferir a previa e conciliar (soma deve fechar)
aegro bank-reconciliation confirm --account bankAccount::abc \
  --external ext::1 --movement mov::9 --dry-run
aegro bank-reconciliation confirm --account bankAccount::abc \
  --external ext::1 --movement mov::9 --execute

# 5) Desfazer, se preciso
aegro bank-reconciliation undo --account bankAccount::abc --key recon::7 --execute
```

---

## 9. Anti-padroes

- NAO confirmar sem conferir a **previa** (`--dry-run`) e a **soma** (deve fechar).
- NAO baixar/realizar uma parcela em silencio ao conciliar — avise que sao duas acoes.
- NAO usar `ignore` como atalho: descasa o saldo Aegro x banco. So em ultimo caso.
- NAO lancar pagamento de fatura de cartao como despesa, nem resgate como receita
  — use **transferencia**.
- NAO auto-confirmar amarelos (nao-exatos) nem entradas de PDF: sempre item-a-item.
- NAO prometer "conciliado" no fluxo de PDF — e baixa assistida, sem registro formal.

---

## Skills relacionadas

- `aegro-financeiro` — lancamentos, parcelas, contas bancarias, realizar/baixar, transferencias.
- `aegro-lancamento-financeiro` — decidir como registrar contas a pagar/receber.
- Conciliacao de **saldo por periodo** (macro, multi-conta/mensal) — ver ENTRADA-54.
