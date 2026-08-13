# Planilha da EV -> arquivo de/para

A EV entrega `.xlsx` ou `.csv`. Voce converte para o JSON da secao 4.2 do plano
e **deixa o CLI validar**. Voce nao valida nome de categoria: o CLI resolve
contra a fazenda de verdade e recusa com mensagem melhor que a sua.

---

## 1. Colunas

| Coluna | Sinonimos aceitos | Obrigatoria | Vira |
|---|---|---|---|
| `de` | `origem`, `categoria antiga`, `antiga`, `from` | **sim** | `rules[].from` |
| `para` | `destino`, `categoria nova`, `nova`, `to` | **sim** | `rules[].to` |
| `quando_tag` | `tag`, `agrupador`, `quando tag` | nao | `when.anyTags` |
| `quando_fornecedor` | `fornecedor`, `empresa` | nao | `when.companyKeys` |
| `quando_descricao` | `descricao`, `historico` | nao | `when.descriptionFingerprint` |
| `observacao` | `obs`, `nota`, `comentario` | nao | nada (contexto seu) |

Normalize o cabecalho antes de casar: minusculas, sem acento, `_` e espaco
equivalentes, sem espaco nas pontas. `Categoria Antiga` casa com `de`.

**Uma linha = uma regra.** Duas linhas com o mesmo `de` e `quando` diferentes
viram duas regras, e a ordem da planilha vira a ordem do arquivo — que e a ordem
de precedencia. Diga isso a EV se ela perguntar por que a ordem importa.

---

## 2. Normalizacao dos valores

- **Acento e caixa:** mande o nome **como a EV escreveu**. O CLI dobra acento e
  caixa ao resolver (`_fold`). Nao "conserte" o nome — se estiver errado, a
  mensagem do CLI vai sugerir os parecidos, e essa mensagem e util.
- **Espaco:** apare as pontas e colapse espaco duplo. So isso.
- **Multivalor:** `quando_tag` e `quando_fornecedor` aceitam varios separados
  por `;` (ou `,` se nao houver `;` no texto). `TAG A; TAG B` vira
  `{"anyTags": ["TAG A", "TAG B"]}` — que casa **qualquer uma** delas.
- **`@element`:** se `para` for `@element` (ou "elemento", "categoria do
  elemento"), emita `"to": "@element"` literal. So funciona em conta com itens;
  em conta de nivel de conta o plano bloqueia com `element-rule-on-account-level`.
- **Chave:** se o valor ja vier como `financialCategory::...`, passe direto.

---

## 3. Fornecedor: nome na planilha, chave no JSON

`when.companyKeys` exige **chave** (`company::...`), e a EV escreve o nome. Se a
coluna vier preenchida com nome, resolva antes:

```bash
aegro companies list --farm "<fazenda>" --search-text "<nome>" -o json
```

Se der mais de um resultado, **pergunte a EV qual** — nao escolha o primeiro.
Fornecedor errado num `when` migra o grupo errado inteiro, e o `verify` nao
acusa (a migracao "funcionou", so foi para o lugar errado).

Se a resolucao ficar cara ou ambigua demais, **deixe a linha sem
`quando_fornecedor`** e resolva aquele grupo pela cauda, onde o cluster ja vem
com a `companyKey` correta de graca.

---

## 4. Linhas que nao viram regra

| Situacao | O que fazer |
|---|---|
| `para` vazio | **Nao emita a regra.** Junte todas essas linhas e pergunte a EV de uma vez, ou deixe a cauda resolver. |
| `de` vazio | Linha invalida. Reporte com o numero da linha. |
| Linha inteira vazia | Ignore em silencio. |
| `de` == `para` | Nao emita — o CLI recusaria com "origem e destino sao a mesma categoria". Avise a EV: provavelmente ela quis a **ativa** de mesmo nome, e ai o certo e a chave. |
| Comentario da EV numa celula de dado ("ver com o Joao") | Trate como `para` vazio e leve para a pergunta. |

---

## 5. Exemplo completo

Planilha:

| Categoria Antiga | Categoria Nova | Tag | Obs |
|---|---|---|---|
| Salarios (antigo) | Salarios - Agricultura | SALARIO AGRICULTURA | |
| Salarios (antigo) | Salarios - Armazem | SALARIO ARMAZEM | |
| Combustiveis (antigo) | @element | | resolve pelo elemento |
| Fretes (antigo) | Fretes | | |
| Manutencao de Maquinas ANTIGA | | | ver com a Thais |

Vira:

```json
{
  "version": 1,
  "farm": "FAZENDAS RAIZES AGRO",
  "rules": [
    {"from": "Salarios (antigo)", "to": "Salarios - Agricultura",
     "when": {"anyTags": ["SALARIO AGRICULTURA"]}},
    {"from": "Salarios (antigo)", "to": "Salarios - Armazem",
     "when": {"anyTags": ["SALARIO ARMAZEM"]}},
    {"from": "Combustiveis (antigo)", "to": "@element"},
    {"from": "Fretes (antigo)", "to": "Fretes"}
  ],
  "overrides": []
}
```

A quinta linha **nao virou regra** — vira esta pergunta, com o tamanho medido:

> "Manutencao de Maquinas ANTIGA" ficou sem destino na planilha. Sao 3.620
> lancamentos. A ativa de nome parecido ("Manutencao de Maquinas e
> Equipamentos") e **sintetica**, entao nao da para lancar nela. Quer que eu
> deixe essa categoria fora deste plano e resolva na tela de triagem, onde da
> para separar por tipo de maquina?

Medir antes de perguntar (`category-usage --from "..."`) muda a conversa: a EV
decide sabendo se sao 12 ou 3.620.

---

## 6. Erros que o CLI devolve — repasse como vieram

O `plan` sai com **exit 4** e uma mensagem que ja diz o que fazer:

| Mensagem | Significado |
|---|---|
| `categoria 'X' nao encontrada. Parecidas: A, B, C.` | Erro de digitacao ou nome de outra fazenda. Ofereca as parecidas. |
| `'X' e ambiguo — 2 categorias com esse nome: ... Use a chave.` | Arquivada e ativa com o mesmo nome. Busque a chave e pergunte qual. |
| `'X' esta ARQUIVADA e nao pode ser destino` | A EV apontou para outra categoria morta. |
| `'X' e uma categoria SINTETICA (agrupadora, codigo N)` | Agrupadora, nao lancavel. Precisa da analitica filha. |
| `dimensao 'anyTag' nao existe em 'when'. Quis dizer 'anyTags'?` | Bug seu na conversao. Conserte, nao contorne. |
| `origem e destino sao a mesma categoria` | Ver secao 4. |

Nao parafraseie a lista de parecidas nem o codigo da sintetica: sao o dado que
resolve.
