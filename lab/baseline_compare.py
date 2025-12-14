from __future__ import annotations
import os, json, time
from typing import Dict, Any, List, Tuple
import numpy as np
import requests
from sentence_transformers import SentenceTransformer

BASE_URL = os.environ.get("SAVANT_BASE_URL", "https://antonypamo-apisavant2.hf.space").rstrip("/")
DATASET_PATH = os.environ.get("SAVANT_EVALSET", "lab/data/evalset.jsonl")
OUT_DIR = os.environ.get("ARTIFACTS_DIR", "artifacts/lab")
TIMEOUT = float(os.environ.get("SAVANT_TIMEOUT", "30"))

# Baselines (CPU-friendly). You can add/remove.
BASELINES = [
    ("all-MiniLM-L6-v2", "sentence-transformers/all-MiniLM-L6-v2"),
    ("all-mpnet-base-v2", "sentence-transformers/all-mpnet-base-v2"),
]

SESSION = requests.Session()

def _post(path: str, payload: Dict[str, Any]) -> Tuple[int, Any, float]:
    t0 = time.perf_counter()
    r = SESSION.post(f"{BASE_URL}{path}", json=payload, timeout=TIMEOUT)
    dt = time.perf_counter() - t0
    try:
        body = r.json()
    except Exception:
        body = r.text
    return r.status_code, body, dt

def load_dataset(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows

def ndcg_at_k(ranked_ids: List[str], relevant: set, k: int = 3) -> float:
    def dcg(ids: List[str]) -> float:
        s = 0.0
        for i, _id in enumerate(ids[:k], start=1):
            rel = 1.0 if _id in relevant else 0.0
            s += (2**rel - 1) / np.log2(i + 1)
        return s
    ideal = list(relevant)[:k]
    idcg = dcg(ideal) if ideal else 1.0
    return float(dcg(ranked_ids) / idcg)

def mrr_at_k(ranked_ids: List[str], relevant: set, k: int = 3) -> float:
    for i, _id in enumerate(ranked_ids[:k], start=1):
        if _id in relevant:
            return float(1.0 / i)
    return 0.0

def rank_with_st(query_emb: np.ndarray, cand_embs: np.ndarray, cand_ids: List[str]) -> List[str]:
    # cosine similarity
    q = query_emb / (np.linalg.norm(query_emb) + 1e-12)
    C = cand_embs / (np.linalg.norm(cand_embs, axis=1, keepdims=True) + 1e-12)
    sims = C @ q
    order = np.argsort(-sims)
    return [cand_ids[i] for i in order]

def rank_with_savant_api(query: str, candidates: List[Dict[str, str]]) -> Tuple[List[str], float]:
    # uses /v1/rerank, which ranks candidates for a query using RRFSAVANTMADE on the server
    payload = {"query": query, "documents": [{"id": c["id"], "text": c["text"]} for c in candidates]}
    status, body, dt = _post("/v1/rerank", payload)
    if status != 200:
        raise RuntimeError(f"/v1/rerank failed: status={status} body={str(body)[:200]}")
    results = body.get("results", [])
    ranked = [str(r["id"]) for r in sorted(results, key=lambda x: x.get("rank", 1e9))]
    return ranked, dt

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    data = load_dataset(DATASET_PATH)

    # Load baselines once
    models = []
    for name, model_id in BASELINES:
        models.append((name, SentenceTransformer(model_id)))

    metrics = {"Savant_RRFSAVANTMADE(API)": {"ndcg@3": [], "mrr@3": [], "latency_s": []}}
    for name, _ in models:
        metrics[name] = {"ndcg@3": [], "mrr@3": []}

    for row in data:
        q = row["query"]
        cands = row["candidates"]
        rel = set(row.get("relevant", []))
        cand_ids = [c["id"] for c in cands]
        cand_texts = [c["text"] for c in cands]

        # Savant rank via API
        ranked_savant, dt = rank_with_savant_api(q, cands)
        metrics["Savant_RRFSAVANTMADE(API)"]["ndcg@3"].append(ndcg_at_k(ranked_savant, rel, 3))
        metrics["Savant_RRFSAVANTMADE(API)"]["mrr@3"].append(mrr_at_k(ranked_savant, rel, 3))
        metrics["Savant_RRFSAVANTMADE(API)"]["latency_s"].append(dt)

        # Baselines locally
        for name, m in models:
            q_emb = np.asarray(m.encode([q], normalize_embeddings=False)[0], dtype=float)
            c_emb = np.asarray(m.encode(cand_texts, normalize_embeddings=False), dtype=float)
            ranked = rank_with_st(q_emb, c_emb, cand_ids)
            metrics[name]["ndcg@3"].append(ndcg_at_k(ranked, rel, 3))
            metrics[name]["mrr@3"].append(mrr_at_k(ranked, rel, 3))

    summary = {}
    for name, vals in metrics.items():
        summary[name] = {
            "ndcg@3_mean": float(np.mean(vals["ndcg@3"])) if vals["ndcg@3"] else 0.0,
            "mrr@3_mean": float(np.mean(vals["mrr@3"])) if vals["mrr@3"] else 0.0,
        }
        if "latency_s" in vals:
            arr = np.array(vals["latency_s"], dtype=float)
            summary[name].update({
                "latency_mean_s": float(arr.mean()),
                "latency_p95_s": float(np.quantile(arr, 0.95)) if len(arr) else 0.0,
            })

    out = {
        "base_url": BASE_URL,
        "dataset": os.path.basename(DATASET_PATH),
        "N_queries": len(data),
        "metrics": summary,
    }
    with open(os.path.join(OUT_DIR, "baseline_compare.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
