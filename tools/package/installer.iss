#define AppVersion "2.0.2-alpha.1.2"
[Setup]
AppId={{4A4C3DF0-16C5-4E05-865A-A734367F4CF1}
AppName=Anamnez Asistani V2-alpha1.2.2
AppVersion={#AppVersion}
AppPublisher=Anamnez Asistani
DefaultDirName={localappdata}\Programs\AnamnezAsistani
DisableDirPage=yes
UsePreviousAppDir=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\..\dist
OutputBaseFilename=Anamnez-Asistani-Kurulum
Compression=lzma2
SolidCompression=yes
CloseApplications=no
RestartApplications=no
DisableProgramGroupPage=yes
UninstallDisplayName=Anamnez Asistani
UninstallDisplayIcon={app}\versions\{#AppVersion}\AnamnezAsistani.exe
WizardStyle=modern

[Files]
Source: "..\..\dist\AnamnezAsistani\*"; DestDir: "{app}\versions\{#AppVersion}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\Anamnez Asistani"; Filename: "{app}\versions\{#AppVersion}\AnamnezAsistani.exe"; WorkingDir: "{app}\versions\{#AppVersion}"
Name: "{userdesktop}\Anamnez Asistani"; Filename: "{app}\versions\{#AppVersion}\AnamnezAsistani.exe"; WorkingDir: "{app}\versions\{#AppVersion}"
Name: "{userprograms}\Anamnez Asistani - Onceki surum"; Filename: "{code:PreviousExe}"; Check: HasPrevious

[Registry]
Root: HKCU; Subkey: "Software\AnamnezAsistani"; ValueType: string; ValueName: "CurrentExe"; ValueData: "{app}\versions\{#AppVersion}\AnamnezAsistani.exe"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\versions\{#AppVersion}\AnamnezAsistani.exe"; Description: "Anamnez Asistani'ni baslat"; Flags: nowait postinstall skipifsilent

[Code]
var OldExe: String;
function InitializeSetup(): Boolean;
begin
  RegQueryStringValue(HKCU, 'Software\AnamnezAsistani', 'CurrentExe', OldExe);
  if Pos('\versions\{#AppVersion}\', OldExe) > 0 then OldExe := '';
  Result := True;
end;
function PreviousExe(Param: String): String;
begin Result := OldExe; end;
function HasPrevious(): Boolean;
begin Result := (OldExe <> '') and FileExists(OldExe); end;
