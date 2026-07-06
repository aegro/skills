---
name: aegro-cadastro-safra
description: Cria uma safra no Aegro vinculando talhoes JA existentes da fazenda (tipo, periodo obrigatorio, nome padrao), pela API publica /pub/v1
version: 0.1.0
---

# Cadastro de Safra no Aegro

## Objetivo

Criar uma **safra** vinculando **talhoes que ja existem** na fazenda. O trabalho
e feito pela **API publica `/pub/v1`** (contexto de integration agent, com escopo
por fazenda).

## A safra REUTILIZA talhoes existentes (nao cria talhoes)

> **Talhoes sao entidades persistentes da fazenda, cadastradas uma vez e
> reutilizadas por varias safras ao longo dos anos.** A safra apenas **vincula**
> talhoes que ja existem — ela **nao cria** talhao. A cada safra, os mesmos
> talhoes voltam a ser vinculados (ex.: "T-01" entra na Soja 24/25 e de novo na
> Soja 25/26).

Portanto, **antes de criar a safra**, tenha os talhoes cadastrados e em maos:
liste-os com `GET /pub/v1/glebes` e use os `id`s deles em `glebeKeys`. Se algum
talhao ainda nao existe, cadastre-o primeiro em **`/aegro-cadastro-talhoes`**
(sem duplicar os que ja existem) e so entao crie a safra.

## Quando Usar

- Os talhoes ja estao cadastrados e preciso **criar a safra** (ex.: "Soja 25/26").
- Preciso **vincular talhoes existentes** a uma nova safra.

Para **cadastrar os talhoes** (manual ou por KML), va para
`/aegro-cadastro-talhoes` primeiro.

## Pre-requisitos

- **Fazenda ja existe** e voce tem a `farmKey`.
- **Talhoes ja cadastrados** (veja `/aegro-cadastro-talhoes`); tenha os `id`s.
- Acesso a API com o escopo de escrita `WRITE_CROPS`. A fazenda no header
  `Aegro-Farm-Key`; a chave no header `Aegro-Public-API-Key`.

## A API que a skill usa (`/pub/v1`)

| Acao | Endpoint | Corpo |
|---|---|---|
| Listar talhoes p/ vincular | `GET /pub/v1/glebes` | — |
| Criar safra (vinculando talhoes) | `POST /pub/v1/crops` | `{ type, startDate, endDate, name?, glebeKeys?[] }` |

## Sequencia de Passos

### 1. Escolher os talhoes a vincular

`GET /pub/v1/glebes` e selecione os talhoes da safra; guarde os `id`s deles. Use
os talhoes **existentes** — nao crie novos aqui.

### 2. Criar a safra

`POST /pub/v1/crops` com:
- **`type`** (obrigatorio) — o `CropType` (ex.: `SOY`, `CORN`, `WHEAT`, ...).
- **`startDate`** / **`endDate`** (**obrigatorios**, ISO `yyyy-MM-dd`) — inicio e
  fim da safra. **Nao ha default nem inferencia**: se faltar, retorna **422**.
  (A convencao Aegro de ~1 ano fica a criterio de quem chama.)
- **`name`** (opcional) — se omitido, o backend deriva o **padrao Aegro**
  `"Tipo AA/BB"` do tipo + anos de inicio/fim (ex.: `SOY` + 2025->2026 =
  **"Soja 25/26"**; mesmo ano = "Soja 25"). Informe `name` so para um nome fora
  do padrao.
- **`glebeKeys`** — os `id`s dos **talhoes existentes** (passo 1) a **vincular**.

### 3. Conferir

`GET /pub/v1/crops` e confirme nome, periodo e os talhoes vinculados.

## Boas Praticas

1. **Talhoes primeiro, safra depois** — a safra vincula talhoes que ja existem;
   nao cria talhao.
2. **Reutilize os mesmos talhoes entre safras** — a cada ano a safra nova
   vincula os talhoes existentes; nao recadastre.
3. **Datas obrigatorias** — informe inicio e fim; faltando, 422.
4. **Deixe o nome no padrao** — omita `name` para o "Soja 25/26" automatico,
   exceto quando quiser um nome proprio.
5. **Vincule os talhoes na criacao** (`glebeKeys`) — evita religar depois.

## Limitacoes

- A safra **nao cria talhao**; se um talhao faltar, cadastre em
  `/aegro-cadastro-talhoes` antes.
- `type` deve ser um `CropType` valido.

## Proximos Workflows

| Situacao | Proximo workflow |
|---|---|
| Cadastrar/ajustar talhoes | `/aegro-cadastro-talhoes` |
| Acompanhar a safra (talhoes, atividades) | `/aegro-agronomo` |
| Conferir panorama da fazenda | `/aegro-visao-geral` |
