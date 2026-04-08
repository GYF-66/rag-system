$paperDir = Join-Path (Get-Location) 'paper'
$docx = Get-ChildItem $paperDir -Filter '*.docx' | Where-Object { $_.Name -notlike '*_backup*' } | Select-Object -First 1
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Open($docx.FullName)
$tokens = 'FIGTOKEN1','FIGTOKEN2','FIGTOKEN3','FIGTOKEN4','FIGTOKEN5'
foreach ($token in $tokens) {
  $r = $doc.Content
  $found = $r.Find.Execute($token)
  if ($found) {
    Write-Output ($token + '|' + $r.Start + '|' + $r.End)
  } else {
    Write-Output ($token + '|NOT_FOUND')
  }
}
$doc.Close()
$word.Quit()
