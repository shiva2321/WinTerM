"""Mouse Automation Engine: Coordinates, clicks, drags, and scrolling via Win32 user32.dll.

Window-scoped clicking (ClickInWindow) uses relative coordinates and validates via
WindowFromPoint that the intended HWND owns the pixel before firing — preventing silent
misdelivery to overlapping windows.
"""

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
        "    [DllImport(\"user32.dll\", SetLastError = true)]\n"
        "    public static extern IntPtr OpenInputDesktop(uint dwFlags, bool fInherit, uint dwDesiredAccess);\n"
        "    [DllImport(\"user32.dll\", SetLastError = true)]\n"
        "    public static extern bool CloseDesktop(IntPtr hDesktop);\n"
        "    [DllImport(\"user32.dll\")] public static extern bool SetProcessDPIAware();\n"
        "    [DllImport(\"user32.dll\")] public static extern bool SetCursorPos(int X, int Y);\n"
        "    [DllImport(\"user32.dll\")] public static extern bool GetCursorPos(out POINT lpPoint);\n"
        "    [DllImport(\"user32.dll\")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, int dwExtraInfo);\n"
        "    [DllImport(\"user32.dll\", SetLastError = true)] public static extern IntPtr WindowFromPoint(POINT pt);\n"
        "    [DllImport(\"user32.dll\", SetLastError = true)] public static extern IntPtr GetAncestor(IntPtr hWnd, uint gaFlags);\n"
        "    [StructLayout(LayoutKind.Sequential)]\n"
        "    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }\n"
        "    [DllImport(\"user32.dll\", SetLastError = true)] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);\n"
        "    [DllImport(\"user32.dll\")] public static extern bool IsChild(IntPtr hWndParent, IntPtr hWnd);\n"
        "\n"
        "    public static void RunOnDefaultDesktop(Action act) {\n"
        "        var t = new System.Threading.Thread(() => {\n"
        "            IntPtr desk = IntPtr.Zero;\n"
        "            try {\n"
        "                SetProcessDPIAware();\n"
        "                desk = OpenInputDesktop(0, false, 0x01FF);\n"
        "                if (desk == IntPtr.Zero) desk = OpenDesktop(\"Default\", 0, false, 0x01FF);\n"
        "                if (desk == IntPtr.Zero) desk = OpenDesktop(\"default\", 0, false, 0x01FF);\n"
        "                if (desk != IntPtr.Zero) SetThreadDesktop(desk);\n"
        "            } catch {}\n"
        "            try {\n"
        "                act();\n"
        "            } finally {\n"
        "                if (desk != IntPtr.Zero) CloseDesktop(desk);\n"
        "            }\n"
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
        "\n"
        "    public static void Drag(int startX, int startY, int endX, int endY, int steps, uint downFlag, uint upFlag) {\n"
        "        RunOnDefaultDesktop(() => {\n"
        "            SetCursorPos(startX, startY);\n"
        "            try {\n"
        "                mouse_event(downFlag, 0, 0, 0, 0);\n"
        "                System.Threading.Thread.Sleep(50);\n"
        "                int n = steps > 0 ? steps : 1;\n"
        "                for (int i = 1; i <= n; i++) {\n"
        "                    int curX = startX + (endX - startX) * i / n;\n"
        "                    int curY = startY + (endY - startY) * i / n;\n"
        "                    SetCursorPos(curX, curY);\n"
        "                    System.Threading.Thread.Sleep(10);\n"
        "                }\n"
        "            } finally {\n"
        "                mouse_event(upFlag, 0, 0, 0, 0);\n"
        "            }\n"
        "        });\n"
        "    }\n"
        "\n"
        "    public static void Scroll(uint flag, uint delta) {\n"
        "        RunOnDefaultDesktop(() => { mouse_event(flag, 0, 0, delta, 0); });\n"
        "    }\n"
        "\n"
        "    /// <summary>\n"
        "    /// Click at window-relative coordinates (relX, relY) inside hWnd.\n"
        "    /// Validates via WindowFromPoint that the pixel belongs to hWnd before firing.\n"
        "    /// Returns diagnostic info as a serialisable struct.\n"
        "    /// </summary>\n"
        "    public struct ClickInWindowResult {\n"
        "        public bool Success;\n"
        "        public bool ClickedInCorrectWindow;\n"
        "        public int AbsX;\n"
        "        public int AbsY;\n"
        "        public long TargetHwnd;\n"
        "        public long ActualHwnd;\n"
        "        public string Error;\n"
        "    }\n"
        "    public static ClickInWindowResult ClickInWindow(IntPtr hWnd, int relX, int relY, uint downFlag, uint upFlag, int clicks) {\n"
        "        var result = new ClickInWindowResult { TargetHwnd = hWnd.ToInt64() };\n"
        "        RunOnDefaultDesktop(() => {\n"
        "            try {\n"
        "                // Get current window screen rect\n"
        "                RECT winRect;\n"
        "                if (!GetWindowRect(hWnd, out winRect)) {\n"
        "                    result.Error = \"GetWindowRect failed\";\n"
        "                    return;\n"
        "                }\n"
        "                int absX = winRect.Left + relX;\n"
        "                int absY = winRect.Top + relY;\n"
        "                result.AbsX = absX;\n"
        "                result.AbsY = absY;\n"
        "                // Validate: is the pixel at (absX, absY) owned by our target window?\n"
        "                var pt = new POINT { X = absX, Y = absY };\n"
        "                IntPtr hitWnd = WindowFromPoint(pt);\n"
        "                // Walk up to top-level ancestor (child controls count as same window)\n"
        "                IntPtr ancestor = GetAncestor(hitWnd, 2); // GA_ROOT = 2\n"
        "                if (ancestor == IntPtr.Zero) ancestor = hitWnd;\n"
        "                result.ActualHwnd = ancestor.ToInt64();\n"
        "                result.ClickedInCorrectWindow = (ancestor == hWnd || hitWnd == hWnd || IsChild(hWnd, hitWnd) || (ancestor != IntPtr.Zero && IsChild(hWnd, ancestor)));\n"
        "                if (!result.ClickedInCorrectWindow) {\n"
        "                    result.Error = string.Format(\"WindowFromPoint({0},{1}) returned HWND={2} not target HWND={3}\",\n"
        "                        absX, absY, ancestor.ToInt64(), hWnd.ToInt64());\n"
        "                    result.Success = false;\n"
        "                    return;\n"
        "                }\n"
        "                // Safe to click\n"
        "                SetCursorPos(absX, absY);\n"
        "                System.Threading.Thread.Sleep(50);\n"
        "                for (int i = 0; i < clicks; i++) {\n"
        "                    mouse_event(downFlag, 0, 0, 0, 0);\n"
        "                    System.Threading.Thread.Sleep(40);\n"
        "                    mouse_event(upFlag, 0, 0, 0, 0);\n"
        "                    System.Threading.Thread.Sleep(50);\n"
        "                }\n"
        "                result.Success = true;\n"
        "            } catch (Exception ex) {\n"
        "                result.Error = ex.Message;\n"
        "                result.Success = false;\n"
        "            }\n"
        "        });\n"
        "        return result;\n"
        "    }\n"
        "    public static void MoveSmooth(int startX, int startY, int endX, int endY, int steps) {\n"
        "        RunOnDefaultDesktop(() => {\n"
        "            int n = steps > 5 ? steps : 20;\n"
        "            // Generate intermediate control points for natural Bezier curvature\n"
        "            int ctrlX = (startX + endX) / 2 + (new Random()).Next(-30, 30);\n"
        "            int ctrlY = (startY + endY) / 2 + (new Random()).Next(-30, 30);\n"
        "\n"
        "            for (int i = 1; i <= n; i++) {\n"
        "                float t = (float)i / n;\n"
        "                // Cubic Bezier easing (P0, P1, P2)\n"
        "                float u = 1.0f - t;\n"
        "                float tt = t * t;\n"
        "                float uu = u * u;\n"
        "                int curX = (int)(uu * startX + 2 * u * t * ctrlX + tt * endX);\n"
        "                int curY = (int)(uu * startY + 2 * u * t * ctrlY + tt * endY);\n"
        "                SetCursorPos(curX, curY);\n"
        "                System.Threading.Thread.Sleep(8);\n"
        "            }\n"
        "            SetCursorPos(endX, endY);\n"
        "        });\n"
        "    }\n"
        "\n"
        "    public static void MoveSmoothFromCurrent(int endX, int endY, int steps) {\n"
        "        RunOnDefaultDesktop(() => {\n"
        "            POINT p; GetCursorPos(out p);\n"
        "            int startX = p.X; int startY = p.Y;\n"
        "            int n = steps > 5 ? steps : 20;\n"
        "            int ctrlX = (startX + endX) / 2 + (new Random()).Next(-30, 30);\n"
        "            int ctrlY = (startY + endY) / 2 + (new Random()).Next(-30, 30);\n"
        "            for (int i = 1; i <= n; i++) {\n"
        "                float t = (float)i / n; float u = 1.0f - t;\n"
        "                int curX = (int)(u * u * startX + 2 * u * t * ctrlX + t * t * endX);\n"
        "                int curY = (int)(u * u * startY + 2 * u * t * ctrlY + t * t * endY);\n"
        "                SetCursorPos(curX, curY);\n"
        "                System.Threading.Thread.Sleep(8);\n"
        "            }\n"
        "            SetCursorPos(endX, endY);\n"
        "        });\n"
        "    }\n"
        "\n"
        "    public static ClickInWindowResult HoverInWindow(IntPtr hWnd, int relX, int relY, int dwellMs) {\n"
        "        var result = new ClickInWindowResult { TargetHwnd = hWnd.ToInt64() };\n"
        "        RunOnDefaultDesktop(() => {\n"
        "            try {\n"
        "                RECT winRect;\n"
        "                if (!GetWindowRect(hWnd, out winRect)) {\n"
        "                    result.Error = \"GetWindowRect failed\";\n"
        "                    return;\n"
        "                }\n"
        "                int absX = winRect.Left + relX;\n"
        "                int absY = winRect.Top + relY;\n"
        "                result.AbsX = absX;\n"
        "                result.AbsY = absY;\n"
        "\n"
        "                var pt = new POINT { X = absX, Y = absY };\n"
        "                IntPtr hitWnd = WindowFromPoint(pt);\n"
        "                IntPtr ancestor = GetAncestor(hitWnd, 2);\n"
        "                if (ancestor == IntPtr.Zero) ancestor = hitWnd;\n"
        "                result.ActualHwnd = ancestor.ToInt64();\n"
        "                result.ClickedInCorrectWindow = (ancestor == hWnd || hitWnd == hWnd || IsChild(hWnd, hitWnd) || (ancestor != IntPtr.Zero && IsChild(hWnd, ancestor)));\n"
        "                if (!result.ClickedInCorrectWindow) {\n"
        "                    result.Error = string.Format(\"Hover target ({0},{1}) is covered by HWND={2}, not target HWND={3}\",\n"
        "                        absX, absY, ancestor.ToInt64(), hWnd.ToInt64());\n"
        "                    result.Success = false;\n"
        "                    return;\n"
        "                }\n"
        "\n"
        "                SetCursorPos(absX, absY);\n"
        "                int waitTime = dwellMs > 0 ? dwellMs : 300;\n"
        "                System.Threading.Thread.Sleep(waitTime);\n"
        "                result.Success = true;\n"
        "            } catch (Exception ex) {\n"
        "                result.Error = ex.Message;\n"
        "                result.Success = false;\n"
        "            }\n"
        "        });\n"
        "        return result;\n"
        "    }\n"
        "}\n"
        "'@\n"
        "if (-not ([System.Management.Automation.PSTypeName]'Win32MouseCore').Type) { Add-Type -TypeDefinition $codeMouse -ReferencedAssemblies 'System.Drawing' };\n"
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
            f"[Win32MouseCore]::Drag({start_x}, {start_y}, {end_x}, {end_y}, {steps}, 0x{down_flag:04X}, 0x{up_flag:04X}); "
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
            f"[Win32MouseCore]::Scroll(0x{flag:04X}, [uint32]{uint_delta}); "
            "@{ Action = 'MouseScroll'; Amount = " + str(amount) + "; Horizontal = $" + str(bool(horizontal)).lower() + "; Success = $True } | ConvertTo-Json -Compress"
        )


    @classmethod
    def build_click_in_window_command(
        cls,
        hwnd: str,
        rel_x: int,
        rel_y: int,
        button: str = "left",
        clicks: int = 1,
    ) -> str:
        """Window-relative click with WindowFromPoint containment guard.

        Uses (rel_x, rel_y) coordinates relative to the target window's top-left corner.
        Before firing, validates via WindowFromPoint that the pixel at the computed
        absolute coordinate belongs to the target HWND — aborts if another window
        is covering that pixel, returning ClickedInCorrectWindow=false.
        """
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

        clean_hwnd = str(hwnd).strip()
        return (
            f"{cls.WIN32_MOUSE_HEADER}"
            f"$hwnd = [IntPtr][long]{clean_hwnd};\n"
            f"$r = [Win32MouseCore]::ClickInWindow($hwnd, {rel_x}, {rel_y}, 0x{down_flag:04X}, 0x{up_flag:04X}, {clicks});\n"
            "@{\n"
            "    Action          = 'ClickInWindow';\n"
            "    Success         = $r.Success;\n"
            "    ClickedInCorrectWindow = $r.ClickedInCorrectWindow;\n"
            "    RelX            = " + str(rel_x) + ";\n"
            "    RelY            = " + str(rel_y) + ";\n"
            "    AbsX            = $r.AbsX;\n"
            "    AbsY            = $r.AbsY;\n"
            "    TargetHwnd      = $r.TargetHwnd;\n"
            "    ActualHwnd      = $r.ActualHwnd;\n"
            "    Error           = $r.Error;\n"
            "} | ConvertTo-Json -Compress\n"
        )

    @classmethod
    def build_move_smooth_command(cls, start_x: int, start_y: int, end_x: int, end_y: int, steps: int = 25) -> str:
        """Generates a command to smoothly move the cursor along a natural Bezier curve."""
        return (
            f"{cls.WIN32_MOUSE_HEADER}"
            f"[Win32MouseCore]::MoveSmooth({start_x}, {start_y}, {end_x}, {end_y}, {steps});\n"
            f"@{{ Action = 'MouseMoveSmooth'; StartX = {start_x}; StartY = {start_y}; EndX = {end_x}; EndY = {end_y}; Success = $True }} | ConvertTo-Json -Compress"
        )

    @classmethod
    def build_move_smooth_from_current_command(cls, end_x: int, end_y: int, steps: int = 20) -> str:
        """Smoothly moves the cursor from its *current* position to (end_x, end_y) along a Bezier path."""
        return (
            f"{cls.WIN32_MOUSE_HEADER}"
            f"[Win32MouseCore]::MoveSmoothFromCurrent({end_x}, {end_y}, {steps});\n"
            f"@{{ Action = 'MouseMoveSmooth'; EndX = {end_x}; EndY = {end_y}; Success = $True }} | ConvertTo-Json -Compress"
        )

    @classmethod
    def build_hover_command(cls, rel_x: int, rel_y: int, hwnd: Optional[int] = None, dwell_ms: int = 500) -> str:
        """Generates a command to hover the cursor over a target window coordinate to reveal tooltips or menus."""
        if hwnd is not None:
            clean_hwnd = str(hwnd).strip()
            return (
                f"{cls.WIN32_MOUSE_HEADER}"
                f"$hwnd = [IntPtr][long]{clean_hwnd};\n"
                f"$r = [Win32MouseCore]::HoverInWindow($hwnd, {rel_x}, {rel_y}, {dwell_ms});\n"
                "@{\n"
                "    Action          = 'HoverInWindow';\n"
                "    Success         = $r.Success;\n"
                "    ClickedInCorrectWindow = $r.ClickedInCorrectWindow;\n"
                "    RelX            = " + str(rel_x) + ";\n"
                "    RelY            = " + str(rel_y) + ";\n"
                "    AbsX            = $r.AbsX;\n"
                "    AbsY            = $r.AbsY;\n"
                "    DwellMs         = " + str(dwell_ms) + ";\n"
                "    TargetHwnd      = $r.TargetHwnd;\n"
                "    ActualHwnd      = $r.ActualHwnd;\n"
                "    Error           = $r.Error;\n"
                "} | ConvertTo-Json -Compress\n"
            )
        else:
            return (
                f"{cls.WIN32_MOUSE_HEADER}"
                f"[Win32MouseCore]::SetPos({rel_x}, {rel_y});\n"
                f"Start-Sleep -Milliseconds {dwell_ms};\n"
                f"@{{ Action = 'HoverScreen'; X = {rel_x}; Y = {rel_y}; DwellMs = {dwell_ms}; Success = $True }} | ConvertTo-Json -Compress"
            )

    @classmethod
    def build_scroll_into_view_command(
        cls,
        hwnd: int,
        target_rel_y: int,
        viewport_center_y: int = 400,
        tolerance: int = 80,
    ) -> str:
        """Calculates vertical delta between target element Y and viewport center, generating calibrated wheel scrolls."""
        delta_y = target_rel_y - viewport_center_y
        clean_hwnd = str(hwnd).strip()

        # Each standard mouse wheel notch (120 units) scrolls approximately 60-80 pixels in Windows
        ticks = int(abs(delta_y) / 60)
        direction = "down" if delta_y > 0 else "up"

        if ticks <= 0 or abs(delta_y) <= tolerance:
            return (
                "@{\n"
                "    Action          = 'ScrollIntoView';\n"
                "    Success         = $True;\n"
                "    Status          = 'AlreadyInViewport';\n"
                f"    TargetRelY      = {target_rel_y};\n"
                f"    ViewportCenterY = {viewport_center_y};\n"
                "} | ConvertTo-Json -Compress"
            )

        scroll_amount = -ticks if direction == "down" else ticks
        scroll_cmd = cls.build_scroll_command(amount=scroll_amount)
        return (
            f"# Scroll Into View: DeltaY={delta_y} ({direction.upper()} {ticks} ticks)\n"
            f"{scroll_cmd}"
        )

    # Aliases for convenience
    generate_move_cursor = build_move_command
    generate_drag = build_drag_and_drop_command
    generate_scroll = build_scroll_command
    generate_click_in_window = build_click_in_window_command

    @classmethod
    def generate_click(cls, button: str = "left", double_click: bool = False, x: Optional[int] = None, y: Optional[int] = None, clicks: int = 1) -> str:
        if double_click:
            clicks = 2
        return cls.build_click_command(x=x, y=y, button=button, clicks=clicks)


