---
name: aegro-importacao-fornecedores
description: >-
  Importa a carteira de fornecedores de uma planilha (nome + CPF/CNPJ) para o
  Aegro pela CLI: classifica o documento, enriquece opcionalmente os dados de
  quem tem CNPJ, mostra previa para conferencia e cria as empresas sem
  duplicar. Use quando pedirem "importar fornecedores", "subir a lista de
  fornecedores", "cadastrar fornecedores em lote", "planilha de fornecedores";
  EN "import suppliers in bulk". NAO use para cadastrar um fornecedor so (use
  /aegro-financeiro) nem para importar patrimonio (use
  /aegro-importacao-patrimonio).
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

## Ordem Obrigatoria: Lote Pequeno -> Verificacao -> Resto

Importacao em prod mexe em dados **reais** do cliente e **nao tem delete em
lote** — um cadastro errado e trabalhoso de desfazer. A protecao **nao** e
importar em staging antes: aquele ambiente e reposto de producao todo dia as
03:15 BRT, entao a carga de la desaparece e nao prova que a de prod vai valer.
O que limita o estrago e o tamanho do primeiro lote. Siga sempre esta ordem:

1. **Importe um lote pequeno primeiro** (5 a 10 linhas), no ambiente do
   trabalho, **cobrindo cada caso** da planilha: CNPJ com endereco e CPF. Uma
   duzia de cadastros errados se conserta a mao; trezentos, nao.
2. **Verifique por leitura** — nao confie so no "criado com sucesso". Confira
   via `aegro companies get <key>` ou `aegro companies list` que os campos
   chegaram como esperado. Ha caminho de escrita no Aegro que responde sucesso
   sem gravar, e a releitura e o que separa um do outro.
3. **So depois que a amostra conferir**, importe o resto, apos confirmacao
   explicita do usuario.

> Um ensaio em `staging` (`--env staging`) continua util para **conhecer o
> comando** e ver a forma da saida — e as chaves de la sao as mesmas de
> producao, porque o ambiente e uma copia. Mas o que voce **criou** la morre no
> restore das 03:15 BRT: nao use como validacao.

> Os comandos `companies` (`create`/`get`/`list`/`update`) expoem `--env`
> (`staging` para homologacao; `prod` para producao; default `prod`) e
> **`--farm <nome|farm::key>`** — passe os dois explicitamente em cada comando. A
> flag `--farm` e preferivel ao `farms select`, porque viaja com o comando: nao
> depende de arquivo global que outra sessao possa ter trocado. (A env var
> `AEGRO_ACTIVE_FARM` foi removida em 28/07/2026.)

## Fluxo de Importacao

> Rode este fluxo inteiro **no ambiente do trabalho**, comecando por um lote
> pequeno: os passos 1 a 5 preparam, o 6 cria a amostra e o 6b confere por
> leitura. So depois da conferencia vai o resto (ver secao acima).

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
# Indexar empresas existentes no ambiente do trabalho (paginar ate cobrir todas)
aegro companies list --farm "<fazenda>" --env prod --fiscal-number-type CNPJ --output json
aegro companies list --farm "<fazenda>" --env prod --fiscal-number-type CPF --output json
# ou conferir um caso especifico:
aegro companies list --farm "<fazenda>" --env prod --search-text "<nome>"
```

Compare tambem por nome normalizado (ignorando acento/maiusculas). **Quando
houver duplicata, PARE e pergunte ao usuario** como proceder (caso a caso ou em
lote); o **default seguro e NAO duplicar** (pular o registro). So crie apos a
decisao do usuario.

### 6. Criar em lote

Crie uma empresa por linha. Capture a `key` retornada de cada uma.

```bash
# --env e --farm explicitos em todo comando: o default de --env e prod, e um
# alvo implicito e o que faz a carga cair na fazenda errada. Comece pelo lote
# pequeno e so mande o resto depois da conferencia por leitura (passo 6b).

# Fornecedor com CNPJ (apos enriquecimento)
aegro companies create --farm "<fazenda>" --env prod \
  --name "AGRO EXEMPLO LTDA" \
  --type PROVIDER \
  --fiscal-code 23706398000181 --fiscal-type CNPJ \
  --legal-name "AGRO EXEMPLO COMERCIO DE INSUMOS LTDA" \
  --trade-name "AGRO EXEMPLO"

# Fornecedor com CPF
aegro companies create --farm "<fazenda>" --env prod \
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

**Alvo:** `--env` e `--farm` explicitos em **todo** comando, apontando para o
ambiente e a fazenda do trabalho (ver "Ordem Obrigatoria: Lote Pequeno ->
Verificacao -> Resto"). Comece pelo lote pequeno; os mesmos comandos servem para
o resto da carga, sem mudar nada alem do conteudo do lote.

### 6b. Verificar (obrigatorio apos o lote pequeno)

```bash
aegro companies get --farm "<fazenda>" <key> --env prod --output table
aegro companies list --farm "<fazenda>" --env prod --fiscal-number-type CNPJ --output table
```

Confira uma amostra que cubra CNPJ enriquecido, CPF e sem documento — **por
leitura**, nunca pela mensagem de sucesso. So importe o resto quando a amostra
estiver correta.

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
| Erro 4xx (validacao) do CLI | Conferir flags; nao faz retry |
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
