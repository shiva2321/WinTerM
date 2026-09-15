# WinTerM Documentation Hub

Welcome to the official technical documentation for **WinTerM** — the operating system substrate and cognitive toolkit that equips AI agents with eyes, hands, and terminal mastery on Windows and Linux/WSL2.

---

## Documentation Navigation

```
docs/
├── README.md                      # This documentation hub index
├── ARCHITECTURE.md                # 10-layer subsystem architecture & 5W cognitive pipeline
├── MCP_TOOLS.md                   # Complete reference for all 54 Model Context Protocol tools
├── CLI_REFERENCE.md               # Full command-line reference for the `winterm` CLI
├── UI_PERCEPTION_AND_ACTIONS.md   # Zero-dependency WinRT OCR, Set-of-Mark badges, Screen Mental Map, and UI automation
├── PROOFS_AND_BENCHMARKS.md       # Real-world proofs, telemetry, and test suite metrics
└── assets/                        # Visual proof screenshots and diagrams
```

---

## Guides by Topic

### 1. [Architecture & Cognitive Engine](ARCHITECTURE.md)
Understand how WinTerM decomposes goals and executes commands safely:
- **The 5W Cognitive Model**: What, How, When, Why, and What Happens After.
- **The 10-Layer Subsystem**: Kernel/Boot, Storage, Processes, Services, Registry, Security, Network, Diagnostics, Desktop GUI, and Linux/WSL.
- **Multi-Agent Coexistence**: Resource locking, session coordination, and fluke-contained swarms.

### 2. [54 MCP Tools Reference](MCP_TOOLS.md)
Comprehensive reference for all 54 Model Context Protocol (MCP) tools:
- **Core 5W Pipeline** (6 tools)
- **Linux & WSL2** (5 tools)
- **Knowledge Graph** (6 tools)
- **Application Lifecycle** (4 tools)
- **Window Management** (4 tools)
- **UI Automation & Inputs** (9 tools)
- **Advanced Perception & Grounding** (8 tools)
- **Playbooks & Reusable Tasks** (4 tools)
- **Multi-Agent Swarm** (5 tools)
- Full parameter signatures, descriptions, and JSON-RPC call examples.

### 3. [CLI Reference](CLI_REFERENCE.md)
How to use the `winterm` command-line utility from PowerShell, CMD, or bash:
- System diagnostics (`winterm info`, `winterm subsystems`)
- Autonomous execution (`winterm plan`, `winterm run`, `winterm diagnose`)
- Desktop automation (`winterm app`, `winterm window`, `winterm input`, `winterm ui`, `winterm screen`)
- Knowledge graph queries (`winterm graph`)
- Swarm coordination (`winterm swarm`)
- Universal tool runner (`winterm tool <tool_name> [args]`)

### 4. [UI Perception & Physical Actions Guide](UI_PERCEPTION_AND_ACTIONS.md)
How WinTerM perceives and interacts with Windows GUI applications:
- **The 3 App Classes**: Win32/WPF (Class A), Chromium/Electron (Class B), DirectX/Canvas (Class C).
- **Hardware-Accelerated WinRT OCR**: Zero-dependency screen-to-text extraction.
- **Set-of-Mark (SoM) Grounding**: Numbered badge overlays for multimodal vision agents.
- **Physical Input Safety**: STA thread isolation, `OpenInputDesktop`, `ForceForegroundVerified`, and window-contained clicks.

### 5. [Proofs, Telemetry & Benchmarks](PROOFS_AND_BENCHMARKS.md)
Empirical evidence of WinTerM's capabilities:
- **Google Chrome Autonomous Search**: Complete keyboard/mouse navigation, search execution, and 65-line OCR extraction.
- **Windows 11 Notepad Text Injection**: Non-invasive UIAutomation ValuePattern and hardware SendInput.
- **Test Suite Metrics**: 182 passing automated unit, integration, and CLI tests (100% pass rate).
- **Knowledge Graph Density**: 10,374 nodes, 5,675 edges across 3 Microsoft & Hugging Face datasets.

---

## Agent Integration Guides
For agent-specific setup manuals and instructions:
- [Claude Code Integration](../CLAUDE.md)
- [Google Gemini / Antigravity Integration](../GEMINI.md)
- [DeepSeek (V3 & R1) Integration](../DEEPSEEK.md)
- [OpenCode Integration](../OPENCODE.md)
- [Universal Agent Directives](../AGENTS.md)
