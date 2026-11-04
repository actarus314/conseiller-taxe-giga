"""Captures d'écran du README (captures/*.png, à réduire ensuite à 60 %).
Le site du jeu bloque Chrome sans interface (page de vérification) : les captures se font sur une copie
locale de sa page, servie sur 127.0.0.1:8765, avec un faux serveur (réponses /api/* simulées dans Chrome,
rien n'est envoyé au vrai serveur) et l'état réel d'une partie à deux moments du 03/11/2026.
  curl -s https://taxe-au-giga.fr/ -o <dossier>/index.html
  python3 -m http.server 8765 --directory <dossier> --bind 127.0.0.1 &
  python3 dev/outils/captures.py <dossier de sortie>
"""
import json, os, pathlib, sys, time
from playwright.sync_api import sync_playwright
SRC = (pathlib.Path(__file__).resolve().parents[2] / 'conseiller.js').read_text(encoding='utf-8')
O1152 = dict(doigt=14, stagiaire=32, chat=29, hamster=25, souris=6, bot=20, fax=15, commission=11, gant=9, satellite=2)
O1236 = dict(doigt=36, stagiaire=39, chat=35, hamster=32, souris=25, bot=27, fax=22, commission=18, gant=20, satellite=9)
def fake(state):
    def h(route):
        u = route.request.url
        if u.endswith('/api/sync'):
            body = dict(ok=True, build='2026-11-03e', code=None, n=0, clicks=0, bought=[], offline={'s': 0, 'visits': 0}, refund=0,
                        autoclick=None, now=int(time.time() * 1000), gold=None, buffs=[], totalCount=124051689179403, uniques=39371, realCount=85144063,
                        me={'id': 'demo', 'total': state['produced'], 'rank': None}, state=dict(state, serious=False))
            route.fulfill(status=200, content_type='application/json', body=json.dumps(body))
        else:
            route.fulfill(status=200, content_type='application/json', body='{"ok":false}')
    return h
def scene(p, name, owned, wallet, produced, mode, vp, clicks=0, hist=False, mobile=False, place=None, minimize=False):
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'],
                          proxy={'server': os.environ['HTTPS_PROXY'], 'bypass': '127.0.0.1,localhost'} if os.environ.get('HTTPS_PROXY') else None)
    ctx = b.new_context(viewport=vp, device_scale_factor=2, is_mobile=mobile, has_touch=mobile, locale='fr-FR', timezone_id='Europe/Paris')
    pg = ctx.new_page()
    pg.route('**://*taxe-au-giga.fr/**', lambda r: r.abort())  # rien ne doit atteindre le vrai jeu
    pg.route('**/api/**', fake(dict(produced=produced, wallet=wallet, owned=owned, rate=0, click=0)))
    pg.route('**/*.pdf*', lambda r: r.abort())
    pg.add_init_script(f"try{{localStorage.setItem('tagAdv-mode','{mode}')}}catch(e){{}}")
    if hist:  # 2 h de jeu observé : une série de 2 min à 5 clics/s toutes les 20 min (0.5 clic/s en moyenne)
        pg.add_init_script("try{const m0=Math.floor(Date.now()/6e4),h={};for(let a=1;a<=120;a++)h[m0-a]=a%20<2?300:0;"
                           "localStorage.setItem('tagAdv-clics',JSON.stringify(h));localStorage.setItem('tagAdv-vu',String(m0-120))}catch(e){}")
    pg.goto('http://127.0.0.1:8765/', wait_until='domcontentloaded', timeout=60000)
    pg.wait_for_function("document.querySelectorAll('#shop button.item').length > 5", timeout=30000)
    pg.evaluate("document.querySelectorAll('.banner, .toast, .bubble').forEach(e => e.remove())")
    pg.add_style_tag(content='#confetti{display:none!important}')
    pg.evaluate(SRC)
    shop = pg.locator('#shop')
    shop.scroll_into_view_if_needed()
    pg.evaluate("window.scrollBy(0, document.querySelector('#shop').getBoundingClientRect().top - 90)")
    if clicks:
        # fenêtres d'annonce du jeu retirées d'abord : posées sur TAXER, elles recevraient les clics
        pg.evaluate("""[...document.body.querySelectorAll('*')].filter(e => getComputedStyle(e).position === 'fixed' && !e.closest('#tagAdv, #stickyTax, header, .site')).forEach(e => e.remove())""")
        btn = pg.locator('#taxBtn')  # bouton principal : le bouton flottant n'est pas toujours à l'écran
        btn.scroll_into_view_if_needed(); pg.wait_for_timeout(600)
        for _ in range(clicks):
            btn.click(force=True); pg.wait_for_timeout(200)  # 5 clics par seconde
    pg.wait_for_timeout(1200)
    # le meilleur bonus au milieu de l'écran, le panneau posé là où il ne le cache pas
    pg.evaluate("(() => { const b = document.querySelector('.tagAdvBest'); if (b) window.scrollBy(0, b.getBoundingClientRect().top - innerHeight * %s); })()" % ('0.62' if mobile else '0.45'))
    if place:  # glissé par son en-tête, comme à la main : le panneau garde alors cette place
        hb = pg.locator('#tagAdv header').bounding_box(); bx = pg.locator('#tagAdv').bounding_box()
        gx, gy = hb['x'] + 20, hb['y'] + hb['height'] / 2
        pg.mouse.move(gx, gy); pg.mouse.down(); pg.mouse.move(place[0] + gx - bx['x'], place[1] + gy - bx['y'], steps=8); pg.mouse.up()
    if minimize: pg.evaluate("document.querySelector('#tagAdv').classList.add('min')")
    # fenêtres d'annonce du jeu retirées : tout élément fixe autre que le panneau, le bouton TAXER et l'en-tête
    pg.evaluate("""[...document.body.querySelectorAll('*')].filter(e => getComputedStyle(e).position === 'fixed' && !e.closest('#tagAdv, #stickyTax, header, .site')).forEach(e => e.remove())""")
    pg.wait_for_timeout(400)
    pg.evaluate("document.querySelectorAll('.banner, .toast, .bubble').forEach(e => e.remove())")
    info = pg.evaluate("({ now: document.querySelector('#tagAdv .now').innerText, ft: document.querySelector('#tagAdv .ft').innerText, best: document.querySelector('.tagAdvBest')?.dataset.id })")
    top = 64 if mobile else 80  # sous l'en-tête du jeu (compteurs en direct, vides hors ligne)
    pg.screenshot(path=os.path.join(OUT, name), clip={'x': 0, 'y': top, 'width': vp['width'], 'height': vp['height'] - top})
    print(name, json.dumps(info, ensure_ascii=False))
    b.close()
if __name__ == '__main__':
    OUT = sys.argv[1]
    with sync_playwright() as p:
        scene(p, 'passif.png', O1152, 9847633, 41373467, 'passif', {'width': 1280, 'height': 800}, place=[70, 130])
        scene(p, 'auto-clics.png', O1236, 20600000, 160000000, 'auto', {'width': 1280, 'height': 800}, clicks=60, hist=True, place=[70, 130])
        scene(p, 'mobile.png', O1152, 9847633, 41373467, 'auto', {'width': 390, 'height': 844}, mobile=True)
