---
name: aegro-cadastro-patrimonio
description: Guia para cadastrar e gerenciar patrimonios, abastecimentos e manutencoes
version: 0.5.4
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
  --inputs '[{"elementKey": "element::combustivel", "quantity": {"unit": "L", "magnitude": 200}}]'
```

`--stock-location-key` e **obrigatorio** na criacao, com ou sem `--inputs`: o
servidor recusa o lancamento sem local de estoque (422
`invalid.asset-event.stock-location.key.required`). Descubra os locais com
`aegro stock locations`. Havendo `--inputs`, e desse local que sai a baixa.

## Sequencia: Registrar Manutencao

```bash
# Preventiva com pecas (adicionar --crop-prorate-group-key para ratear na safra)
aegro maintenances create --farm "<fazenda>" \
  --asset-key <asset_key> --date "2026-03-12" --hourmeter 1545 \
  --stock-location-key <stock_location_key> \
  --observations "Revisao 500h" \
  --inputs '[{"elementKey": "element::filtro01", "quantity": {"unit": "un", "magnitude": 1}}]'
```

`--stock-location-key` tambem e obrigatorio aqui — vale para todo evento de
patrimonio (abastecimento e manutencao).

## Limitacoes Atuais

| Bug | Impacto | Workaround |
|-----|---------|------------|
| **#6** `weather create` → HTTP 500 | Impossivel criar registros meteorologicos | Registrar pelo Aegro App |

**Resolvido:** `fuel-supplies list` e `maintenances list` (antigos bugs #3 e #4,
HTTP 500) voltaram a responder 200 — confirmado em staging em 24/07/2026. Pode
listar o historico normalmente.

## Formato de Resposta

Apresentar tabela com: Nome, Tipo, Fabricante, Ano, Valor, Chave.
Sugerir proximos passos: primeiro abastecimento, manutencao preventiva.

## Proximos Workflows

- **Controlar estoque de pecas/combustivel** → `/aegro-reconciliacao-estoque`
- **Ratear manutencao para safra** → `/aegro-analise-rentabilidade`
- **Visao geral da fazenda** → `/aegro-visao-geral`
