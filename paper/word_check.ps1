try {
  $word = New-Object -ComObject Word.Application
  Write-Output 'WORD_OK'
  $word.Quit()
} catch {
  Write-Output 'WORD_NOT_AVAILABLE'
}
