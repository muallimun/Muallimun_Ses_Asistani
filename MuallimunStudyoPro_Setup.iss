; ==============================================================================
; MUALLİMUN AI SES STÜDYOSU PRO (v1.2.0) — INNO SETUP 6 TEK PARÇA KURULUM BETİĞİ
; Mimari: 64-Bit Windows 10/11 | Tekil .EXE | Kurulu Sürüm ve Açık Uygulama Algılamalı
; ==============================================================================

#define MyAppName "Muallimun AI Ses Stüdyosu Pro"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "Muallimun Dijital Eğitim Teknolojileri"
#define MyAppURL "https://www.muallimun.com"
#define MyAppGuideURL "https://muallimun.com/muallimun_ses_studyosu/"
#define MyAppRepoURL "https://github.com/muallimun/Muallimun_Ses_Asistani"
#define MyAppExeName "MuallimunStudyoPro.exe"
#define MyDistDir "dist\MuallimunStudyoPro"

[Setup]
; Benzersiz Uygulama Kimliği (Güncellemelerin ve kurulu sürüm tespitinin anahtarıdır)
AppId={{8F4A92B1-5C7E-4D3A-9B12-7E6F4C8A2026}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppGuideURL}
AppUpdatesURL={#MyAppRepoURL}/releases
AppCopyright=Copyright (C) 2026 {#MyAppPublisher}

; Uygulama açıkken kurulum yapılmasını önleyen Windows Mutex kilidi (main.py ile tam uyumlu)
AppMutex=MuallimunStudyoPro_Running_Mutex
CloseApplications=yes

; 64-Bit Mimari Kilidi (PyTorch ve CUDA için zorunlu)
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Program Files yazma izni (PermissionError) sorunlarını %100 önlemek için
; doğrudan kullanıcının yazma izni olan AppData\Local\Programs dizinine kurar.
DefaultDirName={localappdata}\Programs\MuallimunStudyoPro
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
AllowNoIcons=yes

; Bilgilendirme ve Lisans Ekranları
LicenseFile=LICENSE
InfoBeforeFile=kurulum_oncesi_bilgi.txt
InfoAfterFile=kurulum_sonrasi_rehber.txt

; Çıktı Klasörü ve Sabit (Versiyonsuz) Kurulum Dosyası Adı
OutputDir=installer_cikti
OutputBaseFilename=Muallimun_Studyo_Pro_Setup
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} (v{#MyAppVersion})

; Görsel Sihirbaz Stili
WizardStyle=modern
WizardSizePercent=115,115
DisableWelcomePage=no
ShowLanguageDialog=auto

; Tek Parça .EXE ve Bellek Dostu (Out of Memory Önleyici) Sıkıştırma Ayarları
DiskSpanning=no
Compression=lzma2/fast
LZMADictionarySize=16384
LZMANumBlockThreads=2
LZMAUseSeparateProcess=yes
SolidCompression=no

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Dirs]
; Kullanıcının ürettiği sesler, özel referans sesler ve ayarlar güncelleme/kaldırma sırasında silinmez
Name: "{app}\config"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\cikti_sesler"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\cikti_sesler\tekli_studyo"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\cikti_sesler\diyaloglar"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\cikti_sesler\metinler"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\referans_sesler_ozel"; Permissions: users-modify; Flags: uninsneveruninstall

[Files]
; 1. Ana EXE, _internal kütüphaneleri, ffmpeg.exe ve 8 referans WAV dosyası
; (Geliştirici makinesindeki geçici önbellekler, kişisel ayarlar ve deneme sesleri hariç tutulur)
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Excludes: "config\*,\.studyo_ref_cache*,cikti_sesler\*,referans_sesler_ozel\*,*.bak"; Flags: ignoreversion recursesubdirs createallsubdirs

; 2. Fabrika presetleri her güncellemede yenilenir
Source: "{#MyDistDir}\config\factory_presets.json"; DestDir: "{app}\config"; Flags: ignoreversion

; 3. Ses havuzu ve hareke sözlüğü: Kullanıcı daha önce kurmuşsa mevcut özel seslerini/sözlüğünü ezmez!
Source: "{#MyDistDir}\config\voice_pool.json"; DestDir: "{app}\config"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "{#MyDistDir}\config\tashkeel_sozluk.json"; DestDir: "{app}\config"; Flags: onlyifdoesntexist uninsneveruninstall

; 4. Hızlı Başlangıç Rehberini uygulama klasörüne bırak
Source: "kurulum_sonrasi_rehber.txt"; DestDir: "{app}"; DestName: "HIZLI_BASLANGIC_REHBERI.txt"; Flags: ignoreversion

[Icons]
; Başlat Menüsü Kısayolları
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\app_icon.ico"; Comment: "24kHz Neural Arapça Ses Klonlama ve Dublaj Stüdyosu"
Name: "{group}\Çıktı Sesler Klasörü"; Filename: "{app}\cikti_sesler"; Comment: "Üretilen ses dosyaları klasörü"
Name: "{group}\Hızlı Başlangıç Rehberi"; Filename: "{app}\HIZLI_BASLANGIC_REHBERI.txt"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Masaüstü Kısayolu
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon; Comment: "Muallimun AI Ses Stüdyosu Pro"

[Run]
; Kurulum bittiğinde stüdyoyu başlatma seçeneği
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Uygulama kaldırıldığında yalnızca geçici referans önbelleğini temizle (üretilen seslere dokunma)
Type: filesandordirs; Name: "{app}\.studyo_ref_cache_v8"
Type: filesandordirs; Name: "{app}\.studyo_ref_cache_v7"

[Code]
// Bilgisayarda uygulama zaten kuruluysa kullanıcıyı tespit edip bilgilendiren fonksiyon
function InitializeSetup(): Boolean;
var
  UninstallKey: String;
  InstalledVersion: String;
  MsgText: String;
begin
  Result := True;
  UninstallKey := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{8F4A92B1-5C7E-4D3A-9B12-7E6F4C8A2026}_is1';
  InstalledVersion := '';

  if not RegQueryStringValue(HKCU, UninstallKey, 'DisplayVersion', InstalledVersion) then
    RegQueryStringValue(HKLM, UninstallKey, 'DisplayVersion', InstalledVersion);

  if InstalledVersion <> '' then
  begin
    MsgText := 'Bilgisayarınızda Muallimun AI Ses Stüdyosu Pro (Kurulu Sürüm: v' + InstalledVersion + ') zaten yüklü görünüyor.' + #13#10 + #13#10 +
               'Mevcut kurulumu güncellemek veya onarmak istiyor musunuz?' + #13#10 + #13#10 +
               'ℹ️ Not: Ürettiğiniz ses dosyaları (cikti_sesler), eklediğiniz özel referans sesler ve hareke sözlüğünüz silinmez; olduğu gibi korunur.';
    if MsgBox(MsgText, mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
    end;
  end;
end;