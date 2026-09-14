"""Encoding Expert: Manages code pages (CP65001, CP1252, CP437) and UTF-8 stream integrity."""

import sys
from typing import Tuple


class EncodingExpert:
    """Solves Windows terminal character encoding pitfalls, byte stream corruption, and code page traps."""

    CODEPAGE_UTF8 = 65001
    CODEPAGE_WINDOWS_1252 = 1252
    CODEPAGE_OEM_US = 437

    @classmethod
    def get_encoding_preamble(cls) -> str:
        """Returns PowerShell preamble to force UTF-8 console output encoding."""
        return (
            "[Console]::InputEncoding = [System.Text.Encoding]::UTF8; "
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
            "$OutputEncoding = [System.Text.Encoding]::UTF8; "
        )

    @classmethod
    def decode_stream(cls, raw_bytes: bytes) -> str:
        """Robustly decodes raw stdout/stderr bytes from a Windows subprocess.
        
        Attempts decoders in priority order:
        1. UTF-8 (Strict)
        2. Windows-1252 (Western European ANSI)
        3. CP437 (Standard US OEM console codepage)
        4. Latin-1 / UTF-8 replacement (Lossless fallback)
        """
        if not raw_bytes:
            return ""

        # Check for UTF-8 Byte Order Mark (BOM)
        if raw_bytes.startswith(b"\xef\xbb\xbf"):
            raw_bytes = raw_bytes[3:]

        # 1. Try UTF-8
        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            pass

        # 2. Try Windows-1252
        try:
            return raw_bytes.decode("cp1252")
        except UnicodeDecodeError:
            pass

        # 3. Try OEM Codepage 437
        try:
            return raw_bytes.decode("cp437")
        except UnicodeDecodeError:
            pass

        # 4. Fallback: UTF-8 with replacement characters
        return raw_bytes.decode("utf-8", errors="replace")

    @classmethod
    def wrap_utf8_redirection(cls, command: str, destination_file: str) -> str:
        """Wraps a native command redirection to guarantee UTF-8 output on PowerShell 5.1.
        
        In Windows PowerShell 5.1, `dotnet > log.txt` writes UTF-16LE, and raw byte
        streams can get mangled. This ensures clean UTF-8 text log files.
        """
        return f"{command} 2>&1 | Out-File -Encoding UTF8 {destination_file}"
