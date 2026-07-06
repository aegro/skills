---
name: aegro-entrada-setup-fazenda
description: Orquestra o setup inicial de uma fazenda no Aegro — cadastra talhoes (manual ou por importacao de KML) e cria a safra vinculando os talhoes, via API publica /pub/v1, para acelerar o onboarding feito pelos EVs
version: 0.1.0
---

# Setup de Fazenda no Aegro (Talhoes + Safra)

## Objetivo

Acelerar o **setup inicial de uma fazenda** durante o onboarding: cadastrar os
**talhoes** (glebas) e criar a primeira **safra** ja vinculando esses talhoes.
Esta skill e a camada de **processo** de entrada, acima do cadastro cru: recebe
o material que o EV tem em maos (uma planilha de talhoes, um arquivo KML, ou so
os nomes/areas), decide o melhor caminho de cadastro e entrega a fazenda pronta
para o produtor comecar a operar.

O trabalho e feito pela **API publica `/pub/v1`** (contexto de integration
agent, com escopo por fazenda) — os mesmos endpoints ficam disponiveis para o
agente e para automacoes de entrada.

## Quando Usar

- Fazenda nova recem-criada que precisa ter os **talhoes cadastrados**.
- O EV tem um **KML** com os poligonos dos talhoes e quer importar de uma vez.
- Precisa criar a **safra** (ex.: "Soja 25/26") e **vincular** os talhoes a ela.
- Onboarding em lote onde cadastrar talhao a talhao pela tela seria lento.

Para dar entrada de **nota fiscal**, va para `/aegro-entrada-nota-fiscal`. Para
cadastro operacional geral (fazenda, usuarios), veja `/aegro-operacional`.

## Pre-requisitos

- **Fazenda ja existe** e voce tem a `farmKey` dela (a criacao da fazenda em si
  nao faz parte desta skill).
- **Integration agent** autenticado com os escopos de escrita:
  `WRITE_GLEBES` (criar talhoes) e `WRITE_CROPS` (criar safra). A fazenda-alvo
  vai no header `X-Aegro-Farm-Key`.
- Saber a **unidade de area da fazenda** (hectare `ha` ou alqueire `alq`): ela e
  definida na fazenda (`Farm.areaMeasuringUnit`) e as areas informadas
  manualmente devem estar **nessa unidade**. Na importacao por KML a area e
  calculada automaticamente.

## A API que a skill usa (`/pub/v1`)

| Acao | Endpoint | Corpo |
|---|---|---|
| Criar talhao | `POST /pub/v1/glebes` | `{ name, area:{magnitude,unit}, tag?, group?, polygon? }` |
| Previa do KML (parse, **nao persiste**) | `POST /pub/v1/glebes/kml/preview` | multipart `file=<arquivo.kml>` |
| Criar safra (vinculando talhoes) | `POST /pub/v1/crops` | `{ type, name?, startDate?, endDate?, glebeKeys?[] }` |

O `kml/preview` devolve uma **lista no formato do corpo de `POST /pub/v1/glebes`**
(name, area, polygon) — ou seja, os talhoes ja prontos para registrar. Nao ha
endpoint que persista KML direto: a **unica via de escrita** de talhao e o
`POST /pub/v1/glebes` (um por talhao).

Todos exigem o header `X-Aegro-Farm-Key` e o escopo correspondente. Para
conferir o que foi criado, use os `GET /pub/v1/glebes` e `GET /pub/v1/crops`
(ja existentes).

## Fluxo de Decisao

```
Fazenda criada (tenho a farmKey)
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
   |  escolher o tipo (CropType), o periodo e vincular os talhoes
   |  nome default "Tipo AA/BB" (ex.: "Soja 25/26"); periodo default 1 ano
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
2. **Validar:** mostre a lista para o EV conferir/ajustar nomes e areas.
3. **Criar (persistir):** para **cada** talhao aprovado, envie o item ao
   `POST /pub/v1/glebes` (o payload da previa ja esta no formato certo — pode
   editar antes, ex.: setar `group`). Esse e o unico endpoint que grava talhao.

> **Sempre passe pela previa antes de criar** — e o passo que deixa o EV validar
> o que o KML traria. KML invalido/ilegivel ou sem nenhum poligono retorna
> **422** — verifique o arquivo (deve ter
> `<Polygon><outerBoundaryIs><LinearRing><coordinates>`).

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
  2025→2026 = **"Soja 25/26"**; mesmo ano = "Soja 25"). Informe `name` so quando
  quiser um nome fora do padrao.
- **`startDate`** / **`endDate`** (opcionais, ISO `yyyy-MM-dd`) — se omitidos,
  `startDate` = hoje e `endDate` = `startDate` + **1 ano** (padrao Aegro).
- **`glebeKeys`** — a lista de `id`s dos talhoes (do passo 2) a **vincular** a
  safra. E aqui que os talhoes entram na safra.

### 4. Conferir a safra

`GET /pub/v1/crops` e confirme o nome, o periodo e os talhoes vinculados. A
fazenda esta pronta para operar.

## Boas Praticas

1. **KML antes de manual** — quando ha KML, importe: menos digitacao, poligono e
   area corretos de uma vez.
2. **Area sempre na unidade da fazenda** — confirme `ha` vs `alq` antes de
   cadastrar manualmente; a API nao adivinha a unidade.
3. **Conferir antes de criar a safra** — talhao errado vira safra errada; valide
   nomes/areas no passo 2.
4. **Deixe o nome da safra no padrao** — omita `name` para o "Soja 25/26"
   automatico, exceto quando a fazenda pede um nome proprio.
5. **Vincular os talhoes na criacao da safra** (`glebeKeys`) — evita ter de
   religar depois.
6. **Um escopo por acao** — o agente precisa de `WRITE_GLEBES` para talhoes e
   `WRITE_CROPS` para a safra; sem o escopo a chamada retorna **403**.

## Limitacoes / Dependencias

- **KML** importa apenas `<Placemark>` com **poligono**; pontos e linhas sao
  ignorados. A ordem das coordenadas do KML e `lng,lat` (tratada internamente).
- **Area do KML** e uma aproximacao geodesica (esferica, WGS84); para talhoes
  pequenos e ok, mas confira quando a precisao for critica.
- **Unidade de area manual**: o valor e interpretado na unidade da fazenda; nao
  ha conversao automatica de um `ha` informado numa fazenda em `alq`.
- **Criacao da fazenda** e **usuarios/permissoes** nao fazem parte desta skill
  (veja `/aegro-operacional`).

## Proximos Workflows

| Situacao | Proximo workflow |
|---|---|
| Dar entrada de nota fiscal | `/aegro-entrada-nota-fiscal` |
| Conferir panorama da fazenda | `/aegro-visao-geral` |
| Cadastro operacional (fazenda, usuarios) | `/aegro-operacional` |
| Acompanhar a safra (talhoes, atividades) | `/aegro-agronomo` |
