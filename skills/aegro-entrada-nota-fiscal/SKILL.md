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
| Lancar | `aegro received-fiscal-documents lancar <accessKey> --desde ... --ate ... --category "<nome>"|--financial-category-key <key> --bank-account-key <key> [--dry-run|--execute]` | Monta o lancamento a partir dos itens conciliados e cria via **API publica** (`POST /pub/v1/bills`). Delega valores/forma ao lancamento financeiro. |

> O `detalhe`/`lancar` resolvem a `accessKey` -> URL do XML via `listar` na janela `--desde/--ate`
> (passe `--xml-url` para pular a busca). Toda mutacao exige `--execute` (use `--dry-run` para prever).

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
5. LANCAR: lancar --dry-run (revisar) -> --execute  (delega ao /aegro-lancamento-financeiro)
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
a nota **ja tem lancamento** — conciliar/arquivar, **nao duplicar**. O `lancar` tambem avisa.

### 4. Conciliar entidades — **por padrao, sempre**

Conciliar preserva o **detalhamento por item** (elemento do catalogo, custo, estoque). Este e o
comportamento padrao do processo — **conduza a conciliacao** salvo se o usuario for **explicito**
em nao querer:

- **Produtos**: para cada item, use a **sugestao** do `detalhe` (quando houver) ou pergunte o
  elemento do catalogo; rode `conciliar --item <invoiceItemId>=<elementId> ... --execute`. O
  mapeamento fica salvo e e reaproveitado nas proximas notas do mesmo fornecedor.
- **Fornecedor / produtor**: vem conciliados por CNPJ->empresa no `detalhe`; se faltar, cadastre/
  associe a empresa (`/aegro-financeiro`).

> **So pule a conciliacao com opt-out explicito do usuario.** Sem conciliar, o `lancar` **nao**
> lanca silenciosamente: ele pede a conciliacao (recomendado) OU exige a flag **`--sem-itens`**
> (lanca apenas o total, perdendo o detalhamento por item). Deixe claro ao usuario o que se perde.

### 5. Pagamento: lancar ou conciliar
"Pagamento" nem sempre e uma despesa nova — pode ser a conciliacao de uma despesa **ja cadastrada**.
Se ja existe conta similar (mesmo fornecedor/valor/periodo/nº nota), concilie; senao, lance.

### 6. Lancar (delega ao financeiro)
`lancar --dry-run` para revisar o payload; depois `--execute`. Categoria e conta vem por
`--category`/`--bank-account` (ou chave); o que faltar volta como envelope `needs_input`. Sempre:
- **`receipt`** = numero da nota (automatico a partir do detalhe).
- **`nfeAccessKey`** = chave de acesso (automatico).
- **Itens** conciliados viram `inputs`; servico sem catalogo -> conciliar a um item generico.

## Casos que acionam a pessoa (v1)

| Caso | Sinais | Acao |
|---|---|---|
| Contra-nota / retorno | espelha uma emissao existente | localizar a emissao e **arquivar** |
| Transporte em suspensao | natureza de transporte, ICMS suspenso | **acionar a pessoa** |
| Remessa sem processo | remessa sem venda/compra fechada | vincular a pedido/contrato ou **acionar a pessoa** |

## Limitacoes / Dependencias

- **Auth**: comandos usam APIs internas -> exigem OAuth first-party (`aegro auth login`).
- **Lancamento parcelado (bug aberto — [FNC-112]):** `POST /pub/v1/bills` com pagamento **a prazo**
  retorna 500 e persiste a conta **sem as parcelas** (e sem backlink NFe<->bill — [ENTRADA-84]).
  Ate o fix: prefira **`--dry-run`** para validar, e trate lancamento parcelado com cautela
  (a vista/`PROMPT` funciona). Nunca relancar em cima de um 500 (duplica).
- **Vinculo NFe<->bill ([ENTRADA-84]):** o lancamento pela API publica ainda **nao marca** a NFe
  como lancada (segue `NONE`). Confirme manualmente para evitar duplicidade.
- **Sub-skills de conciliacao** dedicadas: ainda inline (via `conciliar` + `/aegro-financeiro`).
- **Casos fiscais** (contra-nota, transporte, remessa) acionam a pessoa no v1.

## Proximos Workflows

| Situacao | Proximo workflow |
|---|---|
| Preencher a conta a pagar/receber | `/aegro-lancamento-financeiro` |
| Regras de bills/categorias/parcelas | `/aegro-financeiro` |
| Cadastrar fornecedores em lote | `/aegro-importacao-fornecedores` |
| Conferir impacto no caixa | `/aegro-visao-geral` |
