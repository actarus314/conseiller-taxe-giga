"""Vérification dans Chrome, sur la copie locale du jeu servie pour dev/outils/captures.py (même mode d'emploi) :
position du panneau (jamais sur le grand bouton TAXER, à 4 largeurs d'écran, en haut de page et après défilement)
et clics du mode mini du jeu (fenêtre surgissante, et fenêtre « image dans l'image » ouverte avant le panneau).
  python3 dev/outils/verif-navigateur.py
"""
import pathlib, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from captures import fake  # faux serveur du jeu, commun aux captures  # noqa: E402
SRC = (pathlib.Path(__file__).resolve().parents[2] / 'conseiller.js').read_text(encoding='utf-8')
O = dict(doigt=36, stagiaire=39, chat=35, hamster=32, souris=25, bot=27, fax=22, commission=18, gant=20, satellite=9)
R = """(() => { const R = s => { const e = document.querySelector(s); const r = e.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)]; };
  const a = R('#tagAdv'), b = R('#taxBtn'); const ov = a[0] < b[2] && a[2] > b[0] && a[1] < b[3] && a[3] > b[1] && b[3] > 0 && b[1] < innerHeight; return { panneau: a, taxer: b, recouvre: ov }; })()"""
def page(p, vp, pip=True):
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
    ctx = b.new_context(viewport=vp)
    pg = ctx.new_page()
    pg.route('**://*taxe-au-giga.fr/**', lambda r: r.abort()); pg.route('**/api/**', fake(dict(produced=160000000, wallet=20600000, owned=O, rate=0, click=0)))
    if not pip: pg.add_init_script("delete window.documentPictureInPicture; delete Window.prototype.documentPictureInPicture")
    pg.goto('http://127.0.0.1:8765/', wait_until='domcontentloaded')
    pg.wait_for_function("document.querySelectorAll('#shop button.item').length > 5", timeout=30000)
    pg.evaluate("[...document.body.querySelectorAll('*')].filter(e => getComputedStyle(e).position === 'fixed' && !e.closest('#stickyTax, header, .site')).forEach(e => e.remove())")
    return b, ctx, pg
with sync_playwright() as p:
    for vp in ({'width': 1280, 'height': 800}, {'width': 1440, 'height': 900}, {'width': 1920, 'height': 1080}, {'width': 390, 'height': 844}):
        b, ctx, pg = page(p, vp); pg.evaluate(SRC); pg.wait_for_timeout(500)
        hd = pg.evaluate(R)
        pg.evaluate("window.scrollBy(0, 600)"); pg.wait_for_timeout(500); bas = pg.evaluate(R)
        print(vp['width'], 'haut de page :', hd, '| après défilement :', bas); b.close()
    # mode mini, fenêtre surgissante (navigateur sans image dans l'image), ouverte panneau ouvert
    b, ctx, pg = page(p, {'width': 1280, 'height': 800}, pip=False); pg.evaluate(SRC)
    with ctx.expect_page() as pi: pg.locator('#miniBtn').click()
    mini = pi.value; mini.wait_for_selector('#mTax')
    for _ in range(10): mini.locator('#mTax').click(); mini.wait_for_timeout(150)
    c = pg.evaluate("window.__tagAdv.state().cadence"); print('fenêtre surgissante : clics comptés', c['tot'], '| série', round(c['rate'], 1))
    pg.evaluate("window.__tagAdv.stop()"); print('window.open rendu au jeu :', pg.evaluate("!String(window.open).includes('watchMini') && !String(window.open).includes('winOpen')")); b.close()
    # image dans l'image : ouverte avant le panneau, puis panneau lancé
    b, ctx, pg = page(p, {'width': 1280, 'height': 800}); pg.locator('#miniBtn').click(); pg.wait_for_timeout(800)
    print('image dans l’image ouverte :', pg.evaluate("!!(window.documentPictureInPicture && documentPictureInPicture.window)"))
    pg.evaluate(SRC); pg.wait_for_timeout(300); print('fenêtre suivie par le panneau :', pg.evaluate("window.__tagAdv.state().minis")); b.close()
