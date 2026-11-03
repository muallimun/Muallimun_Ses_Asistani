# 🛡️ Güvenlik Politikası ve Mimari Güvenceler (Security Policy)

**Muallimun AI Ses Stüdyosu Pro**, eğitimcilerin ve içerik üreticilerinin yerel bilgisayarlarında güvenle çalışacak şekilde tasarlanmıştır.

## 📦 Desteklenen Sürümler

| Sürüm | Güvenlik Desteği | Açıklama |
| :--- | :--- | :--- |
| **v1.2.x** | ✅ Aktif Destek | İçerik-adresli Checkpoint v2, Path Guard ve güvenli QThread mimarisi |
| **< v1.2.0** | ❌ Desteklenmiyor | Lütfen v1.2.0 veya üzeri sürüme güncelleyin |

---

## 🔒 Uygulanan Güvenlik ve Veri Bütünlüğü Standartları

v1.2.0 sürümü itibarıyla uygulamada aşağıdaki güvenlik katmanları standart olarak uygulanmaktadır:

1. **Çıktı Klasörü Hapsetme Koruması (Path Traversal Guard):**
   * Dışarıdan içe aktarılan Excel (`.xlsx`), CSV, JSON ve TXT dosyalarındaki `id`, `grup_id` ve dosya yolu alanları `guvenli_kimlik_temizle()` ve `guvenli_hedef_yol_cozumle()` fonksiyonlarından geçirilir.
   * `../`, mutlak sürücü yolları, UNC yolları veya Windows ayrılmış cihaz adları (`CON`, `PRN`, `AUX` vb.) engellenir; hiçbir çıktı dosyası belirlenen hedef kök klasörün dışına yazılamaz.

2. **Güvenli Model Yükleme ve Ortam İzolasyonu:**
   * Uygulama başlangıcında (`main.py`) kullanıcının haberi olmadan paket silen veya ortamı değiştiren otomatik `pip uninstall / install` işlemleri yapılmaz.
   * Global `torch.load` davranışı bozulmaz; model ağırlıkları yalnızca doğrulanan yerel model yükleme adımında dar kapsamda çağrılır.
   * Uygulama içerisinde düz metin (plaintext) bulut API anahtarı tutulmaz.

3. **Atomik Yapılandırma ve Veritabanı Koruması:**
   * Kullanıcı ayarları (`user_settings.json`) ve referans ses havuzu (`voice_pool.json`), elektrik kesintisi veya ani kapanmalarda veri kaybı yaşanmaması için `.tmp` + `os.fsync()` + `.bak` yedekli atomik yazım yöntemiyle kaydedilir.
   * Toplu seslendirme geçmişi (`studyo_checkpoints.db`), eşzamanlı erişim kilitlenmelerine karşı SQLite `WAL (Write-Ahead Logging)` modunda ve parametreli sorgularla (SQL Injection korumalı) çalışır.

4. **Gizlilik ve Çevrimdışı (Offline) Çalışma:**
   * **Spark-TTS (`SPARK_ARABIC`)** ve **Coqui XTTS v2 (`XTTS_STUDIO`)** modelleri indirildikten sonra tamamen yerel ekran kartı (GPU) veya işlemci (CPU) üzerinde çalışır; metinleriniz veya referans sesleriniz hiçbir harici sunucuya gönderilmez.
   * Yalnızca **Hızlı Direkt TTS (`FAST_DIRECT_TTS`)** modu seçildiğinde metinler çevrimiçi ses sentezi için Microsoft Edge TTS servisine iletilir.

---

## 🚨 Güvenlik Açığı Bildirimi (Reporting a Vulnerability)

Uygulamada bir güvenlik açığı veya dosya bütünlüğü sorunu tespit ederseniz:

1. Lütfen GitHub deponuzdaki **[Security Advisories](https://github.com/muallimun/Muallimun_Ses_Asistani/security/advisories)** sekmesi üzerinden veya doğrudan **[Issues](https://github.com/muallimun/Muallimun_Ses_Asistani/issues)** bölümünden bildirim oluşturun.
2. Bildiriminizde işletim sistemi sürümünüzü, Python/PyTorch sürümünüzü ve hatayı yeniden üretme adımlarını paylaşın.