# Règle gloutonne contre stratégies qui anticipent — 03/11/2026

Sorties brutes de `python3 dev/sim/anticipation.py`, depuis la partie réelle à 14 h 25 puis à 17 h 23 (build du jeu 2026-11-03g).

Conclusion : la meilleure anticipation (simulation jusqu'à la fin de la période) gagne de 0.00 % à 0.68 % ; avec un horizon de 30 ou 60 min, elle perd jusqu'à 44 % sur 24 h en négligeant les gros paliers (IA, Gazette du multivers). La règle du conseiller est gardée.

## Partie à 14 h 25

```
État de départ : produit 1.886e+09, cagnotte 4.356e+07, production 1.867e+05/s, revenu à 5 clics/s 2.663e+06/s
Visites produites sur la période, règle gloutonne (conseiller) contre stratégie par simulation

+VT : avec valeur terminale (revenu atteint à l'horizon prolongé jusqu'à la fin de la période)

clics/s  durée     horizon      glouton     anticipe    écart décisions  temps
      0    4 h      30 min    3.937e+09    3.893e+09   -1.14%        90     0s
      0    4 h      60 min    3.937e+09    3.908e+09   -0.74%        43     0s
      0    4 h  30 min +VT    3.937e+09    3.893e+09   -1.14%        90     0s
      0    4 h  60 min +VT    3.937e+09    3.951e+09   +0.35%        74     0s
      0    4 h fin période    3.937e+09    3.938e+09   +0.01%        63     1s
        parc final différent (glouton, anticipe) : {'bot': (37, 41), 'chat': (45, 50), 'commission': (28, 31), 'fax': (32, 37), 'hamster': (42, 47), 'stagiaire': (49, 54)}
      0   24 h      30 min    7.756e+10    4.351e+10  -43.90%       244     0s
      0   24 h      60 min    7.756e+10    7.052e+10   -9.08%       214     1s
      0   24 h  30 min +VT    7.756e+10    4.359e+10  -43.80%       244     0s
      0   24 h  60 min +VT    7.756e+10    6.214e+10  -19.88%       242     1s
      0   24 h fin période    7.756e+10    7.809e+10   +0.68%       160     6s
        parc final différent (glouton, anticipe) : {'bot': (45, 52), 'chat': (53, 60), 'commission': (36, 41), 'datacenter': (11, 14), 'fax': (40, 46), 'hamster': (50, 57), 'ia': (3, 2), 'satellite': (28, 34), 'stagiaire': (57, 63)}
      5    4 h      30 min      1.3e+11      1.3e+11   +0.02%       230    17s
      5    4 h      60 min      1.3e+11      1.3e+11   +0.02%       230    27s
      5    4 h  30 min +VT      1.3e+11    1.242e+11   -4.41%       231    16s
      5    4 h  60 min +VT      1.3e+11      1.3e+11   +0.02%       230    27s
      5    4 h fin période      1.3e+11      1.3e+11   +0.02%       230    57s
        parc final différent (glouton, anticipe) : {'bot': (42, 43), 'chat': (49, 51), 'commission': (33, 34), 'datacenter': (8, 9), 'doigt': (77, 78), 'fax': (37, 38), 'gant': (49, 50), 'hamster': (46, 48), 'ia': (1, 0), 'souris': (66, 67), 'stagiaire': (53, 54), 'tampon': (44, 45), 'trounoir': (17, 18)}
      5   24 h      30 min     1.59e+12    1.442e+12   -9.30%       435    11s
      5   24 h      60 min     1.59e+12     1.56e+12   -1.90%       402    21s
      5   24 h  30 min +VT     1.59e+12    1.433e+12   -9.92%       437    12s
      5   24 h  60 min +VT     1.59e+12    1.536e+12   -3.41%       413    20s
      5   24 h fin période     1.59e+12    1.591e+12   +0.01%       374   114s
        parc final différent (glouton, anticipe) : {'bot': (51, 52), 'chat': (56, 58), 'commission': (42, 43), 'datacenter': (17, 18), 'decret': (20, 21), 'doigt': (84, 86), 'fax': (46, 47), 'gant': (56, 58), 'hamster': (54, 58), 'satellite': (34, 35), 'souris': (73, 74), 'stagiaire': (60, 61), 'tampon': (51, 52), 'trounoir': (26, 27)}
```

## Partie à 17 h 23

```
État de départ : produit 2.02e+10, cagnotte 4.727e+07, production 6.181e+05/s, revenu à 5 clics/s 6.794e+06/s
Visites produites sur la période, règle gloutonne (conseiller) contre stratégie par simulation

+VT : avec valeur terminale (revenu atteint à l'horizon prolongé jusqu'à la fin de la période)

clics/s  durée     horizon      glouton     anticipe    écart décisions  temps
      0    4 h      30 min    1.048e+10    1.006e+10   -4.05%       114     0s
      0    4 h      60 min    1.048e+10    1.029e+10   -1.81%        71     0s
      0    4 h  30 min +VT    1.048e+10     9.74e+09   -7.09%       111     0s
      0    4 h  60 min +VT    1.048e+10    1.049e+10   +0.05%        48     0s
      0    4 h fin période    1.048e+10    1.049e+10   +0.07%        48     0s
        parc final différent (glouton, anticipe) : {'bot': (43, 46), 'chat': (51, 54), 'commission': (33, 35), 'fax': (38, 41), 'hamster': (48, 51), 'satellite': (25, 26), 'stagiaire': (54, 58), 'trounoir': (17, 18)}
      0   24 h      30 min     1.23e+11    8.333e+10  -32.25%       222     0s
      0   24 h      60 min     1.23e+11    9.563e+10  -22.24%       207     0s
      0   24 h  30 min +VT     1.23e+11     8.24e+10  -33.01%       222     0s
      0   24 h  60 min +VT     1.23e+11    9.566e+10  -22.22%       241     0s
      0   24 h fin période     1.23e+11     1.23e+11   +0.03%       101     3s
        parc final différent (glouton, anticipe) : {'bot': (47, 51), 'chat': (55, 59), 'commission': (38, 40), 'fax': (42, 46), 'hamster': (52, 56), 'satellite': (30, 33), 'stagiaire': (59, 63), 'trounoir': (22, 24)}
      5    4 h      30 min    1.483e+11    1.483e+11   -0.01%       118     3s
      5    4 h      60 min    1.483e+11    1.483e+11   +0.00%       119     6s
      5    4 h  30 min +VT    1.483e+11     1.47e+11   -0.88%       133     4s
      5    4 h  60 min +VT    1.483e+11    1.461e+11   -1.49%       131     7s
      5    4 h fin période    1.483e+11    1.483e+11   +0.00%       119    15s
        parc final différent (glouton, anticipe) : {'bot': (43, 44), 'chat': (50, 52), 'commission': (34, 35), 'doigt': (78, 79), 'fax': (38, 40), 'gant': (50, 51), 'satellite': (26, 27), 'souris': (66, 68), 'stagiaire': (54, 55), 'trounoir': (18, 19)}
      5   24 h      30 min    1.659e+12    1.501e+12   -9.54%       308     4s
      5   24 h      60 min    1.659e+12    1.623e+12   -2.17%       299     8s
      5   24 h  30 min +VT    1.659e+12    1.502e+12   -9.51%       309     5s
      5   24 h  60 min +VT    1.659e+12    1.621e+12   -2.32%       297    10s
      5   24 h fin période    1.659e+12    1.661e+12   +0.11%       272    77s
        parc final différent (glouton, anticipe) : {'bot': (51, 54), 'chat': (56, 60), 'commission': (42, 45), 'datacenter': (17, 20), 'decret': (20, 22), 'doigt': (84, 88), 'fax': (46, 49), 'gant': (56, 60), 'hamster': (54, 60), 'satellite': (34, 37), 'souris': (73, 76), 'stagiaire': (60, 63), 'tampon': (51, 53), 'trounoir': (26, 29)}
```
