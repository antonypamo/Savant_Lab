# Savant LAB CI/CD Gate

## What this does
- Smoke tests: `/`, `/health`, `/docs`, `/openapi.json`
- Hardening tests: size/control chars/injection-like content on `/evaluate`
- Benchmark: N requests to `/evaluate`, computes p50/p95/p99 and error_rate
- Release gate: fails CI if thresholds are exceeded

## Configure
Set GitHub Actions secret `SAVANT_BASE_URL` to your Space URL.

## Thresholds
Edit `lab/thresholds.json`.

## Run locally
```bash
pip install -r lab/requirements-lab.txt
export SAVANT_BASE_URL="https://antonypamo-apisavant2.hf.space"
python lab/savant_lab_runner.py
```
