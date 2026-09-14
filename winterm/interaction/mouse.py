"""Mouse Automation Engine: Coordinates, clicks, drags, and scrolling via Win32 user32.dll."""

from typing import Optional


class MouseEngine:
    """Manages mouse cursor positioning, clicking, dragging, and wheel scrolling."""

    WIN32_MOUSE_HEADER = (
        "$codeMouse = @'\n"
        "using System;\n"
        "using System.Drawing;\n"
        "using System.Runtime.InteropServices;\n"
        "public class Win32MouseCore {\n"
        "    [StructLayout(LayoutKind.Sequential)]\n"
        "    public struct POINT { public int X; public int Y; }\n"
        "    [DllImport(\"user32.dll\", SetLastError = true)]\n"
        "    public static extern IntPtr OpenDesktop(string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);\n"
        "    [DllImport(\"user32.dll\", SetLastError = true)]\n"
        "    public static extern bool SetThreadDesktop(IntPtr hDesktop);\n"
        "    [DllImport(\"user32.dll\")] public static extern bool SetProcessDPIAware();\n"
        "    [DllImport(\"user32.dll\")] public static extern bool SetCursorPos(int X, int Y);\n"
        "    [DllImport(\"user32.dll\")] public static extern bool GetCursorPos(out POINT lpPoint);\n"
        "    [DllImport(\"user32.dll\")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, int dwExtraInfo);\n"
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
        "    public static void SetPos(int x, int y) {\n"
        "        RunOnDefaultDesktop(() => { SetCursorPos(x, y); });\n"
        "    }\n"
        "\n"
        "    public static void Click(int x, int y, uint downFlag, uint upFlag, int clicks) {\n"
        "        RunOnDefaultDesktop(() => {\n"
        "            if (x >= 0 && y >= 0) {\n"
        "                SetCursorPos(x, y);\n"
        "                System.Threading.Thread.Sleep(30);\n"
        "            }\n"
        "            for (int i = 0; i < clicks; i++) {\n"
        "                mouse_event(downFlag, 0, 0, 0, 0);\n"
        "                System.Threading.Thread.Sleep(40);\n"
        "                mouse_event(upFlag, 0, 0, 0, 0);\n"
        "                System.Threading.Thread.Sleep(50);\n"
        "            }\n"
        "        });\n"
        "    }\n"
        "}\n"
        "'@\n"
        "if (-not ([System.Management.Automation.PSTypeName]'Win32MouseCore').Type) { Add-Type -TypeDefinition $codeMouse };\n"
    )

    # Win32 Mouse Event Flags
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_MIDDLEDOWN = 0x0020
    MOUSEEVENTF_MIDDLEUP = 0x0040
    MOUSEEVENTF_WHEEL = 0x0800
    MOUSEEVENTF_HWHEEL = 0x1000

    @classmethod
    def build_move_command(cls, x: int, y: int, smooth: bool = False, steps: int = 15) -> str:
        """Generates a command to move the mouse cursor to absolute (X, Y) coordinates."""
        script = (
            f"{cls.WIN32_MOUSE_HEADER}"
            f"[Win32MouseCore]::SetPos({x}, {y}); "
            "@{ Action = 'MouseMove'; TargetX = " + str(x) + "; TargetY = " + str(y) + "; Success = $True } | ConvertTo-Json -Compress"
        )
        return script

    @classmethod
    def build_click_command(
        cls,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        clicks: int = 1,
        double: bool = False,
        double_click: bool = False,
    ) -> str:
        """Generates a command to click at optional coordinates or current cursor location."""
        if (double or double_click) and clicks == 1:
            clicks = 2
        btn = button.lower()
        if btn == "right":
            down_flag = cls.MOUSEEVENTF_RIGHTDOWN
            up_flag = cls.MOUSEEVENTF_RIGHTUP
        elif btn in ("middle", "center"):
            down_flag = cls.MOUSEEVENTF_MIDDLEDOWN
            up_flag = cls.MOUSEEVENTF_MIDDLEUP
        else:
            down_flag = cls.MOUSEEVENTF_LEFTDOWN
            up_flag = cls.MOUSEEVENTF_LEFTUP

        px = x if x is not None else -1
        py = y if y is not None else -1

        return (
            f"{cls.WIN32_MOUSE_HEADER}"
            f"[Win32MouseCore]::Click({px}, {py}, 0x{down_flag:04X}, 0x{up_flag:04X}, {clicks}); "
            "@{ Action = 'MouseClick'; Button = '" + button + "'; Clicks = " + str(clicks) + "; X = " + str(px) + "; Y = " + str(py) + "; Success = $True } | ConvertTo-Json -Compress"
        )

    @classmethod
    def build_drag_and_drop_command(
        cls,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        steps: int = 20,
        button: str = "left",
    ) -> str:
        """Generates a command to simulate clicking and dragging between two points."""
        down_flag = cls.MOUSEEVENTF_RIGHTDOWN if button.lower() == "right" else cls.MOUSEEVENTF_LEFTDOWN
        up_flag = cls.MOUSEEVENTF_RIGHTUP if button.lower() == "right" else cls.MOUSEEVENTF_LEFTUP
        return (
            f"{cls.WIN32_MOUSE_HEADER}"
            f"[Win32MouseCore]::SetCursorPos({start_x}, {start_y}) | Out-Null; "
            f"try {{ "
            f"    [Win32MouseCore]::mouse_event(0x{down_flag:04X}, 0, 0, 0, 0); "
            f"    Start-Sleep -Milliseconds 50; "
            f"    $steps = {steps}; "
            f"    for ($i = 1; $i -le $steps; $i++) {{ "
            f"        $curX = [int]({start_x} + (({end_x} - {start_x}) * $i / $steps)); "
            f"        $curY = [int]({start_y} + (({end_y} - {start_y}) * $i / $steps)); "
            f"        [Win32MouseCore]::SetCursorPos($curX, $curY) | Out-Null; "
            f"        Start-Sleep -Milliseconds 10; "
            f"    }} "
            f"}} finally {{ "
            f"    [Win32MouseCore]::mouse_event(0x{up_flag:04X}, 0, 0, 0, 0); "
            f"}} "
            "@{ Action = 'MouseDragAndDrop'; StartX = " + str(start_x) + "; StartY = " + str(start_y) + "; EndX = " + str(end_x) + "; EndY = " + str(end_y) + "; Success = $True } | ConvertTo-Json -Compress"
        )

    @classmethod
    def build_scroll_command(cls, amount: int = 1, horizontal: bool = False, delta: Optional[int] = None) -> str:
        """Generates a command to scroll the mouse wheel (positive for up, negative for down)."""
        flag = cls.MOUSEEVENTF_HWHEEL if horizontal else cls.MOUSEEVENTF_WHEEL
        effective_delta = delta if delta is not None else (amount * 120)
        uint_delta = effective_delta & 0xFFFFFFFF
        return (
            f"{cls.WIN32_MOUSE_HEADER}"
            f"[Win32MouseCore]::mouse_event(0x{flag:04X}, 0, 0, [uint32]{uint_delta}, 0); "
            "@{ Action = 'MouseScroll'; Amount = " + str(amount) + "; Horizontal = " + str(horizontal).lower() + "; Success = $True } | ConvertTo-Json -Compress"
        )


    # Aliases for convenience
    generate_move_cursor = build_move_command
    generate_drag = build_drag_and_drop_command
    generate_scroll = build_scroll_command

    @classmethod
    def generate_click(cls, button: str = "left", double_click: bool = False, x: Optional[int] = None, y: Optional[int] = None, clicks: int = 1) -> str:
        if double_click:
            clicks = 2
        return cls.build_click_command(x=x, y=y, button=button, clicks=clicks)

