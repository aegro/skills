---
name: aegro-lancamento-financeiro
description: Guia para criar e gerenciar contas a pagar e receber corretamente
version: 0.6.0
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
- **Staging-first** (uso interno): lance com `--env staging`, confira na UI, e
  promova com `--env prod` rodando o mesmo arquivo. Nao sugira staging a clientes.

Sintaxe completa e exemplos em `/aegro-financeiro` (secao 4.1.1). O fluxo manual
de parcelas abaixo (`create-installment`) continua valido para ajustes finos de
parcelamento em lancamentos existentes.

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
    Quantas parcelas?
    /              \
UMA               VARIAS
(a vista)         (parcelado)
   |                  |
Parcela unica     Dividir valor
venc = hoje       e vencimentos
```

## Sequencia de Passos

### 1. Identificar tipo de operacao

Perguntar ao usuario:
- Despesa (conta a pagar) ou receita (conta a receber)?
- Valor total e quantas parcelas?
- Data de vencimento (ou primeira parcela)?

### 2. Buscar categoria financeira

Buscar categorias ANALYTIC do tipo correto (DEBTOR ou CREDITOR).
A categoria impacta diretamente o DRE -- escolher com cuidado.
Se nao encontrar, buscar subcategorias da categoria pai.

### 3. Buscar ou identificar empresa

Buscar fornecedor (PROVIDER) para despesas ou cliente (CLIENT) para receitas.
Se nao encontrar, informar que precisa cadastrar primeiro.

### 4. Selecionar conta bancaria

Listar contas bancarias, identificar a padrao e verificar saldo disponivel.

### 5. Localizar ou criar bill

Se for parcela adicional, buscar a bill existente e verificar status.
Para nova transacao, identificar a bill correta.

### 6. Criar parcela(s)

Criar parcelas com bill_key, bank_account_key, vencimento e valor.

### 7. Confirmar lancamento

Buscar parcelas da bill para verificar que tudo foi criado corretamente.

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

### Pagamento a Vista

1. Parcela unica com vencimento = data do pagamento
2. Pode ser realizada imediatamente apos criacao

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

## Proximos Workflows

| Situacao | Proximo workflow |
|----------|------------------|
| Verificar impacto no caixa | `/aegro-visao-geral` |
| Analisar custos da safra | `/aegro-analise-rentabilidade` |
| Reconciliar com estoque | `/aegro-reconciliacao-estoque` |
