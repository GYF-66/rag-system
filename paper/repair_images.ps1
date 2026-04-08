$paperDir = Join-Path (Get-Location) 'paper'
$docx = Get-ChildItem $paperDir -Filter '*.docx' | Where-Object { $_.Name -notlike '*_backup*' } | Select-Object -First 1
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Open($docx.FullName)

function InsertAtToken($doc, $word, $token, $imagePath, $caption, $widthCm) {
  $r = $doc.Content
  if ($r.Find.Execute($token)) {
    $start = $r.Start
    $r.Text = ''
    $imgRange = $doc.Range($start, $start)
    $shape = $doc.InlineShapes.AddPicture($imagePath, $false, $true, $imgRange)
    $shape.Width = [int]($doc.Application.CentimetersToPoints([double]$widthCm))
    $shape.Range.Select() | Out-Null
    $word.Selection.ParagraphFormat.Alignment = 1
    $word.Selection.MoveRight() | Out-Null
    $word.Selection.TypeParagraph()
    $word.Selection.TypeText($caption)
    $word.Selection.ParagraphFormat.Alignment = 1
    $word.Selection.TypeParagraph()
    $word.Selection.TypeParagraph()
  }
}

InsertAtToken $doc $word 'FIGTOKEN2' (Join-Path $paperDir 'fig2.png') '图2 多层次回答示意图（一）：认知学伴视角' 11.5
InsertAtToken $doc $word 'FIGTOKEN3' (Join-Path $paperDir 'fig3.png') '图3 多层次回答示意图（二）：决策支持视角' 11.5
InsertAtToken $doc $word 'FIGTOKEN4' (Join-Path $paperDir 'fig4.png') '图4 多层次回答示意图（三）：教学助理视角' 11.5
InsertAtToken $doc $word 'FIGTOKEN5' (Join-Path $paperDir 'fig5.png') '图5 课程知识图谱可视化界面' 15

$doc.Save()
$doc.Close()
$word.Quit()
[Console]::WriteLine('OK')
