$ErrorActionPreference = 'Stop'
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Run setup.cmd first to prepare AniEdge for AMD.' }
Start-Process -FilePath $taskPython -ArgumentList ('"' + (Join-Path $PSScriptRoot 'player.py') + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
