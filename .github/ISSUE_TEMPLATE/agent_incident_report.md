---
name: 🤖 AI Agent Incident Report
about: Report when an AI agent hallucinated, hung on stdin, or failed a task on Windows
title: "[AGENT INCIDENT] "
labels: ["agent-incident", "hallucination", "self-healing"]
assignees: ""
---

### What Was the AI Agent Trying to Accomplish?
*Describe the natural language prompt or high-level goal given to the agent (e.g. "Draw a square in Paint", "Restart the audio service", "Find what process holds port 3000").*

### Which AI Agent Framework Was Used?
- [ ] Google Antigravity
- [ ] Claude Code / Claude Desktop
- [ ] Cursor IDE / Windsurf
- [ ] OpenAI Swarm / OpenAI Operator
- [ ] LangChain / LangGraph
- [ ] CrewAI / AutoGen
- [ ] Custom In-House Agent

### Incident Category
- [ ] **Parameter Hallucination**: Agent invented non-existent switches or parameters.
- [ ] **Interactive Hang**: Agent ran a command that hung waiting for stdin confirmation (`[Y/N]`).
- [ ] **UTF-8 Corruption**: Stderr/Stdout codepage corruption caused agent parsing failure.
- [ ] **UI Automation Failure**: Control element was not found in UI tree or `winterm_ui_click` missed.
- [ ] **Input Desync**: Keystrokes or clicks leaked into an unintended background window.
- [ ] **Error Healing Failure**: WinTerM failed to recognize an error code or proposed an incorrect fix.

### Command or MCP Tool Invoked
```powershell
# Paste the exact command or tool call made by the agent
```

### What Happened vs What Should Have Happened
- **What Happened**:
- **What Should Have Happened**:

### Decision Trace / Tool Output Log
```json
// Paste the Decision Trace or tool execution JSON result here
```

### Proposed Self-Healing Rule or Fix (Optional)
If you know how WinTerM should automatically heal or prevent this in the future, let us know!
