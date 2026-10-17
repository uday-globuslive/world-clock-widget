# Creates Desktop and Start Menu shortcuts that launch the widget without a console window.
$ErrorActionPreference = 'Stop'
$pythonw = Join-Path (Split-Path (Get-Command python).Source) 'pythonw.exe'
if (-not (Test-Path $pythonw)) { throw "pythonw.exe not found next to python.exe" }
$script = Join-Path $PSScriptRoot 'WorldClock.pyw'
$shell = New-Object -ComObject WScript.Shell
$targets = @(
    [Environment]::GetFolderPath('Desktop'),
    (Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs')
)
foreach ($dir in $targets) {
    $lnk = $shell.CreateShortcut((Join-Path $dir 'World Clock.lnk'))
    $lnk.TargetPath = $pythonw
    $lnk.Arguments = "`"$script`""
    $lnk.WorkingDirectory = $PSScriptRoot
    $lnk.IconLocation = "$env:SystemRoot\System32\shell32.dll,265"
    $lnk.Save()
    Write-Host "Created shortcut in $dir"
}
