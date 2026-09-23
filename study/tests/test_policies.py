"""Known-answer tests for the four policies and the observation buffer.

Each test states the answer that traffic-engineering reasoning requires, then
checks the implementation produces it.  No test is calibrated against a
simulation outcome.
"""
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "policies"))
import policies as POL

PATHS = {"A": ["a1", "a2"], "B": ["b1", "b2"]}
LEN = {"A": 1000.0, "B": 1500.0}
FF = {"a1": 50.0, "a2": 50.0, "b1": 75.0, "b2": 75.0}
CAP = {"a1": 2000.0, "a2": 2000.0, "b1": 1000.0, "b2": 1000.0}
FAIL = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "   <-- " + detail))
    if not cond:
        FAIL.append(name)


def obs_with(samples, lag=60.0, window=120.0):
    o = POL.Observatory(list(FF), FF, lag, window, 30.0)
    for t, m in samples:
        o.record(t, m, {e: 0.0 for e in FF})
    return o


# 1 -- the buffer must not reveal anything newer than the lag
o = obs_with([(380.0, {e: 10.0 for e in FF}), (500.0, {e: 999.0 for e in FF})])
ser, seen = o.path_series(510.0, PATHS)   # visible window = [330, 450]
check("policy sees the in-window sample and not the newer one",
      seen and ser["A"] == [20.0], f"got {ser['A']}")

# 2 -- with no admissible sample the policy must fall back to free flow
o2 = obs_with([(0.0, {e: 999.0 for e in FF})])
ser2, seen2 = o2.path_series(5.0, PATHS)
check("free-flow fallback before any visible sample",
      seen2 is False and abs(ser2["A"][0] - 100.0) < 1e-9, f"got {ser2}")

# 3 -- P1 ignores traffic state entirely
p1 = POL.P1Static(PATHS, LEN)
hot = obs_with([(0.0, {"a1": 9e3, "a2": 9e3, "b1": 1.0, "b2": 1.0})])
check("P1 chooses the shortest path regardless of congestion",
      p1.choose(200.0, "v", None)[0] == "A")

# 4 -- P2 follows the observed mean
o4 = obs_with([(0.0, {"a1": 400.0, "a2": 400.0, "b1": 10.0, "b2": 10.0})])
p2 = POL.P2Reactive(PATHS, o4)
check("P2 chooses the lower observed mean travel time",
      p2.choose(100.0, "v", None)[0] == "B")

# 5 -- P4 must prefer the steadier path when means are equal
samples = []
for k, t in enumerate([0.0, 30.0, 60.0]):
    vol = [10.0, 190.0, 100.0][k]          # B: mean 100, high spread
    samples.append((t, {"a1": 50.0, "a2": 50.0, "b1": vol / 2, "b2": vol / 2}))
o5 = obs_with(samples, lag=0.0, window=120.0)
ser5, _ = o5.path_series(60.0, PATHS)
mA, mB = sum(ser5["A"]) / 3, sum(ser5["B"]) / 3
p4 = POL.P4Reliability(PATHS, o5, lam=1.0)
check("test fixture really does equalise the two means",
      abs(mA - mB) < 1e-6, f"A={mA} B={mB}")
check("P4 breaks a tie in the mean towards the lower-variance path",
      p4.choose(60.0, "v", None)[0] == "A")
p4b = POL.P4Reliability(PATHS, o5, lam=0.0)
check("P4 with lambda=0 is indifferent (reduces to the mean)",
      abs(p4b.choose(60.0, "v", None)[1]["score"]["A"]
          - p4b.choose(60.0, "v", None)[1]["score"]["B"]) < 1e-6)

# 6 -- P3 admissibility must exclude a path that is too slow
o6 = obs_with([(0.0, {"a1": 50.0, "a2": 50.0, "b1": 500.0, "b2": 500.0})], lag=0.0)
p3 = POL.P3LoadBalance(PATHS, o6, CAP, eps=0.20, assign_window=120.0)
pick, info = p3.choose(60.0, "v", None)
check("P3 excludes a path outside the travel-time tolerance",
      info["admissible"] == ["A"] and pick == "A", f"got {info['admissible']}")

# 7 -- KNOWN ANSWER: equal travel time, unequal capacity -> split in capacity ratio
o7 = obs_with([(0.0, {e: 50.0 for e in FF})], lag=0.0)
p3b = POL.P3LoadBalance(PATHS, o7, CAP, eps=0.20, assign_window=120.0)
picks = {"A": 0, "B": 0}
for i in range(300):
    picks[p3b.choose(60.0, f"v{i}", None)[0]] += 1
ratio = picks["A"] / max(picks["B"], 1)
check("P3 splits equal-cost paths in proportion to capacity (2:1 expected)",
      abs(ratio - 2.0) <= 0.12, f"A={picks['A']} B={picks['B']} ratio={ratio:.3f}")

# 8 -- P3 must degenerate to P2 when capacities are equal
CAP_EQ = {e: 1000.0 for e in FF}
p3c = POL.P3LoadBalance(PATHS, o7, CAP_EQ, eps=0.20, assign_window=120.0)
picks2 = {"A": 0, "B": 0}
for i in range(300):
    picks2[p3c.choose(60.0, f"v{i}", None)[0]] += 1
check("P3 splits equal-cost equal-capacity paths evenly",
      abs(picks2["A"] - picks2["B"]) <= 2, f"{picks2}")

# 8b -- a degenerate assignment window must be refused, not silently absorbed
try:
    POL.P3LoadBalance(PATHS, o7, CAP, eps=0.20, assign_window=1e9)
    check("P3 refuses a degenerate assignment window", False, "no error raised")
except ValueError:
    check("P3 refuses a degenerate assignment window", True)

# 9 -- determinism: identical inputs must give identical decisions
a = [POL.P2Reactive(PATHS, o4).choose(100.0, f"v{i}", None)[0] for i in range(5)]
b = [POL.P2Reactive(PATHS, o4).choose(100.0, f"v{i}", None)[0] for i in range(5)]
check("policy decisions are deterministic given identical state", a == b)

print()
print(f"{'ALL TESTS PASS' if not FAIL else 'FAILURES: ' + ', '.join(FAIL)}")
sys.exit(1 if FAIL else 0)
