---
name: aegro-cadastro-patrimonio
requires-cli: 0.19.0
description: >-
  Cadastra ativos da fazenda no Aegro pela CLI — maquina, veiculo, silo,
  benfeitoria, pivo e estacao meteorologica — e deixa o ativo pronto para
  receber abastecimento e manutencao, entregando o link direto da ficha. Use
  quando pedirem "cadastrar trator", "adicionar maquina", "criar patrimonio",
  "registrar veiculo", "cadastrar silo"; EN "register a machine", "add an
  asset". NAO use para subir a frota inteira de uma planilha (use
  /aegro-importacao-patrimonio) nem para registrar abastecimento ou manutencao
  (use /aegro-patrimonial).
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

Fazenda dita em **cada comando** com `--farm "<Fazenda|farm::key>"` — nao por `farms select`.
O estado do `farms select` e global por maquina, e uma sessao paralela troca o alvo
da outra sem avisar: foi assim que, em 11/08/2026, a entrega de dois pedidos de
compra foi gravada em producao na fazenda errada, deixando o estoque negativo e
duas manutencoes custeadas em R$ 0,00 sem nenhuma mensagem de erro. Em sessao de
agente, ligue tambem `AEGRO_SAFE_MODE=1`, que recusa escrita cuja fazenda nao veio
de `--farm` (`IMPLICIT_FARM_BLOCKED`).

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
`invalid.asset-event.stock-location.key.required`) e a CLI barra antes, com exit 4.
Descubra os locais com `aegro stock locations`. Havendo `--inputs`, e desse local que
sai a baixa — e `quantity` vai como objeto `{"unit": ..., "magnitude": ...}`, nunca
numero solto.

## Sequencia: Registrar Manutencao

```bash
# Preventiva com pecas (para apropriar o custo a uma safra, ver a secao abaixo)
aegro maintenances create --farm "<fazenda>" \
  --asset-key <asset_key> --date "2026-03-12" --hourmeter 1545 \
  --stock-location-key <stock_location_key> \
  --observations "Revisao 500h" \
  --inputs '[{"elementKey": "element::filtro01", "quantity": {"unit": "un", "magnitude": 1}}]'
```

`--stock-location-key` tambem e obrigatorio aqui — vale para todo evento de
patrimonio (abastecimento e manutencao).

## Apropriar o custo a uma safra (ou a parte dela)

Vale para abastecimento e manutencao:

| Quero... | Flags |
|---|---|
| Custo na safra inteira (rateio por area) | `--crop-key crop::C` |
| Custo so em alguns talhoes da safra | `--crop-key crop::C` + `--crop-glebe "<nome ou chave>"` e/ou `--glebe-tag "<agrupador>"` |
| Desfazer a restricao por talhao | `--clear-crop-glebes` (no `update`) |
| Conferir onde o custo caiu | `get <key> --apportionment` |

```bash
# Custo apenas nos talhoes do agrupador "Estancia" (exige login OAuth e uma safra so)
aegro maintenances create --farm "<fazenda>" \
  --asset-key <asset_key> --date "2026-03-12" --hourmeter 1545 \
  --stock-location-key <stock_location_key> \
  --crop-key <crop_key> --glebe-tag "Estancia" --execute
```

**Nao use `--crop-prorate-group-key` para apontar talhoes.** Grupo de rateio tem cota
de plano (1 grupo na maioria, 2 no Avancado) e serve para um conjunto de safras
reutilizado entre lancamentos — gastar o unico slot da fazenda por lancamento estoura
a cota. Detalhes e modos de falha em `/aegro-patrimonial`.

## Limitacoes

| Bug | Impacto | Workaround |
|-----|---------|------------|
| **#6** `weather create` → HTTP 500 | Impossivel criar registros meteorologicos | Registrar pelo Aegro App |

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
- **Apropriar custo de manutencao a safra ou a talhoes** → `/aegro-patrimonial`
- **Analisar a rentabilidade por safra** → `/aegro-analise-rentabilidade`
- **Visao geral da fazenda** → `/aegro-visao-geral`
