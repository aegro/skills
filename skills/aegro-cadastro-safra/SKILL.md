---
name: aegro-cadastro-safra
description: Cria uma safra no Aegro vinculando talhoes JA existentes da fazenda (tipo, periodo obrigatorio, nome padrao), usando a CLI aegro
---

# Cadastro de Safra no Aegro

## Objetivo

Criar uma **safra** vinculando **talhoes que ja existem** na fazenda. Todas as
operacoes sao feitas pela **CLI `aegro`**.

## A safra REUTILIZA talhoes existentes (nao cria talhoes)

> **Talhoes sao entidades persistentes da fazenda, cadastradas uma vez e
> reutilizadas por varias safras ao longo dos anos.** A safra apenas **vincula**
> talhoes que ja existem — ela **nao cria** talhao. A cada safra, os mesmos
> talhoes voltam a ser vinculados (ex.: "T-01" entra na Soja 24/25 e de novo na
> Soja 25/26).

Portanto, **antes de criar a safra**, tenha os talhoes cadastrados e em maos:
liste-os com `aegro glebes list` e use as `key`s deles em `--glebe-key`. Se algum
talhao ainda nao existe, cadastre-o primeiro em **`/aegro-cadastro-talhoes`**
(sem duplicar os que ja existem) e so entao crie a safra.

## Quando Usar

- Os talhoes ja estao cadastrados e preciso **criar a safra** (ex.: "Soja 25/26").
- Preciso **vincular talhoes existentes** a uma nova safra.

Para **cadastrar os talhoes** (manual ou por KML), va para
`/aegro-cadastro-talhoes` primeiro.

## Pre-requisitos

- **Carregue antes o domain skill `/aegro-agronomo`** (dominio de safras e
  talhoes) — segue o padrao das skills de workflow do Aegro.
- **CLI `aegro`** configurada e **fazenda ativa** selecionada.
- **Talhoes ja cadastrados** (veja `/aegro-cadastro-talhoes`); tenha as `key`s.

## Comandos da CLI

| Acao | Comando |
|---|---|
| Listar safras existentes (evitar duplicar) | `aegro crops list` |
| Listar talhoes p/ vincular | `aegro glebes list` |
| Criar safra (vinculando talhoes) | `aegro crops create --type <TIPO> --name <nome> --start-date <YYYY-MM-DD> --end-date <YYYY-MM-DD> [--glebe-key <key> ...] [--measuring-unit <un>] [--stock-location-key <key>]` |
| Ver a safra criada | `aegro crops get <crop_key>` |

Dica: `crops create` aceita `--dry-run` (mostra o que seria enviado, sem gravar)
e `--execute`.

## Sequencia de Passos

### 1. Escolher os talhoes a vincular

Antes, confira se a safra ja nao existe (evite duplicar): `aegro crops list`.
Depois liste os talhoes:

```bash
aegro crops list --farm "<fazenda>"        # a safra ja existe? entao nao recrie
aegro glebes list --farm "<fazenda>"       # talhoes a vincular
```
Selecione os talhoes da safra e guarde as `key`s. Use os talhoes **existentes** —
nao crie novos aqui.

> **`crops list` e `glebes list` sao paginados (50 por pagina).** Antes de
> concluir que a safra "nao existe" ou que faltam talhoes, **pagine ate esgotar**
> (`--page 2`, `--page 3`... ate a pagina vir vazia). Em fazendas maiores, olhar
> so a pagina 1 gera safra duplicada ou deixa talhoes de fora do vinculo.

### 2. Criar a safra

```bash
aegro crops create --farm "<fazenda>" --type SOY --name "Soja 25/26" \
  --start-date 2025-10-01 --end-date 2026-03-01 \
  --glebe-key glebe::aaa --glebe-key glebe::bbb
```
- **`--type`** (obrigatorio) — o `CropType` (ex.: `SOY`, `CORN`, `WHEAT`, ...).
- **`--name`** (**obrigatorio**) — o nome da safra. Siga a **convencao Aegro
  "Tipo AA/BB"** (ex.: Soja + 2025->2026 = **"Soja 25/26"**; mesmo ano = "Soja
  25"). O backend nao deriva nem traduz: o nome que voce passar e o que fica.
- **`--start-date`** / **`--end-date`** (**obrigatorios**, `YYYY-MM-DD`) — inicio
  e fim da safra. **Nao ha default nem inferencia**: se faltar, e erro. (A
  convencao Aegro de ~1 ano fica a criterio de quem chama.)
- **`--glebe-key`** (repetivel) — as `key`s dos **talhoes existentes** (passo 1) a
  **vincular**.
- **`--measuring-unit`** (opcional) — unidade de medida da safra (ex.: `"sc 60Kg"`,
  `"kg"`). **Se omitido, usa a unidade padrao do tipo de cultura** (ex.: SOY →
  sacas de 60kg).
- **`--stock-location-key`** (opcional) — local de estoque (ex.:
  `stockLocation::<id>`). **Se omitido, usa o estoque padrao da fazenda.** Se
  informar um local que nao e da fazenda, retorna 422.

> **Descontos de colheita:** a safra **herda automaticamente os descontos padrao**
> quando voce nao os informa (o servidor resolve, nao a CLI): se ja existe uma
> safra do mesmo tipo, copia os descontos dela; senao, aplica os descontos padrao
> daquele tipo de cultura (umidade, impureza, etc.). Nao ha flag pra isso no
> `crops create` — e feito no serv-core na criacao.

### 3. Conferir

```bash
aegro crops get --farm "<fazenda>" <crop_key>
```
Confirme nome, periodo e os talhoes vinculados.

## Boas Praticas

1. **Talhoes primeiro, safra depois** — a safra vincula talhoes que ja existem;
   nao cria talhao.
2. **Reutilize os mesmos talhoes entre safras** — a cada ano a safra nova
   vincula os talhoes existentes; nao recadastre.
3. **Datas obrigatorias** — informe `--start-date` e `--end-date`.
4. **Nomeie no padrao** — `--name` e obrigatorio; siga a convencao "Soja 25/26"
   (Tipo AA/BB). O backend nao gera nome automatico.
5. **Vincule os talhoes na criacao** (`--glebe-key`) — evita religar depois.

## Limitacoes

- A safra **nao cria talhao**; se um talhao faltar, cadastre em
  `/aegro-cadastro-talhoes` antes.
- `--type` deve ser um `CropType` valido.

## Entregue o Link da Safra

Depois de criar a safra, ofereca o link — o `crops create` devolve `key` e
`farmKey`:

```
{host}/farm/{farmId}/crop/{cropId}#crop-dashboard
```

Trocando a aba conforme o que a pessoa vai fazer em seguida: `crop-map`
(conferir os talhoes no mapa), `crop-manage` (atividades), `crop-inputs`,
`crop-harvest`.

Para um talhao **dentro** da safra, o caminho e
`{host}/farm/{farmId}/crop/{cropId}/glebe/{glebeId}` — e o `{glebeId}` vem
do campo **`glebeKey`** do `crop-glebes list`, nunca do `key` (que e o
`cropGlebe::`). Usar o `key` gera link quebrado.

Regras que nao podem ser puladas (detalhe em `/aegro-operacional`, secao
"Link Direto para a Entidade"): host vem do `--env` da sessao
(`https://app.aegro.com.br` em prod, `https://app.staging.aegro.io` em
staging), a URL usa a chave **sem** o prefixo `tipo::`, e link com aba
invalida **nao da erro** — cai na home da fazenda em silencio. Nunca invente
template por analogia.

## Proximos Workflows

| Situacao | Proximo workflow |
|---|---|
| Cadastrar/ajustar talhoes | `/aegro-cadastro-talhoes` |
| Acompanhar a safra (talhoes, atividades) | `/aegro-agronomo` |
| Conferir panorama da fazenda | `/aegro-visao-geral` |
