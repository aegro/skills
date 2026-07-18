---
name: aegro-entrada-nota-fiscal
description: Orquestra a entrada de uma NFe recebida no Aegro pela CLI — lista, abre o detalhe, concilia fornecedor/produtor/produtos (por padrao), verifica duplicidade e delega o lancamento financeiro
version: 0.2.0
---

# Entrada de Nota Fiscal no Aegro

## Objetivo

Decidir **o que fazer com uma NFe recebida** e leva-la ao financeiro. Esta skill e
a camada de **processo**, acima do lancamento: lista as notas, entende o que a
nota e (despesa, receita, remessa, retorno, transporte), **concilia as entidades**,
evita duplicidade e delega o lancamento em si.

O **preenchimento do formulario** (categoria, parcelas, rateio) e responsabilidade
da skill de lancamento (`/aegro-lancamento-financeiro`) — aqui cuidamos da
**decisao e da conciliacao**, nao da sintaxe do bill.

## Quando Usar

- Dar entrada no financeiro de uma **NFe recebida** (de fornecedor) ja disponivel no Aegro (SEFAZ).
- Decidir se a nota vira despesa, receita ou outro fluxo.
- Conciliar fornecedor/produtor e os **produtos** da nota (produto-da-nota -> elemento do catalogo).
- Garantir que a nota ainda nao foi lancada.

Para lancar **uma conta manual** sem nota fiscal, va direto para `/aegro-lancamento-financeiro`.

## Pre-requisitos

- **Login OAuth**: os comandos usam **APIs internas** do Aegro — exige `aegro auth login`
  (nao funciona com API key). Selecione a fazenda (`aegro farms select`) e o ambiente (`--env`).
- `/aegro-financeiro` — bills, categorias, parcelas, empresas, contas bancarias.
- `/aegro-lancamento-financeiro` — sequencia de decisao de a pagar/receber.
- `/aegro-operacional` — fazenda ativa, autenticacao.

## Comandos (grupo `received-fiscal-documents`)

O fluxo e dirigido por 4 comandos da CLI `aegro` (todos aceitam `--env prod|staging`):

| Passo | Comando | O que faz |
|---|---|---|
| Listar | `aegro received-fiscal-documents listar --desde <YYYY-MM-DD> --ate <YYYY-MM-DD> [--tipo NFE] [--status-financeiro NONE] [--texto ...]` | Lista as NFe recebidas (cabecalho): fornecedor, numero, CFOP, valor e **status financeiro** (`NONE`/`SINGLE`/`MULTIPLE`). |
| Detalhe | `aegro received-fiscal-documents detalhe <accessKey> --desde ... --ate ...` | Traz itens (codigo, descricao, NCM, **CFOP por item**, qtd, valor), totais/descontos, pagamento+parcelas, fornecedor/produtor conciliados e **sugestoes de elemento** por item. |
| Conciliar | `aegro received-fiscal-documents conciliar <accessKey> --desde ... --ate ... --item <invoiceItemId>=<elementId> ... --execute` | Persiste o mapa **produto-da-nota -> elemento** (por fazenda+fornecedor+item), reutilizado nas proximas notas. |
| Preparar | `aegro received-fiscal-documents preparar <accessKey> --desde ... --ate ... [--cash-flow EXPENSE] [--payment-method ...] [--sem-itens]` | **Read-only.** Emite o **payload derivado da NF-e** (`nfeAccessKey`, `receipt`, `companyKey`, `cashFlow`, `paymentMethod`, `inputs`, `installments`) pronto para o `create-bill`. **NAO cria a bill.** |
| Lancar (delega) | `aegro financial create-bill --nfe-access-key <k> --receipt <n> --company-key <c> --cash-flow <cf> --payment-method <pm> --inputs '<inputs>' --installments '<installments>' --financial-category-key <cat> --bank-account-key <conta> --execute` | O **unico** comando que cria a bill (`POST /pub/v1/bills`). Recebe o payload do `preparar` + **categoria** e **conta** (que a NF-e nao tem). Ver `/aegro-lancamento-financeiro`. |

> O `detalhe`/`preparar` resolvem a `accessKey` -> URL do XML via `listar` na janela `--desde/--ate`
> (passe `--xml-url` para pular a busca). `conciliar` muta (exige `--execute`); `preparar` e read-only.

## Fluxo de Decisao

```
listar (janela recente, --status-financeiro NONE = ainda nao lancadas)
        |
1. Escolher a nota -> detalhe (papel da fazenda + CFOP + natureza)
        |
2. DUPLICIDADE: status financeiro != NONE / relatedBills -> ja lancada; NAO duplicar
        |
3. CLASSIFICAR (despesa / receita / contra-nota / transporte / remessa)
        |
4. CONCILIAR (PADRAO): fornecedor, produtor e PRODUTOS (item -> elemento)
        |
5. PREPARAR (payload da NF-e) -> financial create-bill + categoria/conta  (delega ao /aegro-lancamento-financeiro)
```

## Sequencia de Passos

### 1. Listar e escolher a nota
`listar` na janela desejada (ex.: ultimos 30 dias). Para ver so o que falta lancar, filtre
`--status-financeiro NONE`. Abra o `detalhe` da nota escolhida.

### 2. Papel da fazenda + natureza fiscal
Do `detalhe`: **a fazenda emitiu ou recebeu?** Combine com **CFOP** e **natureza da operacao** —
esse trio define a classificacao. Nao decidir despesa/receita so pelo "parece compra".

### 3. Verificar duplicidade
O proprio `listar`/`detalhe` traz `financialEntryMultiplicity` e `relatedBills`. Se **!= NONE**,
a nota **ja tem lancamento** — conciliar/arquivar, **nao duplicar**. O `preparar` tambem avisa.

### 4. Conciliar entidades — **por padrao, sempre**

Conciliar preserva o **detalhamento por item** (elemento do catalogo, custo, estoque). Este e o
comportamento padrao do processo — **conduza a conciliacao** salvo se o usuario for **explicito**
em nao querer:

- **Produtos**: para cada item, use a **sugestao** do `detalhe` (quando houver) ou pergunte o
  elemento do catalogo; rode `conciliar --item <invoiceItemId>=<elementId> ... --execute`. O
  mapeamento fica salvo e e reaproveitado nas proximas notas do mesmo fornecedor.
- **Fornecedor / produtor**: vem conciliados por CNPJ->empresa no `detalhe`; se faltar, cadastre/
  associe a empresa (`/aegro-financeiro`).

> **So pule a conciliacao com opt-out explicito do usuario.** Sem conciliar, o `preparar` **nao**
> emite silenciosamente sem os itens: ele pede a conciliacao (recomendado) OU exige a flag
> **`--sem-itens`** (prepara apenas o total, perdendo o detalhamento por item). Deixe claro o que se perde.

### 5. Pagamento: lancar ou conciliar
"Pagamento" nem sempre e uma despesa nova — pode ser a conciliacao de uma despesa **ja cadastrada**.
Se ja existe conta similar (mesmo fornecedor/valor/periodo/nº nota), concilie; senao, lance.

### 6. Preparar e delegar ao lancamento (`create-bill`)
Rode `preparar` para obter o **payload derivado da NF-e** (read-only): `nfeAccessKey`, `receipt`,
`companyKey`, `cashFlow`, `paymentMethod`, `inputs` (itens conciliados) e `installments`. O que a
NF-e **nao tem** — **categoria financeira** e **conta bancaria** — voce decide/pergunta e passa ao
`financial create-bill` (o **unico** que cria a bill). Mapeie 1:1 os campos do payload nas flags do
`create-bill` e acrescente `--financial-category-key`/`--bank-account-key` (ou `--category`/`--bank-account`).
- **Itens** conciliados viram `inputs`; servico sem catalogo -> conciliar a um item generico.
- A criacao, a forma de pagamento e o preenchimento final sao do `/aegro-lancamento-financeiro`.

## Casos que acionam a pessoa (v1)

| Caso | Sinais | Acao |
|---|---|---|
| Contra-nota / retorno | espelha uma emissao existente | localizar a emissao e **arquivar** |
| Transporte em suspensao | natureza de transporte, ICMS suspenso | **acionar a pessoa** |
| Remessa sem processo | remessa sem venda/compra fechada | vincular a pedido/contrato ou **acionar a pessoa** |

## Limitacoes / Dependencias

- **Auth**: comandos usam APIs internas -> exigem OAuth first-party (`aegro auth login`).
- **Lancamento parcelado (bug aberto — [FNC-112]):** ao criar via `create-bill` (`POST /pub/v1/bills`)
  com pagamento **a prazo**, a API retorna 500 e persiste a conta **sem as parcelas**. Ate o fix,
  trate lancamento parcelado com cautela (a vista/`PROMPT` funciona) e **nunca recrie em cima de um
  500** (duplica).
- **Vinculo NFe<->bill ([ENTRADA-84]):** criar a bill com `nfeAccessKey` **nao marca** a NFe como
  lancada (segue `NONE`). Confirme manualmente para evitar duplicidade.
- **Sub-skills de conciliacao** dedicadas: ainda inline (via `conciliar` + `/aegro-financeiro`).
- **Casos fiscais** (contra-nota, transporte, remessa) acionam a pessoa no v1.

## Proximos Workflows

| Situacao | Proximo workflow |
|---|---|
| Preencher a conta a pagar/receber | `/aegro-lancamento-financeiro` |
| Regras de bills/categorias/parcelas | `/aegro-financeiro` |
| Cadastrar fornecedores em lote | `/aegro-importacao-fornecedores` |
| Conferir impacto no caixa | `/aegro-visao-geral` |
