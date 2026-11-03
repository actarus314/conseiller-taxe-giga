# Conseiller — Taxe au Giga

Panneau posé sur la page de [Taxe au Giga](https://taxe-au-giga.fr/) qui surligne le bonus à acheter, avec le compte à rebours jusqu'au prochain achat et les huit suivants.

Il lit ce que le jeu affiche. **Aucun clic, aucun achat, aucun appel au serveur du jeu.**

## Installation

- **Script utilisateur** (Tampermonkey, Violentmonkey) : ouvrir [`conseiller.user.js`](https://raw.githubusercontent.com/actarus314/conseiller-taxe-giga/main/conseiller.user.js), l'extension propose l'installation. Le panneau s'ouvre à chaque visite du jeu.
- **Favori** : créer un favori dont l'adresse est le contenu de [`bookmarklet.txt`](bookmarklet.txt), puis le cliquer sur la page du jeu. Un second clic ferme le panneau.

## Modèle

- Prix d'un bonus : arrondi supérieur de `base × 1.15^possédés`.
- Visites par clic : `floor(1 + Σ bonus de clic + (0.01 + Σ bonus en %) × production/s)`.
- Choix : le bonus qui minimise *attente avant de pouvoir le payer* + *temps pour qu'il se rembourse*.
- Le serveur ne compte que 760 clics par minute et 18000 par heure.

Barème recopié du code du jeu (build 2026-11-03e). Une alerte rose apparaît si un prix ou la puissance de clic affichés ne correspondent plus.

## Développement

- `conseiller.js` est la seule source ; `python3 dev/outils/build.py <version>` génère `conseiller.user.js`, `bookmarklet.txt` et `index.html`.
- Tests : `cd dev/tests && npm install && npm test`.
- Simulateur des stratégies : `python3 dev/sim/modele.py <clics par seconde>`.
