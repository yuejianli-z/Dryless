# Dryless — shared Windows / macOS delivery

Read docs/START_HERE.md and docs/FEATURE_PARITY.md before changes.
User goal: one GitHub release/version, equal functionality on Windows and Mac;
same information architecture, system-appropriate native details.

- Preserve the approved logo, typography direction, sage-green palette, and three-page layout.
- No logo redesign, unrelated feature additions, removed features, or fourth alert stage.
- docs/FEATURE_PARITY.md F2 is the product contract; docs/MAC_REVIEW.md tracks implementation gaps.
- Windows owns shared behavior definitions, acceptance cases and audio assets. Native platform code may differ;
  same business-event inputs must satisfy the same contract. Keep timing/aggregation out of views.
- Mac SwiftUI/Vision is allowed; preserve its native design. Model accuracy requires separate real-device evidence.
- Never commit real user history, camera captures, tokens, absolute personal paths or virtual environments.
- Tests use a temporary DRYLESS_DATA_DIR before importing application modules.
- Mac owner: preserve existing codex/macos-native; fetch/read the Windows contract and PR to codex/dryless-design-v2.
- The 2026-09-13 F2 documentation records target behavior, not completed implementation; check the gap report before claiming parity.
- Windows owner maintains the base branch. No force pushes. Fetch before editing shared code.
- Update docs/release/windows.md or macos.md with commands, commit, hardware and actual results.
- Do not mark pending/manual checks passed using mocks, screenshots alone, or build success.
- Final stable tag/release requires both platforms to pass docs/RELEASE_CHECKLIST.md.
- Never delete old builds to produce a new one. python build.py writes a versioned directory.
