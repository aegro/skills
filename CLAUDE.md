# Padrao das skills publicas do Aegro

Leia antes de editar qualquer `SKILL.md`. O crivo mecanico esta em
`scripts/lint_skills.py` e roda na PR — se voce mudar uma regra aqui, mude la.

Este arquivo e so regra. O porque de cada uma, quando nao for obvio, esta em
[`docs/decisions/`](docs/decisions/).

## O que uma skill e

Instrucao para um agente executar trabalho de cliente pela CLI `aegro`. Nao e
documentacao de referencia, nao e changelog, e nao e o registro da investigacao
que produziu a instrucao.

O leitor e um modelo com contexto limitado que vai agir. Cada linha que nao muda
o que ele faz custa espaco que faltaria para a linha que muda.

## A regra que mais pega

**Fica o numero que muda o que o agente faz. Sai o argumento que justificou
escrever a linha.**

Fica — muda a decisao:

> Cerca de 3% dos lancamentos nao gravam em silencio: a API responde 200 e a
> conta continua na categoria antiga. Nao trate como incidente; traga o numero
> para quem opera decidir.

Sai — e o debate que ja terminou:

> Evidencia nova, e mais forte que a anterior: a amostra estratificada achou uma
> classe com um unico lancamento, que a amostra seca tinha pouca chance de pegar.

O que **nunca** entra no corpo da skill:

- data de medicao ou de conferencia (`Conferido em producao em 21/08/2026`);
- tamanho de amostra, denominador, taxa de acerto (`acertou em 24 de 24 casos`);
- numero de PR ou de release do serv-core, nome de branch, `conferido por
  conteudo de branch`;
- changelog de bug ja corrigido — se o bug acabou, apague a linha do bug em vez
  de anunciar que ele acabou;
- autoria ou procedencia (`hipotese minha`, `feedback do Fulano`, `achado do
  CodeRabbit`);
- **nome de cliente, fazenda real ou qualquer PII** — este repositorio e publico,
  e o conteudo dele vai para o PyPI dentro do wheel da CLI.

Tudo isso pertence ao **corpo da PR**, que e onde um humano vai procurar quando
desconfiar da linha. O template de PR reserva uma secao para isso. Se a regra em
si e que precisa de defesa, o lugar e `docs/decisions/`.

## A `description`

E a unica coisa que o modelo le para decidir se carrega a skill. Uma description
curta nao e "enxuta": e uma skill que nao dispara, ou que dispara em cima da
skill vizinha.

Minimo de 200 caracteres, em bloco `>-`, com quatro partes nesta ordem:

1. **O que faz**, concreto, dizendo que e pela CLI `aegro`.
2. **Gatilhos em PT-BR** entre aspas, com as palavras que o usuario usa de
   verdade — `"o estoque nao bate"`, nao `"reconciliacao de inventario"`.
3. **Gatilhos em EN** entre aspas, precedidos de `EN`.
4. **`NAO use ...`** apontando a skill certa: `NAO use para X (use /aegro-outra)`.

```yaml
description: >-
  Concilia o extrato bancario com o financeiro do Aegro pela CLI: importa o OFX,
  casa entradas do extrato com os movimentos internos, confirma em lote e fecha o
  saldo Aegro x banco no periodo. Use quando pedirem "conciliar o banco",
  "importar OFX", "o saldo nao bate com o extrato"; EN "bank reconciliation",
  "import OFX". NAO use para lancar conta nova (use /aegro-lancamento-financeiro)
  nem para divergencia de estoque (use /aegro-reconciliacao-estoque).
```

## Frontmatter

So tres campos, e dois sao obrigatorios:

| Campo | | |
|---|---|---|
| `name` | obrigatorio | igual ao nome do diretorio |
| `description` | obrigatorio | contrato acima |
| `requires-cli` | opcional | versao minima da CLI, exatamente `X.Y.Z` |

O valor tem de ser `X.Y.Z` e nada mais: `0.19`, `>=0.19.0` ou um comentario na
mesma linha sao pisos que a CLI nao consegue comparar — ela ignora, e o piso
nunca avisa. O crivo recusa.

Nao existe `version:` por skill ([0001](docs/decisions/0001-sem-version-por-skill.md)).

## Corpo

Titulos de secao, na ordem que fizer sentido para a skill — use so os que ela
precisa:

`Objetivo` · `Quando usar` · `Vocabulario` · `Pre-requisitos` ·
`Sequencia de passos` · `Referencia de comandos` · `Regras de negocio` ·
`Validacoes e erros comuns` · `Anti-padroes` · `Limitacoes` ·
`Proximos workflows`

Secao que o vocabulario nao previu pode existir. O que nao pode e acrescentar
palavra a uma que ja existe: `Referencia Completa de Comandos` ao lado de
`Referencia de comandos`, `Limitacoes Atuais` ao lado de `Limitacoes`. Caixa o
crivo nao cobra
([0002](docs/decisions/0002-titulo-palavra-a-mais-nao-caixa.md)).

Todo exemplo de comando que **escreve** passa `--farm "<fazenda>"`. Nao existe
fazenda selecionada implicita, e o estado do `farms select` e global por maquina:
uma sessao em paralelo troca o alvo da outra sem avisar.

Escrita perigosa mostra `--dry-run` **e** a forma que aplica (`--execute`): dizer
para apagar e mostrar so o ensaio deixa o agente adivinhando a flag.

Nao use nomes da era MCP (`list_farms`, `select_farm`).

As regras desta secao valem tambem para os `reference/*.md` da skill, e o crivo
os le ([0003](docs/decisions/0003-crivo-le-os-reference.md)).

## Antes de abrir a PR

```bash
python scripts/lint_skills.py
```

E responda a pergunta do template: **que linha desta PR muda o que o agente
faz?** Se a resposta for "nenhuma", a mudanca provavelmente pertence ao corpo do
commit.

Peca review, e confira que o pedido saiu: `main` exige uma aprovacao e ninguem
tem bypass, entao PR sem revisor pedido fica parada. O CODEOWNERS auto-solicita.
