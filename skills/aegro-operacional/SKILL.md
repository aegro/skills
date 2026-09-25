---
name: aegro-operacional
requires-cli: 0.28.0
description: >-
  Dominio operacional do Aegro pela CLI — fazendas, autenticacao, agrupadores
  (tags), empresas, pedidos de compra, anexos de arquivo e os links diretos
  que abrem a entidade no app. E a skill de orquestracao: define a fazenda
  explicita em toda escrita e as regras que valem entre dominios. Use quando
  pedirem "trocar de fazenda", "listar fazendas", "criar agrupador", "anexar
  arquivo", "gerar o link do lancamento", "pedido de compra"; EN "switch
  farm", "attach a file". NAO use para lancar conta (use /aegro-financeiro)
  nem para atividade de campo (use /aegro-agronomo).
---

# Dominio Operacional

Referencia completa do dominio operacional da Fazenda Aegro (`farm::5711512de4b0e15eb04da4d0`, ~67k ha).
Cobre autenticacao, gestao de fazendas, tags, empresas, ordens de compra e a orquestracao de fluxos entre dominios.

## Vocabulario

| Termo | Definicao | Exemplo |
|-------|-----------|---------|
| Farm | Propriedade rural vinculada a uma API Key. Cada token da acesso a exatamente uma fazenda | `farm::5711512de4b0e15eb04da4d0` |
| API Key | Token de integracao solicitado via token@aegro.com.br. Identifica fazenda e permissoes | Header `Aegro-Public-API-Key` |
| Tag | Marcador para categorizar recursos (patrimonios, atividades, colheitas, talhoes, etc.) | Tag "Lote Norte" tipo GLEBE |
| Relation Type | Tipo de entidade que a tag categoriza. Define permissao necessaria para criar | `MACHINE`, `VEHICLE`, `GLEBE`, `ACTIVITY`, `HARVEST_TAG`, `BILL`, `PURCHASE` |
| Company | Empresa cadastrada — fornecedor, cliente ou transportadora. Usada em financeiro e compras | Bayer CropScience (PROVIDER) |
| Purchase Order | Ordem de compra vinculada a empresa, com itens, valores e entregas | OC-2026-001 — Defensivos safra 25/26 |
| Element | Item do catalogo (defensivo, fertilizante, semente, servico, produto). Entidade cross-domain | Glifosato 480 SL (DEFENSIVE) |
| Key | Identificador unico no formato `tipo::hexstring` (ex: `farm::5711...`, `tag::abc123`, `company::def456`) | `purchaseOrder::67a1b2c3d4e5f6` |

## Autenticacao e Setup

### Hierarquia de Credenciais (prioridade)

1. **Variavel de ambiente** `AEGRO_FARMS` — JSON map `{"nome_fazenda": "api_key"}` (CI/CD)
2. **Arquivo apontado** por `AEGRO_FARMS_FILE` — caminho para arquivo JSON com mesmo formato
3. **Arquivo local** `~/.config/aegro/credentials.json` — criado por `aegro auth login`

### Arquivos de Estado

| Arquivo | Conteudo | Gerenciado por |
|---------|----------|----------------|
| `~/.config/aegro/credentials.json` | Map nome → API key | `aegro auth login` |
| `~/.config/aegro/state.json` | Fazenda selecionada, timestamp | `aegro farms select` (sombreado por `--farm`) |

### Comandos de Autenticacao

```bash
# Login interativo — solicita nome da fazenda e API key, salva em credentials.json
aegro auth login

# Verificar status da autenticacao e fazenda ativa
aegro auth status

# Remover credenciais locais
aegro auth logout
```

### Staging e reposto de producao as 03:15 BRT — o que isso muda

O ambiente de staging (`app.staging.aegro.io`) **nao e zerado: e substituido**.
Todo dia as **03:15 BRT** ele e restaurado por completo a partir de um snapshot
de producao — restore de cluster inteiro, sem merge e sem preservar o que foi
escrito la. Tres consequencias praticas, e as tres ja custaram tempo em campo:

1. **Sessoes e logins sao invalidados**: toda sessao de trabalho em staging
   comeca verificando a autenticacao, e refazer o login no dia seguinte e o
   fluxo normal.
2. **O que voce lancou la some.** A maioria dos ajustes de estoque
   conferidos por uma EV voltaram ao valor original tres dias depois. Staging
   serve para conhecer um comando novo, **nao como validacao** de que a operacao
   vai valer.
3. **As chaves sao as mesmas de producao.** Staging e uma copia, com os mesmos
   `_id`: uma chave achada la vale em prod — e a fazenda que responde em staging
   pode ser a do cliente, com os dados reais dele. O que existe so em staging e
   o **registro que voce criou depois do ultimo restore**.

```bash
# Sempre no inicio de uma sessao de staging
aegro auth status --env staging

# Se a sessao caiu (reset diario), refaca o login — comportamento esperado
aegro auth login --env staging
```

**Erro 401 em staging no inicio do dia e comportamento esperado, NAO bug.** Nao
gaste tempo diagnosticando nem reporte como falso positivo no feedback de dev —
o reset diario ja e conhecido.
So investigue um 401 de staging se ele persistir **depois** de um
`aegro auth login --env staging` bem-sucedido na mesma sessao.

### Selecao de Fazenda Ativa

A fazenda ativa vem de **duas** fontes, nesta ordem:

1. **`--farm <nome|farm::key>`** — flag aceita em **todo** comando de API. Escopo
   de uma invocacao. E a forma recomendada.
2. **`state.json`** — escrito por `aegro farms select`, global por maquina.

```bash
# Recomendado: a fazenda viaja com o comando, imune a outras sessoes
aegro farms info --farm "Fazenda Aegro"
aegro farms info --farm farm::5711512de4b0e15eb04da4d0

# Single-machine / dev — persiste em state.json global:
aegro farms select "Fazenda Aegro"

# Listar fazendas; `key` e o identificador estavel aceito por --farm, e `source`
# indica a origem da selecao ativa ("flag" | "state" | null):
aegro farms list --farm "Fazenda Aegro"

# Detalhes da fazenda ativa (chama a API):
aegro farms info --farm "Fazenda Aegro"
```

**Multi-fazenda (varias sessoes em paralelo):** com uma sessao por fazenda —
operador de servicos atendendo varios clientes — **passe `--farm` em cada
comando**. O `state.json` e global por maquina: o `farms select` de uma sessao
troca o alvo de todas as outras, silenciosamente.

**A env var `AEGRO_ACTIVE_FARM` nao existe mais.** Tres caminhos para a
mesma coisa era a propria fonte da confusao, e ela nao resolvia o caso principal:
num harness de agente, um `export` de shell **nao persiste** entre chamadas de
tool. Se a variavel ainda estiver definida no ambiente, os comandos de API falham
com `ACTIVE_FARM_ENV_REMOVED` (exit 4) em vez de operar pelo `state.json` — que
seria uma fazenda diferente da que ela indica. Remova-a e use `--farm`.

**O `--farm` aceita nome ou key.** O nome casa sem exigir caixa e acento exatos
(`"fazenda aegro"` encontra `"Fazenda Aegro"`); a key (`farm::...`, visivel em
`farms list`) e opaca e estavel, util para evitar quoting de nomes com espaco.
Nome ambiguo e recusado, nunca adivinhado. Keys so resolvem no modo OAuth.

**Escrita em safe mode exige fazenda explicita.** Com `AEGRO_SAFE_MODE=1`, uma
mutacao com `--execute` cuja fazenda veio do `state.json` falha com
`IMPLICIT_FARM_BLOCKED` (exit 4) — a mensagem traz o `--farm` pronto para repetir
o comando. Dry-run nao e bloqueado e mostra `farmSource` no envelope, indicando de
onde veio a fazenda.

**Validacao antes de operar:** rode `aegro farms list` e confirme que a fazenda
alvo aparece com `"active": true`. Se o `source` nao bater com o esperado, PARE e
investigue antes de qualquer comando de escrita — ou simplesmente passe `--farm`,
que dispensa a validacao.

**Nota:** Todo comando de dominio exige fazenda ativa. Sem nenhuma das duas
fontes, retorna exit code 2 (auth) com mensagem orientando o `--farm`.

## Formato Global da CLI

### Output

| Formato | Flag | Descricao |
|---------|------|-----------|
| JSON | `--output json` (default) | Saida estruturada para parsing por LLMs e scripts |
| Tabela | `--output table` | Formatado com Rich para leitura humana |
| CSV | `--output csv` | Para export e planilhas |

### Capturando a saida por programa (Windows)

A CLI escreve **UTF-8** no stdout, sempre, independente do code page do console
(ela reconfigura os streams na entrada). Quem captura tem que dizer isso:

```python
subprocess.run([...], capture_output=True, text=True,
               encoding="utf-8", errors="replace")
```

Sem o `encoding=`, o Python usa o encoding do locale — **cp1252 no Windows** — e
estoura `UnicodeDecodeError: 'charmap' codec can't decode byte 0x8d`. O byte muda
conforme o texto: cp1252 tem cinco bytes indefinidos (`0x81 0x8D 0x8F 0x90 0x9D`),
que em UTF-8 sao o segundo byte de `Á Í Ï Ð Ý`. Maiuscula acentuada em nome de
produto vindo de NF-e (`SAIDA`, `OLEO DIESEL`, `AGUA` em caixa alta) e a fonte
mais comum — mas nao a unica: esses mesmos bytes aparecem como continuacao de
outros caracteres, e `--output table` desenha molduras que os contem, entao a
tabela estoura sem um acento sequer. Minuscula acentuada nao estoura: vira texto
trocado, em silencio. Ou seja, o erro parece aleatorio e nao e — mas a regra de
quando ele aparece e mais larga que "tem acento maiusculo".

Isso **nao e erro do lancamento**: a escrita acontece, quem se perde e a leitura
da resposta. Numa rodada real isso interrompeu a conferencia de 32 lancamentos,
que tiveram de ser reconferidos relistando com `--launched`.

E **stdout carrega so o resultado**; log, aviso e progresso vao para stderr.
Capture os dois separados, nunca `stderr=STDOUT` — misturar quebra o parse do
JSON.

### Nomes de campo: API publica x API interna

Sao dois vocabularios, e filtrar pelo nome errado devolve **zero resultados em
silencio** — que le como "nao existe" em vez de "perguntei errado".

| Conceito | API publica (o que a CLI devolve na maioria dos comandos) | API interna (`/app/rest`) |
|---|---|---|
| valor da conta | `totalAmount`, objeto `{currencyCode, amount}` | `totalValue`, numero |
| item movimenta estoque | nao existe no recurso publico | `inputs[].stockable` |

`aegro financial bills` (listagem) e `aegro financial bill <key>` (individual)
devolvem **o mesmo shape**, os dois com `totalAmount` — conferido em producao. O
individual e ate mais completo: traz `financialCategory` inteiro, que a listagem
devolve com os campos nulos.

Antes de concluir "nao achei", confira se o campo do filtro existe na resposta:
um `.get("totalValue")` numa resposta publica devolve `None` sempre.

### Paginacao

- Padrao: **50 itens por pagina**, maximo 100
- Controle via `--page N` (inicia em 1). **Nao existe `--per-page`** no CLI: o
  tamanho da pagina e definido pela API.
- Resposta inclui metadata: `totalItems`, `totalPages`, `currentPage`

### Formato de Chaves

Todas as chaves seguem o padrao `tipo::hexstring`:

```
farm::5711512de4b0e15eb04da4d0
tag::67a1b2c3d4e5f67890abcdef
company::5f8e3c1a2b4d6e7890f12345
purchaseOrder::67a1b2c3d4e5f6
element::5a9c2d3e4f5b6a7890cdef12
asset::57d299c3e4b059f24e3f99b0
crop::68dd6719e90f726622b7f549
```

### Link Direto para a Entidade (deep link)

Depois de criar ou editar algo, **ofereca ao usuario o link que abre aquela
entidade** no navegador. Monte o link a partir do que o proprio comando devolveu:
nao existe `aegro link` nem endpoint que resolva isso.

Host pelo `--env` da sessao — nunca use o `AEGRO_API_BASE_URL`:

| env | host |
|-----|------|
| prod | `https://app.aegro.com.br` |
| staging | `https://app.staging.aegro.io` |

**A lista abaixo e FECHADA.** So estas entidades tem link direto no Aegro:

| Entidade | Template | Abre |
|----------|----------|------|
| Conta (bill) | `/farm/{farmId}?billId={billId}#farm-finance` | dialogo "Editar lancamento" da conta |
| Patrimonio | `/farm/{farmId}?assetId={assetId}#farm-assets` | ficha do patrimonio |
| Safra | `/farm/{farmId}/crop/{cropId}#crop-dashboard` | a safra |
| Talhao | `/farm/{farmId}/glebe/{glebeId}` | o talhao |
| Talhao (formulario) | `/farm/{farmId}/edit-glebe/{glebeId}` | "Editar area" carregado — prefira a linha acima, este abre como "Area excluida" em talhao sem geometria |
| Talhao na safra | `/farm/{farmId}/crop/{cropId}/glebe/{glebeId}` | o talhao dentro da safra |
| Item de estoque | `/farm/{farmId}?elementId={elementId}&locationId={locationId}&tab=stockItemHistory#farm-stock` | "Historico de item" do insumo naquele local |

Abas (`#`) alternativas da safra, quando fizer sentido: `crop-manage`,
`crop-inputs`, `crop-costs`, `crop-realized-costs`, `crop-harvest`, `crop-scout`,
`crop-map`, `crop-outcomes`.

Quatro regras, todas ja custaram link quebrado:

1. **Tire o prefixo da chave.** A URL usa so o hexstring:
   `bill::68d29a2e556faf2b209a0c20` -> `?billId=68d29a2e556faf2b209a0c20`.
2. **Talhao na safra usa o `glebeKey`, NAO a chave `cropGlebe::`.** O
   `crop-glebes list` devolve os dois campos: use `cropKey` + `glebeKey` e ignore
   o `key`.
3. **A API interna fala outro dialeto.** `received-fiscal-documents launch-bill`,
   `purchase-orders create-bill`, `financial settle` e `bank-reconciliation`
   devolvem `id`/`farmId` (ja sem prefixo) no lugar de `key`/`farmKey`. Leia os
   dois.
4. **Link errado nao da erro — ele mente.** Aba desconhecida (ou sem permissao)
   cai na home da fazenda e reescreve a URL, sem aviso nenhum. Por isso: **nunca
   invente template por analogia.** `?billId=` funcionar nao implica que
   `?harvestLogId=` ou `?purchaseOrderId=` funcionem — eles nao existem.

**Quando a entidade nao esta na tabela** (abastecimento, manutencao, romaneio,
pedido de compra, atividade, parcela, NF-e, pecuaria, empresa, elemento, categoria
financeira, agrupador, conta bancaria): diga que **nao existe link direto para
isso no Aegro**. Se ajudar, ofereca a secao — dizendo que e a secao, nunca
apresentando lista como se fosse a entidade.

Ao entregar o link, diga o que ele abre. **Regra de uso unico so vale para os
tres links com parametro de consulta** (Conta, Patrimonio, Item de estoque):
o parametro (`?billId=`, `?assetId=`, `?elementId=&locationId=`) e consumido
ao abrir, entao recarregar a pagina nao reabre o dialogo/ficha. Os links de
Safra e Talhao usam parametro de rota (`/crop/{cropId}`, `/glebe/{glebeId}`):
nao sao consumidos, e recarregar ou reabrir funciona normalmente.

```bash
# Criou a conta e o comando devolveu key + farmKey:
#   {"key": "bill::68d29a2e556faf2b209a0c20",
#    "farmKey": "farm::5711512de4b0e15eb04da4d0", ...}
# O link (prod) fica:
#   https://app.aegro.com.br/farm/5711512de4b0e15eb04da4d0?billId=68d29a2e556faf2b209a0c20#farm-finance
```

### Exit Codes

| Codigo | Significado | Quando |
|--------|-------------|--------|
| 0 | Sucesso | Operacao concluida |
| 1 | Erro generico | Falha inesperada, timeout, erro de rede |
| 2 | Erro de autenticacao | API key invalida, fazenda nao selecionada |
| 3 | Nao encontrado | Recurso com chave invalida ou inexistente |
| 4 | Erro de validacao | Campos obrigatorios faltando, formato invalido |

### Erros em JSON (stderr)

Erros sao emitidos em stderr no formato JSON, nunca misturados com stdout:

```json
{"error": {"code": "VALIDATION_ERROR", "message": "Campo 'name' e obrigatorio", "details": {"field": "name"}}}
```

### Rede que intercepta HTTPS (proxy corporativo)

Em maquina de empresa cujo proxy re-assina o trafego HTTPS, o certificado que o
servidor apresenta e o do proxy — e o CLI nao confia nele por default. O caso
que mais custa tempo e o do UPLOAD (`files upload`/`attach`, `--attach`,
`--file`), porque o S3 e o unico host fora do dominio Aegro naquele caminho, e
dai a falha fica parecendo defeito do anexo.

**Da versao 0.24 em diante** o erro nomeia o problema (exit 1):

```json
{"error": {"code": "TLS_TRUST_ERROR", "message": "Certificado HTTPS rejeitado ao falar com s3.amazonaws.com. ... A rede provavelmente intercepta HTTPS (proxy/firewall corporativo) com um CA que este cliente nao conhece. Tentei: CA do operador, certifi, trust store do sistema. Aponte AEGRO_CA_BUNDLE para o certificado raiz da sua rede (peca a TI) ..."}}
```

NAO repita o comando e NAO reporte como instabilidade do Aegro — as duas coisas
so gastam tempo, porque a falha e da maquina, nao do servico. O conserto e
apontar a CA da rede:

```bash
export AEGRO_CA_BUNDLE=/caminho/para/ca-da-empresa.pem   # SSL_CERT_FILE tambem vale; AEGRO_CA_BUNDLE vence
```

O arquivo vem do suporte de TI. Se a variavel apontar para um caminho que nao
existe ou nao carrega, o CLI avisa com `CONFIG_ERROR` (exit 1) em vez de
ignorar em silencio. **Nunca sugira desabilitar a verificacao de certificado**:
nao existe flag para isso no CLI, e isso e de proposito.

**Ate a 0.23** o mesmo caso saia como `API_ERROR` com `status: 502` e a
mensagem generica `Erro de conexao com o servico Aegro: ConnectError`, que le
como servico fora do ar. Se voce ver ISSO num upload que falha sempre no mesmo
ponto, e provavelmente o mesmo problema: peca a atualizacao do CLI
(`uv tool upgrade aegro`) antes de investigar o Aegro.

### Parametros Repetiveis

Flags que aceitam multiplos valores usam repeticao:

```bash
aegro tags list --farm "Fazenda Aegro" --relation-type MACHINE --relation-type VEHICLE
aegro elements list --farm "Fazenda Aegro" --category DEFENSIVE --category FERTILIZER
```

## Referencia de comandos

### farms

| Comando | Descricao | Flags |
|---------|-----------|-------|
| `aegro farms list` | Lista fazendas; cada entrada tem `key`, `env`, `active` e `source` (`flag`/`state`/null) | `--env`, `--farm`, `--output` |
| `aegro farms select <nome>` | Persiste fazenda ativa em state.json global | `--env` |
| `aegro farms info` | Detalhes da fazenda ativa via API | `--env`, `--farm`, `--output` |

```bash
# Preferido: a fazenda viaja com o comando (imune a sessoes em paralelo)
aegro farms info --farm "Fazenda Aegro"
# {"key": "farm::5711512de4b0e15eb04da4d0", "name": "Fazenda Aegro", ...}

# Dev single-machine (persiste em state.json):
aegro farms select "Fazenda Aegro"
aegro farms info --farm "Fazenda Aegro"
```

### auth

| Comando | Descricao | Flags |
|---------|-----------|-------|
| `aegro auth login` | Setup interativo de credenciais | — |
| `aegro auth status` | Verifica autenticacao e fazenda ativa | `--env` |
| `aegro auth logout` | Remove credenciais locais | — |

### files (anexos de arquivo)

Upload generico de imagem/documento para o S3 da Aegro e vinculo do arquivo a
uma entidade, com releitura de conferencia apos o save. O upload usa a policy
assinada da API interna, entao **exige login OAuth** (`aegro auth login`) —
com API key o comando falha cedo (exit 2), antes de escrever qualquer coisa.

| Comando | Descricao | Flags |
|---------|-----------|-------|
| `aegro files upload` | Sobe um arquivo e devolve `url` (chave S3) e `urlFull` (download) | `--file/-f`, `--content-type`, `--execute` |
| `aegro files attach` | Vincula arquivo(s) a uma entidade existente | `--entity`, `--key`, `--file/-f` (sobe e vincula) ou `--url` (vincula chave S3 ja subida), `--execute` |
| `aegro files list-attachments` | Lista os anexos de uma entidade | `--entity`, `--key` |

Entidades aceitas em `--entity` (prefixo da `--key` entre parenteses):
`realization` (`activityLog::`), `fuel-supply` e `maintenance`
(`assetEvent::`), `bill`, `purchase-order`, `purchase-requisition`,
`harvest-log`, `asset`, `element`, `bank-transfer`, `livestock-lot`.
`realization`, `fuel-supply` e `maintenance` tem rota publica (vincular `--url`
funciona ate com API key); as demais usam a API interna e exigem OAuth sempre.

Tamanho: o limite e **100 MB** por arquivo (recusado localmente acima disso,
sem gastar rede). Arquivo grande funciona — 50 MB sobem em ~40 s.

Regras que evitam retrabalho:

- **Idempotencia por chave S3**: reanexar a mesma `--url` nao grava nada (a
  saida traz `saved: false` e o registro nem e tocado). Repetir `--file` sobe
  o arquivo DE NOVO e cria uma segunda copia. Se o vinculo falhar depois do
  upload, o stderr traz o comando de retry com `--url` — use ele, nunca
  repita o `--file`.
- **`totalAttachments: null` nao e zero**: significa que o anexo foi gravado
  mas a releitura de conferencia nao pode ser lida. Confira com
  `files list-attachments` antes de concluir qualquer coisa.
- Comandos de escrita tem acucar para anexar na mesma invocacao: `--attach`
  em `financial create-bill`/`update-bill`, `purchase-orders create/update` e
  `purchase-requisitions create/update`; `--file` em
  `activities create-realization`/`update-realization` e em
  `fuel-supplies`/`maintenances create/update` (no update de abastecimento e
  manutencao, `--file` ACRESCENTA). Em falha parcial (registro salvo, anexo
  nao), o `--attach` e o `--file` de abastecimento/manutencao trazem no stderr
  um JSON `ATTACH_FAILED` com `attachRetry`; o `--file` da realizacao traz o
  `files attach ... --url` em texto. Rode esse comando e **nunca repita o
  create** (duplicaria o registro).
- **Dois comandos ja anexam sozinhos, sem flag**: da **v0.24.0** em diante o
  `received-fiscal-documents launch-bill` e o `launch-purchase-order` sobem a
  DANFE da nota no proprio create (`--no-attach-danfe` desliga). Antes de
  anexar em conta ou pedido que veio de NF-e, confira com
  `files list-attachments` — anexar de novo deixa a mesma DANFE duas vezes.
  Anexo que falha ali nao derruba o lancamento: o registro nasce sem ele, e o
  envelope traz `anexo`/`anexoVerificacao` dizendo o que houve.
- **Nao da para anexar** (o CLI recusa explicando, sem gastar upload):
  planejamento de atividade (so a realizacao ganhou o campo); `shipment`
  (remessa: o servidor recusa o re-save com erro generico na maioria dos
  registros); livestock-loss/
  transfer/weighing (API sem update); e **elemento IMPORTADO** (do catalogo
  global ou de outro catalogo — o servidor recusa qualquer re-save dele; so o
  elemento criado NA FAZENDA aceita, igual a tela do app). Nesses casos, anexe
  pela tela do app.
- **Anexo em elemento e caso RARO — nao ofereca por conta propria.** Poucas
  pessoas anexam arquivo a elemento do catalogo; so faca quando o usuario
  pedir explicitamente. Quando fizer, saiba que `isImported: true` em
  `elements list` significa que NAO vai funcionar — e isso vale para pouco mais
  da metade do catalogo, com FERTILIZER perto de 100%. Detalhe por categoria em
  `/aegro-estoquista`.

### tags (= Agrupadores)

**"Agrupador" na tela e `tag` na API sao a MESMA entidade**: o que muda e o
`relationType`. A tela Cadastros > Agrupadores tem uma aba por tipo. Quem chega
pedindo "agrupador financeiro" quer `--relation-type BILL`, **nao**
`fin-categories` (aquilo e plano de contas; ver skill `aegro-financeiro`).

| Aba na tela "Agrupadores" | `--relation-type` |
|---------------------------|-------------------|
| Area | `GLEBE` |
| Atividade | `ACTIVITY` |
| Colheita | `HARVEST_TAG` |
| Identificadores de colheita | `HARVEST_IDENTIFIER` |
| **Financeiro** | **`BILL`** |
| Pecuaria | `LIVESTOCK` |
| Pedido de compra | `PURCHASE` |

> Fonte canonica das abas: `TAGS_PAGE_GROUP_ROUTE_CONFIGURATION` em
> `client-web/apps/aegroweb/src/app/presentation/page-groups/tags/tags-page-group.container.ts`.
> Existem outros tipos validos sem aba propria (patrimonio, `OBSERVATION`,
> `SCOUT_METHOD`, `SALE`, `LIVESTOCK_ACTIVITY`).

| Comando | Descricao | Flags |
|---------|-----------|-------|
| `aegro tags relation-types` | **Lista completa** de tipos + aba da tela | `--output` |
| `aegro tags get <tag-key>` | Busca agrupador por chave | `--output` |
| `aegro tags list` | Lista agrupadores com filtros | `--relation-type`, `--relation-type-raw`, `--status`, `--search-text`, `--page`, `--output` |
| `aegro tags create` | Cria agrupador | `--name` (obrig.), `--relation-type` (obrig.), `--status` |
| `aegro tags update <tag-key>` | Atualiza (patch parcial: so o que muda) | `--name`, `--relation-type` |
| `aegro tags archive <tag-key>` | Arquiva (sai da selecao, sem apagar historico) | `--dry-run`, `--execute` |
| `aegro tags unarchive <tag-key>` | Desarquiva | `--dry-run`, `--execute` |

```bash
# A lista completa de tipos vem do proprio CLI - nao decore nem copie daqui
aegro tags relation-types --output table

# Criar agrupador FINANCEIRO (a aba "Financeiro" da tela)
aegro tags create --farm "Fazenda Aegro" --name "Despesas a vista" --relation-type BILL --dry-run

# Listar os agrupadores financeiros que ja existem (SEMPRE antes de criar em lote)
aegro tags list --farm "Fazenda Aegro" --relation-type BILL --output table
```

**Tipo invalido morre no cliente:** `--relation-type` e validado localmente
(exit 4, sem chamada HTTP) e a mensagem lista os validos com a aba de cada um.
Para um tipo novo que o CLI ainda nao conhece, use `--relation-type-raw`.

**Criacao em lote a partir de planilha:** nem a API nem o CLI recusam agrupador
repetido - a deduplicacao e sua. Faca nesta ordem:

1. **Deduplique a planilha.** A identidade de um agrupador e
   `(relationType, nome normalizado)` na fazenda. Normalize o nome antes de
   comparar: corte espaco das pontas, colapse espaco interno e compare
   ignorando caixa e acento ("Adubos ", "adubos" e "ADUBOS" sao a MESMA linha).
   Reduza a planilha a esse conjunto unico.
2. **Liste o que ja existe** com `--relation-type <TIPO>` e subtraia, usando a
   mesma normalizacao do passo 1.
3. **Rode `--dry-run` e depois `--execute` so sobre o que sobrou** - o conjunto
   unico e ainda inexistente no Aegro.

Pular o passo 1 e o erro que passa pelo `--dry-run`: duas linhas iguais da
planilha viram dois agrupadores iguais, porque cada uma e um `create` valido.

Se criar errado, o desfazer e o arquivamento (nao existe `delete` no CLI):

```bash
aegro tags archive --farm "<fazenda>" tag::abc --execute     # sai da selecao, historico preservado
aegro tags unarchive --farm "<fazenda>" tag::abc --execute   # reversivel
```

**`archive`/`unarchive` exigem login OAuth** (`aegro auth login`): a API publica
nao expoe arquivamento, entao esses dois comandos usam a API interna. Fazenda
autenticada por API key falha cedo com mensagem apontando o login.

**Nao existe `--status` em `tags update`:** o PATCH da API publica nao aceita o
campo, e a flag antiga nunca teve efeito (a mudanca era descartada em silencio).
Use `aegro tags archive`.

### companies

| Comando | Descricao | Flags |
|---------|-----------|-------|
| `aegro companies get <key>` | Busca empresa por chave | `--output` |
| `aegro companies list` | Lista empresas com filtros | `--search-text`, `--fiscal-type` (alias: `--fiscal-number-type`), `--page`, `--env`, `--farm`, `--output` |
| `aegro companies create` | Cadastra nova empresa | `--name` (obrig.), `--fiscal-code` (obrig.), `--fiscal-type` (obrig.), `--type`, `--trade-name`, `--legal-name`, `--observations` |

```bash
# Cadastrar fornecedor de insumos
aegro companies create --farm "Fazenda Aegro" \
  --name "AgroInsumos Sul Ltda" \
  --fiscal-code "12.345.678/0001-90" \
  --fiscal-type CNPJ \
  --type PROVIDER
# {"key": "company::67f2b3c4d5e6a7b8", "name": "AgroInsumos Sul Ltda", ...}

# Buscar empresa por texto
aegro companies list --farm "Fazenda Aegro" --search-text "Bayer"
```

**Tipos de empresa:** `PROVIDER` (fornecedor), `CLIENT` (cliente), `TRANSPORTER` (transportadora)

### purchase-orders

| Comando | Descricao | Flags |
|---------|-----------|-------|
| `aegro purchase-orders get <key>` | Busca ordem de compra por chave | `--output` |
| `aegro purchase-orders list` | Lista ordens de compra | `--company-key`, `--start-date`, `--end-date`, `--search-text`, `--delivery-status`, `--page`, `--env`, `--farm`, `--output` |
| `aegro purchase-orders create` | Cria ordem de compra | `--order-date` (obrig.), `--currency` (obrig.), `--gross-amount` (obrig.), `--items` (obrig. JSON), `--company-key`, `--description`, `--expected-delivery-date`, `--tag` |

```bash
# Criar ordem de compra de defensivos
aegro purchase-orders create --farm "Fazenda Aegro" \
  --company-key "company::67f2b3c4d5e6a7b8" \
  --order-date "2026-03-13" \
  --currency BRL \
  --gross-amount 45000.00 \
  --description "Defensivos safra 25/26 - lote 1" \
  --items '[{"elementKey": "element::5a9c2d3e4f5b6a78", "quantity": 500, "unitPrice": 90.00}]'

# Listar compras de um fornecedor
aegro purchase-orders list --farm "Fazenda Aegro" --company-key "company::67f2b3c4d5e6a7b8" --start-date 2026-01-01
```

**Remessa lancada por engano: apague, nao compense.** `delete-shipment` apaga a
remessa **e** os lancamentos de estoque que ela gerou, no mesmo caminho. Lancar
uma segunda remessa para "corrigir" nao resolve: a primeira ja conta para o
`deliveryProgress`, e o pedido fica com entrega em dobro.

```bash
# A chave da remessa sai no get-internal do pedido
aegro purchase-orders get-internal --farm "<fazenda>" <pedido>
aegro purchase-orders delete-shipment --farm "<fazenda>" \
  --shipping-key <chave-da-remessa> --purchase-order-key <chave-do-pedido> --dry-run
aegro purchase-orders delete-shipment --farm "<fazenda>" \
  --shipping-key <chave-da-remessa> --purchase-order-key <chave-do-pedido> --execute
```

Usa a API interna (`DELETE /app/rest/shippings/{id}`) — exige `aegro auth login`.

## Orquestracao Entre Dominios

Fluxos operacionais que cruzam multiplos dominios do Aegro. A sequencia correta evita inconsistencias.

### Fluxo 1: Compra de Insumo (Operacional → Estoque → Financeiro)

```
companies create (ou usar existente)
    → purchase-orders create (vincula empresa + itens)
        → stock entry (registra entrada no deposito)
            → financial create-bill (lancamento + parcelas a pagar)
```

```bash
# 1. Garantir fornecedor cadastrado
aegro companies list --farm "Fazenda Aegro" --search-text "AgroInsumos"
# Se nao existir: aegro companies create ...

# 2. Criar ordem de compra
aegro purchase-orders create --farm "Fazenda Aegro" \
  --company-key "company::67f2b3c4d5e6a7b8" \
  --order-date "2026-03-13" \
  --currency BRL \
  --gross-amount 45000.00 \
  --items '[{"elementKey": "element::5a9c2d3e4f5b6a78", "quantity": 500, "unitPrice": 90.00}]'

# 3. Registrar entrada no estoque
aegro stock entry --farm "Fazenda Aegro" \
  --element-key "element::5a9c2d3e4f5b6a78" \
  --location-key "stockLocation::abc123" \
  --quantity 500 \
  --date "2026-03-15"

# 4. Criar o lancamento financeiro com as parcelas
# A API publica NAO expoe create/update/delete de parcela avulsa: as parcelas
# vao no campo `installments` do proprio create-bill.
# SEMPRE --dry-run primeiro: apresente o plano (valor, categoria, parcelas)
# a quem opera e so troque para --execute depois da confirmacao explicita.
aegro financial create-bill \
  --description "Compra de fertilizante - safra 25/26" \
  --total-amount 45000.00 \
  --cash-flow EXPENSE \
  --payment-method INSTALLMENT \
  --category "Insumos" \
  --bank-account-key "bankAccount::def456" \
  --installments '[{"number": 1, "dueDate": "2026-04-15", "amount": {"currencyCode": "BRL", "amount": 45000}}]' \
  --farm "Fazenda Aegro" --dry-run
# Usuario conferiu e aprovou o plano? Repita o MESMO comando com --execute.
```

### Fluxo 2: Aplicacao de Defensivo (Agronomico → Estoque)

```
activities create-plan (planeja aplicacao com insumos)
    → realizacao via Aegro App (execucao no campo)
        → consumo de estoque automatico (baixa gerada pela realizacao)
```

**Nota:** A realizacao no campo gera baixa automatica de estoque. Se o estoque nao baixou apos realizacao, verificar se a realizacao tem insumos vinculados.

```bash
# 1. Planejar aplicacao
aegro activities create-plan --farm "Fazenda Aegro" \
  --crop-key "crop::68dd6719e90f726622b7f549" \
  --type APPLICATION \
  --start-date "2026-03-15" \
  --observations "Aplicacao herbicida pre-emergente" \
  --inputs '[{"elementKey": "element::5a9c2d3e4f5b6a78", "amount": {"magnitude": 2.5, "unit": "L/HA"}}]' \
  --dry-run

# 2. Verificar realizacoes (apos execucao no campo)
aegro activities realizations --farm "Fazenda Aegro" --crop-key "crop::68dd6719e90f726622b7f549"

# 3. Conferir baixa de estoque
aegro stock logs --farm "Fazenda Aegro" --element-key "element::5a9c2d3e4f5b6a78" --start-date 2026-03-01
```

### Fluxo 3: Colheita (Campo → Financeiro)

```
harvest-logs create (registra romaneio de colheita)
    → financial create-bill (lancamento + recebivel da venda)
```

```bash
# 1. Registrar colheita
aegro harvest-logs create --farm "Fazenda Aegro" \
  --crop-key "crop::68dd6719e90f726622b7f549" \
  --date "2026-03-10" \
  --gross-weight 32000 \
  --humidity 14.5

# 2. Gerar conta a receber (venda do grao)
# SEMPRE --dry-run primeiro; --execute so apos o usuario conferir o plano.
aegro financial create-bill \
  --description "Venda de soja - safra 25/26" \
  --total-amount 192000.00 \
  --cash-flow REVENUE \
  --payment-method INSTALLMENT \
  --category "Venda de graos" \
  --bank-account-key "bankAccount::def456" \
  --installments '[{"number": 1, "dueDate": "2026-04-30", "amount": {"currencyCode": "BRL", "amount": 192000}}]' \
  --farm "Fazenda Aegro" --dry-run
# Usuario conferiu e aprovou o plano? Repita o MESMO comando com --execute.
```

### Fluxo 4: Manutencao de Patrimonio (Patrimonial → Estoque → Financeiro)

```
maintenances create (registra manutencao com pecas)
    → stock removal automatico (baixa de pecas do deposito)
        → financial create-bill (lancamento + conta a pagar do servico)
```

```bash
# 1. Registrar manutencao com pecas
aegro maintenances create --farm "Fazenda Aegro" \
  --asset-key "asset::57d299c3e4b059f24e3f99b0" \
  --date "2026-03-12" \
  --stock-location-key "stockLocation::abc123" \
  --hourmeter 1550 \
  --observations "Troca filtros + oleo - revisao 500h" \
  --inputs '[{"elementKey": "element::filtro01", "quantity": {"unit": "un", "magnitude": 2}}]'

# 2. Gerar o lancamento do servico de manutencao
# SEMPRE --dry-run primeiro; --execute so apos o usuario conferir o plano.
aegro financial create-bill \
  --description "Revisao 500h - troca de filtros e oleo" \
  --total-amount 3500.00 \
  --cash-flow EXPENSE \
  --payment-method INSTALLMENT \
  --category "Manutencao" \
  --bank-account-key "bankAccount::def456" \
  --installments '[{"number": 1, "dueDate": "2026-04-15", "amount": {"currencyCode": "BRL", "amount": 3500}}]' \
  --farm "Fazenda Aegro" --dry-run
# Usuario conferiu e aprovou o plano? Repita o MESMO comando com --execute.
```

### Fluxo 5: Custeio — Vinculo Elemento x Categoria Financeira

```
elements set-categories (vincula insumo a categoria financeira)
    → custos de atividades aparecem classificados no DRE
```

```bash
# Vincular defensivo a categoria financeira "Defensivos"
aegro elements set-categories --farm "Fazenda Aegro" \
  --element-key "element::5a9c2d3e4f5b6a78" \
  --expense-category-key "finCategory::desp_defensivos" \
  --revenue-category-key "finCategory::rec_vendas"
```

**Importancia:** Sem esse vinculo, custos de atividades nao aparecem categorizados nos relatorios financeiros (DRE).

## Entidades Cross-Domain

### Companies (Operacional + Financeiro)

A mesma empresa aparece em dois contextos:

| Contexto | Uso | Exemplo |
|----------|-----|---------|
| Operacional | Fornecedor em ordens de compra | `purchase-orders create --company-key ...` |
| Financeiro | Contraparte em contas a pagar/receber | Vinculado via bill ao fornecedor |

**Regra:** Sempre criar a empresa antes de usar em purchase-orders ou financial.

### Elements (Agronomico + Estoque + Financeiro)

Um elemento participa de tres dominios simultaneamente:

| Dominio | Papel | Comando |
|---------|-------|---------|
| Agronomico | Insumo planejado/aplicado em atividades | `activities create-plan --inputs ...` |
| Estoque | Item com posicao e movimentacoes | `stock items --element-key ...` |
| Financeiro | Custo categorizado via set-categories | `elements set-categories --element-key ...` |

**Regra:** Criar o elemento e vincular categorias financeiras antes de usar em atividades e estoque.

## Validacoes e erros comuns

### Versao do CLI: leia o aviso antes de culpar a skill

O CLI avisa no stderr quando ha versao mais nova no PyPI. **Nao engula o
aviso** — deriva de versao e a causa comum de "o comando nao aceita essa flag"
e de skill que parece errada. Se a maquina esta atras, atualize antes de
investigar:

```bash
pip install -U aegro && aegro --version
```

### Logica de Retry

A regra depende de o comando **ler** ou **escrever**:

| Tipo | Exemplos | 5xx, timeout ou queda de conexao |
|---|---|---|
| Leitura | `list`, `get`, `bills`, `installments`, qualquer busca | Pode repetir. O CLI ja retenta sozinho com backoff; se persistir, espere e tente de novo |
| Escrita | `create-*`, `update-*`, `realize`, `settle`, `launch-bill`, romaneio, abastecimento, atividade, conta | **Nao repita.** Procure o registro primeiro |

**Por que escrita e diferente:** a API grava o registro e so depois falha no
resto do processamento, e o erro que volta nao desfaz nada. "Servidor
indisponivel" numa escrita NAO quer dizer que nada foi criado — repetir as
cegas cria o registro em duplicidade, e cada nova tentativa cria outro. O CLI
nunca retenta escrita sozinho; nao retente voce.

Depois de 5xx ou timeout numa escrita, nesta ordem:

1. **Leia o `error.conferencia`, se vier.** `create-bill` e `create-bills`
   procuram a conta sozinhos (`launch-bill` tambem confere e avisa no stderr):
   - `situacao: "criada"` — a conta existe (`contas[]` traz `key` e `link`).
     Nao repita. Confira as parcelas pelo link: o erro pode ter deixado a
     conta sem parcela.
   - `situacao: "nao_criada"` com `podeRepetir: true` — conferido e nada foi
     gravado. Pode repetir.
   - `situacao: "inconclusiva"` — o CLI nao consegue afirmar (conta parecida,
     conta igual criada pouco antes, timeout sem resposta). O `motivo` diz por
     que, e `contas[]` traz as candidatas. Siga o passo 2 e mostre as candidatas
     ao usuario.
   Em CLI que traz a conferencia, o lote (`create-bills`) para na linha que
   falhou e o stdout diz o que ja foi gravado (`resultados`), de que linha
   retomar (`retomarNaLinha`) e quais linhas anteriores voltaram sem criar
   (`linhasAnterioresNaoCriadas`). Em CLI mais antigo nada disso vem: conte pela
   listagem o que ja entrou antes de qualquer coisa. Nao reenvie o arquivo inteiro:
   preserve as linhas confirmadas como criadas, corrija erros 4xx e, para 5xx ou
   timeout, confirme pela busca completa quais linhas nao foram criadas antes de
   processa-las em um novo lote.
2. **Sem conferencia, procure voce** pela listagem do dominio, filtrando pelo que
   identifica o registro: conta por data de lancamento + descricao + valor (e
   numero do documento, se houver); atividade por safra + data + tipo; romaneio
   por safra + data + peso; abastecimento por patrimonio + data + litros.
   `activities create-plan`/`create-realization` avisam o que acharam na
   listagem e dizem quando a conferencia foi parcial — parcial nao e "nao
   existe".
3. **So repita se a busca completa nao achar nada.** Depois de timeout, espere
   um minuto e busque de novo antes de repetir: o servidor pode ainda estar
   gravando. Achou: use o registro que existe (corrija com `update` se
   precisar). Achou mais de um igual: pode ser duplicata de tentativa anterior
   ou lancamento legitimo repetido — mostre as chaves ao usuario e deixe ele
   decidir; nao apague por conta propria.
4. **Se o mesmo 5xx voltar com os mesmos dados**, pare: e achado novo. Junte
   comando e resposta e reporte, em vez de tentar de novo.

Erros **4xx** (400, 401, 403, 404, 422) nunca se resolvem repetindo: corrija o
comando.

### Erros Comuns e Diagnostico

| HTTP | Significado | Acao |
|------|-------------|------|
| 500 | Erro interno do servidor | Leitura: pode repetir. **Escrita: nao repita — procure o registro primeiro** (ver "Logica de Retry"). Se persistir com os mesmos dados, e achado novo: reporte |
| 422 | Erro de validacao | Leia a mensagem: em campo de enumeracao e unidade ela **lista os valores aceitos**. Nao faz retry, e nao e bug do servidor |
| 404/204 | Recurso nao encontrado | Validar formato da chave (`tipo::hexstring`). Chave pode estar errada |
| 401 | Nao autenticado | Verificar API key com `aegro auth status`. Em **staging**, 401 no inicio do dia e esperado (reset diario) — refazer `aegro auth login --env staging` |
| 403 | Sem permissao | Token nao tem permissao para a operacao. Solicitar novo token |
| Timeout | Sem resposta em 30s | Leitura: pode repetir, a API pode estar lenta. **Escrita: o registro pode ter sido gravado — procure antes de repetir** |

### Dicas Gerais

- **Sempre validar chaves** antes de usar — formato `tipo::hexstring`, sem `/`, `?`, `#` ou espacos
- **Paginacao**: Se resultado vier vazio, verificar se `page` esta dentro de `totalPages`
- **Datas**: Sempre ISO 8601 (`YYYY-MM-DD`). Fuso horario do servidor: America/Sao_Paulo
