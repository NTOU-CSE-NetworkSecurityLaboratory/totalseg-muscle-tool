# WebView UI Status (2026-03-05)

## Summary

The `pywebview_tailwind_shell` UI is functionally usable for internal workflows and pre-release UAT.

## Current Readiness

- Batch segmentation: ready
- Compare workflow: ready
- License recovery flow: ready
- Session logging: ready
- Window lifecycle cleanup: ready

## Risk Position

- This UI is not yet marked as final clinician-facing product UI.
- For direct doctor-facing deployment, PySide remains the safer default until final UAT sign-off.

## Why This Matters

- Clinical users need extremely stable, predictable UX.
- Current WebView build is close, but visual and interaction details are still being tuned.

## Recommendation

- Keep PySide as production default.
- Continue WebView pilot with internal/partner users.
- Promote WebView only after checklist-based UAT is fully green.
