# A tela de triagem — como montar, abrir e ler de volta

A tela e um **arquivo HTML local**. Nao publique, nao hospede, nao mande para
servico externo: ela contem descricao de lancamento, fornecedor e valor de um
cliente real.

---

## 1. Montar

### 1.1 Junte o dado

```js
{
  "meta":      { ...conteudo de <plano>.jsonl.meta.json... },
  "grupos":    [ ...o campo `grupos` do stdout do `plan`... ],
  "clusters":  [ ...o campo `clusters` de <plano>.jsonl.unresolved.json... ],
  "categorias": [ {"key": "financialCategory::...", "nome": "Energia Eletrica",
                   "codigo": "3.1.2"} ],
  "nomes":     { "financialCategory::velha": "Energia (antigo)",
                 "company::c1": "CPFL PAULISTA",
                 "element::e9": "Diesel S10" },
  "planoArquivo": "plano-salarios.jsonl"
}
```

- **`meta`** agora traz `farmKey` (chave da fazenda) e `sourcesWithoutRule`. O
  `farmKey` e o que permite o **link direto para cada conta** — o pedido n.1 de
  quem decide, porque sem ele decidir exige sair da tela. As amostras da cauda
  trazem `inputsCount`: quantos itens a conta tem (nao quais).
- **`categorias`** e o catalogo **para a EV escolher destino**. Monte com
  `aegro fin-categories list --farm "<fazenda>" --status ACTIVE --page N -o json`,
  paginando ate acabar (50 por pagina). O nome esta em `description` (com
  fallback `name`). **Descarte `type: "SYNTHETIC"`** — sintetica e agrupadora e
  nao e lancavel; oferece-la seria oferecer uma falha garantida.
- **`nomes`** e so para **exibir**, e cobre chave que nao esta em `categorias`.
  **Fornecedor e insumo ja vem prontos do CLI**: o `unresolved.json` traz um
  bloco `labels` com `{"companies": {...}, "elements": {...}}`. Copie os dois
  para dentro de `nomes` e pronto.

  Falta so a **categoria de origem**, que e ARQUIVADA e por isso nao aparece no
  `fin-categories list --status ACTIVE`:

  ```bash
  aegro fin-categories list --farm "<fazenda>" --status ARCHIVED --page N -o json
  ```

  Chave que nao estiver em `nomes` a tela exibe crua — **e isso e o certo**.
  Nunca invente nome para uma chave que nao resolveu.

  *Se o CLI for anterior a `--labels`* (SKILL.md 1.1), voce resolve fornecedor e
  insumo. **Um `get` por chave CITADA na cauda**, e nao a listagem do catalogo:
  parece a recomendacao errada e nao e. Medido em campo: a cauda citava **116
  chaves**, enquanto `companies list` paginado (2.254 fornecedores) somado a
  `elements list` **estourou o teto de 10 minutos sem terminar**. Rotulo faltando
  atrasa uma decisao; varredura de catalogo atrasa a sessao inteira.

  Vale o esforco: um cartao que diz "CPFL PAULISTA" e decidivel; um que diz
  `company::64a0f1...` obriga a EV a sair da tela para descobrir de quem e.
- **`grupos`** e o agregado que o `plan` imprimiu (campos `status`, `fromKeys`,
  `toKey`, `ruleIndex`, `why`, `reason`, `bills`, `totalAmount`). Se voce nao
  guardou o stdout, rode o `plan` de novo — e deterministico e nao escreve nada.
  O painel de aprovacao deriva os bloqueados desses grupos, mas o **numero
  autoritativo** por motivo esta em `meta.blockedByReason` (com o total em
  `meta.blockedTotal`): se os dois divergirem, acredite no meta.
- Voce **pode** acrescentar a um cluster um campo `sugestaoAssistente`:
  `{"toKey": "...", "evidence": "descricao diz 'CPFL', que e concessionaria de energia"}`.
  A tela renderiza como opcao propria, rotulada, e **nunca** pre-marcada.

### 1.2 Substitua no template

Serialize o objeto acima e troque `__DADOS_JSON__` (secao 3) por ele.
**Escape `<` como `<` na string JSON** antes de substituir — descricao de
lancamento e texto de cliente, e um `</script>` acidental quebraria a pagina.

Escreva o resultado ao lado do plano, ex.
`triagem-plano-salarios.html`, e abra:

```bash
start triagem-plano-salarios.html     # Windows
open  triagem-plano-salarios.html     # macOS
xdg-open triagem-plano-salarios.html  # Linux
```

---

## 2. Ler de volta

A EV revisa o painel de aprovacao, marca a caixa "revisei", decide os clusters e
clica **Baixar decisoes**. O arquivo cai na pasta de downloads dela como
`decisoes-<plano>.json`:

```json
{
  "version": 1,
  "plano": "plano-salarios.jsonl",
  "planHash": "sha256:9f2c...",
  "farm": "FAZENDAS RAIZES AGRO",
  "revisouAgregado": true,
  "decisoes": [
    {"cluster": "company::c1|pagto energia eletrica cpfl",
     "by": "company+fingerprint",
     "acao": "migrar",
     "toKey": "financialCategory::nova",
     "toNome": "Energia Eletrica",
     "origem": "sugestao",
     "sugestaoSource": "precedent",
     "fromKeys": ["financialCategory::velha"],
     "companyKey": "company::c1",
     "fingerprint": "pagto energia eletrica cpfl",
     "elementKeys": [],
     "count": 137,
     "why": ""},
    {"cluster": "__sem-sinal__", "by": "none", "acao": "manual",
     "toKey": null, "toNome": null, "origem": "escolha-manual",
     "sugestaoSource": null, "fromKeys": ["financialCategory::velha"],
     "companyKey": null, "fingerprint": "", "elementKeys": [],
     "count": 9, "why": "",
     "billKeys": ["bill::z0", "bill::z1"]}
  ]
}
```

`acao` e `migrar` | `manual` | `adiar` (`adiar` nao aparece no arquivo — some).
`origem` e `sugestao` | `sugestao-assistente` | `escolha-manual`.

**`manual` substituiu `manter`, e a troca nao e cosmetica.** "Manter na categoria
antiga" descrevia o efeito tecnico (nao mexer) e escondia a intencao real, que em
campo era quase sempre *"essa eu resolvo na mao"*. E a justificativa, que era
obrigatoria, so produzia texto inventado para poder seguir. Agora a observacao e
opcional e essas contas saem da migracao **e entram numa lista com link**, que e
o que a pessoa precisa para de fato resolve-las.

**`billKeys` so vem quando a decisao vira override** — `acao: "manual"`, ou
cluster `by: "none"`. Decisao que vira regra nao carrega a lista: com 20 mil
lancamentos, carregar seria tornar o arquivo (e o fallback de copiar e colar)
inutilizavel. Se voce precisar das chaves de um cluster que virou regra, elas
estao no `unresolved.json`.

**A tela tambem baixa `arrumar-na-mao-<plano>.md`**, com uma linha por conta
marcada como manual e link direto para cada uma. Guarde: ele e a semente do
relatorio final (SKILL.md secao 10), que junta essas com as que o `apply` nao
conseguiu gravar.

**Confira o `planHash` contra o `meta.json` antes de usar.** Se nao bater, a EV
decidiu sobre uma tela velha — pare e regenere. Se `revisouAgregado` vier
`false`, o arquivo veio de uma versao adulterada da pagina: pergunte antes de
seguir.

Se o download nao funcionar na maquina dela (politica de navegador), a tela tem
**Copiar JSON**: ela cola na conversa e voce escreve o arquivo.

Depois: expanda em `rules`/`overrides` seguindo a secao 7 da SKILL.md
(atencao a ordem — especifica antes de geral) e rode o `plan` de novo.

---

## 3. Template

Substitua `__DADOS_JSON__`. Nada mais.

```html
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Triagem da migracao de categorias</title>
<style>
:root{
  --bg:#f6f7f9; --card:#fff; --ink:#16181d; --muted:#666e7a; --line:#dfe3e8;
  --accent:#1c6b3f; --accent-ink:#fff; --warn:#8a5300; --warn-bg:#fff5e0;
  --danger:#9b1c1c; --danger-bg:#fdecec; --ok:#1c6b3f; --ok-bg:#e8f4ec;
  --chip:#eef1f4;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#14161a; --card:#1c1f25; --ink:#e8eaed; --muted:#9aa3ad; --line:#2c313a;
    --accent:#4ea373; --accent-ink:#0d1f15; --warn:#e0b25c; --warn-bg:#332a16;
    --danger:#f08a8a; --danger-bg:#3a1f1f; --ok:#7fc79c; --ok-bg:#183024;
    --chip:#262b33;
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:14px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{position:sticky;top:0;z-index:20;background:var(--card);
  border-bottom:1px solid var(--line);padding:10px 16px}
.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.grow{flex:1}
h1{font-size:16px;margin:0}
h2{font-size:14px;margin:0 0 8px;text-transform:uppercase;letter-spacing:.04em;
  color:var(--muted)}
main{max-width:1080px;margin:0 auto;padding:16px 16px 96px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;
  padding:14px;margin-bottom:12px}
.chip{background:var(--chip);border-radius:999px;padding:2px 9px;font-size:12px;
  white-space:nowrap}
.chip.ok{background:var(--ok-bg);color:var(--ok)}
.chip.warn{background:var(--warn-bg);color:var(--warn)}
.chip.danger{background:var(--danger-bg);color:var(--danger)}
.mono{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:12px}
.muted{color:var(--muted)}
/* O cabecalho declarativo: frases, nao numeros soltos. */
.resumo{font-size:15px;line-height:1.7}
.resumo b{font-size:17px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--line);
  vertical-align:top}
th{color:var(--muted);font-weight:600}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.scroll{overflow-x:auto}
button{font:inherit;background:var(--chip);color:var(--ink);border:1px solid var(--line);
  border-radius:6px;padding:5px 11px;cursor:pointer}
button.primary{background:var(--accent);color:var(--accent-ink);border-color:transparent}
button:disabled{opacity:.45;cursor:not-allowed}
input[type=text],input[type=search],select{font:inherit;background:var(--card);
  color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:5px 8px;
  max-width:100%}
label.opt{display:flex;gap:7px;align-items:flex-start;padding:5px 7px;
  border-radius:6px;cursor:pointer}
label.opt:hover{background:var(--chip)}
.decidido{border-left:3px solid var(--accent)}
.manual{border-left:3px solid var(--warn)}
.bar{height:6px;background:var(--chip);border-radius:3px;overflow:hidden;min-width:140px}
.bar>i{display:block;height:100%;background:var(--accent)}
footer{position:fixed;bottom:0;left:0;right:0;z-index:20;background:var(--card);
  border-top:1px solid var(--line);padding:10px 16px}
details>summary{cursor:pointer;color:var(--muted);font-size:13px;padding:3px 0}
.banner{border-radius:6px;padding:9px 11px;margin-bottom:10px}
.banner.danger{background:var(--danger-bg);color:var(--danger)}
.banner.warn{background:var(--warn-bg);color:var(--warn)}
.evid{border-left:2px solid var(--line);padding-left:9px;margin:6px 0}
.filtros button[aria-pressed=true]{background:var(--accent);color:var(--accent-ink);
  border-color:transparent}
a{color:var(--accent)}
.massa{background:var(--chip);border-radius:8px;padding:10px 12px;margin-bottom:12px}
.ok-txt{color:var(--ok)}
.nao-txt{color:var(--danger)}
</style>
</head>
<body>
<header>
  <div class="row">
    <h1>Triagem da migracao</h1>
    <span class="chip" id="hFarm"></span>
    <span class="chip" id="hEnv"></span>
    <span class="grow"></span>
    <span class="mono muted" id="hHash"></span>
    <button id="btCopiarHash">Copiar hash</button>
  </div>
  <div class="row" style="margin-top:7px">
    <div class="bar grow"><i id="hBar" style="width:0"></i></div>
    <span class="mono" id="hProg"></span>
  </div>
  <!-- Filtros e busca: com 152 grupos, rolar a pagina inteira para achar o que
       falta decidir e o gargalo real da sessao. -->
  <div class="row filtros" style="margin-top:7px" id="hFiltros">
    <button data-f="todos" aria-pressed="true">Todos</button>
    <button data-f="sem-decisao" aria-pressed="false">Sem decisao</button>
    <button data-f="decididos" aria-pressed="false">Decididos</button>
    <button data-f="manual" aria-pressed="false">Resolver na mao</button>
    <button data-f="com-sugestao" aria-pressed="false">Com sugestao</button>
    <button data-f="sem-sugestao" aria-pressed="false">Sem sugestao</button>
    <input type="search" id="hBusca" placeholder="buscar agrupador, descricao ou fornecedor"
           size="34">
    <span class="mono muted" id="hFiltroInfo"></span>
  </div>
</header>

<main>
  <section class="card" id="aprovacao"></section>
  <h2 id="tituloCauda"></h2>
  <!-- Acao em massa sobre O QUE ESTA FILTRADO. Sem isto, um destino que vale
       para 40 grupos exige 40 vezes o mesmo clique. -->
  <div class="massa" id="massa" style="display:none">
    <div class="row">
      <b>Aplicar aos grupos filtrados</b>
      <span class="mono muted" id="massaN"></span>
    </div>
    <div class="row" style="margin-top:7px">
      <input type="text" id="massaCat" list="listaCats" size="40"
             placeholder="digite o nome ou o codigo da categoria de destino">
      <span class="mono" id="massaCatOk"></span>
      <button id="btMassaAplicar">Aplicar categoria a todos</button>
      <button id="btMassaManual">Marcar todos como resolver na mao</button>
      <button id="btMassaLimpar">Limpar decisao de todos</button>
    </div>
  </div>
  <div id="cauda"></div>
  <section class="card" id="paraMao" style="display:none"></section>
</main>

<datalist id="listaCats"></datalist>

<footer>
  <div class="row">
    <label class="opt" style="padding:0">
      <input type="checkbox" id="revisei">
      <span>Revisei o agregado e os bloqueados acima</span>
    </label>
    <span class="grow"></span>
    <span class="mono muted" id="fResumo"></span>
    <button id="btCopiar">Copiar JSON</button>
    <button id="btLista" disabled>Baixar lista para arrumar na mao</button>
    <button class="primary" id="btBaixar" disabled>Baixar decisoes</button>
  </div>
</footer>

<script id="dados" type="application/json">__DADOS_JSON__</script>
<script>
const D = JSON.parse(document.getElementById('dados').textContent);
const clusters = D.clusters || [], cats = D.categorias || [], meta = D.meta || {};
const catPorChave = Object.fromEntries(cats.map(c => [c.key, c]));
const NOMES = D.nomes || {};
const decisoes = {};
const estado = {filtro:'todos', busca:''};

const brl = n => (typeof n === 'number' ? n : 0).toLocaleString('pt-BR',
  {style:'currency', currency:'BRL'});
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g,
  c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dia = s => /^\d{4}-\d{2}-\d{2}/.test(s || '') ? s.slice(0,10).split('-').reverse().join('/') : (s || '');
/* Nome legivel de qualquer chave. Cai na chave crua quando ninguem sabe o nome —
   melhor mostrar a chave do que mentir. */
const nome = k => NOMES[k] || (catPorChave[k] || {}).nome || k || '';
const nomeCat = k => nome(k) || '(sem destino)';

/* ---------- link para a conta no Aegro ----------
   Pedido n.1 de quem decide: sem ele, decidir exige sair da tela, procurar a
   conta no Financeiro e voltar. O id da fazenda vem no meta (`farmKey`); o
   ambiente escolhe o dominio. Chave de staging e de producao sao as MESMAS
   (staging restaura de producao), entao o link de staging aponta para a mesma
   conta — cuidado ao mandar a lista para alguem: confira o ambiente. */
const BASES = {prod:'https://app.aegro.com.br', staging:'https://app.staging.aegro.io'};
const idDe = k => String(k == null ? '' : k).split('::').pop();
function linkConta(billKey){
  const base = BASES[meta.env] || BASES.prod;
  const fazenda = idDe(meta.farmKey);
  if (!fazenda || !billKey) return '';
  return base + '/farm/' + fazenda + '?billId=' + idDe(billKey) + '#farm-finance';
}
/* Quantos itens a conta tem — nao QUAIS. Saber que sao 3 produtos muda como se
   le a descricao; resolver o nome de cada um seria 315 paginas de catalogo nesta
   fazenda, e o nome nao decide nada: quem decide e o conjunto de agrupadores. */
function itensDe(a){
  const n = a.inputsCount;
  if (n == null) return '';
  if (!n) return 'sem itens';
  return n + (n > 1 ? ' produtos/servicos' : ' produto/servico');
}

/* Motivo de bloqueio -> o que significa, dito para quem nao le codigo. Motivo
   sem entrada aqui aparece cru na tela, e isso e um bug DESTA tela: se o CLI
   ganhar um motivo novo, acrescente a explicacao junto. */
const MOTIVOS = {
  'recurrence': ['Lancamento recorrente',
    'O Aegro responde "salvo" e nao salva. Bloqueado de proposito; migra depois, com o mesmo comando e sem retrabalho.'],
  'settled-recurrence-inputs': ['Recorrente com parcela ja paga',
    'O Aegro recusa alterar os itens desse lancamento. A categoria da conta inteira ainda poderia ser trocada.'],
  'revenue-item-apportioned-noop': ['Receita com itens e rateio de safra',
    'Medido: o Aegro responde vazio e nao grava. Bloqueado antes da escrita para nao contar como migrado.'],
  'stock-location-closed': ['Rateio aponta para local de estoque fechado',
    'Medido: o Aegro responde "salvo" e nao grava. Reabrir o local (ou corrigir o rateio) resolve.'],
  'apportion-per-item': ['Itens travados pela apropriacao de custo por item',
    'Este lancamento tem custo apropriado item por item, e o Aegro nao deixa alterar os itens por fora. A troca precisa ser feita na tela do Aegro.'],
  'override-multi-source': ['Lancamento com duas categorias antigas',
    'Ele tem itens de DUAS categorias antigas diferentes, e a decisao conta a conta so tem um destino — os dois itens iriam para o mesmo lugar. Decida por regra (que separa item a item) em vez de conta a conta.'],
  'operation-type-mismatch': ['Receita apontada para categoria de despesa',
    'Ou o contrario. O Aegro recusaria a gravacao.'],
  'account-and-items': ['Categoria antiga na conta E nos itens',
    'Dado legado incoerente: nao ha uma alteracao que arrume as duas pontas de uma vez. Precisa de olhar humano.'],
  'input-without-category': ['Item sem categoria propria',
    'Nao da para saber o que trocar nesse item.'],
  'element-without-category': ['Insumo sem categoria oficial cadastrada',
    'A regra manda usar a categoria do insumo, e esse insumo nao tem uma. Nao se chuta.'],
  'element-rule-on-account-level': ['Regra de insumo num lancamento sem itens',
    'A regra manda usar a categoria do insumo, mas este lancamento nao tem itens.'],
  'element-category-not-postable': ['Categoria oficial do insumo nao aceita lancamento',
    'Ela esta arquivada ou e so agrupadora. Usa-la faria o lote inteiro parar.']
};

/* ---------- dicionario: nada de jargao chega na tela ----------
   Todo valor cru do CLI passa por aqui antes de aparecer. A tela foi rejeitada
   em campo por falar `planned`/`unresolved`/`cluster`/`override`/
   `by: company+fingerprint` — vocabulario do modelo interno do CLI, varios em
   ingles. Se voce acrescentar algo novo, acrescente a traducao junto. */
const T = {
  status: {
    planned:   'vai mudar de categoria',
    unresolved:'ainda sem destino definido',
    kept:      'fica como esta, de proposito',
    blocked:   'recusado pelo sistema'
  },
  /* O que os lancamentos do grupo tem em comum — a frase entra sozinha num
     chip, sem prefixo ("agrupados por agrupador" ficava redundante). */
  eixo: {
    tags:                 'mesmo agrupador',
    'company+fingerprint':'mesmo fornecedor e descricao',
    company:              'mesmo fornecedor',
    fingerprint:          'mesma descricao',
    element:              'mesmo insumo',
    none:                 'sem pista em comum'
  },
  /* De onde veio o palpite -> [texto na tela, cor]. E a forca da sugestao, e e
     por isso que a EV confia ou desconfia dela. Dicionario UNICO: nao crie
     outro mapa de fonte em lugar nenhum. */
  fonte: {
    precedent:['A propria base do cliente ja usa essa categoria', 'ok'],
    element:  ['Categoria oficial cadastrada no insumo', 'ok'],
    lexical:  ['O nome e quase igual ao de uma categoria ativa — confira', 'warn'],
    none:     ['Nenhuma pista encontrada na base', 'danger'],
    assistant:['Palpite do assistente, sem precedente na base — confira', 'warn']
  }
};
const FONTES = T.fonte;
const traduzEixo   = v => T.eixo[v]   || v;
const traduzStatus = v => T.status[v] || v;

/* ---------- painel de aprovacao ---------- */
function rotuloGrupo(g){
  const de = (g.fromKeys || []).map(nome).join(', ') || '(?)';
  if (g.status === 'planned') return de + ' → ' + nomeCat(g.toKey);
  return de;
}

/* O CLI carimba em UTC (`2026-08-18T06:47:29+00:00`), que e o certo para
   guardar e o errado para mostrar: sao 03:47 no relogio da EV, e nenhum
   escritorio le ISO. Converte para o horario de Brasilia e escreve o fuso —
   hora sem fuso e a que faz alguem achar que o plano e de outro dia. */
function quando(iso){
  if (!iso) return '?';
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  const p = new Intl.DateTimeFormat('pt-BR', {
    timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit',
    year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false,
  }).formatToParts(d).reduce((a, x) => (a[x.type] = x.value, a), {});
  return p.day + '/' + p.month + '/' + p.year + ' as ' + p.hour + ':' + p.minute +
    ' (horario de Brasilia)';
}

/* Uma frase declarativa no lugar dos numeros soltos. "planned: 36" era a
   primeira coisa que a EV lia, e nao significava nada para ela. */
function frasePainel(c, valorPlanejado){
  const linha = (n, texto, extra) => !n ? '' :
    '<div><b>' + n + '</b> ' + texto + (extra || '') + '</div>';
  return '<div class="resumo">' +
    linha(c.planned || 0, 'lancamento(s) vao mudar de categoria',
          valorPlanejado ? ' (' + brl(valorPlanejado) + ')' : '') +
    linha(c.unresolved || 0, 'ainda sem destino — decida abaixo') +
    linha(c.kept || 0, 'ficam como estao, de proposito') +
    linha(c.blocked || 0, 'o sistema recusou; nao serao tocados') +
    '</div>';
}

function pintaAprovacao(){
  const c = meta.counts || {}, sweep = meta.sweep || {}, g = D.grupos || [];
  const bloq = {};
  for (const grupo of g){
    if (grupo.status !== 'blocked') continue;
    const r = grupo.reason || 'desconhecido';
    bloq[r] = bloq[r] || {n:0, v:0};
    bloq[r].n += grupo.bills || 0;
    bloq[r].v += grupo.totalAmount || 0;
  }
  let html = '<h2>O que este plano faz</h2>';

  if (sweep.complete === false){
    html += '<div class="banner danger"><b>A varredura nao fechou.</b> ' +
      'Declarado ' + esc(sweep.declaredTotal) + ', coletado ' +
      esc(sweep.uniqueCollected) + '. ' + esc(JSON.stringify(sweep.issues || [])) +
      '<br>Nao aprove: parte da categoria pode ter ficado de fora do plano.</div>';
  }
  /* Categoria de origem no escopo da corrida SEM regra: os lancamentos dela
     entram como "sem destino" e aparecem abaixo. Dito aqui porque o silencio
     nesse ponto ja fez 95 lancamentos passarem em branco. */
  if ((meta.sourcesWithoutRule || []).length){
    html += '<div class="banner warn"><b>' + meta.sourcesWithoutRule.length +
      '</b> categoria(s) antiga(s) desta rodada ainda nao tem regra nenhuma: ' +
      esc(meta.sourcesWithoutRule.map(nome).join('; ')) +
      '. Os lancamentos delas estao aqui embaixo, sem destino — nada sera ' +
      'escrito neles enquanto voce nao decidir.</div>';
  }
  const valorPlanejado = g.filter(x => x.status === 'planned')
    .reduce((s, x) => s + (x.totalAmount || 0), 0);
  html += frasePainel(c, valorPlanejado) +
    '<div class="muted" style="margin:6px 0 12px">Plano gerado em ' +
    esc(quando(meta.generatedAt)) + '.</div>';

  if (meta.recurrentInSweep){
    html += '<div class="banner warn"><b>' + meta.recurrentInSweep +
      '</b> lancamento(s) recorrente(s) neste recorte; <b>' +
      (meta.recurrentBlocked || 0) + '</b> ficam de fora desta rodada. ' +
      'O Aegro ainda nao grava essa alteracao em lancamento recorrente — nao e ' +
      'erro seu nem dado errado. Eles migram depois, com o mesmo comando e sem ' +
      'refazer nada.</div>';
  }

  /* Blocos com titulo, e nao uma tabela unica com prefixo em caixa alta no meio
     do texto. A EV perguntou, olhando a tabela antiga: "o que sao aqueles grupos
     ali, sao os que ja foram, os que foram resolvidos, os que nao foram?" — e a
     tela nao respondia. Cada bloco abre dizendo o que ele e. */
  const tabela = (linhas, colunaPorque) =>
    '<div class="scroll"><table><thead><tr><th>Grupo</th>' +
    '<th class="num">Lancamentos</th><th class="num">Valor</th>' +
    '<th>' + colunaPorque + '</th></tr></thead><tbody>' +
    linhas.map(x =>
      '<tr><td>' + esc(rotuloGrupo(x)) + '</td>' +
      '<td class="num">' + (x.bills || 0) + '</td>' +
      '<td class="num">' + brl(x.totalAmount) + '</td>' +
      '<td class="muted">' + esc(x.why || x.reason || '') + '</td></tr>').join('') +
    '</tbody></table></div>';

  const bloco = (titulo, frase, linhas, colunaPorque) => !linhas.length ? '' :
    '<h2 style="margin-top:16px">' + titulo + '</h2>' +
    '<p class="muted" style="margin:2px 0 8px">' + frase + '</p>' +
    tabela(linhas, colunaPorque);

  html += bloco('O que vai mudar',
    'Estes lancamentos saem da categoria antiga e vao para a nova assim que ' +
    'voce aprovar.',
    g.filter(x => x.status === 'planned'), 'Por que este destino');

  html += bloco('O que fica como esta',
    'Decisoes conscientes: alguem marcou para nao mexer.',
    g.filter(x => x.status === 'kept'), 'Por que fica');

  html += bloco('O que ainda nao tem destino',
    'Nenhuma das regras que voce definiu alcancou estes lancamentos. Eles nao ' +
    'serao tocados — e os grupos mais abaixo nesta pagina sao onde voce decide ' +
    'o que fazer com eles.',
    g.filter(x => x.status === 'unresolved'), 'O que faltou');

  const motivos = Object.keys(bloq);
  if (motivos.length){
    html += '<h2 style="margin-top:16px">O que o sistema recusou</h2>' +
      '<p class="muted" style="margin:2px 0 8px">O Aegro nao aceita (ou nao ' +
      'grava) esta alteracao nestes lancamentos. Nao e erro seu nem dado ' +
      'corrompido, e nada sera escrito neles. Eles entram na lista do fim da ' +
      'pagina, para arrumar um a um na tela do Aegro.</p><div class="scroll">' +
      '<table><thead><tr><th>Motivo</th><th class="num">Lancamentos</th>' +
      '<th class="num">Valor</th><th>O que significa</th></tr></thead><tbody>' +
      motivos.map(m => {
        const info = MOTIVOS[m];
        return '<tr><td>' + esc(info ? info[0] : m) +
        '</td><td class="num">' + bloq[m].n +
        '</td><td class="num">' + brl(bloq[m].v) + '</td><td class="muted">' +
        esc(info ? info[1] : 'Motivo novo, ainda sem explicacao nesta tela (' +
          m + ') — pergunte ao time antes de aprovar.') +
        '</td></tr>';
      }).join('') + '</tbody></table></div>';
  }
  document.getElementById('aprovacao').innerHTML = html;
}

/* ---------- cauda ---------- */
function tituloDe(cl){
  if (cl.by === 'tags') return 'agrupador ' + (cl.tags || []).join(' + ');
  if (cl.by === 'company+fingerprint') return cl.fingerprint + ' — ' + nome(cl.companyKey);
  if (cl.by === 'company') return nome(cl.companyKey) + ' (sem descricao util)';
  if (cl.by === 'fingerprint') return cl.fingerprint;
  if (cl.by === 'element') return 'insumo ' + (cl.elementKeys || []).map(nome).join(', ');
  return 'sem pista nenhuma';
}

/* O que vai acontecer se ela escolher isto — em portugues, nao no nome do
   campo do arquivo de/para. */
function previa(cl, d){
  const n = (cl.fromKeys || []).length || 1;
  if (!d) return 'Nada muda agora. Este grupo volta na proxima rodada.';
  if (d.acao === 'manual')
    return 'Estes ' + cl.count + ' lancamento(s) ficam de fora da migracao e ' +
      'entram na lista do fim da pagina, para arrumar na tela do Aegro.';
  if (cl.by === 'none')
    return 'Sem pista para virar regra: a decisao vale conta a conta, ' +
      'nos ' + cl.count + ' lancamento(s) deste grupo.';
  const criterio = {
    'tags':'terem os mesmos agrupadores',
    'company+fingerprint':'serem do mesmo fornecedor e terem a mesma descricao',
    'company':'serem do mesmo fornecedor',
    'fingerprint':'terem a mesma descricao',
    'element':'terem o mesmo insumo'
  }[cl.by];
  return 'Vira ' + (n > 1 ? n + ' regras' : 'uma regra') +
    ' que alcanca lancamentos por ' + criterio +
    ' — inclusive os que aparecerem depois.';
}

function textoBusca(cl){
  return [
    (cl.tags || []).join(' '),
    cl.fingerprint || '',
    nome(cl.companyKey),
    (cl.samples || []).map(a => (a.description || '') + ' ' + nome(a.companyKey)).join(' ')
  ].join(' ').toLowerCase();
}

function visiveis(){
  const busca = estado.busca.trim().toLowerCase();
  return clusters.map((cl, i) => i).filter(i => {
    const cl = clusters[i], d = decisoes[cl.cluster];
    if (estado.filtro === 'sem-decisao' && d) return false;
    if (estado.filtro === 'decididos' && !d) return false;
    if (estado.filtro === 'manual' && !(d && d.acao === 'manual')) return false;
    if (estado.filtro === 'com-sugestao' && !((cl.suggestion || {}).toKey)) return false;
    if (estado.filtro === 'sem-sugestao' && (cl.suggestion || {}).toKey) return false;
    if (busca && !textoBusca(cl).includes(busca)) return false;
    return true;
  });
}

function cartao(i){
  const cl = clusters[i];
  const s = cl.suggestion || {}, sa = cl.sugestaoAssistente;
  const d = decisoes[cl.cluster];
  const opcoes = [];
  if (s.toKey) opcoes.push({v:'sugestao', rot:'Aplicar sugestao: <b>' + esc(nomeCat(s.toKey)) +
    '</b>', src:s.source || 'none', ev:s.evidence, pre:!!s.prechecked});
  if (sa && sa.toKey) opcoes.push({v:'assistente', rot:'Palpite do assistente: <b>' +
    esc(nomeCat(sa.toKey)) + '</b>', src:'assistant', ev:sa.evidence, pre:false});
  /* Ja decidido: o radio nasce onde a decisao esta, e nao no default. Sem isto,
     filtrar e voltar apagaria visualmente o que ela ja escolheu. */
  const marcado = v => {
    if (!d) return opcoes.some(o => o.v === v && o.pre) ? ' checked' : '';
    if (d.acao === 'manual') return v === 'manual' ? ' checked' : '';
    if (d.origem === 'sugestao') return v === 'sugestao' ? ' checked' : '';
    if (d.origem === 'sugestao-assistente') return v === 'assistente' ? ' checked' : '';
    return v === 'outra' ? ' checked' : '';
  };
  const catEscolhida = d && d.acao === 'migrar' && d.origem === 'escolha-manual'
    ? rotuloCat(catPorChave[d.toKey] || {key:d.toKey, nome:nomeCat(d.toKey)}) : '';
  /* Grupo de UM lancamento nasce com a amostra aberta: nele a amostra E o grupo,
     e clicar para ver a unica linha era clique puro. Aqui eram 84 de 152. */
  const aberto = cl.count === 1 ? ' open' : '';

  return '<section class="card' + (d ? (d.acao === 'manual' ? ' manual' : ' decidido') : '') +
    '" id="c' + i + '" data-i="' + i + '">' +
    '<div class="row"><b>#' + (i+1) + '</b> <span>' + esc(tituloDe(cl)) + '</span>' +
    '<span class="grow"></span><span class="chip">' + cl.count + ' lancamentos</span>' +
    '<span class="chip">' + brl(cl.totalAmount) + '</span>' +
    '<span class="chip">' + esc(traduzEixo(cl.by)) + '</span></div>' +

    opcoes.map(o => {
      const f = FONTES[o.src] || FONTES.none;
      /* A FONTE em portugues, nao o rotulo cru (`precedent`, `lexical`). E ela
         que diz a forca do palpite, e e por isso que a EV confia ou nao. */
      return '<div class="evid"><span class="chip ' + f[1] + '">' + esc(f[0]) +
        '</span><div class="muted" style="margin-top:4px">' +
        esc(o.ev || '') + '</div></div>';
    }).join('') +
    (opcoes.length ? '' : '<div class="evid muted">' + esc(s.evidence || '') + '</div>') +

    '<div style="margin-top:8px">' +
    opcoes.map(o => '<label class="opt"><input type="radio" name="d' + i + '" value="' +
      o.v + '"' + marcado(o.v) + '><span>' + o.rot + '</span></label>').join('') +
    '<label class="opt"><input type="radio" name="d' + i + '" value="outra"' +
      marcado('outra') + '><span>Escolher outra categoria</span></label>' +
    /* Busca DENTRO da caixa (datalist), e nao num campo separado ao lado de um
       select: eram dois cliques e um vaivem para cada escolha. A validacao fica
       a vista porque digitacao incompleta nao pode virar decisao errada em
       silencio. */
    '<div style="padding-left:26px;display:none" data-campo="outra">' +
      '<input type="text" data-cat list="listaCats" size="42" value="' + esc(catEscolhida) +
      '" placeholder="digite o nome ou o codigo"> <span class="mono" data-catok></span></div>' +
    '<label class="opt"><input type="radio" name="d' + i + '" value="manual"' +
      marcado('manual') + '><span>Resolver manualmente (vou arrumar na tela do Aegro)</span></label>' +
    /* Sem justificativa obrigatoria: em campo a exigencia so fez inventar texto
       para poder seguir. O que importa e a conta entrar na lista do fim. */
    '<div style="padding-left:26px;display:none" data-campo="manual">' +
      '<input type="text" data-why size="52" value="' + esc((d && d.why) || '') +
      '" placeholder="observacao (opcional)"></div>' +
    '<label class="opt"><input type="radio" name="d' + i + '" value="adiar"' +
      (d ? '' : '') + '><span>Decidir depois</span></label></div>' +

    '<div class="muted mono" data-previa style="margin-top:6px"></div>' +

    '<details style="margin-top:6px"' + aberto + '><summary>' +
    (cl.samples || []).length +
    ' amostra(s) · origem: ' + esc((cl.fromKeys || []).map(nome).join(', ')) + '</summary>' +
    '<div class="scroll"><table><thead><tr><th>Data</th><th>Fornecedor</th>' +
    '<th>Descricao</th><th>Itens</th><th class="num">Valor</th><th></th></tr></thead><tbody>' +
    /* Fornecedor por LINHA, e nao no cabecalho do grupo: agrupado por
       agrupador, um cartao junta dezenas de fornecedores diferentes, e e aqui
       que a EV ve de quem e cada um. */
    (cl.samples || []).map(a => {
      const url = linkConta(a.billKey);
      return '<tr><td>' + esc(dia(a.entryDate)) + '</td><td>' +
      esc(a.companyKey ? nome(a.companyKey) : '') + '</td><td>' +
      esc(a.description) + '</td><td class="muted">' + esc(itensDe(a)) +
      '</td><td class="num">' + brl(a.totalAmount) + '</td><td>' +
      (url ? '<a href="' + esc(url) + '" target="_blank" rel="noopener">abrir</a>' : '') +
      '</td></tr>';
    }).join('') + '</tbody></table></div></details></section>';
}

function rotuloCat(c){
  return c.nome + (c.codigo ? ' (' + c.codigo + ')' : '');
}
/* Resolve o que foi digitado. Aceita o rotulo inteiro, o nome, ou o codigo. */
function achaCat(texto){
  const t = (texto || '').trim().toLowerCase();
  if (!t) return null;
  return cats.find(c => rotuloCat(c).toLowerCase() === t)
      || cats.find(c => (c.nome || '').toLowerCase() === t)
      || cats.find(c => (c.codigo || '').toLowerCase() === t)
      || null;
}
function pintaValidacao(campo, alvo){
  const c = achaCat(campo.value);
  if (!campo.value.trim()){ alvo.textContent = ''; alvo.className = 'mono'; return c; }
  alvo.textContent = c ? 'ok: ' + rotuloCat(c) : 'nao encontrei essa categoria';
  alvo.className = 'mono ' + (c ? 'ok-txt' : 'nao-txt');
  return c;
}

function baseDecisao(cl){
  return {cluster:cl.cluster, by:cl.by, fromKeys:cl.fromKeys || [],
    companyKey:cl.companyKey || null, fingerprint:cl.fingerprint || '',
    elementKeys:cl.elementKeys || [], count:cl.count, why:''};
}

function leCartao(i){
  const cl = clusters[i], no = document.getElementById('c' + i);
  if (!no) return;
  const escolhido = no.querySelector('input[name="d' + i + '"]:checked');
  no.querySelector('[data-campo="outra"]').style.display =
    escolhido && escolhido.value === 'outra' ? '' : 'none';
  no.querySelector('[data-campo="manual"]').style.display =
    escolhido && escolhido.value === 'manual' ? '' : 'none';
  const campoCat = no.querySelector('[data-cat]');
  const alvoOk = no.querySelector('[data-catok]');
  const catDigitada = pintaValidacao(campoCat, alvoOk);

  if (!escolhido){ delete decisoes[cl.cluster]; }
  else {
    const v = escolhido.value;
    /* `billKeys` so entra quando a decisao vira OVERRIDE (resolver na mao, ou
       cluster sem sinal). Decisao que vira regra nao precisa da lista, e
       carrega-la faria o arquivo de decisoes ter dezenas de milhares de chaves —
       inutilizando o fallback de copiar e colar. */
    const chaves = cl.billKeys || [];
    const base = baseDecisao(cl);
    if (v === 'adiar'){ delete decisoes[cl.cluster]; }
    else if (v === 'manual'){
      decisoes[cl.cluster] = {...base, acao:'manual', toKey:null, toNome:null,
        origem:'escolha-manual', sugestaoSource:null,
        why:no.querySelector('[data-why]').value.trim(), billKeys:chaves};
    } else {
      let k = null, origem = 'escolha-manual', src = null;
      if (v === 'sugestao'){ k = (cl.suggestion || {}).toKey; origem = 'sugestao';
        src = (cl.suggestion || {}).source; }
      else if (v === 'assistente'){ k = (cl.sugestaoAssistente || {}).toKey;
        origem = 'sugestao-assistente'; src = 'assistant'; }
      else { k = catDigitada ? catDigitada.key : null; }
      if (k) decisoes[cl.cluster] = {...base, acao:'migrar', toKey:k, toNome:nomeCat(k),
        origem, sugestaoSource:src, ...(cl.by === 'none' ? {billKeys:chaves} : {})};
      else delete decisoes[cl.cluster];
    }
  }
  const d = decisoes[cl.cluster];
  no.classList.toggle('decidido', !!d && d.acao !== 'manual');
  no.classList.toggle('manual', !!d && d.acao === 'manual');
  no.querySelector('[data-previa]').textContent = previa(cl, d);
  atualiza();
}

/* ---------- lista para arrumar na mao ----------
   Toda conta que a migracao NAO vai tocar, com link. E o que sobra para uma
   pessoa fazer a mao, e sem esta lista ela nao sabe por onde comecar. */
function contasParaMao(){
  const itens = [];
  for (const cl of clusters){
    const d = decisoes[cl.cluster];
    if (!d || d.acao !== 'manual') continue;
    const porChave = Object.fromEntries((cl.samples || []).map(a => [a.billKey, a]));
    for (const chave of (cl.billKeys || [])){
      const a = porChave[chave] || {};
      itens.push({billKey:chave, entryDate:a.entryDate || '', description:a.description || '',
        totalAmount:a.totalAmount, companyKey:a.companyKey || null,
        motivo:'voce marcou para resolver na mao', why:d.why || '',
        de:(cl.fromKeys || []).map(nome).join(', ')});
    }
  }
  return itens;
}

function pintaParaMao(){
  const itens = contasParaMao();
  const no = document.getElementById('paraMao');
  document.getElementById('btLista').disabled = !itens.length;
  if (!itens.length){ no.style.display = 'none'; no.innerHTML = ''; return; }
  no.style.display = '';
  no.innerHTML = '<h2>Para arrumar na mao (' + itens.length + ' lancamento(s))</h2>' +
    '<p class="muted" style="margin:2px 0 8px">Estes ficam fora da migracao ' +
    'automatica. O botao no pe da pagina baixa esta lista com os links, para ' +
    'trabalhar nela depois.</p><div class="scroll"><table><thead><tr>' +
    '<th>Data</th><th>Fornecedor</th><th>Descricao</th><th>Categoria antiga</th>' +
    '<th class="num">Valor</th><th></th></tr></thead><tbody>' +
    itens.map(x => {
      const url = linkConta(x.billKey);
      return '<tr><td>' + esc(dia(x.entryDate)) + '</td><td>' +
        esc(x.companyKey ? nome(x.companyKey) : '') + '</td><td>' +
        esc(x.description) + '</td><td class="muted">' + esc(x.de) + '</td>' +
        '<td class="num">' + brl(x.totalAmount) + '</td><td>' +
        (url ? '<a href="' + esc(url) + '" target="_blank" rel="noopener">abrir</a>' : '') +
        '</td></tr>';
    }).join('') + '</tbody></table></div>';
}

function markdownParaMao(){
  const itens = contasParaMao();
  const linhas = ['# Contas para arrumar na mao — ' + (meta.farm || ''), '',
    'Ambiente: ' + (meta.env || '?') + '. Gerado em ' + quando(meta.generatedAt) + '.', '',
    'Arquivo local com dado de cliente: nao publicar.', '',
    '| Data | Fornecedor | Descricao | Categoria antiga | Valor | Link |',
    '|---|---|---|---|---:|---|'];
  for (const x of itens){
    linhas.push('| ' + dia(x.entryDate) + ' | ' + (x.companyKey ? nome(x.companyKey) : '') +
      ' | ' + String(x.description || '').replace(/\|/g, '/').replace(/\n/g, ' ') +
      ' | ' + x.de + ' | ' + brl(x.totalAmount) +
      ' | [abrir](' + linkConta(x.billKey) + ') |');
  }
  return linhas.join('\n') + '\n';
}

function atualiza(){
  const n = Object.keys(decisoes).length;
  const cobertos = Object.values(decisoes).reduce((a, d) => a + (d.count || 0), 0);
  const total = clusters.reduce((a, c) => a + (c.count || 0), 0);
  document.getElementById('hProg').textContent =
    n + '/' + clusters.length + ' grupos · ' + cobertos + '/' + total + ' lancamentos';
  document.getElementById('hBar').style.width =
    (total ? Math.round(cobertos * 100 / total) : 0) + '%';
  const naMao = Object.values(decisoes).filter(d => d.acao === 'manual')
    .reduce((a, d) => a + (d.count || 0), 0);
  document.getElementById('fResumo').textContent = n + ' decisao(oes)' +
    (naMao ? ' · ' + naMao + ' para arrumar na mao' : '');
  document.getElementById('btBaixar').disabled =
    !document.getElementById('revisei').checked || n === 0;
  pintaParaMao();
}

function payload(){
  return JSON.stringify({version:1, plano:D.planoArquivo || meta.planFile || '',
    planHash:meta.planHash || '', farm:meta.farm || '',
    revisouAgregado:document.getElementById('revisei').checked,
    decisoes:Object.values(decisoes)}, null, 2);
}

/* ---------- render da cauda, com filtro ---------- */
function render(){
  const idx = visiveis();
  document.getElementById('hFiltroInfo').textContent =
    idx.length === clusters.length ? '' : idx.length + ' de ' + clusters.length + ' grupos';
  document.getElementById('massa').style.display = idx.length > 1 ? '' : 'none';
  document.getElementById('massaN').textContent = idx.length + ' grupo(s) filtrado(s)';
  document.getElementById('cauda').innerHTML = idx.map(cartao).join('');
  for (const i of idx){
    const no = document.getElementById('c' + i);
    no.addEventListener('input', () => leCartao(i));
    no.addEventListener('change', () => leCartao(i));
    leCartao(i);
  }
  atualiza();
}

/* ---------- bootstrap ---------- */
document.getElementById('hFarm').textContent = meta.farm || '(fazenda?)';
document.getElementById('hEnv').textContent = meta.env || '(env?)';
/* Hash truncado na tela (o botao copia inteiro): 71 caracteres empurrariam a
   barra para fora em tela estreita, e ninguem le hash com o olho. */
document.getElementById('hHash').textContent =
  (meta.planHash || '').slice(0, 22) + ((meta.planHash || '').length > 22 ? '...' : '');
document.getElementById('hHash').title = meta.planHash || '';
document.getElementById('tituloCauda').textContent = clusters.length
  ? clusters.length + ' grupo(s) que ainda nao tem destino'
  : 'Nada aqui: todo lancamento ja tem destino ou decisao';
document.getElementById('listaCats').innerHTML = cats.map(c =>
  '<option value="' + esc(rotuloCat(c)) + '"></option>').join('');
pintaAprovacao();
render();

for (const bt of document.querySelectorAll('#hFiltros button')){
  bt.addEventListener('click', () => {
    estado.filtro = bt.dataset.f;
    for (const outro of document.querySelectorAll('#hFiltros button'))
      outro.setAttribute('aria-pressed', String(outro === bt));
    render();
  });
}
document.getElementById('hBusca').addEventListener('input', e => {
  estado.busca = e.target.value; render();
});

/* Acao em massa: sempre com confirmacao que DIZ QUANTOS grupos, porque o
   estrago de um clique errado aqui e proporcional ao filtro. */
document.getElementById('massaCat').addEventListener('input', e =>
  pintaValidacao(e.target, document.getElementById('massaCatOk')));
document.getElementById('btMassaAplicar').onclick = () => {
  const c = achaCat(document.getElementById('massaCat').value);
  const idx = visiveis();
  if (!c){ alert('Escolha uma categoria valida antes.'); return; }
  if (!confirm('Aplicar "' + rotuloCat(c) + '" a ' + idx.length + ' grupo(s) filtrado(s)?')) return;
  for (const i of idx){
    const cl = clusters[i];
    decisoes[cl.cluster] = {...baseDecisao(cl), acao:'migrar', toKey:c.key,
      toNome:nomeCat(c.key), origem:'escolha-manual', sugestaoSource:null,
      ...(cl.by === 'none' ? {billKeys:cl.billKeys || []} : {})};
  }
  render();
};
document.getElementById('btMassaManual').onclick = () => {
  const idx = visiveis();
  if (!confirm('Marcar ' + idx.length + ' grupo(s) filtrado(s) como resolver na mao?')) return;
  for (const i of idx){
    const cl = clusters[i];
    decisoes[cl.cluster] = {...baseDecisao(cl), acao:'manual', toKey:null, toNome:null,
      origem:'escolha-manual', sugestaoSource:null, billKeys:cl.billKeys || []};
  }
  render();
};
document.getElementById('btMassaLimpar').onclick = () => {
  const idx = visiveis();
  if (!confirm('Limpar a decisao de ' + idx.length + ' grupo(s) filtrado(s)?')) return;
  for (const i of idx) delete decisoes[clusters[i].cluster];
  render();
};

document.getElementById('revisei').addEventListener('change', atualiza);
document.getElementById('btCopiarHash').onclick = () =>
  navigator.clipboard.writeText(meta.planHash || '');
document.getElementById('btCopiar').onclick = () =>
  navigator.clipboard.writeText(payload());
function baixa(texto, arquivo, tipo){
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([texto], {type:tipo}));
  a.download = arquivo;
  a.click();
  URL.revokeObjectURL(a.href);
}
document.getElementById('btBaixar').onclick = () => {
  const nomeArq = (D.planoArquivo || 'plano').replace(/[\\/]/g, '_');
  baixa(payload(), 'decisoes-' + nomeArq + '.json', 'application/json');
};
document.getElementById('btLista').onclick = () => {
  const nomeArq = (D.planoArquivo || 'plano').replace(/[\\/]/g, '_');
  baixa(markdownParaMao(), 'arrumar-na-mao-' + nomeArq + '.md', 'text/markdown');
};
atualiza();
</script>
</body>
</html>
```

---

## 4. O que a tela deliberadamente NAO faz

- **Nao escreve na API.** Ela produz um arquivo de decisoes. Toda escrita passa
  pelo `apply`, sobre um plano aprovado por hash.
- **Nao pre-marca `lexical`, `none` nem `assistant`.** Decisao fraca nao nasce
  aceita (D7). Se voce mexer no template, mantenha isso.
- **Nao deixa baixar sem a caixa "revisei" marcada.** A caixa e a razao de o
  painel de aprovacao estar na mesma tela: aprovar o hash sem olhar os
  bloqueados e como a migracao silenciosamente fica pela metade.
- **Nao oferece categoria sintetica nem arquivada** — desde que voce filtre
  `SYNTHETIC` e use `--status ACTIVE` ao montar `categorias`. Esse filtro e seu.
- **Nao resolve o NOME de cada insumo da conta.** Mostra quantos itens sao, e
  para. Resolver o nome custaria 315 paginas de catalogo (15.714 elementos nesta
  fazenda) ou 1 GET por chave, e o nome nao decide nada: quem decide e o conjunto
  de agrupadores. Se alguem pedir, pergunte primeiro o que a decisao mudaria.
- **Nao age em massa sem dizer quantos.** Toda acao sobre o filtrado confirma
  nomeando a contagem, porque o estrago de um clique errado ali e proporcional ao
  filtro.
- **Nao aceita categoria digitada pela metade.** A caixa valida a vista ("ok:
  <categoria>" / "nao encontrei") — digitacao incompleta virando decisao errada em
  silencio e pior que erro barulhento.

### 4.1 Cuidado com o link em staging

A chave de staging e a MESMA de producao (staging restaura de producao), entao o
link de staging aponta para a mesma conta que o de producao. Isso e util para
conferir, e e uma armadilha ao mandar a lista para alguem: **diga em que ambiente
o ensaio rodou**. A tela ja escreve o ambiente no cabecalho e no markdown.
