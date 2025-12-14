from __future__ import annotations
import os, json, glob, datetime
from typing import Dict, Any, List

ARTIFACTS_DIR = os.environ.get("ARTIFACTS_DIR", "artifacts/lab")
OUT_DIR = os.environ.get("DASHBOARD_OUT", "dashboard_site")
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
SHA = os.environ.get("GITHUB_SHA", "local")[:7]
STAMP = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    gate_path = os.path.join(ARTIFACTS_DIR, "gate.json")
    bench_path = os.path.join(ARTIFACTS_DIR, "benchmark.json")
    smoke_path = os.path.join(ARTIFACTS_DIR, "smoke.json")
    hard_path = os.path.join(ARTIFACTS_DIR, "hardening.json")
    comp_path = os.path.join(ARTIFACTS_DIR, "baseline_compare.json")

    gate = load_json(gate_path) if os.path.exists(gate_path) else {}
    bench = load_json(bench_path) if os.path.exists(bench_path) else {}
    smoke = load_json(smoke_path) if os.path.exists(smoke_path) else {}
    hard = load_json(hard_path) if os.path.exists(hard_path) else {}
    comp = load_json(comp_path) if os.path.exists(comp_path) else {}

    # Append to history
    hist_file = os.path.join(OUT_DIR, "history.json")
    history: List[Dict[str, Any]] = []
    if os.path.exists(hist_file):
        history = load_json(hist_file) if os.path.getsize(hist_file) else []

    entry = {
        "stamp": STAMP,
        "run_id": RUN_ID,
        "sha": SHA,
        "base_url": gate.get("base_url"),
        "p95_s": bench.get("p95_s"),
        "p99_s": bench.get("p99_s"),
        "error_rate": bench.get("error_rate"),
        "pass": gate.get("pass"),
        "baseline_compare": comp.get("metrics", {}),
    }
    history.append(entry)

    # keep last 200
    history = history[-200:]
    with open(hist_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    # Simple HTML (no JS deps)
    def row(e):
        return f"<tr><td>{e['stamp']}</td><td>{e['sha']}</td><td>{e.get('p95_s','')}</td><td>{e.get('p99_s','')}</td><td>{e.get('error_rate','')}</td><td>{'PASS' if e.get('pass') else 'FAIL'}</td></tr>"

    rows = "\n".join(row(e) for e in reversed(history))
    base = gate.get("base_url","")
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Savant LAB Dashboard</title>
<style>
body{{font-family:Arial, sans-serif;margin:28px;}}
.card{{border:1px solid #ddd;border-radius:12px;padding:14px;margin:14px 0;}}
table{{border-collapse:collapse;width:100%;}}
th,td{{border:1px solid #ddd;padding:8px;text-align:left;}}
.code{{font-family:ui-monospace, SFMono-Regular, Menlo, monospace;background:#f6f6f6;padding:2px 6px;border-radius:6px;}}
</style></head><body>
<h1>Savant LAB Dashboard</h1>
<div class="card">
  <b>Base URL:</b> <span class="code">{base}</span><br/>
  <b>Last update:</b> <span class="code">{STAMP}</span>
</div>

<div class="card">
  <h2>Latency history (end-to-end)</h2>
  <table>
    <thead><tr><th>timestamp</th><th>sha</th><th>p95_s</th><th>p99_s</th><th>error_rate</th><th>gate</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>

<div class="card">
  <h2>Latest baseline comparison (NDCG@3 / MRR@3)</h2>
  <pre class="code">{json.dumps(comp.get("metrics",{}), indent=2, ensure_ascii=False)}</pre>
</div>

<div class="card">
  <h2>Smoke + Hardening (latest)</h2>
  <pre class="code">{json.dumps({{"smoke": smoke, "hardening": hard}}, indent=2, ensure_ascii=False)[:4000]}</pre>
</div>

</body></html>"""
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    main()
