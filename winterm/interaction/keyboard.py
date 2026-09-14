"""Keyboard Automation Engine: Synthesizes keystrokes, hotkeys, and text typing for Windows."""

import re
from typing import List, Optional, Any, Union


class KeyboardEngine:
    """Manages keyboard input automation on Windows via System.Windows.Forms.SendKeys and Win32 API."""

    SPECIAL_KEYS = {
        "enter": "{ENTER}",
        "return": "{ENTER}",
        "tab": "{TAB}",
        "esc": "{ESC}",
        "escape": "{ESC}",
        "backspace": "{BACKSPACE}",
        "bksp": "{BACKSPACE}",
        "delete": "{DELETE}",
        "del": "{DELETE}",
        "up": "{UP}",
        "down": "{DOWN}",
        "left": "{LEFT}",
        "right": "{RIGHT}",
        "home": "{HOME}",
        "end": "{END}",
        "pageup": "{PGUP}",
        "pagedown": "{PGDN}",
        "f1": "{F1}", "f2": "{F2}", "f3": "{F3}", "f4": "{F4}",
        "f5": "{F5}", "f6": "{F6}", "f7": "{F7}", "f8": "{F8}",
        "f9": "{F9}", "f10": "{F10}", "f11": "{F11}", "f12": "{F12}",
        "space": " ",
    }

    MODIFIER_MAP = {
        "ctrl": "^",
        "control": "^",
        "shift": "+",
        "alt": "%",
    }

    # Virtual key codes for Win32 keybd_event (used for Windows key combinations)
    VK_CODES = {
        "lwin": 0x5B,
        "rwin": 0x5C,
        "tab": 0x09,
        "enter": 0x0D,
        "escape": 0x1B,
        "space": 0x20,
        "left": 0x25,
        "up": 0x26,
        "right": 0x27,
        "down": 0x28,
        "delete": 0x2E,
    }

    WIN32_KBD_HEADER = (
        "$codeKbd = @'\n"
        "using System;\n"
        "using System.Runtime.InteropServices;\n"
        "public class Win32KbdCore {\n"
        "    [DllImport(\"user32.dll\", SetLastError = true)]\n"
        "    public static extern IntPtr OpenDesktop(string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);\n"
        "    [DllImport(\"user32.dll\", SetLastError = true)]\n"
        "    public static extern bool SetThreadDesktop(IntPtr hDesktop);\n"
        "    [DllImport(\"user32.dll\")] public static extern bool SetProcessDPIAware();\n"
        "    [DllImport(\"user32.dll\")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, int dwExtraInfo);\n"
        "\n"
        "    public static void RunOnDefaultDesktop(Action act) {\n"
        "        var t = new System.Threading.Thread(() => {\n"
        "            try {\n"
        "                SetProcessDPIAware();\n"
        "                IntPtr dDesk = OpenDesktop(\"Default\", 0, false, 0x01FF);\n"
        "                if (dDesk == IntPtr.Zero) dDesk = OpenDesktop(\"default\", 0, false, 0x01FF);\n"
        "                if (dDesk != IntPtr.Zero) SetThreadDesktop(dDesk);\n"
        "            } catch {}\n"
        "            act();\n"
        "        });\n"
        "        t.SetApartmentState(System.Threading.ApartmentState.STA);\n"
        "        t.Start();\n"
        "        t.Join();\n"
        "    }\n"
        "\n"
        "    public static void TypeUnicode(string text, int intervalMs) {\n"
        "        RunOnDefaultDesktop(() => {\n"
        "            foreach (char c in text) {\n"
        "                if (c == '\\r') continue;\n"
        "                if (c == '\\n') {\n"
        "                    keybd_event(0x0D, 0, 0, 0);\n"
        "                    keybd_event(0x0D, 0, 2, 0);\n"
        "                } else {\n"
        "                    keybd_event(0, (byte)c, 0x0004, 0);\n"
        "                    keybd_event(0, (byte)c, 0x0004 | 0x0002, 0);\n"
        "                }\n"
        "                if (intervalMs > 0) System.Threading.Thread.Sleep(intervalMs);\n"
        "            }\n"
        "        });\n"
        "    }\n"
        "\n"
        "    public static void SendHotkey(string mod, byte vk) {\n"
        "        RunOnDefaultDesktop(() => {\n"
        "            bool isCtrl = mod.IndexOf(\"ctrl\", StringComparison.OrdinalIgnoreCase) >= 0;\n"
        "            bool isShift = mod.IndexOf(\"shift\", StringComparison.OrdinalIgnoreCase) >= 0;\n"
        "            bool isAlt = mod.IndexOf(\"alt\", StringComparison.OrdinalIgnoreCase) >= 0;\n"
        "            bool isWin = mod.IndexOf(\"win\", StringComparison.OrdinalIgnoreCase) >= 0;\n"
        "\n"
        "            if (isWin) keybd_event(0x5B, 0, 0, 0);\n"
        "            if (isCtrl) keybd_event(0x11, 0, 0, 0);\n"
        "            if (isShift) keybd_event(0x10, 0, 0, 0);\n"
        "            if (isAlt) keybd_event(0x12, 0, 0, 0);\n"
        "\n"
        "            keybd_event(vk, 0, 0, 0);\n"
        "            System.Threading.Thread.Sleep(50);\n"
        "            keybd_event(vk, 0, 2, 0);\n"
        "\n"
        "            if (isAlt) keybd_event(0x12, 0, 2, 0);\n"
        "            if (isShift) keybd_event(0x10, 0, 2, 0);\n"
        "            if (isCtrl) keybd_event(0x11, 0, 2, 0);\n"
        "            if (isWin) keybd_event(0x5B, 0, 2, 0);\n"
        "        });\n"
        "    }\n"
        "\n"
        "    public static void PressKey(byte vk, int count) {\n"
        "        RunOnDefaultDesktop(() => {\n"
        "            for (int i = 0; i < count; i++) {\n"
        "                keybd_event(vk, 0, 0, 0);\n"
        "                keybd_event(vk, 0, 2, 0);\n"
        "                if (count > 1) System.Threading.Thread.Sleep(30);\n"
        "            }\n"
        "        });\n"
        "    }\n"
        "}\n"
        "'@\n"
        "if (-not ([System.Management.Automation.PSTypeName]'Win32KbdCore').Type) { Add-Type -TypeDefinition $codeKbd };\n"
    )

    @classmethod
    def escape_for_sendkeys(cls, text: str) -> str:
        """Escapes reserved characters in SendKeys (+, ^, %, ~, (, ), {, })."""
        return re.sub(r"([+^%~(){}])", r"{\1}", text)

    @classmethod
    def build_type_text_command(cls, text: str, delay_ms: int = 15, interval_ms: Optional[int] = None) -> str:
        """Generates a PowerShell command to type text using native Win32 Unicode keybd_event simulation."""
        effective_delay = interval_ms if interval_ms is not None else delay_ms
        ps_escaped = text.replace("'", "''")
        return (
            f"{cls.WIN32_KBD_HEADER}"
            f"[Win32KbdCore]::TypeUnicode('{ps_escaped}', {effective_delay}); "
            "@{ Action = 'TypeText'; Length = " + str(len(text)) + "; Success = $True } | ConvertTo-Json -Compress"
        )

    @classmethod
    def build_hotkey_command(cls, modifiers: Any, key: Optional[str] = None) -> str:
        """Generates a PowerShell command to send a key combination via native Win32 keybd_event."""
        if isinstance(modifiers, str):
            mods = [modifiers]
        elif isinstance(modifiers, (list, tuple)):
            mods = list(modifiers)
        else:
            mods = []

        if key is None:
            if not mods:
                return "@{ Action = 'EmptyHotkey'; Success = $False } | ConvertTo-Json -Compress"
            target_key = mods.pop()
        else:
            target_key = key

        lower_mods = [m.lower().strip() for m in mods]
        lower_key = target_key.lower().strip()
        mod_str = "+".join(lower_mods)

        # Look up virtual key code
        vk_code = cls.VK_CODES.get(lower_key)
        if vk_code is None:
            if len(lower_key) == 1:
                vk_code = ord(lower_key.upper())
            else:
                vk_code = 0

        return (
            f"{cls.WIN32_KBD_HEADER}"
            f"[Win32KbdCore]::SendHotkey('{mod_str}', {vk_code}); "
            "@{ Action = 'SendHotkey'; Sequence = '" + mod_str + "+" + target_key + "'; Success = $True } | ConvertTo-Json -Compress"
        )

    @classmethod
    def build_press_key_command(cls, key: str, count: int = 1) -> str:
        """Generates a PowerShell command to press a specific key one or multiple times."""
        lower_k = key.lower().strip()
        send_key = cls.SPECIAL_KEYS.get(lower_k, cls.escape_for_sendkeys(key))
        if count > 1:
            if send_key.startswith("{") and send_key.endswith("}"):
                base = send_key[1:-1]
                send_str = f"{{{base} {count}}}"
            else:
                send_str = send_key * count
        else:
            send_str = send_key

        return (
            f"{cls.WIN32_KBD_HEADER}"
            f"[System.Windows.Forms.SendKeys]::SendWait('{send_str}'); "
            "@{ Action = 'PressKey'; Key = '" + key + "'; Count = " + str(count) + "; Success = $True } | ConvertTo-Json -Compress"
        )

    # Aliases for convenience
    build_type_command = build_type_text_command
    escape_sendkeys = escape_for_sendkeys
    generate_type_text = build_type_text_command

    @classmethod
    def generate_win_hotkey(cls, key: str) -> str:
        return cls.build_hotkey_command(["win"], key)

    @classmethod
    def generate_sendkeys_hotkey(cls, keys: str) -> str:
        return cls.build_hotkey_command([keys])

