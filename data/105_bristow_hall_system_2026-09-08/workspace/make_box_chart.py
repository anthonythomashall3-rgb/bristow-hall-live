"""Where the frozen route stands: onset and end calls against the committee's announcements.
Lag is measured in days from the last day of the turning-point month, the convention the route uses."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np, pandas as pd

BLUE, ORANGE = "#2a78d6", "#eb6834"
SURF, INK, INK2 = "#fcfcfb", "#0b0b0b", "#52514e"

# the frozen route, 1948-2026 (freeze.py / FROZEN_RECORD.txt)
onset = [10, 51, -11, -70, 31, 120, 30, 142, 51, 30, 126, 26]
trough = [130, 10, 71, 71, 45, 71, 41, 44, 101, 41, 16, 41]
PEAKS = ["1948-11","1953-07","1957-08","1960-04","1969-12","1973-11","1980-01","1981-07","1990-07","2001-03","2007-12","2020-02"]

# the committee's twelve formal announcements, 1980-2021 (NBER announcement page)
ann_pk = {"1980-01":"1980-06-03","1981-07":"1982-01-06","1990-07":"1991-04-25",
          "2001-03":"2001-11-26","2007-12":"2008-12-01","2020-02":"2020-06-08"}
ann_tr = {"1980-07":"1981-07-08","1982-11":"1983-07-08","1991-03":"1992-12-22",
          "2001-11":"2003-07-17","2009-06":"2010-09-20","2020-04":"2021-07-19"}
TROUGHS = ["1949-10","1954-05","1958-04","1961-02","1970-11","1975-03","1980-07","1982-11","1991-03","2001-11","2009-06","2020-04"]
def month_end(m): return (pd.Timestamp(m + "-01") + pd.DateOffset(months=1)) - pd.Timedelta(days=1)
comm_pk = [(pd.Timestamp(v) - month_end(k)).days for k, v in ann_pk.items()]
comm_tr = [(pd.Timestamp(v) - month_end(k)).days for k, v in ann_tr.items()]
same_pk = [onset[PEAKS.index(k)] for k in ann_pk]
same_tr = [trough[TROUGHS.index(k)] for k in ann_tr]

fig, axes = plt.subplots(1, 2, figsize=(11, 4.1), facecolor=SURF)
panels = [("A.  Peaks", [onset, same_pk, comm_pk]), ("B.  Troughs", [trough, same_tr, comm_tr])]
labels = ["The rule\ntwelve turning points", "The rule\nthe six comparable", "The committee\nthe six announced"]
for ax, (title, data) in zip(axes, panels):
    ax.set_facecolor(SURF)
    bp = ax.boxplot(data, vert=False, widths=0.55, patch_artist=True, showfliers=False,
                    medianprops=dict(color=INK, lw=2), whiskerprops=dict(color=INK2, lw=1),
                    capprops=dict(color=INK2, lw=1), boxprops=dict(lw=0))
    for i, patch in enumerate(bp["boxes"]):
        patch.set_facecolor(ORANGE if i == 2 else BLUE); patch.set_alpha(0.30 if i == 1 else 0.55)
    for i, vals in enumerate(data, start=1):
        ax.scatter(vals, np.full(len(vals), i) + np.random.RandomState(3).uniform(-.11, .11, len(vals)),
                   s=17, color=ORANGE if i == 3 else BLUE, zorder=3, edgecolor=SURF, linewidth=.8)
        med = float(np.median(vals))
        ax.annotate(f"{med:.0f} d", (med, i + .34), ha="center", fontsize=8.5, color=INK)
    ax.axvline(0, color=INK2, lw=.8, ls=(0, (4, 3)))
    ax.set_yticks([1, 2, 3]); ax.set_yticklabels(labels, fontsize=8.5, color=INK)
    ax.set_xlabel("days from the end of the turning-point month", fontsize=8.5, color=INK2)
    ax.set_title(title, fontsize=10.5, color=INK, loc="left", pad=8)
    ax.tick_params(axis="x", labelsize=8.5, colors=INK2)
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(INK2); ax.grid(axis="x", color="#e6e5e0", lw=.7); ax.set_axisbelow(True)
    ax.invert_yaxis()
fig.suptitle("The frozen route against the committee, 1948–2026", fontsize=12, color=INK, x=.012, ha="left", y=.99)
fig.tight_layout(rect=[0, 0, 1, .94])
fig.savefig("route_vs_committee_box.png", dpi=300, facecolor=SURF)
print("peaks  rule12 med %.0f | rule6 med %.0f | committee med %.0f" % (np.median(onset), np.median(same_pk), np.median(comm_pk)))
print("troughs rule12 med %.0f | rule6 med %.0f | committee med %.0f" % (np.median(trough), np.median(same_tr), np.median(comm_tr)))
print("committee peaks", comm_pk, "\ncommittee troughs", comm_tr)
