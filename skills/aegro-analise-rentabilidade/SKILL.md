---
name: aegro-analise-rentabilidade
description: Calcular ROI, custo por hectare e margem bruta da safra
version: 0.5.3
---

# Analise de Rentabilidade

## Objetivo

Calcular e apresentar indicadores de rentabilidade da safra:
custo por hectare, custo por saca, margem bruta e ROI.
Fundamental para tomada de decisao e consultoria.

## Quando Usar

- Avaliacao de resultado da safra (pos-colheita)
- Comparacao entre safras ou talhoes
- Planejamento da proxima safra com base em custos
- Cliente pergunta "quanto lucrei?" ou "qual meu custo por hectare?"

## Pre-requisitos

Carregue estes domain skills antes de iniciar:

- **`/aegro-agronomo`** — comandos de safra, talhoes, atividades, colheitas e realizacoes
- **`/aegro-financeiro`** — comandos de lancamentos, parcelas e categorias

Fazenda deve estar selecionada. Safra preferencialmente apos colheita (dados mais completos).

## Formulas

```
CUSTO TOTAL = Custos Diretos + Custos Indiretos (rateados)

Custos Diretos (de realizacoes):
  + Sementes      (atividades tipo SOWING)
  + Defensivos    (atividades tipo APPLICATION)
  + Fertilizantes (atividades tipo FERTILIZATION)
  + Operacoes     (colheita, servicos, combustivel)

Custos Indiretos (via rateio):
  + Administrativo, depreciacao, manutencao geral

RECEITA = Producao (sacas) x Preco Medio
          (ou soma de vendas lancadas no financeiro)

CUSTO/HA   = Custo Total / Area (ha)
CUSTO/SACA = Custo Total / Producao (sacas)
MARGEM BRUTA = Receita - Custo Total
MARGEM %     = (Margem Bruta / Receita) x 100
ROI          = (Margem Bruta / Custo Total) x 100

Producao em sacas (soja): Peso Descontado (kg) / 60
```

## Sequencia de Coleta de Dados

### 1. Identificar safra

```bash
aegro crops list --farm "<fazenda>" --start-date {{ano-1}}-01-01 --end-date {{ano}}-12-31
aegro crops get --farm "<fazenda>" <crop_key>
```

Extrair: area total (ha), cultura, ciclo, status.

### 2. Confirmar talhoes e area

```bash
aegro crops glebes --farm "<fazenda>" <crop_key>
```

Somar areas dos crop-glebes para area total confirmada.

### 3. Obter custos diretos (realizacoes)

```bash
aegro activities realizations --farm "<fazenda>" --crop-key <crop_key>
```

Agrupar custos por tipo: plantio, aplicacoes, adubacao, colheita.

### 4. Obter custos indiretos (rateios)

```bash
aegro crops prorates --farm "<fazenda>" --crop-key <crop_key>
aegro crops prorate --farm "<fazenda>" <prorate_key>
```

Se existirem rateios, somar valores rateados para esta safra.

### 5. Obter receita

```bash
aegro financial installments --farm "<fazenda>" --operation-type REVENUE
```

Filtrar vendas da safra. Se nao houver vendas lancadas, solicitar preco medio ao usuario.

### 6. Calcular producao

Usar dados de romaneios (colheita). Producao em sacas = peso descontado total (kg) / 60.

## Calculo

Aplicar as formulas da secao acima com os dados coletados.
**Dados incompletos?** Alertar o usuario sobre subestimativa e quais dados faltam.

## Formato de Resposta

```markdown
## Analise de Rentabilidade: [Cultura] [Safra]

### Dados da Safra
| Indicador | Valor |
|-----------|-------|
| Area | X ha |
| Producao | X sacas |
| Produtividade | X sc/ha |

### Custos
| Categoria | Valor | R$/ha |
|-----------|-------|-------|
| Sementes | R$ X | R$ X |
| Defensivos | R$ X | R$ X |
| Fertilizantes | R$ X | R$ X |
| Operacoes | R$ X | R$ X |
| **Custo Direto** | **R$ X** | **R$ X** |
| Rateio | R$ X | R$ X |
| **CUSTO TOTAL** | **R$ X** | **R$ X** |

### Indicadores de Rentabilidade
| Indicador | Valor | Avaliacao |
|-----------|-------|-----------|
| Custo/ha | R$ X | (vs benchmark) |
| Custo/saca | R$ X | |
| Margem Bruta | R$ X | |
| Margem % | X% | |
| **ROI** | **X%** | |

### Composicao de Custos (%)
[Representacao visual da distribuicao percentual]

### Observacoes
- [insights relevantes, comparativos, pontos de atencao]
```

## Benchmarks de Referencia (Soja Brasil)

| Indicador | Baixo | Medio | Alto |
|-----------|-------|-------|------|
| Custo/ha | <R$ 2.000 | R$ 2.000-2.800 | >R$ 2.800 |
| Produtividade | <50 sc/ha | 50-65 sc/ha | >65 sc/ha |
| Margem % | <40% | 40-60% | >60% |

*Valores de referencia - variam por regiao, ano e cambio. Usar como orientacao, nao como regra.*

## Proximos Workflows

- **Verificar dados completos** → `/aegro-fechamento-safra`
- **Conferir custos de insumos** → `/aegro-reconciliacao-estoque`
- **Monitorar defensivos** → `/aegro-monitoramento-pragas`
- **Visao geral da fazenda** → `/aegro-visao-geral`
