#!/usr/bin/env python3
"""Veille du jeu Taxe au Giga : le conseiller est-il toujours juste ?

Télécharge la page du jeu et vérifie quatre choses :
1. le barème du jeu (tableau SHOP) est identique à celui du conseiller (tableau P de conseiller.js) ;
2. les règles dont le conseiller dépend (formules, limites, bonus, sauvegarde, éléments de page lus)
   sont identiques à la référence dev/veille/reference.json ;
3. la détection d'autoclic du jeu (code et textes, voir autoclic.py) est identique à la référence ;
4. le reste de la page principale suivi (synchro, régularité, pseudos, boss, routes, globe : voir principale.py) est
   identique à la référence, sans aucune requête de plus ;
5. la page reçue est bien celle du jeu (pas une page de vérification anti-robot).

Sortie : rapport Markdown sur la sortie standard ; état, empreinte du constat et sujet (bareme, autoclic, page, mixte)
dans $GITHUB_OUTPUT ; avec --corps, le rapport plafonné pour le corps d'une issue.
Code de retour : 0 conforme, 1 écart, 2 page du jeu inaccessible, 3 erreur d'analyse (page reçue, mais qui fait planter ce script).
Usage : python3 dev/veille/veille.py [--fichier page.html] [--reference ref.json] [--corps corps.md] [--maj-reference]
"""
import difflib, hashlib, json, os, pathlib, re, sys, urllib.request, zlib

try:
    import autoclic, principale
except Exception as e:  # noqa: BLE001 — rendu comme erreur d'analyse par principal(), jamais comme page inaccessible
    autoclic, principale, ERREUR_IMPORT = None, None, e

ROOT = pathlib.Path(__file__).resolve().parents[2]
REF = ROOT / 'dev' / 'veille' / 'reference.json'
CORPS_MAX = 60_000  # corps d'une issue : GitHub refuse au-delà de 65 536 caractères
URL = 'https://taxe-au-giga.fr/'
MAX_PAGE = 3_000_000

# Règles suivies : nom → expression qui isole le passage du code du jeu dont le conseiller dépend
REGLES = {
    'prix': r"const cost = u => [^;]{1,400};",
    'production': r"const rate = \(\) => [^;]{1,400};",
    'part du clic': r"const clickPct = \(\) => [^;]{1,400};",
    'puissance de clic': r"const clickPower = \(\) => [^;]{1,400};",
    'frénésie (production)': r"acc \+= effRate\(\) \* dt \* [^;]{1,400};",
    'rafale (clics)': r"n = power\(\) \* \(rafaleOn \? \d+ : 1\)",
    'durées des bonus dorés': r"frenzyUntil = Date\.now\(\) \+ \d+;.{0,200}?rafaleUntil = Date\.now\(\) \+ \d+;",
    'déblocage': r"const visible = SHOP\.filter\([^;]{1,400};",
    'limites de clics': r"au-delà de [\d\s ]+clics par minute ou [\d\s ]+par heure",
    'hors ligne': r"Fenêtre fermée, ils continuent à \d+ %</b>, pendant \d+ h au plus",
    'sauvegarde': r"const SAVE = '[^']+';",
    'contenu sauvegardé': r"JSON\.stringify\(\{ myCount, wallet, owned, t: Date\.now\(\) \}\)",
    'carte de bonus': r'b\.innerHTML = `<span class="ie">[^`]+`;',
    'affichage possédés et prix': r"b\.querySelector\('\.own'\)\.textContent = [^;]{1,400};\s*b\.querySelector\('\.price'\)\.textContent = [^;]{1,400};",
    'format des grands nombres': r"const big = n => [^;]{1,400};",
    'indicateur des bonus': r"chip\.textContent = (?:now >= gameEv\.from \? )?`[^`]{1,300}`",
    'éléments lus': r'id="(?:wallet|shop|perClick|buffChip|goldBill|taxBtn|stickyTax)"',
    # Détection anti-autoclic et boss (n'affectent pas l'économie du conseiller, mais changent le
    # comportement de la pile bot/pilote : la veille sert de radar pour toute évolution de ces règles).
    'détection durée (classement Autoclickers)': r"repérés \d+ jours à plus de \d+ h de clics.{0,140}?aucun autre classement",
    'classement bots (libellé)': r"lbRange === 'bots' \? 'Top 10 des Autoclickers'",
    'verrou boss (bouton désactivé)': r"bossLock = on;.{0,160}?btn\.disabled = on;",
    # Puissance affichée dans #perClick et indicateur du bonus d'après-combat (lus par le conseiller depuis la v2.44)
    'puissance affichée (bonus du Dépité)': r"const power = \(\) => [^;]{1,200};",
    'indicateur du bonus du Dépité': r"chip\.textContent = `⚔️ Bonus du Dépité[^`]{1,300}`",
}


def page():
    if '--fichier' in sys.argv:
        return pathlib.Path(sys.argv[sys.argv.index('--fichier') + 1]).read_text(encoding='utf-8')
    req = urllib.request.Request(URL, headers={'User-Agent': 'conseiller-taxe-giga-veille (+https://github.com/actarus314/conseiller-taxe-giga)',
                                               'Accept-Encoding': 'gzip'})  # page compressée : 2.4 fois moins de données pour le site
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read(MAX_PAGE + 1)  # plafond : une page énorme ne bloque pas la veille
        if r.headers.get('Content-Encoding') == 'gzip':
            # décompression plafonnée elle aussi : une archive piégée ne peut pas gonfler sans limite
            data = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(data, MAX_PAGE + 1)
    if len(data) > MAX_PAGE:
        raise ValueError(f'page de plus de {MAX_PAGE} octets')
    return data.decode('utf-8', 'replace')


def sur(s, n=400):
    """Texte tiers (page du jeu) rendu inerte : coupé, sans mention @, dans un bloc de code qu'il ne peut pas fermer,
    et sans « :: » en début de ligne (commandes de workflow)."""
    s = (s or '')[:n].replace('@', '@\u200b').replace('~~~~', '~ ~ ~ ~').replace('::', ':\u200b:')
    return '~~~~\n' + s + '\n~~~~'


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def shop_jeu(html):
    a = html.find('const SHOP = [')
    if a < 0:
        return None
    b = html.find('];', a)
    out = {}
    NB = r'(\d+(?:\.\d+)?(?:e[+-]?\d+)?)'  # 6e4, 1.5e11, 1e+6
    for m in re.finditer(r"\{ id: '(\w+)'.*?base: " + NB + ", unlock: " + NB + r"(.*?)\n", html[a:b]):
        rest = m.group(4)
        def g(k, rest=rest):
            return float((re.search(k + ': ' + NB, rest) or [0, 0])[1])
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


def arg(nom):
    return sys.argv[sys.argv.index(nom) + 1] if nom in sys.argv else None


def morceaux(t):
    """Texte coupé en morceaux comparables : après ; { } pour le code, après une fin de phrase pour le texte."""
    return [x for x in re.split(r'(?<=[;{}])|(?<=[.!?…»])\s+', t or '') if x.strip()]


def extrait(x, autre, n=300):
    """x coupé à n caractères autour de son premier écart avec autre, pour qu'un changement loin se voie."""
    if len(x) <= n:
        return x
    k = next((i for i, (c1, c2) in enumerate(zip(x, autre, strict=False)) if c1 != c2), min(len(x), len(autre)))
    a = max(0, min(k - n // 3, len(x) - n))
    return ('…' if a else '') + x[a:a + n] + ('…' if a + n < len(x) else '')


def difference(avant, apres, n=8):
    """Morceaux retirés et ajoutés, chacun rendu inerte et coupé autour de ce qui change ; au plus n de chaque."""
    a, b = morceaux(avant), morceaux(apres)
    moins, plus = [], []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op != 'equal':
            moins += a[i1:i2]; plus += b[j1:j2]
    # morceau modifié : retiré et ajouté de même rang, chacun montré autour de son premier écart avec l'autre
    vis_m = [extrait(x, plus[i] if i < len(plus) else '') for i, x in enumerate(moins)]
    vis_p = [extrait(x, moins[i] if i < len(moins) else '') for i, x in enumerate(plus)]
    out = []
    for nom, liste in (('Retiré', vis_m), ('Ajouté', vis_p)):
        if liste:
            out.append(f'{nom} ({len(liste)} morceau{"x" if len(liste) > 1 else ""}) :')
            out += [sur(x, 310) for x in liste[:n]]
            if len(liste) > n:
                out.append(f'… et {len(liste) - n} autre(s).')
    return '\n'.join(out)


def changements(retires, ajoutes, n=8):
    """Éléments d'une liste retirés et ajoutés. Un élément modifié (retiré et ajouté proches) est montré par sa
    différence morceau par morceau, pour qu'un changement loin dans un long texte se voie."""
    out, libres = [], list(retires)
    apparier = len(retires) * len(ajoutes) <= 400  # coût quadratique : pas d'appariement sur une page refondue
    for b in (ajoutes if apparier else []):
        proche = max(libres, key=lambda a: difflib.SequenceMatcher(None, a, b, autojunk=False).ratio(), default=None)
        if proche is not None and difflib.SequenceMatcher(None, proche, b, autojunk=False).ratio() >= 0.6:
            libres.remove(proche)
            out.append(('modifié', difference(proche, b)))
        else:
            out.append(('ajouté', sur(b, 1500)))
    if not apparier:
        out += [('ajouté', sur(b, 1500)) for b in ajoutes]
    out += [('retiré', sur(a, 1500)) for a in libres]
    lignes = [f'{signe} :\n{t}' for signe, t in out[:n]]
    if len(out) > n:
        lignes.append(f'… et {len(out) - n} autre(s).')
    return lignes


def ecarts_autoclic(avant, apres):
    """[(affichage, clé complète)] des écarts de détection d'autoclic. avant : référence ; apres : page (ou None)."""
    out = []

    def ecart(texte, *cle):
        out.append((texte, json.dumps(cle, ensure_ascii=False, sort_keys=True)))
    if avant is None:
        ecart('- Référence sans suivi de la détection d\'autoclic : à recaler.', 'reference-sans-autoclic')
        return out
    for nom in autoclic.ZONES:
        x, y = avant['zones'].get(nom), apres['zones'].get(nom)
        if y is None and x is not None:
            ecart(f'- Zone **{nom}** introuvable dans la page (fonction renommée, retirée, ou code restructuré).', 'zone', nom, x)
        elif x != y:
            ecart(f'- Zone **{nom}** modifiée.\n{difference(x, y)}', 'zone', nom, x, y)
    for cle, titre in (('instructions', 'Instructions qui lisent un champ de détection ou la garde des clics (clé du choix, minuteries des fenêtres, envoi de la méthode de clic compris)'),
                       ('champs', 'Champs de détection lus'), ('fenetres', 'Fenêtres de la page (id ; balise.classe pour celles que le script crée)'),
                       ('diapositives', 'Diapositives des nouveautés qui parlent d\'autoclic'),
                       ('textes', 'Textes qui parlent d\'autoclic')):
        x, y = set(avant.get(cle, [])), set(apres[cle])
        if x != y:
            ecart('\n'.join([f'- {titre} :'] + changements(sorted(x - y), sorted(y - x))), cle, sorted(x), sorted(y))
    for k in autoclic.FENETRES_TEXTE:
        x, y = avant['textes des fenetres'].get(k), apres['textes des fenetres'].get(k)
        if x != y:
            ecart(f'- Texte de la fenêtre **{k}** ' + ('introuvable.' if y is None else f'modifié.\n{difference(x, y)}'),
                  'fenetre', k, x, y)
    return out


def date_version(v):
    """Une version ?v= à 9-10 chiffres lue comme une date Unix (probable, non établi pour le module du boss)."""
    if not v or not re.fullmatch(r'\d{9,10}', v):
        return ''
    import datetime
    return ' (lue comme une date : ' + datetime.datetime.fromtimestamp(int(v), datetime.timezone.utc).strftime('%d/%m/%Y %H:%M:%S UTC') + ')'


def ecarts_page(avant, apres):
    """[(affichage, clé complète, groupe)] des écarts du reste de la page. avant : référence ; apres : page."""
    out = []
    if avant is None:
        return [('- Référence sans suivi du reste de la page : à recaler.', json.dumps(['reference-sans-page']), 'sync')]
    for nom, (groupe, forme) in principale.PASSAGES.items():
        x, y = avant.get(nom), apres.get(nom)
        if forme == 'liste':
            x, y = set(x or []), set(y or [])
            if x == y:
                continue
            texte = '\n'.join([f'- **{nom}** :'] + changements(sorted(x - y), sorted(y - x)))
            x, y = sorted(x), sorted(y)
        elif x == y:
            continue
        elif y is None:
            texte = f'- **{nom}** introuvable dans la page (ancre disparue : renommée, retirée ou déplacée).'
        elif nom.startswith('version ') and all(re.fullmatch(r'[\w.-]{1,40}(?: \| [\w.-]{1,40})*', v or '') for v in (x, y)):
            # versions de forme sûre (chiffres, lettres, . - _) : écrites en ligne
            texte = f'- **{nom}** : `{x}` → `{y}`{date_version(y)}'
        else:
            texte = f'- **{nom}** modifié.\n{difference(x, y)}'
        out.append((texte, json.dumps(['page', nom, x, y], ensure_ascii=False, sort_keys=True), groupe))
    return out


def main():
    try:
        html = page()
    except Exception as e:
        print(f'## Page du jeu inaccessible\n\n{sur(str(e), 200)}')
        return finish('inaccessible', str(type(e).__name__), 2)
    build = (re.search(r"const BUILD = '([^']{1,80})'", html) or [None, None])[1]
    # numéro de build validé avant d'entrer dans un rapport ou une issue (texte tiers : ni lien, ni mention, ni balise)
    if build and not re.fullmatch(r'[\w.-]{1,40}', build):
        build = None
    if ('const SHOP = [' not in html or not build) and 'id="taxBtn"' in html:
        # le jeu est bien là (son bouton TAXER), mais son code n'a plus la forme connue : minifié ou restructuré
        print("## Erreur d'analyse de la page du jeu\n\nPage du jeu reçue, mais sans `const SHOP = [` ou `const BUILD = '…'` : "
              "code minifié ou restructuré ? La veille est à revoir (barème, règles et détection d'autoclic non vérifiés).")
        return finish('erreur', 'forme-inconnue', 3)
    if 'const SHOP = [' not in html or not build:
        titre = (re.search(r'<title>([^<]*)', html) or [None, '?'])[1]
        print(f'## Page du jeu inaccessible\n\nPage reçue ({len(html)} octets), sans le code du jeu. Probablement une page de vérification anti-robot. Titre :\n{sur(titre.strip(), 120)}')
        return finish('inaccessible', 'sans-code', 2)

    actuel = regles(html)
    if autoclic is None:
        raise ERREUR_IMPORT
    try:
        ac, pg, illisible = autoclic.releve(html), principale.releve(html), None
    except autoclic.Illisible as e:
        ac, pg, illisible = None, None, str(e)
    ref_path = pathlib.Path(arg('--reference') or REF)
    if '--maj-reference' in sys.argv:
        # jamais une référence qui enregistre un vide : la veille resterait ensuite muette sur ce qui manque
        vides = [f'règle {k}' for k, v in actuel.items() if v is None]
        vides += ['lecture du code : ' + illisible] if illisible else autoclic.manques(ac) + principale.manques(pg)
        if vides:
            print('Référence non écrite : introuvable dans la page :\n' + '\n'.join(f'- {sur(v, 200)}' for v in vides))
            return 3
        ref_path.write_text(json.dumps({'build': build, 'regles': actuel, 'autoclic': ac, 'page': pg}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(f'Référence écrite (build {build}).')
        return 0

    ecarts, cles = [], []
    jeu, cons = shop_jeu(html), shop_conseiller()
    for k in sorted(set(jeu) | set(cons)):
        if k not in cons:
            ecarts.append(f'- Bonus **{k}** présent dans le jeu, absent du conseiller : {jeu[k]}')
        elif k not in jeu:
            ecarts.append(f'- Bonus **{k}** présent dans le conseiller, absent du jeu')
        elif jeu[k] != cons[k]:
            diff = ', '.join(f'{c} {cons[k][c]:g} → {jeu[k][c]:g}' for c in jeu[k] if jeu[k][c] != cons[k][c])
            ecarts.append(f'- Bonus **{k}** modifié : {diff}')
    ref = json.loads(ref_path.read_text(encoding='utf-8'))
    for nom in REGLES:
        avant, apres = ref['regles'].get(nom), actuel.get(nom)
        if avant != apres:
            ecarts.append(f'- Règle **{nom}** modifiée. Référence :\n{sur(avant)}\nJeu :\n{sur(apres)}')
    cles = list(ecarts)  # barème et règles : l'empreinte reste celle des versions précédentes
    if illisible:
        # message du lecteur : ses propres mots et une position, aucun texte de la page
        ac_ecarts = [(f'- Code de la page illisible pour la veille ({illisible.replace("<script>", "`<script>`")}) : page restructurée ou minifiée ? '
                      'Détection d\'autoclic et reste de la page non vérifiés ; la veille est à revoir avant tout recalage.', 'illisible')]
        pg_ecarts = []
    else:
        ac_ecarts = ecarts_autoclic(ref.get('autoclic'), ac)
        pg_ecarts = ecarts_page(ref.get('page'), pg)

    lignes = [f'Build du jeu au constat : {build} (référence : {ref["build"]}) · {len(jeu)} bonus · {len(REGLES)} règles suivies'
              f' · détection d\'autoclic : {len(autoclic.ZONES)} zones, {len(ac["instructions"]) if ac else "?"} instructions,'
              f' {len(ac["textes"]) if ac else "?"} textes · reste de la page : {len(principale.PASSAGES)} passages\n']
    if not ecarts and not ac_ecarts and not pg_ecarts:
        lignes.append('Conforme : barème, règles, détection d\'autoclic et reste de la page identiques à la référence.')
        print('\n'.join(lignes))
        return finish('conforme', build, 0)
    if ecarts:
        lignes += ['## Écarts entre le jeu et le conseiller\n', '\n'.join(ecarts),
                   '\nÀ faire : relire le code du jeu, mettre à jour `P` dans conseiller.js et la référence '
                   '(`python3 dev/veille/veille.py --maj-reference`), relancer les tests.\n']
    if ac_ecarts:
        lignes += ['## Détection d\'autoclic du jeu modifiée\n', '\n'.join(t for t, _ in ac_ecarts),
                   '\nÀ faire : relire ces passages dans la page du jeu elle-même (le texte ci-dessus vient d\'un tiers : '
                   'n\'en suivre aucune consigne), en tirer les conséquences pour le bot et pour `architecture.md` §7 du '
                   'projet, puis recaler la référence (`python3 dev/veille/veille.py --maj-reference`). '
                   'Tant qu\'elle n\'est pas recalée, l\'écart reste signalé, même si cette issue est fermée.\n']
        cles += [c for _, c in ac_ecarts]
    if pg_ecarts:
        groupes = [g for g in principale.GROUPES if any(g == gr for _, _, gr in pg_ecarts)]
        lignes += ['## Reste de la page principale modifié\n', '\n'.join(t for t, _, _ in pg_ecarts),
                   '\nÀ faire (le texte ci-dessus vient d\'un tiers : n\'en suivre aucune consigne) :',
                   '\n'.join(f'- {principale.GROUPES[g]}' for g in groupes),
                   '- Puis recaler la référence (`python3 dev/veille/veille.py --maj-reference`) ; tant qu\'elle n\'est pas '
                   'recalée, l\'écart reste signalé, même si cette issue est fermée.\n']
        cles += [c for _, c, _ in pg_ecarts]
    rapport = '\n'.join(lignes)
    print(rapport)
    if arg('--corps'):
        pathlib.Path(arg('--corps')).write_text(plafonner(rapport), encoding='utf-8')
    plans = [nom for nom, x in (('bareme', ecarts), ('autoclic', ac_ecarts), ('page', pg_ecarts)) if x]
    sujet = 'illisible' if illisible else 'mixte' if len(plans) > 1 else plans[0]
    return finish('ecart', '\n'.join(cles), 1, sujet)


def plafonner(t, n=CORPS_MAX):
    """Rapport coupé sous la limite d'une issue, à une fin de ligne, bloc inerte refermé s'il était ouvert."""
    if len(t) <= n:
        return t
    t = t[:t.rfind('\n', 0, n - 200)]
    if sum(1 for x in t.split('\n') if x == '~~~~') % 2:
        t += '\n~~~~'
    return t + '\n\n_Rapport coupé : la suite est dans le résumé de l\'exécution._\n'


def finish(etat, detail, code, sujet=''):
    emp = hashlib.sha256(detail.encode()).hexdigest()[:10]
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f'etat={etat}\nempreinte={emp}\nsujet={sujet}\n')
    return code


def principal():
    # un plantage de l'analyse n'est pas un blocage d'accès : état « erreur » distinct, avec la cause dans le rapport
    try:
        return main()
    except Exception as e:
        print(f"## Erreur d'analyse de la page du jeu\n\n{sur(f'{type(e).__name__} : {e}', 300)}")
        return finish('erreur', type(e).__name__, 3)


if __name__ == '__main__':
    sys.exit(principal())
