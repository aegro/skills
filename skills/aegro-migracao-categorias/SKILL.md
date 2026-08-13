---
name: aegro-migracao-categorias
description: >-
  Conduz a migracao de categoria financeira em massa no Aegro (milhares de
  lancamentos saindo de categorias arquivadas para a arvore nova) pela CLI
  aegro. Converte a planilha de/para da EV em JSON validado, roda o `plan`,
  renderiza uma TELA LOCAL de triagem sobre a cauda que nenhuma regra resolveu
  (clusters com contagem, valor, amostras, sugestao com fonte e evidencia) mais
  o painel de aprovacao (agregado, bloqueados, hash), recebe as decisoes de
  volta como regras/overrides, e conduz canario -> verify -> lote -> verify.
  Use quando pedirem "migrar categoria em massa", "trocar milhares de
  lancamentos de categoria", "categoria antiga para a nova", "de/para de
  categorias", "triar a cauda da migracao", "aplicar o plano de migracao";
  EN "bulk category migration", "migrate financial categories in bulk",
  "triage the migration tail". NAO use para trocar a categoria de um punhado de
  lancamentos (use /aegro-financeiro com `financial update-bill`), para criar
  categoria (use `fin-categories create`), nem para migrar qualquer outro campo
  que nao seja categoria financeira.
version: 0.1.0
---

# Aegro Migracao de Categorias em Massa

Skill para tirar milhares de lancamentos de categorias arquivadas e leva-los
para a arvore nova, com a decisao humana concentrada em ~30 grupos em vez de
espalhada por 20 mil lancamentos.

O caso que originou isto: um cliente com **23.583 lancamentos em 67 categorias
arquivadas**. Sete dessas categorias tem gemea ativa exata (2.944 lancamentos
com destino inequivoco, que o `plan` resolve sozinho). As outras **60 exigem
julgamento humano** — as antigas eram planas e a arvore nova desdobrou
("Manutencao de Maquinas ANTIGA", 3.620 contas, virou Tratores / Pulverizadores
/ Semeadeiras / Vagoes). E esse julgamento que a tela desta skill torna rapido.

> **Requer login OAuth.** O `plan` descobre lancamento recorrente pela API
> interna. Rode `aegro auth login [--env staging]`. Em modo API key o comando
> falha com exit 2.
>
> **Requer aegro CLI >= 0.19.0.** Confira ANTES de qualquer coisa (secao 1).
> Skill nova rodando contra CLI antigo fica **falsa em silencio**.
>
> **`--farm "<nome|farm::key>"` explicito em todo comando.** O `farms select`
> grava state global por maquina; com varias sessoes abertas, a selecao de uma
> troca o alvo das outras. Em safe mode a escrita recusa fazenda implicita.
>
> **Dado de cliente nao sai da maquina.** A tela contem descricao de
> lancamento, fornecedor e valor de um cliente real. Renderize **arquivo HTML
> local** e abra no navegador. NAO publique como artifact hospedado, NAO mande o
> `unresolved.json`, o plano ou o ledger para servico externo, e NAO cole
> descricao de lancamento em busca na web.

---

## 1. Checagem de versao — faca isto primeiro, sempre

```bash
aegro --version
aegro financial migrate-category plan --help
```

O segundo comando e o que importa: ele prova que a maquina de migracao existe
neste CLI. Se `aegro --version` for **menor que 0.19.0**, ou se o `--help`
falhar, **pare e diga isto ao usuario**, sem tentar contornar:

> Esta skill precisa do `aegro` >= 0.19.0 (voce tem X). Atualize com
> `uv tool upgrade aegro` (ou `pip install -U aegro`) e rode de novo.

Por que falhar alto: a skill chega por `aegro skills sync`, que **nao** depende
de release do CLI. Uma skill nova pode encontrar um CLI velho. Guard novo no CLI
que a skill nao conhece produz plano que parece certo e nao e.

---

## 2. O invariante — leia antes de improvisar

**O `apply` so executa o que esta no plano aprovado por hash.** Decisao da EV
entra como regra no de/para e **volta pelo `plan`**. Nunca direto no `apply`,
nunca editando o `plano.jsonl` a mao (o hash quebra e o `apply` recusa — e esta
certo).

O ciclo, inteiro:

```text
planilha da EV --> de/para JSON --> plan --> tela (aprovacao + cauda)
                        ^                          |
                        |                          v
                        +--- regras/overrides <-- decisoes da EV
                                                   |
                    UNRESOLVED = 0 (ou consciente) |
                                                   v
                        apply --limit 20 --> verify --> apply (lote) --> verify
                                                                            |
                                              category-usage --from <antiga> = 0
```

Converge porque cada rodada so reapresenta o que ficou de fora, e `keep`
aposenta o caso duvidoso em vez de traze-lo de volta. Cada `plan` custa segundos
(~40 s para 15 mil lancamentos).

---

## 3. Papeis: o que e do CLI e o que e seu

| Trabalho | Quem faz |
|---|---|
| Varrer, casar regra, montar payload, bloquear, agrupar a cauda, tabular precedente | **CLI** (`plan`) |
| Converter a planilha em de/para JSON | **voce** (secao 4) |
| Renderizar a tela e receber as decisoes | **voce** (secao 6) |
| Expandir decisao em `rules`/`overrides` | **voce** (secao 7) |
| Escrever na API | **CLI** (`apply`) |
| Provar o resultado | **CLI** (`verify`) |

O CLI **nao emite palpite de LLM**. Voce pode acrescentar uma sugestao sua
(`source: "assistant"`), sempre rotulada e **nunca pre-marcada** — ver secao 6.

---

## 4. Planilha da EV -> arquivo de/para

Contrato completo em [`reference/planilha.md`](reference/planilha.md). Resumo:

| Coluna | Obrigatoria | Vira |
|---|---|---|
| `de` | sim | `rules[].from` (nome ou `financialCategory::key`) |
| `para` | sim | `rules[].to` (nome, key, ou `@element`) |
| `quando_tag` | nao | `when.anyTags` (separado por `;`) |
| `quando_fornecedor` | nao | `when.companyKeys` |
| `quando_descricao` | nao | `when.descriptionFingerprint` |
| `observacao` | nao | nada (so contexto para voce) |

Aceite sinonimo de cabecalho (`origem`/`categoria antiga` = `de`;
`destino`/`categoria nova` = `para`), normalize acento e caixa, e ignore linha
vazia. Para ler `.xlsx` use a skill `xlsx`; `.csv` leia direto.

**Nao invente destino.** Linha com `para` vazio nao vira regra — vira pergunta
para a EV, ou espera a cauda resolver.

Depois de escrever o JSON, **deixe o CLI validar**. Ele recusa com mensagem
acionavel e exit 4: nome inexistente com sugestao de parecidos, nome ambiguo
exigindo a chave, destino arquivado, destino sintetico, dimensao `when`
desconhecida. Repasse a mensagem do CLI para a EV **como veio** — ela e melhor
que qualquer parafrase sua.

**Nomes sao traicoeiros nesta base.** Acento, caixa, sufixo variando
("ANTIGA"/"ANTIGO"/"(antiga)"/"- Antiga"), e **duplicata entre arquivada e
ativa**: nesta fazenda existe "Outros Custos Agricolas" arquivada *e* ativa com
o mesmo nome. Quando o CLI acusar ambiguidade, resolva com a chave:

```bash
aegro fin-categories list --farm "<fazenda>" --search-text "Outros Custos" -o table
```

Forma do arquivo:

```json
{
  "version": 1,
  "farm": "FAZENDAS RAIZES AGRO",
  "rules": [
    {"from": "Salarios (antigo)", "to": "Salarios - Agricultura",
     "when": {"anyTags": ["SALARIO AGRICULTURA"]}},
    {"from": "Combustiveis (antigo)", "to": "@element"},
    {"from": "Fretes (antigo)", "to": "Fretes"}
  ],
  "overrides": [
    {"billKey": "bill::9f1", "to": "Adiantamentos"},
    {"billKey": "bill::7c2", "keep": true, "why": "estorno, categoria antiga e proposital"}
  ]
}
```

Regras de precedencia: **primeira regra que casa vence**, na ordem do arquivo;
`overrides` vencem regra. `when` e **whitelist** — `anyTag` no lugar de `anyTags`
e recusado (casaria a categoria inteira em silencio). `"to": "@element"` usa a
categoria oficial do elemento de cada item; so faz sentido em conta com itens.

---

## 5. Inventario e `plan`

Antes do de/para, se a EV nao souber o tamanho:

```bash
aegro financial category-usage --farm "<fazenda>" --env staging \
  --from "Salarios (antigo)" --group-by tag,company,element,level -o table
```

Responde "isto sao 12 grupos ou 800?" em segundos, com completude provada.

Depois:

```bash
aegro financial migrate-category plan --farm "<fazenda>" --env staging \
  --map depara.json --out plano-salarios.jsonl
```

Gera **tres** arquivos e imprime o hash:

| Arquivo | Conteudo |
|---|---|
| `plano-salarios.jsonl` | uma linha por lancamento, com o payload pronto |
| `plano-salarios.jsonl.meta.json` | contagens, varredura, `planHash`, `sourceKeys` |
| `plano-salarios.jsonl.unresolved.json` | a cauda agrupada em clusters, com sugestao |

`plan` e `verify` **nao escrevem nada** na API. Rodar `plan` de novo com o mesmo
dado da o **mesmo hash** — plano e deterministico, e re-planejar nao invalida uma
aprovacao a toa.

Status possiveis de cada linha: `planned` · `unresolved` · `kept` · `blocked`.
Os motivos de bloqueio e como explica-los a EV estao em
[`reference/interpretacao.md`](reference/interpretacao.md).

---

## 6. A tela de triagem

Template e protocolo completos em
[`reference/tela-triagem.md`](reference/tela-triagem.md). O que a tela cobre:

1. **Painel de aprovacao** (topo): fazenda, ambiente, quando foi gerado, o
   `planHash` com botao de copiar, as contagens por status, o agregado por
   regra, os **bloqueados por motivo**, e aviso alto se a varredura nao fechou.
   A EV precisa ver o que **nao** vai migrar antes de liberar o hash — aprovar
   sem olhar os `blocked` e o ponto cego do FNC-184.
2. **A cauda**: um cartao por cluster, do maior para o menor, com contagem,
   valor, amostras de descricao, os sinais que formaram o grupo, e a sugestao
   com **fonte e evidencia a vista**.

Hierarquia da sugestao — a tela mostra a **fonte**, nao so o destino:

| `source` | Significado | Nasce marcada |
|---|---|---|
| `precedent` | A propria base do cliente ja responde | **sim** |
| `element` | Categoria oficial do elemento | **sim** |
| `lexical` | Nome da antiga sem o sufixo bate com uma ativa | nao |
| `none` | Sem sinal nenhum | nao |
| `assistant` | Julgamento seu pela descricao | **nunca** |

Voce **pode** acrescentar `source: "assistant"` num cluster que veio `none`,
com uma linha de justificativa. Sempre rotulado "sem precedente na base" e
**sempre em branco**. Isso e decisao D7 do plano, e existe porque a EV disse
exatamente isso: ela nao quer reconferir chute de LLM. Nao burle marcando por
"confianca alta".

Passos:

1. Leia `plano.jsonl.meta.json`, `plano.jsonl.unresolved.json` e o `grupos` do
   stdout do `plan`.
2. Carregue o catalogo de categorias lancaveis para a EV escolher destino:
   `aegro fin-categories list --farm "<fazenda>" --status ACTIVE --page N -o json`
   (50 por pagina; pagine ate acabar). Descarte `type: "SYNTHETIC"` — sintetica
   e agrupadora e **nao e lancavel**.
3. Monte o HTML a partir do template e escreva num diretorio de trabalho local
   (ao lado do plano). Abra no navegador.
4. A EV decide e clica **Baixar decisoes** -> `decisoes-<plano>.json` na pasta
   de downloads dela.
5. Voce le esse arquivo e expande em `rules`/`overrides` (secao 7).

---

## 7. Decisoes -> regras

**Prefira regra a override.** 800 bills viram ~30 regras; regra e auditavel e
re-executavel, override e residuo. So use override quando o cluster nao tem
sinal nenhum (`by: "none"`) ou quando a decisao e `manter`.

Expansao, por tipo de cluster:

| `cluster.by` | Vira | `when` |
|---|---|---|
| `company+fingerprint` | regra | `{"companyKeys": [companyKey], "descriptionFingerprint": fingerprint}` |
| `company` | regra | `{"companyKeys": [companyKey]}` |
| `fingerprint` | regra | `{"descriptionFingerprint": fingerprint}` |
| `element` | regra | `{"elementKeys": elementKeys}` |
| `none` | **override por billKey** | — |
| acao `manter` (qualquer `by`) | **override `keep: true` por billKey**, com `why` | — |
| acao `adiar` | nada — volta na proxima rodada | — |

Duas coisas que quebram silenciosamente se voce nao cuidar:

1. **Uma regra tem um `from` so.** Cluster com varios `fromKeys` vira **uma
   regra por fromKey**, mesmo `when` e mesmo `to`.
2. **Ordem importa: da regra mais especifica para a mais geral.** Emita nesta
   ordem — `company+fingerprint`, depois `fingerprint`, depois `element`, depois
   `company` — e **acrescente ao fim** das regras que ja existem no de/para.
   Uma regra `{"companyKeys": [c1]}` posta antes de
   `{"companyKeys": [c1], "descriptionFingerprint": "..."}` engole o grupo
   especifico sem avisar ninguem.

Depois de escrever, **rode o `plan` de novo** e compare: a cauda tem que
encolher. Se um cluster que a EV decidiu continuar aparecendo em `unresolved`, a
regra nao casou — mostre a regra emitida ao lado de uma amostra do cluster e
investigue, nao emita override para "resolver".

---

## 8. Aprovar, canario, lote

Nunca pule o canario. A ordem:

```bash
# 1. Canario de 20, em staging
aegro financial migrate-category apply --farm "<fazenda>" --env staging \
  --plan plano-salarios.jsonl --approve sha256:9f2c... --limit 20 --execute

# 2. Prova imediata
aegro financial migrate-category verify --farm "<fazenda>" --env staging \
  --plan plano-salarios.jsonl --sample 20

# 3. So depois, o lote (retomavel pelo ledger)
aegro financial migrate-category apply --farm "<fazenda>" --env staging \
  --plan plano-salarios.jsonl --approve sha256:9f2c... --concurrency 4 --execute

# 4. Prova final
aegro financial migrate-category verify --farm "<fazenda>" --env staging \
  --plan plano-salarios.jsonl
```

- `--approve <hash>` e **obrigatorio**. Sem ele o CLI imprime o hash e sai com 4.
  Peca a aprovacao **explicita** da EV antes de colar o hash — ela e o gesto de
  autorizacao, nao burocracia.
- O `apply` **recusa plano com mais de 24h** (`--max-plan-age-hours`). Nao
  aumente o teto para contornar: gere o plano de novo. A base mudou.
- **Staging restaura de producao diariamente** (~06:25 UTC). Plano gerado antes
  do restore fica obsoleto, e o canario se desfaz. Otimo para ensaio, inutil
  como registro.
- **Producao e decisao humana.** Nunca rode `--execute` em producao sem o
  usuario pedir naquele turno, com a fazenda nomeada. Repita o canario de 20 em
  producao e confira na UI antes do lote.
- `--concurrency` 4 por padrao (~340 ms por escrita medidos). Acima de 8 sai
  aviso.
- O ledger `<plano>.ledger.jsonl` e append-only: rodar de novo **retoma** de onde
  parou. Se o lote abortar, nao apague o ledger.

---

## 9. Ler o `verify`

Detalhe campo a campo em
[`reference/interpretacao.md`](reference/interpretacao.md). O essencial:

| Campo | Leitura |
|---|---|
| `migrados` | saiu da categoria antiga — OK |
| `naoTentados` | **nao e falha.** E o que falta aplicar (normal depois do canario) |
| `falharam` | tentadas e ainda na antiga |
| `falhaSilenciosa` | **a mais grave**: ledger diz OK e a conta continua na antiga. Assinatura do FNC-184 |
| `aindaNaCategoriaAntigaSemEstarNoPlano` | alguem mexeu por fora, ou a varredura achou algo novo |
| `alteracaoColateral` | mudou campo alem da categoria — **pare e investigue** |

O `verify` sai com codigo 1 quando algo tentado falhou. **Criterio de pronto do
trabalho inteiro:** `category-usage --from "<antiga>"` devolver **0**.

---

## 10. Guardrails

1. **Toda escrita e proposta, nunca silencio.** Mostre o agregado e peca
   confirmacao antes de cada `apply --execute`. A EV decide; voce conduz.
2. **Recorrente e bloqueado, nao migrado.** PATCH publico em bill recorrente e
   no-op silencioso (FNC-184, esperando fix do backend): responde 200 e nao
   salva. O plano bloqueia com `blockedReason: recurrence` **de proposito**.
   Explique isso a EV sem assustar: nao e erro dela nem dado corrompido, e um
   conjunto que migra depois **com o mesmo comando e sem codigo novo**. O numero
   de bloqueados e a evidencia que prioriza o fix — reporte-o.
3. **Nunca chute destino.** Sem regra e sem override, o lancamento fica
   `unresolved` e **nao e escrito**. Isso e feature.
4. **Destino obvio pode ser sintetico.** A ativa "Manutencao de Maquinas e
   Equipamentos" parece o destino natural da maior categoria e **nao e
   lancavel** — seriam 3.620 falhas. O CLI barra; nao tente contornar.
5. **Nao edite `plano.jsonl`, `.meta.json` nem o ledger a mao.** Todos os tres
   sao registro. Mudou de ideia? Muda o de/para e roda `plan`.
6. **Um erro estrutural aborta o lote** e isso e correto: e bug do plano.
   Corrija o de/para e replaneje — nao suba `--max-failures`.

---

## 11. Anti-padroes

- NAO aprovar o hash sem a EV ter visto os `blocked` e o agregado.
- NAO pre-marcar sugestao `assistant` ou `lexical`, por mais obvia que pareca.
- NAO transformar a cauda inteira em `overrides` por billKey porque e mais
  rapido — vira residuo que ninguem consegue auditar depois.
- NAO usar `keep` como "nao sei": `keep` significa "fica na antiga de proposito",
  e exige `why`. "Nao sei" e `adiar` (volta na proxima rodada).
- NAO publicar a tela como artifact hospedado nem mandar `unresolved.json` para
  fora da maquina.
- NAO rodar `--execute` em producao por iniciativa propria.
- NAO tratar `naoTentados > 0` como falha.
- NAO seguir para o lote com `falhaSilenciosa > 0`.

---

## 12. Referencia de comandos

| Comando | Params principais | Tipo |
|---|---|---|
| `financial category-usage` | `--from <cat>` (repetivel) `[--group-by tag,company,element,level]` `[--top N]` `[--start-date --end-date]` | leitura |
| `financial migrate-category plan` | `--map <json>` `--out <jsonl>` `[--no-suggest]` `[--samples N]` `[--start-date --end-date]` | leitura |
| `financial migrate-category apply` | `--plan <jsonl>` `--approve sha256:...` `[--limit N]` `[--concurrency 4]` `[--max-failures 25]` `[--max-plan-age-hours 24]` `--dry-run`/`--execute` | **escrita** |
| `financial migrate-category verify` | `--plan <jsonl>` `[--sample 10]` | leitura |
| `fin-categories list` | `[--status ACTIVE]` `[--type]` `[--operation-type]` `[--search-text]` `[--page N]` | leitura |
| `auth login` | `[--env staging]` | — |

Todos aceitam `--farm`, `--env` e `-o json|table|csv`. Codigos de saida:
**2** falta OAuth · **4** entrada invalida (de/para, hash, plano velho) ·
**1** o lote abortou ou o `verify` achou falha.

---

## Skills relacionadas

- `aegro-financeiro` — lancamentos, parcelas, categorias, contas, empresas.
- `aegro-lancamento-financeiro` — decidir como registrar conta a pagar/receber.
- `aegro-conciliacao-bancaria` — mesmo padrao de divisao: comando fino, skill
  orquestra e apresenta.
- `xlsx` — ler a planilha da EV quando vier em `.xlsx`.
