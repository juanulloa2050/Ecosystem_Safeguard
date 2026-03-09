#define MyAppName "Ecosystem Safeguard"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "EPICS IEEE"
#define MyAppExeName "EcosystemSafeguard.exe"

[Setup]
; Identificador único del programa (déjalo así para la prueba)
AppId={{E64A0A2B-1E3E-4B4E-9C0B-9F0D2D7C1A11}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

; ✅ Instalar como app (admin) en Program Files
DefaultDirName={autopf}\{#MyAppName}
PrivilegesRequired=admin

; Carpeta en el Menú Inicio
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output del instalador
OutputDir=installer_out
OutputBaseFilename=EcosystemSafeguard_Setup_{#MyAppVersion}

Compression=lzma2
SolidCompression=yes

ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; ✅ Copia TODO el contenido de dist\EcosystemSafeguard\ al directorio de instalación
Source: "..\dist\EcosystemSafeguard\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; ✅ Acceso directo en Start Menu
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

; ✅ Acceso directo en Desktop (SIEMPRE)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
; Opcional: checkbox para abrir al finalizar instalación
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent