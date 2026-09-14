"""WinTerm CLI: Interactive terminal interface for the Windows Terminal AI Agent Toolkit."""

import sys
from typing import Optional, List, Dict, Any
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.markup import escape
from winterm.agent.winterm_agent import WinTermAgent
from winterm.models.context import ShellType
from winterm.engine.environment import WindowsEnvironment
from winterm.knowledge.error_catalog import WindowsErrorCatalog

app = typer.Typer(
    name="winterm",
    help="AI Agent Toolkit for Windows Terminal - Mastering What, How, When, Why, and What Happens After.",
    add_completion=False,
)
console = Console()


@app.command()
def info():
    """Inspects and displays the host Windows terminal environment and capabilities."""
    ctx = WindowsEnvironment.probe()

    table = Table(title="Windows Terminal Environment Snapshot", border_style="cyan")
    table.add_column("Property", style="bold white")
    table.add_column("Value", style="green")

    table.add_row("Operating System", f"{ctx.os_name} {ctx.os_release} (Build {ctx.os_build})")
    table.add_row("Architecture", ctx.architecture)
    table.add_row("PowerShell Version", ctx.powershell_version)
    table.add_row("PowerShell 7 (pwsh)", "[OK] Available" if ctx.pwsh_available else "[X] Not Installed")
    table.add_row("WSL Available", "[OK] Available" if ctx.wsl_available else "[X] Not Installed")
    table.add_row("Current Elevation", ctx.current_elevation.value.upper())
    table.add_row("Console Code Page", str(ctx.active_code_page))
    table.add_row("LongPathsEnabled (>260 chars)", "[OK] Yes" if ctx.long_paths_enabled else "[X] No (260 char limit active)")
    table.add_row("Package Managers", ", ".join(ctx.installed_package_managers) or "None detected")
    table.add_row("Current Directory", ctx.current_directory)

    console.print(table)


@app.command()
def subsystems():
    """Lists the 9 architectural Windows terminal subsystem layers and capabilities."""
    layers = [
        ("Layer 0: Kernel & Boot", "KernelBootSubsystem", "BCD (bcdedit), powercfg, drivers (pnputil), TPM, UEFI/BIOS"),
        ("Layer 1: Storage & NTFS", "StorageNTFSSubsystem", "Get-Disk, Volumes, BitLocker, VSS shadow copies, ACLs (icacls/Get-Acl)"),
        ("Layer 2: Process & Memory", "ProcessMemorySubsystem", "Process priority, CPU affinity bitmasks, loaded DLL modules, threads, memory trim"),
        ("Layer 3: Services & Tasks", "ServicesTasksSubsystem", "SCM failure auto-recovery (sc.exe), startup types, Task Scheduler (schtasks)"),
        ("Layer 4: Registry & Policies", "RegistryPolicySubsystem", "HKLM/HKCU typed properties (DWord/QWord), Group Policy (gpupdate, gpresult)"),
        ("Layer 5: Security & Crypto", "SecurityCryptoSubsystem", "whoami /priv privileges, local users/groups, Certificate Store, Windows Defender"),
        ("Layer 6: Network & Firewall", "NetworkFirewallSubsystem", "Get-NetAdapter, IPv4 routing table, New-NetFirewallRule, DNS flush, WinHTTP proxy"),
        ("Layer 7: Diagnostics & Health", "DiagnosticsHealthSubsystem", "Event Log (Get-WinEvent), performance counters (Get-Counter), sfc /scannow, dism"),
        ("Layer 8: Virtualization & Packages", "VirtualizationPackagesSubsystem", "WSL lifecycle, Hyper-V VMs (Get-VM), Optional Features, winget/choco package manager"),
        ("Layer 9: Desktop GUI & Interaction", "DesktopGuiSubsystem", "shell:AppsFolder discovery, window management (focus/resize), UI Automation, mouse/keyboard/pen inputs"),
    ]

    table = Table(title="WinTerm 10-Layer Subsystem Architecture", border_style="green")
    table.add_column("Layer", style="bold yellow")
    table.add_column("Subsystem Class", style="cyan")
    table.add_column("Capabilities & Primitives", style="white")

    for layer, cls_name, caps in layers:
        table.add_row(layer, cls_name, caps)

    console.print(table)


@app.command()
def plan(
    goal: str = typer.Argument(..., help="Natural language goal to plan"),
):
    """Decomposes a goal into a staged Windows execution plan (WHAT to do)."""
    agent = WinTermAgent()
    plan_obj = agent.plan(goal)

    console.print(Panel(f"[bold cyan]Goal:[/bold cyan] {goal}\n[bold]Plan ID:[/bold] {plan_obj.plan_id}", title="Execution Plan"))

    table = Table(title=f"Staged Plan Steps ({len(plan_obj.steps)} total)", border_style="blue")
    table.add_column("Step", style="bold yellow")
    table.add_column("Title", style="white")
    table.add_column("Category", style="cyan")
    table.add_column("Target Shell", style="magenta")
    table.add_column("Command", style="green")

    for step in plan_obj.steps:
        synth_cmd = agent.synthesizer.synthesize_step_command(step)
        table.add_row(
            step.step_id,
            step.title,
            step.category.value,
            step.target_shell.value,
            synth_cmd[:80] + ("..." if len(synth_cmd) > 80 else ""),
        )

    console.print(table)


@app.command()
def explain(
    command: str = typer.Argument(..., help="Command string to analyze"),
    shell: str = typer.Option("powershell_51", "--shell", "-s", help="Target shell (powershell_51, pwsh, cmd)"),
):
    """Explains a command across the complete 5W Cognitive Model (What, How, When, Why, After)."""
    agent = WinTermAgent()
    shell_enum = ShellType(shell) if shell in [s.value for s in ShellType] else ShellType.POWERSHELL_51

    from winterm.models.intent import PlanStep, ActionCategory
    step = PlanStep(
        step_id="explain-step",
        title="Analyze command",
        category=ActionCategory.CUSTOM,
        raw_intent=command,
        command=command,
        target_shell=shell_enum,
    )

    trace = agent.explain(step)
    impact = agent.predictor.predict_step_impact(step)

    console.print(Panel(f"[bold green]Command:[/bold green] {step.command}", title="5W Decision Trace"))

    tree = Tree("[bold cyan]5W Cognitive Breakdown[/bold cyan]")
    tree.add(f"[bold]1. WHAT:[/bold] {trace.what}")
    tree.add(f"[bold]2. HOW:[/bold] {trace.how}")

    when_branch = tree.add("[bold]3. WHEN (Preconditions & Guards):[/bold]")
    if trace.when:
        for chk in trace.when:
            when_branch.add(f"- {chk.check_type.value}: {chk.target} (probe: `{chk.probe_command}`)")
    else:
        when_branch.add("- Safe to execute unconditionally.")

    why_branch = tree.add("[bold]4. WHY (Semantic Justification):[/bold]")
    why_branch.add(f"Justification: {trace.why.command_justification}")
    if trace.why.alternatives_rejected:
        for alt in trace.why.alternatives_rejected:
            why_branch.add(f"Rejected: `{alt.alternative}` ({alt.reason})")

    after_branch = tree.add(f"[bold]5. AFTER (Impact & Risk: {impact.risk_level.value.upper()}):[/bold]")
    after_branch.add(f"Summary: {trace.after}")
    if impact.rollback:
        after_branch.add(f"Rollback recipe: `{impact.rollback.command}`")

    console.print(tree)


@app.command()
def run(
    goal: str = typer.Argument(..., help="Goal to plan and execute"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Simulate execution without running commands"),
    auto_heal: bool = typer.Option(True, "--auto-heal/--no-auto-heal", help="Automatically attempt healing on failure"),
):
    """Plans, explains, executes, and verifies a goal on Windows Terminal."""
    agent = WinTermAgent()
    console.print(f"[bold cyan]Planning goal:[/bold cyan] {goal}")

    plan_obj = agent.plan(goal)
    console.print(f"Generated plan with {len(plan_obj.steps)} step(s). Starting execution...")

    for step in plan_obj.steps:
        console.print(Panel(f"[bold]Executing:[/bold] {step.title}\n[dim]{step.command}[/dim]", title=step.step_id))
        res, verif, trace = agent.execute_step(step, dry_run=dry_run, auto_heal=auto_heal)

        if res.success:
            console.print(f"[bold green][OK] Success[/bold green] in {res.duration_ms}ms")
            if res.stdout:
                console.print(f"[dim]{res.stdout[:200]}[/dim]")
            if verif:
                console.print(f"[cyan]Verification:[/cyan] {verif.details}")
        else:
            console.print(f"[bold red][X] Failed[/bold red] with exit code {res.exit_code}")
            if res.stderr:
                console.print(f"[red]{res.stderr}[/red]")
            if res.healing_proposal:
                console.print(Panel(
                    f"Root Cause: {res.healing_proposal.root_cause}\n"
                    f"Remedy: {res.healing_proposal.remedy_explanation}\n"
                    f"Command: `{res.healing_proposal.healing_command}`",
                    title="Self-Healing Proposal",
                    border_style="yellow"
                ))
            break


@app.command()
def diagnose(
    error_text: str = typer.Argument(..., help="Error message or stderr text to diagnose"),
    command: str = typer.Option("", "--command", "-c", help="The command that failed"),
):
    """Diagnoses a Windows terminal error string and generates remediation steps."""
    proposal = WindowsErrorCatalog.diagnose(
        stderr=error_text,
        stdout="",
        exit_code=1,
        failed_command=command,
    )

    if proposal:
        console.print(Panel(
            f"[bold]Error Signature:[/bold] {proposal.error_signature}\n"
            f"[bold]Root Cause:[/bold] {proposal.root_cause}\n"
            f"[bold]Remedy:[/bold] {proposal.remedy_explanation}\n"
            f"[bold]Healing Command:[/bold] `{proposal.healing_command}`\n"
            f"[bold]Requires Elevation:[/bold] {proposal.requires_elevation}",
            title="[bold green]Diagnosis & Self-Healing Plan[/bold green]",
            border_style="green"
        ))
    else:
        console.print("[yellow]No specific Windows error signature matched. Check raw stderr.[/yellow]")


# =============================================================================
# KNOWLEDGE GRAPH SUB-COMMANDS
# =============================================================================

graph_app = typer.Typer(
    name="graph",
    help="Query and reason across the Windows Terminal Knowledge Graph.",
)
app.add_typer(graph_app, name="graph")


@graph_app.command("info")
def graph_info():
    """Displays Knowledge Graph topological metrics and ontology breakdown."""
    from winterm.graph.engine import WindowsKnowledgeGraph
    kg = WindowsKnowledgeGraph()
    metrics = kg.get_metrics()

    console.print(Panel(
        f"[bold cyan]Total Entities (Nodes):[/bold cyan] {metrics['total_nodes']}\n"
        f"[bold cyan]Total Relationships (Edges):[/bold cyan] {metrics['total_edges']}",
        title="Windows Terminal Knowledge Graph Topology",
        border_style="cyan",
    ))

    t_nodes = Table(title="Ontological Entity Types (Nodes)", border_style="blue")
    t_nodes.add_column("Entity Type", style="bold yellow")
    t_nodes.add_column("Count", style="green")
    for nt, cnt in sorted(metrics["node_type_counts"].items()):
        t_nodes.add_row(nt, str(cnt))
    console.print(t_nodes)

    t_edges = Table(title="Semantic Relationships (Edges)", border_style="green")
    t_edges.add_column("Relation Type", style="bold cyan")
    t_edges.add_column("Count", style="green")
    for rel, cnt in sorted(metrics["relation_type_counts"].items()):
        t_edges.add_row(rel, str(cnt))
    console.print(t_edges)


@graph_app.command("blast-radius")
def graph_blast_radius(
    resource: str = typer.Argument(..., help="Service or resource name (e.g. RpcSs, LanmanServer)"),
    depth: int = typer.Option(2, "--depth", "-d", help="Cascade traversal depth"),
):
    """Calculates cascading downstream impact if a service or resource is stopped or modified."""
    from winterm.graph.engine import WindowsKnowledgeGraph
    kg = WindowsKnowledgeGraph()
    report = kg.calculate_blast_radius(resource, depth=depth)

    risk_style = "bold red" if report.risk_score in ("CRITICAL", "HIGH") else "bold green"
    console.print(Panel(
        f"[bold]Target Entity:[/bold] {report.root_node_id}\n"
        f"[bold]Assessed Risk:[/bold] [{risk_style}]{report.risk_score}[/{risk_style}]\n"
        f"[bold]Cascade Traversal Depth:[/bold] {report.blast_radius_depth}\n\n"
        f"[bold]Executive Impact Summary:[/bold]\n{report.impact_summary}",
        title="Knowledge Graph Blast Radius Assessment",
        border_style="red" if report.risk_score == "CRITICAL" else "yellow",
    ))

    tree = Tree(f"[bold red]Cascading Dependency Tree for {report.root_node_id}[/bold red]")
    direct_branch = tree.add(f"[bold yellow]Direct Dependents ({len(report.direct_dependents)}):[/bold yellow]")
    for dep in report.direct_dependents:
        direct_branch.add(f"[white]{dep}[/white]")

    if report.cascading_dependents:
        cascade_branch = tree.add(f"[bold magenta]Transitive Cascading Dependents ({len(report.cascading_dependents)}):[/bold magenta]")
        for cdep in report.cascading_dependents:
            cascade_branch.add(f"[white]{cdep}[/white]")

    console.print(tree)


@graph_app.command("validate")
def graph_validate(
    command: str = typer.Argument(..., help="Command string or cmdlet to validate (e.g. 'Get-Process -Name -Id' or 'bcdedit.exe /enum')"),
    params: Optional[str] = typer.Option(None, "--params", "-p", help="Explicit comma or space-delimited parameters"),
):
    """Validates command and flags against the Knowledge Graph to prevent hallucinations."""
    from winterm.graph.engine import WindowsKnowledgeGraph
    kg = WindowsKnowledgeGraph()

    tokens = command.strip().split()
    cmd_name = tokens[0] if tokens else ""
    parameters = [t for t in tokens[1:] if t.startswith("-") or t.startswith("/")]

    if params:
        for p in params.replace(",", " ").split():
            clean_p = p.strip()
            if clean_p and clean_p not in parameters:
                parameters.append(clean_p)

    res = kg.validate_command_parameters(cmd_name, parameters)

    if res.is_valid:
        console.print(Panel(
            f"[bold green][OK] Command and all {len(res.valid_parameters)} parameter(s) validated successfully![/bold green]\n"
            f"Command: [cyan]{res.command}[/cyan]\n"
            f"Valid parameters: [white]{', '.join(res.valid_parameters) or 'None specified'}[/white]",
            title="Parameter Hallucination Check Passed",
            border_style="green",
        ))
    else:
        warn_msg = f"[bold red][X] Hallucination / Invalid parameters detected![/bold red]\n"
        warn_msg += f"Command: [cyan]{res.command}[/cyan]\n"
        if res.valid_parameters:
            warn_msg += f"Valid parameters: [green]{', '.join(res.valid_parameters)}[/green]\n"
        if res.unknown_parameters:
            warn_msg += f"Unknown / Invalid parameters: [bold red]{', '.join(res.unknown_parameters)}[/bold red]\n"
        if res.suggestions:
            warn_msg += "\n[bold yellow]Suggestions:[/bold yellow]\n"
            for unk, sug in res.suggestions.items():
                warn_msg += f"  - For '{unk}' did you mean: [bold green]{sug}[/bold green]?\n"

        console.print(Panel(warn_msg, title="Validation Failed", border_style="red"))


@graph_app.command("remedy")
def graph_remedy(
    error_code: str = typer.Argument(..., help="HRESULT, Win32 error, or exception (e.g. 0x80070005, 10048)"),
):
    """Resolves an error signature to an ordered multi-step remediation path."""
    from winterm.graph.engine import WindowsKnowledgeGraph
    kg = WindowsKnowledgeGraph()
    path = kg.find_remediation_chains(error_code)

    if not path:
        console.print(f"[yellow]No graph remediation path registered for '{error_code}'.[/yellow]")
        return

    console.print(Panel(
        f"[bold]Error Code:[/bold] {path.error_code}\n"
        f"[bold]Root Cause:[/bold] {path.root_cause}\n"
        f"[bold]Required Privileges:[/bold] {', '.join(path.required_privileges)}",
        title="Knowledge Graph Error Remediation Chain",
        border_style="cyan",
    ))

    t_steps = Table(title="Ordered Remediation Sequence", border_style="green")
    t_steps.add_column("Step", style="bold yellow")
    t_steps.add_column("Action", style="white")
    t_steps.add_column("Command", style="green")
    t_steps.add_column("Condition / Expected", style="cyan")

    for s in path.remediation_steps:
        cond = s.get("condition") or s.get("expected") or "Unconditional"
        t_steps.add_row(
            str(s.get("step", "-")),
            s.get("action", ""),
            s.get("command", ""),
            str(cond),
        )
    console.print(t_steps)


@graph_app.command("alternatives")
def graph_alternatives(
    command: str = typer.Argument(..., help="Command or cmdlet name (e.g. Stop-Process, reg.exe)"),
):
    """Lists registered equivalent commands across shells and native tools."""
    from winterm.graph.engine import WindowsKnowledgeGraph
    kg = WindowsKnowledgeGraph()
    alts = kg.find_command_alternatives(command)

    if alts:
        console.print(Panel(
            f"[bold]Target Command:[/bold] {command}\n"
            f"[bold green]Registered Alternatives:[/bold green] {', '.join(alts)}",
            title="Command Alternatives",
            border_style="green",
        ))
    else:
        console.print(f"[yellow]No alternative commands cross-linked for '{command}'.[/yellow]")


@graph_app.command("search-intent")
def graph_search_intent(
    query: str = typer.Argument(..., help="Natural language goal or task (e.g. 'find all text files modified')"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results to return"),
):
    """Searches indexed HuggingFace Windows intent corpus (sumit-s-nair/command-dataset)."""
    from winterm.graph.engine import WindowsKnowledgeGraph
    kg = WindowsKnowledgeGraph()
    results = kg.resolve_intent_to_commands(query, top_k=top_k)

    if not results:
        console.print(f"[yellow]No close matching Windows intents found for '{query}'.[/yellow]")
        return

    table = Table(title=f"Matched Windows Intents for '{query}'", border_style="cyan")
    table.add_column("#", style="bold yellow")
    table.add_column("Natural Language Instruction", style="white")
    table.add_column("Concrete Command", style="green")
    table.add_column("Shell", style="magenta")
    table.add_column("Score", style="cyan")

    for i, r in enumerate(results, 1):
        instr_display = escape(r["instruction"][:70] + ("..." if len(r["instruction"]) > 70 else ""))
        cmd_display = escape(r["command"][:60] + ("..." if len(r["command"]) > 60 else ""))
        table.add_row(
            str(i),
            instr_display,
            cmd_display,
            escape(r["shell"]),
            str(r["relevance_score"]),
        )
    console.print(table)


@graph_app.command("docs")
def graph_docs(
    command: str = typer.Argument(..., help="Windows command or executable name (e.g. fsutil, robocopy, bcdedit)"),
):
    """Displays Microsoft command documentation and syntax (IAmSomeone/Windows_command)."""
    from winterm.graph.engine import WindowsKnowledgeGraph
    kg = WindowsKnowledgeGraph()
    docs = kg.get_command_documentation(command)

    if not docs:
        console.print(f"[yellow]No indexed documentation found for '{command}'.[/yellow]")
        return

    console.print(Panel(
        f"[bold cyan]Command:[/bold cyan] {escape(docs['name'])}\n"
        f"[bold]Subsystem:[/bold] {escape(docs['subsystem'])}\n"
        f"[bold]Applies To:[/bold] {escape(docs['applies_to'] or 'Windows Client / Server')}\n\n"
        f"[bold]Description:[/bold]\n{escape(docs['description'] or 'No description recorded.')}",
        title="Official Windows Command Documentation",
        border_style="cyan",
    ))

    if docs["syntax"]:
        t_syn = Table(title="Syntax Patterns", border_style="blue")
        t_syn.add_column("Syntax", style="green")
        for syn in docs["syntax"][:5]:
            t_syn.add_row(escape(syn))
        console.print(t_syn)

    if docs["parameters"]:
        t_par = Table(title=f"Parameters ({len(docs['parameters'])} total)", border_style="green")
        t_par.add_column("Parameter / Switch", style="bold yellow")
        t_par.add_column("Description", style="white")
        for p, d in list(docs["parameters"].items())[:12]:
            t_par.add_row(escape(p), escape(d[:100] + ("..." if len(d) > 100 else "")))
        console.print(t_par)


@graph_app.command("safety")
def graph_safety(
    command: str = typer.Argument(..., help="Command string to inspect for safety (mshojaei77/terminal-command-execution-sft)"),
):
    """Evaluates safety level, privilege risks, and warnings for a command."""
    from winterm.graph.engine import WindowsKnowledgeGraph
    kg = WindowsKnowledgeGraph()
    safety = kg.get_safety_classification(command)

    style = "bold red" if safety["is_dangerous"] else "bold green"
    console.print(Panel(
        f"[bold]Command:[/bold] {escape(command)}\n"
        f"[bold]Safety Classification:[/bold] [{style}]{safety['safety_label'].upper()}[/{style}]\n"
        f"[bold]Skill Category:[/bold] {escape(safety['skill'])}\n"
        f"[bold]Dangerous / High Risk:[/bold] {safety['is_dangerous']}\n"
        f"[bold]Warning / Rationale:[/bold] {escape(safety['warning'] or 'Standard operation; no special risk flagged.')}",
        title="SFT Safety Evaluation",
        border_style="red" if safety["is_dangerous"] else "green",
    ))


@graph_app.command("ingest")
def graph_ingest(
    force: bool = typer.Option(False, "--force", "-f", help="Force re-download from HuggingFace"),
):
    """Ingests and compiles the 3 HuggingFace Windows datasets into local cache."""
    from winterm.graph.hf_ingestor import HuggingFaceIngestor
    console.print("[cyan]Ingesting Windows command datasets from HuggingFace...[/cyan]")
    corpus = HuggingFaceIngestor.load_or_ingest(force_reingest=force)
    console.print(Panel(
        f"[bold green][OK] Ingestion complete![/bold green]\n"
        f"- Commands parsed (IAmSomeone/Windows_command): {len(corpus.get('commands', {}))}\n"
        f"- Natural-language intents (sumit-s-nair/command-dataset): {len(corpus.get('intents', []))}\n"
        f"- Safety rules (mshojaei77/terminal-command-execution-sft): {len(corpus.get('safety_rules', []))}",
        title="HuggingFace Ingestion Summary",
        border_style="green",
    ))


# =============================================================================
# APPLICATION OPERATIONS CLI (FIND, LAUNCH, CLOSE, LEARN)
# =============================================================================
app_cli = typer.Typer(help="Windows Application Discovery, Launching, and Learning.")
app.add_typer(app_cli, name="app")


@app_cli.command("find")
def app_find(
    query: Optional[str] = typer.Argument(None, help="Application name or keyword to search"),
    limit: int = typer.Option(25, "--limit", "-l", help="Maximum applications to return"),
):
    """Finds installed applications across shell:AppsFolder, Start Menu, and Registry."""
    import json
    agent = WinTermAgent()
    res, _, _ = agent.find_applications(query=query, limit=limit)
    if res.exit_code != 0 or not res.stdout:
        console.print(f"[red]Error discovering applications: {escape(res.stderr)}[/red]")
        return

    try:
        apps = json.loads(res.stdout)
        if isinstance(apps, dict):
            apps = [apps]
        table = Table(title=f"Installed Windows Applications (Query: '{query or 'all'}')", border_style="cyan")
        table.add_column("Application Name", style="bold white")
        table.add_column("Type", style="yellow")
        table.add_column("Source", style="magenta")
        table.add_column("Target / ID", style="green")

        for a in apps:
            table.add_row(escape(a.get("Name", "")), a.get("Type", ""), a.get("Source", ""), escape(a.get("Target", "")))
        console.print(table)
    except Exception as ex:
        console.print(res.stdout)


@app_cli.command("launch")
def app_launch(
    target: str = typer.Argument(..., help="Executable path, AUMID, shortcut, or protocol URI"),
    args: Optional[str] = typer.Option(None, "--args", "-a", help="Arguments to pass to application"),
    elevated: bool = typer.Option(False, "--elevated", "-e", help="Launch with administrator privileges"),
):
    """Launches any Windows application (Win32, UWP Store app, or protocol URI)."""
    agent = WinTermAgent()
    console.print(f"[cyan]Launching '{target}'...[/cyan]")
    res, _, _ = agent.launch_application(target=target, arguments=args, elevated=elevated)
    console.print(res.stdout or res.stderr)


@app_cli.command("close")
def app_close(
    target: str = typer.Argument(..., help="Process name, window title, or PID to close"),
    force: bool = typer.Option(False, "--force", "-f", help="Force terminate process immediately"),
):
    """Gracefully closes or forcefully terminates a running application."""
    agent = WinTermAgent()
    console.print(f"[cyan]Closing '{target}' (Force={force})...[/cyan]")
    res, _, _ = agent.close_application(target=target, force=force)
    console.print(res.stdout or res.stderr)


@app_cli.command("learn")
def app_learn(
    target: str = typer.Argument(..., help="Application or command to discover and learn (e.g. ping, ffmpeg, notepad)"),
):
    """Probes local help, parses options, cross-references Knowledge Graph, and synthesizes an operational guide."""
    agent = WinTermAgent()
    console.print(f"[cyan]Probing and learning operational guide for '{target}'...[/cyan]")
    dossier = agent.learn_application(target)

    status_color = "green" if "LEARNED" in dossier["status"] else "yellow"
    console.print(Panel(
        f"[bold]Target:[/bold] {escape(dossier['target'])}\n"
        f"[bold]Status:[/bold] [{status_color}]{dossier['status']}[/{status_color}]\n"
        f"[bold]Mode:[/bold] {dossier['mode']}\n"
        f"[bold]Synopsis:[/bold] {escape(dossier['synopsis'])}\n"
        f"[bold]Operational Summary:[/bold] {escape(dossier['operational_summary'])}",
        title=f"Application Learning Dossier: {target}",
        border_style=status_color,
    ))

    if dossier["options"]:
        t_opt = Table(title=f"Discovered CLI Options ({len(dossier['options'])} total)", border_style="cyan")
        t_opt.add_column("Flag / Switch", style="bold yellow")
        t_opt.add_column("Description", style="white")
        for opt in dossier["options"][:15]:
            t_opt.add_row(escape(opt["flag"]), escape(opt["description"][:100]))
        console.print(t_opt)

    if dossier["web_learning"]["search_queries"]:
        console.print(Panel(
            "\n".join(f"- {q}" for q in dossier["web_learning"]["search_queries"]),
            title="External / Web Documentation Queries",
            border_style="blue",
        ))


# =============================================================================
# WINDOW MANAGEMENT CLI (LIST, FOCUS, RESIZE, STATE, CLOSE)
# =============================================================================
window_cli = typer.Typer(help="Windows Top-Level Window Management.")
app.add_typer(window_cli, name="window")


@window_cli.command("list")
def window_list(
    query: Optional[str] = typer.Argument(None, help="Filter by window title or process name"),
):
    """Lists visible top-level windows with title, PID, handle, bounds, and state."""
    import json
    agent = WinTermAgent()
    res, _, _ = agent.list_windows(query=query)
    if res.exit_code != 0 or not res.stdout:
        console.print(f"[red]Error listing windows: {escape(res.stderr)}[/red]")
        return

    try:
        windows = json.loads(res.stdout)
        if isinstance(windows, dict):
            windows = [windows]
        table = Table(title=f"Visible Application Windows (Filter: '{query or 'all'}')", border_style="cyan")
        table.add_column("Handle (HWND)", style="bold cyan")
        table.add_column("Process", style="yellow")
        table.add_column("Title", style="bold white")
        table.add_column("Bounds (XxY WxH)", style="green")
        table.add_column("State", style="magenta")

        for w in windows:
            table.add_row(
                str(w.get("Handle", "")),
                escape(w.get("ProcessName", "")),
                escape(w.get("Title", "")),
                f"{w.get('X')},{w.get('Y')} ({w.get('Width')}x{w.get('Height')})",
                w.get("State", ""),
            )
        console.print(table)
    except Exception:
        console.print(res.stdout)


@window_cli.command("focus")
def window_focus(
    identifier: str = typer.Argument(..., help="Window title, process name, or HWND to focus"),
):
    """Brings an application window to the foreground and restores it if minimized."""
    agent = WinTermAgent()
    console.print(f"[cyan]Focusing window '{identifier}'...[/cyan]")
    res, _, _ = agent.focus_window(identifier=identifier)
    console.print(res.stdout or res.stderr)


@window_cli.command("resize")
def window_resize(
    identifier: str = typer.Argument(..., help="Window title, process name, or HWND"),
    x: int = typer.Argument(..., help="Screen X coordinate"),
    y: int = typer.Argument(..., help="Screen Y coordinate"),
    width: int = typer.Argument(..., help="Window width in pixels"),
    height: int = typer.Argument(..., help="Window height in pixels"),
):
    """Repositions and resizes an application window."""
    agent = WinTermAgent()
    console.print(f"[cyan]Resizing window '{identifier}' to {width}x{height} at ({x}, {y})...[/cyan]")
    res, _, _ = agent.resize_window(identifier, x, y, width, height)
    console.print(res.stdout or res.stderr)


@window_cli.command("close")
def window_close(
    identifier: str = typer.Argument(..., help="Window title, process name, or HWND"),
):
    """Sends native Win32 WM_CLOSE message to gracefully close an application window."""
    agent = WinTermAgent()
    console.print(f"[cyan]Closing window '{identifier}'...[/cyan]")
    res, _, _ = agent.close_window(identifier)
    console.print(res.stdout or res.stderr)



# =============================================================================
# INPUT & UI AUTOMATION CLI (TYPE, HOTKEY, CLICK, DRAG, INSPECT)
# =============================================================================
input_cli = typer.Typer(help="Keyboard, Mouse, and UI Automation Control.")
app.add_typer(input_cli, name="input")


@input_cli.command("type")
def input_type(
    text: str = typer.Argument(..., help="Text string to type via SendKeys"),
    interval: int = typer.Option(10, "--interval", "-i", help="Delay between keystrokes in ms"),
):
    """Types keyboard text into active window."""
    agent = WinTermAgent()
    res, _, _ = agent.type_text(text, interval_ms=interval)
    console.print(res.stdout or res.stderr)


@input_cli.command("hotkey")
def input_hotkey(
    keys: List[str] = typer.Argument(..., help="Key sequence (e.g. ctrl c, win r, alt f4)"),
):
    """Simulates pressing a keyboard hotkey or key combination."""
    agent = WinTermAgent()
    res, _, _ = agent.press_hotkey(keys)
    console.print(res.stdout or res.stderr)


@input_cli.command("click")
def input_click(
    x: int = typer.Argument(..., help="Screen X coordinate"),
    y: int = typer.Argument(..., help="Screen Y coordinate"),
    button: str = typer.Option("left", "--button", "-b", help="Mouse button (left, right, middle)"),
    double: bool = typer.Option(False, "--double", "-d", help="Double click"),
):
    """Moves mouse and clicks at specified coordinates."""
    agent = WinTermAgent()
    res, _, _ = agent.mouse_click(x, y, button=button, double=double)
    console.print(res.stdout or res.stderr)


@input_cli.command("drag")
def input_drag(
    start_x: int = typer.Argument(..., help="Start X coordinate"),
    start_y: int = typer.Argument(..., help="Start Y coordinate"),
    end_x: int = typer.Argument(..., help="End X coordinate"),
    end_y: int = typer.Argument(..., help="End Y coordinate"),
):
    """Drags mouse from start coordinates to end coordinates."""
    agent = WinTermAgent()
    res, _, _ = agent.mouse_drag(start_x, start_y, end_x, end_y)
    console.print(res.stdout or res.stderr)


@input_cli.command("inspect")
def input_inspect(
    window: str = typer.Argument(..., help="Target window title, process name, or HWND to inspect"),
    max_items: int = typer.Option(50, "--limit", "-l", help="Max UI elements to return"),
):
    """Inspects UI Automation elements (buttons, edits, menus) in a window."""
    import json
    agent = WinTermAgent()
    res, _, _ = agent.inspect_window_elements(window, max_items=max_items)
    if res.exit_code != 0 or not res.stdout:
        console.print(f"[red]Error inspecting UI elements: {escape(res.stderr)}[/red]")
        return


    try:
        data = json.loads(res.stdout)
        elements = data.get("Elements", [])
        table = Table(title=f"UI Elements in '{data.get('WindowTitle')}' ({len(elements)} items)", border_style="cyan")
        table.add_column("Control Type", style="bold yellow")
        table.add_column("Name", style="bold white")
        table.add_column("AutomationId", style="green")
        table.add_column("Center (X, Y)", style="cyan")

        for el in elements:
            cx = el.get("CenterX")
            cy = el.get("CenterY")
            center_str = f"({cx}, {cy})" if cx is not None and cy is not None else "-"
            table.add_row(el.get("ControlType", ""), escape(el.get("Name", "")), escape(el.get("AutomationId", "")), center_str)
        console.print(table)
    except Exception:
        console.print(res.stdout)


# =============================================================================
# SCREEN PERCEPTION & CAPTURE CLI (STATE, CAPTURE)
# =============================================================================
screen_cli = typer.Typer(help="Live Screen Perception & Visual Capture Control.")
app.add_typer(screen_cli, name="screen")


@screen_cli.command("state")
def screen_state():
    """Queries live display resolution, active cursor position, and foreground window info."""
    import json
    agent = WinTermAgent()
    res, _, _ = agent.get_screen_state()
    if res.exit_code != 0 or not res.stdout:
        console.print(f"[red]Error querying screen state: {escape(res.stderr)}[/red]")
        return
    try:
        data = json.loads(res.stdout)
        table = Table(title="Interactive Screen State", border_style="cyan")
        table.add_column("Property", style="bold yellow")
        table.add_column("Value", style="bold white")
        table.add_row("Resolution", f"{data.get('ScreenWidth')} x {data.get('ScreenHeight')}")
        table.add_row("Cursor Pos", f"({data.get('CursorX')}, {data.get('CursorY')})")
        table.add_row("Foreground Title", escape(str(data.get('ForegroundTitle') or '')))
        table.add_row("Foreground HWND", str(data.get('ForegroundHWND') or ''))
        console.print(table)
    except Exception:
        console.print(res.stdout)


@screen_cli.command("capture")
def screen_capture(
    output: str = typer.Option("screenshot.png", "--output", "-o", help="Destination PNG file path"),
    window: Optional[str] = typer.Option(None, "--window", "-w", help="Optional window title filter"),
):
    """Captures desktop or window screenshot as PNG."""
    agent = WinTermAgent()
    console.print(f"[cyan]Capturing screen to '{output}'...[/cyan]")
    res, _, _ = agent.capture_screen(output, window_query=window)
    console.print(res.stdout or res.stderr)


if __name__ == "__main__":
    app()



