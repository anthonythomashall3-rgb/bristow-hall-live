# remove the feeds table from the page (Anthony, 11 September 2026: "REMOVE THIS SECTION FROM THE WEBSITE").
# The `feeds` block stays in the state JSON - it costs nothing and the audit can read it - but nothing renders it.
# The daily line in the "Next data" list stays: it names the S&P 500 close and the search week, which the list had
# never shown. Idempotent; run from 105/workspace: python3 s2/remove_feeds_table.py
import os,sys,re
T=os.path.abspath(sys.argv[1] if len(sys.argv)>1 else '../site/template.html')
s=open(T).read(); o=s
# 1. the heading and the table
i=s.find('  <p class="kv"><b>Every series the rule reads</b>')
if i>=0:
    j=s.find('</table></div>\n',i)
    assert j>0, 'table end not found'
    s=s[:i]+s[j+len('</table></div>\n'):]
# 2. the renderer
a=s.find("const fb=document.querySelector('#feeds tbody');")
if a>=0:
    b=s.find("const ul=$('#nextlist');",a)
    assert b>a, 'renderer end not found'
    s=s[:a]+s[b:]
if s!=o: open(T,'w').write(s); print('feeds table removed from',T)
else: print('nothing to remove (already out)')
print('feeds table present:', 'id="feeds"' in s, '| renderer present:', "#feeds tbody" in s)
