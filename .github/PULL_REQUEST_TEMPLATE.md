## Description
<!-- Provide a brief description of the changes introduced in this PR -->

## Related Issue(s)
<!-- Fixes #(issue) or Relates to #(issue) -->

## Type of Change
- [ ] 🐛 Bug fix (non-breaking change fixing an issue)
- [ ] ✨ New feature (non-breaking change adding functionality)
- [ ] 🛡️ Security / Reliability enhancement (hardening against Windows edge cases)
- [ ] ⚡ Performance optimization
- [ ] 📝 Documentation update
- [ ] 🧪 Test suite additions

## Quality & Safety Checklist
- [ ] **100% Passing Tests**: I have run `python -m pytest tests/ -v` and all tests pass cleanly.
- [ ] **No Blind Pixel Coordinates**: I did not add hardcoded pixel coordinate hacks; interactions use dynamic UI Automation trees, screen metrics, or relative bounding box calculations.
- [ ] **Guaranteed Release Blocks**: Any simulated mouse or keyboard gestures are wrapped in `try ... finally` release blocks to guarantee no OS input queue freezes.
- [ ] **Quoting & Call Operator**: Any synthesized PowerShell paths with whitespace are properly quoted and prefixed with `&`.
- [ ] **Non-Interactive Switches**: Commands include `-Force`, `-Confirm:$false`, `/Y`, or `--yes` to prevent headless hangs.
- [ ] **Documentation Updated**: If new tools or commands were added, I updated `README.md` and/or tool docstrings.
