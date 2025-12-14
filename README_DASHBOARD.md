# Savant CI/CD + Latency Dashboard + Baseline Compare

## What you get
- **Release gate**: smoke + hardening + benchmark (p50/p95/p99 + error_rate)
- **Baseline compare**: Savant rerank via API vs local SentenceTransformer baselines on a small evalset
- **Dashboard**: deploys `index.html` + `history.json` to `gh-pages`

## Setup (once)
1) Add Actions secret `SAVANT_BASE_URL` (optional; defaults to your public Space).
2) Enable GitHub Pages:
   - Settings → Pages → Build and deployment → Source: `Deploy from a branch`
   - Branch: `gh-pages` / root

## Files
- `lab/savant_lab_runner.py` (gate)
- `lab/baseline_compare.py` (compare)
- `lab/make_dashboard.py` (site)
- `.github/workflows/savant_lab_dashboard.yml` (CI + deploy)
- `lab/data/evalset.jsonl` (small starter evalset)

## Extend evalset
Replace `lab/data/evalset.jsonl` with your own query/candidates/relevant. Keep same JSONL schema.
