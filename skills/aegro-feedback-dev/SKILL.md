---
name: aegro-feedback-dev
description: >-
  Fecha a sessao de trabalho na CLI `aegro` reportando ao time de dev o que nao
  saiu como o usuario queria: parte do resultado esperado, percorre o caminho
  tentado e por que, o que deu errado, as voltas que o agente deu e o desfecho
  de cada uma, e entrega por mensagem no Google Chat (time Aegro) ou no molde do
  formulario publico (cliente), com PII mascarada e sem credenciais. A fonte e a
  propria sessao - o que foi pedido e o que o agente executou. Use quando o
  usuario pedir "manda isso pro time", "reporta esse erro", "isso nao
  funcionou, avisa o pessoal", "compila o feedback da sessao"; EN "report this
  to the dev team", "send session feedback". Use tambem por conta propria, sem
  esperar o pedido, quando um comando `aegro` falhar e nem o caminho documentado
  nem as voltas tentadas entregarem o resultado: registre o item na hora,
  enquanto o contexto existe, e ofereca o envio ao fim. NAO use para suporte a
  cliente final nem para bug do app Aegro fora do fluxo CLI/API (segue o fluxo
  normal de bug), e nao use no lugar de resolver: primeiro entregue o resultado
  ao usuario, depois reporte.
---

# Feedback da sessao -> time de dev

O usuario tentou fazer alguma coisa no Aegro pela CLI e nao conseguiu, ou
conseguiu por uma volta. Esta skill transforma essa sessao em um item que o time
de dev consegue agir: o que tinha de sair, o que voce tentou, o que quebrou, as
voltas e o desfecho de cada uma.

Voce estava la. **Nao va procurar o erro em arquivo** - a sessao e a fonte, e e a
unica que tem o *por que* de cada escolha.

## Regra dura: sem git, sem repositorio

Esta skill **nao usa git**, nao roda `gh`, nao abre issue nem PR e nao escreve em
repositorio nenhum. Quem opera (EV de campo, time de Servicos, cliente) nao tem
acesso a repositorio - passo que dependa disso e passo que nunca acontece. O doc
fica **local** e a entrega e **mensagem no Chat ou formulario**. Nada mais.

## Quando usar

**Gatilho 1 - o usuario pede.** No fim da sessao, ou logo depois de algo falhar:
"manda isso pro time", "reporta esse erro". Compile o que atritou na sessao.

**Gatilho 2 - voce chega aqui sozinho.** Um comando `aegro` falhou, voce tentou
as voltas que sabia e o resultado pedido nao saiu - ou so saiu por fora, na mao,
no app. Carregue esta skill **no momento em que isso fica claro**, enquanto o
contexto esta inteiro.

**Registre na hora, entregue no fim.** O trabalho do usuario vem antes do
relatorio: termine o que da para terminar (ou desista junto com ele) e so entao
mostre o item e ofereca o envio. Carregar a skill nao autoriza parar a tarefa
para escrever documento. Excecao unica: **dado de cliente gravado errado em
producao** - escale na hora, com o que tiver.

**Nao reporte** quando o tropeco foi seu e nao custou nada ao usuario: erro que
voce corrigiu na sequencia, comando que funcionou na segunda tentativa depois de
ler o `--help`. Vira item quando custou retrabalho, tempo ou o resultado, **ou**
quando voce so achou o caminho certo por tentativa e erro - isso e lacuna de
instrucao, e e exatamente o que o dono da skill precisa saber.

**Nao use** para suporte a cliente final, para bug do app Aegro sem relacao com
CLI/API publica (fluxo normal de bug), nem no meio do lancamento como desculpa
para nao tentar a proxima volta.

## Modo da sessao: time Aegro vs. cliente (ler primeiro)

Identifique quem esta na sessao pelo **e-mail do usuario** no contexto:

- **Interno - `@aegro.com.br`**: doc local + entrega pelo Chat, formulario como
  alternativa. Ver "Entrega no modo interno".
- **Externo - outro dominio** (cliente): relatorio **no molde do formulario
  publico** (Email + Resumo + Descricao), pronto para colar. Ver "Entrega no modo
  externo".

Sem e-mail identificavel, trate como **externo**.

## Sequencia de passos

### 1. Reconstituir o item a partir da sessao

Cada parte tem fonte direta na conversa, nesta ordem - ela e o formato, nao uma
sugestao de redacao:

1. **Resultado esperado** - o que o usuario pediu, em termos de negocio: "a nota
   do fornecedor_x lancada, com as 3 parcelas a prazo nas datas do boleto". Se o
   pedido foi vago, **pergunte agora**, antes de fechar a sessao: "o que tinha de
   estar no Aegro no fim?". Uma pergunta, nao um formulario.
2. **Caminho tentado e por que** - o comando que voce rodou e o que te levou ate
   ele: a instrucao da skill, um campo da nota, a saida do comando anterior. O
   *por que* e a parte que so voce tem; sem ele o dev nao consegue julgar se a
   instrucao induziu ao erro.
3. **O que deu errado** - resposta e efeito observado, com ambiente e versao.
4. **Contornos** - cada volta depois da falha, **com o desfecho de cada uma**:
   funcionou, pela metade, nao funcionou. Inclua as que nao funcionaram: e o que
   impede o proximo agente de repetir o mesmo caminho.
5. **Desfecho** - o resultado saiu? Por qual volta, e a que custo (tempo,
   lancamento manual no app). "Nao saiu" tambem e desfecho.
6. **Diagnostico** - hipotese do que aconteceu, **dita como hipotese**. Sem
   hipotese, escreva `sem hipotese`: hipotese inventada custa mais caro que
   nenhuma, porque a triagem passa a investigar a hipotese em vez do sintoma.

Comecar pelo erro inverte a leitura: o dev recebe um payload recusado sem saber o
que a pessoa queria lancar, e nao tem como julgar se a recusa estava certa.

### 2. Relatar a sua propria conduta sem maquiar

Metade da sessao foi voce, e o relato e sobre a sessao inteira. Duas regras:

- **Nao promova erro seu a bug da plataforma.** Se voce inventou um campo, errou
  a flag ou chamou o comando de outro fluxo, o item diz isso com todas as letras.
  A recusa da API estava certa; o que falhou foi a instrucao que te deixou
  escolher errado. Mandado como bug de API, o item volta fechado como "funciona
  como esperado" e a instrucao ambigua fica de pe.
- **Nao esconda as voltas erradas.** Elas parecem constrangedoras e sao o dado
  mais util do doc: todo caminho errado que pareceu razoavel na hora e uma linha
  que falta em alguma skill.

### 3. Decidir de quem e o problema

A pergunta que define o dono: **existia caminho certo?**

- **Nao existia** - o caminho documentado e exatamente o que falhou: dono `CLI`
  (comando ou saida do `aegro`) ou `API` (plataforma / API publica).
- **Existia e voce nao pegou** - dono `skill`: o item descreve o que faltou na
  instrucao para fechar o caminho errado.
- **Nao da para saber** - `dono: a investigar`, dizendo o que falta para decidir.
  E resposta legitima; chutar `API` nao e.

Combinacao vale, indicando a ordem (ex.: `skill, depois API`).

### 4. Juntar o repetido

Mesmo sintoma varias vezes na sessao = **um item**, com `ocorrencias: N`. Se o
mesmo sintoma bloqueou resultados esperados diferentes, mantenha um item so e
liste os resultados esperados - e essa lista que mostra o alcance do fix.
Sintomas iguais com donos diferentes sao **dois itens**: a correcao nao e a
mesma.

Se ja houver doc de sessao anterior nesta maquina com o mesmo sintoma, nao cale
nem reescreva a historia toda: acrescente `ja reportado em <arquivo>` no item.
Repeticao e sinal de prioridade.

### 5. Limpar a evidencia

A evidencia mora dentro do caminho tentado, do que deu errado e de cada contorno
- cada um leva o comando executado e a resposta resumida; o item leva ambiente
(staging/prod) e versao do CLI uma vez. Contorno sem comando nao e
reaproveitavel por quem ler.

**Nunca** credenciais, nem mascaradas. PII de cliente sempre trocada (nome ->
`cliente_x`, fornecedor -> `fornecedor_x`, CNPJ -> `00.000.000/0001-00`).
Prefira shape e agregado a dado bruto. No modo externo, mascare tambem dado
comercial sensivel que nao seja PII (preco negociado, config interna, numero
financeiro do cliente) antes de montar Resumo/Descricao - a confirmacao manual
nao substitui essa limpeza.

### 6. Escrever o doc da sessao

Salve em `$AEGRO_LEARNING_DIR/feedback-AAAA-MM-DD-<tema>.md` - o doc e a fonte da
entrega e o registro para a proxima sessao. Sanitize `<tema>` antes de montar o
caminho: slug curto (letras, numeros, hifen), rejeitando vazio, barra, contrabarra
e `..` - o valor sai do relato e nao e confiavel como esta. Se ja existir arquivo
do mesmo tema e dia, acrescente a hora (`feedback-AAAA-MM-DD-HHmm-<tema>.md`) em
vez de sobrescrever. Grave com criacao exclusiva (falha se o nome ja existir,
nunca substitui o arquivo); em colisao mesmo com a hora, acrescente um sufixo
curto extra e tente de novo, sem repetir o nome que colidiu. Sem
`$AEGRO_LEARNING_DIR` definida, use o diretorio atual e
registre no doc que foi essa a pasta; se nem isso for possivel, diga que o
registro nao foi persistido - nunca siga em silencio.

```markdown
# Feedback da sessao - <tema> (AAAA-MM-DD)

> Sessao encerrada <HH:MM> BRT | CLI vX | staging|prod | N itens
> Entrega: pendente

## 1. <o resultado esperado que nao saiu, em uma linha>
- resultado esperado: <o que tinha de existir no Aegro no fim>
- caminho tentado: `<comando>` - escolhido porque <o que levou ate ele>
- o que deu errado: <resposta e efeito observado>
- contornos:
  1. `<comando>` -> <o que aconteceu> - funcionou | pela metade | nao funcionou
  2. ...
- desfecho: saiu pelo contorno N (custo: <tempo/retrabalho>) | so no app, fora do
  CLI | nao saiu
- diagnostico: <hipotese, dita como hipotese> | sem hipotese
- dono: CLI | API | skill | a investigar
- ocorrencias: N na sessao | ja reportado em <arquivo>
- sugestao: <a menor melhoria que entrega o resultado esperado pelo caminho certo>
```

### 7. Entregar

Mostre o item ao usuario antes de qualquer envio. Modo interno -> "Entrega no
modo interno"; modo externo -> "Entrega no modo externo". Depois, atualize a
linha `> Entrega:` (`chat AAAA-MM-DD`, `formulario AAAA-MM-DD (N itens)` ou
`pendente - <motivo>`).

## Entrega no modo interno (Chat primeiro, formulario como alternativa)

**Caminho 1 - Google Chat (preferido).** Com conector do Chat disponivel:

1. **Localize a conversa**: a **DM com o dono da triagem do feedback do CLI**
   (hoje o Antonio Brasil, do time Agentes de Entrada), pelo nome. Busca vazia ou
   ambigua -> **pergunte** qual conversa usar, nao chute.
2. **Nunca poste em espaco/canal** por conta propria - so DM, e so em espaco se o
   usuario pedir aquele espaco.
3. **Monte as mensagens** (formato abaixo): cabecalho numa mensagem, **um item
   por mensagem**, todas na **mesma thread** (reuse a thread devolvida pela
   primeira). Nao concatene tudo numa mensagem - chega truncada. Se o conector
   nao devolver thread reutilizavel, caia para o Caminho 2: mensagens soltas se
   espalham e a leitura fragmenta.
4. **Confirme antes de enviar**: mostre o texto exato e envie so com um "sim"
   explicito. Mensagem em nome de alguem nao sai sem confirmacao.
5. **Se o envio falhar no meio**, marque `> Entrega: pendente - envio parcial
   (itens enviados: <lista>)` **antes** de tentar de novo; a proxima tentativa
   manda so o que falta.

Chat aceita Markdown, mas **nao aceita tabela**:

```text
*Feedback da sessao - <tema>* (AAAA-MM-DD)
N itens | CLI vX | <ambiente>
Doc completo: <caminho local do .md>
```

```text
*(i/N) <o resultado esperado que nao saiu>*
esperado: <o que tinha de existir no Aegro no fim>
tentado: `<comando>` porque <o que levou ate ele>
deu errado: <resposta resumida>
contornos: 1) `<comando>` -> funcionou | 2) `<comando>` -> nao funcionou
desfecho: <saiu por qual volta e a que custo, ou nao saiu>
diagnostico: <hipotese> | sem hipotese
dono: CLI | ocorrencias: N
sugestao: <a menor melhoria que entrega o esperado pelo caminho certo>
```

Item acima de ~3500 caracteres: corte pelos contornos que nao funcionaram -
esperado, desfecho e o contorno que funcionou ficam sempre - e cite o caminho do
doc local.

**Caminho 2 - formulario** (sem conector, offline ou preferencia do usuario).
Formulario **"Agentes de Entrada - Feedback uso do CLI"**:

`https://aegrodev.atlassian.net/jira/software/form/691a79c4-57d5-4224-a22c-02d5727cb896`

Campos: **Email** (obrigatorio), **Resumo** (obrigatorio), **Descricao**, anexo
opcional. **Um envio por item**. Mesmas regras de `Resumo:` / `Descricao:` do
modo externo.

Nunca deixe a sessao em "pendente" silencioso: sem nenhum caminho disponivel,
diga o caminho do doc local, peca ao usuario para mandar o arquivo no Chat do
time e marque `> Entrega: pendente - <motivo>`.

## Entrega no modo externo (formulario)

O cliente **nao tem conta no Jira**: deixe o envio a **um clique**, com o
conteudo pronto para colar.

**Formulario "Agentes de Entrada - Necessidade na CLI"** (publico, sem login):
`https://aegrodev.atlassian.net/jira/software/form/bf7148ca-5456-4fc7-b5a1-bf6cc7bc49ed`

Por item (um envio por item):

- **Email:** pergunte o e-mail do cliente (vai como reporter). Diga que e o unico
  dado de contato que sai; nada de PII de terceiro.
- **Resumo:** o **resultado esperado que nao saiu**, em uma linha, prefixado pelo
  tipo - `[FR]` para falta na CLI, `[Bug]` para erro. Ex.: `[Bug] Nao consigo
  lancar nota de fornecedor_x com parcelas a prazo`. **Nao use a mensagem de erro
  como resumo**: ela descreve a tentativa, nao o que ficou faltando.
- **Descricao:** a sequencia do passo 1 (esperado, caminho tentado e por que, o
  que deu errado, contornos com desfecho, desfecho, diagnostico, sugestao), com
  comando, resposta resumida, ambiente e versao - anonimizada, sem credenciais.

Apresente o link e, por item, um bloco copiavel com `Resumo:` e `Descricao:`.
Com varios itens, liste e deixe o cliente escolher quais enviar.

## O formulario nao se envia sozinho

Os dois formularios tem **reCAPTCHA** e nao tem endpoint publico de submissao
anonima: a Forms REST API da Atlassian so submete formulario **ja anexado a uma
issue existente** e exige autenticacao no Jira.

- **Nao tente automatizar o envio** - nem POST direto, nem preencher por browser.
  O reCAPTCHA existe para barrar exatamente isso.
- O caminho automatico do modo interno e o **Chat**; o formulario e sempre
  conteudo pronto para a pessoa colar e enviar.

## Anti-padroes

- **Parar a tarefa para escrever o relatorio.** Registre, termine o trabalho,
  reporte no fim.
- **Reportar todo 4xx.** Erro que voce causou e corrigiu sem custo nao e item.
- **Mandar a mensagem de erro como titulo.** O dev fica sem saber o que deveria
  ter ficado pronto.
- **Item guarda-chuva** ("a CLI esta instavel") - nao gera acao.
- **Hipotese inventada** para o campo diagnostico nao ficar vazio.
- **Reportar como bug o que a skill ja avisava** e voce nao leu: leia o aviso e
  siga. Se o aviso existia mas era ambiguo, ai sim e item de `skill`.

## Limitacoes

- Sem git, sem `gh`, sem issue, sem PR. Doc local + Chat ou formulario.
- O formulario nao se envia sozinho; quem clica e a pessoa.
- A sessao e a unica fonte com o *por que* de cada escolha. Se a conversa foi
  compactada e voce nao recupera o motivo de um caminho, escreva `motivo da
  escolha nao recuperado` em vez de racionalizar depois do fato.
- Diario (`$AEGRO_LEARNING_DIR/journal-*.md`) e telemetria
  (`$AEGRO_TELEMETRY_DIR/*.jsonl`), quando existirem, servem para conferir
  comando e resposta exatos - nunca como substituto do relato da sessao, e
  sempre passando pela limpeza do passo 5.

## Validacoes e erros comuns

- **Dado de cliente gravado errado em producao** -> nao espere o fim da sessao:
  escale na hora pelo Chat, com o item parcial.
- **Mais de 5 itens numa sessao** -> algo maior quebrou. Agrupe por fluxo e mande
  o panorama primeiro; detalhe depois do time olhar.
- **O usuario nao sabe dizer o que esperava** (assumiu a tarefa no meio) -> nao
  promova o erro a bug: registre com `resultado esperado: nao reconstituido` e
  diga que falta isso.
- **Usuario recusa o envio** -> guarde o doc, diga o caminho e pare. Nao mande
  mesmo assim.

## Referencia de comandos

| Objetivo | Comando |
|---|---|
| Versao do CLI (para a evidencia) | `aegro --version` |
| Docs de sessoes anteriores nesta maquina | `ls $AEGRO_LEARNING_DIR/feedback-*.md` |
| Ver se o sintoma ja foi reportado | `grep -il "<sintoma>" $AEGRO_LEARNING_DIR/feedback-*.md` |
| Diario da sessao (complemento) | `ls $AEGRO_LEARNING_DIR/journal-*.md` |
