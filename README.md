# 🎙️ Muallimun AI Ses Stüdyosu Pro (v1.2.1)

**Yüzlerce Metni Tek Komutla Toplu Seslendirme • 24kHz GPU Neural Ses Klonlama • Fasih Arapça Vakıf/Vasıl Motoru • 5-Katmanlı Stüdyo DSP Mastering**

🌐 **Canlı Tanıtım ve Görsel Kılavuz:** [https://muallimun.com/muallimun_ses_studyosu/](https://muallimun.com/muallimun_ses_studyosu/)  
🏛️ **Kurumsal Portal:** [Muallimun.Net (www.muallimun.com)](https://www.muallimun.com)  
⬇️ **Doğrudan Kurulum Paketi (Windows 64-Bit Tek .EXE):** [Muallimun_Studyo_Pro_Setup.exe İndir](https://github.com/muallimun/Muallimun_Ses_Asistani/releases/latest/download/Muallimun_Studyo_Pro_Setup.exe)

---

## 🌟 Muallimun AI Ses Stüdyosu Pro Nedir ve Diğer TTS Araçlarından Nasıl Ayrılır?

**Muallimun AI Ses Stüdyosu Pro**; Arapça ders kitapları, dijital sözlükler, etkileşimli eğitim materyalleri (flipbook, SCORM, mobil uygulamalar) ve e-öğrenme portalları için özel olarak geliştirilmiş açık kaynaklı, masaüstü yapay zeka ses klonlama ve toplu seslendirme stüdyosudur.

Standart metin okuma (TTS) araçları tek seferde yalnızca bir metni okutup sıradan ve mekanik bir ses çıktısı verirken, **Muallimun AI Ses Stüdyosu Pro** eğitim yayıncılığı ve içerik üretimi için şu **6 temel farkı** sunar:

1. **📦 Yüzlerce Kelime, Cümle, Diyalog ve Metni Tek Komutla Seslendirme:**
   * Excel (`.xlsx`), JSON, CSV veya TXT dosyalarınızdaki yüzlerce hatta binlerce satırı sürükle-bırak (*Drag & Drop*) ile tabloya yükleyip **tek bir komutla** sırayla seslendirebilirsiniz.
   * Kaynak dosyanızda belirlediğiniz özel dosya adlarını (`ses_dosyasi`, `ses_erkek`, `ses_kadin`) birebir korur; her kelime veya cümleyi ister tek karakterle ister **Erkek + Kadın çift üretim** olarak ayrı klasörlere kaydeder.
   * **Referans Ses İmzalı Checkpoint v2 (SQLite WAL):** Yarıda kalan büyük listelerde metin, tonlama, DSP ve referans ses dosyası imzasını doğrulayarak sağlam kayıtları atlar ve kaldığı yerden devam eder.
2. **🚀 Gerçek GPU (NVIDIA CUDA) Hızlandırma ve Akıllı VRAM Ölçekleme:**
   * Varsayılan ana motorumuz **⭐ Spark-TTS**, ses sentezini doğrudan ekran kartınızın (GPU) CUDA çekirdekleri üzerinde çalıştırır.
   * **Yüksek kaliteli ve güçlü ekran kartlarında (RTX 3060 / 4060 / 4070 / 4080 vb.) sentez hızı ve toplu üretim verimi katlanarak artar; uzun Arapça cümleler doğal nefes gruplarıyla sıfır kesilmeyle üretilir.**
3. **🎙️ 8 Hazır Stüdyo Karakteri + Kendi Özel Referans Sesinizi Klonlama:**
   * Uygulama içinde hazır gelen **8 stüdyo karakterini** (2 Yetişkin Erkek, 2 Yetişkin Kadın, 2 Erkek Çocuk, 2 Kız Çocuk) kullanabilir veya **4–12 saniyelik** temiz bir ses kaydı ekleyerek kendi sesinizi / dilediğiniz bir spikerin sesini 24kHz kalitesinde klonlayabilirsiniz.
4. **🟢 İster Hazır Modlarla Tek Tıkla Üretim (Kolay Mod), 🟣 İster Sese Profesyonel Müdahale (Uzman Mod):**
   * **Kolay Mod:** Teknik ayarlarla uğraşmadan *Tek Kelime, Cümle, Atasözü, Diyalog* veya *Uzun Metin* modunu ve **8 Akustik Duygu/Tonlama Profilinden** birini seçip hemen ses üretin.
   * **Uzman Mod:** Sese profesyonel dokunuşlar yapmak istediğinizde *Okuma Hızı, Sıcaklık (Temperature), Top-K/Top-P, Min/Max Token, High-Pass/Low-Pass Filtre, RMS Gürültü Kapısı, Tanh Drive Sıcaklığı* ve *Başlangıç/Bitiş Nefes Payları* dahil **18+ akustik parametreyi** dahili `ℹ️` açıklama rehberleriyle dilediğiniz gibi özelleştirin.
5. **🕌 Fasih Arapça Kıraat, Vakıf/Vasıl ve 2 Aşamalı Hibrit Harekeleme:**
   * Cümle ve durak sonlarındaki *tâ-i merbûtayı* (`مَدْرَسَةٌ -> مَدْرَسَهْ`), fetha tenvinleri (`عَفْوًا -> عَفْوَنْ`), *Kat' ve Vasıl hemzelerini* (`إِنْسَان، إِسْمَاعِيل، اِسْمُكَ`), *Mîm-i Cem* geçişlerini (`عَلَيْهِمُ الْمَسْجِدُ`), *İltikaü's-Sakineyn* kurallarını (`وَمِنَ الْبَيْتِ، رَأَوُ الْوَلَدْ`), mansub med vakfını (`الْقَاضِيَ -> الْقَاضِي`) ve son hareke sükûnunu (`اَلْعِلْمُ نُورٌ -> اَلْعِلْمُ نُورْ`) otomatik uygular.
   * Eksik harekeli veya harekesiz metinleri **2 Aşamalı Hibrit Tashkeel Motoru** (Öğrenen Yerel Eğitim Sözlüğü + Çevrimiçi Mishkal + Bitişik Harf-i Cer/Atıf İ'rab Tamamlayıcı) ile tek tıkla harekeler.
6. **🎭 Çoklu Rol Diyalog ve Uzun Metin Birleştirme Stüdyosu:**
   * Diyalog metinlerindeki konuşmacıları (Öğretmen, Anne, Baba, Çocuk vb.) analiz ederek 8 sesten otomatik rol dağıtır; her diyaloğu kendi klasöründe hem satır satır hem de aktif konuşma enerjisi (`Gated RMS`) dengelenmiş ve doğal nefes boşluklarıyla birleştirilmiş tek parça (`diyalog_tamami.mp3` / `tamami.mp3`) olarak üretir.

---

## 🆕 v1.2.1 Sürümünde Öne Çıkan Yenilikler

* **İlk Hece Korumalı ve Kenar Dolgulu (Edge-Padded) 24kHz DSP:** RMS gürültü kapısında `mode="edge"` kenar dolgusu ile ilk 50 ms'deki `-6 dB` kazanç düşüşü tamamen giderildi; `لَا، / نَعَمْ، / كِتَابٌ / لِلطُّلَّابِ` gibi kısa kelimelerin ve şeddeli ilk hecelerin yutulmasını önleyen `<48 ms` darbe filtresi devreye alındı.
* **Gelişmiş Fasih Arapça (MSA) Fonetik Motoru:** Cümle ortasındaki Kat' hemzesi (`إِنْسَان، إِسْمَاعِيل، إِنْشَاء`) koruması, Mîm-i Cem (`عَلَيْهِمُ الْـ، بِهِمُ الْـ، ذَهَبْتُمُ الْـ`) dammesi, çoğul fiil (`رَأَوُ الْـ`) geçişi, `وَلِلطُّلَّابِ / فَلِلْمُعَلِّمِ` harekeleme desteği ve izafet/sıfat tamlaması korumalı cümle bölücü eklendi.
* **Aktif Konuşma Enerjili (Gated RMS) Ses Birleştirme:** Diyalog ve uzun metin birleştirmelerinde virgül duraksamalarından etkilenmeyen aktif konuşma RMS dengelemesi ve `±%12` doğal insan nefesi varyansı (jitter) eklendi.
* **Tam Senkronize Arayüz (UI/UX):** 4. ve 5. sekmelerde ikiz kart düzeni, mevcut üretilen satırları ve `🔊 Dinle` butonlarını sıfırlamayan `➕ Satır Ekle / ➖ Satır Sil` araçları, seçili satır harekeleme ve 1./3./4./5. sekmeler arası çift yönlü motor/preset senkronizasyonu tamamlandı.

---

## 🚀 GPU (NVIDIA CUDA) Hızlandırma Mimarisi ve 4 Kademeli Performans Ölçekleme

Uygulamanın varsayılan ana ses klonlama motoru olan **⭐ Spark-TTS (`IbrahimSalah/Arabic-TTS-Spark`)**, derin öğrenme tabanlı 24kHz BiCodec ses sentezini **GPU (Ekran Kartı)** üzerinde gerçekleştirir.

* **Ekran Kartı Gücünün Hıza ve Kaliteye Etkisi:** Bilgisayarınızdaki NVIDIA ekran kartının CUDA çekirdek sayısı ve VRAM (Video Belleği) kapasitesi ne kadar yüksekse, ses dalgalarının örülme hızı o kadar yükselir. Özellikle yüzlerce satırlık **Toplu Seslendirme** ve **Çoklu Diyalog** işlemlerinde güçlü bir GPU, saatler sürebilecek işlemleri dakikalar içinde tamamlar.
* **Akıllı 4 Kademeli Donanım Yönetimi (`⚡ GPU Optimize`):** Uygulama açılışta ekran kartınızın modelini ve **gerçek boş VRAM** miktarını otomatik ölçerek aşağıdaki 4 performans kademesinden en uygununu devreye alır (Dilerseniz üst bardaki **⚡ GPU Optimize** butonundan kademeyi kendiniz de seçebilirsiniz):

| Donanım Kademesi | Hedef Ekran Kartı / Donanım | Nefes Grubu Eşiği & Token Bütçesi | Performans ve Verim Etkisi |
| :--- | :--- | :--- | :--- |
| **🚀 Kademe 1: Pro Stüdyo Tam Kapasite** | **10 GB / 12 GB+ VRAM** *(RTX 3060 12GB, 3080, 4070, 4080, 4090 vb.)* | **16 Kelimeye Kadar Tek Nefes** *(1180 Max Token)* | **Maksimum Hız & Verim:** 16 kelimeye kadar tek nefeste, daha uzun cümleleri ise bağlaç sınırlarından doğal nefes gruplarıyla en yüksek hızda üretir. |
| **⚖️ Kademe 2: Dengeli Stüdyo Performansı** | **7 GB – 10 GB VRAM** *(RTX 2070, 3060 Ti, 3070, 4060, 4060 Ti vb.)* | **15 Kelimeye Kadar Tek Nefes** *(1050 Max Token)* | **Yüksek Hızlı Seri Üretim:** 15 kelimeye kadar tek nefeste okur, uzun cümleleri tamlama bütünlüğünü koruyarak nefes gruplarına böler. |
| **⚡ Kademe 3: Hafif ve Hızlı Laptop Modu** | **4 GB – 6 GB VRAM** *(RTX 3050, 3050 Ti, GTX 1650/1660, RTX 2060 vb.)* | **14 Kelimeye Kadar Tek Nefes** *(980 Max Token + Otomatik Önbellek Temizliği)* | **4 GB VRAM Koruma Kalkanı:** 14 kelimeye kadar tek nefeste okur; her üretimde VRAM'i temizleyerek bellek taşmasını ve son kelime kesilmesini önler. |
| **💻 Kademe 4: CPU (İşlemci) Modu** | **Harici GPU Olmayan Sistemler** *(Dahili GPU + Çok Çekirdekli CPU)* | **12 Kelimeye Kadar Tek Nefes** *(850 Max Token)* | Ekran kartı olmadan işlemci üzerinde güvenli klonlama yapar (Ekran kartsız PC'lerde en hızlı üretim için **⚡ Hızlı Direkt TTS** önerilir). |

---

## 💿 Kurulum Seçenekleri

### Seçenek A: Tek Parça Hazır Kurulum Paketi (`Setup.exe` — Son Kullanıcılar İçin Önerilen)
Python, PyTorch, CUDA veya FFmpeg kurulumuyla uğraşmadan doğrudan çalıştırmak için:

1. **[Muallimun_Studyo_Pro_Setup.exe](https://github.com/muallimun/Muallimun_Ses_Asistani/releases/latest/download/Muallimun_Studyo_Pro_Setup.exe)** (~1.57 GB) tek parça kurulum dosyasını bilgisayarınıza indirin.
2. İndirdiğiniz **`Muallimun_Studyo_Pro_Setup.exe`** dosyasına çift tıklayarak kurulumu tamamlayın.
   * *(Not: Windows SmartScreen koruma ekranı çıkarsa **"Ek bilgi"** → **"Yine de çalıştır"** seçeneğine tıklayın. Kurulum sihirbazı yazma izni sorunlarını önlemek için kullanıcı profilinize otomatik kurulur ve mevcut seslerinizi/ayarlarınızı korur.)*
3. Masaüstünde oluşan **Muallimun AI Ses Stüdyosu Pro** kısayoluyla stüdyoyu başlatın.

---

### Seçenek B: Kaynak Koddan Kurulum ve Çalıştırma (Geliştiriciler İçin — Python 3.12)

#### 1. Depoyu İndirin
~~~powershell
git clone https://github.com/muallimun/Muallimun_Ses_Asistani.git
cd Muallimun_Ses_Asistani
~~~

#### 2. PyTorch (CUDA 12.1) ve Gerekli Kütüphaneleri Kurun
NVIDIA ekran kartı (GPU) hızlandırması için önce PyTorch CUDA sürümünü, ardından diğer bağımlılıkları yükleyin:
~~~powershell
py -3.12 -m pip install torch==2.5.1+cu121 torchaudio==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121
py -3.12 -m pip install -r requirements.txt
~~~

#### 3. Uygulamayı Başlatın
~~~powershell
py -3.12 main.py
~~~

---

## 🧠 Desteklenen 3 Seslendirme Motoru Karşılaştırması

| Ses Motoru | Çalışma Ortamı | Hareke & Klonlama | En Uygun Kullanım Senaryosu |
| :--- | :--- | :--- | :--- |
| **1. ⭐ Spark-TTS (`IbrahimSalah/Arabic-TTS-Spark`)** | Yerel GPU / CPU (Çevrimdışı) | **Tam Harekeli Metin Zorunlu** • 24kHz Birebir Ses Klonlama | Harekeli ders kitapları, sözlük kelimeleri, gramer cümleleri, atasözleri ve 8 karakterli diyaloglar için **önerilen ana stüdyo motoru**. |
| **2. ⚡ Hızlı Direkt Neural TTS** | Çevrimiçi Servis (0 MB VRAM) | Harekeli ve Harekesiz Okur • Hazır Neural Ses Kullanır | Harekesiz metinler, hızlı ön-izleme ve harici ekran kartı olmayan bilgisayarlarda seri üretim. |
| **3. 🗣️ Coqui XTTS v2** | Yerel GPU / CPU (Çevrimdışı) | Alternatif / Deneysel Çok Dilli Klonlama | Alternatif ses rengi denemeleri (Arapça mahreç ve hareke sadakati Spark-TTS kadar yüksek değildir). |

---

## 🎭 8 Akustik Duygu ve Tonlama Profili

Seçtiğiniz tonlama profili; konuşma hızını, örnekleme sıcaklığını (`temperature`), `top_p / top_k` kararlılığını, `Tanh Drive` doygunluğunu ve cümle sonu sönümlenme payını otomatik kalibre eder:

| Tonlama Profili | Akustik Karakter ve DSP Etkisi |
| :--- | :--- |
| **✨ 1. Otomatik (Noktalamaya Duyarlı)** | Evet/Hayır sorusu (`هَلْ`), soru edatı (`أَيْنَ/كَيْفَ`), ünlem (`!`), tek kelime ve cümle uzunluğunu algılayarak en kararlı doğal MSA tonlamasını uygular. |
| **🔤 2. Sözlük & Tek Kelime** | Düşük sıcaklık (`0.50`), dar örnekleme (`top_k=22`, `top_p=0.80`) ve net vakıf sükûnu ile sıfır sapmalı mahreç okuması yapar. |
| **🎓 3. Akademik Muallim** | Gramer örnekleri ve ders kitabı cümleleri için tane tane, sakin ve anlaşılır öğretmen tonu (`0.94x`) sağlar. |
| **🌿 4. Babacan & Hikmetli Nasihat** | Atasözleri ve vecizeler için ağırbaşlı tempo (`0.89x`), bağlaçlardan önce otomatik tefekkür durağı (`،`) ve sıcak tını uygular. |
| **🎭 5. Canlı & Enerjik Diyalog** | Karşılıklı konuşma ve diyalog replikleri için doğal, akıcı ve samimi konuşma vurgusu sağlar. |
| **❓ 6. Soru & Merak Vurgusu** | Soru edatları (`هَلْ، مَاذَا، كَيْفَ، أَيْنَ`) içeren cümlelerde soru vurgusunu kararlı şekilde belirginleştirir. |
| **❗ 7. Coşkulu & Vurgulu Hitabet** | Ünlem, nida (`يَا أَيُّهَا`) ve hitabet cümleleri için dolgun gövdeli ve güçlü vurgu sunar. |
| **📖 8. Dingin Öyküleyici (Anlatıcı)** | Uzun okuma parçaları ve hikayeler için dinleyiciyi yormayan, dengeli anlatıcı temposu sağlar. |

---

## 📊 Toplu Seslendirme İçin Desteklenen Sütun İsimleri (Excel, JSON, CSV)

**4. Sekmede (Toplu Seslendirme)** kendi Excel (`.xlsx`), CSV veya JSON dosyanızı yüklerken aşağıdaki sütun/alan adlarını kullanabilirsiniz (Uygulama içinden hazır şablon da indirebilirsiniz):

| Alan / Sütun Adı | Zorunlu mu? | Ne İşe Yarar ve Nasıl Çalışır? |
| :--- | :--- | :--- |
| **`arapca`** *(veya `metin`, `kelime`)* | ✅ **Zorunlu** | Seslendirilecek Arapça kelime, cümle veya paragraf metni. |
| **`ses_dosyasi`** *(veya `dosya_adi`, `filename`)* | İsteğe Bağlı | Tekil üretimde çıkacak ses dosyasının özel adı (Örn: `unite1_kelime05.mp3`). Belirtilmezse `id` kullanılır. |
| **`ses_erkek` / `ses_kadin`** | İsteğe Bağlı | Çift üretimde (`Erkek + Kadın`) erkek ve kadın ses dosyalarına verilecek özel dosya adları. |
| **`id`** *(veya `kod`, `sira`)* | Önerilir | Özel dosya adı belirtilmemişse ses dosyasının kaydedileceği benzersiz kimlik (Örn: `cumle_0001`). |
| **`ses_secimi`** *(veya `referans_ses`)* | İsteğe Bağlı | Satıra özel karakter seçimi: `otomatik`, `IKISI` (Çift üretim), `E1`, `E2`, `K1`, `K2`, `EC1`, `EC2`, `KC1`, `KC2`, `DIREKT`. |
| **`turkce`** *(veya `anlam`, `not`)* | İsteğe Bağlı | Tabloda bilgi ve arama kolaylığı sağlayan Türkçe anlam veya ders notu. |

---

## 🎚️ 5-Katmanlı 24kHz Stüdyo DSP Mastering ve Teknik Kalite Kontrolü (QA)

Üretilen her ses dosyası diske kaydedilmeden önce şu 5 akustik katmandan geçirilir:
1. **Saf Referans ve Doğal Nefes Koruması:** Özel referans seslerde doğal nefes aralıklarını (`420 ms -> 220 ms`, `22 ms` Raised-Cosine geçiş) koruyarak konuşmacı ritmini modele aktarır.
2. **18ms Onset Yumuşatma & Sıfır Fazlı Butterworth High-Pass Filtre (`80 Hz`):** Sesin doğal gövdesini koruyarak başlangıç darbelerini ve dip uğultularını temizler.
3. **Kenar Dolgulu (`mode="edge"`) Yumuşak RMS Gürültü Kapısı ve İlk Hece Kalkanı:** İlk 50 ms'de hiçbir ses kaybı yaşatmadan kelime aralarındaki boşluk tıslamalarını süzer; kısa ilk kelimeleri (`لَا، / نَعَمْ،`) ve son harf sükûnlarını korur.
4. **Anti-Aliasing Harmonik Sıcaklık (`%65 Dry + %35 Wet Tanh Drive` → `2. Derece Butterworth LPF` + DC Sıfırlama):** Peltek ve ıslıklı Arapça harflerin (`س، ص، ث، ش`) netliğini bozmadan dijital cızırtıları süzer.
5. **Kosinüs Eğrili Doğal Çıkış (`150 ms` Fade-Out + `120 ms` Nefes Yastığı) ve FFmpeg True-Peak Limiter (`-1.0 dBFS`):** Son kelimenin aniden kesilmesini ve MP3 dönüşümünde sesin çatlamasını (clipping) önler.

---

## ⌨️ Pratik Klavye Kısayolları

| Kısayol | İşlev |
| :--- | :--- |
| **`Ctrl + Enter`** | Aktif Arapça metni hemen seslendir (1. Sekme) |
| **`Esc`** | Devam eden ses sentezini güvenli şekilde durdur |
| **`Ctrl + (+)` / `Ctrl + (-)`** | Arapça metin alanı yazı boyutunu büyüt / küçült (`➕ A+` / `➖ A-`) |
| **`F1`** | Kapsamlı Kullanım Kılavuzunu ve 5 Adımlı Başlangıç Turunu aç |

---

## 📂 Proje Dizin Yapısı

~~~text
Muallimun_Ses_Asistani/
├── main.py                      # Tekil çalışma kilidi (QLockFile/Mutex), DPI ve güvenli başlatıcı (v1.2.1)
├── version.json                 # GitHub otomatik güncelleme kontrolcüsü için sürüm ve yayın notları
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
├── MuallimunStudyoPro.spec      # PyInstaller derleme yapılandırması
├── MuallimunStudyoPro_Setup.iss # Inno Setup 6 tek parça kurulum paketi betiği
├── requirements.txt             # Python 3.12 bağımlılık listesi
├── SECURITY.md                  # Güvenlik politikası ve veri bütünlüğü standartları
└── LICENSE                      # MIT Lisansı ve üçüncü taraf model bildirimleri
~~~

---

## 📄 Lisans ve İletişim

Bu projenin kaynak kodları **MIT Lisansı** altında sunulmaktadır. Çalışma zamanında kullanılan yapay zeka ses modelleri (`IbrahimSalah/Arabic-TTS-Spark`, `Coqui XTTS v2`, `Edge-TTS`) kendi orijinal lisanslarına tabidir; ayrıntılar için [LICENSE](LICENSE) dosyasına bakınız.

* **Geliştirici:** Muallimun Dijital Eğitim Teknolojileri — [www.muallimun.com](https://www.muallimun.com)
* **Web Kılavuz ve İndirme Sayfası:** [muallimun.com/muallimun_ses_studyosu](https://muallimun.com/muallimun_ses_studyosu/)
* **GitHub Deposu:** [github.com/muallimun/Muallimun_Ses_Asistani](https://github.com/muallimun/Muallimun_Ses_Asistani)