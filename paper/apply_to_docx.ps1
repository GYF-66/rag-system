$paperDir = Join-Path (Get-Location) 'paper'
$docx = Get-ChildItem $paperDir -Filter '*.docx' | Where-Object { $_.Name -notlike '*_backup*' } | Select-Object -First 1
if (-not $docx) { throw '未找到论文docx文件' }
$backup = Join-Path $paperDir '智能助手论文初稿_backup.docx'
if (Test-Path $backup) { Copy-Item $backup $docx.FullName -Force }

$chapter2 = [System.IO.File]::ReadAllText((Join-Path $paperDir 'chapter2_insert.txt'))
$chapter3 = [System.IO.File]::ReadAllText((Join-Path $paperDir 'chapter3_insert.txt'))
$chapter4 = [System.IO.File]::ReadAllText((Join-Path $paperDir 'chapter4_insert.txt'))
$assembled = "$chapter2`r`n`r`n$chapter3`r`n`r`n$chapter4"

function Insert-ImageAtToken($doc, $token, $imagePath, $caption, $widthCm) {
  $range = $doc.Content
  if ($range.Find.Execute($token)) {
    $range.Text = ''
    $range.Collapse(0)
    $shape = $doc.InlineShapes.AddPicture($imagePath, $false, $true, $range)
    $shape.Width = $doc.Application.CentimetersToPoints([double]$widthCm)
    $shape.Range.ParagraphFormat.Alignment = 1
    $afterImage = $shape.Range.Duplicate
    $afterImage.Collapse(0)
    $afterImage.InsertParagraphAfter()
    $captionRange = $afterImage.Duplicate
    $captionRange.Collapse(0)
    $captionRange.Text = $caption
    $captionRange.ParagraphFormat.Alignment = 1
    $captionRange.Font.NameFarEast = '宋体'
    $captionRange.Font.Name = 'Times New Roman'
    $captionRange.Font.Size = 10.5
    $captionRange.InsertParagraphAfter()
    $captionRange.InsertParagraphAfter()
  }
}

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Open($docx.FullName)

$rangeStart = $doc.Paragraphs.Item(15).Range.Start
$rangeEnd = $doc.Paragraphs.Item(39).Range.Start - 1
$targetRange = $doc.Range($rangeStart, $rangeEnd)
$targetRange.Text = $assembled

$bodyRange = $doc.Range($rangeStart, $rangeStart + $assembled.Length)
$bodyRange.Font.NameFarEast = '宋体'
$bodyRange.Font.Name = 'Times New Roman'
$bodyRange.Font.Size = 10.5
$bodyRange.ParagraphFormat.Alignment = 3
$bodyRange.ParagraphFormat.FirstLineIndent = $word.CentimetersToPoints(0.74)
$bodyRange.ParagraphFormat.LineSpacingRule = 0

Insert-ImageAtToken $doc 'FIGTOKEN1' (Join-Path $paperDir 'photo\图1_系统功能架构图.png') '图1 人工智能专业培养RAG智能助手系统功能架构图' 15.5
Insert-ImageAtToken $doc 'FIGTOKEN2' (Join-Path $paperDir '1.png') '图2 多层次回答示意图（一）：认知学伴视角' 11.5
Insert-ImageAtToken $doc 'FIGTOKEN3' (Join-Path $paperDir '2.png') '图3 多层次回答示意图（二）：决策支持视角' 11.5
Insert-ImageAtToken $doc 'FIGTOKEN4' (Join-Path $paperDir '3.png') '图4 多层次回答示意图（三）：教学助理视角' 11.5
Insert-ImageAtToken $doc 'FIGTOKEN5' (Join-Path $paperDir 'photo\图5_知识图谱.png') '图5 课程知识图谱可视化界面' 15

$doc.Save()
$doc.Close()
$word.Quit()
Write-Output 'DOCX_UPDATED'
