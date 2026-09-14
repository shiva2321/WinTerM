"""Layer 6: Networking, Firewall, Remote Management & Sockets Subsystem."""

from typing import Dict, Any, List, Optional
from winterm.models.context import ShellType, ElevationLevel
from winterm.models.intent import PlanStep, ActionCategory


class NetworkFirewallSubsystem:
    """Manages network adapters, IP routing, Windows Advanced Firewall, DNS, WinRM, and WinHTTP."""

    @classmethod
    def list_network_adapters(cls) -> PlanStep:
        """Enumerates physical and virtual network adapters with link speeds and MAC addresses."""
        return PlanStep(
            step_id="net-adapters-list",
            title="Inspect Network Adapters and Link Speeds",
            category=ActionCategory.NETWORK,
            raw_intent="list network adapters",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                "Get-NetAdapter | "
                "Select-Object -Property Name,InterfaceDescription,Status,LinkSpeed,MacAddress | "
                "ConvertTo-Json -Depth 5"
            ),
            metadata={"subsystem": "network_firewall", "action": "list_adapters"},
        )

    @classmethod
    def inspect_ip_routing_table(cls) -> PlanStep:
        """Retrieves active IPv4/IPv6 routing table entries and gateways."""
        return PlanStep(
            step_id="net-routing-table",
            title="Inspect IPv4 Routing Table and Default Gateways",
            category=ActionCategory.NETWORK,
            raw_intent="inspect routing table",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                "Get-NetRoute -AddressFamily IPv4 | "
                "Select-Object -Property DestinationPrefix,NextHop,RouteMetric,InterfaceAlias | "
                "ConvertTo-Json -Depth 5"
            ),
            metadata={"subsystem": "network_firewall", "action": "routing_table"},
        )

    @classmethod
    def create_firewall_rule(
        cls,
        rule_name: str,
        port: int,
        protocol: str = "TCP",
        direction: str = "Inbound",
        action: str = "Allow",
    ) -> PlanStep:
        """Creates a rule in Windows Defender Advanced Firewall."""
        return PlanStep(
            step_id=f"net-fw-create-{rule_name.replace(' ', '_')}",
            title=f"Create Firewall Rule '{rule_name}' ({direction} {protocol} {port} -> {action})",
            category=ActionCategory.NETWORK,
            raw_intent=f"create firewall rule {rule_name}",
            target_shell=ShellType.POWERSHELL_51,
            required_elevation=ElevationLevel.ADMIN,
            command=(
                f"New-NetFirewallRule -DisplayName '{rule_name}' -Direction {direction} "
                f"-LocalPort {port} -Protocol {protocol} -Action {action} -Profile Any"
            ),
            metadata={"subsystem": "network_firewall", "rule_name": rule_name, "port": port},
        )

    @classmethod
    def remove_firewall_rule(cls, rule_name: str) -> PlanStep:
        """Deletes a named firewall rule."""
        return PlanStep(
            step_id=f"net-fw-del-{rule_name.replace(' ', '_')}",
            title=f"Remove Firewall Rule: {rule_name}",
            category=ActionCategory.NETWORK,
            raw_intent=f"remove firewall rule {rule_name}",
            target_shell=ShellType.POWERSHELL_51,
            required_elevation=ElevationLevel.ADMIN,
            command=f"Remove-NetFirewallRule -DisplayName '{rule_name}' -ErrorAction SilentlyContinue",
            metadata={"subsystem": "network_firewall", "rule_name": rule_name},
        )

    @classmethod
    def flush_dns_cache(cls) -> PlanStep:
        """Flushes and resets the local Windows DNS Resolver Cache."""
        return PlanStep(
            step_id="net-dns-flush",
            title="Flush Windows DNS Client Resolver Cache",
            category=ActionCategory.NETWORK,
            raw_intent="flush dns cache",
            target_shell=ShellType.CMD,
            command="ipconfig /flushdns",
            metadata={"subsystem": "network_firewall", "action": "flush_dns"},
        )

    @classmethod
    def query_winhttp_proxy(cls) -> PlanStep:
        """Inspects system WinHTTP proxy configuration."""
        return PlanStep(
            step_id="net-winhttp-proxy",
            title="Inspect WinHTTP System Proxy Settings",
            category=ActionCategory.NETWORK,
            raw_intent="query winhttp proxy",
            target_shell=ShellType.CMD,
            command="netsh winhttp show proxy",
            metadata={"subsystem": "network_firewall", "action": "winhttp_proxy"},
        )
