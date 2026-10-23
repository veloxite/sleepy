#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
[Setup]
AppId={{9FA5A767-D57E-4AA6-A54C-032EE9A53BD2}
AppName=Sleepy
AppVersion={#AppVersion}
AppPublisher=veloxite
AppPublisherURL=https://github.com/veloxite/sleepy
DefaultDirName={localappdata}\Programs\Sleepy
DefaultGroupName=Sleepy
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installers
OutputBaseFilename=Sleepy-{#AppVersion}-windows-x64-setup
SetupIconFile=..\assets\sleepy.ico
UninstallDisplayIcon={app}\Sleepy.exe
LicenseFile=..\LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "..\dist\Sleepy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Sleepy"; Filename: "{app}\Sleepy.exe"; AppUserModelID: "Sleepy.Desktop.1"
Name: "{autodesktop}\Sleepy"; Filename: "{app}\Sleepy.exe"; Tasks: desktopicon; AppUserModelID: "Sleepy.Desktop.1"

[Run]
Filename: "{app}\Sleepy.exe"; Description: "Open Sleepy"; Flags: nowait postinstall skipifsilent

; Deliberately retain %LOCALAPPDATA%\Sleepy and OS-vault keys on uninstall.
