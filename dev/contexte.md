# Contexte — Conseiller Taxe au Giga

- **Objet** : surcouche pour taxe-au-giga.fr (jeu incrémental satirique) qui indique le bonus à acheter. Lit l'affichage du jeu ; aucun clic, aucun achat, aucun appel au serveur du jeu.
- **Source du code** : `conseiller.js`. `conseiller.user.js`, `bookmarklet.txt` et `index.html` sont générés par `dev/outils/build.py <version>`.
- **Barème** : recopié du code du jeu (build 2026-11-03e). Prix = arrondi_sup(base × 1.15^possédés). Visites par clic = floor(1 + Σ bonus de clic + (0.01 + Σ pct) × production/s), vérifié contre la valeur du serveur (5770 et 13099 sur la partie de Romain).
- **Limites serveur** : 760 clics/min et 18000 clics/h comptés ; autoclic détecté (plafond tenu 3 min) puis clics ignorés 10 min.
- **Règle de choix** : minimiser attente avant paiement + prix ÷ gain. Comparée par `dev/sim/modele.py` à prix ÷ gain seul et à une variante Cookie Clicker : meilleure ou à égalité sur 1 h à 7 jours.
- **Pourquoi une surcouche** : l'API du jeu (api.taxe-au-giga.fr) n'autorise pas les autres origines (aucun en-tête CORS), une page séparée ne peut pas la lire.
- **Identité visuelle** : celle du jeu (crème, encre noire, ombre portée pleine, vert #19d3a2 pour l'action).
- **Tests** : `dev/tests` (`npm test`, jsdom) sur des états simulés au format exact du jeu.
- **Si le jeu change** : le panneau passe une alerte rose quand un prix ou la puissance de clic ne correspondent plus ; relire le tableau `SHOP` du jeu et mettre à jour `P` dans `conseiller.js`.
