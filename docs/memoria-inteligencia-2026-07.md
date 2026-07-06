# Memória: camada de inteligência Aegro (CLI × skills × agente)

> Consolidação das decisões, arquitetura e aprendizados das sessões de
> 2026-06-25 a 2026-07-02 (Antônio + Claude). Escrito para quem for **editar as
> skills** — este doc é o contexto que as skills devem refletir.
> Fontes detalhadas vivem no repo `aegro/tool-aegro-cli` (seção 8).

---

## 1. Arquitetura de 3 camadas (a decisão-mãe)

| Camada | Papel | Natureza |
|---|---|---|
| **CLI** (`tool-aegro-cli`) | as *mãos* — resolve nome→chave, infere, valida, preview, executa, instrumenta | determinístico, testável, **sem LLM** |
| **Skill** (este repo) | o *manual/SOP* — como lançar certo, disciplina de confirmação, staging-first, vocabulário, gotchas de domínio | markdown, iterável por não-eng |
| **Agente** (Claude/Cowork) | o *cérebro no momento* — lê input cru, escolhe skill, conversa, desambigua, pergunta o mínimo | não-determinístico (e tudo bem) |

**Regra de fronteira (teste de 1 pergunta):**
- Comportamento idêntico toda vez? → **CLI**
- Eu escreveria num SOP pra treinar um EV novo? → **skill**
- Exige entender o que o humano quis dizer? → **agente**

**A costura é o contrato `needs_input`**: o CLI resolve/infere/valida e devolve
um envelope estruturado (`status`, `resolved`, `inferred`, `missing` com "why",
`ambiguous` com candidatos, `preview` com NOMES). O agente pergunta **só** o que
está em missing/ambiguous. Skill nunca deve mandar o agente "adivinhar" chave —
sempre nomes + `--complete` para conferir antes de executar.

**Anti-padrão declarado:** não embutir LLM dentro do CLI. O CLI fica
inteligente sendo uma *ferramenta* melhor, não um chatbot.

## 2. O dial de confirmação (estratégia de produto)

Dois objetivos que parecem opostos são o mesmo projeto:
- **Agora**: assistente para EVs que confirma MUITO (tabela de conferência,
  staging-first, preview) — EVs toleram erro e dão feedback rápido.
- **Depois**: agente que lança para o cliente "sem perguntar quase nada".

A ponte: **cada confirmação do EV é dado rotulado**. A telemetria mede o acerto
por campo/operação; quando um campo acerta consistentemente, aquela pergunta é
desligada. O assistente de EV é a **fábrica de dados** do agente autônomo.
Confiança se ganha do dado, não se decide no chute.

Feedback automático (sem o EV pedir): telemetria sempre-ligada no CLI
(`AEGRO_TELEMETRY_DIR`, JSONL anonimizado, nunca credenciais) + diário de sessão
(responsabilidade da skill) + hook de fim de sessão que consolida o doc de
aprendizado. Coleta semanal manual pelo time. Ver
`tool-aegro-cli/docs/ev-cowork/`.

## 3. O que o CLI (aegro 0.10.0, PyPI) já faz — e as skills devem usar

- **Multi-ambiente**: `--env staging|prod` / `AEGRO_ENV` (staging =
  `app.staging.aegro.io`, MESMA credencial de prod; credenciais por bucket).
  Comandos "bare" honram `AEGRO_ENV` (fix #49). **Staging é uso interno** —
  regra de skill: usar primeiro, NUNCA sugerir a cliente.
- **Resolução nome→chave**: `--company`, `--category`, `--bank-account`,
  `--apportion-crop`, e `product` nos itens de pedido. Server-side (searchText):
  company, fin_category, bank_account. Client-side (paginar+token): element,
  crop, assets. Ambíguo/não-encontrado → `needs_input` com candidatos — nunca
  chuta, **nunca cria cadastro sozinho**.
- **`--complete`**: resolve+infere+reporta sem executar (modo agente).
  `--dry-run`: preview humano com nomes. `AEGRO_SAFE_MODE`/`--execute` seguem.
- **Batch name-based**: `financial create-bills --batch` e `purchase-orders
  create-batch --from-file` → tabela de conferência por linha; promoção
  staging→prod = mesmo arquivo trocando `--env` (chaves re-resolvidas).
- **Inferência**: farmKey da credencial, data=hoje (America/Sao_Paulo).
- **Escrita segura** (0.10.0): sem retry em POST (a API tem "500 cosmético" que
  persiste antes de falhar — retry duplicava), `origin: MANUALLY` automático
  (evita bill fantasma), bloqueio de bill em moeda estrangeira, discounts de PO
  defaultados, avisos USD em pedidos.
- **Apropriação**: `--apportion-crop "Safra X"` (repetível) → `financialApportion
  CROP_PRORATE`; múltiplas safras = rateio automático proporcional à área.

## 4. Gotchas de domínio/API que as skills PRECISAM ensinar (validados)

1. **Apropriação tem 2 tipos**: **direta** (1+ safras; sem percentual; multi-safra
   rateia por área automaticamente) e **salva** (`cropProrateGroup`, percentuais
   pré-definidos, ex. "Administrativo" 50/50). Via API: direta ✅; salva é
   **somente-leitura** (não aplica em bill, não cria grupo). `cropProrateGroupKey`
   na raiz do bill é aceito e IGNORADO.
2. **Pedido de compra em USD**: a API armazena como recebido e o app **divide
   pela cotação** ao exibir → enviar valores **JÁ CONVERTIDOS em BRL** +
   `currencyCode USD` + `currencyExchangeRate`. USD bruto corrompe (US$4,85 →
   US$0,94; incidente SOMA 01/07).
3. **Bill em moeda estrangeira NÃO existe via API**: currencyCode coagido p/ BRL
   e `currencyConversion` ignorado na escrita (validado staging 02/07). CLI
   bloqueia; alternativa = lançar convertido em BRL ou usar o app.
4. **Parcelas não têm CRUD avulso** (só filter/realizeList/GET): nascem no
   `create-bill` (campo `installments`), pagas via `realize` (irreversível —
   sem unrealize). A skill financeiro antiga ensinava comandos INEXISTENTES
   (create/update/delete-installment) — corrigido.
5. **Dinheiro**: `MoneyPublicResource {"currencyCode","amount"}` unificado na
   spec atual. PO é diferente (campos na raiz, números nos itens).
6. **fiscalNumber obrigatório** em companies (objeto {code, fiscalNumberType,
   countryCode}).
7. **Busca de empresa tem falso-negativo** (caso SUMITOMO): antes de cadastrar
   "novo" fornecedor, listar sem filtro / confirmar com humano. Não criar
   fornecedor por CNPJ de filial — unificar (regra da EV).
8. **Backend exige discounts em PO** (pedido + itens; não documentado; o 400
   culpa o campo errado) — CLI defaulta 0.
9. **Staging ≠ prod hoje**: elements/stock/realization filters com 500
   persistente só no staging — resolução de produto por nome indisponível lá.

## 5. Estado das skills (este repo)

Branch **`feat/skills-insercao-inteligente-contas`** (commits locais, push
liberado agora):
- `aegro-financeiro`: +4.1.1 (create-bill inteligente/needs_input), 4.5
  reescrita (PO por nome, USD, create-batch), **remoção do CRUD de parcela
  inexistente**, apropriação salva×direta (regra 6), gotchas de moeda
  (unificado + bill estrangeira bloqueada), anti-padrões atualizados.
- `aegro-lancamento-financeiro`: "Caminho Rápido: create-bill inteligente"
  (nomes + staging-first + --complete antes de executar).

**Rascunho da skill do EV** (a promover para skills-internal):
`tool-aegro-cli/docs/ev-cowork/skill-aeg-ev-lancamento-contas.md` — SOP completo
(confirmar intenção, tabela, staging→conferir→prod, diário de sessão).
Split de repos: `aegro/skills` = público; `aegro/skills-internal` = harness
interno EV; `pmdusso/aegro-skills` = legado, não publicar.

## 6. Backlog priorizado (para as próximas threads de skill)

1. **P0 adiado — playbook por cliente** ("memória de regras"): arquivo por
   fazenda que o agente lê no início e ATUALIZA quando o EV ensina uma regra
   ("decidiu 1x → nunca mais pergunta"). Regras típicas: conta bancária por tipo
   de pagamento (à vista×cartão×cooperativo), vencimento de cartão (dia 10, não
   o default), rateio por safra em transição, fornecedor canônico, agrupador=
   tags, data "gerado" vs "criado", moeda. Design em
   `tool-aegro-cli/docs/feedback/2026-06-29-duda-operacao.md`.
2. **Clarificar CLI × API nas skills** (feedback do cliente João: a skill dele
   "poluiu" sem saber quando usar cada um). Padrão: CLI-first; API direta só
   onde o CLI não cobre.
3. Incorporar as **skills do próprio João** quando ele enviar (prometido).
4. Guard de duplicidade antes de lançar (nota reenviada via WhatsApp) — P1.
5. Anexos de documentos ao registro: API não suporta write de `files` — skill
   orienta anexo manual pós-lançamento.

## 7. Método de trabalho que funcionou (para manter)

- Feedback de campo → doc de triagem em `docs/feedback/` (resolvido / mapeado /
  novo, com dono CLI×API×skill) → fixes + encaminhamento.
- **Validar em staging antes de release** (a mesma credencial funciona nos 2).
- Babysit de PR + release automatizada por tag (`vX.Y.Z` → PyPI).
- Toda fórmula/validação determinística desce da skill para o CLI; a skill
  encolhe para julgamento + procedimento.

## 8. Fontes (repo `tool-aegro-cli`)

- `docs/design-inteligencia-insercao.md` — o design da camada de inserção.
- `docs/feedback/2026-06-29-duda-operacao.md` — sessão EV (priorizada).
- `docs/feedback/2026-07-01-pedidos-usd-soma.md` — incidente USD.
- `docs/feedback/2026-07-02-relatorio-cliente-api.md` — triagem do relatório do
  cliente integrador (+status C1–C9).
- `docs/reports/2026-07-02-auditoria-swagger.md` — auditoria spec×CLI×docs +
  validação em staging.
- `docs/melhorias-api-publica.md` — itens 1–17 encaminhados à plataforma.
- `docs/ev-cowork/` — provisionamento do assistente de EV + skill draft.
- Releases: 0.8.0 (multi-env + contas), 0.9.0 (nomes em PO + fix AEGRO_ENV),
  0.10.0 (escrita segura + apropriação + bloqueios USD).
