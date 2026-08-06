---
name: aegro-feedback-dev
description: >-
  Compila erros, atritos e sugestoes das sessoes de lancamento (notas e contas)
  num doc de triagem para o time de dev melhorar API, CLI e skills. Coleta os
  blocos de erro dos diarios de sessao ($AEGRO_LEARNING_DIR), telemetria JSONL do
  CLI aegro e relato direto na conversa; deduplica por sintoma, classifica cada
  item (resolvido/mapeado/novo) com dono (CLI, API publica ou skill) e evidencia
  anonimizada, e produz um doc de feedback pronto para entregar ao time. A
  entrega nunca passa por git: no modo interno (time Aegro) tenta mensagem no
  Google Chat para o dono da triagem, com confirmacao antes de enviar, e cai no
  formulario de feedback do CLI quando nao ha conector; no modo cliente monta o
  conteudo no molde do formulario publico para o cliente enviar a um clique. Use
  ao fim de uma sessao com erros ("compilar esses erros pro time de dev", "montar
  relatorio dos bugs da sessao") ou na rodada semanal ("triagem do feedback",
  "fechar o feedback da semana", "compile field feedback", "triage errors for
  dev"). NAO use para suporte a cliente final, para reportar bug de produto Aegro
  fora do fluxo CLI/API (use o fluxo normal de bug), nem durante o lancamento em
  si (quem registra e a skill de lancamento; esta compila).
version: 0.2.0
---

# Feedback de campo -> time de dev

Transforma o que deu errado nas sessoes de lancamento em melhoria concreta de
API, CLI e skills: um doc de triagem com dono por item, evidencia anonimizada e
uma entrega que chega ao time no fim da rodada.

## Regra dura: sem git, sem repositorio

Esta skill **nao usa git**, nao roda `gh`, nao abre issue nem PR e nao escreve em
repositorio nenhum. Quem compila (EV de campo, time de Servicos) nao tem acesso a
repositorio - passo que dependa disso e passo que nunca acontece, e a rodada se
perde. O doc fica **local** e a entrega e **mensagem no Chat ou formulario**.
Nada mais.

## Modo da sessao: time Aegro vs. cliente (ler primeiro)

Identifique quem esta compilando pelo **e-mail do usuario** no contexto da sessao:

- **Interno - `@aegro.com.br`** (EV de campo, time de Servicos, dev): gera o doc
  local e entrega pelo caminho da secao "Entrega no modo interno" - Chat primeiro,
  formulario como alternativa.
- **Externo - outro dominio** (cliente): monta o relatorio **no molde do
  formulario publico** (Email + Resumo + Descricao) e entrega o conteudo pronto
  para colar, com o link. Ver "Entrega no modo externo".

Sem e-mail identificavel, trate como **externo**.

## Quando usar / quando NAO usar

**Usar:**
- Ao fim de uma sessao de lancamento em que a skill de lancamento
  (`/aegro-entrada-nota-fiscal` e afins) registrou blocos `### erro` e o usuario
  aceitou compilar.
- Na rodada semanal de coleta do time (consolidar os diarios acumulados).
- Quando alguem relatar um problema recorrente fora de sessao.

**Nao usar:**
- Suporte a cliente final ou bug do app Aegro sem relacao com CLI/API publica -
  segue o fluxo normal de bug do produto.
- Durante o lancamento: registrar e responsabilidade da skill de lancamento;
  compilar no meio da sessao atrapalha quem opera.

## Fontes de dados

1. **Diarios de sessao**: `$AEGRO_LEARNING_DIR/journal-*.md` - blocos `### erro`
   (comando, resposta, impacto, workaround, sugestao).
2. **Telemetria do CLI**: `$AEGRO_TELEMETRY_DIR/*.jsonl` - needs_input, resolucoes
   ambiguas, timings, status de API. **Contrato**: os `.jsonl` nao devem conter
   identificadores brutos de cliente/fornecedor (nome, CPF/CNPJ, e-mail, keys de
   fazenda com nome). Se um registro trouxer, aplique redacao campo a campo
   (`cliente_a`, `00.000.000/0001-00`) **antes** de deduplicar ou de copiar
   qualquer trecho para o doc - nao confie que a fonte "ja veio anonimizada".
3. **Docs de aprendizado**: `$AEGRO_LEARNING_DIR/aprendizado-*.md`.
4. **Rodadas anteriores**: `$AEGRO_LEARNING_DIR/feedback-*.md` - unica base de
   comparacao disponivel para dedupe entre rodadas.
5. **Relato direto** na conversa (transformar em item estruturado).

Se alguma fonte nao existir no ambiente (comum no modo externo, sem diario/
telemetria), siga com as disponiveis e diga quais faltaram - nunca invente item
sem evidencia.

## Fluxo

### 1. Coletar e recortar

Leia as fontes do periodo (sessao atual ou semana). Cada bloco `### erro`, cada
padrao recorrente na telemetria e cada relato vira um item candidato.

### 2. Deduplicar por sintoma

Mesmo sintoma em sessoes diferentes = **um item so**, com contagem de ocorrencias
e fazendas afetadas (mascaradas: `cliente_a`, `cliente_b`). Frequencia e sinal de
prioridade - registre-a.

### 3. Classificar cada item

Duas dimensoes, sempre:

- **Status**: `resolvido` (fix ja existe - citar versao do CLI), `mapeado` (ja
  conhecido - citar a rodada anterior ou o gotcha da skill que descreve) ou
  `novo`.
- **Dono**: `CLI` (comando ou saida do `aegro`), `API` (plataforma / API publica),
  `skill` (instrucao da skill) - ou combinacao, indicando a ordem.

Antes de marcar `novo`, confira as rodadas anteriores em
`$AEGRO_LEARNING_DIR/feedback-*.md` e os gotchas das skills - item re-reportado
vira ocorrencia do item existente, nao duplicata.

Se nao houver rodada anterior no ambiente (maquina nova, `$AEGRO_LEARNING_DIR`
vazio), se a leitura do historico estiver incompleta ou indisponivel, ou se a
rodada anterior mais recente ja declarar `dedupe: parcial` no proprio
cabecalho, **declare `dedupe: parcial`** no cabecalho do doc: sem historico
completo e legivel nao da para afirmar que um item e `novo`, e a triagem
precisa saber disso para nao priorizar duplicata. Marque `dedupe: completo` so
quando todo o historico necessario foi lido por inteiro.

### 4. Evidenciar com seguranca

Cada item leva: comando executado (sem credenciais), resposta resumida, ambiente
(staging/prod), versao do CLI. **Nunca** credenciais; PII de cliente sempre
mascarada (nome -> `cliente_x`, CNPJ -> `00.000.000/0001-00`). Prefira
shape/agregado a dado bruto.

### 5. Gerar o doc de triagem

Salve sempre em `$AEGRO_LEARNING_DIR/feedback-AAAA-MM-DD-<tema>.md` - o doc local
e a fonte da entrega (mensagem no Chat ou campos do formulario) e o registro da
rodada para o dedupe da proxima. Antes de montar o caminho, sanitize `<tema>`:
normalize para um slug curto e seguro (letras, numeros, hifen), rejeite vazio,
`/`, `\` e `..` - o valor pode vir do relato da sessao e nao e confiavel como
esta. Se ja existir arquivo para o mesmo tema e data (segunda rodada no dia),
acrescente a hora (`feedback-AAAA-MM-DD-HHmm-<tema>.md`) em vez de sobrescrever
a rodada anterior. Se `$AEGRO_LEARNING_DIR` nao estiver definida, use
`./feedback-AAAA-MM-DD-<tema>.md` (diretorio atual) como fallback e registre no
doc que foi essa a pasta usada; se nem isso for possivel, nao siga em silencio -
diga explicitamente que a rodada nao foi persistida. Formato:

```markdown
# Feedback de campo - <tema> (AAAA-MM-DD)

> Fontes: N sessoes (DD/MM-DD/MM), M itens apos dedupe. dedupe: completo | parcial
> Entrega: pendente

## Itens

### 1. <sintoma em uma linha>
- status: novo | mapeado | resolvido
- dono: CLI | API | skill (ordem, se combinado)
- ocorrencias: N (cliente_a, cliente_b)
- evidencia: comando + resposta resumida + ambiente + versao
- impacto: <o que travou/atrasou/quase deu errado>
- sugestao: <a menor melhoria que elimina o sintoma>

## Resolvidos desde a ultima rodada
- <item> (CLI vX)
```

Feche o loop: itens `resolvido` desde a ultima rodada entram na secao curta
"Resolvidos desde a ultima rodada" - quem reporta precisa ver que funciona.

### 6. Entregar

Modo interno -> "Entrega no modo interno". Modo externo -> "Entrega no modo
externo". Depois de entregar, atualize a linha `> Entrega:` do doc
(`chat AAAA-MM-DD`, `formulario AAAA-MM-DD (N itens)` ou `pendente - <motivo>`).

## Entrega no modo interno (Chat primeiro, formulario como alternativa)

**Caminho 1 - mensagem no Google Chat (preferido).** Se a sessao tiver conector do
Google Chat disponivel:

1. **Localize a conversa**: busque a **DM com o dono da triagem do feedback do CLI**
   (hoje o Antonio Brasil, do time Agentes de Entrada) pelo nome. Se a busca nao
   achar ou vier ambigua, **pergunte** ao usuario qual conversa usar - nao chute.
2. **Nunca poste em espaco/canal** por conta propria. So DM, e so em espaco se o
   usuario pedir aquele espaco explicitamente.
3. **Monte as mensagens** (formato abaixo). Mensagem de Chat tem limite de tamanho:
   **nao concatene o doc inteiro numa mensagem** - ela chega truncada e a rodada
   volta a se perder. Cabecalho numa mensagem, **um item por mensagem**, todas na
   **mesma thread** (reuse a thread devolvida pela primeira mensagem; se nao vier,
   envie em sequencia com o prefixo `(i/N)`, que preserva a leitura).
4. **Confirme antes de enviar**: mostre o texto exato de todas as mensagens e envie
   somente com um "sim" explicito do usuario. Mensagem em nome de alguem nao sai
   sem confirmacao.
5. **Depois de enviar**, mostre o que foi enviado e atualize `> Entrega:` no doc.

Formato das mensagens (Chat aceita Markdown, mas **nao aceita tabela** - nada de
`|`):

```
*Feedback de campo - <tema>* (AAAA-MM-DD)
Fontes: N sessoes (DD/MM-DD/MM) | M itens apos dedupe | dedupe: completo|parcial
Doc completo: <caminho local do .md>
```

```
*(i/N) <sintoma em uma linha>*
status: novo | dono: CLI
ocorrencias: N (cliente_a, cliente_b)
impacto: <o que travou>
evidencia: `<comando>` -> <resposta resumida> | <ambiente> | CLI vX
sugestao: <a menor melhoria que elimina o sintoma>
```

Se um item sozinho ainda passar de ~3500 caracteres, resuma a evidencia na
mensagem e diga que o trecho completo esta no doc local, citando o caminho.

**Caminho 2 - formulario (sem conector, offline ou usuario preferiu).** Entregue no
molde do formulario **"Agentes de Entrada - Feedback uso do CLI"**:

`https://aegrodev.atlassian.net/jira/software/form/691a79c4-57d5-4224-a22c-02d5727cb896`

Campos: **Email** (obrigatorio), **Resumo** (obrigatorio), **Descricao**, anexo
opcional. **Um envio por item** - cada submissao cria uma issue. Mesmas regras de
`Resumo:` / `Descricao:` da secao do modo externo.

Nunca deixe a rodada em "pendente" silencioso: se nenhum caminho estiver
disponivel (sem conector e sem browser), diga o caminho do doc local e peca ao
usuario para mandar o arquivo no Chat do time, e marque
`> Entrega: pendente - <motivo>`.

## Entrega no modo externo (formulario)

O cliente **nao tem conta no Jira**, entao a skill deixa o envio a **um clique**:
monta o conteudo exatamente no molde e o cliente cola e clica Enviar.

**Formulario "Agentes de Entrada - Necessidade na CLI"** (publico, sem login):
`https://aegrodev.atlassian.net/jira/software/form/bf7148ca-5456-4fc7-b5a1-bf6cc7bc49ed`

Campos: **Email** (obrigatorio), **Resumo** (obrigatorio), **Descricao** (texto),
anexo opcional.

**O que a skill entrega, por item** (um envio por item):

- **Email:** pergunte o e-mail do cliente (para retorno). Ele vai como reporter -
  deixe claro que e o unico dado de contato que sai; nao inclua PII de terceiro.
- **Resumo:** o sintoma em uma linha, prefixado pelo tipo - `[FR]` para pedido de
  funcionalidade/falta na CLI, `[Bug]` para erro. Ex.: `[Bug] launch-bill 500 ao
  parcelar nota de fornecedor_x`.
- **Descricao:** o corpo estruturado do item (impacto, evidencia com comando +
  resposta resumida, ambiente, versao do CLI, sugestao) - **anonimizado**
  (fornecedor -> `fornecedor_x`, CNPJ -> `00.000.000/0001-00`), sem credenciais.

**Como apresentar:** mostre o link e, para cada item, um bloco copiavel com
`Resumo:` e `Descricao:` prontos. Instrua: abrir o link, colar os dois campos,
preencher o e-mail, clicar **Enviar**. Se houver varios itens, liste-os e deixe o
cliente escolher quais enviar.

## O formulario nao se envia sozinho

Os dois formularios sao protegidos por **reCAPTCHA** e nao tem endpoint publico de
submissao anonima: a Forms REST API da Atlassian so submete formulario **ja
anexado a uma issue existente** e exige autenticacao no Jira. Ou seja:

- **Nao tente automatizar o envio** - nem POST direto, nem preencher o formulario
  por browser. O reCAPTCHA existe para barrar exatamente isso, e quem resolve
  captcha e a pessoa.
- O caminho **automatico** do modo interno e o **Chat**. O formulario e sempre
  "conteudo pronto para a pessoa colar e enviar".

## Principios

- **Evidencia > opiniao**: item sem comando/resposta reproduzivel e hipotese -
  entra marcado como tal, no fim do doc.
- **Um item = um sintoma com dono.** Item "guarda-chuva" nao gera acao.
- **Frequencia prioriza**: 1 ocorrencia interessa; 5 ocorrencias mandam.
- **Entrega confirmada > entrega automatica**: mostre o texto e espere o "sim".
- **Fechar o loop motiva o campo**: reporte de volta o que foi resolvido.
- **Seguranca primeiro**: nada de credenciais; PII mascarada; conteudo interno -
  so Chat interno ou formulario da Aegro, nenhum outro canal (e-mail externo,
  upload em servico de terceiro, link publico).

## Failure modes - quando escalar

- Item aponta **perda ou corrupcao de dado de cliente em prod** (ex.: valor
  gravado errado) -> nao espere a rodada semanal: escale imediatamente pelo Chat
  com o doc parcial.
- Divergencia entre telemetria e diario -> registre as duas versoes e marque para
  investigacao, nao escolha uma.
- Volume grande demais (>30 itens novos) -> agrupe por modulo e proponha priorizar
  com o time antes de detalhar tudo, para nao virar uma enxurrada de mensagens.
- Sem `$AEGRO_LEARNING_DIR` no ambiente -> use o fallback
  `./feedback-AAAA-MM-DD-<tema>.md`, compile so com o relato da conversa,
  declare `dedupe: parcial` e siga; nao aborte a rodada.

## Comandos de referencia

| Objetivo | Comando |
|---|---|
| Listar diarios do periodo | `ls $AEGRO_LEARNING_DIR/journal-*.md` |
| Blocos de erro dos diarios (bloco inteiro, ate o proximo heading - nao trunque com `grep -A N`) | `awk '/^### /{p=/^### erro/} p' $AEGRO_LEARNING_DIR/journal-*.md` |
| Telemetria da semana | `ls $AEGRO_TELEMETRY_DIR/*.jsonl` |
| Rodadas anteriores (para dedupe) | `ls $AEGRO_LEARNING_DIR/feedback-*.md` |
| Versao do CLI (para a evidencia) | `aegro --version` |
