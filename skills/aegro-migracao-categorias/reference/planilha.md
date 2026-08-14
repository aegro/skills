# Da planilha do usuario para regras deterministicas

## O principio

**A planilha e do usuario, nao sua.** Nao existe um formato que voce possa
exigir: cada fazenda organiza a decisao do jeito que faz sentido para ela, e
nenhuma vai adivinhar o layout que voce preferia. Medido em campo: a planilha
real nao tinha nenhuma das colunas que a primeira versao desta skill declarava
obrigatorias, e seguindo aquele contrato ao pe da letra as 1.777 linhas eram
todas invalidas — quando na verdade a planilha estava **certa**, so falava outra
lingua.

Seu trabalho e o de um compilador, em quatro tempos:

```text
LER o que veio  ->  INFERIR o que significa  ->  CONFIRMAR com o usuario
                ->  COMPILAR em regra deterministica
```

Voce pode ser flexivel na entrada porque a saida **nao** e flexivel: o `when` do
de/para e uma whitelist fechada, e o CLI recusa qualquer coisa fora dela. E essa
assimetria que deixa voce aceitar planilha bagunacada sem produzir migracao
bagunacada.

---

## Passo 1 — Leia tudo e mostre o que veio

Abra **todas** as abas (`.xlsx` via a skill `xlsx`; `.csv` direto). Antes de
interpretar, mostre ao usuario o que voce achou:

> A aba "Lista Agrupadores" tem 1.777 linhas e 3 colunas: `AGRUPADOR`,
> `Categoria`, `Codigo`. Primeiras linhas:
> `AGR COMPRA/VENDA SOJA, ADM388S, CPF - LEANDRO TENORIO | Venda Soja | 3.1.1.1`

Nunca comece perguntando "cade a coluna `de`?". Comece dizendo o que voce leu.

---

## Passo 2 — Descubra o eixo de origem

A pergunta que importa: **o que identifica o lancamento nesta planilha?** Cada
resposta compila para um `when` diferente.

| O que a coluna parece ser | Como reconhecer | Compila para |
|---|---|---|
| Categoria antiga | os valores batem com nomes/codigos de categoria da fazenda | `rules[].from` direto, sem `when` |
| **Tag unica** (na tela: *Agrupador*) | os valores batem com tags existentes (`aegro tags list --relation-type BILL`) | `when.anyTags: [tag]` |
| **Conjunto de tags** | um valor traz **varias** tags juntas | `when.allTags: [t1, t2, ...]` |
| Fornecedor | nomes de empresa | `when.companyKeys` (resolva o nome antes) |
| Elemento / produto | nomes do catalogo de elementos | `when.elementKeys` |
| Trecho de historico | texto livre repetido | `when.descriptionFingerprint` |

Como decidir sem chutar: pegue ~20 valores distintos da coluna e cruze com a
realidade da fazenda —

```bash
aegro financial category-usage --farm "<fazenda>" --from "<categoria antiga>" \
  --group-by tag,company,element --top 50 -o json
```

Se os valores da planilha aparecem em `porTag`, o eixo e tag. Em
`porFornecedor`, e fornecedor. **Cruze, nao deduza pelo nome da coluna** — uma
coluna chamada "Categoria" pode conter o destino, e uma chamada "AGRUPADOR" pode
conter tags.

---

## Passo 3 — Conjunto de tags e o caso que mais engana

Este foi o caso real, e ele **silenciosamente migra milhares de lancamentos para
o lugar errado** se voce errar.

O valor `AGR COMPRA/VENDA SOJA, ADM388S, CPF - LEANDRO TENORIO, VENDA DE SOJA`
nao e um rotulo: sao **quatro tags** que aparecem juntas na mesma conta. A
planilha esta dizendo "conta que tem essas quatro tags vai para Venda Soja".

- Isso e **E**, e o primitivo correto e **`allTags`** (o CLI testa
  `procuradas <= tags` do lancamento).
- `anyTags` seria **OU**, e esta errado aqui. Uma tag comum como
  `FAZENDA RAIZES` aparece em dezenas de combinacoes que vao para destinos
  diferentes — um `anyTags: ["FAZENDA RAIZES"]` casaria todas elas e mandaria
  tudo para um destino so.
- **E o `verify` nao acusaria**: a conta saiu da categoria antiga, entao a
  migracao "funcionou". O erro so aparece no relatorio do cliente, meses depois.

**Separar os tokens:** o unico separador confiavel e a **virgula**, porque as
proprias tags contem `/` e ` - ` (`AGR COMPRA/VENDA SOJA`, `CPF - LEANDRO
TENORIO`). Nunca quebre por esses. Depois de quebrar por virgula, **valide cada
token contra a lista real de tags** (`aegro tags list --relation-type BILL`): token que nao existe
como tag e sinal de que voce quebrou errado ou de que a tag foi renomeada — leve
ao usuario em vez de emitir a regra.

---

## Passo 4 — Ordene da mais especifica para a mais geral

`allTags` e teste de **subconjunto**. Uma conta com 5 tags casa tanto a regra de
5 tags quanto qualquer regra formada por um subconjunto delas. Como **a primeira
regra que casa vence**, regra curta posta antes de regra longa engole a longa.

**Ordene por numero de tags, decrescente.** Sempre. Mesmo raciocinio para
`companyKeys + descriptionFingerprint` antes de `companyKeys` sozinho.

Depois de gerar, confira: para cada par de regras onde as tags de uma sao
subconjunto das da outra, a maior tem que vir primeiro. E barato de checar e
caro de descobrir depois.

---

## Passo 5 — Destino: prefira o codigo a chave, e a chave ao nome

Se a planilha traz uma coluna de **codigo contabil** (`3.1.1.1`, `4.1.6.1.8`),
use-a: codigo e unico, nome nao e. Resolva codigo -> chave voce mesmo e emita a
**chave** em `to`:

```bash
aegro fin-categories list --farm "<fazenda>" --status ACTIVE --page N -o json
```

Isso mata de uma vez o problema de nome duplicado (nesta base existe "Outros
Custos Agricolas" arquivada **e** ativa com o mesmo nome) sem precisar da
mensagem de ambiguidade do CLI.

Codigo que nao existe no catalogo, ou que aponta para categoria `SYNTHETIC` ou
`ARCHIVED`: **nao emita a regra** — vira pergunta (Passo 6). Valores de erro de
planilha (`#N/A`, `#REF!`, `-`, `n/a`) sao celula vazia, nao destino.

---

## Passo 6 — Incompletude nao bloqueia. Nunca.

Planilha pela metade e o estado **normal**, nao um erro. Na planilha real, 896
de 1.777 linhas (50,4%) estavam sem destino — e isso nao impede migrar as outras
881.

A postura:

1. **Compile o que da.** Toda linha completa vira regra e entra nesta rodada.
2. **Meca o que falta antes de perguntar.** Agrupe as linhas em branco e conte
   quantos lancamentos elas representam. "Faltam 896 linhas" e ruido; "faltam 12
   grupos, que somam 3.620 lancamentos, e estes 3 sozinhos sao 2.900" e uma
   conversa.
3. **Pergunte uma vez, em lote**, com o maior primeiro. Nunca linha a linha.
4. **Siga.** O que ficou sem destino vira `unresolved`, e `unresolved`
   **nunca e escrito** — o dado fica exatamente como estava. Nao ha risco em
   migrar so uma parte.
5. **A proxima rodada so reapresenta o que sobrou.** O usuario completa a
   planilha quando puder, ou decide na tela de triagem; nas duas vias a cauda
   encolhe.

Diga isso ao usuario com todas as letras, porque ele provavelmente acha que
precisa terminar a planilha antes de comecar:

> Dessas 1.777 linhas, 881 estao completas e cobrem N lancamentos — da para
> migrar essas hoje. As 896 em branco ficam como estao, sem risco: o comando
> nunca escreve o que nao tem destino. Elas voltam na proxima rodada, e ai voce
> me diz o destino das maiores.

---

## Passo 7 — Confirme a interpretacao antes de rodar o `plan`

Voce inferiu; agora prove que inferiu certo, **antes** de gastar uma varredura.
Mostre em uma tela:

> Entendi a coluna `AGRUPADOR` como **conjunto de tags** (E, nao OU), o
> `Codigo` como destino, e o `Categoria` como o nome do destino (usei o codigo).
>
> - 881 linhas viraram regra; 896 ficaram sem destino (Passo 6)
> - 4 tokens nao batem com nenhuma tag da fazenda: `ADM388S`, ... — confere?
> - As regras estao ordenadas da mais especifica (5 tags) para a mais geral
> - Amostra: `allTags: ["AGR COMPRA/VENDA SOJA", "ADM388S"]` -> `Venda Soja (3.1.1.1)`
>
> Rodo o `plan`?

Se a leitura estiver errada, aqui custa uma frase. Depois do `plan` custa uma
varredura, e depois do `apply` custa uma migracao errada que o `verify` nao pega.

---

## Erros do CLI — repasse como vieram

O `plan` sai com **exit 4** e uma mensagem que ja diz o que fazer:

| Mensagem | Significado |
|---|---|
| `categoria 'X' nao encontrada. Parecidas: A, B, C.` | Digitacao, ou nome de outra fazenda. Ofereca as parecidas. |
| `'X' e ambiguo — 2 categorias com esse nome: ... Use a chave.` | Arquivada e ativa com o mesmo nome. Resolva por codigo (Passo 5). |
| `'X' esta ARQUIVADA e nao pode ser destino` | Destino morto. |
| `'X' e uma categoria SINTETICA (agrupadora, codigo N)` | Agrupadora, nao lancavel. Precisa da analitica filha. |
| `dimensao 'anyTag' nao existe em 'when'. Quis dizer 'anyTags'?` | Bug seu na compilacao. Conserte, nao contorne. |
| `origem e destino sao a mesma categoria` | Provavelmente a ativa homonima; use a chave. |

Nao parafraseie a lista de parecidas nem o codigo da sintetica: sao o dado que
resolve.
