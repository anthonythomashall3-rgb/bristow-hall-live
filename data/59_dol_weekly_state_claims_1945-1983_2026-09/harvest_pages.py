"""Page-harvest volumes of the DOL weekly release (6 September 2026).  Three volumes were harvested page by page on
4 September from babel.hathitrust.org/cgi/imgsrv/html (24_bristow_rule_lab/hathitrust_raw/hathi_<label>.txt, pages
separated by '===SEQ n===') and never parsed: v.23 (Jul 1967-Jun 1968, uiug.30112109870417, 618 pages), v.30 nos 28-53
(Jan-Jun 1975, uiug.30112109870482, a second copy) and v.34 nos 27-52 (Apr-Sep 1979, uiug.30112109870599, the half-volume
whose Cornell OCR is unreadable).  This writes each as a page directory in the form the readers expect (one file per
page, one OCR token per line as in the plaintext zips), normalising the harvest's spacing around punctuation
('July 1 , 1967' -> 'July 1, 1967', 'Dist . of' -> 'Dist. of') so the heading regexes match.  Usage: python3 harvest_pages.py <outroot>"""
import re, os, sys, shutil
SRC="/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/mnt/Onset Detector Data/24_bristow_rule_lab/hathitrust_raw/"
VOLS=[('hathi_v23_1967_68.txt','v23_1967_68'),('hathi_v34_1979_no27_52.txt','v34_1979_no27_52'),('hathi_v30_1975_no28_53.txt','v30_1975_no28_53'),
      ('hathi_v09_1953_54.txt','v09_1953_54'),('hathi_v14h_1958_59.txt','v14h_1958_59'),('hathi_v10h_1954_55.txt','v10h_1954_55'),('hathi_v15h_1959_60.txt','v15h_1959_60')]   # 6 Sep 2026, evening: Harvard's copy, harvested through the babel fetch channel
def norm(l):
    l=re.sub(r'\s+([,.:;%\)])',r'\1',l); l=re.sub(r'\(\s+',r'(',l); l=re.sub(r'\s+/\s*',r'/',l); return l
def write(outroot):
    for f,lab in VOLS:
        t=open(SRC+f,encoding='utf-8',errors='replace').read(); parts=re.split(r'===SEQ (\d+)===',t)
        d=os.path.join(outroot,'hathi_'+lab); shutil.rmtree(d,ignore_errors=True); os.makedirs(d); n=0
        for i in range(1,len(parts),2):
            lines=[norm(l.strip()) for l in parts[i+1].split('\n') if l.strip()]
            open(os.path.join(d,'%08d.txt'%int(parts[i])),'w').write('\n'.join(lines)+'\n'); n+=1
        print(lab,'pages',n)
if __name__=='__main__': write(sys.argv[1] if len(sys.argv)>1 else os.path.expanduser('~'))
