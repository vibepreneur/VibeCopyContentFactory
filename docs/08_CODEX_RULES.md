# Autonomous Codex coding workflow

## How to work without demanding owner's micro-decisions
1. Read docs and source; determine current tests and env. List two or three internal choices only if a change could break production; otherwise choose simplest documented default.
2. Execute code/test cycles. Do not stop at a proposal or TODO skeleton unless required dependency or permission is genuinely unavailable.
3. After each completed phase update `TASKS.md` and `CHANGELOG.md` with file list + real test commands/results. Mark `MOCK` vs `REAL` explicitly.
4. No code deletion beyond own generated artifacts. No risky git clean/reset. Leave existing unstaged user changes intact. Do not deploy to production or auto-run paid provider calls.
5. If lengthy session ends, leave copy-paste-ready `NEXT_STEP` and exact test commands in TASKS.md.
6. When Codebase and spec conflict, inspect actual code, preserve user behavior, implement closest stable contract, note deviation explicitly.

## Documentation organization
- Factory root AGENTS.md short persistent policy. `README.md` navigation/start, `docs/*` source of product/architecture, `TASKS.md` working checklist, `CHANGELOG.md` factual history.
- Vibe Copy root `AGENTS.md` already belongs to the original project, installer appends only two-line pointer; worker docs in `docs/content_factory_worker/`, tasks and changelog separately.
- `SKILL.md` not needed for MVP; reusable discrete automation skill can be built later if pattern repeats.

## No false completion
'Complete' only after green automated tests. 'Integration tested' only when real network/service exercised. 'Ready to deploy' is not 'deployed'. For API provider calls include cost and explicit user authorization.
