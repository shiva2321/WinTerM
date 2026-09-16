"""Layer 6: Networking, Firewall, Remote Management & Sockets Subsystem."""

from typing import Dict, Any, List, Optional
from winterm.models.context import ShellType, ElevationLevel
from winterm.models.intent import PlanStep, ActionCategory
from winterm.knowledge.param_safety import ps_literal, safe_identifier, validated_choice, int_in_range

_DIRECTIONS = ("Inbound", "Outbound")
_PROTOCOLS = ("TCP", "UDP", "ICMPv4", "ICMPv6", "Any")
_ACTIONS = ("Allow", "Block", "NotConfigured")


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
        safe_name = safe_identifier(rule_name, fallback="WinTermRule")
        safe_port = int_in_range(port, 1, 65535, 0)
        safe_proto = validated_choice(protocol, _PROTOCOLS, "TCP")
        safe_dir = validated_choice(direction, _DIRECTIONS, "Inbound")
        safe_action = validated_choice(action, _ACTIONS, "Allow")
        return PlanStep(
            step_id=f"net-fw-create-{safe_name}",
            title=f"Create Firewall Rule '{safe_name}' ({safe_dir} {safe_proto} {safe_port} -> {safe_action})",
            category=ActionCategory.NETWORK,
            raw_intent=f"create firewall rule {safe_name}",
            target_shell=ShellType.POWERSHELL_51,
            required_elevation=ElevationLevel.ADMIN,
            command=(
                f"New-NetFirewallRule -DisplayName {ps_literal(safe_name)} -Direction {safe_dir} "
                f"-LocalPort {safe_port} -Protocol {safe_proto} -Action {safe_action} -Profile Any"
            ),
            metadata={"subsystem": "network_firewall", "rule_name": safe_name, "port": safe_port},
        )

    @classmethod
    def remove_firewall_rule(cls, rule_name: str) -> PlanStep:
        """Deletes a named firewall rule."""
        safe_name = safe_identifier(rule_name, fallback="WinTermRule")
        return PlanStep(
            step_id=f"net-fw-del-{safe_name}",
            title=f"Remove Firewall Rule: {safe_name}",
            category=ActionCategory.NETWORK,
            raw_intent=f"remove firewall rule {safe_name}",
            target_shell=ShellType.POWERSHELL_51,
            required_elevation=ElevationLevel.ADMIN,
            command=f"Remove-NetFirewallRule -DisplayName {ps_literal(safe_name)} -ErrorAction SilentlyContinue",
            metadata={"subsystem": "network_firewall", "rule_name": safe_name},
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
