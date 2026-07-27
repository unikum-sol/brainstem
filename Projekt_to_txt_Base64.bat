@echo off
echo Exportiere Projektdateien...
powershell -NoProfile -Command "$t = Get-Date -Format 'yyyyMMdd_HHmmss'; $f = 'PROJEKT_BASE64_' + $t + '.txt'; Get-ChildItem -Recurse -Include *.py, *.sql | ForEach-Object { '=== DATEI: ' + $_.Name + ' ==='; $b = [System.IO.File]::ReadAllBytes($_.FullName); [Convert]::ToBase64String($b, [System.Base64FormattingOptions]::InsertLineBreaks); '' } | Out-File -Encoding utf8 $f; Write-Host ('✅ Export erfolgreich! Datei gespeichert als: ' + $f) -ForegroundColor Green"
pause