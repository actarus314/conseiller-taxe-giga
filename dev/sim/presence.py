#!/usr/bin/env python3
"""Mode Auto : quel seuil de pause sépare le jeu passif d'une absence ?

Compare la moyenne sur 3 h d'horloge, des seuils fixes (30, 45, 60, 90 min) et un seuil adaptatif (2 × la médiane des pauses),
sur 12 journées simulées pour trois rythmes de jeu. Coût : courbe mesurée le 05/11/2026 sur la partie de Romain
(perte de production sur 24 h selon le rapport entre la cadence retenue et la vraie, à 0.8 clic/s).
Résultat (05/11/2026) : seuil de 60 min retenu, le plus robuste ; le seuil adaptatif surestime ; tous coûtent moins de 1 %.
Usage : python3 dev/sim/presence.py
"""
import random, statistics as st, bisect
COUT = [(0, -0.24), (0.5, -0.19), (0.75, -0.06), (0.9, -0.02), (1, 0), (1.1, 0.01), (1.25, -0.04), (1.5, -0.52), (2, -2.15), (3, -11.11), (5, -21)]
def cout(r):
    xs = [a for a, _ in COUT]; i = bisect.bisect(xs, r)
    if i == 0: return COUT[0][1]
    if i >= len(COUT): return COUT[-1][1]
    (x0, y0), (x1, y1) = COUT[i - 1], COUT[i]; return y0 + (y1 - y0) * (r - x0) / (x1 - x0)
def journees(jours, pause_moy, rng):
    m = []  # clics par minute, None = absent
    while len(m) < jours * 1440:
        for _ in range(rng.choice([1, 2, 3])):  # blocs de présence dans la journée
            bloc = rng.randint(60, 300); t = 0
            while t < bloc:
                g = int(rng.expovariate(1 / pause_moy)); m += [0] * min(g, bloc - t); t += g
                if t >= bloc: break
                d = rng.randint(1, 3); m += [rng.randint(240, 420) for _ in range(d)]; t += d
            m += [None] * rng.randint(45, 120)  # absence courte
        m += [None] * rng.randint(420, 540)  # nuit
    return m
def estime(m, k, seuil):
    # remonte au plus 24 h ; minutes comptées : présentes ou absentes (panneau ouvert), sauf au-delà du seuil dans une pause sans clic
    lo = max(0, k - 1440); seq = [0 if x is None else x for x in m[lo:k]]
    cnt = [True] * len(seq); run = 0
    for i, x in enumerate(seq):
        run = run + 1 if x == 0 else 0
        if seuil is not None and run > seuil: cnt[i] = False
    tot = n = 0
    for i in range(len(seq) - 1, -1, -1):
        if cnt[i]: tot += seq[i]; n += 1
        if n >= 180: break
    return tot / 60 / max(n, 30)
def seuil_adapt(m, k):
    # 2 × la médiane des pauses entre séries terminées des dernières 24 h, borné à 20-90 min
    lo = max(0, k - 1440); seq = [0 if x is None else x for x in m[lo:k]]; gaps = []; run = 0; seen = False
    for x in seq:
        if x: 
            if seen and run: gaps.append(run)
            run = 0; seen = True
        else: run += 1
    gaps = [g for g in gaps if g < 240]
    return min(90, max(20, 2 * st.median(gaps))) if gaps else 45
for pause_moy in (10, 20, 35):
    rng = random.Random(7); m = journees(12, pause_moy, rng)
    pres = [x for x in m if x is not None]; vrai = sum(pres) / 60 / len(pres)
    pts = [k for k in range(2880, len(m), 7) if m[k] is not None]
    print(f"\npauses de {pause_moy} min en moyenne entre séries · vraie cadence de présence {vrai:.2f}/s")
    for nom, f in [('horloge 3 h (actuel)', lambda k, m=m: estime(m, k, None)), ('seuil 30 min', lambda k, m=m: estime(m, k, 30)), ('seuil 45 min', lambda k, m=m: estime(m, k, 45)),
                   ('seuil 60 min', lambda k, m=m: estime(m, k, 60)), ('seuil 90 min', lambda k, m=m: estime(m, k, 90)), ('seuil adaptatif', lambda k, m=m: estime(m, k, seuil_adapt(m, k)))]:
        r = [f(k) / vrai for k in pts]; c = [cout(x) for x in r]
        print(f"  {nom:<22} médiane ×{st.median(r):.2f} · surestimé ×1.5+ {100*sum(x>=1.5 for x in r)/len(r):4.1f} % du temps · ×2+ {100*sum(x>=2 for x in r)/len(r):4.1f} % · coût moyen {st.mean(c):+.3f} %")
