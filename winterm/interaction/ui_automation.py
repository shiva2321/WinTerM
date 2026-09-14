"""Windows UI Automation Engine: Inspects controls, invokes buttons, and inputs values via System.Windows.Automation."""

import json
from typing import Optional, Dict, Any, List
from winterm.interaction.window_manager import WindowManager
from winterm.interaction.mouse import MouseEngine
from winterm.interaction.keyboard import KeyboardEngine


class UIAutomationEngine:
    """Automates and inspects graphical user interface elements across Windows desktop applications."""

    UIA_HEADER = (
        f"{WindowManager.WIN32_WINDOW_HELPER}\n"
        f"{MouseEngine.WIN32_MOUSE_HEADER}\n"
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
            "try { "
            "    $elem = [System.Windows.Automation.AutomationElement]::FromHandle($hWnd); "
            "    if (-not $elem) { "
            f"        @{{ Success = $False; Target = '{clean_target}'; Error = 'Could not acquire AutomationElement from window handle' }} | ConvertTo-Json -Compress; "
            "        exit 0; "
            "    }; "
            "    $descendants = $elem.FindAll( "
            "        [System.Windows.Automation.TreeScope]::Descendants, "
            "        [System.Windows.Automation.Condition]::TrueCondition "
            "    ); "
            "    $items = [System.Collections.Generic.List[PSCustomObject]]::new(); "
            "    foreach ($d in $descendants) { "
            "        if ($items.Count -ge " + str(max_items) + ") { break }; "
            "        try { "
            "            $cur = $d.Current; "
            "            $name = $cur.Name; "
            "            $autoId = $cur.AutomationId; "
            "            $ctrlType = $cur.ControlType.ProgrammaticName.Replace('ControlType.', ''); "
            "            $rc = $cur.BoundingRectangle; "
            "            if ($name -or $autoId) { "
            "                $hasWidth = $rc.Width -gt 1; "
            "                $hasHeight = $rc.Height -gt 1; "
            "                $centerX = if ($hasWidth) { [int]($rc.X + ($rc.Width / 2)) } else { $null }; "
            "                $centerY = if ($hasHeight) { [int]($rc.Y + ($rc.Height / 2)) } else { $null }; "
            "                $items.Add([PSCustomObject]@{ "
            "                    Name = $name; "
            "                    AutomationId = $autoId; "
            "                    ControlType = $ctrlType; "
            "                    ClassName = $cur.ClassName; "
            "                    IsEnabled = $cur.IsEnabled; "
            "                    X = [int]$rc.X; "
            "                    Y = [int]$rc.Y; "
            "                    Width = [int]$rc.Width; "
            "                    Height = [int]$rc.Height; "
            "                    CenterX = $centerX; "
            "                    CenterY = $centerY; "
            "                }); "
            "            } "
            "        } catch {} "
            "    }; "
            "    @{ Success = $True; WindowTitle = $foundTitle; WindowHandle = $hWnd.ToInt64(); ElementCount = $items.Count; Elements = $items } | ConvertTo-Json -Compress -Depth 4 "
            "} catch { "
            "    @{ Success = $False; WindowTitle = $foundTitle; WindowHandle = $hWnd.ToInt64(); Error = $_.Exception.Message } | ConvertTo-Json -Compress "
            "}"
        )
        return script

    @classmethod
    def build_click_element_command(cls, window_identifier: str, element_query: str) -> str:
        """Generates PowerShell command to click a UI element by name or automation ID using InvokePattern or coordinates."""
        clean_target = window_identifier.replace("'", "''")
        clean_elem = element_query.replace("'", "''")
        script = (
            f"{cls.UIA_HEADER}"
            "$foundTitle = ''; "
            f"$hWnd = [Win32WindowCore]::ResolveWindow('{clean_target}', [ref]$foundTitle); "
            "if ($hWnd -eq [IntPtr]::Zero) { "
            f"    @{{ Success = $False; Target = '{clean_target}'; Error = 'Window not found' }} | ConvertTo-Json -Compress; "
            "    exit 0; "
            "}; "
            "[Win32WindowCore]::ForceForeground($hWnd) | Out-Null; "
            "Start-Sleep -Milliseconds 200; "
            "try { "
            "    $root = [System.Windows.Automation.AutomationElement]::FromHandle($hWnd); "
            "    $all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition); "
            "    $matched = $null; "
            "    foreach ($item in $all) { "
            "        try { "
            "            $cur = $item.Current; "
            f"            if ($cur.Name -like '*{clean_elem}*' -or $cur.AutomationId -like '*{clean_elem}*') {{ "
            "                $matched = $item; "
            "                break; "
            "            } "
            "        } catch {} "
            "    }; "
            "    if (-not $matched) { "
            f"        @{{ Success = $False; ElementQuery = '{clean_elem}'; Error = 'Element not found in window tree' }} | ConvertTo-Json -Compress; "
            "        exit 0; "
            "    }; "
            "    $methodUsed = 'InvokePattern'; "
            "    $invoked = $false; "
            "    try { "
            "        $pattern = $matched.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern); "
            "        if ($pattern) { "
            "            $pattern.Invoke(); "
            "            $invoked = $true; "
            "        } "
            "    } catch {}; "
            "    if (-not $invoked) { "
            "        $methodUsed = 'CoordinateClick'; "
            "        $rc = $matched.Current.BoundingRectangle; "
            "        $clickX = [int]($rc.X + ($rc.Width / 2)); "
            "        $clickY = [int]($rc.Y + ($rc.Height / 2)); "
            "        [Win32MouseCore]::SetCursorPos($clickX, $clickY) | Out-Null; "
            "        Start-Sleep -Milliseconds 100; "
            "        [Win32MouseCore]::mouse_event(0x02, 0, 0, 0, 0); "  # LEFTDOWN
            "        Start-Sleep -Milliseconds 50; "
            "        [Win32MouseCore]::mouse_event(0x04, 0, 0, 0, 0); "  # LEFTUP
            "    }; "
            "    @{ Success = $True; Method = $methodUsed; Element = $matched.Current.Name; AutomationId = $matched.Current.AutomationId } | ConvertTo-Json -Compress "
            "} catch { "
            "    @{ Success = $False; Error = $_.Exception.Message } | ConvertTo-Json -Compress "
            "}"
        )
        return script

    @classmethod
    def build_set_element_text_command(cls, window_identifier: str, element_query: str, text: str) -> str:
        """Generates PowerShell command to set the text of an Edit or Input control via ValuePattern or SendKeys."""
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
            "[Win32WindowCore]::ForceForeground($hWnd) | Out-Null; "
            "Start-Sleep -Milliseconds 200; "
            "try { "
            "    $root = [System.Windows.Automation.AutomationElement]::FromHandle($hWnd); "
            "    $all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition); "
            "    $matched = $null; "
            "    foreach ($item in $all) { "
            "        try { "
            "            $cur = $item.Current; "
            f"            if ($cur.Name -like '*{clean_elem}*' -or $cur.AutomationId -like '*{clean_elem}*') {{ "
            "                $matched = $item; "
            "                break; "
            "            } "
            "        } catch {} "
            "    }; "
            "    if (-not $matched) { "
            f"        @{{ Success = $False; ElementQuery = '{clean_elem}'; Error = 'Element not found in window tree' }} | ConvertTo-Json -Compress; "
            "        exit 0; "
            "    }; "
            "    # Attempt ValuePattern first "
            "    $methodUsed = 'ValuePattern'; "
            "    $setDone = $false; "
            "    try { "
            "        $valPattern = $matched.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern); "
            "        if ($valPattern) { "
            f"            $valPattern.SetValue('{raw_text}'); "
            "            $setDone = $true; "
            "        } "
            "    } catch {}; "
            "    if (-not $setDone) { "
            "        # Fallback to SetFocus + SendKeys "
            "        $methodUsed = 'FocusAndSendKeys'; "
            "        try { $matched.SetFocus() } catch { "
            "            $rc = $matched.Current.BoundingRectangle; "
            "            $clickX = [int]($rc.X + ($rc.Width / 2)); "
            "            $clickY = [int]($rc.Y + ($rc.Height / 2)); "
            "            [Win32MouseCore]::SetCursorPos($clickX, $clickY) | Out-Null; "
            "            [Win32MouseCore]::mouse_event(0x02, 0, 0, 0, 0); "
            "            [Win32MouseCore]::mouse_event(0x04, 0, 0, 0, 0); "
            "        }; "
            "        Start-Sleep -Milliseconds 150; "
            f"        [System.Windows.Forms.SendKeys]::SendWait('{escaped_text}'); "
            "    }; "
            f"    @{{ Success = $True; Method = $methodUsed; Element = $matched.Current.Name; Value = '{raw_text}' }} | ConvertTo-Json -Compress "
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
