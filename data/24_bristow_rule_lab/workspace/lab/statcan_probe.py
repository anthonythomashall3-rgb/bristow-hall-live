import json,subprocess
# StatCan WDS: list series for candidate historical monthly tables
CAND={
 '14100018':'Labour force characteristics, monthly (1976+)',
 '14100287':'Labour force characteristics, monthly, seasonally adjusted',
 '20100008':'Retail trade sales by province (1991+)',
 '20100078':'Retail trade, historical',
 '16100047':'Manufacturing sales',
 '36100434':'GDP at basic prices, monthly',
 '23100056':'Railway carloadings',
 '14100027':'Employment by industry, monthly',
 '18100004':'CPI monthly',
 '10100122':'Historical',
}
for pid,desc in CAND.items():
    url=f'https://www150.statcan.gc.ca/t1/wds/rest/getCubeMetadata'
    body=json.dumps([{"productId":int(pid)}])
    p=subprocess.run(['curl','-sS','--max-time','60','-X','POST','-H','Content-Type: application/json',
                      '-d',body,url],capture_output=True,text=True)
    try:
        j=json.loads(p.stdout)
        o=j[0]
        if o.get('status')!='SUCCESS': print(pid,desc,'->',o.get('status')); continue
        ob=o['object']
        print(pid, ob.get('cubeTitleEn','')[:60],'|',ob.get('cubeStartDate'),'->',ob.get('cubeEndDate'),'| freq',ob.get('frequencyCode'))
    except Exception as e:
        print(pid,'ERR',str(e)[:80], p.stdout[:120])
