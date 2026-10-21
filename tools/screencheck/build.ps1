param([Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference = 'Stop'
$frameworkPath = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
$compilerPath = Join-Path $frameworkPath 'csc.exe'
$wpfPath = Join-Path $frameworkPath 'WPF'
if (-not (Test-Path -LiteralPath $compilerPath)) { throw '.NET Framework C# compiler not found.' }
$references = @('UIAutomationClient.dll','UIAutomationTypes.dll','WindowsBase.dll') | ForEach-Object { '/reference:' + (Join-Path $wpfPath $_) }
& $compilerPath /nologo /target:winexe /platform:anycpu /optimize+ "/out:$OutputPath" "/win32manifest:$(Join-Path $PSScriptRoot 'app.manifest')" /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Runtime.Serialization.dll $references (Join-Path $PSScriptRoot 'MiamedScreenCheck.cs')
if ($LASTEXITCODE -ne 0) { throw 'Compilation failed.' }
