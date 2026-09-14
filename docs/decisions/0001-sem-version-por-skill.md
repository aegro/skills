# 0001 — Nao existe `version:` por skill

Agosto de 2026.

O frontmatter de cada `SKILL.md` tinha um `version:` mantido a mao. O crivo agora
recusa o campo.

## Por que ele saiu

O valor era apagado e regravado na publicacao — `inject_version` em
`scripts/skills_source.py` e `_stamp` em `aegro/cli/skills.py`, no
`tool-aegro-cli`, escrevem a versao do pacote no snapshot embutido. Ou seja: o
numero que a pessoa mantinha a mao nunca chegava a ser lido por nada.

O unico efeito observavel dele era conflito. Duas PRs que mexessem em skills
diferentes nao conflitavam; duas que mexessem na mesma skill conflitavam **na
linha do `version:`**, que nenhuma das duas tinha motivo para tocar. Foi o que
aconteceu com a #26.

## O que sobrou mantido a mao

A versao do plugin, em `.claude-plugin/plugin.json` e
`.claude-plugin/marketplace.json`. Sao duas copias do mesmo numero e nada confere
que elas concordam — mesmo problema, escala menor. Se voltar a doer, o caminho e
o mesmo: gerar em vez de manter.
