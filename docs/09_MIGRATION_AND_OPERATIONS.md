# Operational guidelines

## Local Windows HP
- Python venv for Factory, Node/npm for its local `./Remotion/` module, FFmpeg/ffprobe in PATH. Run `npm install` for imported source, not for the old source project if existing dependencies already present (avoid unintended upgrades), pin package-lock.
- CPU Intel i5-8265U and 8 GB RAM: one heavy render, no concurrent browser remotion instances; close memory-intensive applications, benchmark a single case before 10.
- `data/` outside Git; backup approved library + factory.sqlite3 routinely. Never expose `.env` in uploads/screenshots.

## VPS Worker and bot
- One source repository/one deployment revision, two supervised processes: public bot + Worker; separate env worker with auth token and factory db path. Deploy requires separate explicit authorization.
- Run worker on loopback/private interface only + tailnet/firewall, dedicated bearer. Document and test exactly which port and path exposed; disable public access. HTTPS if network path requires it; tailnet authenticates transport but not replaces bearer and file validation.
- Smoke tests in staging: public bot existing user flow works, worker capabilities/status, one authorised processing at owner-approved spend. Separate cost journal and no user credits touched.
- Rollback code revision and factory schema using tested migrations/backup; never modify live user DB on speculation.

## Baselines and plans
Keep sqlite schema migrations idempotent and versioned. New schema always established on ephemeral test DB before use. User supplies VPN and secrets only to local env, not chat; Codex never commits them.
