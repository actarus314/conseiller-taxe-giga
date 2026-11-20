#!/usr/bin/env python3
"""Tests de la veille (dev/veille/veille.py), sur des pages fabriquées : aucune copie de la page du jeu dans le dépôt.

Page fabriquée : le numéro de build, le tableau SHOP écrit d'après le barème du conseiller (tableau P de conseiller.js),
chaque passage de règle tel qu'il est noté dans dev/veille/reference.json, et un modèle de la détection d'autoclic
(AUTOCLIC, écrit pour ces tests à la forme de la page du jeu, avec les pièges de lecture connus). Les tests comparent à
une référence tirée de cette page fabriquée, pas à dev/veille/reference.json.
Usage : python3 dev/veille/test_veille.py
"""
import contextlib, datetime, io, json, os, pathlib, re, subprocess, sys, tempfile

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import autoclic, fichiers, principale, veille  # noqa: E402

REF = json.loads((ICI / 'reference.json').read_text(encoding='utf-8'))
echecs = 0


# Modèle de la détection d'autoclic (forme de la page du jeu, build 2026-11-18f) : sept zones, dont une fléchée ;
# synchro à chaîne if…else ; gardes isTrusted et oneShot ; fenêtres ; diapositive ; textes ; et les pièges du lecteur
# (expression régulière qui contient un guillemet, gabarit à ${…}, commentaire à mot-clé, plusieurs blocs <script>).
AUTOCLIC = """<button id="taxBtn">TAXER</button>
<a href="/regles#autoclick">🤖 Autoclick : ce qui est interdit</a>
<aside class="news" id="news" role="dialog" hidden>
  <div class="nw-slide" data-slide="0"><b>Hier</b><p>+0 €</p></div>
  <div class="nw-slide" data-slide="1" hidden><b>🤖 Autoclick : nouvelles règles</b>
    <p class="nw-line">Plus de 175 000 clics en 8 h : avertissement.</p><p>Faites des pauses <a href="/regles">Les règles</a></p></div>
</aside>
<div class="bn-ov" id="bnOv" role="dialog" aria-modal="true" hidden><h2>Bravo</h2></div>
<div class="bn-ov" id="acOv" role="dialog" aria-modal="true" hidden><div class="bn-card"><h2>Comportement anormal détecté</h2>
  <p>Vos clics ne ressemblent pas à ceux d’un humain.</p><div class="ac-ch"><button id="acStop">J’arrête</button></div></div></div>
<div class="bn-ov" id="durOv" role="dialog" aria-modal="true" hidden><div><h2 id="durTitle">Avertissement</h2><p id="durTxt"></p></div></div>
<div class="bn-ov" id="acWarnOv" role="dialog" aria-modal="true" hidden><div><h2>Attention</h2><p>Rien n’est bloqué pour l’instant.</p></div></div>
<dialog id="txDlg"><p>Facture</p></dialog>
<script>const esc = t => String(t).replace(/[&<>"]/g, c => '&#' + c.charCodeAt(0) + ';'); // « autoclic » en commentaire
  const note = 'Méthode de clic (avertissement autoclick) : ';
</script>
<script>
  async function sync(d) {
    if (d.ok) {
      if (d.acNotice) acNotice(d.acNotice, d.me && d.me.id);
      if (d.acDur) durWarn(d.acDur);
      if (d.acWarn) { acwInfo = d.acWarn; acWarnShow(); }
      if (d.autoclick && !(d.acNotice && d.acNotice.ask)) showBanner('🤖 Bien vu l’autoclick', 'Vos clics ne comptent plus.');
      else if (rr > 30) { say(`🥵 au-delà de ${n} clics par minute`); }
    }
  }
  function acNotice(n, pid) { acAsk = !!n.ask && !acChoice; if (acAsk) acShow(); }
  function acShow() { const ov = $('acOv'); if (!acAsk || !ov.hidden) return; $('acName').textContent = ` « ${taxerName(pid)} »`; ov.hidden = false; }
  const acPick = c => { acChoice = c; say(c === 'stop' ? '✋ Merci !' : '🤖 Hors classement.'); };
  function durWarn(x) {
    const n = +x.n || 1, max = +x.max || 3;
    if (x.vol) {
      $('durTitle').textContent = x.bot ? 'Classement Autoclickers : trop de clics en 8 h' : 'Avertissement : trop de clics en 8 h';
    } else if (x.h24) {
      $('durTitle').textContent = 'Classement Autoclickers : clics 24 h sur 24';
    } else {
      $('durTitle').textContent = `Avertissement ${n}/${max} : plus de 18 h de clics`;
    }
  }
  function acWarnShow() { const ov = $('acWarnOv'); if (!acwInfo || !ov.hidden) return; ov.hidden = false; }
  function acWarnClose(t) { acwInfo = null; $('acWarnOv').hidden = true; if (t) say(t); }
  let k = c++ / 2; if (d.acTest) go(); k = j / 3;
  say(`clics : ${d.acGab}`);
  document.body.insertAdjacentHTML('beforeend', '<div class="bn-ov" id="pzOv" role="dialog"></div>');
  function oneShot(el, tell) { el.addEventListener('keydown', e => { if (e.repeat) { e.preventDefault(); return; } }); }
  oneShot(btn, true);
  btn.addEventListener('click', e => {
    if (!e.isTrusted || bossLock) return;
    taxHit(e.timeStamp);
  });
  const ratio = clicks / 2, tip = 'Un humain se fatigue, un autoclicker non.';
</script>
"""


# Modèle du reste de la page principale (forme du build 2026-11-19d) : régularité et origine de ses horodatages, les deux
# corps envoyés à /api/sync, règle des pseudos, contrat du boss, restes de la détection d'autoclic (clé, minuteries,
# envoi de la méthode, fenêtre créée par le script), routes du collecteur, globe ; puis le bandeau et le chargeur du
# boss, chacun dans son bloc <script>.
PRINCIPALE = """<script>
  const clickTimes = []; let lastClickAt = 0;
  function cadence() {
    const t = clickTimes.splice(0); if (t.length < 30) return undefined;
    return { n: t.length, cv: 0.5 };
  }
  function taxHit(ts) { realPending++; clickTimes.push(ts); if (clickTimes.length > 1500) clickTimes.splice(0, 500); return 1; }
  tax.addEventListener('click', e => { if (!e.isTrusted) return; const n = taxHit(performance.now()); });
  const AC_KEY = 'taxe-giga-ac-choice';
  let acChoice = ''; try { acChoice = localStorage.getItem(AC_KEY) || ''; } catch (e) {}
  async function flush() {
    let flags = {}; try { flags = cardFlags(); } catch (e) {}
    const body = { code: myCode, clicks: rr, cad: cadence(), acChoice: acChoice || undefined, tb: 1, ...flags };
    let legacy = false;
    if (!body.code) { if (legacy && myCount > 0) body.legacy = { myCount, wallet }; }
    const r = await api('/api/sync', { method: 'POST', headers: { 'content-type': 'text/plain' }, body: JSON.stringify(body) });
    const d = r.ok ? await r.json() : { ok: false };
  }
  function beacon() {
    const body = { code, clicks: rr, gold: goldClicked || undefined };
    try { ok = navigator.sendBeacon(API + '/api/sync', new Blob([JSON.stringify(body)], { type: 'text/plain' })); } catch (e) {}
  }
  function cardFlags() { const f = {}; if (Date.now() - rankAsked > 600000) f.rk = 1; return f; }
  const NOUNS = ['Hamster', 'Stagiaire', 'Gobe-Octet'];
  const ADJS = ['fiscal', 'sournois', 'infatigable'];
  const taxerName = id => { const h = parseInt(id.slice(0, 6), 16) || 0; return `${NOUNS[h % NOUNS.length]} ${ADJS[(h >> 4) % ADJS.length]} #${h % 1000}`; };
  setInterval(acShow, 3000);
  setInterval(acWarnShow, 3000);
  try { const r = await fetch('/api/feedback.php', { method: 'POST', body: JSON.stringify({ kind: 'bug', sec: 'autoclick-avert', msg: v }) }); } catch (err) {}
  function bubble() { bub = mk('div', 'fb-bub'); bub.setAttribute('role', 'dialog'); }
  async function loadBoard() {
    const r = await api(`/api/leaderboard?v=3&r=${want}${me ? '&me=' + me.id : ''}`, { cache: 'no-store' });
    try { const m = await api(`/api/taxer?id=${me.id}`, { cache: 'no-store' }); } catch (e) {}
  }
  const mondeMod = () => import('/monde/monde.js?v=29');
  function mondePlay(g) { mondeMod().then(m => { mondeCtl = m.play({ code: myCode, envoisUrl: '/monde/envois.php', regionsUrl: '/monde/regions.php', g }); }); }
  window.TaxeBoss = { pseudo: id => taxerName(id), myId: () => me && me.id, now: () => Date.now() + serverOffset, lock(on) { setLock(on); } };
</script>
<div id="bossBar" hidden></div><script>/* Dépité 4000 tous les soirs à 18 h */
(() => {
  const el = document.getElementById('bossBar'), $ = id => document.getElementById(id);
  const slot = () => { let o = parisAt(18, 0, 0); if (now() >= o + 280000) o = parisAt(18, 0, 1); return o; };
  $('bbGo').onclick = () => { if (window.bossReopen) { window.bossReopen(); } else location.reload(); };
  function paint() { const OPEN = slot(), F = OPEN + 120000; el.hidden = Date.now() < F; }
  paint(); setInterval(paint, 1000);
})();
</script>
<script>/* Boss : rien n'est chargé hors de l'événement */
(() => {
  const F = at(18, 2), A = F - 32 * 60000, B = F + 2 * 3600000; if (Date.now() < A || Date.now() > B) return;
  const go = () => { window.BOSS_SERVER = { hit: '/boss/hit.php', state: '/boss/state.json' }; for (const f of ['boss-event-net.js', 'boss-site.js']) { const s = document.createElement('script'); s.src = '/boss/' + f + '?v=1794501311'; document.body.appendChild(s); } };
  setTimeout(go, 1500);
})();
</script>
"""


def page(build="2026-11-04n", shop=None, regles=None, autoclic=AUTOCLIC, principale=PRINCIPALE):
    shop = shop if shop is not None else veille.shop_conseiller()
    lignes = [f"const BUILD = '{build}';", 'const SHOP = [']
    for k, u in shop.items():
        extra = ''.join(f", {c}: {u[c]:g}" for c in ('rate', 'click', 'pct', 'max') if u[c])
        lignes.append(f"  {{ id: '{k}', name: '', base: {u['base']:g}, unlock: 1{extra} }},")
    lignes.append('];')
    for texte in (regles or REF['regles']).values():
        lignes += (texte or '').split(' | ')
    return '\n'.join(lignes) + '\n' + autoclic + principale


TMP = pathlib.Path(tempfile.mkdtemp())
REF_TEST = TMP / 'reference.json'


def lancer(html, *args, sortie=None):
    """Veille sur une page fabriquée, comparée à la référence des tests. sortie : fichier $GITHUB_OUTPUT."""
    f = TMP / 'page.html'
    f.write_text(html, encoding='utf-8')
    env = dict(os.environ)
    env.pop('GITHUB_OUTPUT', None)
    if sortie:
        env['GITHUB_OUTPUT'] = str(sortie)
    r = subprocess.run([sys.executable, str(ICI / 'veille.py'), '--fichier', str(f), '--reference', str(REF_TEST), *args],
                       capture_output=True, text=True, env=env)
    return r.returncode, r.stdout


def mute(avant, apres, html=None):
    html = html or page()
    assert avant in html, avant
    return html.replace(avant, apres, 1)


def verifie(nom, ok, detail=''):
    global echecs
    print(('  ok   ' if ok else '  ÉCHEC ') + nom + (f' ({detail})' if detail and not ok else ''))
    echecs += not ok


code, out = lancer(page(), '--maj-reference')
verifie('référence des tests écrite depuis la page fabriquée', code == 0 and REF_TEST.exists(), out[-300:])
code, out = lancer(page())
verifie('page conforme : code 0', code == 0 and 'Conforme' in out, out[-300:])

regles = dict(REF['regles']); regles['limites de clics'] = regles['limites de clics'].replace('1 030', '2 000')
code, out = lancer(page(regles=regles))
verifie('règle modifiée (limite de clics) : écart signalé', code == 1 and 'limites de clics' in out, out[-200:])

shop = veille.shop_conseiller(); shop['doigt'] = dict(shop['doigt'], base=12)
code, out = lancer(page(shop=shop))
verifie('barème modifié (prix de base) : écart signalé', code == 1 and 'doigt' in out and 'base 10 → 12' in out, out[-200:])

html = page().replace("rate: 250000", "rate: 2.5e+5")
code, out = lancer(html)
verifie('nombre écrit 2.5e+5 dans le tableau du jeu : lu, page conforme', code == 0, out[-200:])

code, out = lancer(page(build="@quelquun [ici](https://exemple.invalid) <img src=x>"))
verifie('numéro de build piégé : page refusée (forme inconnue), rien de son texte dans le rapport', code == 3 and '@quelquun' not in out and 'exemple.invalid' not in out, out[-200:])

code, out = lancer('<html><title>Vérification</title>Un instant…</html>')
verifie('page sans le code du jeu (vérification anti-robot) : inaccessible', code == 2 and 'inaccessible' in out, out[-200:])


# ---------- détection d'autoclic ----------
CAS = [
    ('seuil changé dans durWarn', mute("'Avertissement : trop de clics en 8 h'", "'Avertissement : trop de clics en 6 h'"), 'durWarn'),
    ('branche de durWarn changée', mute('} else if (x.h24) {', '} else if (x.h24 || x.h20) {'), 'durWarn'),
    ('zone fléchée (acPick) changée', mute("acChoice = c;", "acChoice = c; flush();"), 'acPick'),
    ('nouveau champ ac… dans la synchro', mute("if (d.acDur) durWarn(d.acDur);", "if (d.acDur) durWarn(d.acDur);\n      if (d.acPause) durWarn(d.acPause);"), 'acPause'),
    ('suite else de la synchro changée', mute("else if (rr > 30)", "else if (rr > 40)"), 'Instructions'),
    ('garde isTrusted changée', mute("if (!e.isTrusted || bossLock) return;", "if (!e.isTrusted || bossLock || e.detail === 0) return;"), 'Instructions'),
    ('appel de oneShot retiré', mute("oneShot(btn, true);", ""), 'Instructions'),
    ('fenêtre neuve', mute('<dialog id="txDlg">', '<div class="bn-ov" id="pauseOv" hidden></div><dialog id="txDlg">'), 'pauseOv'),
    ('texte de fenêtre changé', mute('Rien n’est bloqué pour l’instant.', 'Vos clics sont bloqués.'), 'acWarnOv'),
    ('diapositive changée', mute('Plus de 175 000 clics en 8 h', 'Plus de 150 000 clics en 8 h'), 'Diapositives'),
    ('texte HTML balayé changé', mute('🤖 Autoclick : ce qui est interdit', '🤖 Autoclick : les limites'), 'Textes'),
    ('chaîne JS après une expression régulière à guillemet (lecteur pas déraillé)', mute("'Méthode de clic (avertissement autoclick) : '", "'Méthode de clic (signalement autoclick) : '"), 'Textes'),
    ('chaîne JS en fin de script changée', mute("'Un humain se fatigue, un autoclicker non.'", "'Un humain se fatigue, un autoclicker jamais.'"), 'Textes'),
    ('fonction renommée : zone introuvable', mute('function durWarn(x) {', 'function durAlert(x) {'), 'introuvable'),
    ('lecteur perdu : écart « illisible »', mute("const ov = $('acWarnOv');", "const ov = $('acWarnOv);"), 'illisible'),
]
for nom, html, attendu in CAS:
    code, out = lancer(html)
    verifie(nom + ' : écart signalé', code == 1 and attendu in out, out[-400:])

CAS2 = [
    ('acNotice changée', mute('acAsk = !!n.ask && !acChoice;', 'acAsk = !!n.ask;'), 'acNotice'),
    ('acShow changée', mute("if (!acAsk || !ov.hidden) return;", "if (!acAsk || !ov.hidden || busy) return;"), 'acShow'),
    ('acWarnShow changée', mute("if (!acwInfo || !ov.hidden) return; ov.hidden = false;", "if (!acwInfo) return; ov.hidden = false;"), 'acWarnShow'),
    ('acWarnClose changée', mute('acwInfo = null;', 'acwInfo = 0;'), 'acWarnClose'),
    ('signature de durWarn changée', mute('function durWarn(x) {', 'function durWarn(x, lim = 5) {'), 'durWarn'),
    ('texte de la fenêtre durOv changé', mute('<h2 id="durTitle">Avertissement</h2>', '<h2 id="durTitle">Alerte</h2>'), 'durOv'),
    ('instruction après « c++ / 2 » (division, pas expression régulière)', mute('if (d.acTest) go();', 'if (d.acTest) stop();'), 'Instructions'),
    ('champ lu dans un gabarit', mute('${d.acGab}', '${d.acGab2}'), 'acGab2'),
    ('fenêtre injectée par le script', mute('id="pzOv"', 'id="pzOv2"'), 'pzOv2'),
    ('fenêtre injectée, guillemets échappés', mute("const ratio = clicks / 2", "el.innerHTML = \"<div class=\\\"bn-ov\\\" id=\\\"esc1\\\"></div>\";\n  const ratio = clicks / 2"), 'esc1'),
    ('fenêtre injectée, apostrophes et role=dialog', mute("const ratio = clicks / 2", "el.innerHTML = \"<div role='dialog' id='apo1'></div>\";\n  const ratio = clicks / 2"), 'apo1'),
    ('texte à « triche » (hors « triche du compteur ») changé', mute('<dialog id="txDlg"><p>Facture</p>', '<dialog id="txDlg"><p>Facture</p><p>Toute triche est sanctionnée.</p>'), 'Textes'),
    ('règle annoncée à côté d\'un passage déjà suivi', mute('aucun autre classement', 'aucun autre classement. Un autoclicker récidiviste est banni'), 'Textes'),
]
for nom, html, attendu in CAS2:
    code, out = lancer(html)
    verifie(nom + ' : écart signalé', code == 1 and attendu in out, out[-400:])

# ---------- reste de la page principale (lot V2) et restes de la détection d'autoclic ----------
CAS3 = [
    # 1. régularité envoyée au serveur et origine de ses horodatages
    ('cadence() changée', mute('if (t.length < 30) return undefined;', 'if (t.length < 20) return undefined;'), 'cadence()'),
    ('horodatage gardé par taxHit changé', mute('clickTimes.push(ts);', 'clickTimes.push(Date.now());'), 'taxHit()'),
    ('origine des horodatages (bouton) changée', mute('taxHit(e.timeStamp);', 'taxHit(performance.now());'), 'origine des horodatages'),
    ('origine des horodatages (version mini) changée', mute('const n = taxHit(performance.now());', 'const n = taxHit(e.timeStamp);'), 'origine des horodatages'),
    ('second site d\'appel de taxHit au texte identique', mute('const AC_KEY =', "sticky.addEventListener('click', e => { if (!e.isTrusted || bossLock) return;\n    taxHit(e.timeStamp);\n  });\n  const AC_KEY ="), 'origine des horodatages de clickTimes** :\najouté :\n~~~~\ntaxHit(e.timeStamp);'),
    ('clickTimes rempli ailleurs', mute('const AC_KEY =', 'document.onclick = () => clickTimes.push(Date.now());\n  const AC_KEY ='), 'origine des horodatages'),
    # 2. ce que la page envoie à /api/sync, chaque corps séparément
    ('champ ajouté au corps de la synchro', mute('tb: 1, ...flags };', 'tb: 1, hz: 1, ...flags };'), 'synchro, jusqu'),
    ('champ retiré du corps de la synchro', mute('cad: cadence(), ', ''), 'synchro, jusqu'),
    ('body.legacy changé', mute('body.legacy = { myCount, wallet };', 'body.legacy = { myCount, wallet, owned };'), 'synchro, jusqu'),
    ('champ ajouté au corps de fermeture', mute('const body = { code, clicks: rr, gold', 'const body = { code, clicks: rr, cad: cadence(), gold'), 'envoi de fermeture'),
    ('cardFlags() changée', mute('f.rk = 1;', 'f.rk = 1; f.vu = 1;'), 'cardFlags()'),
    ('adresse de la synchro changée (hors de l\'objet des options)', mute("api('/api/sync', { method", "api('/api/sync2', { method"), 'synchro, jusqu'),
    ('source d\'un champ du corps changée (flags)', mute('let flags = {};', 'let flags = { zz: 1 };'), 'synchro, jusqu'),
    ('plafond des clics envoyés changé', mute('clicks: rr, cad', 'clicks: Math.min(rr, 30000), cad'), 'synchro, jusqu'),
    ('second envoi dans beacon', mute("{ type: 'text/plain' })); } catch (e) {}", "{ type: 'text/plain' })); navigator.sendBeacon(API + '/api/sync', JSON.stringify(autre)); } catch (e) {}"), 'envoi de fermeture'),
    ('second envoi dans flush, après le premier', mute("const d = r.ok ? await r.json() : { ok: false };", "const d = r.ok ? await r.json() : { ok: false };\n    navigator.sendBeacon(API + '/api/sync', JSON.stringify(autre));"), 'autres envois à /api/sync'),
    ('envoi vers une route voisine (/api/sync2)', mute('function cardFlags()', "api('/api/sync2', { body: x });\n  function cardFlags()"), 'autres envois à /api/sync'),
    ('troisième envoi à /api/sync', mute('function cardFlags()', "setInterval(() => api('/api/sync', { method: 'POST', body: '{}' }), 6e4);\n  function cardFlags()"), 'autres envois'),
    # 3. règle des pseudos
    ('taxerName() changée', mute('#${h % 1000}', '#${h % 10000}'), 'taxerName()'),
    ('table NOUNS changée', mute("'Stagiaire', ", "'Stagiaire', 'Greffier', "), 'tables NOUNS et ADJS'),
    # 4. boss : chargeur, version, ancre, bandeau, contrat
    ('fenêtre horaire du chargeur changée', mute('A = F - 32 * 60000', 'A = F - 40 * 60000'), 'chargeur du module du boss** modifié'),
    ('adresse du boss changée', mute("state: '/boss/state.json'", "state: '/boss/etat.json'"), 'chargeur du module du boss** modifié'),
    ('version du module du boss changée', mute('?v=1794501311', '?v=1794600000'), 'version du module du boss** : `1794501311` → `1794600000` (lue comme une date'),
    ('ancre du chargeur disparue', mute("'boss-event-net.js', ", "'boss-net.js', "), 'chargeur du module du boss** introuvable'),
    ('chargeur passé dans le bloc du jeu : ancre perdue', mute("<script>/* Boss : rien n'est chargé", "<script>const SHOP = [];\n/* Boss : rien n'est chargé"), 'chargeur du module du boss** introuvable'),
    ('calendrier du bandeau changé', mute('o + 280000', 'o + 300000'), 'bandeau du Dépité** modifié'),
    ('ancre du bandeau disparue', mute("getElementById('bossBar')", "getElementById('bossBand')"), 'bandeau du Dépité** introuvable'),
    ('contrat window.TaxeBoss changé', mute(' now: () => Date.now() + serverOffset,', ''), 'contrat window.TaxeBoss'),
    ('membre ajouté au contrat après coup', mute('</script>\n<div id="bossBar"', '  window.TaxeBoss.zork = () => 1;\n</script>\n<div id="bossBar"'), 'contrat window.TaxeBoss'),
    ('contrat complété par Object.assign', mute('</script>\n<div id="bossBar"', '  Object.assign(window.TaxeBoss, { zork: 1 });\n</script>\n<div id="bossBar"'), 'contrat window.TaxeBoss'),
    # 5. restes de la détection d'autoclic
    ('clé AC_KEY changée', mute("'taxe-giga-ac-choice'", "'taxe-giga-ac-choix'"), 'Instructions'),
    ('minuterie de acShow changée', mute('setInterval(acShow, 3000);', 'setInterval(acShow, 5000);'), 'Instructions'),
    ('minuterie de acWarnShow retirée', mute('setInterval(acWarnShow, 3000);', ''), 'Instructions'),
    ('envoi de la méthode de clic changé', mute("sec: 'autoclick-avert'", "sec: 'autoclick-methode'"), 'Instructions'),
    ('fenêtre créée par le script changée', mute("mk('div', 'fb-bub')", "mk('div', 'fb-pop')"), 'div.fb-pop (script)'),
    ('fenêtre <dialog> créée par le script', mute('function bubble() {', "function bubble() { const w = document.createElement('dialog');"), 'dialog (script)'),
    ('champ lu par crochets', mute('function cardFlags()', "if (d['acPause']) stop();\n  function cardFlags()"), 'Champs de détection lus :\najouté :\n~~~~\nacPause'),
    ('instruction qui lit un champ par crochets', mute('function cardFlags()', "if (d['acPause']) stop();\n  function cardFlags()"), "if(d['acPause'])stop();"),
    ('champ lu par déstructuration', mute('function cardFlags()', 'const { acHalt, ok } = d;\n  function cardFlags()'), 'Champs de détection lus :\najouté :\n~~~~\nacHalt'),
    ('champ déstructuré à clé entre guillemets', mute('function cardFlags()', "const { 'acStop': s } = d;\n  function cardFlags()"), 'Champs de détection lus :\najouté :\n~~~~\nacStop'),
    ('champ déstructuré après un commentaire', mute('function cardFlags()', 'const { ok,\n    // champ\n    acNote /* fin */ } = d;\n  function cardFlags()'), 'Champs de détection lus :\najouté :\n~~~~\nacNote'),
    ('instruction qui déstructure un champ', mute('function cardFlags()', 'const { acHalt, ok } = d;\n  function cardFlags()'), 'const{acHalt,ok}=d;'),
    # 6. routes que lit le collecteur
    ('version du classement changée', mute('/api/leaderboard?v=3&', '/api/leaderboard?v=4&'), 'routes lues par le collecteur'),
    ('paramètre de la fiche changé', mute('/api/taxer?id=', '/api/taxer?pid='), 'routes lues par le collecteur'),
    # 7. globe
    ('version du module du globe changée', mute('monde.js?v=29', 'monde.js?v=30'), 'version du module du globe** : `29` → `30`'),
    ('adresse du globe changée', mute("envoisUrl: '/monde/envois.php'", "envoisUrl: '/monde/envoi.php'"), 'chargeur et appel du module du globe'),
    ('appel du globe renommé (hors de l\'objet passé)', mute('m.play({', 'm.run({'), 'chargeur et appel du module du globe'),
]
for nom, html, attendu in CAS3:
    code, out = lancer(html)
    verifie(nom + ' : écart signalé', code == 1 and attendu in out, out[-400:])

code, out = lancer(mute('#${h % 1000}', '#${h % 10000}'))
verifie("règle des pseudos : l'issue dit « vérifier ce qui la recopie »", 'Règle des pseudos changée : vérifier ce qui la recopie.' in out, out[-400:])
o7, o8 = TMP / 'o7', TMP / 'o8'
lancer(mute('monde.js?v=29', 'monde.js?v=30'), sortie=o7)
verifie('sujet « page »', 'sujet=page' in o7.read_text())
lancer(mute('monde.js?v=29', 'monde.js?v=30', page(shop=shop)), sortie=o8)
verifie('sujet « mixte » (barème et page)', 'sujet=mixte' in o8.read_text())
code, out = lancer(mute('function cardFlags()', 'const { x: acLocal } = d;\n  function cardFlags()'), '--maj-reference')
verifie('déstructuration vers un nom local « ac… » : pas un champ lu', code == 0 and 'acLocal' not in json.loads(REF_TEST.read_text(encoding='utf-8'))['autoclic']['champs'], out[-300:])
code, out = lancer(page(), '--maj-reference')  # référence des tests rétablie
code, out = lancer(mute('if (t.length < 30) return', 'if (t.length  <  30)   return'))
verifie('reformatage dans cadence() : conforme', code == 0, out[-300:])
code, out = lancer(mute('const mondeMod =', "// fiche : /api/taxer?id=, globe : /monde/, envoi : /api/sync ; 'clickTimes'\n  const mondeMod ="))
verifie('commentaire qui cite les routes suivies : conforme', code == 0, out[-300:])
code, out = lancer(mute('const mondeMod =', "const aide = 'clickTimes, taxHit(x), body et legacy : sans effet';\n  const mondeMod ="))
verifie('chaîne qui cite les noms suivis dans le code : conforme', code == 0, out[-300:])
code, out = lancer(mute("'boss-event-net.js', ", "'boss-net.js', "), '--maj-reference')
verifie("recalage refusé si l'ancre du chargeur manque", code == 3 and 'chargeur du module du boss' in out, out[-300:])
ref = json.loads(REF_TEST.read_text(encoding='utf-8')); ref.pop('page')
REF_SANS2 = TMP / 'ref-sans-page.json'; REF_SANS2.write_text(json.dumps(ref), encoding='utf-8')
f = TMP / 'page.html'; f.write_text(page(), encoding='utf-8')
r = subprocess.run([sys.executable, str(ICI / 'veille.py'), '--fichier', str(f), '--reference', str(REF_SANS2)], capture_output=True, text=True)
verifie('référence sans suivi du reste de la page : écart', r.returncode == 1 and 'Référence sans suivi du reste de la page' in r.stdout, r.stdout[-300:])

# aucune requête de plus : le téléchargement compté sur un passage complet (urlopen remplacé, page fabriquée)
appels = []


class Reponse:
    headers = {}

    def __init__(self, data):
        self.data = data

    def read(self, n):
        return self.data[:n]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def urlopen_compte(req, timeout=None):
    appels.append(req.full_url)
    return Reponse(page().encode())


argv, vrai = sys.argv, veille.urllib.request.urlopen
# hors de la plage du jour des fichiers à part (sinon le passage les lit aussi : voir plus bas)
sys.argv, veille.urllib.request.urlopen = ['veille.py', '--reference', str(REF_TEST), '--maintenant', '2026-11-20T12:00:00Z'], urlopen_compte
try:
    with contextlib.redirect_stdout(io.StringIO()):
        code = veille.main()
finally:
    sys.argv, veille.urllib.request.urlopen = argv, vrai
verifie('une seule requête au site par passage (conforme)', code == 0 and appels == [veille.URL], appels)

pg = REF.get('page') or {}
verifie('reference.json : section page complète (passages ancrés, inventaires attendus)',
        bool(pg) and set(pg) == set(principale.PASSAGES) and not principale.manques(pg))
# codes de compte « GOBE-XXXX-… » : jamais dans le dépôt ; les pseudos « Gobe-Octet … » n'en sont pas
CODE_COMPTE = re.compile(r'\bGOBE(?:[-\s]?[A-Z0-9]{4}){4}\b', re.I)
verifie('contrôle des codes de compte : trouve un code, pas un pseudo',
        CODE_COMPTE.search('GOBE' + '-ABCD-1234-EFGH-5678') and CODE_COMPTE.search('gobe' + '-abcd-1234-efgh-5678')
        and not CODE_COMPTE.search('Gobe-Octet sournois #732') and not CODE_COMPTE.search("'Gobe-Octet','Contrôleur'"))
RACINE = ICI.parents[1]
du_depot = [x for x in RACINE.rglob('*') if x.is_file() and not {'.git', 'node_modules'} & set(x.relative_to(RACINE).parts)]
verifie('aucun code de compte dans le dépôt (pseudos permis ; tirets, espaces ou rien entre les groupes)',
        CODE_COMPTE.search('GOBE' + ' ABCD 1234 EFGH 5678') and CODE_COMPTE.search('gobe' + 'abcd1234efgh5678')
        and not any(CODE_COMPTE.search(x.read_text(encoding='utf-8', errors='ignore')) for x in du_depot), len(du_depot))

# lecture des motifs de déstructuration sur le découpage du lecteur (commentaires et chaînes délimités) :
# (code, champs attendus, instruction enregistrée attendue — texte normalisé, ou None)
DESTRUCTURES = [
    ("const { ok,\n // champ\n acX } = d;", ['acX'], 'const{ok,acX}=d;'),
    ('const { /* c */ acX } = d;', ['acX'], 'const{acX}=d;'),
    ('const { ok, acX /* x */ } = d;', ['acX'], 'const{ok,acX}=d;'),
    ('const { ok, acX // x\n } = d;', ['acX'], 'const{ok,acX}=d;'),
    ("const { 'a//b': s, acZ } = d;", ['acZ'], "const{'a//b':s,acZ}=d;"),
    ("const { ok = '//', acV } = d;", ['acV'], "const{ok='//',acV}=d;"),
    ("const { 'a/*b': s, acW, 'c*/d': t } = d;", ['acW'], "const{'a/*b':s,acW,'c*/d':t}=d;"),
    ("const { u = 'https://x', acA } = d;", ['acA'], "const{u='https://x',acA}=d;"),
    ('const { ok, // }\n acB } = d;', ['acB'], 'const{ok,acB}=d;'),
    ('const { acA, /* } */ acB } = d;', ['acA', 'acB'], 'const{acA,acB}=d;'),
    ("const { 'acQ': s, \"acR\" : r } = d;", ['acQ', 'acR'], "const{'acQ':s,\"acR\":r}=d;"),
    ("const { 'a\\x63S': s } = d;", ['acS'], "const{'acS':s}=d;"),
    ('const { acK /* c */ : l } = d;', ['acK'], 'const{acK:l}=d;'),
    ('const { ok = 4 / 2 / 1, acDV } = d;', ['acDV'], 'const{ok=4/2/1,acDV}=d;'),
    ('let {acX}=d;', ['acX'], 'let{acX}=d;'),
    ('const /* c */ { acX } = d;', ['acX'], 'const{acX}=d;'),
    ('const { a } = x, { acB } = y;', ['acB'], 'const{a}=x,{acB}=y;'),
    ('let a = 1, { acB } = y;', ['acB'], 'let a=1,{acB}=y;'),
    ('const { acX } = d, { acY } = e;', ['acX', 'acY'], 'const{acX}=d,{acY}=e;'),
    ('const { a: { acN } } = d;', ['acN'], 'const{a:{acN}}=d;'),
    ('if (x) { y(); } ({ acP } = d);', ['acP'], '{acP}=d'),
    ('x = `${(() => { const { acG } = d; return 1; })()}`;', ['acG'], 'const{acG}=d;'),
    ('const { ...acL } = d;', [], None),
    ('const { x: acY } = d;', [], None),
    ("const { u = 'a, acX', ok } = d;", [], None),
    ("const { ok = ', acS, ' } = d;", [], None),
    ('const { ok = `${a}, acX`, acT } = d;', ['acT'], 'const{ok=`${a}, acX`,acT}=d;'),
    ('for (const { acF } of liste) f(acF);', [], None),
]
for code, attendu, instr in DESTRUCTURES:
    r = autoclic.releve(f'<script>{code}</script>')
    verifie(f'déstructuration lue sur le découpage : {code!r} → {attendu}',
            r['champs'] == attendu and r['instructions'] == ([instr] if instr else []), (r['champs'], r['instructions']))

long_avant = 'x = 1;' * 80 + "say('autoclic 36e5');"
code, out = lancer(mute("say(`clics : ${d.acGab}`);", "say(`clics : ${d.acGab}`); if (d.acLong) { " + long_avant + " }"), '--maj-reference')
code, out = lancer(mute("say(`clics : ${d.acGab}`);", "say(`clics : ${d.acGab}`); if (d.acLong) { " + long_avant.replace('36e5', '72e5') + " }"))
verifie('changement loin dans une longue instruction : visible dans le rapport', code == 1 and '72e5' in out and '36e5' in out, out[-500:])
long_txt = 'Règle : ' + 'des pauses, ' * 70 + 'sinon 30 jours.'
code, out = lancer(mute("say(`clics : ${d.acGab}`);", "say(`clics : ${d.acGab}`); say('" + long_txt + "');"), '--maj-reference')
code, out = lancer(mute("say(`clics : ${d.acGab}`);", "say(`clics : ${d.acGab}`); say('" + long_txt.replace('30 jours', '90 jours') + "');"))
verifie('changement loin dans un long morceau sans « ; » : visible dans le rapport', code == 1 and '90 jours' in out, out[-500:])
code, out = lancer(page(), '--maj-reference')  # référence des tests rétablie

code, out = lancer(mute("'Méthode de clic (avertissement autoclick) : '", "'M\\xE9thode de clic (avertissement autoclick) : '"))
verifie('échappement \\xE9 dans une chaîne : décodé, conforme', code == 0, out[-300:])
code, out = lancer(mute("  const note = 'Méthode de clic (avertissement autoclick) : ';\n</script>", "  const note = 'Méthode de clic (avertissement autoclick) : ';\n</SCRIPT data-x=\"1\" >"))
verifie('balise de fin </SCRIPT …> à attributs : blocs bien découpés, conforme', code == 0, out[-300:])
code, out = lancer(page().replace("const BUILD = '2026-11-04n'", "const BUILD = '2026-11-05a'"))
verifie('build seul changé : conforme', code == 0, out[-300:])
ref = json.loads(REF_TEST.read_text(encoding='utf-8')); ref.pop('autoclic')
REF_SANS = TMP / 'ref-sans.json'; REF_SANS.write_text(json.dumps(ref), encoding='utf-8')
f = TMP / 'page.html'; f.write_text(page(), encoding='utf-8')
r = subprocess.run([sys.executable, str(ICI / 'veille.py'), '--fichier', str(f), '--reference', str(REF_SANS)], capture_output=True, text=True)
verifie('référence sans suivi de l\'autoclic : écart', r.returncode == 1 and 'Référence sans suivi' in r.stdout, r.stdout[-300:])
o5 = TMP / 'o5'
lancer(mute("const ov = $('acWarnOv');", "const ov = $('acWarnOv);"), sortie=o5)
verifie('code illisible : sujet « illisible »', 'sujet=illisible' in o5.read_text())
code, out = lancer(mute("const ov = $('acWarnOv');", "const ov = $('acWarnOv);"))
verifie('code illisible : message sans balise <script> nue', '`<script>`' in out and ' <script> ' not in out, out[-300:])
o6 = TMP / 'o6'
lancer(mute("const ov = $('acWarnOv');", "const ov = $('acWarnOv);", page(shop=shop)), sortie=o6)
verifie('code illisible avec écart de barème : sujet « illisible » (titre juste)', 'sujet=illisible' in o6.read_text())

verifie('zones et fenêtres suivies : liste attendue',
        autoclic.ZONES == ('durWarn', 'acNotice', 'acShow', 'acPick', 'acWarnShow', 'acWarnClose', 'oneShot')
        and autoclic.FENETRES_TEXTE == ('acOv', 'durOv', 'acWarnOv'))
ac = REF.get('autoclic') or {}
verifie('reference.json : section autoclic complète (zones, fenêtres, champs du jeu)',
        bool(ac) and not autoclic.manques(ac) and set(ac['zones']) == set(autoclic.ZONES)
        and {'acDur', 'acNotice', 'acWarn', 'autoclick'} <= set(ac['champs']) and ac['textes'] and ac['instructions'])

code, out = lancer(mute('if (x.vol) {', '// commentaire neuf, avec autoclic\n      if (x.vol)   {'))
verifie('reformatage et commentaire seuls : conforme', code == 0, out[-300:])
code, out = lancer(mute('// « autoclic » en commentaire', '// autre commentaire sur l’autoclicker'))
verifie('commentaire à mot-clé changé hors zone : conforme', code == 0, out[-300:])

o1, o2 = TMP / 'o1', TMP / 'o2'
h = mute('Plus de 175 000 clics en 8 h', 'Plus de 150 000 clics en 8 h')
lancer(h, sortie=o1); lancer(h.replace("const BUILD = '2026-11-04n'", "const BUILD = '2026-11-05a'"), sortie=o2)
emp = [re.search(r'empreinte=(\w+)', o.read_text()).group(1) for o in (o1, o2)]
verifie('empreinte de l\'issue indépendante du build', emp[0] == emp[1])
verifie('sujet « autoclic »', 'sujet=autoclic' in o1.read_text())
shop = veille.shop_conseiller(); shop['doigt'] = dict(shop['doigt'], base=12)
o3 = TMP / 'o3'
lancer(page(shop=shop), sortie=o3)
verifie('sujet « bareme »', 'sujet=bareme' in o3.read_text())
o4 = TMP / 'o4'
lancer(mute('Plus de 175 000 clics en 8 h', 'Plus de 150 000 clics en 8 h', page(shop=shop)), sortie=o4)
verifie('sujet « mixte »', 'sujet=mixte' in o4.read_text())

code, out = lancer(mute('🤖 Autoclick : ce qui est interdit', '::error::autoclic @quelquun ~~~~ fin [lien](https://exemple.invalid)'))
verifie('texte tiers piégé dans un texte balayé : inerte dans le rapport (mention, commande « :: », bloc)',
        code == 1 and '@quelquun' not in out and '\n::' not in out and '~~~~ fin' not in out, out[-400:])

avant = REF_TEST.read_text(encoding='utf-8')
code, out = lancer(mute('function durWarn(x) {', 'function durAlert(x) {'), '--maj-reference')
verifie('recalage refusé si une zone manque (référence inchangée)', code == 3 and 'durWarn' in out and REF_TEST.read_text(encoding='utf-8') == avant, out[-300:])

code, out = lancer(page().replace('const SHOP = [', 'var SHOP=['))
verifie('code du jeu méconnaissable (minifié) : erreur d\'analyse, pas « inaccessible »', code == 3 and 'minifié' in out, out[-300:])

long = 'x\n~~~~\n' + ('a' * 99 + '\n') * 800 + '~~~~\n'  # 80 000 caractères, en lignes
c = veille.plafonner(long)
verifie('corps d\'issue plafonné sous la limite de GitHub (65 536, marge pour le lien), bloc refermé',
        len(c) <= 65_000 and c.count('~~~~') % 2 == 0, len(c))


def plante():
    raise ValueError('nombre illisible')


main_vrai, veille.main = veille.main, plante
code = veille.principal()
veille.main = main_vrai
verifie("plantage de l'analyse : état « erreur » (code 3), distinct d'une page inaccessible", code == 3)

# ---------- fichiers à part (modules du boss et du globe, /regles) ----------
# Modèles écrits pour ces tests, à la forme des fichiers du jeu (20/11/2026) : chaque zone suivie y est, avec des pièges
# du lecteur (chaîne à accolade, commentaire, gabarit). Aucune copie des fichiers du jeu dans le dépôt.
BOSS_NET = """/* BossEvent : scène du combat */
var BossEvent = (function () {
  function mount(host, opts) {
    var root = host.shadowRoot || host.attachShadow({ mode: "open" });
    var HTML = "<div class=\\"focus\\" id=\\"focus\\"><button id=\\"start\\">Rejoindre</button><button id=\\"bossBtn\\"></button>"
      + "<div id=\\"squads\\"></div><div id=\\"bonuses\\"></div><button id=\\"superBtn\\">Super</button><div id=\\"end\\"></div>"
      + "<button id=\\"closeEnd\\" hidden>Fermer</button></div>";
    root.innerHTML = HTML;
    var $ = function (id) { return root.getElementById(id); };
    var P2 = 0.5, CAP3 = 14, CAP = 6, WIN = 1500; // plafonds { par seconde }
    var S = null, ME = 0, squads = [];
    var hit = function (t) { return []; }; // autre « hit », local : pas dans la zone des coups
    function gate() {
      var t = S.t;
      if (t < S.stunUntil) { S.refused++; return false; }
      var sec = Math.floor(t / 1000);
      if (sec !== S.sec) { S.sec = sec; S.n = 0; }
      if (S.n >= (S.fever || S.press ? CAP3 : CAP)) { S.refused++; return false; }
      S.n++; S.counted++;
      return true;
    }
    function hit(x, y, real) { if (!gate()) return false; S.dmg += 1; return true; }
    function clickSquad(q, e) { if (q.sealed) { q.hp -= 1; } }
    function launchSuper() { if (S.charge >= 1) { S.charge = 0; $("superBtn").classList.remove("full"); } }
    function closeFocus() { host.hidden = true; if (opts.onClose) opts.onClose(); }
    squads.forEach(function (q) {
      q.w.addEventListener("click", function (e) { e.stopPropagation(); if (e.isTrusted) clickSquad(q, e); });
    });
    $("bossBtn").addEventListener("click", function (e) { if (!e.isTrusted) return; if (hit(e.clientX, e.clientY, true)) $("bossBtn").classList.add("broke"); });
    $("superBtn").addEventListener("click", function (e) { if (e.isTrusted) launchSuper(); });
    $("start").textContent = S && S.done ? "Retourner cliquer" : `Rejoindre ${opts.pseudo}`;
    $("end").className = "win";
    return {
      me: function () { return S ? { ms: Math.round(S.t), on: S.on, dmg: S.dmg, cl: S.counted } : null; },
      probe: function () { return { state: S ? S.state : "", pt: 0, fever: !!(S && S.fever), me: ME }; },
      close: closeFocus,
      state: function () { return { hp: S ? S.hp / S.hp0 : 1 }; },
    };
  }
  return { mount: mount };
})();
"""
BOSS_SITE = """(function () {
  var T = window.TaxeBoss, SV = window.BOSS_SERVER, ev = null;
  var hostEl = document.getElementById('bossHost');
  function open(o) { ev = window.bossEv = BossEvent.mount(hostEl, o); T.lock(true); }
  window.bossReopen = function () { open({}); };
  document.addEventListener('visibilitychange', function () { if (ev && document.hidden) ev.close(); });
})();
"""
MONDE = """export const preload = () => 1;
const KEY = 'taxe-giga-cp';
export function play(o) {
  const w = document.createElement('div'); w.className = 'mw'; w.setAttribute('role', 'dialog'); w.setAttribute('aria-label', 'Le tour du monde');
  w.innerHTML = `<div class="mw-prog"><em>0 / 174</em></div><div class="mw-paper"></div><div class="mw-cool" hidden></div>`;
  const paper = w.querySelector('.mw-paper');
  const btn = (c, t) => { const b = document.createElement('button'); b.className = c; b.textContent = t; return b; };
  const go = btn('go', 'Continuer ➜'), skip = btn('go mw-x', 'Passer ⏭');
  function launchFree() { const c = 'DE'; fetch(o.envoisUrl, { method: 'POST', body: JSON.stringify({ c }) }); localStorage.setItem('taxe-giga-monde-pays', '[]'); }
  function goFree() { w.querySelector('.mw-cool').hidden = false; paper.textContent = 'Pliez la facture'; }
  paper.addEventListener('keydown', e => { if (e.key === 'Enter') { paper.classList.add('f3'); launchFree(); } });
  w.addEventListener('click', e => { if (e.target.closest('.mw-cx')) goFree(); });
}
"""
REGLES = """<!doctype html><html><head><title>Règles</title><style>section { margin: 0 }</style></head><body>
<nav><a href="#resume">En bref</a></nav>
<section id="resume"><h2 id="h-resume">En bref</h2><p>Interdit : un <b>autoclicker</b>, une macro.</p></section>
<section id="limites"><h2>Les limites</h2><p>1 030 clics comptés par minute au plus.</p></section>
<section id="autoclick"><h2>L’autoclick</h2><div><p>Un premier avertissement.</p><p>Une pause de 10 minutes.</p></div></section>
<section id="reprise"><h2>Reprendre une partie</h2><p>Votre code secret ( GOBE-XXXX-… ).</p></section>
<section id="appel"><h2>Faites appel</h2><p>Votre pseudo (par exemple « Gobe-Octet sournois #732 »).</p></section>
<section id="faq"><h2>Questions</h2><details><summary>Entrée maintenue ?</summary><p>Un vrai appui à chaque taxe.</p></details>
<section class="q"><p>Sous-section.</p></section><p>Classement de tous les temps conservé.</p></section>
</body></html>
"""
MODELES = {'boss-event-net': BOSS_NET, 'boss-site': BOSS_SITE, 'monde': MONDE, 'regles': REGLES}
PAGE_F = page()  # page principale fabriquée (versions ?v= des modules : celles de PRINCIPALE)


def copies(**mutes):
    """Arguments --fichier-… avec les modèles, chacun muté par (avant, après) si donné ; None : copie non fournie."""
    out = []
    for nom, texte in MODELES.items():
        m = mutes.get(nom.replace('-', '_'), ())
        if m is None:
            continue
        for avant, apres in ([m] if m and isinstance(m[0], str) else m):
            assert avant in texte, (nom, avant)
            texte = texte.replace(avant, apres, 1)
        f = TMP / f'copie-{nom}'
        f.write_text(texte, encoding='utf-8')
        out += [f'--fichier-{nom}', str(f)]
    return out


def sorties(o):
    return dict(x.split('=', 1) for x in o.read_text().splitlines() if '=' in x)


of = TMP / 'of'
code, out = lancer(PAGE_F, '--maj-reference', *copies())
reff = json.loads(REF_TEST.read_text(encoding='utf-8')).get('fichiers') or {}
verifie('fichiers à part : référence des tests écrite avec les trois fichiers, rien d\'absent',
        code == 0 and set(reff) == {'boss', 'globe', 'regles'} and not any(fichiers.manques(k, reff[k]) for k in reff), out[-400:])
verifie('fichiers à part : #reprise non suivie (gabarit de code de compte), les cinq autres sections le sont',
        set(reff['regles']['sections']) == {'resume', 'limites', 'autoclick', 'appel', 'faq'} and 'GOBE-XXXX' not in json.dumps(reff, ensure_ascii=False)
        and 'Gobe-Octet' in reff['regles']['sections']['appel'])
verifie('fichiers à part : zones et empreintes seulement, pas de copie des fichiers',
        all('empreinte' in reff[k][p] and len(reff[k][p]['empreinte']) == 16 for k in ('boss', 'globe') for p in reff[k]))
of.unlink(missing_ok=True)
code, out = lancer(PAGE_F, *copies(), sortie=of)
s = sorties(of)
verifie('fichiers à part conformes : état « conforme », passage complet, page principale conforme',
        code == 0 and s.get('etat') == 'conforme' and s.get('fichiers_etat') == 'conforme' and s.get('fichiers_complet') == 'true', (s, out[-300:]))
of.unlink()
code, out = lancer(PAGE_F, *copies(monde=None), sortie=of)
s = sorties(of)
verifie('un fichier à part non lu : état « partiel », jamais « conforme » pour l\'ensemble', s.get('fichiers_etat') == 'partiel'
        and 'module du globe : non lu' in out and 'tous lus' not in out, (s, out[-300:]))

CAS_F = [
    ('module du boss : plafond de cadence (CAP) changé', dict(boss_event_net=('CAP = 6,', 'CAP = 8,')), 'constantes du combat'),
    ('module du boss : compte des coups changé', dict(boss_event_net=('S.n++; S.counted++;', 'S.n += 2; S.counted++;')), 'compte et refus des coups'),
    ('module du boss : garde isTrusted retirée', dict(boss_event_net=('if (e.isTrusted) launchSuper();', 'launchSuper();')), 'gardes isTrusted'),
    ('module du boss : interface rendue changée', dict(boss_event_net=('probe: function () { return { state:', 'probe: function () { return { etat:')), 'interface rendue'),
    ('module du boss : élément de la scène renommé', dict(boss_event_net=('id=\\"superBtn\\"', 'id=\\"superB\\"')), 'gabarit HTML'),
    ('module du boss : texte du bouton changé', dict(boss_event_net=('"Retourner cliquer"', '"Revenir au jeu"')), 'textes écrits dans la scène'),
    ('module du boss : classe d\'état changée', dict(boss_event_net=('classList.add("broke")', 'classList.add("cassé")')), 'changements de classe'),
    ('module du boss : globale renommée', dict(boss_site=('ev = window.bossEv = ', 'ev = window.bossEvent = ')), 'globales posées'),
    ('module du boss : contrat de la page changé', dict(boss_site=('T.lock(true)', 'T.verrou(true)')), 'contrat de la page'),
    ('module du boss : hôte de la scène renommé', dict(boss_site=("'bossHost'", "'bossHote'")), 'hôte de la scène'),
    ('module du boss : écouteur ajouté', dict(boss_site=("  window.bossReopen", "  hostEl.addEventListener('keydown', function () {});\n  window.bossReopen")), 'écouteurs'),
    ('module du boss : partie non suivie changée (empreinte seule)', dict(boss_event_net=('return root.getElementById(id);', 'return root.querySelector("#" + id);')), 'modifié hors des zones suivies'),
    ('module du boss : écouteur de boss-site.js changé', dict(boss_site=('if (ev && document.hidden)', 'if (ev && !document.hidden)')), 'écouteurs'),
    ('module du boss : fonction suivie disparue', dict(boss_event_net=('function closeFocus()', 'function fermer()')), 'introuvable'),
    ('module du boss : coup sur le boss changé', dict(boss_event_net=('S.dmg += 1;', 'S.dmg += 2;')), 'coup sur le boss (hit)'),
    ('module du boss : fonction déclarée réécrite en flèche (zone introuvable, pas l\'autre « hit »)',
     dict(boss_event_net=('function hit(x, y, real) {', 'var hit2 = function (x, y, real) {')), 'coup sur le boss (hit)** introuvable'),
    ('module du boss : autre « hit » local changé (hors des zones suivies)', dict(boss_event_net=('return []; };', 'return [1]; };')), 'modifié hors des zones suivies'),
    ('module du globe : lancement libre changé', dict(monde=("const c = 'DE';", "const c = 'FR';")), 'lancement libre'),
    ('module du globe : classe de la fenêtre renommée', dict(monde=("'.mw-cx'", "'.mw-close'")), 'classes de la fenêtre'),
    ('module du globe : clé du stockage changée', dict(monde=("'taxe-giga-monde-pays'", "'taxe-giga-pays'")), 'stockage du navigateur'),
    ('module du globe : clé du stockage déclarée en constante changée', dict(monde=("const KEY = 'taxe-giga-cp';", "const KEY = 'taxe-giga-code';")), 'clés du stockage du jeu'),
    ('module du globe : envoi changé', dict(monde=("fetch(o.envoisUrl,", "fetch('/monde/e.php',")), 'envois au serveur'),
    ('module du globe : fenêtre renommée', dict(monde=("'Le tour du monde'", "'Le globe'")), 'fenêtre du globe'),
    ('module du boss : mode de la racine de la scène changé', dict(boss_event_net=('attachShadow({ mode: "open" })', 'attachShadow({ mode: "closed" })')), 'racine de la scène'),
    ('module du globe : libellé de bouton changé', dict(monde=("btn('go', 'Continuer ➜')", "btn('go', 'Suite ➜')")), 'boutons de la fenêtre'),
    ('module du globe : classe racine mw changée', dict(monde=("w.className = 'mw';", "w.className = 'globe';")), 'classes de la fenêtre'),
    ('module du globe : élément créé changé', dict(monde=("const w = document.createElement('div');", "const w = document.createElement('section');")), 'éléments créés par le module'),
    ('module du globe : structure écrite changée (em de la progression)', dict(monde=('<em>0 / 174</em>', '<span>0 / 174</span>')), 'structure écrite dans la fenêtre'),
    ('module du globe : export renommé', dict(monde=('export function play(o)', 'export function jouer(o)')), 'noms exportés'),
    ('module du globe : partie non suivie changée (empreinte seule)', dict(monde=('export const preload = () => 1;', 'export const preload = () => 2;')), 'modifié hors des zones suivies'),
    ('/regles : section #resume changée', dict(regles=('une macro.', 'une macro, un script.')), 'section **#resume** modifiée'),
    ('/regles : section #limites changée', dict(regles=('1 030 clics', '1 200 clics')), 'section **#limites** modifiée'),
    ('/regles : section #autoclick changée (bloc imbriqué)', dict(regles=('Une pause de 10 minutes.', 'Une pause de 30 minutes.')), 'section **#autoclick** modifiée'),
    ('/regles : section #appel changée', dict(regles=('Faites appel', 'Écrivez-nous')), 'section **#appel** modifiée'),
    ('/regles : section #faq changée', dict(regles=('Un vrai appui', 'Un appui')), 'section **#faq** modifiée'),
    ('/regles : #faq changée après une section imbriquée', dict(regles=('tous les temps conservé', 'tous les temps perdu')), 'section **#faq** modifiée'),
    ('/regles : section #autoclick disparue', dict(regles=('<section id="autoclick">', '<section id="autoclic">')), '#autoclick** introuvable'),
    ('/regles : section ajoutée', dict(regles=('<section id="faq">', '<section id="bots"><p>Classement</p></section><section id="faq">')), 'liste des sections'),
    ('module du boss illisible (chaîne non fermée)', dict(boss_site=("'bossHost'", "'bossHost")), 'illisible'),
]
for nom, mutes, attendu in CAS_F:
    of.unlink(missing_ok=True)
    code, out = lancer(PAGE_F, *copies(**mutes), sortie=of)
    s = sorties(of)
    verifie(f'écart nommé : {nom}', s.get('fichiers_etat') == 'ecart' and attendu in out and s.get('etat') == 'conforme', (s, out[-500:]))
for nom, mutes in [('commentaire et reformatage dans un module', dict(boss_event_net=('var S = null, ME = 0', '// note\n    var S=null,   ME = 0'))),
                   ('/regles : section #reprise changée (non suivie)', dict(regles=('Votre code secret', 'Votre code'))),
                   ('/regles : texte hors section changé', dict(regles=('<a href="#resume">En bref</a>', '<a href="#resume">Résumé</a>')))]:
    of.unlink(missing_ok=True)
    code, out = lancer(PAGE_F, *copies(**mutes), sortie=of)
    verifie(f'sans écart : {nom}', sorties(of).get('fichiers_etat') == 'conforme', out[-400:])
of.unlink(missing_ok=True)
code, out = lancer(PAGE_F, *copies(regles=('Faites appel', '::error::@quelquun ~~~~ [lien](https://exemple.invalid)')), sortie=of)
verifie('texte tiers piégé dans /regles : inerte dans le rapport', '@quelquun' not in out and '\n::' not in out and '~~~~ [lien]' not in out, out[-400:])
o1, o2 = TMP / 'of1', TMP / 'of2'
for o, b in ((o1, '2026-11-04n'), (o2, '2026-11-05a')):
    o.unlink(missing_ok=True)
    lancer(PAGE_F.replace("const BUILD = '2026-11-04n'", f"const BUILD = '{b}'"), *copies(regles=('1 030 clics', '1 200 clics')), sortie=o)
verifie('étiquette d\'issue des fichiers indépendante du build, par fichier', sorties(o1)['fichiers_etiquettes'] == sorties(o2)['fichiers_etiquettes']
        and re.fullmatch(r'regles-[0-9a-f]{10}', sorties(o1)['fichiers_etiquettes']), sorties(o1))
of.unlink(missing_ok=True)
lancer(PAGE_F, *copies(regles=('1 030 clics', '1 200 clics'), monde=("const c = 'DE';", "const c = 'FR';")), sortie=of)
verifie('deux fichiers changés : une étiquette chacun', re.fullmatch(r'globe-[0-9a-f]{10} regles-[0-9a-f]{10}', sorties(of)['fichiers_etiquettes']), sorties(of))
avant = REF_TEST.read_text(encoding='utf-8')
code, out = lancer(PAGE_F, '--maj-reference', *copies(boss_event_net=('function hit(', 'function frappe(')))
verifie('recalage refusé si une zone d\'un module manque (référence inchangée)', code == 3 and 'hit' in out and REF_TEST.read_text(encoding='utf-8') == avant, out[-300:])
code, out = lancer(PAGE_F, '--maj-reference', *copies(regles=('<section id="faq">', '<section id="questions">')))
verifie('recalage refusé si une section de /regles manque', code == 3 and '#faq' in out and REF_TEST.read_text(encoding='utf-8') == avant, out[-300:])
code, out = lancer(PAGE_F, '--maj-reference')
verifie('recalage hors réseau sans copies : fichiers à part repris de l\'ancienne référence',
        code == 0 and json.loads(REF_TEST.read_text(encoding='utf-8')).get('fichiers') == reff and 'repris' in out, out[-300:])
ref = json.loads(REF_TEST.read_text(encoding='utf-8')); ref.pop('fichiers')
REF_SANS3 = TMP / 'ref-sans3.json'; REF_SANS3.write_text(json.dumps(ref), encoding='utf-8')
r = subprocess.run([sys.executable, str(ICI / 'veille.py'), '--fichier', str(TMP / 'page.html'), '--reference', str(REF_SANS3), *copies()],
                   capture_output=True, text=True)
verifie('référence sans suivi des fichiers à part : écart (jamais « conforme »)', 'Référence sans suivi du module du boss' in r.stdout, r.stdout[-300:])

rf = REF.get('fichiers') or {}
verifie('reference.json : section fichiers complète (boss, globe, /regles ; zones attendues, rien d\'absent)',
        set(rf) == {'boss', 'globe', 'regles'} and not any(fichiers.manques(k, rf[k]) for k in rf)
        and all(set(rf[k][p]['zones']) == {z[0] for z in fichiers.ZONES[p]} for k in ('boss', 'globe') for p in fichiers.FICHIERS[k][1]))

# quand lire : plage du jour, version du module du boss, rattrapage, demande
H = datetime.datetime


def plan(t, tous=False, ratt='', vp='1', vr='1'):
    return set(fichiers.a_lire(H.fromisoformat(t), tous, fichiers.rattrapage_lu(ratt), vp, vr))


verifie('plan : dans la plage du jour, les trois fichiers ; hors plage, aucun',
        plan('2026-11-20T03:10:00+00:00') == {'boss', 'globe', 'regles'} and plan('2026-11-20T03:24:00+00:00') == set()
        and plan('2026-11-20T03:07:59+00:00') == set() and plan('2026-11-20T04:10:00+01:00') == {'boss', 'globe', 'regles'})
verifie('plan : version ?v= du boss différente de la référence → module du boss à chaque passage',
        plan('2026-11-20T12:00:00+00:00', vp='2') == {'boss'} and plan('2026-11-20T12:00:00+00:00', vp=None) == set())
verifie('plan : rattrapage jusqu\'au troisième échec, puis attente de la plage',
        plan('2026-11-20T12:00:00+00:00', ratt='regles:1,globe:2') == {'regles', 'globe'} and plan('2026-11-20T12:00:00+00:00', ratt='regles:3') == set()
        and plan('2026-11-20T03:10:00+00:00', ratt='regles:3') == {'boss', 'globe', 'regles'})
verifie('plan : plage de 16 min, bornes comprises au début, exclues à la fin',
        datetime.datetime.combine(datetime.date(2026, 11, 20), fichiers.PLAGE[1]) - datetime.datetime.combine(datetime.date(2026, 11, 20), fichiers.PLAGE[0]) == datetime.timedelta(minutes=16)
        and plan('2026-11-20T03:23:59+00:00') == {'boss', 'globe', 'regles'} and plan('2026-11-20T03:08:00+00:00') == {'boss', 'globe', 'regles'})
verifie('plan : version ?v= différente mais module du boss à son troisième échec → attend la plage',
        plan('2026-11-20T12:00:00+00:00', ratt='boss:3', vp='2') == set() and plan('2026-11-20T12:00:00+00:00', ratt='boss:2', vp='2') == {'boss'})
verifie('plan : tous sur demande (envoi sur main, lancement manuel)', plan('2026-11-20T12:00:00+00:00', tous=True) == {'boss', 'globe', 'regles'})
verifie('rattrapage : entrée de forme inattendue ignorée', fichiers.rattrapage_lu('boss:1,x:2,regles:0,globe:2;rm,regles:12') == {'boss': 1}
        and fichiers.rattrapage_ecrit({'regles': 2, 'boss': 1}) == 'boss:1,regles:2')
fichiers.SUIVI_GLOBE = False
verifie('plan : globe non suivi quand SUIVI_GLOBE est faux', plan('2026-11-20T03:10:00+00:00', tous=True) == {'boss', 'regles'})
fichiers.SUIVI_GLOBE = True
# requêtes par jour : passages toutes les 15,3 min (mesuré le 20/11/2026), départ à chaque minute d'un quart d'heure
par_jour = []
for depart in range(16):
    t, n = H(2026, 11, 20, 0, depart, tzinfo=datetime.timezone.utc), 0
    while t < H(2026, 11, 21, 0, depart, tzinfo=datetime.timezone.utc):
        n += sum(len(fichiers.FICHIERS[k][1]) for k in fichiers.a_lire(t, False, {}, '1', '1'))
        t += datetime.timedelta(minutes=15.3)
    par_jour.append(n)
verifie('requêtes de plus par jour (passages à 15,3 min) : 4, ou 8 quand deux passages tombent dans la plage',
        set(par_jour) <= {4, 8} and 4 in par_jour, par_jour)


# requêtes comptées sur des passages complets (urlopen remplacé) : adresses, échecs, page principale inaccessible
class Refus(Exception):
    pass


def passage(*args, refus=(), page_html=None, sortie=None, erreur=None):
    """Un passage de veille.principal() sans réseau ; refus : adresses qui échouent (403). [adresses demandées]."""
    demandes = []

    def ouvre(req, timeout=None):
        u = req.full_url
        demandes.append(u)
        if any(x in u for x in refus):
            raise veille.urllib.error.HTTPError(u, 403, erreur or 'Forbidden', {}, None)
        chemin = u.split('taxe-au-giga.fr', 1)[1].split('?')[0]
        return Reponse((page_html or PAGE_F if chemin == '/' else MODELES[{'/boss/boss-event-net.js': 'boss-event-net', '/boss/boss-site.js': 'boss-site',
                                                                          '/monde/monde.js': 'monde', '/regles': 'regles'}[chemin]]).encode())
    veille.SORTIES_FICHIERS.clear()
    env, argv, vrai = os.environ.get('GITHUB_OUTPUT'), sys.argv, veille.urllib.request.urlopen
    if sortie:
        sortie.unlink(missing_ok=True); os.environ['GITHUB_OUTPUT'] = str(sortie)
    else:
        os.environ.pop('GITHUB_OUTPUT', None)
    sys.argv, veille.urllib.request.urlopen = ['veille.py', '--reference', str(REF_TEST), *args], ouvre
    try:
        with contextlib.redirect_stdout(io.StringIO()) as sortie_std:
            code = veille.principal()
    finally:
        sys.argv, veille.urllib.request.urlopen = argv, vrai
        if env is None:
            os.environ.pop('GITHUB_OUTPUT', None)
        else:
            os.environ['GITHUB_OUTPUT'] = env
    return code, demandes, sortie_std.getvalue()


v_boss = principale.releve(PAGE_F)['version du module du boss']
v_globe = principale.releve(PAGE_F)['version du module du globe']
code, d, _ = passage('--maintenant', '2026-11-20T12:00:00Z')
verifie('hors plage : une seule requête au site (page principale)', d == [veille.URL], d)
code, d, out = passage('--maintenant', '2026-11-20T03:10:00Z', sortie=of)
verifie('dans la plage : page principale puis les quatre fichiers à part, versions ?v= de la page',
        d == [veille.URL, f'{fichiers.RACINE}/boss/boss-event-net.js?v={v_boss}', f'{fichiers.RACINE}/boss/boss-site.js?v={v_boss}',
              f'{fichiers.RACINE}/monde/monde.js?v={v_globe}', f'{fichiers.RACINE}/regles'] and sorties(of)['fichiers_etat'] == 'conforme', (d, out[-300:]))
code, d, _ = passage('--maintenant', '2026-11-20T12:00:00Z', '--tous')
verifie('sur demande (--tous) : cinq requêtes', len(d) == 5, d)
code, d, out = passage('--maintenant', '2026-11-20T12:00:00Z', '--rattrapage', 'regles:1', sortie=of)
s = sorties(of)
verifie('rattrapage réussi : /regles seule relue, rattrapage vidé', d == [veille.URL, f'{fichiers.RACINE}/regles'] and s['rattrapage'] == '' and s['fichiers_etat'] == 'partiel', (d, s))
code, d, out = passage('--maintenant', '2026-11-20T03:10:00Z', refus=('/regles',), sortie=of)
s = sorties(of)
verifie('/regles injoignable une fois : ni issue (état « partiel »), rattrapage regles:1, page principale conforme',
        s['fichiers_etat'] == 'partiel' and s['rattrapage'] == 'regles:1' and s['etat'] == 'conforme' and code == 0 and 'non lu' in out, (s, out[-400:]))
code, d, out = passage('--maintenant', '2026-11-20T03:25:00Z', '--rattrapage', 'regles:2', refus=('/regles',), sortie=of)
s = sorties(of)
verifie('/regles injoignable une troisième fois de suite : signalé (état « inaccessible »)',
        s['fichiers_etat'] == 'inaccessible' and s['rattrapage'] == 'regles:3' and s['fichiers_etiquettes'] == 'inaccessible-regles', s)
code, d, out = passage('--maintenant', '2026-11-20T03:40:00Z', '--rattrapage', 'regles:3', sortie=of)
verifie('après le signalement : plus de relance hors plage (zéro requête de plus), rattrapage gardé',
        d == [veille.URL] and sorties(of)['rattrapage'] == 'regles:3' and sorties(of)['fichiers_etat'] == 'rien', (d, sorties(of)))
code, d, out = passage('--maintenant', '2026-11-20T03:10:00Z', refus=('boss-event-net',), sortie=of)
verifie('module en deux parties : arrêt au premier échec (pas de requête pour la seconde)',
        f'{fichiers.RACINE}/boss/boss-site.js?v={v_boss}' not in d and sorties(of)['rattrapage'] == 'boss:1', d)
page_ecart = mute('Plus de 175 000 clics en 8 h', 'Plus de 150 000 clics en 8 h')
code, d, out = passage('--maintenant', '2026-11-20T03:10:00Z', refus=('/boss/',), page_html=page_ecart, sortie=of)
s = sorties(of)
verifie('module injoignable et écart de la page principale : l\'écart reste signalé, état des fichiers à part distinct',
        code == 1 and s['etat'] == 'ecart' and s['sujet'] == 'autoclic' and s['fichiers_etat'] == 'partiel', s)
code, d, out = passage('--maintenant', '2026-11-20T03:10:00Z', '--rattrapage', 'globe:1', page_html='<html><title>Un instant</title></html>', sortie=of)
verifie('page principale inaccessible : aucune requête de plus, rattrapage transmis tel quel',
        d == [veille.URL] and sorties(of)['rattrapage'] == 'globe:1' and sorties(of)['fichiers_etat'] == 'rien', (d, sorties(of)))
vrai_modeles = dict(MODELES); MODELES['monde'] = '<html><title>Vérification</title></html>'
code, d, out = passage('--maintenant', '2026-11-20T03:10:00Z', sortie=of)
MODELES.update(vrai_modeles)
verifie('module reçu en HTML (vérification anti-robot) : échec d\'accès, pas un écart', sorties(of)['fichiers_etat'] == 'partiel'
        and sorties(of)['rattrapage'] == 'globe:1', sorties(of))
code, d, out = passage('--maintenant', '2026-11-20T12:00:00Z', page_html=PAGE_F.replace(f'?v={v_boss}', '?v=1794600000'), sortie=of)
verifie('version ?v= du boss changée : écart de la page principale, module du boss lu à ce passage',
        sorties(of)['etat'] == 'ecart' and len(d) == 3 and all('/boss/' in x and '?v=1794600000' in x for x in d[1:]), d)

code, d, out = passage('--maintenant', '2026-11-20T03:25:00Z', '--rattrapage', 'regles:2', refus=('/regles',), sortie=of)
s = sorties(of)
verifie('échec qui dure seul : étiquette « inaccessible-regles » seulement', s['fichiers_etiquettes'] == 'inaccessible-regles', s)
MODELES['boss-event-net'] = BOSS_NET.replace('CAP = 6,', 'CAP = 8,')
code, d, out = passage('--maintenant', '2026-11-20T03:10:00Z', '--rattrapage', 'regles:2', refus=('/regles',), sortie=of)
s = sorties(of)
verifie('échec qui dure à côté d\'un écart d\'un autre fichier : signalé aussi (étiquette à lui)',
        s['fichiers_etat'] == 'ecart' and s['fichiers_etiquettes'].split()[-1] == 'inaccessible-regles' and s['fichiers_etiquettes'].startswith('boss-')
        and 'Échec qui dure' in out, (s, out[-300:]))
code, d, out = passage('--maintenant', '2026-11-20T03:10:00Z', '--rattrapage', 'globe:1', refus=('/regles',), sortie=of)
verifie('premier échec à côté d\'un écart : pas d\'étiquette « inaccessible »', 'inaccessible' not in sorties(of)['fichiers_etiquettes'], sorties(of))
MODELES['boss-event-net'] = BOSS_NET
code, d, out = passage('--maintenant', '2026-11-20T03:10:00Z', refus=('/regles',), erreur='::error:: @quelquun ~~~~ fin', sortie=of)
verifie('message d\'échec d\'un fichier (texte du site) inerte dans le rapport', 'non lu' in out and '@quelquun' not in out and '\n::' not in out
        and '~~~~ fin' not in out, out[-400:])
avant = REF_TEST.read_text(encoding='utf-8')
code, d, out = passage('--maj-reference', refus=('/regles',))
verifie('recalage refusé si un fichier à part n\'a pas pu être lu (référence inchangée)', code == 3 and 'non lu' in out
        and REF_TEST.read_text(encoding='utf-8') == avant, out[-300:])
code, d, out = passage('--fichier', str(TMP / 'page.html'), '--fichier-regles', str(TMP / 'copie-regles'), '--maintenant', '2026-11-20T03:10:00Z', '--tous')
verifie('hors réseau (--fichier) : aucune requête, même dans la plage et avec --tous', d == [], d)
code, out = lancer(PAGE_F, '--maj-reference', *copies(boss_event_net=('probe: function () { return { state:', 'sonde: function () { return { state:')))
verifie('recalage refusé si une zone d\'inventaire requise est vide (interface rendue)', code == 3 and 'interface rendue' in out
        and REF_TEST.read_text(encoding='utf-8') == avant, out[-300:])
etq = []
for m in (('CAP = 6,', 'CAP = 7,'), ('CAP = 6,', 'CAP = 9,')):
    of.unlink(missing_ok=True); lancer(PAGE_F, *copies(boss_event_net=m), sortie=of); etq.append(sorties(of)['fichiers_etiquettes'])
verifie('deux écarts différents d\'un même fichier : deux étiquettes différentes', etq[0] != etq[1] and all(e.startswith('boss-') for e in etq), etq)

print('\nTout est passé' if not echecs else f'\n{echecs} échec(s)')
sys.exit(1 if echecs else 0)
