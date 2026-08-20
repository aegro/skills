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
version: 0.3.2
---

# Aegro Migracao de Categorias em Massa

Skill para tirar milhares de lancamentos de categorias arquivadas e leva-los
para a arvore nova, com a decisao humana concentrada em dezenas de grupos em
vez de espalhada por 20 mil lancamentos.

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
> **Requer os comandos `financial migrate-category`.** Prove com `--help` antes
> de qualquer coisa (secao 1.1) — a checagem e por capacidade, nao por numero de
> versao.
>
> **Canario sem `--stratify-by` nao e prova.** `--limit N` seco pega as N
> primeiras do plano, nao uma amostra representativa. Sempre
> `--limit N --stratify-by apportion,level,cashFlow` (secao 8.1), e leia
> [`reference/interpretacao.md`](reference/interpretacao.md) 4.1 a 4.3 antes de
> liberar qualquer lote.
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

## 1. Antes de qualquer comando

### 1.1 Checagem de capacidade — faca isto primeiro, sempre

```bash
aegro --version
aegro financial migrate-category plan --help
```

**Quem decide e o `--help`, nao a versao.** Se o `--help` sair 0, a maquina de
migracao existe neste CLI e voce pode seguir — qualquer que seja o numero da
versao. Se o `--help` falhar, **pare e diga isto ao usuario**, sem contornar:

> Esta skill precisa dos comandos `financial migrate-category`, que este `aegro`
> nao tem (voce esta na versao X). Atualize com
> `uv tool install aegro@latest --force` (ou `pip install -U aegro`) e rode de
> novo.

**O comando de upgrade importa.** `uv tool upgrade aegro` **nao atualiza** uma
instalacao com pin exato: ela roda, atualiza dependencias, sai com sucesso e
deixa o `aegro` na versao velha (medido em campo — a mensagem diz
`aegro is pinned to 0.15.0 ... reinstall with uv tool install aegro@latest`).
Quem seguisse a instrucao antiga acharia que atualizou e nao teria atualizado.

A versao e **informativa**: com o `--help` funcionando, siga. Por que nao barrar
por numero: build de desenvolvimento deriva a versao da ultima tag, entao um
`0.17.1.dev2` **tem** os comandos enquanto um `0.18.0` publicado nao tinha.
Medido: o gate numerico reprovava exatamente o binario que tinha a feature.
Comparacao de versao responde a pergunta errada — a certa e "os comandos
existem?", e so o `--help` responde isso.

**Sonde tambem as flags que voce vai usar**, no mesmo `--help`, porque a skill
chega por `aegro skills sync` (sem release do CLI) e pode encontrar CLI velho:

| Flag | Se faltar |
|---|---|
| `--effective-start/--effective-end` | o recorte pela data da tela nao existe: so `--start-date/--end-date` (data de lancamento). Diga isso ao usuario **antes** de perguntar o recorte (1.2) |
| `--labels/--no-labels` | o `unresolved.json` vem sem nomes; resolva voce (secao 6) |
| `--resume/--no-resume`, `--sweep-concurrency` | varredura sem retomada; falha no meio custa a corrida inteira |
| `--stratify-by` | canario manual (secao 8.1) |
| `sources` no de/para | categoria de origem SEM regra nao e varrida, e os lancamentos dela **desaparecem** do plano (95 deles em campo). Sem a flag, use uma regra sentinela por categoria: `{"from": "<antiga>", "to": "<qualquer ativa>", "when": {"allTags": ["__NAO_CASA__"]}}` |
| `--only-bill` no `apply` | para reaplicar um subconjunto, monte um de/para dedicado com overrides e rode um `plan` inteiro |
| `--max-transient-failures` | 429 conta como falha e aborta o lote por `--max-failures`: baixe `--concurrency` para 2 antes de comecar |
| `<plano>.verify.json` | `chavesQueFalharam` vem cortado em 20; para a lista inteira, releia conta a conta (custa minutos) |

O risco que sobra e real: guard novo no CLI que a skill nao conhece produz plano
que parece certo e nao e. Se algo na saida do CLI nao bater com o que esta
escrito aqui, **acredite no CLI e relate**.

### 1.2 Contrato de abertura — pergunte antes de gastar

**Faca esta rodada de perguntas ANTES do primeiro comando que custe minutos.**
Uma vez, em lote, com o preco na mesa. Nao e formalidade: a sessao de campo de
14/08 gastou ~1h50 em varreduras que morreram sem produzir arquivo, e o recorte
que teria evitado isso nunca foi oferecido como escolha.

A regra geral, e ela vale alem desta lista: **decisao que a EV toma em 10
segundos e economiza mais de 5 minutos de maquina e sempre perguntada — antes,
nunca depois.** O inverso tambem: o que nao muda com a resposta dela (formato de
payload, ordem de requisicoes, concorrencia) **nunca** vira pergunta.

Levante o barato primeiro (`fin-categories list` responde em segundos) e
pergunte:

1. **Qual recorte?** E a pergunta que mais muda o resultado, e ela tem duas
   respostas possiveis que parecem a mesma:
   - **data de lancamento** (`--start-date/--end-date`): quando a conta foi
     registrada;
   - **a data que aparece na tela do Financeiro**
     (`--effective-start/--effective-end`): pagamento quando a parcela esta
     paga, vencimento quando nao. **E o que a EV quer dizer com "as contas de
     2026"** — e o pedido real de 14/08 era este.

   Pergunte na lingua dela: *"'as contas de 2026' e pelo que aparece na tela do
   Financeiro (pagou/vence em 2026) ou pela data em que o lancamento foi
   registrado?"*. Sem recorte tambem e resposta valida: migra a divida inteira
   da categoria.
2. **Por onde comecar?** Todas as categorias ou as N maiores primeiro? Migrar
   por partes e **seguro por construcao** (o que fica de fora vira `unresolved`,
   e `unresolved` nunca e escrito) — diga isso, porque ela provavelmente acha
   que precisa fazer tudo de uma vez.
3. **A planilha esta completa?** Parcial nao bloqueia nada (secao 4.1). Traga
   isso para a abertura em vez de descobrir depois.
4. **Ambiente e fazenda.** Staging primeiro? Qual fazenda, nomeada?

Depois das respostas, **anuncie o custo e so entao rode** (secao 2).

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
aposenta o caso duvidoso em vez de traze-lo de volta.

### 2.1 Custo: anuncie antes, nunca prometa segundos

**O CLI diz o preco antes de gastar — repasse isso.** Logo depois da primeira
pagina, o `plan` imprime no **stderr** a estimativa, e ela e **exata**, nao
palpite: vem do `totalPagesCount` do servidor.

```
aegro: varredura: 11.291 lancamentos declarados, 113 paginas, ~6 min restantes.
```

O que fazer com essa linha:

- **acima de ~5 min, pare e confirme com a EV** antes de deixar rodar, mostrando
  a alternativa de recorte (secao 1.2);
- abaixo disso, informe e siga.

**No recorte por data efetiva sao DUAS linhas, e repassar so a segunda mente.**
A primeira diz quantos lancamentos o RECORTE tem; a segunda, como o CLI vai
busca-los — e o numero dela e o da **categoria inteira**, porque paginar a
categoria costuma ser a rota mais barata:

```
aegro: recorte por data efetiva 2025-12-01..2026-08-19: 1.432 lancamento(s) nas
categorias de origem, achados em 1 requisicao.
aegro: 1.301 contas a buscar numa categoria de 21.691: paginar custa 217
requisicoes contra 1.301 lendo uma a uma. Lendo por paginas.
```

Em campo eu repassei so "21.691 lancamentos, 217 paginas" e o Antonio corrigiu:
*"nao tem 21 mil lancamentos de dezembro para ca"*. Ele estava certo — o recorte
era 1.432. **Diga o numero do recorte primeiro**, e o da rota como custo.

Durante a corrida o CLI emite progresso a cada poucos segundos. **Repasse o
essencial**: silencio de dezenas de minutos foi lido em campo como "travou", e
custou corridas abortadas na mao.

Duas coisas que mudaram o custo e a conversa:

| Antes | Agora |
|---|---|
| custo era funcao do **intervalo de datas** (varredura bissectava desde ~2000, uma conta perdida em 2011 pagava a arvore inteira) | custo e **1 requisicao por pagina de 100**; a bisseccao so entra como reparo se a contagem nao fechar |
| falha no minuto 55 devolvia **zero** | a varredura tem checkpoint (`<plano>.sweep.jsonl`): retoma de onde parou |
| token de ~1h vencia no meio e matava a corrida | renova sozinho dentro da sessao |
| recorte pela data da tela **nao existia** | `--effective-start/--effective-end`; o CLI escolhe sozinho a rota mais barata para busca-lo e diz qual escolheu (secao 5) |

Se voce estiver num CLI que **nao** tem essas flags (secao 1.1), assuma a pior
hipotese antiga — varredura sem recorte custa dezenas de minutos — e **nunca
prometa iteracao instantanea**.

### 2.2 Espera longa nao sequestra a conversa

`plan` de muitos minutos roda em **segundo plano**. Enquanto ele corre, use o
tempo com a EV: revise a planilha, ou a cauda da rodada anterior. Volte com
atualizacoes em vez de sumir.

Se a corrida morrer, **diga o que o checkpoint preservou** e o custo real de
retomar (o CLI avisa "retomando a varredura de ..." e so vai a rede pelo que
falta). Nunca refaca em silencio — foi assim que a sessao de campo perdeu quase
duas horas sem ninguem perceber o padrao.

**Confirme a leitura da planilha ANTES do `plan`** (secao 4): refazer custa a
varredura inteira de novo.

---

## 3. Papeis: o que e do CLI e o que e seu

| Trabalho | Quem faz |
|---|---|
| Varrer, casar regra, montar payload, bloquear, agrupar a cauda, tabular precedente | **CLI** (`plan`) |
| Resolver o nome de fornecedor e insumo da cauda (`labels`) | **CLI** (`plan`) |
| Converter a planilha em de/para JSON | **voce** (secao 4) |
| Perguntar o recorte e anunciar o custo | **voce** (secao 1.2 e 2.1) |
| Renderizar a tela, **em portugues de negocio**, e receber as decisoes | **voce** (secao 6) |
| Expandir decisao em `rules`/`overrides` | **voce** (secao 7) |
| Escrever na API | **CLI** (`apply`) |
| Provar o resultado | **CLI** (`verify`) |

O CLI **nao emite palpite de LLM**. Voce pode acrescentar uma sugestao sua
(`source: "assistant"`), sempre rotulada e **nunca pre-marcada** — ver secao 6.

---

## 4. Planilha do usuario -> arquivo de/para

**Nao exija formato.** Voce e um compilador, nao um validador de schema: leia o
que veio, infira o que significa, **confirme a leitura**, e so entao compile em
regra deterministica. Passo a passo em
[`reference/planilha.md`](reference/planilha.md) — leia antes de tocar em
qualquer planilha.

Por que isso importa: nenhum cliente vai adotar um padrao seu. Medido em campo,
a planilha real nao tinha nenhuma das colunas que a primeira versao desta skill
exigia — e mesmo assim estava **certa**, so falava outra lingua (o eixo era
*conjunto de tags*, nao categoria).

O resumo do que muda na sua cabeca:

| Nao faca | Faca |
|---|---|
| exigir colunas `de`/`para` | descobrir qual coluna identifica o lancamento e qual da o destino |
| assumir que 1 valor = 1 tag | checar se o valor traz **varias** tags juntas -> `allTags` (E), nao `anyTags` (OU) |
| deduzir pelo nome da coluna | cruzar os valores com `category-usage --group-by tag,company,element` |
| resolver destino por nome | resolver por **codigo** contabil quando existir (nome duplica, codigo nao) |
| exigir a planilha completa | migrar o que esta completo e **medir** o que falta (secao 4.1) |

Voce pode ser flexivel na entrada porque a saida nao e: o `when` e uma whitelist
fechada e o CLI recusa qualquer coisa fora dela.

**Tres erros da planilha real que so aparecem na hora de escrever** (medidos em
19/08/2026, planilha de 1.777 linhas):

| Erro | Como aparece | O que fazer |
|---|---|---|
| **codigo contabil desatualizado com nome certo** | "Venda Pecuaria 3.1.2", mas a lancavel e a 3.1.2.1 | resolver por codigo falha e por nome funciona — quando os dois discordam, **confirme com a EV** e prefira o nome |
| **destino de natureza oposta** | aporte que ENTRA apontado para categoria de investimento (saida); despesa com agrupador `VENDA DE MILHO` apontada para receita | o `when` **nao tem** dimensao de fluxo de caixa, entao regra nao separa: a saida e override por conta. Foram 11 contas |
| **conjunto de agrupadores contido em outro** | 84 pares em que o conjunto de uma regra esta contido no de outra, com destino diferente | emitir da **mais especifica para a mais geral** e obrigatorio (secao 7). **Meca e reporte esses pares antes de aplicar** — e o erro que muda destino sem ninguem ver |

### 4.1 Planilha pela metade nao bloqueia nada

Metade em branco e o estado **normal** (na planilha real: 896 de 1.777 linhas
sem destino). Isso **nao** impede migrar as outras.

1. Compile as linhas completas e rode com elas.
2. Meca o que falta antes de perguntar: "faltam 896 linhas" e ruido; "faltam 12
   grupos que somam 3.620 lancamentos, e 3 deles sao 2.900" e uma conversa.
3. Pergunte **uma vez, em lote**, do maior para o menor.
4. Siga. O que ficou sem destino vira `unresolved`, e `unresolved` **nunca e
   escrito** — nao ha risco nenhum em migrar so uma parte.

Diga isso ao usuario, porque ele provavelmente acha que precisa terminar a
planilha antes de comecar. Ele nao precisa.

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

Responde "isto sao 12 grupos ou 800?" com completude provada, e e o passo mais
barato do fluxo — o unico que responde o tamanho antes de qualquer compromisso.

Depois, com o recorte que a EV escolheu na abertura (secao 1.2):

```bash
# Sem recorte: a divida inteira da categoria.
aegro financial migrate-category plan --farm "<fazenda>" --env staging \
  --map depara.json --out plano-salarios.jsonl

# Pela data que aparece na TELA do Financeiro (pagou/vence no periodo).
aegro financial migrate-category plan --farm "<fazenda>" --env staging \
  --map depara.json --out plano-2026.jsonl \
  --effective-start 2026-01-01 --effective-end 2026-12-31

# Pela data de LANCAMENTO (quando a conta foi registrada).
aegro financial migrate-category plan --farm "<fazenda>" --env staging \
  --map depara.json --out plano-ago23.jsonl \
  --start-date 2023-08-01 --end-date 2023-08-31
```

Os dois recortes **nao se combinam** — o CLI recusa com exit 4, porque
responderiam perguntas diferentes na mesma corrida. Cada um tem um preco
explicito, e a EV precisa saber qual esta pagando:

| Recorte | Fica de fora | O CLI avisa? |
|---|---|---|
| nenhum | nada | — |
| `--effective-*` | conta **sem parcela** (a vista sem pagamento / sem condicao): ela nao tem data efetiva | **sim**, conta quantas sao no stderr e grava em `meta.sweep.semParcelaForaDoRecorte` |
| `--start-date/--end-date` | conta com **data de lancamento nula** | nao — sem janela ela entra; com janela, nao |

**Como o recorte e buscado nao e decisao sua nem da EV — e do CLI.** Vale saber
o que ele faz, porque voce vai ver isso no stderr e vai precisar explicar.

Quais contas entram e **sempre** a enumeracao do servidor. O que o CLI escolhe e
so como buscar o conteudo delas, e as duas rotas tem custo oposto: ler uma a uma
custa 1 requisicao por **alvo**; paginar a categoria custa 1 por **cada 100**
lancamentos, alvo ou nao. Medido em staging (18/08/2026, FAZENDAS RAIZES AGRO):
79 alvos custaram 81 requisicoes lendo um a um, enquanto a categoria inteira
(150 contas) sai em 2 paginas.

Ele sonda a categoria, compara os dois custos e vai pela rota mais barata,
dizendo qual escolheu e com que numeros:

```
aegro: 3.000 contas a buscar numa categoria de 21.856: paginar custa 219
requisicoes contra 3.000 lendo uma a uma. Lendo por paginas.
```

**Repasse essa linha, nao a transforme em pergunta.** Escolher rota e decisao de
engenharia — a EV nao tem como responder, e em 14/08 esse tipo de conta virou
tempo parado. Se ela perguntar por que demora, a linha ja tem a resposta.

O que sobra para voce e o recorte em si (seçao 1.2), que muda o **resultado**, e
nao a rota, que muda so o custo. E a garantia que sustenta isso: o conjunto e
reconciliado **por chave** no fim, e todo alvo que a rota escolhida nao trouxe e
lido individualmente e contado — rota nunca perde conta em silencio.

### 5.1 Declare o escopo da corrida (`sources`)

**Categoria de origem que nao tem regra tem que estar em `sources`, ou os
lancamentos dela desaparecem.** Em campo (19/08/2026) a migracao foi dividida em
11 lotes de categorias; nos lotes onde parte das categorias nao tinha regra, elas
nao foram varridas, e seus lancamentos nao apareceram nem como "sem destino" —
**95 lancamentos**, achados so porque alguem comparou a contagem entre duas
rodadas.

```json
{
  "version": 1,
  "sources": ["Manutencao de Maquinas ANTIGA", "Taxas ANTIGA"],
  "rules": [{"from": "Taxas ANTIGA", "to": "Taxas e Emolumentos"}]
}
```

Aqui a "Manutencao" e varrida sem ter regra: os lancamentos dela entram como
**sem destino** e aparecem na tela para a EV decidir. O `plan` avisa alto, com
nome, e grava `sourcesWithoutRule` no meta. Regra de bolso: **toda categoria que
a EV mencionou nesta rodada vai em `sources`**, tenha regra ou nao.

### 5.2 Fazenda grande: lotes por categoria

Para fazenda com dezenas de milhares de lancamentos, divida o de/para em lotes de
categorias, com teto de ~2.500 lancamentos por lote. Isso resolveu tres coisas de
uma vez em campo:

- **504 de paginacao profunda.** A varredura das 67 categorias juntas (21.691
  lancamentos, 217 paginas) falhou **cinco vezes na mesma ultima pagina** — offset
  ~21.600, sempre 504, com timeout de 30 s e de 120 s. As 216 anteriores passam
  sempre. Nenhum lote pagina tao fundo, e os 11 fecharam de primeira.
- **retomada barata**: refazer um lote custa minutos, nao a corrida.
- **429 diluido**: menos pressao de cota por corrida.

Custa mais comandos, e exige o `sources` de cada lote (5.1). Diga isso a EV: e
uma escolha de robustez, nao um contorno improvisado.

Gera **tres** arquivos e imprime o hash:

| Arquivo | Conteudo |
|---|---|
| `plano-salarios.jsonl` | uma linha por lancamento, com o payload pronto |
| `plano-salarios.jsonl.meta.json` | contagens, varredura, `planHash`, `sourceKeys`, o recorte usado |
| `plano-salarios.jsonl.unresolved.json` | a cauda agrupada em clusters, com sugestao **e os nomes** (`labels`) |

Um quarto arquivo aparece quando a varredura **nao** fecha:
`<plano>.sweep.jsonl` e o checkpoint. Ele existir significa "a corrida anterior
nao terminou" — rode de novo e ela retoma. Nao apague, e nao edite.

`plan` e `verify` **nao escrevem nada** na API. Rodar `plan` de novo com o mesmo
dado da o **mesmo hash** — plano e deterministico, e re-planejar nao invalida uma
aprovacao a toa.

Status possiveis de cada linha: `planned` · `unresolved` · `kept` · `blocked`.
Os motivos de bloqueio e como explica-los a EV estao em
[`reference/interpretacao.md`](reference/interpretacao.md).

---

## 6. A tela de triagem

> **A tela nao e opcional — nem quando a cauda e vazia.** O painel de aprovacao
> mora nela, e a caixa *"revisei o que nao vai mudar"* travando o download e
> justamente o que impede aprovar um hash sem olhar os bloqueados. Em 14/08 o
> proprio assistente pulou a tela e apresentou o agregado como tabela no chat,
> justificando que a cauda era irrelevante; com isso o gate de seguranca virou
> carimbo. Se a cauda estiver vazia, a tela fica so com o painel — e ainda assim
> e nela que a EV aprova.

Template e protocolo completos em
[`reference/tela-triagem.md`](reference/tela-triagem.md). **A regra que manda
ali:** termo de negocio na frente, termo tecnico no maximo entre parenteses, e
nenhum rotulo em ingles visivel. A tela foi rejeitada em campo com as palavras
*"muito ruim", "bem esquisito", "nao e uma linguagem que os EVs vao entender"* —
e a decomposicao disso virou o template atual.

O que a tela cobre:

1. **Painel de aprovacao** (topo): fazenda, ambiente, quando foi gerado, o
   `planHash` com botao de copiar, as contagens por status, o agregado por
   regra, os **bloqueados por motivo**, e aviso alto se a varredura nao fechou.
   A EV precisa ver o que **nao** vai migrar antes de liberar o hash — aprovar
   sem olhar os `blocked` e o ponto cego que o FNC-184 criou.
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
2. **Os nomes de fornecedor e insumo ja vem prontos**, no bloco `labels` do
   `unresolved.json` (`{"companies": {...}, "elements": {...}}`). Use-os: cartao
   que diz `company::64a0...` nao e decidivel. Chave ausente do mapa e chave que
   nao resolveu — mostre a chave crua, nao invente nome.

   *Se o CLI for anterior a `--labels`* (secao 1.1), resolva voce — e **um `get`
   por chave citada**, nao a listagem. Parece errado e nao e: a cauda cita
   dezenas de chaves, enquanto `companies list` paginado estourou 10 minutos com
   2.254 fornecedores em campo.
3. Carregue o catalogo de categorias lancaveis para a EV escolher destino:
   `aegro fin-categories list --farm "<fazenda>" --status ACTIVE --page N -o json`
   (50 por pagina; pagine ate acabar). Descarte `type: "SYNTHETIC"` — sintetica
   e agrupadora e **nao e lancavel**.
4. Monte o HTML a partir do template e escreva num diretorio de trabalho local
   (ao lado do plano). Abra no navegador.
5. A EV decide e clica **Baixar decisoes** -> `decisoes-<plano>.json` na pasta
   de downloads dela.
6. Voce le esse arquivo e expande em `rules`/`overrides` (secao 7).

---

## 7. Decisoes -> regras

**Prefira regra a override.** Regra e auditavel e re-executavel; override e
residuo.

**O CLI agrupa pelo sinal mais forte, e o primeiro deles e o agrupador.** Isso
mudou: antes ele agrupava por fornecedor+descricao, e onde a descricao e quase
unica por conta isso virava quase um cartao por lancamento — medido, 959 sem
regra viraram **745 clusters, 631 deles com um unico lancamento**. Os mesmos 959
por **agrupador** dao **21 grupos**, e agora e o CLI que faz isso (o eixo e o
CONJUNTO de agrupadores da conta, que vira uma regra `allTags` direta).

Se voce estiver num CLI anterior a isso (cluster `by` nunca vem `tags`), o
reagrupamento volta a ser seu: cruze os `billKeys` da cauda com
`category-usage --group-by tag`. **Nao despeje 745 cartoes na tela de ninguem**
— se nem por tag colapsar, diga isso ao usuario.

Use override so quando o cluster nao tem sinal nenhum (`by: "none"`) ou quando a
decisao e "resolver manualmente".

Expansao, por tipo de cluster:

| `cluster.by` | Vira | `when` |
|---|---|---|
| `tags` | regra | `{"allTags": tags}` — o conjunto inteiro, como veio |
| `company+fingerprint` | regra | `{"companyKeys": [companyKey], "descriptionFingerprint": fingerprint}` |
| `company` | regra | `{"companyKeys": [companyKey]}` |
| `fingerprint` | regra | `{"descriptionFingerprint": fingerprint}` |
| `element` | regra | `{"elementKeys": elementKeys}` |
| `none` | **override por billKey** | — |
| acao `manual` (qualquer `by`) | **override `keep: true` por billKey** — e a conta entra no relatorio final (secao 9.2). O `why` da tela e opcional; se vier vazio, use "resolver manualmente" | — |
| acao `adiar` | nada — volta na proxima rodada | — |

Tres coisas que quebram silenciosamente se voce nao cuidar:

1. **Uma regra tem um `from` so.** Cluster com varios `fromKeys` vira **uma
   regra por fromKey**, mesmo `when` e mesmo `to`.
2. **Ordem importa: da regra mais especifica para a mais geral.** Emita nesta
   ordem — `company+fingerprint`, depois `tags`, depois `fingerprint`, depois
   `element`, depois `company` — e **acrescente ao fim** das regras que ja
   existem no de/para. Uma regra `{"companyKeys": [c1]}` posta antes de
   `{"companyKeys": [c1], "descriptionFingerprint": "..."}` engole o grupo
   especifico sem avisar ninguem.
3. **Override numa conta com itens de origens diferentes e recusado.** Override
   e decisao por CONTA e escreve o mesmo destino em todo item que esteja em
   categoria de origem; numa conta que mistura duas origens, isso colapsaria as
   duas num destino so. O CLI bloqueia com `override-multi-source` — e a saida e
   **regra**, que decide item a item. Se voce ver esse motivo no plano, nao
   tente contornar com mais override.

Depois de escrever, **rode o `plan` de novo** e compare: a cauda tem que
encolher. Se um cluster que a EV decidiu continuar aparecendo em `unresolved`, a
regra nao casou — mostre a regra emitida ao lado de uma amostra do cluster e
investigue, nao emita override para "resolver".

---

## 8. Aprovar, canario, lote

Nunca pule o canario — e **estratifique** antes (secao 8.1), porque `--limit N`
pega as N primeiras do plano, nao uma amostra representativa. A ordem:

```bash
# 1. Canario de 20, em staging
aegro financial migrate-category apply --farm "<fazenda>" --env staging \
  --plan plano-salarios.jsonl --approve sha256:9f2c... \
  --limit 20 --stratify-by apportion,level,cashFlow --execute

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
- `--concurrency` 4 por padrao (~340 ms por escrita medidos; 21 escritas em 25 s).
  Acima de 8 sai aviso. **Concorrencia nao causa nem evita a falha silenciosa** —
  medido com `--concurrency 1` e o resultado foi identico.
- O ledger `<plano>.ledger.jsonl` e append-only: rodar de novo **retoma** de onde
  parou. Se o lote abortar, nao apague o ledger.

### 8.1 Canario estratificado — faca isto ANTES do canario normal

`--limit N` pega as **N primeiras pendentes do plano**, e a ordem do plano nao e
aleatoria. Medido: num plano com **95,6%** de contas com rateio de custo, as sem
rateio ficaram todas na frente — a primeira com rateio caiu no **indice 14**. O
canario de 20 pegou o no-op silencioso por **uma posicao**; `--limit 14` teria
fechado 20/20 verde e liberado 3.163 escritas que nao gravariam.

**O CLI estratifica — e voce so precisa pedir:**

```bash
--limit 20 --stratify-by apportion,level,cashFlow
```

A flag distribui as N do `--limit` pelas classes presentes no plano. As dimensoes
sao exatamente essas tres, e dimensao desconhecida e **erro**, nao silencio.

Duas coisas continuam sendo suas:

1. **`--limit` sem `--stratify-by` imprime aviso** listando as classes que a
   amostra deixou de fora. Nao engula esse aviso: repasse a EV, porque e a
   diferenca entre canario verde que prova algo e canario verde que nao prova nada.
2. **Mostre a composicao antes de escrever.** *"O plano e 90% ASSET_PRORATE/item,
   4% STOCK_INPUTS/item, 4% sem rateio, 2% CROP_PRORATE/conta — o canario vai
   pegar as quatro."* Ela aprova o hash sabendo o que a amostra cobre.

Se algum dia o CLI nao tiver a flag, a versao manual e um de/para so com
`overrides` (2–3 contas por combinacao) mais uma regra que nao casa com nada,
porque `rules` nao pode ser vazio. Foi assim que a terceira causa de
`falhaSilenciosa` apareceu, antes de existir `--stratify-by`.

**Evidencia nova, e mais forte que a anterior** (19/08/2026): um plano de 1.272
lancamentos tinha 7 classes, e uma delas tinha **1 unico lancamento** — justamente
o que a API recusa por apropriacao de custo por item. O canario de 55
estratificado o encontrou; um `--limit 50` seco tinha ~4% de chance de toca-lo.
Classe de 1 em 1.272 e exatamente o que estratificar existe para achar.

**Como distribuir entre lotes:** proporcional ao tamanho do lote, mas **nunca
menos que o numero de classes daquele lote** — abaixo disso a estratificacao nao
tem vaga para distribuir e o CLI avisa que a amostra deixou classes de fora.

---

## 9. Ler o `verify`

Detalhe campo a campo em
[`reference/interpretacao.md`](reference/interpretacao.md). O essencial:

| Campo | Leitura |
|---|---|
| `migrados` | saiu da categoria antiga — OK |
| `naoTentados` | **nao e falha.** E o que falta aplicar (normal depois do canario) |
| `falharam` | tentadas e ainda na antiga |
| `falhaSilenciosa` | **a mais grave**: ledger diz OK e a conta continua na antiga. Com os guards atuais deve ser **0** — ver [interpretacao.md](reference/interpretacao.md) 4.1 |
| `naCaudaAindaNaAntiga` | cauda, bloqueado e mantido: o plano sabe que ficam. **Informativo** |
| `colateralDeVerdade` | conta que o plano nunca viu. **> 0 e o unico caso que pede replanejar** |
| `alteracaoColateral` | mudou campo alem da categoria — **pare e investigue** |

O `verify` sai com codigo 1 quando algo tentado falhou. **Criterio de pronto do
trabalho inteiro:** `category-usage --from "<antiga>"` devolver **0**.

A lista completa de cada categoria (quem falhou, quem nao foi tentada, quem
mudou colateral) esta em **`<plano>.verify.json`** — o stdout corta em 20 de
proposito. E desse arquivo que sai o relatorio da secao 9.2.

### 9.1 Quando o Aegro nao grava e ninguem sabe por que: PERGUNTE

Existem duas coisas que acontecem na escrita, sao **excecao**, e **nao tem causa
identificada**:

| O que acontece | Medido em campo (19/08/2026) |
|---|---|
| **Nao gravou em silencio.** A API responde 200, o ledger registra OK, a conta continua na categoria antiga. Nao e nenhuma das causas conhecidas: reproduzivel com concorrencia 1, releitura minutos depois confirma, e as contas sao identicas a centenas que gravaram | **38 de 1.234** (3,1%) |
| **Gravou, e o total da conta mudou 1 centavo** — para cima ou para baixo. A soma dos itens continua certa; e o total que o servidor recalcula ao regravar `inputs` | **26 de 783** de nivel item (3,3%); nenhuma de nivel conta |

**Nao invente causa e nao bloqueie por palpite** (secao 10, item 8). E **nao
decida sozinho o que fazer**: as duas coisas mexem em como o cliente fecha o mes,
e isso e decisao dela, nao sua. Traga assim, com o numero na mao:

> Das 1.234 contas, **38 o Aegro respondeu que salvou e nao salvou** — nao ha
> causa conhecida, o time ja tem as chaves e nada foi corrompido. E **26** de
> nivel item migraram com **1 centavo** de diferenca no total da conta.
> Como voce prefere: eu arrumo essas 64 na mao agora, deixo para depois do
> lote inteiro, ou paro tudo aqui?

E pergunte especificamente sobre o centavo: **em fechamento contabil, centavo e
divergencia** — quem sabe se importa e ela.

### 9.2 O relatorio final: uma linha por conta, com link

**Toda migracao termina com um relatorio.** Nao um resumo: uma **linha por conta
que nao migrou ou que migrou com ressalva, com link direto** para ela no Aegro. E
o unico artefato com que a pessoa consegue trabalhar depois — sem ele, "38 contas
falharam" e uma informacao que nao se pode usar.

Monte a partir de tres fontes, todas locais:

| Fonte | O que tira dela |
|---|---|
| `<plano>.verify.json` | as listas INTEIRAS: `chavesQueFalharam`, `chavesComFalhaSilenciosa`, `chavesNaoTentadas`, `chavesColaterais` |
| `plano.jsonl` | de cada chave: data, descricao, fornecedor, valor, categoria de origem e destino, nivel, rateio, e o `blocked_reason` de quem o plano recusou |
| `arrumar-na-mao-<plano>.md` (baixado da tela) | as que a EV marcou como "resolver manualmente" |

Formato — o que funcionou em campo:

```markdown
# Contas com problema na migracao de categorias — <FAZENDA>

**<ambiente>, <data>.** <N> lancamentos no plano, **<M> migrados e provados**.

> Arquivo local com dado de cliente — nao versionar, nao publicar.

| Problema | Contas | Valor | O que fazer |
|---|---:|---:|---|
| Nao gravou em silencio (causa desconhecida) | 38 | R$ ... | aguardar o time; nada foi corrompido |
| Recusado: rateio aponta para local fechado | 16 | R$ ... | corrigir o dado apontado, migrar depois |
| Recusado: itens travados por apropriacao por item | 1 | R$ ... | editar os itens na tela do Aegro |
| Migrou, mas o total mudou 1 centavo | 26 | R$ ... | conferir se importa ao fechamento |

## <um bloco por problema>

| Data | Descricao | De | Para | Nivel | Valor | Link |
```

Quatro regras que o relatorio tem que respeitar:

1. **Um link por conta**, no ambiente onde a migracao rodou:
   `https://app.aegro.com.br/farm/{farmId}?billId={billId}#farm-finance`
   (`app.staging.aegro.io` em staging). O `farmId` vem de `meta.farmKey`.
2. **Agrupado por problema, com o que fazer em cada um.** "Falhou" nao diz se ela
   espera o time, corrige um cadastro, ou edita na tela.
3. **Ordenado por valor, decrescente.** Se ela so tiver tempo para dez, que sejam
   as dez que importam.
4. **Local, e dito no proprio arquivo.** Descricao, fornecedor e valor de cliente
   real: nao versione, nao publique, nao mande para servico externo.

Se o ensaio foi em staging, **escreva o ambiente no relatorio**: a chave e a mesma
de producao, entao o link abre a conta real e alguem pode achar que ja foi mexido.

---

## 10. Guardrails

1. **Toda escrita e proposta, nunca silencio.** Mostre o agregado e peca
   confirmacao antes de cada `apply --execute`. A EV decide; voce conduz.
2. **Escrita que responde 200 pode nao ter gravado.** Sao **tres** causas
   medidas de no-op silencioso, e o `plan` bloqueia as tres: `recurrence`,
   `revenue-item-apportioned-noop` e `stock-location-closed`. Confira o numero por
   motivo em `meta.blockedByReason`. `falhaSilenciosa > 0` num CLI atual significa
   **guard faltando ou causa nova** — pare e investigue
   ([interpretacao.md](reference/interpretacao.md) 4.1). Por isso `verify` nunca e
   opcional.
3. **Recorrente MIGRA por default — isso mudou em 20/08/2026.** O no-op silencioso
   do FNC-184 foi corrigido (serv-core#5304) e esta em **producao desde a release
   `v2026.08.17-114950`** (17/08/2026), em staging desde 13/08 — conferido por
   conteudo de branch no serv-core e **provado por releitura** em staging.
   O que voce precisa fazer com isso:
   - **nao repita "o Aegro nao grava recorrente"**. Era verdade e nao e mais; a
     tela tambem foi corrigida.
   - o `plan` **avisa** quantos recorrentes entraram, nomeando a release. Repasse:
     e escrita que antes nao acontecia.
   - `--no-allow-recurrent` e o escape, e serve para um caso so: **servidor mais
     antigo que aquela release** (serv-core local desatualizado, por exemplo). O
     CLI nao tem como saber a versao — quem sabe e quem roda.
   - sobra o 422 de recorrente **com parcela paga E itens**, bloqueado como
     `settled-recurrence-inputs`. No nivel da conta a mesma conta migra, e a maioria
     e de nivel conta: medido, 22 com parcela paga e **zero** barradas.
   - canario + verify continuam obrigatorios, **nao** por causa do FNC-184, e sim
     porque nenhuma escrita em massa aqui vai sem canario.
4. **Nunca chute destino.** Sem regra e sem override, o lancamento fica
   `unresolved` e **nao e escrito**. Isso e feature.
5. **Destino obvio pode ser sintetico.** A ativa "Manutencao de Maquinas e
   Equipamentos" parece o destino natural da maior categoria e **nao e
   lancavel** — seriam 3.620 falhas. O CLI barra; nao tente contornar.
6. **Nao edite `plano.jsonl`, `.meta.json` nem o ledger a mao.** Todos os tres
   sao registro. Mudou de ideia? Muda o de/para e roda `plan`.
7. **Um erro estrutural aborta o lote** e isso e correto: e bug do plano.
   Corrija o de/para e replaneje — nao suba `--max-failures`. Cota (429) e 5xx
   **nao** contam nesse teto (tem o proprio, `--max-transient-failures`): se o
   lote parar por eles, a resposta e baixar `--concurrency` para 2, nao subir teto.
8. **Nao bloqueie em massa por correlacao parcial.** O erro de julgamento mais
   caro da sessao de campo: com **5 casos** eu concluí que a causa do no-op era
   "rateio de patrimonio + desconto" e **bloqueei 32 lancamentos** com esse motivo
   escrito no plano. Ao desbloquear, **20 dos 22 gravaram normalmente**.
   Hipotese de causa exige o **2x2 completo** (com e sem cada condicao) e um teste
   que tente **derruba-la**, nao confirma-la. Enquanto a causa nao fecha, o certo e
   **tentar e deixar o `verify` acusar**: falha silenciosa nao corrompe nada, e
   bloquear por palpite custa migracao que funcionaria.
9. **Um processo por fazenda, sempre.** Duas corridas de `plan`/`apply` ao mesmo
   tempo **se invalidam na rotacao do token OAuth**, e o sintoma sao 401
   intermitentes que parecem instabilidade do servidor. Perdi cerca de uma hora
   nisso: parei um script e o **loop filho continuou rodando**, processando lotes
   em paralelo com o script novo. Ao matar um script, **confirme que o processo
   filho morreu** antes de comecar outro. O CLI avisa ("sessao usada em outro
   processo"), mas a mensagem se perde no meio dos 429.
10. **Staging reseta de madrugada: gere e aplique na mesma janela.** O reset
   apaga as credenciais do ambiente (`FARM_NOT_FOUND` do nada) e restaura a base,
   entao plano da noite anterior nao vale — e o `apply` recusaria plano com mais de
   24 h de todo jeito. As **decisoes** da EV nao se perdem (sao locais); as
   varreduras, sim.

---

## 11. Anti-padroes

- NAO aprovar o hash sem a EV ter visto os `blocked` e o agregado.
- NAO pre-marcar sugestao `assistant` ou `lexical`, por mais obvia que pareca.
- NAO transformar a cauda inteira em `overrides` por billKey porque e mais
  rapido — vira residuo que ninguem consegue auditar depois.
- NAO usar "resolver manualmente" como "nao sei": ele significa "essa eu arrumo
  na tela do Aegro", e a conta entra no relatorio final. "Nao sei" e `adiar`
  (volta na proxima rodada).
- NAO terminar a migracao sem entregar o relatorio de conta a conta (secao 9.2).
  "38 contas falharam" sem a lista com link e uma informacao inutilizavel.
- NAO decidir sozinho o que fazer com o no-op silencioso nem com o centavo
  (secao 9.1): os dois mexem no fechamento do cliente. Pergunte.
- NAO publicar a tela como artifact hospedado nem mandar `unresolved.json` para
  fora da maquina.
- NAO rodar `--execute` em producao por iniciativa propria.
- NAO tratar `naoTentados > 0` como falha.
- NAO seguir para o lote com `falhaSilenciosa > 0`.
- NAO comecar uma varredura longa sem oferecer o recorte como escolha (secao
  1.2) — foi assim que a sessao de campo perdeu ~1h50.
- NAO pular a tela porque "a cauda e irrelevante": o painel de aprovacao mora
  nela (secao 6).
- NAO repassar termo de implementacao para a EV (`unresolved`, `cluster`,
  `override`, `by: company+fingerprint`). Traduza — a tabela esta em
  [`reference/tela-triagem.md`](reference/tela-triagem.md).

---

## 12. Referencia de comandos

| Comando | Params principais | Tipo |
|---|---|---|
| `financial category-usage` | `--from <cat>` (repetivel) `[--group-by tag,company,element,level]` `[--top N]` `[--start-date --end-date]` `[--effective-start --effective-end]` `[--sweep-concurrency N]` | leitura |
| `financial migrate-category plan` | `--map <json>` `--out <jsonl>` `[--no-suggest]` `[--no-labels]` `[--samples N]` `[--start-date --end-date]` `[--effective-start --effective-end]` `[--resume/--no-resume]` `[--no-allow-recurrent]` `[--sweep-concurrency N]` | leitura |
| `financial migrate-category apply` | `--plan <jsonl>` `--approve sha256:...` `[--limit N]` `[--stratify-by apportion,level,cashFlow]` `[--only-bill <chave>]` `[--concurrency 4]` `[--max-failures 25]` `[--max-transient-failures 200]` `[--max-plan-age-hours 24]` `--dry-run`/`--execute` | **escrita** |
| `financial migrate-category verify` | `--plan <jsonl>` `[--sample 10]` — grava `<plano>.verify.json` com as listas inteiras | leitura |
| `fin-categories list` | `[--status ACTIVE]` `[--type]` `[--operation-type]` `[--search-text]` `[--page N]` | leitura |
| `auth login` | `[--env staging]` | — |

Todos aceitam `--farm`, `--env` e `-o json|table|csv`. Codigos de saida:
**2** falta OAuth · **4** entrada invalida (de/para, hash, plano velho) ·
**1** o lote abortou ou o `verify` achou falha.

**Os dois recortes, e o preco de cada um**, estao na secao 5. O recorte usado
vai no meta e o `verify` reusa o mesmo — nao passe recorte para o `verify`.

**Ao parsear a saida:** redirecione stdout e stderr **separados**. **stdout so
carrega o resultado** (o JSON/tabela/CSV); log, aviso (`aegro: ...`), progresso
e envelope de erro vao para stderr. Entao `2>&1` mistura texto com o JSON e o
parse quebra.

> **Isto mudou, e a versao anterior desta skill afirmava o contrario do que o
> CLI fazia.** O `structlog` nunca tinha sido configurado, e o default dele e
> **stdout**: num plano longo, o `aegro_api_retry` de um 504 caia no meio do
> JSON e quebrava o parse de quem seguia esta doc. O CLI foi corrigido.
>
> **Se voce estiver num CLI anterior a essa correcao**, o sintoma e exatamente
> esse — linha de log dentro do stdout. Ate atualizar, parseie de forma
> tolerante (procure o primeiro `{`) e **diga ao usuario que o CLI esta velho**,
> em vez de conviver em silencio.

---

## Skills relacionadas

- `aegro-financeiro` — lancamentos, parcelas, categorias, contas, empresas.
- `aegro-lancamento-financeiro` — decidir como registrar conta a pagar/receber.
- `aegro-conciliacao-bancaria` — mesmo padrao de divisao: comando fino, skill
  orquestra e apresenta.
- `xlsx` — ler a planilha da EV quando vier em `.xlsx`.
