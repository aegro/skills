---
name: aegro-financeiro
description: Dominio financeiro do Aegro - lancamentos, parcelas, categorias, contas bancarias e empresas
version: 0.6.0
---

# Aegro Financeiro

Skill especializada no dominio financeiro da plataforma Aegro. Cobre lancamentos (bills),
parcelas (installments), categorias financeiras, contas bancarias, empresas e ordens de compra.

---

## 1. Vocabulario

| Termo Aegro             | Termo CLI              | Descricao                                                                                  |
|--------------------------|------------------------|--------------------------------------------------------------------------------------------|
| Lancamento financeiro    | `bill`                 | Registro contabil pai. Agrupa uma ou mais parcelas.                                        |
| Parcela                  | `installment`          | Fracao de pagamento de um lancamento. Possui valor, vencimento e status.                   |
| Categoria financeira     | `fin-categories`       | Classificacao contabil. Pode ser SYNTHETIC (agrupadora) ou ANALYTIC (recebe lancamentos).  |
| Tipo de operacao (bill)  | `--operation-type`     | REVENUE (receita) ou EXPENSE (despesa). Usado no filtro de installments.                   |
| Tipo de operacao (cat)   | `--operation-type`     | CREDITOR (credora) ou DEBTOR (devedora). Usado em categorias financeiras.                  |
| Status da parcela        | `--status`             | PAID (paga) ou NOT_PAID (pendente).                                                       |
| Conta bancaria           | `bank-accounts`        | Conta onde parcelas sao vinculadas. Possui saldo e saldo inicial.                          |
| Empresa                  | `companies`            | Fornecedor, cliente ou transportadora vinculado a fazenda.                                 |
| Ordem de compra          | `purchase-orders`      | Pedido de compra vinculado a uma empresa, com itens e valores.                             |
| Realizar                 | `realize`              | Ato de marcar parcelas como pagas em lote.                                                 |
| Tipo de categoria        | `--type`               | SYNTHETIC (nao recebe lancamentos, agrupa) ou ANALYTIC (recebe lancamentos diretamente).   |
| Tipo de conta (bill)     | `--bill-type`          | PAYABLE (a pagar) ou RECEIVABLE (a receber).                                               |
| Status da categoria      | `--status`             | ACTIVE ou INACTIVE.                                                                       |
| Documento fiscal         | `fiscalNumber`         | Objeto aninhado com `code`, `fiscalNumberType` (CPF/CNPJ) e `countryCode`.                |

---

## 2. Modelo de Dados

```
FARM
 +-- FINANCIAL_CATEGORY (hierarquia: SYNTHETIC pai -> ANALYTIC filhas)
 |     parentCode vincula filha a mae
 +-- BILL (lancamento financeiro)
 |     +-- INSTALLMENT (1:N parcelas)
 |           bankAccountKey -> BANK_ACCOUNT
 +-- BANK_ACCOUNT (conta bancaria)
 +-- COMPANY (fornecedor/cliente/transportadora)
 +-- PURCHASE_ORDER
 |     companyKey -> COMPANY
 |     items[] -> lista de produtos com quantidade e valor
 +-- ELEMENT
       set-categories vincula ELEMENT a FINANCIAL_CATEGORY (ponte entre dominios estoque e financeiro)
```

Relacionamentos-chave:
- Uma BILL pode ter N INSTALLMENTs (parcelas).
- Cada INSTALLMENT aponta para exatamente uma BANK_ACCOUNT.
- FINANCIAL_CATEGORY forma arvore: SYNTHETIC agrupa, ANALYTIC recebe lancamentos.
- `elements set-categories` conecta insumos (dominio estoque) a categorias financeiras.

---

## 3. Regras de Negocio

1. **SYNTHETIC vs ANALYTIC**: Categorias SYNTHETIC servem apenas para agrupar. Somente categorias ANALYTIC podem receber lancamentos financeiros. Nao tente associar lancamentos a categorias SYNTHETIC.

2. **create-installment requer bill_key existente**: Antes de criar uma parcela, o lancamento (bill) ja deve existir. Valide com `aegro financial bill <key>`.

3. **Formato de valor -- PARCELA vs CONTA BANCARIA**:
   - Parcela (installment): `{"amount": X, "currency": "BRL"}`
   - Conta bancaria (bank-account): `{"currencyCode": "BRL", "amount": X}`
   - SAO FORMATOS DIFERENTES. Trocar gera erro 400.

4. **update-installment e PUT total**: O endpoint de atualizacao e PUT (nao PATCH). Todos os campos obrigatorios devem ser enviados: `key`, `billKey`, `bankAccountKey`, `number`, `dueDate`, `amount`. Omitir qualquer um causa erro.

5. **realize e operacao em lote**: O comando `realize` recebe multiplas chaves de parcela e marca todas como PAID de uma vez. Body: `{"list": ["key1", "key2"]}`.

6. **Parcela PAID nao pode ser excluida**: Tentar `delete-installment` em parcela com status PAID retorna HTTP 405 (Method Not Allowed). Primeiro altere o status para NOT_PAID via update-installment, depois exclua.

7. **Tipos de empresa sao repetiveis**: Uma empresa pode ser simultaneamente PROVIDER, CLIENT e TRANSPORTER. Use `--type PROVIDER --type CLIENT`.

8. **fiscalNumber e objeto aninhado**: No body da API, o documento fiscal e estruturado como:
   ```json
   {"fiscalNumber": {"code": "12345678000199", "fiscalNumberType": "CNPJ", "countryCode": "BR"}}
   ```

9. **fin-categories create exige 6 campos obrigatorios**: `--description`, `--type`, `--operation-type`, `--status`, `--bill-type`, `--code`. Todos sao required. Omitir qualquer um gera erro.

10. **Paginacao padrao**: Todos os endpoints de listagem usam `requiredPageNumber` e `maximumItemsPerPageCount: 50`. Use `--page` para navegar.

---

## 4. Referencia de Comandos

### 4.1 financial (lancamentos e parcelas)

| Comando               | Tipo     | Parametros obrigatorios                                    | Parametros opcionais                                                                 |
|------------------------|----------|------------------------------------------------------------|--------------------------------------------------------------------------------------|
| `bill <key>`           | GET      | `bill_key` (argumento)                                     | `--output`                                                                           |
| `installment <key>`    | GET      | `installment_key` (argumento)                              | `--output`                                                                           |
| `installments`         | POST     | (nenhum)                                                   | `--operation-type`, `--status` (repetivel), `--due-date-start`, `--due-date-end`, `--bill-key` (repetivel), `--page` |
| `create-installment`   | POST     | `--bill-key`, `--bank-account-key`, `--due-date`, `--amount` | `--currency` (default BRL)                                                          |
| `update-installment`   | PUT      | `<key>` (arg), `--bill-key`, `--bank-account-key`, `--number`, `--due-date`, `--amount` | `--currency`, `--status`, `--realized-date`, `--realized-amount`, `--realized-currency` |
| `delete-installment`   | DELETE   | `<key>` (argumento)                                        | (nenhum)                                                                             |
| `realize`              | POST     | `--key` (repetivel, obrigatorio)                           | (nenhum)                                                                             |
| `create-bill`          | POST     | inteligente (ver 4.1.1)                                    | `--description`, `--total-amount`, `--cash-flow`, `--payment-method`, `--category`/`--financial-category-key`, `--company`/`--company-key`, `--bank-account`/`--bank-account-key`, `--farm-key`, `--entry-date`, `--currency`, `--env`, `--complete`, `--dry-run` |
| `create-bills`         | POST     | `--batch <arquivo.json>`                                   | `--env`, `--complete`, `--dry-run`, `--execute`                                     |

**Exemplos reais:**

```bash
# Listar despesas pendentes no mes de marco/2026
aegro financial installments --operation-type EXPENSE --status NOT_PAID \
  --due-date-start 2026-03-01 --due-date-end 2026-04-01

# Criar parcela de R$ 1.500 para lancamento existente
aegro financial create-installment --bill-key bill::abc123 \
  --bank-account-key bankAccount::def456 --due-date 2026-04-15 --amount 1500.00

# Atualizar parcela (PUT total - todos os campos obrigatorios)
aegro financial update-installment installment::ghi789 \
  --bill-key bill::abc123 --bank-account-key bankAccount::def456 \
  --number 1 --due-date 2026-04-15 --amount 2000.00 \
  --status PAID --realized-date 2026-04-10

# Realizar (pagar) multiplas parcelas em lote
aegro financial realize --key installment::aaa --key installment::bbb

# Excluir parcela pendente
aegro financial delete-installment installment::ghi789
```

### 4.1.1 Insercao inteligente de contas (create-bill / create-bills)

`create-bill` resolve **nomes em chaves**, infere contexto e diz o que falta de
forma estruturada -- em vez de exigir que voce conheca `company::`,
`financialCategory::` e `farmKey`. Use nomes; deixe o CLI resolver.

O que o comando faz por voce:
- **Resolve por nome**: `--company "Fornecedor X"`, `--category "Insumos"`,
  `--bank-account "Conta BB"` viram chaves. As variantes exatas
  (`--company-key`, `--financial-category-key`, `--bank-account-key`) seguem
  validas para scripts.
- **Infere contexto**: `--farm-key` vem da credencial (omita); `--entry-date`
  vira hoje em America/Sao_Paulo se omitida.
- **Pergunta so o que falta**: sem TTY, campos faltantes/ambiguos saem como um
  envelope `needs_input` (status, resolved, inferred, missing, ambiguous, preview)
  e **nada e executado**. Resolva os pontos e reinvoque. Use `--complete` para
  forcar esse modo (resolve+infere+reporta, sem executar).
- **Preview com nomes**: `--dry-run` mostra o payload resolvido com nomes (nao
  chaves) para conferencia antes de executar.

Campos do lancamento: `--cash-flow` e `REVENUE|EXPENSE`; `--payment-method` e
`PROMPT|INSTALLMENT|NO_PAYMENT|UNKNOWN`; `--category` deve ser uma categoria
ANALYTIC (ver regra 1). Parcelamento detalhado vai em `--installments` (JSON).

```bash
# Conta a pagar resolvendo nomes; fazenda e data inferidas
aegro financial create-bill --description "Adubo NPK" --total-amount 1500 \
  --cash-flow EXPENSE --payment-method PROMPT \
  --category "Insumos" --company "Fornecedor X"

# Modo headless: so resolve/infere e diz o que falta (nao executa)
aegro financial create-bill --description "Adubo" --total-amount 1500 \
  --cash-flow EXPENSE --payment-method PROMPT --complete
```

**Lancamento em massa (`create-bills`)** -- a tabela de conferencia. Recebe um
arquivo JSON com uma lista de lancamentos *name-based* (mesmos campos) e devolve
uma tabela por linha com `status` (ok/needs_input) e nomes resolvidos:

```bash
# Tabela de conferencia (nao executa)
aegro financial create-bills --batch contas.json --env staging --complete

# Lancar em staging; depois conferir na UI e promover trocando --env
aegro financial create-bills --batch contas.json --env staging
aegro financial create-bills --batch contas.json --env prod
```

Exemplo de `contas.json`:

```json
[
  {"description": "Adubo NPK", "totalAmount": 1500, "cashFlow": "EXPENSE",
   "paymentMethod": "PROMPT", "category": "Insumos", "company": "Fornecedor X"},
  {"description": "Venda soja", "totalAmount": 90000, "cashFlow": "REVENUE",
   "paymentMethod": "INSTALLMENT", "category": "Venda de Graos", "company": "Cerealista Y"}
]
```

### 4.2 fin-categories (categorias financeiras)

| Comando                  | Tipo     | Parametros obrigatorios                                                              | Parametros opcionais                                      |
|---------------------------|----------|--------------------------------------------------------------------------------------|-----------------------------------------------------------|
| `get <key>`               | GET      | `key` (argumento)                                                                    | `--output`                                                |
| `list`                    | POST     | (nenhum)                                                                             | `--type` (repetivel), `--operation-type` (repetivel), `--status` (repetivel), `--search-text`, `--page` |
| `create`                  | POST     | `--description`, `--type`, `--operation-type`, `--status`, `--bill-type`, `--code`   | `--observations`, `--parent-code`                         |
| `subcategories <key>`     | POST     | `key` (argumento)                                                                    | `--element-category` (repetivel), `--page`                |

**Exemplos reais:**

```bash
# Listar categorias analiticas de despesa ativas
aegro fin-categories list --type ANALYTIC --operation-type DEBTOR --status ACTIVE

# Criar categoria pai (sintetica)
aegro fin-categories create --description "Custos Operacionais" --type SYNTHETIC \
  --operation-type DEBTOR --status ACTIVE --bill-type PAYABLE --code "2"

# Criar subcategoria (analitica, vinculada ao pai pelo parent-code)
aegro fin-categories create --description "Defensivos Agricolas" --type ANALYTIC \
  --operation-type DEBTOR --status ACTIVE --bill-type PAYABLE --code "2.1" --parent-code "2"

# Listar subcategorias de uma categoria pai
aegro fin-categories subcategories financialCategory::xyz
```

### 4.3 bank-accounts (contas bancarias)

| Comando           | Tipo     | Parametros obrigatorios | Parametros opcionais                                                                                                   |
|--------------------|----------|--------------------------|------------------------------------------------------------------------------------------------------------------------|
| `get <key>`        | GET      | `key` (argumento)        | `--output`                                                                                                             |
| `list`             | POST     | (nenhum)                 | `--search-text`, `--bank-name`, `--page`                                                                               |
| `create`           | POST     | `--name`                 | `--balance`, `--balance-currency`, `--initial-balance`, `--initial-balance-currency`, `--initial-balance-date`, `--is-default`, `--code`, `--bank`, `--bank-code`, `--bank-name`, `--branch-code` |

**Exemplos reais:**

```bash
# Listar contas bancarias
aegro bank-accounts list
aegro bank-accounts list --search-text "Itau" --bank-name "Itau"

# Criar conta bancaria com saldo inicial
aegro bank-accounts create --name "Conta Itau" \
  --balance 10000 --balance-currency BRL \
  --initial-balance 10000 --initial-balance-currency BRL \
  --initial-balance-date 2025-01-01

# Criar conta padrao
aegro bank-accounts create --name "Conta Principal BB" --is-default \
  --bank-name "Banco do Brasil" --bank-code "001" --branch-code "1234"
```

### 4.4 companies (empresas)

| Comando           | Tipo     | Parametros obrigatorios | Parametros opcionais                                                                              |
|--------------------|----------|--------------------------|---------------------------------------------------------------------------------------------------|
| `get <key>`        | GET      | `key` (argumento)        | `--output`                                                                                        |
| `list`             | POST     | (nenhum)                 | `--search-text`, `--fiscal-number-type`, `--page`                                                 |
| `create`           | POST     | `--name`                 | `--type` (repetivel), `--fiscal-code`, `--fiscal-type`, `--fiscal-country`, `--trade-name`, `--legal-name`, `--observations` |

**Exemplos reais:**

```bash
# Listar fornecedores com CNPJ
aegro companies list --fiscal-number-type CNPJ

# Criar fornecedor com CNPJ
aegro companies create --name "AgroSul Ltda" --type PROVIDER \
  --fiscal-code 12345678000199 --fiscal-type CNPJ

# Criar empresa que e fornecedor E cliente
aegro companies create --name "CoopAgri" --type PROVIDER --type CLIENT \
  --trade-name "Cooperativa Agricola" --legal-name "CoopAgri Ltda"
```

### 4.5 purchase-orders (ordens de compra)

| Comando           | Tipo     | Parametros obrigatorios                                    | Parametros opcionais                                                              |
|--------------------|----------|------------------------------------------------------------|-----------------------------------------------------------------------------------|
| `get <key>`        | GET      | `key` (argumento)                                          | `--output`                                                                        |
| `list`             | POST     | (nenhum)                                                   | `--company-key`, `--search-text`, `--start-date`, `--end-date`, `--delivery-status`, `--page` |
| `create`           | POST     | `--company-key`, `--order-date`, `--gross-amount`, `--items` | `--currency` (default BRL), `--expected-delivery-date`, `--description`, `--discount-amount`, `--company-order-code` |

**Exemplos reais:**

```bash
# Listar ordens de compra de um fornecedor
aegro purchase-orders list --company-key company::abc123

# Criar ordem de compra (--items e JSON string)
aegro purchase-orders create --company-key company::abc123 \
  --order-date 2026-03-15 --gross-amount 15000 \
  --items '[{"productKey":"element::xyz","quantity":500}]' \
  --description "Compra de defensivos safra 25/26" \
  --expected-delivery-date 2026-04-01
```

---

## 5. Gotchas de API

### CRITICO: Formatos de valor monetario diferentes

O Aegro usa dois formatos distintos de valor monetario dependendo do recurso:

```
Parcela (installment):    {"amount": 1500.00, "currency": "BRL"}
                          campo "currency" (sem prefixo)

Conta bancaria:           {"currencyCode": "BRL", "amount": 10000.00}
                          campo "currencyCode" (com prefixo Code)

Entrada de estoque:       {"amount": 500.00, "currencyCode": "BRL"}
                          campo "currencyCode" (com prefixo Code)

Ordem de compra body:     campo "currencyCode" no body raiz (nao aninhado)
```

Usar o formato errado resulta em erro HTTP 400.

### update-installment e PUT total

Nao e PATCH. Todos os campos obrigatorios devem ser enviados, inclusive os que nao mudaram:
`key`, `billKey`, `bankAccountKey`, `number`, `dueDate`, `amount`.

### fin-categories create exige todos os 6 campos

Campos obrigatorios: `--description`, `--type`, `--operation-type`, `--status`, `--bill-type`, `--code`.
Nao ha valores default. Omitir qualquer um retorna erro 422.

### purchase-orders --items e JSON string

O parametro `--items` recebe uma string JSON (nao e flag repetivel). Exemplo:
`--items '[{"productKey":"element::xyz","quantity":10}]'`

### Filtros usam POST (nao GET)

Todos os endpoints de listagem (`installments`, `fin-categories list`, `bank-accounts list`, `companies list`, `purchase-orders list`) usam POST com body JSON, nao GET com query params.

### Ambiente: prod vs staging (multi-env)

`--env prod|staging` (ou `AEGRO_ENV`) seleciona base URL e credenciais por
ambiente -- cada ambiente tem credenciais proprias (`aegro auth login --env staging`).
`staging` (`app.staging.aegro.io`) e homologacao, **uso interno**: lance ali,
confira, e so entao promova para `prod`. As chaves diferem entre ambientes, por
isso o batch de `create-bills` e *name-based* e re-resolvido por ambiente -- a
promocao staging->prod e rodar o mesmo arquivo trocando `--env`. Nao sugira
staging a clientes.

---

## 6. Padroes e Exemplos

### Listar despesas pendentes dos proximos 30 dias

```bash
aegro financial installments --operation-type EXPENSE --status NOT_PAID \
  --due-date-start 2026-03-13 --due-date-end 2026-04-13
```

### Buscar categorias de despesa para vincular a insumo

```bash
# 1. Listar categorias analiticas de despesa
aegro fin-categories list --type ANALYTIC --operation-type DEBTOR --status ACTIVE

# 2. Vincular categoria ao elemento (ponte estoque -> financeiro)
aegro elements set-categories element::xxx --expense-category-key financialCategory::yyy
```

### Consultar saldo consolidado de contas

```bash
# Listar todas as contas e verificar saldo
aegro bank-accounts list --output table
```

### Fluxo completo: criar fornecedor e ordem de compra

```bash
# 1. Criar empresa fornecedora
aegro companies create --name "Syngenta Brasil" --type PROVIDER \
  --fiscal-code 60744463000178 --fiscal-type CNPJ

# 2. Anotar a key retornada (company::abc123)

# 3. Criar ordem de compra vinculada
aegro purchase-orders create --company-key company::abc123 \
  --order-date 2026-03-15 --gross-amount 25000 \
  --items '[{"productKey":"element::def456","quantity":200}]' \
  --description "Defensivos safra soja 25/26"
```

### Realizar parcelas vencidas em lote

```bash
# 1. Listar parcelas vencidas
aegro financial installments --operation-type EXPENSE --status NOT_PAID \
  --due-date-start 2026-01-01 --due-date-end 2026-03-13

# 2. Realizar as parcelas desejadas
aegro financial realize --key installment::aaa --key installment::bbb --key installment::ccc
```

---

## 7. Anti-padroes

1. **Nao crie parcela sem verificar que o bill existe.** Sempre execute `aegro financial bill <key>` antes de `create-installment`. Se o bill nao existir, a API retorna 404.

2. **Nao tente excluir parcela PAID.** Retorna HTTP 405. Primeiro atualize o status para NOT_PAID com `update-installment`, depois exclua.

3. **Nao misture formatos de moeda.** Parcela usa `{"amount": X, "currency": "BRL"}`. Conta bancaria usa `{"currencyCode": "BRL", "amount": X}`. Verifique o formato correto antes de montar o body.

4. **Nao use PATCH mental no update-installment.** E PUT total. Envie TODOS os campos obrigatorios, mesmo os que nao mudaram. Busque a parcela atual com `aegro financial installment <key>` e reenviie os campos.

5. **Nao associe lancamentos a categorias SYNTHETIC.** Somente ANALYTIC recebe lancamentos. Verifique o tipo com `aegro fin-categories get <key>`.

6. **Nao esqueca --parent-code ao criar subcategoria.** Sem `--parent-code`, a categoria sera criada como raiz, quebrando a hierarquia.

7. **Verifique saldo antes de sugerir realize.** O realize nao valida saldo bancario. Confirme com o usuario que ha saldo suficiente na conta antes de marcar parcelas como pagas.

8. **Nao crie empresa duplicada.** Antes de `companies create`, busque com `companies list --search-text "nome"` ou `--fiscal-number-type CNPJ` para evitar duplicatas.
