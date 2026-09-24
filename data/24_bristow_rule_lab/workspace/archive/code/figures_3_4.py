import pandas as pd, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates
plt.rcParams.update({'font.family':'DejaVu Serif','font.size':8,'axes.linewidth':0.6,'figure.dpi':200})
import os
HERE=os.path.dirname(os.path.abspath(__file__))
D=os.path.join(HERE,'..','data','fred')+os.sep
DASH=os.path.join(HERE,'..','data','dashboard')+os.sep
OUT=os.path.join(HERE,'..','figures')+os.sep
REC=[("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),
     ("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04")]
def shade(ax,x0):
    for p,t in REC:
        p=pd.Timestamp(p);t=pd.Timestamp(t)
        if t<pd.Timestamp(x0): continue
        ax.axvspan(p,t,color='0.82',lw=0,zorder=0)
# Figure 3: SOS
d=pd.read_csv(D+'IURSA.csv',parse_dates=['observation_date']); d.columns=['date','iur']
d['iur']=pd.to_numeric(d.iur,errors='coerce'); d=d.dropna().reset_index(drop=True)
d['ma26']=d.iur.rolling(26).mean(); d['sos']=d.ma26-d.ma26.shift(1).rolling(52).min()
fig,ax=plt.subplots(figsize=(7.4,3.4)); shade(ax,'1972-01-01')
ax.plot(d.date,d.sos,lw=0.85,color='#8b1a1a')
ax.axhline(0.20,ls=(0,(3,2)),lw=0.8,color='k')
ax.set_ylim(-0.15,4.2); ax.set_ylabel('SOS indicator (pp)',fontsize=9)
ax.tick_params(labelsize=8.5)
ax.set_title('The SOS Indicator, 1972–2026',fontsize=11,pad=8)
ax.text(pd.Timestamp('1973-01-01'),0.42,'threshold +0.20',fontsize=8)
ax.annotate('plateau at 0.2000,\ntwelve weeks, 2023',xy=(pd.Timestamp('2023-06-01'),0.24),
    xytext=(pd.Timestamp('2004-01-01'),1.45),fontsize=8.5,ha='left',
    arrowprops=dict(arrowstyle='-',lw=0.6,color='0.35'))
ax.text(pd.Timestamp('1991-06-01'),3.80,'2020 peak 10.07; axis clipped at 4.0',fontsize=8,color='0.4')
for s_ in ['top','right']: ax.spines[s_].set_visible(False)
fig.tight_layout(); fig.savefig(OUT+'fig3.png',bbox_inches='tight'); plt.close(fig)

# Figure 4: Michez rule (authors' dashboard) + Sahm
mi=pd.read_csv(DASH+'michaillat_saez_recession_indicator.csv',parse_dates=['Date']); mi.columns=['date','m']
sc=pd.read_csv(D+'SAHMCURRENT.csv',parse_dates=['observation_date']); sc.columns=['date','s']
sc['s']=pd.to_numeric(sc.s,errors='coerce')
fig,ax=plt.subplots(figsize=(7.4,3.4))
sub=mi[(mi.date>='2021-06-01')]; subs=sc[(sc.date>='2021-06-01')]
ax.plot(sub.date,sub.m,lw=1.2,color='#1f4e79',label='Michez indicator')
ax.plot(subs.date,subs.s,lw=1.2,color='#8b1a1a',label='Sahm indicator')
ax.axhline(0.29,ls=(0,(3,2)),lw=0.8,color='#1f4e79'); ax.axhline(0.50,ls=(0,(3,2)),lw=0.8,color='#8b1a1a')
ax.text(pd.Timestamp('2021-07-01'),0.325,'Michez threshold 0.29',fontsize=8,color='#1f4e79')
ax.text(pd.Timestamp('2021-07-01'),0.535,'Sahm threshold 0.50',fontsize=8,color='#8b1a1a')
ax.set_ylim(-0.1,1.05); ax.set_ylabel('Indicator (pp)',fontsize=9)
ax.tick_params(labelsize=8.5)
ax.set_title('Both Alarms Peak in August 2024',fontsize=11,pad=8)
ax.plot([pd.Timestamp('2024-08-01')],[0.57],marker='o',ms=4.2,color='#8b1a1a',zorder=7)
ax.plot([pd.Timestamp('2024-08-01')],[0.54],marker='o',ms=4.2,color='#1f4e79',zorder=7)
ax.annotate('Aug 2024:\nSahm 0.57, Michez 0.54',xy=(pd.Timestamp('2024-08-01'),0.58),
    xytext=(pd.Timestamp('2024-11-01'),0.88),fontsize=8.5,ha='left',
    arrowprops=dict(arrowstyle='-',lw=0.6,color='0.35'))
ax.legend(fontsize=8.5,frameon=False,loc='upper left',bbox_to_anchor=(0.015,0.99))
for s_ in ['top','right']: ax.spines[s_].set_visible(False)
ax.set_xlim(pd.Timestamp('2021-06-01'),pd.Timestamp('2026-09-01'))
fig.tight_layout(); fig.savefig(OUT+'fig4.png',bbox_inches='tight'); plt.close(fig)
print("fig3, fig4 done")
