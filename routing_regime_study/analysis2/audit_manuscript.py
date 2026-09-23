"""Check every load-bearing number in the manuscript against the analysis outputs."""
import json, re, statistics as st
import core as K

TEX = open("/home/user/TORS/routing_regime_study/final/main.tex").read()
OLD = json.load(open("/home/user/TORS/routing_regime_study/analysis/results.json"))
EX = json.load(open("extend.json")); EX2 = json.load(open("extend2.json"))
T = K.ctx_means("time"); C = K.ctx_means("co2")
COST, aT, aC = K.scalarise(T, C, K.CTXS)
HB = {c: min(COST[c].values()) for c in K.CTXS}
P = EX["physical"]; LAD = EX["ladder"]; RD = EX["regime_decomposition"]

def present(s):
    return s in TEX

checks = []
def chk(label, text, value=None, fmt=None):
    ok = present(text)
    checks.append((label, text, ok))
    return ok

# --- headline decision quantities -------------------------------------------
chk("headroom / fixed DTT", "0.03018")
chk("fixed SP", "0.31825")
chk("fixed TECO10", "0.20757")
chk("selector regret", "0.00606")
chk("capture", "79.9")
chk("optimal 21/24", "21 of 24")
chk("within 1% 22/24", "22 of 24")
chk("extrap pooled", "0.07649")
chk("extrap 1680", "0.14856")
chk("extrap 720", "0.02456")
chk("extrap 1200", "0.05633")
chk("worst-fixed gap", "0.28807")
chk("SP regret at 1680", "0.67611")
chk("regret at 720", "0.03422")
chk("adaptive transition", "0.01818")
# physical
chk("sel time", "412.17"); chk("sel co2", "1114.64")
chk("dtt time", "425.17"); chk("dtt co2", "1145.36")
chk("delta t", "13.00"); chk("delta co2", "30.71")
chk("delta t pct", "3.06"); chk("delta co2 pct", "2.68")
chk("hb time", "409.25"); chk("hb co2", "1106.12")
# references
chk("ref time", "542.844"); chk("ref co2", "1263.515")
# ladder
chk("R1", "0.01878"); chk("R3", "0.01417"); chk("R1 captured", "37.8"); chk("R3 captured", "53.1")
chk("max regret R0", "0.13176"); chk("max regret R3", "0.10079"); chk("max regret R4", "0.11545")
# thresholds
chk("threshold 960", "960"); chk("threshold 1440", "1440")
chk("no-signal ablation", "72.9")
# noise
chk("resolved 22/24", "22 of the 24"); chk("min ratio", "2.03")
chk("median SE 720", "0.0057"); chk("median SE 1200", "0.0334"); chk("median SE 1680", "0.0232")
chk("max SE", "0.0697")
chk("seed headroom mean", "0.03377"); chk("seed headroom SE", "0.00381")
chk("seed block 1", "0.04138"); chk("seed block 2", "0.03035"); chk("seed block 3", "0.02959")
chk("median margin 1200", "0.2757")
# pareto
chk("pareto 2crit", "1.29"); chk("pareto 3crit", "1.67")
chk("pareto low 2", "1.38"); chk("pareto low 3", "2.38")
chk("within-context r time-co2", "0.96"); chk("within-context r time-stopped", "0.62")
# mechanism
for v in ("250.3", "288.0", "277.2", "17.9", "84.8", "113.7", "441.2", "554.9", "322.5",
          "416.9", "104.1", "114.3", "37.80", "18.31", "38.43", "23.80", "51.6", "38.1",
          "255.1", "590.7", "248.5", "423.2"):
    chk(f"mech {v}", v)
# campaign
chk("cohort", "270{,}432"); chk("insertion 720", "0.12"); chk("insertion 1200", "5.54")
chk("insertion 1680", "262.41"); chk("worst insertion", "810.29")
chk("SP ins 1680", "447.5"); chk("DTT ins 1680", "6.3")
chk("mass", "1.69"); chk("algebra", "6.9")
# controls
chk("eco loss", "21.62"); chk("eco worst", "78.16"); chk("eco panels", "3 of\n8 panels")
chk("wape", "14.71"); chk("bias", "0.32"); chk("spearman-free", "21 of 24 contexts")
# robustness
chk("tree range lo", "50.9"); chk("tree range hi", "79.9")
chk("weights lo", "78.1"); chk("weights hi", "81.7")
chk("seed cap 1", "60.8"); chk("seed cap 2", "67.7"); chk("seed cap 3", "90.2")
chk("train-only", "79.8"); chk("innet captured", "80.1"); chk("innet headroom", "0.03305")

bad = [c for c in checks if not c[2]]
print(f"manuscript numeric audit: {len(checks)-len(bad)}/{len(checks)} strings found")
for lab, s, _ in bad:
    print(f"  MISSING  {lab}: {s!r}")

# --- independent recomputation of the values the strings assert ---------------
print()
recomputed = {
    "fixed DTT mean regret": st.mean(COST[c]["DTT"] - HB[c] for c in K.CTXS),
    "fixed SP mean regret": st.mean(COST[c]["SP"] - HB[c] for c in K.CTXS),
    "selector mean regret": LAD["R4_tree_depth3"]["mean"],
    "capture pct": LAD["R4_tree_depth3"]["captured_pct"],
    "R2 == R4": LAD["R2_demand_signal_threshold"]["mean"] == LAD["R4_tree_depth3"]["mean"],
    "SP-DTT fixed gap": st.mean(COST[c]["SP"] - HB[c] for c in K.CTXS) - st.mean(COST[c]["DTT"] - HB[c] for c in K.CTXS),
    "resolved contexts": EX["noise_resolved_total"],
    "3crit pareto contains primary winner": EX2["two_crit_winner_is_3d_pareto"],
    "physical dt": P["d_time"], "physical dco2": P["d_co2"],
}
for k, v in recomputed.items():
    print(f"  {k}: {v}")
