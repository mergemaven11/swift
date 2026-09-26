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

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\SwiftFilez.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\swf.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\SwiftFilez"; Filename: "{app}\SwiftFilez.exe"; WorkingDir: "{userprofile}"
Name: "{group}\SwiftFilez CLI"; Filename: "{cmd}"; Parameters: "/K ""{app}\swf.exe"" --help"; WorkingDir: "{userprofile}"
Name: "{autodesktop}\SwiftFilez"; Filename: "{app}\SwiftFilez.exe"; WorkingDir: "{userprofile}"; Tasks: desktopicon

[Run]
Filename: "{app}\SwiftFilez.exe"; Description: "Launch SwiftFilez"; Flags: nowait postinstall skipifsilent
