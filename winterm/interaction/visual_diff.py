"""Visual State Verifier: Perceptual image difference detection and asynchronous UI state change waiting.

Provides closed-loop confirmation that mouse clicks, hotkeys, or text inputs actually
modified the target window, eliminating fragile race conditions and arbitrary sleep delays.
"""

import json
from typing import Optional, Dict, Any, List
from winterm.interaction.window_manager import WindowManager
from winterm.interaction.screen import ScreenPerceptionEngine


class VisualStateVerifier:
    """Verifies visual UI state transitions and performs smart waits on graphical changes."""

    DIFF_HELPER = (
        "Add-Type -AssemblyName System.Drawing;\n"
        "function Compare-WindowBitmaps($bmp1, $bmp2) {\n"
        "    if ($bmp1.Width -ne $bmp2.Width -or $bmp1.Height -ne $bmp2.Height) { return 100.0 };\n"
        "    $totalSampled = 0;\n"
        "    $differentPixels = 0;\n"
        "    # Sample in a 4x4 stride for ultra-fast performance\n"
        "    for ($x = 0; $x -lt $bmp1.Width; $x += 4) {\n"
        "        for ($y = 0; $y -lt $bmp1.Height; $y += 4) {\n"
        "            $c1 = $bmp1.GetPixel($x, $y);\n"
        "            $c2 = $bmp2.GetPixel($x, $y);\n"
        "            $diff = [Math]::Abs($c1.R - $c2.R) + [Math]::Abs($c1.G - $c2.G) + [Math]::Abs($c1.B - $c2.B);\n"
        "            if ($diff -gt 30) { $differentPixels++ };\n"
        "            $totalSampled++;\n"
        "        };\n"
        "    };\n"
        "    if ($totalSampled -eq 0) { return 0.0 };\n"
        "    return [Math]::Round(($differentPixels / $totalSampled) * 100.0, 2);\n"
        "}\n"
    )

    @classmethod
    def build_wait_for_ui_change_command(
        cls,
        window_identifier: str,
        timeout_ms: int = 3000,
        min_diff_pct: float = 0.5,
        poll_interval_ms: int = 100,
    ) -> str:
        """Generates PowerShell command to poll target window until its visual rendering changes beyond threshold."""
        clean_target = window_identifier.replace("'", "''")

        script = (
            f"{WindowManager.WIN32_WINDOW_HELPER}\n"
            f"{ScreenPerceptionEngine.WIN32_SCREEN_HEADER}\n"
            f"{cls.DIFF_HELPER}\n"
            "$foundTitle = '';\n"
            f"$hWnd = [Win32WindowCore]::ResolveWindow('{clean_target}', [ref]$foundTitle);\n"
            "if ($hWnd -eq [IntPtr]::Zero) {\n"
            f"    @{{ Success = $False; Target = '{clean_target}'; Error = 'Window not found' }} | ConvertTo-Json -Compress;\n"
            "    exit 0;\n"
            "};\n"
            "$rect = New-Object Win32WindowCore+RECT;\n"
            "[Win32WindowCore]::GetWindowRect($hWnd, [ref]$rect) | Out-Null;\n"
            "$w = [Math]::Max(10, $rect.Right - $rect.Left);\n"
            "$h = [Math]::Max(10, $rect.Bottom - $rect.Top);\n"
            "\n"
            "$basePath = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), ('winterm_base_' + [System.Guid]::NewGuid().ToString('N') + '.png'));\n"
            "$curPath = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), ('winterm_cur_' + [System.Guid]::NewGuid().ToString('N') + '.png'));\n"
            "\n"
            "try {\n"
            "    # Capture baseline frame\n"
            "    [Win32ScreenCore]::CaptureScreen($basePath, $rect.Left, $rect.Top, $w, $h) | Out-Null;\n"
            "    $bytesBase = [System.IO.File]::ReadAllBytes($basePath);\n"
            "    $msBase = [System.IO.MemoryStream]::new($bytesBase);\n"
            "    $bmpBase = [System.Drawing.Bitmap]::new($msBase);\n"
            "    \n"
            f"    $sw = [System.Diagnostics.Stopwatch]::StartNew();\n"
            f"    $timeoutMs = {int(timeout_ms)};\n"
            f"    $minDiff = {float(min_diff_pct)};\n"
            f"    $pollMs = {int(poll_interval_ms)};\n"
            "    $changed = $false;\n"
            "    $lastDiff = 0.0;\n"
            "    \n"
            "    while ($sw.ElapsedMilliseconds -lt $timeoutMs) {\n"
            "        Start-Sleep -Milliseconds $pollMs;\n"
            "        [Win32WindowCore]::GetWindowRect($hWnd, [ref]$rect) | Out-Null;\n"
            "        $cw = [Math]::Max(10, $rect.Right - $rect.Left);\n"
            "        $ch = [Math]::Max(10, $rect.Bottom - $rect.Top);\n"
            "        [Win32ScreenCore]::CaptureScreen($curPath, $rect.Left, $rect.Top, $cw, $ch) | Out-Null;\n"
            "        if (Test-Path $curPath) {\n"
            "            $bytesCur = [System.IO.File]::ReadAllBytes($curPath);\n"
            "            $msCur = [System.IO.MemoryStream]::new($bytesCur);\n"
            "            $bmpCur = [System.Drawing.Bitmap]::new($msCur);\n"
            "            $lastDiff = Compare-WindowBitmaps $bmpBase $bmpCur;\n"
            "            $bmpCur.Dispose();\n"
            "            $msCur.Dispose();\n"
            "            if ($lastDiff -ge $minDiff) {\n"
            "                $changed = $true;\n"
            "                break;\n"
            "            };\n"
            "        };\n"
            "    };\n"
            "    \n"
            "    $bmpBase.Dispose();\n"
            "    $msBase.Dispose();\n"
            "    \n"
            "    @{\n"
            "        Success = $True;\n"
            "        StateChanged = $changed;\n"
            "        ElapsedMs = $sw.ElapsedMilliseconds;\n"
            "        DiffPercentage = $lastDiff;\n"
            "        ThresholdPercentage = $minDiff;\n"
            "        WindowTitle = $foundTitle;\n"
            "    } | ConvertTo-Json -Compress;\n"
            "} catch {\n"
            "    @{ Success = $False; Error = $_.Exception.Message } | ConvertTo-Json -Compress;\n"
            "} finally {\n"
            "    try { if (Test-Path $basePath) { [System.IO.File]::Delete($basePath) } } catch {};\n"
            "    try { if (Test-Path $curPath) { [System.IO.File]::Delete($curPath) } } catch {};\n"
            "}\n"
        )
        return script
