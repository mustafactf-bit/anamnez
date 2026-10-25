param([Parameter(Mandatory=$true)][string]$OutputPath)
$ErrorActionPreference='Stop'
$fw = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
if (!(Test-Path (Join-Path $fw 'csc.exe'))) { $fw = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319' }
$csc = Join-Path $fw 'csc.exe'
if (!(Test-Path $csc)) { throw 'Windows .NET Framework 4.x compiler missing.' }
$wpf = Join-Path $fw 'WPF'
& $csc /nologo /target:winexe /platform:anycpu /optimize+ "/out:$OutputPath" /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Runtime.Serialization.dll /reference:System.Security.dll /reference:System.dll "/reference:$(Join-Path $wpf 'UIAutomationClient.dll')" "/reference:$(Join-Path $wpf 'UIAutomationTypes.dll')" "/reference:$(Join-Path $wpf 'WindowsBase.dll')" (Join-Path $PSScriptRoot 'MiamedScreenCheckV11.cs')
if ($LASTEXITCODE -ne 0) { throw 'C# compilation failed.' }
Write-Host "Built $OutputPath"
