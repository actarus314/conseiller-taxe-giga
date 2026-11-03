#!/usr/bin/env python3
"""Veille du jeu Taxe au Giga : le conseiller est-il toujours juste ?

Télécharge la page du jeu et vérifie trois choses :
1. le barème du jeu (tableau SHOP) est identique à celui du conseiller (tableau P de conseiller.js) ;
2. les règles dont le conseiller dépend (formules, limites, bonus, sauvegarde, éléments de page lus)
   sont identiques à la référence dev/veille/reference.json ;
3. la page reçue est bien celle du jeu (pas une page de vérification anti-robot).

Sortie : rapport Markdown sur la sortie standard, empreinte du constat dans $GITHUB_OUTPUT.
Code de retour : 0 conforme, 1 écart, 2 page du jeu inaccessible.
Usage : python3 dev/veille/veille.py [--fichier page.html] [--maj-reference]
"""
import hashlib, json, os, pathlib, re, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
REF = ROOT / 'dev' / 'veille' / 'reference.json'
URL = 'https://taxe-au-giga.fr/'

# Règles suivies : nom → expression qui isole le passage du code du jeu dont le conseiller dépend
REGLES = {
    'prix': r"const cost = u => [^;]+;",
    'production': r"const rate = \(\) => [^;]+;",
    'part du clic': r"const clickPct = \(\) => [^;]+;",
    'puissance de clic': r"const clickPower = \(\) => [^;]+;",
    'frénésie (production)': r"acc \+= effRate\(\) \* dt \* [^;]+;",
    'rafale (clics)': r"n = power\(\) \* \(rafaleOn \? \d+ : 1\)",
    'durées des bonus dorés': r"frenzyUntil = Date\.now\(\) \+ \d+;.{0,200}?rafaleUntil = Date\.now\(\) \+ \d+;",
    'déblocage': r"const visible = SHOP\.filter\([^;]+;",
    'limites de clics': r"au-delà de [\d\s ]+clics par minute ou [\d\s ]+par heure",
    'hors ligne': r"Fenêtre fermée, ils continuent à \d+ %</b>, pendant \d+ h au plus",
    'sauvegarde': r"const SAVE = '[^']+';",
    'contenu sauvegardé': r"JSON\.stringify\(\{ myCount, wallet, owned, t: Date\.now\(\) \}\)",
    'carte de bonus': r'b\.innerHTML = `<span class="ie">[^`]+`;',
    'affichage possédés et prix': r"b\.querySelector\('\.own'\)\.textContent = [^;]+;\s*b\.querySelector\('\.price'\)\.textContent = [^;]+;",
    'éléments lus': r'id="(?:wallet|shop|perClick|buffChip|goldBill|taxBtn|stickyTax)"',
}


def page():
    if '--fichier' in sys.argv:
        return pathlib.Path(sys.argv[sys.argv.index('--fichier') + 1]).read_text(encoding='utf-8')
    req = urllib.request.Request(URL, headers={'User-Agent': 'conseiller-taxe-giga-veille (+https://github.com/actarus314/conseiller-taxe-giga)'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'replace')


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def shop_jeu(html):
    a = html.find('const SHOP = [')
    if a < 0:
        return None
    b = html.find('];', a)
    out = {}
    for m in re.finditer(r"\{ id: '(\w+)'.*?base: ([\d.e]+), unlock: ([\d.e]+)(.*?)\n", html[a:b]):
        rest = m.group(4)
        g = lambda k: float((re.search(k + r': ([\d.e]+)', rest) or [0, 0])[1])
        out[m.group(1)] = dict(base=float(m.group(2)), rate=g('rate'), click=g('click'), pct=g('pct'), max=g('max'))
    return out


def shop_conseiller():
    src = (ROOT / 'conseiller.js').read_text(encoding='utf-8')
    a = src.index('const P = ['); b = src.index('].map(', a)
    out = {}
    for m in re.finditer(r"\['(\w+)', '(?:[^'\\]|\\.)*', ([^\]]+)\]", src[a:b]):
        v = [float(x) for x in m.group(2).split(',')] + [0, 0, 0, 0, 0]
        out[m.group(1)] = dict(base=v[0], rate=v[1], click=v[2], pct=v[3], max=v[4])
    return out


def regles(html):
    out = {}
    for nom, rx in REGLES.items():
        found = re.findall(rx, html, re.S)
        out[nom] = ' | '.join(sorted(set(norm(x) for x in found))) if found else None
    return out


def main():
    try:
        html = page()
    except Exception as e:
        print(f'## Page du jeu inaccessible\n\n{e}')
        return finish('inaccessible', str(type(e).__name__), 2)
    build = (re.search(r"const BUILD = '([^']+)'", html) or [None, None])[1]
    if 'const SHOP = [' not in html or not build:
        titre = (re.search(r'<title>([^<]*)', html) or [None, '?'])[1]
        print(f'## Page du jeu inaccessible\n\nPage reçue : « {titre.strip()} » ({len(html)} octets), sans le code du jeu. Probablement une page de vérification anti-robot.')
        return finish('inaccessible', 'sans-code', 2)

    actuel = regles(html)
    if '--maj-reference' in sys.argv:
        REF.write_text(json.dumps({'build': build, 'regles': actuel}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(f'Référence écrite (build {build}).')
        return 0

    ecarts = []
    jeu, cons = shop_jeu(html), shop_conseiller()
    for k in sorted(set(jeu) | set(cons)):
        if k not in cons:
            ecarts.append(f'- Bonus **{k}** présent dans le jeu, absent du conseiller : {jeu[k]}')
        elif k not in jeu:
            ecarts.append(f'- Bonus **{k}** présent dans le conseiller, absent du jeu')
        elif jeu[k] != cons[k]:
            diff = ', '.join(f'{c} {cons[k][c]:g} → {jeu[k][c]:g}' for c in jeu[k] if jeu[k][c] != cons[k][c])
            ecarts.append(f'- Bonus **{k}** modifié : {diff}')
    ref = json.loads(REF.read_text(encoding='utf-8'))
    for nom in REGLES:
        avant, apres = ref['regles'].get(nom), actuel.get(nom)
        if avant != apres:
            ecarts.append(f'- Règle **{nom}** modifiée\n  - référence : `{avant}`\n  - jeu : `{apres}`')

    print(f'Build du jeu : {build} (référence : {ref["build"]}) · {len(jeu)} bonus · {len(REGLES)} règles suivies\n')
    if not ecarts:
        print('Conforme : barème et règles identiques à ceux du conseiller.')
        return finish('conforme', build, 0)
    print('## Écarts entre le jeu et le conseiller\n')
    print('\n'.join(ecarts))
    print('\nÀ faire : relire le code du jeu, mettre à jour `P` dans conseiller.js et la référence (`python3 dev/veille/veille.py --maj-reference`), relancer les tests.')
    return finish('ecart', '\n'.join(ecarts), 1)


def finish(etat, detail, code):
    emp = hashlib.sha256(detail.encode()).hexdigest()[:10]
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f'etat={etat}\nempreinte={emp}\n')
    return code


if __name__ == '__main__':
    sys.exit(main())
