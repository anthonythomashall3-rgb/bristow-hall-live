# append §9 to the search-week memo and correct the TSA sentence in place (run on the Mac after deployment)
# usage: python3 s2/apply_memo_v329.py "11 September 2026" "HH:MM" "WALK_RESULT text" "AUDIT_RESULT text"
import os,sys,hashlib
DATE,TIME,WALK,AUDIT=sys.argv[1:5]
p=os.path.expanduser('~/Projects/Recession Papers/BRISTOW-HALL-RULE-SEARCH-WEEK-v327-2026-09-10.md')
s=open(p).read()
h=hashlib.sha256(s.encode()).hexdigest()[:16]; assert h=='fb4d51e3634ca574', h   # the memo as last committed (cloud copy identical)
old="September 2026 from \"did not exist in March 2020\") — so read on the day it was published it fires 18 March, two days after\nthe search week, and it stays as data;"
new="September 2026 from \"did not exist in March 2020\") — so read on the day it was published it fires 18 March, two days after\nthe v3.28 search week of 16 March (six days after v3.29's 12 March; §9), and it stays as data;"
assert s.count(old)==1, s.count(old); s=s.replace(old,new)
s9=open('s2/memo_s9_v329.md').read().replace('DEPLOY_DATE',DATE).replace('DEPLOY_TIME',TIME).replace('WALK_RESULT',WALK).replace('AUDIT_RESULT',AUDIT)
assert 'DEPLOY_' not in s9 and '_RESULT' not in s9
s=s.rstrip('\n')+'\n'+s9
open(p,'w').write(s); print('memo edited; sha', hashlib.sha256(s.encode()).hexdigest()[:16])
