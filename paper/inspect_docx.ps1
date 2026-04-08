Add-Type -AssemblyName System.IO.Compression.FileSystem
$docx = Get-ChildItem '.\paper' -Filter '*.docx' | Select-Object -First 1
if (-not $docx) { Write-Output 'DOCX_NOT_FOUND'; exit 1 }
$zip = [System.IO.Compression.ZipFile]::OpenRead($docx.FullName)
$entry = $zip.GetEntry('word/document.xml')
$reader = New-Object System.IO.StreamReader($entry.Open())
$xml = $reader.ReadToEnd()
$reader.Close()
$zip.Dispose()
$text = $xml -replace '</w:p>', "`r`n"
$text = [regex]::Replace($text, '<[^>]+>', '')
$text.Substring(0, [Math]::Min(18000, $text.Length)) | Write-Output
