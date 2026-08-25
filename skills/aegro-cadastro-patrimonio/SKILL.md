---
name: aegro-cadastro-patrimonio
description: Guia para cadastrar e gerenciar patrimonios, abastecimentos e manutencoes
version: 0.6.0
---

# Cadastro de Patrimonio

## Objetivo

Cadastrar ativos da fazenda (maquinas, veiculos, silos, benfeitorias, pivos,
estacoes meteorologicas) e iniciar o tracking de abastecimentos e manutencoes.

## Quando Usar

- Novo equipamento adquirido (trator, colheitadeira, pickup)
- Cadastrar frota existente no sistema
- Registrar abastecimento de combustivel
- Registrar manutencao preventiva ou corretiva
- Cliente pergunta "como cadastro meu trator?" ou "como registro abastecimento?"

## Pre-requisitos

Carregue este domain skill antes de iniciar:

- **`/aegro-patrimonial`** — vocabulario, modelo de dados, regras de negocio e comandos de patrimonio

Fazenda deve estar selecionada.

## Fluxo de Decisao - Tipo de Ativo

```
Qual tipo de patrimonio?
│
├── Maquina agricola (trator, colheitadeira, pulverizador, plantadeira)
│   └── assets create-machine --machine-type <TIPO>
│       Tipos: TRACTOR, HARVESTER, SPRAYER, PLANTER, FERTILIZER, TILLER, WAGON, OTHER
│       Se implemento acoplado (grade, subsolador): adicionar --is-implement
│
├── Veiculo (caminhao, pickup, utilitario)
│   └── assets create-vehicle
│       Usa hodometro (km), NAO horimetro
│
├── Silo / armazem
│   └── assets create-garner
│
├── Benfeitoria (barracao, oficina, casa)
│   └── assets create-immobilized
│
├── Pivo de irrigacao
│   └── assets create-pivot
│
└── Estacao meteorologica
    └── assets create-weather-station
        ATENCAO: Bug #6 impede criar weather-logs via API
```

## Sequencia: Cadastrar Ativo

### 1. Verificar se o ativo ja existe

```bash
aegro assets list --farm "<fazenda>" --type <TIPO>
```

Confirmar que nao ha duplicata pelo nome/fabricante.

### 2. Criar o patrimonio

```bash
# Exemplo: trator
aegro assets create-machine --farm "<fazenda>" \
  --name "JD 8R 410" \
  --manufacturer "John Deere" \
  --machine-type TRACTOR \
  --manufacture-year 2023 \
  --value 1200000 --currency BRL \
  --hourmeter 1500

# Exemplo: veiculo
aegro assets create-vehicle --farm "<fazenda>" \
  --name "Hilux CD 4x4" \
  --manufacturer "Toyota" \
  --manufacture-year 2024 \
  --value 320000 --currency BRL \
  --odometer 15000
```

### 3. Confirmar cadastro

```bash
aegro assets get --farm "<fazenda>" <asset_key_retornada>
```

**Campos obrigatorios por tipo:**
- MACHINE: `--name`, `--machine-type` (obrigatorio, sem ele da 422)
- VEHICLE: `--name`
- GARNER/IMMOBILIZED/PIVOT/WEATHER_STATION: `--name`

**Campos recomendados:** `--manufacturer`, `--manufacture-year`, `--value`, `--currency`

## Sequencia: Registrar Abastecimento

```bash
# Maquina (horimetro) | Veiculo: trocar --hourmeter por --odometer
aegro fuel-supplies create --farm "<fazenda>" \
  --asset-key <asset_key> --date "2026-03-13" --hourmeter 1550 \
  --stock-location-key <stock_location_key> \
  --inputs '[{"elementKey": "element::combustivel", "quantity": 200}]'
```

Com `stockLocationKey`: baixa de estoque automatica. Sem ele: registro informativo apenas.

## Sequencia: Registrar Manutencao

```bash
# Preventiva com pecas (adicionar --crop-prorate-group-key para ratear na safra)
aegro maintenances create --farm "<fazenda>" \
  --asset-key <asset_key> --date "2026-03-12" --hourmeter 1545 \
  --stock-location-key <stock_location_key> \
  --observations "Revisao 500h" \
  --inputs '[{"elementKey": "element::filtro01", "quantity": 1}]'
```

## Limitacoes Atuais

| Bug | Impacto | Workaround |
|-----|---------|------------|
| **#6** `weather create` → HTTP 500 | Impossivel criar registros meteorologicos | Registrar pelo Aegro App |

**Conferido em producao em 21/08/2026:** as listagens que antes davam 500 voltaram a funcionar — `glebes list`, `crop-glebes list`, `fuel-supplies list` e `maintenances list`, inclusive filtrando por patrimonio e por periodo, e paginando. Os itens de **escrita** (POST) nao foram reconferidos — testar exigiria criar registro em producao.

**Consequencia:** guardar a chave retornada continua sendo bom habito para conferir
o registro logo apos criar, mas a listagem posterior via CLI **funciona** — `fuel-supplies list` e `maintenances list` aceitam `--asset-key` e periodo.

## Formato de Resposta

Apresentar tabela com: Nome, Tipo, Fabricante, Ano, Valor, Chave.
Sugerir proximos passos: primeiro abastecimento, manutencao preventiva.

## Entregue o Link do Patrimonio

Depois de cadastrar, ofereca o link — todos os `create-*` de patrimonio
devolvem `key` e `farmKey`:

```
{host}/farm/{farmId}?assetId={assetId}#farm-assets
```

Abre a ficha do patrimonio (painel, eventos, custos no periodo).

**Abastecimento e manutencao nao tem link direto** — sao eventos de
patrimonio, e o Aegro nao expoe URL para eles. Depois de
`fuel-supplies create` ou `maintenances create`, ofereca o link do
**patrimonio** (aba Eventos) dizendo que e a ficha da maquina, nao o
lancamento.

Regras que nao podem ser puladas (detalhe em `/aegro-operacional`, secao
"Link Direto para a Entidade"): host vem do `--env` da sessao
(`https://app.aegro.com.br` em prod, `https://app.staging.aegro.io` em
staging), a URL usa a chave **sem** o prefixo `tipo::`, e link com aba
invalida **nao da erro** — cai na home da fazenda em silencio. Nunca invente
template por analogia.

## Proximos Workflows

- **Controlar estoque de pecas/combustivel** → `/aegro-reconciliacao-estoque`
- **Ratear manutencao para safra** → `/aegro-analise-rentabilidade`
- **Visao geral da fazenda** → `/aegro-visao-geral`
