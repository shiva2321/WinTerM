# Contributing to WinTerM

Welcome! First of all, thank you for considering contributing to **WinTerM**. 🎉

AI agents are changing how humans compute, but Windows has historically been hostile to autonomous execution: unpredictable UTF-8 codepages, hanging interactive stdin prompts, focus stealing, and blind pixel coordinate guesses that break across display scales. 

**WinTerM changes this.** We are building the world's most reliable, deterministic, and safe cognitive execution layer for Windows Terminal and Desktop. Whether you're fixing a typo, adding support for a new Windows API, or contributing dataset models, your contributions are celebrated!

---

## Table of Contents
- [Quickstart for Developers (5 Minutes)](#quickstart-for-developers-5-minutes)
- [The 5 Golden Rules of WinTerM](#the-5-golden-rules-of-winterm)
- [Codebase Architecture Primer](#codebase-architecture-primer)
- [How to Contribute](#how-to-contribute)
  - [1. Adding or Enhancing an MCP Tool](#1-adding-or-enhancing-an-mcp-tool)
  - [2. Adding a New Subsystem Primitive](#2-adding-a-new-subsystem-primitive)
  - [3. Adding an Error Signature & Self-Healing Rule](#3-adding-an-error-signature--self-healing-rule)
  - [4. Expanding the Knowledge Graph](#4-expanding-the-knowledge-graph)
- [Community Wishlist & "Good First Issues"](#community-wishlist--good-first-issues)
- [Pull Request & Review Process](#pull-request--review-process)
- [Community & Getting Help](#community--getting-help)

---

## Quickstart for Developers (5 Minutes)

### Prerequisites
- **OS**: Windows 10, Windows 11, or Windows Server 2022+
- **Python**: Python 3.10, 3.11, or 3.12+
- **PowerShell**: Windows PowerShell 5.1 and/or PowerShell 7+ (`pwsh`)

### 1. Clone & Set Up Virtual Environment
```powershell
# Clone the repository
git clone https://github.com/shiva2321/WinTerM.git
cd WinTerM

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install in editable mode with development dependencies
python -m pip install -e ".[dev,mcp]"
```

### 2. Run the Test Suite
WinTermAgent maintains a **100% passing test suite**:
```powershell
python -m pytest tests/ -v
```
All tests should pass before you write any code.

---

## The 5 Golden Rules of WinTerM

Every pull request must adhere to these five architectural invariants:

1. **Never Guess Blind Coordinates (UI Tree First)**:
   - Always inspect UI Automation trees (`winterm_ui_inspect`) to discover true bounding boxes and automation IDs before clicking or typing.
2. **Guaranteed Cleanup Blocks (`try ... finally`)**:
   - Every simulated mouse drag, pen stroke, or key down MUST be wrapped in a `try ... finally` block that guarantees release (`MOUSEEVENTF_LEFTUP` / `KEYEVENTF_KEYUP`). An agent must never lock the host OS input queue.
3. **Strict Shell Quoting & Call Operator (`&`)**:
   - Any synthesized PowerShell command that contains paths with whitespace must be quoted and prefixed with the call operator: `& "C:\Path With Spaces\app.exe"`.
4. **Interactive Prompt Elimination**:
   - Commands must explicitly prevent hanging on interactive prompts. Inject `-Force`, `-Confirm:$false`, `/Y`, or `--yes` into all synthesized actions.
5. **100% Test Coverage for New Features**:
   - Any new tool, subsystem primitive, or graph query must come with automated pytest unit tests in the `tests/` directory.

---

## Codebase Architecture Primer

The repository is modularly organized into clean cognitive layers:

```
winterm/
├── agent/            # High-level orchestrator & session ledger (WinTermAgent)
├── cognition/        # 5W pipeline: Planner, Synthesizer, Scheduler, Reasoner, Predictor
├── subsystems/       # 10-layer Windows subsystem execution engines (Layer 0 to Layer 9)
├── interaction/      # Desktop GUI, UIA, window manager, mouse, keyboard, pen/touch, screen
├── graph/            # 10,374-node NetworkX ontological knowledge graph & datasets
├── knowledge/        # Shell matrices, error catalogs, encoding experts, elevation rules
├── tools/            # FastMCP server (32 tools), JSON schemas, and agent system prompts
└── cli/              # Rich interactive Typer CLI (`winterm`)
```

---

## How to Contribute

### 1. Adding or Enhancing an MCP Tool
All MCP tools are exposed to AI agents (Claude Code, Google Antigravity, Cursor, OpenAI) via Model Context Protocol.
1. Implement the tool logic in [`winterm/tools/tool_definitions.py`](file:///d:/Agent_toolkit/winterm/tools/tool_definitions.py).
   - Ensure you unpack `exec_res, _, _ = _agent_instance...` when calling `WinTermAgent` methods.
   - Include a comprehensive docstring with `CRITICAL AGENT INSTRUCTION` explaining how and when the LLM should invoke it.
2. Add the tool JSON Schema to `EXPORTED_TOOLS_SCHEMA` in [`winterm/tools/tool_definitions.py`](file:///d:/Agent_toolkit/winterm/tools/tool_definitions.py).
3. Register the tool decorator in [`winterm/tools/mcp_server.py`](file:///d:/Agent_toolkit/winterm/tools/mcp_server.py).
4. Add a unit test in [`tests/test_interaction_engine.py`](file:///d:/Agent_toolkit/tests/test_interaction_engine.py) verifying schema integrity.

### 2. Adding a New Subsystem Primitive
WinTerM classifies Windows management into 10 hierarchical subsystems (Layers 0–9).
1. Identify the appropriate subsystem in [`winterm/subsystems/`](file:///d:/Agent_toolkit/winterm/subsystems/).
2. Add a `plan_*` method that returns a validated `PlanStep` with:
   - `command`: Robust, quoted PowerShell/Win32 command.
   - `target_shell`: `ShellType.POWERSHELL_51`, `ShellType.PWSH`, or `ShellType.CMD`.
   - `preconditions`: Required state checks (e.g. `PreconditionType.PATH_EXISTS`).
3. Add corresponding convenience methods on `WinTermAgent` in [`winterm/agent/winterm_agent.py`](file:///d:/Agent_toolkit/winterm/agent/winterm_agent.py).
4. Add unit tests in `tests/test_subsystems_*.py`.

### 3. Adding an Error Signature & Self-Healing Rule
When Windows commands fail, WinTerM automatically identifies the root cause and provides a remediation command.
1. Open [`winterm/knowledge/error_catalog.py`](file:///d:/Agent_toolkit/winterm/knowledge/error_catalog.py).
2. Add a new `KnownErrorSignature` with:
   - `error_id`: Unique identifier (e.g. `ERR_SHARING_VIOLATION`).
   - `regex_pattern`: Matches the Windows HRESULT, NTSTATUS, or stderr snippet.
   - `friendly_explanation`: Clear explanation of why Windows rejected the command.
   - `remediation_proposal`: Concrete PowerShell command to fix the issue.
3. Test the diagnosis in `tests/test_knowledge.py`.

### 4. Expanding the Knowledge Graph
Our Knowledge Graph (`networkx.MultiDiGraph`) contains 10,374 nodes and 5,675 directed semantic edges.
1. Look at [`winterm/graph/compiler.py`](file:///d:/Agent_toolkit/winterm/graph/compiler.py).
2. Add factual Windows commands, parameter flags, safety tiers (`safe`, `destructive`, `privileged`), or service dependencies.
3. Ensure all bidirectional relationships (`DEPENDS_ON` / `DEPENDENCY_OF`, `ALTERNATIVE_TO`) maintain symmetry.

---

## Community Wishlist & "Good First Issues"

Looking for a great project to tackle? Here are high-impact areas where the community needs your help:

- [ ] **Windows OCR Perception Layer**: Add a lightweight OCR engine (via Windows.Media.Ocr WinRT API or Tesseract) to read text inside Class C canvas apps (Paint, game windows, CAD tools).
- [ ] **Multi-Monitor Display Geometry**: Extend `winterm_screen_state` to support virtual desktop spaces, multi-monitor bounding boxes, and per-monitor DPI scaling factors.
- [ ] **Audio Endpoint Switcher Subsystem**: Add audio playback and recording device enumeration and switching via CoreAudio APIs.
- [ ] **WSL2 Deep Bridging**: Enhance `VirtualizationPackagesSubsystem` with zero-copy translation of Linux paths (`/mnt/c/...`) and native Linux CLI execution from PowerShell.
- [ ] **Accessibility Notification Listeners**: Add real-time UI Automation event listening (`UIA_AutomationPropertyChangedEventId`) to notify agents immediately when dialogs open.

Check out our [GitHub Issues](https://github.com/shiva2321/WinTerM/issues) tagged `good first issue` and `help wanted`!

---

## Pull Request & Review Process

1. **Fork the repo** and create a feature branch:
   ```powershell
   git checkout -b feature/my-cool-subsystem
   ```
2. **Follow Conventional Commits**:
   - `feat: add Windows OCR perception tool`
   - `fix: correct regex for protocol URI launch`
   - `docs: improve 5W decision trace explanation`
   - `test: add unit tests for display geometry`
3. **Format & Test**:
   - Run `python -m pytest tests/ -v` and make sure 100% of tests pass.
4. **Submit your PR**:
   - Fill out our PR template describing the change, why it matters, and how you tested it.
   - Maintainers will review and merge quickly!

---

## Community & Getting Help

- 💡 **GitHub Discussions**: Share ideas, request features, and showcase what you've built on [GitHub Discussions](https://github.com/shiva2321/WinTerM/discussions).
- 🐛 **Issue Tracker**: Report bugs or agent failure incidents via [GitHub Issues](https://github.com/shiva2321/WinTerM/issues).

Thank you for helping make Windows the greatest operating system for autonomous AI agents! 🚀
