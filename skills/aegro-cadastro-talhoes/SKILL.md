---
name: aegro-cadastro-talhoes
description: Cadastra e mantem os talhoes (glebas) de uma fazenda no Aegro, manualmente ou importando de um KML (com previa antes de gravar), pela API publica /pub/v1
version: 0.1.0
---

# Cadastro de Talhoes no Aegro

## Objetivo

Cadastrar e manter os **talhoes** (glebas) de uma fazenda — manualmente ou
**importando um KML** (com prevalidacao antes de gravar). O trabalho e feito pela
**API publica `/pub/v1`** (contexto de integration agent, com escopo por fazenda).

## Talhoes NAO se duplicam (regra fundamental)

> **O talhao e uma entidade PERSISTENTE da fazenda, cadastrada UMA vez e
> REUTILIZADA pelas safras ao longo dos anos.** A mesma gleba entra em varias
> safras (ex.: "T-01" na Soja 24/25, depois na Soja 25/26, ...). **Nunca
> recadastre um talhao que ja existe** — nao crie um talhao novo por safra nem
> reimporte o mesmo KML criando duplicatas.

Por isso, **antes de criar qualquer talhao**:

1. **Liste os talhoes que a fazenda ja tem:** `GET /pub/v1/glebes`.
2. **Compare** com o que voce pretende cadastrar (por **nome** e, quando houver,
   pela **area/poligono**).
3. **Reutilize** os que ja existem (guarde os `id`s deles para vincular a safra)
   e **crie apenas os que faltam**.

Duplicar talhoes polui a fazenda, quebra relatorios por area e confunde o
vinculo com as safras. Na duvida se um talhao "e o mesmo", trate como o mesmo e
reutilize.

## Quando Usar

- Preciso **cadastrar os talhoes** de uma fazenda pela primeira vez.
- Tenho um **KML** com os poligonos dos talhoes e quero importa-los.
- Preciso **adicionar um talhao novo** a uma fazenda que ja tem talhoes (criando
  so o que falta, sem duplicar).

## Pre-requisitos

- **Fazenda ja existe** e voce tem a `farmKey` dela.
- Acesso a API com o escopo de escrita `WRITE_GLEBES`. A fazenda-alvo vai no
  header `Aegro-Farm-Key`; a chave no header `Aegro-Public-API-Key`.
- Saber a **unidade de area da fazenda** (`ha` ou `alq`): as areas informadas
  manualmente devem estar nessa unidade. No KML a area e calculada
  automaticamente.

## A API que a skill usa (`/pub/v1`)

| Acao | Endpoint | Corpo |
|---|---|---|
| Listar talhoes existentes (dedup!) | `GET /pub/v1/glebes` | — |
| Criar talhao | `POST /pub/v1/glebes` | `{ name, area:{magnitude,unit}, tag?, group?, polygon? }` |
| Previa do KML (parse, **nao persiste**) | `POST /pub/v1/glebes/kml/preview` | multipart `file=<arquivo.kml>` |

O `kml/preview` devolve uma **lista no formato do corpo de `POST /pub/v1/glebes`**
(name, area, polygon) — os talhoes ja prontos para registrar. Nao ha endpoint
que persista KML direto: a **unica via de escrita** de talhao e o
`POST /pub/v1/glebes` (um por talhao).

## Fluxo

```
Fazenda (tenho a farmKey)
        |
1. LISTAR talhoes existentes  --> GET /pub/v1/glebes   (evitar duplicata!)
        |
2. Cadastrar os que FALTAM
   |
   +-- Tenho KML?  --> PREVIA /pub/v1/glebes/kml/preview (parse, nao persiste)
   |      valida + REMOVE da lista os que ja existem
   |      --> POST /pub/v1/glebes p/ CADA talhao NOVO
   |
   +-- Manual      --> POST /pub/v1/glebes  (um por talhao novo)
        |
3. CONFERIR (GET) nomes, areas e total
        |
        v
   Proximo passo: criar/atualizar a SAFRA vinculando estes talhoes
   --> /aegro-cadastro-safra
```

## Sequencia de Passos

### 1. Listar os talhoes existentes (sempre primeiro)

`GET /pub/v1/glebes`. Esta e a base para **nao duplicar**: veja quais talhoes a
fazenda ja tem (nome, area, `id`). Os `id`s serao usados depois para vincular a
safra.

### 2. Cadastrar apenas os talhoes que faltam

**Caminho A — KML. Fluxo: previa -> comparar -> criar so os novos.**

1. **Previa (parse, nao persiste):** `POST /pub/v1/glebes/kml/preview` (multipart,
   campo `file`). Devolve a lista dos talhoes do arquivo no formato de create
   (nome, area geodesica ja na unidade da fazenda, poligono), **sem gravar nada**.
   Placemarks sem poligono (pontos) sao ignorados; sem nome vira "Talhao N".
2. **Comparar com os existentes (passo 1)** e **remover da lista os que ja
   existem** — nao recadastre.
3. **Criar so os novos:** para cada talhao restante, `POST /pub/v1/glebes`.

**Caminho B — manual.** Para cada talhao **que ainda nao existe**,
`POST /pub/v1/glebes` com:
- **`name`** (obrigatorio).
- **`area`** `{ magnitude, unit }` (obrigatorio) — na unidade da fazenda
  (`ha`/`alq`); confirme antes.
- **`group`** (opcional) — `id` de um talhao "pai" para agrupar.
- **`polygon`** (opcional) — pares `[lat, lng]`.
- **`tag`** (opcional).

### 3. Conferir

`GET /pub/v1/glebes` e valide nomes, areas e total. Garanta que nao ha
duplicatas antes de seguir para a safra.

## Boas Praticas

1. **Sempre listar antes de criar** — dedup e a regra #1; talhao existe uma vez e
   e reutilizado pelas safras.
2. **KML antes de manual** quando existe — menos digitacao, poligono e area de
   uma vez; mas ainda compare com os existentes antes de gravar.
3. **Area na unidade da fazenda** — a API nao adivinha `ha` vs `alq`.
4. **Nao crie talhao por safra** — a mesma gleba serve varias safras; a
   vinculacao anual e feita na safra, nao recriando o talhao.

## Limitacoes

- **KML** importa apenas `<Placemark>` com **poligono**; pontos/linhas sao
  ignorados. Ordem das coordenadas do KML e `lng,lat` (tratada internamente).
- **Area do KML** e aproximacao geodesica (esferica, WGS84); confira quando a
  precisao for critica.
- **Unidade manual**: valor interpretado na unidade da fazenda; sem conversao
  automatica.

## Proximos Workflows

| Situacao | Proximo workflow |
|---|---|
| Criar/atualizar a safra vinculando estes talhoes | `/aegro-cadastro-safra` |
| Acompanhar a safra (talhoes, atividades) | `/aegro-agronomo` |
| Conferir panorama da fazenda | `/aegro-visao-geral` |
