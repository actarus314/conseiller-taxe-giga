(() => {
  // Conseiller pour taxe-au-giga.fr : lit l'état affiché par le jeu, ne clique et n'achète jamais rien.
  if (!/^(taxe-au-giga\.fr|localhost|127\.0\.0\.1)$/.test(location.hostname)) { alert('Conseiller : à lancer sur taxe-au-giga.fr'); return; }
  if (window.__tagAdv) { window.__tagAdv.stop(); return; }

  const VERSION = '2.15'; // écrite par dev/outils/build.py <version>

  // Barème recopié du code du jeu le 03/11/2026 (build 2026-11-03h : Décret porté à +100000 par clic).
  // prix = arrondi_sup(base × 1,15^possédés) ; rate = visites/s ; click = visites en plus par clic ; pct = part de la production ajoutée à chaque clic.
  const P = [
    ['doigt', 'Doigt de fonctionnaire', 10, 0, 2], ['stagiaire', 'Stagiaire F5', 15, 0.5], ['chat', 'Chat sur le clavier', 100, 2],
    ['hamster', 'Hamster-routeur', 600, 8], ['souris', 'Souris à molette fiscale', 500, 0, 20], ['bot', 'Ferme de bots', 6000, 40],
    ['fax', 'Fax ministériel', 6e4, 200], ['commission', 'Commission à 11 contre 10', 6e5, 1100], ['gant', 'Gant de clic en or massif', 15e4, 0, 600],
    ['satellite', 'Satellite de taxation', 5e6, 3000], ['trounoir', 'Trou noir fiscal', 7.5e7, 15000], ['tampon', 'Tampon « Adopté » automatique', 2e7, 0, 40000],
    ['mainetat', 'Main de l’État', 5e8, 0, 0, 0.01, 1], ['decret', 'Décret d’application', 1e9, 0, 100000], ['datacenter', 'Datacenter sur le Vieux-Port', 1e9, 60000],
    ['ia', 'IA qui lit la gazette en boucle', 1.2e10, 250000], ['recommande', 'Clic en recommandé avec AR', 5e9, 0, 0, 0.02, 1],
    ['art493', 'Article 49.3', 5e10, 0, 0, 0.04, 1], ['ordonnance', 'Ordonnance du clic', 5e10, 0, 200000], ['multivers', 'Gazette du multivers', 1.5e11, 1.2e6],
    ['niche', 'Niche fiscale du clic', 5e11, 0, 0, 0.08, 1], ['quantique', 'Taxe quantique', 2e12, 6e6], ['directive', 'Directive européenne du clic', 2.5e12, 0, 3e6],
    ['mondial', 'Amendement mondial', 5e12, 0, 0, 0.15, 1],
  ].map(([id, name, base, rate = 0, click = 0, pct = 0, max = 0]) => ({ id, name, base, rate, click, pct, max }));
  const cost = (u, n) => Math.ceil(u.base * Math.pow(1.15, n));
  // Limites du serveur : 760 clics comptés par minute, 18000 par heure (au-delà, les clics ne rapportent rien)
  const LIM_MIN = 760, LIM_H = 18000, CPS_MAX = LIM_MIN / 60, HORIZON = 900; // horizon de 15 min pour répartir le reste du quota horaire
  // minutes tenues au plafond de clics/min avant que le serveur y voie un autoclic (clics alors ignorés autant de minutes)
  const AUTOCLIC = 10;
  // multiplicateurs des bonus de la Facture dorée : production ×3, clics ×10
  const FRENESIE = 3, RAFALE = 10;
  // part de la production ajoutée à chaque clic sans aucun bonus en %
  const PCT_BASE = 0.01;
  // rafraîchissement (ms), sauvegarde du compteur (ms), achats planifiés, largeur d'écran « téléphone » (px)
  const TICK = 250, SAVE_EVERY = 5000, PLAN_LEN = 8, PHONE = 600;
  // écart relatif toléré entre le modèle et l'affichage du jeu (prix, puissance de clic)
  const DRIFT = 0.01;
  const CPS_MIN = 0.1, CPS_DEFAULT = 5;
  const clampCps = v => Math.min(CPS_MAX, Math.max(CPS_MIN, parseFloat(v) || CPS_DEFAULT));

  // Production d'un parc : passive (rate) et par clic, comme clickPower() du jeu
  const prodRate = own => P.reduce((s, u) => s + u.rate * (own[u.id] || 0), 0);
  // rate : prodRate(own), déjà calculée par l'appelant
  const clickPow = (own, rate = prodRate(own)) => Math.floor(1 + P.reduce((s, u) => s + u.click * (own[u.id] || 0), 0) + (PCT_BASE + P.reduce((s, u) => s + u.pct * (own[u.id] || 0), 0)) * rate);
  const income = (own, cps) => { const r = prodRate(own); return r + (cps > 0 ? clickPow(own, r) * cps : 0); };

  const $ = s => document.querySelector(s);
  const num = s => {
    if (!s) return NaN;
    const t = s.replace(/[\s  💰]/g, '').replace(',', '.');
    const m = t.match(/^([\d.]+)(billions?|Md|M)?$/); if (!m) return NaN;
    return parseFloat(m[1]) * (m[2] === 'Md' ? 1e9 : m[2] === 'M' ? 1e6 : m[2] ? 1e12 : 1);
  };
  // nombres au point décimal, sans séparateur de milliers
  const fmt = n => n < 1e6 ? String(Math.round(n)) : n < 1e9 ? (n / 1e6).toFixed(2) + ' M' : n < 1e12 ? (n / 1e9).toFixed(2) + ' Md' : (n / 1e12).toFixed(2) + ' T';
  const dec1 = n => n.toFixed(1).replace(/\.0$/, '');
  const cpsTxt = n => n < 1 ? n.toFixed(2) : dec1(n); // cadence : deux décimales sous 1 clic/s
  const pad = n => String(n).padStart(2, '0');
  // compte à rebours à la seconde jusqu'à 1 h, puis heures et minutes
  const dur = s => { if (!isFinite(s)) return 'après quelques clics'; if (s < 1) return 'moins d’1 s'; const k = Math.ceil(s);
    return k < 60 ? k + ' s' : k < 3600 ? Math.floor(k / 60) + ' min ' + pad(k % 60) + ' s' : Math.floor(k / 3600) + ' h ' + pad(Math.floor(k % 3600 / 60)); };
  const durMin = s => s < 3600 ? Math.round(s / 60) + ' min' : Math.floor(s / 3600) + ' h ' + pad(Math.floor(s % 3600 / 60));
  // créé une fois : toLocaleTimeString(options) en recrée un à chaque appel (72 µs)
  const hhmm = new Intl.DateTimeFormat('fr-FR', { hour: '2-digit', minute: '2-digit' });
  const clock = s => !isFinite(s) ? '—' : hhmm.format(Date.now() + s * 1000);
  const store = (k, v) => { try { if (v === undefined) return localStorage.getItem('tagAdv-' + k); localStorage.setItem('tagAdv-' + k, v); } catch (e) { return null; } };

  // Réglages : Auto (moyenne mesurée, par défaut), Passif (aucun clic) ou Actif (cadence fixée)
  let mode = ['auto', 'passif', 'actif'].includes(store('mode')) ? store('mode') : 'auto';
  let cpsPlan = clampCps(store('cps'));

  // Mesure des clics réels sur TAXER (bouton principal, bouton flottant et bouton du mode mini).
  // Mode Auto : moyenne des clics sur le temps de jeu observé des 3 dernières heures (minutes où le panneau
  // tournait), comptée sur 30 min au moins : des séries de clics espacées donnent une cadence stable, valable
  // pendant et entre les séries, qui est celle qui rembourse un bonus de clic.
  // Série en cours (affichage seul) : clics de la dernière minute, interrompue après 8 s sans clic.
  // Compteur par minute (0 = minute observée sans clic), gardé dans le navigateur pour survivre à un rechargement.
  const WIN = 60e3, STOP = 8e3, recent = [];
  const MOY_MIN = 180, MOY_PLANCHER = 30; // fenêtre de la moyenne et durée minimale comptée, en minutes
  let perMin = {}; try { perMin = JSON.parse(store('clics') || '{}') || {}; } catch (e) { perMin = {}; }
  // début de l'observation minute par minute (v2.14) : les minutes plus anciennes, notées par les versions qui ne
  // gardaient que les minutes avec clics, comptent pour le quota horaire mais pas pour la moyenne
  let since = parseInt(store('vu'), 10); if (!Number.isFinite(since)) { since = Math.floor(Date.now() / 60e3); store('vu', String(since)); }
  const onClick = e => {
    if (!e.isTrusted || !e.target.closest || !e.target.closest('#taxBtn, #stickyTax, #mTax')) return;
    const t = Date.now(); recent.push(t); const m = Math.floor(t / 60e3); perMin[m] = (perMin[m] || 0) + 1;
  };
  document.addEventListener('click', onClick, true);
  // Mode mini du jeu : TAXER dans une petite fenêtre, « image dans l'image » (Chrome, Edge), sinon fenêtre surgissante
  // nommée taxe-giga-mini. La première est retrouvée même ouverte avant le panneau ; la seconde seulement si elle
  // s'ouvre panneau ouvert (window.open est alors observé, sans rien changer à son résultat).
  const minis = new Set();
  const watchMini = w => { try { if (w && !minis.has(w)) { w.document.addEventListener('click', onClick, true); minis.add(w); } } catch (e) { /* fenêtre fermée */ } };
  const DPIP = window.documentPictureInPicture, onPip = e => watchMini(e.window);
  if (DPIP) { DPIP.addEventListener('enter', onPip); watchMini(DPIP.window); }
  const winOpen = window.open;
  const openSpy = function (...a) { const w = winOpen.apply(this, a); if (a[1] === 'taxe-giga-mini') watchMini(w); return w; };
  window.open = openSpy;
  function cadence() {
    const now = Date.now(), m0 = Math.floor(now / 60e3);
    while (recent.length && recent[0] < now - WIN) recent.shift();
    if (!(m0 in perMin)) perMin[m0] = 0; // minute observée
    let hour = 0, tot = 0, seen = 0;
    for (const k in perMin) {
      if (k <= m0 - MOY_MIN) { delete perMin[k]; continue; }
      if (k > m0 - 60) hour += perMin[k];
      if (k >= since) { tot += perMin[k]; seen++; }
    }
    const obs = (seen - 1) * 60 + (now % 60e3) / 1000; // la minute en cours compte pour ce qui en est écoulé
    const avg = tot / Math.max(obs, MOY_PLANCHER * 60), minute = perMin[m0];
    const out = { avg, obs, tot, rate: 0, idle: Infinity, hour, minute };
    if (!recent.length) return out;
    out.idle = now - recent[recent.length - 1];
    if (out.idle > STOP) return out;
    let i = recent.length - 1; while (i > 0 && recent[i] - recent[i - 1] <= STOP) i--; // début de la série en cours
    out.rate = (recent.length - i) / (Math.max(3000, now - recent[i]) / 1000);
    return out;
  }
  const ivSave = setInterval(() => store('clics', JSON.stringify(perMin)), SAVE_EVERY);

  // Cagnotte : l'affichage du jeu est arrondi (10000 près en M, 10 M près en Md, 10 Md près en billions). La sauvegarde du jeu
  // (exacte, réécrite toutes les 5 s), plus la production et les clics TAXER faits depuis son heure, donne
  // la valeur fine ; elle est gardée dans l'intervalle d'arrondi de l'affichage, qui reste la référence.
  function walletNow(own, boost) {
    const txt = ($('#wallet') || {}).textContent || '', shown = num(txt);
    if (!Number.isFinite(shown)) return shown;
    const [lo, hi] = /billion/.test(txt) ? [shown - 5e9, shown + 5e9] : /Md/.test(txt) ? [shown - 5e6, shown + 5e6] : /M/.test(txt) ? [shown - 5e3, shown + 5e3] : [shown, shown + 1];
    let est = NaN;
    try {
      const sv = JSON.parse(localStorage.getItem('taxe-giga-partie-v1') || 'null');
      if (sv && Number.isFinite(sv.wallet) && sv.t) {
        const since = recent.filter(t => t > sv.t).length; // clics comptés par le panneau depuis la sauvegarde
        est = sv.wallet + prodRate(own) * (boost.fz ? FRENESIE : 1) * Math.max(0, Date.now() - sv.t) / 1000 + since * clickPow(own) * (boost.rf ? RAFALE : 1);
      }
    } catch (e) {}
    return Number.isFinite(est) ? Math.min(hi, Math.max(lo, est)) : shown;
  }

  // Lecture de l'état affiché
  function read() {
    const items = [], drift = [], own = {};
    for (const u of P) {
      const b = $(`#shop button.item[data-id="${u.id}"]`);
      if (!b) continue; // pas encore débloqué
      const ownTxt = (b.querySelector('.own') || {}).textContent || '';
      const done = ownTxt.includes('✓');
      const n = done ? 1 : parseInt(ownTxt.replace(/\D/g, ''), 10) || 0;
      own[u.id] = n;
      if (!done) {
        const shown = num((b.querySelector('.price') || {}).textContent), c = cost(u, n);
        if (shown && Math.abs(shown - c) / c > DRIFT) drift.push(u.name);
        items.push({ u, el: b });
      }
    }
    // la puissance de clic affichée par le jeu sert de contrôle du modèle
    const pcTxt = ($('#perClick') || {}).textContent || '', pc = /volontaire/.test(pcTxt) ? 0 : parseInt(pcTxt.replace(/\D/g, ''), 10); // mode sérieux : rien à contrôler
    if (pc && items.length && Math.abs(pc - clickPow(own)) > Math.max(2, pc * DRIFT)) drift.push('puissance de clic');
    // bonus de la Facture dorée en cours, lus dans le bandeau du jeu : Frénésie (production ×3) ou Rafale (clics ×10)
    const chip = $('#buffChip'), ct = chip && !chip.hidden ? chip.textContent : '', left = (ct.match(/(\d+)\s*s\b/) || [])[1];
    const boost = { fz: /Frénésie/.test(ct) && left ? +left : 0, rf: /Rafale/.test(ct) && left ? +left : 0 };
    const gold = $('#goldBill'); // Facture dorée à l'écran
    return { items, own, drift, wallet: walletNow(own, boost), boost, goldUp: !!gold && !gold.hidden };
  }

  // Revenu à l'instant t (s) : Frénésie = production ×3 pendant fz s, Rafale = clics ×10 pendant rf s
  const rateAt = (own, cps, b, t) => { const r = prodRate(own); return r * (t < b.fz ? FRENESIE : 1) + (cps > 0 ? clickPow(own, r) * cps * (t < b.rf ? RAFALE : 1) : 0); };
  // Morceaux de temps où le revenu est constant : [0, fin du 1er bonus], [.., fin du 2e], [.., ∞)
  const pieces = b => [...new Set([b.fz, b.rf].filter(x => x > 0))].sort((x, y) => x - y).concat(Infinity);
  // Revenu de chaque morceau de temps, calculé une fois par étape du plan : [{ end, rate }]
  const segments = (own, cps, b) => { let start = 0; return pieces(b).map(end => { const seg = { end, rate: rateAt(own, cps, b, start) }; start = end; return seg; }); };
  // temps pour gagner `amount`
  function earnTime(amount, segs) {
    if (amount <= 0) return 0;
    let t = 0;
    for (const { end, rate } of segs) {
      if (rate > 0 && amount <= rate * (end - t)) return t + amount / rate;
      if (end === Infinity) return Infinity;
      amount -= rate * (end - t); t = end;
    }
  }
  // visites gagnées pendant T s
  function earned(T, segs) {
    let t = 0, sum = 0;
    for (const { end, rate } of segs) { const e = Math.min(end, T); if (e > t) sum += rate * (e - t); t = e; if (t >= T) break; }
    return sum;
  }
  const after = (b, dt) => ({ fz: Math.max(0, b.fz - dt), rf: Math.max(0, b.rf - dt) });
  // Choix : le bonus qui minimise (attente avant de pouvoir le payer + temps pour qu'il se rembourse).
  function pick(items, own, w, cps, boost) {
    let best = null, bs = Infinity; const r0 = income(own, cps), segs = segments(own, cps, boost);
    for (const it of items) {
      const n = own[it.u.id] || 0; if (it.u.max && n >= it.u.max) continue;
      own[it.u.id] = n + 1; const g = income(own, cps) - r0; own[it.u.id] = n; if (g <= 0) continue;
      const c = cost(it.u, n), wait = earnTime(c - w, segs), s = wait + c / g;
      if (s < bs) { bs = s; best = { it, c, wait, segs }; }
    }
    return best;
  }
  function plan(st, cps, k) {
    // boost : Frénésie / Rafale en cours
    const own = { ...st.own }; let w = st.wallet, t = 0, boost = st.boost; const out = [];
    for (let i = 0; i < k; i++) {
      const best = pick(st.items, own, w, cps, boost); if (!best) break;
      const { it, c, wait, segs } = best, n = own[it.u.id] || 0;
      if (!isFinite(wait)) { out.push({ it, c, t: Infinity, n: n + 1 }); break; }
      w += earned(wait, segs) - c; boost = after(boost, wait); t += wait;
      own[it.u.id] = n + 1; out.push({ it, c, t, n: n + 1 });
    }
    return out;
  }

  // Interface
  // couleurs du panneau et de la marque : déclarées une seule fois (variables --tag*), sans toucher à celles du jeu
  const css = document.createElement('style');
  css.textContent = `
  #tagAdv,.tagAdvBest{--tagInk:#1a1a1a;--tagPaper:#fffbe6;--tagGo:#19d3a2}
  #tagAdv{position:fixed;right:12px;z-index:60;width:min(340px,calc(100vw - 24px));background:var(--tagPaper);color:var(--tagInk);
    border:3px solid var(--tagInk);border-radius:14px;box-shadow:5px 5px 0 var(--tagInk);font:14px/1.4 "Space Grotesk",system-ui,sans-serif}
  #tagAdv header{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:8px 12px;border-bottom:2px solid var(--tagInk);font-weight:700;user-select:none;cursor:move;touch-action:none}
  #tagAdv.gold header{background:#ffd23f}
  #tagAdv header .v{font:500 11px/1 "IBM Plex Mono",ui-monospace,Menlo,monospace;color:#555;margin-left:4px;text-decoration:underline;cursor:pointer}
  #tagAdv header .v:focus-visible{outline:2px solid var(--tagInk);outline-offset:2px}
  #tagAdv header button{all:unset;cursor:pointer;padding:0 4px;font-size:16px}
  #tagAdv .modes{display:flex;gap:6px;padding:8px 12px 0;flex-wrap:wrap;align-items:center}
  #tagAdv .modes button{all:unset;cursor:pointer;border:2px solid var(--tagInk);border-radius:8px;padding:3px 10px;font-weight:700;font-size:13px}
  #tagAdv .modes button[aria-pressed="true"]{background:var(--tagInk);color:var(--tagPaper)}
  #tagAdv .modes label{font-size:12px;display:flex;gap:4px;align-items:center;margin-left:auto}
  #tagAdv .modes label[hidden]{display:none}
  #tagAdv .modes input{width:46px;font:inherit;border:2px solid var(--tagInk);border-radius:6px;padding:1px 4px;background:#fff;color:var(--tagInk)}
  #tagAdv .now{padding:10px 12px;font-size:16px}
  #tagAdv .now b{display:block;font-size:18px}
  #tagAdv .now.go{background:var(--tagGo)}
  #tagAdv ol{margin:0;padding:6px 12px 10px 32px;font-size:13px}
  #tagAdv ol li{margin:2px 0}
  #tagAdv .ft{padding:6px 12px 8px;border-top:2px dashed var(--tagInk);font-size:12px;color:#555}
  #tagAdv .warn{padding:6px 12px;background:#ffb3d6;font-size:12px}
  #tagAdv.min .modes,#tagAdv.min ol,#tagAdv.min .ft{display:none}
  .tagAdvBest{outline:5px solid var(--tagGo)!important;outline-offset:2px;position:relative}
  .tagAdvBest::after{content:attr(data-adv);position:absolute;top:-12px;left:12px;background:var(--tagGo);color:var(--tagInk);border:2px solid var(--tagInk);
    border-radius:8px;padding:1px 8px;font:700 12px/1.4 "Space Grotesk",system-ui,sans-serif;pointer-events:none}`;
  document.head.appendChild(css);
  const box = document.createElement('div'); box.id = 'tagAdv';
  box.innerHTML = `<header><span><span class="t">🧮 Conseiller</span> <a class="v" href="https://github.com/actarus314/conseiller-taxe-giga" target="_blank" rel="noopener">v${VERSION}</a></span><span><button data-a="min" aria-label="Réduire">–</button><button data-a="x" aria-label="Fermer">✕</button></span></header>
    <div class="modes"><button data-m="auto">Auto</button><button data-m="passif">Passif</button><button data-m="actif">Actif</button>
      <label data-cps>clics/s prévus <input id="tagAdvCps" type="number" step="0.5"></label></div>
    <div class="warn" hidden></div><div class="now"></div><ol></ol><div class="ft"></div>`;
  document.body.appendChild(box);
  // téléphone : panneau réduit au conseil, la boutique reste visible
  if (innerWidth < PHONE) box.classList.add('min');
  const ui = { title: box.querySelector('header .t'), now: box.querySelector('.now'), warn: box.querySelector('.warn'), ol: box.querySelector('ol'), ft: box.querySelector('.ft') };
  // N'écrit dans le DOM que ce qui change : innerHTML recrée tous les nœuds même à contenu identique (recalcul de style et de mise en page à chaque tick)
  const shown = {};
  const put = (k, el, prop, v) => { if (shown[k] !== v) { el[prop] = v; shown[k] = v; } };
  const cpsIn = box.querySelector('#tagAdvCps'); cpsIn.min = CPS_MIN; cpsIn.max = CPS_MAX; cpsIn.value = cpsPlan;
  cpsIn.addEventListener('change', () => { cpsPlan = clampCps(cpsIn.value); cpsIn.value = cpsPlan; store('cps', cpsPlan); tick(); });
  const setMode = m => { mode = m; store('mode', m); box.querySelectorAll('[data-m]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.m === m))); box.querySelector('[data-cps]').hidden = m !== 'actif'; tick(); };
  box.addEventListener('click', e => {
    const a = e.target.dataset.a;
    if (a === 'min') box.classList.toggle('min'); if (a === 'x') stop();
    if (e.target.dataset.m) setMode(e.target.dataset.m);
  });

  let dragged = false; // déplacé à la main : il garde sa place
  // Position : en bas à droite, au-dessus du bouton TAXER flottant. S'il y couvrirait le grand bouton TAXER à l'écran
  // (à 1280 px de large, il est dans la colonne de droite ; sur téléphone, en bas de l'écran d'accueil) : en bas à
  // gauche, sinon en haut sous l'en-tête du jeu. Revue à chaque rafraîchissement (défilement, taille du panneau) ;
  // le DOM n'est réécrit que si elle change.
  const setStyle = (k, v) => { if (box.style[k] !== v) box.style[k] = v; };
  function place() {
    if (dragged) return;
    const st = $('#stickyTax'), h = st ? st.offsetHeight : 64, below = 24 + h + 18;
    const w = box.offsetWidth, hh = box.offsetHeight, hdr = document.querySelector('header'), up = Math.round((hdr ? hdr.getBoundingClientRect().bottom : 64) + 8);
    let pos = { side: 'right', top: null };
    const tb = $('#taxBtn'), t = tb && tb.getBoundingClientRect();
    if (t && t.width && t.bottom > 0 && t.top < innerHeight) {
      const hits = (l, y) => l < t.right && l + w > t.left && y < t.bottom && y + hh > t.top;
      const low = innerHeight - below - hh;
      pos = [{ side: 'right', top: null, l: innerWidth - 12 - w, y: low }, { side: 'left', top: null, l: 12, y: low }, { side: 'right', top: up, l: innerWidth - 12 - w, y: up }]
        .find(c => !hits(c.l, c.y)) || pos;
    }
    setStyle('top', pos.top == null ? 'auto' : pos.top + 'px');
    setStyle('bottom', pos.top == null ? `calc(${below}px + env(safe-area-inset-bottom, 0px))` : 'auto');
    setStyle('left', pos.side === 'left' ? '12px' : ''); setStyle('right', pos.side === 'left' ? 'auto' : '');
  }
  const hd = box.querySelector('header');
  // fin du glissement en cours (pointerup, pointercancel ou fermeture du panneau)
  let endDrag = null;
  hd.addEventListener('pointerdown', e => {
    if (e.target.closest('button, a')) return;
    if (endDrag) endDrag();
    const r = box.getBoundingClientRect(), dx = e.clientX - r.left, dy = e.clientY - r.top;
    const mv = ev => { dragged = true; box.style.left = Math.max(0, Math.min(innerWidth - r.width, ev.clientX - dx)) + 'px'; box.style.top = Math.max(0, Math.min(innerHeight - 40, ev.clientY - dy)) + 'px'; box.style.right = box.style.bottom = 'auto'; };
    const up = () => { removeEventListener('pointermove', mv); removeEventListener('pointerup', up); removeEventListener('pointercancel', up); endDrag = null; };
    endDrag = up; addEventListener('pointermove', mv); addEventListener('pointerup', up); addEventListener('pointercancel', up);
  });
  addEventListener('resize', place); place();

  let last = null;
  const unmark = () => { if (marked) { marked.classList.remove('tagAdvBest'); delete marked.dataset.adv; marked = null; } };
  const PFX = /^🟢 [^·]+ · /, baseTitle = () => document.title.replace(PFX, ''); let marked = null;
  function tick() {
    const st = last = read();
    place();
    box.classList.toggle('gold', st.goldUp || !!st.boost.rf); // la Facture dorée ne reste que 15 s à l'écran
    put('title', ui.title, 'textContent', st.goldUp ? '🧾 Facture dorée à cliquer !' : st.boost.rf ? `⚡ Rafale : cliquer ! (×${RAFALE}, ${st.boost.rf} s)` : '🧮 Conseiller');
    // Cadence retenue : la cadence voulue (moyenne mesurée en Auto, réglée en Actif), dans la limite de 760/min,
    // et du reste du quota horaire réparti sur 15 min quand il ne suffit plus.
    const cad = cadence(), left = Math.max(0, LIM_H - cad.hour), capped = left === 0;
    const want = mode === 'actif' ? cpsPlan : mode === 'auto' ? cad.avg : 0;
    const cps = Math.min(want, CPS_MAX, left / HORIZON);
    const why = !want || cps >= want - 0.05 ? '' : capped ? '' : cps < Math.min(want, CPS_MAX) - 0.05 ? `ramenée à ${cpsTxt(cps)} : reste ${left} clics sur le quota de l’heure` : `ramenée à ${dec1(CPS_MAX)}, plafond de ${LIM_MIN} clics par minute`;
    if (!Number.isFinite(st.wallet) || !$('#shop')) { put('now', ui.now, 'innerHTML', 'Boutique introuvable : recharger la page du jeu.'); return; }
    if (!st.items.length) { put('now', ui.now, 'innerHTML', 'Aucun bonus débloqué : cliquer sur TAXER.'); return; }
    put('warnHidden', ui.warn, 'hidden', !st.drift.length);
    if (st.drift.length) put('warn', ui.warn, 'textContent', `⚠️ Le jeu ne correspond plus au barème connu (${st.drift.join(', ')}) : il a peut-être changé ses règles, conseils à prendre avec prudence.`);
    const out = plan(st, cps, PLAN_LEN), first = out[0];
    if (!first || marked !== first.it.el) unmark();
    if (!first) return;
    const ready = !first.it.el.disabled; // le bouton du jeu fait foi pour « achetable maintenant »
    // le jeu peut réécrire les classes de la carte : la marque est reposée si elle a disparu
    const adv = ready ? '👉 À ACHETER' : '⏳ ' + dur(first.t);
    if (!first.it.el.classList.contains('tagAdvBest')) first.it.el.classList.add('tagAdvBest');
    if (first.it.el.dataset.adv !== adv) first.it.el.dataset.adv = adv;
    marked = first.it.el;
    put('nowClass', ui.now, 'className', 'now' + (ready ? ' go' : ''));
    put('now', ui.now, 'innerHTML', ready
      ? `Acheter maintenant<b>${first.it.u.name}</b>💰 ${fmt(first.c)} · devient ×${first.n}`
      : (isFinite(first.t) ? `Prochain achat dans ${dur(first.t)} (${clock(first.t)})` : 'Prochain achat après quelques clics') + `<b>${first.it.u.name}</b>💰 ${fmt(first.c)} · ne rien acheter d’autre d’ici là`);
    put('ol', ui.ol, 'innerHTML', out.slice(1).map(o =>
      `<li>${o.it.u.name} ×${o.n} · 💰 ${fmt(o.c)} · ${o.t < 1 ? 'tout de suite' : clock(o.t)}</li>`).join(''));
    const parts = [`Revenu ${fmt(income(st.own, cps))}/s` + (cps ? ` (dont clics ${fmt(clickPow(st.own) * cps)})` : ''), `cagnotte 💰 ${fmt(st.wallet)}`];
    if (st.boost.fz) parts.push(`🔥 Frénésie : revenu ${fmt(rateAt(st.own, cps, st.boost, 0))}/s pendant ${st.boost.fz} s (production ×${FRENESIE})`);
    if (st.boost.rf) parts.push(cps ? `⚡ Rafale : revenu ${fmt(rateAt(st.own, cps, st.boost, 0))}/s pendant ${st.boost.rf} s (clics ×${RAFALE})` : `⚡ Rafale : chaque clic ×${RAFALE} pendant ${st.boost.rf} s, à condition de cliquer`);
    if (capped && mode !== 'passif') parts.push(`⚠️ ${LIM_H} clics atteints sur l’heure : les clics ne comptent plus, conseil passif`);
    else if (mode === 'auto') parts.push(cps ? `conseil calculé pour ${cpsTxt(cps)} clic/s, moyenne de ${cad.tot} clics sur ${durMin(Math.max(cad.obs, MOY_PLANCHER * 60))}` + (cad.obs < MOY_PLANCHER * 60 ? ' (durée minimale comptée)' : ' de jeu observé') + (why ? ` (cadence ${why})` : '') : 'aucun clic dans la moyenne des 3 dernières heures : conseil passif');
    else if (why) parts.push(`cadence ${why}`);
    if (mode !== 'passif' || cad.hour) parts.push(`clics : ` + (cad.rate ? `série en cours ${dec1(cad.rate)}/s, ` : '') + `${cad.hour}/${LIM_H} sur l’heure, ${cad.minute}/${LIM_MIN} cette minute`);
    if (!capped && cad.hour > LIM_H - 2000) parts.push(`⚠️ bientôt ${LIM_H} clics sur l’heure : au-delà, ils ne comptent plus`);
    if (cad.minute > LIM_MIN - 60) parts.push(`⚠️ près de ${LIM_MIN} clics cette minute : au-delà, ils ne comptent plus, et un rythme tenu au plafond ${AUTOCLIC} min est pris pour un autoclic (clics ignorés ${AUTOCLIC} min)`);
    put('ft', ui.ft, 'textContent', parts.join(' · '));
    const t = (ready ? '🟢 ' + first.it.u.name + ' · ' : '') + baseTitle(); if (document.title !== t) document.title = t;
  }
  setMode(mode);
  const iv = setInterval(tick, TICK);
  function stop() {
    clearInterval(iv); clearInterval(ivSave); store('clics', JSON.stringify(perMin)); box.remove(); css.remove(); document.title = baseTitle();
    document.removeEventListener('click', onClick, true); removeEventListener('resize', place);
    if (DPIP) DPIP.removeEventListener('enter', onPip);
    if (window.open === openSpy) window.open = winOpen;
    for (const w of minis) try { w.document.removeEventListener('click', onClick, true); } catch (e) { /* fenêtre fermée */ }
    unmark(); if (endDrag) endDrag();
    delete window.__tagAdv;
  }
  // état lu au dernier rafraîchissement (diagnostic depuis la console, et tests)
  window.__tagAdv = { stop, state: () => last && { wallet: last.wallet, own: { ...last.own }, boost: { ...last.boost }, cadence: cadence(), minis: minis.size } };
})();
