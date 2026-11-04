# 🎙️ Muallimun AI Ses Stüdyosu Pro (v1.2.0)

**Fasih Arapça Vakıf/Vasıl Ön-İşleme • 24kHz Neural Ses Klonlama • 5-Katmanlı Stüdyo DSP Mastering**

**Muallimun AI Ses Stüdyosu Pro**, Arapça ders kitapları, dijital sözlükler, etkileşimli eğitim materyalleri ve e-öğrenme portalları ([muallimun.net](https://muallimun.net)) için geliştirilmiş açık kaynaklı, masaüstü yapay zeka seslendirme ve dublaj stüdyosudur.

---

## ✨ Temel Özellikler

* **⭐ 24kHz Neural Ses Klonlama (`Spark-TTS`):** `IbrahimSalah/Arabic-TTS-Spark` (BiCodec) mimarisiyle 8 hazır stüdyo karakterini (Yetişkin Erkek/Kadın, Çocuk Erkek/Kız) veya kendi eklediğiniz özel referans sesi birebir klonlayarak çevrimdışı (offline) ses üretir.
* **🛡️ Best-of-2 Akustik Klonlama Koruması:** Özel referans seslerde olası hizalama veya cızırtı sorunlarına karşı *Saf Akustik Kimlik Klonlama* ve *Best-of-2* doğallık seçimi ile en pürüzsüz çıktıyı garanti eder.
* **⚡ Hızlı Direkt Neural TTS:** Ekran kartı (VRAM) gerektirmeden çevrimiçi hazır Arapça neural seslerle hızlı ön-izleme ve seri üretim yapar.
* **🎭 8 Akustik Duygu ve Tonlama Profili:** *Otomatik (Noktalamaya Duyarlı)*, *Akademik Muallim*, *Sözlük (Tek Kelime)*, *Canlı Diyalog*, *Coşkulu Hitabet*, *Soru Tonlaması*, *Babacan & Hikmetli Nasihat* ve *Dingin Öyküleyici* profilleriyle metnin ruhuna uygun hız, sıcaklık ve DSP doygunluğu uygular.
* **🕌 Fasih Arapça Vakıf & Vasıl Motoru ve Hibrit Harekeleme:**
  * Cümle ve durak sonlarındaki *tâ-i merbûtayı* (`مَدْرَسَةٌ -> مَدْرَسَهْ`), *fetha tenvini* (`كِتَابًا -> كِتَابَا` / Medd-i İvaz), şedde ve son hareke sükûnunu otomatik uygular.
  * Uzun paragrafları bölerken *harf-i cer* ve bölünmez Arapça edatların (`فِي، مِنْ، إِلَى، عَلَى، أَنْ، لَا`) satır sonunda tek başına kalmasını engeller.
  * Harekesiz metinleri **2 Aşamalı Hibrit Tashkeel Motoru** (Çevrimiçi Mishkal + Devre Kesici + 360+ Kelimelik Yerel Eğitim Sözlüğü) ile otomatik harekeler.
* **📦 Toplu Seslendirme, Sürükle-Bırak & Seçmeli Kuyruk:** Excel (`.xlsx`), JSON, CSV ve TXT listelerini sürükle-bırak (*Drag & Drop*) ile içe aktarır. İster tüm listeyi, ister arama ve satır aralığı (`1 - 50`) seçimiyle yalnızca belirlediğiniz satırları seslendirir.
* **⏭️ İçerik ve Parametre Adresli Checkpoint v2 (SQLite WAL):** Yarıda kalan toplu işlemlerde metin, ses karakteri, motor, hız, sıcaklık ve DSP parmak izini doğrulayarak mevcut sağlam dosyaları atlar, kaldığı yerden devam eder.
* **🎬 Çoklu Rol Diyalog ve Uzun Metin Stüdyosu:** Diyalog JSON dosyalarındaki konuşmacılara cinsiyet ve rollerine göre 8 sesten çakışmasız rol dağıtır; seçilen veya tüm diyalogları ayrı klasörlerde hem satır satır hem de birleştirilmiş `diyalog_tamami.mp3` olarak üretir.
* **🎚️ Anti-Aliasing Stüdyo DSP & Teknik QA:** DC Offset temizliği, High-Pass (`80Hz`), yumuşak RMS gürültü kapısı, `Tanh Drive` harmonik doygunluk, 4. derece Butterworth Low-Pass (`11.2kHz`) anti-aliasing filtre, FFmpeg True-Peak Limiter (`level=0`) ve dalga formu üzerinde gerçek RMS/dBFS kalite kontrolü sunar.
* **☀️/🌙 Aydınlık & Karanlık Stüdyo Teması ve A+/A- Tipografi:** Göz konforuna uygun Gece Mavisi Koyu Stüdyo ve Aydınlık Kitap Kağıdı temaları ile düzeni bozmayan `➕ A+` / `➖ A-` Arapça yazı boyutu kontrolü.

---

## 💿 Kurulum Seçenekleri

### Seçenek A: Hazır Kurulum Paketi (`Setup.exe` — Son Kullanıcılar İçin Önerilen)
Python veya ek kütüphane kurulumuyla uğraşmadan doğrudan çalıştırmak için:
1. Sağ menüdeki **[Releases](https://github.com/muallimun/Muallimun_Ses_Asistani/releases)** sayfasından en güncel `Muallimun_Studyo_Pro_v1.2.0_Setup.exe` kurulum dosyasını (ve varsa `.bin` veri paketlerini) aynı klasöre indirin.
2. `Setup.exe` dosyasını çalıştırarak kurulumu tamamlayın ve masaüstü kısayolundan stüdyoyu başlatın.

---

### Seçenek B: Kaynak Koddan Kurulum ve Çalıştırma (Geliştiriciler İçin — Python 3.12)

#### 1. Depoyu İndirin
```powershell
git clone [https://github.com/muallimun/Muallimun_Ses_Asistani.git](https://github.com/muallimun/Muallimun_Ses_Asistani.git)
cd Muallimun_Ses_Asistani
```

#### 2. PyTorch (CUDA 12.1) ve Gerekli Kütüphaneleri Kurun
NVIDIA ekran kartı (GPU) hızlandırması için önce PyTorch CUDA sürümünü, ardından diğer bağımlılıkları yükleyin:
```powershell
py -3.12 -m pip install torch==2.5.1+cu121 torchaudio==2.5.1+cu121 --index-url [https://download.pytorch.org/whl/cu121](https://download.pytorch.org/whl/cu121)
py -3.12 -m pip install -r requirements.txt
```

#### 3. Uygulamayı Başlatın
```powershell
py -3.12 main.py
```

---

## ⌨️ Pratik Klavye Kısayolları

| Kısayol | İşlev |
| :--- | :--- |
| **`Ctrl + Enter`** | Aktif Arapça metni hemen seslendir (1. Sekme) |
| **`Esc`** | Devam eden ses sentezini güvenli şekilde durdur |
| **`Ctrl + (+)` / `Ctrl + (-)`** | Arapça metin alanı yazı boyutunu büyüt / küçült (`A+` / `A-`) |
| **`F1`** | Kapsamlı Kullanım Kılavuzunu ve 5 Adımlı Başlangıç Turunu aç |

---

## 📂 Proje Dizin Yapısı

```text
Muallimun_Ses_Asistani/
├── main.py                      # Uygulama giriş noktası ve ortam kontrolü
├── core/
│   ├── config_manager.py        # Atomik JSON ayarları, 5 preset ve özel ses havuzu yönetimi
│   ├── studyo_motoru.py         # Spark-TTS, Direkt TTS, XTTS v2, Vakıf/Vasıl ve 24kHz DSP motoru
│   └── batch_worker.py          # Toplu üretim işçisi, 8 tonlama profili, Excel/JSON/CSV/TXT ve SQLite Checkpoint v2
├── ui/
│   ├── main_window.py           # Ana stüdyo penceresi (Sekme 1, 2, 3), Waveform QA ve ses oynatıcı
│   ├── studyo_sekmeler_b.py     # Toplu Seslendirme (Sekme 4) ve Diyalog/Uzun Metin Stüdyosu (Sekme 5)
│   ├── setup_wizard.py          # Modeller rehberi, Tıkla-Kur kütüphane yöneticisi ve referans ses denetimi
│   └── rehber_ve_guncelleyici.py# Hibrit Arapça harekeleme motoru, QSS temaları, kılavuz ve GitHub güncelleyici
├── config/
│   ├── factory_presets.json     # 5 içerik modunun fabrika DSP ve sentez parametreleri
│   ├── voice_pool.json          # 8 yerleşik stüdyo karakteri ve özel ses tanımları
│   └── tashkeel_sozluk.json     # Öğrenen yerel Arapça harekeleme sözlüğü
├── ref_*.wav                    # 24kHz yerleşik stüdyo referans ses dosyaları (8 karakter)
├── requirements.txt             # Python 3.12 bağımlılık listesi
├── SECURITY.md                  # Güvenlik politikası ve veri bütünlüğü standartları
└── LICENSE                      # MIT Lisansı ve üçüncü taraf model bildirimleri
```

---

## 📄 Lisans ve İletişim

Bu projenin kaynak kodları **MIT Lisansı** altında sunulmaktadır. Çalışma zamanında kullanılan yapay zeka ses modelleri (`IbrahimSalah/Arabic-TTS-Spark`, `Coqui XTTS v2`, `Edge-TTS`) kendi orijinal lisanslarına tabidir; ayrıntılar için [LICENSE](LICENSE) dosyasına bakınız.

* **Geliştirici:** Muallimun Dijital Eğitim Teknolojileri — [muallimun.net](https://muallimun.net)
* **GitHub Deposu:** [github.com/muallimun/Muallimun_Ses_Asistani](https://github.com/muallimun/Muallimun_Ses_Asistani)