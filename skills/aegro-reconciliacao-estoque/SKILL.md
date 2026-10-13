---
name: aegro-reconciliacao-estoque
requires-cli: 0.14.0
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
                  + Entradas: compras e devolucoes de venda, transferencias
                    recebidas (inclui entrega de pedido de compra), entradas
                    manuais, ganhos de inventario
                  - Saidas: consumo em atividades (realizacoes), vendas e
                    devolucoes de compra, transferencias enviadas, saidas
                    manuais, abastecimento e manutencao de maquina, perdas de
                    inventario

DIVERGENCIA = Estoque Atual (sistema) - Estoque Teorico
```

Cada log entra uma vez so, na linha da tabela do passo 4 em que caiu.

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

A saida de `aegro stock logs` e de `aegro stock log <key>` **nao traz tipo de
movimentacao**: `MANUAL_ENTRY`, `MANUAL_REMOVAL`, `TRANSFER` e
`ACTIVITY_CONSUMPTION` nao existem no JSON. Nao achar esses nomes nao quer dizer
que nao houve consumo nem entrada.

**Saldo.** O log **tira** `quantity` do local em `sourceLocationKey` e **poe** no
local em `destinationLocationKey`; lado ausente e fora do estoque. Some por
local, convertendo cada log (`quantity.unit`) para a unidade da posicao em
`stock items`. Destino `company::` e posicao no fornecedor, nao no armazem.
`quantity` 0 nao move saldo — e ajuste de valor (juros ou desconto de parcela,
diferenca de pedido) ou contagem de inventario que bateu: nao conte como compra,
venda nem devolucao.

**Origem.** Leia a tabela de cima para baixo e pare na primeira linha que casar.
Chave que nao se aplica some do JSON (nao vem `null`); "nenhuma das tres" e sem
`activityLogKey`, `billKey` e `companyKey`.

| Chaves no log | O que e | Saldo |
|---|---|---|
| `activityLogKey` | Consumo de realizacao de atividade | sai da origem |
| `billKey`, so destino | Conta: compra ou devolucao de venda | entra no destino |
| `billKey`, so origem | Conta: venda ou devolucao de compra | sai da origem |
| origem e destino | Transferencia; com origem `company::`, em geral entrega de pedido de compra | sai da origem, entra no destino |
| `companyKey` sem `billKey`, so destino `company::` | Pedido de compra (a entrega e outro log, que tira de `company::`) | entra no fornecedor |
| `companyKey` sem `billKey`, so origem | Entrega de venda (romaneio) | sai da origem |
| nenhuma das tres, so destino | Entrada manual (inclusive compra lancada sem conta) ou ganho em contagem de inventario | entra no destino |
| nenhuma das tres, so origem | Saida manual, abastecimento ou manutencao de maquina, perda em contagem de inventario, ou entrega de venda sem comprador | sai da origem |

Log que nao casa com nenhuma linha: aplique so a regra de saldo e mostre o log a
quem opera.

Compra feita por pedido de compra entra pelo pedido e pela entrega. O log com
`billKey` dessa conta so traz o que passou do pedido, ou um ajuste de valor: a
falta dele nao e "entrada nao registrada".

Para separar a ultima linha, case com `aegro fuel-supplies list` e
`aegro maintenances list` do periodo: `stockLocationKey` do evento igual ao
`sourceLocationKey` do log, mesma `occurrenceDate`, insumo em `inputs` e a soma
dos logs igual a quantidade do insumo — evento rateado entre safras vira um log
por safra; tolere diferenca de arredondamento. O que nao casar e saida manual,
perda de inventario ou entrega de venda sem comprador.

`stock logs` so traz movimento com um lado em local de estoque ou fornecedor:
colheita entrando no silo nao aparece. Posicao de `stock items` com `locationKey`
fora de `stockLocation::` e `company::` (silo, contrato de venda) nao tem log
ali; deixe-a fora da comparacao.

Toda listagem aqui devolve 50 por pagina: repita com `--page 2`, `--page 3`...
ate vir uma pagina com menos de 50.

Calcular totais de entrada e saida por local.

### 5. Cruzar com consumo em atividades

Buscar realizacoes no periodo (`aegro activities realizations`, todas as
paginas) e filtrar as que usaram o elemento. Calcular total consumido em
atividades.

Comparar com os logs que tem `activityLogKey`: o valor e a `key` da realizacao
(`activityLog::`). Some os logs por `activityLogKey` antes de comparar — a
realizacao gera um log por insumo aplicado, e pode ter mais de um do mesmo
insumo. O log leva a data de **fim** da realizacao: a que termina depois do
periodo tem o log fora dele.

Realizacao do insumo sem log, depois disso, nao baixou o estoque — em geral foi
lancada sem local de estoque.

### 6. Calcular divergencia

Aplicar a formula de reconciliacao e quantificar a divergencia.

### 7. Investigar causas (se divergencia != 0)

Listar atividades que consomem o insumo (APPLICATION, FERTILIZATION, SOWING).
Verificar:
- Atividade planejada mas sem realizacao
- Realizacao registrada mas sem baixa de estoque (realizacao sem local de
  estoque grava e nao baixa). Em `stock logs`, a baixa de uma realizacao e o
  log com `activityLogKey` igual a chave dela; saida manual vem sem esse campo.
- Saida manual do mesmo insumo e quantidade, em data proxima, de uma realizacao
  que ja tem baixa: o insumo saiu duas vezes. Mostre as duas ao usuario e deixe
  ele decidir o que desfazer — nao exclua a realizacao por conta propria.
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
