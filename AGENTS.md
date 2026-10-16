# AGENTS.md — Vibe Copy Content Factory (self-contained project)

- Work ONLY inside `C:/Проекты/VibeCopyContentFactory`. This repository includes the existing approved `./Remotion/` subfolder. **Do not access or modify `C:/Проекты/TonePaste`**, the public bot repository, and do not create a multi-root VS Code workspace.
- Main goal: implement functioning MVP Modes A/B as documented, focusing on time-to-demo. Read `README.md`, `docs/07_DECISIONS.md`, `docs/11_DEPLOYMENT_AND_REPOSITORIES.md`, `docs/05_TASKS_AND_ACCEPTANCE.md`, `TASKS.md` before large changes.
- The Worker interface is the read-only spec at `docs/contracts/worker-openapi.yaml`. Do not invent endpoints/fields or copy any Vibe Copy AI-pipeline Python code. If interface appears insufficient, record a proposed contract change rather than silently diverging.
- Preserve owner-approved visual Remotion v9 UI. It is **already** in `./Remotion` (capital R). Make only compatibility changes, keep working sample renders and don't move/overwrite assets. No new Telegram UI clone.
- Mode A: exactly 10 initial candidate slots; approve one -> proceed immediately to screencast/montage; retry only if explicitly requested; reject final -> possible PARTIAL. Mode B: approved cached assets only, never any paid AI call. Separate admin Telegram bot.
- No production deploy, payments, real AI provider charges, changing live secrets or live user DB without owner's explicit approval. For tests use fake providers, staging files and disposable DB.
- SQLite/WAL queue, local assets, one simultaneous heavy render (HP 8GB), FFmpeg final composer; avoid unnecessary infra complexity.
- Work autonomously through milestones with actual self-run tests; don't report mock tests as live integration. Update `TASKS.md` and `CHANGELOG.md` with actual changes and passing/failing command outputs after each milestone. Protect user's uncommitted changes; never run destructive reset/clean.
- When finished, report commands for local startup, status (MOCK/REAL), tested functions, pending secrets and exact blockers. Do not claim production ready until end-to-end real integration is verified.
