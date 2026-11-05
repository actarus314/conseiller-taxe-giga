#!/usr/bin/env python3
"""Tests de la veille (dev/veille/veille.py), sur des pages fabriquées : aucune copie de la page du jeu dans le dépôt.

Page fabriquée : le numéro de build, le tableau SHOP écrit d'après le barème du conseiller (tableau P de conseiller.js),
et chaque passage de règle tel qu'il est noté dans dev/veille/reference.json.
Usage : python3 dev/veille/test_veille.py
"""
import json, pathlib, subprocess, sys, tempfile

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import veille  # noqa: E402

REF = json.loads((ICI / 'reference.json').read_text(encoding='utf-8'))
echecs = 0


def page(build="2026-11-04n", shop=None, regles=None):
    shop = shop if shop is not None else veille.shop_conseiller()
    lignes = [f"const BUILD = '{build}';", 'const SHOP = [']
    for k, u in shop.items():
        extra = ''.join(f", {c}: {u[c]:g}" for c in ('rate', 'click', 'pct', 'max') if u[c])
        lignes.append(f"  {{ id: '{k}', name: '', base: {u['base']:g}, unlock: 1{extra} }},")
    lignes.append('];')
    for texte in (regles or REF['regles']).values():
        lignes += (texte or '').split(' | ')
    return '\n'.join(lignes) + '\n'


def lancer(html):
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / 'page.html'
        f.write_text(html, encoding='utf-8')
        r = subprocess.run([sys.executable, str(ICI / 'veille.py'), '--fichier', str(f)], capture_output=True, text=True)
        return r.returncode, r.stdout


def verifie(nom, ok, detail=''):
    global echecs
    print(('  ok   ' if ok else '  ÉCHEC ') + nom + (f' ({detail})' if detail and not ok else ''))
    echecs += not ok


code, out = lancer(page())
verifie('page conforme : code 0', code == 0 and 'Conforme' in out, out[-200:])

regles = dict(REF['regles']); regles['limites de clics'] = regles['limites de clics'].replace('1 030', '2 000')
code, out = lancer(page(regles=regles))
verifie('règle modifiée (limite de clics) : écart signalé', code == 1 and 'limites de clics' in out, out[-200:])

shop = veille.shop_conseiller(); shop['doigt'] = dict(shop['doigt'], base=12)
code, out = lancer(page(shop=shop))
verifie('barème modifié (prix de base) : écart signalé', code == 1 and 'doigt' in out and 'base 10 → 12' in out, out[-200:])

html = page().replace("rate: 250000", "rate: 2.5e+5")
code, out = lancer(html)
verifie('nombre écrit 2.5e+5 dans le tableau du jeu : lu, page conforme', code == 0, out[-200:])

code, out = lancer(page(build="@quelquun [ici](https://exemple.invalid) <img src=x>"))
verifie('numéro de build piégé : page refusée, rien de son texte dans le rapport', code == 2 and '@quelquun' not in out and 'exemple.invalid' not in out, out[-200:])

code, out = lancer('<html><title>Vérification</title>Un instant…</html>')
verifie('page sans le code du jeu (vérification anti-robot) : inaccessible', code == 2 and 'inaccessible' in out, out[-200:])


def plante():
    raise ValueError('nombre illisible')


veille.main = plante
code = veille.principal()
verifie("plantage de l'analyse : état « erreur » (code 3), distinct d'une page inaccessible", code == 3)

print('\nTout est passé' if not echecs else f'\n{echecs} échec(s)')
sys.exit(1 if echecs else 0)
