"""Germany: the Council's four monthly channels plus the quarterly GDP the Council says it reads
with them ("mehrere makrooekonomische Indikatoren auf Monats- und Quartalsbasis"), as a fifth
channel.  GDP is the OECD QNA volume series DEU.B1_GE.VOBARSA.Q (1960Q1 on, West Germany linked
before 1991; DBnomics, fetched 2 September 2026; lab/nat/deu/DEU_gdp_q_oecd_qna.csv), placed at
the quarter's middle month and interpolated to months on the log level - the only way a
quarterly series can sit in a monthly panel.  Held out; shipped configuration; nothing chosen."""
import sys; sys.path.insert(0,'/home/claude/lab')
import numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
import io, contextlib
buf=io.StringIO()
with contextlib.redirect_stdout(buf):
    import deu_test as T
g=pd.read_csv('/home/claude/lab/nat/deu/DEU_gdp_q_oecd_qna.csv',index_col=0,parse_dates=True).iloc[:,0]
lg=np.log(g); m=lg.resample('MS').asfreq().interpolate('linear'); gm=np.exp(m)
GDP=('quarterly GDP, interpolated',gm)
for tag,chs in [("the four channels the Council itself names",T.COUNCIL+T.COUNCIL_EXTRA),
                ("the Council's four with quarterly GDP",T.COUNCIL+T.COUNCIL_EXTRA+[GDP]),
                ("quarterly GDP alone",[GDP,GDP]),
                ("the six-channel panel with quarterly GDP",T.CH+[GDP])]:
    r=T.run(tag,chs)
    print(f'{tag:48s} peaks {r[0]}/{r[2]} troughs {r[1]}/{r[2]}  MAD {r[3]:.2f} {r[4]:.2f}')
    for x in r[5]: print(f'     peak {x[0]} err {str(x[1]):>5s}    trough {x[2]} err {str(x[3]):>5s}')
