## Que linha desta PR muda o que o agente faz?

<!--
Responda em uma frase. Se a resposta for "nenhuma", a mudança provavelmente
pertence ao corpo do commit, não à SKILL.md.
-->

## O que muda

<!-- Skills tocadas e o comportamento novo, do ponto de vista de quem usa. -->

## Como foi verificado

<!--
Comando rodado, ambiente (staging/produção), e o que a releitura mostrou.
Detalhe de medição — data, tamanho de amostra, taxa de acerto, número de PR
do serv-core — vai AQUI, não na skill. Na skill fica só o número que muda o
que o agente faz.
-->

## Checklist

- [ ] `python scripts/lint_skills.py` limpo.
- [ ] Comando ou flag citado já saiu no PyPI, ou a instrução vale nas duas versões e diz quando o CLI cobra.
- [ ] `requires-cli` é a primeira release publicada que tem o recurso, ou não mudou.
- [ ] PR do CLI relacionada citada aqui (ou "nenhuma").
- [ ] Sem nome de cliente, fazenda real, data de medição, denominador ou número de PR no corpo da skill.
- [ ] Título `type(scope): description` com type aceito pela org (`chore` reprova).
