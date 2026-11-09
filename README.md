# Conseiller — Taxe au Giga

Panneau posé sur la page de [Taxe au Giga](https://taxe-au-giga.fr/) qui surligne le bonus à acheter, avec le compte à rebours jusqu'au prochain achat et les sept suivants.

Il lit ce que le jeu affiche. **Aucun clic, aucun achat, aucun appel au serveur du jeu.**

[![Ouvrir la page d'installation](https://img.shields.io/badge/Ouvrir_la_page_d%27installation_%E2%86%97-19d3a2?style=for-the-badge)](https://actarus314.github.io/conseiller-taxe-giga/)

![Conseil en mode Passif : Satellite à acheter, suite des achats prévue](captures/passif.png)

| Mode Auto, pendant une série de clics | Téléphone |
|---|---|
| ![Mode Auto pendant une série de clics, colonne En direct ; moyenne de 0.51 clic/s sur 2 h : Tampon à acheter](captures/auto-clics.png) | ![Panneau réduit sur téléphone](captures/mobile.png) |

## Modes

| Mode | Cadence de clic prise en compte |
|---|---|
| **Auto** (défaut) | moyenne des clics TAXER sur les 3 dernières heures de présence (cherchées sur 24 h, comptées sur 30 min au moins) ; au-delà d'1 h sans clic, c'est une absence, écartée de la moyenne : au retour d'une nuit, le conseil repart sur la cadence d'avant ; aucun clic sur 24 h : conseil passif |
| Passif | aucune : seule la production automatique compte |
| Actif | fixée à la main dans les détails (5 clics/s par défaut), ouverts d'office en Actif tant qu'ils n'ont été ni ouverts ni fermés à la main |

Dans tous les cas, la cadence retenue reste sous 1030 clics par minute (17.2/s), et le reste du quota de 24000 clics par heure se répartit sur 15 min quand il ne suffit plus. Les clics sont comptés minute par minute dans le navigateur ; les minutes où le panneau était fermé ne comptent ni dans les clics ni dans la durée de la moyenne. Seuil d'1 h choisi par simulation ([`dev/sim/presence.py`](dev/sim/presence.py)). Les clics du mode mini du jeu comptent aussi : toujours dans la fenêtre « image dans l'image » de Chrome et Edge, et dans la fenêtre séparée des autres navigateurs si elle s'ouvre panneau ouvert.

## Installation

- **Script utilisateur** (Tampermonkey, Violentmonkey) : ouvrir [`conseiller.user.js`](https://raw.githubusercontent.com/actarus314/conseiller-taxe-giga/main/conseiller.user.js), l'extension propose l'installation. Le panneau s'ouvre à chaque visite du jeu.
- **Favori à jour** (conseillé) : glisser le bouton vert de la [page d'installation](https://actarus314.github.io/conseiller-taxe-giga/) dans la barre de favoris, ou créer un favori dont l'adresse est le contenu de [`bookmarklet-auto.txt`](bookmarklet-auto.txt). Il charge `conseiller.js` depuis GitHub Pages à chaque clic : une nouvelle version arrive quelques minutes après sa publication (déploiement de Pages, puis une minute de cache au plus).
- **Favori figé** : le contenu de [`bookmarklet.txt`](bookmarklet.txt), avec le code entier dans l'adresse ; rien n'est chargé à distance, mais il faut le refaire à chaque nouvelle version.

Un clic sur le favori ouvre le panneau, un second le ferme. Le panneau se place de lui-même hors du grand bouton TAXER ; production en bleu, clic en rose (boutons Passif et Actif, barre à gauche de chaque achat) ; glissé par son en-tête, il garde la place choisie. En bas : production automatique (réelle), apport des clics à la cadence retenue (moyenne mesurée en Auto, prévue en Actif) et cagnotte ; pendant une série de clics (Auto, Actif), la colonne des clics passe en direct ; Facture dorée et Rafale ont un bandeau jaune sous l'en-tête, Frénésie, bonus du Dépité, événements du jeu et limites de clics une alerte en bas ; un signal sonore, à cocher dans les détails, prévient de l'apparition d'une Facture dorée (puis rappel toutes les 3 s tant qu'elle est à l'écran) et du début d'un événement du jeu (le jeu ne montre la facture que si son onglet est visible à l'écran) ; la flèche ▾ déplie le revenu sur lequel le plan est calculé (production + clics) et la moyenne. Sur téléphone, le panneau s'ouvre réduit au conseil ; le bouton « – » le déplie.

## Modèle

- Prix d'un bonus : arrondi supérieur de `base × 1.15^possédés`.
- Visites par clic : `floor(1 + Σ bonus de clic + (0.01 + Σ bonus en %) × production/s)`.
- Choix : le bonus qui minimise *attente avant de pouvoir le payer* + *temps pour qu'il se rembourse*.
- Bonus temporaires comptés pour leur durée : Frénésie (production +200 %), Rafale (clics ×10) événements du jeu (production ×2 pendant quelques heures, par exemple) et bonus d'après-combat du Dépité (clics ×1,5 à ×2,5), lus sur l'indicateur du jeu.

Barème recopié du code du jeu (build 2026-11-04e, inchangé jusqu'au build 2026-11-09a). Une alerte rose apparaît si un prix ou la puissance de clic affichés ne correspondent plus.

## Développement

- `conseiller.js` est la seule source ; `python3 dev/outils/build.py <version>` génère `conseiller.user.js`, `bookmarklet-auto.txt`, `bookmarklet.txt` (code compressé par terser : `npm ci` dans `dev/tests` d'abord) et `index.html`.
- Tests : `cd dev/tests && npm install && npm test`.
- Simulateur des stratégies : `python3 dev/sim/modele.py <clics par seconde>`.
- Captures : `dev/outils/captures.py` (mode d'emploi en tête du fichier).
- Contrôles à chaque envoi et sur chaque demande de fusion : tests (dont garde-fous de performance), actionlint et zizmor sur les workflows, ruff sur les scripts Python. CodeQL analyse le code, Dependabot propose chaque mois les mises à jour des actions et des dépendances de test. Signaler une faille : voir [SECURITY.md](SECURITY.md).
- Veille : en continu, relancée après le délai de l'environnement `attente-veille`, [`dev/veille/veille.py`](dev/veille/veille.py) compare le barème et les règles du jeu à ceux du conseiller ([workflow](.github/workflows/veille.yml)). Écart : une issue étiquetée `veille`, refermée d'elle-même au retour à la normale. Page inaccessible (le site bloque parfois les robots quand son trafic monte) : un seul essai, la relance suivante est sautée sans requête au site, et l'issue n'est ouverte qu'au deuxième échec de suite. Après une mise à jour du conseiller : `python3 dev/veille/veille.py --maj-reference`.
