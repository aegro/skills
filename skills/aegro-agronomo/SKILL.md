---
name: aegro-agronomo
requires-cli: 0.19.0
description: >-
  Dominio agronomico do Aegro pela CLI — safras, talhoes na safra, atividades
  planejadas e realizadas, romaneios de colheita, clima e insumos de producao:
  vocabulario, comandos e regras. Use quando pedirem "registrar atividade",
  "plantio", "aplicacao de defensivo", "colheita", "romaneio", "quanto colhi",
  "atividades da safra"; EN "record a field activity", "harvest log". NAO use
  para criar a safra ou o talhao do zero (use /aegro-cadastro-safra e
  /aegro-cadastro-talhoes) nem para custo e rentabilidade (use
  /aegro-analise-rentabilidade).
---

# Agronomo - Dominio Agronomico do Aegro

Referencia completa do dominio agronomico: safras, talhoes, atividades de campo,
registros de colheita, dados climaticos e insumos de producao (sementes, defensivos,
fertilizantes). Base para todos os workflows agronomicos.

---

## 1. Vocabulario

| Termo Aegro | Termo API | Definicao |
|-------------|-----------|-----------|
| **Safra** | `crop` | Ciclo produtivo com periodo definido (ex: Soja 2025/26). Contem talhoes, atividades e colheitas. |
| **Talhao** | `glebe` | Unidade permanente de terra na fazenda. Nao muda entre safras. Area fixa em hectares. |
| **Talhao de Safra** | `crop-glebe` | Vinculo talhao-safra. Area efetivamente plantada naquele ciclo. Central para produtividade. |
| **Atividade** | `activity` | Operacao agricola planejada ou executada (plantio, aplicacao, colheita, etc). |
| **Plano** | `plan` | Planejamento: quais talhoes, quais insumos, datas previstas. |
| **Realizacao** | `realization` | Execucao efetiva. Uma atividade pode ter multiplas realizacoes. |
| **Operacao (tag)** | `tag` | Nome/etiqueta da atividade, exibido como "Operacao" no app web/mobile. Na API o campo se chama `tag`. |
| **Romaneio** | `harvest-log` | Registro de pesagem de colheita. Pesos: bruto, tara, liquido, descontado, produto. |
| **Rateio** | `crop-prorate` | Distribuicao proporcional de custos entre talhoes. Soma = 100%. |
| **Elemento** | `element` | Insumo: semente, defensivo, fertilizante, item ou servico. |
| **Produtividade** | - | Sacas/ha. Soja: peso descontado (kg) / area (ha) / 60. |
| **Desconto** | `harvest-discount` | Reducoes no peso: umidade, impureza, avariados. Por safra. |

**Chaves:** Formato `tipo::hex` (ex: `crop::68dd6719e90f726622b7f549`). Hexadecimais sao IDs MongoDB.

---

## 2. Modelo de Dados e Relacionamentos

```
FARM (fazenda)
├── GLEBE (talhoes permanentes - area fixa)
├── CROP (safra - ciclo produtivo)
│   ├── CROP_GLEBE (talhao vinculado a safra = area plantada)
│   ├── ACTIVITY (atividade agricola)
│   │   ├── PLAN (planejamento: cropGlebeKeys[], inputs[] → ELEMENTS)
│   │   └── REALIZATION[] (execucoes, impacta STOCK)
│   ├── HARVEST_LOG (romaneios: cropGlebes[], pesos, seedKey)
│   ├── CROP_PRORATE (rateios entre talhoes)
│   └── HARVEST_DISCOUNTS (config umidade/impureza)
└── ELEMENT (insumos globais)
    ├── SEED (tipo: SOYBEAN, CORN...) ├── DEFENSIVE (tipo: HERBICIDE...)
    ├── FERTILIZER                    └── ITEM / SERVICE
```

**Eixo central:** CROP_GLEBE. Atividades, colheitas e produtividade sao por crop-glebe.
Sem crop-glebes vinculados, a safra nao tem operacoes possiveis.

---

## 3. Regras de Negocio

### Tipos de Atividade
`SOWING` (plantio), `APPLICATION` (defensivos), `FERTILIZATION` (adubacao), `HARVEST` (colheita),
`SEED_TREATMENT` (tratamento sementes), `PEST_SCOUTING` (monitoramento), `TILLAGE` (preparo solo), `OTHER`.

### Tipos de Defensivo
`HERBICIDE` (plantas daninhas), `INSECTICIDE` (insetos), `FUNGICIDE` (doencas), `ACARICIDE` (acaros), `OTHER` (adjuvantes).

### Modo de Calculo de Colheita
- **`AUTOMATIC`** (padrao): Calcula pesos a partir de bruto/tara + descontos da safra.
- **`MANUAL`**: Usuario informa todos os pesos. Usado quando balanca ja desconta.

### Descontos de Colheita
- Umidade base soja: 13-14% (acima desconta proporcionalmente)
- Impureza maxima soja: 1-2% (acima desconta kg/kg)
- Configurados por safra: `aegro crops harvest-discounts <crop_key>`

### Calculo de Produtividade
```
Produtividade (sc/ha) = Peso Descontado Total (kg) / Area (ha) / 60
```
1 saca soja = 60 kg. Usar peso descontado (apos umidade/impureza), nao peso liquido bruto.

### Realizacoes e Rateios
- Uma atividade pode ter multiplas realizacoes (ex: colheita em 3 dias)
- Realizacoes baixam estoque automaticamente
- Rateios: status `ACTIVE` ou `ARCHIVED`, soma percentuais = 100%

---

## 4. Referencia de comandos

### 4.1 Safras (`aegro crops`)

| Comando | Argumentos/Opcoes |
|---------|-------------------|
| `crops get <crop_key>` | posicional |
| `crops list` | `--start-date`, `--end-date`, `--page` |
| `crops glebes <crop_key>` | posicional, `--glebe-key` (repetivel), `--page` |
| `crops prorate <prorate_key>` | posicional |
| `crops prorates` | `--crop-key` (repetivel), `--status` (repetivel), `--search`, `--page` |
| `crops harvest-discounts <crop_key>` | posicional |

```bash
aegro crops list --farm "<fazenda>" --start-date 2025-01-01 --end-date 2026-12-31
aegro crops glebes --farm "<fazenda>" crop::68dd6719e90f726622b7f549
aegro crops prorates --farm "<fazenda>" --crop-key crop::68dd6719e90f726622b7f549 --status ACTIVE
```

### 4.2 Talhoes de Safra (`aegro crop-glebes`)

| Comando | Argumentos/Opcoes |
|---------|-------------------|
| `crop-glebes get <key>` | posicional |
| `crop-glebes list <crop_key>` | posicional, `--page` |

`crop-glebes list` recebe `crop_key` posicional. Endpoint: `POST /pub/v1/crops/{crop_key}/crop-glebes/filter`.

```bash
aegro crop-glebes list --farm "<fazenda>" crop::68dd6719e90f726622b7f549
```

### 4.3 Talhoes Permanentes (`aegro glebes`)

| Comando | Argumentos/Opcoes |
|---------|-------------------|
| `glebes get <key>` | posicional |
| `glebes list` | `--page` |

### 4.4 Atividades (`aegro activities`)

| Comando | Argumentos/Opcoes |
|---------|-------------------|
| `activities get <key>` | posicional |
| `activities list` | `--crop-key`, `--status` (repetivel), `--type` (repetivel), `--page` |
| `activities plan <key>` | posicional - **chave da atividade** → `/activities/{key}/plan` |
| `activities get-plan <key>` | posicional - **chave do plano** → `/activities/plans/{key}` |
| `activities realizations` | `--activity-key`, `--crop-key`, `--start-date`, `--end-date`, `--page` |
| `activities get-realization <key>` | posicional |
| `activities create-plan` | `--crop-key` (obrig.), `--type` (obrig.), `--start-date` (obrig.), `--activity-key`, `--crop-glebe-key` (repetivel), `--end-date`, `--observations`, `--tag` (Operacao: nome/etiqueta), `--inputs` (JSON) |
| `activities create-realization` | mesmas opcoes do create-plan (inclui `--tag`) + `--area`/`--area-unit`, `--stock-location-key`, `--farm-user-key` (repetivel), `--file` (anexo, repetivel — exige OAuth) |
| `activities update-plan <key>` | `--body` (JSON Merge Patch, **PATCH**) - so os campos a alterar |
| `activities update-realization <key>` | `--body` (JSON Merge Patch, **PATCH**) - so os campos a alterar; `--file` (anexo, repetivel — ACRESCENTA aos existentes) |
| `activities delete-activity <key>` | posicional - **chave da atividade** → `DELETE /activities/{key}`. Mutacao: `--dry-run`/`--execute`, `--farm` |
| `activities delete-realization <key>` | posicional - **chave da realizacao** → `DELETE /activities/realizations/{key}`. Mutacao: `--dry-run`/`--execute`, `--farm` |

**ATENCAO exclusao (`delete-*`):**
- `delete-activity <ACTIVITY_KEY>` remove a atividade **e, em cascata, seu plano e todas as realizacoes**, estornando o estoque vinculado.
- `delete-realization <REALIZATION_KEY>` remove uma realizacao **e estorna o estoque dela**; se restarem plano ou outras realizacoes a atividade e mantida, senao e removida junto.
- A chave da realizacao tem prefixo **`activityLog::`** (nao `activityRealization::`) - e o valor que vem no campo `key` de `activities realizations` / `get-realization`. Prefixo errado retorna 404, indistinguivel de "nao existe".
- E **exclusao logica (soft-delete)**: sai das listagens, mas nao ha como desfazer pela API — trate como irreversivel. Chave desconhecida ou de outra fazenda retorna 404.
- **`get`/`get-realization` por chave AINDA retornam o registro excluido**, sem nenhum marcador de exclusao. Para confirmar que a exclusao aconteceu, consulte a **listagem** (`activities list` / `activities realizations`) — nunca o get por chave.
- **Sem `AEGRO_SAFE_MODE=1` nao ha trava: `delete-*` sem flag nenhuma apaga na hora**, sem preview e sem confirmacao. Com `AEGRO_SAFE_MODE=1`, escrever exige `--execute` e `--farm` explicito (senao `SAFE_MODE_BLOCKED` / `IMPLICIT_FARM_BLOCKED`).
- O `--dry-run` **so imprime a requisicao que seria enviada** - nao chama o servidor, entao nao confirma que a chave existe, que ela e daquela fazenda, nem quanta coisa a cascata vai levar junto. Para prever de verdade **o que sera apagado**, consulte antes: `activities get <ACTIVITY_KEY>` e `activities realizations --activity-key <ACTIVITY_KEY>`.

**ATENCAO `plan` vs `get-plan`:**
- `activities plan <ACTIVITY_KEY>` → plano a partir da chave da **atividade**
- `activities get-plan <PLAN_KEY>` → plano pela chave do **plano**
- `activities create-plan` cria **planejamento**; `activities create-realization` cria
  **realizacao** (execucao em campo).
- **Editar e PATCH / JSON Merge Patch** (`update-plan`/`update-realization`): passe em
  `--body` apenas os campos a alterar, ex.: `--body '{"tag":"Aplicacao de Herbicida"}'`
  para trocar a Operacao. O `tag` (Operacao) e atributo da **atividade** — alterar num
  plano ou realizacao reflete na atividade inteira (plano + todas as realizacoes).

**Anexos na realizacao (`--file` / `aegro files attach`):**
- A realizacao aceita **anexo de arquivo** (ficha de aplicacao, receituario
  agronomico, ordem de servico) — e a unica entidade com anexo em escrita na
  API publica (desde 20/08/2026). **Planejamento NAO tem anexo**: nao anuncie
  nem tente anexar em plano (`create-plan`/`update-plan` nao tem `--file`).
- `create-realization --file ficha.pdf` (repetivel) sobe o arquivo e manda a
  referencia no PROPRIO POST — uma requisicao de escrita so. O upload usa a API
  interna, entao `--file` **exige login OAuth** (`aegro auth login`); com API
  key o comando falha antes de criar qualquer coisa (exit 2).
- **Nao e atomico, e isso importa no erro.** O upload acontece ANTES do POST,
  entao existe um estado intermediario: a realizacao pode ser criada sem o
  anexo (servidor antigo que descarta `files`, ou falha na conferencia). Nesse
  caso o comando sai com **exit 1** e o stderr traz o comando de retry pronto,
  por `--url`. **NUNCA repita o `create-realization`** — a realizacao ja
  existe e voce criaria uma segunda. Rode o retry que o CLI emitiu:

  ```bash
  aegro files attach --farm "<fazenda>" --entity realization --key activityLog::<id> \
    --url "<chave S3 que saiu no stderr>" --execute
  ```

  Reanexar a mesma chave S3 e no-op (a saida traz `saved: false`), entao o
  retry por `--url` pode ser repetido sem medo. Ja repetir com `--file` sobe o
  arquivo de novo e cria uma SEGUNDA copia do anexo.
- `update-realization --file` **acrescenta** aos anexos existentes: o comando
  le a realizacao antes e reenvia a lista completa, porque o PATCH substitui
  `files` por inteiro (mandar so os novos apagaria os antigos). Para trocar a
  lista, passe `files` explicitamente no `--body`. `aegro files attach
  --entity realization` faz o mesmo append e serve quando voce nao quer mexer
  em mais nada.
- Consultar: `aegro files list-attachments --entity realization --key activityLog::<id>`
  (funciona ate com API key; a leitura e publica). Cada item traz `url` (chave
  S3) e o nome derivado dela.
- Se o vinculo falhar DEPOIS do upload, o stderr traz o comando de retry com
  `--url` — reanexar a mesma chave S3 e no-op (dedup); repetir com `--file`
  sobe o arquivo de novo e cria uma SEGUNDA copia.
- Limite de 100 MB por arquivo; PDF, imagem, planilha e documento em geral
  funcionam (validado em campo). Depois de `create-realization --file` e de
  `update-realization --file` o CLI **rele a realizacao** e mostra os anexos
  gravados — a resposta crua da API nao traz o campo `files`, entao e a
  releitura que confirma.

**Maquina e horimetro (`machineHours`):**
- Plano e realizacao aceitam o campo `machineHours` no corpo — lista de objetos
  `{"machineKey": "asset::<id>", "hours": <n>, "startHourmeter": <n>, "endHourmeter": <n>}`.
  `machineKey` e a chave do patrimonio (maquina — veja `aegro assets list --type MACHINE`).
- **Via CLI so e setavel por `update-plan`/`update-realization --body`** (JSON Merge
  Patch); `create-plan`/`create-realization` nao tem flag para maquina/horimetro. Para
  lancar atividade com maquina: crie primeiro, depois atualize com o `--body`.
- Na leitura (`get-plan`/`get-realization`) o campo volta como `machineHours`.

```bash
aegro activities list --farm "<fazenda>" --crop-key crop::68dd6719e90f726622b7f549 --type APPLICATION
aegro activities list --farm "<fazenda>" --crop-key crop::68dd6719e90f726622b7f549 --type SOWING --type HARVEST
aegro activities realizations --farm "<fazenda>" --crop-key crop::68dd6719e90f726622b7f549 --start-date 2025-10-01 --end-date 2026-03-31

# Criar plano de plantio com insumos
aegro activities create-plan --farm "<fazenda>" \
  --crop-key crop::68dd6719e90f726622b7f549 \
  --type SOWING --start-date 2026-01-15 \
  --crop-glebe-key cropGlebe::68dd6730e90f726622b7f555 \
  --tag "Plantio Soja TMG 2381" \
  --observations "Plantio soja TMG 2381" \
  --inputs '[{"elementKey":"element::abc123","amount":{"magnitude":50,"unit":"KG/HA"}}]' \
  --dry-run

# Excluir uma atividade (cascata: plano + realizacoes).
# 1) Veja o que sera apagado - isto SIM consulta o servidor:
aegro activities get activity::68dd6719e90f726622b7f549 --farm "Fazenda Sul"
aegro activities realizations --activity-key activity::68dd6719e90f726622b7f549 --farm "Fazenda Sul"
# 2) Confira a requisicao (nao valida no servidor) e efetive, com o MESMO --farm nos dois:
aegro activities delete-activity activity::68dd6719e90f726622b7f549 --dry-run --farm "Fazenda Sul"
aegro activities delete-activity activity::68dd6719e90f726622b7f549 --execute --farm "Fazenda Sul"

# Criar realizacao ja com a ficha de aplicacao anexada (--file exige OAuth)
aegro activities create-realization --farm "Fazenda Sul" \
  --crop-key crop::68dd6719e90f726622b7f549 --type APPLICATION --start-date 2026-08-01 \
  --file ./ficha-aplicacao.pdf --execute

# Acrescentar anexo a uma realizacao existente SEM perder os anteriores
aegro files attach --entity realization --key activityLog::68dd6730e90f726622b7f560 \
  --file ./receituario.pdf --farm "Fazenda Sul" --execute
aegro files list-attachments --entity realization --key activityLog::68dd6730e90f726622b7f560

# Vincular maquina + horimetro a uma realizacao (so via update --body; create nao tem flag)
aegro activities update-realization activityLog::68dd6730e90f726622b7f560 --farm "Fazenda Sul" \
  --body '{"machineHours":[{"machineKey":"asset::abc123","hours":8,"startHourmeter":1200,"endHourmeter":1208}]}' \
  --execute

# Excluir apenas uma realizacao - chave com prefixo activityLog::, idem: confira antes
aegro activities get-realization activityLog::68dd6730e90f726622b7f560 --farm "Fazenda Sul"
aegro activities delete-realization activityLog::68dd6730e90f726622b7f560 --dry-run --farm "Fazenda Sul"
aegro activities delete-realization activityLog::68dd6730e90f726622b7f560 --execute --farm "Fazenda Sul"
```

### 4.5 Romaneios de Colheita (`aegro harvest-logs`)

| Comando | Argumentos/Opcoes |
|---------|-------------------|
| `harvest-logs get <key>` | posicional |
| `harvest-logs create` | ver parametros abaixo |

**Parametros `create`:** `--crop-key` (obrig.), `--date` (obrig., YYYY-MM-DD), `--crop-glebe` (repetivel),
`--calculation-mode` (AUTOMATIC/MANUAL, default AUTOMATIC), `--seed-key`, `--destination-key`,
`--gross-weight` (kg), `--tare-weight` (kg), `--net-weight` (kg), `--discounted-weight` (kg),
`--product-weight` (kg), `--observations`, `--identifier`, `--invoice-code`, `--romaneio-code`.

```bash
# Romaneio automatico
aegro harvest-logs create --farm "<fazenda>" \
  --crop-key crop::68dd6719e90f726622b7f549 --date 2026-03-10 \
  --crop-glebe cropGlebe::68dd6730e90f726622b7f555 \
  --gross-weight 32000 --tare-weight 12000

# Romaneio manual completo
aegro harvest-logs create --farm "<fazenda>" \
  --crop-key crop::68dd6719e90f726622b7f549 --date 2026-03-10 \
  --crop-glebe cropGlebe::68dd6730e90f726622b7f555 \
  --crop-glebe cropGlebe::68dd6730e90f726622b7f556 \
  --calculation-mode MANUAL --seed-key element::seed123 \
  --gross-weight 32000 --tare-weight 12000 --net-weight 20000 \
  --discounted-weight 19400 --product-weight 19400 \
  --romaneio-code "ROM-2026-0042" --invoice-code "NF-88901"
```

**Romaneio com destino (silo) sai em um comando so.** Com `--destination-key`,
se o servidor descartar o silo no create, o CLI completa por PATCH e confere
por releitura — a saida ja e o registro relido. Se a completacao falhar, o
comando **falha dizendo que o romaneio ja existe**: nunca repita o `create`,
use o `update` que ele sugere, ou voce duplica o romaneio.

**Campo desconhecido no `--body` e recusado antes de enviar** (exit 4). Nao e
frescura do CLI: a API aceitaria a requisicao, descartaria o campo e
responderia sucesso — o romaneio ficaria sem o dado e a releitura pareceria
certa. Se um nome de campo for recusado, ele mudou; confira com `--help`.

**Anexo no romaneio** (foto da nota, ticket de balanca):
`aegro files attach --farm "<fazenda>" --entity harvest-log --key harvestLog::<id> --file ./ticket.jpg --execute`
(exige OAuth; releitura de conferencia inclusa). Consulta:
`aegro files list-attachments --entity harvest-log --key harvestLog::<id>`.

### 4.6 Clima (`aegro weather`)

| Comando | Argumentos/Opcoes |
|---------|-------------------|
| `weather get <key>` | posicional |
| `weather create` | `--weather-station-key` (obrig.), `--date` (obrig.), parametros pareados abaixo |

**Parametros pareados** (ambos presentes ou ambos ausentes):
- `--precipitation` + `--precipitation-unit` (ex: `mm`)
- `--temperature` + `--temperature-unit` (ex: `CELSIUS`)

**Independentes:** `--humidity` (%), `--pressure` (hPa).

```bash
aegro weather create --farm "<fazenda>" --weather-station-key weatherstation::ws001 --date 2026-03-12 \
  --precipitation 12.5 --precipitation-unit mm \
  --temperature 28.0 --temperature-unit CELSIUS --humidity 65.0
```

### 4.7 Elementos / Insumos (`aegro elements`)

| Comando | Argumentos/Opcoes |
|---------|-------------------|
| `elements get <key>` | posicional |
| `elements list` | `--category` (repetivel), `--type` (repetivel), `--page` |
| `elements create-defensive` | `--name` (obrig.), `--type` (obrig.), `--unit` (obrig.), `--manufacturer`, `--observations` |
| `elements create-fertilizer` | `--name` (obrig.), `--unit` (obrig.), `--manufacturer`, `--observations` |
| `elements create-seed` | `--name` (obrig.), `--type` (obrig.), `--unit` (obrig.), `--manufacturer`, `--observations` |

Categorias agro: `SEED`, `DEFENSIVE`, `FERTILIZER`.

```bash
aegro elements list --farm "<fazenda>" --category SEED
aegro elements list --farm "<fazenda>" --category DEFENSIVE --type HERBICIDE
aegro elements create-defensive --farm "<fazenda>" --name "Roundup Original" --type HERBICIDE --unit L --manufacturer Monsanto
aegro elements create-fertilizer --farm "<fazenda>" --name "MAP Granulado" --unit KG --manufacturer Mosaic
aegro elements create-seed --farm "<fazenda>" --name "TMG 2381 IPRO" --type SOYBEAN --unit KG --manufacturer TMG
```

**Opcao global:** Todos os comandos aceitam `--output` / `-o` com `json` (padrao), `table` ou `csv`.

---

## 5. Padroes e Exemplos Reais

### Formato de Chaves
```
crop::68dd6719e90f726622b7f549       cropGlebe::68dd6730e90f726622b7f555
glebe::68dd6725e90f726622b7f550      activity::68e1a3b2f4c8901234567890
element::68e2c5d6e7890abcdef12345    harvestlog::68e2b4c5d6789012345abcde
weatherstation::ws001
```

Sempre usar a chave completa com prefixo. Os hexadecimais sao IDs MongoDB de 24 caracteres.

### Paginacao

- Maximo **50 itens/pagina**, parametro `--page` (default: 1)
- Se retornar exatamente 50 itens, ha mais paginas
- Iterar `--page 2`, `--page 3`... ate receber menos de 50

### Formato --inputs (create-plan)

O parametro `--inputs` recebe string JSON com array de objetos:

```json
[
  {"elementKey": "element::abc123", "amount": {"magnitude": 2.5, "unit": "L/HA"}},
  {"elementKey": "element::def456", "amount": {"magnitude": 150, "unit": "ML/HA"}}
]
```

Use `elementKey` + `amount`. Nao use `productKey` (campo de compras) nem
`quantity` em atividades. Rode `--dry-run` antes e, apos executar, confira os
insumos persistidos com `aegro activities plan <ACTIVITY_KEY>` ou
`aegro activities get-plan <PLAN_KEY>`.

Unidades comuns: `KG/HA`, `L/HA`, `ML/HA`, `G/HA`, `KG`, `L`, `UN`.

### Fluxo de Pesagem de Colheita

```
1. Caminhao na balanca         → Peso bruto: 32.000 kg
2. Descarrega grao
3. Caminhao volta na balanca   → Tara: 12.000 kg
4. Sistema calcula (modo AUTOMATIC):
   Peso liquido = 32.000 - 12.000 = 20.000 kg
   Desconto umidade (14.2% → base 13%) = -1.7% = -340 kg
   Desconto impureza (1.5% → base 1%) = -0.5% = -100 kg
   Peso descontado = 20.000 - 440 = 19.560 kg
   Peso produto = 19.560 kg
5. Produtividade do talhao (50 ha):
   19.560 / 50 / 60 = 6.52 sc/ha
```

### Ciclo Completo da Safra

```
1. aegro crops list                                         → safras ativas
2. aegro crops glebes <crop_key>                            → talhoes vinculados
3. aegro activities list --crop-key <k> --type SOWING       → plantio
4. aegro activities list --crop-key <k> --type APPLICATION  → aplicacoes
5. aegro activities realizations --crop-key <k>             → execucoes reais
6. aegro harvest-logs get <key>                             → romaneios
7. Produtividade: soma pesos descontados / soma areas / 60
```

### Cenarios Comuns de Consulta

```bash
# Quanto produziu a safra? (coletar todos os romaneios)
aegro crops list --farm "<fazenda>" --start-date 2025-01-01 --end-date 2026-12-31
# → pegar crop_key da safra desejada
aegro activities list --farm "<fazenda>" --crop-key crop::xxx --type HARVEST
# → ver realizacoes de colheita com pesos

# Quais defensivos foram aplicados?
aegro activities list --farm "<fazenda>" --crop-key crop::xxx --type APPLICATION
aegro activities realizations --farm "<fazenda>" --crop-key crop::xxx --start-date 2025-10-01

# Qual a area plantada?
aegro crops glebes --farm "<fazenda>" crop::xxx
# → somar areas dos crop-glebes retornados
```

---

## 6. Bugs e Workarounds Conhecidos

| Bug | Sintoma | Workaround |
|-----|---------|------------|
| **#5** `elements create-seed` | `POST /elements/seeds` → 500 | Cadastrar sementes pela interface web. Leitura funciona normal. |
| **#6** `weather create` | `POST /weather-logs` → 500 | Registrar clima pela interface web. Leitura funciona normal. |

**Regra geral:** Endpoints de escrita sao mais propensos a 500. Testar com dados minimos.
Se falhar, orientar usuario a usar a interface web (app.aegro.com.br).

---

## 7. Anti-padroes

1. **Listar atividades sem `--crop-key`:** Retorna TODAS as safras misturadas. Sempre filtrar por safra.

2. **Criar plano sem verificar crop-glebes:** Antes de `create-plan` com `--crop-glebe-key`,
   confirmar existencia com `crops glebes <crop_key>`. Chaves invalidas causam erro silencioso.

3. **Confundir `plan` com `get-plan`:**
   - `activities plan <ACTIVITY_KEY>` → endpoint `/activities/{key}/plan`
   - `activities get-plan <PLAN_KEY>` → endpoint `/activities/plans/{key}`
   - Chave errada = 404 ou dados incorretos.

4. **Peso liquido como produtividade:** Usar peso descontado/produto, nunca liquido bruto.

5. **Ignorar paginacao:** 50 itens = provavelmente ha mais paginas.

6. **Romaneio sem `--crop-key`:** Parametro obrigatorio. Sem ele, erro de validacao.

7. **Parametros clima desemparelhados:** `--precipitation` exige `--precipitation-unit` (e vice-versa).
   Mesma regra para `--temperature`/`--temperature-unit`. Desemparelhar causa exit code 4.
