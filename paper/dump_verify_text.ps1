$paperDir = Join-Path (Get-Location) 'paper'
$docx = Get-ChildItem $paperDir -Filter '*.docx' | Where-Object { $_.Name -notlike '*_backup*' } | Select-Object -First 1
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Open($docx.FullName)
$paras = $doc.Paragraphs
for ($i = 15; $i -le [Math]::Min(35, $paras.Count); $i++) {
  $text = $paras.Item($i).Range.Text.Replace("`r",' ').Replace("`a",' ').Trim()
  if ($text.Length -gt 0) { Write-Output ($i.ToString() + '|' + $text) }
}
$doc.Close()
$word.Quit()
