# WinTerM CLI Reference Guide

The `winterm` CLI provides direct terminal access to all WinTerM subsystems without requiring Python scripting or an active MCP server connection.

```powershell
# Run directly via the installed binary
winterm --help

# Or via Python module execution
python -m winterm --help
```

---

## 1. System Diagnostics & Info

### `winterm info`
Probes and displays the host Windows terminal environment, PowerShell edition, elevation level, console code page, long paths status, and package managers.
```powershell
winterm info
```

### `winterm subsystems`
Prints the 10-layer architectural subsystem matrix with available capabilities.
```powershell
winterm subsystems
```

---

## 2. Planning, Explanation & Execution

### `winterm plan`
Decomposes a natural language goal into staged execution steps.
```powershell
winterm plan "Find what process is using port 8080 and stop it"
```

### `winterm explain`
Explains a command across the 5W model (What, How, When, Why, After).
```powershell
winterm explain "Stop-Process -Id 1234 -Force"
```

### `winterm run`
Plans, explains, simulates, executes, and verifies a goal with automated self-healing.
```powershell
# Safe simulation without modifying system state
winterm run "Query top 5 memory processes" --dry-run

# Live execution
winterm run "Query system hardware info"

# Explicitly allow dangerous commands (bypasses SafetyGate)
winterm run "Remove-Item -Recurse -Force C:\Temp\OldBuilds" --confirm-high-risk
```

### `winterm diagnose`
Diagnoses any Windows terminal error string and generates remediation commands.
```powershell
winterm diagnose "0x80070005: Access is denied."
```

---

## 3. Universal Tool Runner

### `winterm tool`
Executes any of the 51 WinTerM tools directly from the CLI. Handles PowerShell 5.1 unquoted JSON arguments gracefully.
```powershell
# List open windows
winterm tool winterm_window_list

# Focus a window by HWND
winterm tool winterm_window_focus '{"identifier": "789800"}'

# Execute native OCR
winterm tool winterm_ui_ocr '{"window": "789800"}'

# Press a hotkey
winterm tool winterm_input_hotkey '{"keys": ["win", "r"]}'
```

### `winterm tools`
Prints a formatted table of all 51 available tools.
```powershell
winterm tools
```

---

## 4. Application Lifecycle (`winterm app`)

```powershell
# Search for installed applications across AppsFolder, Start Menu, and Registry
winterm app search "Chrome"

# Launch an application or URI
winterm app launch "chrome.exe" --args "https://www.google.com"

# Close an application gracefully or forcefully
winterm app close "notepad.exe"
winterm app close "chrome.exe" --force
```

---

## 5. Window Management (`winterm window`)

```powershell
# List visible top-level windows (returns HWND, title, bounds, state)
winterm window list
winterm window list "Chrome"

# Bring window to foreground and restore if minimized
winterm window focus 789800

# Reposition and resize window
winterm window resize 789800 100 100 1920 1080

# Close window gracefully
winterm window close 789800
```

---

## 6. UI Automation & Grounding (`winterm ui`)

```powershell
# Inspect UIAutomation controls inside a window
winterm ui inspect 789800

# Run hardware-accelerated WinRT Native OCR on window canvas
winterm ui ocr 789800

# Generate Set-of-Mark (SoM) visual grounding badges ([1], [2], [3]...)
winterm ui som 789800 "som_badges.png"

# Cognitive Screen Mental Map with zones and action affordances
winterm ui mental-map 789800
winterm ui mental-map 789800 --json

# Smart cascading click: UIAutomation -> OCR -> Coordinates
winterm ui smart-click 789800 "Search"

# Calibrated vertical scroll into viewport
winterm ui scroll-to 789800 650

# Set text in an edit control
winterm ui set-text 789800 "SearchEditBox" "quantum computing"

# Wait for visual change/page load
winterm ui wait-change 789800 --timeout 5000
```

---

## 7. Hardware Input Simulation (`winterm input`)

```powershell
# Type Unicode text using safe SendInput
winterm input type "Hello World"

# Clear existing input and type replacement safely
winterm input type-clear "Replacement search text"

# Smooth Bezier hover over element or coordinates
winterm input hover 789800 --query "Settings" --dwell 600
winterm input hover 789800 --x 350 --y 120 --dwell 500

# Press single keys or key combinations
winterm input hotkey win r
winterm input hotkey ctrl l
winterm input hotkey enter

# Window-contained mouse click (X, Y)
winterm input click 450 220 --button left

# Mouse drag
winterm input drag 100 100 500 500
```

---

## 8. Screen Perception (`winterm screen`)

```powershell
# Capture desktop or specific window to PNG
winterm screen capture -o "desktop.png"
winterm screen capture -w 789800 -o "chrome.png"

# Inspect screen metrics and cursor position
winterm screen state
```

---

## 9. Knowledge Graph Reasoning (`winterm graph`)

```powershell
# Graph topology and summary
winterm graph info

# Cascading service blast radius analysis
winterm graph blast-radius RpcSs --depth 2

# Parameter validation and typo defense
winterm graph validate "Get-Process -Name svchost"

# Natural language intent query
winterm graph search-intent "find files modified today"

# Official Microsoft command docs
winterm graph docs robocopy

# Safety classification
winterm graph safety "Remove-Item C:\Windows -Recurse"

# Error remediation path
winterm graph remedy 0x80070005

# Command alternatives
winterm graph alternatives Stop-Process
```

---

## 10. Multi-Agent Swarm (`winterm swarm`)

```powershell
# Dispatch a scoped sub-agent
winterm swarm dispatch "AuditWorker" --privilege read_only_audit --goal "Inspect open ports"

# View swarm status, circuit breakers, and fault counts
winterm swarm status

# Read messages from the Swarm Message Board
winterm swarm board --limit 20

# Review proactive suggestions proposed by sub-agents
winterm swarm suggestions list
winterm swarm suggestions approve --id sug-123
```
