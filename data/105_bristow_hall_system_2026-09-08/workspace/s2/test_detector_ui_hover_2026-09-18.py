# Hover test (18 Sep 2026): slow sweeps at 1Y/5Y/10Y/Max must land on every observation; fast sweep keeps the marker at the pointer. Needs Playwright + Chromium. Usage: python3 test_detector_ui_hover_2026-09-18.py https://bhrrealtime.pages.dev/detector/
import sys,asyncio,json
from playwright.async_api import async_playwright
page_file=sys.argv[1]; mode=sys.argv[2] if len(sys.argv)>2 else 'all'
OBS="""()=>{ window.__seen=[]; const ch=document.querySelector('#chart'); const rec=()=>{ const t=document.querySelector('#cur text'); if(t){ const l=t.textContent.split(':')[0]; if(window.__seen[window.__seen.length-1]!==l) window.__seen.push(l);} };
  new MutationObserver(rec).observe(ch,{subtree:true,childList:true,characterData:true}); }"""
FMTD="""const MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']; const f=s=>{const p=s.split('-');return MON[+p[1]-1]+' '+(+p[2])+', '+p[0];};"""
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        pg=await b.new_page(viewport={'width':1512,'height':982})
        errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
        await pg.goto(page_file); await pg.wait_for_timeout(500)
        await pg.evaluate(OBS)
        async def geo():
            return await pg.evaluate("()=>{const s=document.querySelector('#chart svg'); const r=s.getBoundingClientRect(); return [r.left,r.top,r.width,r.height]}")
        async def span_points(x0,x1):
            # points whose drawn x lies in [x0,x1] css px (reads the date axis from inputs)
            return await pg.evaluate("""([x0,x1])=>{ const s=document.querySelector('#chart svg'); const r=s.getBoundingClientRect(); const W=+s.getAttribute('width'); const k=W/r.width; const ml=56,mr=16; const pw=W-ml-mr;
               const a=Date.parse(document.querySelector('#d0').value), b=Date.parse(document.querySelector('#d1').value)+45*86400000; """+FMTD+"""
               const out=[]; for(const d of S.series.dates){ const p=d.split('-'); const t=Date.UTC(+p[0],+p[1]-1,+p[2]); const x=(ml+(t-a)/(b-a)*pw)/k+r.left; if(x>=x0&&x<=x1) out.push(f(d)); } return out; }""",[x0,x1])
        async def slow_sweep(x0,x1,y,wait,step=1.0):
            await pg.evaluate("()=>{window.__seen=[]}")
            x=x0
            while x<=x1:
                await pg.mouse.move(x,y); await pg.wait_for_timeout(wait); x+=step
            await pg.wait_for_timeout(300)
            return await pg.evaluate("()=>window.__seen")
        for rng,wait,span in [('1',10,400),('5',60,300),('10',90,200),('max',260,25)]:
            await pg.click('.ranges a[data-range="%s"]'%rng); await pg.wait_for_timeout(300); await pg.evaluate(OBS)
            L,T,Wd,Hd=await geo(); x0=L+400; x1=x0+span; y=T+Hd*0.55
            seen=await slow_sweep(x0,x1,y,wait)
            pts=await span_points(x0+2,x1-2)
            missed=[d for d in pts if d not in set(seen)]
            print(f'range {rng}: slow sweep over {span}px: {len(pts)} points in span, missed {len(missed)}', missed[:5])
        # fast sweep at Max: marker must stay near the pointer
        await pg.click('.ranges a[data-range="max"]'); await pg.wait_for_timeout(300)
        L,T,Wd,Hd=await geo()
        await pg.mouse.move(L+200,T+200); await pg.mouse.move(L+900,T+200,steps=15); await pg.wait_for_timeout(250)
        gap=await pg.evaluate("([px])=>{const l=document.querySelector('#cur line'); const s=document.querySelector('#chart svg'); const r=s.getBoundingClientRect(); const k=+s.getAttribute('width')/r.width; return l? Math.abs(+l.getAttribute('x1')/k + r.left - px):null}",[L+900])
        print('fast sweep at Max: marker distance from pointer after 250 ms (px):',gap)
        print('errors',errs)
        await b.close()
asyncio.run(main())
