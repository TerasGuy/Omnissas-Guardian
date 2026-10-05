; Omnissa Guardian setup. The program, the default library, and article images.

#define MyAppName "Omnissa Guardian"
#define MyAppVersion "2.0.0"
#define MyAppExeName "OmnissaGuardian.exe"

[Setup]
AppId={{A7E3C1D4-6B58-4F0A-9C2E-1D8F4B6A0E77}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Omnissa Archive
DefaultDirName={autopf}\Omnissa Guardian
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=OmnissaGuardianSetup
SetupIconFile=..\assets\omnissa-guardian.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "..\dist\OmnissaGuardian\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dist\package-staging\archive.sqlite"; DestDir: "{app}\data\library"; DestName: "archive.sqlite"; Flags: ignoreversion onlyifdoesntexist uninsneveruninstall
Source: "..\data\assets\*"; DestDir: "{app}\data\assets"; Flags: ignoreversion recursesubdirs createallsubdirs uninsneveruninstall

[Dirs]
Name: "{app}\data\library\inbox"; Flags: uninsneveruninstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
