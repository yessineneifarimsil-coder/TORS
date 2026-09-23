"""Boundary localisation.

The main grid samples demand every 600 veh/h, so it can only place a policy
switch inside a 600 veh/h bracket.  Where a switch occurs, this refines the
bracket with three intermediate demand levels.

The refined estimate is still a BRACKET between adjacent sampled levels.  The
experiment samples a grid; a grid cannot locate a boundary more finely than its
own spacing, and no continuous threshold is claimed from it.
"""
import json, os, sys, itertools, warnings
warnings.filterwarnings("ignore")
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as K

RES = os.path.join(HERE, "..", "results")
CELL = ["gc", "penetration", "lag", "incident", "alt"]
MAX_BRACKETS = 24          # compute cap, declared here
SUBLEVELS = (150.0, 300.0, 450.0)


def brackets(ct):
    """Cells where the resolved winner changes between adjacent demand levels."""
    W = K.winners(ct)
    out = []
    for key, g in W.groupby(CELL):
        g = g.sort_values("demand")
        rows = g[g.resolved]
        if len(rows) < 2:
            continue
        r = rows.reset_index(drop=True)
        for i in range(len(r) - 1):
            if r.loc[i, "winner"] != r.loc[i + 1, "winner"]:
                lo, hi = r.loc[i, "demand"], r.loc[i + 1, "demand"]
                out.append(dict(zip(CELL, key), lo=float(lo), hi=float(hi),
                                from_policy=r.loc[i, "winner"],
                                to_policy=r.loc[i + 1, "winner"],
                                margin_lo=float(r.loc[i, "margin"]),
                                margin_hi=float(r.loc[i + 1, "margin"])))
    out.sort(key=lambda d: -(d["margin_lo"] + d["margin_hi"]))
    return out


def plan(ct, path):
    bs = brackets(ct)[:MAX_BRACKETS]
    jobs = []
    for k, b in enumerate(bs):
        for frac in SUBLEVELS:
            d = b["lo"] + frac
            if d >= b["hi"]:
                continue
            for pol in K.POLICIES:
                for sd in range(1001, 1006):
                    jobs.append({c: b[c] for c in CELL} |
                                {"demand": d, "policy": pol, "seed": sd,
                                 "ctx": f"BL{k:02d}"})
    json.dump(jobs, open(path, "w"))
    return bs, jobs


def report(ct_main, path_bl):
    if not os.path.exists(path_bl):
        return {"status": "boundary campaign not present"}
    bdf, _ = K.load(path_bl)
    ct_bl = K.context_table(bdf)
    combined = K.context_table(
        __import__("pandas").concat([
            K.load(os.path.join(RES, "main.jsonl"))[0], bdf]))
    W = K.winners(combined)
    out = []
    for b in brackets(ct_main)[:MAX_BRACKETS]:
        sel = W
        for c in CELL:
            sel = sel[np.isclose(sel[c].astype(float), float(b[c]))]
        sel = sel[(sel.demand >= b["lo"]) & (sel.demand <= b["hi"])].sort_values("demand")
        seq = [(float(r.demand), r.winner, bool(r.resolved))
               for _, r in sel.iterrows()]
        lo_ref, hi_ref = b["lo"], b["hi"]
        for i in range(len(seq) - 1):
            if seq[i][1] != seq[i + 1][1] and seq[i][2] and seq[i + 1][2]:
                lo_ref, hi_ref = seq[i][0], seq[i + 1][0]
                break
        out.append(dict(b, refined_lo=lo_ref, refined_hi=hi_ref,
                        width_before=b["hi"] - b["lo"],
                        width_after=hi_ref - lo_ref,
                        sequence=seq))
    return out


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "plan"
    df, _ = K.load(os.path.join(RES, "main.jsonl"))
    R = json.load(open(os.path.join(RES, "results.json")))
    df = df[~df.ctx_key.isin(set(R["validity"]["excluded_contexts"]))]
    ct = K.context_table(df)
    if mode == "plan":
        bs, jobs = plan(ct, os.path.join(RES, "boundary_jobs.json"))
        print(f"{len(brackets(ct))} switching brackets found; "
              f"refining the {len(bs)} widest-margin ones with "
              f"{len(jobs)} runs")
        for b in bs[:8]:
            print(f"   {b['from_policy']}->{b['to_policy']} between "
                  f"{b['lo']:.0f} and {b['hi']:.0f} veh/h  "
                  f"(gc={b['gc']}, pen={b['penetration']}, lag={b['lag']:.0f}, "
                  f"inc={b['incident']}, alt={b['alt']})")
    else:
        rep = report(ct, os.path.join(RES, "boundary.jsonl"))
        R["boundary"] = rep
        json.dump(R, open(os.path.join(RES, "results.json"), "w"), indent=1,
                  default=str)
        if isinstance(rep, list):
            nb = [r for r in rep if r["width_after"] < r["width_before"]]
            print(f"refined {len(nb)}/{len(rep)} brackets")
            for r in rep[:10]:
                print(f"   {r['from_policy']}->{r['to_policy']}: "
                      f"[{r['lo']:.0f},{r['hi']:.0f}] -> "
                      f"[{r['refined_lo']:.0f},{r['refined_hi']:.0f}] veh/h")
        else:
            print(rep)
