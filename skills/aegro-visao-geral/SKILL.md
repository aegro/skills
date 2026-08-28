---
name: aegro-visao-geral
description: >-
  Panorama da fazenda pela CLI aegro: safras ativas, saldo consolidado das
  contas bancarias, contas a pagar e a receber dos proximos 30 dias e alertas
  de estoque, num resumo unico para abrir atendimento ou reuniao de
  acompanhamento. Use quando pedirem "como esta minha fazenda", "panorama da
  fazenda", "resumo geral", "o que precisa de atencao"; EN "farm overview",
  "how is my farm doing". NAO use para executar acao — e so leitura: para
  lancar conta use /aegro-lancamento-financeiro, para safra use
  /aegro-cadastro-safra, para estoque use /aegro-estoquista.
---

# Visao Geral da Fazenda

## Objetivo

Fornecer um panorama rapido e acionavel da fazenda: safras ativas, posicao
financeira, contas pendentes e alertas de estoque. Ideal para inicio de
atendimento ou reuniao de acompanhamento.

## Quando Usar

- Inicio de sessao com cliente
- Cliente pergunta "como esta minha fazenda?"
- Antes de investigar problema especifico
- Reuniao de acompanhamento periodico

## Pre-requisitos de Conhecimento

Para detalhes dos comandos e regras de negocio:
- `/aegro-operacional` -- fazendas, talhoes, selecao de fazenda
- `/aegro-agronomo` -- safras, atividades, colheitas
- `/aegro-financeiro` -- parcelas, categorias, contas bancarias

## Sequencia de Passos

### 1. Confirmar a fazenda

Liste com `aegro farms list` e confirme com o usuario qual e a fazenda. Passe
`--farm "<Fazenda|farm::key>"` em **todos** os comandos seguintes: nao existe
fazenda "selecionada" implicita, e uma sessao em paralelo trocaria o alvo desta
sem avisar. Sem a fazenda
nenhum passo seguinte funciona.

### 2. Listar safras ativas

Buscar safras com periodo amplo (ano anterior ao proximo).
- Destacar safras com colheita em andamento
- Calcular area total por cultura
- Identificar safras sem atividades recentes (possivel problema)

### 3. Verificar saldo bancario

Listar contas bancarias e consolidar saldos.
- Somar saldos para posicao consolidada
- Destacar contas com saldo negativo
- Identificar conta principal (is_default: true)

### 4. Identificar contas a pagar (proximos 30 dias)

Buscar parcelas PENDING com vencimento nos proximos 30 dias.
- Agrupar por semana de vencimento
- Destacar valores acima de R$ 10.000
- Calcular total a pagar e comparar com saldo disponivel

### 5. Identificar contas a receber (proximos 30 dias)

Buscar parcelas CREDITOR PENDING no mesmo periodo.
- Calcular total a receber
- Identificar maiores devedores

### 6. Verificar estoque critico (opcional)

Listar itens em estoque.
- Alertar itens com quantidade zero ou negativa
- Identificar insumos criticos (defensivos, fertilizantes)

## Como Interpretar Resultados

O valor deste workflow esta na **sintese cruzada**:

| Sinal | Interpretacao | Gravidade |
|-------|---------------|-----------|
| Saldo < total a pagar 30d | Risco de inadimplencia | ALTA |
| Safra sem atividade > 15 dias | Possivel abandono ou falha de registro | MEDIA |
| Estoque zerado de insumo critico | Risco operacional | ALTA |
| Saldo projetado positivo | Situacao financeira saudavel | OK |
| Receber > pagar | Fluxo de caixa favoravel | OK |

**Saldo projetado** = Saldo atual - A pagar + A receber (30 dias)

## Formato de Resposta

```markdown
## Fazenda: {{nome}}

### Safras Ativas
| Cultura | Safra | Area (ha) | Status |
|---------|-------|-----------|--------|
| Soja | 24/25 | 450 | Colheita |
| Milho | 24/25 | 200 | Vegetativo |

**Area total:** 650 ha

### Posicao Financeira
| Indicador | Valor |
|-----------|-------|
| Saldo em conta | R$ 125.000,00 |
| A pagar (30 dias) | R$ 45.000,00 |
| A receber (30 dias) | R$ 80.000,00 |
| **Saldo projetado** | **R$ 160.000,00** |

### Alertas
- Estoque de Glifosato zerado
- 2 parcelas vencem esta semana (R$ 15.000)
- Safra de Soja sem atividades ha 15 dias
```

## Proximos workflows

| Alerta detectado | Proximo workflow |
|------------------|------------------|
| Problema financeiro | `/aegro-lancamento-financeiro` |
| Safra proxima do fim | `/aegro-fechamento-safra` |
| Divergencia de estoque | `/aegro-reconciliacao-estoque` |
| Muitas aplicacoes | `/aegro-monitoramento-pragas` |
| Analise de custos | `/aegro-analise-rentabilidade` |
