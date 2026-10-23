param([string]$Compiler = 'C:/Program Files (x86)/Inno Setup 6/ISCC.exe')
$ErrorActionPreference = 'Stop'
# Disposable CI-only installation exercise. Never use real patient fixtures.
if (!$env:GITHUB_ACTIONS) { throw 'Run this installation exercise only in disposable GitHub CI' }
$appDir = Join-Path $env:RUNNER_TEMP 'Anamnez-install-fixture'
$dataDir = Join-Path $env:LOCALAPPDATA 'AnamnezAsistani'
New-Item -ItemType Directory -Force $dataDir | Out-Null
$sentinel = Join-Path $dataDir 'install-test-sentinel.json'
'{"synthetic":"keep-this-data"}' | Set-Content $sentinel
$before = (Get-FileHash $sentinel).Hash
$oldScript = Join-Path $PSScriptRoot 'previous-test.iss'
# This is a packaging fixture for the previous layout, not an actual old release.
(Get-Content (Join-Path $PSScriptRoot 'installer.iss') -Raw).Replace('2.0.2-alpha.1.5','2.0.2-alpha.1.4') | Set-Content $oldScript
& $Compiler $oldScript
if ($LASTEXITCODE -ne 0) { throw 'Previous fixture compiler failed' }
$installer = Join-Path (Get-Location) 'dist/Anamnez-Asistani-Kurulum.exe'
function Install-Fixture {
    $process = Start-Process $installer -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/NOCLOSEAPPLICATIONS',('/DIR="'+$appDir+'"')) -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "Fixture installation failed: $($process.ExitCode)" }
}
Install-Fixture
& $Compiler (Join-Path $PSScriptRoot 'installer.iss')
if ($LASTEXITCODE -ne 0) { throw 'Current compiler failed' }
Install-Fixture
$oldExe = Join-Path $appDir 'versions/2.0.2-alpha.1.4/AnamnezAsistani.exe'
$newExe = Join-Path $appDir 'versions/2.0.2-alpha.1.5/AnamnezAsistani.exe'
if (!(Test-Path $oldExe) -or !(Test-Path $newExe)) { throw 'Side-by-side versions missing' }
if ((Get-FileHash $sentinel).Hash -ne $before) { throw 'User data changed' }
$current = (Get-ItemProperty HKCU:/Software/AnamnezAsistani).CurrentExe
if ($current -ne $newExe) { throw 'Current version pointer incorrect' }
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Programs')) 'Anamnez Asistani - Onceki surum.lnk'))
if ($shortcut.TargetPath -ne $oldExe) { throw 'Rollback shortcut incorrect' }
foreach ($exe in @($newExe,$oldExe)) {
    $report = Join-Path $env:RUNNER_TEMP ([Guid]::NewGuid().ToString()+'.json')
    $process = Start-Process $exe -ArgumentList @('--package-smoke',('"'+$report+'"')) -WindowStyle Hidden -PassThru -Wait
    if ($process.ExitCode -ne 0 -or !(Test-Path $report)) { throw 'Installed/rollback runtime failed' }
}
$uninstall = Start-Process (Join-Path $appDir 'unins000.exe') -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -WindowStyle Hidden -PassThru -Wait
if ($uninstall.ExitCode -ne 0 -or (Get-FileHash $sentinel).Hash -ne $before) { throw 'Uninstall data-preservation failure' }
Write-Output 'Synthetic install, upgrade, rollback launch and uninstall data preservation passed.'
