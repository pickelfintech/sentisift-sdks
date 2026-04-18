# Examples - Python SDK

Runnable examples for common integration patterns. Each script is self-contained: set `SENTISIFT_API_KEY` in your environment and run with the venv that has `sentisift` installed.

```bash
pip install sentisift
export SENTISIFT_API_KEY=sk_sentisift_your_key_here
python examples/quickstart.py
```

| File | What it demonstrates |
|---|---|
| `quickstart.py` | The minimal happy path: send three comments, print the result, print balance. |
| `analyze_with_intelligence.py` | Send enough comments to cross the processing threshold. Read Intelligence (themes, Omega Ratio) on Professional/Enterprise. Render Influence comments separately from organic ones. |
| `error_handling.py` | All the typed exceptions in one place. Shows how to read `docs_url` and `request_id` for self-service debugging. |
| `wait_for_ready.py` | Poll `/health` and use `wait_until_ready()` to gate on cold-start model loading after a deploy. |
| `batched_ingestion.py` | A long-running worker that pulls comments from a queue and submits them in batches per article. Honors retry-after on 429. |

For real-world deployment patterns (FastAPI middleware, Flask hook, Django signal), see the **Integration Recipes** section of [api-docs.html](https://sentisift.com/api-docs.html).
