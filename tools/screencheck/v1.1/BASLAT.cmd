@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
set "HERE=%~dp0"
set "EXE=%HERE%Miamed-Ekran-Kontrol-v1.1.exe"
if not exist "%EXE%" (
  echo Miamed Ekran Kontrolu v1.1 hazirlaniyor...
  set "FRAMEWORK=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319"
  if not exist "%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe" set "FRAMEWORK=%WINDIR%\Microsoft.NET\Framework\v4.0.30319"
  if not exist "!FRAMEWORK!\csc.exe" (
    echo .NET Framework 4.x bulunamadi. Bilgi islem destegi alin.
    pause
    exit /b 1
  )
  "!FRAMEWORK!\csc.exe" /nologo /target:winexe /platform:anycpu /optimize+ /out:"%EXE%" /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Runtime.Serialization.dll /reference:System.Security.dll /reference:System.dll /reference:"!FRAMEWORK!\WPF\UIAutomationClient.dll" /reference:"!FRAMEWORK!\WPF\UIAutomationTypes.dll" /reference:"!FRAMEWORK!\WPF\WindowsBase.dll" "%HERE%MiamedScreenCheckV11.cs"
  if errorlevel 1 (
    echo Derleme basarisiz. Bilgi islemden destek alin; kurum guvenlik politikalarini asmayin.
    pause
    exit /b 1
  )
)
start "" "%EXE%"
endlocal
