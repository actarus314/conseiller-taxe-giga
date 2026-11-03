#!/usr/bin/env python3
"""Génère les fichiers dérivés depuis conseiller.js (la seule source du code) :
- conseiller.user.js : script utilisateur (Tampermonkey, Violentmonkey)
- bookmarklet-auto.txt : favori qui charge conseiller.js depuis GitHub Pages à chaque clic (toujours à jour)
- bookmarklet.txt    : favori autonome, version figée (le code entier dans l'adresse)
- index.html         : page d'installation, depuis dev/page-install.html
Usage : python3 dev/outils/build.py <version>   (ex. 2.1)
"""
import html, pathlib, re, sys, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[2]
version = sys.argv[1] if len(sys.argv) > 1 else '0.0'
# la version affichée par le panneau est écrite dans la source, à partir du seul argument de ce script
src = re.sub(r"const VERSION = '[^']*';", f"const VERSION = '{version}';", (ROOT / 'conseiller.js').read_text(encoding='utf-8'), count=1)
(ROOT / 'conseiller.js').write_text(src, encoding='utf-8')

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

# favori à jour : le paramètre change chaque minute, ce qui contourne le cache de 10 min de Pages
PAGES = 'https://actarus314.github.io/conseiller-taxe-giga/conseiller.js'
auto = ("javascript:(()=>{if(location.hostname!=='taxe-au-giga.fr')return alert('Conseiller : à lancer sur taxe-au-giga.fr');fetch('" + PAGES + "?m='+Math.floor(Date.now()/6e4))"
        ".then(r=>{if(!r.ok)throw r.status;return r.text()}).then(eval)"
        ".catch(e=>alert('Conseiller : chargement impossible depuis GitHub Pages ('+e+')'))})()")
(ROOT / 'bookmarklet-auto.txt').write_text(auto + '\n', encoding='utf-8')

tpl = (ROOT / 'dev' / 'page-install.html').read_text(encoding='utf-8')
page = (tpl.replace('__BM_AUTO__', html.escape(auto, quote=True)).replace('__BM__', html.escape(bm, quote=True))
        .replace('__VERSION__', version))
(ROOT / 'index.html').write_text(page, encoding='utf-8')
print(f'v{version} : conseiller.user.js, bookmarklet-auto.txt ({len(auto)} car.), bookmarklet.txt ({len(bm)} car.), index.html')
