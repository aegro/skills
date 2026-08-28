---
name: aegro-patrimonial
requires-cli: 0.21.0
description: >-
  Dominio de patrimonio do Aegro pela CLI — maquinas, veiculos, silos,
  benfeitorias, pivos e estacoes, mais abastecimentos de combustivel e
  manutencoes, com apropriacao de custo por safra e por subconjunto de
  talhoes. Use quando pedirem "abastecimento", "horimetro", "manutencao da
  maquina", "consumo de diesel", "custo da frota"; EN "fuel supply", "machine
  maintenance". NAO use para cadastrar o ativo pela primeira vez (use
  /aegro-cadastro-patrimonio) nem para importar a frota em lote (use
  /aegro-importacao-patrimonio).
---

# Dominio Patrimonial

Referencia completa do dominio de patrimonio da Fazenda Aegro (`farm::5711512de4b0e15eb04da4d0`, ~67k ha).
Cobre ativos (maquinas, veiculos, silos, benfeitorias, pivos, estacoes meteorologicas), abastecimentos de combustivel e manutencoes.

## Fazenda explicita em toda escrita

Diga a fazenda em **cada comando** com `--farm "<Fazenda|farm::key>"`. Nao confie
no `farms select`: o estado e global por maquina, e uma sessao paralela troca o
alvo da outra sem avisar.

Em 11/08/2026, em producao, a entrega de dois pedidos de compra foi gravada na
fazenda errada exatamente assim. Nada acusou o erro: o pedido apareceu 100%
entregue, o insumo nao entrou no estoque de quem comprou, o saldo ficou negativo
na baixa seguinte e duas manutencoes sairam custeadas em R$ 0,00.

Em sessao de agente, ligue tambem `AEGRO_SAFE_MODE=1`: alem de exigir
`--execute`, ele recusa escrita cuja fazenda nao veio de `--farm`
(`IMPLICIT_FARM_BLOCKED`, exit 4). No envelope do `--dry-run`, confira `farm` e
`farmSource: "flag"` antes de aprovar.

## Vocabulario

| Termo | Definicao | Formato da Chave |
|-------|-----------|------------------|
| Asset (Patrimonio) | Bem da fazenda: maquina, veiculo, silo, benfeitoria, pivo ou estacao meteorologica | `asset::hexstring` |
| Fuel Supply (Abastecimento) | Evento de abastecimento de combustivel vinculado a um patrimonio | `assetEvent::hexstring` |
| Maintenance (Manutencao) | Evento de manutencao vinculado a um patrimonio, pode consumir pecas do estoque | `assetEvent::hexstring` |
| Horimetro | Contador de horas de operacao. Usado em MACHINE e PIVOT | Valor numerico (ex: 1550.5) |
| Hodometro (Odometro) | Contador de quilometros rodados. Usado em VEHICLE | Valor em km (ex: 85000) |
| Implemento | Equipamento acoplado a maquina (isImplement: true). Nao tem horimetro proprio | Flag booleana no asset |
| Stock Location | Local de estoque de onde saem pecas/combustivel para eventos | `stockLocation::hexstring` |
| Talhao (Glebe) | Area fisica da fazenda. Usado para restringir a apropriacao de custo | `glebe::hexstring` |
| Talhao da safra (CropGlebe) | Vinculo entre um talhao e uma safra, com a area plantada | `cropGlebe::hexstring` |
| Agrupador (tag do talhao) | Rotulo que agrupa talhoes (ex: "Estancia"). Na tela aparece como "Agrupador" | Texto livre no talhao |
| Grupo de rateio | Grupo de safras salvo, reutilizavel entre lancamentos. **Limitado por cota de plano** | `cropProrateGroup::hexstring` |

> **Abastecimento e manutencao sao o mesmo objeto no backend** (`AssetEvent`), por isso
> a chave dos dois e `assetEvent::...` — nao existe `fuelSupply::` nem `maintenance::`.
> O comando (`fuel-supplies` ou `maintenances`) e que diz o tipo do evento.

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
  │     ├── FUEL_SUPPLY (assetEvent::...)
  │     │     ├── assetKey → referencia ao patrimonio
  │     │     ├── occurrenceDate: "2026-03-13"
  │     │     ├── hourmeterAtOccurrence: 1550
  │     │     ├── stockLocationKey → deposito de combustivel
  │     │     ├── inputs: [{elementKey, quantity}]
  │     │     └── cropKeys: [crop::...]  → apropriacao do custo (ver regra 7)
  │     │           └── talhoes escolhidos → restringe o custo a parte da safra
  │     │
  │     └── MAINTENANCE (assetEvent::...)
  │           ├── assetKey → referencia ao patrimonio
  │           ├── occurrenceDate: "2026-03-12"
  │           ├── hourmeterAtOccurrence: 1545
  │           ├── stockLocationKey → deposito de pecas
  │           ├── inputs: [{elementKey, quantity}]
  │           └── cropKeys: [crop::...]  → apropriacao do custo (ver regra 7)
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

### 7. Apropriacao de custo: safra inteira, talhoes escolhidos ou grupo de rateio

O custo de um abastecimento ou manutencao pode ser apropriado a safra. Ha tres niveis
de granularidade, e escolher errado espalha custo em area que nao consumiu nada:

| Quero... | Flags | Observacao |
|---|---|---|
| Custo na safra **inteira** | `--crop-key crop::C` (repetivel) | Rateio automatico por area entre todos os talhoes da safra |
| Custo em **parte** dos talhoes da safra | `--crop-key crop::C` + `--crop-glebe` e/ou `--glebe-tag` | Exige **exatamente uma** safra e login OAuth |
| Reusar um conjunto de safras salvo | `--crop-prorate-group-key cropProrateGroup::G` | **Cota de plano** — ver aviso abaixo |
| Voltar a safra inteira | `--clear-crop-glebes` (so no `update`) | Remove a restricao por talhao |
| Conferir onde o custo caiu | `fuel-supplies get <key> --apportionment` (idem `maintenances`) | O GET publico nao devolve essa composicao |

**Nao gaste o grupo de rateio para restringir a um talhao.** O grupo de rateio e
limitado por cota de plano: **1 grupo** na maioria dos planos, **2** no Avancado,
ilimitado so no Premium ou com addon. Criar um grupo por lancamento estoura a cota
(`ConsumableLimitBoundExceededException`) e queima o unico slot da fazenda. Grupo de
rateio serve para um conjunto de safras **reutilizado** entre lancamentos; para
apontar talhoes de uma safra, use `--crop-glebe`/`--glebe-tag`.

`--crop-glebe` aceita `glebe::<id>`, `cropGlebe::<id>` **ou o nome do talhao** (casa
sem exigir caixa e acento exatos). `--glebe-tag` casa pelo agrupador e pega todos os
talhoes daquele grupo — e a forma mais curta quando a safra cobre blocos separados.
As duas flags sao repetiveis e combinam entre si.

No `create`, a safra vem do `--crop-key` (exatamente um). No `update`, `--crop-key` e
**opcional**: a safra sai do proprio lancamento quando ha uma so, e o comando pede a
flag quando ha mais de uma.

#### O que restringir por talhao realmente faz

Restringe o **custo**, nao o percentual: a area de rateio do lancamento passa a ser a
soma dos talhoes escolhidos. Numa safra de 100 ha em tres talhoes (20, 30 e 50 ha),
selecionar o agrupador que cobre 20+30 faz a area apropriada cair de 100 para 50 ha.

#### Como falha (e nunca em silencio)

| Situacao | Saida |
|---|---|
| Sem login OAuth | **exit 2**, antes de qualquer escrita — nada e criado |
| Mais de um `--crop-key` com flag de talhao | **exit 4** — a restricao exige uma safra so |
| Flag de talhao junto com `--crop-prorate-group-key` | **exit 4** — com grupo, o servidor recalcula a partir dele e sobrescreveria a selecao |
| Nome de talhao ambiguo (dois talhoes com o mesmo nome) | **exit 4** com as chaves para desambiguar — o CLI nao escolhe por voce |
| Restricao nao persistiu | **exit 1**, `NOT_PERSISTED`, avisando que o lancamento **existe** e entregando o comando para retomar |

A gravacao sai em **duas pernas**: o `create`/`update` publico e, depois, a restricao
por talhao pela API interna (a API publica ainda nao expoe o campo). Por isso a
restricao **exige `aegro auth login`** — API key nao serve. Se a segunda perna falhar,
o lancamento ja existe: **nao repita o comando inteiro** (duplicaria o lancamento) —
use o comando de retomada que o erro imprime, que e um `update`.

## Referencia de Comandos

### assets

> **`--farm "<Fazenda|farm::key>"` e obrigatorio em todo comando de escrita desta
> tabela** (`create-*`, `update-*`, `delete-*`), e nao esta repetido linha a linha.
> Ver "Fazenda explicita em toda escrita" no topo.

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

**Anexo no patrimonio** (foto, nota de compra):
`aegro files attach --farm "<fazenda>" --entity asset --key asset::<id> --file ./foto.jpg --execute`
(exige OAuth). **Abastecimento e manutencao NAO aceitam anexo pelo CLI**: o
serv-core descarta `files` em update vindo de cliente nao-web (o CLI recusa
`--entity fuel-supply`/`maintenance` com esse motivo; aguarda correcao no
servidor — anexe pela tela do app enquanto isso).

### fuel-supplies

| Comando | Descricao | Flags Principais |
|---------|-----------|-----------------|
| `aegro fuel-supplies get <key>` | Busca abastecimento por chave | `--apportionment` (composicao do custo), `--output` |
| `aegro fuel-supplies list` | Lista abastecimentos | `--asset-key`, `--start-date`, `--end-date`, `--page`, `--output` |
| `aegro fuel-supplies create` | Cria abastecimento | `--asset-key` (obrig.), `--date` (obrig.), `--stock-location-key` (obrig.), `--hourmeter`, `--odometer`, `--observations`, `--inputs` (JSON), `--crop-key`, `--crop-glebe`, `--glebe-tag`, `--crop-prorate-group-key`, `--farm-user-key`, `--skip-verify` |
| `aegro fuel-supplies update <key>` | Atualiza abastecimento (PATCH parcial) | mesmas flags do create + `--clear-crop-glebes` |

```bash
# Registrar abastecimento de trator (Diesel S10 - 200L)
aegro fuel-supplies create --farm "Fazenda Aegro" \
  --asset-key "asset::57d299c3e4b059f24e3f99b0" \
  --date "2026-03-13" \
  --hourmeter 1550 \
  --stock-location-key "stockLocation::abc123" \
  --observations "Diesel S10 - 200L - Tanque sede" \
  --inputs '[{"elementKey": "element::combustivel_diesel", "quantity": {"unit": "L", "magnitude": 200}}]'
# {"key": "assetEvent::67f4d5e6a7b8c9d0", "assetKey": "asset::57d299c3e4b059f24e3f99b0", ...}

# Registrar abastecimento de veiculo (com hodometro)
aegro fuel-supplies create --farm "Fazenda Aegro" \
  --asset-key "asset::veiculo_hilux01" \
  --date "2026-03-13" \
  --odometer 15500 \
  --stock-location-key "stockLocation::abc123" \
  --observations "Diesel S10 - 80L - Posto externo"

# Buscar abastecimento especifico
aegro fuel-supplies get --farm "Fazenda Aegro" "assetEvent::67f4d5e6a7b8c9d0"

# Atualizar observacao de abastecimento
aegro fuel-supplies update --farm "Fazenda Aegro" "assetEvent::67f4d5e6a7b8c9d0" \
  --asset-key "asset::57d299c3e4b059f24e3f99b0" \
  --date "2026-03-13" \
  --hourmeter 1550 \
  --observations "Diesel S10 - 200L - Tanque sede - Corrigido"

# Custo na safra inteira (rateio automatico por area entre os talhoes da safra)
aegro fuel-supplies create --farm "Fazenda Aegro" \
  --asset-key "asset::57d299c3e4b059f24e3f99b0" \
  --date "2026-03-13" \
  --hourmeter 1550 \
  --stock-location-key "stockLocation::abc123" \
  --crop-key "crop::5d817ac8338bf976a0244391" \
  --inputs '[{"elementKey": "element::combustivel_diesel", "quantity": 200}]'

# Custo SO nos talhoes do agrupador "Estancia" (a safra cobre blocos separados)
# Exige login OAuth e exatamente um --crop-key
aegro fuel-supplies create --farm "Fazenda Aegro" \
  --asset-key "asset::57d299c3e4b059f24e3f99b0" \
  --date "2026-03-13" \
  --hourmeter 1550 \
  --stock-location-key "stockLocation::abc123" \
  --crop-key "crop::5d817ac8338bf976a0244391" \
  --glebe-tag "Estancia" \
  --execute

# Corrigir lancamento que ficou na safra inteira: restringir a um talhao pelo nome
# No update a safra sai do proprio lancamento — --crop-key so e necessario se houver mais de uma
aegro fuel-supplies update --farm "Fazenda Aegro" "assetEvent::67f4d5e6a7b8c9d0" \
  --crop-glebe "Talhao 3" --execute

# Desfazer a restricao, devolvendo o custo para a safra inteira
aegro fuel-supplies update --farm "Fazenda Aegro" "assetEvent::67f4d5e6a7b8c9d0" \
  --clear-crop-glebes --execute

# Conferir a apropriacao (safra, share e talhoes) — o GET publico nao traz isso
aegro fuel-supplies get --farm "Fazenda Aegro" "assetEvent::67f4d5e6a7b8c9d0" --apportionment
```

### maintenances

| Comando | Descricao | Flags Principais |
|---------|-----------|-----------------|
| `aegro maintenances get <key>` | Busca manutencao por chave | `--apportionment` (composicao do custo), `--output` |
| `aegro maintenances list` | Lista manutencoes | `--asset-key`, `--start-date`, `--end-date`, `--page`, `--output` |
| `aegro maintenances create` | Cria manutencao | `--asset-key` (obrig.), `--date` (obrig.), `--stock-location-key` (obrig.), `--hourmeter`, `--odometer`, `--crop-prorate-group-key`, `--observations`, `--inputs` (JSON), `--farm-user-key`, `--crop-key`, `--crop-glebe`, `--glebe-tag`, `--skip-verify` |
| `aegro maintenances update <key>` | Atualiza manutencao (PATCH parcial) | mesmas flags do create + `--clear-crop-glebes` |

```bash
# Registrar manutencao preventiva de trator (troca de filtros + oleo)
aegro maintenances create --farm "Fazenda Aegro" \
  --asset-key "asset::57d299c3e4b059f24e3f99b0" \
  --date "2026-03-12" \
  --hourmeter 1545 \
  --stock-location-key "stockLocation::abc123" \
  --observations "Revisao 500h - Troca filtros oleo/ar/combustivel + oleo motor 15W40" \
  --inputs '[{"elementKey": "element::filtro_oleo01", "quantity": {"unit": "un", "magnitude": 1}}, {"elementKey": "element::filtro_ar01", "quantity": {"unit": "un", "magnitude": 1}}, {"elementKey": "element::oleo_motor01", "quantity": {"unit": "L", "magnitude": 18}}]'
# {"key": "assetEvent::67f5e6a7b8c9d0e1", "assetKey": "asset::57d299c3e4b059f24e3f99b0", ...}

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

# Manutencao apropriada a uma safra (custo rateado por area em toda a safra)
aegro maintenances create --farm "Fazenda Aegro" \
  --asset-key "asset::57d299c3e4b059f24e3f99b0" \
  --date "2026-03-08" \
  --hourmeter 1540 \
  --stock-location-key "stockLocation::abc123" \
  --crop-key "crop::5d817ac8338bf976a0244391" \
  --observations "Reparo sistema hidraulico - safra 25/26"

# Manutencao apropriada a talhoes especificos da safra (exige OAuth e uma safra so)
aegro maintenances create --farm "Fazenda Aegro" \
  --asset-key "asset::57d299c3e4b059f24e3f99b0" \
  --date "2026-03-08" \
  --hourmeter 1540 \
  --stock-location-key "stockLocation::abc123" \
  --crop-key "crop::5d817ac8338bf976a0244391" \
  --crop-glebe "Talhao 1" --crop-glebe "Talhao 2" \
  --observations "Reparo do pivo que atende so esses dois talhoes" \
  --execute

# Manutencao com GRUPO DE RATEIO salvo — use apenas para um conjunto de safras
# REUTILIZADO entre lancamentos. Ha cota de plano (1 grupo na maioria); nao crie
# um grupo por lancamento nem para apontar um talhao (use --crop-glebe).
aegro maintenances create --farm "Fazenda Aegro" \
  --asset-key "asset::57d299c3e4b059f24e3f99b0" \
  --date "2026-03-08" \
  --hourmeter 1540 \
  --stock-location-key "stockLocation::abc123" \
  --crop-prorate-group-key "cropProrateGroup::6903854211d95556f227b028" \
  --observations "Reparo rateado entre as safras do grupo"

# Buscar manutencao especifica
aegro maintenances get --farm "Fazenda Aegro" "assetEvent::67f5e6a7b8c9d0e1"

# Conferir em que talhoes o custo caiu
aegro maintenances get --farm "Fazenda Aegro" "assetEvent::67f5e6a7b8c9d0e1" --apportionment
```

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

### 4. Nao esqueca o tipo de maquina (machineType) para MACHINE

O campo `machineType` e **obrigatorio** para patrimonios tipo `MACHINE`. Sem ele, a criacao falha com HTTP 422.

```bash
# ERRADO - falta machineType
aegro assets create-machine --farm "Fazenda Aegro" --name "Trator" --manufacturer "John Deere"
# Erro 422: machineType is required

# CORRETO
aegro assets create-machine --farm "Fazenda Aegro" --name "Trator" --manufacturer "John Deere" --machine-type TRACTOR
```

### 5. Nao passe `quantity` como numero solto em `inputs`

`quantity` e um objeto com `unit` e `magnitude`. Numero solto e recusado pela CLI
antes de chegar na API — `INVALID_INPUTS`, **exit 4**.

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

### 6. Nao paralelize chamadas de escrita da CLI

Nao ha bulk-update: operacoes em lote (ex: aplicar rateio a centenas de abastecimentos) exigem uma chamada `update` por registro. Rodar essas chamadas em paralelo causa HTTP 409 "Erro inesperado" mesmo em registros sem relacao entre si — observado em 2026-08-10 (CLI v0.16.0): com 5 chamadas paralelas, 2 de 5 falharam; com 3 paralelas, ~1,4% de falha; sequencial, 0 falhas.

```bash
# ERRADO - paralelismo gera 409 esporadico
cat keys.txt | xargs -P 5 -I {} aegro fuel-supplies update {} --crop-prorate-group-key "..." --execute

# ERRADO tambem - "xargs -P 1" serializa mas nao interrompe o lote: se uma chave falhar,
# xargs segue processando as chaves restantes e o erro se perde no meio de centenas de linhas
cat keys.txt | xargs -P 1 -I {} aegro fuel-supplies update {} --crop-prorate-group-key "..." --execute

# CORRETO - loop sequencial que para no primeiro erro que nao adianta repetir.
# Cada chave tenta ate 3 vezes (1 tentativa + 2 repeticoes, esperando 1s e 2s) e SO
# repete no 409 esporadico: exit 2 (auth), 3 (nao encontrado) e 4 (validacao) nao
# melhoram com retry e interrompem o lote na hora. O status HTTP vem em
# `error.status` no JSON que a CLI escreve em stderr.
# O `|| [ -n "$key" ]` processa a ultima chave mesmo se keys.txt nao terminar em newline.
while IFS= read -r key || [ -n "$key" ]; do
  [ -z "$key" ] && continue
  ok=""
  for delay in 0 1 2; do
    [ "$delay" -gt 0 ] && sleep "$delay"
    erro=$(aegro fuel-supplies update "$key" --crop-prorate-group-key "..." --execute 2>&1 >/dev/null)
    rc=$?
    if [ "$rc" -eq 0 ]; then ok=1; break; fi
    case "$erro" in
      *'"status": 409'*) continue ;;
      *) echo "Erro nao-transitorio (exit $rc) na chave $key: $erro" >&2; exit 1 ;;
    esac
  done
  if [ -z "$ok" ]; then
    echo "409 persistiu apos 3 tentativas na chave $key - interrompendo o lote" >&2
    exit 1
  fi
done < keys.txt
```

Sempre valide o payload com `--dry-run` em 1 registro antes de rodar o lote com `--execute`.

### 7. Nao junte stdout e stderr ao capturar `--output json`

Em raras situacoes (retry apos erro 5xx), a CLI pode emitir uma linha de warning que, com `2>&1`, se mistura ao JSON e quebra o parse. Redirecione apenas o stdout — mas isso reduz o risco, nao elimina: se o warning sair pelo proprio stdout (nao pelo stderr), o arquivo fica contaminado mesmo sem `2>&1`. Valide sempre o arquivo com um parser JSON antes de consumi-lo; se o parse falhar, descarte a resposta e repita a chamada.

```bash
# ERRADO - warning de retry pode corromper o JSON
aegro fuel-supplies list --farm "Fazenda Aegro" --page 27 --output json > pagina27.json 2>&1

# CORRETO - stdout puro no arquivo, warnings continuam visiveis no terminal.
# Escolha UMA vez o parser JSON que existir na maquina - nao assuma python3.
if command -v python3 >/dev/null 2>&1; then
  valida_json() { python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$1"; }
elif command -v python >/dev/null 2>&1; then
  valida_json() { python -c "import json,sys; json.load(open(sys.argv[1]))" "$1"; }
elif command -v jq >/dev/null 2>&1; then
  valida_json() { jq -e . "$1" >/dev/null; }
elif command -v node >/dev/null 2>&1; then
  valida_json() { node -e "JSON.parse(require('fs').readFileSync(process.argv[1],'utf8'))" "$1"; }
else
  echo "nenhum parser JSON disponivel (python3, python, jq ou node) - abortando" >&2
  exit 1
fi

# JSON valido nao basta: se a CLI saiu com erro, o arquivo pode estar truncado
# num ponto que ainda parseia. Exija exit 0 DA CLI e parse OK.
for tentativa in 1 2 3; do
  aegro fuel-supplies list --farm "Fazenda Aegro" --page 27 --output json > pagina27.json
  rc=$?
  if [ "$rc" -eq 0 ] && valida_json pagina27.json 2>/dev/null; then break; fi
  rm -f pagina27.json
  if [ "$tentativa" -eq 3 ]; then
    echo "pagina27.json invalido ou CLI falhou (exit $rc) apos 3 tentativas - abortando" >&2
    exit 1
  fi
done
```
