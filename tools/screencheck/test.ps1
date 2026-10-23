param([Parameter(Mandatory=$true)][string]$HelperPath)
$ErrorActionPreference = 'Stop'
$compilerPath = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$targetFolder = Split-Path -Parent $HelperPath
$fixturePath = Join-Path $targetFolder 'ScreenCheckTests.exe'
$resultPath = Join-Path $targetFolder 'screencheck-test-result.txt'
& $compilerPath /nologo /target:winexe /platform:anycpu "/out:$fixturePath" /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Web.Extensions.dll (Join-Path $PSScriptRoot 'ProbeTests.cs')
if ($LASTEXITCODE -ne 0) { throw 'Test fixture compilation failed.' }
$testProcess = Start-Process -FilePath $fixturePath -ArgumentList @(('"' + $HelperPath + '"'), ('"' + $resultPath + '"')) -PassThru -WindowStyle Hidden
if (-not $testProcess.WaitForExit(45000)) { $testProcess.Kill(); throw 'Fixture timed out.' }
if (Test-Path -LiteralPath $resultPath) { Get-Content -LiteralPath $resultPath }
if ($testProcess.ExitCode -ne 0) { throw 'Screen-check tests failed.' }
