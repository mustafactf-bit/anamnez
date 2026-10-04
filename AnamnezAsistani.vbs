Option Explicit

Dim shell, fso, folder, appPath, lookup, pythonPath, command

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
appPath = fso.BuildPath(folder, "anamnez_asistani.py")

If Not fso.FileExists(appPath) Then
    MsgBox "Uygulama dosyası bulunamadı:" & vbCrLf & appPath, vbCritical, "Anamnez Asistanı"
    WScript.Quit 1
End If

pythonPath = fso.BuildPath(folder, ".venv\Scripts\pythonw.exe")
If Not fso.FileExists(pythonPath) Then
    On Error Resume Next
    Set lookup = shell.Exec("where.exe pythonw.exe")
    If Err.Number <> 0 Then
        MsgBox "Python bulunamadı. Python 3'ü kurup PATH'e ekleyin, ardından WhisperKurulum.vbs dosyasını çalıştırın.", vbExclamation, "Anamnez Asistanı"
        WScript.Quit 1
    End If
    On Error GoTo 0

    pythonPath = Trim(Split(lookup.StdOut.ReadAll, vbCrLf)(0))
    If lookup.ExitCode <> 0 Or Len(pythonPath) = 0 Then
        MsgBox "pythonw.exe bulunamadı. Python 3'ü kurup PATH'e ekleyin, ardından WhisperKurulum.vbs dosyasını çalıştırın.", vbExclamation, "Anamnez Asistanı"
        WScript.Quit 1
    End If
End If

command = Chr(34) & pythonPath & Chr(34) & " " & Chr(34) & appPath & Chr(34)
On Error Resume Next
shell.Run command, 0, False
If Err.Number <> 0 Then
    MsgBox "Uygulama başlatılamadı:" & vbCrLf & Err.Description, vbCritical, "Anamnez Asistanı"
    WScript.Quit 1
End If
On Error GoTo 0
