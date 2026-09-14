"""Tests for High-Level Windows Subsystems: Layer 6 (Network/Firewall), Layer 7 (Diagnostics/Health), Layer 8 (Virtualization/Packages)."""

import pytest
from winterm.subsystems.network_firewall import NetworkFirewallSubsystem
from winterm.subsystems.diagnostics_health import DiagnosticsHealthSubsystem
from winterm.subsystems.virtualization_packages import VirtualizationPackagesSubsystem
from winterm.models.context import ShellType, ElevationLevel
from winterm.models.intent import ActionCategory


def test_network_firewall_subsystem_plans():
    # List adapters
    step_adapters = NetworkFirewallSubsystem.list_network_adapters()
    assert "Get-NetAdapter" in step_adapters.command

    # Routing table
    step_route = NetworkFirewallSubsystem.inspect_ip_routing_table()
    assert "Get-NetRoute" in step_route.command

    # Create firewall rule
    step_fw = NetworkFirewallSubsystem.create_firewall_rule(
        rule_name="AgentInboundPort",
        port=9090,
        protocol="TCP",
        direction="Inbound",
    )
    assert "New-NetFirewallRule" in step_fw.command
    assert "9090" in step_fw.command
    assert step_fw.required_elevation == ElevationLevel.ADMIN

    # Flush DNS
    step_dns = NetworkFirewallSubsystem.flush_dns_cache()
    assert "ipconfig /flushdns" in step_dns.command

    # WinHTTP Proxy
    step_proxy = NetworkFirewallSubsystem.query_winhttp_proxy()
    assert "netsh winhttp show proxy" in step_proxy.command


def test_diagnostics_health_subsystem_plans():
    # Event Log errors
    step_events = DiagnosticsHealthSubsystem.query_recent_system_errors(max_events=20)
    assert "Get-WinEvent" in step_events.command
    assert "LogName = 'System'" in step_events.command

    # Performance Counters
    step_perf = DiagnosticsHealthSubsystem.query_live_performance_metrics()
    assert "Get-Counter" in step_perf.command

    # SFC Scannow
    step_sfc = DiagnosticsHealthSubsystem.scan_system_file_integrity()
    assert "sfc /scannow" in step_sfc.command
    assert step_sfc.required_elevation == ElevationLevel.ADMIN

    # DISM CheckHealth
    step_dism = DiagnosticsHealthSubsystem.dism_health_check()
    assert "dism.exe /Online /Cleanup-Image /CheckHealth" in step_dism.command
    assert step_dism.required_elevation == ElevationLevel.ADMIN


def test_virtualization_packages_subsystem_plans():
    # WSL list
    step_wsl = VirtualizationPackagesSubsystem.list_wsl_distributions()
    assert "wsl.exe --list --verbose" in step_wsl.command

    # WSL shutdown
    step_down = VirtualizationPackagesSubsystem.shutdown_wsl()
    assert "wsl.exe --shutdown" in step_down.command

    # Hyper-V
    step_vm = VirtualizationPackagesSubsystem.list_hyperv_vms()
    assert "Get-VM" in step_vm.command
    assert step_vm.required_elevation == ElevationLevel.ADMIN

    # Optional Features
    step_feat = VirtualizationPackagesSubsystem.query_windows_optional_features("Hyper-V")
    assert "Get-WindowsOptionalFeature" in step_feat.command

    # Winget Install
    step_winget = VirtualizationPackagesSubsystem.winget_install("Git.Git")
    assert "winget.exe install" in step_winget.command
    assert "Git.Git" in step_winget.command
    assert "--accept-package-agreements" in step_winget.command
