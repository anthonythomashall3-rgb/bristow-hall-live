import pandas as pd, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.dates as mdates
plt.rcParams.update({'font.family':'DejaVu Serif','font.size':8,'axes.linewidth':0.6,
                     'xtick.direction':'out','ytick.direction':'out','figure.dpi':200})
import os
HERE=os.path.dirname(os.path.abspath(__file__))
D=os.path.join(HERE,'..','data','fred')+os.sep
DASH=os.path.join(HERE,'..','data','dashboard')+os.sep
OUT=os.path.join(HERE,'..','figures')+os.sep
def load(n,c=None):
    d=pd.read_csv(D+n+'.csv',parse_dates=['observation_date']); d.columns=['date','v']
    d['v']=pd.to_numeric(d.v,errors='coerce'); return d.dropna().reset_index(drop=True)

REC=[("1948-11","1949-10"),("1953-07","1954-05"),("1957-08","1958-04"),("1960-04","1961-02"),
     ("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),
     ("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04")]
def shade(ax,x0=None,x1=None):
    for p,t in REC:
        p=pd.Timestamp(p); t=pd.Timestamp(t)
        if x0 is not None and t<pd.Timestamp(x0): continue
        ax.axvspan(p,t,color='0.82',lw=0,zorder=0)

# ---------------- Figure 1: yield curve ----------------
t=load('T10Y2Y')
fig,ax=plt.subplots(figsize=(7.4,3.4))
shade(ax,'1976-01-01')
ax.plot(t.date,t.v,lw=0.7,color='#1f4e79')
ax.axhline(0,color='k',lw=0.8)
ax.set_ylabel('10-year minus 2-year yield (pp)',fontsize=9)
ax.tick_params(labelsize=8.5)
ax.set_title('The 10Y–2Y Treasury Spread, 1976–2026',fontsize=11,pad=8)
ax.annotate('537 consecutive trading days below zero,\nJul 2022 – Aug 2024',
    xy=(pd.Timestamp('2023-07-03'),-1.08),xytext=(pd.Timestamp('2004-01-01'),-1.75),
    fontsize=8.5,ha='left',arrowprops=dict(arrowstyle='-',lw=0.6,color='0.35'))
for s_ in ['top','right']: ax.spines[s_].set_visible(False)
ax.set_xlim(pd.Timestamp('1976-01-01'),pd.Timestamp('2026-12-31'))
fig.tight_layout(); fig.savefig(OUT+'fig1.png',bbox_inches='tight'); plt.close(fig)

u=load('UNRATE'); sc=load('SAHMCURRENT')
fig,axes=plt.subplots(2,1,figsize=(7.4,5.2),sharex=True,gridspec_kw={'height_ratios':[1.35,1]})

def dbox(ax,a,b,y0,y1,shade_):
    a=pd.Timestamp(a); b=pd.Timestamp(b)
    ax.add_patch(Rectangle((mdates.date2num(a),y0),mdates.date2num(b)-mdates.date2num(a),y1-y0,
        fill=False,ls=(0,(2.2,1.6)),lw=1.1,ec=shade_,zorder=6))

DARK='0.25'; LIGHT='0.62'

ax=axes[0]; shade(ax); ax.plot(u.date,u.v,lw=0.85,color='#1f4e79')
ax.set_ylabel('Unemployment rate (%)',fontsize=9); ax.set_ylim(0,16)
ax.set_title('Unemployment, the Sahm Rule and the Missing Gray Bar',fontsize=11,pad=8)
dbox(ax,'2024-04-01','2024-08-01',0,16,DARK)
dbox(ax,'2003-04-01','2003-07-01',0,16,LIGHT)
ax.annotate('Apr–Aug 2024',xy=(pd.Timestamp('2024-06-01'),6.0),
    xytext=(pd.Timestamp('2016-06-01'),1.4),fontsize=8.5,color=DARK,ha='center',
    arrowprops=dict(arrowstyle='-',lw=0.6,color=DARK))
ax.annotate('1962–63',xy=(pd.Timestamp('1963-01-01'),5.8),xytext=(pd.Timestamp('1959-06-01'),1.4),
    fontsize=8,ha='center',arrowprops=dict(arrowstyle='-',lw=0.5,color='0.45'))
ax.annotate('1966–67',xy=(pd.Timestamp('1967-01-01'),3.7),xytext=(pd.Timestamp('1970-06-01'),1.4),
    fontsize=8,ha='center',arrowprops=dict(arrowstyle='-',lw=0.5,color='0.45'))
ax.annotate('1985–86',xy=(pd.Timestamp('1986-06-01'),7.1),xytext=(pd.Timestamp('1990-06-01'),13.0),
    fontsize=8,ha='center',arrowprops=dict(arrowstyle='-',lw=0.5,color='0.45'))
ax.annotate('2002–03',xy=(pd.Timestamp('2003-01-01'),5.9),xytext=(pd.Timestamp('1998-06-01'),1.2),
    fontsize=8,ha='center',arrowprops=dict(arrowstyle='-',lw=0.5,color='0.45'))
for s_ in ['top','right']: ax.spines[s_].set_visible(False)
ax.tick_params(labelsize=8.5)

ax=axes[1]; shade(ax); ax.plot(sc.date,sc.v,lw=0.85,color='#8b1a1a')
ax.axhline(0.50,ls=(0,(3,2)),lw=0.8,color='k')
ax.set_ylabel('Sahm indicator (pp)',fontsize=9); ax.set_ylim(-0.4,4.6)
ax.text(pd.Timestamp('1949-06-01'),0.70,'threshold +0.50',fontsize=8)
ax.plot([pd.Timestamp('2024-08-01')],[0.57],marker='o',ms=4.2,color='k',zorder=7)
ax.annotate('peak 0.57, Aug 2024',xy=(pd.Timestamp('2024-08-01'),0.70),
    xytext=(pd.Timestamp('2003-06-01'),2.60),fontsize=8.5,ha='left',
    arrowprops=dict(arrowstyle='-',lw=0.6,color='0.35'))
dbox(ax,'2024-04-01','2024-08-01',-0.4,4.6,DARK)
dbox(ax,'2003-04-01','2003-07-01',-0.4,4.6,LIGHT)
for s_ in ['top','right']: ax.spines[s_].set_visible(False)
ax.tick_params(labelsize=8.5)
ax.set_xlim(pd.Timestamp('1948-01-01'),pd.Timestamp('2026-10-01'))
fig.tight_layout(); fig.savefig(OUT+'fig2.png',bbox_inches='tight'); plt.close(fig)
print("fig1, fig2 done")
