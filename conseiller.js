(() => {
  // Conseiller pour taxe-au-giga.fr : lit l'état affiché par le jeu, ne clique et n'achète jamais rien.
  if (!/^(taxe-au-giga\.fr|localhost|127\.0\.0\.1)$/.test(location.hostname)) { alert('Conseiller : à lancer sur taxe-au-giga.fr'); return; }
  if (window.__tagAdv) { window.__tagAdv.stop(); return; }

  const VERSION = '2.37'; // écrite par dev/outils/build.py <version>

  // Barème recopié du code du jeu le 03/11/2026 (Décret porté à +100000 par clic au build 2026-11-03h), identique au build 2026-11-04n.
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
  // Limites du serveur (build 2026-11-04l) : 1030 clics comptés par minute, 24000 par heure (au-delà, les clics ne rapportent rien)
  const LIM_MIN = 1030, LIM_H = 24000, CPS_MAX = LIM_MIN / 60, HORIZON = 900; // horizon de 15 min pour répartir le reste du quota horaire
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
  const clampCps = v => { const x = parseFloat(v); return Number.isFinite(x) ? Math.min(CPS_MAX, Math.max(CPS_MIN, x)) : CPS_DEFAULT; };

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
  // trois chiffres significatifs (suite des achats : un ordre de grandeur suffit, la place va au nom)
  const fmt3 = n => n < 1e6 ? String(Math.round(n)) : ((v, u) => (v < 10 ? v.toFixed(2) : v < 100 ? v.toFixed(1) : Math.round(v)) + ' ' + u)(...(n < 999.5e6 ? [n / 1e6, 'M'] : n < 999.5e9 ? [n / 1e9, 'Md'] : [n / 1e12, 'T']));
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
  // texte venu de la page du jeu (nom d'événement) avant de l'insérer dans du HTML
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const store = (k, v) => { try { if (v === undefined) return localStorage.getItem('tagAdv-' + k); localStorage.setItem('tagAdv-' + k, v); } catch (e) { return null; } };

  // Réglages : Auto (moyenne mesurée, par défaut), Passif (aucun clic) ou Actif (cadence fixée)
  let mode = ['auto', 'passif', 'actif'].includes(store('mode')) ? store('mode') : 'auto';
  // dernier événement du jeu lu sur son indicateur (nom, multiplicateur, fin), gardé pour les moments où l'indicateur montre autre chose
  // validée au chargement : nom court, multiplicateur entre 1 et 100, fin à moins de 24 h
  const evOk = e => !!e && typeof e.nm === 'string' && e.nm.length <= 60 && Number.isFinite(e.mult) && e.mult >= 1 && e.mult <= 100
    && Number.isFinite(e.to) && e.to > Date.now() && e.to < Date.now() + 864e5;
  let evMem = null; try { evMem = JSON.parse(store('ev') || 'null'); } catch (e) { evMem = null; }
  if (!evOk(evMem)) evMem = null;
  let cpsPlan = clampCps(store('cps'));

  // Mesure des clics réels sur TAXER (bouton principal, bouton flottant et bouton du mode mini).
  // Mode Auto : moyenne des clics sur les 3 dernières heures de présence, cherchées sur 24 h et comptées sur 30 min au moins.
  // Présence : minutes où le panneau tournait, sauf au-delà d'1 h sans aucun clic (nuit, réunion : absence, pas jeu passif).
  // Des séries espacées donnent ainsi une cadence stable, la même pendant et entre les séries, et retrouvée dès le retour
  // d'une absence. Seuil d'1 h choisi par simulation (dev/sim/presence.py) : le plus robuste des seuils essayés.
  // Série en cours (colonne « En direct » seulement) : cadence sur les 5 dernières secondes (fenêtre glissante, ou depuis le
  // premier clic de la série s'il date de moins de 5 s, 1 s au moins) ; série interrompue après 5 s sans clic.
  // Compteur par minute (0 = minute observée sans clic), gardé dans le navigateur pour survivre à un rechargement.
  const WIN = 60e3, STOP = 5e3, LIVE = 5e3, recent = [];
  const MOY_MIN = 180, MOY_PLANCHER = 30, PAUSE = 60, JOUR = 1440; // en minutes : présence moyennée, durée minimale comptée, pause vue comme une absence, recherche
  // validé au chargement : objet de minutes (entiers) vers des nombres de clics finis ; le reste est écarté
  let perMin = {}; try { perMin = JSON.parse(store('clics') || '{}'); } catch (e) { perMin = {}; }
  perMin = perMin && typeof perMin === 'object' && !Array.isArray(perMin)
    ? Object.fromEntries(Object.entries(perMin).filter(([k, v]) => /^\d+$/.test(k) && Number.isFinite(v) && v >= 0)) : {};
  let perMinDirty = false;
  // début de l'observation minute par minute (v2.14) : les minutes plus anciennes, notées par les versions qui ne
  // gardaient que les minutes avec clics, comptent pour le quota horaire mais pas pour la moyenne
  let since = parseInt(store('vu'), 10); if (!Number.isFinite(since)) { since = Math.floor(Date.now() / 60e3); store('vu', String(since)); }
  const onClick = e => {
    if (!e.isTrusted || !e.target.closest || !e.target.closest('#taxBtn, #stickyTax, #mTax')) return;
    const t = Date.now(); recent.push(t); const m = Math.floor(t / 60e3); perMin[m] = (perMin[m] || 0) + 1; perMinDirty = true;
  };
  document.addEventListener('click', onClick, true);
  // Mode mini du jeu : TAXER dans une petite fenêtre, « image dans l'image » (Chrome, Edge), sinon fenêtre surgissante
  // nommée taxe-giga-mini. La première est retrouvée même ouverte avant le panneau ; la seconde seulement si elle
  // s'ouvre panneau ouvert (window.open est alors observé, sans rien changer à son résultat).
  const minis = new Set();
  let stopped = false;
  const watchMini = w => { try { if (!stopped && w && !minis.has(w)) { w.document.addEventListener('click', onClick, true); minis.add(w); w.addEventListener('pagehide', () => minis.delete(w)); } } catch (e) { /* fenêtre fermée */ } };
  const DPIP = window.documentPictureInPicture, onPip = e => watchMini(e.window);
  if (DPIP) { DPIP.addEventListener('enter', onPip); watchMini(DPIP.window); }
  const winOpen = window.open;
  const openSpy = function (...a) { const w = winOpen.apply(this, a); if (a[1] === 'taxe-giga-mini') watchMini(w); return w; }; // inactive une fois le panneau arrêté
  window.open = openSpy;
  // minutes passées : recalculées une fois par minute (seule la minute en cours change entre deux)
  let past = null;
  function pastMinutes(m0) {
    const ks = Object.keys(perMin).map(Number).filter(k => k < m0).sort((x, y) => x - y), counted = [];
    // avant le premier clic de la fenêtre, comme dans la simulation (dev/sim/presence.py) : la fenêtre s'ouvre comme un clic
    let last = m0 - JOUR, hour = 0;
    for (const k of ks) {
      if (k <= m0 - JOUR) { delete perMin[k]; perMinDirty = true; continue; }
      const n = perMin[k]; if (k > m0 - 60) hour += n; if (n > 0) last = k;
      if (k >= since && (n > 0 || k - last <= PAUSE)) counted.push(n);
    }
    return { m0, counted, last, hour };
  }
  function cadence() {
    const now = Date.now(), m0 = Math.floor(now / 60e3);
    // horloge reculée (réglage à la main, grosse correction) : série et début d'observation repartent de maintenant
    if (recent.length && recent[recent.length - 1] > now + 1000) { recent.length = 0; past = null; }
    if (since > m0) { since = m0; store('vu', String(since)); }
    while (recent.length && recent[0] < now - WIN) recent.shift();
    if (!(m0 in perMin)) { perMin[m0] = 0; perMinDirty = true; } // minute observée
    if (!past || past.m0 !== m0) past = pastMinutes(m0);
    const cur = perMin[m0], curIn = m0 >= since && (cur > 0 || m0 - past.last <= PAUSE);
    const prev = past.counted.slice(-(MOY_MIN - (curIn ? 1 : 0)));
    const tot = prev.reduce((x, y) => x + y, 0) + (curIn ? cur : 0);
    const obs = prev.length * 60 + (curIn ? (now % 60e3) / 1000 : 0); // la minute en cours compte pour ce qui en est écoulé
    const avg = tot / Math.max(obs, MOY_PLANCHER * 60);
    const out = { avg, obs, tot, rate: 0, idle: Infinity, hour: past.hour + cur, minute: cur };
    if (!recent.length) return out;
    out.idle = now - recent[recent.length - 1];
    if (out.idle > STOP) return out;
    let i = recent.length - 1; while (i > 0 && recent[i] - recent[i - 1] <= STOP) i--; // début de la série en cours
    const from = Math.max(recent[i], now - LIVE); let n = 0; for (let j = recent.length - 1; j >= i && recent[j] >= from; j--) n++;
    out.rate = n / (Math.max(1000, now - from) / 1000);
    return out;
  }
  const save = () => { if (perMinDirty) { store('clics', JSON.stringify(perMin)); perMinDirty = false; } };
  const ivSave = setInterval(save, SAVE_EVERY);

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
      // sauvegarde antérieure à un achat (parc différent de celui affiché) : ignorée, l'affichage fait foi
      const same = sv && sv.owned && typeof sv.owned === 'object' && Object.keys(own).every(id => (sv.owned[id] || 0) === own[id]);
      if (same && Number.isFinite(sv.wallet) && sv.t) {
        const clicks = recent.filter(t => t > sv.t).length; // clics comptés par le panneau depuis la sauvegarde
        est = sv.wallet + prodRate(own) * prodMul(boost, 0) * Math.max(0, Date.now() - sv.t) / 1000 + clicks * clickPow(own) * (boost.rf ? RAFALE : 1);
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
        const price = num((b.querySelector('.price') || {}).textContent), c = cost(u, n);
        if (price && Math.abs(price - c) / c > DRIFT) drift.push(u.name);
        items.push({ u, el: b });
      }
    }
    // la puissance de clic affichée par le jeu sert de contrôle du modèle
    const pcTxt = ($('#perClick') || {}).textContent || '', pc = /volontaire/.test(pcTxt) ? 0 : parseInt(pcTxt.replace(/\D/g, ''), 10); // mode sérieux : rien à contrôler
    if (pc && items.length && Math.abs(pc - clickPow(own)) > Math.max(2, pc * DRIFT)) drift.push('puissance de clic');
    // bonus de la Facture dorée en cours, lus dans le bandeau du jeu : Frénésie (production ×3) ou Rafale (clics ×10)
    const chip = $('#buffChip'), ct = chip && !chip.hidden ? chip.textContent : '', left = (ct.match(/(\d+)\s*s\b/) || [])[1];
    const fzOn = /^\s*🔥 Frénésie/.test(ct), rfOn = /^\s*⚡ Rafale/.test(ct);
    const boost = { fz: fzOn && left ? +left : 0, rf: rfOn && left ? +left : 0, ev: 0, evm: 1, evn: '' };
    // Événement du jeu (build 2026-11-04n) : production ×mult pendant quelques heures, cumulée avec la Frénésie (1 + 2 + mult − 1).
    // L'indicateur du jeu ne l'affiche que hors Frénésie et Rafale : sa fin est retenue, et pendant une Frénésie sans fin connue,
    // le multiplicateur affiché (×4 au lieu de ×3) suffit à le déduire, pour la durée de la Frénésie.
    const evm = /📣 (.+?) : production ×(\d+(?:[.,]\d+)?) jusqu.à .*?encore (?:(\d+) h (\d+)|(\d+) min)/.exec(ct);
    // fin lue à la minute, arrondie au-dessus par le jeu : on retire 30 s ; écrite seulement si le nom, le multiplicateur ou la fin (à 1 min près) change
    if (evm) {
      const e = { nm: evm[1].slice(0, 60), mult: parseFloat(evm[2].replace(',', '.')), to: Date.now() + (evm[3] ? (+evm[3] * 60 + +evm[4]) : +evm[5]) * 60e3 - 30e3 };
      if (evOk(e) && (!evMem || evMem.nm !== e.nm || evMem.mult !== e.mult || Math.abs(evMem.to - e.to) > 60e3)) { evMem = e; store('ev', JSON.stringify(e)); }
    } else if (!fzOn && !rfOn && evMem) { evMem = null; store('ev', 'null'); } // indicateur masqué ou sans événement : il n'y en a pas (ou plus)
    if (evMem && evMem.to > Date.now()) Object.assign(boost, { ev: Math.round((evMem.to - Date.now()) / 1000), evm: evMem.mult, evn: evMem.nm });
    const fzm = boost.fz && /production ×(\d+(?:[.,]\d+)?)/.exec(ct), fzx = fzm ? parseFloat(fzm[1].replace(',', '.')) : FRENESIE;
    if (boost.fz && fzx > FRENESIE && !boost.ev) Object.assign(boost, { ev: boost.fz, evm: fzx - FRENESIE + 1, evn: 'événement' });
    const gold = $('#goldBill'); // Facture dorée à l’écran
    return { items, own, drift, wallet: walletNow(own, boost), boost, goldUp: !!gold && !gold.hidden };
  }

  // Revenu à l'instant t (s) : Frénésie = production ×3 pendant fz s, Rafale = clics ×10 pendant rf s, événement = production ×mult pendant ev s
  // multiplicateur de production à l'instant t (s) : Frénésie (+2) et événement du jeu (+mult − 1) s'additionnent
  const prodMul = (b, t) => 1 + (t < b.fz ? FRENESIE - 1 : 0) + (t < (b.ev || 0) ? b.evm - 1 : 0);
  const rateAt = (own, cps, b, t) => { const r = prodRate(own); return r * prodMul(b, t) + (cps > 0 ? clickPow(own, r) * cps * (t < b.rf ? RAFALE : 1) : 0); };
  // Morceaux de temps où le revenu est constant : [0, fin du 1er bonus], [.., fin du suivant]…, [.., ∞)
  const pieces = b => [...new Set([b.fz, b.rf, b.ev].filter(x => x > 0))].sort((x, y) => x - y).concat(Infinity);
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
  const after = (b, dt) => ({ ...b, fz: Math.max(0, b.fz - dt), rf: Math.max(0, b.rf - dt), ev: Math.max(0, (b.ev || 0) - dt) });
  // Choix : le bonus qui minimise (attente avant de pouvoir le payer + temps pour qu'il se rembourse). Le remboursement compte
  // les bonus en cours sur leur durée (un bonus de production rapporte ×mult pendant un événement, ×3 pendant une Frénésie).
  function pick(items, own, w, cps, boost) {
    let best = null, bs = Infinity; const segs = segments(own, cps, boost), ends = segs.map(g => g.end);
    const r0 = prodRate(own), c0 = cps > 0 ? clickPow(own, r0) : 0;
    for (const it of items) {
      const n = own[it.u.id] || 0; if (it.u.max && n >= it.u.max) continue;
      // gain du bonus, morceau par morceau : production en plus (×Frénésie, ×événement) et clics en plus (×Rafale)
      own[it.u.id] = n + 1; const dC = cps > 0 ? clickPow(own, r0 + it.u.rate) - c0 : 0; own[it.u.id] = n;
      let start = 0; const gain = ends.map(end => { const g = { end, rate: it.u.rate * prodMul(boost, start) + dC * cps * (start < boost.rf ? RAFALE : 1) }; start = end; return g; });
      if (gain[gain.length - 1].rate <= 0) continue;
      const c = cost(it.u, n), wait = earnTime(c - w, segs), s = wait + earnTime(c, gain);
      if (s < bs) { bs = s; best = { it, c, wait, segs }; }
    }
    return best;
  }
  function plan(st, cps, k) {
    // boost : Frénésie, Rafale, événement en cours, décomptés achat après achat
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
  #tagAdv header{display:flex;align-items:center;gap:6px;padding:7px 8px 7px 10px;border-bottom:2px solid var(--tagInk);font-weight:700;user-select:none;cursor:move;touch-action:none;white-space:nowrap}
  #tagAdv header .id{flex:0 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;font-size:14.5px}
  #tagAdv header .ctl{flex:none}
  #tagAdv .flash{padding:5px 12px;background:#ffd23f;border-bottom:2px solid var(--tagInk);font-weight:700;font-size:13px}
  #tagAdv header .v{font:500 10px/1 "IBM Plex Mono",ui-monospace,Menlo,monospace;color:#555;margin-left:2px;text-decoration:underline;cursor:pointer}
  #tagAdv header .v:focus-visible{outline:2px solid var(--tagInk);outline-offset:2px}
  #tagAdv header button{all:unset;cursor:pointer;padding:0 3px;font-size:16px}
  #tagAdv .seg{flex:none;margin:0 auto;display:inline-flex;border:2px solid var(--tagInk);border-radius:7px;overflow:hidden}
  #tagAdv .seg button{all:unset;cursor:pointer;padding:1px 5px;font-weight:700;font-size:11.5px;line-height:1.4}
  #tagAdv .seg button+button{border-left:2px solid var(--tagInk)}
  #tagAdv .seg button[aria-pressed="true"]{background:var(--tagInk);color:var(--tagPaper)}
  #tagAdv .seg button:focus-visible{outline:2px solid var(--tagInk);outline-offset:-4px}
  #tagAdv .det label{display:flex;gap:6px;align-items:center;color:var(--tagInk)}
  #tagAdv .det label[hidden]{display:none}
  #tagAdv .det input[type=checkbox]{all:revert;margin:0;accent-color:var(--tagInk)}
  #tagAdv .det input{width:44px;font:inherit;font-size:12px;line-height:1.4;text-align:center;border:2px solid var(--tagInk);border-radius:6px;padding:1px 4px;background:#fff;color:var(--tagInk)}
  #tagAdv .now{padding:10px 12px;font-size:16px}
  #tagAdv .now b{display:block;font-size:18px}
  /* compte à rebours sur une ligne : chiffres de largeur fixe, sans retour à la ligne (coupé par « … » sur un écran étroit) */
  #tagAdv .now .w{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-variant-numeric:tabular-nums}
  #tagAdv .now.go{background:var(--tagGo)}
  #tagAdv .now small{display:block;font-size:12.5px;color:#555;margin-top:2px}
  #tagAdv ol{margin:0;padding:6px 12px 10px;font-size:13px;list-style:none}
  #tagAdv ol li{display:grid;grid-template-columns:minmax(0,1fr) 2.4em 4.3em 3.1em;gap:6px;align-items:baseline;margin:2px 0}
  /* production en bleu, clic en rose : boutons Passif et Actif, étiquettes du bas, barre du conseil et de chaque achat (sans légende) */
  #tagAdv{--tagProd:#2b7bd6;--tagClic:#e0479e}
  #tagAdv .now{border-left:6px solid transparent}
  #tagAdv .now.kp{border-left-color:var(--tagProd)}
  #tagAdv .now.kc{border-left-color:var(--tagClic)}
  #tagAdv ol li{position:relative}
  #tagAdv ol li::before{content:'';position:absolute;left:-8px;top:3px;bottom:3px;width:3px;border-radius:2px}
  #tagAdv ol li.kp::before{background:var(--tagProd)}
  #tagAdv ol li.kc::before{background:var(--tagClic)}
  #tagAdv .seg button[data-m=passif]{color:var(--tagProd)}
  #tagAdv .seg button[data-m=actif]{color:var(--tagClic)}
  #tagAdv .seg button[data-m=passif][aria-pressed=true]{background:var(--tagProd);color:#fff}
  #tagAdv .seg button[data-m=actif][aria-pressed=true]{background:var(--tagClic);color:#fff}
  #tagAdv .kpi span:nth-child(1) small{color:var(--tagProd)}
  #tagAdv .kpi span:nth-child(2) small{color:var(--tagClic)}
  #tagAdv ol .n{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  #tagAdv ol .k{color:#555;font-variant-numeric:tabular-nums;text-align:right}
  #tagAdv ol .p,#tagAdv ol .h{font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
  #tagAdv ol .h{color:#666}
  #tagAdv ol .h.go{background:var(--tagGo);color:var(--tagInk);font-weight:700;border-radius:4px;padding:0 3px}
  #tagAdv .ft{padding:6px 12px 8px;border-top:2px dashed var(--tagInk);font-size:12px;color:#555;display:flex;flex-direction:column;gap:5px}
  #tagAdv .ft .top{display:flex;align-items:center;gap:6px}
  #tagAdv .kpi{flex:1;min-width:0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
  #tagAdv .kpi span.live{background:#d3f5ea;border-radius:6px;margin:-3px -5px;padding:3px 5px}
  #tagAdv .kpi span{display:flex;flex-direction:column;min-width:0}
  #tagAdv .kpi small{font:600 9.5px/1.2 "IBM Plex Mono",ui-monospace,Menlo,monospace;text-transform:uppercase;letter-spacing:.05em;color:#666}
  #tagAdv .kpi b{font:700 13px/1.3 "Space Grotesk",system-ui,sans-serif;color:var(--tagInk);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  #tagAdv .kpi i{font-style:normal;font-size:11px;color:#666;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  #tagAdv .ft button{all:unset;flex:none;width:20px;height:20px;display:grid;place-items:center;cursor:pointer;color:var(--tagInk);border:2px solid var(--tagInk);border-radius:6px}
  #tagAdv .ft button svg{width:12px;height:12px;transition:transform .15s}
  #tagAdv .ft button[aria-expanded="true"] svg{transform:rotate(180deg)}
  #tagAdv .ft button:focus-visible{outline:2px solid var(--tagInk);outline-offset:2px}
  #tagAdv .al,#tagAdv .det,#tagAdv .dtx{display:grid;gap:3px}
  #tagAdv .al:empty,#tagAdv .det[hidden]{display:none}
  #tagAdv .al p,#tagAdv .det p{margin:0}
  #tagAdv .al p{padding:3px 7px;border-radius:6px;background:#fff3b0;color:var(--tagInk)}
  #tagAdv .al p.lim{background:#ffb3d6}
  #tagAdv .warn{padding:6px 12px;background:#ffb3d6;font-size:12px}
  #tagAdv.min ol,#tagAdv.min .ft{display:none}
  .tagAdvBest{outline:5px solid var(--tagGo)!important;outline-offset:2px;position:relative}
  .tagAdvBest::after{content:attr(data-adv);position:absolute;top:-12px;left:12px;background:var(--tagGo);color:var(--tagInk);border:2px solid var(--tagInk);
    border-radius:8px;padding:1px 8px;font:700 12px/1.4 "Space Grotesk",system-ui,sans-serif;pointer-events:none}`;
  document.head.appendChild(css);
  const box = document.createElement('div'); box.id = 'tagAdv';
  box.innerHTML = `<header><span class="id"><span class="t">Conseiller</span> <a class="v" href="https://github.com/actarus314/conseiller-taxe-giga" target="_blank" rel="noopener">v${VERSION}</a></span>
      <span class="seg" role="group" aria-label="Mode de conseil"><button data-m="auto">Auto</button><button data-m="passif">Passif</button><button data-m="actif">Actif</button></span>
      <span class="ctl"><button data-a="min" aria-label="Réduire">–</button><button data-a="x" aria-label="Fermer">✕</button></span></header>
    <div class="flash" hidden></div>
    <div class="warn" hidden></div><div class="now"></div><ol></ol>
    <div class="ft"><div class="top"><div class="kpi"></div><button data-a="det" aria-expanded="false" aria-label="Détails"><svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2 4.2 6 8.2 10 4.2" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg></button></div><div class="al"></div><div class="det" hidden><label><input id="tagAdvSon" type="checkbox"> 🔔 Son : Facture dorée (rappel 3 s), événement</label><label data-cps>Cadence prévue (Actif) <input id="tagAdvCps" type="text" inputmode="decimal" autocomplete="off"> clics/s</label><div class="dtx"></div></div></div>`;
  document.body.appendChild(box);
  // téléphone : panneau réduit au conseil, la boutique reste visible
  if (innerWidth < PHONE) box.classList.add('min');
  const ui = { flash: box.querySelector('.flash'), now: box.querySelector('.now'), warn: box.querySelector('.warn'), ol: box.querySelector('ol'), kpi: box.querySelector('.kpi'), al: box.querySelector('.al'), det: box.querySelector('.det'), dtx: box.querySelector('.det .dtx'), detBtn: box.querySelector('[data-a="det"]') };
  // N'écrit dans le DOM que ce qui change : innerHTML recrée tous les nœuds même à contenu identique (recalcul de style et de mise en page à chaque tick)
  const shown = {};
  const put = (k, el, prop, v) => { if (shown[k] !== v) { el[prop] = v; shown[k] = v; } };
  // cadence prévue (mode Actif) : champ texte, pour afficher le point décimal quelle que soit la langue du navigateur ;
  // la virgule est acceptée à la saisie, les flèches haut et bas ajoutent ou retirent 0.5
  const cpsIn = box.querySelector('#tagAdvCps'), showCps = () => { cpsIn.value = dec1(cpsPlan); };
  const setCps = v => { cpsPlan = clampCps(String(v).replace(',', '.')); showCps(); store('cps', cpsPlan); tick(); };
  showCps();
  cpsIn.addEventListener('change', () => setCps(cpsIn.value));
  cpsIn.addEventListener('keydown', e => { if (e.key === 'ArrowUp' || e.key === 'ArrowDown') { e.preventDefault(); setCps(cpsPlan + (e.key === 'ArrowUp' ? 0.5 : -0.5)); } });
  const setMode = m => { mode = m; store('mode', m); box.querySelectorAll('[data-m]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.m === m))); box.querySelector('[data-cps]').hidden = m !== 'actif'; tick(); };
  box.addEventListener('click', e => {
    const a = (e.target.closest('[data-a]') || {}).dataset?.a; // un clic sur le chevron (dessin) compte pour son bouton
    if (a === 'min') box.classList.toggle('min'); if (a === 'x') stop();
    if (a === 'det') { detOpen = !detOpen; store('det', detOpen ? '1' : '0'); showDet(); }
    // passage en Actif : détails dépliés tant que l'utilisateur n'a pas choisi lui-même de les ouvrir ou fermer
    if (e.target.dataset.m) { if (e.target.dataset.m === 'actif' && store('det') == null) { detOpen = true; showDet(); } setMode(e.target.dataset.m); }
  });

  // Détail du bas (cadence prévue en Actif, revenu supposé par le plan, moyenne) : replié par défaut, l'état choisi est retenu
  // sans choix de l'utilisateur, ouverts en Actif (réglage de la cadence prévue sous la main), fermés sinon
  let detOpen = store('det') == null ? mode === 'actif' : store('det') === '1';

  // Signal sonore (désactivé par défaut, retenu) : apparition d'une Facture dorée (15 s pour la cliquer), début d'un événement du jeu.
  // Sons synthétisés par le navigateur (Web Audio), sans fichier. Le navigateur n'autorise le son qu'après un geste :
  // cocher la case suffit ; après un rechargement, le premier clic sur la page le rend possible.
  let sonOn = store('son') === '1', actx = null;
  const sonIn = box.querySelector('#tagAdvSon'); sonIn.checked = sonOn;
  const audio = () => {
    try {
      if (!actx) { const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return null; actx = new AC(); }
      if (actx.state === 'suspended') actx.resume();
      return actx;
    } catch (e) { return null; }
  };
  // notes (Hz) jouées l'une après l'autre : Facture dorée, aiguë et brève ; événement, trois notes montantes
  // rappel tant que la facture est affichée : deux notes plus graves, toutes les 3 s (4 rappels au plus sur ses 15 s)
  const SON_FACTURE = [988, 1319, 988, 1319], SON_RAPPEL = [740, 988], RAPPEL = 3000, SON_EVENEMENT = [523, 659, 784];
  const beep = notes => {
    const c = sonOn && audio(); if (!c) return;
    let t = c.currentTime + 0.02;
    for (const f of notes) {
      const o = c.createOscillator(), g = c.createGain();
      o.type = 'sine'; o.frequency.value = f;
      g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.3, t + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.3);
      o.connect(g); g.connect(c.destination); o.start(t); o.stop(t + 0.32); t += 0.16;
    }
  };
  const unlock = () => { if (sonOn) audio(); };
  document.addEventListener('pointerdown', unlock, true);
  sonIn.addEventListener('change', () => { sonOn = sonIn.checked; store('son', sonOn ? '1' : '0'); if (sonOn) beep(SON_FACTURE); });
  let goldWas = false, evWas = null, goldBeep = 0;
  const showDet = () => { ui.det.hidden = !detOpen; ui.detBtn.setAttribute('aria-expanded', String(detOpen)); }; // le chevron tourne avec aria-expanded
  showDet();

  let dragged = false; // déplacé à la main : il garde sa place
  // Position : en bas à droite, au-dessus du bouton TAXER flottant ; sinon en bas à gauche, en haut à droite, en haut à gauche
  // (sous l'en-tête du jeu) : la première qui ne recouvre ni le grand bouton TAXER ni le bouton flottant quand ils sont à l'écran,
  // à défaut celle qui en recouvre le moins. Revue à chaque rafraîchissement (défilement, taille du panneau, bandeaux) ;
  // le DOM n'est réécrit que si elle change.
  const setStyle = (k, v) => { if (box.style[k] !== v) box.style[k] = v; };
  const onScreen = el => { if (!el) return null; const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    return r.width && r.height && r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth && cs.display !== 'none' && cs.visibility !== 'hidden' && +cs.opacity > 0.05 ? r : null; };
  function place() {
    if (dragged) return;
    const st = $('#stickyTax'), h = st ? st.offsetHeight : 64, below = 24 + h + 18;
    const w = box.offsetWidth, hh = box.offsetHeight, hdr = document.querySelector('header:not(#tagAdv header)'), up = Math.round((hdr ? hdr.getBoundingClientRect().bottom : 64) + 8);
    const obst = [onScreen($('#taxBtn')), onScreen(st)].filter(Boolean);
    const low = innerHeight - below - hh, L = 12, R = innerWidth - 12 - w;
    const cands = [{ side: 'right', top: null, l: R, y: low }, { side: 'left', top: null, l: L, y: low }, { side: 'right', top: up, l: R, y: up }, { side: 'left', top: up, l: L, y: up }];
    const area = c => obst.reduce((s, t) => s + Math.max(0, Math.min(c.l + w, t.right) - Math.max(c.l, t.left)) * Math.max(0, Math.min(c.y + hh, t.bottom) - Math.max(c.y, t.top)), 0);
    let pos = cands[0], best = Infinity;
    for (const c of cands) { const a = area(c); if (a < best) { best = a; pos = c; } if (!a) break; }
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
  // état neutre quand le conseil ne peut pas être donné : plus de marque, de fond vert, de suite, ni de titre « 🟢 »
  const blank = msg => {
    unmark(); put('nowClass', ui.now, 'className', 'now'); put('now', ui.now, 'textContent', msg);
    put('ol', ui.ol, 'innerHTML', ''); put('kpi', ui.kpi, 'innerHTML', ''); put('al', ui.al, 'innerHTML', ''); put('det', ui.dtx, 'innerHTML', '');
    const t = baseTitle(); if (document.title !== t) document.title = t;
  };
  // une erreur (page du jeu inattendue, donnée imprévue) s'affiche dans le panneau au lieu de le figer
  function tick() {
    try { tickBody(); } catch (e) { blank('Erreur du conseiller : ' + (e && e.message || e) + '. Recharger la page du jeu.'); }
    place();
  }
  function tickBody() {
    const st = last = read();
    // signaux sonores sur les apparitions seulement (pas au chargement du panneau pour un événement déjà en cours)
    if (st.goldUp && !goldWas) { beep(SON_FACTURE); goldBeep = Date.now(); }
    else if (st.goldUp && Date.now() - goldBeep >= RAPPEL) { beep(SON_RAPPEL); goldBeep = Date.now(); }
    goldWas = st.goldUp;
    const evKey = st.boost.ev ? st.boost.evn + '×' + st.boost.evm : '';
    if (evWas !== null && evKey && evKey !== evWas) beep(SON_EVENEMENT); evWas = evKey;
    // bandeau jaune sous l'en-tête : Facture dorée à l’écran (elle n'y reste que 15 s), puis Rafale en cours
    const flash = st.goldUp ? '🧾 Facture dorée à cliquer !' : st.boost.rf ? `⚡ Rafale : cliquer ! (×${RAFALE}, ${st.boost.rf} s)` : '';
    put('flash', ui.flash, 'textContent', flash); put('flashHidden', ui.flash, 'hidden', !flash);
    // Cadence retenue : la cadence voulue (moyenne mesurée en Auto, réglée en Actif), dans la limite par minute (LIM_MIN),
    // et du reste du quota horaire réparti sur 15 min quand il ne suffit plus.
    const cad = cadence(), left = Math.max(0, LIM_H - cad.hour), capped = left === 0;
    const want = mode === 'actif' ? cpsPlan : mode === 'auto' ? cad.avg : 0;
    const cps = Math.min(want, CPS_MAX, left / HORIZON);
    const why = !want || cps >= want - 0.05 ? '' : capped ? '' : cps < Math.min(want, CPS_MAX) - 0.05 ? `ramenée à ${cpsTxt(cps)} : reste ${left} clics sur le quota de l’heure` : `ramenée à ${dec1(CPS_MAX)}, plafond de ${LIM_MIN} clics par minute`;
    if (!Number.isFinite(st.wallet) || !$('#shop')) { blank('Boutique introuvable : recharger la page du jeu.'); return; }
    if (!st.items.length) { blank('Aucun bonus débloqué : cliquer sur TAXER.'); return; }
    put('warnHidden', ui.warn, 'hidden', !st.drift.length);
    if (st.drift.length) put('warn', ui.warn, 'textContent', `⚠️ Le jeu ne correspond plus au barème connu (${st.drift.join(', ')}) : il a peut-être changé ses règles, conseils à prendre avec prudence.`);
    const out = plan(st, cps, PLAN_LEN), first = out[0];
    if (!first || marked !== first.it.el) unmark();
    if (!first) { blank('Aucun achat à conseiller.'); return; }
    const ready = !first.it.el.disabled; // le bouton du jeu fait foi pour « achetable maintenant »
    // le jeu peut réécrire les classes de la carte : la marque est reposée si elle a disparu
    const adv = ready ? '👉 À ACHETER' : '⏳ ' + dur(first.t);
    if (!first.it.el.classList.contains('tagAdvBest')) first.it.el.classList.add('tagAdvBest');
    if (first.it.el.dataset.adv !== adv) first.it.el.dataset.adv = adv;
    marked = first.it.el;
    put('nowClass', ui.now, 'className', 'now' + (ready ? ' go' : '') + (first.it.u.rate ? ' kp' : ' kc'));
    put('now', ui.now, 'innerHTML', ready
      ? `Acheter maintenant<b>${first.it.u.name}</b>💰 ${fmt(first.c)} · devient ×${first.n}`
      : `<span class="w">${isFinite(first.t) ? `Prochain achat à ${clock(first.t)} (${dur(first.t)})` : 'Prochain achat après quelques clics'}</span>` + `<b>${first.it.u.name}</b>💰 ${fmt(first.c)} · devient ×${first.n}<small>ne rien acheter d’autre d’ici là</small>`);
    put('ol', ui.ol, 'innerHTML', out.slice(1).map(o =>
      // une ligne par achat, dans l'ordre : nom (coupé par « … » s'il est trop long), nombre possédé après achat, prix, heure
      // (marquée quand l'achat est possible tout de suite après le précédent)
      `<li class="${o.it.u.rate ? 'kp' : 'kc'}"><span class="n">${o.it.u.name}</span><span class="k">×${o.n}</span><span class="p">${fmt3(o.c)}</span><span class="h${o.t < 1 ? ' go' : ''}">${clock(o.t)}</span></li>`).join(''));
    // Bas du panneau : chiffres clés toujours visibles, alertes seulement quand elles comptent, détail replié.
    // Production : réelle (parc possédé, ×3 pendant une Frénésie, ×mult pendant un événement). Clics : à la cadence retenue (moyenne mesurée en Auto,
    // réglée en Actif). Le plan suppose leur somme, nommée comme telle dans le détail.
    const prod = prodRate(st.own) * prodMul(st.boost, 0), clk = clickPow(st.own) * cps * (st.boost.rf ? RAFALE : 1);
    // Clics pendant une série (Auto, Actif) : la colonne passe en direct (ce que la série rapporte, Rafale comprise), sur fond vert,
    // sans ligne en plus ; elle revient à la cadence retenue 5 s après le dernier clic. Le plan, lui, garde la cadence retenue.
    const live = mode !== 'passif' && !capped && cad.rate > 0;
    const kpi = [['Production', fmt(prod) + '/s', st.boost.fz || st.boost.ev ? `×${dec1(prodMul(st.boost, 0))} ${st.boost.fz ? 'Frénésie' : 'événement'}` : 'automatique'],
      mode === 'passif' || capped ? ['Clics', 'non comptés', mode === 'passif' ? 'mode Passif' : 'quota de l’heure atteint']
        : live ? ['En direct', '+' + fmt(clickPow(st.own) * cad.rate * (st.boost.rf ? RAFALE : 1)) + '/s', `${dec1(cad.rate)} ${cad.rate >= 2 ? 'clics' : 'clic'}/s` + (st.boost.rf ? ` ×${RAFALE}` : ''), 'live']
        : ['Clics', '+' + fmt(clk) + '/s', `${mode === 'auto' ? 'moyenne' : 'prévus'} ${cpsTxt(cps)}/s` + (st.boost.rf ? ` ×${RAFALE}` : '')],
      ['Cagnotte', '💰 ' + fmt(st.wallet), '']];
    put('kpi', ui.kpi, 'innerHTML', kpi.map(([k, v, sub, cl]) => `<span${cl ? ` class="${cl}"` : ''}><small>${k}</small> <b>${v}</b>${sub ? ` <i>${sub}</i>` : ''}</span>`).join(''));
    const al = [], det = [];
    // courtes : la colonne Production dit déjà que c'est la production qui est multipliée
    if (st.boost.ev) al.push(`📣 ${esc(st.boost.evn)} ×${dec1(st.boost.evm)} · encore ${dur(st.boost.ev)}`);
    if (st.boost.fz) al.push(`🔥 Frénésie ×${dec1(prodMul(st.boost, 0))} · encore ${st.boost.fz} s`);
    // Rafale : signalée par le bandeau jaune du haut seulement (consigne d'action), pas en double ici
    const lim = [];
    if (capped && mode !== 'passif') lim.push(`${LIM_H} clics atteints sur l’heure : les clics ne comptent plus, conseil passif`);
    else if (why) lim.push(`cadence ${why}`);
    if (!capped && cad.hour > LIM_H - 2000) lim.push(`bientôt ${LIM_H} clics sur l’heure : au-delà, ils ne comptent plus`);
    if (cad.minute > LIM_MIN - 60) lim.push(`près de ${LIM_MIN} clics cette minute : au-delà, ils ne comptent plus, et un rythme tenu au plafond ${AUTOCLIC} min est pris pour un autoclic (clics ignorés ${AUTOCLIC} min)`);
    det.push(`plan calculé sur ${fmt(prod + clk)}/s : production` + (cps ? ` + clics à ${cpsTxt(cps)}/s` : ' seule'));
    if (mode === 'auto') det.push(cad.tot ? `moyenne de ${cad.tot} clics sur ${durMin(Math.max(cad.obs, MOY_PLANCHER * 60))}` + (cad.obs < MOY_PLANCHER * 60 ? ' (durée minimale comptée)' : ' de présence (au-delà d’1 h sans clic, minutes écartées)') : 'aucun clic compté sur 24 h : conseil passif');
    put('al', ui.al, 'innerHTML', al.map(t => `<p>${t}</p>`).join('') + lim.map(t => `<p class="lim">⚠️ ${t}</p>`).join(''));
    put('det', ui.dtx, 'innerHTML', det.map(t => `<p>${t}</p>`).join(''));
    const t = (ready ? '🟢 ' + first.it.u.name + ' · ' : '') + baseTitle(); if (document.title !== t) document.title = t;
  }
  let iv = 0;
  function stop() {
    stopped = true; perMinDirty = true; save();
    document.removeEventListener('pointerdown', unlock, true); try { if (actx) actx.close(); } catch (e) { /* déjà fermé */ }
    clearInterval(iv); clearInterval(ivSave); box.remove(); css.remove(); document.title = baseTitle();
    document.removeEventListener('click', onClick, true); removeEventListener('resize', place);
    if (DPIP) DPIP.removeEventListener('enter', onPip);
    if (window.open === openSpy) window.open = winOpen;
    for (const w of minis) try { w.document.removeEventListener('click', onClick, true); } catch (e) { /* fenêtre fermée */ }
    unmark(); if (endDrag) endDrag();
    delete window.__tagAdv;
  }
  // état lu au dernier rafraîchissement (diagnostic depuis la console, et tests) ; déclaré avant le premier rafraîchissement,
  // pour qu'un second clic sur le favori arrête toujours le panneau
  window.__tagAdv = { stop, state: () => last && { wallet: last.wallet, own: { ...last.own }, boost: { ...last.boost }, cadence: cadence(), minis: minis.size } };
  setMode(mode);
  iv = setInterval(tick, TICK);
})();
