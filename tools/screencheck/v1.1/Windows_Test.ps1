# Compile the tool if needed, then check invalid-window and patient-free WinForms fixture.
# No Gmail, live hospital software, or real patient information is used.
$ErrorActionPreference = 'Stop'
$exe = Join-Path $PSScriptRoot 'Miamed-Ekran-Kontrol-v1.1.exe'
$folder = Join-Path $env:TEMP ('miamed-v11-accept-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $folder | Out-Null
try {
  if (!(Test-Path -LiteralPath $exe)) { & (Join-Path $PSScriptRoot 'build.ps1') -OutputPath $exe }
  # Regression: hospital executable uses MIA-Med rather than Miamed.
  $assembly = [Reflection.Assembly]::LoadFrom($exe)
  $matcher = $assembly.GetType('MainWindow').GetMethod('IsMiamedLabel', [Reflection.BindingFlags]'NonPublic,Static')
  if (!$matcher) { throw 'Process name matcher missing.' }
  $names = @(
    @{Label='MIA-Med (PID 13056)'; Expected=$true},
    @{Label='Miamed (PID 123)'; Expected=$true},
    @{Label='MIA Med (PID 42)'; Expected=$true},
    @{Label='MIA_Med (PID 42)'; Expected=$true},
    @{Label='OtherMed (PID 42)'; Expected=$false},
    @{Label='NotMIA-Med (PID 42)'; Expected=$false},
    @{Label='MIA-Med (PID abc)'; Expected=$false}
  )
  foreach ($case in $names) {
    if ($matcher.Invoke($null, @($case.Label)) -ne $case.Expected) { throw "Process name regression: $($case.Label)" }
  }
  Write-Output 'PASS process-name labels (7/7).'
  $compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
  if (!(Test-Path -LiteralPath $compiler)) { $compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe' }
  if (!(Test-Path -LiteralPath $compiler)) { throw 'Windows .NET Framework compiler missing.' }
  $fixture = Join-Path $folder 'Miamed-v11-SyntheticTests.exe'
  $report = Join-Path $folder 'result.txt'
  & $compiler /nologo /target:winexe /platform:anycpu "/out:$fixture" /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Web.Extensions.dll (Join-Path $PSScriptRoot 'tests\ProbeTestsV11.cs')
  if ($LASTEXITCODE -ne 0) { throw 'Synthetic fixture compilation failed.' }
  $p = Start-Process -FilePath $fixture -ArgumentList @(('"' + $exe + '"'),('"' + $report + '"')) -PassThru -WindowStyle Hidden
  if (!$p.WaitForExit(60000)) { $p.Kill(); throw 'Synthetic UI test exceeded 60 seconds.' }
  if ((Test-Path $report)) { Get-Content $report }
  if ($p.ExitCode -ne 0) { throw 'Synthetic UI test failed.' }
} finally { Remove-Item -LiteralPath $folder -Recurse -Force -ErrorAction SilentlyContinue }
