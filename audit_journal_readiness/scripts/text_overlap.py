"""Shared word n-gram overlap between manuscripts (LaTeX commands stripped)."""
import re, sys, json, zipfile, tempfile, os
T=tempfile.mkdtemp()
for tag,z in (("conf648","IC_TORS26_FINAL.zip"),("conf432","IC_TORS26_ORIGINAL_STUDY.zip")):
    zf=zipfile.ZipFile("/home/user/TORS/"+z); n=[x for x in zf.namelist() if x.endswith("main.tex")][0]
    os.makedirs(f"{T}/{tag}",exist_ok=True); open(f"{T}/{tag}/main.tex","wb").write(zf.read(n))
def words(p):
    t=open(p).read()
    t=re.sub(r"%.*","",t); t=re.sub(r"\\begin\{(table|tabular|figure)\*?\}.*?\\end\{\1\*?\}"," ",t,flags=re.S)
    t=re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?"," ",t); t=re.sub(r"[{}$^_~\\&]"," ",t)
    return re.findall(r"[a-z]+",t.lower())
def grams(w,n): return {tuple(w[i:i+n]) for i in range(len(w)-n+1)}
A={"journal":"/home/user/TORS/journal/manuscript/main.tex",
   "conf648":f"{T}/conf648/main.tex","conf432":f"{T}/conf432/main.tex"}
W={k:words(v) for k,v in A.items()}
out={k:len(v) for k,v in W.items()}
for a,b in [("journal","conf648"),("journal","conf432"),("conf648","conf432")]:
    for n in (6,8,10,12):
        ga,gb=grams(W[a],n),grams(W[b],n)
        out[f"{a}~{b} n={n}"]=dict(shared=len(ga&gb),frac_of_first=round(len(ga&gb)/len(ga),4),frac_of_second=round(len(ga&gb)/len(gb),4))
print(json.dumps(out,indent=1))
json.dump(out,open("outputs/text_overlap.json","w"),indent=1)
