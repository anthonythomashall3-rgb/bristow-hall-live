"""Fetch a list of UPI archive article URLs (argv or stdin), saving raw gzipped, printing the extracted text."""
import sys, re
sys.path.insert(0, '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps/scripts')
from fetch import get
from upitext import upi_text
urls = sys.argv[1:] or sys.stdin.read().split()
for u in urls:
    m = re.search(r'Archives/(\d{4})/(\d\d)/(\d\d)/[^/]+/(\d+)', u)
    name = f'upi_{m.group(1)}-{m.group(2)}-{m.group(3)}_{m.group(4)}.html'
    p, s, b = get(u, name, gz=True)
    ti, d, body = upi_text(b)
    print('=====', s, name, '|', ti, '|', d); print(body[:2500])
