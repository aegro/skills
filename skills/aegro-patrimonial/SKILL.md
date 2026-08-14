---
name: aegro-patrimonial
description: Dominio de patrimonio do Aegro - ativos, maquinas, veiculos, abastecimentos e manutencoes
version: 0.6.7
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
- `FUEL_SUPPLY/MAINTENANCE → stockLocationKey`: **obrigatorio na criacao** do evento; e dele que sai a baixa automatica de pecas/combustivel quando ha `inputs`

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

Tanto `fuel-supplies` quanto `maintenances` aceitam `inputs` — lista de insumos
consumidos. `quantity` e um **objeto** com `unit` e `magnitude` (numero solto e
recusado pela CLI):

```json
{
  "inputs": [
    {"elementKey": "element::combustivel01", "quantity": {"unit": "L", "magnitude": 200}},
    {"elementKey": "element::filtro01", "quantity": {"unit": "un", "magnitude": 2}}
  ]
}
```

A baixa de estoque sai do `stockLocationKey` do evento — que e **obrigatorio na
criacao**, tenha `inputs` ou nao (ver anti-padrao 1).

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
| `aegro fuel-supplies list` | Lista abastecimentos | `--asset-key`, `--start-date`, `--end-date`, `--page`, `--output` |
| `aegro fuel-supplies create` | Cria abastecimento | `--asset-key` (obrig.), `--date` (obrig.), `--stock-location-key` (obrig.), `--hourmeter`, `--odometer`, `--observations`, `--inputs` (JSON) |
| `aegro fuel-supplies update <key>` | Atualiza abastecimento | mesmas flags do create |

```bash
# Registrar abastecimento de trator (Diesel S10 - 200L)
aegro fuel-supplies create --farm "Fazenda Aegro" \
  --asset-key "asset::57d299c3e4b059f24e3f99b0" \
  --date "2026-03-13" \
  --hourmeter 1550 \
  --stock-location-key "stockLocation::abc123" \
  --observations "Diesel S10 - 200L - Tanque sede" \
  --inputs '[{"elementKey": "element::combustivel_diesel", "quantity": {"unit": "L", "magnitude": 200}}]'
# {"key": "fuelSupply::67f4d5e6a7b8c9d0", "assetKey": "asset::57d299c3e4b059f24e3f99b0", ...}

# Registrar abastecimento de veiculo (com hodometro)
aegro fuel-supplies create --farm "Fazenda Aegro" \
  --asset-key "asset::veiculo_hilux01" \
  --date "2026-03-13" \
  --odometer 15500 \
  --stock-location-key "stockLocation::abc123" \
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
| `aegro maintenances list` | Lista manutencoes | `--asset-key`, `--start-date`, `--end-date`, `--page`, `--output` |
| `aegro maintenances create` | Cria manutencao | `--asset-key` (obrig.), `--date` (obrig.), `--stock-location-key` (obrig.), `--hourmeter`, `--odometer`, `--crop-prorate-group-key`, `--observations`, `--inputs` (JSON), `--farm-user-key` |
| `aegro maintenances update <key>` | Atualiza manutencao | mesmas flags do create |

```bash
# Registrar manutencao preventiva de trator (troca de filtros + oleo)
aegro maintenances create --farm "Fazenda Aegro" \
  --asset-key "asset::57d299c3e4b059f24e3f99b0" \
  --date "2026-03-12" \
  --hourmeter 1545 \
  --stock-location-key "stockLocation::abc123" \
  --observations "Revisao 500h - Troca filtros oleo/ar/combustivel + oleo motor 15W40" \
  --inputs '[{"elementKey": "element::filtro_oleo01", "quantity": {"unit": "un", "magnitude": 1}}, {"elementKey": "element::filtro_ar01", "quantity": {"unit": "un", "magnitude": 1}}, {"elementKey": "element::oleo_motor01", "quantity": {"unit": "L", "magnitude": 18}}]'
# {"key": "maintenance::67f5e6a7b8c9d0e1", "assetKey": "asset::57d299c3e4b059f24e3f99b0", ...}

# Manutencao corretiva de colheitadeira
aegro maintenances create --farm "Fazenda Aegro" \
  --asset-key "asset::colheitadeira_case01" \
  --date "2026-03-10" \
  --hourmeter 318 \
  --stock-location-key "stockLocation::abc123" \
  --observations "Troca correia do elevador - quebra em operacao" \
  --inputs '[{"elementKey": "element::correia_elevador", "quantity": {"unit": "un", "magnitude": 1}}]'

# Manutencao de veiculo (usa hodometro)
aegro maintenances create --farm "Fazenda Aegro" \
  --asset-key "asset::veiculo_hilux01" \
  --date "2026-03-11" \
  --odometer 15200 \
  --stock-location-key "stockLocation::abc123" \
  --observations "Troca oleo + filtros - revisao 10.000km" \
  --inputs '[{"elementKey": "element::oleo_motor_5w30", "quantity": {"unit": "L", "magnitude": 7}}, {"elementKey": "element::filtro_oleo_hilux", "quantity": {"unit": "un", "magnitude": 1}}]'

# Manutencao com rateio para safra
aegro maintenances create --farm "Fazenda Aegro" \
  --asset-key "asset::57d299c3e4b059f24e3f99b0" \
  --date "2026-03-08" \
  --hourmeter 1540 \
  --stock-location-key "stockLocation::abc123" \
  --crop-prorate-group-key "prorateGroup::safra2526" \
  --observations "Reparo sistema hidraulico - rateado para safra 25/26"

# Buscar manutencao especifica
aegro maintenances get --farm "Fazenda Aegro" "maintenance::67f5e6a7b8c9d0e1"
```

## Bugs e Workarounds

### Bugs #3 e #4 (`fuel-supplies/filter` e `maintenances/filter`, HTTP 500) — NAO REPRODUZEM

**Severidade:** Baixa (rebaixada — ver status)
**Endpoints:** `POST /pub/v1/assets/fuel-supplies/filter` e `POST /pub/v1/assets/maintenances/filter`
**Correlation IDs (ocorrencias originais):** `ca918f1c-3e1d-4f81-a1ca-77d092daa087` (#3), `fcdffc11-3ad3-4e77-83dc-c5141278fef2` (#4)

**Status:** os dois voltaram a responder 200. Historico da revalidacao:

| Quando | O que foi medido |
|---|---|
| 2026-07-24 | `fuel-supplies list` respondeu em staging — foi a listagem que permitiu confirmar um abastecimento gravado apos um 504 |
| 2026-08-10 | ~35 chamadas de `fuel-supplies list` em staging e producao (27 paginas / 1314 registros), com e sem filtro de data |
| 2026-08-14 | **os dois** em producao: `fuel-supplies list` 586 registros / 12 paginas, `maintenances list` 170 registros / 4 paginas |

**Impacto:** nenhum. Use `aegro fuel-supplies list` e `aegro maintenances list`
normalmente — inclusive para conferir historico, sem recorrer ao Aegro App.

**Se um 500 voltar a aparecer:** repita ate 3 tentativas com backoff de 1s/2s/4s
(pode ser intermitente; mesma politica de retry documentada em `aegro-operacional`).
So trate como bloqueio se persistir depois disso, e reporte — seria regressao, nao o
bug antigo.

### Bug #6: `weather-logs` POST retorna HTTP 500

**Severidade:** Media
**Endpoint:** `POST /pub/v1/weather-logs`
**Status:** Aberto — sem previsao de correcao
**Correlation ID:** `d68b29a6-8f78-4448-b8c3-85e5f55b445a`

**Impacto:** Impossivel criar registros meteorologicos via CLI/API. O GET individual funciona, e a estacao meteorologica existe (`asset::57d299c3e4b059f24e3f99b0`).

**Workaround:** Registrar dados climaticos diretamente no Aegro App (interface web).

## Anti-padroes

### 1. Nao crie evento de patrimonio sem local de estoque

`--stock-location-key` e obrigatorio no `create` de abastecimento **e** de
manutencao, com ou sem `--inputs`: o servidor recusa qualquer evento sem local de
estoque (422 `invalid.asset-event.stock-location.key.required`). Nao e "registro
informativo" — e erro.

A CLI barra isso localmente, com **exit 4**, inclusive no `--dry-run` (verificado em
14/08/2026); versoes antigas so falhavam quando havia `--inputs`.

```bash
# ERRADO - vai falhar (exit 4 na CLI, 422 no servidor)
aegro fuel-supplies create --farm "Fazenda Aegro" \
  --asset-key "asset::57d299c3e4b059f24e3f99b0" --date "2026-03-13" --hourmeter 1550

# CORRETO - descubra o local e passe a flag
aegro stock locations --farm "Fazenda Aegro"
aegro fuel-supplies create --farm "Fazenda Aegro" \
  --asset-key "asset::57d299c3e4b059f24e3f99b0" --date "2026-03-13" --hourmeter 1550 \
  --stock-location-key "stockLocation::abc123"
```

No `update` a flag nao e exigida: o PATCH e parcial e o evento herda o local ja
gravado. Passe-a quando estiver trocando os `inputs`, para nao deixar a baixa de
estoque implicita.

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

### 6. Nao passe `quantity` como numero solto em `inputs`

`quantity` e um objeto com `unit` e `magnitude`. Numero solto e recusado pela CLI
antes de chegar na API — `INVALID_INPUTS`, **exit 4** (verificado em 14/08/2026).

```bash
# ERRADO - quantity como numero
aegro maintenances create --farm "Fazenda Aegro" --asset-key "asset::x" --date "2026-03-12" \
  --stock-location-key "stockLocation::abc123" \
  --inputs '[{"elementKey": "element::filtro01", "quantity": 2}]'

# CORRETO - quantity com unidade e magnitude
aegro maintenances create --farm "Fazenda Aegro" --asset-key "asset::x" --date "2026-03-12" \
  --stock-location-key "stockLocation::abc123" \
  --inputs '[{"elementKey": "element::filtro01", "quantity": {"unit": "un", "magnitude": 2}}]'
```

### 7. Nao paralelize chamadas de escrita da CLI

Nao ha bulk-update: operacoes em lote (ex: aplicar rateio a centenas de abastecimentos) exigem uma chamada `update` por registro. Rodar essas chamadas em paralelo causa HTTP 409 "Erro inesperado" mesmo em registros sem relacao entre si — observado em 2026-08-10 (CLI v0.16.0): com 5 chamadas paralelas, 2 de 5 falharam; com 3 paralelas, ~1,4% de falha; sequencial, 0 falhas.

```bash
# ERRADO - paralelismo gera 409 esporadico
cat keys.txt | xargs -P 5 -I {} aegro fuel-supplies update {} --crop-prorate-group-key "..." --execute

# ERRADO tambem - "xargs -P 1" serializa mas nao interrompe o lote: se uma chave falhar,
# xargs segue processando as chaves restantes e o erro se perde no meio de centenas de linhas
cat keys.txt | xargs -P 1 -I {} aegro fuel-supplies update {} --crop-prorate-group-key "..." --execute

# CORRETO - loop sequencial que interrompe o lote no primeiro erro; a chamada isolada de
# cada chave ainda pode repetir ate 3 vezes (esperando 1s e 2s entre elas) se um 409
# ocorrer - repetir nao garante sucesso, entao pare o lote para investigar se o erro
# persistir apos as 3 tentativas
while IFS= read -r key; do
  ok=""
  for delay in 0 1 2; do
    [ "$delay" -gt 0 ] && sleep "$delay"
    if aegro fuel-supplies update "$key" --crop-prorate-group-key "..." --execute; then
      ok=1
      break
    fi
  done
  if [ -z "$ok" ]; then
    echo "Falhou apos 3 tentativas na chave $key - interrompendo o lote" >&2
    exit 1
  fi
done < keys.txt
```

Sempre valide o payload com `--dry-run` em 1 registro antes de rodar o lote com `--execute`.

### 8. Nao junte stdout e stderr ao capturar `--output json`

Em raras situacoes (retry apos erro 5xx), a CLI pode emitir uma linha de warning que, com `2>&1`, se mistura ao JSON e quebra o parse. Redirecione apenas o stdout — mas isso reduz o risco, nao elimina: se o warning sair pelo proprio stdout (nao pelo stderr), o arquivo fica contaminado mesmo sem `2>&1`. Valide sempre o arquivo com um parser JSON antes de consumi-lo; se o parse falhar, descarte a resposta e repita a chamada.

```bash
# ERRADO - warning de retry pode corromper o JSON
aegro fuel-supplies list --farm "Fazenda Aegro" --page 27 --output json > pagina27.json 2>&1

# CORRETO - stdout puro no arquivo, warnings continuam visiveis no terminal;
# valide com o parser JSON que existir na maquina (python3, python, node, jq) - nao
# assuma um. Se a validacao falhar: descarte o arquivo, avise em stderr e pare -
# nao siga com dado corrompido. Limite o retry da chamada a 3 tentativas.
for tentativa in 1 2 3; do
  aegro fuel-supplies list --farm "Fazenda Aegro" --page 27 --output json > pagina27.json
  python3 -c "import json; json.load(open('pagina27.json'))" 2>/dev/null && break
  rm -f pagina27.json
  if [ "$tentativa" -eq 3 ]; then
    echo "pagina27.json invalido apos 3 tentativas - abortando" >&2
    exit 1
  fi
done
```
