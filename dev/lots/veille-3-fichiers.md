# Lot V3 — veille : modules du boss (et du globe) et page `/regles`

Préparé le 19/11/2026, relu en contexte neuf le même jour. Type : **mineur**, outillage de surveillance (requêtes nouvelles au site). Relecture de fin de lot : **ciblée Sonnet** en contexte neuf, puis contre-vérification si elle relève un bloquant ou un « à corriger ». Prérequis : **lot V2 livré** (`dev/lots/veille-2-page.md` : mêmes fichiers ; V2 suit déjà le chargeur du module et sa version `?v=`).

## Objet

Le lot V2 suit la version `?v=` du module du boss, qui change probablement à chaque déploiement (une seule observation au 19/11 : à confirmer dans ce lot), sans dire ce qui a changé. Ce lot dit ce qui a changé dans le module du boss, et suit les sections de la page `/regles` qui parlent d'autoclic (texte affiché aux joueurs). Les deux demandent des requêtes de plus au site.

## Décision à soumettre à Romain en tête de lot (rien ne se code avant sa réponse)

**Quand la veille télécharge-t-elle le module du boss et `/regles` ?** Elle passe toutes les ~15 min, depuis les machines de GitHub, et fait une seule requête aujourd'hui ; l'hébergeur bloque parfois les robots quand son trafic monte (`dev/contexte.md`, « Veille et 403 »).

Faits qui bornent les voies, relevés le 19/11 :

- la référence ne change qu'au recalage manuel. Après un déploiement du module, « `?v=` différent de la référence » reste vrai à chaque passage jusqu'au recalage ;
- le build de la page diffère déjà de la référence (19a contre 18f) sans écart, donc « quand le build change » reviendrait à « à chaque passage » ;
- l'état gardé d'un passage à l'autre (`sauter`, `echecs`) est remis à zéro par le lancement horaire et par chaque envoi sur `main` qui touche la veille (`dev/veille/**`, `veille.yml`, `conseiller.js` : valeurs par défaut de `veille.yml`). Il ne peut pas compter des heures ni des jours. Une voie sans état reste possible par l'horloge (télécharger seulement dans une plage fixe de chaque heure ou de chaque jour), avec deux limites à mesurer : plusieurs passages peuvent tomber dans une même plage (lancement horaire, envois, intervalle réel de plus de 15 min), et elle ne peut pas compter des échecs qui durent ;
- tailles : module, `boss-event-net.js` 176 007 octets et `boss-site.js` 28 507 octets (≈ 62 Ko compressés à deux) ; `/regles`, 21 113 octets (≈ 7 Ko compressés) ; `monde.js` non mesuré (à mesurer si le point 2 s'active).

Voies à présenter avec leur coût mesuré (requêtes et volume par jour) et leur délai de détection : à chaque passage ; sur une plage horaire (une fois par heure, ou une fois par jour) ; et, pour le module, seulement quand `?v=` diffère de la référence (donc à chaque passage jusqu'au recalage). Vérifier ces faits dans le lot avant de les présenter, puis s'arrêter jusqu'à la réponse.

## À lire d'abord

- Le cahier V2 et ce que V2 a livré (`CHANGELOG.md`, puce **Veille** de `dev/contexte.md`, foyer des choix de la veille).
- `dev/veille/veille.py` (téléchargement, plafond de taille `MAX_PAGE`, rendu inerte `sur()`, gestion du 403), `.github/workflows/veille.yml` (entrées `sauter`, `echecs`, états, issues).
- Projet claude.ai : `architecture.md` §5 (combat du Dépité par le bot), §7, §11 ; `claude/regles.md`.
- **Dépôt privé `actarus314/taxe-au-giga-bot`** (à attacher à la session) : le bot, pour l'inventaire du point 1.

## Périmètre

1. **Module du boss** (`/boss/boss-event-net.js`, `/boss/boss-site.js`, lisibles hors de l'heure du combat, vérifié le 19/11). Zones à suivre, avec la normalisation d'`autoclic.py` (le lecteur lit les deux fichiers sans erreur, essai du 19/11), plus une empreinte de chaque fichier entier :
   - **les contrôles propres au module** : plafonds de cadence (`CAP = 6`, `CAP3 = 14`, ≈ l. 111 de `boss-event-net.js` ; le réglage de cadence du bot pour le combat s'y rapporte : voir `architecture.md` §5 du projet, à ne pas recopier ici), compte et refus des coups (≈ l. 1765-1772), gardes `isTrusted` (≈ l. 839 et suivantes) ;
   - **ce que le bot utilise** (inventaire tiré du dépôt bot) : sélecteurs, gestionnaires capturés, globales (`window.bossEv`, `window.bossReopen`, `BOSS_SERVER`, contrat `window.TaxeBoss` côté module), textes lus.

   Dans le dépôt public (`reference.json`, issues) : pas de copie des 200 Ko (zones et empreintes seulement), et des noms de zones neutres, sans rien qui décrive le bot ni ses fichiers. L'issue dit quelles zones ont changé, ou seulement le reste du module. Limite à écrire : un module modifié sans changement de `?v=` n'est vu que si la voie choisie le télécharge quand même.
2. **Module du globe** (`/monde/monde.js?v=…`) : **seulement si** Romain a décidé entre-temps que le bot pilote le globe (décision en attente au 19/11, `architecture.md` §11). Même traitement que le module du boss, inventaire tiré du bot. Sinon, ne rien faire : V2 suit déjà sa version.
3. **`/regles`** : sections qui parlent d'autoclic. Au 19/11 : `#autoclick` (≈ 1 000 caractères de texte), `#resume` (« Interdit : un autoclicker… »), `#faq` (retour au classement, touche Entrée maintenue, avertissement) et `#limites` ; `#appel` est à examiner. Chaque section est suivie en entier, normalisée, et rendue inerte par `sur()` dans les rapports.

   `#appel` contient des pseudos (« Gobe-Octet sournois #732 ») et `#reprise` un gabarit « GOBE-XXXX-… » : ce ne sont pas des codes de compte, mais un contrôle des codes insensible à la casse les trouverait. Ne pas suivre `#reprise`, et distinguer les pseudos.
4. **Requêtes nouvelles** : un seul essai chacune, plafond de taille comme `MAX_PAGE`, rien pendant un passage sauté. Un échec ne doit jamais masquer un écart de la page principale, ni faire conclure « conforme » sur ce qui n'a pas été lu.

   Le workflow a aujourd'hui ces états : `conforme`, `ecart`, `erreur` (issue tout de suite), `inaccessible` (issue au deuxième échec de suite) et le passage sauté. Ce qui en découle :
   - un écart remplace les autres issues ;
   - « conforme » les referme toutes.

   À concevoir : le sort d'un échec passager sur un fichier secondaire (un 403 isolé). Il ne doit ni ouvrir d'issue, ni remplacer celle d'un vrai écart, ni la refermer ; un échec qui dure doit finir par être signalé. Le choix se décrit dans `dev/contexte.md`.
5. **Essais hors réseau** : `--fichier` ne couvre que la page principale. Il faut une option équivalente pour chaque module et pour `/regles`, pour jouer l'étalon sur des copies.

## Choix déjà tranchés (ne pas les rouvrir)

- Ceux du cahier V2 : écarts traités à la main, jamais de « conforme » silencieux, build seul sans issue, pas de copie de la page pour les tests, rien du dépôt privé dans le dépôt public (ni chemin, ni nom, ni réglage du bot).

## Étalon (fixé d'avance)

- Fichiers actuels, après recalage : « Conforme ».
- Sur des copies hors dépôt, l'écart attendu pour chaque cas :
  - un contrôle du module (`CAP`) modifié ;
  - une zone utilisée par le bot modifiée ;
  - une partie non suivie modifiée (empreinte seule) ;
  - la version `?v=` changée ;
  - chaque section suivie de `/regles` modifiée ;
  - une zone du module ou une section de `/regles` disparue (écart nommé, jamais « conforme »).
- Module injoignable et, en même temps, un écart de la page principale : l'écart reste signalé, et son issue n'est pas remplacée.
- Module ou `/regles` injoignable une fois : ni issue ouverte, ni issue refermée. Échec qui dure : signalé comme prévu au point 4.
- Passage sauté : zéro requête.
- Nombre de requêtes par passage et par jour : mesuré, et conforme à la décision de Romain.
- Tests du dépôt sur des fichiers fabriqués, avec un sabotage qui les fait échouer pour chaque défense ; `dev/tests` en deux passes ; ruff, actionlint et zizmor propres.

**Critère de correction** des relectures : se corrige tout constat qui touche ce périmètre, l'étalon ou une régression de la veille ; le reste suit le tri par gravité.

## À mettre à jour dans le même lot

- `CHANGELOG.md`.
- `dev/contexte.md` : puce **Veille** (foyer), et « Veille et 403 » si la politique des requêtes change.
- Projet claude.ai, à relire juste avant d'écrire : `architecture.md` §1 (résumé court avec renvoi), §7 (si `/regles` dit du nouveau ; voir le point 6 du §7 d'`architecture.md`, sortie de mise à l'écart consignée le 19/11), §11.
- Pousser sur `main`, vérifier la CI et le premier passage réel.
