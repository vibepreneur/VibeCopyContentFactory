# Data + contract for Factory

## Storage (SQLite WAL local to factory)
- `assets(id, type, path, sha256, mime, width, height, duration, rights_status, approved_at, source_id, created_at, status)`; type original/ref/result/static_avatar/animated_avatar/screencast/other.
- `photo_pairs(id, original_asset_id, reference_asset_id, tags_json, status)`; ~50 manually curated explicit pairs. No random pairing by default.
- `cases(id, pair_id, processing_request_id, result_asset_id, screencast_asset_id, pipeline_version, status, reviewed_at)`.
- `processing_attempts(id, case_id, request_id UNIQUE, attempt_no, worker_status, generation_cost_amount nullable, cost_status, created_at)`.
- `batches(id, mode, target_count, status, created_at, finished_at)`; `batch_slots(id,batch_id,case_id,attempt_no,stage,status)`; 10 initial Mode A slots not auto-replenished.
- `hooks(id, text, tags_json, status)`, `scenarios(id,name,version,definition_json,status)`.
- `combinations(id,batch_id,avatar_clip_asset_id,screencast_asset_id,hook_id,scenario_id,scenario_version,creative_revision,status,created_at)` with UNIQUE on all identity fields; exact key includes revision so edits are explicit.
- `video_jobs(id, combination_id, final_asset_id, duration, output_status, review_status, error_code, created_at)`.
- `expenses(id, source_call_id UNIQUE nullable, source_type, batch_id, asset_id, currency, amount_nullable, cost_status actual|estimated|unknown, provider, created_at)`.
- `queue_jobs(id,type,payload_json,status,lease_until,attempt_count,created_at,updated_at)`; recover on restart. Do not rely on in-memory tasks.

## Review transitions
Candidate: `PAIR_SELECTED → PROCESSING_QUEUED → PROCESSING → PENDING_REVIEW → APPROVED | RETRY_REQUESTED | REJECT_FINAL`. Retry uses new request_id and returns to PROCESSING, no silent paid retry. Approved triggers `SCREENCAST_QUEUED → SCREENCAST_RENDERED → VIDEO_QUEUED → VIDEO_RENDERED → VIDEO_PENDING_REVIEW → VIDEO_APPROVED | VIDEO_REJECTED | VIDEO_REMAKE_REQUESTED`. Invalid transitions rejected; callbacks idempotent.

## Factory → Worker
Factory uses the **read-only matching snapshot** `docs/contracts/worker-openapi.yaml`. The authoritative specification is `TonePaste/docs/content_factory_worker/contracts/worker-openapi.yaml` in Vibe Copy; two copies initially have identical SHA-256 and contract v1. When server changes the contract, update the factory snapshot intentionally and rerun client contract tests; do not independently invent API fields. `POST /v1/jobs` multipart pair+UUID; `GET /v1/jobs/{id}`; `GET /v1/jobs/{id}/result` binary; `GET /v1/capabilities`. Separate `contract_version` from `pipeline_version`. Reconcile unknown provider states, no auto-dup paid calls.

## Factory → Remotion v9 (`./Remotion/`, internal adapter)
Input case config should point to unique immutable files for original/reference/result, scenario optional, run with one CLI subprocess and known output path; validate input file existence and formats, render result `1080x1920,30fps`, return path/hash/size. Current v9 has shared `src/case.generated.mjs` and `tools/render-case.mjs` concurrency=1; sequential one at a time and unique staging case folders. Avoid writing over shared original `assets/` and show two-case test.

## Example factory case metadata (proposed)
```json
{"case_id":"CASE_014","pair_id":"PAIR_014","assets":{"original_asset_id":"O014","reference_asset_id":"R014","result_asset_id":"G014"},"processing":{"request_id":"0fdc5400-3cf3-4097-9e71-6e51ce43b87e","pipeline_version":"rev-xyz"},"review_status":"APPROVED","screencast":{"template":"v9_social_fill","duration_seconds":22}}
```

## File layout
`data/{staging,approved/{avatars,cases,screencasts,final},rejected,logs}`, `data/` not version-controlled, separate root ENV for path and disk caps. `approved` immutable, multiple outputs reference approved originals. Clean staging by TTL except accounting history.
