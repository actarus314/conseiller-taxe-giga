#!/usr/bin/env python3
"""La règle du conseiller (un achat à la fois) perd-elle face à une stratégie qui anticipe ?

Règle du conseiller (« gloutonne ») : acheter le bonus qui minimise attente + prix ÷ gain, au revenu actuel.
Stratégie qui anticipe (« par simulation ») : à chaque achat, essayer chacun des meilleurs candidats, simuler
la suite avec la règle gloutonne pendant un horizon H, et garder celui qui a produit le plus de visites.
Simulation par événements (achat possible, déblocage d'un palier), exacte à revenu constant entre deux événements.

Usage : python3 dev/sim/anticipation.py
"""
import math, pathlib, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
src = (pathlib.Path(__file__).parent / 'modele.py').read_text(encoding='utf-8').split('o0=dict')[0]
exec(src)  # S, cost, income, gain : barème et modèle du jeu, communs au simulateur


def available(o, c):
    return [u for u in S if (c >= u['unlock'] or o.get(u['id'], 0) > 0) and not (u['max'] and o.get(u['id'], 0) >= u['max'])]


def ranked(o, w, c, cps):
    R = income(o, cps)
    out = []
    for u in available(o, c):
        g = gain(u, o, cps)
        if g > 0:
            k = cost(u, o)
            out.append((max(0, k - w) / R + k / g, u))
    out.sort(key=lambda x: x[0])
    return [u for _, u in out]


def next_unlock(o, c):
    t = [u['unlock'] for u in S if u['unlock'] > c and not o.get(u['id'], 0)]
    return min(t) if t else math.inf


def advance(o, w, c, t, cps, target, T):
    """Attendre de pouvoir payer `target` (ou un déblocage, ou la fin). Renvoie w, c, t, acheté ?"""
    R = income(o, cps)
    k = cost(target, o)
    dt_buy = max(0.0, (k - w) / R)
    dt_unl = max(0.0, (next_unlock(o, c) - c) / R)
    dt = min(dt_buy, dt_unl, T - t)
    w += R * dt; c += R * dt; t += dt
    if dt == dt_buy and t < T + 1e-9 and w >= k - 1e-6:
        w -= k; o[target['id']] = o.get(target['id'], 0) + 1
        return w, c, t, True
    return w, c, t, False


def greedy(o, w, c, t, T, cps, first=None):
    o = dict(o)
    pending = first
    while t < T - 1e-9:
        u = pending or (ranked(o, w, c, cps) or [None])[0]
        if u is None:
            R = income(o, cps); c += R * (T - t); break
        w, c, t, bought = advance(o, w, c, t, cps, u, T)
        if bought:
            pending = None
    return c, o


def lookahead(o, w, c, T, cps, H, N=6):
    o = dict(o); t = 0.0
    decisions = 0
    while t < T - 1e-9:
        cands = ranked(o, w, c, cps)[:N]
        if not cands:
            c += income(o, cps) * (T - t); break
        h = min(T, t + H)
        best = max(cands, key=lambda u: greedy(o, w, c, t, h, cps, first=u)[0])
        decisions += 1
        while t < T - 1e-9:
            w, c, t, bought = advance(o, w, c, t, cps, best, T)
            if bought:
                break
            if best not in available(o, c):
                break
            # un déblocage est survenu : la décision est réexaminée
            if ranked(o, w, c, cps)[:N] != cands:
                break
    return c, o, decisions


if __name__ == '__main__':
    # partie réelle lue sur le serveur à 14 h 25 le 03/11/2026
    o0 = dict(doigt=46, stagiaire=45, chat=41, hamster=38, souris=34, bot=33, fax=28, commission=24, gant=21, satellite=16, trounoir=7, tampon=12)
    w0, c0 = 43557887, 1885613722
    print('Visites produites sur la période, règle gloutonne (conseiller) contre stratégie par simulation\n')
    print(f"{'clics/s':>7} {'durée':>6} {'horizon':>8} {'glouton':>12} {'anticipe':>12} {'écart':>8} {'décisions':>9} {'temps':>6}")
    for cps in (0, 5):
        for T in (4 * 3600, 24 * 3600):
            g, og = greedy(o0, w0, c0, 0.0, T, cps)
            for H in (1800, 3600):
                t1 = time.time()
                a, oa, n = lookahead(o0, w0, c0, T, cps, H)
                print(f"{cps:>7} {T // 3600:>4} h {H // 60:>5} min {g - c0:>12.4g} {a - c0:>12.4g} {100 * (a - g) / (g - c0):>+7.2f}% {n:>9} {time.time() - t1:>5.0f}s")
            diff = {k: (og.get(k, 0), oa.get(k, 0)) for k in set(og) | set(oa) if og.get(k, 0) != oa.get(k, 0)}
            print(f"{'':>7} parc final différent (glouton, anticipe) : {dict(sorted(diff.items()))}")
