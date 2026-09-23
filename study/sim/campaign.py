"""Run a list of jobs in parallel, append results to a JSONL file, resume-safe."""
import os, sys, json, argparse, subprocess, hashlib
from concurrent.futures import ProcessPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, "run.py")
KEYS = ["policy", "demand", "gc", "penetration", "lag", "window", "alt",
        "incident", "inc_family", "bg", "seed",
        "p3_eps", "p3_assign_window", "p4_lambda", "ctx"]


def job_key(j):
    return hashlib.md5(json.dumps({k: j.get(k) for k in KEYS},
                                  sort_keys=True, default=str).encode()).hexdigest()


def _one(j):
    cmd = [sys.executable, RUN]
    for k in KEYS:
        if k in j and j[k] is not None and j[k] != "":
            cmd += [f"--{k.replace('_','-')}", str(j[k])]
    env = dict(os.environ)
    env.setdefault("SUMO_HOME", "/usr/local/lib/python3.11/dist-packages/sumo")
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=900, env=env)
        line = [l for l in out.stdout.splitlines() if l.startswith("{")]
        if not line:
            return {"_error": (out.stderr or out.stdout)[-400:], **j}
        r = json.loads(line[-1]); r["_key"] = job_key(j); return r
    except Exception as e:
        return {"_error": repr(e)[:400], **j}


def execute(jobs, out_path, workers=4, label=""):
    done = set()
    if os.path.exists(out_path):
        with open(out_path) as f:
            for l in f:
                try:
                    done.add(json.loads(l).get("_key"))
                except Exception:
                    pass
    todo = [j for j in jobs if job_key(j) not in done]
    print(f"[{label}] {len(jobs)} jobs, {len(jobs)-len(todo)} cached, {len(todo)} to run",
          flush=True)
    n_err = 0
    with open(out_path, "a") as fh, ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_one, j): j for j in todo}
        for i, fu in enumerate(as_completed(futs), 1):
            r = fu.result()
            if "_error" in r:
                n_err += 1
                if n_err <= 3:
                    print("  ERROR:", r["_error"][:300], flush=True)
            fh.write(json.dumps(r) + "\n"); fh.flush()
            if i % 25 == 0 or i == len(todo):
                print(f"  [{label}] {i}/{len(todo)}  errors={n_err}", flush=True)
    return n_err


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--jobs", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--label", default="")
    a = p.parse_args()
    jobs = json.load(open(a.jobs))
    sys.exit(1 if execute(jobs, a.out, a.workers, a.label) else 0)
