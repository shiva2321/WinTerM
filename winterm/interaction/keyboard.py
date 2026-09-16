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
        "win": 0x5B,
        "windows": 0x5B,
        "tab": 0x09,
        "enter": 0x0D,
        "return": 0x0D,
        "escape": 0x1B,
        "esc": 0x1B,
        "space": 0x20,
        "backspace": 0x08,
        "bksp": 0x08,
        "left": 0x25,
        "up": 0x26,
        "right": 0x27,
        "down": 0x28,
        "delete": 0x2E,
        "del": 0x2E,
        "home": 0x24,
        "end": 0x23,
        "pageup": 0x21,
        "pagedown": 0x22,
    }

    WIN32_KBD_HEADER = (
        "$codeKbd = @'\n"
        "using System;\n"
        "using System.Runtime.InteropServices;\n"
        "public class Win32KbdCore {\n"
        "    [StructLayout(LayoutKind.Sequential)]\n"
        "    public struct KEYBDINPUT { public ushort wVk; public ushort wScan; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }\n"
        "    [StructLayout(LayoutKind.Sequential)]\n"
        "    public struct MOUSEINPUT { public int dx; public int dy; public uint mouseData; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }\n"
        "    [StructLayout(LayoutKind.Sequential)]\n"
        "    public struct HARDWAREINPUT { public uint uMsg; public ushort wParamL; public ushort wParamH; }\n"
        "    [StructLayout(LayoutKind.Explicit)]\n"
        "    public struct InputUnion { [FieldOffset(0)] public MOUSEINPUT mi; [FieldOffset(0)] public KEYBDINPUT ki; [FieldOffset(0)] public HARDWAREINPUT hi; }\n"
        "    [StructLayout(LayoutKind.Sequential)]\n"
        "    public struct INPUT { public uint type; public InputUnion U; }\n"
        "\n"
        "    private const uint INPUT_KEYBOARD = 1;\n"
        "    private const uint KEYEVENTF_UNICODE = 0x0004;\n"
        "    private const uint KEYEVENTF_KEYUP = 0x0002;\n"
        "\n"
        "    [DllImport(\"user32.dll\", SetLastError = true)]\n"
        "    public static extern IntPtr OpenDesktop(string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);\n"
        "    [DllImport(\"user32.dll\", SetLastError = true)]\n"
        "    public static extern bool SetThreadDesktop(IntPtr hDesktop);\n"
        "    [DllImport(\"user32.dll\", SetLastError = true)]\n"
        "    public static extern bool CloseDesktop(IntPtr hDesktop);\n"
        "    [DllImport(\"user32.dll\")] public static extern bool SetProcessDPIAware();\n"
        "    [DllImport(\"user32.dll\")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, int dwExtraInfo);\n"
        "    [DllImport(\"user32.dll\", SetLastError = true)]\n"
        "    public static extern uint SendInput(uint nInputs, [MarshalAs(UnmanagedType.LPArray), In] INPUT[] pInputs, int cbSize);\n"
        "\n"
        "    public static void RunOnDefaultDesktop(Action act) {\n"
        "        var t = new System.Threading.Thread(() => {\n"
        "            IntPtr dDesk = IntPtr.Zero;\n"
        "            try {\n"
        "                SetProcessDPIAware();\n"
        "                dDesk = OpenDesktop(\"Default\", 0, false, 0x01FF);\n"
        "                if (dDesk == IntPtr.Zero) dDesk = OpenDesktop(\"default\", 0, false, 0x01FF);\n"
        "                if (dDesk != IntPtr.Zero) SetThreadDesktop(dDesk);\n"
        "            } catch {}\n"
        "            try { act(); }\n"
        "            finally { if (dDesk != IntPtr.Zero) { try { CloseDesktop(dDesk); } catch {} } }\n"
        "        });\n"
        "        t.SetApartmentState(System.Threading.ApartmentState.STA);\n"
        "        t.Start();\n"
        "        t.Join();\n"
        "    }\n"
        "\n"
        "    private static INPUT UnicodeInput(char c, bool keyUp) {\n"
        "        var inp = new INPUT();\n"
        "        inp.type = INPUT_KEYBOARD;\n"
        "        inp.U.ki.wVk = 0;\n"
        "        inp.U.ki.wScan = (ushort)c;\n"
        "        inp.U.ki.dwFlags = KEYEVENTF_UNICODE | (keyUp ? KEYEVENTF_KEYUP : 0);\n"
        "        inp.U.ki.dwExtraInfo = IntPtr.Zero;\n"
        "        return inp;\n"
        "    }\n"
        "\n"
        "    private static INPUT VkInput(ushort vk, bool keyUp) {\n"
        "        var inp = new INPUT();\n"
        "        inp.type = INPUT_KEYBOARD;\n"
        "        inp.U.ki.wVk = vk;\n"
        "        inp.U.ki.wScan = 0;\n"
        "        inp.U.ki.dwFlags = keyUp ? KEYEVENTF_KEYUP : 0;\n"
        "        inp.U.ki.dwExtraInfo = IntPtr.Zero;\n"
        "        return inp;\n"
        "    }\n"
        "\n"
        "    // Types Unicode text via SendInput -- the API Microsoft documents as\n"
        "    // supporting KEYEVENTF_UNICODE. The legacy keybd_event() function does\n"
        "    // NOT document support for that flag; using it there is undefined\n"
        "    // behavior and was observed to crash/kill modern (WinUI3) apps such as\n"
        "    // the Windows 11 Notepad during real-world testing.\n"
        "    public static void TypeUnicode(string text, int intervalMs) {\n"
        "        RunOnDefaultDesktop(() => {\n"
        "            int cb = Marshal.SizeOf(typeof(INPUT));\n"
        "            if (intervalMs <= 0) {\n"
        "                // Fast path: batch the whole string into one SendInput call.\n"
        "                var batch = new System.Collections.Generic.List<INPUT>(text.Length * 2);\n"
        "                foreach (char c in text) {\n"
        "                    if (c == '\\r') continue;\n"
        "                    if (c == '\\n') {\n"
        "                        batch.Add(VkInput(0x0D, false));\n"
        "                        batch.Add(VkInput(0x0D, true));\n"
        "                    } else {\n"
        "                        batch.Add(UnicodeInput(c, false));\n"
        "                        batch.Add(UnicodeInput(c, true));\n"
        "                    }\n"
        "                }\n"
        "                if (batch.Count > 0) {\n"
        "                    var arr = batch.ToArray();\n"
        "                    SendInput((uint)arr.Length, arr, cb);\n"
        "                }\n"
        "            } else {\n"
        "                // Paced path: send each character as its own down/up pair with\n"
        "                // a delay in between, for apps that need time to react per key.\n"
        "                foreach (char c in text) {\n"
        "                    if (c == '\\r') continue;\n"
        "                    INPUT[] pair = (c == '\\n')\n"
        "                        ? new INPUT[] { VkInput(0x0D, false), VkInput(0x0D, true) }\n"
        "                        : new INPUT[] { UnicodeInput(c, false), UnicodeInput(c, true) };\n"
        "                    SendInput((uint)pair.Length, pair, cb);\n"
        "                    System.Threading.Thread.Sleep(intervalMs);\n"
        "                }\n"
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
        tokens = []
        if isinstance(modifiers, str):
            raw_list = [modifiers]
        elif isinstance(modifiers, (list, tuple)):
            raw_list = list(modifiers)
        else:
            raw_list = []

        for item in raw_list:
            if item:
                tokens.extend([p.strip() for p in re.split(r'[\+\-\s]+', str(item)) if p.strip()])

        if key is not None:
            tokens.extend([p.strip() for p in re.split(r'[\+\-\s]+', str(key)) if p.strip()])

        if not tokens:
            return "@{ Action = 'EmptyHotkey'; Success = $False } | ConvertTo-Json -Compress"

        target_key = tokens.pop()
        mods = tokens

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
            "Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue; "
            f"[System.Windows.Forms.SendKeys]::SendWait('{send_str}'); "
            "@{ Action = 'PressKey'; Key = '" + key + "'; Count = " + str(count) + "; Success = $True } | ConvertTo-Json -Compress"
        )

    @classmethod
    def build_type_with_clear_command(cls, text: str, delay_ms: int = 15, interval_ms: Optional[int] = None) -> str:
        """Clears existing content via Ctrl+A and Backspace, then types replacement text using SendInput."""
        effective_delay = interval_ms if interval_ms is not None else delay_ms
        ps_escaped = text.replace("'", "''")
        return (
            f"{cls.WIN32_KBD_HEADER}"
            # Send Ctrl+A then Backspace. SendHotkey's C# signature is
            # (string mod, byte vk); the previous six-argument call could never
            # bind and aborted the whole script.
            "[Win32KbdCore]::SendHotkey('ctrl', 0x41);\n"
            "Start-Sleep -Milliseconds 60;\n"
            "[Win32KbdCore]::PressKey(0x08, 1);\n"
            "Start-Sleep -Milliseconds 60;\n"
            f"[Win32KbdCore]::TypeUnicode('{ps_escaped}', {effective_delay});\n"
            f"@{{ Action = 'TypeWithClear'; Length = {len(text)}; Success = $True }} | ConvertTo-Json -Compress"
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


