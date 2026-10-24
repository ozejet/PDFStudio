; The installer contains every runtime. Nothing is downloaded on the user's PC.
#ifndef AppVersion
  #error Build with scripts/build_installer.py
#endif
#define VersionDir "versions\" + AppVersion
#define AppExe "{app}\" + VersionDir + "\PDFStudio.exe"
#define AppIcon "{app}\" + VersionDir + "\_internal\web\dist\branding\pdfstudio.ico"

[Setup]
AppId={{D9E40995-203D-4EC7-9F90-12864C63C94D}
AppName=PDF Studio
AppVersion={#AppVersion}
AppVerName=PDF Studio {#AppVersion}
VersionInfoVersion={#VersionNumbers}
DefaultDirName={localappdata}\Programs\PDF Studio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
SetupArchitecture=x64
ArchitecturesAllowed=x64
MinVersion=10.0.14393
OutputDir={#InstallerOutput}
OutputBaseFilename=PDFStudio-Setup-{#AppVersion}
SetupIconFile={#BundleDir}\_internal\web\dist\branding\pdfstudio.ico
UninstallDisplayIcon={#AppIcon}
UninstallFilesDir={app}\uninstall
CreateUninstallRegKey=not IsTestInstall
Compression=lzma2/fast
SolidCompression=yes
LZMANumBlockThreads=4
DiskSpanning=no
WizardStyle=modern
CloseApplications=no
RestartApplications=no
ChangesAssociations=yes
SetupLogging=yes
DisableWelcomePage=no

[Messages]
WelcomeLabel2=This will install PDF Studio {#AppVersion} on your computer.%n%nPDF Studio opens in its own desktop window. Python, WebView2, fonts and offline document conversion are included. No separate downloads are needed.%n%nExisting PDF Studio sessions can remain open during an update.

[Tasks]
Name: desktopicon; Description: "Create a Desktop shortcut"; Flags: unchecked; Check: not IsTestInstall

[Files]
; Keep the prerequisite first so checking it does not unpack the whole app.
Source: "{#BundleDir}\_internal\vendor\prerequisites\VC_redist.x64.exe"; Flags: dontcopy
Source: "{#BundleDir}\_internal\vendor\prerequisites\MicrosoftEdgeWebView2RuntimeInstallerX64.exe"; Flags: dontcopy
Source: "{#BundleDir}\*"; DestDir: "{app}\{#VersionDir}"; Excludes: "windows-integration.json,_internal\vendor\prerequisites\VC_redist.x64.exe,_internal\vendor\prerequisites\MicrosoftEdgeWebView2RuntimeInstallerX64.exe"; Flags: ignoreversion recursesubdirs createallsubdirs

[Registry]
#include GeneratedDir + "\registration.iss"

[Icons]
Name: "{userprograms}\PDF Studio"; Filename: "{#AppExe}"; WorkingDir: "{app}\{#VersionDir}"; IconFilename: "{#AppIcon}"; AppUserModelID: "PDFStudio.Desktop"; Check: not IsTestInstall
Name: "{userprograms}\PDF Studio (browser)"; Filename: "{#AppExe}"; Parameters: "--browser"; WorkingDir: "{app}\{#VersionDir}"; IconFilename: "{#AppIcon}"; AppUserModelID: "PDFStudio.Desktop"; Check: not IsTestInstall
Name: "{userdesktop}\PDF Studio"; Filename: "{#AppExe}"; WorkingDir: "{app}\{#VersionDir}"; IconFilename: "{#AppIcon}"; AppUserModelID: "PDFStudio.Desktop"; Tasks: desktopicon; Check: not IsTestInstall

[Run]
Filename: "{#AppExe}"; Description: "Open PDF Studio"; Flags: nowait postinstall skipifsilent

[Code]
var
  RuntimeNeedsRestart: Boolean;

function IsTestInstall: Boolean;
begin
  { Used by the project smoke check: files/uninstaller only, no OS integration. }
  Result := ExpandConstant('{param:TESTMODE|0}') = '1';
end;

function FileIsInUse(const Filename: String): Boolean;
var
  Stream: TFileStream;
begin
  Result := False;
  if not FileExists(Filename) then exit;
  try
    { Open existing, read/write, exclusive sharing; never modifies the file. }
    Stream := TFileStream.Create(Filename, $0012);
    Stream.Free;
  except
    Result := True;
  end;
end;

function WebView2VersionIsReady(const RootKey: Integer): Boolean;
var
  Version: String;
  InstalledVersion, RequiredVersion: Int64;
begin
  Result := False;
  if not RegQueryStringValue(RootKey, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) then exit;
  if StrToVersion(Version, InstalledVersion) and StrToVersion('{#MinimumWebView2Version}', RequiredVersion) then
    Result := ComparePackedVersion(InstalledVersion, RequiredVersion) >= 0;
end;

function WebView2IsReady: Boolean;
begin
  Result := WebView2VersionIsReady(HKLM32) or WebView2VersionIsReady(HKCU);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Installed: Cardinal;
  RuntimeVersion: String;
  InstalledVersion, RequiredVersion: Int64;
  ExitCode: Integer;
begin
  Result := '';
  { New versions get separate directories; reinstallation must not touch a live one. }
  if FileIsInUse(ExpandConstant('{#AppExe}')) then begin
    Result := 'This version of PDF Studio is open. Save your work and use Quit PDF Studio, then run setup again. Your session has been left open.';
    exit;
  end;
  if IsTestInstall then begin
    Log('TESTMODE: Microsoft runtime installation and Windows integration skipped.');
    exit;
  end;
  if not WebView2IsReady then begin
    ExtractTemporaryFile('MicrosoftEdgeWebView2RuntimeInstallerX64.exe');
    if not Exec(ExpandConstant('{tmp}\MicrosoftEdgeWebView2RuntimeInstallerX64.exe'), '/silent /install', '', SW_HIDE, ewWaitUntilTerminated, ExitCode) then begin
      Result := 'Windows could not start the included WebView2 runtime installer.';
      exit;
    end;
    if not WebView2IsReady then begin
      Result := 'The included WebView2 runtime could not be installed (code ' + IntToStr(ExitCode) + '). Restart Windows and try setup again.';
      exit;
    end;
  end;
  if RegQueryDWordValue(HKLM64, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Installed', Installed) and
     RegQueryStringValue(HKLM64, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Version', RuntimeVersion) then begin
    if Copy(RuntimeVersion, 1, 1) = 'v' then Delete(RuntimeVersion, 1, 1);
    if (Installed = 1) and StrToVersion(RuntimeVersion, InstalledVersion) and
       StrToVersion('{#RedistVersion}', RequiredVersion) then
      if ComparePackedVersion(InstalledVersion, RequiredVersion) >= 0 then exit;
  end;
  ExtractTemporaryFile('VC_redist.x64.exe');
  if not ShellExec('runas', ExpandConstant('{tmp}\VC_redist.x64.exe'), '/install /quiet /norestart', '', SW_HIDE, ewWaitUntilTerminated, ExitCode) then begin
    Result := 'Windows could not install the included Microsoft runtime. Allow the Windows permission prompt and try again.';
    exit;
  end;
  if (ExitCode <> 0) and (ExitCode <> 1638) and (ExitCode <> 3010) then
    Result := 'The included Microsoft runtime could not be installed (code ' + IntToStr(ExitCode) + ').';
  if ExitCode = 3010 then RuntimeNeedsRestart := True;
end;

function NeedRestart: Boolean;
begin
  Result := RuntimeNeedsRestart;
end;

function InitializeUninstall: Boolean;
var
  Found: TFindRec;
begin
  Result := True;
  if FindFirst(ExpandConstant('{app}\versions\*'), Found) then begin
    try
      repeat
        if (Found.Name <> '.') and (Found.Name <> '..') then
          if FileIsInUse(ExpandConstant('{app}\versions\') + Found.Name + '\PDFStudio.exe') then begin
            Result := False;
            if not UninstallSilent then
              MsgBox('PDF Studio is open. Save your work and use Quit PDF Studio before uninstalling. Your session has been left open.', mbInformation, MB_OK);
            exit;
          end;
      until not FindNext(Found);
    finally
      FindClose(Found);
    end;
  end;
end;
