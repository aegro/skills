---
name: aegro-cadastro-safra
description: Cria uma safra no Aegro vinculando talhoes JA existentes da fazenda (tipo, periodo obrigatorio, nome padrao), usando a CLI aegro
version: 0.1.0
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

- **CLI `aegro`** configurada e **fazenda ativa** selecionada.
- **Talhoes ja cadastrados** (veja `/aegro-cadastro-talhoes`); tenha as `key`s.

## Comandos da CLI

| Acao | Comando |
|---|---|
| Listar talhoes p/ vincular | `aegro glebes list` |
| Criar safra (vinculando talhoes) | `aegro crops create --type <TIPO> --start-date <YYYY-MM-DD> --end-date <YYYY-MM-DD> [--name <nome>] [--glebe-key <key> ...]` |
| Ver a safra criada | `aegro crops get <crop_key>` |

Dica: `crops create` aceita `--dry-run` (mostra o que seria enviado, sem gravar)
e `--execute`.

## Sequencia de Passos

### 1. Escolher os talhoes a vincular

```bash
aegro glebes list
```
Selecione os talhoes da safra e guarde as `key`s. Use os talhoes **existentes** —
nao crie novos aqui.

### 2. Criar a safra

```bash
aegro crops create --type SOY \
  --start-date 2025-10-01 --end-date 2026-03-01 \
  --glebe-key glebe::aaa --glebe-key glebe::bbb
```
- **`--type`** (obrigatorio) — o `CropType` (ex.: `SOY`, `CORN`, `WHEAT`, ...).
- **`--start-date`** / **`--end-date`** (**obrigatorios**, `YYYY-MM-DD`) — inicio
  e fim da safra. **Nao ha default nem inferencia**: se faltar, e erro. (A
  convencao Aegro de ~1 ano fica a criterio de quem chama.)
- **`--name`** (opcional) — se omitido, o backend deriva o **padrao Aegro**
  `"Tipo AA/BB"` do tipo + anos de inicio/fim (ex.: `SOY` + 2025->2026 =
  **"Soja 25/26"**; mesmo ano = "Soja 25"). Informe `--name` so para um nome fora
  do padrao.
- **`--glebe-key`** (repetivel) — as `key`s dos **talhoes existentes** (passo 1) a
  **vincular**.

### 3. Conferir

```bash
aegro crops get <crop_key>
```
Confirme nome, periodo e os talhoes vinculados.

## Boas Praticas

1. **Talhoes primeiro, safra depois** — a safra vincula talhoes que ja existem;
   nao cria talhao.
2. **Reutilize os mesmos talhoes entre safras** — a cada ano a safra nova
   vincula os talhoes existentes; nao recadastre.
3. **Datas obrigatorias** — informe `--start-date` e `--end-date`.
4. **Deixe o nome no padrao** — omita `--name` para o "Soja 25/26" automatico,
   exceto quando quiser um nome proprio.
5. **Vincule os talhoes na criacao** (`--glebe-key`) — evita religar depois.

## Limitacoes

- A safra **nao cria talhao**; se um talhao faltar, cadastre em
  `/aegro-cadastro-talhoes` antes.
- `--type` deve ser um `CropType` valido.

## Proximos Workflows

| Situacao | Proximo workflow |
|---|---|
| Cadastrar/ajustar talhoes | `/aegro-cadastro-talhoes` |
| Acompanhar a safra (talhoes, atividades) | `/aegro-agronomo` |
| Conferir panorama da fazenda | `/aegro-visao-geral` |
