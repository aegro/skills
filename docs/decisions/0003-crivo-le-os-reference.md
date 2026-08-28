# 0003 — As regras de corpo valem para `reference/*.md`

Agosto de 2026.

O crivo lia so o `SKILL.md`. As checagens de corpo — nome de ferramenta morta,
data de medicao, denominador de amostra — agora rodam em todo markdown da skill.

O buraco apareceu do pior jeito. Um nome de fazenda de cliente estava em cinco
lugares deste repositorio, que e publico. A primeira limpeza tirou o que estava
no `SKILL.md`, ao lado de uma data de medicao, e o assunto pareceu resolvido —
dois `reference/*.md` continuaram com o nome, porque nada os lia.

Consequencia que o repositorio publico nao esgota: `scripts/sync-skills.py`
embute o `main` deste repositorio no wheel da CLI a cada publicacao, e
`publish.yml` tem um guard que falha se o snapshot **nao** entrar no pacote. Isto
e, conteudo daqui vai para o PyPI, que e imutavel e espelhado.
