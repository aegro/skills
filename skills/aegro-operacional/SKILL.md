---
name: aegro-operacional
description: Dominio operacional do Aegro - fazendas, autenticacao, tags e orquestracao entre dominios
version: 0.5.1
---

# Dominio Operacional

Referencia completa do dominio operacional da Fazenda Aegro (`farm::5711512de4b0e15eb04da4d0`, ~67k ha).
Cobre autenticacao, gestao de fazendas, tags, empresas, ordens de compra e a orquestracao de fluxos entre dominios.

## Vocabulario do Dominio

| Termo | Definicao | Exemplo |
|-------|-----------|---------|
| Farm | Propriedade rural vinculada a uma API Key. Cada token da acesso a exatamente uma fazenda | `farm::5711512de4b0e15eb04da4d0` |
| API Key | Token de integracao solicitado via token@aegro.com.br. Identifica fazenda e permissoes | Header `Aegro-Public-API-Key` |
| Tag | Marcador para categorizar recursos (patrimonios, atividades, colheitas, talhoes, etc.) | Tag "Lote Norte" tipo GLEBE |
| Relation Type | Tipo de entidade que a tag categoriza. Define permissao necessaria para criar | `MACHINE`, `VEHICLE`, `GLEBE`, `ACTIVITY`, `HARVEST_TAG`, `BILL`, `PURCHASE` |
| Company | Empresa cadastrada — fornecedor, cliente ou transportadora. Usada em financeiro e compras | Bayer CropScience (PROVIDER) |
| Purchase Order | Ordem de compra vinculada a empresa, com itens, valores e entregas | OC-2026-001 — Defensivos safra 25/26 |
| Element | Item do catalogo (defensivo, fertilizante, semente, servico, produto). Entidade cross-domain | Glifosato 480 SL (DEFENSIVE) |
| Key | Identificador unico no formato `tipo::hexstring` (ex: `farm::5711...`, `tag::abc123`, `company::def456`) | `purchaseOrder::67a1b2c3d4e5f6` |

## Autenticacao e Setup

### Hierarquia de Credenciais (prioridade)

1. **Variavel de ambiente** `AEGRO_FARMS` — JSON map `{"nome_fazenda": "api_key"}` (CI/CD)
2. **Arquivo apontado** por `AEGRO_FARMS_FILE` — caminho para arquivo JSON com mesmo formato
3. **Arquivo local** `~/.config/aegro/credentials.json` — criado por `aegro auth login`

### Arquivos de Estado

| Arquivo | Conteudo | Gerenciado por |
|---------|----------|----------------|
| `~/.config/aegro/credentials.json` | Map nome → API key | `aegro auth login` |
| `~/.config/aegro/state.json` | Fazenda selecionada, timestamp | `aegro farms select` (shadow-ado por `AEGRO_ACTIVE_FARM`) |

### Comandos de Autenticacao

```bash
# Login interativo — solicita nome da fazenda e API key, salva em credentials.json
aegro auth login

# Verificar status da autenticacao e fazenda ativa
aegro auth status

# Remover credenciais locais
aegro auth logout
```

### Selecao de Fazenda Ativa

A fazenda ativa e resolvida nesta ordem de precedencia:

1. **`AEGRO_ACTIVE_FARM`** env var — escopo de processo/sessao. Recomendado para
   orquestracao (ex.: Claude Cowork operando multiplas fazendas em paralelo).
2. **`state.json`** — escrito por `aegro farms select`, global por maquina.

```bash
# Escopo de sessao (Cowork, CI, scripts) — nao contamina outras sessoes:
AEGRO_ACTIVE_FARM="Fazenda Aegro" aegro farms info

# Single-machine / dev — persiste em state.json global:
aegro farms select "Fazenda Aegro"

# Listar fazendas; o campo `source` indica a origem da selecao ativa
# ("env" | "state" | null). Use para validar o setup antes de operar:
aegro farms list

# Detalhes da fazenda ativa (chama a API):
aegro farms info
```

**Multi-fazenda (Claude Cowork):** Em contextos com varias fazendas configuradas
(operador de servicos atendendo varios clientes), sempre prefira
`AEGRO_ACTIVE_FARM` por sessao/projeto. `farms select` grava global e pode
ser sobrescrito por outra sessao em paralelo, contaminando a fazenda ativa.

**Validacao obrigatoria antes de operar:** rode `aegro farms list` e confirme
que a fazenda alvo aparece com `"active": true`. Se o `source` nao bater com
o esperado (env em Cowork, state em dev local), PARE e investigue antes de
qualquer comando de escrita.

**Nota:** Todo comando de dominio exige fazenda ativa. Sem selecao (nem env
var nem state.json), retorna exit code 2 (auth) com mensagem orientando
`AEGRO_ACTIVE_FARM=<nome>` ou `aegro farms select`.

## Formato Global da CLI

### Output

| Formato | Flag | Descricao |
|---------|------|-----------|
| JSON | `--output json` (default) | Saida estruturada para parsing por LLMs e scripts |
| Tabela | `--output table` | Formatado com Rich para leitura humana |
| CSV | `--output csv` | Para export e planilhas |

### Paginacao

- Padrao: **50 itens por pagina**, maximo 100
- Controle via `--page N` (inicia em 1) e `--per-page N`
- Resposta inclui metadata: `totalItems`, `totalPages`, `currentPage`

### Formato de Chaves

Todas as chaves seguem o padrao `tipo::hexstring`:

```
farm::5711512de4b0e15eb04da4d0
tag::67a1b2c3d4e5f67890abcdef
company::5f8e3c1a2b4d6e7890f12345
purchaseOrder::67a1b2c3d4e5f6
element::5a9c2d3e4f5b6a7890cdef12
asset::57d299c3e4b059f24e3f99b0
crop::68dd6719e90f726622b7f549
```

### Exit Codes

| Codigo | Significado | Quando |
|--------|-------------|--------|
| 0 | Sucesso | Operacao concluida |
| 1 | Erro generico | Falha inesperada, timeout, erro de rede |
| 2 | Erro de autenticacao | API key invalida, fazenda nao selecionada |
| 3 | Nao encontrado | Recurso com chave invalida ou inexistente |
| 4 | Erro de validacao | Campos obrigatorios faltando, formato invalido |

### Erros em JSON (stderr)

Erros sao emitidos em stderr no formato JSON, nunca misturados com stdout:

```json
{"error": {"code": "VALIDATION_ERROR", "message": "Campo 'name' e obrigatorio", "details": {"field": "name"}}}
```

### Parametros Repetiveis

Flags que aceitam multiplos valores usam repeticao:

```bash
aegro tags list --relation-types MACHINE --relation-types VEHICLE
aegro elements list --categories DEFENSIVE --categories FERTILIZER
```

## Referencia de Comandos

### farms

| Comando | Descricao | Flags |
|---------|-----------|-------|
| `aegro farms list` | Lista fazendas; cada entrada tem `active` e `source` (`env`/`state`/null) | `--output` |
| `aegro farms select <nome>` | Persiste fazenda ativa em state.json global (warn se `AEGRO_ACTIVE_FARM` estiver setada) | — |
| `aegro farms info` | Detalhes da fazenda ativa via API | `--output` |

```bash
# Preferido em orquestracao (Cowork, CI, scripts) — escopo de sessao:
AEGRO_ACTIVE_FARM="Fazenda Aegro" aegro farms info
# {"key": "farm::5711512de4b0e15eb04da4d0", "name": "Fazenda Aegro", ...}

# Dev single-machine (persiste em state.json):
aegro farms select "Fazenda Aegro"
aegro farms info
```

### auth

| Comando | Descricao | Flags |
|---------|-----------|-------|
| `aegro auth login` | Setup interativo de credenciais | — |
| `aegro auth status` | Verifica autenticacao e fazenda ativa | `--output` |
| `aegro auth logout` | Remove credenciais locais | — |

### tags

| Comando | Descricao | Flags |
|---------|-----------|-------|
| `aegro tags get <tag-key>` | Busca tag por chave | `--output` |
| `aegro tags list` | Lista tags com filtros | `--relation-types`, `--statuses`, `--search-text`, `--page`, `--per-page`, `--output` |
| `aegro tags create` | Cria nova tag | `--name` (obrig.), `--relation-type` (obrig.), `--status` |

```bash
# Criar tag para maquinas
aegro tags create --name "Frota Principal" --relation-type MACHINE
# {"key": "tag::67f1a2b3c4d5e6f7", "name": "Frota Principal", "relationType": "MACHINE", "status": "ACTIVE"}

# Listar tags de atividades
aegro tags list --relation-types ACTIVITY --statuses ACTIVE
```

**Relation Types disponiveis:** `MACHINE`, `VEHICLE`, `WEATHER_STATION`, `IMMOBILIZED`, `PIVOT`, `GARNER`, `HARVEST_TAG`, `HARVEST_IDENTIFIER`, `BILL`, `OBSERVATION`, `SCOUT_METHOD`, `GLEBE`, `ACTIVITY`, `PURCHASE`

### companies

| Comando | Descricao | Flags |
|---------|-----------|-------|
| `aegro companies get <key>` | Busca empresa por chave | `--output` |
| `aegro companies list` | Lista empresas com filtros | `--search-text`, `--fiscal-number-type`, `--page`, `--per-page`, `--output` |
| `aegro companies create` | Cadastra nova empresa | `--name` (obrig.), `--fiscal-number-code` (obrig.), `--fiscal-number-type` (obrig.), `--types`, `--trade-name`, `--legal-name`, `--observations` |

```bash
# Cadastrar fornecedor de insumos
aegro companies create \
  --name "AgroInsumos Sul Ltda" \
  --fiscal-number-code "12.345.678/0001-90" \
  --fiscal-number-type CNPJ \
  --types PROVIDER
# {"key": "company::67f2b3c4d5e6a7b8", "name": "AgroInsumos Sul Ltda", ...}

# Buscar empresa por texto
aegro companies list --search-text "Bayer"
```

**Tipos de empresa:** `PROVIDER` (fornecedor), `CLIENT` (cliente), `TRANSPORTER` (transportadora)

### purchase-orders

| Comando | Descricao | Flags |
|---------|-----------|-------|
| `aegro purchase-orders get <key>` | Busca ordem de compra por chave | `--output` |
| `aegro purchase-orders list` | Lista ordens de compra | `--company-key`, `--start-date`, `--end-date`, `--search-text`, `--delivery-status`, `--tag`, `--page`, `--per-page`, `--output` |
| `aegro purchase-orders create` | Cria ordem de compra | `--order-date` (obrig.), `--currency-code` (obrig.), `--gross-amount` (obrig.), `--items` (obrig. JSON), `--company-key`, `--description`, `--expected-delivery-date`, `--tags` |

```bash
# Criar ordem de compra de defensivos
aegro purchase-orders create \
  --company-key "company::67f2b3c4d5e6a7b8" \
  --order-date "2026-03-13" \
  --currency-code BRL \
  --gross-amount 45000.00 \
  --description "Defensivos safra 25/26 - lote 1" \
  --items '[{"elementKey": "element::5a9c2d3e4f5b6a78", "quantity": 500, "unitPrice": 90.00}]'

# Listar compras de um fornecedor
aegro purchase-orders list --company-key "company::67f2b3c4d5e6a7b8" --start-date 2026-01-01
```

## Orquestracao Entre Dominios

Fluxos operacionais que cruzam multiplos dominios do Aegro. A sequencia correta evita inconsistencias.

### Fluxo 1: Compra de Insumo (Operacional → Estoque → Financeiro)

```
companies create (ou usar existente)
    → purchase-orders create (vincula empresa + itens)
        → stock entry (registra entrada no deposito)
            → financial create-installment (gera parcelas a pagar)
```

```bash
# 1. Garantir fornecedor cadastrado
aegro companies list --search-text "AgroInsumos"
# Se nao existir: aegro companies create ...

# 2. Criar ordem de compra
aegro purchase-orders create \
  --company-key "company::67f2b3c4d5e6a7b8" \
  --order-date "2026-03-13" \
  --currency-code BRL \
  --gross-amount 45000.00 \
  --items '[{"elementKey": "element::5a9c2d3e4f5b6a78", "quantity": 500, "unitPrice": 90.00}]'

# 3. Registrar entrada no estoque
aegro stock entry \
  --element-key "element::5a9c2d3e4f5b6a78" \
  --location-key "stockLocation::abc123" \
  --quantity 500 \
  --date "2026-03-15"

# 4. Criar parcela financeira
aegro financial create-installment \
  --bill-key "bill::xyz789" \
  --bank-account-key "bankAccount::def456" \
  --due-date "2026-04-15" \
  --amount-value 45000.00 \
  --amount-currency BRL
```

### Fluxo 2: Aplicacao de Defensivo (Agronomico → Estoque)

```
activities create-plan (planeja aplicacao com insumos)
    → realizacao via Aegro App (execucao no campo)
        → consumo de estoque automatico (baixa gerada pela realizacao)
```

**Nota:** A realizacao no campo gera baixa automatica de estoque. Se o estoque nao baixou apos realizacao, verificar se a realizacao tem insumos vinculados.

```bash
# 1. Planejar aplicacao
aegro activities create-plan \
  --crop-key "crop::68dd6719e90f726622b7f549" \
  --type APPLICATION \
  --start-date "2026-03-15" \
  --observations "Aplicacao herbicida pre-emergente" \
  --inputs '[{"elementKey": "element::5a9c2d3e4f5b6a78", "amount": {"magnitude": 2.5, "unit": "L/HA"}}]' \
  --dry-run

# 2. Verificar realizacoes (apos execucao no campo)
aegro activities realizations --crop-key "crop::68dd6719e90f726622b7f549"

# 3. Conferir baixa de estoque
aegro stock logs --element-key "element::5a9c2d3e4f5b6a78" --start-date 2026-03-01
```

### Fluxo 3: Colheita (Campo → Financeiro)

```
harvest-logs create (registra romaneio de colheita)
    → financial create-installment (gera recebivel da venda)
```

```bash
# 1. Registrar colheita
aegro harvest-logs create \
  --crop-key "crop::68dd6719e90f726622b7f549" \
  --date "2026-03-10" \
  --gross-weight 32000 \
  --humidity 14.5

# 2. Gerar conta a receber (venda do grao)
aegro financial create-installment \
  --bill-key "bill::venda001" \
  --bank-account-key "bankAccount::def456" \
  --due-date "2026-04-30" \
  --amount-value 192000.00 \
  --amount-currency BRL
```

### Fluxo 4: Manutencao de Patrimonio (Patrimonial → Estoque → Financeiro)

```
maintenances create (registra manutencao com pecas)
    → stock removal automatico (baixa de pecas do deposito)
        → financial create-installment (gera conta a pagar do servico)
```

```bash
# 1. Registrar manutencao com pecas
aegro maintenances create \
  --asset-key "asset::57d299c3e4b059f24e3f99b0" \
  --date "2026-03-12" \
  --stock-location-key "stockLocation::abc123" \
  --hourmeter 1550 \
  --observations "Troca filtros + oleo - revisao 500h" \
  --inputs '[{"elementKey": "element::filtro01", "quantity": 2}]'

# 2. Gerar parcela do servico de manutencao
aegro financial create-installment \
  --bill-key "bill::manut001" \
  --bank-account-key "bankAccount::def456" \
  --due-date "2026-04-15" \
  --amount-value 3500.00 \
  --amount-currency BRL
```

### Fluxo 5: Custeio — Vinculo Elemento x Categoria Financeira

```
elements set-categories (vincula insumo a categoria financeira)
    → custos de atividades aparecem classificados no DRE
```

```bash
# Vincular defensivo a categoria financeira "Defensivos"
aegro elements set-categories \
  --element-key "element::5a9c2d3e4f5b6a78" \
  --expense-category-key "finCategory::desp_defensivos" \
  --revenue-category-key "finCategory::rec_vendas"
```

**Importancia:** Sem esse vinculo, custos de atividades nao aparecem categorizados nos relatorios financeiros (DRE).

## Entidades Cross-Domain

### Companies (Operacional + Financeiro)

A mesma empresa aparece em dois contextos:

| Contexto | Uso | Exemplo |
|----------|-----|---------|
| Operacional | Fornecedor em ordens de compra | `purchase-orders create --company-key ...` |
| Financeiro | Contraparte em contas a pagar/receber | Vinculado via bill ao fornecedor |

**Regra:** Sempre criar a empresa antes de usar em purchase-orders ou financial.

### Elements (Agronomico + Estoque + Financeiro)

Um elemento participa de tres dominios simultaneamente:

| Dominio | Papel | Comando |
|---------|-------|---------|
| Agronomico | Insumo planejado/aplicado em atividades | `activities create-plan --inputs ...` |
| Estoque | Item com posicao e movimentacoes | `stock items --element-key ...` |
| Financeiro | Custo categorizado via set-categories | `elements set-categories --element-key ...` |

**Regra:** Criar o elemento e vincular categorias financeiras antes de usar em atividades e estoque.

## Bugs Conhecidos e Retry

### Resumo de Bugs Ativos

| # | Endpoint | Severidade | Dominio Afetado | Workaround |
|---|----------|------------|-----------------|------------|
| 1 | `glebes/filter` 500 | Alta | Talhoes | Usar `GET /glebes/{key}` individual se chave conhecida |
| 2 | `crop-glebes/filter` 500 | Alta | Safra/Talhoes | Usar `GET /crop-glebes/{key}` individual |
| 3 | `fuel-supplies/filter` 500 | Media | Patrimonial | **Sem workaround** para listagem. GET individual funciona |
| 4 | `maintenances/filter` 500 | Media | Patrimonial | **Sem workaround** para listagem. GET individual funciona |
| 5 | `elements/seeds` POST 500 | Media | Catalogo | Cadastrar sementes manualmente no Aegro App |
| 6 | `weather-logs` POST 500 | Media | Climatico | Registrar dados climaticos manualmente no Aegro App |

### Logica de Retry

- **3 tentativas** com backoff exponencial (1s, 2s, 4s)
- Apenas para erros **retriaveis**: HTTP 500, 502, 503, 504, timeout
- Erros **nao retriaveis**: 400, 401, 403, 404, 422

### Erros Comuns e Diagnostico

| HTTP | Significado | Acao |
|------|-------------|------|
| 500 | Erro interno do servidor | Retry automatico. Se persistir, verificar tabela de bugs conhecidos |
| 422 | Erro de validacao | Verificar campos obrigatorios e formatos. Nao faz retry |
| 404/204 | Recurso nao encontrado | Validar formato da chave (`tipo::hexstring`). Chave pode estar errada |
| 401 | Nao autenticado | Verificar API key com `aegro auth status` |
| 403 | Sem permissao | Token nao tem permissao para a operacao. Solicitar novo token |
| Timeout | Sem resposta em 30s | Retry automatico. API pode estar lenta |

### Dicas Gerais

- **Sempre validar chaves** antes de usar — formato `tipo::hexstring`, sem `/`, `?`, `#` ou espacos
- **Paginacao**: Se resultado vier vazio, verificar se `page` esta dentro de `totalPages`
- **Datas**: Sempre ISO 8601 (`YYYY-MM-DD`). Fuso horario do servidor: America/Sao_Paulo
