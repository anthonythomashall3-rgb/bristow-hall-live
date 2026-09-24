# Peak-hold test (18 Sep 2026): how wide the hold at the 2008-09 peak is at each zoom. Usage: python3 test_detector_peakhold_2026-09-18.py <page url or file>
import asyncio,sys,json
from playwright.async_api import async_playwright
f=sys.argv[1]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1497,'height':1000}); errs=[]; pg.on('pageerror',lambda e: errs.append(str(e)))
        await pg.goto(f if f.startswith('http') else 'file://'+f); await pg.wait_for_timeout(400)
        async def setwin(a,bb):
            await pg.evaluate("([a,b])=>{const d0=document.querySelector('#d0'),d1=document.querySelector('#d1'); d0.value=a; d1.value=b; d1.dispatchEvent(new Event('change'))}",[a,bb]); await pg.wait_for_timeout(200)
        async def probe(label, peak):
            # x of the peak in css px, then sweep +-14 px in 0.5 px steps at the plot's bottom
            g=await pg.evaluate("""(pk)=>{const s=document.querySelector('#chart svg'); const r=s.getBoundingClientRect(); const W=+s.getAttribute('width'); const k=W/r.width; const ml=56,mr=16; const pw=W-ml-mr;
                const a=Date.parse(document.querySelector('#d0').value), b=(()=>{const v=document.querySelector('#d1').value; const last=S.series.dates[S.series.dates.length-1]; return Date.parse(v)+(v===last?45*86400000:0);})(); const p=pk.split('-'); const t=Date.UTC(+p[0],+p[1]-1,+p[2]);
                const xs=(ml+(t-a)/(b-a)*pw)/k+r.left; const n=S.series.dates.filter(d=>{const q=d.split('-'); const tt=Date.UTC(+q[0],+q[1]-1,+q[2]); return tt>=a&&tt<=b;}).length; return {x:xs, top:r.top, h:r.height, rho:n/(pw/k)}}""",peak)
            MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']; y,m,d=peak.split('-'); plab=f"{MON[int(m)-1]} {int(d)}, {y}"
            held=[]; seen=set(); steps=[i*0.5 for i in range(-28,29)]
            for dx in steps:
                await pg.mouse.move(g['x']+dx, g['top']+g['h']*0.9); await pg.wait_for_timeout(35)
                lab=await pg.evaluate("()=>{const t=document.querySelector('#cur text'); return t?t.textContent.split(':')[0]:null}")
                seen.add(lab)
                if lab==plab: held.append(dx)
            span=await pg.evaluate("""([x0,x1])=>{const s=document.querySelector('#chart svg'); const r=s.getBoundingClientRect(); const W=+s.getAttribute('width'); const k=W/r.width; const ml=56,mr=16; const pw=W-ml-mr;
                const a=Date.parse(document.querySelector('#d0').value), b=(()=>{const v=document.querySelector('#d1').value; const last=S.series.dates[S.series.dates.length-1]; return Date.parse(v)+(v===last?45*86400000:0);})(); return S.series.dates.filter(d=>{const q=d.split('-'); const t=Date.UTC(+q[0],+q[1]-1,+q[2]); const x=(ml+(t-a)/(b-a)*pw)/k+r.left; return x>=x0&&x<=x1;}).length}""",[g['x']-14,g['x']+14])
            hw=(min(held),max(held)) if held else None
            print(f"{label:18s} days per px {g['rho']:.2f}: peak held from {hw[0] if hw else '-'} to {hw[1] if hw else '-'} px; days within +-14 px {span}")
        pk=await pg.evaluate("()=>{ const D=S.series.dates,V=S.series.values; let best=-1,bi=-1; for(let k=0;k<D.length;k++){ if(D[k]>='2008-01-01'&&D[k]<'2010-01-01'&&V[k]>=best){best=V[k];bi=k;} } return D[bi]; }")
        print('2008-09 peak', pk)
        await pg.click('.ranges a[data-range="max"]'); await pg.wait_for_timeout(200); await probe('Max',pk)
        for lab,a,bb in [('20 years','1994-06-01','2014-06-01'),('10 years','2004-06-01','2014-06-01'),('5 years','2006-06-01','2011-06-01'),('3 years','2007-06-01','2010-06-01'),('2 years','2008-01-01','2010-01-01'),('1 year','2008-12-01','2009-12-01')]:
            await setwin(a,bb); await probe(lab,pk)
        print('errors',errs)
        await b.close()
asyncio.run(main())
