param([string]$PythonPath)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskPython = $PythonPath
if (-not $taskPython) {
    $taskLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($taskLauncher) {
        $taskPython = & $taskLauncher.Source -3.12 -c 'import sys; print(sys.executable)' 2>$null
        if ($LASTEXITCODE -ne 0) { $taskPython = $null }
    }
    if (-not $taskPython) {
        $taskCommand = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($taskCommand) { $taskPython = $taskCommand.Source }
    }
}
if (-not $taskPython) { throw 'Install Python 3.12 x64 with tkinter and pip, then run setup.cmd again.' }
& $taskPython -c "import sys, struct, tkinter; assert sys.version_info >= (3, 10); assert struct.calcsize('P') == 8"
if ($LASTEXITCODE -ne 0) { throw 'Python x64 with tkinter is required. Python 3.12 is the tested version.' }
$taskVenv = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.venv\Scripts\pip.exe'))) {
    & $taskPython -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
}
& $taskVenv -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
& $taskVenv (Join-Path $PSScriptRoot 'install_assets.py')
if ($LASTEXITCODE -ne 0) { throw 'Runtime asset installation failed.' }
& $taskVenv -c "import tkinter, numpy, PIL, onnxruntime as ort; assert 'DmlExecutionProvider' in ort.get_available_providers(); print('AniEdge for AMD is ready. Run start.cmd.')"
if ($LASTEXITCODE -ne 0) { throw 'DirectML dependency verification failed.' }
