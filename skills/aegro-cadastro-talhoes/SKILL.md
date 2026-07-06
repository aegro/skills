---
name: aegro-cadastro-talhoes
description: Cadastra e mantem os talhoes (glebas) de uma fazenda no Aegro, manualmente ou importando de um KML (com previa antes de gravar), usando a CLI aegro
version: 0.1.0
---

# Cadastro de Talhoes no Aegro

## Objetivo

Cadastrar e manter os **talhoes** (glebas) de uma fazenda — manualmente ou
**importando um KML** (com prevalidacao antes de gravar). Todas as operacoes sao
feitas pela **CLI `aegro`** (que fala com a API da fazenda ativa).

## Talhoes NAO se duplicam (regra fundamental)

> **O talhao e uma entidade PERSISTENTE da fazenda, cadastrada UMA vez e
> REUTILIZADA pelas safras ao longo dos anos.** A mesma gleba entra em varias
> safras (ex.: "T-01" na Soja 24/25, depois na Soja 25/26, ...). **Nunca
> recadastre um talhao que ja existe** — nao crie um talhao novo por safra nem
> reimporte o mesmo KML criando duplicatas.

Por isso, **antes de criar qualquer talhao**:

1. **Liste os talhoes que a fazenda ja tem:** `aegro glebes list`.
2. **Compare** com o que voce pretende cadastrar (por **nome** e, quando houver,
   pela **area/poligono**).
3. **Reutilize** os que ja existem (guarde as `key`s deles para vincular a safra)
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

- **CLI `aegro`** configurada e uma **fazenda ativa** selecionada (a CLI resolve
  a fazenda e a credencial).
- Saber a **unidade de area da fazenda** (`ha` ou `alq`): as areas informadas
  manualmente devem estar nessa unidade. No KML a area e calculada
  automaticamente.

## Comandos da CLI

| Acao | Comando |
|---|---|
| Listar talhoes existentes (dedup!) | `aegro glebes list` |
| Ver um talhao | `aegro glebes get <key>` |
| Previa do KML (**nao persiste**) | `aegro glebes preview-kml --file <arquivo.kml>` |
| Criar talhao | `aegro glebes create --name <nome> --area <valor> --area-unit <ha\|alq> [--group <key>] [--polygon <json>] [--tag <tag>]` |

`glebes preview-kml` parseia o arquivo e mostra os talhoes que **seriam**
criados (nome, area geodesica ja na unidade da fazenda, poligono) **sem gravar
nada**. Nao ha comando que persista KML direto: a **unica via de escrita** de
talhao e `aegro glebes create` (um por talhao).

Dica: as escritas (`glebes create`) aceitam `--dry-run` (mostra o que seria
enviado, sem gravar) e `--execute`.

## Fluxo

```
Fazenda ativa
        |
1. LISTAR existentes   --> aegro glebes list        (evitar duplicata!)
        |
2. Cadastrar os que FALTAM
   |
   +-- Tenho KML?  --> aegro glebes preview-kml --file talhoes.kml   (nao persiste)
   |      compara com os existentes, REMOVE os que ja existem
   |      --> aegro glebes create ...   p/ CADA talhao NOVO
   |
   +-- Manual      --> aegro glebes create ...   (um por talhao novo)
        |
3. CONFERIR   --> aegro glebes list
        |
        v
   Proximo passo: criar/atualizar a SAFRA vinculando estes talhoes
   --> /aegro-cadastro-safra
```

## Sequencia de Passos

### 1. Listar os talhoes existentes (sempre primeiro)

```bash
aegro glebes list
```

Esta e a base para **nao duplicar**: veja quais talhoes a fazenda ja tem (nome,
area, `key`). As `key`s serao usadas depois para vincular a safra.

### 2. Cadastrar apenas os talhoes que faltam

**Caminho A — KML. Fluxo: previa -> comparar -> criar so os novos.**

```bash
# 1) previa (parseia, NAO persiste)
aegro glebes preview-kml --file talhoes.kml
```
Devolve a lista dos talhoes do arquivo (nome, area geodesica na unidade da
fazenda, poligono). Placemarks sem poligono (pontos) sao ignorados; sem nome
vira "Talhao N".

```bash
# 2) para CADA talhao que NAO existe ainda, cria:
aegro glebes create --name "T-01" --area 45.5 --area-unit ha \
  --polygon '[[-23.1,-47.1],[-23.1,-47.09],[-23.11,-47.09],[-23.1,-47.1]]'
```
Compare com o `glebes list` do passo 1 e **crie so os que faltam**.

**Caminho B — manual.** Para cada talhao **que ainda nao existe**:

```bash
aegro glebes create --name "T-02" --area 30 --area-unit ha
```
- **`--name`** (obrigatorio).
- **`--area`** + **`--area-unit`** (obrigatorios) — valor na unidade da fazenda
  (`ha`/`alq`); confirme antes. (`--unit` e alias de `--area-unit`.)
- **`--group`** (opcional) — `key` de um talhao "pai" para agrupar.
- **`--polygon`** (opcional) — JSON de pares `[[lat,lng],...]`.
- **`--tag`** (opcional).

### 3. Conferir

```bash
aegro glebes list
```
Valide nomes, areas e total; garanta que nao ha duplicatas antes de seguir para
a safra.

## Boas Praticas

1. **Sempre `aegro glebes list` antes de criar** — dedup e a regra #1; talhao
   existe uma vez e e reutilizado pelas safras.
2. **KML antes de manual** quando existe — menos digitacao; mas ainda compare com
   os existentes antes de criar.
3. **Area na unidade da fazenda** — a CLI nao adivinha `ha` vs `alq` (`--area-unit`).
4. **Nao crie talhao por safra** — a mesma gleba serve varias safras; a
   vinculacao anual e feita na safra, nao recriando o talhao.
5. **Use `--dry-run`** quando quiser conferir o que seria enviado antes de gravar.

## Limitacoes

- **KML** importa apenas `<Placemark>` com **poligono**; pontos/linhas sao
  ignorados. A area do KML e aproximacao geodesica (esferica, WGS84); confira
  quando a precisao for critica.
- **Unidade manual**: valor interpretado na unidade da fazenda; sem conversao
  automatica.

## Proximos Workflows

| Situacao | Proximo workflow |
|---|---|
| Criar/atualizar a safra vinculando estes talhoes | `/aegro-cadastro-safra` |
| Acompanhar a safra (talhoes, atividades) | `/aegro-agronomo` |
| Conferir panorama da fazenda | `/aegro-visao-geral` |
