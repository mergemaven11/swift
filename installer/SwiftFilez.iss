#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-dev"
#endif

#define MyAppName "SwiftFilez"
#define MyAppPublisher "Tobias Scott"
#define MyAppURL "https://swift-cli.netlify.app/"
#define MyAppExeName "SwiftFilez.exe"

[Setup]
AppId={{4B9DA1E8-10DA-47DD-AFA7-52EAC6A4576E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\SwiftFilez
DefaultGroupName=SwiftFilez
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=SwiftFilez-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=SwiftFilez Windows Installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
LicenseFile=EULA.txt
InfoBeforeFile=PRIVACY.txt
ChangesEnvironment=yes

[Tasks]
Name: "addtopath"; Description: "Add SwiftFilez command-line tools to my &PATH (recommended)"; GroupDescription: "Command-line integration:"
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\SwiftFilez.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\swf.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\SwiftFilez"; Filename: "{app}\SwiftFilez.exe"; WorkingDir: "{userdocs}"
Name: "{group}\SwiftFilez CLI"; Filename: "{cmd}"; Parameters: "/K ""{app}\swf.exe"" --help"; WorkingDir: "{userdocs}"
Name: "{autodesktop}\SwiftFilez"; Filename: "{app}\SwiftFilez.exe"; WorkingDir: "{userdocs}"; Tasks: desktopicon

[Run]
Filename: "{app}\SwiftFilez.exe"; Description: "Launch SwiftFilez"; Flags: nowait postinstall skipifsilent

[Code]
function PathContains(const PathValue, Dir: string): Boolean;
begin
  Result := Pos(';' + LowerCase(Dir) + ';', ';' + LowerCase(PathValue) + ';') > 0;
end;

procedure AddToUserPath;
var
  PathValue: string;
  AppDir: string;
begin
  AppDir := ExpandConstant('{app}');
  if not RegQueryStringValue(HKCU, 'Environment', 'Path', PathValue) then
    PathValue := '';

  if not PathContains(PathValue, AppDir) then
  begin
    if (PathValue <> '') and (PathValue[Length(PathValue)] <> ';') then
      PathValue := PathValue + ';';
    PathValue := PathValue + AppDir;
    RegWriteExpandStringValue(HKCU, 'Environment', 'Path', PathValue);
  end;
end;

procedure RemoveFromUserPath;
var
  PathValue: string;
  AppDir: string;
begin
  AppDir := ExpandConstant('{app}');
  if RegQueryStringValue(HKCU, 'Environment', 'Path', PathValue) then
  begin
    StringChangeEx(PathValue, ';' + AppDir, '', True);
    StringChangeEx(PathValue, AppDir + ';', '', True);
    if CompareText(PathValue, AppDir) = 0 then
      PathValue := '';
    RegWriteExpandStringValue(HKCU, 'Environment', 'Path', PathValue);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('addtopath') then
    AddToUserPath;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    RemoveFromUserPath;
end;
