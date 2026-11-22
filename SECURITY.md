# Sécurité

Le conseiller s'exécute dans la page de taxe-au-giga.fr, là où le jeu garde l'identifiant de partie du joueur. Une faille ou un comportement suspect se signale **en privé** : onglet *Security* du dépôt, bouton *Report a vulnerability*. Pas d'issue publique pour une faille.

Points vérifiés par l'audit du 03/11/2026 :

- le panneau n'insère jamais de texte lu dans la page du jeu comme du HTML ;
- il ne clique, n'achète et n'appelle rien auprès du serveur du jeu ;
- le favori à jour ne démarre que sur taxe-au-giga.fr ; le panneau (`conseiller.js`, donc le script utilisateur et le favori figé) accepte aussi `localhost` et `127.0.0.1`, seulement pour les captures du dépôt (`dev/outils/captures.py`), et refuse tout autre nom de domaine ;
- le favori à jour exécute le `conseiller.js` publié sur GitHub Pages : sa sûreté dépend de celle de la branche `main` (signature obligatoire, réécriture et suppression interdites). Le favori figé (`bookmarklet.txt`) ne charge rien à distance.
