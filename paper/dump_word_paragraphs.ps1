$docx = Get-ChildItem '.\paper' -Filter '*.docx' | Select-Object -First 1
$out = '.\paper\word_paragraphs.txt'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Open($docx.FullName)
$lines = New-Object System.Collections.Generic.List[string]
for ($i = 1; $i -le $doc.Paragraphs.Count; $i++) {
  $text = $doc.Paragraphs.Item($i).Range.Text -replace "`r", '' -replace "`a", '' -replace "`v", ''
  $text = $text.Trim()
  if ($text -ne '') {
    $style = ''
    try { $style = $doc.Paragraphs.Item($i).Range.Style.NameLocal } catch { $style = '' }
    $lines.Add(($i.ToString() + '|' + $style + '|' + $text))
  }
}
$doc.Close()
$word.Quit()
$fullOut = Join-Path (Get-Location) 'paper\word_paragraphs.txt'
[System.IO.File]::WriteAllLines($fullOut, $lines, [System.Text.UTF8Encoding]::new($false))
Write-Output $fullOut
