---
name: aegro-agronomo
requires-cli: 0.21.0
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
| **Romaneio** | `harvest-log` | Registro de pesagem de colheita. Pesos: bruto, tara, produto (bruto - tara), descontado (soma dos descontos) e liquido (produto - descontado). |
| **Rateio** | `crop-prorate` | Distribuicao proporcional de custos entre talhoes. Soma = 100%. |
| **Elemento** | `element` | Insumo: semente, defensivo, fertilizante, item ou servico. |
| **Produtividade** | - | Sacas/ha. Soja: peso liquido (kg) / area (ha) / 60. |
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
    ├── SEED (tipo: SOY, CORN...)     ├── DEFENSIVE (tipo: HERBICIDE...)
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

### Pesos do romaneio

| Peso | Campo | O que e |
|------|-------|---------|
| Bruto | `totalGrossWeight` | Caminhao cheio na balanca |
| Tara | `tareWeight` | Caminhao vazio |
| Produto | `productWeight` | Bruto - tara |
| Descontado | `totalDiscountedWeight` | **Soma** dos descontos (umidade, impureza...), em kg |
| Liquido | `totalNetWeight` | Produto - descontado: o que o armazem credita e o produtor confere |

"Peso descontado" e o quanto foi descontado, **nao** o peso depois dos descontos.
O numero que o produtor reconhece de cabeca e o **liquido** do ticket.

### Modo de Calculo de Colheita
- **`AUTOMATIC`** — como o Aegro trabalha: informe bruto, tara e as linhas de
  desconto do ticket, e o Aegro calcula produto, descontado e liquido. Seguro so
  na CLI que calcula pela previa do servidor antes de gravar (ver 4.5); na CLI
  antiga ele grava o romaneio **sem aplicar desconto nenhum** (liquido = produto)
  e responde sucesso.
- **`MANUAL`** — grava os cinco pesos do ticket como estao. O servidor **nao
  confere** se bruto - tara - descontos bate com o liquido; confira antes de gravar.

### Descontos de Colheita
- Umidade base soja: 13-14% (acima desconta proporcionalmente)
- Impureza maxima soja: 1-2% (acima desconta kg/kg)
- Configurados por safra: `aegro crops harvest-discounts <crop_key>`

### Calculo de Produtividade
```
Produtividade (sc/ha) = Peso Liquido Total (kg) / Area (ha) / 60
```
1 saca soja = 60 kg. Usar o peso liquido (apos umidade/impureza) — nao o produto,
nem o descontado, que e a soma dos descontos.

Romaneio com `totalDiscountedWeight` = 0 e desconto no ticket (umidade, impureza)
tem liquido inflado: foi gravado sem aplicar o desconto. Antes de somar a
produtividade, aponte esses romaneios ao usuario em vez de soma-los calado.

### Realizacoes e Rateios
- Uma atividade pode ter multiplas realizacoes (ex: colheita em 3 dias)
- Realizacao **com insumos** lancada pela CLI nao baixa o estoque deles. Com
  `--inputs` e `--stock-location-key`, o create responde erro 500 **e grava a
  realizacao mesmo assim**, sem movimentar o estoque: nao repita o comando
  (cada tentativa cria outra), confira com `activities realizations` e peca a
  saida de estoque em separado (`/aegro-estoquista`) ou lance a baixa pela tela.
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
  API publica. **Planejamento NAO tem anexo**: nao anuncie
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
| `harvest-logs list` | `--crop-key` (obrig., repetivel), `--identifier`, `--silo`, `--glebe-key`, `--start-date`, `--end-date`, `--tag`, `--receipt`, `--limit` |
| `harvest-logs get <key>` | posicional |
| `harvest-logs create` | ver parametros abaixo |
| `harvest-logs update <key>` | posicional, `--body` (PATCH parcial). Mutacao: `--dry-run`/`--execute`, `--farm` |

**`get` prova que o romaneio existe.** Romaneio excluido na tela responde **204**,
o mesmo terminal de chave inexistente — nao mais 200 com o corpo. Entao 200 no
`get` e confirmacao de que o registro esta vigente, e `update` sobre excluido
responde 404 sem tocar no dado.

**Parametros `create`:** `--crop-key` (obrig.), `--date` (obrig., YYYY-MM-DD), `--crop-glebe` (repetivel),
`--seed-key` (obrig.), `--calculation-mode` (`AUTOMATIC`/`MANUAL`), `--destination-key`,
`--gross-weight` (kg), `--tare-weight` (kg), `--net-weight` (kg), `--discounted-weight` (kg),
`--product-weight` (kg), `--discount` (repetivel), `--discount-index` (repetivel, quando
a CLI tiver), `--observations`, `--identifier`, `--invoice-code`, `--romaneio-code`.

**Antes de montar o comando:**
- **O anexo e um ticket de pesagem?** Sem bruto **ou** sem tara no papel (nota
  fiscal de venda ou remessa, relatorio de periodo, print sem tara), nao e
  romaneio: diga isso ao usuario e pergunte o ticket, em vez de inventar pesos.
  Documento que soma varias cargas (varios tickets, relatorio de periodo) vira um
  romaneio por carga, ou pergunte ao usuario como ele quer registrar — nunca some
  as cargas num romaneio so.
- **Carga dividida:** quando bruto - tara nao e o peso desta carga (o ticket
  reparte uma pesagem entre destinos, contratos ou talhoes), nao ajuste bruto nem
  tara para caber: pergunte ao usuario qual parte e deste romaneio e como ele
  registra a divisao. Se a CLI recusar dizendo que a diferenca "nao e desconto",
  e isso — nao lance em `MANUAL` para fazer caber.
- **Casos que parecem ticket e pedem cuidado:**
  - **retirada** (o caminhao sai carregado da fazenda): a pesagem de entrada, vazio,
    e a **tara**, e a de saida e o bruto — nao inverta;
  - **toneladas**: converta para kg antes (`31,86 t` = `31860`); cuidado com a
    virgula de milhar (`31,860` pode ser 31.860 kg);
  - **planilha com bruto e tara carga a carga** (nao e ticket, mas traz cada
    pesagem): um romaneio por linha, confirmando com o usuario antes;
  - **uma pesagem descarregada em dois destinos** (bitrem em dois silos): um
    romaneio so, com os destinos em `--observations`, ou pergunte como ele registra;
  - **teor ou desconto escrito a mao** sobre um ticket sem desconto: nao e desconto
    do ticket — pergunte ao usuario antes de lancar;
  - **rotulos que enganam:** leia o que o numero e, nao so o rotulo — ha ticket em
    que "Peso Liquido" vem antes dos descontos (e o produto), "Peso Bruto" e o
    produto ou "Peso Total" e o bruto. Confira pela conta: bruto - tara = produto,
    produto - descontos = liquido;
  - **nome do desconto diferente do tipo da safra** (ex.: "Ardidos" no ticket e
    "Avariados" na safra): nao decida sozinho; pergunte ao usuario qual tipo usar;
  - **dois tickets da mesma carga** (origem e destino): um romaneio so, com os pesos
    do ticket que o usuario indicar — pergunte qual vale;
  - **varios vagoes ou compartimentos numa pesagem so**: um romaneio por pesagem,
    nao por vagao, salvo se o usuario pedir o contrario;
  - **desconto fixo sem nome** (ex.: uma coluna "desconto" em kg numa planilha):
    pergunte ao usuario de que tipo e, antes de lancar.
- **Semente e obrigatoria.** Sem `--seed-key` o Aegro recusa. Use a cultivar do
  ticket ou a generica da cultura da safra (`aegro elements list --category SEED`).
- **Nomes dos descontos:** rode `aegro crops harvest-discounts <safra>` e use os
  nomes que ele lista (ex.: `Impureza (%)`). Na CLI com previa, `Impureza` tambem
  casa com `Impureza (%)`.

**Primeiro, qual CLI esta instalada.** Rode `aegro harvest-logs create --help`. Se
aparecer `--discount-index`, a CLI calcula pela previa do servidor e o padrao e
`AUTOMATIC` — siga "CLI com previa". Se nao aparecer, siga "CLI antiga": nela o
`AUTOMATIC` grava sem desconto nenhum, milhares de quilos a mais, com sucesso na
resposta.

**Taxa do desconto nao e teor da classificacao.** O ticket imprime o teor medido
("umidade 14,2") e o desconto aplicado ("desconto 1,7%" ou em kg). `--discount
"Umidade=1.7%"` e o **percentual do desconto** (ou `"Umidade=340kg"`, o peso); o
teor vai em `--discount-index "Umidade=14.2"`, que so registra, nao desconta.
Nunca passe o teor em `--discount` com `%`. Na CLI antiga, deixe o teor na
observacao.

**CLI com previa: `AUTOMATIC`, conferido contra o liquido do ticket.** Informe
bruto, tara, cada linha de desconto do ticket e, em `--net-weight`, o **liquido
impresso no ticket**. Quando o ticket imprime taxa e peso da mesma linha, passe
os dois (`--discount "Umidade=1.7%" --discount "Umidade=340kg"`): o Aegro grava
os dois como vieram. O Aegro calcula; se o liquido calculado nao bater com o do
ticket, nada e gravado e a mensagem diz a causa que os numeros permitem afirmar
— siga o que ela disser:
- **"fecha se ... for calculado sobre o peso SEM impureza"**: o armazem usou outra
  base. Informe o **kg de cada linha** como o ticket imprime — o Aegro grava o kg
  como veio — ou peca ao usuario para ajustar a base na configuracao da safra. Se
  o ticket so imprime as taxas (sem kg), a mensagem diz isso: ou o usuario ajusta a
  base da safra pela tela e voce lanca de novo, ou `MANUAL` com os cinco pesos do
  ticket e as taxas em `--observations`;
- **"o proprio ticket nao fecha"** (linhas todas em kg): nao lance. Mostre ao
  usuario produto, linhas e liquido do papel e pergunte — nao ajuste numero para
  caber, nem em `MANUAL`;
- **"o Aegro desconta MAIS que o ticket"**: nao e desconto faltando; confira taxa
  x teor e linha repetida;
- nos outros casos: desconto do ticket que a safra nao tem como tipo (veja o
  paragrafo abaixo), base de calculo, linha esquecida. Se nada explicar, pergunte.

Diferenca maior que um quinto do produto nao e desconto: a CLI recusa sem sugerir
`MANUAL` — veja "Carga dividida" acima. Nunca calcule o liquido voce mesmo: quem
calcula e o Aegro. Exige `aegro auth login`; com API key, use o `MANUAL` abaixo.

**Desconto do ticket sem tipo na safra** (taxa de servico, taxa de recepcao,
amostra): **a CLI nao registra.** Ele nao vira linha de desconto, e a CLI nao
cadastra tipo de desconto na safra. Diga isso ao usuario e deixe ele escolher:
- cadastrar o tipo na safra pela tela e voce lancar em `AUTOMATIC`; ou
- lancar em `MANUAL` com os cinco pesos do ticket (o descontado e o total do
  ticket, com esse desconto dentro), as linhas dos tipos que a safra tem, e o
  desconto sem tipo escrito em `--observations`, ex.:
  `--observations "Taxa de servico do armazem: 2590 kg (sem tipo na safra)"`.
  A CLI avisa em `atencaoDescontoSemLinha` que as linhas somam menos que o
  descontado — e o esperado nesse caso. Se, **havendo linhas**, a parte sem linha
  passar de um quinto do produto, a CLI recusa: isso nao e desconto (carga
  dividida, ticket que nao fecha) — pergunte ao usuario.

**Ticket so com teores** (umidade 22,8, impureza 1,2 e nenhuma taxa ou peso de
desconto): nao lance com `0%`. Pergunte ao usuario se o armazem descontou e
quanto (taxa ou kg), ou se o teor esta dentro da base e o desconto e zero. Se o
ticket **imprime** o desconto como 0 (ex.: "desconto 0,00 kg"), isso ja e a
resposta: lance `0kg` sem perguntar. Leituras de qualidade que nao sao desconto
(PH, ATR, Brix, Pol) vao so em `--discount-index` (ex.: `--discount-index
"PH=77"`), sem `--discount`. No `MANUAL`, o teor de qualquer desconto tambem pode
ir sozinho em `--discount-index` (o descontado e o do ticket; o teor so registra).
O `--dry-run` lista em `teorComDescontoZero` as linhas com teor e desconto 0 — so
para conferencia: se o papel imprime o 0, siga.

```bash
# Ensaio: a previa do servidor aparece em calculadoPeloServidor e liquidoDoTicket
aegro harvest-logs create --farm "<fazenda>" \
  --crop-key crop::68dd6719e90f726622b7f549 --date 2026-03-10 \
  --crop-glebe cropGlebe::68dd6730e90f726622b7f555 --seed-key element::seed123 \
  --gross-weight 32000 --tare-weight 12000 \
  --discount "Umidade=340kg" --discount-index "Umidade=14.2" \
  --discount "Impureza=100kg" --discount-index "Impureza=1.5" \
  --net-weight 19560 --romaneio-code "ROM-2026-0042" --dry-run

# Mostrado ao usuario produto, descontos e liquido do ensaio, e confirmado, grava
aegro harvest-logs create --farm "<fazenda>" \
  --crop-key crop::68dd6719e90f726622b7f549 --date 2026-03-10 \
  --crop-glebe cropGlebe::68dd6730e90f726622b7f555 --seed-key element::seed123 \
  --gross-weight 32000 --tare-weight 12000 \
  --discount "Umidade=340kg" --discount-index "Umidade=14.2" \
  --discount "Impureza=100kg" --discount-index "Impureza=1.5" \
  --net-weight 19560 --romaneio-code "ROM-2026-0042" --execute
```

Ticket sem o liquido impresso: omita `--net-weight` e mostre ao usuario o
liquido de `calculadoPeloServidor` antes do `--execute`.

**CLI antiga, ou API key: `MANUAL` com os cinco pesos do ticket.** Passe
`--calculation-mode MANUAL` **explicito** e `--gross-weight`, `--tare-weight`,
`--product-weight` (bruto - tara), `--discounted-weight` (produto - liquido) e
`--net-weight`. Os cinco porque CLI antiga nao deriva produto nem descontado, e o
que faltar fica vazio no romaneio. **Cada linha de desconto em kg** (o ticket
imprime): no `MANUAL` o Aegro nao calcula nada, e a linha so com `%` e gravada com
peso 0 — a CLI com previa recusa; na antiga, passe sempre o kg. Mostre ao usuario
bruto - tara = produto e produto - liquido = descontado, confira que o descontado
bate com a soma dos descontos do ticket, e so entao grave. Sem o liquido do
ticket, **nao** lance na CLI antiga: peca o liquido.

Ticket que imprime so a taxa de cada desconto, sem o kg: prefira o `AUTOMATIC`
(a CLI com previa calcula o kg pela taxa e confere com o liquido do ticket). Se
tiver de ser `MANUAL` (API key ou CLI antiga), lance os cinco pesos do ticket sem
linhas de desconto e escreva as taxas em `--observations` (ex.: `"Umidade 1,7%;
Impureza 0,5% (so taxa no ticket)"`) e os teores em `--discount-index` — a CLI
avisa que o descontado nao tem linha, e e o esperado nesse caso, mesmo com
desconto alto (grao umido desconta 25% ou mais); so acima de metade do produto
ela recusa. Nunca invente o kg de uma linha.

```bash
aegro harvest-logs create --farm "<fazenda>" \
  --crop-key crop::68dd6719e90f726622b7f549 --date 2026-03-10 \
  --crop-glebe cropGlebe::68dd6730e90f726622b7f555 --seed-key element::seed123 \
  --calculation-mode MANUAL \
  --gross-weight 32000 --tare-weight 12000 --product-weight 20000 \
  --discounted-weight 440 --net-weight 19560 \
  --discount "Umidade=340kg" --discount "Impureza=100kg" \
  --romaneio-code "ROM-2026-0042" --dry-run
aegro harvest-logs create --farm "<fazenda>" \
  --crop-key crop::68dd6719e90f726622b7f549 --date 2026-03-10 \
  --crop-glebe cropGlebe::68dd6730e90f726622b7f555 --seed-key element::seed123 \
  --calculation-mode MANUAL \
  --gross-weight 32000 --tare-weight 12000 --product-weight 20000 \
  --discounted-weight 440 --net-weight 19560 \
  --discount "Umidade=340kg" --discount "Impureza=100kg" \
  --romaneio-code "ROM-2026-0042" --execute
```

**Depois de gravar, leia `avisos` e confira o liquido.** Na CLI com previa, a
saida traz `avisos` (descontado sem linha, descontado alto, taxa e kg da mesma
linha que nao batem) tambem no `--execute`: leve cada um ao usuario. O de taxa x kg
(`atencaoTaxaKg` no ensaio) quer dizer que o kg nao e a taxa aplicada ao produto
nem ao peso sem impureza — confira no ticket se o kg e daquela linha e se a taxa e
o percentual do desconto, antes do `--execute`. Leia `conferenciaDoLiquido`:
- `"conferido": true` — o liquido gravado e o previsto; cite ao usuario o
  `liquidoGravadoKg`.
- `"conferido": false` — o romaneio **foi gravado** e o liquido nao pode ser
  conferido. Nao repita o `create`; faca o que `oQueFazer` diz (`harvest-logs get`
  e comparar `totalNetWeight`) antes de dar a tarefa por feita.
- Sem esse campo (CLI antiga), rode `aegro harvest-logs get <key>` e compare
  `totalNetWeight` com o liquido do ticket.

`NET_WEIGHT_MISMATCH` quer dizer que o romaneio **existe** com outro liquido. Nao
repita o `create` (duplica a carga no estoque) e nao corrija o liquido sozinho:
produto e descontado ficariam incoerentes. Leve ao usuario os dois numeros e
peca que ele corrija no app (safra, aba Colheita) o numero do ticket que
divergiu — bruto, tara ou a linha de desconto; ao salvar, o Aegro recalcula o
liquido.

**Romaneio com destino (silo) sai em um comando so.** O `--destination-key` grava
no proprio create, e a CLI confere o silo por releitura; se a API tiver descartado
o silo, a CLI completa por PATCH. Se a completacao falhar, o comando **falha
dizendo que o romaneio ja existe**: nunca repita o `create`, use o `update` que
ele sugere, ou voce duplica o romaneio.

**Campo desconhecido no `--body` e recusado antes de enviar** (exit 4). Nao e
frescura do CLI: a API aceitaria a requisicao, descartaria o campo e
responderia sucesso — o romaneio ficaria sem o dado e a releitura pareceria
certa. Se um nome de campo for recusado, ele mudou; confira com `--help`.

**Anexo no romaneio** (foto da nota, ticket de balanca):
`aegro files attach --farm "<fazenda>" --entity harvest-log --key harvestLog::<id> --file ./ticket.jpg --execute`
(exige OAuth; releitura de conferencia inclusa). Se o `attach` falhar dizendo que
**nada foi anexado**, repetir o mesmo comando e seguro — a CLI ja tenta uma vez
sozinha em falha de conexao. Se ela disser que os arquivos **ja estao no S3**, use o
comando que ela imprime (reaproveita o upload, sem duplicar). Consulta:
`aegro files list-attachments --entity harvest-log --key harvestLog::<id>`.

### 4.6 Clima (`aegro weather`)

| Comando | Argumentos/Opcoes |
|---------|-------------------|
| `weather get <key>` | posicional |
| `weather create` | `--weather-station-key` (obrig.), `--date` (obrig.), parametros pareados abaixo |

**Parametros pareados** (ambos presentes ou ambos ausentes):
- `--precipitation` + `--precipitation-unit` (ex: `mm`)
- `--temperature` + `--temperature-unit` (simbolo: `ºC`)

**Independentes:** `--humidity` (%), `--pressure` (hPa).

> **A unidade de temperatura e o simbolo `ºC`, nao `CELSIUS`** -- `CELSIUS`
> volta `422` (`Unidade não encontrada para o símbolo 'CELSIUS'`). O `º` e o
> **ordinal masculino** (U+00BA), nao o sinal de grau `°` (U+00B0) -- a olho
> nu sao identicos. No stderr o erro sai escapado (`\u00baC`), entao grep
> pela forma acentuada nao acha. Copie o simbolo do exemplo abaixo.

```bash
aegro weather create --farm "<fazenda>" --weather-station-key asset::<id da estacao> --date 2026-03-12 \
  --precipitation 12.5 --precipitation-unit mm \
  --temperature 28.0 --temperature-unit "ºC" --humidity 65.0
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
aegro elements create-fertilizer --farm "<fazenda>" --name "MAP Granulado" --unit kg --manufacturer Mosaic
aegro elements create-seed --farm "<fazenda>" --name "TMG 2381 IPRO" --type SOY --unit kg --manufacturer TMG
```

**Opcao global:** Todos os comandos aceitam `--output` / `-o` com `json` (padrao), `table` ou `csv`.

---

## 5. Padroes e Exemplos Reais

### Formato de Chaves
```
crop::68dd6719e90f726622b7f549       cropGlebe::68dd6730e90f726622b7f555
glebe::68dd6725e90f726622b7f550      activity::68e1a3b2f4c8901234567890
element::68e2c5d6e7890abcdef12345    harvestlog::68e2b4c5d6789012345abcde
asset::6697d5988e266153a020e87f   (estacao meteorologica -- weather-station-key)
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
4. Produto = 32.000 - 12.000 = 20.000 kg
5. Armazem classifica e imprime o ticket:
   Umidade: teor 14,2%  → desconto 340 kg
   Impureza: teor 1,5%  → desconto 100 kg
   Descontado = 340 + 100 = 440 kg
   Liquido = 20.000 - 440 = 19.560 kg
6. Lance com bruto, tara, descontos e o liquido do ticket (4.5); --dry-run antes
7. Produtividade do talhao (50 ha):
   19.560 / 50 / 60 = 6.52 sc/ha   (liquido, nunca o descontado)
```

### Ciclo Completo da Safra

```
1. aegro crops list                                         → safras ativas
2. aegro crops glebes <crop_key>                            → talhoes vinculados
3. aegro activities list --crop-key <k> --type SOWING       → plantio
4. aegro activities list --crop-key <k> --type APPLICATION  → aplicacoes
5. aegro activities realizations --crop-key <k>             → execucoes reais
6. aegro harvest-logs get <key>                             → romaneios
7. Produtividade: soma dos pesos liquidos / soma areas / 60
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

## 6. Validacoes e erros comuns

**Leia a mensagem antes de chamar de bug.** Campo de enumeracao ou unidade com
valor errado volta **422 listando os valores aceitos** — inclusive `type` de
elemento e `measuringUnit`. Nao repita a chamada e **nao mande o usuario para a
interface web**: corrija o valor que a resposta nomeia.

---

## 7. Anti-padroes

1. **Listar atividades sem `--crop-key`:** Retorna TODAS as safras misturadas. Sempre filtrar por safra.

2. **Tratar `--crop-glebe-key` como se nao fosse conferido:** o servidor resolve a
   chave na escrita e **recusa com 422** o que nao existe, nao e da fazenda ou nao
   pertence a safra da atividade — e o GET seguinte devolve as mesmas chaves. Nao
   ha mais vinculo que some nem chave de outra safra gravada calada. Continue
   listando `crop-glebes list <crop_key>` para **escolher** a chave certa; so nao
   trate o 422 como bug.

3. **Confundir `plan` com `get-plan`:**
   - `activities plan <ACTIVITY_KEY>` → endpoint `/activities/{key}/plan`
   - `activities get-plan <PLAN_KEY>` → endpoint `/activities/plans/{key}`
   - Chave errada = 404 ou dados incorretos.

4. **Produtividade pelo peso errado:** use o liquido (depois dos descontos). O
   descontado (`totalDiscountedWeight`) e a soma dos descontos, e o produto ainda
   tem umidade e impureza.

5. **Ignorar paginacao:** 50 itens = provavelmente ha mais paginas.

6. **Romaneio sem `--crop-key`:** Parametro obrigatorio. Sem ele, erro de validacao.

7. **Parametros clima desemparelhados:** `--precipitation` exige `--precipitation-unit` (e vice-versa).
   Mesma regra para `--temperature`/`--temperature-unit`. Desemparelhar causa exit code 4.
