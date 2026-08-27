# Padrao das skills publicas do Aegro

Leia antes de editar qualquer `SKILL.md`. O crivo mecanico esta em
`scripts/lint_skills.py` e roda na PR — se voce mudar uma regra aqui, mude la.

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

> Evidencia nova, e mais forte que a anterior (19/08/2026): um plano de 1.272
> lancamentos tinha 7 classes, e uma delas tinha 1 unico lancamento. O canario
> de 55 estratificado o encontrou; um `--limit 50` seco tinha ~4% de chance.

O que **nunca** entra no corpo da skill:

- data de medicao ou de conferencia (`Conferido em producao em 21/08/2026`);
- tamanho de amostra, denominador, taxa de acerto (`acertou em 24 de 24 casos`);
- numero de PR ou de release do serv-core, nome de branch, `conferido por
  conteudo de branch`;
- changelog de bug ja corrigido — se o bug acabou, apague a linha do bug em vez
  de anunciar que ele acabou;
- autoria ou procedencia (`hipotese minha`, `feedback do Fulano`, `achado do
  CodeRabbit`);
- **nome de cliente, fazenda real ou qualquer PII** — este repositorio e publico.

Tudo isso pertence ao **corpo da PR**, que e onde um humano vai procurar quando
desconfiar da linha. O template de PR reserva uma secao para isso.

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

O valor tem de ser `X.Y.Z` e nada mais. `0.19`, `>=0.19.0` ou um comentario na
mesma linha (`0.19.0  # primeira release com --execute`) sao pisos que a CLI nao
consegue comparar — ela ignora, e o piso nunca avisa. O crivo recusa.

Declare `requires-cli` quando a skill citar comando ou flag que nao existe em
toda versao suportada. Use o numero da **primeira** release que tem o recurso
(`git tag --contains <commit>` no tool-aegro-cli), nunca a versao corrente por
reflexo: um piso alto demais faz todo mundo receber aviso inutil, e aviso inutil
e aviso ignorado.

Confira a tag no branch certo. O trunk do tool-aegro-cli e o `dev`, e ele fica a
frente do PyPI: `git tag --contains` num commit que so esta no `dev` devolve
vazio, e vazio quer dizer "ainda nao saiu", nao "esta em todas". Foi assim que
quatro pisos sairam errados aqui — `files attach` parecia 0.19.0 e e 0.21.0.

Quem compara e o `aegro skills install`/`sync`, que **avisa, sem bloquear** — a
skill instala do mesmo jeito. O comparador entrou na **v0.22.0**: em CLI mais
antiga o campo e lido por ninguem, entao o piso protege quem ja atualizou e nao
alcanca quem mais precisaria dele. Por isso o piso nao substitui a ressalva no
corpo quando a diferenca muda o que o agente deve fazer — veja
`aegro-financeiro` e `aegro-entrada-nota-fiscal`.

**Nunca declare uma versao que ainda nao saiu no PyPI.** Se a skill precisa
documentar comportamento que so existe no `dev`, escreva a regra de forma que
valha nas duas versoes e diga a partir de quando o CLI passa a cobrar — como em
`aegro-financeiro`, na secao de parcela a prazo.

**Nao existe `version:` por skill.** Ela era mantida a mao, apagada e regravada
na publicacao (`inject_version`/`_stamp` no `tool-aegro-cli`), e o unico efeito
observavel dela era gerar conflito entre PRs. A unica versao mantida a mao no
repositorio e a do plugin, em `.claude-plugin/`.

## Corpo

Titulos de secao, na ordem que fizer sentido para a skill — use so os que ela
precisa:

`Objetivo` · `Quando usar` · `Vocabulario` · `Pre-requisitos` ·
`Sequencia de passos` · `Referencia de comandos` · `Regras de negocio` ·
`Validacoes e erros comuns` · `Anti-padroes` · `Limitacoes` ·
`Proximos workflows`

Secao que o vocabulario nao previu pode existir. O que nao pode e **acrescentar
palavra a uma que ja existe**: `Referencia Completa de Comandos` ao lado de
`Referencia de comandos`, `Vocabulario do Dominio` ao lado de `Vocabulario`,
`Limitacoes Atuais` ao lado de `Limitacoes`. A palavra a mais nao carrega
informacao e faz parecer outra secao. O crivo cobra isso; caixa (`Quando Usar`
contra `Quando usar`) ele nao cobra, porque ninguem procura errado por causa
dela.

Todo exemplo de comando que **escreve** passa `--farm "<fazenda>"`. Nao existe
fazenda selecionada implicita: `AEGRO_ACTIVE_FARM` saiu em 28/07/2026, e o
estado do `farms select` e global por maquina — uma sessao em paralelo troca o
alvo da outra sem avisar.

Escrita perigosa mostra `--dry-run` antes de `--execute`.

Nao use nomes da era MCP (`list_farms`, `select_farm`): ela morreu em 03/2026.

## Antes de abrir a PR

```bash
python scripts/lint_skills.py
```

E responda a pergunta do template: **que linha desta PR muda o que o agente
faz?** Se a resposta for "nenhuma", a mudanca provavelmente pertence ao corpo do
commit.

O crivo le o `SKILL.md` e tambem os `reference/*.md` da skill: as regras de corpo
valem para os dois. Foi por olhar so o `SKILL.md` que um nome de cliente
sobreviveu em dois arquivos de referencia.

Peca review, e confira que o pedido saiu. `main` exige uma aprovacao e ninguem
tem bypass, entao PR sem revisor pedido nao entra — fica parada. O CODEOWNERS
auto-solicita, mas conferir custa um segundo.
