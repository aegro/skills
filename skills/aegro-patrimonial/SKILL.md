---
name: aegro-patrimonial
description: Dominio de patrimonio do Aegro - ativos, maquinas, veiculos, abastecimentos e manutencoes
version: 0.6.4
---

# Dominio Patrimonial

Referencia completa do dominio de patrimonio da Fazenda Aegro (`farm::5711512de4b0e15eb04da4d0`, ~67k ha).
Cobre ativos (maquinas, veiculos, silos, benfeitorias, pivos, estacoes meteorologicas), abastecimentos de combustivel e manutencoes.

## Vocabulario

| Termo | Definicao | Formato da Chave |
|-------|-----------|------------------|
| Asset (Patrimonio) | Bem da fazenda: maquina, veiculo, silo, benfeitoria, pivo ou estacao meteorologica | `asset::hexstring` |
| Fuel Supply (Abastecimento) | Evento de abastecimento de combustivel vinculado a um patrimonio | `fuelSupply::hexstring` |
| Maintenance (Manutencao) | Evento de manutencao vinculado a um patrimonio, pode consumir pecas do estoque | `maintenance::hexstring` |
| Horimetro | Contador de horas de operacao. Usado em MACHINE e PIVOT | Valor numerico (ex: 1550.5) |
| Hodometro (Odometro) | Contador de quilometros rodados. Usado em VEHICLE | Valor em km (ex: 85000) |
| Implemento | Equipamento acoplado a maquina (isImplement: true). Nao tem horimetro proprio | Flag booleana no asset |
| Stock Location | Local de estoque de onde saem pecas/combustivel para eventos | `stockLocation::hexstring` |

### Tipos de Patrimonio (type)

| Tipo | Descricao | Endpoint de Criacao | Medidor |
|------|-----------|--------------------|---------|
| `MACHINE` | Maquinas agricolas (tratores, colheitadeiras, pulverizadores, plantadeiras) | `assets create-machine` | Horimetro |
| `VEHICLE` | Veiculos (caminhoes, pickups, utilitarios) | `assets create-vehicle` | Hodometro (km) |
| `GARNER` | Silos e armazens de graos | `assets create-garner` | Horimetro |
| `IMMOBILIZED` | Benfeitorias (barracoes, oficinas, casas) | `assets create-immobilized` | — (usa vida util: `--life-span`) |
| `PIVOT` | Pivos de irrigacao | `assets create-pivot` | Horimetro |
| `WEATHER_STATION` | Estacoes meteorologicas | `assets create-weather-station` | — |

### Tipos de Maquina (machineType) — somente para type MACHINE

| Tipo | Descricao |
|------|-----------|
| `TRACTOR` | Trator |
| `HARVESTER` | Colheitadeira |
| `SPRAYER` | Pulverizador |
| `PLANTER` | Plantadeira |
| `FERTILIZER` | Adubadora |
| `TILLER` | Implemento de preparo de solo |
| `WAGON` | Vagao / transbordo |
| `OTHER` | Outros |

## Modelo de Dados

```
FARM (farm::5711512de4b0e15eb04da4d0)
  │
  ├── ASSET (type: MACHINE)
  │     ├── machineType: TRACTOR, HARVESTER, SPRAYER, ...
  │     ├── currentHourmeter: 1550
  │     ├── isImplement: false
  │     ├── value: {currencyCode: "BRL", amount: 1200000}
  │     │
  │     ├── FUEL_SUPPLY (fuelSupply::...)
  │     │     ├── assetKey → referencia ao patrimonio
  │     │     ├── occurrenceDate: "2026-03-13"
  │     │     ├── hourmeterAtOccurrence: 1550
  │     │     ├── stockLocationKey → deposito de combustivel
  │     │     └── inputs: [{elementKey, quantity}]
  │     │
  │     └── MAINTENANCE (maintenance::...)
  │           ├── assetKey → referencia ao patrimonio
  │           ├── occurrenceDate: "2026-03-12"
  │           ├── hourmeterAtOccurrence: 1545
  │           ├── stockLocationKey → deposito de pecas
  │           └── inputs: [{elementKey, quantity}]
  │
  ├── ASSET (type: VEHICLE)
  │     ├── currentOdometer: 85000 (km)
  │     └── eventos usam odometerAtOccurrenceInKilometers
  │
  ├── ASSET (type: GARNER)
  │     └── Silo — sem eventos de combustivel tipicos
  │
  ├── ASSET (type: IMMOBILIZED)
  │     └── Benfeitoria — barracoes, oficinas
  │
  ├── ASSET (type: PIVOT)
  │     ├── currentHourmeter
  │     └── eventos de manutencao com horimetro
  │
  └── ASSET (type: WEATHER_STATION)
        └── WEATHER_LOG (registro climatico)
              ├── weatherStationKey → referencia a estacao
              ├── date: "2026-03-13"
              └── precipitation: {magnitude: 15.5, unit: "mm"}
```

**Relacoes importantes:**
- `ASSET → FUEL_SUPPLY`: Um patrimonio tem N abastecimentos
- `ASSET → MAINTENANCE`: Um patrimonio tem N manutencoes
- `ASSET (WEATHER_STATION) → WEATHER_LOG`: Estacao tem N registros climaticos
- `FUEL_SUPPLY/MAINTENANCE → stockLocationKey`: Evento pode referenciar local de estoque para baixa automatica de pecas/combustivel

## Regras de Negocio

### 1. Seis endpoints de criacao especificos

Cada tipo de patrimonio tem seu endpoint dedicado. **Nao existe** um endpoint generico `assets create`.

| Tipo | Comando CLI | Campos Especificos |
|------|-------------|-------------------|
| MACHINE | `assets create-machine` | `--machine-type` (obrig.), `--hourmeter`, `--is-implement` |
| VEHICLE | `assets create-vehicle` | `--odometer` (km) |
| GARNER | `assets create-garner` | `--hourmeter` |
| IMMOBILIZED | `assets create-immobilized` | — (benfeitoria nao tem medidor; use `--life-span`/`--life-span-unit`) |
| PIVOT | `assets create-pivot` | `--hourmeter` |
| WEATHER_STATION | `assets create-weather-station` | `--hourmeter` |

### 2. Implementos (isImplement)

Maquinas com `isImplement: true` sao equipamentos acoplados (grades, subsoladores, carretas). Nao possuem horimetro proprio — usam o horimetro da maquina tratora.

### 3. Valor do patrimonio (value)

O campo `value` e um objeto aninhado `MoneyPublicResource`:

```json
{"currencyCode": "BRL", "amount": 1200000.00}
```

Na CLI, passado como flags separadas:
```bash
--value 1200000 --currency BRL
```

### 4. Horimetro no abastecimento

O campo `hourmeterAtOccurrence` no abastecimento permite calcular consumo de combustivel em L/h:

```
Consumo (L/h) = Litros abastecidos / (Horimetro atual - Horimetro anterior)
```

**Exemplo:** Se abasteceu 200L no horimetro 1550 e o anterior foi 1500:
```
200L / (1550 - 1500) = 4.0 L/h
```

### 5. Inputs em eventos (abastecimento e manutencao)

Tanto `fuel-supplies` quanto `maintenances` aceitam `inputs` — lista de insumos consumidos:

```json
{
  "inputs": [
    {"elementKey": "element::combustivel01", "quantity": 200},
    {"elementKey": "element::filtro01", "quantity": 2}
  ]
}
```

Se `stockLocationKey` estiver preenchido, a baixa de estoque e feita automaticamente no local indicado.

### 6. Hodometro vs Horimetro em eventos

| Tipo do Asset | Campo no evento | Unidade |
|---------------|----------------|---------|
| MACHINE | `hourmeterAtOccurrence` | Horas |
| PIVOT | `hourmeterAtOccurrence` | Horas |
| VEHICLE | `odometerAtOccurrenceInKilometers` | Km |
| GARNER | `hourmeterAtOccurrence` | Horas |
| IMMOBILIZED | — (benfeitoria nao tem medidor) | — |

## Referencia de Comandos

### assets

| Comando | Descricao | Flags Principais |
|---------|-----------|-----------------|
| `aegro assets get <key>` | Busca patrimonio por chave | `--output` |
| `aegro assets list` | Lista patrimonios com filtros | `--type`, `--machine-type`, `--page`, `--output` |
| `aegro assets create-machine` | Cria maquina | `--name` (obrig.), `--machine-type` (obrig.), `--manufacturer`, `--manufacture-year`, `--value`, `--currency`, `--hourmeter`, `--is-implement`, `--tag-or-model`, `--observations` |
| `aegro assets create-vehicle` | Cria veiculo | `--name` (obrig.), `--manufacturer`, `--manufacture-year`, `--value`, `--currency`, `--odometer`, `--tag-or-model`, `--observations` |
| `aegro assets create-garner` | Cria silo | `--name` (obrig.), `--manufacturer`, `--manufacture-year`, `--value`, `--currency`, `--hourmeter`, `--observations` |
| `aegro assets create-immobilized` | Cria benfeitoria | `--name` (obrig.), `--manufacturer`, `--manufacture-year`, `--value`, `--currency`, `--acquisition-date`, `--life-span`, `--life-span-unit`, `--observations` |
| `aegro assets create-pivot` | Cria pivo de irrigacao | `--name` (obrig.), `--manufacturer`, `--manufacture-year`, `--value`, `--currency`, `--hourmeter`, `--observations` |
| `aegro assets create-weather-station` | Cria estacao meteorologica | `--name` (obrig.), `--manufacturer`, `--manufacture-year`, `--value`, `--currency`, `--observations` |

#### Exemplos de criacao de patrimonios

```bash
# Criar trator John Deere
aegro assets create-machine --farm "Fazenda Aegro" \
  --name "JD 8R 410" \
  --manufacturer "John Deere" \
  --machine-type TRACTOR \
  --manufacture-year 2023 \
  --value 1200000 \
  --currency BRL \
  --hourmeter 1500
# {"key": "asset::67f3c4d5e6a7b8c9", "name": "JD 8R 410", "type": "MACHINE", "machineType": "TRACTOR", ...}

# Criar colheitadeira
aegro assets create-machine --farm "Fazenda Aegro" \
  --name "Case IH 8250" \
  --manufacturer "Case IH" \
  --machine-type HARVESTER \
  --manufacture-year 2024 \
  --value 2800000 \
  --currency BRL \
  --hourmeter 320

# Criar pulverizador autopropelido
aegro assets create-machine --farm "Fazenda Aegro" \
  --name "Jacto Uniport 4530" \
  --manufacturer "Jacto" \
  --machine-type SPRAYER \
  --manufacture-year 2022 \
  --value 1600000 \
  --currency BRL \
  --hourmeter 2100

# Criar implemento (grade aradora)
aegro assets create-machine --farm "Fazenda Aegro" \
  --name "Grade Aradora 32 discos" \
  --manufacturer "Baldan" \
  --machine-type TILLER \
  --manufacture-year 2021 \
  --value 85000 \
  --currency BRL \
  --is-implement

# Criar veiculo (pickup)
aegro assets create-vehicle --farm "Fazenda Aegro" \
  --name "Hilux CD 4x4 SRV" \
  --manufacturer "Toyota" \
  --manufacture-year 2024 \
  --value 320000 \
  --currency BRL \
  --odometer 15000

# Criar silo
aegro assets create-garner --farm "Fazenda Aegro" \
  --name "Silo Metalico 3000t" \
  --manufacturer "Kepler Weber" \
  --manufacture-year 2020 \
  --value 450000 \
  --currency BRL

# Criar benfeitoria (sem medidor: usa aquisicao + vida util)
aegro assets create-immobilized --farm "Fazenda Aegro" \
  --name "Barracao de Maquinas" \
  --manufacture-year 2018 \
  --value 280000 \
  --currency BRL \
  --acquisition-date "2018-06-01" \
  --life-span 219000 \
  --life-span-unit h   # ~25 anos; default da unidade e 'h' para nao-veiculo

# Criar pivo de irrigacao
aegro assets create-pivot --farm "Fazenda Aegro" \
  --name "Pivo Central Talhao 5" \
  --manufacturer "Valley" \
  --manufacture-year 2022 \
  --value 650000 \
  --currency BRL \
  --hourmeter 4200

# Criar estacao meteorologica
aegro assets create-weather-station --farm "Fazenda Aegro" \
  --name "Estacao Sede" \
  --manufacturer "Davis Instruments" \
  --manufacture-year 2023 \
  --value 12000 \
  --currency BRL

# Listar apenas maquinas do tipo trator
aegro assets list --farm "Fazenda Aegro" --type MACHINE --machine-type TRACTOR

# Listar todos os veiculos
aegro assets list --farm "Fazenda Aegro" --type VEHICLE
```

### fuel-supplies

| Comando | Descricao | Flags Principais |
|---------|-----------|-----------------|
| `aegro fuel-supplies get <key>` | Busca abastecimento por chave | `--output` |
| `aegro fuel-supplies list` | Lista abastecimentos (Bug #3 nao reproduz desde 2026-08-10 — usar normalmente) | `--asset-key`, `--start-date`, `--end-date`, `--page`, `--output` |
| `aegro fuel-supplies create` | Cria abastecimento | `--asset-key` (obrig.), `--date` (obrig.), `--hourmeter`, `--odometer`, `--stock-location-key`, `--observations`, `--inputs` (JSON) |
| `aegro fuel-supplies update <key>` | Atualiza abastecimento | mesmas flags do create |

```bash
# Registrar abastecimento de trator (Diesel S10 - 200L)
aegro fuel-supplies create --farm "Fazenda Aegro" \
  --asset-key "asset::57d299c3e4b059f24e3f99b0" \
  --date "2026-03-13" \
  --hourmeter 1550 \
  --stock-location-key "stockLocation::abc123" \
  --observations "Diesel S10 - 200L - Tanque sede" \
  --inputs '[{"elementKey": "element::combustivel_diesel", "quantity": 200}]'
# {"key": "fuelSupply::67f4d5e6a7b8c9d0", "assetKey": "asset::57d299c3e4b059f24e3f99b0", ...}

# Registrar abastecimento de veiculo (com hodometro)
aegro fuel-supplies create --farm "Fazenda Aegro" \
  --asset-key "asset::veiculo_hilux01" \
  --date "2026-03-13" \
  --odometer 15500 \
  --observations "Diesel S10 - 80L - Posto externo"

# Buscar abastecimento especifico
aegro fuel-supplies get --farm "Fazenda Aegro" "fuelSupply::67f4d5e6a7b8c9d0"

# Atualizar observacao de abastecimento
aegro fuel-supplies update --farm "Fazenda Aegro" "fuelSupply::67f4d5e6a7b8c9d0" \
  --asset-key "asset::57d299c3e4b059f24e3f99b0" \
  --date "2026-03-13" \
  --hourmeter 1550 \
  --observations "Diesel S10 - 200L - Tanque sede - Corrigido"
```

### maintenances

| Comando | Descricao | Flags Principais |
|---------|-----------|-----------------|
| `aegro maintenances get <key>` | Busca manutencao por chave | `--output` |
| `aegro maintenances list` | Lista manutencoes (Bug #4 - tentar primeiro; ver Bugs e Workarounds) | `--asset-key`, `--start-date`, `--end-date`, `--page`, `--output` |
| `aegro maintenances create` | Cria manutencao | `--asset-key` (obrig.), `--date` (obrig.), `--hourmeter`, `--odometer`, `--stock-location-key`, `--crop-prorate-group-key`, `--observations`, `--inputs` (JSON), `--farm-user-key` |
| `aegro maintenances update <key>` | Atualiza manutencao | mesmas flags do create |

```bash
# Registrar manutencao preventiva de trator (troca de filtros + oleo)
aegro maintenances create --farm "Fazenda Aegro" \
  --asset-key "asset::57d299c3e4b059f24e3f99b0" \
  --date "2026-03-12" \
  --hourmeter 1545 \
  --stock-location-key "stockLocation::abc123" \
  --observations "Revisao 500h - Troca filtros oleo/ar/combustivel + oleo motor 15W40" \
  --inputs '[{"elementKey": "element::filtro_oleo01", "quantity": 1}, {"elementKey": "element::filtro_ar01", "quantity": 1}, {"elementKey": "element::oleo_motor01", "quantity": 18}]'
# {"key": "maintenance::67f5e6a7b8c9d0e1", "assetKey": "asset::57d299c3e4b059f24e3f99b0", ...}

# Manutencao corretiva de colheitadeira
aegro maintenances create --farm "Fazenda Aegro" \
  --asset-key "asset::colheitadeira_case01" \
  --date "2026-03-10" \
  --hourmeter 318 \
  --observations "Troca correia do elevador - quebra em operacao" \
  --inputs '[{"elementKey": "element::correia_elevador", "quantity": 1}]'

# Manutencao de veiculo (usa hodometro)
aegro maintenances create --farm "Fazenda Aegro" \
  --asset-key "asset::veiculo_hilux01" \
  --date "2026-03-11" \
  --odometer 15200 \
  --observations "Troca oleo + filtros - revisao 10.000km" \
  --inputs '[{"elementKey": "element::oleo_motor_5w30", "quantity": 7}, {"elementKey": "element::filtro_oleo_hilux", "quantity": 1}]'

# Manutencao com rateio para safra
aegro maintenances create --farm "Fazenda Aegro" \
  --asset-key "asset::57d299c3e4b059f24e3f99b0" \
  --date "2026-03-08" \
  --hourmeter 1540 \
  --crop-prorate-group-key "prorateGroup::safra2526" \
  --observations "Reparo sistema hidraulico - rateado para safra 25/26"

# Buscar manutencao especifica
aegro maintenances get --farm "Fazenda Aegro" "maintenance::67f5e6a7b8c9d0e1"
```

## Bugs e Workarounds

### Bug #3: `fuel-supplies/filter` retorna HTTP 500 (NAO REPRODUZ desde 2026-08-10)

**Severidade:** Baixa (rebaixada — ver status)
**Endpoint:** `POST /pub/v1/assets/fuel-supplies/filter`
**Status:** Nao reproduz — em revalidacao pelo time de API. Em 2026-08-10 (CLI v0.16.0), ~35 chamadas de `fuel-supplies list` funcionaram em staging e producao (27 paginas / 1314 registros em producao), com e sem filtros de data. Pode ser intermitente ou ja ter sido corrigido.
**Correlation ID (ocorrencia original):** `ca918f1c-3e1d-4f81-a1ca-77d092daa087`

**Impacto:** Nenhum confirmado atualmente. Se o erro 500 voltar a ocorrer, tente novamente antes de assumir bloqueio.

**O que fazer:** Use `aegro fuel-supplies list` normalmente. Se falhar com 500, repita a chamada (pode ser intermitente); so recorra ao Aegro App se o erro persistir apos algumas tentativas.

### Bug #4: `maintenances/filter` retorna HTTP 500

**Severidade:** Media
**Endpoint:** `POST /pub/v1/assets/maintenances/filter`
**Status:** Aberto — sem previsao de correcao
**Correlation ID:** `fcdffc11-3ad3-4e77-83dc-c5141278fef2`

**Impacto:** O comando `aegro maintenances list` retornava erro 500 na ultima ocorrencia registrada (nao retestado desde entao).

**O que funciona:**
- `aegro maintenances get <key>` — busca individual funciona
- `aegro maintenances create` — criacao funciona
- `aegro maintenances update <key>` — atualizacao funciona

**Workaround:** Tente `aegro maintenances list` primeiro — o endpoint irmao (`fuel-supplies/filter`, Bug #3) parou de reproduzir em 2026-08-10, e este pode ter sido corrigido junto (nao retestado ainda). Se falhar com 500 persistente, use o Aegro App para consultar historico e `maintenances get` com a chave conhecida para registros individuais.

### Bug #6: `weather-logs` POST retorna HTTP 500

**Severidade:** Media
**Endpoint:** `POST /pub/v1/weather-logs`
**Status:** Aberto — sem previsao de correcao
**Correlation ID:** `d68b29a6-8f78-4448-b8c3-85e5f55b445a`

**Impacto:** Impossivel criar registros meteorologicos via CLI/API. O GET individual funciona, e a estacao meteorologica existe (`asset::57d299c3e4b059f24e3f99b0`).

**Workaround:** Registrar dados climaticos diretamente no Aegro App (interface web).

## Anti-padroes

### 1. Nao assuma bloqueio permanente em fuel-supplies list / maintenances list

Os endpoints de listagem ja retornaram HTTP 500 persistente (Bugs #3 e #4), mas o Bug #3 nao reproduz desde 2026-08-10. Tente a listagem normalmente; se falhar com 500, repita antes de assumir bloqueio total.

```bash
# Tente primeiro - funcionava em 2026-08-10 (CLI v0.16.0)
aegro fuel-supplies list --farm "Fazenda Aegro" --asset-key "asset::57d299c3e4b059f24e3f99b0"

# Fallback se o 500 persistir apos algumas tentativas - GET individual com chave conhecida
aegro fuel-supplies get --farm "Fazenda Aegro" "fuelSupply::67f4d5e6a7b8c9d0"
```

### 2. Nao use horimetro em veiculos

Veiculos (`type: VEHICLE`) usam **hodometro** (`odometerAtOccurrenceInKilometers`), nao horimetro. Passar `hourmeterAtOccurrence` em eventos de veiculo sera ignorado ou causara inconsistencia.

```bash
# ERRADO - veiculo nao usa horimetro
aegro fuel-supplies create --farm "Fazenda Aegro" --asset-key "asset::veiculo01" --hourmeter 1500 ...

# CORRETO - veiculo usa hodometro (km)
aegro fuel-supplies create --farm "Fazenda Aegro" --asset-key "asset::veiculo01" --odometer 85000 ...
```

### 3. Nao esqueca o fabricante (manufacturer)

Embora `manufacturer` nao seja tecnicamente obrigatorio na API, e **fortemente recomendado** para identificacao e relatorios. Patrimonios sem fabricante dificultam busca e gestao.

```bash
# EVITAR - sem fabricante dificulta identificacao
aegro assets create-machine --farm "Fazenda Aegro" --name "Trator 180cv" --machine-type TRACTOR

# MELHOR - com fabricante e modelo identificavel
aegro assets create-machine --farm "Fazenda Aegro" \
  --name "JD 8R 410" \
  --manufacturer "John Deere" \
  --machine-type TRACTOR
```

### 4. Nao crie estacao meteorologica esperando registrar dados via API

O Bug #6 bloqueia criacao de `weather-logs` via API. Se criar estacao meteorologica via CLI, os registros climaticos precisarao ser inseridos pelo Aegro App.

### 5. Nao esqueca o tipo de maquina (machineType) para MACHINE

O campo `machineType` e **obrigatorio** para patrimonios tipo `MACHINE`. Sem ele, a criacao falha com HTTP 422.

```bash
# ERRADO - falta machineType
aegro assets create-machine --farm "Fazenda Aegro" --name "Trator" --manufacturer "John Deere"
# Erro 422: machineType is required

# CORRETO
aegro assets create-machine --farm "Fazenda Aegro" --name "Trator" --manufacturer "John Deere" --machine-type TRACTOR
```

### 6. Nao misture inputs sem stockLocationKey

Se passar `inputs` em um evento de abastecimento ou manutencao, considere tambem passar `stockLocationKey`. Sem ele, os insumos sao registrados no evento mas **nao geram baixa automatica de estoque**.

```bash
# Inputs sem stockLocationKey = registro informativo apenas, sem baixa de estoque
aegro maintenances create --farm "Fazenda Aegro" --asset-key "asset::x" --date "2026-03-12" \
  --inputs '[{"elementKey": "element::filtro01", "quantity": 2}]'

# Inputs com stockLocationKey = baixa automatica do estoque no local indicado
aegro maintenances create --farm "Fazenda Aegro" --asset-key "asset::x" --date "2026-03-12" \
  --stock-location-key "stockLocation::abc123" \
  --inputs '[{"elementKey": "element::filtro01", "quantity": 2}]'
```

### 7. Nao paralelize chamadas de escrita da CLI

Nao ha bulk-update: operacoes em lote (ex: aplicar rateio a centenas de abastecimentos) exigem uma chamada `update` por registro. Rodar essas chamadas em paralelo causa HTTP 409 "Erro inesperado" mesmo em registros sem relacao entre si — observado em 2026-08-10 (CLI v0.16.0): com 5 chamadas paralelas, 2 de 5 falharam; com 3 paralelas, ~1,4% de falha; sequencial, 0 falhas.

```bash
# ERRADO - paralelismo gera 409 esporadico
cat keys.txt | xargs -P 5 -I {} aegro fuel-supplies update {} --crop-prorate-group-key "..." --execute

# CORRETO - sequencial; se um 409 ocorrer mesmo assim, repetir a chamada isolada resolve
cat keys.txt | xargs -P 1 -I {} aegro fuel-supplies update {} --crop-prorate-group-key "..." --execute
```

Sempre valide o payload com `--dry-run` em 1 registro antes de rodar o lote com `--execute`.

### 8. Nao junte stdout e stderr ao capturar `--output json`

Em raras situacoes (retry apos erro 5xx), a CLI pode emitir uma linha de warning que, com `2>&1`, se mistura ao JSON e quebra o parse. Redirecione apenas o stdout.

```bash
# ERRADO - warning de retry pode corromper o JSON
aegro fuel-supplies list --farm "Fazenda Aegro" --page 27 --output json > pagina27.json 2>&1

# CORRETO - stdout puro no arquivo, warnings continuam visiveis no terminal
aegro fuel-supplies list --farm "Fazenda Aegro" --page 27 --output json > pagina27.json
```
