# 0005 — `requires-cli` e a primeira release que tem o recurso

Agosto de 2026.

O piso e o numero da **primeira** release publicada que tem o comando ou a flag
que a skill cita. Nunca a versao corrente por reflexo: piso alto demais faz todo
mundo receber aviso inutil, e aviso inutil e aviso ignorado.

## O erro que criou a regra de conferir no branch certo

Os pisos da primeira rodada foram conferidos com `git tag --contains` no `main`
do `tool-aegro-cli`. O trunk dele e o **`dev`**, e o `dev` fica a frente do PyPI.
`git tag --contains` num commit que so esta no `dev` devolve vazio — e vazio quer
dizer "ainda nao saiu", nao "esta em todas".

Quatro pisos sairam errados assim. `files attach` e `list-attachments` entraram
na v0.21.0 (commit `6e04e98`) e pareciam 0.19.0; o guard de campo desconhecido no
`--body` tambem e 0.21.0. `aegro-migracao-categorias` pedia 0.19.0 e precisa de
0.20.0 (`--effective-start`, `--sweep-concurrency`).

O pior nao era o numero. `aegro-agronomo` declarava 0.19.0 e dizia ao agente que
o CLI recusa campo desconhecido no `--body` antes de enviar. Na 0.19.0 isso nao
existe: a API aceita, descarta o campo em silencio e responde 200 — e o paragrafo
seguinte da propria skill dizia que a releitura ia parecer certa.

## Por que o piso nao substitui a ressalva no corpo

Quem compara e o `aegro skills install`/`sync`, e o comparador entrou na v0.22.0.
Em CLI mais antiga o campo nao e lido por ninguem: o piso protege quem ja
atualizou e nao alcanca quem mais precisaria dele.

Por isso, quando a diferenca de versao muda o que o agente deve fazer, a skill
diz no corpo — primeiro a verdade que nao depende de versao, depois a guarda
datada. Ver `aegro-financeiro` (conta bancaria em parcela a prazo) e
`aegro-entrada-nota-fiscal` (lancamento PARCIAL).
