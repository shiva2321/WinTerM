"""Pen & Touch Automation Engine: Injects pointer strokes and parametric geometric paths for drawing."""

import math
from typing import List, Tuple, Dict, Any


class PenTouchEngine:
    """Generates continuous drawing strokes, touch gestures, and geometric paths for drawing on canvases."""

    WIN32_POINTER_HEADER = (
        "$code = @'\n"
        "using System;\n"
        "using System.Runtime.InteropServices;\n"
        "public class Win32PointerCore {\n"
        "    [DllImport(\"user32.dll\")] public static extern bool SetCursorPos(int X, int Y);\n"
        "    [DllImport(\"user32.dll\")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, int dwExtraInfo);\n"
        "}\n"
        "'@\n"
        "if (-not ([System.Management.Automation.PSTypeName]'Win32PointerCore').Type) { Add-Type -TypeDefinition $code }; "
    )

    @classmethod
    def generate_circle_points(
        cls,
        center_x: int,
        center_y: int,
        radius: int,
        steps: int = 36,
    ) -> List[Tuple[int, int]]:
        """Calculates discrete coordinate points tracing a circle."""
        steps = max(1, int(steps))
        points = []
        for i in range(steps + 1):
            theta = 2.0 * math.pi * (i / float(steps))
            x = int(round(center_x + radius * math.cos(theta)))
            y = int(round(center_y + radius * math.sin(theta)))
            points.append((x, y))
        return points

    @classmethod
    def generate_rectangle_points(
        cls,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> List[Tuple[int, int]]:
        """Calculates coordinate points tracing a closed rectangle."""
        return [
            (x, y),
            (x + width, y),
            (x + width, y + height),
            (x, y + height),
            (x, y),
        ]

    @classmethod
    def generate_line_points(
        cls,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        steps: int = 20,
    ) -> List[Tuple[int, int]]:
        """Calculates intermediate points along a straight line vector."""
        steps = max(1, int(steps))
        points = []
        for i in range(steps + 1):
            t = i / float(steps)
            px = int(round(start_x + (end_x - start_x) * t))
            py = int(round(start_y + (end_y - start_y) * t))
            points.append((px, py))
        return points

    @classmethod
    def build_stroke_command(
        cls,
        points: List[Tuple[int, int]],
        pointer_type: str = "pen",
        delay_ms: int = 8,
        button: str = "left",
    ) -> str:
        """Generates a PowerShell command that drags a pointer smoothly through a sequence of points."""
        if not points:
            return "@{ Action = 'EmptyStroke'; Success = $False } | ConvertTo-Json -Compress"

        first_x, first_y = points[0]
        point_ops = []
        for x, y in points[1:]:
            point_ops.append(f"[Win32PointerCore]::SetCursorPos({x}, {y}) | Out-Null; Start-Sleep -Milliseconds {delay_ms};")

        path_execution = " ".join(point_ops)
        down_flag = "0x0008" if button.lower() == "right" else "0x0002"
        up_flag = "0x0010" if button.lower() == "right" else "0x0004"

        return (
            f"{cls.WIN32_POINTER_HEADER}"
            f"[Win32PointerCore]::SetCursorPos({first_x}, {first_y}) | Out-Null; "
            "try { "
            "    Start-Sleep -Milliseconds 40; "
            f"    [Win32PointerCore]::mouse_event({down_flag}, 0, 0, 0, 0); "
            "    Start-Sleep -Milliseconds 40; "
            f"    {path_execution} "
            "} finally { "
            f"    [Win32PointerCore]::mouse_event({up_flag}, 0, 0, 0, 0); "
            "} "
            "@{ Action = 'PointerStroke'; PointerType = '" + pointer_type + "'; PointCount = " + str(len(points)) + "; Success = $True } | ConvertTo-Json -Compress"
        )

    # Aliases for convenience
    generate_stroke = build_stroke_command

