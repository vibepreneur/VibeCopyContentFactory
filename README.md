# Vibe Copy Content Factory — MVP

Private GitHub repository: [vibepreneur/VibeCopyContentFactory](https://github.com/vibepreneur/VibeCopyContentFactory), default branch `main`.

Git tracks Factory/Remotion source, documentation, dependency lockfiles and the existing Remotion sample assets. Local libraries/databases, generated videos, secrets, installed dependencies and portable tools are excluded; back up working materials separately.

## Local MOCK implementation

Python Factory, SQLite/WAL queue, Modes A/B, frozen-contract fake HTTP Worker/client, private Telegram adapter and real Remotion/FFmpeg integration are implemented. Real paid Worker/Kling integration is pending; no production deployment or publishing.

Start from this folder with the already prepared environment:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m factory doctor
.\.venv\Scripts\python.exe -X utf8 -m factory demo --verify-remotion
```

The demo uses its own SQLite database and scripted test reviews. It prints the MP4/report paths. Full setup, import format, review commands, bot startup and recovery: [local Windows guide](docs/12_LOCAL_RUN.md). Actual test evidence: [TASKS.md](TASKS.md).

**This is the independent Factory project.** Source path: `C:/Проекты/VibeCopyContentFactory`. Existing working Remotion v9 is already at `./Remotion/`; **do not relocate or reinitialize**. The public Vibe Copy source in `C:/Проекты/TonePaste` belongs to another repository and a separate VS Code window.

## User goal
Produce batches of 10 vertical videos for Reels/Shorts/TikTok automatically with the existing real-looking Telegram screencast generator. Mode A creates new approved AI cases and video assets (manual quality gate), Mode B recombines cached approved assets without paid AI requests. User manually chooses music on the social platform and uploads.

## Documents (Codex reads)
- `AGENTS.md` — rules and boundaries; `TASKS.md` — work queue and real test results; `CHANGELOG.md` — actual code changes.
- `docs/01_PRODUCT.md`, `docs/02_PRD.md` — business requirements and two modes.
- `docs/03_ARCHITECTURE.md`, `docs/11_DEPLOYMENT_AND_REPOSITORIES.md` — final two-repo topology.
- `docs/04_DATA_AND_API.md`, `docs/contracts/worker-openapi.yaml` — data and stable inter-service API.
- `docs/05_TASKS_AND_ACCEPTANCE.md`, `docs/06_TEST_PLAN.md` — milestones/acceptance.
- `docs/07_DECISIONS.md`, `docs/08_CODEX_RULES.md`, `docs/09_MIGRATION_AND_OPERATIONS.md` — decisions and workflow.
- `docs/10_EXISTING_REMOTION_AUDIT.md` — preserve working v9.

## Runtime topology
Factory Python app, separate Telegram admin bot, SQLite and local immutable asset storage, Processing Worker HTTP client (server hosted in **Vibe Copy**), `./Remotion/` CLI renderer, local FFmpeg composer. No shared FS/DB with VPS. Use fake Worker + pre-rendered avatar for offline tests. Secrets via `.env` only after owner config; no real paid AI in automated tests.

## For Codex
Use `PROMPTS/FACTORY_START.md` from the v0.5 documentation package. Read actual files and execute tests; the project may initially contain only documentation and Remotion. Don't assume it is already implemented.
