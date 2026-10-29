# Contribuindo com as skills publicas do Aegro

Este repo e mantido pela squad **Agentes** e aceita PR de qualquer squad: quem entrega um comando
novo no [`tool-aegro-cli`](https://github.com/aegro/tool-aegro-cli) escreve ou atualiza a skill que
o instrui. As regras do conteudo (o que entra e o que nao entra numa `SKILL.md`) estao em
[`AGENTS.md`](AGENTS.md) e o crivo mecanico em `scripts/lint_skills.py`; este arquivo diz **como o
trabalho entra e sai** do repo.

Tres coisas tornam este repo diferente dos repos de codigo:

- **E publico.** Nada de nome de cliente, fazenda real, credencial ou dado interno. O que esta
  aqui e lido por qualquer pessoa.
- **Merge em `main` e publicacao.** O marketplace do Claude Code le o repo, `aegro skills sync`
  baixa o `main` em runtime e a proxima release do CLI embute um snapshot no wheel do PyPI. Nao
  existe passo de deploy entre a aprovacao e o cliente.
- **A skill nao tem runtime proprio.** O que ela cita precisa existir na CLI publicada; o drift
  semanal confere, mas uma semana depois.

## Antes de comecar

1. **Todo trabalho nasce de uma issue.** Instrucao errada relatada por usuario e um
   [Ticket de Suporte](https://github.com/aegro/workspace/blob/dev/governance/conventions/ticket-de-suporte.md)
   no `aegro/workspace` (repo interno da Aegro; quem e de fora reporta pelo Suporte) com
   `Produto = CLI`; a `aegro-feedback-dev` abre ou monta o bloco.
   Skill nova ou secao nova por causa de comando novo e uma `Tarefa` ligada a PR do CLI.
2. **Confira o estado da CLI publicada** (`pip index versions aegro` ou a pagina do PyPI) antes de
   escrever instrucao que depende de comando recente.
3. **Setup:** so Python 3.12+. `python scripts/lint_skills.py` roda sem rede e sem a CLI.

## Quem revisa

- `.github/CODEOWNERS` pede review de `@aegro/squad-agentes` em tudo. A ruleset de `main` exige
  uma aprovacao de outra pessoa, threads resolvidas e squash; ninguem tem bypass.
- Skill de um dominio (financeiro, agricola, fiscal) escrita por outra squad: a Agentes revisa a
  forma e o acoplamento com o CLI; a regra de negocio e de quem escreveu.
- A automacao de tickets (`aeg-code-ticket --profile skills`) abre PRs aqui em draft, como
  `aegro-github-bot`, quando o fix de um ticket do CLI tambem muda a instrucao. Revise como
  qualquer PR.

## Checklist de skill nova ou de secao nova

- [ ] Diretorio `skills/aegro-<dominio>/` com `SKILL.md`; `name` igual ao diretorio.
- [ ] `description` em bloco `>-`, 200 caracteres ou mais, nas quatro partes do
      [`AGENTS.md`](AGENTS.md#a-description) (o que faz pela CLI, gatilhos PT-BR, gatilhos `EN`,
      `NAO use ... (use /aegro-outra)`).
- [ ] Titulos de secao do vocabulario do `AGENTS.md`; sem palavra a mais num titulo que ja existe.
- [ ] Todo exemplo de escrita passa `--farm "<fazenda>"`; escrita perigosa mostra `--dry-run` **e**
      `--execute`.
- [ ] Nenhum comando ou flag que ainda nao saiu no PyPI, salvo com a ressalva de versao no corpo.
- [ ] `requires-cli: X.Y.Z` e a primeira release publicada que tem o recurso, conferida com
      `git tag --contains <sha>` no `dev` do `tool-aegro-cli` ([decisao 0005](docs/decisions/0005-piso-da-primeira-release.md)).
- [ ] Sem data de medicao, denominador, numero de PR, autoria, nome de cliente ou fazenda no corpo.
      Isso vai no corpo da PR.
- [ ] Skill nova listada no `README.md` (o crivo cobra).
- [ ] `python scripts/lint_skills.py` limpo.

## Fluxo de PR

1. Branch de `main`: `<tipo>/<slug>` (`fix/financeiro-parcela-a-prazo`). Tipos aceitos pelo check
   da org: `feat` `fix` `build` `docs` `refactor` `ci` `revert` `test` `perf`; `chore` reprova.
2. Abra contra `main` com o template preenchido. A primeira pergunta do template e a que importa:
   **que linha desta PR muda o que o agente faz?**
3. Titulo `type(scope): description`, scope = a skill tocada (`fix(aegro-financeiro): ...`), ou
   `skills` quando a PR toca varias.
4. Merge exige uma aprovacao, threads resolvidas e os checks obrigatorios da ruleset:
   `all_checks_passed` (que agrega o `lint` e o `gitleaks`) e `check_pr_title`. Squash; o subject
   do squash e o titulo da PR.

## Coordenacao com o CLI

| Situacao | O que fazer |
|---|---|
| Comando novo ou flag nova no CLI | A PR do CLI cita a skill afetada; a PR da skill e aberta junto e **espera a tag** do CLI para subir o `requires-cli`. Enquanto a tag nao sai, a skill pode entrar com a instrucao escrita para valer nas duas versoes. |
| Comando removido ou renomeado no CLI | A PR do CLI abre a PR par aqui antes do merge. O drift semanal e a rede, nao o processo. |
| Defeito do CLI ou do endpoint descoberto ao escrever a skill | Ticket de Suporte com `Produto = CLI`. A skill **nao** ganha contorno; no maximo a ressalva que muda o que o agente faz enquanto o defeito existe, removida quando o fix sai. |
| Drift semanal acusou divergencia (`issue fixa "Drift: skills x CLI publicada"`) | Corrija a skill, ou o parser do drift quando for falso positivo. Nao feche a issue: o job a reabre. |

## Publicacao e versao

- Merge em `main` publica. Nao ha tag nem release no repo.
- A versao do plugin em `.claude-plugin/plugin.json` e `marketplace.json` e uma so, mantida a mao
  nas duas copias: suba `minor` quando entra skill nova e `patch` quando so muda instrucao, no
  mesmo PR. Gerar esse numero em vez de manter e debito conhecido
  ([decisao 0001](docs/decisions/0001-sem-version-por-skill.md)).
- O snapshot embutido no wheel do CLI so atualiza na proxima release do CLI; quem usa `aegro skills
  sync` recebe no mesmo dia. Instrucao urgente (dado gravado errado) pede aviso no canal do time
  de Servicos alem do merge.

## O que nao entra aqui

- Codigo da CLI, teste de comando, snapshot OpenAPI: `tool-aegro-cli`.
- Skills internas da operacao da Aegro: `aegro/workspace/tools/plugins/` (marketplace interno).
- Registro de investigacao, feedback de campo, PRD: `aegro/workspace`. A skill fica so com o
  numero que muda o que o agente faz; o porque vai em `docs/decisions/` quando a regra precisa
  de defesa.
