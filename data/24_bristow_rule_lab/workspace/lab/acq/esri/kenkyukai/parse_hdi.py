"""Parse ESRI's historical-DI component tables (ヒストリカルＤＩ（一致指数）の推移) out of the
committee materials: for each block, the year/month header, then one line per component
'Cn <name> + - + ...', then 拡張系列数 / 採用系列数.  Output: long table (file, series code,
series name, month, sign)."""
import re, sys, subprocess, glob, pandas as pd
KAN={'平成':1988,'令和':2018,'昭和':1925}
def wareki(tok):
    m=re.match(r'(平成|令和|昭和)(\d+)年\((\d{4})年\)',tok)
    if m: return int(m.group(3))
    m=re.match(r'(\d{4})年',tok)
    if m: return int(m.group(1))
    m=re.match(r'(平成|令和|昭和)(\d+)年',tok)
    if m: return KAN[m.group(1)]+int(m.group(2))
    return None
def parse(pdf):
    txt=subprocess.run(['pdftotext','-layout',pdf,'-'],capture_output=True,text=True).stdout
    lines=txt.split('\n'); out=[]
    i=0
    while i<len(lines):
        l=lines[i]
        # a month header line: contains '1月' ... '12月' tokens
        months=re.findall(r'(\d{1,2})月',l)
        if len(months)>=6 and not re.search(r'[+\-]{1}\s',l) and 'C' not in l:
            # find years on this or the previous line(s)
            yrs=[]
            for k in range(max(0,i-2),i+1):
                for tok in re.findall(r'(?:平成|令和|昭和)?\d+年(?:\(\d{4}年\))?',lines[k]):
                    y=wareki(tok)
                    if y: yrs.append((lines[k].find(tok),y))
            if not yrs: i+=1; continue
            # assign a year to each month: year increments when month number decreases
            mnums=[int(m) for m in months]
            years=[]; y=sorted(yrs)[0][1]
            for j,mn in enumerate(mnums):
                if j>0 and mn<mnums[j-1]: y+=1
                years.append(y)
            # the first year on the header may belong to the first block of months
            # use the leftmost year label as the year of the first month
            cols=[pd.Timestamp(yy,mn,1) for yy,mn in zip(years,mnums)]
            # component lines follow
            j=i+1; rows=[]
            while j<len(lines) and j<i+25:
                cl=lines[j]
                m=re.match(r'\s*(C\d{1,2})\s+(\S+)\s+(.*)$',cl)
                if m:
                    signs=re.findall(r'[+\-]',m.group(3))
                    if len(signs)==len(cols):
                        for c,sg in zip(cols,signs): rows.append((pdf,m.group(1),m.group(2),c,sg))
                if '採用系列数' in cl or 'ヒストリカル' in cl and '%' in cl: break
                j+=1
            out+=rows; i=j
        i+=1
    return out
if __name__=='__main__':
    rows=[]
    for f in sorted(glob.glob('*.pdf')): rows+=parse(f)
    df=pd.DataFrame(rows,columns=['file','code','name','month','sign'])
    df.to_csv('esri_hdi_components.csv',index=False)
    print(len(df),'rows from',df.file.nunique(),'files')
    print(df.groupby('file').month.agg(['min','max','count']).to_string())
