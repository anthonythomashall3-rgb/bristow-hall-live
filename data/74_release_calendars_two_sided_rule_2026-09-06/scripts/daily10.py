"""The first-print weekly insured rate (collection 59) added as an extra proposal, at two lines on each branch, and
carried past 1971 to the end of its own record in April 1983."""
exec(open('daily9.py').read().split('P("\\n=== baseline v3.1 ===")')[0].replace("out=open('daily9.out','w')","out=open('daily10.out','w')"))
FH45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
FH25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
P("=== baseline v3.1 ==="); go('v3.1',[CRED])
P("\n=== both lines on each branch, pre-1971 ===")
for a,b in [(0.45,0.75),(0.45,1.00),(0.50,0.75),(0.45,0.60)]:
    for c,d in [(0.25,0.45),(0.25,0.60),(0.30,0.45)]:
        go(f'rt {a}+{b} / {c}+{d}',[CRED],F45x=FH45+leg_rt(RT,a)+leg_rt(RT,b),F25x=FH25+leg_rt(RT,c)+leg_rt(RT,d))
P("\n=== the same, carried to April 1983 (the record's own end) ===")
for a,b in [(0.45,0.75),(0.45,1.00)]:
    for c,d in [(0.25,0.45),(0.25,0.60)]:
        go(f'rt to 1983: {a}+{b} / {c}+{d}',[CRED],F45x=FH45+leg_rt(RT,a,stop='1984-01-01')+leg_rt(RT,b,stop='1984-01-01'),
                                              F25x=FH25+leg_rt(RT,c,stop='1984-01-01')+leg_rt(RT,d,stop='1984-01-01'))
P("\n=== single line, carried to April 1983 ===")
for a,c in [(0.45,0.25),(0.50,0.30),(0.75,0.45)]:
    go(f'rt to 1983: {a}/{c}',[CRED],F45x=FH45+leg_rt(RT,a,stop='1984-01-01'),F25x=FH25+leg_rt(RT,c,stop='1984-01-01'))
P("\n=== fine sweep of the low pair, pre-1971 (where 1953 lives) ===")
for a in [0.40,0.45,0.50,0.55]:
    for c in [0.20,0.25,0.30,0.35]:
        go(f'rt {a}/{c}',[CRED],F45x=FH45+leg_rt(RT,a),F25x=FH25+leg_rt(RT,c))
out.close()
