---
name: aegro-reconciliacao-estoque
description: >-
  Explica, pela CLI `aegro`, divergencia entre o estoque registrado no Aegro,
  o consumo lancado
  em atividades de campo e os lancamentos financeiros, apontando a causa
  provavel de cada diferenca. Use quando pedirem "o estoque nao bate",
  "sobrou/faltou insumo", "divergencia de estoque", "auditoria de insumos",
  "conferir consumo da lavoura"; EN "stock does not match". NAO use para
  consultar saldo ou movimentar estoque (use /aegro-estoquista) nem para
  conciliar extrato bancario (use /aegro-conciliacao-bancaria).
---

# Reconciliacao de Estoque

## Objetivo

Identificar e explicar divergencias entre o estoque registrado no sistema,
o consumo em atividades de campo e os lancamentos financeiros. Essencial
para auditoria, controle de insumos e fechamento de safra.

## Quando Usar

- Cliente reclama "estoque nao bate"
- Antes de fechamento de safra
- Auditoria periodica de insumos
- Compra registrada mas estoque nao aumentou
- Aplicacao feita mas estoque nao baixou

## Pre-requisitos de Conhecimento

Para detalhes dos comandos e regras de negocio:
- `/aegro-estoquista` -- locais, itens, movimentacoes, entradas, saidas
- `/aegro-agronomo` -- atividades, realizacoes (consumo de insumos)

## Formula de Reconciliacao

```
Estoque Teorico = Estoque Inicial
                  + Entradas (compras, devolucoes)
                  + Transferencias recebidas
                  - Consumo em atividades (realizacoes)
                  - Transferencias enviadas
                  - Saidas manuais (perdas, ajustes)
                  - Abastecimento e manutencao de maquina

DIVERGENCIA = Estoque Atual (sistema) - Estoque Teorico
```

Se divergencia = 0, estoque esta conciliado.
Se divergencia != 0, investigar causas.

## Sequencia de Passos

### 1. Mapear locais de estoque

Listar armazens/depositos e guardar location_keys.

### 2. Identificar insumo alvo

Listar elementos por categoria (DEFENSIVE, FERTILIZER, SEED).
Se usuario especificou insumo, filtrar por nome.
Priorizar insumos criticos (alto valor ou uso frequente).

### 3. Verificar posicao atual

Buscar itens em estoque para o elemento selecionado.
Registrar quantidade atual por local e unidade de medida.

**Sinal de alerta:** Quantidade negativa indica problema de registro.

### 4. Levantar historico de movimentacoes

Buscar os logs do elemento no periodo da safra, todas as paginas:

```bash
aegro stock logs --farm "<fazenda>" --element-key element::<id> \
  --start-date 2025-09-01 --end-date 2026-03-31
```

**O log nao tem campo de tipo.** Nao procure `ACTIVITY_CONSUMPTION`,
`MANUAL_ENTRY`, `MANUAL_REMOVAL` nem `TRANSFER`: esses nomes nao existem na
saida, e nao acha-los nao quer dizer que nao houve consumo. Cada log tira
`quantity` do local em `sourceLocationKey` e poe no local em
`destinationLocationKey`. A origem se le pelas chaves presentes — chave que nao
se aplica some do JSON:

| Chaves no log | O que e | Direcao |
|---|---|---|
| `activityLogKey` | Consumo de realizacao de atividade | Saida |
| `billKey`, so destino | Conta: compra ou devolucao de venda | Entrada |
| `billKey`, so origem | Conta: venda ou devolucao de compra | Saida |
| origem e destino | Transferencia; com origem `company::`, e a entrega de pedido de compra | Sai da origem, entra no destino |
| `companyKey` sem `billKey`, so destino `company::` | Pedido de compra ainda no fornecedor | Nao entra no armazem ate a entrega |
| `companyKey` sem `billKey`, so origem | Entrega de venda (romaneio) | Saida |
| nenhuma das tres, so destino | Entrada manual ou ganho de inventario | Entrada |
| nenhuma das tres, so origem | Saida manual, abastecimento ou manutencao de maquina, ou perda de inventario | Saida |

"Nenhuma das tres" e sem `activityLogKey`, `billKey` e `companyKey`.

Calcular totais de entrada e saida por local, na mesma unidade (`quantity.unit`).

A ultima linha junta origens que a API publica nao separa. Para isolar
abastecimento e manutencao, case com `aegro fuel-supplies list` e
`aegro maintenances list` no mesmo periodo: mesmo `stockLocationKey`,
`occurrenceDate` e insumo em `inputs`. Evento rateado entre safras vira varios
logs, que somam a quantidade do insumo. O que nao casar e saida manual ou perda
de inventario.

### 5. Cruzar com consumo em atividades

Buscar realizacoes no periodo e filtrar as que usaram o elemento.
Calcular total consumido em atividades.
Comparar com os logs que tem `activityLogKey`: o valor e a `key` da realizacao
(`activityLog::`), entao case um a um com `aegro activities realizations`.
Realizacao do insumo sem log correspondente nao baixou o estoque.

### 6. Calcular divergencia

Aplicar a formula de reconciliacao e quantificar a divergencia.

### 7. Investigar causas (se divergencia != 0)

Listar atividades que consomem o insumo (APPLICATION, FERTILIZATION, SOWING).
Verificar:
- Atividade planejada mas sem realizacao
- Realizacao registrada mas sem baixa de estoque
- Quantidade aplicada vs quantidade baixada

## Como Identificar Divergencias

| Divergencia | Significado | Causa mais provavel | Onde investigar |
|-------------|-------------|---------------------|-----------------|
| Atual > Teorico | Estoque "sobrando" | Entrada nao registrada | NFs de compra pendentes |
| Atual < Teorico | Estoque "faltando" | Saida nao registrada | Realizacoes sem baixa |
| Diverge por local | Deslocamento fisico | Transferencia nao feita | Movimentacoes entre locais |
| Quantidade negativa | Erro de registro | Saida antes da entrada | Ordem cronologica dos lancamentos |

**Diagnostico rapido:**
- Se diferenca corresponde a uma realizacao especifica, provavelmente e baixa nao registrada
- Se diferenca corresponde a um valor de NF, provavelmente e entrada nao registrada
- Se diferenca e pequena e difusa, pode ser arredondamento ou perda natural

## Formato de Resposta

```markdown
## Reconciliacao de Estoque: {{nome_insumo}}

### Posicao Atual
| Local | Quantidade | Unidade |
|-------|------------|---------|
| Armazem Central | 150 | L |
| Deposito Campo | 30 | L |
| **Total** | **180 L** | |

### Movimentacoes ({{inicio}} a {{fim}})
| Tipo | Quantidade |
|------|------------|
| Entradas (compras) | +500 L |
| Consumo em aplicacoes | -280 L |
| Ajustes/perdas | -20 L |
| **Saldo movimentado** | **+200 L** |

### Reconciliacao
| Item | Valor |
|------|-------|
| Estoque inicial | 50 L |
| + Movimentacoes | +200 L |
| = **Estoque teorico** | **250 L** |
| Estoque atual | 180 L |
| **DIVERGENCIA** | **-70 L** |

### Causa Provavel
- Aplicacao em 15/03 consumiu 50L sem baixa de estoque

### Acoes Recomendadas
1. Verificar realizacao de 15/03
2. Conferir fisicamente o estoque
3. Registrar ajuste se confirmado
```

## Proximos Workflows

| Situacao | Proximo workflow |
|----------|------------------|
| Corrigir lancamentos financeiros | `/aegro-lancamento-financeiro` |
| Verificar aplicacoes | `/aegro-monitoramento-pragas` |
| Visao geral da fazenda | `/aegro-visao-geral` |
| Fechar safra | `/aegro-fechamento-safra` |
