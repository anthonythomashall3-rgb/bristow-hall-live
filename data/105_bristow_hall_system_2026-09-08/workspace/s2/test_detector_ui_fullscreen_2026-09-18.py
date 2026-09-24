# Fullscreen test (18 Sep 2026): the graph fills the screen at 1512x982 and 1728x1117, and on a phone with no fullscreen API. Usage: python3 test_detector_ui_fullscreen_2026-09-18.py <url> <screenshot prefix>
import sys,asyncio
from playwright.async_api import async_playwright
page_file,prefix=sys.argv[1],sys.argv[2]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        for label,vp,noapi in [('mac14',{'width':1512,'height':982},False),('mac16',{'width':1728,'height':1117},False),('phone_noapi',{'width':390,'height':844},True)]:
            ctx=await b.new_context(viewport=vp, device_scale_factor=2 if label!='phone_noapi' else 3)
            if noapi: await ctx.add_init_script("delete Element.prototype.requestFullscreen; delete Element.prototype.webkitRequestFullscreen;")
            pg=await ctx.new_page(); errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
            await pg.goto(page_file); await pg.wait_for_timeout(500)
            await pg.click('#fs'); await pg.wait_for_timeout(900)
            r=await pg.evaluate("()=>{const c=document.querySelector('#chart'); const s=c.querySelector('svg'); const sr=s.getBoundingClientRect(); const pl=document.querySelector('#plot'); const pr=pl.getBoundingClientRect(); const fr=document.querySelector('.foot').getBoundingClientRect(); return {api:!!document.fullscreenElement, pfs:pl.classList.contains('pfs'), btn:document.querySelector('#fs').textContent, view:[innerWidth,innerHeight], plot:[pr.left,pr.top,pr.width,pr.height], svgDrawn:[+s.getAttribute('width'),+s.getAttribute('height')], svgShown:[Math.round(sr.width),Math.round(sr.height)], footBottom:Math.round(fr.bottom), clipped:pl.scrollHeight>pl.clientHeight+1}}")
            print(label, r)
            await pg.screenshot(path=f'{prefix}_{label}_fs.png')
            if noapi:
                await pg.keyboard.press('Escape'); await pg.wait_for_timeout(500)
            else:
                await pg.click('#fs'); await pg.wait_for_timeout(900)
            r2=await pg.evaluate("()=>{const s=document.querySelector('#chart svg'); return {api:!!document.fullscreenElement, pfs:document.querySelector('#plot').classList.contains('pfs'), svg:[+s.getAttribute('width'),+s.getAttribute('height')], btn:document.querySelector('#fs').textContent}}")
            print(label,'after exit', r2, 'errors', errs)
            await ctx.close()
        await b.close()
asyncio.run(main())
