---
name: aegro-importacao-fornecedores
description: Importar fornecedores em lote a partir de uma planilha (Nome + CPF/CNPJ), com enriquecimento opcional de dados da Receita
version: 0.5.1
---

# Importacao de Fornecedores em Lote

## Objetivo

Subir a carteira de fornecedores de um cliente de uma vez, a partir de uma
planilha simples (nome + documento). Le a planilha, classifica o documento
(CNPJ/CPF/sem documento), opcionalmente enriquece os dados de quem so tem o
CNPJ, mostra uma previa para conferencia e cria as empresas via CLI, sem
duplicar.

## Quando Usar

- Migracao inicial: cadastrar centenas de fornecedores de uma so vez
- Cliente entrega uma planilha de fornecedores/clientes para subir no Aegro
- Onboarding premium com lista grande de empresas

Para cadastrar **um** fornecedor isolado, use `/aegro-financeiro` ou
`/aegro-operacional`.

## Pre-requisitos

Carregue antes de iniciar:

- **`/aegro-operacional`** — modelo de `companies`, autenticacao, selecao de fazenda
- **`/aegro-financeiro`** — contexto do fornecedor em contas a pagar/receber

Tambem:

- Fazenda ativa confirmada (`aegro farms list` — conferir `active` e `source`)
- Planilha com as colunas `Nome` e `CPF/CNPJ`
- Para ler a planilha, use a skill **`xlsx`**

## Modelo da Planilha

Uma aba, uma linha por fornecedor. A linha 1 e cabecalho; linhas totalmente
vazias devem ser ignoradas.

### Colunas -> flags do CLI

| Coluna planilha | Flag CLI | Observacao |
|---|---|---|
| `Nome` | `--name` | Obrigatorio. Linha sem nome = ignorar |
| `CPF/CNPJ` | `--fiscal-code` + `--fiscal-type` | 14 digitos -> `CNPJ`; 11 digitos -> `CPF`; vazio -> **nao cadastra** (ver abaixo) |

- Todos sao cadastrados com `--type PROVIDER` (fornecedor).
- **Normalize o documento para digitos** (remova `.`, `/`, `-`) antes de enviar.
- **Documento e obrigatorio:** a API rejeita empresa sem CPF/CNPJ com erro
  **422 (campos invalidos)**. Linhas sem documento **nao podem ser cadastradas** —
  pule e registre no relatorio.

## Ordem Obrigatoria de Ambientes: Staging -> Verificacao -> Prod

Importacao em prod mexe em dados **reais** do cliente e **nao tem delete em
lote** — um cadastro errado e trabalhoso de desfazer. Por isso, **nunca importe
direto em prod**. Siga sempre esta ordem:

1. **Importe primeiro em staging** (`AEGRO_ENV=staging`), numa fazenda de teste.
   Rode o fluxo completo (passos 1 a 6) contra staging.
2. **Verifique manualmente uma amostra** depois da carga — nao confie so no
   "criado com sucesso". Confira via `aegro companies get <key>` ou
   `aegro companies list`. Cubra cada caso: CNPJ (com endereco) e CPF.
3. **So depois de o staging conferir**, repita a mesma importacao em prod
   (ambiente default, sem `AEGRO_ENV`), apos confirmacao explicita do usuario.

> Os comandos `companies create`/`get` nao expoem `--env`; o alvo e controlado
> pela variavel **`AEGRO_ENV`** (`staging` para homologacao; ausente = prod) e a
> fazenda ativa por **`AEGRO_ACTIVE_FARM`**.

## Fluxo de Importacao

> Rode este fluxo inteiro em **staging** primeiro. So replique em **prod** depois
> da verificacao manual.

### 1. Ler a planilha

Use a skill `xlsx` para extrair a aba de dados. Descarte o cabecalho e todas as
linhas sem `Nome`. Conte quantos fornecedores validos existem antes de seguir.

### 2. Validar e mapear

Para cada linha:

- `Nome` preenchido (senao pular e registrar no relatorio)
- Classificar `CPF/CNPJ` pelos digitos: 14 -> `CNPJ`; 11 -> `CPF`; vazio ->
  **sem documento, nao cadastra** (a API retorna 422); qualquer outro tamanho ->
  marcar erro (nao criar)
- Normalizar o documento para digitos

### 3. Enriquecer dados (opcional, so CNPJ)

Para fornecedores com **CNPJ** e dados incompletos, enriqueca os dados
consultando a **Receita Federal** (razao social -> `--legal-name`, nome fantasia
-> `--trade-name`) antes de cadastrar. Os detalhes do endpoint e a autenticacao
sao fornecidos em **runtime** (nunca versionados nesta skill nem hardcoded).

Preserve o `Nome` da planilha em `--name`; use o retorno da Receita para
**completar** `--legal-name`/`--trade-name`. Se a consulta falhar (sessao
expirada, CNPJ nao encontrado, timeout), cadastre mesmo assim com os dados da
planilha e marque a linha como "nao enriquecido" no relatorio. CPF e sem
documento nao consultam a Receita.

### 4. Previa para conferencia

Mostre uma **tabela de previa** (nome, tipo de documento, documento mascarado,
enriquecido?) e o total a criar, mais a lista de linhas puladas/com erro.
**Peca confirmacao explicita do usuario antes de criar qualquer coisa.**

### 5. Dedup — nunca duplicar; em duvida, perguntar

Antes de criar, detecte duplicatas de **documento (CNPJ/CPF normalizado em
digitos)** em duas frentes:

- **dentro da propria planilha** (linhas repetidas)
- **contra empresas ja cadastradas** no ambiente

```bash
# Indexar empresas existentes (paginar ate cobrir todas)
aegro companies list --fiscal-number-type CNPJ --output json
aegro companies list --fiscal-number-type CPF --output json
# ou conferir um caso especifico:
aegro companies list --search-text "<nome>"
```

Compare tambem por nome normalizado (ignorando acento/maiusculas). **Quando
houver duplicata, PARE e pergunte ao usuario** como proceder (caso a caso ou em
lote); o **default seguro e NAO duplicar** (pular o registro). So crie apos a
decisao do usuario.

### 6. Criar em lote

Crie uma empresa por linha. Capture a `key` retornada de cada uma.

```bash
# Fornecedor com CNPJ (apos enriquecimento)
aegro companies create \
  --name "AGRO EXEMPLO LTDA" \
  --type PROVIDER \
  --fiscal-code 23706398000181 --fiscal-type CNPJ \
  --legal-name "AGRO EXEMPLO COMERCIO DE INSUMOS LTDA" \
  --trade-name "AGRO EXEMPLO"

# Fornecedor com CPF
aegro companies create \
  --name "JOAO DA SILVA" \
  --type PROVIDER \
  --fiscal-code 12345678901 --fiscal-type CPF
```

> **Sem documento nao cadastra:** a API exige CPF/CNPJ e rejeita empresa sem
> documento com **422 (campos invalidos)**. Nao tente cadastrar so com
> `--name --type PROVIDER` — pule a linha e registre no relatorio.

**Importacao segura (recomendado para lotes):** com `AEGRO_SAFE_MODE=1`, rode a
primeira linha com `--dry-run` para validar o payload, depois use `--execute`
nas criacoes. Faca retry em erros 5xx/timeout; nao faca retry em 4xx.

**Alvo:** em staging use `AEGRO_ENV=staging AEGRO_ACTIVE_FARM="<fazenda de teste>"`;
em prod omita `AEGRO_ENV` e use a fazenda real. Os mesmos comandos valem para os
dois ambientes.

### 6b. Verificar (obrigatorio apos o passe em staging)

```bash
aegro companies get <key> --output table
aegro companies list --fiscal-number-type CNPJ --output table
```

Confira uma amostra que cubra CNPJ enriquecido, CPF e sem documento. So avance
para prod quando a amostra estiver correta.

### 7. Relatorio final

Apresente:

- Criados: nome + chave retornada
- Pulados: duplicata (por documento/nome) ou sem nome
- Erros: linha + motivo (ex: documento com tamanho invalido)
- Enriquecidos: quantos CNPJs tiveram dados completados pela Receita

## Validacoes e Erros Comuns

| Situacao | Acao |
|---|---|
| Linha sem `Nome` | Pular, registrar no relatorio |
| Documento com tamanho inesperado (nem 11 nem 14) | Marcar erro, nao criar |
| Documento vazio | **Nao cadastra** (API retorna 422); pular e registrar |
| Duplicata por documento ou nome | **Parar e perguntar**; default: nao duplicar |
| Erro 4 (validacao) do CLI | Conferir flags; nao faz retry |
| Falha na consulta a Receita | Cadastrar com dados da planilha; marcar "nao enriquecido" |

## Limitacoes

- Sem endpoint de criacao em lote: cada empresa e um `companies create` separado
- Sem delete em lote: cadastros errados sao corrigidos um a um
- **Documento obrigatorio:** a API nao aceita empresa sem CPF/CNPJ (erro 422);
  linhas sem documento ficam de fora
- Enriquecimento so vale para CNPJ e depende de uma sessao valida de staging
  fornecida em runtime

## Proximos Workflows

- **Vincular fornecedor a contas a pagar** -> `/aegro-financeiro`
- **Criar ordens de compra** -> `/aegro-operacional`
