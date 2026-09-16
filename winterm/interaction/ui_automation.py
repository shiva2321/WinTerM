"""Windows UI Automation Engine: Inspects controls, invokes buttons, and inputs values via System.Windows.Automation."""

import json
from typing import Optional, Dict, Any, List
from winterm.interaction.window_manager import WindowManager
from winterm.interaction.mouse import MouseEngine
from winterm.interaction.keyboard import KeyboardEngine
from winterm.interaction.screen import ScreenPerceptionEngine
from winterm.interaction.ocr_engine import WindowsOCREngine


class UIAutomationEngine:
    """Automates and inspects graphical user interface elements across Windows desktop applications."""

    UIA_HEADER = (
        f"{WindowManager.WIN32_WINDOW_HELPER}\n"
        f"{MouseEngine.WIN32_MOUSE_HEADER}\n"
        f"{ScreenPerceptionEngine.WIN32_SCREEN_HEADER}\n"
        f"{WindowsOCREngine.WINRT_OCR_HELPER}\n"
        "Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes, System.Windows.Forms;\n"
    )

    @classmethod
    def build_inspect_elements_command(cls, window_identifier: str, max_items: int = 100) -> str:
        """Generates PowerShell command to inspect all interactive UI Automation elements inside a window."""
        clean_target = window_identifier.replace("'", "''")
        script = (
            f"{cls.UIA_HEADER}"
            "$foundTitle = ''; "
            f"$hWnd = [Win32WindowCore]::ResolveWindow('{clean_target}', [ref]$foundTitle); "
            "if ($hWnd -eq [IntPtr]::Zero) { "
            f"    @{{ Success = $False; Target = '{clean_target}'; Error = 'Window not found' }} | ConvertTo-Json -Compress; "
            "    exit 0; "
            "}; "
            "$items = [System.Collections.Generic.List[PSCustomObject]]::new(); "
            "try { "
            "    $elem = [System.Windows.Automation.AutomationElement]::FromHandle($hWnd); "
            "    if ($elem) { "
            "        $descendants = $elem.FindAll( "
            "            [System.Windows.Automation.TreeScope]::Descendants, "
            "            [System.Windows.Automation.Condition]::TrueCondition "
            "        ); "
            "        foreach ($d in $descendants) { "
            "            if ($items.Count -ge " + str(max_items) + ") { break }; "
            "            try { "
            "                $cur = $d.Current; "
            "                $name = $cur.Name; "
            "                $autoId = $cur.AutomationId; "
            "                $ctrlType = $cur.ControlType.ProgrammaticName.Replace('ControlType.', ''); "
            "                $rc = $cur.BoundingRectangle; "
            "                if ($name -or $autoId) { "
            "                    $hasWidth = $rc.Width -gt 1; "
            "                    $hasHeight = $rc.Height -gt 1; "
            "                    $centerX = if ($hasWidth) { [int]($rc.X + ($rc.Width / 2)) } else { $null }; "
            "                    $centerY = if ($hasHeight) { [int]($rc.Y + ($rc.Height / 2)) } else { $null }; "
            "                    $items.Add([PSCustomObject]@{ "
            "                        Name = $name; "
            "                        AutomationId = $autoId; "
            "                        ControlType = $ctrlType; "
            "                        ClassName = $cur.ClassName; "
            "                        IsEnabled = $cur.IsEnabled; "
            "                        X = [int]$rc.X; "
            "                        Y = [int]$rc.Y; "
            "                        Width = [int]$rc.Width; "
            "                        Height = [int]$rc.Height; "
            "                        CenterX = $centerX; "
            "                        CenterY = $centerY; "
            "                    }); "
            "                } "
            "            } catch {} "
            "        }; "
            "    }; "
            "} catch {}; "
            "if ($items.Count -eq 0) { "
            "    try { "
            "        $rect = New-Object Win32WindowCore+RECT; "
            "        [Win32WindowCore]::GetWindowRect($hWnd, [ref]$rect) | Out-Null; "
            "        $w = [Math]::Max(10, $rect.Right - $rect.Left); "
            "        $h = [Math]::Max(10, $rect.Bottom - $rect.Top); "
            "        $tempOcr = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), ('winterm_inspect_' + [System.Guid]::NewGuid().ToString('N') + '.png')); "
            "        $cap = [Win32ScreenCore]::CaptureScreen($tempOcr, $rect.Left, $rect.Top, $w, $h); "
            "        if ($cap -and (Test-Path $tempOcr)) { "
            "            $file = Await-WinRT ([Windows.Storage.StorageFile]::GetFileFromPathAsync($tempOcr)) ([Windows.Storage.StorageFile]); "
            "            $stream = Await-WinRT ($file.OpenAsync(0)) ([Windows.Storage.Streams.IRandomAccessStream]); "
            "            $decoder = Await-WinRT ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder]); "
            "            $softwareBitmap = Await-WinRT ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap]); "
            "            $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages(); "
            "            if ($engine) { "
            "                $ocrRes = Await-WinRT ($engine.RecognizeAsync($softwareBitmap)) ([Windows.Media.Ocr.OcrResult]); "
            "                foreach ($line in $ocrRes.Lines) { "
            "                    if ($items.Count -ge " + str(max_items) + ") { break }; "
            "                    if (-not $line.Text) { continue }; "
            "                    $minX = $w; $minY = $h; $maxX = 0; $maxY = 0; "
            "                    foreach ($wItem in $line.Words) { "
            "                        $wrc = $wItem.BoundingRect; "
            "                        if ($wrc.X -lt $minX) { $minX = [int]$wrc.X }; "
            "                        if ($wrc.Y -lt $minY) { $minY = [int]$wrc.Y }; "
            "                        if (($wrc.X + $wrc.Width) -gt $maxX) { $maxX = [int]($wrc.X + $wrc.Width) }; "
            "                        if (($wrc.Y + $wrc.Height) -gt $maxY) { $maxY = [int]($wrc.Y + $wrc.Height) }; "
            "                    }; "
            "                    $boxW = [Math]::Max(10, $maxX - $minX); "
            "                    $boxH = [Math]::Max(10, $maxY - $minY); "
            "                    $items.Add([PSCustomObject]@{ "
            "                        Name = $line.Text; "
            "                        AutomationId = ''; "
            "                        ControlType = 'VisualText'; "
            "                        ClassName = 'RenderedText'; "
            "                        IsEnabled = $true; "
            "                        X = [int]($rect.Left + $minX); "
            "                        Y = [int]($rect.Top + $minY); "
            "                        Width = $boxW; "
            "                        Height = $boxH; "
            "                        CenterX = [int]($rect.Left + $minX + ($boxW / 2)); "
            "                        CenterY = [int]($rect.Top + $minY + ($boxH / 2)); "
            "                    }); "
            "                }; "
            "            }; "
            "        }; "
            "        try { if (Test-Path $tempOcr) { [System.IO.File]::Delete($tempOcr) } } catch {}; "
            "    } catch {}; "
            "}; "
            "@{ Success = $True; WindowTitle = $foundTitle; WindowHandle = $hWnd.ToInt64(); ElementCount = $items.Count; Elements = $items } | ConvertTo-Json -Compress -Depth 4 "
        )
        return script

    @classmethod
    def build_click_element_command(cls, window_identifier: str, element_query: str) -> str:
        """Generates PowerShell command to click a UI element with verified focus, UIA, and OCR fallback."""
        from winterm.interaction.smart_resolver import SmartUIResolver
        return SmartUIResolver.build_smart_click_command(window_identifier, element_query)

    @classmethod
    def build_set_element_text_command(cls, window_identifier: str, element_query: str, text: str) -> str:
        """Generates PowerShell command to set the text of an Edit or Input control via ValuePattern or OCR-located focus + SendKeys."""
        clean_target = window_identifier.replace("'", "''")
        clean_elem = element_query.replace("'", "''")
        escaped_text = KeyboardEngine.escape_for_sendkeys(text).replace("'", "''")
        raw_text = text.replace("'", "''")

        script = (
            f"{cls.UIA_HEADER}"
            "$foundTitle = ''; "
            f"$hWnd = [Win32WindowCore]::ResolveWindow('{clean_target}', [ref]$foundTitle); "
            "if ($hWnd -eq [IntPtr]::Zero) { "
            f"    @{{ Success = $False; Target = '{clean_target}'; Error = 'Window not found' }} | ConvertTo-Json -Compress; "
            "    exit 0; "
            "}; "
            "$fgRes = [Win32WindowCore]::ForceForegroundVerified($hWnd); "
            "Start-Sleep -Milliseconds 150; "
            "try { "
            "    $matched = $null; "
            "    try { "
            "        $root = [System.Windows.Automation.AutomationElement]::FromHandle($hWnd); "
            "        if ($root) { "
            "            $all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition); "
            "            foreach ($item in $all) { "
            "                try { "
            "                    $cur = $item.Current; "
            f"                    if ($cur.Name -like '*{clean_elem}*' -or $cur.AutomationId -like '*{clean_elem}*') {{ "
            "                        $matched = $item; "
            "                        break; "
            "                    } "
            "                } catch {} "
            "            }; "
            "        } "
            "    } catch {}; "
            "    if ($matched) { "
            "        $methodUsed = 'ValuePattern'; "
            "        $setDone = $false; "
            "        try { "
            "            $valPattern = $matched.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern); "
            "            if ($valPattern) { "
            f"                $valPattern.SetValue('{raw_text}'); "
            "                $setDone = $true; "
            "            } "
            "        } catch {}; "
            "        if (-not $setDone) { "
            "            $methodUsed = 'FocusAndSendKeys'; "
            "            $rc = $matched.Current.BoundingRectangle; "
            "            $rect2 = New-Object Win32WindowCore+RECT; "
            "            [Win32WindowCore]::GetWindowRect($hWnd, [ref]$rect2) | Out-Null; "
            "            $relX = [int]($rc.X - $rect2.Left + ($rc.Width / 2)); "
            "            $relY = [int]($rc.Y - $rect2.Top + ($rc.Height / 2)); "
            "            [Win32MouseCore]::ClickInWindow($hWnd, $relX, $relY, 0x0002, 0x0004, 1) | Out-Null; "
            "            Start-Sleep -Milliseconds 150; "
            f"            [System.Windows.Forms.SendKeys]::SendWait('{escaped_text}'); "
            "        }; "
            f"        @{{ Success = $True; Method = $methodUsed; Element = $matched.Current.Name; Value = '{raw_text}'; FocusConfirmed = $fgRes.FocusConfirmed }} | ConvertTo-Json -Compress; "
            "        exit 0; "
            "    }; "
            "    $rect = New-Object Win32WindowCore+RECT; "
            "    [Win32WindowCore]::GetWindowRect($hWnd, [ref]$rect) | Out-Null; "
            "    $w = [Math]::Max(10, $rect.Right - $rect.Left); "
            "    $h = [Math]::Max(10, $rect.Bottom - $rect.Top); "
            "    $tempOcr = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), ('winterm_settext_' + [System.Guid]::NewGuid().ToString('N') + '.png')); "
            "    $targetRelX = -1; $targetRelY = -1; "
            "    try { "
            "        $cap = [Win32ScreenCore]::CaptureScreen($tempOcr, $rect.Left, $rect.Top, $w, $h); "
            "        if ($cap -and (Test-Path $tempOcr)) { "
            "            $file = Await-WinRT ([Windows.Storage.StorageFile]::GetFileFromPathAsync($tempOcr)) ([Windows.Storage.StorageFile]); "
            "            $stream = Await-WinRT ($file.OpenAsync(0)) ([Windows.Storage.Streams.IRandomAccessStream]); "
            "            $decoder = Await-WinRT ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder]); "
            "            $softwareBitmap = Await-WinRT ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap]); "
            "            $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages(); "
            "            if ($engine) { "
            "                $ocrRes = Await-WinRT ($engine.RecognizeAsync($softwareBitmap)) ([Windows.Media.Ocr.OcrResult]); "
            "                foreach ($line in $ocrRes.Lines) { "
            f"                    if ($line.Text -like '*{clean_elem}*' -or '{clean_elem}' -like ('*' + $line.Text + '*')) {{ "
            "                        $minX = $w; $minY = $h; $maxX = 0; $maxY = 0; "
            "                        foreach ($wItem in $line.Words) { "
            "                            $wrc = $wItem.BoundingRect; "
            "                            if ($wrc.X -lt $minX) { $minX = [int]$wrc.X }; "
            "                            if ($wrc.Y -lt $minY) { $minY = [int]$wrc.Y }; "
            "                            if (($wrc.X + $wrc.Width) -gt $maxX) { $maxX = [int]($wrc.X + $wrc.Width) }; "
            "                            if (($wrc.Y + $wrc.Height) -gt $maxY) { $maxY = [int]($wrc.Y + $wrc.Height) }; "
            "                        }; "
            "                        $targetRelX = [int]($minX + (($maxX - $minX) / 2)); "
            "                        $targetRelY = [int]($minY + (($maxY - $minY) / 2)); "
            "                        break; "
            "                    }; "
            "                }; "
            "            }; "
            "        }; "
            "    } finally { "
            "        try { if (Test-Path $tempOcr) { [System.IO.File]::Delete($tempOcr) } } catch {}; "
            "    }; "
            "    if ($targetRelX -ge 0 -and $targetRelY -ge 0) { "
            "        $cr = [Win32MouseCore]::ClickInWindow($hWnd, $targetRelX, $targetRelY, 0x0002, 0x0004, 1); "
            "        Start-Sleep -Milliseconds 150; "
            f"        [System.Windows.Forms.SendKeys]::SendWait('{escaped_text}'); "
            f"        @{{ Success = $True; Method = 'OCR.ClickInWindowAndSendKeys'; Target = '{clean_elem}'; Value = '{raw_text}'; FocusConfirmed = $fgRes.FocusConfirmed }} | ConvertTo-Json -Compress; "
            "    } else { "
            f"        @{{ Success = $False; ElementQuery = '{clean_elem}'; Error = 'Element not found in window tree or via OCR'; FocusConfirmed = $fgRes.FocusConfirmed }} | ConvertTo-Json -Compress; "
            "    }; "
            "} catch { "
            "    @{ Success = $False; Error = $_.Exception.Message } | ConvertTo-Json -Compress "
            "}"
        )
        return script

    # Aliases for convenience
    @classmethod
    def generate_inspect_window(cls, window_identifier: str = "", max_items: int = 100, max_depth: Optional[int] = None) -> str:
        return cls.build_inspect_elements_command(window_identifier, max_items=max_items)

    @classmethod
    def generate_click_element(
        cls,
        window_identifier: str,
        element_query: str = "",
        element_name: str = "",
        automation_id: str = "",
        control_type: str = "",
    ) -> str:
        query = element_query or element_name or automation_id or control_type
        return cls.build_click_element_command(window_identifier, query)

    @classmethod
    def generate_set_element_text(
        cls,
        window_identifier: str,
        text: str,
        element_query: str = "",
        element_name: str = "",
        automation_id: str = "",
        control_type: str = "",
    ) -> str:
        query = element_query or element_name or automation_id or control_type
        return cls.build_set_element_text_command(window_identifier, query, text)
