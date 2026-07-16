---
name: aegro-integracao
description: Criar e gerenciar chaves de API (integration agents) por fazenda na CLI Aegro, concedendo o escopo mínimo para a tarefa
version: 0.5.1
---

# Aegro Integração — Chaves de API por Fazenda

## Objetivo

Guiar a criação de uma chave de API (integration agent) para uma fazenda,
após login OAuth, concedendo **o escopo mínimo** necessário para o que o
usuário quer fazer, e salvando a chave na memória da CLI.

## Quando Usar

- "criar uma chave de API", "gerar token de integração", "conectar sistema X"
- Antes de usar comandos `/pub/v1` que precisam de api-key própria.

## Pré-requisitos

1. **OAuth**: rode `aegro auth status`. Se não autenticado, `aegro auth login`.
2. **Fazenda**: `aegro farms list`; selecione com `aegro farms select "<nome>"`.

## Fluxo

1. **Pergunte o que a chave vai fazer** (só leitura de safras? lançar estoque?
   integração completa?). Traduza a intenção em módulos.
2. **Escopo mínimo** — prefira `READ_*`; só use `WRITE_*` se houver escrita; só
   use `ALL` se o usuário pedir integração total. Use a tabela abaixo.
3. Descubra os escopos válidos no ambiente: `aegro integration-agents authorizations`.
4. Crie: `aegro integration-agents create -n "<rótulo>" -a <AUTH> [-a <AUTH> ...]`
   (ou `--scope read|write|all`). **`--expires YYYY-MM-DD` é obrigatória** e
   deve ser < 1 ano; se omitida a CLI usa 7 dias por padrão (e pergunta em modo
   interativo). Prefira janelas curtas.
5. **Confirme** "chave criada e salva na memória" **sem** exibir o segredo.
   NÃO use `--show` nem repita o valor da chave na conversa.
6. Para auditar/revogar: `aegro integration-agents list` / `... revoke <key> --yes`.

## Tabela tarefa → authorization (escopo mínimo)

| Tarefa envolve            | Leitura              | Escrita               |
|---------------------------|----------------------|-----------------------|
| Safras/culturas           | READ_CROPS           | WRITE_CROPS           |
| Talhões                   | READ_GLEBES          | WRITE_GLEBES          |
| Estoque (movimentações)   | READ_STOCK_LOGS      | WRITE_STOCK_LOGS      |
| Itens/locais de estoque   | READ_STOCK_ITEMS / READ_STOCK_LOCATIONS | (somente leitura) |
| Elementos/insumos         | READ_ELEMENTS        | WRITE_ELEMENTS        |
| Financeiro (contas)       | READ_BILLS / READ_INSTALLMENTS | WRITE_BILLS / WRITE_INSTALLMENTS |
| Categorias financeiras    | READ_FINANCIAL_CATEGORIES | WRITE_FINANCIAL_CATEGORIES |
| Contas/transf. bancárias  | READ_BANK_ACCOUNTS / READ_BANK_TRANSFERS | WRITE_BANK_ACCOUNTS / WRITE_BANK_TRANSFERS |
| Atividades                | READ_ACTIVITIES      | WRITE_ACTIVITIES / REALIZE_ACTIVITIES |
| NF-e / produtos fiscais   | READ_NFES / READ_FISCAL_PRODUCTS | WRITE_NFES / WRITE_FISCAL_PRODUCTS |
| Patrimônio                | READ_ASSETS          | WRITE_ASSETS          |
| Tags                      | READ_TAGS            | WRITE_TAGS            |
| Integração total          | —                    | ALL                   |

> A lista viva e completa vem de `aegro integration-agents authorizations`.

## Segurança

- O comando **não** imprime o segredo por padrão; já fica salvo em
  `~/.config/aegro/credentials.json`. Nunca peça `--show` só para exibir, e
  nunca cole o valor da chave na conversa.
