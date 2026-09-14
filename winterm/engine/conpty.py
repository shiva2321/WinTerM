"""ConPTY and Interactive Terminal Utilities: Prompt detection and non-blocking safety."""

import re
from typing import List


class InteractivePromptDetector:
    """Detects whether command output indicates an interactive prompt waiting for user input."""

    PROMPT_PATTERNS: List[re.Pattern] = [
        re.compile(r"\[y/n\]", re.IGNORECASE),
        re.compile(r"\(y/n\)", re.IGNORECASE),
        re.compile(r"Are you sure", re.IGNORECASE),
        re.compile(r"Do you want to continue", re.IGNORECASE),
        re.compile(r"Press any key to continue", re.IGNORECASE),
        re.compile(r"Password:\s*$", re.IGNORECASE),
        re.compile(r"Enter passphrase", re.IGNORECASE),
        re.compile(r"Overwrite \? \(Yes/No/All\)", re.IGNORECASE),
    ]

    @classmethod
    def contains_interactive_prompt(cls, text: str) -> bool:
        """Checks if text contains common CLI interactive prompt strings."""
        if not text:
            return False
        last_lines = "\n".join(text.strip().splitlines()[-3:])
        return any(pattern.search(last_lines) for pattern in cls.PROMPT_PATTERNS)
