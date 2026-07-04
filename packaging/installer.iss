; Inno Setup script for the bundled Windows installer.
; Compile: packaging\build_installer.ps1
; Requires packaging\staging from packaging\build.ps1

#ifndef AppVersion
  #define AppVersion "0.5.0"
#endif

#define MyAppName "AI Data Room Organizer"
#define MyAppPublisher "Data Room Organizer"
#define MyAppURL "https://github.com/"
#define MyAppExeName "DataRoomOrganizer.exe"
#define MyDoctorExeName "DataRoomDoctor.exe"
#define StageDir "staging"

[Setup]
AppId={{A7B3C9D1-4E2F-5A6B-8C0D-1E2F3A4B5C6D}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppVerName={#MyAppName} {#AppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=AI-Data-Room-Organizer-Setup
Compression=lzma2/max
SolidCompression=yes
InternalCompressLevel=max
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
DisableProgramGroupPage=no
UninstallDisplayIcon={app}\launcher\{#MyAppExeName}
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#StageDir}\app\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#StageDir}\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#StageDir}\tools\*"; DestDir: "{app}\tools"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#StageDir}\models\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#StageDir}\launcher\*"; DestDir: "{app}\launcher"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#StageDir}\BUILD_INFO.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Data Room Organizer"; Filename: "{app}\launcher\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Data Room Doctor"; Filename: "{app}\launcher\{#MyDoctorExeName}"; WorkingDir: "{app}"
Name: "{commondesktop}\Data Room Organizer"; Filename: "{app}\launcher\{#MyAppExeName}"; Tasks: desktopicon; WorkingDir: "{app}"

[Run]
Filename: "{app}\launcher\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Messages]
FinishedLabel=Setup finished. Use the Start Menu or desktop shortcut to open the Data Room Organizer in your browser.
