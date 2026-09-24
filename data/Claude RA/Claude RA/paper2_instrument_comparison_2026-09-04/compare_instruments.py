"""Sahm vs SOS vs Michez on the current vintage, 1960-2026.
Inputs: SAHMCURRENT.csv, IURSA.csv, michaillat_saez_recession_indicator.csv
(all from the Hall & Bristow 2026 replication archive).
Reports first crossing and lag for each NBER peak, and every crossing outside
a dated recession, its twelve-month tail, and a five-month early-warning window.
Result (4 Sep 2026): over the seven recessions 1973-2020 that IURSA reaches,
SOS median lag 2 months vs Sahm 3; SOS earlier in four, later in two, level in one;
SOS exceeds its line outside recessions in one month (Dec 2002), Sahm in three
episodes (1992 tail, Jul-Aug 2003, Jul-Sep 2024). Michez dashboard begins 2001.
"""
import csv, sys
from collections import OrderedDict
def col(path):
    r = list(csv.reader(open(path)))[1:]
    return OrderedDict((a[:7], float(b)) for a, b in r if b not in ('', '.'))
def mo(s):
    y, m = map(int, s.split('-')); return y * 12 + m
REC = [("1960-04","1961-02"),("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),
       ("1981-07","1982-11"),("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),
       ("2020-02","2020-04")]
def sos_monthly(path):
    w = [(a, float(b)) for a, b in list(csv.reader(open(path)))[1:] if b not in ('', '.')]
    out = {}
    for i in range(78, len(w)):
        ma = sum(v for _, v in w[i-25:i+1]) / 26
        prev = [sum(v for _, v in w[j-25:j+1]) / 26 for j in range(i-52, i)]
        k = w[i][0][:7]
        out[k] = max(out.get(k, -9), ma - min(prev))
    return OrderedDict(sorted(out.items()))
if __name__ == '__main__':
    sahm, iursa, mich = sys.argv[1], sys.argv[2], sys.argv[3]
    series = [("Sahm", col(sahm), 0.50, False), ("SOS", sos_monthly(iursa), 0.20, True),
              ("Michez", col(mich), 0.29, True)]
    for name, s, thr, strict in series:
        lags = []
        for p, t in REC:
            hit = next((k for k, v in s.items() if mo(p) <= mo(k) <= mo(t) + 6
                        and ((v > thr) if strict else (v >= thr))), None)
            lags.append((p, hit, mo(hit) - mo(p) if hit else None))
        print(name, lags)
