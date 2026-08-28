---
name: aegro-importacao-patrimonio
description: >-
  Importa a frota e os bens de uma fazenda para o Aegro pela CLI a partir de
  uma planilha no modelo Aegro: valida e mapeia as colunas, mostra previa para
  conferencia e cria os ativos sem duplicar. Use quando pedirem "importar
  patrimonio", "subir a frota", "cadastrar maquinas em lote", "planilha de
  patrimonio"; EN "import assets in bulk". NAO use para cadastrar um ativo so
  (use /aegro-cadastro-patrimonio) nem para importar fornecedores (use
  /aegro-importacao-fornecedores).
---

# Importacao de Patrimonio em Lote

## Objetivo

Importar a frota e os bens de uma fazenda de uma vez, a partir de uma planilha
no modelo Aegro de importacao de patrimonio. Le a planilha, valida e mapeia as
colunas, mostra uma previa para conferencia e cria os ativos via CLI, evitando
duplicatas.

## Quando Usar

- Migracao inicial: cadastrar a frota existente de um cliente de uma so vez
- Cliente entrega uma planilha de bens (Excel) para subir no Aegro
- Cadastro em lote de muitas maquinas/veiculos/benfeitorias

Para cadastrar **um** ativo isolado, use `/aegro-cadastro-patrimonio`.

## Pre-requisitos

Carregue antes de iniciar:

- **`/aegro-patrimonial`** — vocabulario, modelo de dados, regras e comandos
- **`/aegro-cadastro-patrimonio`** — fluxo de cadastro individual (esta skill o aplica em lote)

Tambem:

- Fazenda selecionada (`aegro farms info` para confirmar)
- Planilha no modelo (abas `Dados` e `Dicionário`)
- Para ler a planilha, use a skill **`xlsx`**

## Modelo da Planilha

Duas abas:

- **`Dados`** — uma linha por ativo. A linha 1 e cabecalho; pode haver uma
  linha em branco antes. Linhas totalmente vazias devem ser ignoradas.
- **`Dicionário`** — tabelas de referencia de `type` e `sub_type` (apenas
  consulta; nao e importada).

### Colunas da aba `Dados` -> flags do CLI

| Coluna planilha | Flag CLI | Observacao |
|---|---|---|
| `nome` | `--name` | Obrigatorio. Linha sem nome = ignorar |
| `tipo` | (define o comando `create-*`) | Ver tabela abaixo |
| `sub_tipo` | `--machine-type` | Apenas para `tipo = Máquina` |
| `é um implemento` | `--is-implement` | `SIM` -> aplica a flag; `NÃO`/vazio -> omite. So vale para Máquina e Benfeitoria |
| `data de aquisição` | `--acquisition-date` | Formato `YYYY-MM-DD`. Converter datas com hora (ex: `2015-06-16 00:00:00` -> `2015-06-16`) |
| `modelo` | `--tag-or-model` | |
| `fabricante` | `--manufacturer` | Recomendado (ver anti-padrao #3 do dominio) |
| `horimetro/odometro` | `--hourmeter` **ou** `--odometer` | `--odometer` so para Veículo; demais usam `--hourmeter` |
| `ano de fabricação` | `--manufacture-year` | Inteiro |
| `valor (R$)` | `--value` + `--currency BRL` | Numerico |
| `vida útil (h/km)` | `--life-span` (+ `--life-span-unit`) | Unidade default: `km` para Veículo, `h` para os demais |
| `observação/chassi` | `--observations` | Chassi/serie costuma vir aqui |

### `tipo` -> comando

| `tipo` na planilha | Comando | Asset type |
|---|---|---|
| `Máquina` | `aegro assets create-machine` | MACHINE (exige `--machine-type`) |
| `Veículo` | `aegro assets create-vehicle` | VEHICLE (usa `--odometer`) |
| `Silo` | `aegro assets create-garner` | GARNER |
| `Benfeitoria` | `aegro assets create-immobilized` | IMMOBILIZED |
| `Pivô` | `aegro assets create-pivot` | PIVOT |
| `Estação Meteorológica` | `aegro assets create-weather-station` | WEATHER_STATION |

### `sub_tipo` -> `--machine-type` (somente Máquina)

| `sub_tipo` na planilha | `--machine-type` |
|---|---|
| `Trator` | `TRACTOR` |
| `Pulverizador` | `SPRAYER` |
| `Colheitadeira` | `HARVESTER` |
| `Adubador` | `FERTILIZER` |
| `Semeadeira` | `PLANTER` |
| `Arado` | `TILLER` |
| `Vagão` | `WAGON` |
| `Outro` | `OTHER` |
| `Não é uma Máquina` | — (so aparece quando `tipo` != Máquina; ignorar) |

## Ordem Obrigatoria: Lote Pequeno -> Verificacao -> Resto

Importacao em prod mexe em dados **reais** do cliente e **nao tem delete em
lote** — um mapeamento errado e trabalhoso de desfazer (um `update-*` por
ativo). A protecao **nao** e importar em staging antes: aquele ambiente e
reposto de producao todo dia as 03:15 BRT, entao a carga de la desaparece e nao
prova que a de prod vai valer. O que limita o estrago e o tamanho do primeiro
lote. Siga sempre esta ordem:

1. **Importe um lote pequeno primeiro** (5 a 10 ativos), no ambiente do
   trabalho, escolhido para **cobrir cada caso** da planilha: cada `tipo`
   presente, o mapeamento `sub_tipo -> machineType`, uma data que precise de
   conversao, `isImplement`, valor/medidor.
2. **Verifique por leitura** — nao confie so no "criado com sucesso". Confira no
   App ou via `aegro assets get <key>` que os campos chegaram como esperado (e
   nao, por exemplo, uma data invalida virando erro). Ha caminho de escrita no
   Aegro que responde sucesso sem que a alteracao valha, e a releitura e o que
   separa um do outro.
3. **So depois que a amostra conferir**, importe o resto, apos confirmacao
   explicita do usuario.

> Um ensaio em `staging` (`--env staging`) continua util para **conhecer o
> comando** e ver a forma da saida — e as chaves de la sao as mesmas de
> producao, porque o ambiente e uma copia. Mas o que voce **criou** la morre no
> restore das 03:15 BRT: nao use como validacao.

Essa ordem existe para pegar bugs de mapeamento (ex: data so com hora gerando
400, `machineType` faltando gerando 422) numa duzia de ativos, e nao na planilha
inteira do cliente.

## Fluxo de Importacao

> Rode este fluxo inteiro **no ambiente do trabalho**, comecando por um lote
> pequeno: o passo 5 cria a amostra e o 5b confere por leitura. So depois da
> conferencia vai o resto (ver secao acima). O `--env` controla o alvo.

### 1. Ler a planilha

Use a skill `xlsx` para extrair a aba `Dados`. Descarte a linha de cabecalho e
todas as linhas sem `nome`. Conte quantos ativos validos existem antes de seguir.

### 2. Validar e mapear

Para cada linha:

- `nome` preenchido (senao pular e registrar no relatorio)
- `tipo` reconhecido (senao marcar como erro)
- Se `tipo = Máquina`: `sub_tipo` deve mapear para um `machineType` valido.
  **Sem `--machine-type` a API retorna 422** (regra do dominio)
- Normalizar `é um implemento`: `SIM` -> flag; resto -> sem flag
- Converter `data de aquisição` para `YYYY-MM-DD`. **So envie se for uma data
  real**: planilhas as vezes trazem so a hora (`00:00`/`00:00:00`) sem data —
  nesses casos omita `--acquisition-date` (enviar `00:00:00` resulta em 400)
- Converter `ano de fabricação` e `valor` para numero. **Trate `0` como
  ausente**: nao envie `--manufacture-year 0` nem `--value 0` (planilhas usam
  `0` como "nao informado"). Omita a flag nesses casos.
- Escolher medidor: Veículo -> `--odometer`; demais -> `--hourmeter`

### 3. Previa para conferencia

Mostre uma **tabela de previa** (nome, tipo, machineType, fabricante, ano,
valor, medidor) e o total a criar, mais a lista de linhas puladas/com erro.
**Peca confirmacao explicita do usuario antes de criar qualquer coisa.**

Esta confirmacao e obrigatoria: importacao mexe em dados reais do cliente e e
trabalhosa de desfazer (nao ha delete em lote).

### 4. Dedup

Antes de criar, liste o que ja existe e pule duplicatas por nome:

```bash
# cubra TODOS os tipos presentes na planilha - um list por tipo (--env do alvo):
aegro assets list --farm "<fazenda>" --env prod --type MACHINE --output json
aegro assets list --farm "<fazenda>" --env prod --type VEHICLE --output json
aegro assets list --farm "<fazenda>" --env prod --type GARNER --output json
aegro assets list --farm "<fazenda>" --env prod --type IMMOBILIZED --output json
aegro assets list --farm "<fazenda>" --env prod --type PIVOT --output json
aegro assets list --farm "<fazenda>" --env prod --type WEATHER_STATION --output json
# ou: aegro assets list --env prod --search "<nome>"  para conferir um nome especifico
```

Compare nomes de forma tolerante (ignorando acento/maiusculas). Alerte o usuario
sobre cada nome ja existente e nao recrie.

### 5. Criar em lote

Crie um ativo por linha com o comando do tipo. Exemplos:

```bash
# Maquina (trator) com vida util em horas
aegro assets create-machine --farm "<fazenda>" \
  --name "TRATOR MF 4297/4K" \
  --machine-type TRACTOR \
  --manufacturer "MASSEY FERGUSON" \
  --manufacture-year 2014 \
  --acquisition-date 2015-06-16 \
  --value 180000 --currency BRL \
  --life-span 12000 --life-span-unit h \
  --tag-or-model "MF 4297/4K" \
  --observations "RAAT0008JEC003320"

# Implemento (semeadeira)
aegro assets create-machine --farm "<fazenda>" \
  --name "PLANTADEIRA JD 1109" \
  --machine-type PLANTER \
  --manufacturer "JOHN DEERE" \
  --is-implement \
  --manufacture-year 2016 \
  --value 250000 --currency BRL

# Veiculo (usa hodometro e vida util em km)
aegro assets create-vehicle --farm "<fazenda>" \
  --name "Hilux CD 4x4" \
  --manufacturer "Toyota" \
  --manufacture-year 2024 \
  --value 320000 --currency BRL \
  --odometer 15000 \
  --life-span 300000 --life-span-unit km

# Pivo
aegro assets create-pivot --farm "<fazenda>" \
  --name "Pivo Central Talhao 5" \
  --manufacturer "Valley" \
  --value 650000 --currency BRL
```

**Importacao segura (recomendado para lotes):** com `AEGRO_SAFE_MODE=1`, rode a
primeira linha com `--dry-run` para validar o payload, depois use `--execute`
nas criacoes. Capture a `key` retornada de cada ativo.

**Alvo:** `--env` explicito em **todo** comando, apontando para o ambiente do
trabalho (ver "Ordem Obrigatoria: Lote Pequeno -> Verificacao -> Resto"). Comece
pelo lote pequeno; os mesmos comandos servem para o resto da carga.

### 5b. Verificar (obrigatorio apos o lote pequeno)

Depois de criar a amostra, **confira por leitura** — nunca pela mensagem de
sucesso — antes de mandar o resto. Use as chaves capturadas:

```bash
aegro assets get --farm "<fazenda>" <key> --env prod --output table
# ou conferir por tipo:
aegro assets list --farm "<fazenda>" --env prod --type MACHINE --output table
```

Cheque uma amostra que cubra cada `tipo`, o `machineType`, datas, `isImplement`
e valor/medidor. So importe o resto quando a amostra estiver correta.

### 6. Relatorio final

Apresente:

- Criados: nome + chave retornada
- Pulados (duplicata ou sem nome)
- Erros (linha, motivo — ex: 422 por `machineType` faltando)

Guarde as chaves: nao ha listagem confiavel de abastecimentos/manutencoes
depois (Bugs #3 e #4 do dominio), entao as chaves dos ativos sao a referencia
para os proximos passos.

## Validacoes e Erros Comuns

| Situacao | Acao |
|---|---|
| Linha sem `nome` | Pular, registrar no relatorio |
| `tipo` desconhecido | Marcar erro, nao tentar criar |
| Máquina sem `sub_tipo` mapeavel | Erro — API da 422 sem `--machine-type` |
| Data com hora (`... 00:00:00`) | Converter para `YYYY-MM-DD` |
| Celula so com hora, sem data (`00:00`) | Omitir `--acquisition-date` (enviar `00:00:00` da 400) |
| `valor`/`ano` nao numericos | Limpar (remover `R$`, separadores) ou marcar erro |
| `valor` ou `ano` igual a `0` | Tratar como ausente: omitir `--value`/`--manufacture-year` |
| Veículo com horimetro | Usar `--odometer`, nunca `--hourmeter` |

## Limitacoes

- Sem endpoint de criacao em lote: cada ativo e um `create-*` separado
- Sem delete em lote: erros de importacao sao corrigidos um a um (`update-*`)
- Abastecimentos e manutencoes nao sao parte deste modelo de planilha — use
  `/aegro-cadastro-patrimonio` depois, com as chaves geradas aqui

## Proximos Workflows

- **Registrar abastecimentos/manutencoes** -> `/aegro-cadastro-patrimonio`
- **Controlar estoque de pecas/combustivel** -> `/aegro-reconciliacao-estoque`
- **Visao geral da fazenda** -> `/aegro-visao-geral`
