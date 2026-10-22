$ErrorActionPreference = 'Stop'
$launcherRoot = $PSScriptRoot
$pythonPath = Join-Path $launcherRoot 'venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Create the virtual environment first. See README.md.' }
$shortcutShell = New-Object -ComObject WScript.Shell
$shortcut = $shortcutShell.CreateShortcut((Join-Path $launcherRoot 'Sleepy.lnk'))
$shortcut.TargetPath = $pythonPath
$shortcut.Arguments = '"' + (Join-Path $launcherRoot 'desktop_agent.py') + '" --open'
$shortcut.WorkingDirectory = $launcherRoot
$shortcut.IconLocation = (Join-Path $launcherRoot 'assets\sleepy.ico') + ',0'
$shortcut.Description = 'Sleepy personal assistant'
$shortcut.Save()
Write-Output 'Created Sleepy.lnk in the project folder. Open it to start Sleepy.'
