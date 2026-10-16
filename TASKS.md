# TASKS — Factory

- [x] F0: Inspected actual Remotion, preserved 48-file hash manifest/source backup; newly rendered baseline MP4 verified by ffprobe.
- [x] F1: Local Python Factory, SQLite/WAL schema, immutable library and contract-conforming durable fake HTTP Worker. Tests pass on disposable databases.
- [x] F2: Two different photo triples each rendered twice; decoded original/reference/result frames match each repeat and differ between cases. Inputs unchanged, config restored, serial render mutex verified.
- [x] F3: 12 actual masters independently validated after explicit limited-range/BT.709 conversion: H.264/yuv420p, 1080×1920/30fps, exactly 900 frames/30s, no audio; hooks/event captions/CTA present.
- [x] F4: Mode B selector: concurrent reservations of 20 distinct combinations, pair novelty and exhaustion verified; Worker client never constructed. Actual 10-MP4 run tracked under F8.
- [x] F5: Mode A: 10 candidates via real localhost HTTP/fake provider; idempotent review, immediate queueing, 3 explicit retries, PARTIAL and per-attempt expense summaries verified.
- [x] F6 (MOCK): Private bot/controller, allowlist, review UI and delivery adapter; actual aiogram dispatch and sendMediaGroup/sendVideo/sendDocument tested with an in-memory Telegram transport. Live token trial pending.
- [x] F7 (MOCK): AvatarProvider interface, cached approved clip provider, technical test clips and spending guards tested. Live Kling API/model adapter intentionally blocked pending owner selection/approval.
- [x] F8 (MOCK): Frozen-schema fake producer + consumer HTTP tests and actual local media E2E completed; A PARTIAL and B 10/10, zero B provider calls. Actual VPS producer/service trial NOT RUN.
- [ ] REAL integration gate: choose/implement Kling API adapter, configure local secrets/VPN/spending caps, obtain explicit paid-test authorization, verify real Worker + Telegram + Kling end-to-end. No production deployment authorized.

Update checked boxes only after actual tests; log commands and results. State fake vs real integration. If credentials unavailable, finish mock MVP before reporting external blockers.

## 2026-10-16 — F0/F1/F4/F5 verification (MOCK)

- `python -X utf8 tools/bootstrap.py backup` → PASS: 48 files in `data/baseline/manifest.json`; source copies under `data/baseline/Remotion/`.
- `python -m venv .venv` → initial FAIL: sandbox denied ensurepip temporary files. Escalated `.venv/Scripts/python.exe -X utf8 -m ensurepip --upgrade --default-pip` → PASS.
- `.venv/Scripts/python.exe -X utf8 -m pip install -r requirements.txt` → initial sandbox index failure; escalated install → PASS.
- `python -X utf8 tools/bootstrap.py ffmpeg` → initial network denial; escalated run → PASS, portable FFmpeg 9.0.2 archive SHA-256 verified.
- From Remotion: `node node_modules/@remotion/cli/remotion-cli.js render src/index.ts VibeCopySocialFill out/FACTORY-baseline.mp4 --codec=h264 --concurrency=1 --disallow-parallel-encoding` → initial sandbox `spawn EPERM`; escalated run PASS, 900 frames, 13,263,593 bytes.
- `factory.media.probe(...FACTORY-baseline.mp4, expected=30)` → PASS: H.264, 1080×1920, 30/1, 30.000000s.
- `.venv/Scripts/python.exe -X utf8 -m pytest -q --basetemp=.cache/pytest` → first run 8 passed / 1 failed (test upload threshold smaller than PNG fixture). Corrected fixture threshold.
- `.venv/Scripts/python.exe -X utf8 -m pytest -q -p no:cacheprovider --basetemp=.cache/pytest` → PASS: **9 passed**, 18.87s; Python 3.14 deprecation warnings from old pytest-asyncio.
- `.venv/Scripts/python.exe -X utf8 -m factory doctor` → PASS: Python 3.14.0, Node v24.11.1, full FFmpeg/ffprobe, contract 1.0 hash OK; REAL integrations UNVERIFIED.
- Full media demo running separately; first sandbox attempt failed on Chromium and was resumed with escalation, preserving its SQLite jobs/UUIDs.
- No `.git` directory was present at start. No repository initialized, no commits, no deploy or paid calls. Public bot regression tests NOT RUN (other project outside authorized scope).

## 2026-10-16 — recovery and Telegram adapter milestone (MOCK)

- Added migration v2: queue owner PID + process start time, detecting dead runners without confusing recycled PIDs. Heavy render recovery also waits for any orphaned render subprocess.
- Expanded suite first run → 16 passed / 1 failed: Windows denied reading the already locked mutex byte. Fixed initialization to inspect file size without reading that byte; lock test uses an isolated directory to avoid competing with the actual demo.
- `.venv/Scripts/python.exe -X utf8 -m pytest -q -p no:cacheprovider --basetemp=.cache/pytest` → PASS: **17 passed**, 58.04s.
- Covered ambiguous submit restart with zero resubmits, nullable costs, cached/Kling guards, final approve/reject/remake idempotency, technical resume with the same combination, 50-pair import, and cross-process mutex.
- Actual aiogram Dispatcher + Bot exercised with a recording BaseSession: unauthorized commands blocked, authorized routing works; delivery uses sendMediaGroup/sendMessage/sendVideo/sendDocument. No Telegram network calls.
- aiogram 3.29.0 was yanked by its publisher; pinned and installed 3.31.0 locally. pytest-asyncio updated to 1.4.0 for Python 3.14 compatibility; next full-suite result pending.
- Media demo: first A master rendered and validated; immediate-approval proof records **9 other candidates pending**. Second triple and repeated-frame verification are in progress.

## 2026-10-16 — F2/F3/F7 MOCK media milestone

- `.venv/Scripts/python.exe -X utf8 -m factory demo --resume data/demo/c2f46518-ce4e-4912-9543-9c4f84334dc8 --verify-remotion` → two distinct A cases rendered; each then rendered again. See `demo-state.json` → `remotion_verification`: six decoded frame hashes, source hashes and repeated output paths.
- An already running demo had the old mutex implementation loaded; an independent preview exposed its locked-byte error. Restarted with the fixed implementation, reusing the completed repeated MP4 rather than rendering it again. No new Worker attempts created by technical resume.
- Two actual 30s FFmpeg masters passed the composer's ffprobe checks. `tools/verify_artifacts.py ... --preview-only` → PASS, montage storyboard visually inspected; it is explicitly not the complete artifact validation.
- `.venv/Scripts/python.exe -X utf8 -m pytest -q -p no:cacheprovider --basetemp=.cache/pytest` after dependency updates → **21 passed in 50.48s**, no warnings. Final source check → **21 passed in 75.24s**, no warnings.
- From Remotion: `npm.cmd run check:v9` → PASS (CASE_001 900 frames, CASE_SHORT 661); `npm.cmd run check:syntax` → PASS after actual Factory renders.
- `.venv/Scripts/python.exe -X utf8 -m pip check` → PASS, no broken requirements. Full environment frozen in `requirements.lock`.
- Worker snapshot SHA-256 rechecked unchanged: `836bf9654da8bc538de67434d9e94a4682fd1c127a08647283151d24485b7c74`.
- Final Mode B 10-MP4 run and independent all-artifact verification still in progress; F8 remains unchecked until those commands finish.

## 2026-10-16 — independent media validation caught and corrected encoding issue

- First full demo completed: A 10 slots / 2 masters / 8 explicit rejects → PARTIAL; B 10 masters → COMPLETED; 11 fake attempts including one requested retry, **0 B provider calls**, **0 real paid calls**.
- `.venv/Scripts/python.exe -X utf8 tools/verify_artifacts.py data/demo/c2f46518-ce4e-4912-9543-9c4f84334dc8` → FAIL: final `pix_fmt` was `yuvj420p` despite the requested pixel format, due to inherited full-range metadata from Remotion.
- Fixed composer with explicit TV-range conversion and BT.709 encoder metadata; added `INVALID_FINAL_PIXEL_FORMAT` validation before review/delivery.
- `.venv/Scripts/python.exe -X utf8 tools/recompose_demo.py data/demo/c2f46518-ce4e-4912-9543-9c4f84334dc8 --limit 1` → PASS: first repaired master validated as yuv420p, same video/combination ID, zero Worker calls.
- Remaining 11 test-only masters are being re-encoded with the same work orders. Original approved files are retained immutably; active video jobs point to corrected files. F3/F8 await complete revalidation.

## 2026-10-16 — FINAL MOCK MVP verification

- `.venv/Scripts/python.exe -X utf8 tools/recompose_demo.py data/demo/c2f46518-ce4e-4912-9543-9c4f84334dc8 --skip 1` → PASS: remaining **11 masters**, same video/combination IDs, zero Worker calls.
- `.venv/Scripts/python.exe -X utf8 -m factory demo --resume data/demo/c2f46518-ce4e-4912-9543-9c4f84334dc8 --verify-remotion` → PASS, 4.81s checkpoint replay without new renders/Worker attempts. Report and human-readable exports refreshed.
- `.venv/Scripts/python.exe -X utf8 tools/verify_artifacts.py data/demo/c2f46518-ce4e-4912-9543-9c4f84334dc8` → PASS: **12 masters**, H.264/yuv420p, 1080×1920, 30 fps, 30s, 900 packets each; monotonic DTS and 30 fps PTS grid; all baseline sources/assets/old sample videos unchanged except the intended CLI adapter. Corrected storyboard inspected.
- `.venv/Scripts/python.exe -X utf8 -m pytest -q -p no:cacheprovider --basetemp=.cache/pytest` → FINAL PASS: **22 passed in 42.20s**, no warnings. Added true-HTTP preflight failure/recovery check: no POST/no spend on failed auth, same UUID on technical resume; ambiguous POST still never resubmits.
- Final `factory doctor` → PASS: MOCK, Python 3.14.0, Node v24.11.1, portable full FFmpeg/ffprobe, frozen contract hash OK. `pip check`, Remotion syntax and v9 checks also PASS.
- A: exactly 10 initial slots; first master rendered with 9 other candidates pending; one explicitly requested retry/new UUID; 2 test-approved masters + 8 explicit rejects → PARTIAL. This is not a claim that 10 A masters were rendered.
- B: 10 distinct active combination keys and 10 actual masters → COMPLETED under scripted test QA. **0 B provider calls, 0 real paid calls**. Fake expense sum 13.75 RUB is fixture data, not money spent.
- Measured heavy processes: 31 (includes 4 successful Remotion renders, initial sandbox failure, technical avatars and both original/corrected FFmpeg encodes). Sum of measured execution durations **1495.28s**, peak summed process-tree RSS **1,098,551,296 bytes**. Includes repair/QA work; excludes baseline render, OS and unrelated applications. Raw evidence: `logs/performance.jsonl`.
- Artifacts: [representative MP4](data/demo/c2f46518-ce4e-4912-9543-9c4f84334dc8/demo-master.mp4), [report with all 12 paths/SHA-256](data/demo/c2f46518-ce4e-4912-9543-9c4f84334dc8/report.json), `exports/A-*.mp4`, `exports/B-*.mp4`, `qa/verification.json`, `remotion-verification.jpg` in the same demo directory. Test decisions do not replace human creative QA.

### Complete automated case list (22 PASS)

```text
tests/test_contract.py::test_http_idempotency_binary_and_restart
tests/test_contract.py::test_auth_limits_mime_paths_and_errors
tests/test_contract.py::test_version_guard_and_unknown_cost
tests/test_contract.py::test_failed_attempt_cost_is_retained
tests/test_contract.py::test_all_contract_image_formats[JPEG-image/jpeg-.jpg]
tests/test_contract.py::test_all_contract_image_formats[PNG-image/png-.png]
tests/test_contract.py::test_all_contract_image_formats[WEBP-image/webp-.webp]
tests/test_contract.py::test_rate_limit_and_bad_result_hash
tests/test_factory.py::test_mode_a_review_retry_partial_and_cost
tests/test_factory.py::test_mode_b_parallel_unique_novelty_and_zero_worker
tests/test_factory.py::test_queue_restart_and_immutable_library
tests/test_factory.py::test_bot_auth_callbacks_and_missing_delivery
tests/test_factory.py::test_retry_limit_and_reconciliation_guard
tests/test_recovery_and_reviews.py::test_ambiguous_submit_restart_never_resubmits
tests/test_recovery_and_reviews.py::test_unknown_cost_and_avatar_guards
tests/test_recovery_and_reviews.py::test_preflight_failure_can_resume_same_uuid_without_new_attempt
tests/test_recovery_and_reviews.py::test_video_approve_reject_remake_idempotency
tests/test_recovery_and_reviews.py::test_failed_render_resume_keeps_combination
tests/test_recovery_and_reviews.py::test_import_50_pairs_missing_asset_and_conflict
tests/test_recovery_and_reviews.py::test_heavy_lock_serializes_processes
tests/test_telegram_adapter.py::test_actual_aiogram_routing_and_allowlist
tests/test_telegram_adapter.py::test_actual_telegram_delivery_methods_are_mocked
```

### Startup / exact remaining blockers

From this project root, `.venv/Scripts/python.exe -X utf8 -m factory demo` starts a fresh isolated demo with no secrets; add `--verify-remotion` for the four-render repeat check. [Full Windows startup/review/recovery instructions](docs/12_LOCAL_RUN.md).

- REAL Mode A is deliberately blocked: Kling is currently a provider interface + disabled guard, not a working live API implementation. Owner must select API/model; then implement/authenticate that adapter and verify it with approved spending caps.
- Real Worker needs `WORKER_BASE_URL`, separate `WORKER_BEARER_TOKEN`, private VPN connectivity and staging producer/consumer smoke validation. Current canonical VPS contract/service behavior was not inspected; only the frozen local snapshot and fake producer were tested.
- Real admin Telegram needs a separate `FACTORY_TELEGRAM_TOKEN`, `FACTORY_ADMIN_USER_IDS` and a manual album/MP4 trial. Only mock Telegram transport was used.
- Paid tests require explicit owner approval and finite budgets. Commercial rights on demo materials are not established; imports are marked test-only. Human creative review remains pending.
- Public bot regression suite NOT RUN because TonePaste is outside the authorized workspace. No live secrets, public bot, payments, production DB, deploy or publishing touched.
- NEXT_STEP for REAL: configure secrets locally (never in chat), agree Kling API and staged test budget, then implement/verify the live adapter and private Worker/Telegram integration. MOCK delivery has no outstanding blocker.

## 2026-10-16 — GitHub repository setup

- [x] Created private repository [vibepreneur/VibeCopyContentFactory](https://github.com/vibepreneur/VibeCopyContentFactory); default branch `main`, local `origin` uses HTTPS with the existing Git Credential Manager account.
- `git init -b main` / staging → PASS. Added `pytest-cache-files-*/` ignore rule; 102 files staged, 8,759,253 uncompressed bytes; largest file 6,544,126 bytes. No working data, generated renders, local environment or dependencies staged.
- Staged-file audit → initial secret-pattern flag in `tests/test_telegram_adapter.py`; reviewed both occurrences as synthetic alphabet tokens used only with `RecordingSession`. Final audit → PASS, no other findings; frozen Worker contract SHA-256 unchanged.
- Initial sandbox credential read and `.git` metadata writes → permission denied. Scoped escalated retries → PASS; credentials never printed or committed. GitHub CLI is not installed; repository creation/verification used authenticated GitHub REST with existing credential-helper authorization.
- `git commit -m "Initial commit: local MOCK content factory"` → PASS, `46a6f7e6aa3f3bb34f0f4701bd1df3f8f93628d7`.
- `git push -u origin main` → PASS; remote tracking established. GitHub API GET repository/commit/tree → PASS: private=true, matching commit SHA, 102 files, tree not truncated, no excluded working paths.
- `git fsck --full` → PASS; `git status --short --branch` → `## main...origin/main` with no pending changes before this documentation update. No application source change, new render, functional test run or deployment was needed for repository setup.
