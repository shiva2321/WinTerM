# WinTerM Project Roadmap 🗺️

**WinTerM** is building the foundational cognitive and execution layer for autonomous AI agents on Windows. This roadmap communicates our strategic milestones, active community bounties, and long-term vision.

---

## 🧭 High-Level Vision
Enable any LLM agent—whether running in Claude Code, Google Antigravity, Cursor, OpenAI Swarm, AutoGen, or LangChain—to operate Windows as safely, predictably, and powerfully as an expert Windows systems engineer.

---

## 📍 Release Milestones

### Phase 1: Core Shell Reliability & 5W Cognitive Model (v0.1.0) — ✅ COMPLETED
- [x] **5W Epistemological Pipeline**: Implemented What, How, When, Why, and What Happens After.
- [x] **Strict Windows Shell Reliability**: Automated space quoting, call operator `&`, UTF-8 byte stream preservation, and non-interactive switches (`-Force`, `/Y`).
- [x] **10-Layer Subsystem Architecture**: Coverage from Layer 0 (Kernel & Boot) through Layer 8 (Virtualization & Packages).
- [x] **Ontological Knowledge Graph**: NetworkX graph engine with 10,374 nodes, 5,675 edges, and 3 Hugging Face datasets.
- [x] **Autonomous Error Self-Healing**: Diagnostic catalog translating HRESULTs, NTSTATUS codes, and Win32 errors into instant remediation.

### Phase 2: Desktop GUI, UI Automation & Safety (v0.2.0) — ✅ COMPLETED
- [x] **Layer 9: Desktop GUI Subsystem**: Universal application discovery (`shell:AppsFolder`, Start Menu, Registry) and process lifecycle.
- [x] **UI Automation (UIA) Engine**: Native element inspection, `InvokePattern` click, and `ValuePattern` text input.
- [x] **Guaranteed Input Safety**: Wrapped pointer drags and keystrokes in `try ... finally` release blocks to prevent OS input queue freezes.
- [x] **Top-Level Window Management**: Window listing, UIPI focus-locking bypass, resizing, and clean `WM_CLOSE` messaging.
- [x] **Screen Perception**: Real-time display resolution, cursor metrics, and full-resolution PNG screenshot capture.

### Phase 3: MCP Protocol & Closed-Loop Protocol (v0.3.0) — ✅ COMPLETED
- [x] **Model Context Protocol (MCP) Server**: 32 production tools exposed via JSON-RPC.
- [x] **Closed-Loop Sense-Decide-Act-Verify**: System prompt (`windows_agent_instructions`) grounding agents in safe desktop automation.
- [x] **Anti-Pattern Guardrails**: Eliminated blind coordinate scripts in favor of dynamic element querying.
- [x] **Interactive CLI**: Rich Typer CLI with `plan`, `explain`, `run`, `diagnose`, `graph`, `app`, `window`, `input`, and `screen`.
- [x] **100% Automated Test Suite**: 87 passing unit tests across all layers.

---

### Phase 4: Multi-Modal Vision & OCR Grounding (v0.4.0) — 🚀 IN PROGRESS
- [ ] **Windows Native OCR**: Integrate Windows.Media.Ocr WinRT API for zero-dependency local text extraction from Class C canvas apps.
- [ ] **Visual Bounding-Box Grounding**: Automatic translation from visual bounding boxes to window-relative click offsets.
- [ ] **Multi-Monitor Display Awareness**: Virtual desktop workspace mapping, per-monitor DPI scaling, and multi-display cursor routing.
- [ ] **Live UI Event Streaming**: Listen to `UIA_AutomationPropertyChangedEventId` to react immediately to modal popups, UAC prompts, and toast notifications.

---

### Phase 5: Ecosystem Integrations & Sandbox Orchestration (v0.5.0) — 🔮 PLANNED
- [ ] **1-Click Agent Launchers**: Native plugins for Claude Desktop, Claude Code, Cursor IDE, and VS Code extensions.
- [ ] **Windows Sandbox & Hyper-V Disposable Runners**: Allow agents to spin up disposable Windows Sandbox environments (`WindowsSandbox.exe`) for high-risk executions.
- [ ] **Audio Endpoint & Media Subsystem**: Enumerate audio output devices, switch default playback endpoints, and monitor system audio streams.
- [ ] **Deep WSL2 Interop**: Bidirectional path resolution (`\\wsl$\...` <-> `/mnt/c/...`) and seamless cross-kernel execution pipelines.

---

### Phase 6: Autonomous Multi-Agent Swarm (v1.0.0) — 🌟 THE DESTINATION
- [ ] **Decentralized Multi-Agent Swarm**: Multiple specialized Windows agents (e.g. SysAdmin Agent, UI Navigator Agent, Network Auditor Agent) collaborating over shared memory.
- [ ] **Continuous Learning Ledger**: Agents autonomously log execution successes, edge-case quirks, and newly installed application schemas to a local persistent SQLite knowledge base.
- [ ] **Enterprise Security & Audit Compliance**: Real-time RBAC policy enforcement, cryptographically signed audit logs, and tamper-proof command telemetry.

---

## 🤝 Community Bounties & How to Influence the Roadmap
Have a killer feature in mind? Want to contribute to an active milestone?
1. Open a discussion on [GitHub Discussions](https://github.com/shiva2321/WinTerM/discussions).
2. Check issues labeled `roadmap` or `community bounty`.
3. Read [CONTRIBUTING.md](CONTRIBUTING.md) to get started!
