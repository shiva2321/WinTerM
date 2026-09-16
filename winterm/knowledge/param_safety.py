"""Parameter Safety: deterministic escaping/validation for shell interpolation.

Subsystem builders compose PowerShell and cmd.exe command strings from
caller-supplied values (rule names, registry paths, service names, package IDs,
file paths, ...). Interpolating those values raw allows command injection and
broken quoting. These helpers are the single, central place where such values
are neutralised before they reach a shell.
"""

from __future__ import annotations

import re
from typing import Any, Optional

_CONTROL_CHARS = re.compile(r"[\r\n\x00]")
_IDENTIFIER = re.compile(r"[^A-Za-z0-9_.\-]")
_PACKAGE_ID = re.compile(r"^[A-Za-z0-9._\-+]+$")
_CMD_METACHARS = set('"&|<>^%')


def _strip_controls(value: str) -> str:
    return _CONTROL_CHARS.sub("", value)


def ps_literal(value: Any) -> str:
    """Returns a safe PowerShell single-quoted string literal.

    Single quotes are doubled (PowerShell's escape) so an embedded ``'; ...``
    cannot terminate the literal and start a new statement.
    """
    s = _strip_controls(str(value))
    return "'" + s.replace("'", "''") + "'"


def ps_scalar(value: Any) -> str:
    """Returns a PowerShell scalar: numbers/bools stay literal, strings are quoted."""
    if isinstance(value, bool):
        return "$true" if value else "$false"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    if re.fullmatch(r"-?\d+", s):
        return s
    return ps_literal(s)


def cmd_quote(value: Any, allow_inner_quotes: bool = False) -> str:
    """Returns a safe cmd.exe double-quoted argument.

    Raises :class:`ValueError` when the value contains characters that can break
    out of quotes (``" & | < > ^ %``). Because cmd.exe has no reliable escape for
    doubled quotes inside arguments, rejecting is safer than mangling.
    """
    s = _strip_controls(str(value))
    bad = _CMD_METACHARS.intersection(s)
    if bad:
        if allow_inner_quotes and bad == {'"'}:
            s = s.replace('"', '\\"')
        else:
            raise ValueError(
                f"Unsafe cmd.exe argument {value!r}: contains {sorted(bad)}"
            )
    return '"' + s + '"'


def safe_identifier(value: Any, fallback: str = "", max_length: int = 128) -> str:
    """Strips everything except ``[A-Za-z0-9_.-]`` (service names, task names, ...)."""
    s = _IDENTIFIER.sub("", _strip_controls(str(value)))[:max_length]
    return s or fallback


def validated_choice(value: Any, allowed: Any, default: str) -> str:
    """Returns ``value`` if it matches one of ``allowed`` (case-insensitive), else ``default``."""
    s = str(value).strip()
    for candidate in allowed:
        if s.lower() == str(candidate).lower():
            return str(candidate)
    return default


def package_id(value: Any) -> str:
    """Validates a winget/choco package identifier."""
    s = str(value).strip()
    if not _PACKAGE_ID.match(s):
        raise ValueError(f"Invalid package identifier {value!r}")
    return s


def int_in_range(value: Any, minimum: int, maximum: int, default: int) -> int:
    """Coerces to int and clamps to ``[minimum, maximum]``."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, n))