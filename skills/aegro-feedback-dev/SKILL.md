---
name: aegro-feedback-dev
description: >-
  Compila erros, atritos e sugestoes das sessoes de lancamento (notas e contas)
  num doc de triagem para o time de dev melhorar API, CLI e skills. Coleta os
  blocos de erro dos diarios de sessao ($AEGRO_LEARNING_DIR), telemetria JSONL do
  CLI aegro e relato direto na conversa; deduplica por sintoma, classifica cada
  item (resolvido/mapeado/novo) com dono (CLI, API publica ou skill) e evidencia
  anonimizada, e produz um doc de feedback com encaminhamento. Detecta se quem usa
  e do time Aegro (abre issue/PR interno) ou cliente (monta o feedback no molde do
  formulario publico para o cliente enviar a um clique). Use ao fim de uma sessao com erros ("compilar esses
  erros pro time de dev", "montar relatorio dos bugs da sessao") ou na rodada
  semanal ("triagem do feedback", "fechar o feedback da semana", "compile field
  feedback", "triage errors for dev"). NAO use para suporte a cliente final, para
  reportar bug de produto Aegro fora do fluxo CLI/API (use o fluxo normal de bug),
  nem durante o lancamento em si (quem registra e a skill de lancamento; esta compila).
version: 0.1.0
---

# Feedback de campo -> time de dev

Transforma o que deu errado nas sessoes de lancamento em melhoria concreta de
API, CLI e skills: um doc de triagem com dono por item, evidencia anonimizada e
encaminhamento. E a formalizacao do metodo que ja funcionou nas rodadas de
jun-jul/2026 (`tool-aegro-cli/docs/feedback/`).

## Modo da sessao: time Aegro vs. cliente (ler primeiro)

Identifique quem esta compilando pelo **e-mail do usuario** no contexto da sessao:

- **Interno — `@aegro.com.br`** (time de Servicos / dev): fluxo completo — gera o
  doc de triagem em `tool-aegro-cli/docs/feedback/` e **encaminha** para issue no
  `aegro/tool-aegro-cli`, item em `melhorias-api-publica.md` ou PR de skill.
- **Externo — outro dominio** (cliente): compila o relatorio **no molde do
  formulario publico de feedback** (Email + Resumo + Descricao), entrega o
  conteudo pronto para colar e o link do formulario. **Nao** abre issue em
  repositorio interno nem escreve em `docs/` do tool-aegro-cli. Ver
  "Encaminhamento no modo externo (formulario)".

Sem e-mail identificavel, trate como **externo**.

## Quando usar / quando NAO usar

**Usar:**
- Ao fim de uma sessao de lancamento em que a skill de lancamento
  (`/aegro-entrada-nota-fiscal` e afins) registrou blocos `### erro` e o usuario
  aceitou compilar.
- Na rodada semanal de coleta do time (consolidar os diarios acumulados).
- Quando alguem relatar um problema recorrente fora de sessao.

**Nao usar:**
- Suporte a cliente final ou bug do app Aegro sem relacao com CLI/API publica —
  segue o fluxo normal de bug do produto.
- Durante o lancamento: registrar e responsabilidade da skill de lancamento;
  compilar no meio da sessao atrapalha quem opera.

## Fontes de dados

1. **Diarios de sessao**: `$AEGRO_LEARNING_DIR/journal-*.md` — blocos `### erro`
   (comando, resposta, impacto, workaround, sugestao).
2. **Telemetria do CLI**: `$AEGRO_TELEMETRY_DIR/*.jsonl` — needs_input, resolucoes
   ambiguas, timings, status de API (anonimizada por construcao).
3. **Docs de aprendizado**: `$AEGRO_LEARNING_DIR/aprendizado-*.md`.
4. **Relato direto** na conversa (transformar em item estruturado).

Se alguma fonte nao existir no ambiente (comum no modo externo, sem diario/
telemetria), siga com as disponiveis e diga quais faltaram — nunca invente item
sem evidencia.

## Fluxo

### 1. Coletar e recortar

Leia as fontes do periodo (sessao atual ou semana). Cada bloco `### erro`, cada
padrao recorrente na telemetria e cada relato vira um item candidato.

### 2. Deduplicar por sintoma

Mesmo sintoma em sessoes diferentes = **um item so**, com contagem de ocorrencias
e fazendas afetadas (mascaradas: `cliente_a`, `cliente_b`). Frequencia e sinal de
prioridade — registre-a.

### 3. Classificar cada item

Duas dimensoes, sempre:

- **Status**: `resolvido` (fix ja existe — citar versao/PR), `mapeado` (ja
  conhecido — citar doc/issue) ou `novo`.
- **Dono**: `CLI` (tool-aegro-cli), `API` (plataforma / API publica), `skill`
  (aegro/skills) — ou combinacao, indicando a ordem.

Antes de marcar `novo`, confira o que ja esta mapeado em
`tool-aegro-cli/docs/melhorias-api-publica.md`, nos docs de
`tool-aegro-cli/docs/feedback/` anteriores e nos gotchas das skills — item
re-reportado vira ocorrencia do item existente, nao duplicata.

### 4. Evidenciar com seguranca

Cada item leva: comando executado (sem credenciais), resposta resumida, ambiente
(staging/prod), versao do CLI. **Nunca** credenciais; PII de cliente sempre
mascarada (nome -> `cliente_x`, CNPJ -> `00.000.000/0001-00`). Prefira
shape/agregado a dado bruto.

### 5. Gerar o doc de triagem

No modo interno, salve em `tool-aegro-cli/docs/feedback/AAAA-MM-DD-<tema>.md`. No
modo externo, este doc e a fonte dos campos do formulario (secao
"Encaminhamento no modo externo") — o Resumo de cada item vira o `Resumo:` e o
corpo vira a `Descricao:`. Formato:

```markdown
# Feedback de campo — <tema> (AAAA-MM-DD)

> Fontes: N sessoes (DD/MM-DD/MM), M itens apos dedupe.

## Itens

### 1. <sintoma em uma linha>
- status: novo | mapeado | resolvido
- dono: CLI | API | skill (ordem, se combinado)
- ocorrencias: N (cliente_a, cliente_b)
- evidencia: comando + resposta resumida + ambiente + versao
- impacto: <o que travou/atrasou/quase deu errado>
- sugestao: <a menor melhoria que elimina o sintoma>

## Encaminhamentos
| Item | Dono | Acao | Link |
|---|---|---|---|
```

### 6. Encaminhar

**Modo interno**, com aprovacao do usuario:
- **CLI** -> issue (ou PR direto, se trivial) em `aegro/tool-aegro-cli`.
- **API** -> adicionar/atualizar item em
  `tool-aegro-cli/docs/melhorias-api-publica.md`.
- **skill** -> PR em `aegro/skills`.

**Modo externo:** siga a secao "Encaminhamento no modo externo (formulario)" —
nao abra issue/PR em repositorio interno.

Feche o loop: itens `resolvido` desde a ultima rodada entram numa secao curta
"Resolvidos desde a ultima rodada" — quem reporta precisa ver que funciona.

## Encaminhamento no modo externo (formulario)

O cliente **nao tem conta no Jira** e pode nao ter browser automatizado, e o
formulario e **protegido por reCAPTCHA** — entao a skill **nao envia sozinha**.
O papel dela e deixar o envio a **um clique**: montar o conteudo exatamente no
molde do formulario e o cliente cola e clica Enviar (ele resolve o reCAPTCHA, o
que e trivial para uma pessoa).

**Formulario:**
`https://aegrodev.atlassian.net/jira/software/form/bf7148ca-5456-4fc7-b5a1-bf6cc7bc49ed`
(publico, sem login). Campos: **Email** (obrigatorio), **Resumo** (obrigatorio),
**Descricao** (texto), anexo opcional.

**O que a skill entrega, por item** (um envio por item — o formulario cria uma
issue por submissao):

- **Email:** pergunte o e-mail do cliente (para retorno). Ele vai como reporter
  — deixe claro que e o unico dado de contato que sai; nao inclua PII de terceiro.
- **Resumo:** o sintoma em uma linha, prefixado pelo tipo — `[FR]` para pedido de
  funcionalidade/falta na CLI, `[Bug]` para erro. Ex.: `[Bug] launch-bill 500 ao
  parcelar nota da Corteva`.
- **Descricao:** o corpo estruturado do item (impacto, evidencia com comando +
  resposta resumida, ambiente, versao do CLI, sugestao) — **anonimizado**
  (fornecedor -> `fornecedor_x`, CNPJ -> `00.000.000/0001-00`), sem credenciais.

**Como apresentar:** mostre o link e, para cada item, um bloco copiavel com
`Resumo:` e `Descricao:` prontos. Instrua: abrir o link, colar os dois campos,
preencher o e-mail, clicar **Enviar** (e passar o reCAPTCHA). Se houver varios
itens, liste-os e deixe o cliente escolher quais enviar.

> O formulario se chama "Necessidade na CLI" (intake de FR). Bugs tambem cabem —
> por isso o prefixo `[FR]`/`[Bug]` no Resumo, para a triagem separar depois.
> **Nao tente automatizar o POST** (o reCAPTCHA existe para barrar isso).

## Principios

- **Evidencia > opiniao**: item sem comando/resposta reproduzivel e hipotese —
  entra marcado como tal, no fim do doc.
- **Um item = um sintoma com dono.** Item "guarda-chuva" nao gera acao.
- **Frequencia prioriza**: 1 ocorrencia interessa; 5 ocorrencias mandam.
- **Fechar o loop motiva o campo**: reporte de volta o que foi resolvido.
- **Seguranca primeiro**: nada de credenciais; PII mascarada; conteudo interno.

## Failure modes — quando escalar

- Item aponta **perda ou corrupcao de dado de cliente em prod** (ex.: valor
  gravado errado) -> nao espere a rodada semanal: escale imediatamente ao time de
  dev com o doc parcial.
- Divergencia entre telemetria e diario -> registre as duas versoes e marque para
  investigacao, nao escolha uma.
- Volume grande demais (>30 itens novos) -> agrupe por modulo e proponha priorizar
  com o time antes de detalhar tudo.

## Comandos de referencia

| Objetivo | Comando |
|---|---|
| Listar diarios do periodo | `ls $AEGRO_LEARNING_DIR/journal-*.md` |
| Blocos de erro dos diarios | `grep -A6 "### erro" $AEGRO_LEARNING_DIR/journal-*.md` |
| Telemetria da semana | `ls $AEGRO_TELEMETRY_DIR/*.jsonl` |
| Versao do CLI (para a evidencia) | `aegro --version` |
