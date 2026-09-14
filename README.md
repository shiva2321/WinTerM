# WinTerM: The AI Agent Toolkit for Windows Terminal & Desktop

[![GitHub Repo](https://img.shields.io/badge/GitHub-shiva2321%2FWinTerM-181717?logo=github)](https://github.com/shiva2321/WinTerM)
[![Windows](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011%20%7C%20Server-0078D6?logo=windows)](https://microsoft.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-104%2F104%20Passing-brightgreen?logo=pytest)](https://github.com/shiva2321/WinTerM/actions)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Model Context Protocol](https://img.shields.io/badge/MCP-37%20Tools%20%2B%20Prompts-FF6B6B)](https://modelcontextprotocol.io)
[![Gemini Ready](https://img.shields.io/badge/Gemini-Native%20Support-8E75B2?logo=google)](GEMINI.md)
[![DeepSeek Ready](https://img.shields.io/badge/DeepSeek-R1%20CoT%20Aligned-007AFF?logo=deepseek)](DEEPSEEK.md)
[![Linux & WSL2](https://img.shields.io/badge/Linux%20%26%20WSL2-Deterministic%20Safety-FCC624?logo=linux&logoColor=black)](winterm/subsystems/linux_subsystem.py)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Roadmap](https://img.shields.io/badge/Roadmap-Public-blueviolet)](ROADMAP.md)

**WinTerM** is the foundational AI Agent Toolkit purpose-built for the Windows operating system and Linux/WSL2 environments. It equips autonomous agents with deep terminal mastery, reliable execution mechanics, interactive desktop GUI automation, multi-agent concurrency coordination, and an epistemological **5W Cognitive Model**:
- **WHAT to do**: Natural language intent decomposition into staged Directed Acyclic Graph (DAG) plans.
- **HOW to do**: Production-grade Windows Shell reliability (PowerShell 5.1/7+, CMD, Win32) and Linux/WSL2 Bash execution, quoting, escaping, call operator `&`, UTF-8 byte preservation, elevation handling, and non-interactive guards.
- **WHEN to do**: System state guards, precondition verification, dependency topological sorting, and idempotency checks (skipping already-satisfied states).
- **WHY to do**: Transparent semantic rationale explaining command selection, switch choices, Windows quirk mitigations, and why alternatives were rejected.
- **WHAT WILL HAPPEN AFTER (and How & Why)**: Pre-execution predictive state diff simulation (files, registry, services, processes, ports), safety risk tiering, automated rollback synthesis, post-condition verification, and autonomous error self-healing.

---

## Why WinTerM? (The Paradigm Shift)

Most AI agents running on Windows fail because they rely on fragile shell wrappers or blind pixel-based GUI automation tools. WinTerM fundamentally solves this:

| Capability | Raw PowerShell / CMD | PyAutoGUI / pywin32 | Generic Bash Wrappers | **WinTerM** |
|:---|:---:|:---:|:---:|:---:|
| **5W Cognitive Pipeline** (What, How, When, Why, After) | ❌ None | ❌ None | ❌ None | ✅ **Built-in Epistemological Model** |
| **Windows Shell Reliability** (Quoting, `&`, UTF-8, non-interactive) | ❌ Frequent crashes & hangs | ❌ N/A | ❌ Broken path & syntax | ✅ **Strict Automated Synthesis** |
| **Linux & WSL2 Subsystem** | ❌ None | ❌ None | ⚠️ Fragile & unconstrained | ✅ **Deterministic Safety & Self-Healing** |
| **Interactive Desktop GUI Control** | ❌ Terminal only | ⚠️ Blind pixel coordinate guesses | ❌ Headless only | ✅ **Native UI Automation Trees + Bounds** |
| **Input Queue Safety** | ❌ None | ⚠️ Freezes cursor/queue on crash | ❌ None | ✅ **Guaranteed `try...finally` Release** |
| **Autonomous Error Self-Healing** | ❌ Manual debugging required | ❌ None | ❌ None | ✅ **100+ HRESULT, Win32 & POSIX Catalog** |
| **Knowledge Graph & Hallucination Defense** | ❌ Frequent flag hallucinations | ❌ None | ❌ None | ✅ **10,374-Node Graph with 3 Datasets** |
| **Multi-Agent Coexistence Coordinator** | ❌ Session stomping & collisions | ❌ None | ❌ None | ✅ **Resource Locks & Shared Ledgers** |
| **Model Context Protocol (MCP)** | ❌ None | ❌ None | ❌ None | ✅ **37 Production Tools + System Prompts** |

---

## Universal Agent Ecosystem Compatibility

WinTerM connects out of the box with any AI agent framework:
- 🤖 **Claude Code**: 1-command setup via `claude mcp add winterm python -m winterm.tools.mcp_server` (native [`CLAUDE.md`](CLAUDE.md) and custom skills in [`.claude/skills/winterm/`](.claude/skills/winterm/)).
- 🧩 **OpenCode**: Native [`opencode.json`](opencode.json) and [`OPENCODE.md`](OPENCODE.md) integration for local open-source agent execution.
- ⚡ **Google Gemini & Antigravity**: Native [`GEMINI.md`](GEMINI.md) operating manual with multimodal visual perception grounding (`winterm_screen_capture`).
- 🧠 **DeepSeek (V3 & R1)**: Native [`DEEPSEEK.md`](DEEPSEEK.md) integration aligning R1 `<think>` reasoning tokens with the 5W cognitive pipeline.
- 💻 **Cursor & Windsurf**: Terminal command synthesis and safe background desktop execution.
- 🌐 **LangChain, CrewAI & AutoGen**: Python SDK tool wrappers for multi-agent swarms.
- 🤝 **Simultaneous Multi-Agent Coexistence**: Cooperative resource locking and shared session coordination via `AgentSessionCoordinator`.


---

## The 5W Cognitive Model Architecture

```
                    ┌────────────────────────────┐
                    │     User Natural Goal      │
                    └─────────────┬──────────────┘
                                  │
      ┌───────────────────────────┴───────────────────────────┐
      │               THE 5W COGNITIVE PIPELINE               │
      ├───────────────────────────────────────────────────────┤
      │ 1. WHAT TO DO       TerminalPlanner                   │
      │    Decomposes goal into atomic PlanSteps (DAG)        │
      │                                                       │
      │ 2. HOW TO DO        CommandSynthesizer                │
      │    Enforces quoting, call op &, UTF-8, non-interact   │
      │                                                       │
      │ 3. WHEN TO DO       PreconditionScheduler             │
      │    Evaluates state guards & checks idempotency        │
      │                                                       │
      │ 4. WHY TO DO        SemanticReasoner                  │
      │    Transparent rationale & alternatives rejected      │
      │                                                       │
      │ 5. AFTER & BEYOND   ImpactPredictor & StateVerifier   │
      │    State diff simulation, risk score, undo & heal     │
      └───────────────────────────┬───────────────────────────┘
                                  │
                    ┌─────────────┴──────────────┐
                    │    WindowsShellExecutor    │
                    │ PowerShell 5.1 / 7+ / CMD  │
                    └────────────────────────────┘
```

---

## The 10-Layer Subsystem Architecture

WinTerM covers the complete hierarchy of Windows Terminal operations and desktop interaction:

| Layer | Subsystem Class | Description & Primitives |
|:---|:---|:---|
| **Layer 0: Kernel & Boot** | `KernelBootSubsystem` | BCD store (`bcdedit`), ACPI power schemes (`powercfg`), device drivers (`pnputil`), hardware TPM chip (`Get-Tpm`), UEFI/BIOS firmware boot mode. |
| **Layer 1: Storage & NTFS** | `StorageNTFSSubsystem` | Physical disks (`Get-Disk`), partitions, volumes (`Get-Volume`), BitLocker encryption, VSS shadow copies (`vssadmin`), junctions, symlinks, and ACL permissions (`icacls`, `Get-Acl`, `takeown`). |
| **Layer 2: Process & Memory** | `ProcessMemorySubsystem` | Process lifecycle, priority classes (`PriorityClass`), CPU affinity bitmasks (`ProcessorAffinity`), loaded DLL modules (`$proc.Modules`), threads, and memory working set trimming. |
| **Layer 3: Services & Tasks** | `ServicesTasksSubsystem` | Windows SCM (`Get-Service`), auto-restart failure recovery (`sc.exe failure`), startup types, Task Scheduler (`schtasks /create`, `Get-ScheduledTask`), background jobs. |
| **Layer 4: Registry & Policies** | `RegistryPolicySubsystem` | All registry hives (`HKLM`, `HKCU`, `HKCR`, `HKU`), typed values (`DWord`, `QWord`, `String`), and Group Policy synchronization (`gpupdate /force`, `gpresult /r`). |
| **Layer 5: Security & Crypto** | `SecurityCryptoSubsystem` | User token privileges (`whoami /priv`), local accounts (`Get-LocalUser`), Windows Certificate Store (`Cert:\LocalMachine\My`), Windows Defender protection & exclusions, Credential Manager (`cmdkey`). |
| **Layer 6: Network & Firewall** | `NetworkFirewallSubsystem` | Network adapters (`Get-NetAdapter`), IPv4 routing table (`Get-NetRoute`), Windows Defender Firewall rules (`New-NetFirewallRule`), DNS cache flushing, WinHTTP system proxy (`netsh winhttp`). |
| **Layer 7: Diagnostics & Health** | `DiagnosticsHealthSubsystem` | Windows Event Log (`Get-WinEvent`), real-time performance counters (`Get-Counter`), System File Checker (`sfc /scannow`), and DISM servicing (`dism /CheckHealth`). |
| **Layer 8: Virtualization & Packages** | `VirtualizationPackagesSubsystem` | WSL distributions lifecycle (`wsl.exe -l -v`), Hyper-V virtual machines (`Get-VM`), Windows Optional Features, and package managers (`winget`, `choco`, `scoop`). |
| **Layer 9: Desktop GUI & Interaction** | `DesktopGuiSubsystem` | Universal application discovery (`shell:AppsFolder`, Start Menu, Registry), window management (`EnumDesktopWindows`, `ForceForeground`), UI Automation (`InvokePattern`, `ValuePattern`), and keyboard/mouse/pen input automation. |
| **Layer 10: Linux & WSL2** | `LinuxSubsystem` | Full Linux POSIX compatibility, systemctl daemon control, process/storage/network inspection, non-interactive package management (`apt`/`dnf`/`apk`/`pacman`), and bidirectional path translation (`wslpath`). |


---

## Windows Shell Reliability Standards

WinTerM inherently enforces the golden reliability rules of Windows terminal execution:
1. **Space Quoting & Call Operator (`&`)**:
   - In PowerShell, any path with whitespace is quoted: `& "C:\Program Files\App\bin.exe"`.
2. **Logical Operator Parentheses**:
   - Fixes the common PowerShell trap `if (Test-Path a -or Test-Path b)` -> automatically synthesized as `if ((Test-Path a) -or (Test-Path b))`.
3. **UTF-8 Byte Stream Integrity**:
   - Resolves older Windows PowerShell 5.1 redirection byte corruption with UTF-8 preambles and explicit output encoders.
4. **Interactive Hang Mitigation**:
   - Injects `-Confirm:$false`, `-Force`, `--accept-source-agreements`, `/Y`, and `--yes` to prevent headless agent sessions from hanging on stdin.
5. **ASCII Console Enforcement**:
   - Translates unicode emojis into ASCII tokens (`[OK]`, `[X]`, `[WARN]`) to prevent crash/corruption across legacy OEM code pages.
6. **Win32 Long Path Support**:
   - Supports extended length prefix `\\?\` for paths exceeding the 260-character MAX_PATH threshold.
7. **Autonomous Error Diagnosis & Self-Healing**:
   - Translates Windows HRESULTs and exit codes (`0x80070005 Access Denied`, `0x80070020 Sharing Violation`, `PSSecurityException ExecutionPolicy`, `10048 Port in use`) into actionable remediation commands.

---

## Installation & Setup

```powershell
# Clone or navigate to the repository
cd d:\Agent_toolkit

# Install in editable mode
python -m pip install -e .
```

---

## Command Line Interface (`winterm`)

WinTerM includes a rich interactive CLI:

### 1. Inspect System Environment & Shell Matrix
```powershell
winterm info
winterm subsystems
```
Displays OS version, PowerShell version, active console code page, LongPathsEnabled status, detected package managers, and the full 9-layer subsystem capabilities.

### 2. Plan a Task (The WHAT)
```powershell
winterm plan "Find what process is using port 8080 and stop it"
```

### 3. Deep 5W Breakdown (The WHY, HOW, WHEN, AFTER)
```powershell
winterm explain "Stop-Process -Id 1234 -Force"
```

### 4. Execute with Dry-Run or Full Auto-Healing
```powershell
# Dry-run simulation (predicts impact without modifying system state)
winterm run "Query top 5 memory processes" --dry-run

# Live execution with automated self-healing
winterm run "Query system hardware info"
```

#### Safety Gate (Protects Against Destructive Commands)
Every execution is protected by a deterministic **SafetyGate** (see `winterm/knowledge/safety_guard.py`). Commands classified as `HIGH_DESTRUCTIVE` — e.g. `Remove-Item` on protected system paths, `Stop-Computer`, `Format-Volume`, `diskpart`, registry deletion — are **refused by default**:

```powershell
# Refused (exit code -100) — no confirmation supplied
winterm run "Remove-Item -Recurse -Force C:\Windows\System32"
# [X] Failed with exit code -100
# [SAFETY GATE] Refused to execute: ...

# Explicitly allow high-risk commands (DANGEROUS — use with extreme care)
winterm run "Remove-Item -Recurse -Force C:\Windows\System32" --confirm-high-risk
```

Read-only queries (`Get-*`, `Select-*`, `Test-*`, `netstat`, `ipconfig`, ...) always pass through the gate normally.

### 5. Diagnose Windows Terminal Errors
```powershell
winterm diagnose "0x80070005: Access is denied."
```

### 6. Windows Terminal Knowledge Graph Reasoning
```powershell
# Graph topology and ontological entity breakdown (10,374 nodes, 5,675 edges)
winterm graph info

# Cascading blast radius analysis (direct + transitive dependent services)
winterm graph blast-radius RpcSs --depth 2

# Parameter hallucination validation (flags & typo suggestions)
winterm graph validate "Get-Process -Name svchost -Id 1234"
winterm graph validate "bcdedit.exe /enum /v"

# Natural language intent search across 25,000+ indexed mappings (sumit-s-nair/command-dataset)
winterm graph search-intent "find files modified today"

# Official Microsoft command syntax & parameter docs (IAmSomeone/Windows_command)
winterm graph docs arp
winterm graph docs robocopy

# SFT safety & credential sensitivity classification (mshojaei77/terminal-command-execution-sft)
winterm graph safety "Format-Volume -DriveLetter D"
winterm graph safety "Get-Process"

# Destructive commands are now deterministically flagged (SafetyGuard)
winterm graph safety "Remove-Item -Recurse -Force C:\Windows\System32"
# Safety Classification: DESTRUCTIVE / Dangerous / High Risk: True
winterm graph safety "Stop-Computer -Force"
# Safety Classification: DESTRUCTIVE / Dangerous / High Risk: True

# Multi-step error remediation paths
winterm graph remedy 0x80070005
winterm graph remedy 10048

# Cross-shell command alternatives (cmdlet <-> native Win32)
winterm graph alternatives Stop-Process
```

---

## Windows Terminal Knowledge Graph & Hugging Face Datasets

WinTerM incorporates an ontological, graph-theoretic knowledge engine (`networkx.MultiDiGraph`) with **10,374 nodes** and **5,675 directed semantic edges**, deeply integrating three high-quality terminal datasets:

1. **`mshojaei77/terminal-command-execution-sft`**:
   - Classifies commands into safety tiers (`safe`, `destructive`, `credential_sensitive`, `privileged`), operational skills, and actionable risk warnings.
2. **`IAmSomeone/Windows_command`**:
   - Official Microsoft syntax definitions, compatibility versions (`Windows Server 2022`, `Windows 11`), and full switch dictionaries for 144+ Windows binaries.
3. **`sumit-s-nair/command-dataset`**:
   - Natural language intent-to-command mappings spanning PowerShell and CMD, indexed into intent nodes with word-level relevance grounding.

### Ontological Entities (Nodes)
- `COMMAND` (199): Factual PowerShell cmdlets and Win32 binaries across all 9 architectural layers.
- `PARAMETER` (4,738): Real parameters, switches, and flags with descriptions.
- `INTENT` (5,000): Natural language goal queries mapped to concrete commands.
- `SAFETY_RULE` (355): Safety policies, privilege warnings, and credential risk rules.
- `SERVICE_RESOURCE` (30): Factual Windows SCM services with dependency trees.
- `STATE_ENTITY` (29): System state primitives (TCP ports, DACLs, registry keys, volumes).
- `ERROR_CODE` (10): Real HRESULTs (`0x80070005`, `0x80070422`, `0x800706BA`), Win32 codes (`5`, `10048`), and exceptions.
- `PRIVILEGE` (4): Security token requirements (`StandardUser`, `Administrator`, `SYSTEM`).
- `SUBSYSTEM` (9): The 9 architectural subsystem layers.

### Directional Relationships (Edges)
- `HAS_PARAMETER` (4,738), `MAPS_TO_COMMAND` (313), `PART_OF_SUBSYSTEM` (230), `REQUIRES_PRIVILEGE` (209), `DEPENDS_ON` (47), `DEPENDENCY_OF` (47), `MUTATES_STATE` (37), `ALTERNATIVE_TO` (22), `REMEDIATES_ERROR` (17), `HAS_SAFETY_RULE` (15).

---

## Python SDK Integration

```python
from winterm.agent.winterm_agent import WinTermAgent

agent = WinTermAgent()

# 1. Plan a multi-step goal
plan = agent.plan("Find process on port 3000 and terminate it")

# 2. Inspect the 5W Decision Trace for a step
trace = agent.explain(plan.steps[0])
print(trace.what)
print(trace.why.command_justification)
print(trace.after)

# 3. Knowledge Graph: Intent search, docs & safety
intents = agent.search_intent("find all text files")
docs = agent.get_command_docs("arp")
safety = agent.check_command_safety("Format-Volume -DriveLetter D")

# 4. Knowledge Graph: Blast radius & parameter validation
blast = agent.calculate_blast_radius("RpcSs", depth=2)
print(f"Blast risk: {blast.risk_score}, Direct dependents: {len(blast.direct_dependents)}")

val = agent.validate_command("Get-Process -Name svchost -Id 1234")
print(f"Valid command: {val.is_valid}")

# 5. Execute step with verification
exec_res, verif_res, trace = agent.execute_step(plan.steps[0], dry_run=False)
if exec_res.success:
    print(f"Success! Output: {exec_res.stdout}")

# 6. Undo / Rollback
undo_res = agent.undo_last_action()
```

---

## Model Context Protocol (MCP) Server

Connect WinTerM directly to **Google Antigravity**, **Claude Desktop**, **Claude Code**, or any MCP-compatible AI agent framework. WinTerM exposes a full suite of 32 low-level and high-level tools alongside standardized agent guidance prompts.

### Claude Code Integration (1-Command Setup)
Add WinTerM directly to **Claude Code** via the CLI:
```bash
claude mcp add winterm python -m winterm.tools.mcp_server
```
Claude Code automatically reads the repository instructions in [`CLAUDE.md`](CLAUDE.md) and custom skills in [`.claude/skills/winterm/`](.claude/skills/winterm/).

### OpenCode Integration
OpenCode connects automatically via the repository's [`opencode.json`](opencode.json) and reads operating guidelines from [`OPENCODE.md`](OPENCODE.md):
```json
{
  "mcp": {
    "winterm": {
      "type": "local",
      "command": ["python", "-m", "winterm.tools.mcp_server"]
    }
  }
}
```

### Generic MCP Client Configuration (Claude Desktop, Google Antigravity, Cursor)
Add to your `mcp_config.json` or Claude Desktop configuration:
```json
{
  "mcpServers": {
    "winterm": {
      "command": "python",
      "args": ["-m", "winterm.tools.mcp_server"],
      "cwd": "d:/Agent_toolkit"
    }
  }
}
```

### Exposed MCP Tools (37 Total):

#### 1. Core Execution & 5W Cognitive Engine (7 Tools)
- `plan_terminal_task`: Decomposes natural language goals into staged Directed Acyclic Graph (DAG) execution plans.
- `explain_terminal_command`: Generates 5W Decision Trace explaining What, How, When, Why, and What Happens After.
- `predict_command_impact`: Pre-execution state diff simulation (files, registry, processes, ports), risk score, and rollback synthesis.
- `execute_terminal_command`: Hardened, UTF-8 safe execution with timeout protection and autonomous self-healing.
- `diagnose_terminal_error`: Analyzes stderr and exit codes, classifies Windows error signatures, and proposes concrete remediation.
- `query_windows_knowledge`: Searches the internal Windows knowledge base for command syntax, shell rules, and environment pitfalls.
- `undo_last_terminal_action`: Reverts the last state-modifying action from the rollback history stack.

#### 2. Linux & WSL2 Subsystem (5 Tools)
- `winterm_linux_execute`: Executes bash / POSIX commands with deterministic safety guard checks, non-interactive flags, and self-healing.
- `winterm_linux_path_convert`: Bidirectional path conversion between Windows format (`C:\...`) and Linux format (`/mnt/c/...`).
- `winterm_linux_distro_list`: Queries installed WSL distributions, running states, and default distro.
- `winterm_linux_safety_check`: Deterministic safety analysis blocking destructive commands (`rm -rf /`, raw disk writes, fork bombs).
- `winterm_linux_diagnose_error`: POSIX and Linux error diagnosis covering exit codes 127, 126, 137 OOM, EADDRINUSE, and dpkg locks.

#### 3. Knowledge Graph & Semantic Reasoning (8 Tools)
- `winterm_graph_blast_radius`: Cascading blast radius analysis (direct + transitive dependent services) with risk scoring.
- `winterm_graph_validate_command`: Validates command flags against the 10,374-node Knowledge Graph to catch hallucinations and suggest typos.
- `winterm_graph_remedy_error`: Resolves multi-step error recovery paths for Windows HRESULTs and Win32 codes.
- `winterm_graph_alternatives`: Cross-shell equivalence lookup (PowerShell cmdlet <-> native Win32 binary).
- `winterm_graph_info`: Knowledge Graph topological metrics and ontological entity summary.
- `winterm_graph_search_intent`: Resolves natural language intents against indexed Windows command datasets.
- `winterm_graph_command_docs`: Official Microsoft documentation, syntax, and parameter dictionaries for 144+ Windows binaries.
- `winterm_graph_safety_check`: Evaluates command safety tier, credential sensitivity, and security warnings.

#### 4. Universal Application Discovery, Lifecycle & Dynamic Learning (4 Tools)
- `winterm_app_find`: Discovers installed applications across `shell:AppsFolder`, Start Menu shortcuts, and Uninstall registry keys.
- `winterm_app_launch`: Universally launches any Windows application (Win32 executable, UWP/AUMID Store app, or protocol URI).
- `winterm_app_close`: Gracefully closes (`WM_CLOSE`/`CloseMainWindow`) or forcefully terminates processes.
- `winterm_app_learn`: Probes local CLI help (`--help`, `/?`), parses parameter switches, and queries Knowledge Graph for usage patterns.

#### 5. Window Management & Focus Automation (4 Tools)
- `winterm_window_list`: Enumerates all visible top-level desktop windows with handles (HWND), titles, PIDs, bounds, and states.
- `winterm_window_focus`: Unlocks Windows UIPI focus locks, attaches input threads, and brings target windows to the foreground.
- `winterm_window_resize`: Repositions and resizes application windows to deterministic coordinates and dimensions.
- `winterm_window_close`: Sends native Win32 `WM_CLOSE` messages to gracefully close windows without terminating background threads.

#### 6. UI Automation, Perception & Input Synthesis (9 Tools)
- `winterm_ui_inspect`: Traverses Windows UI Automation element trees (buttons, inputs, menus, list items) with bounding box geometry.
- `winterm_ui_click`: Invokes elements via native `InvokePattern` with mouse coordinate fallback.
- `winterm_ui_set_text`: Sets text in edit/input controls via native `ValuePattern` with SendKeys fallback.
- `winterm_input_type`: Types keyboard text via SendKeys with configurable inter-key delays.
- `winterm_input_hotkey`: Simulates hotkeys and key combinations (`Ctrl+C`, `Win+R`, `Alt+F4`, `Ctrl+Shift+P`).
- `winterm_input_mouse_click`: Moves cursor to (X, Y) and performs mouse clicks (left, right, middle, double-click).
- `winterm_input_mouse_drag`: Performs drag-and-drop mouse gestures from start to end coordinates with guaranteed mouse-up release blocks.
- `winterm_screen_state`: Queries live display resolution, active cursor position, and foreground window metrics.
- `winterm_screen_capture`: Captures high-resolution visual screenshots of the full desktop or target window as PNG for visual perception.

### Exposed MCP Prompts
- `windows_agent_instructions`: Out-of-the-box system prompt that grounds autonomous agents in the Windows closed-loop automation protocol.

---

## Autonomous Agent Interaction Paradigm: The Closed-Loop Protocol

When an AI agent interacts with the Windows desktop and terminal, it must **never write one-off hardcoded automation scripts**. WinTerM enforces a rigorous 4-phase closed loop:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         THE CLOSED-LOOP AGENT CYCLE                         │
│                                                                             │
│   1. SENSE      Inspect app existence, active windows, UI trees, and screen  │
│        │                                                                    │
│        ▼                                                                    │
│   2. DECIDE     Classify app class (A/B/C) & formulate generic actions      │
│        │                                                                    │
│        ▼                                                                    │
│   3. ACT        Focus target window & execute guarded toolkit primitives     │
│        │                                                                    │
│        ▼                                                                    │
│   4. VERIFY     Check post-conditions (UIA tree state / visual screenshot)  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Anti-Pattern: Why Agents Must NOT Write One-Off Python Scripts
Autonomous agents frequently fall into the trap of writing temporary `.py` scripts containing hardcoded pixel coordinates, assumptions about file paths, or raw `mouse_event` loops. In real Windows environments, this pattern fails catastrophically:
1. **DPI & Resolution Fragility**: Hardcoded screen coordinates (e.g. `(400, 300)`) break across displays, scaling factors (100%, 125%, 150%, 200%), and window movements.
2. **Missing Executables**: Hardcoding fixed paths (e.g. `C:\Windows\System32\mspaint.exe`) causes instant failures when apps are packaged as modern MSIX/Store packages, installed in user profiles, or uninstalled.
3. **Input Leakage & Desktop Hijacking**: Injecting global keyboard or mouse events without verifying that the target window has foreground focus directs strokes into background windows (such as the developer's IDE or terminal), corrupting source code.
4. **Input Queue Freezing**: If a script performs a mouse-down or key-down and crashes before the corresponding release event, the entire OS input queue can become locked. WinTerM wraps all gestures in native `try...finally` release blocks.

### The 4-Phase Protocol in Practice

#### Phase 1: SENSE
Before taking any action, establish ground-truth system state:
- Check if the app is installed: `winterm_app_find(query="paint")`.
- If not installed, inform the user or install via `winget install <id>`.
- Check if the app is already open: `winterm_window_list(query="paint")`.
- Establish desktop boundaries: `winterm_screen_state()`.

#### Phase 2: DECIDE
Classify the target application and select the appropriate interaction channel:
- **Class A: Standard Win32 / WPF / UWP Applications** (e.g. Calculator, Notepad, File Explorer):
  - Traversed via `winterm_ui_inspect(window_identifier)`.
  - Manipulated via deterministic automation IDs and control names (`winterm_ui_click`, `winterm_ui_set_text`).
- **Class B: Electron / Chromium Applications** (e.g. VS Code, Slack, Chrome, Edge):
  - Manipulated via keyboard accelerators and command palettes (`winterm_input_hotkey(keys=['ctrl', 'shift', 'p'])`).
  - Navigated via standard URL/omnibar shortcuts (`Ctrl+L`).
- **Class C: Raw Canvas / DirectX / GDI Applications** (e.g. Paint canvas, games, CAD viewports):
  - Lacks granular child UI elements in the UIA tree.
  - Perceived via visual capture (`winterm_screen_capture`).
  - Target coordinates are calculated as relative offsets within the target window's known bounding box (`winterm_window_list`), never blind screen coordinates.

#### Phase 3: ACT
- Explicitly bring the target window to the foreground: `winterm_window_focus(window_identifier)`.
- Execute the chosen action using generic toolkit tools:
  - Text input: `winterm_input_type(text="...")`.
  - Hotkey: `winterm_input_hotkey(keys=["ctrl", "s"])`.
  - Point & Click: `winterm_input_mouse_click(x=..., y=...)`.
  - Vector gesture: `winterm_input_mouse_drag(start_x=..., start_y=..., end_x=..., end_y=...)`.

#### Phase 4: VERIFY
- Confirm state mutation:
  - Check window title updates or dialog prompts: `winterm_window_list()`.
  - Re-inspect UI elements: `winterm_ui_inspect()`.
  - Capture verification screenshot: `winterm_screen_capture(output_path="...")`.
- If the action failed, call `diagnose_terminal_error` or query `winterm_graph_remedy_error` to self-heal.

---

## Command-Line Interface (`winterm`)

WinTerM provides a modular CLI interface matching all toolkit capabilities:

```powershell
# ==============================================================================
# System Information & 10-Layer Subsystem Capabilities
# ==============================================================================
winterm info
winterm subsystems

# ==============================================================================
# 5W Cognitive Planning & Execution
# ==============================================================================
winterm plan "Find what process is using port 8080 and terminate it"
winterm explain "Stop-Process -Id 1234 -Force"
winterm run "Query top 5 memory processes" --dry-run
winterm run "Restart audio service" --auto-heal
winterm diagnose "0x80070005: Access is denied."

# ==============================================================================
# Knowledge Graph & Dataset Reasoning (10,374 Nodes, 5,675 Edges)
# ==============================================================================
winterm graph info
winterm graph blast-radius RpcSs --depth 2
winterm graph validate "Get-Process -Name svchost -Id 1234"
winterm graph search-intent "find files modified today"
winterm graph docs robocopy
winterm graph safety "Format-Volume -DriveLetter D"
winterm graph remedy 0x80070005
winterm graph alternatives Stop-Process

# ==============================================================================
# Application Discovery, Lifecycle & Dynamic Learning
# ==============================================================================
winterm app find "calculator"
winterm app launch "calc.exe"
winterm app learn "ping"
winterm app close "Calculator"

# ==============================================================================
# Top-Level Window Management
# ==============================================================================
winterm window list
winterm window focus "Notepad"
winterm window resize "Notepad" 100 100 1024 768
winterm window close "Notepad"

# ==============================================================================
# Keyboard, Mouse & UI Automation
# ==============================================================================
winterm input inspect "Calculator"
winterm input type "Hello World from WinTerm Agent"
winterm input hotkey ctrl c
winterm input click 500 400 --button left
winterm input drag 100 100 400 400

# ==============================================================================
# Live Screen Perception & Capture
# ==============================================================================
winterm screen state
winterm screen capture --output screenshot.png
winterm screen capture --output app.png --window "Calculator"
```

---

## Running Tests

Run the full automated test suite using pytest:
```powershell
python -m pytest tests/ -v
```

All **87 out of 87 automated tests (100%)** pass cleanly across all 10 architectural layers, CLI command sets, Knowledge Graph reasoning routines, and MCP server integrations.

---

## Community, Contributing & Governance 🤝

**WinTerM** is open-source and built for the global AI agent developer community. We believe the future of autonomous computing on Windows will be built collaboratively.

- 📖 **Contributor Guide**: Read our [CONTRIBUTING.md](CONTRIBUTING.md) for architecture deep-dives, step-by-step guides on adding subsystems/tools, and development setup.
- 🗺️ **Project Roadmap**: See our public vision, active development milestones, and community bounties in [ROADMAP.md](ROADMAP.md).
- 📜 **Code of Conduct**: We are committed to an inclusive, welcoming community. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- 🐛 **Report Issues & Incidents**:
  - Found a bug? File a [Bug Report](https://github.com/shiva2321/WinTerM/issues/new?template=bug_report.md).
  - Did an AI agent hallucinate a Windows command or hang on stdin? File an [AI Agent Incident Report](https://github.com/shiva2321/WinTerM/issues/new?template=agent_incident_report.md).
  - Want a new Windows API, subsystem primitive, or tool? Submit a [Feature Request](https://github.com/shiva2321/WinTerM/issues/new?template=feature_request.md).
- 💬 **Join the Conversation**: Connect with agent builders on [GitHub Discussions](https://github.com/shiva2321/WinTerM/discussions).

---

## License 📄

WinTerM is distributed under the permissive [MIT License](LICENSE). Free for personal, research, startup, and enterprise commercial use.



