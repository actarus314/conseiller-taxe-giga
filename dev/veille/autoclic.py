"""Détection d'autoclic du jeu, telle que la page la porte : ce que la veille en suit.

Trois filets, comparés à la section « autoclic » de dev/veille/reference.json :
- zones de code : corps entiers de fonctions nommées (ZONES), et chaque instruction, où qu'elle soit, qui lit un champ
  de détection (.acXxx, .autoclick) ou la garde des clics (isTrusted, appels de oneShot) ;
- inventaires : champs de détection lus, fenêtres de la page (id), texte des fenêtres d'autoclic et des diapositives
  des nouveautés qui en parlent ;
- balayage : chaque chaîne du code et chaque texte de la page, hors des deux filets précédents, qui contient un mot-clé.
Tout est comparé normalisé (commentaires retirés, blancs réduits, échappements des chaînes décodés) : un reformatage
ne déclenche rien. Une zone introuvable ou un code que le lecteur ne sait pas lire est un écart, jamais un silence.

Le lecteur est volontairement petit (pas d'analyseur JS, pas de Node dans le job de veille) : chaînes, gabarits ${…},
commentaires et expressions régulières littérales. Il ne vise que du code lisible par un humain ; une page minifiée
le mettrait en défaut, et la veille le dirait (écart).
"""
import bisect, html.parser, re

ZONES = ('durWarn', 'acNotice', 'acShow', 'acPick', 'acWarnShow', 'acWarnClose', 'oneShot')
FENETRES_TEXTE = ('acOv', 'durOv', 'acWarnOv')
# champs de détection : convention du jeu (et du bot, qui s'arrête sur tout champ « ac » + majuscule non vide),
# lus par un point (d.acDur) ou par crochets à chaîne littérale (d['acDur'])
CHAMP = re.compile(r'\.(ac[A-Z][\w$]*|autoclick)\b|\[\s*([\'"`])(ac[A-Z][\w$]*|autoclick)\2\s*\]')
# … ou par déstructuration dans une déclaration (const { acDur, autoclick: x } = d), lue sur le découpage du script :
# accolades appariées dans le code seul, commentaires et chaînes déjà délimités (_destructurations)
DESTRUCT = re.compile(r'\b(?:const|let|var)\s*\{')
NOM_CHAMP = re.compile(r'(?:^|,)\s*([\'"]?)(ac[A-Z][\w$]*|autoclick)\1\s*(?=[,:=]|$)')  # clé, pas nom local
# instructions suivies : champ lu, garde des clics, clé du choix gardé, minuteries des fenêtres d'autoclic
INSTR = re.compile(r'\.(?:ac[A-Z][\w$]*|autoclick)\b|\[\s*([\'"`])(?:ac[A-Z][\w$]*|autoclick)\1\s*\]|\bisTrusted\b'
                   r'|(?<!function )\boneShot\s*\(|\bAC_KEY\b|\b(?:setInterval|setTimeout)\s*\(\s*(?:ac[A-Z][\w$]*|durWarn)\b')
# envois au serveur qui portent la méthode de clic d'un joueur averti (adresse dans une chaîne)
ROUTES = re.compile(r'/api/feedback\b')
# fenêtre créée par le script sans HTML dans une chaîne : role posé par setAttribute, ou élément <dialog> créé
ROLE = re.compile(r'([\w$]+)\.setAttribute\(\s*([\'"])role\2\s*,\s*([\'"])dialog\3\s*\)|\bcreateElement\(\s*([\'"])dialog\4\s*\)')
MOTS = re.compile(r'auto-?cli(?:c|ck)|trich(?!e du compteur)|sans (?:la moindre |aucune )?pause|des pauses|sous surveillance'
                  r'|comportement anormal', re.I)
AVANT_REGEX = set('(,=:[!&|?{};+-*%~^<>')
MOTS_AVANT_REGEX = {'return', 'typeof', 'case', 'do', 'else', 'in', 'of', 'new', 'delete', 'void', 'throw', 'yield',
                    'await', 'instanceof'}
VIDES = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}


class Illisible(Exception):
    """Le lecteur ne sait pas lire ce code (page minifiée, syntaxe inattendue) : à signaler, jamais à taire."""


# ---------- lecteur ----------

def _fin_chaine(s, i):
    q, j, n = s[i], i + 1, len(s)
    while j < n:
        c = s[j]
        if c == '\\':
            j += 2; continue
        if c == q:
            return j + 1
        if c == '\n':
            break
        j += 1
    raise Illisible(f'chaîne non fermée (position {i})')


def _fin_expr(s, j):
    """Fin d'une expression ${…} d'un gabarit (j : juste après « ${ »)."""
    prof, n = 0, len(s)
    while j < n:
        c = s[j]
        if c in '\'"':
            j = _fin_chaine(s, j); continue
        if c == '`':
            j = _fin_gabarit(s, j); continue
        if c == '{':
            prof += 1
        elif c == '}':
            if not prof:
                return j + 1
            prof -= 1
        j += 1
    raise Illisible(f'expression de gabarit non fermée (position {j})')


def _fin_gabarit(s, i):
    j, n = i + 1, len(s)
    while j < n:
        c = s[j]
        if c == '\\':
            j += 2
        elif c == '`':
            return j + 1
        elif s.startswith('${', j):
            j = _fin_expr(s, j + 2)
        else:
            j += 1
    raise Illisible(f'gabarit non fermé (position {i})')


def _fin_regex(s, i):
    j, n, classe = i + 1, len(s), False
    while j < n:
        c = s[j]
        if c == '\\':
            j += 2; continue
        if c == '\n':
            break
        if classe:
            classe = c != ']'
        elif c == '[':
            classe = True
        elif c == '/':
            j += 1
            while j < n and (s[j].isalnum() or s[j] in '_$'):
                j += 1
            return j
        j += 1
    raise Illisible(f'expression régulière non fermée (position {i})')


def lire(s):
    """Découpe un script en morceaux (genre, début, fin) : code, chaine (gabarits compris), com, regex."""
    morceaux, i, n, a, prec, mot = [], 0, len(s), 0, '', ''

    def code_jusqua(j):
        if j > a:
            morceaux.append(('code', a, j))
    while i < n:
        c = s[i]
        if c in '\'"`' or s.startswith('//', i) or s.startswith('/*', i) or (
                c == '/' and (prec == '' or prec in AVANT_REGEX or mot in MOTS_AVANT_REGEX)):
            code_jusqua(i)
            if c in '\'"':
                j, genre = _fin_chaine(s, i), 'chaine'
            elif c == '`':
                j, genre = _fin_gabarit(s, i), 'chaine'
            elif s.startswith('//', i):
                j = s.find('\n', i); j, genre = (n if j < 0 else j), 'com'
            elif s.startswith('/*', i):
                j = s.find('*/', i + 2)
                if j < 0:
                    raise Illisible(f'commentaire non fermé (position {i})')
                j, genre = j + 2, 'com'
            else:
                j, genre = _fin_regex(s, i), 'regex'
            morceaux.append((genre, i, j))
            if genre != 'com':
                prec, mot = 'a', ''
            i = a = j
            continue
        if c.isspace():
            i += 1; continue
        if c.isalnum() or c in '_$':
            j = i
            while j < n and (s[j].isalnum() or s[j] in '_$'):
                j += 1
            mot, prec, i = s[i:j], 'a', j
            continue
        # après ++ ou -- (opérande déjà lue), un / est une division, pas une expression régulière
        prec = 'a' if c in '+-' and s[i - 1:i] == c and prec == c else c
        mot = ''
        i += 1
    code_jusqua(n)
    return morceaux


class Script:
    """Un bloc <script> lu : morceaux, et pour chaque {}()[]; du code la pile des parenthèses qui le suit."""

    def __init__(self, s):
        self.s = s
        self.m = lire(s)
        self.debuts = [d for _, d, _ in self.m]
        self.marques = []  # (position, caractère, hauteur de pile après, niveau de bloc après)
        pile = []
        for genre, d, f in self.m:
            if genre != 'code':
                continue
            for k in range(d, f):
                c = s[k]
                if c in '{([':
                    pile.append(c)
                elif c in '})]':
                    if not pile or pile[-1] != {'}': '{', ')': '(', ']': '['}[c]:
                        raise Illisible(f'« {c} » sans ouvrant (position {k})')
                    pile.pop()
                elif c != ';':
                    continue
                niv = max((x + 1 for x, p in enumerate(pile) if p == '{'), default=0)
                self.marques.append((k, c, len(pile), niv))
        if pile:
            raise Illisible('parenthèses ou accolades non fermées en fin de script')
        self.pos = [k for k, *_ in self.marques]

    def genre(self, p):
        x = bisect.bisect_right(self.debuts, p) - 1
        return self.m[x][0] if x >= 0 and p < self.m[x][2] else 'code'

    def dans_code(self, rx):
        """Correspondances dans le code, ou dans un gabarit (ses expressions ${…} sont du code : approximation)."""
        return [m for m in rx.finditer(self.s) if self.genre(m.start()) == 'code' or self.dans_gabarit(m.start())]

    def dans_gabarit(self, p):
        x = bisect.bisect_right(self.debuts, p) - 1
        return x >= 0 and self.m[x][0] == 'chaine' and self.s[self.m[x][1]] == '`' and p < self.m[x][2]

    def _suite(self, k):
        return re.match(r'\s*(else|catch|finally)\b', self.s[k:]) is not None

    def instruction(self, p):
        """(début, fin) de l'instruction qui contient la position p, chaîne if…else comprise."""
        t0 = bisect.bisect_left(self.pos, p) - 1
        L = self.marques[t0][3] if t0 >= 0 else 0  # niveau de bloc de l'instruction
        debut = 0
        for t in range(t0, -1, -1):
            k, c, h, v = self.marques[t]
            if c == '{' and h == L and v == L:
                debut = k + 1; break
            if c in ';}' and h == L and v == L and not self._suite(k + 1):
                debut = k + 1; break
        fin = len(self.s)
        for t in range(t0 + 1, len(self.marques)):
            k, c, h, v = self.marques[t]
            if c == '}' and h < L:
                fin = k; break
            if c == ';' and h == L and v == L and not self._suite(k + 1):
                fin = k + 1; break
            if c == '}' and h == L and v == L and not self._suite(k + 1) \
                    and not re.match(r'\s*[),.;\]?:]', self.s[k + 1:]):
                fin = k + 1; break
        return debut, fin

    def bloc(self, k):
        """Fin (exclue) du bloc qui s'ouvre sur l'accolade en position k."""
        t = bisect.bisect_left(self.pos, k)
        h0 = self.marques[t][2] - 1
        for k2, c, h, _ in self.marques[t + 1:]:
            if c == '}' and h == h0:
                return k2 + 1
        raise Illisible(f'bloc non fermé (position {k})')

    def zone(self, nom):
        """[(début, fin)] des définitions de la fonction nom (déclarée, affectée ou fléchée)."""
        n = re.escape(nom)
        rx = re.compile(rf'\bfunction\s+{n}\s*\(|(?<![\w$.]){n}\s*=\s*(?:async\s+)?(?:function\b|(?:\([^()]*\)|[\w$]+)\s*=>)')
        out = []
        for m in self.dans_code(rx):
            d = m.start() + m.group(0).index(nom) + len(nom)  # signature comprise : paramètres, « = function », flèche
            if m.group(0).startswith('function') or m.group(0).rstrip().endswith('function'):
                k = next((k for k, c, *_ in self.marques if k >= m.end() and c == '{'), None)
                if k is None:
                    continue
                out.append((d, self.bloc(k)))
            else:  # fonction fléchée : corps entre accolades, ou expression jusqu'à la fin de l'instruction
                j = m.end()
                while j < len(self.s) and self.s[j].isspace():
                    j += 1
                out.append((d, self.bloc(j)) if self.s[j:j + 1] == '{' else (d, self.instruction(j)[1]))
        return out

    def texte(self, d, f):
        """Texte normalisé de s[d:f] : commentaires retirés, blancs du code réduits, chaînes décodées."""
        out, code = [], []
        x = max(0, bisect.bisect_right(self.debuts, d) - 1)
        for genre, a, b in self.m[x:]:
            if a >= f:
                break
            a2, b2 = max(a, d), min(b, f)
            if a2 >= b2:
                continue
            if genre in ('code', 'com'):
                code.append(' ' if genre == 'com' else self.s[a2:b2])
                continue
            out.append(compacter(''.join(code))); code = []
            t = self.s[a2:b2]
            out.append(propre(decoder(t)) if genre == 'chaine' else t)
        out.append(compacter(''.join(code)))
        return ''.join(out).strip()


def decoder(t):
    """Échappements \\xHH, \\uHHHH, \\u{…} d'une chaîne rendus en clair (sauf guillemets, barre, fin de ligne)."""
    def un(m):
        c = chr(int(m.group(1) or m.group(2) or m.group(3), 16))
        return m.group(0) if c in '\'"`\\\n\r' else c
    return re.sub(r'\\x([0-9a-fA-F]{2})|\\u([0-9a-fA-F]{4})|\\u\{([0-9a-fA-F]{1,6})\}', un, t)


def compacter(t):
    """Code : blancs réduits à un espace, retirés quand ils ne séparent pas deux mots (« else if » garde le sien)."""
    t = re.sub(r'\s+', ' ', t).strip()
    return re.sub(r'(?<![\w$]) | (?![\w$])', '', t)


def propre(t):
    return re.sub(r'\s+', ' ', t).strip()


# ---------- page ----------

class _Page(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fenetres, self.textes_fen, self.diapos, self.textes = set(), {}, set(), set()
        self.brut = 0  # dans <script> ou <style>
        self.prises = []  # textes en cours de capture : [balise, profondeur, clé, morceaux]

    def handle_starttag(self, tag, attrs):
        a = {k: (v or '') for k, v in attrs}
        if tag in ('script', 'style'):
            self.brut += 1
            return
        cls = a.get('class', '').split()
        id_ = a.get('id', '')
        if tag == 'dialog' or 'bn-ov' in cls or a.get('role') == 'dialog':
            self.fenetres.add(id_ or f'{tag}.{".".join(cls)}')
        for p in self.prises:
            if p[0] == tag and tag not in VIDES:
                p[1] += 1
        if tag in VIDES:
            return
        if id_ in FENETRES_TEXTE:
            self.prises.append([tag, 1, ('fen', id_), []])
        elif 'nw-slide' in cls:
            self.prises.append([tag, 1, ('diapo', None), []])

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.brut = max(0, self.brut - 1)
            return
        for p in list(self.prises):
            if p[0] == tag:
                p[1] -= 1
                if not p[1]:
                    self.prises.remove(p)
                    t = propre(' '.join(p[3]))
                    if p[2][0] == 'fen':
                        self.textes_fen[p[2][1]] = t
                    elif MOTS.search(t):
                        self.diapos.add(t)

    def handle_data(self, data):
        if self.brut:
            return
        if self.prises:
            for p in self.prises:
                p[3].append(data)
            return
        t = propre(data)
        if t and MOTS.search(t):
            self.textes.add(t)


def scripts(page):
    """Contenu des blocs <script>. Comme un navigateur : la balise de fin peut porter des blancs ou des attributs
    (</script >, </script foo>), en majuscules ou non. Découpage pour lire, pas filtre de sécurité."""
    return [m.group(1) for m in re.finditer(r'<script\b[^>]*>(.*?)</script\b[^>]*>', page, re.S | re.I)]


def _destructurations(sc):
    """[(début, position du « = », clés)] des déclarations par déstructuration d'objet du script. Les clés sont le
    texte entre les accolades, réécrit depuis les morceaux du lecteur : code tel quel, commentaire → espace, chaîne →
    '<nom>' si elle ne contient qu'un nom de champ de détection, sinon '' (rien d'une chaîne n'est lu comme du code)."""
    out = []
    for m in DESTRUCT.finditer(sc.s):
        k = m.end() - 1
        if sc.genre(m.start()) != 'code' or sc.genre(k) != 'code':
            continue
        fin = sc.bloc(k) - 1  # accolade fermante appariée (code seul)
        j = fin + 1
        while j < len(sc.s) and (sc.s[j].isspace() or sc.genre(j) == 'com'):
            j += 1
        if sc.s[j:j + 1] != '=' or sc.s[j + 1:j + 2] in ('=', '>'):
            continue  # pas une déclaration par déstructuration (for…of, comparaison)
        cles = []
        for x in range(bisect.bisect_right(sc.debuts, k) - 1, len(sc.m)):
            genre, d, f = sc.m[x]
            if d >= fin:
                break
            d, f = max(d, k + 1), min(f, fin)
            if genre == 'code':
                cles.append(sc.s[d:f])
            elif genre == 'com':
                cles.append(' ')
            else:
                nom = sc.s[d + 1:f - 1] if f - d >= 2 and sc.s[d] in '\'"' and sc.s[f - 1] == sc.s[d] else ''
                cles.append(f"'{nom}'" if re.fullmatch(r'ac[A-Z][\w$]*|autoclick', nom) else "''")
        out.append((m.start(), j, ''.join(cles)))
    return out


def _fenetre_script(src, m):
    """Nom d'une fenêtre créée par le script (ROLE) : balise et classe de l'élément, lues à sa création
    (mk('div', 'classe') du jeu, ou createElement) dans les 3000 caractères qui précèdent."""
    if not m.group(1):
        return 'dialog (script)'
    v = re.escape(m.group(1))
    cree = list(re.finditer(rf'(?<![\w$.]){v}\s*=\s*(?:mk\(\s*([\'"])(\w+)\1\s*(?:,\s*([\'"])([\w -]*)\3)?'
                            rf'|document\.createElement\(\s*([\'"])(\w+)\5)', src[max(0, m.start() - 3000):m.start()]))
    if not cree:
        return f'{m.group(1)} (script)'
    c = cree[-1]
    balise, classe = c.group(2) or c.group(6), (c.group(4) or '').strip()
    return f'{balise}.{".".join(classe.split())} (script)' if classe else f'{balise} (script)'


def releve(page):
    """Ce que la page porte de la détection d'autoclic. Lève Illisible si un bloc de script ne se lit pas.
    Un texte déjà suivi par une règle de veille.py l'est aussi ici : un changement y fait deux écarts, jamais zéro."""
    zones = {nom: [] for nom in ZONES}
    instructions, champs, chaines, fenetres = [], set(), set(), set()  # instructions : doublons gardés
    for n, src in enumerate(scripts(page), 1):
        try:
            sc = Script(src)
        except Illisible as e:
            raise Illisible(f'bloc <script> n° {n} : {e}') from None
        pris = []  # étendues déjà suivies (zones, instructions), exclues du balayage
        for nom in ZONES:
            for d, f in sc.zone(nom):
                zones[nom].append(sc.texte(d, f)); pris.append((d, f))
        for m in sc.dans_code(CHAMP):
            champs.add(m.group(1) or m.group(3))
        for debut, egal, cles in _destructurations(sc):
            noms = [n for _, n in NOM_CHAMP.findall(cles)]
            champs.update(noms)
            if noms and not any(d <= debut < f for d, f in pris):
                # déclaration entière : du mot-clé à la fin de l'instruction qui suit le « = » (les accolades de la
                # déstructuration ne sont pas un bloc)
                d, f = debut, sc.instruction(egal + 1)[1]
                instructions.append(sc.texte(d, f)); pris.append((d, f))
        routes = [d for genre, d, f in sc.m if genre == 'chaine' and ROUTES.search(src[d:f])]
        for p in sorted([m.start() for m in sc.dans_code(INSTR)] + routes):
            if any(d <= p < f for d, f in pris):
                continue
            d, f = sc.instruction(p)
            instructions.append(sc.texte(d, f)); pris.append((d, f))
        for m in sc.dans_code(ROLE):
            fenetres.add(_fenetre_script(src, m))
        for genre, d, f in sc.m:
            # fenêtre écrite dans une chaîne (HTML injecté par le script) : son id entre dans l'inventaire
            # (attributs entre guillemets, guillemets échappés ou apostrophes ; createElement n'est pas vu)
            if genre == 'chaine' and re.search(r'class=\\?["\'][^"\']*\bbn-ov\b|role=\\?["\']dialog|<dialog\b', src[d:f]):
                fenetres |= set(re.findall(r'id=\\?["\']([\w-]{1,60})', src[d:f])) or {'fenêtre sans id (script)'}
            if genre == 'chaine' and not any(a <= d < b for a, b in pris):
                t = propre(decoder(src[d + 1:f - 1]))
                if MOTS.search(t):
                    chaines.add(t)
    p = _Page()
    p.feed(page); p.close()
    textes = sorted(chaines | p.textes)
    return {
        'zones': {nom: (' | '.join(sorted(set(v))) if v else None) for nom, v in zones.items()},
        'instructions': sorted(instructions),
        'champs': sorted(champs),
        'fenetres': sorted(p.fenetres | fenetres),
        'textes des fenetres': {k: p.textes_fen.get(k) for k in FENETRES_TEXTE},
        'diapositives': sorted(p.diapos),
        'textes': textes,
    }


def manques(r):
    """Ce qu'une référence ne doit jamais enregistrer comme vide."""
    out = [f'zone {k}' for k, v in r['zones'].items() if v is None]
    out += [f'fenêtre {k}' for k, v in r['textes des fenetres'].items() if v is None]
    if not r['champs']:
        out.append('champs de détection')
    return out
