"""Unit tests for Linux / WSL Subsystem, SafetyGuard, ErrorCatalog, and Path Translation."""

import pytest
from winterm.knowledge.linux_safety import LinuxSafetyGuard, LinuxSafetyVerdict
from winterm.knowledge.linux_errors import LinuxErrorCatalog
from winterm.subsystems.linux_subsystem import LinuxSubsystem
from winterm.tools.tool_definitions import (
    winterm_linux_safety_check,
    winterm_linux_path_convert,
    winterm_linux_diagnose_error,
)


def test_linux_safety_guard_destructive_rejections():
    """Validates that destructive Linux commands are caught and rejected as dangerous."""
    destructive_commands = [
        "rm -rf /",
        "rm -rf /*",
        "rm -r -f /etc",
        "rm -rf --no-preserve-root /",
        ":(){ :|:& };:",
        "dd if=/dev/zero of=/dev/sda bs=1M",
        "mkfs.ext4 /dev/nvme0n1p1",
        "fdisk /dev/sdb",
        "wipefs -a /dev/sda",
        "chmod -R 777 /",
        "chmod 000 /etc",
        "chown -R root:root /",
        "kill -9 1",
        "shutdown -h now",
        "init 0",
    ]

    for cmd in destructive_commands:
        verdict = LinuxSafetyGuard.evaluate(cmd)
        assert verdict.is_dangerous is True, f"Failed to flag dangerous: {cmd}"
        assert verdict.label == "destructive", f"Wrong label for: {cmd} (got {verdict.label})"
        assert verdict.warning != ""


def test_linux_safety_guard_network_sensitive():
    """Validates detection of firewall-dropping or interface-disabling commands."""
    sensitive = [
        "iptables -F",
        "ufw disable",
        "nft flush ruleset",
        "ip link set eth0 down",
    ]
    for cmd in sensitive:
        verdict = LinuxSafetyGuard.evaluate(cmd)
        assert verdict.is_dangerous is True
        assert verdict.label == "network_sensitive"


def test_linux_safety_guard_privileged():
    """Validates detection of sudo / privileged commands."""
    priv = [
        "sudo systemctl restart docker",
        "doas apt update",
        "userdel -r olduser",
    ]
    for cmd in priv:
        verdict = LinuxSafetyGuard.evaluate(cmd)
        assert verdict.label == "privileged"


def test_linux_safety_guard_safe_commands():
    """Validates that normal read-only or standard commands are classified as safe."""
    safe = [
        "ls -la /var/log",
        "cat /etc/os-release",
        "grep -rn 'error' /tmp",
        "python3 -m pytest tests/",
        "df -h",
        "git status",
        "curl -s https://api.github.com",
    ]
    for cmd in safe:
        verdict = LinuxSafetyGuard.evaluate(cmd)
        assert verdict.is_dangerous is False
        assert verdict.label == "safe"


def test_linux_non_interactive_switch_injection():
    """Validates automated injection of non-interactive switches to prevent terminal hangs."""
    # apt-get
    cmd1 = "sudo apt-get install nginx"
    res1 = LinuxSafetyGuard.make_non_interactive(cmd1)
    assert "-y" in res1
    assert "DEBIAN_FRONTEND=noninteractive" in res1

    # dnf
    cmd2 = "dnf install htop"
    res2 = LinuxSafetyGuard.make_non_interactive(cmd2)
    assert "-y" in res2

    # pacman
    cmd3 = "pacman -S ripgrep"
    res3 = LinuxSafetyGuard.make_non_interactive(cmd3)
    assert "--noconfirm" in res3

    # apk
    cmd4 = "apk add curl"
    res4 = LinuxSafetyGuard.make_non_interactive(cmd4)
    assert "--no-cache" in res4


def test_linux_error_catalog_diagnoses():
    """Validates automated diagnosis of standard Linux/POSIX failures."""
    # Command not found (127)
    d127 = LinuxErrorCatalog.diagnose(stdout="", stderr="bash: jq: command not found", exit_code=127, failed_command="jq .")
    assert d127 is not None
    assert d127.error_signature == "LINUX_COMMAND_NOT_FOUND_EXIT_127"

    # Permission denied (126 / EACCES)
    d126 = LinuxErrorCatalog.diagnose(stdout="", stderr="bash: ./deploy.sh: Permission denied", exit_code=126, failed_command="./deploy.sh")
    assert d126 is not None
    assert d126.error_signature == "LINUX_PERMISSION_DENIED_EACCES_126"
    assert "chmod +x" in d126.healing_command

    # OOM killed (137)
    d137 = LinuxErrorCatalog.diagnose(stdout="", stderr="Killed", exit_code=137, failed_command="python train.py")
    assert d137 is not None
    assert d137.error_signature == "LINUX_OOM_KILLED_EXIT_137"

    # Port in use (98)
    d98 = LinuxErrorCatalog.diagnose(stdout="", stderr="listen tcp 0.0.0.0:8080: bind: address already in use", exit_code=1, failed_command="./server")
    assert d98 is not None
    assert d98.error_signature == "LINUX_PORT_IN_USE_EADDRINUSE_98"

    # dpkg lock
    dpkg = LinuxErrorCatalog.diagnose(stdout="", stderr="E: Could not get lock /var/lib/dpkg/lock-frontend", exit_code=100)
    assert dpkg is not None
    assert dpkg.error_signature == "LINUX_APT_DPKG_LOCK_HELD"


def test_linux_subsystem_path_translation():
    """Validates bidirectional Windows <-> Linux path conversion."""
    # Windows to Linux
    linux_path = LinuxSubsystem.convert_path(r"C:\Users\Asta\project\file.py", to_linux=True)
    assert linux_path == "/mnt/c/Users/Asta/project/file.py"

    linux_d = LinuxSubsystem.convert_path(r"D:\Agent_toolkit\README.md", to_linux=True)
    assert linux_d == "/mnt/d/Agent_toolkit/README.md"

    # Linux to Windows
    win_path = LinuxSubsystem.convert_path("/mnt/c/Users/Asta/project/file.py", to_linux=False)
    assert win_path == r"C:\Users\Asta\project\file.py"

    win_d = LinuxSubsystem.convert_path("/mnt/d/Agent_toolkit/README.md", to_linux=False)
    assert win_d == r"D:\Agent_toolkit\README.md"


def test_linux_subsystem_plan_steps():
    """Validates PlanStep generation across Linux primitives."""
    p_service = LinuxSubsystem.inspect_service("nginx")
    assert "systemctl status nginx" in p_service.command

    p_restart = LinuxSubsystem.restart_service("nginx")
    assert "sudo systemctl restart nginx" in p_restart.command

    p_proc = LinuxSubsystem.list_processes(filter_name="python")
    assert "grep -i 'python'" in p_proc.command

    p_kill = LinuxSubsystem.kill_process(pid=1234, signal=9)
    assert "kill -9 1234" in p_kill.command

    p_df = LinuxSubsystem.disk_free()
    assert "df -h" in p_df.command

    p_net = LinuxSubsystem.network_interfaces()
    assert "ip -brief address show" in p_net.command

    p_ports = LinuxSubsystem.listening_ports()
    assert "ss -tulpn" in p_ports.command

    p_pkg = LinuxSubsystem.install_package("htop", manager="apt")
    assert "apt-get install -y htop" in p_pkg.command


def test_linux_mcp_wrappers():
    """Validates Linux MCP wrapper functions."""
    # Safety check
    res_safe = winterm_linux_safety_check("rm -rf /")
    assert res_safe["is_dangerous"] is True
    assert res_safe["label"] == "destructive"

    # Path convert
    res_path = winterm_linux_path_convert("C:\\Data\\file.txt", to_linux=True)
    assert res_path["converted_path"] == "/mnt/c/Data/file.txt"

    # Error diagnosis
    res_err = winterm_linux_diagnose_error("bash: command not found: htop", exit_code=127, failed_command="htop")
    assert res_err["diagnosed"] is True
    assert res_err["proposal"]["error_signature"] == "LINUX_COMMAND_NOT_FOUND_EXIT_127"
