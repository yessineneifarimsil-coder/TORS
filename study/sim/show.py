import json, sys
for l in sys.stdin:
    if not l.startswith("{"): continue
    r = json.loads(l)
    if "_error" in r:
        print("ERR", r["_error"][:200]); continue
    print(f"{r['policy']} d={r['demand']:.0f} gc={r['gc']:.2f} pen={r['penetration']:.2f} "
          f"lag={r['lag']:.0f} alt={r['alt']} inc={r['incident']} | "
          f"C1sys={r['C1_sys']:7.1f} C1corr={r['C1_corr']:7.1f} C2sys={r['C2_sys']:7.1f} "
          f"C3sys={r['C3_sys']:8.0f} | C/N/S={r['picks_C']}/{r['picks_N']}/{r['picks_S']} "
          f"compl={r['completion']:.3f} tele={r['teleports']}")
