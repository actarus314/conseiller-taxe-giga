// Tests du conseiller sur des états simulés au format exact du jeu (jsdom).
// node test.js      → teste conseiller.js ; node test.js bm → teste le favori généré
const { JSDOM } = require('jsdom');
const utils = require('jsdom/lib/jsdom/living/generated/utils');
const fs = require('fs'), path = require('path'), ROOT = path.join(__dirname, '..', '..');
const SRC = process.argv[2] === 'bm'
  ? decodeURIComponent(fs.readFileSync(path.join(ROOT, 'bookmarklet.txt'), 'utf8').trim().slice(11))
  : fs.readFileSync(path.join(ROOT, 'conseiller.js'), 'utf8');

// formatage du jeu (fonction big() de la page)
const int = n => new Intl.NumberFormat('fr-FR').format(n), nf = d => new Intl.NumberFormat('fr-FR', { minimumFractionDigits: d, maximumFractionDigits: d });
const big = n => n < 1e6 ? int(Math.floor(n)) : n < 1e9 ? nf(2).format(n / 1e6) + ' M' : nf(2).format(n / 1e9) + ' Md';
const B = { doigt: 10, stagiaire: 15, chat: 100, hamster: 600, souris: 500, bot: 6000, fax: 6e4, commission: 6e5, gant: 15e4, satellite: 5e6, trounoir: 7.5e7, tampon: 2e7, datacenter: 1e9 };
const sleep = ms => new Promise(r => setTimeout(r, ms));
let fails = 0;
const check = (ok, msg) => { console.log((ok ? '  ok   ' : '  ÉCHEC ') + msg); if (!ok) fails++; };

async function page({ owned, wallet, mode = 'auto', cps = 5, perClick, chip, clicks = [], hourClicks = 0, at = 0 }) {
  const items = Object.entries(owned).map(([id, n]) => {
    const c = Math.ceil(B[id] * 1.15 ** n);
    return `<button class="item" data-id="${id}" ${wallet < c ? 'disabled' : ''}><span class="ic"><b class="own">×${n}</b><small class="price">💰 ${big(c)}</small></span></button>`;
  }).join('');
  const dom = new JSDOM(`<title>Jeu</title><b id="wallet">${big(wallet)}</b><span id="perClick">${perClick || ''}</span><p id="buffChip" ${chip ? '' : 'hidden'}>${chip || ''}</p>
    <button id="taxBtn">TAXER</button><button id="stickyTax">T</button><div id="shop">${items}</div>`, { runScripts: 'outside-only', url: 'https://taxe-au-giga.fr/' });
  const w = dom.window, d = w.document;
  let now = 1793700000000; w.Date.now = () => now; // horloge simulée
  w.localStorage.setItem('tagAdv-mode', mode); w.localStorage.setItem('tagAdv-cps', String(cps));
  if (hourClicks) w.localStorage.setItem('tagAdv-clics', JSON.stringify({ [Math.floor(now / 60e3) - 5]: hourClicks }));
  w.eval(SRC);
  // clics « de confiance » sur TAXER, à des instants donnés (secondes)
  for (const s of clicks) {
    now = 1793700000000 + s * 1000;
    const e = new w.MouseEvent('click', { bubbles: true }), ei = utils.implForWrapper(e); ei.isTrusted = true;
    utils.implForWrapper(d.getElementById('taxBtn'))._dispatch(ei);
  }
  now = 1793700000000 + at * 1000;
  await sleep(650); // un tour de mise à jour du panneau
  const r = {
    now: d.querySelector('#tagAdv .now').textContent, list: [...d.querySelectorAll('#tagAdv li')].map(l => l.textContent),
    ft: d.querySelector('#tagAdv .ft').textContent, warn: d.querySelector('#tagAdv .warn').hidden ? '' : d.querySelector('#tagAdv .warn').textContent,
    best: d.querySelector('.tagAdvBest')?.dataset.id, adv: d.querySelector('.tagAdvBest')?.dataset.adv,
    text: d.querySelector('#tagAdv').textContent, titles: d.querySelectorAll('#tagAdv [title]').length, docTitle: d.title,
  };
  w.eval('window.__tagAdv.stop()'); r.stopped = !d.querySelector('#tagAdv') && !d.querySelector('.tagAdvBest'); w.close();
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
  check(r.stopped, 'arrêt propre');

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

  console.log('Auto, clics arrêtés depuis 3 min : retour au passif');
  r = await page({ ...base, clicks: every(5, 0, 60), at: 240 });
  check(r.best === 'satellite' && /aucun clic récent/.test(r.ft), r.ft);

  console.log('Auto, 18000 clics déjà comptés sur l’heure : conseil passif et alerte');
  r = await page({ ...base, clicks: every(5, 0, 30), at: 30, hourClicks: 18000 });
  check(r.best === 'satellite' && /18000 clics atteints/.test(r.ft) && !/calculé pour/.test(r.ft), r.ft);

  console.log('Frénésie de 40 s comptée (Commission plus tôt)');
  r = await page({ owned: { ...o, hamster: 26, bot: 21, fax: 16, satellite: 3 }, wallet: 2628957, perClick: '5 803 visites', mode: 'passif', chip: '🔥 Frénésie fiscale : production ×3 encore 40 s' });
  check(r.best === 'commission' && /frénésie 40 s/.test(r.ft), r.now + ' | ' + r.ft);

  console.log('Puissance de clic affichée différente du modèle : alerte');
  r = await page({ ...base, perClick: '9 999 visites' });
  check(/puissance de clic/.test(r.warn), r.warn);

  console.log('Forme : nombres au point décimal sans séparateur, aucune info-bulle native, aucun « vous »');
  r = await page({ ...base, clicks: every(5, 0, 60), at: 60 });
  const t = r.text.replace(/\d{2}:\d{2}/g, '');
  check(!/\d \d{3}\b/.test(t) && !/\d,\d/.test(t), 'aucun « 1 234 » ni « 6,61 » dans le panneau');
  check(r.titles === 0, 'aucun attribut title');
  check(!/\b(vous|tu|achetez)\b/i.test(r.text), 'formulations impersonnelles');

  console.log(fails ? `\n${fails} échec(s)` : '\nTout est passé');
  process.exit(fails ? 1 : 0);
})();
