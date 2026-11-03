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
const big = n => n < 1e6 ? int(Math.floor(n)) : n < 1e9 ? nf(2).format(n / 1e6) + ' M' : nf(2).format(n / 1e9) + ' Md';
const B = { mainetat: 5e8, decret: 1e9, doigt: 10, stagiaire: 15, chat: 100, hamster: 600, souris: 500, bot: 6000, fax: 6e4, commission: 6e5, gant: 15e4, satellite: 5e6, trounoir: 7.5e7, tampon: 2e7, datacenter: 1e9 };
const sleep = ms => new Promise(r => setTimeout(r, ms));
let fails = 0;
const check = (ok, msg) => { console.log((ok ? '  ok   ' : '  ÉCHEC ') + msg); if (!ok) fails++; };

async function page({ owned, wallet, mode = 'auto', cps = 5, perClick, chip, clicks = [], hourClicks = 0, at = 0, done = [], gold = false, save = null }) {
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
  w.localStorage.setItem('tagAdv-mode', mode); w.localStorage.setItem('tagAdv-cps', String(cps));
  if (save) { const sv = typeof save === 'number' ? { w: save, at } : save; w.localStorage.setItem('taxe-giga-partie-v1', JSON.stringify({ wallet: sv.w, owned: {}, myCount: 0, t: now + sv.at * 1000 })); }
  if (hourClicks) w.localStorage.setItem('tagAdv-clics', JSON.stringify({ [Math.floor(now / 60e3) - 5]: hourClicks }));
  w.eval(SRC);
  // clics « de confiance » sur TAXER, à des instants donnés (secondes)
  for (const s of clicks) {
    now = 1793700000000 + s * 1000;
    const e = new w.MouseEvent('click', { bubbles: true }), ei = utils.implForWrapper(e); ei.isTrusted = true;
    utils.implForWrapper(d.getElementById('taxBtn'))._dispatch(ei);
  }
  now = 1793700000000 + at * 1000;
  const refresh = [...timers.values()].reduce((a, b) => (b.ms < a.ms ? b : a)); refresh.f(); // un tour de mise à jour du panneau
  // garde-fou de performance : 20 tours de plus sans aucun changement ne doivent rien écrire dans la page
  const mo = new w.MutationObserver(() => {}); mo.observe(d, { subtree: true, childList: true, attributes: true, characterData: true });
  for (let i = 0; i < 20; i++) refresh.f();
  const idleMutations = mo.takeRecords().length; mo.disconnect();
  const r = {
    now: d.querySelector('#tagAdv .now').textContent, list: [...d.querySelectorAll('#tagAdv li')].map(l => l.textContent),
    ft: d.querySelector('#tagAdv .ft').textContent, warn: d.querySelector('#tagAdv .warn').hidden ? '' : d.querySelector('#tagAdv .warn').textContent,
    best: d.querySelector('.tagAdvBest')?.dataset.id, adv: d.querySelector('.tagAdvBest')?.dataset.adv,
    idleMutations, repo: d.querySelector('#tagAdv header a.v')?.getAttribute('href'), state: w.eval('window.__tagAdv.state()'), text: d.querySelector('#tagAdv').textContent, z: parseInt(w.getComputedStyle(d.querySelector('#tagAdv')).zIndex, 10), titles: d.querySelectorAll('#tagAdv [title]').length, docTitle: d.title,
  };
  w.eval('window.__tagAdv.stop()'); r.stopped = !d.querySelector('#tagAdv') && !d.querySelector('.tagAdvBest') && !d.querySelector('[data-adv]'); r.timers = timers.size; w.close();
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
  check(/Revenu 22174\/s/.test(r.ft), r.ft);
  check(r.stopped && r.timers === 0, 'arrêt propre : panneau, marque et minuteries retirés (minuteries restantes : ' + r.timers + ')');

  console.log('Actif 5/s : revenu 51024/s comme le simulateur, Doigts en premier');
  r = await page({ ...base, mode: 'actif', cps: 5 });
  check(r.best === 'doigt' && /Revenu 51024\/s \(dont clics 28850\)/.test(r.ft), r.ft);

  console.log('Auto sans clic : conseil passif');
  r = await page({ ...base });
  check(r.best === 'satellite' && /aucun clic récent/.test(r.ft), r.ft);

  console.log('Auto, 5 clics/s pendant 60 s : conseil actif à 5/s');
  r = await page({ ...base, clicks: every(5, 0, 60), at: 60 });
  check(r.best === 'doigt' && /calculé pour 5 clics\/s/.test(r.ft) && /Revenu 51024\/s/.test(r.ft), r.ft);

  console.log('Auto, 3 clics/s pendant 20 s : conseil à 3/s (revenu 39484/s)');
  r = await page({ ...base, clicks: every(3, 0, 20), at: 20 });
  check(/calculé pour 3 clics\/s/.test(r.ft) && /Revenu 39484\/s/.test(r.ft), r.ft);

  console.log('Auto, 8 clics/s : gardé tel quel (sous 760/min, quota horaire suffisant)');
  r = await page({ ...base, clicks: every(8, 0, 30), at: 30 });
  check(/calculé pour 8 clics\/s \(cadence mesurée\)/.test(r.ft), r.ft);

  console.log('Auto, 15 clics/s : ramené à 12.7/s (760 par minute), avec la raison');
  r = await page({ ...base, clicks: every(15, 0, 20), at: 20 });
  check(/calculé pour 12.7 clics\/s/.test(r.ft) && /760 clics par minute/.test(r.ft), r.ft);

  console.log('Auto, 5 clics/s mais 17000 clics déjà comptés : reste du quota réparti sur 15 min');
  r = await page({ ...base, clicks: every(5, 0, 30), at: 30, hourClicks: 17000 });
  check(/calculé pour 0.9 clics\/s/.test(r.ft) && /reste 850 clics/.test(r.ft), r.ft);

  console.log('Auto, 5 clics/s puis 1 s de pause (le temps d’un achat) : toujours actif');
  r = await page({ ...base, clicks: every(5, 0, 60), at: 61 });
  check(/calculé pour 4.\d clics\/s/.test(r.ft) && r.best === 'doigt', r.ft);

  console.log('Auto, 5 clics/s puis 4 s sans clic : cadence à peine entamée (4.7/s), conseil inchangé');
  r = await page({ ...base, clicks: every(5, 0, 60), at: 63.8 });
  check(/calculé pour 4.7 clics\/s/.test(r.ft) && r.best === 'doigt', r.ft);

  console.log('Auto, 5 clics/s puis 9 s sans clic : passif');
  r = await page({ ...base, clicks: every(5, 0, 60), at: 68.8 });
  check(r.best === 'satellite' && /clics arrêtés depuis 9 s/.test(r.ft), r.ft);

  console.log('Auto, reprise à 3 clics/s pendant 4 s après un arrêt de 20 s : cadence de la nouvelle série');
  r = await page({ ...base, clicks: [...every(5, 0, 30), ...every(3, 50, 54)], at: 54 });
  check(/calculé pour 3 clics\/s/.test(r.ft), r.ft);

  console.log('Auto, 1 clic/s : arrêt détecté après 8 s sans clic, pas avant');
  r = await page({ ...base, clicks: every(1, 0, 20), at: 26.5 });
  const r2 = await page({ ...base, clicks: every(1, 0, 20), at: 27.5 });
  check(/calculé pour/.test(r.ft) && /clics arrêtés/.test(r2.ft), r.ft + ' || ' + r2.ft);

  console.log('Auto, clics arrêtés depuis 3 min : retour au passif');
  r = await page({ ...base, clicks: every(5, 0, 60), at: 240 });
  check(r.best === 'satellite' && /aucun clic récent/.test(r.ft), r.ft);

  console.log('Auto, 18000 clics déjà comptés sur l’heure : conseil passif et alerte');
  r = await page({ ...base, clicks: every(5, 0, 30), at: 30, hourClicks: 18000 });
  check(r.best === 'satellite' && /18000 clics atteints/.test(r.ft) && !/calculé pour/.test(r.ft), r.ft);

  console.log('Frénésie de 40 s comptée (Commission plus tôt)');
  r = await page({ owned: { ...o, hamster: 26, bot: 21, fax: 16, satellite: 3 }, wallet: 2628957, perClick: '5 803 visites', mode: 'passif', chip: '🔥 Frénésie fiscale : production ×3 encore 40 s' });
  check(r.best === 'commission' && /Prochain achat dans 3 s/.test(r.now) && /Frénésie : revenu 76266\/s pendant 40 s/.test(r.ft), r.now + ' | ' + r.ft);

  console.log('Rafale de 13 s en mode Actif 5/s : clics ×10 dans le revenu et les délais');
  r = await page({ ...base, mode: 'actif', cps: 5, wallet: 2e6, chip: '⚡ Rafale de clics : chaque clic ×10 encore 13 s' });
  check(/Rafale : revenu 310674\/s pendant 13 s/.test(r.ft), r.ft);

  console.log('Rafale en mode Passif : signalée sans être comptée');
  r = await page({ ...base, mode: 'passif', chip: '⚡ Rafale de clics : chaque clic ×10 encore 13 s' });
  check(/chaque clic ×10 pendant 13 s, à condition de cliquer/.test(r.ft), r.ft);

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
  check(!r.warn && /dont clics 2.49 M/.test(r.ft) && !r.list.some(l => /Main de l/.test(l)), r.ft + ' | alerte : ' + (r.warn || 'aucune'));

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
    check(fige < 32000 && auto < 500, `taille des favoris : figé ${fige} caractères (plafond 32000), à jour ${auto} (plafond 500)`);
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
