"""The speed figure: how much earlier the rules date each turning point than the
committee announces it.  Every number is read from table_comparison_nber_vs_rules.csv."""
import pandas as pd, numpy as np, matplotlib, os
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib import font_manager
HOME=os.path.expanduser("~"); MNT=HOME+"/mnt" if os.path.isdir(HOME+"/mnt/Recession Papers") else HOME+"/Projects"
D=MNT+"/Recession Papers/Paper 2/data/"; F=MNT+"/Recession Papers/Paper 2/figures/"
os.makedirs(F,exist_ok=True)
C=pd.read_csv(D+"table_comparison_nber_vs_rules.csv")
BLUE="#2a78d6"; ORANGE="#eb6834"; INK="#0b0b0b"; INK2="#52514e"; GRID="#e6e5e1"; SURF="#ffffff"
avail={f.name for f in font_manager.fontManager.ttflist}
FONT=next((f for f in ["Lato","Carlito","Liberation Sans","DejaVu Sans"] if f in avail),"DejaVu Sans")
plt.rcParams.update({"font.family":FONT,"font.size":9,"axes.edgecolor":INK2,"axes.labelcolor":INK,
                     "xtick.color":INK2,"ytick.color":INK,"figure.facecolor":SURF,"axes.facecolor":SURF})
lab=lambda m: pd.Period(m,"M").strftime("%b %Y")
six=C.dropna(subset=["nber_peak_months"]).copy()
def rows(kind):
    if kind=="peak":
        return [(lab(r.nber_peak), r.sustained_onset_months, r.nber_peak_months,
                 pd.Timestamp(r.sustained_onset_call).strftime("%b %-d, %Y"),
                 pd.Timestamp(r.nber_peak_announced).strftime("%b %-d, %Y")) for _,r in six.iterrows()]
    return [(lab(r.nber_trough), r.end_call_months, r.nber_trough_months,
             pd.Timestamp(r.end_call).strftime("%b %-d, %Y"),
             pd.Timestamp(r.nber_trough_announced).strftime("%b %-d, %Y")) for _,r in six.iterrows()]
XMAX=max(max(r[2] for r in rows("peak")),max(r[2] for r in rows("trough")))+7.5
fig,axes=plt.subplots(1,2,figsize=(11.0,5.4),gridspec_kw=dict(wspace=0.40))
for ax,kind,title in [(axes[0],"peak","A.  Peaks — the start of a recession"),
                      (axes[1],"trough","B.  Troughs — the end of a recession")]:
    R=rows(kind); y=np.arange(len(R))[::-1]
    for yi,(nm,rule,nber,rd,nd) in zip(y,R):
        ax.plot([rule,nber],[yi,yi],color=GRID,lw=3.2,solid_capstyle="round",zorder=1)
        ax.plot([rule],[yi],marker="o",ms=7.5,color=ORANGE,zorder=3,ls="none")
        ax.plot([nber],[yi],marker="o",ms=7.5,color=BLUE,zorder=3,ls="none")
        mid=(rule+nber)/2
        n=int(round(nber-rule))
        ax.text(mid,yi+0.20,"%d month%s earlier"%(n,"" if n==1 else "s"),ha="center",va="bottom",
                fontsize=8.2,color=INK,fontweight="medium")
        ax.text(rule-0.55,yi-0.42,rd,ha="right",va="center",fontsize=6.9,color=ORANGE) if rule>=4 else ax.text(rule-0.55,yi-0.42,rd,ha="right",va="center",fontsize=6.9,color=ORANGE)
        ax.text(nber+0.55,yi-0.42,nd,ha="left",va="center",fontsize=6.9,color=BLUE)
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in R],fontsize=9)
    ax.set_xlim(-8.5,XMAX); ax.set_ylim(-1.0,len(R)-0.25); ax.set_xticks(range(0,int(XMAX)-4,5))
    ax.set_title(title,loc="left",fontsize=10,color=INK,pad=9)
    ax.set_xlabel("Months after the turning point",fontsize=8.4,color=INK2)
    ax.grid(axis="x",color=GRID,lw=0.7); ax.set_axisbelow(True)
    for s in ["top","right","left"]: ax.spines[s].set_visible(False)
    ax.tick_params(axis="y",length=0); ax.axvline(0,color=INK2,lw=0.9,zorder=2)
h=[plt.Line2D([],[],marker="o",ms=7.5,color=ORANGE,ls="none",label="Rule dates the turning point"),
   plt.Line2D([],[],marker="o",ms=7.5,color=BLUE,ls="none",label="NBER announces it")]
fig.legend(handles=h,loc="lower center",ncol=2,frameon=False,fontsize=9,bbox_to_anchor=(0.5,-0.045))
fig.suptitle("Figure 1.  How much earlier the rules date a turning point than the committee announces it",
             x=0.008,ha="left",fontsize=11.2,color=INK,y=1.03)
fig.text(0.008,-0.10,"The six recessions for which the committee issued a formal announcement. Zero is the month the committee "
         "eventually assigned. Orange is the release day on which the mechanical rule made its call from first-print data; blue is "
         "the day the committee announced. Every date is read from the deposited vintages; none is placed by hand.",
         ha="left",va="top",fontsize=7.6,color=INK2,wrap=True)
fig.savefig(F+"figure_speed.png",dpi=300,bbox_inches="tight",facecolor=SURF)
print("peaks, months earlier:",[round(r[2]-r[1]) for r in rows("peak")])
print("troughs, months earlier:",[round(r[2]-r[1]) for r in rows("trough")])
print("total months of lead:",sum(r[2]-r[1] for r in rows("peak"))+sum(r[2]-r[1] for r in rows("trough")))
