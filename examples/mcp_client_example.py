"""Simulated MCP client demonstrating how an external AI agent interacts with WinTerm."""

import json
from winterm.tools.mcp_server import WinTermMCPServer


def main():
    print("=== Simulating MCP Client Request to WinTerm Server ===\n")
    server = WinTermMCPServer()

    # 1. Initialize
    init_req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    resp = server.handle_request(init_req)
    print("1. Initialize Response:")
    print(json.dumps(resp, indent=2))

    # 2. List tools
    list_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    tools_resp = server.handle_request(list_req)
    print("\n2. Discovered Tools:")
    for t in tools_resp["result"]["tools"]:
        print(f"  - {t['name']}: {t['description'][:60]}...")

    # 3. Call 'predict_command_impact'
    call_req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "predict_command_impact",
            "arguments": {
                "command": "Stop-Process -Id 9999 -Force",
                "target_shell": "powershell_51",
            },
        },
    }
    impact_resp = server.handle_request(call_req)
    print("\n3. Impact Prediction Response:")
    print(impact_resp["result"]["content"][0]["text"])


if __name__ == "__main__":
    main()
