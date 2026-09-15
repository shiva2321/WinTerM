"""Layer 9: Windows Desktop GUI, Window Management & Input Automation Subsystem."""

from typing import Dict, Any, List, Optional, Tuple
from winterm.models.context import ShellType, ElevationLevel
from winterm.models.intent import PlanStep, ActionCategory
from winterm.interaction.keyboard import KeyboardEngine
from winterm.interaction.mouse import MouseEngine
from winterm.interaction.pen_touch import PenTouchEngine
from winterm.interaction.app_manager import WindowsAppManager
from winterm.interaction.window_manager import WindowManager
from winterm.interaction.ui_automation import UIAutomationEngine
from winterm.interaction.screen import ScreenPerceptionEngine
from winterm.interaction.ocr_engine import WindowsOCREngine
from winterm.interaction.visual_grounding import SetOfMarkEngine
from winterm.interaction.semantic_tree import SemanticAccessibilityTree
from winterm.interaction.smart_resolver import SmartUIResolver
from winterm.interaction.visual_diff import VisualStateVerifier


class DesktopGuiSubsystem:
    """Manages Windows Desktop GUI automation, window handles, mouse/keyboard inputs, and GDI+ graphics synthesis."""

    # =========================================================================
    # 1. APPLICATION LIFECYCLE & DISCOVERY
    # =========================================================================

    @classmethod
    def find_applications(cls, query: Optional[str] = None, limit: int = 50) -> PlanStep:
        """Searches installed applications across shell:AppsFolder, Start Menu, and Registry App Paths."""
        return PlanStep(
            step_id="gui-find-apps",
            title=f"Find Installed Applications (Query: '{query or 'all'}')",
            category=ActionCategory.CUSTOM,
            raw_intent=f"find applications {query or ''}",
            target_shell=ShellType.POWERSHELL_51,
            command=WindowsAppManager.build_search_command(query=query, limit=limit),
            metadata={"subsystem": "desktop_gui", "action": "find_apps", "query": query},
        )

    @classmethod
    def launch_application(
        cls,
        target: str,
        arguments: Optional[str] = None,
        elevated: bool = False,
    ) -> PlanStep:
        """Launches any Windows application (Win32, UWP/AppsFolder, or Protocol URI)."""
        return PlanStep(
            step_id=f"gui-launch-{target.replace(':', '_').replace('/', '_')}",
            title=f"Launch Application '{target}'" + (" [Elevated]" if elevated else ""),
            category=ActionCategory.CUSTOM,
            raw_intent=f"launch application {target}",
            target_shell=ShellType.POWERSHELL_51,
            command=WindowsAppManager.build_launch_command(target=target, arguments=arguments, elevated=elevated),
            metadata={"subsystem": "desktop_gui", "action": "launch_app", "target": target, "elevated": elevated},
        )

    @classmethod
    def close_application(cls, target: str, force: bool = False) -> PlanStep:
        """Closes an application gracefully via CloseMainWindow or forcefully via Stop-Process."""
        return PlanStep(
            step_id=f"gui-close-{target}",
            title=f"Close Application '{target}'" + (" (Force Kill)" if force else " (Graceful)"),
            category=ActionCategory.CUSTOM,
            raw_intent=f"close application {target}",
            target_shell=ShellType.POWERSHELL_51,
            command=WindowsAppManager.build_close_command(target=target, force=force),
            metadata={"subsystem": "desktop_gui", "action": "close_app", "target": target, "force": force},
        )

    # =========================================================================
    # 2. WINDOW MANAGEMENT
    # =========================================================================

    @classmethod
    def list_windows(cls, query: Optional[str] = None) -> PlanStep:
        """Enumerates visible top-level windows with title, handle, PID, bounds, and state."""
        return PlanStep(
            step_id="gui-list-windows",
            title=f"List Visible Application Windows (Query: '{query or 'all'}')",
            category=ActionCategory.CUSTOM,
            raw_intent=f"list windows {query or ''}",
            target_shell=ShellType.POWERSHELL_51,
            command=WindowManager.build_list_windows_command(query=query),
            metadata={"subsystem": "desktop_gui", "action": "list_windows", "query": query},
        )

    @classmethod
    def focus_window(cls, identifier: str) -> PlanStep:
        """Brings a window to the foreground and restores if minimized."""
        return PlanStep(
            step_id=f"gui-focus-{identifier}",
            title=f"Focus and Restore Window '{identifier}'",
            category=ActionCategory.CUSTOM,
            raw_intent=f"focus window {identifier}",
            target_shell=ShellType.POWERSHELL_51,
            command=WindowManager.build_focus_command(identifier=identifier),
            metadata={"subsystem": "desktop_gui", "action": "focus_window", "identifier": identifier},
        )

    @classmethod
    def resize_move_window(
        cls,
        identifier: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> PlanStep:
        """Repositions and resizes an application window."""
        return PlanStep(
            step_id=f"gui-resize-{identifier}",
            title=f"Resize and Move Window '{identifier}' to {width}x{height} at ({x}, {y})",
            category=ActionCategory.CUSTOM,
            raw_intent=f"resize window {identifier} {width}x{height}",
            target_shell=ShellType.POWERSHELL_51,
            command=WindowManager.build_resize_move_command(identifier, x, y, width, height),
            metadata={"subsystem": "desktop_gui", "action": "resize_move_window", "identifier": identifier},
        )

    @classmethod
    def set_window_state(cls, identifier: str, state: str = "minimize") -> PlanStep:
        """Minimizes, maximizes, or restores a window."""
        return PlanStep(
            step_id=f"gui-state-{identifier}-{state}",
            title=f"Set Window State for '{identifier}' to {state.capitalize()}",
            category=ActionCategory.CUSTOM,
            raw_intent=f"set window state {identifier} {state}",
            target_shell=ShellType.POWERSHELL_51,
            command=WindowManager.build_set_state_command(identifier, state=state),
            metadata={"subsystem": "desktop_gui", "action": "set_window_state", "identifier": identifier, "state": state},
        )

    @classmethod
    def close_window(cls, identifier: str) -> PlanStep:
        """Sends WM_CLOSE message to a window."""
        return PlanStep(
            step_id=f"gui-close-window-{identifier}",
            title=f"Close Window '{identifier}' (WM_CLOSE)",
            category=ActionCategory.CUSTOM,
            raw_intent=f"close window {identifier}",
            target_shell=ShellType.POWERSHELL_51,
            command=WindowManager.build_close_window_command(identifier),
            metadata={"subsystem": "desktop_gui", "action": "close_window", "identifier": identifier},
        )

    # =========================================================================
    # 3. UI AUTOMATION INSPECTION & ELEMENT INTERACTION
    # =========================================================================

    @classmethod
    def inspect_ui_elements(cls, window_identifier: str, max_items: int = 100) -> PlanStep:
        """Traverses UI Automation element tree of a window to discover buttons, edits, and controls."""
        return PlanStep(
            step_id=f"gui-inspect-uia-{window_identifier}",
            title=f"Inspect UI Automation Elements in '{window_identifier}'",
            category=ActionCategory.CUSTOM,
            raw_intent=f"inspect ui elements in {window_identifier}",
            target_shell=ShellType.POWERSHELL_51,
            command=UIAutomationEngine.build_inspect_elements_command(window_identifier, max_items=max_items),
            metadata={"subsystem": "desktop_gui", "action": "inspect_elements", "window": window_identifier},
        )

    @classmethod
    def click_ui_element(cls, window_identifier: str, element_query: str) -> PlanStep:
        """Clicks an element by name or automation ID using InvokePattern or coordinates."""
        return PlanStep(
            step_id=f"gui-click-element-{element_query}",
            title=f"Click UI Element '{element_query}' in '{window_identifier}'",
            category=ActionCategory.CUSTOM,
            raw_intent=f"click {element_query} in {window_identifier}",
            target_shell=ShellType.POWERSHELL_51,
            command=UIAutomationEngine.build_click_element_command(window_identifier, element_query),
            metadata={"subsystem": "desktop_gui", "action": "click_element", "window": window_identifier, "element": element_query},
        )

    @classmethod
    def set_ui_element_text(cls, window_identifier: str, element_query: str, text: str) -> PlanStep:
        """Sets text value into an Edit or Input control via ValuePattern or SendKeys."""
        return PlanStep(
            step_id=f"gui-set-text-{element_query}",
            title=f"Set Text in '{element_query}' in '{window_identifier}'",
            category=ActionCategory.CUSTOM,
            raw_intent=f"set text in {element_query} to {text}",
            target_shell=ShellType.POWERSHELL_51,
            command=UIAutomationEngine.build_set_element_text_command(window_identifier, element_query, text),
            metadata={"subsystem": "desktop_gui", "action": "set_element_text", "window": window_identifier, "element": element_query},
        )

    @classmethod
    def get_screen_state(cls) -> PlanStep:
        """Inspects live screen resolution, active cursor position, and foreground window on the interactive desktop."""
        return PlanStep(
            step_id="gui-screen-state",
            title="Inspect Live Screen State, Resolution & Active Foreground Window",
            category=ActionCategory.CUSTOM,
            raw_intent="get screen state",
            target_shell=ShellType.POWERSHELL_51,
            command=ScreenPerceptionEngine.build_get_screen_state_command(),
            metadata={"subsystem": "desktop_gui", "action": "get_screen_state"},
        )

    @classmethod
    def capture_screen(cls, output_path: str, window_query: Optional[str] = None) -> PlanStep:
        """Captures a visual screenshot of the full desktop or a specific window to a PNG file."""
        return PlanStep(
            step_id="gui-capture-screen",
            title=f"Capture Visual Screenshot to '{output_path}'" + (f" (Window: '{window_query}')" if window_query else " [Full Screen]"),
            category=ActionCategory.CUSTOM,
            raw_intent=f"capture screenshot to {output_path}",
            target_shell=ShellType.POWERSHELL_51,
            command=ScreenPerceptionEngine.build_capture_screen_command(output_path=output_path, window_query=window_query),
            metadata={"subsystem": "desktop_gui", "action": "capture_screen", "output_path": output_path, "window_query": window_query},
        )

    @classmethod
    def find_ui_element(cls, window_identifier: str, query: str) -> PlanStep:
        """Locates an interactive UI element by query (Name, AutomationId, ControlType) and returns live coordinates."""
        clean_q = query.replace(" ", "_")
        return PlanStep(
            step_id=f"gui-find-element-{clean_q}",
            title=f"Find UI Element '{query}' in Window '{window_identifier}'",
            category=ActionCategory.CUSTOM,
            raw_intent=f"find element {query} in {window_identifier}",
            target_shell=ShellType.POWERSHELL_51,
            command=ScreenPerceptionEngine.build_find_element_command(window_identifier, query),
            metadata={"subsystem": "desktop_gui", "action": "find_ui_element", "window": window_identifier, "query": query},
        )

    # =========================================================================
    # 4. KEYBOARD & MOUSE INPUT AUTOMATION
    # =========================================================================

    @classmethod
    def type_text(cls, text: str, interval_ms: int = 10) -> PlanStep:
        """Simulates typing text via Windows SendKeys."""
        return PlanStep(
            step_id="gui-input-type",
            title=f"Type Keyboard Text: '{text[:25]}...'",
            category=ActionCategory.CUSTOM,
            raw_intent=f"type text {text}",
            target_shell=ShellType.POWERSHELL_51,
            command=KeyboardEngine.build_type_command(text, interval_ms=interval_ms),
            metadata={"subsystem": "desktop_gui", "action": "type_text", "text": text},
        )

    @classmethod
    def press_hotkey(cls, keys: List[str]) -> PlanStep:
        """Simulates pressing a hotkey or key combination (e.g. ['ctrl', 'c'], ['win', 'r'])."""
        return PlanStep(
            step_id=f"gui-hotkey-{'-'.join(keys)}",
            title=f"Press Keyboard Hotkey: {'+'.join(keys).upper()}",
            category=ActionCategory.CUSTOM,
            raw_intent=f"press hotkey {'+'.join(keys)}",
            target_shell=ShellType.POWERSHELL_51,
            command=KeyboardEngine.build_hotkey_command(keys),
            metadata={"subsystem": "desktop_gui", "action": "press_hotkey", "keys": keys},
        )

    @classmethod
    def mouse_click(cls, x: int, y: int, button: str = "left", double: bool = False) -> PlanStep:
        """Moves cursor to (X, Y) and performs mouse click."""
        return PlanStep(
            step_id=f"gui-mouse-click-{x}-{y}",
            title=f"Mouse Click ({button.capitalize()}{' Double' if double else ''}) at ({x}, {y})",
            category=ActionCategory.CUSTOM,
            raw_intent=f"click mouse at {x} {y}",
            target_shell=ShellType.POWERSHELL_51,
            command=MouseEngine.build_click_command(x, y, button=button, double=double),
            metadata={"subsystem": "desktop_gui", "action": "mouse_click", "x": x, "y": y, "button": button},
        )

    @classmethod
    def mouse_move(cls, x: int, y: int, smooth: bool = False, steps: int = 15) -> PlanStep:
        """Moves mouse cursor to absolute (X, Y) coordinates."""
        return PlanStep(
            step_id=f"gui-mouse-move-{x}-{y}",
            title=f"Move Mouse to ({x}, {y})" + (" [Smooth]" if smooth else ""),
            category=ActionCategory.CUSTOM,
            raw_intent=f"move mouse to {x} {y}",
            target_shell=ShellType.POWERSHELL_51,
            command=MouseEngine.build_move_command(x, y, smooth=smooth, steps=steps),
            metadata={"subsystem": "desktop_gui", "action": "mouse_move", "x": x, "y": y},
        )

    @classmethod
    def mouse_drag(cls, start_x: int, start_y: int, end_x: int, end_y: int, steps: int = 20) -> PlanStep:
        """Performs a drag-and-drop mouse gesture from (startX, startY) to (endX, endY)."""
        return PlanStep(
            step_id=f"gui-mouse-drag-{start_x}-{start_y}-to-{end_x}-{end_y}",
            title=f"Mouse Drag from ({start_x}, {start_y}) to ({end_x}, {end_y})",
            category=ActionCategory.CUSTOM,
            raw_intent=f"drag mouse from {start_x} {start_y} to {end_x} {end_y}",
            target_shell=ShellType.POWERSHELL_51,
            command=MouseEngine.build_drag_command(start_x, start_y, end_x, end_y, steps=steps),
            metadata={"subsystem": "desktop_gui", "action": "mouse_drag", "start": (start_x, start_y), "end": (end_x, end_y)},
        )

    @classmethod
    def mouse_scroll(cls, amount: int, horizontal: bool = False) -> PlanStep:
        """Performs vertical or horizontal mouse wheel scroll."""
        direction = "Horizontal" if horizontal else "Vertical"
        return PlanStep(
            step_id=f"gui-mouse-scroll-{amount}",
            title=f"Mouse Scroll ({direction}, Amount: {amount})",
            category=ActionCategory.CUSTOM,
            raw_intent=f"scroll mouse {amount}",
            target_shell=ShellType.POWERSHELL_51,
            command=MouseEngine.build_scroll_command(amount=amount, horizontal=horizontal),
            metadata={"subsystem": "desktop_gui", "action": "mouse_scroll", "amount": amount},
        )

    @classmethod
    def pen_draw_path(cls, points: List[Tuple[int, int]], delay_ms: int = 10) -> PlanStep:
        """Draws a continuous parametric path using pen/pointer injection."""
        return PlanStep(
            step_id="gui-pen-draw-path",
            title=f"Continuous Pen/Pointer Stroke ({len(points)} points)",
            category=ActionCategory.CUSTOM,
            raw_intent=f"draw path with {len(points)} points",
            target_shell=ShellType.POWERSHELL_51,
            command=PenTouchEngine.build_stroke_command(points, delay_ms=delay_ms),
            metadata={"subsystem": "desktop_gui", "action": "pen_draw_path", "point_count": len(points)},
        )

    @classmethod
    def draw_geometric_shape(
        cls,
        shape: str = "circle",
        cx: int = 500,
        cy: int = 400,
        radius: int = 100,
        width: int = 200,
        height: int = 150,
        **kwargs,
    ) -> PlanStep:
        """Generates parametric points for a circle, rectangle, or line, and executes a continuous pen stroke."""
        shape_clean = shape.lower()
        if shape_clean == "circle":
            pts = PenTouchEngine.generate_circle_points(cx, cy, radius=radius)
        elif shape_clean in ("rect", "rectangle"):
            pts = PenTouchEngine.generate_rectangle_points(cx, cy, width, height)
        else:
            x2 = kwargs.get("x2", cx + width)
            y2 = kwargs.get("y2", cy + height)
            pts = PenTouchEngine.generate_line_points(cx, cy, x2, y2)

        return cls.pen_draw_path(pts)

    # =========================================================================
    # 5. LEGACY & DIAGNOSTIC HELPERS (PRESERVED FOR COMPATIBILITY)
    # =========================================================================

    @classmethod
    def probe_desktop_session(cls) -> PlanStep:
        """Probes whether an interactive desktop session is active, primary monitor resolution, and scaling."""
        return PlanStep(
            step_id="gui-session-probe",
            title="Probe Windows Interactive Desktop Session & Display Metrics",
            category=ActionCategory.DIAGNOSTIC,
            raw_intent="probe desktop session",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$sz = [System.Windows.Forms.SystemInformation]::PrimaryMonitorSize; "
                "$ui = [System.Windows.Forms.SystemInformation]::UserInteractive; "
                "@{ UserInteractive = $ui; ScreenWidth = $sz.Width; ScreenHeight = $sz.Height; "
                "SessionName = $env:SESSIONNAME } | ConvertTo-Json -Compress"
            ),
            metadata={"subsystem": "desktop_gui", "action": "probe_session"},
        )

    @classmethod
    def generate_circle_graphic(
        cls,
        output_path: str = "$env:TEMP\\winterm_circle.png",
        radius: int = 150,
        center_x: int = 250,
        center_y: int = 250,
        color: str = "RoyalBlue",
        fill: bool = True,
    ) -> PlanStep:
        """Synthesizes a mathematically precise anti-aliased circle using GDI+ and saves to PNG."""
        fill_code = (
            f"$brush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(40, [System.Drawing.Color]::{color})); "
            f"$g.FillEllipse($brush, {center_x - radius}, {center_y - radius}, {radius * 2}, {radius * 2}); "
            "$brush.Dispose(); "
        ) if fill else ""

        ps_script = (
            "Add-Type -AssemblyName System.Drawing; "
            f"$width = {center_x * 2}; $height = {center_y * 2}; "
            "$bmp = New-Object System.Drawing.Bitmap $width, $height; "
            "$g = [System.Drawing.Graphics]::FromImage($bmp); "
            "$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias; "
            "$g.Clear([System.Drawing.Color]::White); "
            f"{fill_code}"
            f"$pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::{color}), 6; "
            f"$g.DrawEllipse($pen, {center_x - radius}, {center_y - radius}, {radius * 2}, {radius * 2}); "
            "$g.Dispose(); $pen.Dispose(); "
            f"$outPath = [System.Environment]::ExpandEnvironmentVariables('{output_path}'); "
            "$bmp.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png); "
            "$bmp.Dispose(); "
            "@{ Path = $outPath; Exists = (Test-Path $outPath); SizeBytes = (Get-Item $outPath).Length } | ConvertTo-Json -Compress"
        )

        return PlanStep(
            step_id="gui-generate-circle",
            title=f"Programmatically Render Anti-Aliased Circle to Image ({color}, radius={radius})",
            category=ActionCategory.CUSTOM,
            raw_intent=f"render circle graphic {output_path}",
            target_shell=ShellType.POWERSHELL_51,
            command=ps_script,
            metadata={"subsystem": "desktop_gui", "action": "render_circle", "output_path": output_path},
        )

    @classmethod
    def open_in_paint(cls, file_path: str = "$env:TEMP\\winterm_circle.png") -> PlanStep:
        """Opens an image file inside Microsoft Paint (mspaint.exe) or registered editor with fallback diagnosis."""
        return PlanStep(
            step_id="gui-open-paint",
            title=f"Launch Paint Application with Rendered Graphic",
            category=ActionCategory.CUSTOM,
            raw_intent=f"open in paint {file_path}",
            target_shell=ShellType.POWERSHELL_51,
            command=(
                f"$f = [System.Environment]::ExpandEnvironmentVariables('{file_path}'); "
                "$paintCmd = Get-Command mspaint.exe -ErrorAction SilentlyContinue; "
                "$uwpApp = Test-Path \"$env:LOCALAPPDATA\\Microsoft\\WindowsApps\\mspaint.exe\"; "
                "if ($paintCmd) { $p = Start-Process mspaint.exe -ArgumentList \"`\"$f`\"\" -PassThru } "
                "elseif ($uwpApp) { $p = Start-Process \"$env:LOCALAPPDATA\\Microsoft\\WindowsApps\\mspaint.exe\" -ArgumentList \"`\"$f`\"\" -PassThru } "
                "else { try { $p = Start-Process $f -PassThru } catch { $p = $null } }; "
                "if ($p) { @{ Launched = $True; ProcessId = $p.Id; ProcessName = $p.ProcessName } | ConvertTo-Json -Compress } "
                "else { @{ Launched = $False; Error = 'Microsoft Paint is not installed on this system'; Suggestion = 'Install via: winget install Microsoft.Paint' } | ConvertTo-Json -Compress }"
            ),
            metadata={"subsystem": "desktop_gui", "action": "open_paint", "file_path": file_path},
        )

    @classmethod
    def live_draw_circle_in_paint(
        cls,
        center_x: int = 500,
        center_y: int = 400,
        radius: int = 150,
    ) -> PlanStep:
        """Launches MS Paint, activates its window, selects the oval tool, and simulates a live mouse drag."""
        start_x = center_x - radius
        start_y = center_y - radius
        end_x = center_x + radius
        end_y = center_y + radius

        win32_helper = (
            "$code = @'\n"
            "using System;\n"
            "using System.Runtime.InteropServices;\n"
            "public class Win32Mouse {\n"
            "    [DllImport(\"user32.dll\")] public static extern bool SetForegroundWindow(IntPtr hWnd);\n"
            "    [DllImport(\"user32.dll\")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, int dwExtraInfo);\n"
            "    [DllImport(\"user32.dll\")] public static extern bool SetCursorPos(int X, int Y);\n"
            "}\n"
            "'@\n"
            "if (-not ([System.Management.Automation.PSTypeName]'Win32Mouse').Type) { Add-Type -TypeDefinition $code }\n"
        )

        automation_script = (
            f"{win32_helper}"
            "Add-Type -AssemblyName System.Windows.Forms\n"
            "$p = Start-Process mspaint.exe -PassThru -ErrorAction SilentlyContinue\n"
            "if (-not $p -and (Test-Path \"$env:LOCALAPPDATA\\Microsoft\\WindowsApps\\mspaint.exe\")) {\n"
            "    $p = Start-Process \"$env:LOCALAPPDATA\\Microsoft\\WindowsApps\\mspaint.exe\" -PassThru -ErrorAction SilentlyContinue\n"
            "}\n"
            "if ($p) {\n"
            "    $p.WaitForInputIdle(3000) | Out-Null\n"
            "    Start-Sleep -Milliseconds 600\n"
            "    [Win32Mouse]::SetForegroundWindow($p.MainWindowHandle) | Out-Null\n"
            "    Start-Sleep -Milliseconds 300\n"
            "    [System.Windows.Forms.SendKeys]::SendWait('%h')\n"
            "    Start-Sleep -Milliseconds 150\n"
            "    [System.Windows.Forms.SendKeys]::SendWait('sh')\n"
            "    Start-Sleep -Milliseconds 250\n"
            f"    [Win32Mouse]::SetCursorPos({start_x}, {start_y})\n"
            "    [Win32Mouse]::mouse_event(0x02, 0, 0, 0, 0)\n"  # MOUSEEVENTF_LEFTDOWN
            "    Start-Sleep -Milliseconds 150\n"
            f"    [Win32Mouse]::SetCursorPos({end_x}, {end_y})\n"
            "    Start-Sleep -Milliseconds 150\n"
            "    [Win32Mouse]::mouse_event(0x04, 0, 0, 0, 0)\n"  # MOUSEEVENTF_LEFTUP
            "    @{ Mode = 'LiveWin32MouseDrag'; ProcessId = $p.Id; Success = $True } | ConvertTo-Json -Compress\n"
            "} else {\n"
            "    @{ Mode = 'LiveWin32MouseDrag'; Success = $False; Reason = 'Microsoft Paint is not installed on this system. Suggestion: run winget install Microsoft.Paint' } | ConvertTo-Json -Compress\n"
            "}"
        )

        return PlanStep(
            step_id="gui-live-paint-drag",
            title=f"Live Win32 Mouse Drag Automation on Paint Canvas (Radius={radius})",
            category=ActionCategory.CUSTOM,
            raw_intent="live draw circle in paint",
            target_shell=ShellType.POWERSHELL_51,
            command=automation_script,
            metadata={"subsystem": "desktop_gui", "action": "live_drag", "radius": radius},
        )

    @classmethod
    def bring_window_to_foreground(cls, process_name: str) -> PlanStep:
        """Brings the main window of a given process to the foreground (redirects to focus_window)."""
        return cls.focus_window(identifier=process_name)

    # =========================================================================
    # MULTI-STEP PLAN CONVENIENCE METHODS (List[PlanStep])
    # =========================================================================

    @classmethod
    def plan_find_apps(cls, pattern: str = "") -> List[PlanStep]:
        return [cls.find_applications(query=pattern)]

    @classmethod
    def plan_launch_app(cls, identifier: str, args: str = "") -> List[PlanStep]:
        return [cls.launch_application(target=identifier, arguments=args)]

    @classmethod
    def plan_close_app(cls, process_name: str, force: bool = False) -> List[PlanStep]:
        return [cls.close_application(target=process_name, force=force)]

    @classmethod
    def plan_list_windows(cls, query: Optional[str] = None) -> List[PlanStep]:
        return [cls.list_windows(query=query)]

    @classmethod
    def plan_focus_window(cls, identifier: str) -> List[PlanStep]:
        return [cls.focus_window(identifier=identifier)]

    @classmethod
    def plan_resize_window(cls, identifier: str, x: int, y: int, width: int, height: int) -> List[PlanStep]:
        return [cls.resize_move_window(identifier, x, y, width, height)]

    @classmethod
    def plan_inspect_ui(cls, title_pattern: str = "", max_depth: int = 3, max_items: int = 100) -> List[PlanStep]:
        return [cls.inspect_ui_elements(title_pattern, max_items=max_items)]

    @classmethod
    def plan_click_element(cls, window_identifier: str, element_query: str) -> List[PlanStep]:
        return [cls.click_ui_element(window_identifier, element_query)]

    @classmethod
    def plan_set_element_text(cls, window_identifier: str, element_query: str, text: str) -> List[PlanStep]:
        return [cls.set_ui_element_text(window_identifier, element_query, text)]

    @classmethod
    def plan_type_text(cls, text: str, delay_ms: int = 15) -> List[PlanStep]:
        return [cls.type_text(text, interval_ms=delay_ms)]

    @classmethod
    def plan_press_hotkey(cls, keys: Any, is_win_hotkey: bool = False) -> List[PlanStep]:
        if isinstance(keys, str):
            k_list = [keys]
        else:
            k_list = list(keys)
        if is_win_hotkey and "win" not in [k.lower() for k in k_list]:
            k_list.insert(0, "win")
        return [cls.press_hotkey(k_list)]

    @classmethod
    def plan_mouse_click(cls, button: str = "left", double: bool = False, x: int = 0, y: int = 0) -> List[PlanStep]:
        return [cls.mouse_click(x, y, button=button, double=double)]

    @classmethod
    def plan_mouse_move(cls, x: int, y: int, smooth: bool = False) -> List[PlanStep]:
        return [cls.mouse_move(x, y, smooth=smooth)]

    @classmethod
    def plan_mouse_drag(cls, start_x: int, start_y: int, end_x: int, end_y: int) -> List[PlanStep]:
        return [cls.mouse_drag(start_x, start_y, end_x, end_y)]

    @classmethod
    def plan_mouse_scroll(cls, amount: int = 1, horizontal: bool = False, delta: Optional[int] = None) -> List[PlanStep]:
        effective_amount = amount if delta is None else int(delta / 120)
        return [cls.mouse_scroll(effective_amount, horizontal=horizontal)]

    @classmethod
    def plan_draw_shape(cls, shape: str, **kwargs) -> List[PlanStep]:
        return [cls.draw_geometric_shape(shape, **kwargs)]

    # =========================================================================
    # 7. ADVANCED UI PERCEPTION & GROUNDING
    # =========================================================================

    @classmethod
    def ocr_window(cls, window_identifier: str, language_tag: str = "en-US") -> PlanStep:
        """Executes native zero-dependency Windows OCR on the target window's graphical rendering."""
        return PlanStep(
            step_id=f"gui-ocr-window-{window_identifier.replace(' ', '_')}",
            title=f"Native Windows OCR on Window '{window_identifier}'",
            category=ActionCategory.CUSTOM,
            raw_intent=f"ocr window {window_identifier}",
            target_shell=ShellType.POWERSHELL_51,
            command=WindowsOCREngine.build_ocr_window_command(window_identifier, language_tag=language_tag),
            metadata={"subsystem": "desktop_gui", "action": "ocr_window", "window": window_identifier, "lang": language_tag},
        )

    @classmethod
    def ocr_image(cls, image_path: str, language_tag: str = "en-US") -> PlanStep:
        """Executes native zero-dependency Windows OCR on an image file on disk."""
        return PlanStep(
            step_id=f"gui-ocr-image",
            title=f"Native Windows OCR on Image '{image_path}'",
            category=ActionCategory.CUSTOM,
            raw_intent=f"ocr image {image_path}",
            target_shell=ShellType.POWERSHELL_51,
            command=WindowsOCREngine.build_ocr_image_command(image_path, language_tag=language_tag),
            metadata={"subsystem": "desktop_gui", "action": "ocr_image", "path": image_path, "lang": language_tag},
        )

    @classmethod
    def som_annotate(cls, window_identifier: str, output_annotated_path: str, max_marks: int = 50) -> PlanStep:
        """Generates Set-of-Mark visual grounding overlay with numbered badges ([1], [2]...) and element index."""
        return PlanStep(
            step_id=f"gui-som-annotate-{window_identifier.replace(' ', '_')}",
            title=f"Set-of-Mark Grounding on Window '{window_identifier}' -> '{output_annotated_path}'",
            category=ActionCategory.CUSTOM,
            raw_intent=f"set of mark annotate {window_identifier}",
            target_shell=ShellType.POWERSHELL_51,
            command=SetOfMarkEngine.build_annotate_window_command(window_identifier, output_annotated_path, max_marks=max_marks),
            metadata={"subsystem": "desktop_gui", "action": "som_annotate", "window": window_identifier, "output": output_annotated_path},
        )

    @classmethod
    def smart_click(
        cls,
        window_identifier: str,
        element_query: str,
        control_type: Optional[str] = None,
        language_tag: str = "en-US",
    ) -> PlanStep:
        """Clicks an element using multi-strategy cascading: UIAutomation -> Native OCR -> Coordinate click."""
        return PlanStep(
            step_id=f"gui-smart-click-{element_query.replace(' ', '_')}",
            title=f"Smart Click '{element_query}' in Window '{window_identifier}' (UIA + OCR Fallback)",
            category=ActionCategory.CUSTOM,
            raw_intent=f"smart click {element_query} in {window_identifier}",
            target_shell=ShellType.POWERSHELL_51,
            command=SmartUIResolver.build_smart_click_command(
                window_identifier,
                element_query,
                control_type=control_type,
                language_tag=language_tag,
            ),
            metadata={"subsystem": "desktop_gui", "action": "smart_click", "window": window_identifier, "query": element_query},
        )

    @classmethod
    def wait_for_ui_change(
        cls,
        window_identifier: str,
        timeout_ms: int = 3000,
        min_diff_pct: float = 0.5,
    ) -> PlanStep:
        """Waits asynchronously for visual UI change in the target window, eliminating race conditions."""
        return PlanStep(
            step_id=f"gui-wait-change-{window_identifier.replace(' ', '_')}",
            title=f"Wait for Visual UI Change in '{window_identifier}' (Timeout: {timeout_ms}ms, Threshold: {min_diff_pct}%)",
            category=ActionCategory.CUSTOM,
            raw_intent=f"wait for ui change in {window_identifier}",
            target_shell=ShellType.POWERSHELL_51,
            command=VisualStateVerifier.build_wait_for_ui_change_command(
                window_identifier,
                timeout_ms=timeout_ms,
                min_diff_pct=min_diff_pct,
            ),
            metadata={"subsystem": "desktop_gui", "action": "wait_ui_change", "window": window_identifier, "timeout_ms": timeout_ms},
        )

    @classmethod
    def plan_ocr_window(cls, window_identifier: str, language_tag: str = "en-US") -> List[PlanStep]:
        return [cls.ocr_window(window_identifier, language_tag=language_tag)]

    @classmethod
    def plan_som_annotate(cls, window_identifier: str, output_annotated_path: str, max_marks: int = 50) -> List[PlanStep]:
        return [cls.som_annotate(window_identifier, output_annotated_path, max_marks=max_marks)]

    @classmethod
    def plan_smart_click(cls, window_identifier: str, element_query: str, control_type: Optional[str] = None) -> List[PlanStep]:
        return [cls.smart_click(window_identifier, element_query, control_type=control_type)]

    @classmethod
    def plan_wait_for_ui_change(cls, window_identifier: str, timeout_ms: int = 3000, min_diff_pct: float = 0.5) -> List[PlanStep]:
        return [cls.wait_for_ui_change(window_identifier, timeout_ms=timeout_ms, min_diff_pct=min_diff_pct)]
