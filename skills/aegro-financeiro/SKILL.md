---
name: aegro-financeiro
description: Dominio financeiro do Aegro - lancamentos, parcelas, categorias, contas bancarias e empresas
version: 0.7.0
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
| Item do lancamento       | `inputs`               | Insumo/produto dentro da bill. Cada item pode ter categoria financeira PROPRIA.            |
| Metodo de pagamento      | `--payment-method`     | PROMPT (a vista, parcela unica JA PAGA), INSTALLMENT (parcelado), NO_PAYMENT (sem pagamento), UNKNOWN. |
| Produtor                 | (nao exposto)          | Empresa "produtor" que organiza lancamentos no produto. NAO existe na API publica.         |

---

## 2. Modelo de Dados

```
FARM
 +-- FINANCIAL_CATEGORY (hierarquia: SYNTHETIC pai -> ANALYTIC filhas)
 |     parentCode vincula filha a mae
 +-- BILL (lancamento financeiro)
 |     +-- INSTALLMENT (0:N parcelas; PROMPT gera 1 ja paga, NO_PAYMENT gera 0)
 |     |     bankAccountKey -> BANK_ACCOUNT
 |     +-- INPUT (0:N itens/insumos da nota)
 |           elementKey -> ELEMENT
 |           financialCategory -> FINANCIAL_CATEGORY (categoria POR ITEM)
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

2. **NAO existe CRUD avulso de parcela na API publica**: os unicos endpoints
   de installments sao `filter`, `realizeList`
   e GET individual. Parcelas **nascem no create-bill** (campo `installments`) e
   sao pagas via `realize`. Para corrigir parcela/valor, use
   `financial update-bill` (PATCH) ou o app.

3. **Formato de valor monetario**: a spec atual unificou em
   `MoneyPublicResource = {"currencyCode": "BRL", "amount": X}` para bills,
   parcelas e contas bancarias. Historicamente parcela aceitava
   `{"amount": X, "currency": "BRL"}` (legado) — em caso de erro 400, use o
   formato com `currencyCode`.

4. **update-bill e PATCH (JSON Merge Patch)**: envie apenas os campos a alterar.
   Nao existe update de parcela avulsa (ver regra 2).

5. **realize e operacao em lote**: O comando `realize` recebe multiplas chaves de parcela e marca todas como PAID de uma vez. Body: `{"list": ["key1", "key2"]}`. Nao ha "unrealize" (desfazer pagamento) na API — correcao apenas pelo app.

6. **Apropriacao de custo (financialApportion)**: ha DOIS tipos no produto —
   **direta** (lancamento aponta para 1+ safras) e **salva**
   (`cropProrateGroup`, rateio pre-definido com percentuais, ex.:
   "Administrativo" 50% milho / 50% soja). Via API publica: a direta existe
   (`financialApportion: {"type": "CROP_PRORATE", "cropKeys": [...]}`; tambem
   ASSET_PRORATE/STOCK_INPUTS/STOCK_HARVEST/APPORTION_LATER). Com **multiplas
   safras**, a divisao e automatica e **proporcional a area de cada safra** —
   nao ha como definir percentuais na direta; percentuais so existem na salva.
   A salva e **somente-leitura** (`crop-prorate/filter` e GET) — nao da para
   aplica-la num lancamento nem criar grupos via API. NAO use
   `cropProrateGroupKey` na raiz do bill: e aceito e ignorado em silencio.

7. **Tipos de empresa sao repetiveis**: Uma empresa pode ser simultaneamente PROVIDER, CLIENT e TRANSPORTER. Use `--type PROVIDER --type CLIENT`.

8. **fiscalNumber e objeto aninhado**: No body da API, o documento fiscal e estruturado como:
   ```json
   {"fiscalNumber": {"code": "12345678000199", "fiscalNumberType": "CNPJ", "countryCode": "BR"}}
   ```

9. **fin-categories create exige 6 campos obrigatorios**: `--description`, `--type`, `--operation-type`, `--status`, `--bill-type`, `--code`. Todos sao required. Omitir qualquer um gera erro.

10. **Paginacao padrao**: Todos os endpoints de listagem usam `requiredPageNumber` e `maximumItemsPerPageCount: 50`. Use `--page` para navegar.

11. **Semantica do paymentMethod**:
    - `PROMPT` (a vista): se `installments` nao for enviado, a API **gera
      automaticamente 1 parcela JA REALIZADA (paga)**; se enviar 1 parcela, ela
      e marcada como paga na criacao. Como realize e irreversivel via API, **so
      use PROMPT quando o pagamento de fato ja ocorreu**.
    - `INSTALLMENT` (parcelado): **exige `installments` nao-vazio** — sem elas a
      API retorna erro de validacao. Parcelas nascem NOT_PAID. Para conta a
      vencer com parcela unica ("a vista a vencer"), use INSTALLMENT com 1
      parcela, NAO use PROMPT.
    - `NO_PAYMENT`/`UNKNOWN` (sem pagamento): nenhuma parcela e criada e a
      conta bancaria do lancamento e **descartada** — o lancamento existe para
      custo/relatorios, sem efeito no fluxo de caixa.

12. **Itens do lancamento (inputs) com categoria POR ITEM**: a bill aceita
    `inputs` (lista de insumos/produtos da nota). Cada item tem `elementKey`,
    `quantity`, `unitAmount`, `amount` e `financialCategory` **propria** (na
    escrita, so a `key` da categoria e considerada:
    `{"financialCategory": {"key": "financialCategory::..."}}`). Quando a conta
    tem itens, **categorize por item** — puxe a categoria ja cadastrada de cada
    elemento quando existir (ver 4.1.1). CRITICO: com `inputs`, o `totalAmount`
    enviado e **IGNORADO** e recalculado como a SOMA dos `amount` dos itens.

13. **Campo "Produtor" NAO existe na API publica**: no produto, bill e parcelas
    tem um produtor (empresa) que organiza os dados — as parcelas herdam o
    produtor da bill. Nenhum recurso publico expoe esse campo: lancamento criado
    via API fica **sem produtor**, e o ajuste so pode ser feito pelo app.
    Se o cliente organiza os lancamentos por produtor, avise antes de lancar
    em massa.

---

## 4. Referencia de Comandos

### 4.1 financial (lancamentos e parcelas)

| Comando               | Tipo     | Parametros obrigatorios                                    | Parametros opcionais                                                                 |
|------------------------|----------|------------------------------------------------------------|--------------------------------------------------------------------------------------|
| `bill <key>`           | GET      | `bill_key` (argumento)                                     | `--output`                                                                           |
| `bills`                | POST     | (nenhum)                                                   | `--operation-type`, `--start-date`, `--end-date`, `--company-key` (repetivel), `--crop-key` (repetivel), `--financial-category-key` (repetivel), `--bank-account-key` (repetivel), `--payment-method` (repetivel), `--receipt`, `--page` |
| `installment <key>`    | GET      | `installment_key` (argumento)                              | `--output`                                                                           |
| `installments`         | POST     | (nenhum)                                                   | `--operation-type`, `--status` (repetivel), `--due-date-start`, `--due-date-end`, `--bill-key` (repetivel), `--page` |
| `realize`              | POST     | `--key` (repetivel, obrigatorio)                           | (nenhum)                                                                             |
| `update-bill`          | PATCH    | `<key>` (arg), `--body` (JSON Merge Patch)                 | `--dry-run`, `--execute`                                                             |
| `create-bill`          | POST     | inteligente (ver 4.1.1)                                    | `--description`, `--total-amount`, `--cash-flow`, `--payment-method`, `--category`/`--financial-category-key`, `--company`/`--company-key`, `--bank-account`/`--bank-account-key`, `--installments` (JSON), `--inputs` (JSON), `--apportion-crop` (repetivel), `--farm-key`, `--entry-date`, `--currency`, `--env`, `--complete`, `--dry-run` |
| `create-bills`         | POST     | `--batch <arquivo.json>`                                   | `--env`, `--complete`, `--dry-run`, `--execute`                                     |

> NAO existem `create-installment`/`update-installment`/`delete-installment` —
> nem no CLI nem na API publica. Parcelas nascem no `create-bill` (campo
> `installments`) e sao pagas via `realize`.

**Exemplos reais:**

```bash
# Listar despesas pendentes no mes de marco/2026
aegro financial installments --operation-type EXPENSE --status NOT_PAID \
  --due-date-start 2026-03-01 --due-date-end 2026-04-01

# Criar lancamento JA parcelado (parcelas nascem no create-bill)
aegro financial create-bill --description "Adubo" --total-amount 3000 \
  --cash-flow EXPENSE --payment-method INSTALLMENT --category "Insumos" \
  --installments '[{"number":1,"dueDate":"2026-04-15","amount":{"currencyCode":"BRL","amount":1500}},{"number":2,"dueDate":"2026-05-15","amount":{"currencyCode":"BRL","amount":1500}}]'

# Corrigir um lancamento existente (PATCH: so os campos a alterar)
aegro financial update-bill bill::abc123 --body '{"description":"Texto novo"}'

# Realizar (pagar) multiplas parcelas em lote
aegro financial realize --key installment::aaa --key installment::bbb
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

Campos do lancamento: `--cash-flow` e `REVENUE|EXPENSE`; `--category` deve ser
uma categoria ANALYTIC (ver regra 1).

**Escolha do `--payment-method`** (semantica completa na regra 11):

| Situacao                             | payment-method | installments               |
|--------------------------------------|----------------|------------------------------|
| Ja foi pago a vista                  | `PROMPT`       | omitir (gera 1 parcela PAGA) |
| A vencer (1 ou N parcelas)           | `INSTALLMENT`  | obrigatorio (JSON, NOT_PAID) |
| Sem movimentacao (so custo/DRE)      | `NO_PAYMENT`   | nao gera parcela             |

**Itens com categoria propria (`--inputs`)**: quando a conta tem itens
(produtos da nota), categorize **por item** em vez de usar so a categoria da
bill. Cada item leva `elementKey` (exato — o CLI nao resolve nome de item aqui),
quantidade, valores e `financialCategory` propria:

```bash
aegro financial create-bill --description "NF 1234 - insumos" \
  --cash-flow EXPENSE --payment-method INSTALLMENT --company "AgroSul" \
  --total-amount 8000 \
  --inputs '[{"elementKey":"element::aaa","quantity":{"magnitude":100,"unit":"L"},"unitAmount":{"currencyCode":"BRL","amount":50},"amount":{"currencyCode":"BRL","amount":5000},"financialCategory":{"key":"financialCategory::defensivos"}},{"elementKey":"element::bbb","quantity":{"magnitude":10,"unit":"t"},"unitAmount":{"currencyCode":"BRL","amount":300},"amount":{"currencyCode":"BRL","amount":3000},"financialCategory":{"key":"financialCategory::fertilizantes"}}]' \
  --installments '[{"number":1,"dueDate":"2026-08-15","amount":{"currencyCode":"BRL","amount":8000}}]'
```

CRITICO: com `--inputs`, o total da bill e a **soma dos `amount` dos itens** —
o `--total-amount` enviado e ignorado. Confira que a soma bate com a nota.

**Puxe a categoria ja cadastrada do item quando existir.** A API publica le a
categoria **direto pelo elemento** (CLI >= 0.11.0) — nao precisa varrer
categorias nem inferir de lancamentos antigos:
- **Varios itens de uma vez (preferido numa nota com N itens):**
  `aegro elements financial-categories expense --element-key <K1> --element-key <K2> ...`
  (ou `revenue`) retorna, por elemento, a categoria daquele tipo numa **unica
  consulta**. Sem `--element-key`, lista todos os elementos da fazenda.
- **Um item so:** `aegro elements get-categories <elementKey>` (GET read-only)
  traz as categorias de receita e de despesa daquele elemento.
- A categoria vem **nula** quando o item nao tem categoria definida para o tipo
  (ou a definida esta arquivada): so entao caia na categoria unica da bill — e
  confirme a escolha com o usuario.

> A busca reversa `aegro fin-categories subcategories <categoryKey>` (4.2)
> responde a pergunta oposta — quais elementos estao numa categoria — e nao e
> mais necessaria so para descobrir a categoria de um item.

```bash
# Compra JA PAGA a vista (PROMPT gera parcela unica paga); nomes resolvidos,
# fazenda e data inferidas
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
  {"description": "Adubo NPK (pago a vista)", "totalAmount": 1500, "cashFlow": "EXPENSE",
   "paymentMethod": "PROMPT", "category": "Insumos", "company": "Fornecedor X"},
  {"description": "Venda soja", "totalAmount": 90000, "cashFlow": "REVENUE",
   "paymentMethod": "INSTALLMENT", "category": "Venda de Graos", "company": "Cerealista Y",
   "installments": [{"number": 1, "dueDate": "2026-08-15",
                     "amount": {"currencyCode": "BRL", "amount": 90000}}]}
]
```

### 4.2 fin-categories (categorias financeiras)

| Comando                  | Tipo     | Parametros obrigatorios                                                              | Parametros opcionais                                      |
|---------------------------|----------|--------------------------------------------------------------------------------------|-----------------------------------------------------------|
| `get <key>`               | GET      | `key` (argumento)                                                                    | `--output`                                                |
| `list`                    | POST     | (nenhum)                                                                             | `--type` (repetivel), `--operation-type` (repetivel), `--status` (repetivel), `--search-text`, `--page` |
| `create`                  | POST     | `--description`, `--type`, `--operation-type`, `--status`, `--bill-type`, `--code`   | `--observations`, `--parent-code`                         |
| `subcategories <key>`     | POST     | `key` (argumento)                                                                    | `--element-category` (repetivel), `--page`                |

> ATENCAO: apesar do nome, `subcategories` chama
> `/financial-categories/{key}/filter`, que lista os **ELEMENTOS (itens)
> vinculados** a categoria — nao subcategorias (direcao categoria->elementos).
> Para a direcao oposta (a categoria de um elemento), use
> `aegro elements financial-categories <expense|revenue>` ou
> `aegro elements get-categories <elementKey>` (ver 4.1.1). Para navegar a
> hierarquia de categorias, use `list` e o `parentKey`/`code` de cada uma.

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

# Listar os ELEMENTOS (itens) vinculados a uma categoria (nome do comando engana)
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
| `create`           | POST     | `--company` (nome) ou `--company-key`, `--order-date`, `--gross-amount`, `--items` | `--currency` (default BRL), `--currency-exchange-rate`, `--tag` (repetivel), `--category`, `--expected-delivery-date`, `--description`, `--discount-amount`, `--company-order-code`, `--env`, `--complete` |
| `create-batch`     | POST     | `--from-file <arquivo.json>`                               | `--throttle`, `--env`, `--complete`                                               |

O item de `--items` usa **`elementKey`** (exato) ou **`product`** (nome, o CLI
resolve) — `productKey` NAO existe e e rejeitado. Campos obrigatorios do item:
`quantity`, `quantityDelivered`, `measuringUnit`, `unitAmount`, `totalAmount`.

**CRITICO — moeda estrangeira (USD):** a API armazena os valores como recebidos
e o app **divide pela cotacao** na exibicao. Envie
`grossAmount`/`unitAmount`/`totalAmount` **JA CONVERTIDOS para BRL**
(`valor USD x cotacao`), com `--currency USD` + `--currency-exchange-rate
<cotacao>`. Enviar USD bruto corrompe a exibicao (US$ 4,85 vira US$ 0,94).

**Exemplos reais:**

```bash
# Listar ordens de compra de um fornecedor
aegro purchase-orders list --company-key company::abc123

# Criar ordem em BRL, resolvendo empresa e produto por nome
aegro purchase-orders create --company "AgroSul" \
  --order-date 2026-03-15 --gross-amount 15000 \
  --items '[{"product":"Glifosato","quantity":500,"quantityDelivered":0,"measuringUnit":"L","unitAmount":30,"totalAmount":15000}]' \
  --description "Compra de defensivos safra 25/26"

# Criar ordem em USD (valores convertidos: US$ 4,85 x 5,1395 = 24.9266 BRL)
aegro purchase-orders create --company "Corteva" --order-date 2026-06-23 \
  --gross-amount 9472.10 --currency USD --currency-exchange-rate 5.1395 \
  --items '[{"product":"Joint Oil","quantity":380,"quantityDelivered":0,"measuringUnit":"L","unitAmount":24.9266,"totalAmount":9472.10}]'

# Lote com tabela de conferencia (staging primeiro, depois --env prod)
aegro purchase-orders create-batch --from-file pedidos.json --env staging --complete
```

---

## 5. Gotchas de API

### Formato de valor monetario: use {"currencyCode", "amount"}

A spec atual da API publica unificou o objeto monetario em
`MoneyPublicResource = {"currencyCode": "BRL", "amount": X}` — bills, parcelas,
contas bancarias e entradas de estoque. Historicamente a parcela aceitava
`{"amount": X, "currency": "BRL"}` (legado, ainda pode funcionar). Regra
pratica: **envie sempre `currencyCode`**; se receber 400, confira o formato.
Ordem de compra e diferente: `currencyCode` e `grossAmount` sao campos na RAIZ
do body (numeros simples nos itens), nao objetos aninhados.

### CRITICO: bill em moeda estrangeira NAO e suportado via API

Em `POST /bills`, `currencyCode: USD` e
**coagido silenciosamente para BRL**, e `currencyConversion`/
`currencyConversionQuoteType` sao **aceitos e ignorados** na escrita — o
lancamento sai errado sem nenhum erro. O CLI **bloqueia** `--currency != BRL`
em create-bill/create-bills com orientacao. Alternativas: lancar o valor JA
CONVERTIDO em BRL (registrando moeda/cotacao na descricao) ou lancar pelo app.
**Pedidos de compra em moeda estrangeira SAO suportados**: valores convertidos
para BRL + `--currency USD --currency-exchange-rate <cotacao>` (ver 4.5).

### PROMPT cria parcela JA PAGA (e realize e irreversivel)

`paymentMethod: PROMPT` gera (ou marca) a parcela unica como **realizada** na
propria criacao — equivale a dizer que o dinheiro ja saiu/entrou. Nao ha
unrealize via API. Conta a vencer com parcela unica = `INSTALLMENT` com 1
parcela. `INSTALLMENT` sem `installments` retorna erro de validacao;
`NO_PAYMENT` descarta a conta bancaria e nao gera parcela.

### Com inputs, totalAmount e recalculado (soma dos itens)

Se a bill tem `inputs`, a API **ignora o `totalAmount` enviado** e grava o
total como a soma dos `amount` dos itens. Divergencia entre soma dos itens e
total da nota (frete, desconto, arredondamento) muda o valor do lancamento em
silencio — confira a soma antes de criar.

### Campo "Produtor" nao e suportado via API

Bill e parcelas tem produtor (empresa) no produto, mas nenhum endpoint publico
expoe o campo (nem na escrita, nem na leitura). Lancamento criado via API fica
sem produtor; ajuste apenas pelo app. Relevante para clientes que organizam o
financeiro por produtor rural.

### Parcelas: sem CRUD avulso na API

Nao existem endpoints de criar/atualizar/excluir parcela individual (so
`filter`, `realizeList` e GET). Parcelas nascem no `create-bill`
(campo `installments`); correcoes via `update-bill` (PATCH) ou pelo app.
Nao ha "unrealize" (desfazer pagamento).

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

1. **Nao invente comandos de parcela.** `create-installment`,
   `update-installment` e `delete-installment` NAO existem (nem no CLI nem na
   API). Parcelas nascem no `create-bill` (campo `installments`); pagamento via
   `realize`; correcao via `update-bill` (PATCH) ou pelo app.

2. **Nao tente "desfazer" pagamento via API.** Nao ha unrealize. Realize e
   irreversivel pela API — confirme antes de executar; correcao so pelo app.

3. **Nao misture formatos de moeda.** Envie `{"currencyCode": "BRL", "amount": X}`
   (MoneyPublicResource unificado na spec atual). Em ordem de compra,
   `currencyCode`/`grossAmount` sao campos na raiz do body.

4. **Nao use `cropProrateGroupKey` na raiz do bill.** E aceito e IGNORADO em
   silencio. Apropriacao direta = `financialApportion` (type CROP_PRORATE +
   cropKeys); apropriacao salva (grupo com percentuais) nao pode ser aplicada
   via API — so leitura.

5. **Nao associe lancamentos a categorias SYNTHETIC.** Somente ANALYTIC recebe lancamentos. Verifique o tipo com `aegro fin-categories get <key>`.

6. **Nao esqueca --parent-code ao criar subcategoria.** Sem `--parent-code`, a categoria sera criada como raiz, quebrando a hierarquia.

7. **Verifique saldo antes de sugerir realize.** O realize nao valida saldo bancario. Confirme com o usuario que ha saldo suficiente na conta antes de marcar parcelas como pagas.

8. **Nao crie empresa duplicada.** Antes de `companies create`, busque com `companies list --search-text "nome"` ou `--fiscal-number-type CNPJ` para evitar duplicatas. Atencao: a busca textual da API tem falso-negativo conhecido (empresa existente pode nao aparecer) — em caso de duvida, liste sem filtro antes de criar. `fiscalNumber` e obrigatorio (required na spec).

9. **Nao use PROMPT para conta a vencer.** PROMPT gera parcela JA PAGA (irreversivel via API). Conta a vencer com parcela unica = INSTALLMENT com 1 parcela.

10. **Nao confie no totalAmount quando enviar inputs.** Com itens, o total gravado e a soma dos `amount` dos itens — o totalAmount enviado e ignorado.

11. **Nao ignore a categoria dos itens.** Se a conta tem itens com categoria ja cadastrada (ou usada em lancamentos anteriores), categorize por item via `inputs` — jogar tudo numa categoria unica da bill distorce o DRE por categoria.
