"""Mechanism analysis from existing 432 runs only. No new simulation."""
import csv, statistics as st, json
from collections import defaultdict
R=[dict(r,time=float(r['time']),co2=float(r['co2']),ins=float(r['ins']),dist=float(r['dist']),
        p95=float(r['p95']),stopped=float(r['stopped']),n=float(r['n']),net_co2=float(r['net_co2']),
        bg_t=float(r['bg_t']),bg_co2=float(r['bg_co2']),demand=int(r['demand'])) for r in csv.DictReader(open("runs.csv"))]
for x in R:
    x['innet']=x['time']-x['ins']
    x['stop_per_veh']=x['stopped']/x['n']          # queue/delay indicator, veh-s per vehicle
    x['co2_per_km']=x['co2']/(x['dist']/1000.0)
    x['speed']=(x['dist']/1000.0)/(x['innet']/3600.0)   # implied in-network mean speed km/h
POL=["SP","DTT","TECO10"]
REG={720:"A low",1200:"B transition",1680:"C high"}
def agg(key,pol,q):
    g=[x for x in R if x['policy']==pol and x['demand']==q]
    return st.mean(x[key] for x in g)
print("="*104)
print("MECHANISM: per-policy means by demand regime (existing outputs only)")
print("="*104)
cols=[("dist","route distance (m)","%8.1f"),("innet","in-network time (s)","%8.1f"),
      ("ins","insertion delay (s)","%8.1f"),("time","journey time (s)","%8.1f"),
      ("speed","implied speed (km/h)","%8.2f"),("stop_per_veh","stopped veh-s/veh","%8.1f"),
      ("co2","CO2 (g)","%8.1f"),("co2_per_km","CO2 per km (g/km)","%8.1f")]
for key,lab,fmt in cols:
    print(f"\n  {lab}")
    print(f"    {'regime':14s}"+"".join(f"{p:>12s}" for p in POL)+f"{'DTT-SP':>12s}{'%diff':>9s}")
    for q in (720,1200,1680):
        v=[agg(key,p,q) for p in POL]
        d=v[1]-v[0]; pc=d/v[0]*100
        print(f"    {REG[q]:14s}"+"".join((fmt%x).rjust(12) for x in v)+(fmt%d).rjust(12)+f"{pc:+8.1f}%")

print("\n"+"="*104)
print("DECOMPOSITION: why the preference reverses  (SP minus DTT, seconds and grams)")
print("="*104)
print(f"  {'regime':14s} {'d_dist(m)':>10s} {'d_innet(s)':>11s} {'d_ins(s)':>10s} {'d_time(s)':>10s} {'d_CO2(g)':>10s} {'d_stop':>9s}")
for q in (720,1200,1680):
    dd=agg('dist','SP',q)-agg('dist','DTT',q); di=agg('innet','SP',q)-agg('innet','DTT',q)
    ds=agg('ins','SP',q)-agg('ins','DTT',q); dt=agg('time','SP',q)-agg('time','DTT',q)
    dc=agg('co2','SP',q)-agg('co2','DTT',q); dq=agg('stop_per_veh','SP',q)-agg('stop_per_veh','DTT',q)
    print(f"  {REG[q]:14s} {dd:10.1f} {di:11.1f} {ds:10.1f} {dt:10.1f} {dc:10.1f} {dq:9.1f}")
print("\n  reading: d_dist<0 => SP is SHORTER (its structural advantage).")
print("           d_innet>0 => SP is SLOWER in-network (congestion penalty).")
print("           sign of d_time flips when the congestion penalty exceeds the distance advantage.")

print("\n"+"="*104)
print("CONGESTION ON THE SHORTEST PATH: does SP degrade faster than DTT?")
print("="*104)
print(f"  {'policy':8s} {'speed@720':>10s} {'speed@1200':>11s} {'speed@1680':>11s} {'loss 720->1680':>15s}")
for p in POL:
    s=[agg('speed',p,q) for q in (720,1200,1680)]
    print(f"  {p:8s} {s[0]:10.2f} {s[1]:11.2f} {s[2]:11.2f} {(s[2]-s[0])/s[0]*100:14.1f}%")
print(f"\n  {'policy':8s} {'stop@720':>10s} {'stop@1200':>11s} {'stop@1680':>11s}  (stopped veh-s per vehicle)")
for p in POL:
    s=[agg('stop_per_veh',p,q) for q in (720,1200,1680)]
    print(f"  {p:8s} {s[0]:10.1f} {s[1]:11.1f} {s[2]:11.1f}")
print(f"\n  {'policy':8s} {'g/km@720':>10s} {'g/km@1200':>11s} {'g/km@1680':>11s}")
for p in POL:
    s=[agg('co2_per_km',p,q) for q in (720,1200,1680)]
    print(f"  {p:8s} {s[0]:10.1f} {s[1]:11.1f} {s[2]:11.1f}")

print("\n"+"="*104)
print("ROUTE DIVERSITY (default-link fraction = share of chosen route on links SUMO never sampled)")
print("="*104)
for p in POL:
    v=[st.mean(float(x['dflt']) for x in R if x['policy']==p and x['demand']==q) for q in (720,1200,1680)]
    print(f"  {p:8s} "+ "".join(f"{y:10.3f}" for y in v))
print("  SP is 0.000 by construction (its route is the most heavily sampled corridor).")
