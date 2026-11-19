# Lot V2 — veille : le reste de la page principale

Préparé le 19/11/2026 (build du jeu 2026-11-19a), relu en contexte neuf le même jour. Type : **mineur**, outillage de surveillance. Relecture de fin de lot : **ciblée Sonnet** en contexte neuf, puis contre-vérification si elle relève un bloquant ou un « à corriger ». Prérequis : aucun. Avant les lots V3 (`dev/lots/veille-3-fichiers.md`) et V4 (`dev/lots/veille-4-lecteur.md`), qui touchent les mêmes fichiers.

## Objet

Étendre la veille de la détection d'autoclic (`dev/veille/autoclic.py`, livrée le 19/11) à ce que la page principale porte encore sans être suivi, **sans aucune requête de plus au site**. Une issue doit s'ouvrir dès que l'un de ces passages change.

## À lire d'abord

- `dev/contexte.md`, puce **Veille** (foyer des choix, limites et bruit de la veille) ; `CHANGELOG.md`, entrée « Veille — 19/11/2026 ».
- `dev/veille/autoclic.py`, `dev/veille/veille.py`, `dev/veille/test_veille.py`, `.github/workflows/veille.yml`.
- Projet claude.ai : `architecture.md` §1, §5 (bot, combat du Dépité), §7 (contrôles du jeu), §11, §12 (collecteur) ; `claude/regles.md` (où écrire quoi, checklist).
- Dépôt privé `actarus314/taxe-au-giga-bot` (à attacher à la session) : seulement pour le point 3 et pour savoir ce que le collecteur lit (point 6).
- La page du jeu, téléchargée dans le lot (`https://taxe-au-giga.fr/`, copie hors dépôt).

## Périmètre

Repères de lignes : page au build 2026-11-19a, à relire dans le lot (ils bougent d'un build à l'autre).

1. **Régularité envoyée au serveur (`cad`)** :
   - la zone `cadence()` (≈ l. 3067-3080) ;
   - d'où viennent les horodatages qu'elle lit : chaque instruction qui alimente `clickTimes`. Aujourd'hui, `taxHit` (≈ l. 3093-3099) reçoit `e.timeStamp` du bouton (≈ l. 3100-3103) et `performance.now()` de la version mini (≈ l. 5895).
2. **Ce que la page envoie à `/api/sync`, dans ses deux émissions** :
   - la synchro (`const body = { … }` ≈ l. 2840 : `clicks`, `cad`, `alive`, `gold`, `acChoice`, `tb`, `bz`, `...flags`…), le champ ajouté ensuite (`body.legacy = { … }`, ≈ l. 2841) et `cardFlags()` (≈ l. 5277), dont les champs partent dans le même corps ;
   - l'envoi de fermeture `beacon()` (≈ l. 2918-2925), qui a son propre `const body` plus court.

   Ancre distincte pour chacune : deux `const body` coexistent. Un champ ajouté ou retiré = écart.
3. **Règle des pseudos** : `taxerName` (≈ l. 3531) et les tables `NOUNS`, `ADJS` (≈ l. 3529-3530). Vérifier dans le dépôt bot si le collecteur ou le widget la recopient. **Rien du dépôt privé dans le dépôt public ni dans les issues** (ni chemin, ni nom de fichier) : l'issue dit seulement « règle des pseudos changée : vérifier ce qui la recopie », et le détail va dans `architecture.md` du projet.
4. **Boss, côté page** :
   - **chargeur** : dernier bloc `<script>` (« Boss : rien n'est chargé hors de l'événement »). Il porte la fenêtre horaire (`A`, `B`), `/boss/hit.php`, `/boss/state.json`, les fichiers `boss-event-net.js`, `boss-site.js` et leur version `?v=`.
     - Observé le 19/11 (une seule observation) : `v=1794501311` = 12/11/2026 16:35:11 UTC, et `Last-Modified` des deux fichiers = 16:35:12 GMT.
     - Probable, non établi : le numéro est généré à chaque déploiement du module, ce qui ferait de ce bloc un signal de déploiement sans requête de plus.
     - C'est une fonction fléchée anonyme : il faut une ancre autre qu'un nom (par exemple le bloc `<script>` qui contient `boss-event-net.js`), et une ancre disparue fait un écart.
   - **bandeau du Dépité** : avant-dernier bloc `<script>` (≈ l. 6141-6196). Calendrier file 18 h / combat 18 h 02 / fin (`slot()`, `paint()`) et appel de `window.bossReopen`.
   - **contrat page → module** : `window.TaxeBoss` (≈ l. 6126-6129 : `yieldTo`, `pseudo`, `myId`, `shareBoss`, `calm`, `sound`, `beep`, `now`, `lock`), que le module lit (tout sauf `now` au 19/11). Seul le verrou est suivi aujourd'hui (règle « verrou boss »).
5. **Restes relevés par la relecture du 19/11** :
   - la clé `AC_KEY` (≈ l. 2825) ;
   - les `setInterval(acShow, …)` et `setInterval(acWarnShow, …)` (≈ l. 3685, 3740) ;
   - l'envoi de la méthode de clic à `/api/feedback.php` (≈ l. 3735) ;
   - les fenêtres créées par le script (aujourd'hui `fb-bub`, ≈ l. 5787, par `mk()` et `setAttribute('role', 'dialog')`, sans rapport avec l'autoclic : elle entrera dans l'inventaire, bruit assumé) ;
   - les champs lus par crochets (`d['acX']`, aucun aujourd'hui).

   La déstructuration (`const { acX } = d`) reste une limite écrite si elle n'est pas couverte.
6. **Routes que lit le collecteur, côté page** : `/api/leaderboard?v=3&r=` (≈ l. 3633), `/api/taxer?id=` (≈ l. 3637, 4515). Suivre les instructions qui les appellent : un changement de version ou de paramètre est un signal pour le collecteur.

7. **Globe « La facture fait le tour du monde »** (build 2026-11-19a), côté page : l'instruction qui charge le module (`import('/monde/monde.js?v=…')`, ≈ l. 3894) et l'appel `m.play({ … })` qui lui passe `envoisUrl: '/monde/envois.php'`, `regionsUrl: '/monde/regions.php'` et le reste. Une version `?v=` ou une adresse changée = écart. Le bot ne le pilote pas encore : `architecture.md` §11 note une décision en attente de Romain sur la méthode.

Hors périmètre :

- les fichiers des modules (boss, globe) et la page `/regles` (lot V3) ;
- la réforme du lecteur qui réduit les fausses alertes (lot V4).

Ce qui est vu en passant hors périmètre se signale à Romain, sans être fait.

## Choix déjà tranchés (ne pas les rouvrir)

- Écarts traités à la main (décision de Romain du 03/11/2026) ; une issue fermée ne vaut pas « déjà vu ».
- Un changement de build seul ne fait pas d'issue ; jamais de « conforme » silencieux (zone introuvable ou code illisible = écart).
- Aucune copie de la page du jeu dans le dépôt pour les tests (pages fabriquées) ; `reference.json` garde des extraits normalisés.
- Bruit assumé : les corps envoyés à `/api/sync` changeront quand l'auteur ajoutera un drapeau. Le bot lit les synchros, et l'issue le dira.
- Rien du dépôt privé dans le dépôt public, cahiers compris : ni chemin, ni nom de fichier, ni réglage du bot.
- Codes de compte « GOBE-… » : jamais dans le dépôt. Les pseudos « Gobe-Octet … » de `NOUNS` n'en sont pas, mais un contrôle insensible à la casse les trouverait : les distinguer.

## Étalon (fixé d'avance)

- Page actuelle, après recalage : « Conforme », code 0.
- Build seul changé (fabriqué) : conforme. La paire réelle 18f → 19a a aussi changé la version de `monde.js` (28 → 29), qui fera désormais un écart (point 7).
- Sur une copie de la vraie page, hors dépôt, une modification de chaque sorte doit faire un écart nommé :
  - une par point du périmètre ;
  - les deux corps de `/api/sync` séparément ;
  - l'origine des horodatages de `clickTimes` ;
  - le chargeur et le bandeau ;
  - l'ancre du chargeur disparue ;
  - la version du module du globe.
- Le script d'essai garde ses cas actuels, qui restent verts.
- **Aucune requête de plus** : un compteur posé sur le téléchargement montre une seule requête par passage.
- Dans `test_veille.py` : un cas par point, sur la page fabriquée. Chaque défense nouvelle est vérifiée par un sabotage qui fait échouer les tests.
- `node test.js` et `node test.js bm` (dans `dev/tests`) verts ; ruff, actionlint et zizmor propres.

**Critère de correction** des relectures : se corrige tout constat qui touche ce périmètre, l'étalon ou une régression de la veille ; le reste suit le tri par gravité (règles de Romain).

## À mettre à jour dans le même lot

- `CHANGELOG.md` (entrée Veille datée).
- `dev/contexte.md`, puce **Veille** : c'est le foyer de la liste de ce qui est suivi, des choix et des limites. Retirer de « Non suivis » ce qui l'est désormais.
- Projet claude.ai :
  - `architecture.md` §1 : résumé court qui renvoie à `dev/contexte.md`, sans recopier la liste ;
  - §11 : état ;
  - §12 : ce que le collecteur doit surveiller, si le point 3 ou 6 le montre ;
  - relire juste avant d'écrire, une autre conversation a pu le changer.
- `README.md` seulement si la description de la veille change.
- Pousser sur `main` (convention du dépôt), puis vérifier la CI et le premier passage réel de la veille.
