## Minimal Runnable AI Path

Train the lightweight baseline:

```powershell
python train_minimal_baseline.py
```

This writes:

- `detection_service/artifacts/minimal_baseline.pkl`
- `detection_service/artifacts/minimal_baseline_eval.json`
- `detection_service/artifacts/minimal_dataset/`

Run the AI HTTP service:

```powershell
python ai_http_service.py --port 8010
```

Use the trainable minimal profile by passing `parameters.model_profile = "minimal_trainable"` in the image batch request.

Inspect the current profiles:

```powershell
curl http://127.0.0.1:8010/api/v1/admin/model-registry?profile=minimal_trainable
```
