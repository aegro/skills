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
| Lancar conta | `launch-bill <doc> --category X --bank-account C [--revenue\|--expense] [...] --dry-run/--execute` | Cria a conta **com vinculo NF-e<->bill**. `--revenue`/`--expense` **obrigatorio em nota de entrada**; `--bank-account` **obrigatoria** sempre que o lancamento gerar parcela (so `--no-payment` dispensa). |
| Lancar pedido | `launch-purchase-order <doc> --dry-run/--execute` | Idem como pedido de compra, com guard de pedido duplicado. |

> `preparar` foi **descontinuado** (ensinava o caminho publico sem vinculo
> NF-e<->bill, ENTRADA-84). Se aparecer, o stub aponta para `launch-bill --dry-run`.

Opcoes do `launch-bill` que replicam a UI web:
- `--category` (obrigatoria na pratica — aceita nome, id ou key; exige folha `ANALYTIC`)
- `--bank-account` (**obrigatoria** quando o lancamento gera parcela — aceita nome,
  id interno ou `bankAccount::<id>`). Sem ela o comando **recusa antes de qualquer
  escrita** (exit 4). Nao existe conta padrao, e a fazenda tem varias: escolher uma
  em silencio seria decidir por onde o dinheiro anda. Descubra com
  `aegro bank-accounts list`.
- Modo de pagamento (os mesmos rotulos da UI): `--no-payment` (Sem pagamento),
  `--prompt` (A Vista: 1 parcela **JA PAGA** - baixa automatica na criacao),
  `--installments N` (A Prazo: parcelas em aberto - N=1 vence na data da nota,
  N>1 sao mensais); sem nenhum, usa as duplicatas da propria nota (nota sem
  duplicatas: o efeito e 1 parcela em aberto na data da nota). Antes de
  escolher, leia a traducao logo abaixo: "a vista" dito pelo usuario **nao**
  vira `--prompt` automaticamente.
- `--currency USD --exchange-rate 5.42` (moeda estrangeira; parcelas acompanham)
- `--create-company` (cria o fornecedor com os dados da nota) e
  `--company <nome|id|key>` (desambigua emitente com CNPJ duplicado)
- **Estoque — duas flags, dois estoques diferentes** (ver secao 5b):
  `--stock-location <key>` movimenta o estoque de **INSUMO** e so vale em
  **despesa**; `--stock-harvest <asset::silo>` (+ `--stock-harvest-crop "Safra X"`)
  movimenta o estoque de **PRODUCAO** — e o que da **baixa** numa venda de graos.
- `--apportion-crop "Safra X"` (rateio), `--asset <id>`, `--tag`,
  `--description`, `--producer`, `--force`.

### Pagamento: "a vista" (fala do usuario) != "A Vista" (rotulo da UI)

No Aegro, o rotulo **"A Vista" gera 1 parcela JA PAGA** (baixa automatica na
criacao, irreversivel via API - correcao so pelo app). Quando o usuario diz
que a nota "e a vista" - ou a nota vem sem duplicatas - ele normalmente
descreve a **condicao de pagamento** (vencimento na data da nota), nao uma
ordem para dar baixa.
Traducao correta (padrao do time de Servicos, reuniao CLI <> Servicos
31/07/2026 - ENTRADA-135):

| O que foi dito / esta na nota | Flag | Efeito |
|---|---|---|
| "a vista" (condicao; baixa NAO confirmada) | `--installments 1` | 1 parcela **em aberto** com vencimento na data da nota; o produtor confirma o pagamento depois |
| "a vista", pagamento JA feito **e** baixa automatica desejada | `--prompt` | 1 parcela ja paga na data da nota |
| Pagamento ja feito, mas o produtor prefere conferir antes de baixar | `--installments 1` | 1 parcela em aberto na data; apos a conferencia, `aegro financial realize` |
| "a prazo" / nota com duplicatas | sem flag | parcelas das duplicatas (o cronograma real da nota) |
| Sem duplicatas e parcelamento combinado | `--installments N` | N parcelas mensais em aberto |
| Remessa / registro sem efeito de caixa | `--no-payment` | sem parcelas (ver secao 3) |

Qualquer linha desta tabela que gere parcela (`--installments`, `--prompt` ou as
duplicatas da nota) exige `--bank-account` — inclusive a traducao default de "a
vista". So `--no-payment` dispensa a conta. Ver a secao de opcoes do
`launch-bill`.

Se a fala e o documento conflitam (usuario diz "a vista"/"ja paguei" mas a
nota TEM duplicatas), as duplicatas sao o cronograma real: aponte a
divergencia e so sobrescreva com `--installments`/`--prompt` se o usuario
confirmar. Nota a prazo ja quitada: lance pelas duplicatas (nascem em aberto)
e registre os pagamentos com `financial realize` em seguida.

**Nunca traduza "a vista" direto para `--prompt`** sem confirmar que o
pagamento ja ocorreu **e** que a baixa automatica e desejada. O proprio time de
Servicos lanca nota com data a vista como "A Prazo" de 1 parcela na mesma data,
justamente para o sistema nao marcar "pago" sozinho e o produtor poder revisar
lancamentos retroativos.

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
Natureza da operacao: RETORNO DE COMODATO
Itens: COLHEITADEIRA CR6.80 (1 un) - PLATAFORMA DE SOJA (1 un)
Conferencia externa: https://www.nfe.fazenda.gov.br/portal/consultaRecaptcha.aspx
  (colar a chave de acesso: 3526...  - 44 digitos)
```

Sempre inclua: numero, datas, valor, emitente **mascarado** + "fornecedor
resolvido: sim/nao", CFOPs com descricao, **natureza da operacao**, itens e o
link de consulta publica da SEFAZ com a chave, para conferir fora do Aegro. Para ver o documento fiscal:
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

**Nota recebida com CFOP 59xx/69xx de remessa ou retorno: NAO e compra — nao
monte conta a pagar.** Foram ~R$ 827 mil em passivo falso quase lancados numa
sessao (uma remessa para demonstracao 5912 e um retorno de deposito 5906),
evitados so pela leitura manual da natureza.

Desde o CLI **v0.17.0** esse guard existe **tambem no `launch-bill`**: nota de
nao-compra lancada como **despesa** para o comando, e so segue com
`--allow-non-purchase` (a decisao aparece no preview do dry-run). Em
**receita** o guard nao dispara — ele protege contra conta a **pagar** falsa, e
receita e classificacao explicita de quem opera (uma venda de producao com CFOP
1905 e legitima; ver secao 5b).

Isso **nao dispensa a leitura**: o guard olha so o CFOP, e a natureza da
operacao ("RETORNO DE COMODATO") costuma decidir antes. Leia `cfopCode` +
`natureOfOperation` no `items` ANTES de oferecer qualquer lancamento — e trate
o bloqueio do CLI como segunda rede, nao como a primeira.

- **Nao-compra (default: arquivar ou acionar a pessoa):** 5905/5906/5907
  (deposito/armazem e retornos), 5912/5913 (demonstracao), 5901/5902
  (industrializacao), 5915/5916 (conserto) — e os equivalentes interestaduais
  69xx. Em 5949/6949 ("outra saida"), decida pela natureza da operacao.
- **Nao confunda com os 59xx lancaveis:** 5929 (cupom->nota de abastecimento)
  e 5922/5923 (faturamento/entrega futura) tem fluxo normal de lancamento.
- **Devolucao** (grupos x2xx/x41x) segue **fora do recorte v1**: revisar na UI.
- So siga para `launch-bill` se o usuario confirmar explicitamente o efeito
  financeiro real, e registre essa confirmacao na conversa.

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
# --env explicito nas DUAS fases: staging no modo interno, prod no externo.
# Sem ele o comando usa o default e um lancamento interno pode ir para producao.

# 1o: preview (nenhuma escrita acontece; o plano completo e exibido)
aegro received-fiscal-documents launch-bill --farm "<fazenda>" --env <staging|prod> <NUMERO> \
  --category "Categoria" --bank-account "<conta bancaria>" --expense --dry-run

# 2o: so depois que o usuario conferir o plano (fornecedor, categoria, parcelas, valor):
aegro received-fiscal-documents launch-bill --farm "<fazenda>" --env <staging|prod> <NUMERO> \
  --category "Categoria" --bank-account "<conta bancaria>" --expense --execute
```

Descubra o nome exato da categoria com `aegro fin-categories list -s "<trecho>"`
("Combustivel" nao casa "Combustiveis e Lubrificantes"); a conta exige categoria
**ANALYTIC** (folha) — sinteticas nao servem.

**Conferencia do dry-run — 3 checagens obrigatorias antes do `--execute`:**

1. **Nomes resolvidos no cadastro.** O dry-run **serializa localmente e NAO
   valida no servidor**: categoria/tag/conta com typo passam batidas e so
   estouram (ou entram erradas) no `--execute`. Resolva cada nome antes, via
   listagem (`fin-categories list -s`, `elements list -s`, cadastros de
   `/aegro-financeiro`) — nunca confie no dry-run para pegar nome errado.
2. **Total da conta vs total da nota.** O `launch-bill` monta a conta pelo
   `value` (soma dos produtos); quando o `totalValue` da nota e maior
   (frete/impostos/acrescimos), a conta nasce **subvalorizada**. Compare os
   dois no `items`; divergiu -> na v0.17.0+ o comando **para** e exige o valor
   explicito: confirme com o operador qual vale e repita o `--dry-run`/
   `--execute` com `--total <valor>`.
3. **Quantidades do estoque plausiveis.** Confira `inputs[].amount` do dry-run
   contra a quantidade da nota: distorcao tipo x1000 indica `conversionRate`
   errado persistido na conciliacao (ex. fator 1000 com nota e elemento na
   MESMA unidade, que deveria ser 1). Nesse caso, lance **sem**
   `--stock-location` **nem** `--stock-harvest` (a mesma distorcao infla os
   dois estoques; com a flag o cost-apportion tende a dar 422) — corrija com
   `conciliate --unit`/`--conversion-rate`, rode um novo dry-run e so ai
   execute, e reporte via `/aegro-feedback-dev`.

Como **pedido de compra**: `launch-purchase-order <doc> --order-code <n> --dry-run`
(depois `--execute`). Requer itens conciliados (itens sem conciliacao ficam fora
do pedido — o comando avisa); itens conciliados ao mesmo elemento sao agregados.

### 5b. Nota que MOVIMENTA ESTOQUE — escolha o estoque certo

> Requer CLI **v0.18.0+** (`--stock-harvest`). Confira com `aegro --version`;
> em versao anterior a flag nao existe e **nao ha caminho de baixa de producao
> pelo CLI** — o fluxo e a UI web (Estq. Producao -> VENDER).

O Aegro tem **dois estoques** e cada um tem a sua flag. Errar a flag foi o
atrito de campo que gerou o ENTRADA-170: numa venda de graos, `--stock-location`
nao da baixa nenhuma da producao.

| Quero... | Flag | Vale em |
|---|---|---|
| Entrada de **insumo** comprado (adubo, defensivo, semente) | `--stock-location <stockLocation::key>` | so **despesa** — em receita o comando para com exit 4 |
| **Baixa** de **producao** vendida (graos saindo do silo) | `--stock-harvest <asset::silo>` + `--stock-harvest-crop "Safra X"` | **receita** = saida; despesa = entrada (compra de graos) |

**A direcao vem da conta, nao da flag**: com `--stock-harvest`, receita **baixa**
o silo e despesa **credita**. Nao existe flag de sentido — classifique a conta
certo e o estoque segue. E o mesmo grupo que a UI monta no switch "RETIRAR E
MOVIMENTAR ITENS -> Estoque de producao".

```bash
# Venda de arroz com baixa do silo (o caso do feedback):
aegro received-fiscal-documents launch-bill <NUMERO> --revenue \
  --category "Venda Agricola" --bank-account "<conta bancaria>" \
  --stock-harvest asset::<id-do-silo> --stock-harvest-crop "Safra Arroz 25/26" \
  --farm "<Fazenda>" --env prod --dry-run
```

Tres coisas que fazem o comando parar antes de escrever — e o conserto:

- **O silo e um `asset` do tipo GARNER**, id de 24 hex. Pegue em
  `aegro assets list --farm "<Fazenda>" --env <staging|prod> --type GARNER`
  (sem `--farm`/`--env` o id pode vir da fazenda/ambiente errado); nome nao
  resolve aqui, e asset que nao seja silo o comando recusa dizendo que nao
  existe nesta fazenda.
- **Todos os itens conciliados**, e o grao (item de categoria SEED) numa unidade
  **compativel com kg** (`kg`, `t`, `sc60`...). `un`/`L` nao convertem — o
  lancamento para e manda reconciliar com `conciliate --unit` /
  `--conversion-rate`. O grupo aceita so semente + servico: adubo/defensivo no
  meio da nota faz o comando reclamar do item, com o codigo dele.
- **A safra e obrigatoria na pratica** (`--stock-harvest-crop`): sem ela a baixa
  nasce sem origem de producao. Nome de safra resolve normalmente.

Depois do `--execute`, o comando **confere a movimentacao no servidor** — existe?
no silo certo? no sentido certo? na quantidade e unidade certas? na safra certa
(o rateio com `--stock-harvest-crop` e conferido junto)? — e responde
"saida de N conferida". Se nao conseguir conferir, o envelope sai `partial` com
`stockUnverified`: **isso nao quer dizer que falhou**, quer dizer que ninguem
confirmou. Confira na UI (Estq. Producao -> Movimentacoes) antes de cogitar
relancar; relancar duplica a baixa.

### 6. [Modo interno] Reproduzir em producao

So depois que o lancamento saiu **certo em staging** e o EV confirmou na UI de
staging (`https://app.staging.aegro.io`):

```bash
# A fazenda vai no PROPRIO comando (--farm), nao num 'farms select' anterior:
# assim o alvo nao depende de estado global que outra sessao pode ter trocado.
# MESMO comando validado, SEMPRE com --dry-run primeiro:
aegro received-fiscal-documents launch-bill <NUMERO> --category "..." --expense \
  --bank-account "<conta bancaria>" --dry-run --env prod --farm "<Fazenda do Cliente>"
# EV confere o plano (incluindo o campo farmSource) e SO ENTAO:
aegro received-fiscal-documents launch-bill <NUMERO> --category "..." --expense \
  --bank-account "<conta bancaria>" --execute --env prod --farm "<Fazenda do Cliente>"
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
| **"500 cosmetico"**: o servidor as vezes responde 5xx **depois** de criar a conta. O `launch-bill` detecta, mas **a conta existir nao prova que o lancamento inteiro persistiu** — a conta e gravada ANTES das parcelas e fora de transacao. | "A conta FOI criada" **nao e mais sinal de sucesso sozinho**: leia o que vem depois. Se disser lancamento **PARCIAL** (exit 1), a conta ficou sem as parcelas — **corrija pela UI e NAO relance**, relancar duplica. |
| **Lancamento PARCIAL**: o comando confere a contagem de parcelas gravadas contra a enviada e sai com exit 1 quando nao bate. | Nunca trate exit 1 como "tentar de novo": a conta ja existe. Abra a conta na UI e complete as parcelas. |
| Guard de duplicidade acusa por numero da nota **na fazenda inteira** (nao so por fornecedor); mostra a(s) conta(s) suspeita(s). | Confira as contas listadas; so `--force` apos confirmar que nao e duplicata real. |
| Categoria financeira e **obrigatoria** e o CLI ainda nao sugere sozinho (a UI sugere). | Pergunte/descubra com `fin-categories list -s`. Exige folha ANALYTIC. |
| Conciliacao parcial -> conta **sem baixa de estoque** (tudo-ou-nada). | Concilie **todos** os itens para ter estoque. |
| Fornecedor recem-criado demora a "aparecer" (consistencia eventual); o CLI contorna buscando por CNPJ. | Se falhar mesmo assim, aguarde ~10s e repita. |
| Busca por chave de acesso (44 digitos) so olha os 50 documentos mais recentes. | Prefira o **numero** da nota (busca no servidor). |
| Nota de ENTRADA/RETORNO exige `--revenue`/`--expense` explicito (nao infere). | Siga a secao 3: default e arquivar ou lancar sem pagamento. |
| Desde a **v0.17.0** o `launch-bill` **bloqueia** NF de nao-compra (59xx/69xx) lancada como **despesa**; em receita nao dispara. | Libere com `--allow-non-purchase` so apos conferir. O guard le so o CFOP — a natureza da operacao continua sendo leitura sua (secao 3). |
| Total divergente (`value` dos produtos x `totalValue` da nota com frete/impostos) **para** o lancamento na v0.17.0+. | Confira os dois no `items` e escolha explicitamente com `--total <valor>`. |
| `--stock-location` **nunca** da baixa de producao — e o estoque de **insumo**, e em nota de receita o comando para (exit 4). | Venda de graos usa `--stock-harvest <asset::silo>` (secao 5b), CLI v0.18.0+. |
| Apos `--execute` com estoque, o envelope pode sair `partial` com `stockUnverified`. | **Nao relance** — a conta foi criada; faltou a *conferencia*. Confira na UI (Estq. Producao -> Movimentacoes). |
| Conciliacao pode ter `conversionRate` errado persistido (ex. 1000 com nota e elemento na mesma unidade) — estoque sairia x1000; `--stock-location` -> 422 de cost-apportion. | Checagem 3 da conferencia do dry-run (secao 5): confira `inputs[].amount` vs quantidade da nota; distorcido -> lance sem `--stock-location` e reporte. |
| Unidade da nota nao reconhecida (ex. SC) gravava `measuringUnit: "ENUM_NOT_FOUND"` em silencio. Na **v0.17.0+** o `conciliate` grava a unidade do **elemento** e o `launch-bill` recusa mapeamento com defeito. | Siga o conserto que o proprio comando indica: `conciliate <doc> --unit CODIGO=un` e/ou `--conversion-rate CODIGO=fator`. O de/para e reusado por (fazenda, fornecedor, item) — fator errado contamina a proxima nota. |
| Dry-run serializa localmente e **nao valida nomes no servidor** (categoria/tag/conta com typo passam). | Checagem 1 da conferencia do dry-run (secao 5): resolva cada nome via listagem antes do execute. |
| `items <numero>` ambiguo pede a key completa mas nao lista os candidatos. | Rode `list` com `--texto <numero>` (ou a janela de datas) para ver os candidatos e escolher a key. |

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

## Entregue o link da conta lancada

Depois do `launch-bill --execute`, ofereca o link que abre a conta gerada
pela nota — e o caminho mais rapido para a pessoa conferir rateio, itens e
categoria sem procurar o lancamento na lista:

```
{host}/farm/{farmId}?billId={billId}#farm-finance
```

**Atencao ao dialeto:** `launch-bill` passa pela API interna e devolve `id`
e `farmId` (ja sem o prefixo `tipo::`), nao `key`/`farmKey`. Use esses
campos direto.

Nao existe link direto para a **nota** (documento recebido) — so para a
conta. Se a pessoa quiser ver a nota, o maximo e a secao:
`{host}/farms/{farmId}/fiscal/received-fiscal-document`. Diga que e a lista,
nao a nota.

Regras que nao podem ser puladas (detalhe em `/aegro-operacional`, secao
"Link Direto para a Entidade"): host vem do `--env` da sessao
(`https://app.aegro.com.br` em prod, `https://app.staging.aegro.io` em
staging), a URL usa a chave **sem** o prefixo `tipo::`, e link com aba
invalida **nao da erro** — cai na home da fazenda em silencio. Nunca invente
template por analogia.

## Proximos workflows

| Situacao | Proximo workflow |
|---|---|
| Preencher a conta a pagar/receber | `/aegro-lancamento-financeiro` |
| Regras de bills/categorias/parcelas | `/aegro-financeiro` |
| Cadastrar fornecedores em lote | `/aegro-importacao-fornecedores` |
| Conferir impacto no caixa | `/aegro-visao-geral` |
| Compilar erros da sessao para o dev (interno) | `/aegro-feedback-dev` |
