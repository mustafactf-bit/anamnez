Option Explicit

Dim shell, fso, folder, requirementsPath, venvPath, venvPython, lookup, pythonPath, result

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
requirementsPath = fso.BuildPath(folder, "requirements.txt")
venvPath = fso.BuildPath(folder, ".venv")
venvPython = fso.BuildPath(venvPath, "Scripts\python.exe")

If Not fso.FileExists(requirementsPath) Then
    MsgBox "requirements.txt dosyası bulunamadı:" & vbCrLf & requirementsPath, vbCritical, "Whisper Kurulumu"
    WScript.Quit 1
End If

On Error Resume Next
Set lookup = shell.Exec("where.exe python.exe")
If Err.Number <> 0 Then
    MsgBox "Python bulunamadı. Python 3.10 veya üzerini kurup PATH'e ekleyin.", vbExclamation, "Whisper Kurulumu"
    WScript.Quit 1
End If
On Error GoTo 0

pythonPath = Trim(Split(lookup.StdOut.ReadAll, vbCrLf)(0))
If lookup.ExitCode <> 0 Or Len(pythonPath) = 0 Then
    MsgBox "python.exe bulunamadı. Python 3.10 veya üzerini kurup PATH'e ekleyin.", vbExclamation, "Whisper Kurulumu"
    WScript.Quit 1
End If

MsgBox "Yerel Whisper ve mikrofon bileşenleri kurulacak. İnternet hızınıza bağlı olarak birkaç dakika sürebilir.", vbInformation, "Whisper Kurulumu"

result = shell.Run(Chr(34) & pythonPath & Chr(34) & " -m venv " & Chr(34) & venvPath & Chr(34), 0, True)
If result <> 0 Then
    MsgBox "Python sanal ortamı oluşturulamadı (çıkış kodu " & result & "). Python kurulumunu kontrol edin.", vbCritical, "Whisper Kurulumu"
    WScript.Quit result
End If

result = shell.Run(Chr(34) & venvPython & Chr(34) & " -m pip install --disable-pip-version-check -r " & Chr(34) & requirementsPath & Chr(34), 0, True)
If result <> 0 Then
    MsgBox "Whisper bileşenleri kurulamadı (çıkış kodu " & result & "). İnternet bağlantısını ve Python sürümünü kontrol edip kurulumu yeniden çalıştırın.", vbCritical, "Whisper Kurulumu"
    WScript.Quit result
End If

MsgBox "Kurulum tamamlandı. AnamnezAsistani.vbs dosyasına çift tıklayarak uygulamayı açabilirsiniz.", vbInformation, "Whisper Kurulumu"
