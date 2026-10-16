# Two projects and one interface (final decision)

## Physical folders and VS Code
- **Project 1 / Vibe Copy (public bot + Worker):** `C:/Проекты/TonePaste`. Open only this folder in its own VS Code window for Worker tasks.
- **Project 2 / Content Factory with Remotion:** `C:/Проекты/VibeCopyContentFactory`. Open only this folder in a separate VS Code window for factory tasks. It already contains `./Remotion` (owner-provided v9).
- No multi-root `.code-workspace` is required or desired. The old `VibeCopyContentFactory.code-workspace` is obsolete, can be ignored; do not delete any source project because of it.
- Never move `./Remotion` automatically. Never pull public Vibe Copy sources into the factory repo. Two processes in Vibe Copy repo are public Telegram bot and Worker; they share the SAME AI processing Python modules on the VPS.

## How isolated agents still integrate
- Worker has authoritative, versioned **OpenAPI spec** `TonePaste/docs/content_factory_worker/contracts/worker-openapi.yaml`.
- Factory has matching **read-only snapshot** `VibeCopyContentFactory/docs/contracts/worker-openapi.yaml` (v1 same SHA on delivery).
- Worker must implement the spec and test it using mock providers and local HTTP ASGI test client.
- Factory must implement client strictly from its snapshot, using a mock server conforming to the same spec; do NOT import the Worker Python project and do NOT access Worker SQLite directly.
- When both are runnable, conduct a real controlled test through private Tailscale/WireGuard API: submit one case, status poll, fetch result, manual approval, Remotion render. This test requires network/secrets and human permission for paid generation; can test with a fake AI provider first.
- If API changes, update the canonical spec in Worker first; copy the same file to Factory; bump contract version for breaking changes; run producer+consumer tests before release. Avoid silently changing the factory snapshot independently.

## Responsibility ownership
- Worker: AI analyzer, generator, validator; provider cost, version, idempotency, result binary; no Telegram user charging.
- Factory: asset libraries, manual review, Telegram admin, Remotion, Kling avatar animation, montage, usage matrix and creative review.
- Contract is the **shared context**; same editor window is not a requirement. A temporary read-only view of both codebases can help on difficult integration issues, but is optional and should not be the normal daily workspace.
