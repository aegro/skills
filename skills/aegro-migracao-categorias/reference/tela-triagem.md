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

- **`categorias`** e o catalogo **para a EV escolher destino**. Monte com
  `aegro fin-categories list --farm "<fazenda>" --status ACTIVE --page N -o json`,
  paginando ate acabar (50 por pagina). O nome esta em `description` (com
  fallback `name`). **Descarte `type: "SYNTHETIC"`** — sintetica e agrupadora e
  nao e lancavel; oferece-la seria oferecer uma falha garantida.
- **`nomes`** e so para **exibir**, e cobre chave que nao esta em `categorias`:
  - **categorias de origem**, que sao ARQUIVADAS (rode o `fin-categories list`
    tambem sem `--status`, ou com `--status ARCHIVED`);
  - **fornecedores** e **elementos** dos clusters.

  **Use `list` paginado, nunca um `get` por chave.** A cauda real tinha 745
  clusters, e a receita ingenua de um `get` por chave distinta deu **1.681
  chamadas** (147 fornecedores + 1.534 elementos) — minutos de espera para
  preencher rotulo:

  ```bash
  aegro companies list --farm "<fazenda>" --page N -o json   # 50/pagina
  aegro elements  list --farm "<fazenda>" --page N -o json   # 50/pagina
  ```

  Pagine ate acabar, monte `{key: nome}` de uma vez, e reserve o `get` para as
  poucas chaves que a listagem nao cobriu. Se a fazenda tiver catalogo grande e
  isso ainda pesar, **exiba a chave crua** em vez de gastar minutos: rotulo faltando
  atrasa uma decisao, varredura de nomes atrasa a sessao inteira.

  Vale o esforco: um cartao que diz "CPFL PAULISTA" e decidivel; um que diz
  `company::64a0f1...` obriga a EV a sair da tela para descobrir de quem e.
- **`grupos`** e o agregado que o `plan` imprimiu (campos `status`, `fromKeys`,
  `toKey`, `ruleIndex`, `why`, `reason`, `bills`, `totalAmount`). Se voce nao
  guardou o stdout, rode o `plan` de novo — e deterministico e nao escreve nada.
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
    {"cluster": "__sem-sinal__", "by": "none", "acao": "manter",
     "toKey": null, "toNome": null, "origem": "escolha-manual",
     "sugestaoSource": null, "fromKeys": ["financialCategory::velha"],
     "companyKey": null, "fingerprint": "", "elementKeys": [],
     "count": 9, "why": "estorno, categoria antiga e proposital",
     "billKeys": ["bill::z0", "bill::z1"]}
  ]
}
```

`acao` e `migrar` | `manter` | `adiar` (`adiar` nao aparece no arquivo — some).
`origem` e `sugestao` | `sugestao-assistente` | `escolha-manual`.

**`billKeys` so vem quando a decisao vira override** — `acao: "manter"`, ou
cluster `by: "none"`. Decisao que vira regra nao carrega a lista: com 20 mil
lancamentos, carregar seria tornar o arquivo (e o fallback de copiar e colar)
inutilizavel. Se voce precisar das chaves de um cluster que virou regra, elas
estao no `unresolved.json`.

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
input[type=text],select{font:inherit;background:var(--card);color:var(--ink);
  border:1px solid var(--line);border-radius:6px;padding:5px 8px;max-width:100%}
label.opt{display:flex;gap:7px;align-items:flex-start;padding:5px 7px;
  border-radius:6px;cursor:pointer}
label.opt:hover{background:var(--chip)}
.decidido{border-left:3px solid var(--accent)}
.bar{height:6px;background:var(--chip);border-radius:3px;overflow:hidden;min-width:140px}
.bar>i{display:block;height:100%;background:var(--accent)}
footer{position:fixed;bottom:0;left:0;right:0;z-index:20;background:var(--card);
  border-top:1px solid var(--line);padding:10px 16px}
details>summary{cursor:pointer;color:var(--muted);font-size:13px;padding:3px 0}
.banner{border-radius:6px;padding:9px 11px;margin-bottom:10px}
.banner.danger{background:var(--danger-bg);color:var(--danger)}
.banner.warn{background:var(--warn-bg);color:var(--warn)}
.evid{border-left:2px solid var(--line);padding-left:9px;margin:6px 0}
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
</header>

<main>
  <section class="card" id="aprovacao"></section>
  <h2 id="tituloCauda"></h2>
  <div id="cauda"></div>
</main>

<footer>
  <div class="row">
    <label class="opt" style="padding:0">
      <input type="checkbox" id="revisei">
      <span>Revisei o agregado e os bloqueados acima</span>
    </label>
    <span class="grow"></span>
    <span class="mono muted" id="fResumo"></span>
    <button id="btCopiar">Copiar JSON</button>
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

const brl = n => (typeof n === 'number' ? n : 0).toLocaleString('pt-BR',
  {style:'currency', currency:'BRL'});
const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g,
  c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dia = s => /^\d{4}-\d{2}-\d{2}/.test(s || '') ? s.slice(0,10).split('-').reverse().join('/') : (s || '');
/* Nome legivel de qualquer chave. Cai na chave crua quando ninguem sabe o nome —
   melhor mostrar a chave do que mentir. */
const nome = k => NOMES[k] || (catPorChave[k] || {}).nome || k || '';
const nomeCat = k => nome(k) || '(sem destino)';

const MOTIVOS = {
  'recurrence': 'Lancamento recorrente. O PATCH publico e no-op silencioso (FNC-184): responde 200 e nao salva. Bloqueado de proposito; migra depois, com o mesmo comando.',
  'operation-type-mismatch': 'Receita apontada para categoria devedora (ou o contrario). O servidor recusaria.',
  'account-and-items': 'A categoria antiga aparece na conta E nos itens. Dado legado incoerente: precisa de olhar humano.',
  'input-without-category': 'Item sem categoria propria. Nao da para saber o que trocar.',
  'element-without-category': 'Regra @element, mas o elemento nao tem categoria oficial cadastrada. Nao se chuta.',
  'element-rule-on-account-level': 'Regra @element numa conta sem itens. @element so vale no nivel de item.',
  'element-category-not-postable': 'A categoria oficial do elemento esta arquivada ou e sintetica. Escreve-la daria 422 e abortaria o lote.'
};
const FONTES = {
  precedent: ['A propria base do cliente responde', 'ok'],
  element: ['Categoria oficial do elemento', 'ok'],
  lexical: ['Nome equivalente — confira', 'warn'],
  none: ['Sem sinal na base', 'danger'],
  assistant: ['Palpite do assistente — sem precedente na base', 'warn']
};

/* ---------- painel de aprovacao ---------- */
function rotuloGrupo(g){
  const de = (g.fromKeys || []).map(nome).join(', ') || '(?)';
  if (g.status === 'planned')
    return de + ' → ' + nomeCat(g.toKey) +
      (g.ruleIndex ? ' (regra #' + g.ruleIndex + ')' : '');
  if (g.status === 'blocked') return 'BLOQUEADO · ' + de;
  if (g.status === 'kept') return 'MANTIDO · ' + de;
  return 'SEM REGRA · ' + de;
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
  let html = '<h2>Antes de aprovar</h2>';

  if (sweep.complete === false){
    html += '<div class="banner danger"><b>A varredura nao fechou.</b> ' +
      'Declarado ' + esc(sweep.declaredTotal) + ', coletado ' +
      esc(sweep.uniqueCollected) + '. ' + esc(JSON.stringify(sweep.issues || [])) +
      '<br>Nao aprove: parte da categoria pode ter ficado de fora do plano.</div>';
  }
  html += '<div class="row" style="margin-bottom:10px">' +
    ['planned','unresolved','kept','blocked'].map(s =>
      '<span class="chip">' + s + ': <b>' + (c[s] || 0) + '</b></span>').join('') +
    '<span class="chip">gerado em ' + esc(meta.generatedAt || '?') + '</span></div>';

  if (meta.recurrentInSweep){
    html += '<div class="banner warn"><b>' + meta.recurrentInSweep +
      '</b> lancamento(s) recorrente(s) na varredura; <b>' +
      (meta.recurrentBlocked || 0) + '</b> bloqueado(s) pelo plano. ' +
      'Recorrente nao e escrito enquanto o FNC-184 nao subir — nao e erro, e um ' +
      'conjunto que migra depois, com o mesmo comando.</div>';
  }

  if (g.length){
    html += '<div class="scroll"><table><thead><tr><th>Grupo</th>' +
      '<th class="num">Lancamentos</th><th class="num">Valor</th><th>Por que</th>' +
      '</tr></thead><tbody>' + g.map(x =>
        '<tr><td>' + esc(rotuloGrupo(x)) + '</td>' +
        '<td class="num">' + (x.bills || 0) + '</td>' +
        '<td class="num">' + brl(x.totalAmount) + '</td>' +
        '<td class="muted">' + esc(x.why || x.reason || '') + '</td></tr>').join('') +
      '</tbody></table></div>';
  }

  const motivos = Object.keys(bloq);
  if (motivos.length){
    html += '<h2 style="margin-top:14px">Nao vai migrar</h2><div class="scroll">' +
      '<table><thead><tr><th>Motivo</th><th class="num">Lancamentos</th>' +
      '<th class="num">Valor</th><th>O que significa</th></tr></thead><tbody>' +
      motivos.map(m =>
        '<tr><td class="mono">' + esc(m) + '</td><td class="num">' + bloq[m].n +
        '</td><td class="num">' + brl(bloq[m].v) + '</td><td class="muted">' +
        esc(MOTIVOS[m] || 'Sem explicacao cadastrada.') +
        '</td></tr>').join('') + '</tbody></table></div>';
  }
  document.getElementById('aprovacao').innerHTML = html;
}

/* ---------- cauda ---------- */
function tituloDe(cl){
  if (cl.by === 'company+fingerprint') return cl.fingerprint + ' — ' + nome(cl.companyKey);
  if (cl.by === 'company') return nome(cl.companyKey) + ' (sem descricao util)';
  if (cl.by === 'fingerprint') return cl.fingerprint;
  if (cl.by === 'element') return 'elemento ' + (cl.elementKeys || []).map(nome).join(', ');
  return 'sem sinal nenhum';
}

function previa(cl, d){
  const n = (cl.fromKeys || []).length || 1;
  if (!d || d.acao === 'adiar') return 'Nada muda no de/para. Volta na proxima rodada.';
  if (d.acao === 'manter') return cl.count + ' override(s) com keep:true.';
  if (cl.by === 'none') return cl.count + ' override(s) por billKey — sem sinal para virar regra.';
  const when = {'company+fingerprint':'companyKeys + descriptionFingerprint',
    'company':'companyKeys', 'fingerprint':'descriptionFingerprint',
    'element':'elementKeys'}[cl.by];
  return n + ' regra(s) (uma por categoria de origem), when: ' + when + '.';
}

function cartao(cl, i){
  const s = cl.suggestion || {}, sa = cl.sugestaoAssistente;
  const opcoes = [];
  if (s.toKey) opcoes.push({v:'sugestao', rot:'Aplicar sugestao: <b>' + esc(nomeCat(s.toKey)) +
    '</b>', src:s.source || 'none', ev:s.evidence, pre:!!s.prechecked});
  if (sa && sa.toKey) opcoes.push({v:'assistente', rot:'Palpite do assistente: <b>' +
    esc(nomeCat(sa.toKey)) + '</b>', src:'assistant', ev:sa.evidence, pre:false});
  return '<section class="card" id="c' + i + '" data-i="' + i + '">' +
    '<div class="row"><b>#' + (i+1) + '</b> <span>' + esc(tituloDe(cl)) + '</span>' +
    '<span class="grow"></span><span class="chip">' + cl.count + ' lancamentos</span>' +
    '<span class="chip">' + brl(cl.totalAmount) + '</span>' +
    '<span class="chip mono">' + esc(cl.by) + '</span></div>' +

    opcoes.map(o => {
      const f = FONTES[o.src] || FONTES.none;
      return '<div class="evid"><span class="chip ' + f[1] + '">' + esc(o.src) +
        ' — ' + esc(f[0]) + '</span><div class="muted" style="margin-top:4px">' +
        esc(o.ev || '') + '</div></div>';
    }).join('') +
    (opcoes.length ? '' : '<div class="evid muted">' + esc(s.evidence || '') + '</div>') +

    '<div style="margin-top:8px">' +
    opcoes.map(o => '<label class="opt"><input type="radio" name="d' + i + '" value="' +
      o.v + '"' + (o.pre ? ' checked' : '') + '><span>' + o.rot + '</span></label>').join('') +
    '<label class="opt"><input type="radio" name="d' + i + '" value="outra">' +
      '<span>Outra categoria</span></label>' +
    '<div style="padding-left:26px;display:none" data-campo="outra">' +
      '<input type="text" data-filtro placeholder="filtrar..." size="22"> ' +
      '<select data-select><option value="">— escolha —</option></select></div>' +
    '<label class="opt"><input type="radio" name="d' + i + '" value="manter">' +
      '<span>Manter na categoria antiga (de proposito)</span></label>' +
    '<div style="padding-left:26px;display:none" data-campo="manter">' +
      '<input type="text" data-why placeholder="por que fica? (obrigatorio)" size="52"></div>' +
    '<label class="opt"><input type="radio" name="d' + i + '" value="adiar">' +
      '<span>Decidir depois</span></label></div>' +

    '<div class="muted mono" data-previa style="margin-top:6px"></div>' +

    '<details style="margin-top:6px"><summary>' + (cl.samples || []).length +
    ' amostra(s) · origem: ' + esc((cl.fromKeys || []).map(nome).join(', ')) + '</summary>' +
    '<div class="scroll"><table><thead><tr><th>Data</th><th>Descricao</th>' +
    '<th class="num">Valor</th></tr></thead><tbody>' +
    (cl.samples || []).map(a => '<tr><td>' + esc(dia(a.entryDate)) + '</td><td>' +
      esc(a.description) + '</td><td class="num">' + brl(a.totalAmount) +
      '</td></tr>').join('') + '</tbody></table></div></details></section>';
}

function preencheSelect(sel, filtro){
  const f = (filtro || '').toLowerCase();
  const lista = cats.filter(c => !f || (c.nome + ' ' + (c.codigo || '')).toLowerCase().includes(f));
  sel.innerHTML = '<option value="">— escolha —</option>' + lista.slice(0, 400).map(c =>
    '<option value="' + esc(c.key) + '">' + esc(c.nome) +
    (c.codigo ? ' (' + esc(c.codigo) + ')' : '') + '</option>').join('');
}

function leCartao(i){
  const cl = clusters[i], no = document.getElementById('c' + i);
  const escolhido = no.querySelector('input[name="d' + i + '"]:checked');
  no.querySelector('[data-campo="outra"]').style.display =
    escolhido && escolhido.value === 'outra' ? '' : 'none';
  no.querySelector('[data-campo="manter"]').style.display =
    escolhido && escolhido.value === 'manter' ? '' : 'none';
  if (!escolhido){ delete decisoes[cl.cluster]; }
  else {
    const v = escolhido.value;
    /* `billKeys` so entra quando a decisao vira OVERRIDE (manter, ou cluster sem
       sinal). Decisao que vira regra nao precisa da lista, e carrega-la faria o
       arquivo de decisoes ter dezenas de milhares de chaves — inutilizando o
       fallback de copiar e colar. */
    const chaves = cl.billKeys || [];
    const base = {cluster:cl.cluster, by:cl.by, fromKeys:cl.fromKeys || [],
      companyKey:cl.companyKey || null, fingerprint:cl.fingerprint || '',
      elementKeys:cl.elementKeys || [], count:cl.count, why:''};
    if (v === 'adiar'){ delete decisoes[cl.cluster]; }
    else if (v === 'manter'){
      const why = no.querySelector('[data-why]').value.trim();
      if (why) decisoes[cl.cluster] = {...base, acao:'manter', toKey:null, toNome:null,
        origem:'escolha-manual', sugestaoSource:null, why, billKeys:chaves};
      else delete decisoes[cl.cluster];
    } else {
      let k = null, origem = 'escolha-manual', src = null;
      if (v === 'sugestao'){ k = (cl.suggestion || {}).toKey; origem = 'sugestao';
        src = (cl.suggestion || {}).source; }
      else if (v === 'assistente'){ k = (cl.sugestaoAssistente || {}).toKey;
        origem = 'sugestao-assistente'; src = 'assistant'; }
      else { k = no.querySelector('[data-select]').value || null; }
      if (k) decisoes[cl.cluster] = {...base, acao:'migrar', toKey:k, toNome:nomeCat(k),
        origem, sugestaoSource:src, ...(cl.by === 'none' ? {billKeys:chaves} : {})};
      else delete decisoes[cl.cluster];
    }
  }
  const d = decisoes[cl.cluster];
  no.classList.toggle('decidido', !!d);
  no.querySelector('[data-previa]').textContent = previa(cl, d);
  atualiza();
}

function atualiza(){
  const n = Object.keys(decisoes).length;
  const cobertos = Object.values(decisoes).reduce((a, d) => a + (d.count || 0), 0);
  const total = clusters.reduce((a, c) => a + (c.count || 0), 0);
  document.getElementById('hProg').textContent =
    n + '/' + clusters.length + ' clusters · ' + cobertos + '/' + total + ' lancamentos';
  document.getElementById('hBar').style.width =
    (total ? Math.round(cobertos * 100 / total) : 0) + '%';
  document.getElementById('fResumo').textContent = n + ' decisao(oes)';
  document.getElementById('btBaixar').disabled =
    !document.getElementById('revisei').checked || n === 0;
}

function payload(){
  return JSON.stringify({version:1, plano:D.planoArquivo || meta.planFile || '',
    planHash:meta.planHash || '', farm:meta.farm || '',
    revisouAgregado:document.getElementById('revisei').checked,
    decisoes:Object.values(decisoes)}, null, 2);
}

/* ---------- bootstrap ---------- */
document.getElementById('hFarm').textContent = meta.farm || '(fazenda?)';
document.getElementById('hEnv').textContent = meta.env || '(env?)';
/* Hash truncado na tela (o botao copia inteiro): 71 caracteres empurrariam a
   barra para fora em tela estreita, e ninguem le hash com o olho. */
document.getElementById('hHash').textContent =
  (meta.planHash || '').slice(0, 22) + ((meta.planHash || '').length > 22 ? '...' : '');
document.getElementById('hHash').title = meta.planHash || '';
document.getElementById('tituloCauda').textContent =
  'A cauda — ' + clusters.length + ' grupo(s) sem regra';
pintaAprovacao();
document.getElementById('cauda').innerHTML = clusters.map(cartao).join('');

clusters.forEach((cl, i) => {
  const no = document.getElementById('c' + i);
  preencheSelect(no.querySelector('[data-select]'), '');
  no.addEventListener('input', e => {
    if (e.target.matches('[data-filtro]'))
      preencheSelect(no.querySelector('[data-select]'), e.target.value);
    leCartao(i);
  });
  no.addEventListener('change', () => leCartao(i));
  leCartao(i);
});

document.getElementById('revisei').addEventListener('change', atualiza);
document.getElementById('btCopiarHash').onclick = () =>
  navigator.clipboard.writeText(meta.planHash || '');
document.getElementById('btCopiar').onclick = () =>
  navigator.clipboard.writeText(payload());
document.getElementById('btBaixar').onclick = () => {
  const nome = (D.planoArquivo || 'plano').replace(/[\\/]/g, '_');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([payload()], {type:'application/json'}));
  a.download = 'decisoes-' + nome + '.json';
  a.click();
  URL.revokeObjectURL(a.href);
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
