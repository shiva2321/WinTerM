"""Windows Shell Executor: Subprocess execution, streaming, timeout control, and error diagnosis."""

import os
import time
import subprocess
from typing import Optional, Tuple
from winterm.models.context import ShellType
from winterm.models.result import ExecutionResult, SelfHealingProposal
from winterm.knowledge.shell_matrix import ShellMatrix
from winterm.knowledge.encoding_expert import EncodingExpert
from winterm.knowledge.error_catalog import WindowsErrorCatalog
from winterm.knowledge.reliability_rules import ReliabilityRules


class WindowsShellExecutor:
    """Robust, production-grade subprocess executor for Windows terminal operations."""

    def __init__(self, default_shell: ShellType = ShellType.POWERSHELL_51):
        self.default_shell = default_shell

    def execute(
        self,
        command: str,
        shell: Optional[ShellType] = None,
        working_directory: Optional[str] = None,
        timeout_seconds: int = 60,
        step_id: str = "exec",
        auto_diagnose: bool = True,
    ) -> ExecutionResult:
        """Executes a terminal command on Windows with strict reliability and error trapping."""
        target_shell = shell or self.default_shell
        cwd = working_directory or os.getcwd()

        # Build full executable command arguments
        shell_bin = ShellMatrix.get_shell_binary(target_shell)

        if target_shell in (ShellType.POWERSHELL_51, ShellType.POWERSHELL_7):
            # Prepend UTF-8 output encoding preamble
            preamble = EncodingExpert.get_encoding_preamble()
            # Wrap with non-interactive flags and reliability rules
            sanitized_cmd = ReliabilityRules.make_non_interactive(command)
            formatted_cmd = ReliabilityRules.format_executable_invocation(sanitized_cmd, target_shell)
            script_body = f"{preamble} {formatted_cmd}"
            cmd_args = ShellMatrix.build_command_args(target_shell, script_body)
        elif target_shell == ShellType.CMD:
            sanitized_cmd = ReliabilityRules.make_non_interactive(command)
            cmd_args = ShellMatrix.build_command_args(target_shell, sanitized_cmd)
        elif target_shell in (ShellType.WSL_BASH, ShellType.BASH):
            from winterm.knowledge.linux_safety import LinuxSafetyGuard
            sanitized_cmd = LinuxSafetyGuard.make_non_interactive(command)
            # Wrap with strict pipefail and non-interactive environment
            script_body = f"set -eo pipefail; export DEBIAN_FRONTEND=noninteractive; {sanitized_cmd}"
            cmd_args = ShellMatrix.build_command_args(target_shell, script_body)
        else:
            # Fallback direct execution
            cmd_args = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command]

        start_time = time.perf_counter()
        timed_out = False
        raw_stdout = b""
        raw_stderr = b""
        exit_code = 0

        proc = None
        startup_info = None
        if os.name == "nt":
            try:
                startup_info = subprocess.STARTUPINFO()
                startup_info.lpDesktop = r"WinSta0\default"
            except Exception:
                startup_info = None

        try:
            proc = subprocess.Popen(
                cmd_args,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,  # Prevent blocking on stdin prompt
                shell=False,
                startupinfo=startup_info,
            )

            raw_stdout, raw_stderr = proc.communicate(timeout=timeout_seconds)
            exit_code = proc.returncode

        except subprocess.TimeoutExpired:
            timed_out = True
            exit_code = -1
            if proc:
                # Cleanly kill the entire process tree on Windows using taskkill
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except Exception:
                    proc.kill()
                try:
                    raw_stdout, raw_stderr = proc.communicate(timeout=2)
                except Exception:
                    pass

        except Exception as ex:
            exit_code = -1
            raw_stderr = f"Subprocess invocation failure: {str(ex)}".encode("utf-8")

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Decode output streams safely
        stdout_str = EncodingExpert.decode_stream(raw_stdout)
        stderr_str = EncodingExpert.decode_stream(raw_stderr)

        if timed_out:
            stderr_str += f"\n[!] Execution timed out after {timeout_seconds} seconds. Process tree terminated."

        success = (exit_code == 0) and not timed_out

        # Auto-diagnose if failed
        healing_proposal: Optional[SelfHealingProposal] = None
        if not success and auto_diagnose:
            healing_proposal = WindowsErrorCatalog.diagnose(
                stderr=stderr_str,
                stdout=stdout_str,
                exit_code=exit_code,
                failed_command=command,
            )

        return ExecutionResult(
            step_id=step_id,
            command=command,
            shell=target_shell,
            success=success,
            exit_code=exit_code,
            stdout=stdout_str.strip(),
            stderr=stderr_str.strip(),
            duration_ms=duration_ms,
            timed_out=timed_out,
            healing_proposal=healing_proposal,
        )
