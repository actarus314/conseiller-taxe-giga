(() => {
  // Conseiller pour taxe-au-giga.fr : lit l'état affiché par le jeu, ne clique et n'achète jamais rien.
  if (window.__tagAdv) { window.__tagAdv.stop(); return; }

  // Barème recopié du code du jeu le 03/11/2026 (build 2026-11-03e).
  // prix = arrondi_sup(base × 1,15^possédés) ; rate = visites/s ; click = visites en plus par clic ; pct = part de la production ajoutée à chaque clic.
  const P = [
    ['doigt', 'Doigt de fonctionnaire', 10, 0, 2], ['stagiaire', 'Stagiaire F5', 15, 0.5], ['chat', 'Chat sur le clavier', 100, 2],
    ['hamster', 'Hamster-routeur', 600, 8], ['souris', 'Souris à molette fiscale', 500, 0, 20], ['bot', 'Ferme de bots', 6000, 40],
    ['fax', 'Fax ministériel', 6e4, 200], ['commission', 'Commission à 11 contre 10', 6e5, 1100], ['gant', 'Gant de clic en or massif', 15e4, 0, 600],
    ['satellite', 'Satellite de taxation', 5e6, 3000], ['trounoir', 'Trou noir fiscal', 7.5e7, 15000], ['tampon', 'Tampon « Adopté » automatique', 2e7, 0, 40000],
    ['mainetat', 'Main de l’État', 5e8, 0, 0, 0.01, 1], ['decret', 'Décret d’application', 1e9, 0, 25000], ['datacenter', 'Datacenter sur le Vieux-Port', 1e9, 60000],
    ['ia', 'IA qui lit la gazette en boucle', 1.2e10, 250000], ['recommande', 'Clic en recommandé avec AR', 5e9, 0, 0, 0.02, 1],
    ['art493', 'Article 49.3', 5e10, 0, 0, 0.04, 1], ['ordonnance', 'Ordonnance du clic', 5e10, 0, 200000], ['multivers', 'Gazette du multivers', 1.5e11, 1.2e6],
    ['niche', 'Niche fiscale du clic', 5e11, 0, 0, 0.08, 1], ['quantique', 'Taxe quantique', 2e12, 6e6], ['directive', 'Directive européenne du clic', 2.5e12, 0, 3e6],
    ['mondial', 'Amendement mondial', 5e12, 0, 0, 0.15, 1],
  ].map(([id, name, base, rate = 0, click = 0, pct = 0, max = 0]) => ({ id, name, base, rate, click, pct, max }));
  const cost = (u, n) => Math.ceil(u.base * Math.pow(1.15, n));
  // Limites du serveur : 760 clics comptés par minute, 18000 par heure (au-delà, les clics ne rapportent rien)
  const LIM_MIN = 760, LIM_H = 18000, CPS_MAX = LIM_MIN / 60, HORIZON = 900; // horizon de 15 min pour répartir le reste du quota horaire

  // Production d'un parc : passive (rate) et par clic, comme clickPower() du jeu
  const prodRate = own => P.reduce((s, u) => s + u.rate * (own[u.id] || 0), 0);
  const clickPow = own => Math.floor(1 + P.reduce((s, u) => s + u.click * (own[u.id] || 0), 0) + (0.01 + P.reduce((s, u) => s + u.pct * (own[u.id] || 0), 0)) * prodRate(own));
  const income = (own, cps) => prodRate(own) + (cps > 0 ? clickPow(own) * cps : 0);

  const $ = s => document.querySelector(s);
  const num = s => {
    if (!s) return NaN;
    const t = s.replace(/[\s  💰]/g, '').replace(',', '.');
    const m = t.match(/^([\d.]+)(Md|M)?$/); if (!m) return NaN;
    return parseFloat(m[1]) * (m[2] === 'Md' ? 1e9 : m[2] === 'M' ? 1e6 : 1);
  };
  // nombres au point décimal, sans séparateur de milliers
  const fmt = n => n < 1e6 ? String(Math.round(n)) : n < 1e9 ? (n / 1e6).toFixed(2) + ' M' : n < 1e12 ? (n / 1e9).toFixed(2) + ' Md' : (n / 1e12).toFixed(2) + ' T';
  const dec1 = n => n.toFixed(1).replace(/\.0$/, '');
  const dur = s => !isFinite(s) ? 'après quelques clics' : s < 1 ? 'quelques secondes' : s < 60 ? Math.ceil(s) + ' s' : s < 3600 ? Math.round(s / 60) + ' min' : dec1(s / 3600) + ' h';
  const clock = s => !isFinite(s) ? '—' : new Date(Date.now() + s * 1000).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  const store = (k, v) => { try { if (v === undefined) return localStorage.getItem('tagAdv-' + k); localStorage.setItem('tagAdv-' + k, v); } catch (e) { return null; } };

  // Réglages : Auto (cadence mesurée, par défaut), Passif (aucun clic) ou Actif (cadence fixée)
  let mode = ['auto', 'passif', 'actif'].includes(store('mode')) ? store('mode') : 'auto';
  let cpsPlan = Math.min(CPS_MAX, Math.max(0.1, parseFloat(store('cps')) || 5));

  // Mesure des clics réels sur TAXER (bouton principal et bouton flottant).
  // Cadence : moyenne des clics de la série en cours sur la dernière minute (3 s de mesure au moins),
  // pour qu'une pause de quelques secondes (le temps d'un achat) la fasse à peine baisser.
  // Arrêt : 8 s sans clic ; une nouvelle série repart alors de zéro.
  // Compteur horaire : par minute, gardé dans le navigateur pour survivre à un rechargement.
  const WIN = 60e3, STOP = 8e3, recent = [];
  let perMin = {}; try { perMin = JSON.parse(store('clics') || '{}') || {}; } catch (e) { perMin = {}; }
  const onClick = e => {
    if (!e.isTrusted || !e.target.closest || !e.target.closest('#taxBtn, #stickyTax')) return;
    const t = Date.now(); recent.push(t); const m = Math.floor(t / 60e3); perMin[m] = (perMin[m] || 0) + 1;
  };
  document.addEventListener('click', onClick, true);
  function cadence() {
    const now = Date.now(), m0 = Math.floor(now / 60e3);
    while (recent.length && recent[0] < now - WIN) recent.shift();
    for (const k in perMin) if (k <= m0 - 60) delete perMin[k];
    const hour = Object.values(perMin).reduce((a, b) => a + b, 0), minute = perMin[m0] || 0;
    if (!recent.length) return { rate: 0, idle: Infinity, hour, minute };
    const idle = now - recent[recent.length - 1];
    if (idle > STOP) return { rate: 0, idle, hour, minute };
    let i = recent.length - 1; while (i > 0 && recent[i] - recent[i - 1] <= STOP) i--; // début de la série en cours
    const n = recent.length - i, span = Math.max(3000, now - recent[i]);
    return { rate: n / (span / 1000), idle, hour, minute };
  }
  const ivSave = setInterval(() => store('clics', JSON.stringify(perMin)), 5000);

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
        if (shown && Math.abs(shown - c) / c > 0.01) drift.push(u.name);
        items.push({ u, el: b });
      }
    }
    // la puissance de clic affichée par le jeu sert de contrôle du modèle
    const pcTxt = ($('#perClick') || {}).textContent || '', pc = /volontaire/.test(pcTxt) ? 0 : parseInt(pcTxt.replace(/\D/g, ''), 10); // mode sérieux : rien à contrôler
    if (pc && items.length && Math.abs(pc - clickPow(own)) > Math.max(2, pc * 0.01)) drift.push('puissance de clic');
    const chip = $('#buffChip'), m = chip && !chip.hidden && /Frénésie/.test(chip.textContent) && chip.textContent.match(/(\d+)\s*s\b/);
    return { items, own, drift, wallet: num(($('#wallet') || {}).textContent), frenzy: m ? +m[1] : 0 };
  }

  // Temps pour gagner `amount`, en tenant compte d'une frénésie en cours (production passive ×3)
  function earnTime(amount, own, cps, fz) {
    if (amount <= 0) return 0;
    const r = income(own, cps), boost = r + 2 * prodRate(own);
    if (fz > 0 && amount <= boost * fz) return amount / boost;
    const rest = fz > 0 ? amount - boost * fz : amount;
    return r > 0 ? Math.max(fz, 0) + rest / r : Infinity;
  }
  // Choix : le bonus qui minimise (attente avant de pouvoir le payer + temps pour qu'il se rembourse).
  function pick(items, own, w, cps, fz) {
    let best = null, bs = Infinity; const r0 = income(own, cps);
    for (const it of items) {
      const n = own[it.u.id] || 0; if (it.u.max && n >= it.u.max) continue;
      const g = income({ ...own, [it.u.id]: n + 1 }, cps) - r0; if (g <= 0) continue;
      const c = cost(it.u, n), s = earnTime(c - w, own, cps, fz) + c / g;
      if (s < bs) { bs = s; best = it; }
    }
    return best;
  }
  function plan(st, cps, k) {
    const own = { ...st.own }; let w = st.wallet, t = 0, fz = st.frenzy; const out = [];
    for (let i = 0; i < k; i++) {
      const it = pick(st.items, own, w, cps, fz); if (!it) break;
      const n = own[it.u.id] || 0, c = cost(it.u, n), wait = earnTime(c - w, own, cps, fz);
      if (!isFinite(wait)) { out.push({ it, c, t: Infinity, n: n + 1 }); break; }
      w += income(own, cps) * wait + 2 * prodRate(own) * Math.min(wait, fz) - c; fz = Math.max(0, fz - wait); t += wait;
      own[it.u.id] = n + 1; out.push({ it, c, t, n: n + 1 });
    }
    return out;
  }

  // Interface
  const css = document.createElement('style');
  css.textContent = `
  #tagAdv{position:fixed;right:12px;z-index:99999;width:min(340px,calc(100vw - 24px));background:#fffbe6;color:#1a1a1a;
    border:3px solid #1a1a1a;border-radius:14px;box-shadow:5px 5px 0 #1a1a1a;font:14px/1.4 system-ui,sans-serif}
  #tagAdv header{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:8px 12px;border-bottom:2px solid #1a1a1a;font-weight:700;user-select:none;cursor:move;touch-action:none}
  #tagAdv header button{all:unset;cursor:pointer;padding:0 4px;font-size:16px}
  #tagAdv .modes{display:flex;gap:6px;padding:8px 12px 0;flex-wrap:wrap;align-items:center}
  #tagAdv .modes button{all:unset;cursor:pointer;border:2px solid #1a1a1a;border-radius:8px;padding:3px 10px;font-weight:700;font-size:13px}
  #tagAdv .modes button[aria-pressed="true"]{background:#1a1a1a;color:#fffbe6}
  #tagAdv .modes label{font-size:12px;display:flex;gap:4px;align-items:center;margin-left:auto}
  #tagAdv .modes label[hidden]{display:none}
  #tagAdv .modes input{width:46px;font:inherit;border:2px solid #1a1a1a;border-radius:6px;padding:1px 4px;background:#fff;color:#1a1a1a}
  #tagAdv .now{padding:10px 12px;font-size:16px}
  #tagAdv .now b{display:block;font-size:18px}
  #tagAdv .now.go{background:#19d3a2}
  #tagAdv ol{margin:0;padding:6px 12px 10px 32px;font-size:13px}
  #tagAdv ol li{margin:2px 0}
  #tagAdv .ft{padding:6px 12px 8px;border-top:2px dashed #1a1a1a;font-size:12px;color:#555}
  #tagAdv .warn{padding:6px 12px;background:#ffb3d6;font-size:12px}
  #tagAdv .warn[hidden]{display:none}
  #tagAdv.min .modes,#tagAdv.min ol,#tagAdv.min .ft{display:none}
  .tagAdvBest{outline:5px solid #19d3a2!important;outline-offset:2px;position:relative}
  .tagAdvBest::after{content:attr(data-adv);position:absolute;top:-12px;left:12px;background:#19d3a2;color:#1a1a1a;border:2px solid #1a1a1a;
    border-radius:8px;padding:1px 8px;font:700 12px/1.4 system-ui,sans-serif;pointer-events:none}`;
  document.head.appendChild(css);
  const box = document.createElement('div'); box.id = 'tagAdv';
  box.innerHTML = `<header><span>🧮 Conseiller</span><span><button data-a="min" aria-label="Réduire">–</button><button data-a="x" aria-label="Fermer">✕</button></span></header>
    <div class="modes"><button data-m="auto">Auto</button><button data-m="passif">Passif</button><button data-m="actif">Actif</button>
      <label data-cps>clics/s prévus <input id="tagAdvCps" type="number" min="0.1" max="12.6" step="0.5"></label></div>
    <div class="warn" hidden></div><div class="now"></div><ol></ol><div class="ft"></div>`;
  document.body.appendChild(box);
  if (innerWidth < 600) box.classList.add('min'); // téléphone : panneau réduit au conseil, la boutique reste visible
  const cpsIn = box.querySelector('#tagAdvCps'); cpsIn.value = cpsPlan;
  cpsIn.addEventListener('change', () => { cpsPlan = Math.min(CPS_MAX, Math.max(0.1, parseFloat(cpsIn.value) || 5)); cpsIn.value = cpsPlan; store('cps', cpsPlan); tick(); });
  const setMode = m => { mode = m; store('mode', m); box.querySelectorAll('[data-m]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.m === m))); box.querySelector('[data-cps]').hidden = m !== 'actif'; tick(); };
  box.addEventListener('click', e => {
    const a = e.target.dataset.a;
    if (a === 'min') box.classList.toggle('min'); if (a === 'x') stop();
    if (e.target.dataset.m) setMode(e.target.dataset.m);
  });

  // Position : au-dessus du bouton TAXER flottant (bas droite), ou là où on a déplacé le panneau
  let dragged = false;
  function place() {
    if (dragged) return;
    const st = $('#stickyTax'), h = st ? st.offsetHeight : 64;
    box.style.top = 'auto';
    box.style.bottom = `calc(${24 + h + 18}px + env(safe-area-inset-bottom, 0px))`;
  }
  const hd = box.querySelector('header');
  hd.addEventListener('pointerdown', e => {
    if (e.target.closest('button')) return;
    const r = box.getBoundingClientRect(), dx = e.clientX - r.left, dy = e.clientY - r.top;
    const mv = ev => { dragged = true; box.style.left = Math.max(0, Math.min(innerWidth - r.width, ev.clientX - dx)) + 'px'; box.style.top = Math.max(0, Math.min(innerHeight - 40, ev.clientY - dy)) + 'px'; box.style.right = box.style.bottom = 'auto'; };
    const up = () => { removeEventListener('pointermove', mv); removeEventListener('pointerup', up); };
    addEventListener('pointermove', mv); addEventListener('pointerup', up);
  });
  addEventListener('resize', place); place();

  const PFX = /^🟢 [^·]+ · /, baseTitle = () => document.title.replace(PFX, ''); let marked = null;
  function tick() {
    const st = read(), now = box.querySelector('.now'), warn = box.querySelector('.warn');
    // Cadence retenue : la cadence voulue (mesurée en Auto, réglée en Actif), dans la limite de 760/min,
    // et du reste du quota horaire réparti sur 15 min quand il ne suffit plus.
    const cad = cadence(), left = Math.max(0, LIM_H - cad.hour), capped = left === 0;
    const want = mode === 'actif' ? cpsPlan : mode === 'auto' ? cad.rate : 0; // clics arrêtés : conseil passif
    const cps = Math.min(want, CPS_MAX, left / HORIZON);
    const why = !want || cps >= want - 0.05 ? '' : capped ? '' : cps < Math.min(want, CPS_MAX) - 0.05 ? `ramenée à ${dec1(cps)} : reste ${left} clics sur le quota de l’heure` : `ramenée à ${dec1(CPS_MAX)}, plafond de 760 clics par minute`;
    if (!Number.isFinite(st.wallet) || !$('#shop')) { now.textContent = 'Boutique introuvable : recharger la page du jeu.'; return; }
    if (!st.items.length) { now.textContent = 'Aucun bonus débloqué : cliquer sur TAXER.'; return; }
    warn.hidden = !st.drift.length;
    if (st.drift.length) warn.textContent = `⚠️ Le jeu ne correspond plus au barème connu (${st.drift.join(', ')}) : il a peut-être changé ses règles, conseils à prendre avec prudence.`;
    const out = plan(st, cps, 8), first = out[0];
    if (marked && (!first || marked !== first.it.el)) { marked.classList.remove('tagAdvBest'); marked = null; }
    if (!first) return;
    const ready = !first.it.el.disabled; // le bouton du jeu fait foi pour « achetable maintenant »
    first.it.el.classList.add('tagAdvBest'); first.it.el.dataset.adv = ready ? '👉 À ACHETER' : '⏳ ' + dur(first.t);
    marked = first.it.el;
    now.className = 'now' + (ready ? ' go' : '');
    now.innerHTML = ready
      ? `Acheter maintenant<b>${first.it.u.name}</b>💰 ${fmt(first.c)} · devient ×${first.n}`
      : (isFinite(first.t) ? `Prochain achat dans ${dur(first.t)} (${clock(first.t)})` : 'Prochain achat après quelques clics') + `<b>${first.it.u.name}</b>💰 ${fmt(first.c)} · ne rien acheter d’autre d’ici là`;
    box.querySelector('ol').innerHTML = out.slice(1).map(o =>
      `<li>${o.it.u.name} ×${o.n} · 💰 ${fmt(o.c)} · ${o.t < 1 ? 'tout de suite' : clock(o.t)}</li>`).join('');
    const parts = [`Revenu ${fmt(income(st.own, cps))}/s` + (cps ? ` (dont clics ${fmt(clickPow(st.own) * cps)})` : ''), `cagnotte 💰 ${fmt(st.wallet)}`];
    if (st.frenzy) parts.push(`🔥 frénésie ${st.frenzy} s comptée`);
    if (capped && want) parts.push('⚠️ 18000 clics atteints sur l’heure : les clics ne comptent plus, conseil passif');
    else if (mode === 'auto') parts.push(cps ? `conseil calculé pour ${dec1(cps)} clics/s` + (why ? ` (cadence ${dec1(cad.rate)}/s ${why})` : ' (cadence mesurée)') : (isFinite(cad.idle) ? `clics arrêtés depuis ${Math.round(cad.idle / 1000)} s : conseil passif` : 'aucun clic récent : conseil passif'));
    else if (why) parts.push(`cadence ${why}`);
    if (mode !== 'passif' || cad.hour) parts.push(`clics : ${dec1(cad.rate)}/s, ${cad.hour}/${LIM_H} sur l’heure, ${cad.minute}/${LIM_MIN} cette minute`);
    if (!capped && cad.hour > LIM_H - 2000) parts.push(`⚠️ bientôt ${LIM_H} clics sur l’heure : au-delà, ils ne comptent plus`);
    if (cad.minute > LIM_MIN - 60) parts.push(`⚠️ près de ${LIM_MIN} clics cette minute : au-delà, ils ne comptent plus, et un rythme tenu au plafond 3 min est pris pour un autoclic (clics ignorés 10 min)`);
    box.querySelector('.ft').textContent = parts.join(' · ');
    const t = (ready ? '🟢 ' + first.it.u.name + ' · ' : '') + baseTitle(); if (document.title !== t) document.title = t;
  }
  setMode(mode);
  const iv = setInterval(tick, 500);
  function stop() {
    clearInterval(iv); clearInterval(ivSave); store('clics', JSON.stringify(perMin)); box.remove(); css.remove(); document.title = baseTitle();
    document.removeEventListener('click', onClick, true); removeEventListener('resize', place);
    if (marked) marked.classList.remove('tagAdvBest');
    delete window.__tagAdv;
  }
  window.__tagAdv = { stop };
})();
