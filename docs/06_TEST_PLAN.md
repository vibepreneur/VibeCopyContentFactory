# Test plan (Codex must execute)

## Zero-secret tests (CI/local)
1. Worker API auth: 401 without bearer, allowed client with correct token, limit accepted upload types/size, rejects forged paths.
2. Idempotency: same UUID/file bytes ×3 triggers exactly 1 mocked paid call; UUID/new file returns conflict; retry requires different UUID.
3. Crash recovery: persisted job after restart; ambiguous provider state remains reconciliation required, no silent resubmit.
4. Public bot regression suite (prior existing tests): user credits, FSM, payments, validation behavior untouched.
5. Expense journal tracks failed, completed, retry attempts; `unknown` value is not converted into 0 cost.
6. Factory photo pairs: import 50 sample metadata pairs, prevent pair IDs with missing assets or unknown rights from automatically publishing.
7. Mode A: 10 initial slots; approve #1 triggers screencast/video while #2–#10 pending; retry #2 new idempotency id; reject #3 final; final count accurately reports PARTIAL.
8. Mode B: unique exact combinations even with concurrent selector calls; priority previously unused avatar/screencast pair; 0 AI mock invocations.
9. Remotion v9: two distinct triples both seen at original/ref/result placements; valid 1080x1920 30fps; no third-party node_modules copied to Git.
10. FFmpeg: valid H264 MP4 final, titled hooks/captions/CTA at expected event timing; output files nonempty, ffprobe.
11. Telegram: unauthorized user blocked, double callback idempotent, missing file properly handled, owner gets MP4.
12. Performance on HP: test 10 renders serial, peak RAM and elapsed time; no unsupported assertion of speed.

## External prerequisites for production E2E
Valid factory admin Telegram token + admin ID, Polza credentials on VPS, Kling configured (if used), private VPN/Tailscale network, Worker bearer token set separately. **No real paid tests/deploys without explicit owner authorization.** Once provided, test one image batch/one Kling avatar and one complete video, then a batch of 10 with spend cap.

## Evidence
Each executed test command + result into TASKS.md. If inability to run Node/FFmpeg/pytest, report as unverified rather than passing. Never assume previous video user rendered equals current integrated E2E test.
