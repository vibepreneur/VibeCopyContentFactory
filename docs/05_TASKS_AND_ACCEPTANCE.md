# Fast MVP plan for Codex

**Goal:** working two-mode MVP, not a polished platform. Developer agent may execute phases continuously and test them itself; user final reviews only after runnable build. When missing external paid credentials, use mocks and report live integration pending.

| Stage | Deliverable | Definition of done (automated) |
|---|---|---|
| M0 (parallel with Worker W0-W5) | Python factory package + SQLite+assets + repo rules | all migrations on fresh temp SQLite, import 2 sample pairs |
| M1 | Existing `./Remotion/` v9 CLI adapter | 2 different triples render as separate MP4 without manual file swap or UI drift; no concurrent render |
| M2 | FFmpeg composer + templated hooks/captions/CTA | 1 master ~30sec 1080x1920, then 10 from approved test assets; ffprobe passes |
| M3 | Mode B selector + unique combination rows | 10 unique combos, exact replay forbidden even during parallel reservations; no AI calls |
| M4 | Mode A + Processing Worker client + 10 independent pending reviews | 10 review candidates from fake Worker; approve one immediately triggers M1/M2, retry new id, reject_final partial |
| M5 | Separate Telegram admin-bot, allowlist, callback UX and delivery | mocked Telegram gateway covers routing; with real admin token one manual review trial |
| M6 | Real provider adapters (Worker shared Vibe core and Kling), caps, end-to-end locally then private VPS | explicit paid test approval, real secrets configured locally, no production deploy without new authorization |

**Critical path for shortest demo:** Use existing pre-rendered avatar MP4 and curated original/ref/result test assets first to finish M1/M2/M3 + mock A. Then connect Worker and Kling. The Mode A interface still means new avatar/screencast on live operation; don't call mock result production-ready.

## Non-negotiable acceptance
- Existing public Vibe Copy tests green, no change in user credits/payment behavior.
- Worker idempotency replay makes **zero** additional provider calls; request ID conflict returns 409; no fake user created.
- Factory human review of AI result occurs before Remotion; individual approved slot immediately starts video, even if other nine pending; final rejected slot does not silently replace it.
- No unapproved images in reusable library; AI expenses from failures retained.
- B only approved files, unique combination DB constraint + pair novelty preference; no API spend.
- Ready mp4 generated locally, archived, sent to admin manually testable; 1 heavy render at once.
- No secrets in git, no public API exposure, no auto-deploy, no production database touching.
