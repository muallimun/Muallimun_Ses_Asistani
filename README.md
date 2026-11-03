# 🎙️ Muallimun AI Ses Stüdyosu Pro (v1.2.0)

**Fasih Arapça Vakıf/Vasıl Ön-İşleme • 24kHz Neural Ses Klonlama • 5-Katmanlı Stüdyo DSP Mastering**

**Muallimun AI Ses Stüdyosu Pro**, Arapça ders kitapları, dijital sözlükler, etkileşimli eğitim materyalleri ve e-öğrenme portalları ([muallimun.net](https://muallimun.net)) için geliştirilmiş açık kaynaklı, masaüstü yapay zeka seslendirme ve dublaj stüdyosudur.

---

## ✨ Temel Özellikler

* **⭐ 24kHz Neural Ses Klonlama (`Spark-TTS`):** `IbrahimSalah/Arabic-TTS-Spark` (BiCodec) mimarisiyle 8 hazır stüdyo karakterini (Yetişkin Erkek/Kadın, Çocuk Erkek/Kız) veya kendi eklediğiniz referans sesi birebir klonlayarak çevrimdışı (offline) ses üretir.
* **⚡ Hızlı Direkt Neural TTS:** Ekran kartı (VRAM) gerektirmeden çevrimiçi hazır Arapça neural seslerle hızlı ön-izleme ve seri üretim yapar.
* **🕌 Fasih Arapça Vakıf & Vasıl Motoru:**
  * Cümle ve durak sonlarındaki *tâ-i merbûtayı* (`مَدْرَسَةٌ -> مَدْرَسَهْ`), *fetha tenvini* (`كِتَابًا -> كِتَابَا`) ve son hareke sükûnunu otomatik uygular.
  * Uzun paragrafları bölerken *harf-i cer* ve bölünmez Arapça edatların (`فِي، مِنْ، إِلَى، عَلَى، أَنْ، لَا`) satır sonunda tek başına kalmasını engeller.
* **📦 Toplu Seslendirme & Seçmeli Kuyruk:** Excel (`.xlsx`), JSON, CSV ve TXT listelerini içe aktarır. İster tüm listeyi, ister arama ve satır aralığı (`1 - 50`) seçimiyle yalnızca belirlediğiniz satırları seslendirir.
* **⏭️ İçerik-Adresli Checkpoint v2 (SQLite WAL):** Yarıda kalan toplu işlemlerde metin, ses karakteri ve motor parmak izini doğrulayarak mevcut sağlam dosyaları atlar, kaldığı yerden devam eder.
* **🎭 Çoklu Rol Diyalog Stüdyosu:** Diyalog JSON dosyalarındaki konuşmacılara cinsiyet ve rollerine göre 8 sesten çakışmasız rol dağıtır; seçilen veya tüm diyalogları ayrı klasörlerde hem satır satır hem de birleştirilmiş `diyalog_tamami.mp3` olarak üretir.
* **🎚️ 5-Katmanlı Stüdyo DSP & Teknik QA:** DC Offset temizliği, Butterworth 80Hz–11.2kHz filtre, yumuşak RMS gürültü kapısı, algısal ses yüksekliği (Loudness) dengeleme, FFmpeg True-Peak Limiter ve dalga formu üzerinde gerçek RMS/dBFS kalite kontrolü sunar.
* **☀️/🌙 Aydınlık & Karanlık Stüdyo Teması:** Göz konforuna uygun Gece Mavisi Koyu Stüdyo ve Aydınlık Kitap Kağıdı temaları arasında tek tıkla geçiş.

---

## 🚀 Kurulum ve Çalıştırma (Python 3.12)

### 1. Depoyu İndirin
```powershell
git clone [https://github.com/muallimun/Muallimun_Ses_Asistani.git](https://github.com/muallimun/Muallimun_Ses_Asistani.git)
cd Muallimun_Ses_Asistani