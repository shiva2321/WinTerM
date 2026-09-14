"""Full-Spectrum Tour of Windows Terminal Subsystems (Layers 0 to 8).

Demonstrates the 5W cognitive agent operating across all architectural layers:
- Layer 0: Firmware & Boot Mode
- Layer 1: Storage Volumes & Filesystem
- Layer 2: Process Memory & Working Set
- Layer 3: Task Scheduler
- Layer 4: Registry Policy (LongPathsEnabled)
- Layer 5: Security Privileges (whoami /priv)
- Layer 6: Network Adapters & DNS
- Layer 7: Performance Counters
- Layer 8: Virtualization (WSL) & Package Management (winget)
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from winterm.agent.winterm_agent import WinTermAgent

console = Console()


def run_tour():
    agent = WinTermAgent()
    console.print(Panel("[bold cyan]WinTermAgent: Full-Spectrum Windows Terminal Mastery Tour[/bold cyan]"))

    tour_goals = [
        ("Layer 0 (Firmware)", "Inspect firmware boot mode"),
        ("Layer 1 (Storage)", "List volumes"),
        ("Layer 2 (Process)", "Show top 5 memory processes"),
        ("Layer 4 (Registry)", "Check registry long paths"),
        ("Layer 5 (Security)", "Audit user privileges"),
        ("Layer 6 (Networking)", "List network adapters"),
        ("Layer 7 (Diagnostics)", "Sample performance counters"),
        ("Layer 8 (Virtualization)", "List WSL distros"),
    ]

    summary_table = Table(title="Subsystem Execution Results", border_style="cyan")
    summary_table.add_column("Layer", style="bold yellow")
    summary_table.add_column("Goal", style="white")
    summary_table.add_column("What (Command)", style="dim green")
    summary_table.add_column("Risk", style="magenta")
    summary_table.add_column("Status", style="bold green")

    for layer_name, goal in tour_goals:
        plan = agent.plan(goal)
        step = plan.steps[0]
        trace = agent.explain(step)
        impact = agent.predictor.predict_step_impact(step)

        # Run live execution
        exec_res, verif_res, _ = agent.execute_step(step, dry_run=False, auto_heal=True)

        status = "[OK] Success" if exec_res.success else f"[X] Exit {exec_res.exit_code}"
        cmd_snippet = step.command[:45] + "..." if len(step.command) > 45 else step.command

        summary_table.add_row(
            layer_name,
            goal,
            cmd_snippet,
            impact.risk_level.value.upper(),
            status,
        )

    console.print(summary_table)
    console.print("\n[bold green][OK] Full-Spectrum tour completed across all Windows subsystems![/bold green]")


if __name__ == "__main__":
    run_tour()
