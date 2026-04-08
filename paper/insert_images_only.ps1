$paperDir = Join-Path (Get-Location) 'paper'
$docx = Get-ChildItem $paperDir -Filter '*.docx' | Where-Object { $_.Name -notlike '*_backup*' } | Select-Object -First 1
if (-not $docx) { throw '未找到论文docx文件' }

function Replace-TokenWithImage($doc, $token, $imagePath, $caption, $widthCm) {
  $findRange = $doc.Content
  if ($findRange.Find.Execute($token)) {
    $findRange.Text = ''
    $findRange.Collapse(0)
    $shape = $findRange.InlineShapes.AddPicture($imagePath)
    $shape.Width = $doc.Application.CentimetersToPoints([double]$widthCm)
    $shape.Range.InsertParagraphAfter() | Out-Null
    $capRange = $shape.Range.Duplicate
    $capRange.Collapse(0)
    $capRange.Text = $caption
    $capRange.InsertParagraphAfter() | Out-Null
    $capRange.InsertParagraphAfter() | Out-Null
  }
}

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Open($docx.FullName)

Replace-TokenWithImage $doc 'FIGTOKEN1' (Join-Path $paperDir 'fig1.png') '图1 人工智能专业培养RAG智能助手系统功能架构图' 15.5
Replace-TokenWithImage $doc 'FIGTOKEN2' (Join-Path $paperDir 'fig2.png') '图2 多层次回答示意图（一）：认知学伴视角' 11.5
Replace-TokenWithImage $doc 'FIGTOKEN3' (Join-Path $paperDir 'fig3.png') '图3 多层次回答示意图（二）：决策支持视角' 11.5
Replace-TokenWithImage $doc 'FIGTOKEN4' (Join-Path $paperDir 'fig4.png') '图4 多层次回答示意图（三）：教学助理视角' 11.5
Replace-TokenWithImage $doc 'FIGTOKEN5' (Join-Path $paperDir 'fig5.png') '图5 课程知识图谱可视化界面' 15

$doc.Save()
$doc.Close()
$word.Quit()
Write-Output 'IMAGES_INSERTED'
