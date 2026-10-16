# Decision Log v0.5

## LOCKED by owner (do not ask again)
1. Two modes. A: new processing and animated avatar + Remotion screencast + hook/captions/CTA, save quality approved source materials. B: combine existing approved assets only, track usage; no AI.
2. Each mode starts with Telegram command target 10; A creates **exactly 10 initial candidates**; immediately process each approve independently. Retry only per owner action; final reject leaves PARTIAL, no silent replacement. Separate human review for results and final MP4.
3. Separate closed admin Telegram bot for factory, not commands in public bot.
4. Public Vibe Copy on VPS; factory initially on HP, future relocation possible.
5. **One repository of Vibe Copy**, public Telegram process and **separate Processing Worker process** share one AI core. Factory has independent repo, no copied Analyzer/Generator/Validator or Telegram FSM.
6. Worker REST v1 over private Tailscale/WireGuard network; separate authentication and AI costs; `contract_version` vs `pipeline_version`.
7. Remotion v9 visual interface complete and approved by owner. Use existing source without redesign; parametric three photos; sequential local rendering; FFmpeg compositing.
8. 50 curated original/reference pairs to start; 100–200 source avatar pictures planned, 50–100 usable screencasts targeted; library reuse first, no giant pre-renders.
9. Prompt/caption overlays generated automatically by templates/optional LLM; user only QA, manual music choice and manual social publishing.
10. Persistent SQLite combination matrix with uniqueness + preferential new avatar/screencast pairs. Cost events saved for all paid AI attempts incl. failed.
11. User prioritizes **fastest working MVP**, Codex should implement/test autonomously with only final result review; no premature polish or server redesign.

## Architect FIXED for speed (change only with clear justified blocker)
A1. Factory SQLite WAL local + local folders; Worker factory jobs SQLite separate from public user DB. No Redis/Celery/required Docker for MVP.
A2. One heavy render at once (Remotion concurrency starting 1); AI provider concurrency conservative 1 initially until true shared provider quota understood.
A3. Private HTTP + bearer; no public open API. Local dev with mock Worker, real VPN only at deploy.
A4. MVP one montage scenario (expandable to 4), template-driven captions (LLM optional), FFmpeg final assembly; no automated artistic QA.
A5. 3 maximum owner-initiated retries per case by default and clear budget guard; do not invoke actual provider without configured spending limits and owner's permission.
A6. Mode A genuinely animates static avatar via Kling when live configured; offline demo substitutes pre-existing approved avatar clip with clear designation.
A7. Remotion v9 is **already located** inside `C:/Проекты/VibeCopyContentFactory/Remotion` as part of the Factory project, not a third VS Code workspace/repository. Do not duplicate or relocate it. Factory integration uses relative path `./Remotion`, preserves all approved Telegram UI; avoid creating a second Remotion copy.

A8. No multi-root `.code-workspace`. Factory and Vibe Copy are developed in **separate VS Code windows**, with separate repositories and agents. Integration correctness enforced through one frozen OpenAPI v1 contract snapshot, consumer/producer contract tests and an end-to-end smoke test, not through opening code in one IDE window.
A9. Vibe Copy Worker is the source of truth for its REST contract; its copy of `docs/content_factory_worker/contracts/worker-openapi.yaml` is canonical. Factory has a read-only synchronized snapshot `docs/contracts/worker-openapi.yaml`. Do not make incompatible independent edits. Before production, run contract and real cross-product integration tests.

## OPEN, not blocker for mock MVP
O1. Actual provider API keys/Telegram admin ID/VPS VPN addresses/deploy credentials: owner provides after tests, never ask to paste secrets into chat.
O2. Exact rights/licenses for images in commercial use: import metadata, block unknown rights on publishing, can test with local example assets.
O3. Precise creative templates and final CTA wording: use placeholders/config defaults; optimize after working pipeline.
O4. Which Kling version and paid animation API accepted: plugin layer, select in live integration step.

## POST MVP
Additional 3 layouts, LLM hooks, avatar style variants (e.g. hair/skin), remote rendering, multi-user dashboards, automated uploads.
