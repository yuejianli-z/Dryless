# Dryless — shared Windows / macOS delivery

Read docs/START_HERE.md and docs/FEATURE_PARITY.md before changes.
User goal: one GitHub release/version, equal functionality on Windows and Mac;
same information architecture, system-appropriate native details.

- Preserve the approved logo, typography direction, sage-green palette, and three-page layout.
- No logo redesign, unrelated feature additions, removed features, or fourth alert stage.
- Shared detector/reminder/data code is the source of truth; isolate platform APIs.
- Never commit real user history, camera captures, tokens, absolute personal paths or virtual environments.
- Tests use a temporary DRYLESS_DATA_DIR before importing application modules.
- Mac owner: branch codex/macos-v0.2.0 from codex/dryless-design-v2, PR back to it.
- Windows owner maintains the base branch. No force pushes. Fetch before editing shared code.
- Update docs/release/windows.md or macos.md with commands, commit, hardware and actual results.
- Do not mark pending/manual checks passed using mocks, screenshots alone, or build success.
- Final stable tag/release requires both platforms to pass docs/RELEASE_CHECKLIST.md.
- Never delete old builds to produce a new one. python build.py writes a versioned directory.
