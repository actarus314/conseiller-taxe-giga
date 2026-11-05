// Tests du conseiller sur des états simulés au format exact du jeu (jsdom).
// node test.js      → teste conseiller.js ; node test.js bm → teste le favori généré
const { JSDOM } = require('jsdom');
// utilitaires internes de jsdom (pour marquer un clic « de confiance ») : leur chemin a changé en jsdom 30
const utils = (() => {
  for (const p of ['jsdom/lib/generated/idl/utils', 'jsdom/lib/jsdom/living/generated/utils']) { try { return require(p); } catch (e) { /* chemin suivant */ } }
  throw new Error('jsdom : utilitaires internes introuvables');
})();
const fs = require('fs'), path = require('path'), ROOT = path.join(__dirname, '..', '..');
const SRC = process.argv[2] === 'bm'
  ? decodeURIComponent(fs.readFileSync(path.join(ROOT, 'bookmarklet.txt'), 'utf8').trim().slice(11))
  : fs.readFileSync(path.join(ROOT, 'conseiller.js'), 'utf8');

// formatage du jeu (fonction big() de la page)
const int = n => new Intl.NumberFormat('fr-FR').format(n), nf = d => new Intl.NumberFormat('fr-FR', { minimumFractionDigits: d, maximumFractionDigits: d });
const big = n => n < 1e6 ? int(Math.floor(n)) : n < 1e9 ? nf(2).format(n / 1e6) + ' M' : n < 1e15 ? nf(2).format(n / 1e9) + ' Md' : nf(2).format(n / 1e12) + ' billions';
const B = { mainetat: 5e8, decret: 1e9, doigt: 10, stagiaire: 15, chat: 100, hamster: 600, souris: 500, bot: 6000, fax: 6e4, commission: 6e5, gant: 15e4, satellite: 5e6, trounoir: 7.5e7, tampon: 2e7, datacenter: 1e9 };
const sleep = ms => new Promise(r => setTimeout(r, ms));
let fails = 0;
const check = (ok, msg) => { console.log((ok ? '  ok   ' : '  ÉCHEC ') + msg); if (!ok) fails++; };

async function page({ owned, wallet, mode = 'auto', cps = 5, perClick, chip, clicks = [], hourClicks = 0, hist = null, ev = null, mini = null, det = false, detClosed = false, clickDet = false, cpsInput = null, clickMode = null, at = 0, done = [], gold = false, save = null }) {
  const items = Object.entries(owned).map(([id, n]) => {
    const c = Math.ceil(B[id] * 1.15 ** n), d = done.includes(id);
    return `<button class="item" data-id="${id}" ${d || wallet < c ? 'disabled' : ''}><span class="ic"><b class="own">${d ? '✓' : '×' + n}</b><small class="price">${d ? 'acquis' : '💰 ' + big(c)}</small></span></button>`;
  }).join('');
  const dom = new JSDOM(`<title>Jeu</title><b id="wallet">${big(wallet)}</b><span id="perClick">${perClick || ''}</span><p id="buffChip" ${chip ? '' : 'hidden'}>${chip || ''}</p><button id="goldBill" ${gold ? '' : 'hidden'}>Facture dorée</button>
    <button id="taxBtn">TAXER</button><button id="stickyTax">T</button><div id="shop">${items}</div>`, { runScripts: 'outside-only', url: 'https://taxe-au-giga.fr/' });
  const w = dom.window, d = w.document;
  let now = 1793700000000; w.Date.now = () => now; // horloge simulée
  const timers = new Map(); let timerId = 0; // minuteries simulées : un « tour de mise à jour » se joue d'un appel, sans attendre 650 ms réelles
  w.setInterval = (f, ms) => { timers.set(++timerId, { f, ms }); return timerId; }; w.clearInterval = id => { timers.delete(id); };
  if (det) w.localStorage.setItem('tagAdv-det', '1');
  if (detClosed) w.localStorage.setItem('tagAdv-det', '0');
  if (ev) w.localStorage.setItem('tagAdv-ev', JSON.stringify({ nm: ev.nm, mult: ev.mult, to: now + ev.left * 1000 }));
  w.localStorage.setItem('tagAdv-mode', mode); w.localStorage.setItem('tagAdv-cps', String(cps));
  if (save) { const sv = typeof save === 'number' ? { w: save, at } : save; w.localStorage.setItem('taxe-giga-partie-v1', JSON.stringify({ wallet: sv.w, owned: {}, myCount: 0, t: now + sv.at * 1000 })); }
  if (hourClicks || hist) {
    const m0 = Math.floor(now / 60e3), pm = {};
    for (const [ago, n] of Object.entries(hist || {})) pm[m0 - ago] = n;
    if (hourClicks) pm[m0 - 5] = (pm[m0 - 5] || 0) + hourClicks;
    w.localStorage.setItem('tagAdv-clics', JSON.stringify(pm));
    if (hist) w.localStorage.setItem('tagAdv-vu', String(m0 - Math.max(...Object.keys(hist).map(Number)))); // historique observé par la v2.14
  }
  // mode mini du jeu : petite fenêtre avec son propre bouton TAXER (#mTax)
  const mw = mini && new JSDOM('<button id="mTax">TAXER !</button>').window;
  let tgt = d.getElementById('taxBtn');
  const stubOpen = () => mw;
  if (mini === 'popup') w.open = stubOpen;
  if (mini && mini.startsWith('pip')) { w.documentPictureInPicture = new w.EventTarget(); if (mini === 'pip-avant') w.documentPictureInPicture.window = mw; }
  w.eval(SRC);
  if (mini === 'popup') w.open('', 'taxe-giga-mini', 'popup');
  if (mini === 'pip-apres') { const ev = new w.Event('enter'); ev.window = mw; w.documentPictureInPicture.dispatchEvent(ev); }
  if (mini) tgt = mw.document.getElementById('mTax');
  // clics « de confiance » sur TAXER, à des instants donnés (secondes)
  for (const s of clicks) {
    now = 1793700000000 + s * 1000;
    const e = new w.MouseEvent('click', { bubbles: true }), ei = utils.implForWrapper(e); ei.isTrusted = true;
    utils.implForWrapper(tgt)._dispatch(ei);
  }
  now = 1793700000000 + at * 1000;
  if (clickDet) d.querySelector('#tagAdv [data-a="det"] path').dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
  if (clickMode) d.querySelector(`#tagAdv [data-m="${clickMode}"]`).click();
  if (cpsInput != null) { const ci = d.getElementById('tagAdvCps'); ci.value = cpsInput; ci.dispatchEvent(new w.Event('change')); }
  const refresh = [...timers.values()].reduce((a, b) => (b.ms < a.ms ? b : a)); refresh.f(); // un tour de mise à jour du panneau
  // garde-fou de performance : 20 tours de plus sans aucun changement ne doivent rien écrire dans la page
  const mo = new w.MutationObserver(() => {}); mo.observe(d, { subtree: true, childList: true, attributes: true, characterData: true });
  for (let i = 0; i < 20; i++) refresh.f();
  const idleMutations = mo.takeRecords().length; mo.disconnect();
  const r = {
    now: d.querySelector('#tagAdv .now').textContent, cpsShown: !d.querySelector('#tagAdv [data-cps]').hidden, cpsVal: d.getElementById('tagAdvCps').value, goTimes: d.querySelectorAll('#tagAdv ol .h.go').length, list: [...d.querySelectorAll('#tagAdv li')].map(l => [...l.children].map(c => c.textContent).join(' ')),
    ft: [...d.querySelectorAll('#tagAdv .kpi span, #tagAdv .al p, #tagAdv .det p')].map(e => e.textContent).join(' · '),
    alerts: [...d.querySelectorAll('#tagAdv .al p')].map(e => e.textContent), detHidden: d.querySelector('#tagAdv .det').hidden, warn: d.querySelector('#tagAdv .warn').hidden ? '' : d.querySelector('#tagAdv .warn').textContent,
    best: d.querySelector('.tagAdvBest')?.dataset.id, adv: d.querySelector('.tagAdvBest')?.dataset.adv,
    idleMutations, repo: d.querySelector('#tagAdv header a.v')?.getAttribute('href'), state: w.eval('window.__tagAdv.state()'), text: d.querySelector('#tagAdv').textContent, z: parseInt(w.getComputedStyle(d.querySelector('#tagAdv')).zIndex, 10), titles: d.querySelectorAll('#tagAdv [title]').length, docTitle: d.title,
  };
  w.eval('window.__tagAdv.stop()'); r.openRestored = mini !== 'popup' || w.open === stubOpen; r.stopped = !d.querySelector('#tagAdv') && !d.querySelector('.tagAdvBest') && !d.querySelector('[data-adv]'); r.timers = timers.size; w.close();
  return r;
}
const every = (n, from, to) => Array.from({ length: Math.round((to - from) * n) }, (_, i) => from + i / n);

(async () => {
  // état réel de la partie à 11 h 52 (lu sur le serveur), puissance de clic serveur 5770
  const o = { doigt: 14, stagiaire: 32, chat: 29, hamster: 25, souris: 6, bot: 20, fax: 15, commission: 11, gant: 9, satellite: 2, trounoir: 0, tampon: 0 };
  const base = { owned: o, wallet: 9847633, perClick: '5 770 visites' };

  console.log('Passif : même plan que le simulateur Python (Satellite puis Fax, Bots, Hamster)');
  let r = await page({ ...base, mode: 'passif' });
  check(r.best === 'satellite' && /Acheter maintenant/.test(r.now), r.now);
  check(/Fax.*×16/.test(r.list[0]) && /Ferme de bots ×21/.test(r.list[1]) && /Hamster-routeur ×26/.test(r.list[2]), 'suite : ' + r.list.slice(0, 3).join(' | '));
  check(r.goTimes === 3, `heure en pastille verte pour les 3 achats possibles aussitôt : ${r.goTimes}`);
  check(/Production 22174\/s automatique/.test(r.ft) && /Clics non comptés mode Passif/.test(r.ft) && /plan calculé sur 22174\/s : production seule/.test(r.ft), r.ft);
  check(r.stopped && r.timers === 0, 'arrêt propre : panneau, marque et minuteries retirés (minuteries restantes : ' + r.timers + ')');

  console.log('Actif 5/s : revenu 51024/s comme le simulateur, Doigts en premier');
  r = await page({ ...base, mode: 'actif', cps: 5 });
  check(r.best === 'doigt' && /Clics \+28850\/s prévus 5\/s/.test(r.ft) && /plan calculé sur 51024\/s : production \+ clics à 5\/s/.test(r.ft), r.ft);

  console.log('Auto sans clic : conseil passif');
  r = await page({ ...base });
  check(r.best === 'satellite' && /aucun clic compté sur 24 h/.test(r.ft), r.ft);

  // historique : minutes écoulées → clics comptés dans cette minute (0 = minute observée sans clic)
  const minutes = (from, to, f) => Object.fromEntries(Array.from({ length: to - from + 1 }, (_, i) => [from + i, f(from + i)]));

  console.log('Auto, 3 h de présence à 30 clics par minute : conseil à 0.50 clic/s (revenu 25059/s)');
  r = await page({ ...base, hist: minutes(1, 179, () => 30) });
  check(/moyenne 0.50\/s/.test(r.ft) && /moyenne de 5370 clics sur 2 h 59 de présence/.test(r.ft) && /plan calculé sur 25059\/s/.test(r.ft), r.ft);

  console.log('Auto, séries de 2 min à 5 clics/s trois fois par heure : même conseil pendant et entre les séries');
  {
    const h = minutes(1, 120, m => m % 20 < 2 ? 300 : 0);
    const entre = await page({ ...base, hist: h });
    const pendant = await page({ ...base, hist: h, clicks: every(5, 0, 30), at: 30 });
    check(/moyenne 0.50\/s/.test(entre.ft) && /plan calculé sur 25167\/s : production \+ clics à 0.52\/s/.test(pendant.ft) && /En direct \+28850\/s 5 clics\/s/.test(pendant.ft) && entre.best === pendant.best,
      'entre : ' + entre.best + ' | pendant : ' + pendant.best + ' | ' + pendant.ft);
  }

  console.log('Auto, 10 min observées avec 600 clics : moyenne comptée sur 30 min au moins (0.33 clic/s)');
  r = await page({ ...base, hist: minutes(1, 10, () => 60) });
  check(/moyenne 0.33\/s/.test(r.ft) && /moyenne de 600 clics sur 30 min \(durée minimale comptée\)/.test(r.ft), r.ft);

  console.log('Auto, une seule série de 60 s à 5 clics/s sur un panneau qui vient de s’ouvrir : 0.17 clic/s, pas 5');
  r = await page({ ...base, clicks: every(5, 0, 60), at: 60 });
  check(/clics à 0.17\/s/.test(r.ft) && /plan calculé sur 23136\/s/.test(r.ft), r.ft);

  console.log('Auto, minutes notées par une version antérieure (clics seuls, sans les minutes sans clic) : hors de la moyenne, dans le quota');
  r = await page({ ...base, hourClicks: 3600 });
  check(/aucun clic compté sur 24 h/.test(r.ft) && r.state.cadence.hour === 3600, r.ft);

  console.log('Auto, clics de plus de 24 h : oubliés, conseil passif');
  r = await page({ ...base, hist: { 1500: 300 } });
  check(r.best === 'satellite' && /aucun clic compté sur 24 h/.test(r.ft), r.ft);

  console.log('Auto, retour après une nuit de 8 h onglet ouvert : moyenne d’avant la nuit retrouvée (au-delà d’1 h sans clic, absence écartée)');
  // 2 h à 30 clics par minute (10 h à 8 h avant), puis 8 h sans clic : 120 minutes de clics + 60 minutes de pause comptées
  r = await page({ ...base, hist: minutes(1, 600, a => a > 480 ? 30 : 0) });
  check(/moyenne 0.33\/s/.test(r.ft) && /moyenne de 3600 clics sur 3 h 00 de présence/.test(r.ft), r.ft.slice(0, 200));

  console.log('Auto, 24000 clics déjà comptés sur l’heure : conseil passif et alerte');
  r = await page({ ...base, clicks: every(5, 0, 30), at: 30, hourClicks: 24000 });
  check(r.best === 'satellite' && r.alerts.some(t => /24000 clics atteints/.test(t)) && /Clics non comptés quota de l’heure atteint/.test(r.ft), r.ft);

  console.log('Actif 5/s mais 23150 clics comptés sur l’heure : reste du quota réparti sur 15 min');
  r = await page({ ...base, mode: 'actif', cps: 5, clicks: every(5, 0, 30), at: 30, hourClicks: 23000 });
  check(/ramenée à 0.94 : reste 850 clics/.test(r.ft), r.ft);

  for (const [m, lab] of [['pip-avant', 'image dans l’image ouverte avant le panneau'], ['pip-apres', 'image dans l’image ouverte après le panneau'], ['popup', 'fenêtre surgissante']]) {
    console.log(`Mode mini du jeu (${lab}) : clics de sa petite fenêtre comptés`);
    r = await page({ ...base, mini: m, clicks: every(5, 0, 30), at: 30 });
    check(r.state.cadence.tot === 150 && /En direct \+28850\/s 5 clics\/s/.test(r.ft) && r.openRestored, `${r.state.cadence.tot} clics comptés · window.open rendu : ${r.openRestored} | ${r.ft.slice(-90)}`);
  }

  console.log('Bas du panneau : détail replié par défaut, alertes visibles ; Frénésie en alerte');
  r = await page({ ...base, mode: 'passif', chip: '🔥 Frénésie fiscale : production ×3 encore 40 s' });
  check(r.detHidden && r.alerts.length === 1 && /Frénésie/.test(r.alerts[0]), 'détail masqué : ' + r.detHidden + ' | alertes : ' + r.alerts.join(' / '));

  console.log('Bas du panneau : détail déplié s’il l’a été la dernière fois');
  r = await page({ ...base, det: true });
  check(!r.detHidden, 'détail masqué : ' + r.detHidden);

  console.log('Actif : cadence prévue affichée avec un point, virgule acceptée à la saisie');
  r = await page({ ...base, mode: 'actif', cps: 5.8 });
  const r2 = await page({ ...base, mode: 'actif', cpsInput: '6,5' });
  check(r.cpsVal === '5.8' && r2.cpsVal === '6.5' && /prévus 6.5\/s/.test(r2.ft), `affiché ${r.cpsVal} | saisi « 6,5 » → ${r2.cpsVal}`);

  console.log('En direct : production de la série de clics en cours (Auto, Actif), Rafale comprise ; rien en Passif ni après 8 s sans clic');
  {
    const auto = await page({ ...base, clicks: every(5, 0, 30), at: 30 });
    const rafale = await page({ ...base, mode: 'actif', clicks: every(5, 0, 30), at: 30, chip: '⚡ Rafale de clics : chaque clic ×10 encore 13 s' });
    const passif = await page({ ...base, mode: 'passif', clicks: every(5, 0, 30), at: 30 });
    const fini = await page({ ...base, clicks: every(5, 0, 30), at: 39 });
    check(/En direct \+28850\/s 5 clics\/s/.test(auto.ft) && /En direct \+288500\/s 5 clics\/s ×10/.test(rafale.ft) && !/En direct/.test(passif.ft) && !/En direct/.test(fini.ft) && /Clics \+481\/s moyenne 0.08\/s/.test(fini.ft),
      [auto, rafale, passif, fini].map(x => (x.ft.match(/(En direct|Clics)[^·]*/) || ['—'])[0]).join(' | '));
  }

  console.log('Événement du jeu lu sur son indicateur : production ×2 pendant sa durée, alerte, plan qui en tient compte');
  {
    r = await page({ ...base, mode: 'passif', chip: '📣 Jour de mobilisation : production ×2 jusqu’à 20 h · encore 7 h 40' });
    check(/Production 44348\/s ×2 événement/.test(r.ft) && r.alerts.some(t => /Jour de mobilisation encore 7 h 40 : production ×2/.test(t)) && r.state.boost.ev === 27600 && /plan calculé sur 44348\/s/.test(r.ft),
      r.ft.slice(0, 120) + ' | ' + r.alerts.join(' / ') + ' | durée ' + r.state.boost.ev);
    console.log('Événement retenu quand l’indicateur montre une Frénésie (×4 = 1 + 2 + 2 − 1)');
    r = await page({ ...base, mode: 'passif', ev: { nm: 'Jour de mobilisation', mult: 2, left: 3600 }, chip: '🔥 Frénésie fiscale : production ×4 encore 40 s' });
    check(/Production 88696\/s ×4 Frénésie/.test(r.ft) && r.alerts.some(t => /Jour de mobilisation/.test(t)), r.ft.slice(0, 120));
    console.log('Frénésie ×4 sans événement connu : multiplicateur déduit pour la durée de la Frénésie');
    r = await page({ ...base, mode: 'passif', chip: '🔥 Frénésie fiscale : production ×4 encore 40 s' });
    check(/Production 88696\/s ×4 Frénésie/.test(r.ft) && r.state.boost.ev === 40, r.ft.slice(0, 120));
  }

  console.log('Passage en Actif : détails dépliés avec le réglage de la cadence prévue ; réglage caché en Auto');
  r = await page({ ...base, clickMode: 'actif' });
  const rAuto = await page({ ...base, det: true });
  check(!r.detHidden && r.cpsShown&& !rAuto.cpsShown, `Actif : détails ${r.detHidden ? 'repliés' : 'dépliés'}, réglage ${r.cpsShown ? 'visible' : 'caché'} | Auto : réglage ${rAuto.cpsShown ? 'visible' : 'caché'}`);

  console.log('Détails : choix retenu (fermés par l’utilisateur, ils restent fermés en passant en Actif), ouverts par défaut au chargement en Actif, chevron cliquable');
  {
    const ferme = await page({ ...base, detClosed: true, clickMode: 'actif' });
    const charge = await page({ ...base, mode: 'actif' });
    const chevron = await page({ ...base, clickDet: true });
    check(ferme.detHidden && !charge.detHidden && !chevron.detHidden, `fermés puis Actif : ${ferme.detHidden ? 'fermés' : 'ouverts'} | chargement en Actif : ${charge.detHidden ? 'fermés' : 'ouverts'} | clic sur le chevron : ${chevron.detHidden ? 'fermés' : 'ouverts'}`);
  }

  console.log('En direct : cadence des 5 dernières secondes (passage de 5 à 8 clics/s vu en 5 s, pause de 4 s visible)');
  {
    const acc = await page({ ...base, clicks: [...every(5, 0, 20), ...every(8, 20, 30)], at: 30 });
    const pause = await page({ ...base, clicks: every(5, 0, 30), at: 34 });
    check(/En direct \+\S+ 8 clics\/s/.test(acc.ft) && /En direct \+\S+ 1 clic\/s/.test(pause.ft),
      [acc, pause].map(x => (x.ft.match(/En direct[^·]*/) || ['—'])[0]).join(' | '));
  }

  console.log('Rafale à l’écran : consigne de cliquer dans l’en-tête');
  r = await page({ ...base, chip: '⚡ Rafale de clics : chaque clic ×10 encore 13 s' });
  check(/⚡ Rafale : cliquer ! \(×10, 13 s\)/.test(r.text), 'en-tête : ' + r.text.slice(0, 40));

  console.log('Frénésie de 40 s comptée (Commission plus tôt)');
  r = await page({ owned: { ...o, hamster: 26, bot: 21, fax: 16, satellite: 3 }, wallet: 2628957, perClick: '5 803 visites', mode: 'passif', chip: '🔥 Frénésie fiscale : production ×3 encore 40 s' });
  check(r.best === 'commission' && /Prochain achat dans 3 s/.test(r.now) && /Production 76266\/s ×3 Frénésie/.test(r.ft) && r.alerts.some(t => /Frénésie encore 40 s/.test(t)), r.now + ' | ' + r.ft);

  console.log('Rafale de 13 s en mode Actif 5/s : clics ×10 dans le revenu et les délais');
  r = await page({ ...base, mode: 'actif', cps: 5, wallet: 2e6, chip: '⚡ Rafale de clics : chaque clic ×10 encore 13 s' });
  check(/plan calculé sur 310674\/s/.test(r.ft) && /×10/.test(r.ft) && /⚡ Rafale : cliquer ! \(×10, 13 s\)/.test(r.text) && !r.alerts.some(t => /Rafale/.test(t)), r.ft);

  console.log('Rafale en mode Passif : signalée sans être comptée');
  r = await page({ ...base, mode: 'passif', chip: '⚡ Rafale de clics : chaque clic ×10 encore 13 s' });
  check(/⚡ Rafale : cliquer ! \(×10, 13 s\)/.test(r.text) && /plan calculé sur 22174\/s : production seule/.test(r.ft), r.ft);

  console.log('Facture dorée à l’écran : signalée dans l’en-tête, panneau sous elle (z-index < 70)');
  r = await page({ ...base, gold: true });
  check(/Facture dorée à cliquer/.test(r.text) && r.z < 70, 'en-tête : ' + r.text.slice(0, 32) + ' | z-index ' + r.z);

  console.log('Puissance de clic affichée différente du modèle : alerte');
  r = await page({ ...base, perClick: '9 999 visites' });
  check(/puissance de clic/.test(r.warn), r.warn);

  // état serveur de 14 h 25 : production 186728.5/s, 495240 visites par clic
  const o2 = { doigt: 46, stagiaire: 45, chat: 41, hamster: 38, souris: 34, bot: 33, fax: 28, commission: 24, gant: 21, satellite: 16, trounoir: 7, tampon: 12, mainetat: 0, decret: 0, datacenter: 0 };
  console.log('Main de l’État (achat unique) non achetée : pas conseillée, rentable bien après le Tampon');
  r = await page({ owned: o2, wallet: 43557887, perClick: '495 240 visites', mode: 'actif', cps: 5 });
  check(r.best === 'tampon' && !r.list.some(l => /Main de l/.test(l)) && !r.warn, r.now + ' | ' + r.list.join(' | '));

  console.log('Main de l’État achetée (✓ « acquis ») : comptée dans la puissance de clic (497107), jamais reproposée');
  r = await page({ owned: { ...o2, mainetat: 1 }, done: ['mainetat'], wallet: 43557887, perClick: '497 107 visites', mode: 'actif', cps: 5 });
  check(!r.warn && /Clics \+2.49 M\/s/.test(r.ft) && !r.list.some(l => /Main de l/.test(l)), r.ft + ' | alerte : ' + (r.warn || 'aucune'));

  console.log('Cagnotte en milliards : valeur fine tirée de la sauvegarde du jeu, compte à rebours à la seconde');
  // affichage « 1,14 Md » (arrondi à 10 M près) ; sauvegarde exacte 1144900000 ; Datacenter ×1 : 60000/s, prochain à 1.15 Md
  r = await page({ owned: { datacenter: 1 }, wallet: 1144900000, mode: 'passif', save: 1144900000 });
  const r3 = await page({ owned: { datacenter: 1 }, wallet: 1144900000, mode: 'passif' });
  check(/dans 1 min 25 s/.test(r.now) && /dans 2 min 47 s/.test(r3.now), 'avec sauvegarde : ' + r.now.slice(0, 40) + ' | sans : ' + r3.now.slice(0, 40));

  console.log('Clics faits depuis la sauvegarde du jeu ajoutés à la cagnotte estimée');
  // Datacenter ×1 (60000/s), Tampon ×35 (clic : 1 + 35 × 40000 + 1 % × 60000 = 1400601) ; sauvegarde 1140000000 à t = 0,
  // 2 clics à 1 et 2 s, lecture à 3 s : 1140000000 + 3 × 60000 + 2 × 1400601 = 1142981202, dans l’arrondi de « 1,14 Md »
  r = await page({ owned: { datacenter: 1, tampon: 35 }, wallet: 1140000000, mode: 'actif', cps: 5, save: { w: 1140000000, at: 0 }, clicks: [1, 2], at: 3 });
  check(Math.abs(r.state.wallet - 1142981202) < 2, 'cagnotte estimée ' + r.state.wallet);

  console.log('Cagnotte et prix au-delà de 1e15, affichés en « billions » depuis le build 2026-11-03m');
  // Taxe quantique ×50 : prix 2e12 × 1.15^50 ≈ 2,17 billions ; cagnotte 3,00 billions
  r = await page({ owned: { quantique: 50 }, wallet: 3e15, mode: 'passif' });
  check(!r.warn && Math.abs(r.state.wallet - 3e15) <= 5e9 && /Taxe quantique/.test(r.now + r.list.join(' ')), 'cagnotte ' + r.state.wallet + ' | ' + r.now.slice(0, 60) + ' | alerte : ' + (r.warn || 'aucune'));

  console.log('Version affichée dans l’en-tête, égale à celle du script utilisateur');
  {
    const v = (fs.readFileSync(path.join(ROOT, 'conseiller.user.js'), 'utf8').match(/@version\s+(\S+)/) || [])[1];
    r = await page({ ...base });
    check(v && r.text.includes('Conseiller v' + v), 'en-tête : ' + r.text.slice(0, 24) + ' | @version ' + v);
    check(r.repo === 'https://github.com/actarus314/conseiller-taxe-giga', 'lien du numéro de version : ' + r.repo);
  }

  console.log('Performance : aucune écriture dans la page quand rien ne change, favoris de taille raisonnable');
  for (const [lab, opts] of [['passif', { ...base, mode: 'passif' }], ['actif', { ...base, mode: 'actif', cps: 5 }], ['frénésie', { ...base, mode: 'passif', chip: '🔥 Frénésie fiscale : production ×3 encore 40 s' }]]) {
    r = await page(opts);
    check(r.idleMutations === 0, `${lab} : ${r.idleMutations} écriture(s) dans la page sur 20 tours sans changement`);
  }
  {
    const fige = fs.readFileSync(path.join(ROOT, 'bookmarklet.txt'), 'utf8').trim().length, auto = fs.readFileSync(path.join(ROOT, 'bookmarklet-auto.txt'), 'utf8').trim().length;
    // plafond du favori figé : Firefox n'enregistre pas un favori de plus de 65536 caractères (URL_LENGTH_MAX de Places),
    // Chrome accepte 2 Mo (kMaxURLChars) ; limite de Safari non trouvée. 60000 garde une marge sous Firefox.
    check(fige < 60000 && auto < 500, `taille des favoris : figé ${fige} caractères (plafond 60000), à jour ${auto} (plafond 500)`);
  }

  console.log('Forme : nombres au point décimal sans séparateur, aucune info-bulle native, aucun « vous »');
  r = await page({ ...base, clicks: every(5, 0, 60), at: 60 });
  const t = r.text.replace(/\d{2}:\d{2}/g, '');
  check(!/\d \d{3}\b/.test(t) && !/\d,\d/.test(t), 'aucun « 1 234 » ni « 6,61 » dans le panneau');
  check(r.titles === 0, 'aucun attribut title');
  check(!/\b(vous|tu|achetez)\b/i.test(r.text), 'formulations impersonnelles');

  console.log('Hors de taxe-au-giga.fr : panneau et favori à jour refusent de démarrer');
  {
    const dom = new JSDOM(`<b id="wallet">0</b><div id="shop"></div>`, { runScripts: 'outside-only', url: 'https://mail.example.com/' });
    const w = dom.window; let msg = '', fetched = 0; w.alert = m => { msg += m + ' | '; }; w.fetch = async () => { fetched++; return { ok: true, text: async () => '' }; };
    w.eval(SRC);
    w.eval(decodeURIComponent(fs.readFileSync(path.join(ROOT, 'bookmarklet-auto.txt'), 'utf8').trim().slice(11)));
    await new Promise(r => setTimeout(r, 50));
    check(!w.document.querySelector('#tagAdv') && fetched === 0 && (msg.match(/à lancer sur taxe-au-giga\.fr/g) || []).length === 2, `panneau ${!!w.document.querySelector('#tagAdv')} · chargements ${fetched} · alertes « ${msg} »`);
    w.close();
  }

  console.log('Favori à jour : charge conseiller.js depuis GitHub Pages (paramètre à la minute), ouvre puis ferme le panneau');
  {
    const auto = fs.readFileSync(path.join(ROOT, 'bookmarklet-auto.txt'), 'utf8').trim();
    const dom = new JSDOM(`<b id="wallet">0</b><div id="shop"></div>`, { runScripts: 'outside-only', url: 'https://taxe-au-giga.fr/' });
    const w = dom.window, urls = [];
    const real = fs.readFileSync(path.join(ROOT, 'conseiller.js'), 'utf8');
    w.fetch = async u => { urls.push(u); return { ok: true, text: async () => real }; };
    w.eval(decodeURIComponent(auto.slice(11))); await sleep(100);
    const opened = !!w.document.querySelector('#tagAdv');
    w.eval(decodeURIComponent(auto.slice(11))); await sleep(100);
    const closed = !w.document.querySelector('#tagAdv');
    check(/^https:\/\/actarus314\.github\.io\/conseiller-taxe-giga\/conseiller\.js\?m=\d+$/.test(urls[0]) && opened && closed, `adresse ${urls[0]} · ouvert ${opened} · refermé ${closed}`);
    let alerted = ''; w.alert = m => { alerted = m; }; w.fetch = async () => ({ ok: false, status: 404 });
    w.eval(decodeURIComponent(auto.slice(11))); await sleep(100);
    check(/chargement impossible.*404/.test(alerted), 'échec de chargement signalé : ' + alerted);
    w.close();
  }

  console.log(fails ? `\n${fails} échec(s)` : '\nTout est passé');
  process.exit(fails ? 1 : 0);
})();
