r"""Verify every \Num macro the manuscript uses is defined in numbers.tex.

The manuscript cites no number except through these macros, so this check is
what guarantees the text cannot contain a figure that the analysis did not
produce."""
import re, glob, sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
defined = set(re.findall(r'\\newcommand\{\\(Num[A-Za-z]+)\}', open("numbers.tex").read()))
used = set()
for f in glob.glob("*.tex") + glob.glob("tables/*.tex"):
    if f == "numbers.tex":
        continue
    used |= set(re.findall(r'\\(Num[A-Za-z]+)', open(f).read()))
missing = sorted(used - defined)
print(f"macros defined {len(defined)}, used {len(used)}, undefined {len(missing)}")
if missing:
    print("UNDEFINED:", missing)
# a bare digit in running text is a number that did not come through a macro
suspicious = []
for f in ("body_results.tex", "body_discussion.tex", "body_conclusion.tex",
          "abstract.tex"):
    for i, line in enumerate(open(f), 1):
        t = re.sub(r'\\[A-Za-z]+', '', line)
        t = re.sub(r'\\label\{[^}]*\}|\\ref\{[^}]*\}|\\cite\{[^}]*\}', '', t)
        for mnum in re.finditer(r'(?<![A-Za-z_])\d+(\.\d+)?', t):
            suspicious.append(f"{f}:{i}: {mnum.group(0)}  |  {line.strip()[:90]}")
print(f"\nliteral numbers outside macros in results/discussion/conclusion/abstract: "
      f"{len(suspicious)}")
for s in suspicious:
    print("   ", s)
sys.exit(1 if missing else 0)
