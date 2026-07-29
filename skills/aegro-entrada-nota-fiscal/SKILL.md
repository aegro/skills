---
name: aegro-entrada-nota-fiscal
description: >-
  Orquestra a entrada de notas fiscais recebidas da SEFAZ no Aegro pela CLI:
  lista as notas nao lancadas, apresenta a ficha da nota (resumo identificavel +
  fornecedor resolvido + consulta SEFAZ), concilia produtos ao catalogo, verifica
  duplicidade e lanca como conta (bill) ou pedido de compra com vinculo NF-e<->bill.
  Sempre dry-run antes de execute. Detecta se o usuario e do time Aegro (staging-first)
  ou cliente (producao direta). Use quando pedirem "dar entrada em nota fiscal",
  "listar notas nao lancadas", "lancar essa NF-e como conta/pedido", "conciliar os
  itens da nota", "launch SEFAZ invoice", "give entry to a received invoice". NAO use
  para lancar conta manual sem nota (use /aegro-lancamento-financeiro), lancamento em
  massa por planilha, ou NFS-e municipal (fora do recorte v1 -> revisar na UI).
version: 0.4.2
---

# Entrada de Nota Fiscal no Aegro

## Objetivo

Decidir **o que fazer com uma NF-e recebida** e leva-la ao financeiro com
seguranca e rastreabilidade. Esta skill e a camada de **processo**: lista as
notas, mostra uma ficha identificavel, entende o que a nota e (despesa, receita,
remessa, retorno, transporte), concilia os produtos e **lanca** — como conta ou
pedido de compra — pelo grupo unificado `received-fiscal-documents`, que cria o
lancamento com **vinculo NF-e<->bill** (mesmo fluxo da UI web).

O preenchimento fino da conta (categoria, parcelas, rateio) apoia-se em
`/aegro-lancamento-financeiro`; aqui cuidamos da **decisao, da conciliacao e do
lancamento a partir do documento**.

## Modo da sessao: time Aegro vs. cliente (ler primeiro)

Antes de qualquer coisa, identifique quem esta operando pelo **e-mail do
usuario** disponivel no contexto da sessao:

- **Interno — e-mail `@aegro.com.br`** (time de Servicos / EV operando a fazenda
  de um cliente): fluxo **staging-first**. Valida na fazenda do cliente em
  `staging`, confere na UI de staging e so entao **reproduz em producao**. Mantem
  o **diario de sessao** (ver secao propria). Este e o modo do piloto ENTRADA-44.
- **Externo — qualquer outro dominio** (cliente operando a propria fazenda):
  opera **direto em producao**. **Nao conduza o cliente a staging** — o ambiente
  existe, nao e segredo, mas nao e o caminho dele. Diario/telemetria nao sao
  exigidos.

Se o e-mail nao estiver disponivel ou for ambiguo, trate como **externo** (o
default seguro e nao levar ninguem a staging). Um EV logado com conta pessoal
pode ativar o modo interno se dizer explicitamente que e do time.

> **A protecao que vale nos dois modos e o `--dry-run` antes de todo
> `--execute`**, conferido com quem opera. Em sessoes de agente, some a isso o
> `AEGRO_SAFE_MODE=1`: alem de exigir `--execute`, ele recusa escrita cuja fazenda
> nao veio de `--farm` (`IMPLICIT_FARM_BLOCKED`) — no envelope do dry-run, confira
> `farm` e `farmSource: "flag"` antes de aprovar.

## Pre-requisitos

- **Login OAuth**: os comandos usam **APIs internas** do Aegro — exige
  `aegro auth login` (nao funciona com API key). Confira com `aegro auth status`.
- Fazenda identificada em **cada comando** com `--farm "<Fazenda|farm::key>"`, e
  ambiente certo (`--env prod` no modo externo; `--env staging` no interno ate
  promover). Prefira a flag ao `farms select`: o state e global por maquina, e com
  varias sessoes abertas (uma por fazenda) a selecao de uma troca o alvo das
  outras. Em safe mode, a escrita recusa fazenda implicita
  (`IMPLICIT_FARM_BLOCKED`).
- `/aegro-financeiro` — bills, categorias, parcelas, empresas, contas bancarias.
- `/aegro-lancamento-financeiro` — sequencia de decisao de a pagar/receber.

## Comandos (grupo `received-fiscal-documents`)

Aliases PT entre parenteses. Todos aceitam `--env prod|staging`.

| Passo | Comando | O que faz |
|---|---|---|
| Listar | `list` (`listar`) `--start-date <YYYY-MM-DD> --end-date <YYYY-MM-DD> [--not-launched\|--launched] [--type NFE\|NFSE] [-o table]` | Resumo por nota: numero, fornecedor (e se ja tem cadastro), CFOPs, valor, se ja esta lancada e as contas vinculadas. Traz `sugestaoDestino` (triagem CFOP conservadora) e `instrucaoUI` para destinos nao executaveis. Alias PT: `--desde/--ate/--tipo/--texto`. |
| Detalhe | `items <doc>` (`detalhe`) `[--full]` | Itens (codigo, descricao, NCM, CFOP por item, qtd, valor), totais, pagamento/parcelas, fornecedor/produtor conciliados e sugestoes de elemento. `--full` = Invoice bruto. `doc` = numero, chave de acesso (44) ou key. |
| Status | `status <doc>...` | Confere em lote se cada nota ja foi lancada, com referencia das bills (guardrail contra duplicidade). |
| Conciliar | `conciliate <doc> --item CODIGO=elemento --execute` (`conciliar`) | Persiste o mapa produto-da-nota -> elemento (por fazenda+fornecedor+item), reaproveitado nas proximas notas. Elemento por nome ou id; preserva `conversionRate` salvo. |
| Lancar conta | `launch-bill <doc> --category X [--revenue\|--expense] [...] --dry-run/--execute` | Cria a conta **com vinculo NF-e<->bill**. `--revenue`/`--expense` **obrigatorio em nota de entrada**. |
| Lancar pedido | `launch-purchase-order <doc> --dry-run/--execute` | Idem como pedido de compra, com guard de pedido duplicado. |

> `preparar` foi **descontinuado** (ensinava o caminho publico sem vinculo
> NF-e<->bill, ENTRADA-84). Se aparecer, o stub aponta para `launch-bill --dry-run`.

Opcoes do `launch-bill` que replicam a UI web:
- `--category` (obrigatoria na pratica — aceita nome, id ou key; exige folha `ANALYTIC`)
- Modo de pagamento (os mesmos rotulos da UI): `--no-payment` (Sem pagamento),
  `--prompt` (A Vista: 1 parcela paga), `--installments N` (A Prazo: N mensais);
  sem nenhum, usa as duplicatas da propria nota.
- `--currency USD --exchange-rate 5.42` (moeda estrangeira; parcelas acompanham)
- `--create-company` (cria o fornecedor com os dados da nota) e
  `--company <nome|id|key>` (desambigua emitente com CNPJ duplicado)
- `--stock-location <key>` (baixa de estoque), `--apportion-crop "Safra X"` (rateio),
  `--asset <id>`, `--tag`, `--description`, `--producer`, `--force`.

## Fluxo de decisao

```text
list (janela recente, --not-launched)
        |
1. Escolher a nota -> FICHA DA NOTA (obrigatoria, antes de qualquer pergunta)
        |
2. DUPLICIDADE: status <doc>  (financialEntryMultiplicity != NONE OU relatedBills -> ja lancada)
        |
3. CLASSIFICAR pelo trio: papel da fazenda (emitiu/recebeu) + CFOP + natureza
        |
4. CONCILIAR (padrao): produtos (item -> elemento); fornecedor/produtor por CNPJ
        |
5. launch-bill (ou launch-purchase-order) --dry-run  ->  conferir  ->  --execute
        |
6. [modo interno] validado em staging -> reproduzir em producao (--dry-run primeiro)
```

## Sequencia de passos

### 1. Listar e escolher a nota

`list --not-launched` na janela desejada. Apresente ao usuario como **tabela de
conferencia em texto** antes de qualquer lancamento. `--launched` mostra as ja
lancadas.

### 1b. FICHA DA NOTA (obrigatoria, antes de qualquer pergunta)

Antes de perguntar categoria/pagamento/qualquer coisa, apresente uma ficha
identificavel da nota escolhida (dados do `list`/`items` + dry-run):

```
NF-e 9161610 - emitida 15/07/2026 - R$ 1.600.000,00
Emitente: fornecedor_x (CNPJ **.***.**8/0001-**) - fornecedor resolvido no cadastro: SIM
CFOP: 1949 (Outra entrada) - Tipo de operacao: ENTRADA/RETORNO
Itens: COLHEITADEIRA CR6.80 (1 un) - PLATAFORMA DE SOJA (1 un)
Conferencia externa: https://www.nfe.fazenda.gov.br/portal/consultaRecaptcha.aspx
  (colar a chave de acesso: 3526...  - 44 digitos)
```

Sempre inclua: numero, datas, valor, emitente **mascarado** + "fornecedor
resolvido: sim/nao", CFOPs com descricao, itens e o link de consulta publica da
SEFAZ com a chave, para conferir fora do Aegro. Para ver o documento fiscal:
`aegro received-fiscal-documents xml <doc> -o nota.xml` e `danfe <doc> -o nota.pdf`.

### 2. Verificar duplicidade

Rode `status <doc>` (ou leia `financialEntryMultiplicity`/`relatedBills` do
`list`/`items`). Considere **ja lancada** quando `financialEntryMultiplicity != NONE`
**OU** `relatedBills` preenchido — verifique os dois. Se ja lancada: conciliar
ou arquivar, **nunca duplicar**. O guard de duplicidade tambem age no
`launch-bill` e mostra a(s) conta(s) suspeita(s) (inclusive deletadas — causa
comum de falso positivo); so use `--force` depois de confirmar que nao e real.

### 3. Papel da fazenda + natureza fiscal

Do `items`: **a fazenda emitiu ou recebeu?** Combine com **CFOP** e **natureza
da operacao** — esse trio define a classificacao. Nao decida despesa/receita so
porque "parece compra".

**Nota de ENTRADA/RETORNO (CFOP 1xxx/2xxx, ex. 1949, 1905): cuidado redobrado.**
O CLI **se recusa a classificar** receita/despesa nessas notas (protecao apos um
quase-lancamento de R$ 1,6M como receita). Recomendacao default, nesta ordem:
1. **Arquivar** o documento (retorno de maquina/remessa sem efeito financeiro), ou
2. **Lancar sem efeito de pagamento** (`--no-payment` + `--expense`/`--revenue`
   — registro documental, sem parcelas), ou
3. So lancar cheio se o usuario confirmar o efeito financeiro real.
Nunca encaminhe lancamento cheio dessas notas sem alerta explicito.

### 4. Conciliar entidades — por padrao, sempre

Conciliar preserva o **detalhamento por item** (elemento do catalogo, custo,
estoque). Conduza a conciliacao salvo opt-out explicito:

- **Produtos**: para cada item use a **sugestao** do `items` ou busque candidatos
  (`aegro elements list -s "<nome do item>"`); rode
  `conciliate <doc> --item CODIGO=Nome --execute`. Fica salvo e reaproveitado.
  Nao existindo candidato, ofereca criar o elemento (`aegro elements create-item`)
  ou seguir sem baixa de estoque (explicando a consequencia).
- **Fornecedor / produtor**: vem conciliado por CNPJ->empresa no `items`; se
  faltar, use `--create-company` no lancamento ou cadastre em `/aegro-financeiro`.

> **Conciliacao parcial -> conta SEM baixa de estoque** (o backend exige total =
> soma dos insumos; e tudo-ou-nada). Para ter estoque, concilie **todos** os itens.

### 5. Lancar — sempre dry-run primeiro

```bash
# 1o: preview (nenhuma escrita acontece; o plano completo e exibido)
aegro received-fiscal-documents launch-bill --farm "<fazenda>" <NUMERO> --category "Categoria" --expense --dry-run

# 2o: so depois que o usuario conferir o plano (fornecedor, categoria, parcelas, valor):
aegro received-fiscal-documents launch-bill --farm "<fazenda>" <NUMERO> --category "Categoria" --expense --execute
```

Descubra o nome exato da categoria com `aegro fin-categories list -s "<trecho>"`
("Combustivel" nao casa "Combustiveis e Lubrificantes"); a conta exige categoria
**ANALYTIC** (folha) — sinteticas nao servem.

Como **pedido de compra**: `launch-purchase-order <doc> --order-code <n> --dry-run`
(depois `--execute`). Requer itens conciliados (itens sem conciliacao ficam fora
do pedido — o comando avisa); itens conciliados ao mesmo elemento sao agregados.

### 6. [Modo interno] Reproduzir em producao

So depois que o lancamento saiu **certo em staging** e o EV confirmou na UI de
staging (`https://app.staging.aegro.io`):

```bash
# A fazenda vai no PROPRIO comando (--farm), nao num 'farms select' anterior:
# assim o alvo nao depende de estado global que outra sessao pode ter trocado.
# MESMO comando validado, SEMPRE com --dry-run primeiro:
aegro received-fiscal-documents launch-bill <NUMERO> --category "..." --expense \
  --dry-run --env prod --farm "<Fazenda do Cliente>"
# EV confere o plano (incluindo o campo farmSource) e SO ENTAO:
aegro received-fiscal-documents launch-bill <NUMERO> --category "..." --expense \
  --execute --env prod --farm "<Fazenda do Cliente>"
```

- **Use o NUMERO da nota** (nao a key/ids): chaves e ids diferem entre ambientes;
  o numero (e nomes de categoria/safra/fornecedor) re-resolve no ambiente certo.
- **Dry-run em prod e inegociavel**, mesmo com comando identico ao de staging —
  cadastros divergem (categoria pode nao existir, fornecedor pode ja existir).
- O guard de duplicidade continua ativo; em prod, duplicata e dado real de
  cliente — **investigue antes de qualquer `--force`**.

## Escopo por release (v1)

- **Triagem: 100%** — toda nota recebe `sugestaoDestino`.
- **Execucao: parcial** — `launch-bill`/`launch-purchase-order` funcionam;
  **remessa e arquivar sao classificacao + instrucao de UI na v1** (execucao na
  v1.1); a skill mostra a `instrucaoUI` e nao tenta executar.
- **NFS-e Nacional** funciona; **NFS-e municipal -> "revisar" na UI**. CT-e e
  devolucoes (CFOP de retorno/devolucao) ficam **fora**: nao lance pelo CLI.

## Casos que acionam a pessoa (v1)

| Caso | Sinais | Acao |
|---|---|---|
| Contra-nota / retorno | espelha uma emissao existente | localizar a emissao e **arquivar** (instrucao de UI) |
| Transporte em suspensao | natureza de transporte, ICMS suspenso | **acionar a pessoa** |
| Remessa sem processo | remessa sem venda/compra fechada | vincular a pedido/contrato ou **acionar a pessoa** |
| NFS-e municipal / CT-e / devolucao | fora do recorte v1 | **revisar na UI** |

## Comportamentos conhecidos

| Comportamento | O que fazer |
|---|---|
| **"500 cosmetico"**: o servidor as vezes responde 5xx **depois** de criar a conta. O `launch-bill` detecta e retorna a conta persistida com aviso. | Se vir "a conta FOI criada", esta certo — **nao relance**. |
| Guard de duplicidade acusa por numero da nota **na fazenda inteira** (nao so por fornecedor); mostra a(s) conta(s) suspeita(s). | Confira as contas listadas; so `--force` apos confirmar que nao e duplicata real. |
| Categoria financeira e **obrigatoria** e o CLI ainda nao sugere sozinho (a UI sugere). | Pergunte/descubra com `fin-categories list -s`. Exige folha ANALYTIC. |
| Conciliacao parcial -> conta **sem baixa de estoque** (tudo-ou-nada). | Concilie **todos** os itens para ter estoque. |
| Fornecedor recem-criado demora a "aparecer" (consistencia eventual); o CLI contorna buscando por CNPJ. | Se falhar mesmo assim, aguarde ~10s e repita. |
| Busca por chave de acesso (44 digitos) so olha os 50 documentos mais recentes. | Prefira o **numero** da nota (busca no servidor). |
| Nota de ENTRADA/RETORNO exige `--revenue`/`--expense` explicito (nao infere). | Siga a secao 3: default e arquivar ou lancar sem pagamento. |

## Diario de sessao (modo interno / EV)

No modo interno, registre em `$AEGRO_LEARNING_DIR/journal-<data>-<ev>.md` (ou
`./journal-piloto-notas.md` se a var nao existir) — comando, resultado, erro,
atrito e o que fluiu bem. Verifique no inicio da sessao se
`AEGRO_LEARNING_DIR`/`AEGRO_TELEMETRY_DIR` estao definidos; se faltarem, avise
que a sessao esta "cega" para a medicao e **ofereca configurar na hora**. Ao fim,
ofereca compilar o diario para o time de dev via `/aegro-feedback-dev`.

No modo externo o diario nao e exigido; se o cliente quiser reportar um problema,
ofereca registrar num arquivo local e orientar o envio pelo canal de suporte.

## Setup da fazenda e playbook de regras

O **playbook** e um arquivo Markdown **por fazenda** com as regras confirmadas
(conta por modo de pagamento, categoria default por fornecedor/CFOP/NCM, rateio
por safra, semantica de data, moeda default, quando a nota vira pedido...). Ele
vive na **skill**, nao no CLI: a skill le o playbook e traduz as regras em
flags/valores explicitos nos comandos, e declara na conversa **quais regras
aplicou** (auditavel). O CLI permanece deterministico.

- **Formato:** um `playbooks/<fazenda-slug>.md` por fazenda (frontmatter com
  fazenda/env/data + regras em secoes). Um arquivo por fazenda para carregar so o
  contexto relevante e nunca vazar regra de um cliente em outro.
- **Onde salvar:** default `$AEGRO_LEARNING_DIR/playbooks/` quando a var existe.
  Quando nao existe (cliente, ou EV sem a var), **o usuario nao precisa saber de
  variavel de ambiente**: no setup a skill pergunta onde salvar em linguagem
  simples ("vou guardar as regras desta fazenda junto dos seus arquivos — ok?") e,
  nas sessoes seguintes, se nao encontrar, pergunta onde esta e registra a
  resposta. **Nunca falhe em silencio** por diretorio ausente.
- Sessoes seguintes comecam com "playbook carregado: N regras".

**Setup (primeira conversa) — modelo "confirmar > perguntar":**

0. **Documento existente primeiro:** pergunte se ja existe um documento com as
   definicoes da fazenda (planilha de regras, doc de onboarding, anotacoes) e
   **ingira** — um documento vale mais que dez confirmacoes; o que ele responde
   nao e perguntado.
1. **Observar antes de perguntar:** leia os cadastros e os ultimos 60-90 dias de
   contas/notas e **proponha** regras ("as notas da Corteva viram sempre
   'Defensivos' pagas da conta corrente — confirmo como regra?"), em vez de um
   formulario em branco. Inclui **detectar o perfil da fazenda**: usa pedido de
   compra? remessa? rateio? SEFAZ ou so XML? — o perfil decide quais fluxos a
   triagem sequer oferece.
2. **Teto de cerimonia:** setup em <= 10 min e ~6 confirmacoes; o que nao deu para
   confirmar vira **regra pendente**, proposta quando o caso aparecer na triagem
   ("primeira nota da Bayer — uso Defensivos?"). O playbook cresce em uso.
3. **Sem jargao:** a localizacao do arquivo e oferecida como default em linguagem
   de usuario; escolha explicita so se a pessoa se importar.

> O de/para item<->catalogo **nao** vai ao playbook: a conciliacao ja persiste
> server-side por fornecedor+item e e reaproveitada.

## Proximos workflows

| Situacao | Proximo workflow |
|---|---|
| Preencher a conta a pagar/receber | `/aegro-lancamento-financeiro` |
| Regras de bills/categorias/parcelas | `/aegro-financeiro` |
| Cadastrar fornecedores em lote | `/aegro-importacao-fornecedores` |
| Conferir impacto no caixa | `/aegro-visao-geral` |
| Compilar erros da sessao para o dev (interno) | `/aegro-feedback-dev` |
