; AgentHub Client installer script for Inno Setup.
;
; Build after creating dist\AgentHubClient.exe:
;   ISCC.exe installer\AgentHubClient.iss

#define MyAppName "AgentHub Client"
#define MyAppVersion "1.0.17"
#define MyAppPublisher "AgentHub"
#define MyAppExeName "AgentHubClient.exe"

[Setup]
AppId={{9F8F0B37-5F1E-4C4C-9A8A-0A63C8F8A104}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\AgentHub\Client
DefaultGroupName=AgentHub
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=AgentHubClientSetup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
CloseApplications=no

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\AgentHub Client"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\AgentHub Client"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
Name: "startup"; Description: "Start AgentHub Client when Windows starts"; GroupDescription: "Startup options:"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "AgentHubClient"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch AgentHub Client"; Flags: nowait postinstall skipifsilent

[Code]
procedure BackupUserConfig();
var
  Source: String;
  Backup: String;
begin
  Source := ExpandConstant('{userappdata}\AgentHub\Client\config.json');
  Backup := ExpandConstant('{userappdata}\AgentHub\Client\config.json.installbak');
  if FileExists(Source) then
  begin
    ForceDirectories(ExtractFileDir(Backup));
    FileCopy(Source, Backup, False);
  end;
end;

procedure RestoreUserConfigIfNeeded();
var
  Source: String;
  Backup: String;
begin
  Source := ExpandConstant('{userappdata}\AgentHub\Client\config.json');
  Backup := ExpandConstant('{userappdata}\AgentHub\Client\config.json.installbak');
  if (not FileExists(Source)) and FileExists(Backup) then
  begin
    ForceDirectories(ExtractFileDir(Source));
    FileCopy(Backup, Source, False);
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  BackupUserConfig();
  Exec(ExpandConstant('{cmd}'), '/C taskkill /IM AgentHubClient.exe /F >NUL 2>NUL', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    RestoreUserConfigIfNeeded();
end;
