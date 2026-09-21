"""Extract a clean run-level dataset from the supplied workbook. No new data is created."""
import openpyxl, csv
P="/root/.claude/uploads/35501cb2-bbe1-5745-801e-da4fe3f5e9fd/144859a5-Routing_Strategy_Selection_Corrected.xlsx"
wb=openpyxl.load_workbook(P,data_only=True)
ws=wb["RAW_PERFORMANCE"]
rows=[]
for r in range(8,ws.max_row+1):
    if not ws.cell(r,1).value: continue
    rows.append(dict(ctx=ws.cell(r,2).value,policy=ws.cell(r,3).value,seed=ws.cell(r,4).value,
        n=ws.cell(r,5).value,time=ws.cell(r,6).value,co2=ws.cell(r,7).value,dist=ws.cell(r,8).value,
        p95=ws.cell(r,9).value,ins=ws.cell(r,10).value,bg_t=ws.cell(r,11).value,bg_co2=ws.cell(r,12).value,
        net_co2=ws.cell(r,13).value,stopped=ws.cell(r,14).value,dflt=ws.cell(r,15).value,
        wape=ws.cell(r,16).value,bias=ws.cell(r,17).value,demand=ws.cell(r,18).value,
        bg=ws.cell(r,19).value,restr=ws.cell(r,20).value,signal=ws.cell(r,21).value,mass=ws.cell(r,23).value))
# scenario design -> speed ratio
sd=wb["SCENARIO_DESIGN"]; ratio={}
for r in range(8,sd.max_row+1):
    c=sd.cell(r,1).value
    if c and str(c).startswith("D"): ratio[c]=sd.cell(r,5).value
for x in rows: x['speed_ratio']=ratio[x['ctx']]
with open("runs.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"wrote runs.csv: {len(rows)} runs, {len(set(x['ctx'] for x in rows))} contexts, "
      f"{len(set(x['policy'] for x in rows))} policies, seeds {sorted(set(x['seed'] for x in rows))}")
# derived in-network time (journey minus insertion) for the boundary analysis
print("sanity: time>=insertion for all runs:", all(x['time']>=x['ins'] for x in rows))
