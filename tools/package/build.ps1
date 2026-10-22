param([string]$Python = '.venv-build/Scripts/python.exe', [string]$Compiler = '')
$ErrorActionPreference = 'Stop'
& $Python -m PyInstaller --noconfirm --clean --windowed --onedir --name AnamnezAsistani --icon assets/app.ico --add-data 'assets:assets' --collect-all faster_whisper --collect-all ctranslate2 --collect-all onnxruntime --collect-all sounddevice --collect-all _sounddevice_data --collect-all llama_cpp --collect-all tokenizers --collect-all cryptography app.py
if ($LASTEXITCODE -ne 0) { throw 'EXE build failed' }
if (!$Compiler) {
    $Compiler = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
    if (!$Compiler) { $Compiler = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6/ISCC.exe' }
}
& $Compiler tools/package/installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
