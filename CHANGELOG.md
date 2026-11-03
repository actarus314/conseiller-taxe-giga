# v2.x — Conseil passif et actif, cadence de clic détectée, déposé dans ce dépôt avec ses tests et son simulateur.

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
