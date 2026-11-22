"""Le reste de la page principale du jeu : ce que la veille en suit, hors barème, règles et détection d'autoclic.

Passages comparés à la section « page » de dev/veille/reference.json, avec la normalisation et le lecteur d'autoclic.py
(aucune requête de plus : tout est lu dans la page déjà téléchargée). Deux formes :
- passage ancré (texte, ou None quand son ancre a disparu : un écart, jamais un silence) ;
- inventaire (liste d'instructions, vide permis) : ce qui apparaît ou disparaît ailleurs dans la page est vu.
Les noms des passages (PASSAGES) sont aussi ceux des écarts dans les rapports ; GROUPES dit ce que chacun touche.
"""
import bisect, re

import autoclic

# nom du passage → (groupe, forme : 'texte' ou 'liste')
PASSAGES = {
    'cadence() (régularité envoyée au serveur)': ('cad', 'texte'),
    'taxHit() (horodatage des clics)': ('cad', 'texte'),
    'origine des horodatages de clickTimes': ('cad', 'liste'),
    'synchro, jusqu\'à son envoi (flush)': ('sync', 'texte'),
    'envoi de fermeture (beacon)': ('sync', 'texte'),
    'cardFlags() (champs ajoutés à la synchro)': ('sync', 'texte'),
    'autres envois à /api/sync': ('sync', 'liste'),
    'taxerName() (règle des pseudos)': ('pseudos', 'texte'),
    'tables NOUNS et ADJS (règle des pseudos)': ('pseudos', 'liste'),
    'chargeur du module du boss': ('boss', 'texte'),
    'version du module du boss': ('boss', 'texte'),
    'bandeau du Dépité': ('boss', 'texte'),
    'contrat window.TaxeBoss': ('boss', 'liste'),
    'routes de classement et de fiche joueur': ('routes', 'liste'),
    'chargeur et appel du module du globe': ('globe', 'liste'),
    'version du module du globe': ('globe', 'texte'),
    'mesure du rythme des images (fps, fréquence)': ('images', 'liste'),
}
# texte de l'« à faire » de chaque groupe (fixe : jamais de texte de la page)
GROUPES = {
    'cad': 'Régularité envoyée au serveur (`cad`) ou origine de ses horodatages changée. Conséquences à vérifier : voir '
           'la documentation privée du projet, groupe `cad`.',
    'sync': 'Ce que la page envoie à `/api/sync` a changé. Un drapeau ajouté par l\'auteur est un bruit attendu ; un champ '
            'nouveau ou retiré est à comprendre avant de recaler. Conséquences à vérifier : voir la documentation privée '
            'du projet, groupe `sync`.',
    'pseudos': 'Règle des pseudos changée. Conséquences à vérifier : voir la documentation privée du projet, groupe '
               '`pseudos`.',
    'boss': 'Chargeur, bandeau ou contrat du module du boss changé (fenêtre horaire, adresses, version, calendrier, '
            '`window.TaxeBoss`). Si c\'est la version `?v=` : probablement un déploiement du module (non établi). '
            'Conséquences à vérifier : voir la documentation privée du projet, groupe `boss`.',
    'routes': 'Routes de classement ou de fiche joueur changées (version, paramètre). Conséquences à vérifier : voir la '
              'documentation privée du projet, groupe `routes`.',
    'globe': 'Chargeur ou appel du module du globe changé (version `?v=`, adresses). Conséquences à vérifier : voir la '
             'documentation privée du projet, groupe `globe`.',
    'images': 'Le code parle du rythme des images (fps, fréquence de l\'écran). Lire ce que le code en fait et s\'il '
              'l\'envoie (synchro, autre adresse). Conséquences à vérifier : voir la documentation privée du projet, '
              'groupe `images`.',
    'recalage': 'Référence sans suivi du reste de la page : la recaler sur une page relue.',
}
ANCRE_CHARGEUR = 'boss-event-net.js'
ANCRE_BANDEAU = 'bossBar'
PRINCIPAL = 'const SHOP = ['  # le bloc du jeu lui-même : jamais pris pour le chargeur ou le bandeau
# mots d'une mesure du rythme des images (demande de Romain du 20/11/2026), dans les noms du code :
# en minuscules au début d'un nom (fps, fpsMax, frame_rate, frameCounter), avec majuscule n'importe où dans un nom
# (maxFps, getFrameRate, FRAME_RATE) ; plus, en chaînes, les clés écrites entre guillemets (o['frameRate'], {"fps": 1}).
# Les textes (« 60 fps à l'écran ») ne comptent pas. Limite : une mesure sans ces mots (écarts entre deux images rangés
# dans un tableau anonyme) n'est pas vue ici ; ce que la page envoie reste suivi par le groupe « sync ».
_SUITE = r'(?:[Rr]ate|[Tt]ime|[Cc]ount|[Pp]er)'
MOTS_IMAGES = (r'(?<![a-z0-9])(?:fps|frames?_?' + _SUITE + r'|refresh_?[Rr]ate|v[Ss]ync)'
               r'|(?:F(?:ps|PS)|Frames?_?' + _SUITE + r'|FRAMES?_?(?:RATE|TIME|COUNT|PER)|Refresh_?[Rr]ate|REFRESH_?RATE|V[Ss]ync|VSYNC)')
CLES_IMAGES = r'(?<=[\'"`])[\w$]*(?:' + MOTS_IMAGES + r')[\w$]*(?=[\'"`])'


def _enonce(sc, p):
    """(début, fin) de l'énoncé entier qui contient p : comme Script.instruction, mais sans s'arrêter aux accolades
    d'un objet littéral (`api(url, { body })`, `m.play({ … })`, `x = { … }`), qui ne sont pas des blocs."""
    while True:
        k = _accolade(sc, p)
        if k is None or not _objet(sc, k):
            return sc.instruction(p)
        p = k  # dans un objet littéral : on remonte à l'énoncé qui le contient


def _accolade(sc, p):
    """Position de l'accolade ouvrante la plus proche qui contient p (parenthèses et crochets traversés), ou None."""
    prof = 0
    for t in range(bisect.bisect_left(sc.pos, p) - 1, -1, -1):
        k, c, *_ = sc.marques[t]
        if c in '})]':
            prof += 1
        elif c in '{([':
            if prof:
                prof -= 1
            elif c == '{':
                return k
    return None


def _objet(sc, k):
    """L'accolade en k ouvre-t-elle un objet littéral (et non un bloc) ? Lu au caractère qui la précède."""
    j = k - 1
    while j >= 0 and sc.s[j].isspace():
        j -= 1
    avant = sc.s[j] if j >= 0 else ''
    if avant in ('(', ',', ':', '[', '?'):
        return True
    if avant == '=':
        return sc.s[j - 1:j] not in ('=', '!', '<', '>')
    mot = re.search(r'[\w$]+$', sc.s[:j + 1])
    return mot is not None and mot.group(0) in ('return', 'yield', 'await')


def _instructions(sc, rx, hors=(), chaines=False):
    """Textes des instructions qui contiennent une correspondance de rx : dans le code (et les gabarits), ou dans les
    chaînes avec chaines=True ; jamais dans les étendues hors. Une correspondance prise dans une instruction déjà
    retenue n'en fait pas une seconde."""
    out, pris = [], list(hors)
    for m in rx.finditer(sc.s):
        p = m.start()
        genre = sc.genre(p)
        if not (genre == 'chaine' if chaines else (genre == 'code' or sc.dans_gabarit(p))):
            continue
        if any(d <= p < f for d, f in pris):
            continue
        d, f = _enonce(sc, p)
        out.append(sc.texte(d, f)); pris.append((d, f))
    return out


def _joint(v):
    return ' | '.join(sorted(set(v))) if v else None


def releve(page):
    """Passages suivis de la page. Lève autoclic.Illisible si un bloc de script ne se lit pas."""
    acc = {nom: [] for nom in PASSAGES}
    for src in autoclic.scripts(page):
        sc = autoclic.Script(src)
        z = {nom: sc.zone(nom) for nom in ('cadence', 'taxHit', 'flush', 'beacon', 'cardFlags', 'taxerName')}
        for fn, nom in (('cadence', 'cadence() (régularité envoyée au serveur)'), ('taxHit', 'taxHit() (horodatage des clics)'),
                        ('cardFlags', 'cardFlags() (champs ajoutés à la synchro)'), ('taxerName', 'taxerName() (règle des pseudos)')):
            acc[nom] += [sc.texte(d, f) for d, f in z[fn]]
        # qui remplit clickTimes, et d'où vient l'instant de chaque clic (appels de taxHit)
        acc['origine des horodatages de clickTimes'] += _instructions(
            sc, re.compile(r'\bclickTimes\b|(?<!function )\btaxHit\s*\('), hors=z['cadence'] + z['taxHit'])
        # les deux émissions vers /api/sync, chacune ancrée dans sa fonction (deux « const body » coexistent) :
        # flush depuis son début jusqu'à l'énoncé qui envoie (tout ce qui prépare le corps : flags, alive, clics, legacy),
        # beacon en entier ; la réponse lue par flush après l'envoi n'en fait pas partie
        sync = re.compile(r'/api/sync')
        emis = []
        for d, f in z['flush']:
            envoi = next((m.start() for m in sync.finditer(src, d, f) if sc.genre(m.start()) == 'chaine'), None)
            if envoi is not None:
                fin = _enonce(sc, envoi)[1]
                acc['synchro, jusqu\'à son envoi (flush)'].append(sc.texte(d, fin)); emis.append((d, fin))
        for d, f in z['beacon']:
            acc['envoi de fermeture (beacon)'].append(sc.texte(d, f)); emis.append((d, f))
        acc['autres envois à /api/sync'] += _instructions(sc, sync, hors=emis, chaines=True)
        acc['tables NOUNS et ADJS (règle des pseudos)'] += _instructions(sc, re.compile(r'\b(?:const|let|var)\s+(?:NOUNS|ADJS)\b'))
        acc['contrat window.TaxeBoss'] += _instructions(sc, re.compile(r'\bTaxeBoss\b'))  # affectation, ajouts, lectures
        acc['routes de classement et de fiche joueur'] += _instructions(sc, re.compile(r'/api/(?:leaderboard|taxer)\b'), chaines=True)
        acc['chargeur et appel du module du globe'] += _instructions(sc, re.compile(r'/monde/'), chaines=True)
        acc['mesure du rythme des images (fps, fréquence)'] += _instructions(sc, re.compile(MOTS_IMAGES))
        acc['mesure du rythme des images (fps, fréquence)'] += _instructions(sc, re.compile(CLES_IMAGES), chaines=True)
        # blocs du boss, suivis en entier ; ancrés par leur contenu (fonctions anonymes : pas de nom)
        if PRINCIPAL not in src:
            entier = sc.texte(0, len(src))
            if ANCRE_CHARGEUR in src:
                acc['chargeur du module du boss'].append(entier)
            elif ANCRE_BANDEAU in src:
                acc['bandeau du Dépité'].append(entier)
    out = {}
    for nom, (_, forme) in PASSAGES.items():
        # inventaire : doublons gardés (un second site d'appel au texte identique au premier est un changement)
        out[nom] = sorted(acc[nom]) if forme == 'liste' else _joint(acc[nom])
    # versions des modules, lues dans leur chargeur : nommées à part pour que l'issue les dise en clair
    out['version du module du boss'] = _joint(re.findall(r'\?v=([\w.-]{1,40})', out['chargeur du module du boss'] or ''))
    out['version du module du globe'] = _joint(re.findall(r'monde\.js\?v=([\w.-]{1,40})',
                                                          ' '.join(out['chargeur et appel du module du globe'])))
    return out


def manques(r):
    """Ce qu'une référence ne doit jamais enregistrer comme absent (ancre disparue, inventaire attendu vide)."""
    out = [f'passage {k}' for k, (_, forme) in PASSAGES.items() if forme == 'texte' and r.get(k) is None]
    for k in ('origine des horodatages de clickTimes', 'contrat window.TaxeBoss', 'tables NOUNS et ADJS (règle des pseudos)', 'routes de classement et de fiche joueur', 'chargeur et appel du module du globe'):
        if not r.get(k):
            out.append(f'passage {k}')
    return out
