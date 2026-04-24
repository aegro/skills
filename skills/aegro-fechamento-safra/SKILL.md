---
name: aegro-fechamento-safra
description: Checklist guiado para encerramento de safra com validacao de dados completos
version: 0.5.0
---

# Fechamento de Safra

## Objetivo

Garantir que todos os dados da safra estejam completos e consistentes antes
do encerramento contabil. Verifica atividades, realizacoes, colheitas,
rateios e descontos, calculando um percentual de completude.

## Quando Usar

- Final do ciclo produtivo (colheita concluida)
- Antes de gerar DRE ou relatorio de custos
- Cliente menciona "fechar safra" ou "encerrar ciclo"
- Auditoria de dados da safra

## Pre-requisitos de Conhecimento

Para detalhes dos comandos e regras de negocio:
- `/aegro-agronomo` -- safras, talhoes, atividades, realizacoes, colheitas, rateios, descontos

## Checklist de Validacao

### 1. Identificar safra a fechar

Listar safras no periodo e confirmar com o usuario qual encerrar.
Guardar `crop_key` da safra selecionada.

### 2. Validar dados gerais da safra

Obter detalhes da safra e verificar:
- Nome e cultura corretos
- Datas de inicio/fim coerentes
- Area total registrada

### 3. Validar talhoes vinculados

Listar talhoes da safra e verificar:
- Todos os talhoes esperados estao presentes
- Areas somam o total da safra
- Nenhum talhao duplicado

### 4. Validar atividades essenciais

Listar atividades da safra e confirmar presenca de:
- SOWING (plantio) -- **obrigatorio**
- APPLICATION (aplicacoes) -- esperado
- FERTILIZATION (adubacao) -- esperado
- HARVEST (colheita) -- **obrigatorio para fechamento**

**Regra:** Atividade sem realizacao = custo nao contabilizado.

### 5. Validar realizacoes

Listar realizacoes da safra e verificar:
- Cada atividade tem pelo menos 1 realizacao
- Realizacoes tem data e quantidade preenchidas
- Insumos consumidos estao registrados

### 6. Validar rateios de custo

Buscar rateios vinculados a safra e verificar:
- Rateios configurados para custos indiretos
- Percentuais somam 100% por grupo
- Criterio de rateio adequado (area, producao, etc)

**Se vazio:** Alertar que custos indiretos nao serao alocados.

### 7. Validar descontos de colheita

Verificar descontos configurados:
- Umidade configurada (base esperada: 13-14%)
- Impureza configurada (base esperada: 1-2%)

**Se vazio:** Alertar que colheitas nao terao descontos aplicados.

### 8. Consolidar checklist

Compilar resultados e apresentar relatorio de fechamento.

## Calculo de Completude

```
Total de atividades: X
Atividades com realizacao: Y
Completude = Y / X * 100%

Meta para fechamento: >= 95%
```

| Completude | Interpretacao |
|------------|---------------|
| 100% | Pronta para fechar |
| 95-99% | Revisar pendencias menores |
| 80-94% | Pendencias significativas - nao fechar |
| < 80% | Safra incompleta - levantar com campo |

## Formato de Resposta

```markdown
## Fechamento de Safra: {{cultura}} {{ciclo}}

### Dados Gerais
| Campo | Valor | Status |
|-------|-------|--------|
| Cultura | Soja | OK |
| Area total | 450 ha | OK |
| Talhoes | 8 | OK |

### Atividades
| Tipo | Planejadas | Realizadas | Status |
|------|------------|------------|--------|
| Plantio | 1 | 1 | OK |
| Aplicacoes | 5 | 5 | OK |
| Colheita | 1 | 0 | PENDENTE |

**Completude:** 90%

### Rateios e Descontos
| Item | Status |
|------|--------|
| Rateio custos fixos | OK (35%) |
| Desconto umidade | OK (14% base) |

### Pendencias para Fechamento
1. Registrar realizacao da colheita
2. Conferir peso liquido nos romaneios
```

## Alertas Criticos

| Situacao | Impacto | Acao |
|----------|---------|------|
| Colheita sem registro | Safra nao pode ser fechada contabilmente | Registrar colheita |
| Atividade sem realizacao | Custo planejado vs realizado diverge | Registrar realizacao |
| Rateio zerado | Custos indiretos nao serao alocados | Configurar rateio |
| Talhao faltando | Area e producao incompletas | Vincular talhao |

## Proximos Workflows

| Situacao | Proximo workflow |
|----------|------------------|
| Divergencia de insumos | `/aegro-reconciliacao-estoque` |
| Calcular margem | `/aegro-analise-rentabilidade` |
| Iniciar proxima safra | `/aegro-visao-geral` |
