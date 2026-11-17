# 🎙️ Muallimun AI Ses Stüdyosu Pro (v1.2.2)

**Yüzlerce Metni Tek Komutla Toplu Seslendirme • 24kHz GPU Neural Ses Klonlama • GPU Termal Koruma Kalkanı • Fasih Arapça Vakıf/Vasıl Motoru • 5-Katmanlı Stüdyo DSP Mastering**

🌐 **Canlı Tanıtım ve Görsel Kılavuz:** [https://muallimun.com/muallimun_ses_studyosu/](https://muallimun.com/muallimun_ses_studyosu/)  
🏛️ **Kurumsal Portal:** [Muallimun.Net (www.muallimun.com)](https://www.muallimun.com)  
⬇️ **Doğrudan Kurulum Paketi (Windows 64-Bit Tek .EXE):** [Muallimun_Studyo_Pro_Setup.exe İndir](https://github.com/muallimun/Muallimun_Ses_Asistani/releases/latest/download/Muallimun_Studyo_Pro_Setup.exe)

---

## 🌟 Muallimun AI Ses Stüdyosu Pro Nedir ve Diğer TTS Araçlarından Nasıl Ayrılır?

**Muallimun AI Ses Stüdyosu Pro**; Arapça ders kitapları, dijital sözlükler, etkileşimli eğitim materyalleri (flipbook, SCORM, mobil uygulamalar) ve e-öğrenme portalları için özel olarak geliştirilmiş bağımsız masaüstü yapay zeka ses klonlama ve toplu seslendirme stüdyosudur.

Standart metin okuma (TTS) araçları tek seferde yalnızca bir metni okutup sıradan ve mekanik bir ses çıktısı verirken, **Muallimun AI Ses Stüdyosu Pro** eğitim yayıncılığı ve içerik üretimi için şu **6 temel farkı** sunar:

1. **📦 Yüzlerce Kelime, Cümle, Diyalog ve Metni Tek Komutla Seslendirme:**
   * Excel (`.xlsx`), JSON, CSV veya TXT dosyalarınızdaki yüzlerce hatta binlerce satırı sürükle-bırak (*Drag & Drop*) ile tabloya yükleyip **tek bir komutla** sırayla seslendirebilirsiniz.
   * **Kalıcı Oturum Belleği (`oturum_durumu.json`):** 4. ve 5. sekmelerde yüklediğiniz kaynak dosyalar, tablo üzerinde yaptığınız harekelemeler ve üretilen seslerin durumları uygulama kapanıp açıldığında silinmez; kaldığınız yerden devam edebilirsiniz.
   * **Referans Ses İmzalı Checkpoint v2 (SQLite WAL) & İşlem Sonu Güç Yönetimi:** Yarıda kalan büyük listelerde sağlam kayıtları atlar; uzun gece üretimlerinde işlem bittiğinde bilgisayarınızı otomatik kapatabilir, uykuya alabilir veya kilitleyebilirsiniz.
2. **🚀 Gerçek GPU (NVIDIA CUDA) Hızlandırma, Canlı Sıcaklık Telemetrisi ve Termal Koruma:**
   * Varsayılan ana motorumuz **⭐ Spark-TTS**, ses sentezini doğrudan ekran kartınızın (GPU) CUDA çekirdekleri üzerinde çalıştırır.
   * **GPU Termal Kalkanı (75°C / 62°C) ve Periyodik Dinlendirme:** Saatler süren toplu üretimlerde ekran kartı sıcaklığını `nvml.dll` üzerinden anlık izler; sıcaklık **75°C**'ye ulaştığında üretimi geçici olarak soğutma molasına alır (**62°C**'ye düştüğünde devam eder) ve her **40 satırda bir 60 saniye** periyodik dinlendirme uygulayarak donanımınızı korur.
3. **🎙️ 8 Hazır Stüdyo Karakteri + Kendi Özel Referans Sesinizi Klonlama:**
   * Uygulama içinde hazır gelen **8 stüdyo karakterini** (2 Yetişkin Erkek, 2 Yetişkin Kadın, 2 Erkek Çocuk, 2 Kız Çocuk) kullanabilir veya **4–12 saniyelik** temiz bir ses kaydı ekleyerek kendi sesinizi / dilediğiniz bir spikerin sesini 24kHz kalitesinde klonlayabilirsiniz.
4. **🟢 İster Hazır Modlarla Tek Tıkla Üretim (Kolay Mod), 🟣 İster Sese Profesyonel Müdahale (Uzman Mod):**
   * **Kolay Mod:** Teknik ayarlarla uğraşmadan *Tek Kelime, Cümle, Atasözü, Diyalog* veya *Uzun Metin* modunu ve **8 Akustik Duygu/Tonlama Profilinden** birini seçip hemen ses üretin.
   * **Uzman Mod:** Sese profesyonel dokunuşlar yapmak istediğinizde *Okuma Hızı, Sıcaklık (Temperature), Top-K/Top-P, Min/Max Token, High-Pass/Low-Pass Filtre, RMS Gürültü Kapısı, Tanh Drive Sıcaklığı* ve *Başlangıç/Bitiş Nefes Payları* dahil **18+ akustik parametreyi** dahili `ℹ️` açıklama rehberleriyle dilediğiniz gibi özelleştirin.
5. **🕌 Fasih Arapça Kıraat, Vakıf/Vasıl ve 2 Aşamalı Hibrit Harekeleme:**
   * Cümle ve durak sonlarındaki *tâ-i merbûtayı* (`مَدْرَسَةٌ -> مَدْرَسَهْ`), fetha tenvinleri (`عَفْوًا -> عَفْوَنْ`), *Kat' ve Vasıl hemzelerini* (`إِنْسَان، إِسْمَاعِيل، اِسْمُكَ`), *Mîm-i Cem* geçişlerini (`عَلَيْهِمُ الْمَسْجِدُ`), *İltikaü's-Sakineyn* kurallarını (`وَمِنَ الْبَيْتِ، رَأَوُ الْوَلَدْ`), mansub med vakfını (`الْقَاضِيَ -> الْقَاضِي`) ve son hareke sükûnunu (`اَلْعِلْمُ نُورٌ -> اَلْعِلْمُ نُورْ`) otomatik uygular.
   * Eksik harekeli veya harekesiz metinleri **2 Aşamalı Hibrit Tashkeel Motoru** ile tek tıkla harekeler ve **`💾 Kuyruğu Kaydet`** butonuyla Excel (`.xlsx`) veya JSON olarak dışa aktarır.
6. **🎭 Çoklu Rol Diyalog ve Uzun Metin Birleştirme Stüdyosu:**
   * Diyalog metinlerindeki konuşmacıları (Öğretmen, Anne, Baba, Çocuk vb.) analiz ederek 8 sesten otomatik rol dağıtır; her diyaloğu kendi klasöründe hem satır satır hem de isteğe bağlı olarak aktif konuşma enerjisi (`Gated RMS`) dengelenmiş tek parça (`diyalog_tamami.mp3` / `tamami.mp3`) halinde üretir.

---

## 🆕 v1.2.2 Sürümünde Öne Çıkan Yenilikler

* **🌡️ GPU Termal Koruma Kalkanı ve Periyodik Dinlendirme (`⚡ GPU Optimize`):** Uzun süreli toplu seslendirmelerde ekran kartının aşırı ısınmasını önlemek için **75°C duraklatma / 62°C devam etme** sıcaklık kalkanı, **her 40 aktif satırda 60 saniye** periyodik dinlendirme molası ve her 25 satırda bir otomatik CUDA VRAM önbellek temizliği eklendi.
* **🚀 Doğrudan NVML (`nvml.dll`) Canlı GPU Sıcaklık ve VRAM Telemetrisi:** Üst bilgi çubuğuna ve GPU Optimize penceresine 5 saniyede bir güncellenen gerçek zamanlı GPU çekirdek sıcaklığı (`🌡️ °C`) ve aktif model VRAM kullanımı göstergesi eklendi.
* **🩺 4 Boyutlu Akustik Cızırtı/Gürültü Kalkanı ve `Sesleri Denetle` Aracı:** Üretilen seslerde yalnızca genlik değişimine değil; **İnsan Sesi Harmonik Perdesi (`80–420 Hz Autocorrelation Voicing`)**, **Yüksek Frekans Tıslama Oranı (`>5.5 kHz`)**, **Genel ve Kuyruk Sıfır Geçiş Oranı (`ZCR`)** ve **Kelime Başına Süre Sınırına** bakan 4 boyutlu doğrulama kuruldu. 3 deneme sonunda konuşma sinyali doğrulanamayan bozuk seslerin diske kaydedilmesi engellendi ve mevcut klasörleri tarayıp bozuk sesleri bulan **`🩺 Sesleri Denetle`** butonu eklendi.
* **💾 Kalıcı Oturum Belleği (`oturum_durumu.json`) ve `Kuyruğu Kaydet`:** 4. ve 5. sekmelerde yüklenen kaynak dosyaların, tablo düzenlemelerinin ve mevcut ses durumlarının uygulama kapatılıp açıldığında otomatik geri yüklenmesi sağlandı; harekelenmiş tabloyu `.xlsx` veya `.json` olarak dışa aktaran **`💾 Kuyruğu Kaydet`** aracı eklendi.
* **⚡ İşlem Sonu Otomatik Güç Yönetimi ve Gece Üretim Raporu:** 4. ve 5. sekmelerin alt çubuğuna toplu işlem tamamlandığında 60 saniye geri sayımlı **Bilgisayarı Kapat, Yeniden Başlat, Uykuya Al, Ekranı Kilitle ve Uygulamayı Kapat** seçenekleri ile çıktı klasörüne kaydedilen `son_uretim_raporu.txt` özet raporu eklendi.

---

## 🚀 GPU (NVIDIA CUDA) Hızlandırma Mimarisi ve 4 Kademeli Performans Ölçekleme

Uygulamanın varsayılan ana ses klonlama motoru olan **⭐ Spark-TTS (`IbrahimSalah/Arabic-TTS-Spark`)**, derin öğrenme tabanlı 24kHz BiCodec ses sentezini **GPU (Ekran Kartı)** üzerinde gerçekleştirir.

| Donanım Kademesi | Hedef Ekran Kartı / Donanım | Nefes Grubu Eşiği & Token Bütçesi | Performans ve Verim Etkisi |
| :--- | :--- | :--- | :--- |
| **🚀 Kademe 1: Pro Stüdyo Tam Kapasite** | **10 GB / 12 GB+ VRAM** *(RTX 3060 12GB, 3080, 4070, 4080, 4090 vb.)* | **16 Kelimeye Kadar Tek Nefes** *(1180 Max Token)* | **Maksimum Hız & Verim:** 16 kelimeye kadar tek nefeste, daha uzun cümleleri ise bağlaç sınırlarından doğal nefes gruplarıyla en yüksek hızda üretir. |
| **⚖️ Kademe 2: Dengeli Stüdyo Performansı** | **7 GB – 10 GB VRAM** *(RTX 2070, 3060 Ti, 3070, 4060, 4060 Ti vb.)* | **15 Kelimeye Kadar Tek Nefes** *(1050 Max Token)* | **Yüksek Hızlı Seri Üretim:** 15 kelimeye kadar tek nefeste okur, uzun cümleleri tamlama bütünlüğünü koruyarak nefes gruplarına böler. |
| **⚡ Kademe 3: Hafif ve Hızlı Laptop Modu** | **4 GB – 6 GB VRAM** *(RTX 3050, 3050 Ti, GTX 1650/1660, RTX 2060 vb.)* | **14 Kelimeye Kadar Tek Nefes** *(980 Max Token + Otomatik Önbellek Temizliği)* | **4 GB VRAM & Termal Koruma Kalkanı:** 14 kelimeye kadar tek nefeste okur; VRAM temizliği ve 75°C/62°C termal kalkan ile dizüstü GPU'ları korur. |
| **💻 Kademe 4: CPU (İşlemci) Modu** | **Harici GPU Olmayan Sistemler** *(Dahili GPU + Çok Çekirdekli CPU)* | **12 Kelimeye Kadar Tek Nefes** *(850 Max Token)* | Ekran kartı olmadan işlemci üzerinde güvenli klonlama yapar (Ekran kartsız PC'lerde en hızlı üretim için **⚡ Hızlı Direkt TTS** önerilir). |

---

## 💿 İndirme ve Kurulum Rehberi (Windows 10/11 64-Bit)

Python, PyTorch, CUDA veya FFmpeg kurulumuyla uğraşmadan doğrudan çalıştırmak için tüm bileşenler tek bir kurulum paketinde birleştirilmiştir:

1. **[Muallimun_Studyo_Pro_Setup.exe](https://github.com/muallimun/Muallimun_Ses_Asistani/releases/latest/download/Muallimun_Studyo_Pro_Setup.exe)** tek parça kurulum dosyasını bilgisayarınıza indirin.
2. İndirdiğiniz **`Muallimun_Studyo_Pro_Setup.exe`** dosyasına çift tıklayarak kurulumu tamamlayın.
   * *(Not: Windows SmartScreen koruma ekranı çıkarsa **"Ek bilgi"** → **"Yine de çalıştır"** seçeneğine tıklayın. Kurulum sihirbazı yazma izni sorunlarını önlemek için kullanıcı profilinize otomatik kurulur ve mevcut seslerinizi/ayarlarınızı korur.)*
3. Masaüstünde oluşan **Muallimun AI Ses Stüdyosu Pro** kısayoluyla stüdyoyu başlatın.

---

## 🧠 Desteklenen 3 Seslendirme Motoru Karşılaştırması

| Ses Motoru | Çalışma Ortamı | Hareke & Klonlama | En Uygun Kullanım Senaryosu |
| :--- | :--- | :--- | :--- |
| **1. ⭐ Spark-TTS (`IbrahimSalah/Arabic-TTS-Spark`)** | Yerel GPU / CPU (Çevrimdışı) | **Tam Harekeli Metin Zorunlu** • 24kHz Birebir Ses Klonlama | Harekeli ders kitapları, sözlük kelimeleri, gramer cümleleri, atasözleri ve 8 karakterli diyaloglar için **önerilen ana stüdyo motoru**. |
| **2. ⚡ Hızlı Direkt Neural TTS** | Çevrimiçi Servis (0 MB VRAM) | Harekeli ve Harekesiz Okur • Hazır Neural Ses Kullanır | Harekesiz metinler, hızlı ön-izleme ve harici ekran kartı olmayan bilgisayarlarda seri üretim. |
| **3. 🗣️ Coqui XTTS v2** | Yerel GPU / CPU (Çevrimdışı) | Alternatif / Deneysel Çok Dilli Klonlama | Alternatif ses rengi denemeleri (Arapça mahreç ve hareke sadakati Spark-TTS kadar yüksek değildir). |

---

## 🎭 8 Akustik Duygu ve Tonlama Profili

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

| Alan / Sütun Adı | Zorunlu mu? | Ne İşe Yarar ve Nasıl Çalışır? |
| :--- | :--- | :--- |
| **`arapca`** *(veya `metin`, `kelime`)* | ✅ **Zorunlu** | Seslendirilecek Arapça kelime, cümle veya paragraf metni. |
| **`ses_dosyasi`** *(veya `dosya_adi`, `filename`)* | İsteğe Bağlı | Tekil üretimde çıkacak ses dosyasının özel adı (Örn: `unite1_kelime05.mp3`). Belirtilmezse `id` kullanılır. |
| **`ses_erkek` / `ses_kadin`** | İsteğe Bağlı | Çift üretimde (`Erkek + Kadın`) erkek ve kadın ses dosyalarına verilecek özel dosya adları. |
| **`id`** *(veya `kod`, `sira`)* | Önerilir | Özel dosya adı belirtilmemişse ses dosyasının kaydedileceği benzersiz kimlik (Örn: `cumle_0001`). |
| **`ses_secimi`** *(veya `referans_ses`)* | İsteğe Bağlı | Satıra özel karakter seçimi: `otomatik`, `IKISI` (Çift üretim), `E1`, `E2`, `K1`, `K2`, `EC1`, `EC2`, `KC1`, `KC2`, `DIREKT`. |
| **`turkce`** *(veya `anlam`, `not`)* | İsteğe Bağlı | Tabloda bilgi ve arama kolaylığı sağlayan Türkçe anlam veya ders notu. |

---

## 🎚️ 5-Katmanlı 24kHz Stüdyo DSP Mastering ve 4 Boyutlu Akustik Kalite Kontrolü (QA)

Üretilen her ses dosyası diske kaydedilmeden önce şu 5 akustik katmandan ve 4 boyutlu konuşma sinyali doğrulamasından geçirilir:
1. **Saf Referans ve Doğal Nefes Koruması:** Özel referans seslerde doğal nefes aralıklarını (`420 ms -> 220 ms`, `22 ms` Raised-Cosine geçiş) koruyarak konuşmacı ritmini modele aktarır.
2. **18ms Onset Yumuşatma & Sıfır Fazlı Butterworth High-Pass Filtre (`80 Hz`):** Sesin doğal gövdesini koruyarak başlangıç darbelerini ve dip uğultularını temizler.
3. **Kenar Dolgulu (`mode="edge"`) Yumuşak RMS Gürültü Kapısı ve İlk Hece Kalkanı:** İlk 50 ms'de hiçbir ses kaybı yaşatmadan kelime aralarındaki boşluk tıslamalarını süzer; kısa ilk kelimeleri (`لَا، / نَعَمْ،`) ve son harf sükûnlarını korur.
4. **Anti-Aliasing Harmonik Sıcaklık (`%65 Dry + %35 Wet Tanh Drive` → `2. Derece Butterworth LPF` + DC Sıfırlama):** Peltek ve ıslıklı Arapça harflerin (`س، ص، ث، ش`) netliğini bozmadan dijital cızırtıları süzer.
5. **4 Boyutlu Konuşma Doğrulaması ve FFmpeg True-Peak Limiter (`-1.0 dBFS`):** Harmonik perde (`80–420 Hz`), spektral tıslama (`>5.5 kHz`), ZCR ve süre testlerinden geçemeyen cızırtılı sesler diske yazılmaz; sağlam sesler `150 ms` kosinüs eğrili sönümlenme ile kaydedilir.

---

## ⌨️ Pratik Klavye Kısayolları

| Kısayol | İşlev |
| :--- | :--- |
| **`Ctrl + Enter`** | Aktif Arapça metni hemen seslendir (1. Sekme) |
| **`Esc`** | Devam eden ses sentezini güvenli şekilde durdur |
| **`Ctrl + (+)` / `Ctrl + (-)`** | Arapça metin alanı yazı boyutunu büyüt / küçült (`➕ A+` / `➖ A-`) |
| **`F1`** | Kapsamlı Kullanım Kılavuzunu ve 5 Adımlı Başlangıç Turunu aç |

---

## 📄 Lisans, Telif Hakkı ve İletişim

**Muallimun AI Ses Stüdyosu Pro**, **Muallimun Dijital Eğitim Teknolojileri** tarafından öğretmenler, öğrenciler, akademisyenler ve içerik üreticileri için **Ücretsiz Eğitim Yazılımı (Freeware — Tüm Hakları Saklıdır / All Rights Reserved)** olarak sunulmaktadır.

* **Üretilen Seslerin Kullanım Hakkı:** Kullanıcıların bu yazılımla ürettikleri ses dosyaları (`.wav` / `.mp3`) üzerinde tüm eğitim ve yayın hakları kendilerine aittir.
* **Telif Koruması:** Geliştiricinin yazılı izni olmaksızın yazılımın kaynak kodlarının, DSP/fonetik algoritmalarının veya arayüz tasarımının kopyalanması, tersine mühendislik (decompile) işlemine tabi tutulması, farklı bir isim/marka altında yeniden dağıtılması veya ticari olarak satılması kesinlikle yasaktır.
* **Üçüncü Taraf Bileşenler:** Çalışma zamanında kullanılan yapay zeka ses modelleri (`IbrahimSalah/Arabic-TTS-Spark`, `Coqui XTTS v2`, `Edge-TTS`) kendi orijinal lisanslarına tabidir; ayrıntılar için [LICENSE](LICENSE) dosyasına bakınız.

- **Geliştirici:** Muallimun Dijital Eğitim Teknolojileri — [www.muallimun.com](https://www.muallimun.com)
- **Web Kılavuz ve İndirme Sayfası:** [muallimun.com/muallimun_ses_studyosu](https://www.muallimun.com/muallimun_ses_studyosu/)
- **GitHub İndirme ve Güncelleme Merkezi:** [github.com/muallimun/Muallimun_Ses_Asistani](https://github.com/muallimun/Muallimun_Ses_Asistani)