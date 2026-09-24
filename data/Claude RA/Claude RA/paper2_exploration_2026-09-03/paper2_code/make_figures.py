"""Figures 1–3 of Paper 2, drawn from data/table_comparison_nber_vs_rules.csv. No number is placed by hand."""
import pandas as pd, numpy as np, matplotlib, os
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib import font_manager
HOME=os.path.expanduser("~"); MNT = HOME+"/mnt" if os.path.isdir(HOME+"/mnt/Recession Papers") else HOME+"/Projects"
D=MNT+"/Recession Papers/Paper 2/data/"; F=MNT+"/Recession Papers/Paper 2/figures/"
C=pd.read_csv(D+"table_comparison_nber_vs_rules.csv")
BLUE="#2a78d6"; ORANGE="#eb6834"; INK="#0b0b0b"; INK2="#52514e"; GRID="#e6e5e1"; SURF="#ffffff"
avail={f.name for f in font_manager.fontManager.ttflist}
FONT=next((f for f in ["Lato","Carlito","Liberation Sans","DejaVu Sans"] if f in avail),"DejaVu Sans")
plt.rcParams.update({"font.family":FONT,"font.size":9,"axes.edgecolor":INK2,"axes.labelcolor":INK,"xtick.color":INK2,"ytick.color":INK,
                     "axes.titleweight":"medium","figure.facecolor":SURF,"axes.facecolor":SURF})
lab=lambda m: pd.Period(m,"M").strftime("%b %Y")
fmt=lambda d: pd.Timestamp(d).strftime("%b %-d, %Y")
def style(ax):
    ax.grid(axis="x", color=GRID, lw=0.7); ax.set_axisbelow(True)
    for s in ["top","right","left"]: ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0); ax.axvline(0, color=INK2, lw=0.8, zorder=3)
def panel(ax, months, names, notes, color, title, xmax, ref=None):
    y=np.arange(len(months))[::-1]
    ax.barh(y, months, height=0.52, color=color, edgecolor="none", zorder=2)
    for yi,m,n in zip(y,months,notes):
        ax.text(max(m,0)+0.3, yi, f"{m:g} mo  ·  {n}", va="center", ha="left", fontsize=7.8, color=INK2)
    if ref is not None:
        for yi,r in zip(y,ref):
            if pd.notna(r): ax.plot([r],[yi], marker="o", ms=6.5, mfc="white", mec=BLUE, mew=1.4, zorder=4, ls="none")
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=8.5)
    ax.set_xlim(min(0,min(months))-0.6, xmax); ax.set_title(title, loc="left", fontsize=9.8, color=INK, pad=7)
    style(ax)
# ---------------- Figure 1: the committee ----------------
six=C.dropna(subset=["nber_peak_months"]).copy()
fig,axes=plt.subplots(2,1,figsize=(8.2,6.3), gridspec_kw=dict(hspace=0.5))
panel(axes[0], six.nber_peak_months.tolist(), [f"Peak {lab(p)}" for p in six.nber_peak], [f"announced {fmt(d)}" for d in six.nber_peak_announced], BLUE,
      "A. Peaks — months from the peak month to the NBER's announcement", 26)
panel(axes[1], six.nber_trough_months.tolist(), [f"Trough {lab(t)}" for t in six.nber_trough], [f"announced {fmt(d)}" for d in six.nber_trough_announced], BLUE,
      "B. Troughs — months from the trough month to the NBER's announcement", 26)
axes[1].set_xlabel("Months after the turning point (NBER convention: announcement month less turning-point month)", fontsize=8.3, color=INK2)
fig.suptitle("Figure 1. The committee's lag: the six recessions with formal announcements, 1980–2020", x=0.01, ha="left", fontsize=10.8, color=INK, y=0.995)
fig.savefig(F+"figure1_nber_lags.png", dpi=300, bbox_inches="tight", facecolor=SURF); plt.close(fig)
# ---------------- Figure 2: the rules ----------------
fig,axes=plt.subplots(2,1,figsize=(8.2,7.7), gridspec_kw=dict(hspace=0.42))
pk_notes=[]
for _,r in C.iterrows():
    n=f"called {fmt(r.first_onset_call)}"
    if r.first_onset_months<0: n+=" (before the peak month)"
    if r.sustained_onset_call!=r.first_onset_call: n+=f"; one-month touch, re-crossed {fmt(r.sustained_onset_call)}"
    pk_notes.append(n)
tr_notes=[]
for _,r in C.iterrows():
    n=f"called {fmt(r.end_call)}, trough dated {lab(r.bristow_end_month)}"
    if r.end_revisions>0: n+=" (revised once)"
    tr_notes.append(n)
panel(axes[0], C.first_onset_months.tolist(), [f"Peak {lab(p)}" for p in C.nber_peak], pk_notes, ORANGE,
      "A. Peaks — months from the NBER peak month to the Sahm Rule's first crossing release", 26)
panel(axes[1], C.end_call_months.tolist(), [f"Trough {lab(t)}" for t in C.nber_trough], tr_notes, ORANGE,
      "B. Troughs — months from the NBER trough month to the Bristow Rule's confirming release", 26)
axes[1].set_xlabel("Months after the turning point (same convention as Figure 1); every call computed from the data as first published", fontsize=8.3, color=INK2)
fig.suptitle("Figure 2. The rules' lag: the nine recessions covered by real-time unemployment vintages, 1960–2020", x=0.01, ha="left", fontsize=10.8, color=INK, y=0.995)
fig.savefig(F+"figure2_rule_lags.png", dpi=300, bbox_inches="tight", facecolor=SURF); plt.close(fig)
# ---------------- Figure 3: box-and-strip comparison ----------------
fig,axes=plt.subplots(1,2,figsize=(8.2,4.6), sharey=True, gridspec_kw=dict(wspace=0.12))
def boxpanel(ax, comm, rule, years, title):
    data=[comm, rule]; cols=[BLUE, ORANGE]
    POS=[0,1.35]
    bp=ax.boxplot(data, positions=POS, widths=0.38, whis=(0,100), patch_artist=True, showfliers=False, zorder=2,
                  medianprops=dict(color=INK, lw=1.6), whiskerprops=dict(color=INK2, lw=1), capprops=dict(color=INK2, lw=1))
    for patch,c in zip(bp["boxes"],cols): patch.set(facecolor=c, alpha=0.22, edgecolor=c, linewidth=1.4)
    for i,(vals,c) in enumerate(zip(data,cols)):
        groups={}
        for v,yr in zip(vals,years): groups.setdefault(v,[]).append(yr)
        for v,yrs_ in sorted(groups.items()):
            k=len(yrs_); xs=POS[i]+np.linspace(-0.07*(k-1),0.07*(k-1),k)
            ax.plot(xs,[v]*k, ls="none", marker="o", ms=7, mfc=c, mec="white", mew=1.2, zorder=4)
            txt=", ".join(yrs_)
            ax.annotate(txt,(xs.max(),v), xytext=(10,0), textcoords="offset points", ha="left", va="center", fontsize=7.4, color=INK2)
        med=float(np.median(vals)); ax.text(POS[i], -1.6, f"median {med:g} mo", ha="center", va="top", fontsize=8.2, color=INK)
        ax.text(POS[i], -2.9, f"mean {np.mean(vals):.1f}", ha="center", va="top", fontsize=7.6, color=INK2)
    ax.set_xticks(POS); ax.set_xticklabels(["NBER committee","Sahm + Bristow rules"], fontsize=8.8); ax.set_xlim(-0.45,2.3)
    ax.set_title(title, loc="left", fontsize=9.8, color=INK, pad=7)
    ax.grid(axis="y", color=GRID, lw=0.7); ax.set_axisbelow(True)
    for s_ in ["top","right"]: ax.spines[s_].set_visible(False)
    ax.tick_params(axis="x", length=0); ax.axhline(0, color=INK2, lw=0.8, zorder=1)
yrs=[str(pd.Period(p,"M").year) for p in six.nber_peak]
boxpanel(axes[0], six.nber_peak_months.tolist(), six.first_onset_months.tolist(), yrs, "A. Peaks (n = 6)")
boxpanel(axes[1], six.nber_trough_months.tolist(), six.end_call_months.tolist(), [str(pd.Period(t,"M").year) for t in six.nber_trough], "B. Troughs (n = 6)")
axes[0].set_ylabel("Months from the turning point to the announcement or call", fontsize=8.5, color=INK2)
axes[0].set_ylim(-4.2, 23)
fig.suptitle("Figure 2. Committee versus rules at the same twelve turning points, 1980–2020", x=0.01, ha="left", fontsize=10.8, color=INK, y=1.0)
fig.savefig(F+"figure3_box_comparison.png", dpi=300, bbox_inches="tight", facecolor=SURF); plt.close(fig)
print("font:",FONT,"| saved", sorted(os.listdir(F)))
