# v2.x — Conseil passif et actif, cadence de clic détectée, déposé dans ce dépôt avec ses tests et son simulateur.

## v2.29 — 05/11/2026
Détails : ouverts d'office en Actif seulement tant qu'aucun choix n'a été fait ; ensuite, le choix (ouverts ou fermés) est retenu, y compris en repassant en Actif. Bouton des détails : chevron dessiné, à la taille de son carré, qui se retourne à l'ouverture.

## v2.28 — 05/11/2026
Placement du panneau plus robuste : le bouton TAXER flottant compte aussi comme obstacle, une quatrième place (en haut à gauche) est essayée, et si aucune n'est libre, le panneau prend celle qui recouvre le moins au lieu de revenir en bas à droite.

## v2.27 — 05/11/2026
Colonne « En direct » : la série de clics s'arrête après 5 s sans clic (8 s avant) ; sans effet sur le conseil, calculé sur la moyenne. Cadence prévue du mode Actif réglée en tête des détails, dépliés au passage en Actif, au lieu d'une ligne sous l'en-tête.

## v2.26 — 05/11/2026
Pendant une série de clics, la colonne des clics passe « En direct » (ce que la série rapporte, Rafale comprise) au lieu d'une ligne en plus : le panneau ne change plus de taille en cliquant. Rafale signalée par le seul bandeau jaune du haut (elle l'était aussi en bas). Détails ouverts par une flèche au bout des chiffres clés, au lieu d'une ligne entière. Veille : un seul essai par passage ; après une page inaccessible, la relance suivante est sautée sans requête au site, et l'issue n'est ouverte qu'au deuxième échec de suite.

## v2.25 — 05/11/2026
Événements du jeu (build 2026-11-04n, premier le 05/11 de 12 h à 20 h : « Jour de mobilisation », production ×2) : lus sur l'indicateur du jeu, comptés dans la production, le plan et les délais pour leur durée, cumulés avec la Frénésie (×4 au lieu de ×3) ; signalés en alerte. Veille : l'indicateur des bonus est suivi (17 règles).

## v2.24 — 05/11/2026
Mode Auto : moyenne sur les 3 dernières heures de présence, cherchées sur 24 h. Au-delà d'1 h sans clic, c'est une absence, écartée : au retour d'une nuit onglet ouvert, le conseil repart sur la cadence d'avant au lieu de partir de zéro pendant 3 h. Seuil choisi par simulation (dev/sim/presence.py) : le plus robuste parmi 30, 45, 60, 90 min et un seuil adaptatif.

## v2.23 — 05/11/2026
En direct : pendant une série de clics (Auto, Actif), une ligne donne sa cadence et ce qu'elle rapporte (Rafale comprise) ; elle disparaît 8 s après le dernier clic. Décompte des clics sur l'heure et la minute retiré du détail : les limites restent signalées en alerte quand elles approchent.

## v2.22 — 04/11/2026
Limites de clics du serveur relevées par le jeu (build 2026-11-04l) : 1030 par minute (17.2/s) et 24000 par heure, au lieu de 760 et 18000 ; détection d'autoclic inchangée (10 min au plafond). Barème et puissance de clic inchangés.

## v2.21 — 04/11/2026
Sélecteur de mode centré dans l'en-tête : 15 px d'écart avec le numéro de version comme avec – et ✕ (6 px avant).

## v2.20 — 04/11/2026
Sélecteur de mode dans l'en-tête, sur une seule ligne avec le titre et la version ; Facture dorée et Rafale signalées par un bandeau jaune sous l'en-tête. Cadence prévue du mode Actif : champ élargi, au point décimal (la virgule reste acceptée à la saisie), flèches haut et bas par pas de 0.5.

## v2.19 — 04/11/2026
Suite des achats : plus de numéros ; prix à trois chiffres (le conseil du haut garde le prix exact) ; l'heure partout, en pastille verte quand l'achat est possible aussitôt après le précédent. Les noms ont la place de tenir presque tous en entier. Modes Auto, Passif et Actif réunis en un sélecteur compact, sur une ligne séparée du conseil par un filet.

## v2.18 — 04/11/2026
Suite des achats en colonnes alignées, une ligne par achat : nom (coupé par « … » s'il est trop long), nombre possédé après achat, prix, heure (« aussitôt » au lieu de « tout de suite »). Conseil en attente : « devient ×n » ajouté, « ne rien acheter d'autre d'ici là » sur sa propre ligne.

## v2.17 — 04/11/2026
Bas du panneau : le « revenu » mêlait production réelle et clics supposés. Il est remplacé par la production automatique (réelle, ×3 pendant une Frénésie), l'apport des clics à la cadence retenue (moyenne en Auto, prévue en Actif, ×10 pendant une Rafale) et la cagnotte, sur trois colonnes fixes qui ne se déforment plus ; le revenu supposé par le plan est nommé dans « détails ». Favori figé compressé par terser : 22428 caractères au lieu de 31969 ; plafond des tests porté à 60000, sous la limite de Firefox (65536 caractères ; Chrome : 2 Mo).

## v2.16 — 04/11/2026
Bas du panneau lisible : revenu, cagnotte et cadence retenue en chiffres clés ; alertes (Frénésie, Rafale, limites de clics) sur fond coloré, affichées seulement quand elles comptent ; moyenne, série en cours et décompte des clics repliés sous « détails » (état retenu).

## v2.15 — 04/11/2026
Mode Auto : moyenne comptée sur les seules minutes notées depuis cette version. Les versions antérieures ne gardaient que les minutes avec clics : prises pour du jeu observé, elles gonflaient la moyenne (2.2 clic/s affiché pour environ 1 clic/s réel). Ces minutes restent dans le quota horaire ; l'alerte des 18000 clics par heure s'affiche aussi quand la moyenne est nulle. Veille : 6 passages par heure au plus (délai de 15 min, plus les passages lancés par un envoi).

## v2.14 — 04/11/2026
Mode Auto : cadence moyenne des clics sur le temps de jeu observé des 3 dernières heures (30 min comptées au moins), au lieu de celle de la série en cours ; des séries espacées (passif la plupart du temps, quelques séries par heure) donnent un conseil stable, sans pousser des bonus de clic pendant une série (simulation sur une partie réelle : jusqu'à 21 % de visites en moins sur 24 h avec l'ancien conseil). Clics du mode mini du jeu (build 2026-11-04e) comptés. Rafale de la Facture dorée : en-tête jaune « cliquer ! ». Panneau placé hors du grand bouton TAXER, qu'il couvrait à 1280 et 1440 px de large et sur téléphone. Veille : page demandée compressée (102 Ko au lieu de 327 Ko), relance réessayée sur une erreur passagère de GitHub. Page d'installation alignée sur ces changements.

## v2.13 — 03/11/2026
Grands nombres : le jeu (build 2026-11-03m) affiche cagnotte et prix en « billions » au-delà de 1e15 ; le panneau les lit, au lieu d'annoncer une boutique introuvable. La veille suit ce format (16 règles).

## v2.12 — 03/11/2026
Polices du jeu (Space Grotesk, IBM Plex Mono) : le panneau reprend celles que la page du jeu charge déjà, la page d'installation les sert elle-même (polices/, licence SIL OFL 1.1) au lieu de Google Fonts, qui recevait l'adresse IP des visiteurs. Page d'installation déclarée en UTF-8 avec une fenêtre d'affichage mobile : elle s'affichait jusqu'ici à la largeur d'un ordinateur sur téléphone.

## v2.11 — 03/11/2026
Audit : panneau 3 à 19 fois moins coûteux par rafraîchissement (Chrome : 0.9–3.5 ms → 0.1–0.4 ms ; formateur d'heure unique, plan calculé une fois par étape, DOM réécrit seulement si changé), glissement arrêté sur pointercancel, constantes uniques. Sécurité : panneau et favori limités à taxe-au-giga.fr ; veille durcie (page plafonnée à 3 Mo, regex bornées, texte du jeu neutralisé dans les issues et hors des journaux, relance plafonnée, actions épinglées par empreinte, Node 22).

## v2.10 — 03/11/2026
Numéro de version du panneau cliquable : il ouvre le dépôt GitHub dans un nouvel onglet, pour signaler un écart ou suivre les versions. Un appui sur le lien ne déplace pas le panneau.

## v2.9 — 03/11/2026
Jeu en build 2026-11-03h : Décret d'application porté de +25000 à +100000 visites par clic, et autoclic repéré après 10 min au plafond de 760 clics/min (3 min avant). Écart trouvé par la veille lancée à la main, ses passages programmés n'ayant pas démarré.

## v2.8 — 03/11/2026
Compte à rebours à la seconde (« 3 min 05 s ») au lieu de la minute arrondie, panneau rafraîchi 4 fois par seconde. Cagnotte affinée par la sauvegarde exacte du jeu plus la production et les clics TAXER faits depuis : l'affichage arrondi à 10 M près en milliards décalait l'attente de plusieurs minutes et ignorait les clics entre deux rafraîchissements.

## v2.7 — 03/11/2026
Numéro de version affiché dans l'en-tête du panneau, pour savoir quelle version le favori a chargée ; il est écrit dans la source par build.py, seule déclaration du numéro.

## v2.6 — 03/11/2026
Favori à jour en bouton principal : il charge conseiller.js depuis GitHub Pages à chaque clic (paramètre à la minute contre le cache de 10 min) et signale un échec de chargement. L'ancien favori reste proposé en version figée (bookmarklet.txt).

## v2.5 — 03/11/2026
Panneau passé sous la Facture dorée (z-index 60, elle est à 70 : il pouvait la recouvrir) et en-tête jaune quand elle est à l'écran. Frénésie et Rafale affichées avec le revenu réel du moment, Rafale (clics ×10) comptée dans les délais ; le compteur « Production /s » du jeu, lui, ignore la Frénésie.

## v2.4 — 03/11/2026
Cadence moyennée sur la dernière minute de la série en cours et arrêt fixé à 8 s sans clic : la v2.3 (15 s, arrêt dès 2 s) faisait chuter la cadence à chaque courte pause. Règles du jeu revérifiées à 14 h 25 : page identique (build 2026-11-03e), production et puissance de clic du serveur égales au modèle.

## v2.3 — 03/11/2026
Arrêt des clics détecté en 2 à 5 s (4 intervalles habituels) au lieu de jusqu'à 2 min ; cadence mesurée sur la série en cours (15 s). Une pause d'1 s pour acheter ne fait pas basculer le conseil.

## v2.2 — 03/11/2026
Captures d'écran dans le README (passif, Auto en cliquant, téléphone) et bouton vers la page d'installation : GitHub retire les liens javascript: des README. Panneau réduit à l'ouverture sous 600 px de large.

## v2.1 — 03/11/2026
Mode Auto par défaut : cadence mesurée sur les clics TAXER (2 min), limitée à 760/min et au reste du quota de 18000/h réparti sur 15 min ; compteur horaire gardé au rechargement. Plafond fixe de 5/s retiré : il sous-estimait le clic sous 12.7/s. Nombres au point décimal, formulations impersonnelles.

## v2.0 — 03/11/2026
Mode Actif (clics à cadence réglable, plafonnée à 5/s par la limite serveur de 18000 clics/h), Frénésie comptée, bouton du jeu seul juge de « achetable ». Panneau placé au-dessus du bouton TAXER flottant ; contrôle de la puissance de clic affichée.

# v1.x — Conseil passif seul.

## v1.0 — 03/11/2026
Premier conseiller (hors dépôt) : surligne le bonus passif qui minimise attente + remboursement, d'après le barème lu dans le code du jeu (build 2026-11-03e).
