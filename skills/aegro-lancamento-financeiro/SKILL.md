---
name: aegro-lancamento-financeiro
description: >-
  Conduz o registro de conta a pagar ou a receber no Aegro pela CLI: decide
  categoria, fornecedor ou cliente, condicao de pagamento e parcelamento antes
  de montar o comando, e entrega o link direto do lancamento criado. Foco na
  sequencia de decisoes, nao na sintaxe. Use quando pedirem "lancar uma
  conta", "registrar despesa", "conta a pagar", "conta a receber", "cadastrar
  o pagamento do fornecedor"; EN "create a bill", "record an expense". NAO use
  para dar entrada em NF-e recebida (use /aegro-entrada-nota-fiscal), para
  conciliar extrato (use /aegro-conciliacao-bancaria) nem como referencia de
  comandos do dominio (use /aegro-financeiro).
---

# Lancamento Financeiro

## Objetivo

Guiar o registro correto de contas a pagar e receber no Aegro, garantindo
categorizacao adequada, vinculacao com fornecedores/clientes e parcelamento
correto. Foco na sequencia de decisoes, nao na sintaxe dos comandos.

## Quando Usar

- Registrar nova compra de insumo
- Lancar venda de producao
- Parcelar pagamento de fornecedor
- Registrar recebimento de cliente
- Corrigir lancamento existente

## Pre-requisitos de Conhecimento

Para detalhes dos comandos e regras de negocio:
- `/aegro-financeiro` -- parcelas, categorias, contas bancarias, empresas, bills

## Caminho Rapido: create-bill inteligente

Para lancar uma conta nova, **prefira `aegro financial create-bill`** -- ele
resolve nomes em chaves, infere fazenda e data, e **pergunta so o que falta**.
Voce nao precisa pre-buscar `company::`/`financialCategory::`/`farmKey`: passe os
nomes.

- Conta unica: `create-bill --description ... --total-amount ... --cash-flow
  EXPENSE|REVENUE --payment-method ... --category "<nome>" --company "<nome>"`.
- **Em massa**: monte um JSON name-based e use `create-bills --batch <arquivo>`,
  que devolve uma **tabela de conferencia** por linha (status + nomes resolvidos).
- **Priorize o acerto**: rode com `--complete` (ou `--dry-run`) primeiro para
  conferir o que foi resolvido/inferido e o que falta, **antes** de executar.
- **Lote pequeno primeiro** (uso interno): escreva algumas linhas no ambiente
  do trabalho, releia o que gravou, e so entao mande o resto. Um ensaio em
  `--env staging` serve para conhecer o comando, **nao como validacao**: aquele
  ambiente e reposto de producao todo dia as 03:15 BRT e o que foi lancado la
  desaparece. Nao sugira staging a clientes.

Sintaxe completa e exemplos em `/aegro-financeiro` (secao 4.1.1). **Parcelas
nascem no proprio `create-bill`** (campo `installments`) -- nao existe CRUD
avulso de parcela na API. Para ajustar a **conta**, use `financial update-bill`
(PATCH) ou o app; para ajustar **parcela** (vencimento ou valor), so pela tela:
`installments` nao existe no schema do patch, e a API ignora campo que nao
declara — por desenho, nao por defeito. O CLI recusa o campo antes de enviar.

- **Anexo da nota/comprovante**: `create-bill --attach ./nota.pdf` (repetivel)
  anexa na mesma invocacao. Exige login OAuth (o upload e API interna); com API
  key falha ANTES de criar. Em conta ja existente:
  `aegro files attach --farm "<fazenda>" --entity bill --key bill::<id> --file ./nota.pdf --execute`.
  Se o create passar e o anexo falhar, o stderr traz `attachRetry` com `--url` --
  rode ele, NUNCA repita o create (duplicaria a conta).

## Fluxo de Decisao

```
Usuario quer lancar transacao
         |
    Despesa ou Receita?
    /                  \
DESPESA               RECEITA
(a pagar)             (a receber)
   |                      |
operation: DEBTOR    operation: CREDITOR
   |                      |
Buscar categoria     Buscar categoria
ANALYTIC + DEBTOR    ANALYTIC + CREDITOR
   |                      |
Empresa tipo         Empresa tipo
PROVIDER             CLIENT
   |                      |
   +---- Definir ----+
         |
    Como sera o pagamento?
    /        |          \
JA PAGO    A VENCER    SEM PAGAMENTO
(baixa     (1..N parc)  (so custo/DRE)
confirmada)   |             |
   |          |             |
PROMPT     INSTALLMENT   NO_PAYMENT
parcela    parcelas em   sem parcela,
unica JA   --installments sem conta
PAGA       (NOT_PAID)    bancaria
```

**Regra do ramo "JA PAGO":** exige pagamento E baixa confirmados (os dois).
Pagamento que ja ocorreu mas cuja baixa ainda NAO foi confirmada segue o ramo
`A VENCER` (`INSTALLMENT` com 1 parcela) -- nunca `JA PAGO`/`PROMPT` so por
causa do vencimento ja ter passado ou ser hoje.

Atencao: `PROMPT` marca a parcela como **paga na criacao** (irreversivel via
API). **"A vista" na fala do usuario descreve a condicao de pagamento
(vencimento imediato), nao a baixa**: conta a vista cuja baixa NAO foi
confirmada - mesmo com vencimento hoje ou na data da nota - e `INSTALLMENT`
com 1 parcela (padrao do time de Servicos, para o sistema nao marcar "pago"
sozinho; ENTRADA-135). `INSTALLMENT` exige `--installments`; `NO_PAYMENT` nao
gera parcela nem movimenta caixa.

## Sequencia de Passos

### 1. Identificar tipo de operacao

Perguntar ao usuario:
- Despesa (conta a pagar) ou receita (conta a receber)?
- **O pagamento JA ACONTECEU ou esta a vencer?** ("a vista" NAO responde isso -
  e condicao de vencimento, nao baixa.) Define o payment-method: PROMPT (parcela
  unica ja paga - so com baixa confirmada), INSTALLMENT (a vencer, 1..N
  parcelas - inclusive conta a vista ainda nao paga: 1 parcela com vencimento
  na data) ou NO_PAYMENT (sem movimentacao de caixa).
- Valor total e quantas parcelas?
- Data de vencimento (ou primeira parcela)?
- A conta tem itens (produtos da nota)? Se sim, categorizar POR ITEM (passo 2).

### 2. Buscar categoria financeira (por item, quando houver itens)

Buscar categorias ANALYTIC do tipo correto (DEBTOR ou CREDITOR).
A categoria impacta diretamente o DRE -- escolher com cuidado.
Se nao encontrar, buscar subcategorias da categoria pai.

**Conta com itens**: cada item pode (e deve) ter categoria propria via
`inputs`. **Puxe a categoria ja cadastrada do item quando existir** — a API
publica le a categoria direto pelo elemento (CLI >= 0.11.0):
`aegro elements financial-categories expense --element-key <K1> --element-key <K2> ...`
(ou `revenue`) traz a categoria de cada item numa unica consulta; para um item
so, `aegro elements get-categories <elementKey>`. So use a categoria unica da
bill quando o item vier sem categoria definida — confirmando com o usuario.
Atencao: com `inputs`, o total da bill vira a SOMA dos itens (o total enviado e
ignorado). Detalhes em `/aegro-financeiro` (regra 12 e secao 4.1.1).

### 3. Buscar ou identificar empresa

Buscar fornecedor (PROVIDER) para despesas ou cliente (CLIENT) para receitas.
A busca textual tem falso-negativo conhecido: se nao encontrar, **liste sem
filtro antes de concluir que nao existe**. Nunca crie a empresa por conta
propria -- confirme com o usuario (e nao cadastre filial como empresa nova se
a matriz ja existe; unifique).

### 4. Selecionar conta bancaria

Listar contas bancarias, identificar a padrao e verificar saldo disponivel.

### 5. Verificar duplicidade

Antes de criar, filtrar lancamentos existentes da mesma empresa no periodo
(mesmo valor/vencimento). Nota reenviada ou planilha relancada e causa comum
de lancamento duplicado -- em caso de suspeita, mostrar os candidatos ao
usuario antes de prosseguir.

### 6. Criar o lancamento com parcelas

Um unico `create-bill` com o campo `installments` -- as parcelas nascem junto
com a bill e nao podem ser criadas avulsas depois. Definir vencimento, valor e
conta bancaria de cada parcela no proprio create.

### 7. Confirmar lancamento

Buscar parcelas da bill (`financial installments --bill-key ...`) para
verificar que tudo foi criado corretamente.

## Fluxos Especificos

### Compra de Insumo Parcelada

1. Tipo: DEBTOR (a pagar)
2. Categoria: buscar em "Insumos", "Defensivos" ou "Fertilizantes"
3. Empresa: fornecedor (PROVIDER)
4. Criar N parcelas dividindo valor e escalonando vencimentos

### Venda de Producao

1. Tipo: CREDITOR (a receber)
2. Categoria: "Venda de Graos" ou similar
3. Empresa: cliente (CLIENT)
4. Parcelas conforme contrato de venda

### Pagamento a Vista (ja pago)

1. `--payment-method PROMPT`, sem `--installments`: a API gera **parcela unica
   JA PAGA** automaticamente (vencimento = data do lancamento)
2. **Isso equivale a um realize, que e irreversivel via API** (nao ha
   "unrealize") -- confirmar com o usuario que o pagamento de fato ocorreu
   E que ele quer a parcela ja baixada
3. Se a conta e "a vista" mas a baixa nao foi confirmada - vencimento futuro
   OU na propria data do lancamento - use `INSTALLMENT` com 1 parcela NOT_PAID
   e realize depois (padrao do time de Servicos: evita a baixa automatica e o
   produtor confirma o pagamento ao revisar)

### Sem Pagamento (so custo/DRE)

1. `--payment-method NO_PAYMENT`: nenhuma parcela e criada e a conta bancaria
   e descartada -- o lancamento nao afeta o fluxo de caixa
2. Usar para registrar custo/receita contabil sem movimentacao financeira
   (ex.: consumo interno, bonificacao); em duvida, confirmar com o usuario

### Conta com Itens (categoria por item)

1. Montar `--inputs` com um item por produto da nota: `elementKey` exato,
   quantidade, valores e `financialCategory` propria de cada item
2. Puxar a categoria ja cadastrada de cada item quando existir (passo 2);
   perguntar so os itens sem categoria
3. Conferir que a soma dos itens = total da nota -- **a API grava como total a
   soma dos itens**, ignorando o total enviado (frete/desconto fora dos itens
   somem em silencio)
4. **Itens NAO movimentam estoque.** `inputs` define categoria por produto e o
   rateio de custo, e nada mais: sem um grupo de apropriacao de estoque no
   corpo, o servidor salva a conta e **nao gera movimentacao nenhuma**, sem erro
   e sem aviso (`StockLogServiceImpl`: `costApportion == null` -> nenhum
   `stockLog`). Nao existe formato de `--inputs` que mude isso.

### Entrada de Estoque: nao sai pelo lancamento manual

Se a pessoa pediu que a nota **entrasse no estoque**, diga isso **antes de
executar** — nao depois. O `create-bill` nao tem flag que monte o grupo
`STOCK_INPUTS` (as duas que existem, `--apportion-crop` e `--apportion-asset`,
produzem `CROP_PRORATE` e `ASSET_PRORATE`), entao a conta sai correta no
financeiro e o estoque fica intocado. Foi exatamente o que aconteceu em campo:
pediu-se entrada de estoque, veio "criado com sucesso", e a operadora descobriu
depois.

Os dois caminhos que funcionam hoje:

| Situacao | Caminho |
|---|---|
| A nota esta na SEFAZ | `/aegro-entrada-nota-fiscal` -> `received-fiscal-documents launch-bill --stock-location "<local>"` (concilia os itens **e** movimenta) |
| Nao ha nota na SEFAZ (so o PDF) | lance a conta aqui **e** a movimentacao em separado, por `/aegro-estoquista` (`stock entry`) — sao dois registros, e diga isso ao usuario |

Enquanto `create-bill` nao tiver a flag, **nao prometa
estoque por este caminho**.

### Conta em Moeda Estrangeira (USD)

Bill em moeda estrangeira **nao e suportada via API** (currencyCode e coagido
para BRL em silencio). Lancar o valor **ja convertido em BRL** e registrar
moeda e cotacao na descricao -- ou orientar o lancamento pelo app.
Detalhes em `/aegro-financeiro` (secao 5).

### Custo Apropriado a Safra

Para o lancamento entrar no custo da safra, usar apropriacao direta:
`--apportion-crop "Safra X"` (repetivel). Com multiplas safras, o rateio e
automatico e proporcional a area. Rateio com percentuais pre-definidos
(apropriacao salva) nao pode ser aplicado via API -- so pelo app.

## Formato de Resposta

```markdown
## Lancamento Financeiro

### Dados da Transacao
| Campo | Valor |
|-------|-------|
| Tipo | Conta a Pagar |
| Fornecedor | Agro Insumos Ltda |
| Categoria | Defensivos > Herbicidas |
| Valor total | R$ 15.000,00 |

### Parcelamento
| Parcela | Vencimento | Valor | Status |
|---------|------------|-------|--------|
| 1/3 | 15/03 | R$ 5.000,00 | Pendente |
| 2/3 | 15/04 | R$ 5.000,00 | Pendente |
| 3/3 | 15/05 | R$ 5.000,00 | Pendente |

### Conta Bancaria
- **Conta:** Banco do Brasil - Conta Corrente
- **Saldo atual:** R$ 125.000,00
```

## Boas Praticas

1. **Sempre categorizar corretamente** -- impacta DRE e relatorios
2. **Vincular ao fornecedor/cliente** -- facilita conciliacao
3. **Usar conta bancaria correta** -- separa operacional de investimento
4. **Descrever a transacao** -- facilita auditoria futura
5. **Conferir parcelamento** -- evita surpresas no fluxo de caixa
6. **Checar duplicidade antes de lancar** -- nota reenviada gera bill dobrada
7. **Anexos sao manuais** -- a API nao anexa arquivos ao lancamento; orientar
   o usuario a anexar o documento pelo app apos o lancamento
8. **Categorizar por item quando a conta tem itens** -- usar `inputs` com a
   categoria ja cadastrada de cada item; categoria unica na bill distorce o
   DRE por categoria
9. **Campo "Produtor" nao sai via API** -- se o cliente organiza os
   lancamentos por produtor rural, avisar ANTES de lancar em massa: o campo
   nao existe na API publica e o ajuste e manual, pelo app, em cada lancamento

## Entregue o Link da Conta

Depois de criar ou editar a conta, ofereca o link que abre **aquele
lancamento** para conferencia. O `create-bill` ja devolve tudo que o link
precisa (`key` e `farmKey`):

```
{host}/farm/{farmId}?billId={billId}#farm-finance
```

Abre o dialogo **Editar lancamento** com a conta carregada. Avise que o link
vale uma vez: o parametro e consumido ao abrir, entao recarregar a pagina
nao reabre o formulario.

Regras que nao podem ser puladas (detalhe em `/aegro-operacional`, secao
"Link Direto para a Entidade"): host vem do `--env` da sessao
(`https://app.aegro.com.br` em prod, `https://app.staging.aegro.io` em
staging), a URL usa a chave **sem** o prefixo `tipo::`, e link com aba
invalida **nao da erro** — cai na home da fazenda em silencio. Nunca invente
template por analogia.

## Proximos Workflows

| Situacao | Proximo workflow |
|----------|------------------|
| Verificar impacto no caixa | `/aegro-visao-geral` |
| Analisar custos da safra | `/aegro-analise-rentabilidade` |
| Reconciliar com estoque | `/aegro-reconciliacao-estoque` |
