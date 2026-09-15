"""Windows Native OCR Engine: Hardware-accelerated local optical character recognition via Windows.Media.Ocr.

Leverages Windows 10/11's built-in WinRT OCR subsystem without requiring external binaries
like Tesseract or heavy Python ML dependencies. Returns recognized text lines, words,
exact bounding boxes, and computed center click targets.
"""

import json
from typing import Optional, Dict, Any, List
from winterm.interaction.window_manager import WindowManager
from winterm.interaction.screen import ScreenPerceptionEngine


class WindowsOCREngine:
    """Provides native zero-dependency Windows OCR perception for windows, images, and screens."""

    WINRT_OCR_HELPER = (
        "Add-Type -AssemblyName System.Runtime.WindowsRuntime;\n"
        "$null = [Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType = WindowsRuntime];\n"
        "$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime];\n"
        "$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime];\n"
        "$asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { "
        "    $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 "
        "} | Select-Object -First 1;\n"
        "function Await-WinRT($op, $type) {\n"
        "    $task = $asTaskGeneric.MakeGenericMethod($type).Invoke($null, @($op));\n"
        "    return $task.GetAwaiter().GetResult();\n"
        "};\n"
    )

    @classmethod
    def build_ocr_image_command(cls, image_path: str, language_tag: str = "en-US") -> str:
        """Generates PowerShell script to execute native Windows OCR on an image file."""
        clean_path = image_path.replace("'", "''").replace('"', '""')
        clean_lang = language_tag.replace("'", "''")

        script = (
            f"{cls.WINRT_OCR_HELPER}\n"
            f"$targetPath = '{clean_path}';\n"
            "if (-not (Test-Path $targetPath)) {\n"
            "    @{ Success = $False; Error = \"File not found: $targetPath\" } | ConvertTo-Json -Compress;\n"
            "    exit 0;\n"
            "};\n"
            "try {\n"
            "    $file = Await-WinRT ([Windows.Storage.StorageFile]::GetFileFromPathAsync($targetPath)) ([Windows.Storage.StorageFile]);\n"
            "    $stream = Await-WinRT ($file.OpenAsync(0)) ([Windows.Storage.Streams.IRandomAccessStream]);\n"
            "    $decoder = Await-WinRT ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder]);\n"
            "    $softwareBitmap = Await-WinRT ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap]);\n"
            "    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages();\n"
            "    if (-not $engine) {\n"
            "        $null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime];\n"
            f"        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('{clean_lang}'));\n"
            "    };\n"
            "    if (-not $engine) {\n"
            "        @{ Success = $False; Error = 'Failed to initialize Windows OCR Engine for language profile' } | ConvertTo-Json -Compress;\n"
            "        exit 0;\n"
            "    };\n"
            "    $ocrResult = Await-WinRT ($engine.RecognizeAsync($softwareBitmap)) ([Windows.Media.Ocr.OcrResult]);\n"
            "    $linesList = [System.Collections.Generic.List[PSCustomObject]]::new();\n"
            "    $allWords = [System.Collections.Generic.List[PSCustomObject]]::new();\n"
            "    foreach ($line in $ocrResult.Lines) {\n"
            "        $wordsList = [System.Collections.Generic.List[PSCustomObject]]::new();\n"
            "        foreach ($w in $line.Words) {\n"
            "            $rc = $w.BoundingRect;\n"
            "            $wObj = [PSCustomObject]@{\n"
            "                Text = $w.Text;\n"
            "                X = [int]$rc.X;\n"
            "                Y = [int]$rc.Y;\n"
            "                Width = [int]$rc.Width;\n"
            "                Height = [int]$rc.Height;\n"
            "                CenterX = [int]($rc.X + ($rc.Width / 2));\n"
            "                CenterY = [int]($rc.Y + ($rc.Height / 2));\n"
            "            };\n"
            "            $wordsList.Add($wObj);\n"
            "            $allWords.Add($wObj);\n"
            "        };\n"
            "        $linesList.Add([PSCustomObject]@{\n"
            "            Text = $line.Text;\n"
            "            Words = $wordsList;\n"
            "        });\n"
            "    };\n"
            "    @{\n"
            "        Success = $True;\n"
            "        SourcePath = $targetPath;\n"
            "        ImageWidth = $decoder.PixelWidth;\n"
            "        ImageHeight = $decoder.PixelHeight;\n"
            "        LinesCount = $linesList.Count;\n"
            "        WordsCount = $allWords.Count;\n"
            "        Text = ($linesList | ForEach-Object { $_.Text }) -join \"`n\";\n"
            "        Lines = $linesList;\n"
            "        Words = $allWords;\n"
            "    } | ConvertTo-Json -Compress -Depth 4;\n"
            "} catch {\n"
            "    @{ Success = $False; Error = $_.Exception.Message } | ConvertTo-Json -Compress;\n"
            "}\n"
        )
        return script

    @classmethod
    def build_ocr_window_command(
        cls,
        window_identifier: str,
        language_tag: str = "en-US",
        temp_dir: Optional[str] = None,
    ) -> str:
        """Captures a target window to temporary storage and performs high-precision OCR on its rendering."""
        clean_target = window_identifier.replace("'", "''")
        clean_lang = language_tag.replace("'", "''")

        script = (
            f"{WindowManager.WIN32_WINDOW_HELPER}\n"
            f"{ScreenPerceptionEngine.WIN32_SCREEN_HEADER}\n"
            f"{cls.WINRT_OCR_HELPER}\n"
            "$foundTitle = '';\n"
            f"$hWnd = [Win32WindowCore]::ResolveWindow('{clean_target}', [ref]$foundTitle);\n"
            "if ($hWnd -eq [IntPtr]::Zero) {\n"
            f"    @{{ Success = $False; Target = '{clean_target}'; Error = 'Window not found for OCR capture' }} | ConvertTo-Json -Compress;\n"
            "    exit 0;\n"
            "};\n"
            "$rect = New-Object Win32WindowCore+RECT;\n"
            "[Win32WindowCore]::GetWindowRect($hWnd, [ref]$rect) | Out-Null;\n"
            "$w = [Math]::Max(10, $rect.Right - $rect.Left);\n"
            "$h = [Math]::Max(10, $rect.Bottom - $rect.Top);\n"
            "$tempPath = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), ('winterm_ocr_' + [System.Guid]::NewGuid().ToString('N') + '.png'));\n"
            "try {\n"
            "    $captured = [Win32ScreenCore]::CaptureScreen($tempPath, $rect.Left, $rect.Top, $w, $h);\n"
            "    if (-not $captured -or -not (Test-Path $tempPath)) {\n"
            "        @{ Success = $False; Target = $foundTitle; Error = 'Failed to capture window bitmap for OCR' } | ConvertTo-Json -Compress;\n"
            "        exit 0;\n"
            "    };\n"
            "    $file = Await-WinRT ([Windows.Storage.StorageFile]::GetFileFromPathAsync($tempPath)) ([Windows.Storage.StorageFile]);\n"
            "    $stream = Await-WinRT ($file.OpenAsync(0)) ([Windows.Storage.Streams.IRandomAccessStream]);\n"
            "    $decoder = Await-WinRT ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder]);\n"
            "    $softwareBitmap = Await-WinRT ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap]);\n"
            "    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages();\n"
            "    if (-not $engine) {\n"
            "        $null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime];\n"
            f"        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('{clean_lang}'));\n"
            "    };\n"
            "    $ocrResult = Await-WinRT ($engine.RecognizeAsync($softwareBitmap)) ([Windows.Media.Ocr.OcrResult]);\n"
            "    $linesList = [System.Collections.Generic.List[PSCustomObject]]::new();\n"
            "    $allWords = [System.Collections.Generic.List[PSCustomObject]]::new();\n"
            "    foreach ($line in $ocrResult.Lines) {\n"
            "        $wordsList = [System.Collections.Generic.List[PSCustomObject]]::new();\n"
            "        foreach ($wItem in $line.Words) {\n"
            "            $rc = $wItem.BoundingRect;\n"
            "            # Compute both window-relative and global screen coordinates\n"
            "            $relX = [int]$rc.X;\n"
            "            $relY = [int]$rc.Y;\n"
            "            $wWidth = [int]$rc.Width;\n"
            "            $wHeight = [int]$rc.Height;\n"
            "            $screenCenterX = [int]($rect.Left + $relX + ($wWidth / 2));\n"
            "            $screenCenterY = [int]($rect.Top + $relY + ($wHeight / 2));\n"
            "            $wObj = [PSCustomObject]@{\n"
            "                Text = $wItem.Text;\n"
            "                RelX = $relX;\n"
            "                RelY = $relY;\n"
            "                Width = $wWidth;\n"
            "                Height = $wHeight;\n"
            "                ScreenCenterX = $screenCenterX;\n"
            "                ScreenCenterY = $screenCenterY;\n"
            "            };\n"
            "            $wordsList.Add($wObj);\n"
            "            $allWords.Add($wObj);\n"
            "        };\n"
            "        $linesList.Add([PSCustomObject]@{\n"
            "            Text = $line.Text;\n"
            "            Words = $wordsList;\n"
            "        });\n"
            "    };\n"
            "    @{\n"
            "        Success = $True;\n"
            "        WindowTitle = $foundTitle;\n"
            "        WindowHandle = $hWnd.ToInt64();\n"
            "        WindowBounds = @{ Left = $rect.Left; Top = $rect.Top; Width = $w; Height = $h };\n"
            "        LinesCount = $linesList.Count;\n"
            "        WordsCount = $allWords.Count;\n"
            "        Text = ($linesList | ForEach-Object { $_.Text }) -join \"`n\";\n"
            "        Lines = $linesList;\n"
            "        Words = $allWords;\n"
            "    } | ConvertTo-Json -Compress -Depth 4;\n"
            "} catch {\n"
            "    @{ Success = $False; WindowTitle = $foundTitle; Error = $_.Exception.Message } | ConvertTo-Json -Compress;\n"
            "} finally {\n"
            "    try { if (Test-Path $tempPath) { [System.IO.File]::Delete($tempPath) } } catch {};\n"
            "}\n"
        )
        return script

    @classmethod
    def build_find_text_command(
        cls,
        window_identifier: str,
        text_query: str,
        language_tag: str = "en-US",
    ) -> str:
        """Finds matching text in a window via OCR and returns its exact screen coordinates for clicking."""
        clean_target = window_identifier.replace("'", "''")
        clean_query = text_query.replace("'", "''")
        clean_lang = language_tag.replace("'", "''")

        script = (
            f"{cls.build_ocr_window_command(clean_target, language_tag=clean_lang)}\n"
        )
        # Wrap script to filter for best match
        wrapped = (
            f"$ocrJson = & {{\n{script}\n}};\n"
            "$data = $ocrJson | ConvertFrom-Json;\n"
            "if (-not $data.Success) { $ocrJson; exit 0 };\n"
            f"$query = '{clean_query}';\n"
            "$matches = [System.Collections.Generic.List[PSCustomObject]]::new();\n"
            "foreach ($w in $data.Words) {\n"
            "    if ($w.Text -like \"*$query*\" -or $query -like \"*$($w.Text)*\") {\n"
            "        $matches.Add($w);\n"
            "    };\n"
            "};\n"
            "@{\n"
            "    Success = $True;\n"
            "    WindowTitle = $data.WindowTitle;\n"
            "    WindowHandle = $data.WindowHandle;\n"
            "    Query = $query;\n"
            "    MatchesCount = $matches.Count;\n"
            "    Matches = $matches;\n"
            "    BestMatch = if ($matches.Count -gt 0) { $matches[0] } else { $null };\n"
            "} | ConvertTo-Json -Compress -Depth 3;\n"
        )
        return wrapped
