/* श्रीमद्भगवद्गीता — भाष्यव्याख्यासङ्ग्रहः. One verse per page (#<chapter>.<verse>; .0 = upodghāta). */
(() => {
  const BHASHYAS = [
    ['shankara', 'शाङ्करभाष्यम्'], ['sridhara', 'श्रीधरी'], ['nilakantha', 'नीलकण्ठी'], ['madhusudana', 'मधुसूदनी']];
  const TIKAS = [['tika', 'आनन्दगिरिटीका'], ['bhashyarka', 'भाष्यार्कप्रकाशः'], ['dhanapati', 'भाष्योत्कर्षदीपिका']];
  const LABEL = Object.fromEntries([...BHASHYAS, ...TIKAS]);
  const DIG = '०१२३४५६७८९';
  const deva = n => String(n).replace(/\d/g, d => DIG[d]);
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const $ = s => document.querySelector(s);

  const store = {
    get(k, d) { try { const v = localStorage.getItem('bg-' + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
    set(k, v) { try { localStorage.setItem('bg-' + k, JSON.stringify(v)); } catch { /* private mode */ } }
  };
  const state = {
    bh: store.get('bh', 'shankara'), tikas: new Set(store.get('tikas', ['tika'])),
    parshve: store.get('parshve', false), pada: store.get('pada', false),
    script: store.get('script', 'devanagari'), size: store.get('size', 20), ch: 1, v: 0
  };

  let index = null;
  const cache = {};
  function load(file) {
    if (!cache[file]) cache[file] = fetch('data/' + file).then(r => { if (!r.ok) throw new Error(file); return r.json(); });
    return cache[file];
  }
  const pad2 = n => String(n).padStart(2, '0');
  const chFile = ch => `ch-${pad2(ch)}.json`;
  const sideFile = (ch, side) => `ch-${pad2(ch)}-${side}.json`;

  /* ---------- text ---------- */
  function item(x) {
    if (typeof x === 'string') return esc(x);
    return `<span class="w${x[2] ? ' m' : ''}"><span class="sj">${esc(x[0])}</span><span class="pd">${esc(x[1])}</span></span>`;
  }
  function run(r) {
    const body = r.slice(1).map(item).join('');
    if (r[0] === 'R') return `<span class="ref">${body}</span>`;
    return r[0] ? `<span class="k-${r[0]}">${body}</span>` : body;
  }
  const paras = (ps, cls = '') => (ps || []).map(p => `<p class="original ${cls}">${p.map(run).join('')}</p>`).join('');

  function mulaBox(ch, verse) {
    const sandhi = verse.lines.map(l => `<p>${esc(l)}</p>`).join('');
    const pada = (verse.pada.length ? verse.pada : verse.lines).map(l => `<p>${esc(l)}</p>`).join('');
    return `<div class="mula-box" id="m-${ch}-${verse.v}">${verse.uvaca ? `<p class="uvaca">${esc(verse.uvaca)}</p>` : ''}` +
      `<div class="sandhi-lines">${sandhi}</div><div class="pada-lines">${pada}</div>` +
      `<span class="verse-ref">${deva(ch)}।${deva(verse.v)}</span></div>`;
  }
  function tikaBlocks(comms, v, zone) {
    return TIKAS.filter(([k]) => state.tikas.has(k) && comms[k]).map(([k, label]) => {
      const blocks = (comms[k][v] || []).filter(b => b.zone === zone);
      if (!blocks.length) return '';
      return `<details class="vy-block" open data-side="${k}"><summary>${label}</summary>${blocks.map(b => paras(b.paras)).join('')}</details>`;
    }).join('');
  }
  const pair = (left, right) => `<div class="pair"><div class="left">${left}</div><div class="right">${right}</div></div>`;

  /* ---------- page ---------- */
  async function render() {
    const { ch, v } = state;
    const status = $('#status');
    status.hidden = false;
    let base;
    try { base = await load(chFile(ch)); } catch { status.innerHTML = '<p>पाठः न लब्धः। पुनः प्रयतताम्।</p>'; return; }
    const verse = base.verses.find(x => x.v === v) || base.verses[0];
    state.v = verse.v;
    const need = state.bh === 'shankara' ? [...state.tikas] : (state.bh ? [state.bh] : []);
    const comms = {};
    await Promise.all(need.map(k => load(sideFile(ch, k)).then(d => { comms[k] = d; }).catch(() => { comms[k] = {}; })));
    if (ch !== state.ch || verse.v !== state.v) return; // the reader moved on meanwhile
    const key = String(verse.v);
    let html = `<h1 class="chapter-heading">${esc(base.head)}</h1><p class="chapter-sub">${esc(base.name)}</p>`;
    if (state.bh === 'shankara') {
      if (verse.v === 0) {
        html += pair(`<p class="bh-label">उपोद्घातः</p>${paras(verse.bh) || '<p class="empty-note">अत्र शाङ्करभाष्ये उपोद्घातः नास्ति।</p>'}`,
          tikaBlocks(comms, key, 'pre') + tikaBlocks(comms, key, 'main'));
      } else {
        if (verse.pre.length || tikaBlocks(comms, key, 'pre')) html += pair(paras(verse.pre, 'avatarika'), tikaBlocks(comms, key, 'pre'));
        html += pair(mulaBox(ch, verse), '');
        const bh = verse.bh.length ? paras(verse.bh) : '<p class="empty-note">अस्य श्लोकस्य शाङ्करभाष्यं नास्ति।</p>';
        html += pair(bh, tikaBlocks(comms, key, 'main'));
      }
    } else if (state.bh) {
      const blocks = (comms[state.bh] || {})[key] || [];
      const body = blocks.length ? blocks.map(b => paras(b.paras)).join('')
        : `<p class="empty-note">अत्र ${LABEL[state.bh]} नास्ति।</p>`;
      html += pair(verse.v === 0 ? '' : mulaBox(ch, verse), `<div class="vy-main"><p class="bh-label">${LABEL[state.bh]}${verse.v === 0 ? ' — उपोद्घातः' : ''}</p>${body}</div>`);
    } else if (verse.v !== 0) {
      html += mulaBox(ch, verse);
    }
    const last = base.verses[base.verses.length - 1].v === verse.v;
    if (last && base.colophon.length && state.bh === 'shankara') html += `<div class="colophon">${paras(base.colophon)}</div>`;
    html += pager(ch, verse.v);
    const content = $('#content');
    content.innerHTML = html;
    transliterate(content);
    status.hidden = true;
    document.title = `${verse.v ? `${deva(ch)}।${deva(verse.v)}` : `${deva(ch)} · उपोद्घातः`} — श्रीमद्भगवद्गीता`;
    $('#as-link').href = `https://advaitasharada.sringeri.net/read/bhagavadgita-bhashya/${ch}/` + (verse.v ? `#BG_C${pad2(ch)}_V${pad2(verse.v)}` : '');
    sidebar();
    store.set('last', `${ch}.${verse.v}`);
  }

  /* ---------- navigation ---------- */
  function flat() { return index.flatMap(c => c.verses.map(v => [c.ch, v])); }
  function label(ch, v) { return v ? `${deva(ch)}।${deva(v)}` : `${deva(ch)} · उपोद्घातः`; }
  function pager(ch, v) {
    const all = flat(), i = all.findIndex(([c, x]) => c === ch && x === v);
    const prev = all[i - 1], next = all[i + 1];
    return `<nav class="unit-pager">${prev ? `<a href="#${prev[0]}.${prev[1]}">← ${label(...prev)}</a>` : '<span></span>'}` +
      `${next ? `<a href="#${next[0]}.${next[1]}">${label(...next)} →</a>` : '<span></span>'}</nav>`;
  }
  function sidebar() {
    const sel = $('#chapter-select');
    if (!sel.options.length) sel.innerHTML = index.map(c => `<option value="${c.ch}">${deva(c.ch)} — ${esc(c.name)}</option>`).join('');
    sel.value = String(state.ch);
    const c = index.find(x => x.ch === state.ch);
    $('#verse-list').innerHTML = c.verses.map(v => v === 0
      ? `<a class="lesson-link source-intro${v === state.v ? ' active' : ''}" href="#${c.ch}.0">उपोद्घातः</a>`
      : `<a class="lesson-link${v === state.v ? ' active' : ''}" href="#${c.ch}.${v}" aria-label="श्लोकः ${deva(v)}">${deva(v)}</a>`).join('');
    transliterate($('#sidebar'));
  }
  function route() {
    const m = /^#(\d+)\.(\d+)$/.exec(location.hash);
    let ch = 1, v = 0;
    if (m) { ch = +m[1]; v = +m[2]; } else {
      const last = /^(\d+)\.(\d+)$/.exec(store.get('last', '1.0')); if (last) { ch = +last[1]; v = +last[2]; }
    }
    const c = index.find(x => x.ch === ch) || index[0];
    state.ch = c.ch;
    state.v = c.verses.includes(v) ? v : c.verses[0];
    closeMenu();
    render().then(() => { window.scrollTo({ top: 0, behavior: 'instant' }); });
  }

  /* ---------- controls ---------- */
  function chips() {
    const bhRow = $('#bhashya-row'), tkRow = $('#tika-row');
    bhRow.innerHTML = '<span>भाष्यम् —</span>' + BHASHYAS.map(([k, l]) =>
      `<button class="bh-chip" data-bh="${k}" aria-pressed="${state.bh === k}">${l}</button>`).join('') +
      (state.bh && state.bh !== 'shankara' ? `<button class="parshve" aria-pressed="${state.parshve}" title="मूलं वामतः, व्याख्या दक्षिणतः">पार्श्वे</button>` : '');
    tkRow.hidden = state.bh !== 'shankara';
    tkRow.innerHTML = '<span>व्याख्याः —</span>' + TIKAS.map(([k, l]) =>
      `<button data-tika="${k}" aria-pressed="${state.tikas.has(k)}">${l}</button>`).join('') +
      `<button class="parshve" aria-pressed="${state.parshve}" title="भाष्यं वामतः, व्याख्याः दक्षिणतः">पार्श्वे</button>`;
    document.body.classList.toggle('parshve', state.parshve && !!state.bh);
    transliterate($('#chips'));
  }
  function bindControls() {
    $('#chips').addEventListener('click', e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.bh) { state.bh = state.bh === b.dataset.bh ? '' : b.dataset.bh; store.set('bh', state.bh); }
      else if (b.dataset.tika) {
        const k = b.dataset.tika; state.tikas.has(k) ? state.tikas.delete(k) : state.tikas.add(k); store.set('tikas', [...state.tikas]);
      } else if (b.classList.contains('parshve')) { state.parshve = !state.parshve; store.set('parshve', state.parshve); }
      chips(); render();
    });
    const pada = $('#pada-toggle');
    const applyPada = () => { document.body.classList.toggle('pada', state.pada); pada.setAttribute('aria-pressed', state.pada); };
    pada.addEventListener('click', () => { state.pada = !state.pada; store.set('pada', state.pada); applyPada(); });
    applyPada();
    const applySize = () => document.documentElement.style.setProperty('--font-size', state.size + 'px');
    $('#size-down').addEventListener('click', () => { state.size = Math.max(15, state.size - 1); store.set('size', state.size); applySize(); });
    $('#size-up').addEventListener('click', () => { state.size = Math.min(30, state.size + 1); store.set('size', state.size); applySize(); });
    applySize();
    const script = $('#script');
    script.value = state.script;
    script.addEventListener('change', () => { state.script = script.value; store.set('script', state.script); chips(); render(); });
    $('#chapter-select').addEventListener('change', e => { location.hash = `#${e.target.value}.${index.find(c => c.ch === +e.target.value).verses[0]}`; });
    $('#menu').addEventListener('click', () => {
      const open = !$('#sidebar').classList.contains('open');
      $('#sidebar').classList.toggle('open', open); $('#menu').setAttribute('aria-expanded', open);
    });
    document.addEventListener('keydown', e => {
      if (e.target.closest('input,select,textarea') || e.metaKey || e.ctrlKey || e.altKey) return;
      const a = document.querySelectorAll('.unit-pager a');
      if (e.key === 'ArrowLeft') { const p = [...a].find(x => x.textContent.startsWith('←')); if (p) location.hash = p.getAttribute('href'); }
      if (e.key === 'ArrowRight') { const n = [...a].find(x => x.textContent.endsWith('→')); if (n) location.hash = n.getAttribute('href'); }
    });
    window.addEventListener('hashchange', route);
  }
  function closeMenu() { $('#sidebar').classList.remove('open'); $('#menu').setAttribute('aria-expanded', 'false'); }

  /* display-only transliteration: the data stays in Devanagari */
  function transliterate(root) {
    document.body.dataset.script = state.script;
    if (state.script === 'devanagari' || !window.Sanscript) return;
    const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walk.nextNode()) {
      const n = walk.currentNode;
      if (n.parentElement.closest('[data-no-transliterate],select')) continue;
      if (/[ऀ-ॿ]/.test(n.nodeValue)) n.nodeValue = Sanscript.t(n.nodeValue, 'devanagari', state.script);
    }
  }

  document.addEventListener('DOMContentLoaded', async () => {
    try { index = await load('index.json'); } catch { $('#status').innerHTML = '<p>अनुक्रमणिका न लब्धा।</p>'; return; }
    bindControls();
    chips();
    route();
  });
})();
