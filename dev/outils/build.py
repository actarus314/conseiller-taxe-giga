#!/usr/bin/env python3
"""Génère les fichiers dérivés depuis conseiller.js (la seule source du code) :
- conseiller.user.js : script utilisateur (Tampermonkey, Violentmonkey)
- bookmarklet.txt    : favori autonome (le code entier dans l'adresse)
- index.html         : page d'installation, depuis dev/page-install.html
Usage : python3 dev/outils/build.py <version>   (ex. 2.1)
"""
import html, pathlib, re, sys, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[2]
version = sys.argv[1] if len(sys.argv) > 1 else '0.0'
src = (ROOT / 'conseiller.js').read_text(encoding='utf-8')

header = f"""// ==UserScript==
// @name         Conseiller — Taxe au Giga
// @namespace    https://github.com/actarus314/conseiller-taxe-giga
// @version      {version}
// @description  Indique le meilleur bonus à acheter dans Taxe au Giga. Ne clique et n'achète rien.
// @match        https://taxe-au-giga.fr/*
// @grant        none
// @run-at       document-idle
// @downloadURL  https://raw.githubusercontent.com/actarus314/conseiller-taxe-giga/main/conseiller.user.js
// @updateURL    https://raw.githubusercontent.com/actarus314/conseiller-taxe-giga/main/conseiller.user.js
// ==/UserScript==
"""
(ROOT / 'conseiller.user.js').write_text(header + src, encoding='utf-8')

# favori : commentaires de ligne et indentation retirés, puis encodage d'adresse
lines = [re.sub(r'^\s+', '', l) for l in src.split('\n') if not re.match(r'^\s*//', l)]
code = '\n'.join(l for l in lines if l)
bm = 'javascript:' + urllib.parse.quote(code, safe="()=>,;:'*!~-_.")
(ROOT / 'bookmarklet.txt').write_text(bm + '\n', encoding='utf-8')

loader = ("javascript:fetch('https://cdn.jsdelivr.net/gh/actarus314/conseiller-taxe-giga@v" + version +
          "/conseiller.js').then(r=>r.text()).then(eval)")
tpl = (ROOT / 'dev' / 'page-install.html').read_text(encoding='utf-8')
page = tpl.replace('__BM__', html.escape(bm, quote=True)).replace('__LOADER__', html.escape(loader, quote=True)).replace('__VERSION__', version)
(ROOT / 'index.html').write_text(page, encoding='utf-8')
print(f'v{version} : conseiller.user.js, bookmarklet.txt ({len(bm)} car.), index.html')
