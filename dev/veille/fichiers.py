"""Fichiers à part du jeu : modules du boss et du globe, page /regles. Ce que la veille en suit, et quand elle les lit.

Chacun demande des requêtes de plus au site. Quand (décision de Romain du 20/11/2026, mesures dans `dev/contexte.md`) :
- module du boss : à chaque passage tant que sa version ?v= dans la page diffère de la référence (déploiement pas encore
  recalé ; sauf après ESSAIS échecs de suite), et une fois par jour dans la plage PLAGE ;
- page /regles et module du globe : une fois par jour dans la plage PLAGE ; le globe tant que SUIVI_GLOBE est vrai ;
- tous à chaque envoi sur main qui touche la veille, et sur demande (lancement manuel, recalage) ;
- un fichier qui n'a pas pu être lu est relu au passage suivant (rattrapage), au plus ESSAIS fois de suite ; au-delà,
  l'échec est signalé (issue) et le fichier attend la plage du jour suivant.
Ce qui est suivi : dans chaque module, des zones de code (fonctions nommées, inventaires d'instructions) lues avec le
lecteur et la normalisation d'autoclic.py, et une empreinte du fichier entier normalisé (un changement ailleurs est vu,
sans copie du fichier) ; dans /regles, le texte de chaque section suivie, et la liste des sections.
Les noms des zones sont aussi ceux des écarts dans les rapports.
"""
import datetime, hashlib, html.parser, re

import autoclic, principale

# plage du jour (heure UTC) : 16 min, plus que l'écart entre deux passages (15,3 min mesurées le 20/11/2026), pour que
# chaque jour en ait au moins un ; juste après le lancement horaire de secours (:07), qui remet l'état à zéro, pour que
# les rattrapages (≈ 15 min chacun) tiennent avant le suivant
PLAGE = (datetime.time(3, 8), datetime.time(3, 24))
ESSAIS = 3  # échecs de suite d'un même fichier avant le signalement
SUIVI_GLOBE = True  # module du globe : suivi tant qu'il sert ; à passer à False quand il ne sert plus (décision du 20/11/2026)

# fichier → (libellé, {partie: adresse}, passage de la page qui porte sa version ?v=)
FICHIERS = {
    'boss': ('module du boss', {'boss-event-net.js': '/boss/boss-event-net.js', 'boss-site.js': '/boss/boss-site.js'},
             'version du module du boss'),
    'globe': ('module du globe', {'monde.js': '/monde/monde.js'}, 'version du module du globe'),
    'regles': ('page /regles', {'regles': '/regles'}, None),
}
RACINE = 'https://taxe-au-giga.fr'

# zones des modules : (nom, forme, motif, requise). requise : la zone ne peut pas être vide dans une référence (le
# recalage la refuse : vide, elle resterait muette ensuite). forme : 'fonction' (corps entier, signature comprise, des seules fonctions
# déclarées « function nom(…) » : un autre nom local identique, comme la flèche « var hit = function (t) » du module du
# boss, n'y entre pas ; une fonction réécrite en flèche est une zone introuvable, donc un écart), 'liste' (instructions
# entières du code et des gabarits qui contiennent le motif, doublons gardés), 'chaines' (instructions dont une chaîne
# contient le motif), 'ensemble' (mots du motif trouvés dans les chaînes, sans doublon), 'noms' (premier groupe trouvé
# du motif dans le code, doublons gardés), 'images' (comme 'liste', plus les instructions dont une chaîne est une clé qui
# contient le motif, principale.CLES_IMAGES : même relevé que le passage de la page)
_COMMUN = [
    ('écouteurs d\'événements', 'liste', r'\.addEventListener\s*\(', True),
    ('gardes isTrusted', 'liste', r'\bisTrusted\b', False),
    ('globales posées par le module', 'liste', r'\bwindow\.[\w$]+\s*=(?![=>])', False),
    ('changements de classe', 'liste', r'\.classList\.(?:add|remove|toggle|replace)\s*\(|\.className\s*[+]?=(?!=)', False),
    ('clés du stockage du jeu (taxe-giga-…)', 'chaines', r'\btaxe-giga-[\w-]+', False),
    ('mesure du rythme des images (fps, fréquence)', 'images', principale.MOTS_IMAGES, False),
]
ZONES = {
    # les gardes isTrusted sont des contrôles propres au module du boss : requises dans boss-event-net.js
    'boss-event-net.js': [z[:3] + (True,) if z[0] == 'gardes isTrusted' else z for z in _COMMUN] + [
        ('constantes du combat (déclaration de CAP et CAP3)', 'liste', r'\bCAP3?\s*=(?![=>])', True),
        ('racine de la scène (attachShadow)', 'liste', r'\battachShadow\s*\(', True),
        ('compte et refus des coups (gate)', 'fonction', 'gate', True),
        ('coup sur le boss (hit)', 'fonction', 'hit', True),
        ('coups sur une travée (clickSquad)', 'fonction', 'clickSquad', True),
        ('super (launchSuper)', 'fonction', 'launchSuper', True),
        ('fermeture de la scène (closeFocus)', 'fonction', 'closeFocus', True),
        ('interface rendue par le montage (me, probe, state, close)', 'liste', r'\bprobe\s*:', True),
        ('gabarit HTML de la scène', 'liste', r'\bvar\s+HTML\s*=', True),
        ('textes écrits dans la scène', 'liste', r'\.(?:textContent|innerText)\s*[+]?=(?!=)', True),
    ],
    'boss-site.js': _COMMUN + [
        ('contrat de la page (TaxeBoss, BOSS_SERVER)', 'liste', r'\b(?:TaxeBoss|BOSS_SERVER)\b|\bT\.[\w$]+\s*\(', True),
        ('montage de la scène (BossEvent.mount)', 'liste', r'\bBossEvent\.mount\s*\(', True),
        ('hôte de la scène', 'chaines', r'bossHost', True),
    ],
    'monde.js': _COMMUN + [
        ('noms exportés par le module', 'noms', r'(?<![\w$.])export\s+(?:default\s+)?(?:async\s+)?(?:function\*?|const|let|var|class)\s+([\w$]+)|(?<![\w$.])export\s*(\{[^}]*\})', True),
        ('lancement libre (launchFree)', 'fonction', 'launchFree', True),
        ('voyage libre (goFree)', 'fonction', 'goFree', True),
        ('stockage du navigateur', 'liste', r'\b(?:localStorage|sessionStorage)\b', True),
        ('envois au serveur', 'liste', r'\bfetch\s*\(|\bsendBeacon\s*\(|\benvoisUrl\b', True),
        ('fenêtre du globe (role, aria-label)', 'chaines', r'aria-label|\bdialog\b', True),
        ('classes de la fenêtre (mw, mw-…)', 'ensemble', r'(?<![\w-])mw(?:-[\w-]+)?(?![\w-])', True),
        ('boutons de la fenêtre (btn)', 'liste', r'(?<![\w$.])btn\s*\(', True),
        ('éléments créés par le module (mk, createElement)', 'liste', r'(?<![\w$.])mk\s*\(|\.createElement\s*\(', True),
        ('structure écrite dans la fenêtre (innerHTML)', 'liste', r'\.innerHTML\s*[+]?=(?!=)', True),
        ('textes écrits dans la fenêtre', 'liste', r'\.(?:textContent|innerText|placeholder)\s*[+]?=(?!=)', True),
    ],
}
# sections suivies de /regles (texte entier) ; #reprise n'est pas suivie (gabarit de code de compte)
SECTIONS = ('resume', 'limites', 'autoclick', 'appel', 'faq')


class Illisible(Exception):
    """Fichier reçu, mais que la veille ne sait pas lire (code restructuré ou minifié) : à signaler, jamais à taire."""


# ---------- lecture ----------

def _declarees(sc, nom):
    """[(début, fin)] des fonctions déclarées « function nom(…) { … } » (signature comprise), dans le code."""
    out = []
    for m in sc.dans_code(re.compile(rf'\bfunction\s*\*?\s*{re.escape(nom)}\s*\(')):
        k = next((k for k, c, *_ in sc.marques if k >= m.end() and c == '{'), None)
        if k is not None:
            out.append((m.start() + m.group(0).index(nom) + len(nom), sc.bloc(k)))
    return out


def releve_module(nom, src):
    """{'zones': {nom de zone: texte | liste | None}, 'empreinte': …} d'une partie d'un module."""
    try:
        sc = autoclic.Script(src)
    except autoclic.Illisible as e:
        raise Illisible(f'{nom} : {e}') from None
    zones = {}
    for zn, forme, motif, _ in ZONES[nom]:
        if forme == 'fonction':
            v = [sc.texte(d, f) for d, f in _declarees(sc, motif)]
            zones[zn] = ' | '.join(sorted(set(v))) if v else None
        elif forme == 'ensemble':
            rx = re.compile(motif)
            zones[zn] = sorted({m.group(0) for g, d, f in sc.m if g == 'chaine' for m in rx.finditer(src, d, f)})
        elif forme == 'noms':  # noms seuls (pas le corps des fonctions exportées), lus dans le code
            zones[zn] = sorted(autoclic.compacter(next(g for g in m.groups() if g)) for m in sc.dans_code(re.compile(motif)))
        elif forme == 'images':
            zones[zn] = sorted(principale._instructions(sc, re.compile(motif))
                               + principale._instructions(sc, re.compile(principale.CLES_IMAGES), chaines=True))
        else:
            zones[zn] = sorted(principale._instructions(sc, re.compile(motif), chaines=forme == 'chaines'))
    return {'zones': zones, 'empreinte': hashlib.sha256(sc.texte(0, len(src)).encode()).hexdigest()[:16]}


class _Regles(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections, self.ids, self.prises, self.brut = {}, [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.brut += 1
            return
        if tag in autoclic.VIDES:
            return
        for p in self.prises:
            if p[0] == tag:
                p[1] += 1
        id_ = dict(attrs).get('id') or ''
        if tag == 'section':
            self.ids.append(id_ or '(sans id)')
            if id_ in SECTIONS:
                self.prises.append([tag, 1, id_, []])

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.brut = max(0, self.brut - 1)
            return
        for p in list(self.prises):
            if p[0] == tag:
                p[1] -= 1
                if not p[1]:
                    self.prises.remove(p)
                    texte = autoclic.propre(' '.join(p[3]))
                    self.sections[p[2]] = texte if p[2] not in self.sections else self.sections[p[2]] + ' | ' + texte

    def handle_data(self, data):
        if not self.brut:
            for p in self.prises:
                p[3].append(data)


def releve_regles(page):
    p = _Regles()
    p.feed(page); p.close()
    return {'sections': {k: p.sections.get(k) for k in SECTIONS}, 'liste des sections': sorted(p.ids)}


def releve(cle, textes):
    """Relevé d'un fichier à partir du texte de chacune de ses parties. Lève Illisible."""
    if cle == 'regles':
        return releve_regles(textes['regles'])
    return {partie: releve_module(partie, textes[partie]) for partie in FICHIERS[cle][1]}


def manques(cle, r):
    """Ce qu'une référence ne doit jamais enregistrer comme absent."""
    if cle == 'regles':
        out = [f'/regles : section #{k}' for k, v in r['sections'].items() if v is None]
        return out + ([] if r['liste des sections'] else ['/regles : aucune section'])
    out = []
    for partie, rp in r.items():
        for zn, _, _, requise in ZONES[partie]:
            v = rp['zones'].get(zn)
            if v is None or (requise and not v):
                out.append(f'{partie} : {zn}')
    return out


# ---------- quand lire ----------

def rattrapage_lu(s):
    """« boss:1,regles:2 » → {'boss': 1, 'regles': 2} ; toute autre forme est ignorée (entrée du lancement)."""
    out = {}
    for x in (s or '').split(','):
        m = re.fullmatch(r'\s*(boss|globe|regles):([1-9])\s*', x)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def rattrapage_ecrit(r):
    return ','.join(f'{k}:{v}' for k, v in sorted(r.items()) if v)


def dans_plage(maintenant):
    t = maintenant.astimezone(datetime.timezone.utc).time()
    return PLAGE[0] <= t < PLAGE[1]


def a_lire(maintenant, tous, rattrapage, version_page, version_ref):
    """{fichier: raison} des fichiers à télécharger ce passage."""
    suivis = [k for k in FICHIERS if k != 'globe' or SUIVI_GLOBE]
    if tous:
        return {k: 'demandé' for k in suivis}
    out = {}
    if dans_plage(maintenant):
        out = {k: 'plage du jour' for k in suivis}
    # ni l'un ni l'autre au-delà de ESSAIS échecs de suite : le fichier attend alors la plage du jour suivant
    if version_page and version_ref and version_page != version_ref and rattrapage.get('boss', 0) < ESSAIS:
        out.setdefault('boss', 'version ?v= différente de la référence')
    for k, n in rattrapage.items():
        if k in suivis and n < ESSAIS:
            out.setdefault(k, f'rattrapage (échec {n} de suite)')
    return out


def adresses(cle, versions):
    """[(partie, adresse complète)] ; la version ?v= lue dans la page quand elle a une forme sûre."""
    v = versions.get(cle)
    q = f'?v={v}' if v and re.fullmatch(r'[\w.-]{1,40}', v) else ''
    return [(partie, RACINE + chemin + q) for partie, chemin in FICHIERS[cle][1].items()]


# ---------- comparaison ----------

def ecarts(cle, avant, apres, difference, changements, retires_ajoutes):
    """[(affichage, clé complète)] des écarts d'un fichier (avant : référence, ou None)."""
    import json
    out = []

    def ecart(texte, *c):
        out.append((texte, json.dumps(['fichiers', cle, *c], ensure_ascii=False, sort_keys=True)))
    libelle = FICHIERS[cle][0]
    if avant is None:
        ecart(f'- Référence sans suivi du {libelle} : à recaler.', 'reference-sans')
        return out
    if cle == 'regles':
        for k in SECTIONS:
            x, y = avant['sections'].get(k), apres['sections'].get(k)
            if x != y:
                ecart(f'- /regles, section **#{k}** ' + ('introuvable (retirée ou renommée).' if y is None else f'modifiée.\n{difference(x, y)}'),
                      'section', k, x, y)
        x, y = sorted(avant['liste des sections']), sorted(apres['liste des sections'])
        if x != y:
            ecart('\n'.join(['- /regles, liste des sections :'] + changements(*retires_ajoutes(x, y))), 'sections', x, y)
        return out
    for partie in FICHIERS[cle][1]:
        ra, rb = avant.get(partie), apres[partie]
        if ra is None:
            ecart(f'- {partie} : absent de la référence, à recaler.', partie, 'reference-sans')
            continue
        vu = False
        for zn, forme, _, _ in ZONES[partie]:
            x, y = ra['zones'].get(zn), rb['zones'].get(zn)
            if forme == 'fonction':
                if x == y:
                    continue
                texte = f'- {partie}, **{zn}** ' + ('introuvable (renommée, retirée ou restructurée).' if y is None else f'modifiée.\n{difference(x, y)}')
            else:
                x, y = sorted(x or []), sorted(y or [])
                if x == y:
                    continue
                texte = '\n'.join([f'- {partie}, **{zn}** :'] + changements(*retires_ajoutes(x, y)))
            vu = True
            ecart(texte, partie, zn, x, y)
        if ra.get('empreinte') != rb['empreinte'] and not vu:
            ecart(f'- {partie} : modifié hors des zones suivies (empreinte `{ra.get("empreinte")}` → `{rb["empreinte"]}`) ; '
                  'relire le fichier lui-même pour savoir quoi.', partie, 'empreinte', ra.get('empreinte'), rb['empreinte'])
        elif ra.get('empreinte') != rb['empreinte']:
            ecart(f'- {partie} : empreinte du fichier entier changée aussi (`{ra.get("empreinte")}` → `{rb["empreinte"]}`), '
                  'un changement hors des zones suivies n\'est pas exclu.', partie, 'empreinte', ra.get('empreinte'), rb['empreinte'])
    return out
