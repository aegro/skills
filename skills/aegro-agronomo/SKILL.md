---
name: aegro-agronomo
description: Dominio agronomico do Aegro - safras, talhoes, atividades, colheitas, clima e insumos de producao
version: 0.5.2
---

# Agronomo - Dominio Agronomico do Aegro

Referencia completa do dominio agronomico: safras, talhoes, atividades de campo,
registros de colheita, dados climaticos e insumos de producao (sementes, defensivos,
fertilizantes). Base para todos os workflows agronomicos.

---

## 1. Vocabulario do Dominio

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

## 4. Referencia Completa de Comandos

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
aegro crops list --start-date 2025-01-01 --end-date 2026-12-31
aegro crops glebes crop::68dd6719e90f726622b7f549
aegro crops prorates --crop-key crop::68dd6719e90f726622b7f549 --status ACTIVE
```

### 4.2 Talhoes de Safra (`aegro crop-glebes`)

| Comando | Argumentos/Opcoes |
|---------|-------------------|
| `crop-glebes get <key>` | posicional |
| `crop-glebes list <crop_key>` | posicional, `--page` |

`crop-glebes list` recebe `crop_key` posicional. Endpoint: `POST /pub/v1/crops/{crop_key}/crop-glebes/filter`.

```bash
aegro crop-glebes list crop::68dd6719e90f726622b7f549
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

**ATENCAO `plan` vs `get-plan`:**
- `activities plan <ACTIVITY_KEY>` → plano a partir da chave da **atividade**
- `activities get-plan <PLAN_KEY>` → plano pela chave do **plano**
- `activities create-plan` cria **planejamento**, nao realizacao. A API publica permite
  consultar realizacoes, mas nao expoe endpoint para criar realizacao.

```bash
aegro activities list --crop-key crop::68dd6719e90f726622b7f549 --type APPLICATION
aegro activities list --crop-key crop::68dd6719e90f726622b7f549 --type SOWING --type HARVEST
aegro activities realizations --crop-key crop::68dd6719e90f726622b7f549 --start-date 2025-10-01 --end-date 2026-03-31

# Criar plano de plantio com insumos
aegro activities create-plan \
  --crop-key crop::68dd6719e90f726622b7f549 \
  --type SOWING --start-date 2026-01-15 \
  --crop-glebe-key cropGlebe::68dd6730e90f726622b7f555 \
  --tag "Plantio Soja TMG 2381" \
  --observations "Plantio soja TMG 2381" \
  --inputs '[{"elementKey":"element::abc123","amount":{"magnitude":50,"unit":"KG/HA"}}]' \
  --dry-run
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
aegro harvest-logs create \
  --crop-key crop::68dd6719e90f726622b7f549 --date 2026-03-10 \
  --crop-glebe cropGlebe::68dd6730e90f726622b7f555 \
  --gross-weight 32000 --tare-weight 12000

# Romaneio manual completo
aegro harvest-logs create \
  --crop-key crop::68dd6719e90f726622b7f549 --date 2026-03-10 \
  --crop-glebe cropGlebe::68dd6730e90f726622b7f555 \
  --crop-glebe cropGlebe::68dd6730e90f726622b7f556 \
  --calculation-mode MANUAL --seed-key element::seed123 \
  --gross-weight 32000 --tare-weight 12000 --net-weight 20000 \
  --discounted-weight 19400 --product-weight 19400 \
  --romaneio-code "ROM-2026-0042" --invoice-code "NF-88901"
```

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
aegro weather create --weather-station-key weatherstation::ws001 --date 2026-03-12 \
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
aegro elements list --category SEED
aegro elements list --category DEFENSIVE --type HERBICIDE
aegro elements create-defensive --name "Roundup Original" --type HERBICIDE --unit L --manufacturer Monsanto
aegro elements create-fertilizer --name "MAP Granulado" --unit KG --manufacturer Mosaic
aegro elements create-seed --name "TMG 2381 IPRO" --type SOYBEAN --unit KG --manufacturer TMG
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
aegro crops list --start-date 2025-01-01 --end-date 2026-12-31
# → pegar crop_key da safra desejada
aegro activities list --crop-key crop::xxx --type HARVEST
# → ver realizacoes de colheita com pesos

# Quais defensivos foram aplicados?
aegro activities list --crop-key crop::xxx --type APPLICATION
aegro activities realizations --crop-key crop::xxx --start-date 2025-10-01

# Qual a area plantada?
aegro crops glebes crop::xxx
# → somar areas dos crop-glebes retornados
```

---

## 6. Bugs e Workarounds Conhecidos

| Bug | Sintoma | Workaround |
|-----|---------|------------|
| **#1** `glebes list` | `POST /glebes/filter` → HTTP 500 | Usar `glebes get <key>` individual. Obter chaves via `crops glebes <crop_key>`. |
| **#2** `crop-glebes list` | `POST /crops/{k}/crop-glebes/filter` → 500 | Usar `crop-glebes get <key>` individual. Ou `crops glebes <crop_key>` com `--glebe-key`. |
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
