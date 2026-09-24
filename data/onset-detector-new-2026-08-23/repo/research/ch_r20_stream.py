import json
def stream_records(fp, maxrec=None):
    dec=json.JSONDecoder(); buf=''; started=False; n=0
    with open(fp,'r') as f:
        while True:
            chunk=f.read(1<<20)
            if not chunk: break
            buf+=chunk
            if not started:
                i=buf.find('"records"')
                if i<0: buf=buf[-20:]; continue
                j=buf.find('[',i)
                if j<0: continue
                buf=buf[j+1:]; started=True
            while True:
                buf=buf.lstrip()
                if buf[:1]==']' or buf=='' : break
                if buf[:1]==',': buf=buf[1:]; continue
                try: obj,end=dec.raw_decode(buf)
                except ValueError: break
                buf=buf[end:]; yield obj; n+=1
                if maxrec and n>=maxrec: return
