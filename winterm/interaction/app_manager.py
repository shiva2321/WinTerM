"""Windows Application Manager: Universal discovery, launching, and lifecycle management."""

import json
from typing import Optional, Dict, Any, List


class WindowsAppManager:
    """Discovers, launches, and manages applications on Windows across Win32, UWP/Store, and URI schemes."""

    @classmethod
    def build_search_command(cls, query: Optional[str] = None, limit: int = 50) -> str:
        """Generates PowerShell command to search for installed applications across shell:AppsFolder, Start Menu, and Registry."""
        safe_limit = max(1, min(int(limit), 500))
        clean_q = str(query).replace("'", "''") if query else ""
        filter_expr = f"$_.Name -like '*{clean_q}*' -or $_.Target -like '*{clean_q}*'" if query else "$True"

        # PowerShell script scanning shell:AppsFolder, Start Menu lnk files, and App Paths registry keys
        script = (
            "$apps = [System.Collections.Generic.List[PSCustomObject]]::new(); "
            "$seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase); "
            # 1. shell:AppsFolder (covers modern UWP, packaged apps, and desktop apps)
            "try { "
            "    $shell = New-Object -ComObject Shell.Application; "
            "    $folder = $shell.NameSpace('shell:AppsFolder'); "
            "    if ($folder) { "
            "        foreach ($item in $folder.Items()) { "
            "            $name = $item.Name; "
            "            $path = $item.Path; "
            "            if ($name -and -not $seen.Contains($name)) { "
            "                [void]$seen.Add($name); "
            "                $appType = if ($path -match '^[A-Za-z0-9._-]+![A-Za-z0-9._-]+') { 'UWP' } else { 'Desktop' }; "
            "                $apps.Add([PSCustomObject]@{ Name = $name; Target = $path; Source = 'AppsFolder'; Type = $appType }); "
            "            } "
            "        } "
            "    } "
            "} catch {}; "
            # 2. Start Menu Shortcuts (.lnk)
            "$startDirs = @( "
            "    [System.IO.Path]::Combine($env:ProgramData, 'Microsoft\\Windows\\Start Menu\\Programs'), "
            "    [System.IO.Path]::Combine($env:AppData, 'Microsoft\\Windows\\Start Menu\\Programs') "
            "); "
            "foreach ($dir in $startDirs) { "
            "    if (Test-Path $dir) { "
            "        Get-ChildItem -Path $dir -Filter '*.lnk' -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object { "
            "            $baseName = $_.BaseName; "
            "            if (-not $seen.Contains($baseName)) { "
            "                [void]$seen.Add($baseName); "
            "                $apps.Add([PSCustomObject]@{ Name = $baseName; Target = $_.FullName; Source = 'StartMenu'; Type = 'Shortcut' }); "
            "            } "
            "        } "
            "    } "
            "} "
            # 3. Registry App Paths
            "$regPaths = @( "
            "    'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths', "
            "    'HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths' "
            "); "
            "foreach ($reg in $regPaths) { "
            "    if (Test-Path $reg) { "
            "        Get-ChildItem -Path $reg -ErrorAction SilentlyContinue | ForEach-Object { "
            "            $appName = $_.PSChildName; "
            "            $exePath = (Get-ItemProperty -Path $_.PSPath -Name '(default)' -ErrorAction SilentlyContinue).'(default)'; "
            "            if ($appName -and $exePath -and -not $seen.Contains($appName)) { "
            "                [void]$seen.Add($appName); "
            "                $apps.Add([PSCustomObject]@{ Name = $appName; Target = $exePath; Source = 'Registry'; Type = 'Executable' }); "
            "            } "
            "        } "
            "    } "
            "} "
            # Filter and output JSON
            f"$results = $apps | Where-Object {{ {filter_expr} }} | Select-Object -First {safe_limit}; "
            "@($results) | ConvertTo-Json -Compress"
        )
        return script

    @classmethod
    def build_launch_command(
        cls,
        target: str,
        arguments: Optional[str] = None,
        elevated: bool = False,
        args: Optional[str] = None,
    ) -> str:
        """Generates PowerShell command to launch any Windows application (Win32, UWP, or Protocol URI)."""
        effective_args = args if args is not None else arguments
        # Clean target string
        sanitized_target = target.replace("'", "''")
        sanitized_args = effective_args.replace("'", "''") if effective_args else ""
        args_clause = f"-ArgumentList '{sanitized_args}'" if effective_args else ""
        verb_clause = "-Verb RunAs" if elevated else ""

        # Logic handles:
        # - Direct UWP Package / AppUserModelId
        # - shell:AppsFolder prefix
        # - URI schemes (e.g. calculator:, ms-settings:)
        # - Regular executable or shortcut
        script = (
            f"$rawTarget = '{sanitized_target}'; "
            f"$rawArgs = '{sanitized_args}'; "
            "try { "
            "    $proc = $null; "
            "    $interactiveLaunched = $false; "
            "    if (-not ('" + str(elevated).lower() + "' -eq 'true') -and ($rawTarget -notlike 'http*') -and ($rawTarget -notlike 'shell:*') -and ($rawTarget -notmatch '^[a-zA-Z0-9.-]+://') -and ($rawTarget -notmatch '^[a-zA-Z0-9.-]+:$')) { "
            "        $tn = 'WinTerm_' + [System.IO.Path]::GetRandomFileName().Substring(0,8); "
            "        $cleanTarget = $rawTarget.Replace('\"', ''); "
            "        $cleanArgs = $rawArgs.Replace('\"', ''); "
            "        $fullTarget = if ($cleanArgs) { $cleanTarget + ' ' + $cleanArgs } else { $cleanTarget }; "
            "        try { "
            "            $schCreate = 'schtasks.exe /create /tn ' + $tn + ' /tr \"\"' + $fullTarget + '\"\" /sc once /st 00:00 /it /f'; "
            "            Invoke-Expression $schCreate | Out-Null; "
            "            if ($LASTEXITCODE -eq 0) { "
            "                Invoke-Expression ('schtasks.exe /run /tn ' + $tn) | Out-Null; "
            "                Start-Sleep -Milliseconds 500; "
            "                Invoke-Expression ('schtasks.exe /delete /tn ' + $tn + ' /f') | Out-Null; "
            "                $interactiveLaunched = $true; "
            "            } "
            "        } catch {} "
            "    }; "
            "    if ($interactiveLaunched) { "
            "        @{ Success = $True; Target = $rawTarget; Mode = 'InteractiveDesktop'; Note = 'Launched on WinSta0\\Default' } | ConvertTo-Json -Compress "
            "    } elseif ($rawTarget -like 'shell:AppsFolder*' -or $rawTarget -match '^[A-Za-z0-9._-]+![A-Za-z0-9._-]+') { "
            "        $appUri = $rawTarget; "
            "        if ($rawTarget -notlike 'shell:AppsFolder*') { $appUri = 'shell:AppsFolder\\' + $rawTarget }; "
            "        $proc = Start-Process explorer.exe -ArgumentList $appUri -PassThru; "
            "        $procId = if ($proc) { $proc.Id } else { $null }; "
            "        @{ Success = $True; Target = $rawTarget; Mode = 'UWP_AppsFolder'; ProcessId = $procId } | ConvertTo-Json -Compress "
            "    } elseif ($rawTarget -match '^[a-zA-Z0-9.-]+:$' -or $rawTarget -match '^[a-zA-Z0-9.-]+://') { "
            "        $proc = Start-Process -FilePath $rawTarget -PassThru; "
            "        $procId = if ($proc) { $proc.Id } else { $null }; "
            "        @{ Success = $True; Target = $rawTarget; Mode = 'ProtocolURI'; ProcessId = $procId } | ConvertTo-Json -Compress "
            "    } else { "
            f"        $proc = Start-Process -FilePath '{sanitized_target}' {args_clause} {verb_clause} -PassThru -ErrorAction Stop; "
            "        @{ Success = $True; Target = $rawTarget; Mode = 'Process'; ProcessId = $proc.Id; ProcessName = $proc.ProcessName } | ConvertTo-Json -Compress "
            "    } "
            "} catch { "
            "    try { "
            f"        Start-Process explorer.exe -ArgumentList '\"{sanitized_target}\"'; "
            "        @{ Success = $True; Target = $rawTarget; Mode = 'ExplorerFallback'; Note = 'Launched via ShellExecute fallback' } | ConvertTo-Json -Compress "
            "    } catch { "
            "        @{ Success = $False; Target = $rawTarget; Error = $_.Exception.Message } | ConvertTo-Json -Compress "
            "    } "
            "}"
        )
        return script

    @classmethod
    def build_close_command(cls, target: str, force: bool = False) -> str:
        """Generates PowerShell command to close an application gracefully or forcefully."""
        sanitized_target = target.replace("'", "''")
        script = (
            f"$target = '{sanitized_target}'; "
            "$procs = @(); "
            "if ($target -match '^\\d+$') { "
            "    $p = Get-Process -Id ([int]$target) -ErrorAction SilentlyContinue; "
            "    if ($p) { $procs += $p }; "
            "} else { "
            "    $name = $target.Replace('.exe', ''); "
            "    $procs = Get-Process -Name $name -ErrorAction SilentlyContinue; "
            "    if (-not $procs) { "
            "        $procs = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like \"*$target*\" }; "
            "    } "
            "}; "
            "if (-not $procs) { "
            "    @{ Success = $False; Target = $target; Error = 'No matching processes found' } | ConvertTo-Json -Compress; "
            "} else { "
            "    $closed = @(); "
            "    foreach ($p in $procs) { "
            f"        if ({'$True' if force else '$False'}) {{ "
            "            $p | Stop-Process -Force -ErrorAction SilentlyContinue; "
            "            $closed += @{ Id = $p.Id; ProcessName = $p.ProcessName; Method = 'ForceKill' }; "
            "        } else { "
            "            $graceful = $p.CloseMainWindow(); "
            "            if ($graceful) { "
            "                $p.WaitForExit(2000) | Out-Null; "
            "                $closed += @{ Id = $p.Id; ProcessName = $p.ProcessName; Method = 'CloseMainWindow' }; "
            "            } else { "
            "                $p | Stop-Process -Force -ErrorAction SilentlyContinue; "
            "                $closed += @{ Id = $p.Id; ProcessName = $p.ProcessName; Method = 'ForceKillFallback' }; "
            "            } "
            "        } "
            "    }; "
            "    @{ Success = $True; Target = $target; ClosedCount = $closed.Count; Details = $closed } | ConvertTo-Json -Compress; "
            "}"
        )
        return script

    # Aliases for convenience
    generate_search_installed_apps = build_search_command
    generate_launch_app = build_launch_command
    generate_close_app = build_close_command
