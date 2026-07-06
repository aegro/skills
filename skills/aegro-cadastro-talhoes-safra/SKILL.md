---
name: aegro-cadastro-talhoes-safra
description: Cadastra talhoes (manualmente ou importando de um KML) e cria safras vinculando talhoes no Aegro, pela API publica /pub/v1
version: 0.1.0
---

# Cadastro de Talhoes e Safras no Aegro

## Objetivo

Cadastrar os **talhoes** (glebas) de uma fazenda e criar uma **safra** vinculando
esses talhoes. Cobre os dois caminhos de cadastro de talhao — **manual** e
**importacao de KML** (com prevalidacao antes de gravar) — e a criacao da safra
com os padroes do Aegro (nome e periodo).

O trabalho e feito pela **API publica `/pub/v1`** (contexto de integration agent,
com escopo por fazenda).

## Quando Usar

- Preciso **cadastrar os talhoes** de uma fazenda (um a um ou em lote).
- Tenho um **KML** com os poligonos dos talhoes e quero importa-los.
- Preciso **criar uma safra** (ex.: "Soja 25/26") e **vincular** talhoes a ela.

## Pre-requisitos

- **Fazenda ja existe** e voce tem a `farmKey` dela.
- Acesso a API com os escopos de escrita: `WRITE_GLEBES` (talhoes) e
  `WRITE_CROPS` (safra). A fazenda-alvo vai no header `Aegro-Farm-Key`; a chave
  no header `Aegro-Public-API-Key`.
- Saber a **unidade de area da fazenda** (hectare `ha` ou alqueire `alq`): ela e
  definida na fazenda e as areas informadas manualmente devem estar **nessa
  unidade**. Na importacao por KML a area e calculada automaticamente.

## A API que a skill usa (`/pub/v1`)

| Acao | Endpoint | Corpo |
|---|---|---|
| Criar talhao | `POST /pub/v1/glebes` | `{ name, area:{magnitude,unit}, tag?, group?, polygon? }` |
| Previa do KML (parse, **nao persiste**) | `POST /pub/v1/glebes/kml/preview` | multipart `file=<arquivo.kml>` |
| Criar safra (vinculando talhoes) | `POST /pub/v1/crops` | `{ type, startDate, endDate, name?, glebeKeys?[] }` |

O `kml/preview` devolve uma **lista no formato do corpo de `POST /pub/v1/glebes`**
(name, area, polygon) — ou seja, os talhoes ja prontos para registrar. Nao ha
endpoint que persista KML direto: a **unica via de escrita** de talhao e o
`POST /pub/v1/glebes` (um por talhao).

## Fluxo de Decisao

```
Fazenda (tenho a farmKey)
        |
1. Cadastrar TALHOES
   |
   +-- Tenho um KML dos talhoes?  --> PREVIA /pub/v1/glebes/kml/preview
   |      (parseia -> payloads prontos p/ criar; NAO persiste; area geodesica)
   |      valida/edita a lista --> POST /pub/v1/glebes p/ CADA talhao (persiste)
   |
   +-- Nao tenho KML             --> POST /pub/v1/glebes  (um por talhao)
          (name + area na UNIDADE DA FAZENDA; group/poligono opcionais)
        |
2. CONFERIR os talhoes criados (nomes, areas, total) via GET
        |
3. Criar a SAFRA
   |  escolher o tipo (CropType), informar inicio e fim, e vincular os talhoes
   |  nome default "Tipo AA/BB" (ex.: "Soja 25/26"); datas (inicio/fim) obrigatorias
        |
4. CONFERIR a safra e os vinculos (glebeKeys) via GET
```

## Sequencia de Passos

### 1. Cadastrar os talhoes

**Caminho A — KML (preferivel quando existe). Fluxo: previa -> validar ->
criar.**

1. **Previa (parse, nao persiste):** `POST /pub/v1/glebes/kml/preview`
   (multipart, campo `file`). O servidor parseia o arquivo e devolve uma
   **lista de talhoes ja no formato do corpo de `POST /pub/v1/glebes`** (nome,
   area geodesica ja na unidade da fazenda, poligono) **sem gravar nada**. Cada
   `<Placemark>` com poligono vira um item: o **nome** sai do placemark (sem
   nome vira "Talhao N"), o **poligono** sai das coordenadas e a **area** e
   calculada da geometria (geodesica) e convertida para a unidade da fazenda.
   Placemarks sem poligono (pontos) sao ignorados.
2. **Validar:** revise a lista (nomes e areas) antes de gravar; ajuste se
   necessario.
3. **Criar (persistir):** para **cada** talhao aprovado, envie o item ao
   `POST /pub/v1/glebes` (o payload da previa ja esta no formato certo — pode
   editar antes, ex.: setar `group`). Esse e o unico endpoint que grava talhao.

**Caminho B — manual.** Para cada talhao, `POST /pub/v1/glebes` com:
- **`name`** (obrigatorio) — o nome do talhao.
- **`area`** `{ magnitude, unit }` (obrigatorio) — o valor (`magnitude`) **na
  unidade da fazenda** (`unit` = `ha` ou `alq`). Confirme a unidade antes; nao
  misture.
- **`group`** (opcional) — o `id` de um talhao "pai" para agrupar talhoes.
- **`polygon`** (opcional) — lista de pares `[lat, lng]` se voce tiver a borda.
- **`tag`** (opcional) — etiqueta livre.

### 2. Conferir os talhoes

`GET /pub/v1/glebes` e valide nomes, areas e o total esperado da fazenda antes
de criar a safra. Se algo veio errado do KML (nome vazio, area destoante),
corrija/recadastre antes de seguir.

### 3. Criar a safra vinculando os talhoes

`POST /pub/v1/crops` com:
- **`type`** (obrigatorio) — o `CropType` (ex.: `SOY`, `CORN`, `WHEAT`, ...).
- **`name`** (opcional) — se omitido, o backend deriva o **padrao Aegro**
  `"Tipo AA/BB"` a partir do tipo e dos anos de inicio/fim (ex.: `SOY` +
  2025->2026 = **"Soja 25/26"**; mesmo ano = "Soja 25"). Informe `name` so
  quando quiser um nome fora do padrao.
- **`startDate`** / **`endDate`** (**obrigatorios**, ISO `yyyy-MM-dd`) — o
  periodo da safra (inicio e fim). Nao ha default nem inferencia: se faltar,
  retorna **422**. (Convencao Aegro de ~1 ano fica a criterio de quem chama.)
- **`glebeKeys`** — a lista de `id`s dos talhoes (do passo 2) a **vincular** a
  safra.

### 4. Conferir a safra

`GET /pub/v1/crops` e confirme o nome, o periodo e os talhoes vinculados.

## Boas Praticas

1. **KML antes de manual** — quando ha KML, importe: menos digitacao, poligono e
   area corretos de uma vez.
2. **Sempre passe pela previa antes de criar** — e o passo que deixa validar o
   que o KML traria; so chame o `POST /pub/v1/glebes` depois de conferir.
3. **Area sempre na unidade da fazenda** — confirme `ha` vs `alq` antes de
   cadastrar manualmente; a API nao adivinha a unidade.
4. **Conferir antes de criar a safra** — talhao errado vira safra errada.
5. **Deixe o nome da safra no padrao** — omita `name` para o "Soja 25/26"
   automatico, exceto quando quiser um nome proprio.
6. **Vincular os talhoes na criacao da safra** (`glebeKeys`) — evita religar
   depois.

## Limitacoes / Dependencias

- **KML** importa apenas `<Placemark>` com **poligono**; pontos e linhas sao
  ignorados. A ordem das coordenadas do KML e `lng,lat` (tratada internamente).
- **Area do KML** e uma aproximacao geodesica (esferica, WGS84); para talhoes
  pequenos e ok, mas confira quando a precisao for critica.
- **Unidade de area manual**: o valor e interpretado na unidade da fazenda; nao
  ha conversao automatica de um `ha` informado numa fazenda em `alq`.
- **Escopos**: `WRITE_GLEBES` para talhoes e `WRITE_CROPS` para a safra; sem o
  escopo a chamada retorna 403.

## Proximos Workflows

| Situacao | Proximo workflow |
|---|---|
| Conferir panorama da fazenda | `/aegro-visao-geral` |
| Acompanhar a safra (talhoes, atividades) | `/aegro-agronomo` |
| Cadastro de patrimonio | `/aegro-cadastro-patrimonio` |
