; ==============================================================================
; MUALLİMUN AI SES STÜDYOSU PRO (v1.2.0) — INNO SETUP 6 KURULUM BETİĞİ
; Mimari: 64-Bit Windows 10/11 | PyInstaller (--onedir) Dağıtımı
; ==============================================================================

#define MyAppName "Muallimun AI Ses Stüdyosu Pro"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "Muallimun Dijital Eğitim Teknolojileri"
#define MyAppURL "https://muallimun.net"
#define MyAppRepoURL "https://github.com/muallimun/Muallimun_Ses_Asistani"
#define MyAppExeName "MuallimunStudyoPro.exe"
#define MyDistDir "dist\MuallimunStudyoPro"

[Setup]
; Benzersiz Uygulama Kimliği (Güncellemelerin aynı klasörü tanıması için sabittir)
AppId={{8F4A92B1-5C7E-4D3A-9B12-7E6F4C8A2026}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppRepoURL}
AppUpdatesURL={#MyAppRepoURL}/releases
AppCopyright=Copyright (C) 2026 {#MyAppPublisher}

; 64-Bit Mimari Kilidi (PyTorch ve CUDA için zorunlu)
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Yönetici izni (UAC) takılmalarını ve SQLite/JSON yazma hatalarını önlemek için
; varsayılan olarak kullanıcı प्रोग्राम dizinine (AppData\Local\Programs) kurar.
DefaultDirName={autopf}\MuallimunStudyoPro
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
AllowNoIcons=yes

; Bilgilendirme ve Lisans Ekranları
LicenseFile=LICENSE
InfoBeforeFile=kurulum_oncesi_bilgi.txt
InfoAfterFile=kurulum_sonrasi_rehber.txt

; Çıktı Klasörü ve İkon Ayarları
OutputDir=installer_cikti
OutputBaseFilename=Muallimun_Studyo_Pro_v{#MyAppVersion}_Setup
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} v{#MyAppVersion}

; Görsel Sihirbaz Stili
WizardStyle=modern
WizardSizePercent=115,115
DisableWelcomePage=no
ShowLanguageDialog=auto

; Sıkıştırma ve 2 GB Üstü Büyük Paket / GitHub Releases (<2GB) Desteği
; NOT: Eğer tek bir .exe dosyası üretmek isterseniz aşağıdaki DiskSpanning=yes
; satırını DiskSpanning=no yapabilirsiniz (Sıkışmış boyut 2.0 GB altında kalırsa tek .exe olur).
Compression=lzma2/fast
LZMADictionarySize=16384
LZMANumBlockThreads=2
LZMAUseSeparateProcess=yes
SolidCompression=no
DiskSpanning=yes
DiskSliceSize=1950000000

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Dirs]
; Kullanıcının ürettiği sesler, özel sesler ve ayarlar güncelleme/kaldırma sırasında silinmez
Name: "{app}\config"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\cikti_sesler"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\cikti_sesler\tekli_studyo"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\cikti_sesler\diyaloglar"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\cikti_sesler\metinler"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\referans_sesler_ozel"; Permissions: users-modify; Flags: uninsneveruninstall

[Files]
; 1. Ana EXE, _internal kütüphaneleri, ffmpeg.exe ve 8 referans WAV dosyası
; (config klasörü hariç tüm derleme dizini)
Source: "{#MyDistDir}\*"; DestDir: "{app}"; Excludes: "config\*,\.studyo_ref_cache*,cikti_sesler\*,referans_sesler_ozel\*"; Flags: ignoreversion recursesubdirs createallsubdirs

; 2. Fabrika presetleri her güncellemede yenilenir
Source: "{#MyDistDir}\config\factory_presets.json"; DestDir: "{app}\config"; Flags: ignoreversion

; 3. Ses havuzu ve hareke sözlüğü: Kullanıcı daha önce kurmuşsa mevcut özel seslerini/sözlüğünü ezmez!
Source: "{#MyDistDir}\config\voice_pool.json"; DestDir: "{app}\config"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "{#MyDistDir}\config\tashkeel_sozluk.json"; DestDir: "{app}\config"; Flags: onlyifdoesntexist uninsneveruninstall

; 4. Hızlı Başlangıç Rehberini uygulama klasörüne de bırak
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