---
name: 💡 Feature Request
about: Suggest an idea or new capability for WinTerM
title: "[FEATURE] "
labels: ["enhancement", "needs-discussion"]
assignees: ""
---

### Is Your Feature Request Related to a Problem? Please Describe.
A clear and concise description of what the problem is. Ex: I'm always frustrated when my agent tries to...

### Describe the Solution You'd Like
A clear and concise description of what you want to happen. Which subsystem or MCP tool should be added or updated?

### Subsystem Layer
- [ ] Layer 0: Kernel & Boot
- [ ] Layer 1: Storage & NTFS
- [ ] Layer 2: Process & Memory
- [ ] Layer 3: Services & Tasks
- [ ] Layer 4: Registry & Policies
- [ ] Layer 5: Security & Crypto
- [ ] Layer 6: Network & Firewall
- [ ] Layer 7: Diagnostics & Health
- [ ] Layer 8: Virtualization & Packages
- [ ] Layer 9: Desktop GUI & Perception
- [ ] MCP Server & Prompts
- [ ] Knowledge Graph & Dataset Reasoning

### Proposed CLI / MCP API Design (Optional)
```powershell
winterm my-subsystem my-action --param value
```
```json
{
  "name": "winterm_new_tool",
  "arguments": { ... }
}
```

### Additional Context
Add any other context, screenshots, or links to Microsoft documentation.
