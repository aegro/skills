---
name: aegro-monitoramento-pragas
description: >-
  Acompanha aplicacoes de defensivos na safra pela CLI, cruza com o consumo de
  estoque e aponta padroes de uso que indiquem risco de resistencia ou
  ineficacia. Use quando pedirem "quais defensivos apliquei", "historico de
  aplicacao", "risco de resistencia", "monitoramento de pragas", "controle
  fitossanitario"; EN "pesticide applications". NAO use para registrar a
  aplicacao (use /aegro-agronomo) nem para saldo de defensivo em estoque (use
  /aegro-estoquista).
---

# Monitoramento de Pragas e Defensivos

## Objetivo

Acompanhar aplicacoes de defensivos na safra, cruzar com consumo de estoque
e identificar padroes de uso que indiquem risco de resistencia ou ineficacia.
Essencial para controle fitossanitario e gestao de custos com defensivos.

## Quando Usar

- Verificar historico de aplicacoes na safra
- Analisar consumo de defensivos vs estoque
- Identificar padroes de frequencia e dosagem
- Avaliar risco de resistencia por uso repetido
- Cliente pergunta "quanto gastei com defensivo?" ou "quantas aplicacoes fiz?"

## Pre-requisitos

Carregue estes domain skills antes de iniciar:

- **`/aegro-agronomo`** — comandos de safra, atividades e realizacoes
- **`/aegro-estoquista`** — comandos de estoque, itens e movimentacoes

Fazenda deve estar selecionada e safra identificada.

## Sequencia de Passos

### 1. Listar defensivos cadastrados

```bash
aegro elements list --farm "<fazenda>" --category DEFENSIVE
```

Organizar por tipo: HERBICIDE, INSECTICIDE, FUNGICIDE, ACARICIDE, OTHER.

### 2. Buscar atividades de aplicacao da safra

```bash
aegro activities list --farm "<fazenda>" --crop-key <crop_key> --type APPLICATION
```

Extrair: data planejada, talhoes alvo, produtos, status (planejada/realizada/cancelada).

### 3. Buscar realizacoes efetivas

```bash
aegro activities realizations --farm "<fazenda>" --crop-key <crop_key> --start-date {{inicio_safra}} --end-date {{hoje}}
```

Filtrar apenas tipo APPLICATION. Extrair: data efetiva, produto, dose/ha, area aplicada.

### 4. Verificar estoque atual de defensivos

```bash
aegro stock items --farm "<fazenda>"
```

Filtrar elementos DEFENSIVE. Identificar: estoque critico (<10% uso medio), zerados.

### 5. Buscar movimentacoes de estoque por produto

```bash
aegro stock logs --farm "<fazenda>" --element-key <defensive_key> --start-date {{inicio_safra}} --end-date {{hoje}}
```

Analisar: entradas (compras), saidas (consumo), transferencias.

### 6. Consolidar e cruzar dados

- Aplicacoes planejadas vs realizadas
- Consumo em realizacoes vs baixas de estoque
- Frequencia de aplicacao por produto e grupo quimico
- Custo acumulado por tipo de defensivo

## Como Interpretar Padroes

### Frequencia de Aplicacao

| Padrao | Interpretacao | Acao |
|--------|--------------|------|
| Mesmo produto >3x na safra | Pressao alta da praga/doenca | Avaliar eficacia |
| Mesmo grupo quimico >4x | Risco de resistencia | Rotacionar grupo |
| Intervalo <15 dias entre aplicacoes | Controle insuficiente | Revisar dose e produto |
| Sem aplicacao por >45 dias | Possivel janela de monitoramento | Confirmar com campo |

### Risco de Resistencia

| Fator | Risco Baixo | Risco Alto |
|-------|-------------|------------|
| Grupos quimicos diferentes | >3 na safra | 1-2 na safra |
| Rotacao de modo de acao | Sim, alternando | Nao, repetindo |
| Dose aplicada vs recomendada | Dose cheia | Subdose (<80%) |
| Eficacia percebida | Estavel | Decrescente |

## Formato de Resposta

```markdown
## Monitoramento de Defensivos: [Cultura] [Safra]

### Resumo
| Indicador | Valor |
|-----------|-------|
| Total de aplicacoes | X |
| Produtos diferentes | X |
| Grupos quimicos | X |
| Custo total estimado | R$ X |

### Aplicacoes por Tipo
| Tipo | Qtd | % Total |
|------|-----|---------|
| Herbicidas | X | X% |
| Inseticidas | X | X% |
| Fungicidas | X | X% |

### Historico Cronologico
| Data | Produto | Tipo | Dose | Area |
|------|---------|------|------|------|

### Estoque Atual
| Produto | Consumido | Estoque | Status |
|---------|-----------|---------|--------|
| ... | X L | X L | OK/BAIXO/ZERADO |

### Alertas
- [lista de alertas identificados]
```

## Boas Praticas Fitossanitarias

1. **Rotacionar grupos quimicos** — Nunca repetir mesmo modo de acao em sequencia
2. **Respeitar dose recomendada** — Subdose gera resistencia, sobredose gera custo
3. **Registrar alvo** — Documentar praga/doenca controlada em cada aplicacao
4. **Respeitar carencia** — Verificar dias para colheita antes de aplicar
5. **Monitorar eficacia** — Retornar ao campo 7-10 dias apos aplicacao

## Indicadores de Alerta

| Situacao | Nivel | Acao |
|----------|-------|------|
| Estoque zerado de defensivo | CRITICO | Verificar necessidade imediata |
| Estoque < 20% do uso medio | ATENCAO | Planejar reposicao |
| >4 aplicacoes mesmo produto | REVISAR | Avaliar resistencia/eficacia |
| Aplicacao planejada sem realizacao | PENDENTE | Confirmar se foi executada |
| Intervalo entre aplicacoes <15 dias | ATENCAO | Revisar pressao e eficacia |

## Proximos Workflows

- **Divergencia de estoque** → `/aegro-reconciliacao-estoque`
- **Custo total da safra** → `/aegro-analise-rentabilidade`
- **Fechar safra** → `/aegro-fechamento-safra`
