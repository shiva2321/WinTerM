"""Dynamic Application & Command Learning Engine for Windows Agents.

Discovers help, parses CLI documentation, cross-references the Windows Knowledge Graph,
and synthesizes operational guides and web search recommendations.
"""

import re
from typing import Dict, Any, List, Optional
from winterm.engine.executor import WindowsShellExecutor
from winterm.graph.engine import WindowsKnowledgeGraph
from winterm.interaction.app_manager import WindowsAppManager


class AppHelpResult(dict):
    """Dictionary that supports both dict indexing and attribute access."""
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'AppHelpResult' object has no attribute '{name}'")


class AppLearner:
    """Discovers how to operate any Windows application or command via local probes and graph reasoning."""

    PROBE_STRATEGIES = [
        # (format_template, shell_type_hint)
        ("{cmd} /?", "cmd"),
        ("Get-Help {cmd} -Detailed", "powershell"),
        ("{cmd} --help", "cli"),
        ("{cmd} -h", "cli"),
        ("help {cmd}", "cmd"),
    ]

    def __init__(
        self,
        executor: Optional[WindowsShellExecutor] = None,
        knowledge_graph: Optional[WindowsKnowledgeGraph] = None,
    ):
        self.executor = executor or WindowsShellExecutor()
        self.kg = knowledge_graph or WindowsKnowledgeGraph()

    def probe_local_help(self, app_or_command: str) -> AppHelpResult:
        """Probes the local system for application help, manuals, or usage syntaxes."""
        cmd = app_or_command.strip()
        best_output = ""
        successful_probe = ""

        # Test each probe strategy in priority order
        for template, probe_type in self.PROBE_STRATEGIES:
            probe_cmd = template.format(cmd=cmd)
            try:
                res = self.executor.execute(probe_cmd, timeout_seconds=4)
                out = (res.stdout or "") + (res.stderr or "")
                # Validate that output is not just an error message or empty
                if len(out.strip()) > 30 and not self._is_command_not_found(out):
                    best_output = out.strip()
                    successful_probe = probe_cmd
                    break
            except Exception:
                continue

        # Check if this is an installed application in shell:AppsFolder or Start Menu
        app_search_res = self.executor.execute(WindowsAppManager.build_search_command(cmd, limit=3))
        is_gui_app = False
        app_details = []
        if app_search_res.exit_code == 0 and app_search_res.stdout:
            import json
            try:
                app_details = json.loads(app_search_res.stdout)
                is_gui_app = len(app_details) > 0
            except Exception:
                pass

        if not best_output:
            return AppHelpResult({
                "success": False,
                "target": cmd,
                "probe_used": None,
                "raw_help": "",
                "options": [],
                "is_gui_app": is_gui_app,
                "app_details": app_details,
            })

        parsed = self.parse_help_text(best_output)
        return AppHelpResult({
            "success": True,
            "target": cmd,
            "probe_used": successful_probe,
            "raw_help": best_output,
            "options": parsed["options"],
            "synopsis": parsed["synopsis"],
            "examples": parsed["examples"],
            "is_gui_app": is_gui_app,
            "app_details": app_details,
        })


    def _is_command_not_found(self, text: str) -> bool:
        """Determines if the output represents a command not found, error, or unhelpful response."""
        lower = text.lower()
        err_markers = [
            "is not recognized as an internal or external command",
            "the term",
            "is not recognized as the name of a cmdlet",
            "cannot find the path specified",
            "no such file or directory",
            "this command is not supported by the help utility",
            "cannot find a provider",
            "cannot find any help files",
            "could not find",
            "helpnotfound",
            "categoryinfo",
            "bad value for option",
            "not found",
        ]
        return any(m in lower for m in err_markers)

    def parse_help_text(self, raw_help: str) -> Dict[str, Any]:
        """Extracts synopsis, parameters/options, subcommands, and examples from help text."""
        lines = [line.rstrip() for line in raw_help.splitlines() if line.strip()]
        synopsis = ""
        options = []
        subcommands = []
        examples = []

        # Find synopsis (lines starting with 'Usage:', 'SYNTAX', or command name)
        for i, line in enumerate(lines):
            lower = line.strip().lower()
            if lower.startswith("usage:") or lower.startswith("syntax:") or lower.startswith("use:"):
                synopsis = line.strip()
                if i + 1 < len(lines) and lines[i + 1].startswith("   "):
                    synopsis += " " + lines[i + 1].strip()
                break

        if not synopsis and lines:
            # Use first non-empty line as brief summary
            synopsis = lines[0]

        # Extract flags and parameters (-x, --xxx, /x, or PowerShell -Param)
        flag_with_desc = re.compile(r"^\s*([/-]{1,2}[a-zA-Z0-9_-]+(?:[ ,/]+[/-]{1,2}[a-zA-Z0-9_-]+)?(?:\s+<[^>]+>)?)\s{2,}(.+)$")
        flag_single_line = re.compile(r"^\s*([/-]{1,2}[a-zA-Z0-9_-]+(?:\s+<[^>]+>)?)\s*$")
        
        seen_flags = set()
        for line in lines:
            m1 = flag_with_desc.match(line)
            if m1:
                opt_flag = m1.group(1).strip()
                opt_desc = m1.group(2).strip()
                if opt_flag.lower() not in seen_flags:
                    seen_flags.add(opt_flag.lower())
                    options.append({"flag": opt_flag, "description": opt_desc})
                continue

            m2 = flag_single_line.match(line)
            if m2:
                opt_flag = m2.group(1).strip()
                if opt_flag.lower() not in seen_flags and not opt_flag.startswith("---"):
                    seen_flags.add(opt_flag.lower())
                    options.append({"flag": opt_flag, "description": ""})
                continue

            if "example" in line.lower() or "examples:" in line.lower():
                examples.append(line.strip())

        return {
            "synopsis": synopsis,
            "options": options[:40],
            "subcommands": subcommands,
            "examples": examples[:10],
        }


    def cross_reference_knowledge_graph(self, app_or_command: str) -> Dict[str, Any]:
        """Cross-references the command with the deterministic Windows Knowledge Graph."""
        cmd_clean = app_or_command.lower().replace(".exe", "")
        alternatives = self.kg.find_command_alternatives(cmd_clean)
        
        # Check if intent matching finds examples
        related_intents = self.kg.resolve_intent_to_commands(app_or_command, top_k=3)

        # Check parameter rules
        graph_command_data = None
        cmd_node_id = f"command:{cmd_clean}"
        if self.kg.graph.has_node(cmd_node_id):
            graph_command_data = dict(self.kg.graph.nodes[cmd_node_id])

        return {
            "is_indexed_in_graph": graph_command_data is not None,
            "graph_node": graph_command_data,
            "alternatives": alternatives,
            "related_tasks": related_intents,
        }

    def generate_web_learning_guidance(self, app_or_command: str, is_gui: bool = False, topic: Optional[str] = None) -> Dict[str, Any]:
        """Synthesizes high-precision search queries to discover online documentation or automation patterns."""
        target = app_or_command.strip()
        queries = [
            f"how to use {target} windows command line arguments documentation",
            f"{target} CLI syntax options examples",
        ]
        if topic:
            queries.append(f"{target} {topic}")
        if is_gui:
            queries.extend([
                f"{target} keyboard shortcuts windows",
                f"automate {target} UI automation powershell",
                f"{target} command line switches silent unattended",
            ])

        return {
            "target": target,
            "search_queries": queries,
            "recommended_queries": queries,
            "recommended_sources": [
                "learn.microsoft.com",
                "ss64.com",
                "github.com",
            ],
            "guidance": (
                f"For {target}, if native CLI help is incomplete, query web documentation using "
                "the generated queries to discover non-interactive flags, configuration files, or keyboard shortcuts."
            ),
        }

    def learn(self, app_or_command: str) -> Dict[str, Any]:
        """Executes full multi-source learning workflow for an application or command."""
        target = app_or_command.strip()
        probe_res = self.probe_local_help(target)
        kg_data = self.cross_reference_knowledge_graph(target)

        if probe_res["success"]:
            parsed = self.parse_help_text(probe_res["raw_help"])
            status = "LEARNED_FROM_LOCAL_HELP"
            mode = "CLI"
            operational_summary = (
                f"Discovered local CLI help via '{probe_res['probe_used']}'. "
                f"Found {len(parsed['options'])} documented options."
            )
        elif probe_res["is_gui_app"]:
            parsed = {"synopsis": f"Windows Graphical Application ({target})", "options": [], "examples": []}
            status = "LEARNED_GUI_APPLICATION"
            mode = "GUI"
            operational_summary = (
                f"Identified as installed Windows GUI application. "
                "Operate via WindowsAppManager (launch/close), WindowManager (focus/resize), "
                "and UIAutomationEngine (inspect/click/type)."
            )
        else:
            parsed = {"synopsis": f"Unindexed or unknown target: {target}", "options": [], "examples": []}
            status = "NEEDS_WEB_RESEARCH"
            mode = "UNKNOWN"
            operational_summary = "No local help or installed GUI match found. Requires web search or verification."

        web_guidance = self.generate_web_learning_guidance(target, is_gui=(mode == "GUI"))

        kg_matches = list(kg_data.get("alternatives", [])) + list(kg_data.get("related_tasks", []))
        if kg_data.get("is_indexed_in_graph"):
            kg_matches.append(kg_data.get("graph_node", {}))

        return {
            "target": target,
            "status": status,
            "mode": mode,
            "operational_summary": operational_summary,
            "synopsis": parsed["synopsis"],
            "options": parsed["options"],
            "examples": parsed["examples"],
            "local_help": {
                "available": probe_res["success"],
                "probe_used": probe_res.get("probe_used"),
                "raw_help": probe_res.get("raw_help", ""),
            },
            "knowledge_graph": kg_data,
            "knowledge_graph_matches": kg_matches,
            "web_learning": web_guidance,
            "web_search_guidance": web_guidance,
            "app_details": probe_res.get("app_details", []),
        }

    # Aliases for convenience
    search_graph_knowledge = cross_reference_knowledge_graph
    generate_web_search_guidance = generate_web_learning_guidance

