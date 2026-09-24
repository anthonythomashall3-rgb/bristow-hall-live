import shim, sys
W=shim.W
src=open("/home/claude/lab/weekly/american_chronology.py").read()
g={"__name__":"__main__","__file__":W+"/lab/weekly/american_chronology.py"}
exec(compile(src,"american_chronology.py","exec"),g)
