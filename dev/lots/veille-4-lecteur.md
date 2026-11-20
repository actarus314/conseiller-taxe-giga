# Lot V4 — veille : moins de fausses alertes du lecteur

Préparé le 19/11/2026. Type : **mineur**, outillage de surveillance. Il change toutes les valeurs de la référence et le comportement de la normalisation : relecture de fin de lot **ciblée Sonnet**, contre-vérification **Opus** si un constat touche la normalisation (risque de faux « conforme »). Prérequis : lots V2 et V3 livrés (mêmes fichiers). Priorité basse : ce lot ne réduit qu'un bruit, il n'ajoute aucune détection.

## Objet

Deux fausses alertes connues de `dev/veille/autoclic.py`, écrites en limite le 19/11, et un défaut du découpage des `${…}` écrit en limite le 20/11 (`dev/contexte.md`, puce **Veille**) :

1. un reformatage à l'intérieur d'une expression `${…}` de gabarit fait un écart : ces expressions sont normalisées comme du texte, pas comme du code ;
2. passer une chaîne de `'…'` à `"…"` fait un écart. La forme unique doit aussi traiter les guillemets échappés (`'it\'s'` contre `"it's"`) ;
3. le découpage d'une expression `${…}` (`_fin_expr`) ne connaît ni les commentaires ni les expressions régulières : un `}` dans l'un d'eux la coupe au mauvais endroit, sans erreur. Depuis le lot V2, qui relit chaque `${…}` comme un script à part pour y trouver les déstructurations, cela donne le plus souvent « code illisible » (`${ s.replace(/}/g, "") }`, `${ a /* } */ }` : fausse alerte, et ni la détection d'autoclic ni le reste de la page ne sont suivis tant que c'est illisible, recalage refusé), et dans un cas un faux « conforme » (`${ f(1) // }` puis, plus loin dans le même `${…}`, une déstructuration `({ acX } = d)`, qui n'est pas vue). Essai d'un relecteur du 20/11, sur sa copie : faire découper les `${…}` par `lire` lui-même (une dizaine de lignes) règle ces cas, tests verts, sabotages non joués. Ce découpage sert à tous les gabarits de la page : la référence peut changer, à recaler dans ce lot.

## Contraintes

- **Ne rien perdre de ce qui est détecté** : chaque test, chaque essai sur la vraie page et chaque sabotage actuels restent verts. Un changement réel du contenu d'une chaîne ou d'une expression `${…}` fait toujours un écart.
- Référence recalée dans le même lot. Le premier passage réel après l'envoi doit être « Conforme », sinon le recalage est faux.
- Depuis le lot V3 (20/11/2026), le lecteur et la normalisation d'`autoclic.py` lisent aussi les modules du boss et du globe (`dev/veille/fichiers.py`, section `fichiers` de la référence, empreintes comprises) : le recalage les couvre (`--maj-reference` les télécharge), et l'étalon du lot V3 (zones et sections modifiées, empreinte seule, module minifié) se rejoue sur des copies réelles des modules.

## Étalon (fixé d'avance)

Sur une copie de la vraie page, hors dépôt :

- pas d'écart pour un reformatage dans un `${…}`, un changement de style de guillemets, ou des guillemets échappés équivalents ;
- les trois `${…}` du point 3 lus sans « illisible », la déstructuration du cas silencieux vue ;
- un écart pour un caractère changé dans une chaîne, dans un `${…}`, ou dans une chaîne à guillemets échappés ;
- les cas des lots précédents restent verts.

Tests du dépôt, sabotages, `dev/tests` en deux passes, ruff, actionlint et zizmor propres.

**Critère de correction** des relectures : se corrige tout constat qui touche la normalisation, l'étalon ou une régression ; le reste suit le tri par gravité.

## À mettre à jour

- `CHANGELOG.md`.
- `dev/contexte.md` (puce **Veille** : retirer ces limites).
- `architecture.md` §11 du projet si l'état change.
- Pousser sur `main`, vérifier la CI et le premier passage réel.
