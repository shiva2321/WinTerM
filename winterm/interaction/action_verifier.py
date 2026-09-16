"""Action Verifier: Before/after window-snapshot pixel diff to confirm actions had visible effect.

Used as a post-action verification gate: capture before, perform action, capture after,
compare. Reports ChangePercent, ChangedRegion, and Verdict (Changed / Unchanged / Error).
Window-scoped capture prevents false positives from unrelated screen activity.
"""

import json
from typing import Optional
from winterm.interaction.window_manager import WindowManager
from winterm.interaction.screen import ScreenPerceptionEngine


class ActionVerifier:
    """Captures before/after screenshots of a specific window and diffs them for change detection."""

    GDI_DIFF_HELPER = (
        "Add-Type -AssemblyName System.Drawing;\n"
        "function Compare-WindowSnapshots($beforePath, $afterPath) {\n"
        "    $b1Bytes = [System.IO.File]::ReadAllBytes($beforePath);\n"
        "    $b2Bytes = [System.IO.File]::ReadAllBytes($afterPath);\n"
        "    $ms1 = [System.IO.MemoryStream]::new($b1Bytes);\n"
        "    $ms2 = [System.IO.MemoryStream]::new($b2Bytes);\n"
        "    $bmp1 = [System.Drawing.Bitmap]::new($ms1);\n"
        "    $bmp2 = [System.Drawing.Bitmap]::new($ms2);\n"
        "    $w = [Math]::Min($bmp1.Width, $bmp2.Width);\n"
        "    $h = [Math]::Min($bmp1.Height, $bmp2.Height);\n"
        "    $total = $w * $h;\n"
        "    if ($total -eq 0) { return @{ Error = 'Empty image' } };\n"
        "    $changed = 0;\n"
        "    $minX = $w; $minY = $h; $maxX = 0; $maxY = 0;\n"
        "    # Sample every 4th pixel for speed (sufficient for UI change detection)\n"
        "    $step = 4;\n"
        "    $sampled = 0;\n"
        "    for ($y = 0; $y -lt $h; $y += $step) {\n"
        "        for ($x = 0; $x -lt $w; $x += $step) {\n"
        "            $p1 = $bmp1.GetPixel($x, $y);\n"
        "            $p2 = $bmp2.GetPixel($x, $y);\n"
        "            $sampled++;\n"
        "            $dr = [Math]::Abs($p1.R - $p2.R);\n"
        "            $dg = [Math]::Abs($p1.G - $p2.G);\n"
        "            $db = [Math]::Abs($p1.B - $p2.B);\n"
        "            if (($dr + $dg + $db) -gt 30) {\n"  # threshold: >30 total channel delta
        "                $changed++;\n"
        "                if ($x -lt $minX) { $minX = $x };\n"
        "                if ($y -lt $minY) { $minY = $y };\n"
        "                if ($x -gt $maxX) { $maxX = $x };\n"
        "                if ($y -gt $maxY) { $maxY = $y };\n"
        "            };\n"
        "        };\n"
        "    };\n"
        "    $bmp1.Dispose(); $bmp2.Dispose();\n"
        "    $ms1.Dispose(); $ms2.Dispose();\n"
        "    $pct = if ($sampled -gt 0) { [Math]::Round(100.0 * $changed / $sampled, 2) } else { 0 };\n"
        "    $region = if ($changed -gt 0) { @{ Left=$minX; Top=$minY; Right=$maxX; Bottom=$maxY } } else { $null };\n"
        "    return @{\n"
        "        SampledPixels   = $sampled;\n"
        "        ChangedPixels   = $changed;\n"
        "        ChangePercent   = $pct;\n"
        "        Changed         = ($pct -ge 0.5);\n"  # >=0.5% change = meaningful
        "        ChangedRegion   = $region;\n"
        "    };\n"
        "}\n"
    )

    @classmethod
    def build_capture_window_snapshot_command(
        cls,
        window_identifier: str,
        output_path: str,
    ) -> str:
        """Captures a screenshot of only the target window (window-scoped, not full-screen)."""
        clean_target = window_identifier.replace("'", "''")
        clean_output = output_path.replace("'", "''").replace('"', '""')
        script = (
            f"{WindowManager.WIN32_WINDOW_HELPER}\n"
            f"{ScreenPerceptionEngine.WIN32_SCREEN_HEADER}\n"
            "$foundTitle = '';\n"
            f"$hWnd = [Win32WindowCore]::ResolveWindow('{clean_target}', [ref]$foundTitle);\n"
            "if ($hWnd -eq [IntPtr]::Zero) {\n"
            f"    @{{ Success = $False; Error = 'Window not found: {clean_target}' }} | ConvertTo-Json -Compress;\n"
            "    exit 0;\n"
            "};\n"
            "$rect = New-Object Win32WindowCore+RECT;\n"
            "[Win32WindowCore]::GetWindowRect($hWnd, [ref]$rect) | Out-Null;\n"
            "$w = [Math]::Max(10, $rect.Right - $rect.Left);\n"
            "$h = [Math]::Max(10, $rect.Bottom - $rect.Top);\n"
            f"$ok = [Win32ScreenCore]::CaptureScreen('{clean_output}', $rect.Left, $rect.Top, $w, $h);\n"
            "@{\n"
            "    Success       = $ok;\n"
            "    WindowTitle   = $foundTitle;\n"
            "    WindowHandle  = $hWnd.ToInt64();\n"
            f"    OutputPath    = '{clean_output}';\n"
            "    Width         = $w;\n"
            "    Height        = $h;\n"
            "} | ConvertTo-Json -Compress\n"
        )
        return script

    @classmethod
    def build_diff_snapshots_command(
        cls,
        before_path: str,
        after_path: str,
        window_identifier: Optional[str] = None,
    ) -> str:
        """Pixel-diffs two window snapshots and returns ChangePercent, ChangedRegion, and Changed bool.

        A ChangePercent >= 0.5 is considered a meaningful UI change (action had visible effect).
        """
        clean_before = before_path.replace("'", "''")
        clean_after = after_path.replace("'", "''")
        script = (
            f"{cls.GDI_DIFF_HELPER}\n"
            f"$result = Compare-WindowSnapshots '{clean_before}' '{clean_after}';\n"
            "$verdict = if ($result.Error) { 'Error' } elseif ($result.Changed) { 'Changed' } else { 'Unchanged' };\n"
            "@{\n"
            "    Success         = (-not $result.Error);\n"
            "    Verdict         = $verdict;\n"
            "    Error           = $result.Error;\n"
            "    Changed         = [bool]$result.Changed;\n"
            "    ChangePercent   = $result.ChangePercent;\n"
            "    SampledPixels   = $result.SampledPixels;\n"
            "    ChangedPixels   = $result.ChangedPixels;\n"
            "    ChangedRegion   = $result.ChangedRegion;\n"
            f"    BeforePath      = '{clean_before}';\n"
            f"    AfterPath       = '{clean_after}';\n"
            "} | ConvertTo-Json -Compress -Depth 4\n"
        )
        return script

    # Convenience aliases
    generate_capture_snapshot = build_capture_window_snapshot_command
    generate_diff_snapshots = build_diff_snapshots_command
