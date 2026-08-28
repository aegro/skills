# 0004 — Crivo na PR, drift agendado

Agosto de 2026.

Sao dois jobs de proposito:

- `lint-skills.yml` roda em toda PR. So checagens que se resolvem lendo o
  repositorio — frontmatter, contrato da description, rastro de investigacao no
  corpo. Sem rede, sem CLI, sem segredo.
- `drift-cli.yml` roda semanalmente. Instala a `aegro` do PyPI e confere que cada
  comando citado existe e que todo exemplo de escrita passa `--farm`.

## Por que o drift nao pode ir para a PR

As duas checagens dele dependem da CLI publicada, e mudam quando o CLI muda.
Cobrar na PR deixaria vermelha a PR de quem nao mexeu em contrato nenhum — e o
autor aprenderia a ignorar o vermelho, que e a unica coisa pior do que nao ter o
job. Mesmo raciocinio do `openapi-drift.yml` no `tool-aegro-cli`.

E nao da para trocar o `--help` real por leitura de assinatura: `--farm` e opcao
compartilhada, definida uma vez em `aegro/cli/_config.py`, entao ela nao aparece
no `def` de cada comando. Um extrator estatico erra — e errou, dizendo que `tags
archive` nao aceitava `--farm` quando aceita.

## O ruido que a primeira versao produziu

Ao passar a ler exemplo inline no meio da prosa, a primeira rodada acusou 43
divergencias contra 4 — e 39 eram falso positivo. Eram linhas da tabela de
referencia, onde a citacao e o nome do comando e as flags moram em outra coluna:

```
| `aegro tags archive <tag-key>` | Arquiva ... | `--dry-run`, `--execute` |
```

Dai a regra: citacao sem flag nenhuma e nome de comando, nao exemplo. A checagem
de existencia continua valendo para ela; a do `--farm`, nao.

O job tambem passou a distinguir timeout de "comando removido". Um runner lento
abria issue acusando skill correta, e alguem ia editar uma skill certa para
perseguir fantasma.
