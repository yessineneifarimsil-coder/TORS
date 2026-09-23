import json, itertools, sys

def grid(**kw):
    keys = list(kw)
    return [dict(zip(keys, v)) for v in itertools.product(*[kw[k] for k in keys])]

if __name__ == "__main__":
    which = sys.argv[1]
    if which == "validate":
        jobs = grid(policy=["P1","P2","P3","P4"], demand=[1200,1800,2400,3000,3600,4200],
                    penetration=[0.2,0.8], lag=[30,300], incident=[0,1], alt=[1,2],
                    seed=[101], gc=[0.50])
    else:
        raise SystemExit("unknown")
    for j in jobs:
        j["ctx"] = f"V_d{j['demand']:.0f}_p{j['penetration']}_l{j['lag']:.0f}_i{j['incident']}_a{j['alt']}"
    json.dump(jobs, open(sys.argv[2], "w"))
    print(len(jobs), "jobs ->", sys.argv[2])
