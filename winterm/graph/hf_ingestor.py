"""HuggingFace Dataset Ingestor: Extracts, structures, and compiles Windows command corpora."""

import gzip
import json
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

COMPILED_CACHE_PATH = Path(__file__).parent / "datasets" / "hf_compiled.json.gz"


class HuggingFaceIngestor:
    """Ingests, filters, and indexes real Windows command datasets from Hugging Face."""

    DATASET_WINDOWS_COMMANDS = "IAmSomeone/Windows_command"
    DATASET_INTENT_COMMANDS = "sumit-s-nair/command-dataset"
    DATASET_TERMINAL_SFT = "mshojaei77/terminal-command-execution-sft"

    _cached_corpus: Optional[Dict[str, Any]] = None

    @classmethod
    def load_or_ingest(cls, force_reingest: bool = False) -> Dict[str, Any]:
        """Loads precompiled corpus if available, otherwise ingests from Hugging Face datasets."""
        if not force_reingest and cls._cached_corpus is not None:
            return cls._cached_corpus

        if not force_reingest and COMPILED_CACHE_PATH.exists():
            try:
                with gzip.open(COMPILED_CACHE_PATH, "rt", encoding="utf-8") as f:
                    cls._cached_corpus = json.load(f)
                    return cls._cached_corpus
            except Exception:
                pass  # Fall back to live ingestion on corrupt cache

        cls._cached_corpus = cls.ingest_all_and_cache()
        return cls._cached_corpus

    @classmethod
    def ingest_all_and_cache(cls) -> Dict[str, Any]:
        """Performs live ingestion from the 3 Hugging Face datasets and persists to gzip cache."""
        from datasets import load_dataset

        corpus: Dict[str, Any] = {
            "commands": cls._ingest_windows_commands(load_dataset),
            "intents": cls._ingest_intent_commands(load_dataset),
            "safety_rules": cls._ingest_safety_rules(load_dataset),
        }

        # Ensure directory exists
        COMPILED_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(COMPILED_CACHE_PATH, "wt", encoding="utf-8") as f:
            json.dump(corpus, f)

        return corpus

    @classmethod
    def _ingest_windows_commands(cls, load_fn) -> Dict[str, Dict[str, Any]]:
        """Extracts Win32 commands, syntax, and parameter documentation from IAmSomeone/Windows_command."""
        try:
            ds = load_fn(cls.DATASET_WINDOWS_COMMANDS, split="train")
        except Exception as ex:
            return {}

        commands: Dict[str, Dict[str, Any]] = {}
        current_cmd = None
        current_section = None

        for i, row in enumerate(ds):
            text = row.get("text", "").strip()
            if not text:
                continue

            # Command header followed by 'Applies to:'
            if i + 1 < len(ds) and "Applies to:" in ds[i + 1].get("text", ""):
                current_cmd = text.split()[0].lower().rstrip(":")
                applies = ds[i + 1].get("text", "").replace("Applies to:", "").strip()
                desc = ds[i + 2].get("text", "").strip() if i + 2 < len(ds) else ""
                commands[current_cmd] = {
                    "name": current_cmd,
                    "applies_to": applies,
                    "description": desc,
                    "parameters": {},
                    "syntax": [],
                }
                current_section = None
                continue

            if current_cmd:
                if "Syntax" in text:
                    current_section = "syntax"
                    continue
                elif "Parameters" in text:
                    current_section = "params"
                    continue

                if current_section == "syntax":
                    if text.startswith(current_cmd) or text.startswith("["):
                        commands[current_cmd]["syntax"].append(text)
                elif current_section == "params":
                    # Flag token match (e.g. /s, /v, -f)
                    if re.match(r"^(?:/[\w\?:\-]+|-\w+|[\w\-]+)\b", text) and len(text.split()) <= 3:
                        param_token = text
                        param_desc = ""
                        if i + 1 < len(ds) and not re.match(r"^(?:/[\w\?:\-]+|-\w+|[\w\-]+)\b", ds[i + 1].get("text", "")):
                            param_desc = ds[i + 1].get("text", "").strip()
                        commands[current_cmd]["parameters"][param_token] = param_desc

        return commands

    @classmethod
    def _ingest_intent_commands(cls, load_fn, limit: int = 5000) -> List[Dict[str, Any]]:
        """Extracts deduplicated Windows intent-to-command pairs from sumit-s-nair/command-dataset."""
        try:
            ds = load_fn(cls.DATASET_INTENT_COMMANDS, split="train")
        except Exception:
            return []

        intents = []
        seen_instructions = set()

        for row in ds:
            os_val = row.get("os", "")
            sh_val = row.get("shell", "")
            if os_val != "windows" and sh_val not in ("powershell", "cmd"):
                continue

            instr = row.get("instruction", "").strip()
            cmd = row.get("command", "").strip()
            if not instr or not cmd or len(instr) < 5:
                continue

            norm_key = instr.lower()
            if norm_key in seen_instructions:
                continue
            seen_instructions.add(norm_key)

            intents.append({
                "instruction": instr,
                "command": cmd,
                "shell": sh_val or "powershell",
                "intent_type": row.get("intent_type", "others"),
            })

            if len(intents) >= limit:
                break

        return intents

    @classmethod
    def _ingest_safety_rules(cls, load_fn) -> List[Dict[str, Any]]:
        """Extracts safety classification and warnings from mshojaei77/terminal-command-execution-sft."""
        try:
            ds = load_fn(cls.DATASET_TERMINAL_SFT, split="train")
        except Exception:
            return []

        safety_rules = []
        seen = set()

        for row in ds:
            family = row.get("shell_family", "")
            if family not in ("cmd", "powershell", "windows"):
                continue

            safety = row.get("safety_label", "safe")
            skill = row.get("skill", "unknown")
            messages = row.get("messages", [])
            user_msg = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
            asst_msg = next((m.get("content", "") for m in messages if m.get("role") == "assistant"), "")

            warning = ""
            if "Warning:" in asst_msg:
                warn_m = re.search(r"Warning:\s*([^\n]+)", asst_msg)
                if warn_m:
                    warning = warn_m.group(1).strip()

            cmd_lines = [
                l.strip() for l in asst_msg.split("\n")
                if l.strip() and not l.strip().startswith("Warning:") and not l.strip().startswith("@echo off")
            ]
            cmd_sample = cmd_lines[0] if cmd_lines else ""

            key = (user_msg[:60].lower(), safety)
            if key in seen:
                continue
            seen.add(key)

            safety_rules.append({
                "intent_context": user_msg[:140],
                "command_sample": cmd_sample[:120],
                "safety_label": safety,
                "skill": skill,
                "warning": warning,
                "shell_family": family,
            })

        return safety_rules
