$paperDir = Join-Path (Get-Location) 'paper'
$docx = Get-ChildItem $paperDir -Filter '*.docx' | Where-Object { $_.Name -notlike '*_backup*' } | Select-Object -First 1
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Open($docx.FullName)
$tokens = 'FIGTOKEN1','FIGTOKEN2','FIGTOKEN3','FIGTOKEN4','FIGTOKEN5'
foreach ($token in $tokens) {
  $r = $doc.Content
  $found = $r.Find.Execute($token)
  if ($found) { Write-Output ($token + '|FOUND') } else { Write-Output ($token + '|OK') }
}
$captions = '图2 多层次回答示意图（一）：认知学伴视角','图3 多层次回答示意图（二）：决策支持视角','图4 多层次回答示意图（三）：教学助理视角','图5 课程知识图谱可视化界面'
foreach ($caption in $captions) {
  $r = $doc.Content
  $found = $r.Find.Execute($caption)
  if ($found) { Write-Output ($caption + '|FOUND') } else { Write-Output ($caption + '|MISSING') }
}
$doc.Close()
$word.Quit()
