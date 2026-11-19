#!/usr/bin/env python3
"""Tests de la veille (dev/veille/veille.py), sur des pages fabriquées : aucune copie de la page du jeu dans le dépôt.

Page fabriquée : le numéro de build, le tableau SHOP écrit d'après le barème du conseiller (tableau P de conseiller.js),
chaque passage de règle tel qu'il est noté dans dev/veille/reference.json, et un modèle de la détection d'autoclic
(AUTOCLIC, écrit pour ces tests à la forme de la page du jeu, avec les pièges de lecture connus). Les tests comparent à
une référence tirée de cette page fabriquée, pas à dev/veille/reference.json.
Usage : python3 dev/veille/test_veille.py
"""
import json, os, pathlib, re, subprocess, sys, tempfile

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import autoclic, veille  # noqa: E402

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


def page(build="2026-11-04n", shop=None, regles=None, autoclic=AUTOCLIC):
    shop = shop if shop is not None else veille.shop_conseiller()
    lignes = [f"const BUILD = '{build}';", 'const SHOP = [']
    for k, u in shop.items():
        extra = ''.join(f", {c}: {u[c]:g}" for c in ('rate', 'click', 'pct', 'max') if u[c])
        lignes.append(f"  {{ id: '{k}', name: '', base: {u['base']:g}, unlock: 1{extra} }},")
    lignes.append('];')
    for texte in (regles or REF['regles']).values():
        lignes += (texte or '').split(' | ')
    return '\n'.join(lignes) + '\n' + autoclic


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


veille.main = plante
code = veille.principal()
verifie("plantage de l'analyse : état « erreur » (code 3), distinct d'une page inaccessible", code == 3)

print('\nTout est passé' if not echecs else f'\n{echecs} échec(s)')
sys.exit(1 if echecs else 0)
