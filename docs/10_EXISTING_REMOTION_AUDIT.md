# Existing Remotion v9: approved internal module

**Authoritative location:** `C:/Проекты/VibeCopyContentFactory/Remotion` (actual folder name **Remotion**, capital R). This is not a third project. The owner already moved and renamed the completed v9 directory. **Do not copy an old ZIP over it, rename it, or rewrite Telegram UI styling.**

Known validated by owner: 1080×1920, 30 fps, two different cases with original/reference/result correctly substituted, faithful Telegram gallery/chat/photo viewer, result zoom and profile. Existing CLI scripts were found in previous archive; **reinspect actual on-disk files** before coding because user may have updated them.

## Minimal integration adapter
- Use paths relative to the factory root: `./Remotion`, not the obsolete Downloads folder or `.code-workspace`.
- `src/Root.tsx`, `src/VibeCopy.tsx`, `src/scene.mjs`, `src/timeline.mjs`, `tools/prepare-case.mjs`, `tools/render-case.mjs`, `cases/`, `package.json` are probable actual files from previous source inspection; verify first.
- Multiple independent cases require **immutable per-case photo paths**; old JSON examples referenced common `assets/original.jpg`, `assets/reference.jpg`, `assets/result.png` that can be accidentally overwritten. Support independent paths and output destinations.
- Prior `tools/prepare-case.mjs` writes a shared `src/case.generated.mjs`. First MVP uses strict serialization + single render lock; avoid parallel remotion renders until truly isolated.
- Python invokes a Node CLI (not the Studio UI). Render to unique MP4 file; save ffprobe width/height/FPS/duration, check exit codes and image checksums.
- Test two independent cases twice, proving old sources are unchanged and images don't cross-contaminate.
- Avoid second complete visual rebuild. Maintain existing checked UI, including the rounded top Vibe Copy bar, gallery geometry and full-screen result.
- Don't require Blender, Premiere, Cloudflare browser, etc. Keep lightweight on HP 8GB RAM.
