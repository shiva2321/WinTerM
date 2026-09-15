"""Screen Perception Engine: Live visual capture, multi-monitor topology, and UI element discovery."""

import json
from typing import Optional, Dict, Any, List
from winterm.interaction.window_manager import WindowManager


class ScreenPerceptionEngine:
    """Provides visual capture, foreground state observation, and semantic element localization for agents."""

    WIN32_SCREEN_HEADER = (
        "$codeScreen = @'\n"
        "using System;\n"
        "using System.Collections.Generic;\n"
        "using System.Drawing;\n"
        "using System.Drawing.Imaging;\n"
        "using System.Runtime.InteropServices;\n"
        "using System.Text;\n"
        "using System.Threading;\n"
        "\n"
        "public class InteractiveScreenState {\n"
        "    public int ScreenWidth;\n"
        "    public int ScreenHeight;\n"
        "    public int VirtualLeft;\n"
        "    public int VirtualTop;\n"
        "    public int VirtualWidth;\n"
        "    public int VirtualHeight;\n"
        "    public int MonitorCount;\n"
        "    public int CursorX;\n"
        "    public int CursorY;\n"
        "    public long ForegroundHandle;\n"
        "    public string ForegroundTitle;\n"
        "    public int ForegroundPid;\n"
        "    public int ForegroundX;\n"
        "    public int ForegroundY;\n"
        "    public int ForegroundWidth;\n"
        "    public int ForegroundHeight;\n"
        "}\n"
        "\n"
        "public class Win32ScreenCore {\n"
        "    [StructLayout(LayoutKind.Sequential)]\n"
        "    public struct POINT { public int X; public int Y; }\n"
        "    [StructLayout(LayoutKind.Sequential)]\n"
        "    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }\n"
        "\n"
        "    [DllImport(\"user32.dll\", SetLastError = true)]\n"
        "    public static extern IntPtr OpenDesktop(string lpszDesktop, uint dwFlags, bool fInherit, uint dwDesiredAccess);\n"
        "    [DllImport(\"user32.dll\", SetLastError = true)]\n"
        "    public static extern bool SetThreadDesktop(IntPtr hDesktop);\n"
        "    [DllImport(\"user32.dll\")] public static extern bool SetProcessDPIAware();\n"
        "    [DllImport(\"user32.dll\")] public static extern bool SetProcessDpiAwarenessContext(IntPtr dpiContext);\n"
        "    [DllImport(\"user32.dll\")] public static extern IntPtr GetForegroundWindow();\n"
        "    [DllImport(\"user32.dll\")] public static extern bool GetCursorPos(out POINT lpPoint);\n"
        "    [DllImport(\"user32.dll\", CharSet = CharSet.Auto, SetLastError = true)]\n"
        "    public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);\n"
        "    [DllImport(\"user32.dll\")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);\n"
        "    [DllImport(\"user32.dll\")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);\n"
        "    [DllImport(\"user32.dll\")] public static extern int GetSystemMetrics(int nIndex);\n"
        "    [DllImport(\"user32.dll\")] public static extern IntPtr GetDC(IntPtr hWnd);\n"
        "    [DllImport(\"user32.dll\")] public static extern int ReleaseDC(IntPtr hWnd, IntPtr hDC);\n"
        "    [DllImport(\"gdi32.dll\")] public static extern IntPtr CreateCompatibleDC(IntPtr hdc);\n"
        "    [DllImport(\"gdi32.dll\")] public static extern IntPtr CreateCompatibleBitmap(IntPtr hdc, int nWidth, int nHeight);\n"
        "    [DllImport(\"gdi32.dll\")] public static extern IntPtr SelectObject(IntPtr hdc, IntPtr hgdiobj);\n"
        "    [DllImport(\"gdi32.dll\")] public static extern bool BitBlt(IntPtr hdcDest, int nXDest, int nYDest, int nWidth, int nHeight, IntPtr hdcSrc, int nXSrc, int nYSrc, uint dwRop);\n"
        "    [DllImport(\"gdi32.dll\")] public static extern bool DeleteDC(IntPtr hdc);\n"
        "    [DllImport(\"gdi32.dll\")] public static extern bool DeleteObject(IntPtr hObject);\n"
        "\n"
        "    public static void RunOnDefaultDesktop(Action act) {\n"
        "        var t = new Thread(() => {\n"
        "            try {\n"
        "                try {\n"
        "                    SetProcessDpiAwarenessContext(new IntPtr(-4)); // DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2\n"
        "                } catch {\n"
        "                    SetProcessDPIAware();\n"
        "                }\n"
        "                IntPtr dDesk = OpenDesktop(\"Default\", 0, false, 0x01FF);\n"
        "                if (dDesk == IntPtr.Zero) dDesk = OpenDesktop(\"default\", 0, false, 0x01FF);\n"
        "                if (dDesk != IntPtr.Zero) SetThreadDesktop(dDesk);\n"
        "            } catch {}\n"
        "            act();\n"
        "        });\n"
        "        t.SetApartmentState(ApartmentState.STA);\n"
        "        t.Start();\n"
        "        t.Join();\n"
        "    }\n"
        "\n"
        "    public static InteractiveScreenState GetLiveState() {\n"
        "        var state = new InteractiveScreenState();\n"
        "        RunOnDefaultDesktop(() => {\n"
        "            state.ScreenWidth = GetSystemMetrics(0);\n"
        "            state.ScreenHeight = GetSystemMetrics(1);\n"
        "            state.VirtualLeft = GetSystemMetrics(76);\n"
        "            state.VirtualTop = GetSystemMetrics(77);\n"
        "            state.VirtualWidth = GetSystemMetrics(78);\n"
        "            state.VirtualHeight = GetSystemMetrics(79);\n"
        "            state.MonitorCount = GetSystemMetrics(80);\n"
        "            POINT pt;\n"
        "            GetCursorPos(out pt);\n"
        "            state.CursorX = pt.X;\n"
        "            state.CursorY = pt.Y;\n"
        "            IntPtr fg = GetForegroundWindow();\n"
        "            state.ForegroundHandle = fg.ToInt64();\n"
        "            if (fg != IntPtr.Zero) {\n"
        "                StringBuilder sb = new StringBuilder(256);\n"
        "                GetWindowText(fg, sb, 256);\n"
        "                state.ForegroundTitle = sb.ToString();\n"
        "                uint pid;\n"
        "                GetWindowThreadProcessId(fg, out pid);\n"
        "                state.ForegroundPid = (int)pid;\n"
        "                RECT r;\n"
        "                GetWindowRect(fg, out r);\n"
        "                state.ForegroundX = r.Left;\n"
        "                state.ForegroundY = r.Top;\n"
        "                state.ForegroundWidth = Math.Max(0, r.Right - r.Left);\n"
        "                state.ForegroundHeight = Math.Max(0, r.Bottom - r.Top);\n"
        "            }\n"
        "        });\n"
        "        return state;\n"
        "    }\n"
        "\n"
        "    public static bool CaptureScreen(string outputPath, int x, int y, int width, int height) {\n"
        "        bool success = false;\n"
        "        RunOnDefaultDesktop(() => {\n"
        "            IntPtr hdcScreen = IntPtr.Zero;\n"
        "            IntPtr hdcMem = IntPtr.Zero;\n"
        "            IntPtr hbm = IntPtr.Zero;\n"
        "            IntPtr hOld = IntPtr.Zero;\n"
        "            try {\n"
        "                hdcScreen = GetDC(IntPtr.Zero);\n"
        "                hdcMem = CreateCompatibleDC(hdcScreen);\n"
        "                hbm = CreateCompatibleBitmap(hdcScreen, width, height);\n"
        "                hOld = SelectObject(hdcMem, hbm);\n"
        "                bool blt = BitBlt(hdcMem, 0, 0, width, height, hdcScreen, x, y, 0x00CC0020);\n"
        "                if (blt) {\n"
        "                    using (Bitmap bmp = Bitmap.FromHbitmap(hbm)) {\n"
        "                        bmp.Save(outputPath, ImageFormat.Png);\n"
        "                    }\n"
        "                    success = true;\n"
        "                }\n"
        "            } catch {}\n"
        "            finally {\n"
        "                if (hOld != IntPtr.Zero && hdcMem != IntPtr.Zero) SelectObject(hdcMem, hOld);\n"
        "                if (hbm != IntPtr.Zero) DeleteObject(hbm);\n"
        "                if (hdcMem != IntPtr.Zero) DeleteDC(hdcMem);\n"
        "                if (hdcScreen != IntPtr.Zero) ReleaseDC(IntPtr.Zero, hdcScreen);\n"
        "            }\n"
        "        });\n"
        "        return success;\n"
        "    }\n"
        "}\n"
        "'@\n"
        "if (-not ([System.Management.Automation.PSTypeName]'Win32ScreenCore').Type) { Add-Type -TypeDefinition $codeScreen -ReferencedAssemblies System.Drawing };\n"
    )

    @classmethod
    def build_capture_screen_command(cls, output_path: str, window_query: Optional[str] = None) -> str:
        """Generates PowerShell command to capture the full desktop or a specific window directly to disk."""
        clean_path = output_path.replace("'", "''").replace('"', '""')
        clean_query = window_query.replace("'", "''") if window_query else ""
        if window_query:
            script = (
                f"{WindowManager.WIN32_WINDOW_HELPER}\n"
                f"{cls.WIN32_SCREEN_HEADER}\n"
                "$foundTitle = '';\n"
                f"$hWnd = [Win32WindowCore]::ResolveWindow('{clean_query}', [ref]$foundTitle);\n"
                "if ($hWnd -ne [IntPtr]::Zero) {\n"
                "    $rect = New-Object Win32WindowCore+RECT;\n"
                "    [Win32WindowCore]::GetWindowRect($hWnd, [ref]$rect) | Out-Null;\n"
                "    $w = [Math]::Max(10, $rect.Right - $rect.Left);\n"
                "    $h = [Math]::Max(10, $rect.Bottom - $rect.Top);\n"
                f"    $ok = [Win32ScreenCore]::CaptureScreen('{clean_path}', $rect.Left, $rect.Top, $w, $h);\n"
                f"    @{{ Success = $ok; OutputPath = '{clean_path}'; WindowTitle = $foundTitle; Width = $w; Height = $h }} | ConvertTo-Json -Compress\n"
                "} else {\n"
                f"    @{{ Success = $False; Target = '{clean_query}'; Error = 'Target window not found for screen capture' }} | ConvertTo-Json -Compress\n"
                "}"
            )
        else:
            script = (
                f"{cls.WIN32_SCREEN_HEADER}\n"
                "$w = [Win32ScreenCore]::GetSystemMetrics(0);\n"
                "$h = [Win32ScreenCore]::GetSystemMetrics(1);\n"
                f"$ok = [Win32ScreenCore]::CaptureScreen('{clean_path}', 0, 0, $w, $h);\n"
                f"@{{ Success = $ok; OutputPath = '{clean_path}'; Mode = 'FullScreen'; Width = $w; Height = $h }} | ConvertTo-Json -Compress"
            )
        return script

    @classmethod
    def build_get_screen_state_command(cls) -> str:
        """Generates PowerShell command to inspect current screen resolution, mouse position, and foreground window."""
        script = (
            f"{cls.WIN32_SCREEN_HEADER}\n"
            "$s = [Win32ScreenCore]::GetLiveState();\n"
            "@{\n"
            "    Success = $True;\n"
            "    ScreenWidth = $s.ScreenWidth;\n"
            "    ScreenHeight = $s.ScreenHeight;\n"
            "    VirtualDesktop = @{\n"
            "        Left = $s.VirtualLeft;\n"
            "        Top = $s.VirtualTop;\n"
            "        Width = $s.VirtualWidth;\n"
            "        Height = $s.VirtualHeight;\n"
            "        MonitorCount = $s.MonitorCount;\n"
            "    };\n"
            "    CursorX = $s.CursorX;\n"
            "    CursorY = $s.CursorY;\n"
            "    ForegroundWindow = @{\n"
            "        Handle = $s.ForegroundHandle;\n"
            "        Title = $s.ForegroundTitle;\n"
            "        ProcessId = $s.ForegroundPid;\n"
            "        X = $s.ForegroundX;\n"
            "        Y = $s.ForegroundY;\n"
            "        Width = $s.ForegroundWidth;\n"
            "        Height = $s.ForegroundHeight;\n"
            "    }\n"
            "} | ConvertTo-Json -Compress -Depth 3"
        )
        return script

    @staticmethod
    def normalize_to_window(
        screen_x: int,
        screen_y: int,
        window_left: int,
        window_top: int,
        window_width: int,
        window_height: int,
    ) -> Dict[str, float]:
        """Calculates resolution-independent normalized coordinates (0.0 to 1.0) inside window bounds."""
        w = max(1, window_width)
        h = max(1, window_height)
        rel_x = screen_x - window_left
        rel_y = screen_y - window_top
        u = max(0.0, min(1.0, rel_x / float(w)))
        v = max(0.0, min(1.0, rel_y / float(h)))
        return {"u": round(u, 4), "v": round(v, 4), "rel_x": rel_x, "rel_y": rel_y}

    @staticmethod
    def denormalize_from_window(
        u: float,
        v: float,
        window_left: int,
        window_top: int,
        window_width: int,
        window_height: int,
    ) -> Dict[str, int]:
        """Converts normalized (u, v) coordinates back to physical global screen coordinates."""
        clamped_u = max(0.0, min(1.0, float(u)))
        clamped_v = max(0.0, min(1.0, float(v)))
        screen_x = int(window_left + (clamped_u * window_width))
        screen_y = int(window_top + (clamped_v * window_height))
        return {"screen_x": screen_x, "screen_y": screen_y}

    @classmethod
    def build_find_element_command(cls, window_identifier: str, query: str) -> str:
        """Locates an element inside a window by name, AutomationId, or ControlType and returns its live screen coordinates."""
        clean_target = window_identifier.replace("'", "''")
        clean_query = query.replace("'", "''")
        script = (
            f"{WindowManager.WIN32_WINDOW_HELPER}\n"
            "Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes;\n"
            "$foundTitle = '';\n"
            f"$hWnd = [Win32WindowCore]::ResolveWindow('{clean_target}', [ref]$foundTitle);\n"
            "if ($hWnd -eq [IntPtr]::Zero) {\n"
            f"    @{{ Success = $False; Target = '{clean_target}'; Error = 'Window not found' }} | ConvertTo-Json -Compress;\n"
            "    exit 0;\n"
            "};\n"
            "try {\n"
            "    $root = [System.Windows.Automation.AutomationElement]::FromHandle($hWnd);\n"
            "    $all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition);\n"
            "    $matches = [System.Collections.Generic.List[PSCustomObject]]::new();\n"
            "    foreach ($item in $all) {\n"
            "        try {\n"
            "            $cur = $item.Current;\n"
            f"            if ($cur.Name -like '*{clean_query}*' -or $cur.AutomationId -like '*{clean_query}*' -or $cur.ControlType.ProgrammaticName -like '*{clean_query}*') {{\n"
            "                $rc = $cur.BoundingRectangle;\n"
            "                $hasWidth = $rc.Width -gt 1;\n"
            "                $hasHeight = $rc.Height -gt 1;\n"
            "                $matches.Add([PSCustomObject]@{\n"
            "                    Name = $cur.Name;\n"
            "                    AutomationId = $cur.AutomationId;\n"
            "                    ControlType = $cur.ControlType.ProgrammaticName.Replace('ControlType.', '');\n"
            "                    IsEnabled = $cur.IsEnabled;\n"
            "                    X = [int]$rc.X;\n"
            "                    Y = [int]$rc.Y;\n"
            "                    Width = [int]$rc.Width;\n"
            "                    Height = [int]$rc.Height;\n"
            "                    CenterX = if ($hasWidth) { [int]($rc.X + ($rc.Width / 2)) } else { $null };\n"
            "                    CenterY = if ($hasHeight) { [int]($rc.Y + ($rc.Height / 2)) } else { $null };\n"
            "                });\n"
            "            }\n"
            "        } catch {}\n"
            "    };\n"
            "    @{\n"
            "        Success = $True;\n"
            "        WindowTitle = $foundTitle;\n"
            "        WindowHandle = $hWnd.ToInt64();\n"
            f"        Query = '{clean_query}';\n"
            "        MatchCount = $matches.Count;\n"
            "        Elements = $matches;\n"
            "        BestMatch = if ($matches.Count -gt 0) { $matches[0] } else { $null }\n"
            "    } | ConvertTo-Json -Compress -Depth 3\n"
            "} catch {\n"
            "    @{ Success = $False; Error = $_.Exception.Message } | ConvertTo-Json -Compress\n"
            "}"
        )
        return script
