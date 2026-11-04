#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MUALLİMUN AI SES STÜDYOSU PRO - ANA PENCERE VE STÜDYO YÖNETİM MERKEZİ (ui/main_window.py)
Özellikler:
  1. Yalnızca Arapça Metin Alanını Etkileyen QSS Destekli Yazı Boyutu (A+ / A-) Kontrolü (Yeşil Kutuyu Genişletmez)
  2. Özel Referans Ses Eklemede Sahte REF_METIN_1 Atamasını Önleyen Saf Akustik Klonlama Desteği
  3. Oturum Boyunca Hareke Uyarısını Susturma ('☐ Bu oturum boyunca bir daha gösterme') Desteği
  4. Kompakt Üst Bar (Tema, Kılavuz ve Güncelleme İçin İkon Butonlar — Metin Kırpılması Önlenmiş)
  5. 3. Sekmedeki 18+ İnce Ayarın Yanında Tıklanabilir 'ℹ️' Bilgi İkonları ve 1./3./4./5. Sekme Tam Senkronizasyonu
"""

import io
import os
import re
import sys
import uuid
import math
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import numpy as np
import soundfile as sf

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QUrl
from PySide6.QtGui import (
    QFont,
    QColor,
    QPainter,
    QPen,
    QDesktopServices,
    QCloseEvent,
    QKeySequence,
    QShortcut,
    QGuiApplication,
)
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QCheckBox,
    QTextEdit,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QTabWidget,
    QGroupBox,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QProgressBar,
    QMessageBox,
    QFrame,
    QSplitter,
    QRadioButton,
    QButtonGroup,
)

from core.config_manager import ConfigManager, PROJECT_ROOT
from core.studyo_motoru import (
    MuallimunStudyoSesMotoru,
    CancelToken,
    DONANIM_PROFILLERI,
    REF_CACHE_DIR,
    REF_METIN_1,
    arapca_akustik_metin_hazirla,
    gpu_vram_durumu_getir,
    gpu_bellegini_optimize_et,
    referans_sesi_on_temizle,
    _ses_dosyasini_guvenli_oku_np,
)
from core.batch_worker import (
    DUYGU_TONU_PROFILLERI,
    duygu_ve_tonlama_hesapla,
    duygu_ve_tonlama_detayli_hesapla,
    guvenli_kimlik_temizle,
    guvenli_hedef_yol_cozumle,
)
from ui.setup_wizard import SetupWizardDialog
from ui.studyo_sekmeler_b import TopluSeslendirmeSekmesi, DiyalogUzunMetinSekmesi
from ui.rehber_ve_guncelleyici import (
    APP_VERSION,
    VARSAYILAN_GITHUB_REPO,
    studyo_tema_qss_olustur,
    arapca_hareke_analizi_yap,
    ArapcaHarekelemeMotoru,
    HarekeUyariVeOnayDialog,
    oturumda_hareke_uyarisi_aktif_mi,
    oturum_arapca_font_boyutu_getir,
    oturum_arapca_font_boyutu_ayarla,
    profesyonel_arapca_font_ailesi_bul,
    profesyonel_arapca_font_olustur,
    DSP_VE_PRESET_PARAMETRE_REHBERI,
    ParametreBilgiDialog,
    BaslangicTuruDialog,
    KullanimKilavuzuDialog,
    GuncellemeKontrolDialog,
    GitHubGuncellemeKontrolWorker,
)


def _kompakt_kutu_ayarla(cmb: QComboBox, min_genislik: int = 120) -> None:
    cmb.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    cmb.setMinimumContentsLength(10)
    cmb.setMinimumWidth(min_genislik)


# ==============================================================================
# 1. ÇAKIŞMASIZ STÜDYO SES OYNATICI (WAV & MP3 DESTEKLİ, DOSYA KİLİDİ KORUMALI)
# ==============================================================================
class GarantiliStudyoSesOynatici:
    def __init__(self) -> None:
        self.aktif_dosya: str = ""
        self._son_gecici_wav: Optional[Path] = None

    def cal(self, dosya_yolu: str) -> Tuple[bool, str]:
        if not dosya_yolu or not os.path.exists(dosya_yolu):
            return False, "Ses dosyası bulunamadı."

        self.durdur()
        try:
            REF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            gecici_wav = REF_CACHE_DIR / f"_play_{uuid.uuid4().hex[:8]}.wav"

            veri = _ses_dosyasini_guvenli_oku_np(dosya_yolu, hedef_sr=24000)
            if veri.size < 100:
                return False, "Ses dosyası boş."
            sf.write(str(gecici_wav), veri, 24000, subtype="PCM_16")
            self._son_gecici_wav = gecici_wav
            self.aktif_dosya = dosya_yolu

            if sys.platform == "win32":
                import winsound
                winsound.PlaySound(str(gecici_wav), winsound.SND_FILENAME | winsound.SND_ASYNC)
                return True, f"🔊 Çalınıyor: {os.path.basename(dosya_yolu)}"
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(dosya_yolu).resolve())))
                return True, f"🔊 Açıldı: {os.path.basename(dosya_yolu)}"
        except Exception as e:
            return False, f"Oynatma hatası: {e}"

    def durdur(self) -> None:
        if sys.platform == "win32":
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
        if self._son_gecici_wav and self._son_gecici_wav.exists():
            try:
                self._son_gecici_wav.unlink()
            except OSError:
                pass
        self._son_gecici_wav = None
        self.aktif_dosya = ""


# ==============================================================================
# 2. GERÇEK TEKNİK SES KONTROLÜ (QA) VE 24kHz DALGA FORMU GÖSTERGESİ
# ==============================================================================
class StudyoWaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(88)
        self.setMaximumHeight(115)
        self.ornekler: Optional[np.ndarray] = None
        self.dosya_adi: str = ""
        self.qa_metni: str = "Ses üretildiğinde veya dinlendiğinde dalga formu ve teknik sinyal raporu burada görünür"
        self.qa_durum: str = "beklemede"
        self.koyu_tema: bool = True
        self.setToolTip(
            "24kHz Stüdyo Dalga Formu ve Otomatik Teknik Kalite Kontrolü (QA):\n"
            "• Süre (sn), ortalama ses enerjisi (RMS dBFS) ve tepe seviyesini (Peak dBFS) ölçer.\n"
            "• Sessiz, aşırı kısık veya kırpılmış (clipped) kayıtları otomatik uyarır."
        )

    def tema_ayarla(self, koyu_mu: bool) -> None:
        self.koyu_tema = koyu_mu
        self.update()

    def temizle(self) -> None:
        self.ornekler = None
        self.dosya_adi = ""
        self.qa_metni = "Ses üretildiğinde veya dinlendiğinde dalga formu burada görünür"
        self.qa_durum = "beklemede"
        self.update()

    def ses_dosyasini_yukle(self, dosya_yolu: str, kelime_sayisi: int = 1) -> bool:
        if not dosya_yolu or not os.path.exists(dosya_yolu):
            self.temizle()
            return False
        try:
            veri = _ses_dosyasini_guvenli_oku_np(dosya_yolu, hedef_sr=24000)
            sr = 24000
            if veri.size < 200 or not np.all(np.isfinite(veri)):
                self.ornekler = None
                self.qa_durum = "uyari"
                self.qa_metni = "❌ Teknik Ses Uyarısı: Geçersiz veya bozuk ses verisi"
                self.update()
                return False

            sure_sn = float(veri.size) / float(sr)
            tepe = float(np.max(np.abs(veri)))
            rms = float(np.sqrt(np.mean(veri ** 2) + 1e-12))

            tepe_db = 20.0 * math.log10(max(1e-6, tepe))
            rms_db = 20.0 * math.log10(max(1e-6, rms))
            k_sayisi = max(1, int(kelime_sayisi))

            dilim_sayisi = 140
            adim = max(1, veri.size // dilim_sayisi)
            dilimler = [
                float(np.max(np.abs(veri[i : i + adim])))
                for i in range(0, min(veri.size, dilim_sayisi * adim), adim)
            ]
            self.ornekler = np.asarray(dilimler, dtype=np.float32)
            self.dosya_adi = os.path.basename(dosya_yolu)

            uyarilar = []
            if rms_db < -44.0 or tepe_db < -30.0:
                uyarilar.append("Çok kısık / sessiz sinyal")
            if sure_sn < 0.16 or (k_sayisi > 1 and (sure_sn / float(k_sayisi)) < 0.09):
                uyarilar.append("Süre çok kısa")
            if tepe > 0.995:
                uyarilar.append("Tepe kırpılması (Clipping)")

            if not uyarilar:
                self.qa_durum = "uygun"
                self.qa_metni = (
                    f"✅ Teknik Ses Kontrolü: Uygun  |  Süre: {sure_sn:.2f} sn  |  "
                    f"RMS: {rms_db:.1f} dBFS  |  Tepe: {tepe_db:.1f} dBFS  |  24000 Hz"
                )
            else:
                self.qa_durum = "uyari"
                self.qa_metni = (
                    f"⚠️ Teknik Ses Uyarısı ({', '.join(uyarilar)})  |  Süre: {sure_sn:.2f} sn  |  "
                    f"RMS: {rms_db:.1f} dBFS  |  Tepe: {tepe_db:.1f} dBFS"
                )

            self.update()
            return self.qa_durum == "uygun"
        except Exception as e:
            self.ornekler = None
            self.qa_durum = "uyari"
            self.qa_metni = f"⚠️ Ses analiz hatası: {e}"
            self.update()
            return False

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        bg = QColor("#060911") if self.koyu_tema else QColor("#f8fafc")
        border = QColor("#1e293b") if self.koyu_tema else QColor("#cbd5e1")
        painter.fillRect(0, 0, w, h, bg)
        painter.setPen(QPen(border, 1))
        painter.drawRoundedRect(1, 1, w - 2, h - 2, 6, 6)

        orta_y = int(h * 0.48)
        cizgi_renk = QColor("#1e293b") if self.koyu_tema else QColor("#cbd5e1")
        painter.setPen(QPen(cizgi_renk, 1, Qt.DashLine))
        painter.drawLine(10, orta_y, w - 10, orta_y)

        if self.ornekler is not None and self.ornekler.size > 0:
            if self.dosya_adi:
                painter.setPen(QColor("#38bdf8") if self.koyu_tema else QColor("#0284c7"))
                painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
                painter.drawText(12, 16, f"🎵 {self.dosya_adi}")

            n = len(self.ornekler)
            kullanilabilir_w = max(50, w - 24)
            adim_x = kullanilabilir_w / float(max(1, n))
            cubuk_w = max(2.0, adim_x * 0.65)
            maks_yukseklik = (h * 0.52) * 0.5

            dalga_renk = (
                (QColor("#10b981") if self.koyu_tema else QColor("#059669"))
                if self.qa_durum == "uygun"
                else QColor("#f59e0b")
            )
            painter.setPen(Qt.NoPen)
            painter.setBrush(dalga_renk)

            for i, val in enumerate(self.ornekler):
                x = 12 + i * adim_x
                oran = max(0.03, min(1.0, float(val)))
                ari_yuk = max(2.0, oran * maks_yukseklik * 2.0)
                painter.drawRoundedRect(int(x), int(orta_y - ari_yuk / 2), int(cubuk_w), int(ari_yuk), 1, 1)

        if self.qa_durum == "uygun":
            metin_renk = QColor("#10b981") if self.koyu_tema else QColor("#047857")
        elif self.qa_durum == "uyari":
            metin_renk = QColor("#f59e0b") if self.koyu_tema else QColor("#b45309")
        else:
            metin_renk = QColor("#64748b")

        painter.setPen(metin_renk)
        painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
        painter.drawText(12, h - 8, self.qa_metni)


# ==============================================================================
# 3. GPU OPTİMİZASYON VE 4 KADEMELİ DONANIM SEÇİM PENCERESİ
# ==============================================================================
class GpuKademeSecimDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, studyo_motor: Optional[MuallimunStudyoSesMotoru], parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.studyo_motor = studyo_motor
        self.setWindowTitle("⚡ GPU Bellek Optimizasyonu ve Donanım Kademesi Seçimi")
        self.setMinimumSize(680, 440)
        self.resize(720, 470)

        tema = self.config_manager.user_settings.get("tema_modu", "koyu")
        self.setStyleSheet(studyo_tema_qss_olustur(tema))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        bilgi = gpu_vram_durumu_getir()
        lbl_ust = QLabel(
            f"<b>Aktif Donanım:</b> {bilgi['cihaz_adi']}<br>"
            f"<b>Bellek Durumu:</b> Model Kullanımı: {bilgi['kullanilan_gb']} GB  |  "
            f"Gerçek Boş VRAM: <b>{bilgi.get('bos_gb', 0)} GB</b> / Toplam: {bilgi['toplam_gb']} GB"
        )
        lbl_ust.setStyleSheet("font-size: 10pt; color: #10b981;")
        layout.addWidget(lbl_ust)

        aciklama = QLabel(
            "💡 <b>Donanım Çalışma Kademesi:</b> 'Otomatik' seçeneği ekran kartınızın boş VRAM kapasitesine göre "
            "en uygun kademeyi seçer. Dilerseniz aşağıdaki 4 kademeden birini zorunlu olarak sabitleyebilirsiniz:"
        )
        aciklama.setWordWrap(True)
        layout.addWidget(aciklama)

        self.radio_grup = QButtonGroup(self)
        mevcut_secim = self.config_manager.user_settings.get("zorunlu_donanim_kademesi", "OTOMATIK")

        secenekler = [
            (
                "OTOMATIK",
                f"✨ Otomatik (Önerilen: {bilgi['profil_detay']['ad']})",
                "Ekran kartınızın boş VRAM miktarına göre cümle bölme ve bellek korumasını otomatik yönetir.",
            )
        ]
        for kod, p in DONANIM_PROFILLERI.items():
            secenekler.append((kod, p["ad"], p["aciklama"]))

        for idx, (kod, baslik, detay) in enumerate(secenekler):
            kutu = QFrame()
            kutu.setStyleSheet("QFrame { border: 1px solid #334155; border-radius: 6px; padding: 4px; }")
            kv = QVBoxLayout(kutu)
            kv.setContentsMargins(8, 4, 8, 4)
            kv.setSpacing(2)

            rb = QRadioButton(baslik)
            rb.setProperty("kademe_kodu", kod)
            rb.setStyleSheet("font-weight: bold;")
            if kod == mevcut_secim:
                rb.setChecked(True)
            self.radio_grup.addButton(rb, idx)
            kv.addWidget(rb)

            lbl_d = QLabel(f"   ℹ️ {detay}")
            lbl_d.setWordWrap(True)
            lbl_d.setStyleSheet("font-size: 8.5pt; color: #94a3b8;")
            kv.addWidget(lbl_d)
            layout.addWidget(kutu)

        layout.addStretch()

        alt = QHBoxLayout()
        btn_pasif_bosalt = QPushButton("🧹 VRAM Önbelleğini Şimdi Temizle")
        btn_pasif_bosalt.setStyleSheet("background-color: #0284c7; color: white; padding: 6px 12px;")
        btn_pasif_bosalt.clicked.connect(self._vram_simdi_temizle)
        alt.addWidget(btn_pasif_bosalt)
        alt.addStretch()

        btn_kaydet = QPushButton("✅ Seçimi Uygula ve Optimize Et")
        btn_kaydet.setStyleSheet("background-color: #059669; color: white; padding: 6px 16px; font-weight: bold;")
        btn_kaydet.clicked.connect(self._uygula_ve_kapat)
        alt.addWidget(btn_kaydet)

        btn_iptal = QPushButton("İptal")
        btn_iptal.clicked.connect(self.reject)
        alt.addWidget(btn_iptal)
        layout.addLayout(alt)

    def _vram_simdi_temizle(self) -> None:
        if self.studyo_motor is not None:
            self.studyo_motor.bosalt(sadece_pasif_modelleri=True)
        gpu_bellegini_optimize_et(self.studyo_motor)
        QMessageBox.information(self, "Bellek Temizlendi", "GPU CUDA önbelleği ve pasif modeller başarıyla temizlendi.")

    def _uygula_ve_kapat(self) -> None:
        secili_btn = self.radio_grup.checkedButton()
        secilen_kod = secili_btn.property("kademe_kodu") if secili_btn else "OTOMATIK"
        self.config_manager.user_settings["zorunlu_donanim_kademesi"] = secilen_kod
        self.config_manager.save_user_settings()

        gpu_bellegini_optimize_et(
            studyo_motor=self.studyo_motor,
            zorunlu_kademe_kodu=None if secilen_kod == "OTOMATIK" else secilen_kod,
        )
        self.accept()


# ==============================================================================
# 4. DETAYLI ÖZEL REFERANS SES EKLEME PENCERESİ
# (Sahte REF_METIN_1 Ataması Kaldırıldı — Boş Bırakılırsa Saf Akustik Klonlama Çalışır)
# ==============================================================================
class OzelReferansSesEkleDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, ses_oynatici: GarantiliStudyoSesOynatici, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.ses_oynatici = ses_oynatici
        self.eklenen_kayit: Optional[Dict[str, Any]] = None

        self.setWindowTitle("➕ Yeni Özel Referans Ses Karakteri Ekle (24kHz Stüdyo Klonlama)")
        self.setMinimumSize(660, 440)
        self.resize(700, 470)

        tema = self.config_manager.user_settings.get("tema_modu", "koyu")
        self.setStyleSheet(studyo_tema_qss_olustur(tema))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        aciklama = QLabel(
            "💡 <b>Referans Ses Ekleme Rehberi:</b> 4–10 saniye uzunluğunda, arka plan müziği ve yankısı olmayan "
            "net bir konuşma kaydı seçin. Dosya içindeki uzun sessizlikler otomatik sıkıştırılacak ve "
            "<b>24kHz Mono PCM_16 WAV</b> standardına dönüştürülecektir."
        )
        aciklama.setWordWrap(True)
        layout.addWidget(aciklama)

        dosya_bar = QHBoxLayout()
        dosya_bar.addWidget(QLabel("Ses Dosyası:"))
        self.edt_dosya_yolu = QLineEdit()
        self.edt_dosya_yolu.setPlaceholderText("Bilgisayarınızdan .wav, .mp3, .flac veya .ogg dosyası seçin...")
        dosya_bar.addWidget(self.edt_dosya_yolu, stretch=1)

        btn_gozat = QPushButton("📂 Gözat...")
        btn_gozat.setStyleSheet("background-color: #0284c7; color: white;")
        btn_gozat.clicked.connect(self._dosya_sec)
        dosya_bar.addWidget(btn_gozat)

        btn_dinle = QPushButton("🔊 Dinle")
        btn_dinle.clicked.connect(self._secili_dosyayi_dinle)
        dosya_bar.addWidget(btn_dinle)
        layout.addLayout(dosya_bar)

        form_grid = QGridLayout()
        form_grid.setSpacing(8)

        form_grid.addWidget(QLabel("Karakter Görünür Adı:"), 0, 0)
        self.edt_karakter_adi = QLineEdit()
        self.edt_karakter_adi.setPlaceholderText("Örn: Özel Ses (İrem Kız Çocuk)")
        form_grid.addWidget(self.edt_karakter_adi, 0, 1)

        form_grid.addWidget(QLabel("Cinsiyet:"), 1, 0)
        self.cmb_cinsiyet = QComboBox()
        self.cmb_cinsiyet.addItem("👨 Erkek (E)", "E")
        self.cmb_cinsiyet.addItem("👩 Kadın (K)", "K")
        self.cmb_cinsiyet.currentIndexChanged.connect(self._cinsiyet_degisti)
        form_grid.addWidget(self.cmb_cinsiyet, 1, 1)

        form_grid.addWidget(QLabel("Rol Kategorisi:"), 2, 0)
        self.cmb_kategori = QComboBox()
        self.cmb_kategori.addItem("Yetişkin Erkek (yetiskin_E)", "yetiskin_E")
        self.cmb_kategori.addItem("Erkek Çocuk / Genç (cocuk_E)", "cocuk_E")
        self.cmb_kategori.addItem("Yetişkin Kadın (yetiskin_K)", "yetiskin_K")
        self.cmb_kategori.addItem("Kız Çocuk / Genç (cocuk_K)", "cocuk_K")
        form_grid.addWidget(self.cmb_kategori, 2, 1)
        layout.addLayout(form_grid)

        layout.addWidget(
            QLabel(
                "📜 <b>Referans Seste Okunan Arapça Metin (İsteğe Bağlı — Boş Bırakılırsa Saf Akustik Klonlama Yapılır):</b>"
            )
        )
        self.txt_ref_metin = QTextEdit()
        self.txt_ref_metin.setLayoutDirection(Qt.RightToLeft)
        aile = profesyonel_arapca_font_ailesi_bul()
        self.txt_ref_metin.setFont(profesyonel_arapca_font_olustur(18))
        self.txt_ref_metin.setStyleSheet(f"QTextEdit {{ font-family: '{aile}'; font-size: 18pt; }}")
        self.txt_ref_metin.setPlaceholderText(
            "İsteğe bağlı: Yüklediğiniz ses dosyasında okunan Arapça metni buraya yazabilirsiniz. "
            "Emin değilseniz BOŞ BIRAKIN; boş bırakıldığında motor yalnızca ses rengini klonlar."
        )
        layout.addWidget(self.txt_ref_metin, stretch=1)

        alt = QHBoxLayout()
        alt.addStretch()
        btn_ekle = QPushButton("➕ 24kHz WAV'a Dönüştür ve Havuza Ekle")
        btn_ekle.setStyleSheet("background-color: #059669; color: white; padding: 7px 16px; font-weight: bold;")
        btn_ekle.clicked.connect(self._onayla_ve_ekle)
        alt.addWidget(btn_ekle)

        btn_iptal = QPushButton("İptal")
        btn_iptal.clicked.connect(self.reject)
        alt.addWidget(btn_iptal)
        layout.addLayout(alt)

    def _cinsiyet_degisti(self) -> None:
        cins = self.cmb_cinsiyet.currentData() or "E"
        hedef_kat = "yetiskin_K" if cins == "K" else "yetiskin_E"
        idx = self.cmb_kategori.findData(hedef_kat)
        if idx >= 0:
            self.cmb_kategori.setCurrentIndex(idx)

    def _dosya_sec(self) -> None:
        dosya, _ = QFileDialog.getOpenFileName(
            self,
            "Referans Ses Dosyası Seç",
            str(Path.home() / "Desktop"),
            "Ses Dosyaları (*.wav *.mp3 *.flac *.ogg)",
        )
        if dosya:
            self.edt_dosya_yolu.setText(dosya)
            stem_kucuk = Path(dosya).stem.lower()
            if not self.edt_karakter_adi.text().strip():
                self.edt_karakter_adi.setText(f"Özel Ses ({Path(dosya).stem[:20]})")
            if any(k in stem_kucuk for k in ("kiz", "kız", "kadin", "kadın", "female", "irem", "zeynep", "leyla")):
                self.cmb_cinsiyet.setCurrentIndex(1)
                if "kiz" in stem_kucuk or "kız" in stem_kucuk or "cocuk" in stem_kucuk:
                    idx_k = self.cmb_kategori.findData("cocuk_K")
                    if idx_k >= 0:
                        self.cmb_kategori.setCurrentIndex(idx_k)

    def _secili_dosyayi_dinle(self) -> None:
        yol = self.edt_dosya_yolu.text().strip()
        if yol and os.path.exists(yol):
            self.ses_oynatici.cal(yol)
        else:
            QMessageBox.warning(self, "Dosya Yok", "Lütfen önce geçerli bir ses dosyası seçin.")

    def _onayla_ve_ekle(self) -> None:
        yol = self.edt_dosya_yolu.text().strip()
        if not yol or not os.path.exists(yol):
            QMessageBox.warning(self, "Dosya Seçilmedi", "Lütfen eklenecek referans ses dosyasını seçin.")
            return
        ad = self.edt_karakter_adi.text().strip() or f"Özel Ses ({Path(yol).stem[:18]})"
        cins = self.cmb_cinsiyet.currentData() or "E"
        kat = self.cmb_kategori.currentData() or f"yetiskin_{cins}"
        ref_metin = self.txt_ref_metin.toPlainText().strip()

        try:
            self.eklenen_kayit = self.config_manager.add_custom_voice(
                kaynak_dosya_yolu=yol,
                gorunen_ad=ad,
                cinsiyet=cins,
                kategori=kat,
                ref_metin=ref_metin,
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ses Ekleme Hatası", str(e))


# ==============================================================================
# 5. TEKLİ STÜDYO ARKA PLAN SENTEZ İŞÇİSİ (8 TONLAMA PROFİLİ & UZMAN MOD TAM SENKRON)
# ==============================================================================
class TekliSentezWorker(QThread):
    ilerleme_sinyali = Signal(int, str)
    log_sinyali = Signal(str)
    tamamlandi_sinyali = Signal(bool, str, str, str)

    def __init__(
        self,
        ana_pencere: "MuallimunStudyoMainWindow",
        arapca_metin: str,
        akustik_metin: str,
        mod_kodu: str,
        duygu_kodu: str,
        secilen_motor_tipi: str,
        referans_kullan: bool,
        cift_uretim: bool,
        tek_ref_id: str,
        erkek_ref_id: str,
        kadin_ref_id: str,
        dosya_adi_temel: str,
        uzanti: str,
        ozel_hiz: Optional[float] = None,
        ozel_temp: Optional[float] = None,
    ):
        super().__init__()
        self.ana_pencere = ana_pencere
        self.arapca_metin = arapca_metin
        self.akustik_metin = akustik_metin
        self.mod_kodu = mod_kodu
        self.duygu_kodu = duygu_kodu
        self.secilen_motor_tipi = secilen_motor_tipi
        self.referans_kullan = referans_kullan
        self.cift_uretim = cift_uretim
        self.tek_ref_id = tek_ref_id
        self.erkek_ref_id = erkek_ref_id
        self.kadin_ref_id = kadin_ref_id
        self.dosya_adi_temel = guvenli_kimlik_temizle(dosya_adi_temel, varsayilan="studyo_kayit_001")
        self.uzanti = ".wav" if uzanti.lower() == "wav" else ".mp3"
        self.ozel_hiz = ozel_hiz
        self.ozel_temp = ozel_temp
        self.cancel_token = CancelToken()

    def durdur(self) -> None:
        self.cancel_token.cancel()
        if self.ana_pencere.studyo_motor is not None:
            self.ana_pencere.studyo_motor.durdur()

    def run(self) -> None:
        try:
            self.ilerleme_sinyali.emit(4, "⏳ Ses motoru hazırlanıyor...")
            motor = self.ana_pencere.motoru_getir_veya_yukle(
                log_fn=self.log_sinyali.emit,
                zorunlu_motor_tipi=self.secilen_motor_tipi,
            )
            motor.durdur_istegi = False

            cfg = self.ana_pencere.config_manager
            preset = cfg.get_preset(self.mod_kodu)
            kelime_turu = str(preset.get("kelime_turu", "genel"))
            tek_kelime_mi = bool(preset.get("tek_kelime_mi", self.mod_kodu == "tek_kelime")) or (self.duygu_kodu == "tek_kelime_sozluk")
            min_tok_ovr = preset.get("min_tokens")
            max_tok_ovr = preset.get("max_tokens")

            ton_detay = duygu_ve_tonlama_detayli_hesapla(self.arapca_metin, preset, self.duygu_kodu)
            hiz = round(float(self.ozel_hiz), 2) if self.ozel_hiz is not None else ton_detay["hiz"]
            temp = round(float(self.ozel_temp), 2) if self.ozel_temp is not None else ton_detay["temp"]
            top_p = ton_detay["top_p"]
            top_k = ton_detay["top_k"]
            dsp_ayar = ton_detay["dsp"]
            hikmetli = ton_detay["hikmetli_durak"]
            algilanan_kip = ton_detay["algilanan_kip"]

            self.log_sinyali.emit(
                f"🎭 Tonlama: {algilanan_kip} (Hız: {hiz}x | Temp: {temp} | Top-P: {top_p} | Top-K: {top_k})"
            )

            ana_cikti = cfg.get_default_output_dir() / "tekli_studyo"
            ana_cikti.mkdir(parents=True, exist_ok=True)
            etkin_ref_kullan = self.referans_kullan and (self.secilen_motor_tipi != "FAST_DIRECT_TTS")

            if self.cift_uretim:
                erkek_hedef = guvenli_hedef_yol_cozumle(ana_cikti, f"erkek/{self.dosya_adi_temel}{self.uzanti}")
                kadin_hedef = guvenli_hedef_yol_cozumle(ana_cikti, f"kadin/{self.dosya_adi_temel}{self.uzanti}")
                erkek_hedef.parent.mkdir(parents=True, exist_ok=True)
                kadin_hedef.parent.mkdir(parents=True, exist_ok=True)

                e_yol = str(cfg.resolve_voice_path(self.erkek_ref_id))
                e_metin = cfg.get_voice_prompt_text(self.erkek_ref_id)

                ok_e = motor.uret_ve_kaydet(
                    arapca_metin=self.arapca_metin,
                    ref_wav_yolu=e_yol,
                    cikti_yolu=erkek_hedef,
                    hiz=hiz,
                    temperature=temp,
                    kelime_turu=kelime_turu,
                    tek_kelime_mi=tek_kelime_mi,
                    hikmetli_durak_ekle=hikmetli,
                    wav_formatini_zorla=(self.uzanti == ".wav"),
                    ozel_ref_metin=e_metin,
                    onceden_hazirlanmis_akustik_metin=self.akustik_metin,
                    min_tokens_override=min_tok_ovr,
                    max_tokens_override=max_tok_ovr,
                    dsp_ayar=dsp_ayar,
                    referans_ses_kullan=etkin_ref_kullan,
                    ilerleme_callback=lambda y, m: self.ilerleme_sinyali.emit(int(y * 0.5), f"[Erkek] {m}"),
                    cancel_token=self.cancel_token,
                    top_p_override=top_p,
                    top_k_override=top_k,
                )

                if self.cancel_token.is_cancelled or motor.durdur_istegi:
                    self.tamamlandi_sinyali.emit(False, "⏹️ İşlem kullanıcı tarafından durduruldu.", "", "")
                    return

                k_yol = str(cfg.resolve_voice_path(self.kadin_ref_id))
                k_metin = cfg.get_voice_prompt_text(self.kadin_ref_id)

                ok_k = motor.uret_ve_kaydet(
                    arapca_metin=self.arapca_metin,
                    ref_wav_yolu=k_yol,
                    cikti_yolu=kadin_hedef,
                    hiz=hiz,
                    temperature=temp,
                    kelime_turu=kelime_turu,
                    tek_kelime_mi=tek_kelime_mi,
                    hikmetli_durak_ekle=hikmetli,
                    wav_formatini_zorla=(self.uzanti == ".wav"),
                    ozel_ref_metin=k_metin,
                    onceden_hazirlanmis_akustik_metin=self.akustik_metin,
                    min_tokens_override=min_tok_ovr,
                    max_tokens_override=max_tok_ovr,
                    dsp_ayar=dsp_ayar,
                    referans_ses_kullan=etkin_ref_kullan,
                    ilerleme_callback=lambda y, m: self.ilerleme_sinyali.emit(50 + int(y * 0.5), f"[Kadın] {m}"),
                    cancel_token=self.cancel_token,
                    top_p_override=top_p,
                    top_k_override=top_k,
                )

                if ok_e and ok_k:
                    self.tamamlandi_sinyali.emit(
                        True, "✅ Erkek ve Kadın stüdyo sesleri başarıyla üretildi!", str(erkek_hedef), str(kadin_hedef)
                    )
                else:
                    hata = motor.son_hata_mesaji or "Çift ses üretimi tamamlanamadı."
                    self.tamamlandi_sinyali.emit(False, f"❌ {hata}", "", "")
            else:
                tek_hedef = guvenli_hedef_yol_cozumle(ana_cikti, f"{self.dosya_adi_temel}{self.uzanti}")
                ref_yol = str(cfg.resolve_voice_path(self.tek_ref_id))
                ref_metin = cfg.get_voice_prompt_text(self.tek_ref_id)

                ok = motor.uret_ve_kaydet(
                    arapca_metin=self.arapca_metin,
                    ref_wav_yolu=ref_yol,
                    cikti_yolu=tek_hedef,
                    hiz=hiz,
                    temperature=temp,
                    kelime_turu=kelime_turu,
                    tek_kelime_mi=tek_kelime_mi,
                    hikmetli_durak_ekle=hikmetli,
                    wav_formatini_zorla=(self.uzanti == ".wav"),
                    ozel_ref_metin=ref_metin,
                    onceden_hazirlanmis_akustik_metin=self.akustik_metin,
                    min_tokens_override=min_tok_ovr,
                    max_tokens_override=max_tok_ovr,
                    dsp_ayar=dsp_ayar,
                    referans_ses_kullan=etkin_ref_kullan,
                    ilerleme_callback=self.ilerleme_sinyali.emit,
                    cancel_token=self.cancel_token,
                    top_p_override=top_p,
                    top_k_override=top_k,
                )

                if self.cancel_token.is_cancelled or motor.durdur_istegi:
                    self.tamamlandi_sinyali.emit(False, "⏹️ İşlem kullanıcı tarafından durduruldu.", "", "")
                    return

                if ok:
                    self.tamamlandi_sinyali.emit(True, "✅ Stüdyo sesi başarıyla üretildi!", str(tek_hedef), "")
                else:
                    hata = motor.son_hata_mesaji or "Ses üretimi başarısız oldu."
                    self.tamamlandi_sinyali.emit(False, f"❌ {hata}", "", "")

        except Exception as e:
            self.tamamlandi_sinyali.emit(False, f"❌ Sentez hatası: {e}", "", "")


# ==============================================================================
# 6. ANA PENCERE (MUALLİMUN AI SES STÜDYOSU PRO)
# ==============================================================================
class MuallimunStudyoMainWindow(QMainWindow):
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        if self.config_manager.user_settings.get("github_repo") in (
            "", None, "abdullahtat/muallimun-ai-ses-studyosu-pro"
        ):
            self.config_manager.user_settings["github_repo"] = VARSAYILAN_GITHUB_REPO
            self.config_manager.save_user_settings()

        self.studyo_motor: Optional[MuallimunStudyoSesMotoru] = None
        self.tekli_worker: Optional[TekliSentezWorker] = None
        self._bekleyen_tekli_isciler: List[QThread] = []
        self._guncelleme_worker: Optional[GitHubGuncellemeKontrolWorker] = None

        self.ses_oynatici = GarantiliStudyoSesOynatici()
        self.son_erkek_veya_tek_ses: str = ""
        self.son_kadin_ses: str = ""
        self.uzman_mod: bool = bool(self.config_manager.user_settings.get("uzman_mod_aktif", False))
        self.tema_modu: str = str(self.config_manager.user_settings.get("tema_modu", "koyu"))
        self._mod_senkron_kilidi: bool = False

        self.setWindowTitle(
            f"Muallimun AI Ses Stüdyosu Pro v{APP_VERSION} — 24kHz Neural Arapça Dublaj & DSP Mastering"
        )
        self.setMinimumSize(1020, 650)
        self.resize(1240, 740)

        self._arayuzu_olustur()
        self._kisayollari_bagla()
        self._temayi_uygula(self.tema_modu)
        self._gorunum_modunu_uygula(self.uzman_mod)
        self.gpu_durumunu_guncelle()

        QTimer.singleShot(350, self._acilis_kontrollerini_calistir)

    def _kisayollari_bagla(self) -> None:
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._tekli_sentez_baslat)
        QShortcut(QKeySequence("Escape"), self, activated=self._tekli_sentez_durdur)
        QShortcut(QKeySequence("F1"), self, activated=self._kullanim_kilavuzunu_ac)
        QShortcut(QKeySequence("Ctrl++"), self, activated=lambda: self._arapca_yazi_boyutunu_degistir(+2))
        QShortcut(QKeySequence("Ctrl+="), self, activated=lambda: self._arapca_yazi_boyutunu_degistir(+2))
        QShortcut(QKeySequence("Ctrl+-"), self, activated=lambda: self._arapca_yazi_boyutunu_degistir(-2))

    def _acilis_kontrollerini_calistir(self) -> None:
        if not self.config_manager.user_settings.get("ilk_acilis_turu_gosterildi", False):
            dlg = BaslangicTuruDialog(self.config_manager, parent=self)
            dlg.exec()

        if self.config_manager.user_settings.get("otomatik_guncelleme_kontrolu", True):
            repo = self.config_manager.user_settings.get("github_repo", VARSAYILAN_GITHUB_REPO)
            self._guncelleme_worker = GitHubGuncellemeKontrolWorker(github_repo=repo, mevcut_surum=APP_VERSION)
            self._guncelleme_worker.sonuc_sinyali.connect(self._arka_plan_guncelleme_sonucu)
            self._guncelleme_worker.start()

    def _arka_plan_guncelleme_sonucu(self, basarili: bool, bilgi: Dict[str, Any]) -> None:
        if basarili and bilgi.get("yeni_surum_var"):
            uzak = bilgi.get("uzak_surum", "")
            self.btn_guncelleme.setText("🎉")
            self.btn_guncelleme.setToolTip(f"🎉 Yeni Sürüm Mevcut (v{uzak}) — İndirmek için tıklayın!")
            self.btn_guncelleme.setStyleSheet(
                "background-color: #10b981; color: white; border: none; font-size: 12pt; font-weight: bold;"
            )
            dlg = GuncellemeKontrolDialog(
                self.config_manager, otomatik_bildirim_mi=True, bilgisiz_bilgi=bilgi, parent=self
            )
            dlg.exec()

    def motoru_getir_veya_yukle(
        self,
        log_fn: Optional[Any] = None,
        zorunlu_motor_tipi: Optional[str] = None,
    ) -> MuallimunStudyoSesMotoru:
        hedef_motor = (
            zorunlu_motor_tipi
            or self.config_manager.user_settings.get("aktif_motor_tercihi", "SPARK_ARABIC")
        )
        if hedef_motor not in ("SPARK_ARABIC", "FAST_DIRECT_TTS", "XTTS_STUDIO"):
            hedef_motor = "SPARK_ARABIC"

        zorunlu_kademe = self.config_manager.user_settings.get("zorunlu_donanim_kademesi", "OTOMATIK")
        kademe_param = None if zorunlu_kademe == "OTOMATIK" else zorunlu_kademe

        if self.studyo_motor is None:
            self.studyo_motor = MuallimunStudyoSesMotoru(
                motor_tercihi=hedef_motor,
                log_callback=log_fn or self._teknik_log_ekle,
                zorunlu_kademe=kademe_param,
            )
        else:
            if log_fn is not None:
                self.studyo_motor.log_callback = log_fn
            if self.studyo_motor.motor_tipi != hedef_motor:
                self.studyo_motor.aktif_motoru_degistir(hedef_motor)

        QTimer.singleShot(100, self.gpu_durumunu_guncelle)
        return self.studyo_motor

    # ------------------------------------------------------------------
    # 3. SEKME İÇİN ETİKET + 'ℹ️' BİLGİ İKONU OLUŞTURUCU YARDIMCI METOT
    # ------------------------------------------------------------------
    def _parametre_bilgi_penceresi_ac(self, parametre_anahtari: str) -> None:
        dlg = ParametreBilgiDialog(
            secili_anahtar=parametre_anahtari,
            koyu_tema=(self.tema_modu != "aydinlik"),
            parent=self,
        )
        dlg.exec()

    def _etiket_ve_info_olustur(self, etiket_metni: str, parametre_anahtari: str, widget_hedef: Optional[QWidget] = None) -> QWidget:
        bilgi = DSP_VE_PRESET_PARAMETRE_REHBERI.get(parametre_anahtari, {})
        ipucu_html = (
            f"<b>{bilgi.get('baslik', etiket_metni)}</b><br>"
            f"{bilgi.get('ozet', '')}<br>"
            f"<i>⭐ Önerilen: {bilgi.get('onerilen', '')}</i><br>"
            f"<span style='color:#38bdf8;'>Detaylı açıklama için 'ℹ️' ikonuna tıklayın.</span>"
        )

        kapsayici = QWidget()
        h = QHBoxLayout(kapsayici)
        h.setContentsMargins(0, 0, 2, 0)
        h.setSpacing(4)

        lbl = QLabel(etiket_metni)
        lbl.setToolTip(ipucu_html)
        h.addWidget(lbl)

        btn_info = QPushButton("ℹ️")
        btn_info.setFixedSize(22, 22)
        btn_info.setCursor(Qt.PointingHandCursor)
        btn_info.setToolTip(ipucu_html)
        btn_info.setStyleSheet(
            "QPushButton { background-color: #0284c7; color: white; border: none; border-radius: 11px; "
            "font-size: 9pt; font-weight: bold; padding: 0px; } "
            "QPushButton:hover { background-color: #10b981; }"
        )
        btn_info.clicked.connect(lambda checked=False, k=parametre_anahtari: self._parametre_bilgi_penceresi_ac(k))
        h.addWidget(btn_info)
        h.addStretch()

        if widget_hedef is not None:
            widget_hedef.setToolTip(ipucu_html)

        return kapsayici

    # ------------------------------------------------------------------
    # ARAPÇA METİN YAZI BOYUTU (+ / -) YÖNETİMİ
    # (Yalnızca Arapça metin alanının puntosunu değiştirir; yeşil kutunun yüksekliğini etkilemez!)
    # ------------------------------------------------------------------
    def _arapca_yazi_boyutunu_degistir(self, fark: int) -> None:
        mevcut = oturum_arapca_font_boyutu_getir()
        yeni_boyut = oturum_arapca_font_boyutu_ayarla(mevcut + fark)
        self._arapca_font_boyutunu_uygula(yeni_boyut)

    def _arapca_font_boyutunu_uygula(self, punto: int) -> None:
        aile = profesyonel_arapca_font_ailesi_bul()
        ana_font = profesyonel_arapca_font_olustur(punto)

        if hasattr(self, "txt_arapca_girdi"):
            self.txt_arapca_girdi.setFont(ana_font)
            self.txt_arapca_girdi.document().setDefaultFont(ana_font)
            self.txt_arapca_girdi.setStyleSheet(
                f"QTextEdit {{ font-family: '{aile}'; font-size: {punto}pt; line-height: 1.45; padding: 6px 10px; }}"
            )

        if hasattr(self, "lbl_yazi_boyutu"):
            self.lbl_yazi_boyutu.setText(f"{punto} pt")
            self.lbl_yazi_boyutu.setToolTip(
                f"Aktif Arapça Font: {aile} ({punto} pt)\n"
                "Oturum boyunca korunur. Değiştirmek için A- / A+ butonlarını veya Ctrl+- / Ctrl++ kısayolunu kullanın."
            )

    def _yesil_vakif_kutusu_stilini_uygula(self) -> None:
        """Alttaki yeşil Canlı Vakıflı Okunuş kutusunun yüksekliğini ve puntosunu sabit tutar."""
        if not hasattr(self, "edt_akustik_onizleme"):
            return
        aile = profesyonel_arapca_font_ailesi_bul()
        sabit_font = profesyonel_arapca_font_olustur(19)
        self.edt_akustik_onizleme.setFont(sabit_font)
        self.edt_akustik_onizleme.setFixedHeight(44)
        koyu_mu = (self.tema_modu != "aydinlik")
        if koyu_mu:
            self.edt_akustik_onizleme.setStyleSheet(
                f"QLineEdit {{ background-color: #063928; color: #ecfdf5; border: 1px solid #10b981; "
                f"border-radius: 6px; padding: 4px 10px; font-family: '{aile}'; font-size: 19pt; }}"
            )
        else:
            self.edt_akustik_onizleme.setStyleSheet(
                f"QLineEdit {{ background-color: #d1fae5; color: #065f46; border: 1px solid #059669; "
                f"border-radius: 6px; padding: 4px 10px; font-family: '{aile}'; font-size: 19pt; }}"
            )

    # ------------------------------------------------------------------
    # ARAYÜZ OLUŞTURMA (KOMPAKT ÜST BAR, 5 SEKME VE ALT DURUM ÇUBUĞU)
    # ------------------------------------------------------------------
    def _arayuzu_olustur(self) -> None:
        merkez = QWidget()
        self.setCentralWidget(merkez)
        ana_v = QVBoxLayout(merkez)
        ana_v.setContentsMargins(10, 8, 10, 8)
        ana_v.setSpacing(6)

        ust_bar = QHBoxLayout()
        ust_bar.setSpacing(6)

        baslik_kutu = QVBoxLayout()
        baslik_kutu.setSpacing(1)
        self.lbl_ana_baslik = QLabel("🎙️ MUALLİMUN AI SES STÜDYOSU PRO")
        self.lbl_ana_baslik.setStyleSheet("font-size: 12.5pt; font-weight: bold; color: #0284c7;")
        self.lbl_alt_baslik = QLabel("Fasih Arapça Vakıf/Vasıl • 24kHz Neural Ses Klonlama & Direkt TTS")
        self.lbl_alt_baslik.setStyleSheet("font-size: 8.2pt; color: #64748b;")
        baslik_kutu.addWidget(self.lbl_ana_baslik)
        baslik_kutu.addWidget(self.lbl_alt_baslik)
        ust_bar.addLayout(baslik_kutu)
        ust_bar.addStretch()

        self.btn_gorunum_modu = QPushButton("🟢 Kolay Mod")
        self.btn_gorunum_modu.setFixedHeight(32)
        self.btn_gorunum_modu.setToolTip("Kolay Mod ile tüm DSP/Token ince ayarlarını açan Uzman Mod arasında geçiş yapar.")
        self.btn_gorunum_modu.clicked.connect(self._gorunum_modu_degistir)
        ust_bar.addWidget(self.btn_gorunum_modu)

        self.lbl_gpu_durum = QLabel("🚀 GPU...")
        self.lbl_gpu_durum.setFixedHeight(32)
        self.lbl_gpu_durum.setStyleSheet(
            "background-color: #111827; color: #10b981; border: 1px solid #1e293b; "
            "border-radius: 6px; padding: 4px 10px; font-weight: bold; font-size: 8.5pt;"
        )
        ust_bar.addWidget(self.lbl_gpu_durum)

        self.btn_gpu_optimize = QPushButton("⚡ GPU Optimize")
        self.btn_gpu_optimize.setFixedHeight(32)
        self.btn_gpu_optimize.setToolTip("VRAM belleğini temizler ve 4 donanım çalışma kademesinden birini seçmenizi sağlar.")
        self.btn_gpu_optimize.setStyleSheet(
            "background-color: #7c3aed; color: white; border: none; padding: 5px 10px; font-weight: bold;"
        )
        self.btn_gpu_optimize.clicked.connect(self._gpu_optimize_diyalogu_ac)
        ust_bar.addWidget(self.btn_gpu_optimize)

        self.btn_kurulum_merkezi = QPushButton("⚙️ Modeller && Kurulum")
        self.btn_kurulum_merkezi.setFixedHeight(32)
        self.btn_kurulum_merkezi.setToolTip("Ses modellerini (Spark-TTS, Direkt TTS, XTTS v2) ve kütüphaneleri yönetir.")
        self.btn_kurulum_merkezi.setStyleSheet(
            "background-color: #0284c7; color: white; border: none; padding: 5px 10px; font-weight: bold;"
        )
        self.btn_kurulum_merkezi.clicked.connect(self._kurulum_sihirbazini_ac)
        ust_bar.addWidget(self.btn_kurulum_merkezi)

        self.btn_tema = QPushButton("☀️" if self.tema_modu == "koyu" else "🌙")
        self.btn_tema.setFixedSize(36, 32)
        self.btn_tema.setStyleSheet("font-size: 12pt; padding: 0px;")
        self.btn_tema.setToolTip("Tema Değiştir: Aydınlık Mod (☀️) / Koyu Stüdyo Modu (🌙)")
        self.btn_tema.clicked.connect(self._tema_degistir)
        ust_bar.addWidget(self.btn_tema)

        self.btn_kilavuz = QPushButton("📘")
        self.btn_kilavuz.setFixedSize(36, 32)
        self.btn_kilavuz.setStyleSheet("font-size: 12pt; padding: 0px;")
        self.btn_kilavuz.setToolTip("Kapsamlı Kullanım Kılavuzu ve 5 Adımlı Başlangıç Turu (F1)")
        self.btn_kilavuz.clicked.connect(self._kullanim_kilavuzunu_ac)
        ust_bar.addWidget(self.btn_kilavuz)

        self.btn_guncelleme = QPushButton("🔄")
        self.btn_guncelleme.setFixedSize(36, 32)
        self.btn_guncelleme.setStyleSheet("font-size: 12pt; padding: 0px;")
        self.btn_guncelleme.setToolTip("GitHub Yeni Sürüm ve Güncelleme Kontrolü")
        self.btn_guncelleme.clicked.connect(self._guncelleme_penceresini_ac)
        ust_bar.addWidget(self.btn_guncelleme)

        ana_v.addLayout(ust_bar)

        self.ana_tabs = QTabWidget()
        self.sekme_1_tekli = self._sekme_1_tekli_studyo_olustur()
        self.sekme_2_referans = self._sekme_2_referans_havuzu_olustur()
        self.sekme_3_dsp = self._sekme_3_dsp_ve_preset_olustur()
        self.sekme_4_toplu = TopluSeslendirmeSekmesi(self)
        self.sekme_5_diyalog = DiyalogUzunMetinSekmesi(self)

        self.ana_tabs.addTab(self.sekme_1_tekli, "🎙️ 1. Seslendirme Stüdyosu")
        self.ana_tabs.setTabToolTip(0, "Tek kelime, cümle veya atasözlerini anında sentezleyin ve dalga formunu inceleyin.")
        self.ana_tabs.addTab(self.sekme_2_referans, "🗣️ 2. Referans Sesler (8+ Karakter)")
        self.ana_tabs.setTabToolTip(1, "8 hazır stüdyo karakterini dinleyin veya kendi özel referans sesinizi ekleyin.")
        self.ana_tabs.addTab(self.sekme_3_dsp, "🎚️ 3. Stüdyo DSP && Preset İnce Ayar")
        self.ana_tabs.setTabToolTip(2, "18+ akustik, token ve 5-katmanlı DSP mastering ayarını 'ℹ️' rehberleriyle yönetin.")
        self.ana_tabs.addTab(self.sekme_4_toplu, "📦 4. Toplu Seslendirme")
        self.ana_tabs.setTabToolTip(3, "Excel, JSON, CSV veya TXT dosyalarını seçmeli kuyruk ve Checkpoint v2 ile seslendirin.")
        self.ana_tabs.addTab(self.sekme_5_diyalog, "🎭 5. Diyalog && Uzun Metin")
        self.ana_tabs.setTabToolTip(4, "8 karakterli diyalogları ve uzun okuma parçalarını cümle cümle + birleşik üretin.")

        ana_v.addWidget(self.ana_tabs, stretch=1)

        alt_bar = QHBoxLayout()
        alt_bar.setSpacing(8)

        self.btn_son_sesi_dinle = QPushButton("🔊 Son Üretilen Sesi Dinle")
        self.btn_son_sesi_dinle.setFixedHeight(30)
        self.btn_son_sesi_dinle.setToolTip("En son sentezlenen ses dosyasını tekrar oynatır.")
        self.btn_son_sesi_dinle.setStyleSheet(
            "background-color: #059669; color: white; border: none; padding: 4px 12px; font-weight: bold;"
        )
        self.btn_son_sesi_dinle.clicked.connect(self._son_uretilen_sesi_dinle)
        alt_bar.addWidget(self.btn_son_sesi_dinle)

        self.btn_sesi_durdur = QPushButton("⏹️ Sesi Durdur")
        self.btn_sesi_durdur.setFixedHeight(30)
        self.btn_sesi_durdur.setToolTip("Çalan sesi anında susturur.")
        self.btn_sesi_durdur.clicked.connect(self._oynatmayi_durdur)
        alt_bar.addWidget(self.btn_sesi_durdur)

        self.lbl_durum_cubugu = QLabel("🎧 Stüdyo Hazır — ⭐ Varsayılan Motor: Spark-TTS (24kHz BiCodec)")
        self.lbl_durum_cubugu.setStyleSheet("color: #64748b; font-size: 9pt;")
        alt_bar.addWidget(self.lbl_durum_cubugu, stretch=1)

        btn_github_repo = QPushButton("🐙 GitHub")
        btn_github_repo.setFixedHeight(28)
        btn_github_repo.setCursor(Qt.PointingHandCursor)
        btn_github_repo.setToolTip("https://github.com/muallimun/Muallimun_Ses_Asistani")
        btn_github_repo.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/muallimun/Muallimun_Ses_Asistani"))
        )
        alt_bar.addWidget(btn_github_repo)

        btn_portal = QPushButton("🏛️ Muallimun Dijital Eğitim Teknolojileri — 🌐 muallimun.net")
        btn_portal.setFixedHeight(28)
        btn_portal.setCursor(Qt.PointingHandCursor)
        btn_portal.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://muallimun.net")))
        alt_bar.addWidget(btn_portal)

        ana_v.addLayout(alt_bar)

        self.txt_teknik_log = QTextEdit()
        self.txt_teknik_log.setReadOnly(True)

    # ------------------------------------------------------------------
    # SEKME 1: TEKLİ SESLENDİRME STÜDYOSU (YAZI BOYUTU +/- VE PROFESYONEL ARAPÇA FONT)
    # ------------------------------------------------------------------
    def _sekme_1_tekli_studyo_olustur(self) -> QWidget:
        sayfa = QWidget()
        dis_h = QHBoxLayout(sayfa)
        dis_h.setContentsMargins(8, 6, 8, 6)

        splitter = QSplitter(Qt.Horizontal)
        dis_h.addWidget(splitter)

        sol_panel = QWidget()
        sol_v = QVBoxLayout(sol_panel)
        sol_v.setContentsMargins(0, 0, 6, 0)
        sol_v.setSpacing(6)

        adim1_kutu = QGroupBox("Adım 1 — İçerik Türü, Doğal Duygu/Tonlama ve Vakıf Seçimi")
        a1_h = QHBoxLayout(adim1_kutu)
        a1_h.setContentsMargins(10, 8, 10, 8)
        a1_h.setSpacing(8)

        a1_h.addWidget(QLabel("Mod:"))
        self.cmb_tekli_mod = QComboBox()
        _kompakt_kutu_ayarla(self.cmb_tekli_mod, 165)
        for kod in ["tek_kelime", "cumle", "atasozu", "diyalog", "uzun_metin"]:
            p = self.config_manager.get_preset(kod)
            self.cmb_tekli_mod.addItem(p["baslik"], kod)
        self.cmb_tekli_mod.setCurrentIndex(1)
        self.cmb_tekli_mod.setToolTip(
            "Seslendirilecek içeriğin türünü seçin.\n"
            "Seçtiğiniz mod, 3. Sekmedeki (Stüdyo DSP & Preset İnce Ayar) kayıtlı ayarlarla senkronize çalışır."
        )
        self.cmb_tekli_mod.currentIndexChanged.connect(self._tekli_mod_degisti)
        a1_h.addWidget(self.cmb_tekli_mod, stretch=1)

        a1_h.addWidget(QLabel("Tonlama:"))
        self.cmb_tekli_tonlama = QComboBox()
        _kompakt_kutu_ayarla(self.cmb_tekli_tonlama, 175)
        for i_t, (d_kod, d_bilgi) in enumerate(DUYGU_TONU_PROFILLERI.items()):
            self.cmb_tekli_tonlama.addItem(d_bilgi["ad"], d_kod)
            self.cmb_tekli_tonlama.setItemData(i_t, d_bilgi.get("aciklama", ""), Qt.ToolTipRole)
        self.cmb_tekli_tonlama.setToolTip(
            "8 Akustik Tonlama Profili:\n"
            "Seçtiğiniz profil okuma hızını, sıcaklığı (temp), örnekleme keskinliğini (top-p/top-k) ve DSP doygunluğunu otomatik ayarlar."
        )
        self.cmb_tekli_tonlama.currentIndexChanged.connect(self._tekli_tonlama_degisti)
        a1_h.addWidget(self.cmb_tekli_tonlama, stretch=1)

        self.lbl_vakif_turu = QLabel("Vakıf:")
        self.cmb_vakif_turu = QComboBox()
        self.cmb_vakif_turu.addItem("İsim / Genel (Sonu Sükûn)", "isim")
        self.cmb_vakif_turu.addItem("Fiil (Son Harekeyi Koru)", "fiil")
        self.cmb_vakif_turu.setToolTip("Tek kelime modunda kelimenin isim (sükûnlu) veya fiil (harekeli) olarak duracağını belirler.")
        self.cmb_vakif_turu.currentIndexChanged.connect(self._canli_vakif_onizleme_guncelle)
        a1_h.addWidget(self.lbl_vakif_turu)
        a1_h.addWidget(self.cmb_vakif_turu)
        sol_v.addWidget(adim1_kutu)

        adim2_kutu = QGroupBox("Adım 2 — Seslendirilecek Arapça Metin ve Otomatik Harekeleme")
        a2_v = QVBoxLayout(adim2_kutu)
        a2_v.setContentsMargins(10, 8, 10, 8)
        a2_v.setSpacing(6)

        hareke_ust_bar = QHBoxLayout()
        hareke_ust_bar.setSpacing(4)
        self.btn_hareke_goster = QPushButton("⌨️ Hareke Klavyesi")
        self.btn_hareke_goster.setCheckable(True)
        self.btn_hareke_goster.setToolTip("Elle hareke eklemek için ekran üstü Arapça hareke tuşlarını açar/kapatır.")
        self.btn_hareke_goster.toggled.connect(lambda acik: self.hareke_cubugu.setVisible(acik))
        hareke_ust_bar.addWidget(self.btn_hareke_goster)

        self.btn_otomatik_harekele = QPushButton("✨ Otomatik Harekele")
        self.btn_otomatik_harekele.setStyleSheet(
            "background-color: #059669; color: white; border: none; padding: 5px 10px; font-weight: bold;"
        )
        self.btn_otomatik_harekele.setToolTip(
            "Harekesiz veya kısmi harekeli Arapça metni 2 Aşamalı Hibrit Tashkeel Motoru ile eksiksiz harekeler."
        )
        self.btn_otomatik_harekele.clicked.connect(self._tekli_metni_otomatik_harekele)
        hareke_ust_bar.addWidget(self.btn_otomatik_harekele)

        self.lbl_hareke_durum = QLabel("🟢 Tam Harekeli (%100)")
        self.lbl_hareke_durum.setStyleSheet("font-size: 8.6pt; font-weight: bold; color: #10b981; padding: 2px 4px;")
        self.lbl_hareke_durum.setToolTip("Spark-TTS motoru için metindeki harf ve kelime sonu hareke yoğunluğu durumu.")
        hareke_ust_bar.addWidget(self.lbl_hareke_durum)
        hareke_ust_bar.addStretch()

        self.btn_font_kucult = QPushButton("➖ A-")
        self.btn_font_kucult.setFixedSize(44, 28)
        self.btn_font_kucult.setToolTip("Yalnızca Arapça metin alanındaki yazı boyutunu küçültür (Ctrl + -).")
        self.btn_font_kucult.clicked.connect(lambda: self._arapca_yazi_boyutunu_degistir(-2))
        hareke_ust_bar.addWidget(self.btn_font_kucult)

        baslangic_punto = oturum_arapca_font_boyutu_getir()
        self.lbl_yazi_boyutu = QLabel(f"{baslangic_punto} pt")
        self.lbl_yazi_boyutu.setAlignment(Qt.AlignCenter)
        self.lbl_yazi_boyutu.setFixedWidth(44)
        self.lbl_yazi_boyutu.setStyleSheet("font-size: 8.5pt; font-weight: bold; color: #0284c7;")
        hareke_ust_bar.addWidget(self.lbl_yazi_boyutu)

        self.btn_font_buyut = QPushButton("➕ A+")
        self.btn_font_buyut.setFixedSize(44, 28)
        self.btn_font_buyut.setToolTip("Yalnızca Arapça metin alanındaki yazı boyutunu büyütür (Ctrl + +).")
        self.btn_font_buyut.clicked.connect(lambda: self._arapca_yazi_boyutunu_degistir(+2))
        hareke_ust_bar.addWidget(self.btn_font_buyut)

        btn_kopyala = QPushButton("📋 Kopyala")
        btn_kopyala.setToolTip("Arapça metni panoya kopyalar.")
        btn_kopyala.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.txt_arapca_girdi.toPlainText()))
        hareke_ust_bar.addWidget(btn_kopyala)

        btn_yapistir = QPushButton("📥 Yapıştır")
        btn_yapistir.setToolTip("Panodaki Arapça metni yapıştırır.")
        btn_yapistir.clicked.connect(lambda: self.txt_arapca_girdi.setPlainText(QGuiApplication.clipboard().text()))
        hareke_ust_bar.addWidget(btn_yapistir)

        btn_temizle_metin = QPushButton("🧹 Temizle")
        btn_temizle_metin.setToolTip("Arapça metin kutusunu temizler.")
        btn_temizle_metin.clicked.connect(lambda: self.txt_arapca_girdi.clear())
        hareke_ust_bar.addWidget(btn_temizle_metin)

        btn_ornek_metin = QPushButton("📝 Örnek Metin")
        btn_ornek_metin.setToolTip("Seçili içerik moduna uygun tam harekeli örnek Arapça metin getirir.")
        btn_ornek_metin.clicked.connect(self._tekli_ornek_metin_getir)
        hareke_ust_bar.addWidget(btn_ornek_metin)
        a2_v.addLayout(hareke_ust_bar)

        self.hareke_cubugu = QWidget()
        h_layout = QHBoxLayout(self.hareke_cubugu)
        h_layout.setContentsMargins(0, 2, 0, 2)
        h_layout.setSpacing(4)
        harekeler = [
            ("Fetha (ـَ)", "\u064E"),
            ("Kesra (ـِ)", "\u0650"),
            ("Damme (ـُ)", "\u064F"),
            ("Sükûn (ـْ)", "\u0652"),
            ("Şedde (ـّ)", "\u0651"),
            ("Tenvin Fetha (ـً)", "\u064B"),
            ("Tenvin Kesra (ـٍ)", "\u064D"),
            ("Tenvin Damme (ـٌ)", "\u064C"),
            ("Virgül (،)", "، "),
            ("Soru (؟)", "؟"),
        ]
        for etiket, karakter in harekeler:
            b_h = QPushButton(etiket)
            b_h.setFixedHeight(26)
            b_h.clicked.connect(lambda checked=False, ch=karakter: self._metne_hareke_ekle(ch))
            h_layout.addWidget(b_h)
        self.hareke_cubugu.setVisible(False)
        a2_v.addWidget(self.hareke_cubugu)

        self.txt_arapca_girdi = QTextEdit()
        self.txt_arapca_girdi.setLayoutDirection(Qt.RightToLeft)
        self.txt_arapca_girdi.setMinimumHeight(115)
        self.txt_arapca_girdi.setPlainText("أُمِّي مُعَلِّمَةٌ نَشِيطَةٌ تُحِبُّ عَمَلَهَا كَثِيرًا.")
        self.txt_arapca_girdi.textChanged.connect(self._canli_vakif_onizleme_guncelle)
        a2_v.addWidget(self.txt_arapca_girdi, stretch=1)

        vakif_bar = QHBoxLayout()
        lbl_vakif = QLabel("🔍 <b>Canlı Vakıflı Okunuş (Motorun Okuyacağı Hal — Düzenlenebilir):</b>")
        lbl_vakif.setStyleSheet("color: #10b981; font-size: 9pt;")
        vakif_bar.addWidget(lbl_vakif)
        vakif_bar.addStretch()

        btn_vakif_sifirla = QPushButton("🔄 Otomatik Vakıf Hesapla")
        btn_vakif_sifirla.setFixedHeight(24)
        btn_vakif_sifirla.setToolTip("Üstteki Arapça metne göre vakıflı/sükûnlu okunuşu yeniden hesaplar.")
        btn_vakif_sifirla.clicked.connect(self._canli_vakif_onizleme_guncelle)
        vakif_bar.addWidget(btn_vakif_sifirla)
        a2_v.addLayout(vakif_bar)

        self.edt_akustik_onizleme = QLineEdit()
        self.edt_akustik_onizleme.setLayoutDirection(Qt.RightToLeft)
        self.edt_akustik_onizleme.setFixedHeight(44)
        self.edt_akustik_onizleme.setToolTip(
            "Ses motoruna gönderilecek nihai vakıflı metin.\n"
            "Durak sonlarındaki tâ-i merbûta (ة -> هْ) ve son hareke sükûnu burada otomatik uygulanır."
        )
        a2_v.addWidget(self.edt_akustik_onizleme)
        sol_v.addWidget(adim2_kutu, stretch=1)

        self._arapca_font_boyutunu_uygula(baslangic_punto)
        self._yesil_vakif_kutusu_stilini_uygula()

        adim3_kutu = QGroupBox("Adım 3 — Stüdyo Dalga Formu (24kHz), Teknik Ses Kontrolü ve Dinleme")
        a3_v = QVBoxLayout(adim3_kutu)
        a3_v.setContentsMargins(10, 8, 10, 8)
        a3_v.setSpacing(6)

        self.waveform_widget = StudyoWaveformWidget(self)
        a3_v.addWidget(self.waveform_widget)

        dinle_bar = QHBoxLayout()
        self.btn_tekil_dinle = QPushButton("🔊 Üretilen Tekil / Erkek Sesini Dinle")
        self.btn_tekil_dinle.setFixedHeight(32)
        self.btn_tekil_dinle.setEnabled(False)
        self.btn_tekil_dinle.clicked.connect(lambda: self.ses_dosyasini_cal(self.son_erkek_veya_tek_ses))
        dinle_bar.addWidget(self.btn_tekil_dinle)

        self.btn_kadin_dinle = QPushButton("🔊 Üretilen Kadın Sesini Dinle")
        self.btn_kadin_dinle.setFixedHeight(32)
        self.btn_kadin_dinle.setEnabled(False)
        self.btn_kadin_dinle.clicked.connect(lambda: self.ses_dosyasini_cal(self.son_kadin_ses))
        dinle_bar.addWidget(self.btn_kadin_dinle)

        dinle_bar.addStretch()

        btn_klasor_ac = QPushButton("📂 Çıktı Klasörünü Aç")
        btn_klasor_ac.setFixedHeight(32)
        btn_klasor_ac.setToolTip("Üretilen tekli seslerin kaydedildiği 'cikti_sesler/tekli_studyo' klasörünü açar.")
        btn_klasor_ac.clicked.connect(self._tekli_cikti_klasorunu_ac)
        dinle_bar.addWidget(btn_klasor_ac)

        self.btn_farkli_kaydet = QPushButton("💾 Sesi Farklı Kaydet...")
        self.btn_farkli_kaydet.setFixedHeight(32)
        self.btn_farkli_kaydet.setEnabled(False)
        self.btn_farkli_kaydet.setToolTip("Son üretilen ses dosyasını istediğiniz bir klasöre farklı isimle kaydeder.")
        self.btn_farkli_kaydet.clicked.connect(self._uretilen_sesi_farkli_kaydet)
        dinle_bar.addWidget(self.btn_farkli_kaydet)

        a3_v.addLayout(dinle_bar)
        sol_v.addWidget(adim3_kutu)

        splitter.addWidget(sol_panel)

        # SAĞ PANEL
        sag_panel = QWidget()
        sag_panel.setMinimumWidth(335)
        sag_panel.setMaximumWidth(430)
        sag_v = QVBoxLayout(sag_panel)
        sag_v.setContentsMargins(6, 0, 0, 0)
        sag_v.setSpacing(6)

        motor_kutu = QGroupBox("Ses Motoru ve Karakter Seçimi")
        m_v = QVBoxLayout(motor_kutu)
        m_v.setContentsMargins(10, 8, 10, 8)
        m_v.setSpacing(6)

        m_satir = QHBoxLayout()
        m_satir.addWidget(QLabel("Motor:"))
        self.cmb_tekli_motor = QComboBox()
        _kompakt_kutu_ayarla(self.cmb_tekli_motor, 180)
        self.cmb_tekli_motor.addItem("🎙️ ⭐ Spark-TTS (Önerilen Klonlama)", "SPARK_ARABIC")
        self.cmb_tekli_motor.addItem("⚡ Hızlı Direkt Neural TTS (Çevrimiçi)", "FAST_DIRECT_TTS")
        self.cmb_tekli_motor.addItem("🗣️ Coqui XTTS v2 (Alternatif)", "XTTS_STUDIO")
        self.cmb_tekli_motor.setToolTip(
            "• ⭐ Spark-TTS (Önerilen): Tam harekeli Arapçada en yüksek mahreç ve ses klonlama kalitesi.\n"
            "• ⚡ Hızlı Direkt Neural TTS: Çevrimiçi hazır seslerle hızlı üretim (Harekesiz metinleri de okur).\n"
            "• 🗣️ Coqui XTTS v2: Alternatif çok dilli model."
        )
        aktif_motor = self.config_manager.user_settings.get("aktif_motor_tercihi", "SPARK_ARABIC")
        idx_m = self.cmb_tekli_motor.findData(aktif_motor)
        if idx_m >= 0:
            self.cmb_tekli_motor.setCurrentIndex(idx_m)
        self.cmb_tekli_motor.currentIndexChanged.connect(self._tekli_motor_secimi_degisti)
        m_satir.addWidget(self.cmb_tekli_motor, stretch=1)
        m_v.addLayout(m_satir)

        self.chk_referans_kullan = QCheckBox("🎙️ Referans Ses Kullan (Klonlama Aktif)")
        self.chk_referans_kullan.setChecked(True)
        self.chk_referans_kullan.setToolTip("Seçili stüdyo karakterinin ses rengini, vurgusunu ve tonlamasını klonlayarak sentez yapar.")
        self.chk_referans_kullan.setStyleSheet("font-weight: bold; color: #10b981;")
        self.chk_referans_kullan.toggled.connect(self._referans_veya_cift_secimi_guncelle)
        m_v.addWidget(self.chk_referans_kullan)

        self.chk_cift_uretim = QCheckBox("👨 + 👩 Erkek ve Kadın İkisini Birden Üret")
        self.chk_cift_uretim.setChecked(False)
        self.chk_cift_uretim.setToolTip("Aynı metni hem Erkek hem Kadın referans sesiyle peş peşe üretir.")
        self.chk_cift_uretim.setStyleSheet("font-weight: bold; color: #0284c7;")
        self.chk_cift_uretim.toggled.connect(self._referans_veya_cift_secimi_guncelle)
        m_v.addWidget(self.chk_cift_uretim)

        self.lbl_tek_ses = QLabel("Ses Karakteri (8 Stüdyo Sesi):")
        self.cmb_tek_ses = QComboBox()
        self.cmb_tek_ses.setToolTip("Seslendirmede kullanılacak referans ses karakterini seçin.")
        m_v.addWidget(self.lbl_tek_ses)
        m_v.addWidget(self.cmb_tek_ses)

        self.lbl_cift_erkek = QLabel("👨 Erkek Referans Sesi:")
        self.cmb_cift_erkek = QComboBox()
        self.lbl_cift_kadin = QLabel("👩 Kadın Referans Sesi:")
        self.cmb_cift_kadin = QComboBox()
        m_v.addWidget(self.lbl_cift_erkek)
        m_v.addWidget(self.cmb_cift_erkek)
        m_v.addWidget(self.lbl_cift_kadin)
        m_v.addWidget(self.cmb_cift_kadin)

        ref_btn_bar = QHBoxLayout()
        btn_ref_dinle = QPushButton("🔊 Bu Sesi Dinle")
        btn_ref_dinle.setToolTip("Seçili referans ses karakterinin orijinal stüdyo kaydını dinler.")
        btn_ref_dinle.setStyleSheet("background-color: #0284c7; color: white; border: none;")
        btn_ref_dinle.clicked.connect(self._secili_referans_sesini_dinle)
        ref_btn_bar.addWidget(btn_ref_dinle)

        btn_ref_metin_gor = QPushButton("📜 Referans Metni")
        btn_ref_metin_gor.setToolTip("Seçili referans seste okunan Arapça metni (Prompt Text) gösterir.")
        btn_ref_metin_gor.clicked.connect(self._secili_referans_metnini_goster)
        ref_btn_bar.addWidget(btn_ref_metin_gor)
        m_v.addLayout(ref_btn_bar)
        sag_v.addWidget(motor_kutu)

        cikti_kutu = QGroupBox("Çıktı ve İnce Ayarlar")
        c_v = QVBoxLayout(cikti_kutu)
        c_v.setContentsMargins(10, 8, 10, 8)
        c_v.setSpacing(5)

        c_satir1 = QHBoxLayout()
        c_satir1.addWidget(QLabel("Format:"))
        self.cmb_cikti_format = QComboBox()
        self.cmb_cikti_format.addItems(["WAV", "MP3"])
        self.cmb_cikti_format.setToolTip("WAV: Kayıpsız 24kHz PCM_16 | MP3: 192kbps True-Peak Limiter'lı kompakt ses.")
        c_satir1.addWidget(self.cmb_cikti_format)

        c_satir1.addWidget(QLabel("Ad:"))
        self.edt_dosya_adi = QLineEdit("studyo_kayit_001")
        self.edt_dosya_adi.setToolTip("Kaydedilecek ses dosyasının temel adı.")
        c_satir1.addWidget(self.edt_dosya_adi, stretch=1)
        c_v.addLayout(c_satir1)

        self.wid_tekli_uzman_ayar = QWidget()
        uz_h = QHBoxLayout(self.wid_tekli_uzman_ayar)
        uz_h.setContentsMargins(0, 2, 0, 2)
        uz_h.setSpacing(6)

        uz_h.addWidget(QLabel("⚡ Hız:"))
        self.spn_tekli_hiz = QDoubleSpinBox()
        self.spn_tekli_hiz.setRange(0.75, 1.25)
        self.spn_tekli_hiz.setSingleStep(0.02)
        self.spn_tekli_hiz.setValue(0.92)
        self.spn_tekli_hiz.setSuffix("x")
        self.spn_tekli_hiz.setToolTip(
            "Anlık okuma hızı çarpanı (0.75x yavaş – 1.25x hızlı).\n"
            "Sol üstteki Mod veya Tonlama değiştiğinde otomatik güncellenir; dilerseniz elle de değiştirebilirsiniz."
        )
        uz_h.addWidget(self.spn_tekli_hiz, stretch=1)

        uz_h.addWidget(QLabel("🌡️ Temp:"))
        self.spn_tekli_temp = QDoubleSpinBox()
        self.spn_tekli_temp.setRange(0.45, 0.78)
        self.spn_tekli_temp.setSingleStep(0.02)
        self.spn_tekli_temp.setValue(0.64)
        self.spn_tekli_temp.setToolTip(
            "Ses tonlama sıcaklığı / varyasyon (0.50 dengeli sözlük tonu – 0.75 canlı diyalog tonu).\n"
            "Sol üstteki Tonlama seçimine göre otomatik güncellenir."
        )
        uz_h.addWidget(self.spn_tekli_temp, stretch=1)
        c_v.addWidget(self.wid_tekli_uzman_ayar)

        self.chk_otomatik_numaralandir = QCheckBox("🔢 Dosya Adını Otomatik Artır (001, 002...)")
        self.chk_otomatik_numaralandir.setChecked(False)
        self.chk_otomatik_numaralandir.setToolTip("İşaretli olduğunda her sentez sonrası dosya adını 001 -> 002 şeklinde artırır.")
        c_v.addWidget(self.chk_otomatik_numaralandir)

        self.chk_zaman_damgasi_ekle = QCheckBox("🕒 Dosya Sonuna Zaman Damgası Ekle")
        self.chk_zaman_damgasi_ekle.setChecked(False)
        self.chk_zaman_damgasi_ekle.setToolTip(
            "İşaretli olduğunda üretilen ses dosyasının sonuna tarih ve saat (_20261104_142030) ekler; eski kayıtların üzerine yazılmaz."
        )
        c_v.addWidget(self.chk_zaman_damgasi_ekle)
        sag_v.addWidget(cikti_kutu)

        aksiyon_bar = QHBoxLayout()
        self.btn_seslendir = QPushButton("🎙️ SESLENDİR")
        self.btn_seslendir.setFixedHeight(44)
        self.btn_seslendir.setToolTip("Arapça metni seçili motor, tonlama ve doğal sönümlenmeli DSP ile sentezler (Ctrl+Enter).")
        self.btn_seslendir.setStyleSheet(
            "background-color: #10b981; color: white; border: none; border-radius: 7px; font-size: 11pt; font-weight: bold;"
        )
        self.btn_seslendir.clicked.connect(self._tekli_sentez_baslat)
        aksiyon_bar.addWidget(self.btn_seslendir, stretch=1)

        self.btn_tekli_durdur = QPushButton("⏹️ DURDUR")
        self.btn_tekli_durdur.setFixedHeight(44)
        self.btn_tekli_durdur.setEnabled(False)
        self.btn_tekli_durdur.setToolTip("Devam eden ses sentezini güvenli şekilde durdurur (Esc).")
        self.btn_tekli_durdur.setStyleSheet(
            "background-color: #dc2626; color: white; border: none; border-radius: 7px; padding: 0 14px; font-weight: bold;"
        )
        self.btn_tekli_durdur.clicked.connect(self._tekli_sentez_durdur)
        aksiyon_bar.addWidget(self.btn_tekli_durdur)
        sag_v.addLayout(aksiyon_bar)

        self.btn_alternatif_uret = QPushButton("🔄 Alternatif Tonlamayla Yeniden Üret")
        self.btn_alternatif_uret.setFixedHeight(30)
        self.btn_alternatif_uret.setToolTip("Bir sonraki duygu/tonlama profiline geçerek metni yeniden seslendirir.")
        self.btn_alternatif_uret.clicked.connect(self._alternatif_tonlamayla_uret)
        sag_v.addWidget(self.btn_alternatif_uret)

        durum_kutu = QGroupBox("Stüdyo Durumu ve İlerleme")
        d_v = QVBoxLayout(durum_kutu)
        d_v.setContentsMargins(10, 8, 10, 8)
        d_v.setSpacing(6)

        self.progress_tekli = QProgressBar()
        self.progress_tekli.setFixedHeight(24)
        self.progress_tekli.setRange(0, 100)
        self.progress_tekli.setValue(0)
        self.progress_tekli.setFormat("Hazır (%p%)")
        d_v.addWidget(self.progress_tekli)

        self.lbl_tekli_sonuc = QLabel("⏳ Sentez için hazır.")
        self.lbl_tekli_sonuc.setWordWrap(True)
        self.lbl_tekli_sonuc.setStyleSheet("font-size: 8.8pt; color: #10b981;")
        d_v.addWidget(self.lbl_tekli_sonuc)

        btn_log_gor = QPushButton("📋 Teknik İşlem Kayıtlarını (Log) Gör")
        btn_log_gor.setFixedHeight(28)
        btn_log_gor.setToolTip("Motor yükleme, token ve DSP işlem detaylarını gösteren kayıt penceresini açar.")
        btn_log_gor.clicked.connect(self._teknik_log_penceresi_ac)
        d_v.addWidget(btn_log_gor)

        sag_v.addWidget(durum_kutu)
        sag_v.addStretch()

        splitter.addWidget(sag_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        self._referans_kombolarini_doldur()
        self._referans_veya_cift_secimi_guncelle()
        self._tekli_mod_degisti()
        return sayfa

    def _tekli_metni_otomatik_harekele(self) -> None:
        mevcut = self.txt_arapca_girdi.toPlainText().strip()
        if not mevcut:
            QMessageBox.information(self, "Metin Boş", "Lütfen önce harekelenecek bir Arapça metin girin.")
            return
        harekeli, kaynak = ArapcaHarekelemeMotoru.metni_otomatik_harekele(mevcut)
        if harekeli:
            self.txt_arapca_girdi.setPlainText(harekeli)
            self.lbl_durum_cubugu.setText(f"✨ Metin otomatik harekelendi ({kaynak})")

    # ------------------------------------------------------------------
    # SEKME 2: REFERANS SES HAVUZU YÖNETİMİ
    # ------------------------------------------------------------------
    def _sekme_2_referans_havuzu_olustur(self) -> QWidget:
        sayfa = QWidget()
        v = QVBoxLayout(sayfa)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(8)

        ust = QHBoxLayout()
        ust.addWidget(QLabel("🗣️ <b>Stüdyo Referans Ses Havuzu (8 Fabrika Karakteri + Özel Eklenen Sesler):</b>"))
        ust.addStretch()

        btn_on_temizle_hepsi = QPushButton("✨ Tüm Referansları 24kHz Ön-Temizlikten Geçir")
        btn_on_temizle_hepsi.setToolTip("Referans sesleri doğal nefes ve vurgularını koruyarak 24kHz önbelleğe alır.")
        btn_on_temizle_hepsi.setStyleSheet("background-color: #0284c7; color: white; padding: 6px 12px;")
        btn_on_temizle_hepsi.clicked.connect(self._tum_referanslari_on_temizle)
        ust.addWidget(btn_on_temizle_hepsi)

        btn_ozel_ekle = QPushButton("➕ Yeni Özel Referans Ses Ekle...")
        btn_ozel_ekle.setToolTip("Kendi ses kaydınızı (.wav / .mp3) 24kHz stüdyo karakteri olarak havuza ekler.")
        btn_ozel_ekle.setStyleSheet("background-color: #059669; color: white; padding: 6px 14px;")
        btn_ozel_ekle.clicked.connect(self._ozel_referans_ses_ekle_diyalogu)
        ust.addWidget(btn_ozel_ekle)

        btn_secili_sil = QPushButton("🗑️ Seçili Özel Sesi Sil")
        btn_secili_sil.setToolTip("Sonradan eklediğiniz özel referans sesini listeden kaldırır.")
        btn_secili_sil.clicked.connect(self._secili_ozel_sesi_sil)
        ust.addWidget(btn_secili_sil)
        v.addLayout(ust)

        self.tablo_ses_havuzu = QTableWidget(0, 6)
        self.tablo_ses_havuzu.verticalHeader().setDefaultSectionSize(40)
        self.tablo_ses_havuzu.setHorizontalHeaderLabels([
            "ID", "Karakter Adı", "Cinsiyet / Kategori", "Dosya Durumu", "Referans Arapça Metin (Prompt Text — Düzenlenebilir)", "İşlem"
        ])
        self.tablo_ses_havuzu.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tablo_ses_havuzu.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tablo_ses_havuzu.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tablo_ses_havuzu.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tablo_ses_havuzu.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.tablo_ses_havuzu.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        v.addWidget(self.tablo_ses_havuzu, stretch=1)

        alt = QHBoxLayout()
        btn_klasor_ozel = QPushButton("📂 Özel Sesler Klasörünü Aç")
        btn_klasor_ozel.clicked.connect(lambda: os.startfile(str(self.config_manager.custom_voices_dir)) if os.name == "nt" else None)
        alt.addWidget(btn_klasor_ozel)
        alt.addStretch()

        btn_metin_kaydet = QPushButton("💾 Tablodaki Referans Metin Değişikliklerini Kaydet")
        btn_metin_kaydet.setStyleSheet("background-color: #0284c7; color: white; padding: 6px 14px;")
        btn_metin_kaydet.clicked.connect(self._referans_tablo_metinlerini_kaydet)
        alt.addWidget(btn_metin_kaydet)
        v.addLayout(alt)

        self._referans_havuzu_tablosunu_yenile()
        return sayfa

    # ------------------------------------------------------------------
    # SEKME 3: 18+ PARAMETRELİ TAM STÜDYO DSP & PRESET İNCE AYAR PANELİ ('ℹ️' İKONLU)
    # ------------------------------------------------------------------
    def _sekme_3_dsp_ve_preset_olustur(self) -> QWidget:
        sayfa = QWidget()
        v = QVBoxLayout(sayfa)
        v.setContentsMargins(12, 8, 12, 8)
        v.setSpacing(8)

        ust = QHBoxLayout()
        self.cmb_preset_sec = QComboBox()
        for kod in ["tek_kelime", "cumle", "atasozu", "diyalog", "uzun_metin"]:
            p = self.config_manager.get_preset(kod)
            self.cmb_preset_sec.addItem(p["baslik"], kod)
        self.cmb_preset_sec.setCurrentIndex(1)
        self.cmb_preset_sec.currentIndexChanged.connect(self._preset_secimi_degisti_3_sekme)

        ust.addWidget(self._etiket_ve_info_olustur("Düzenlenecek İçerik Modu (Preset):", "preset_modu", self.cmb_preset_sec))
        ust.addWidget(self.cmb_preset_sec, stretch=1)

        btn_rehber_tumu = QPushButton("📘 Tüm İnce Ayarların Rehberini Aç")
        btn_rehber_tumu.setToolTip("18+ ince ayarın ne işe yaradığını anlatan renkli rehber penceresini açar.")
        btn_rehber_tumu.setStyleSheet("background-color: #0284c7; color: white;")
        btn_rehber_tumu.clicked.connect(lambda: self._parametre_bilgi_penceresi_ac("hiz"))
        ust.addWidget(btn_rehber_tumu)

        btn_fabrika_don = QPushButton("🔄 Seçili Modu Fabrika Ayarlarına Sıfırla")
        btn_fabrika_don.setToolTip("Yalnızca şu an seçili olan içerik modunun ayarlarını ilk kurulum değerlerine döndürür.")
        btn_fabrika_don.clicked.connect(self._secili_preseti_sifirla)
        ust.addWidget(btn_fabrika_don)

        btn_tumunu_sifirla = QPushButton("⚠️ Tüm Modları Sıfırla")
        btn_tumunu_sifirla.setToolTip("5 içerik modunun tamamını fabrika ayarlarına döndürür.")
        btn_tumunu_sifirla.setStyleSheet("background-color: #dc2626; color: white;")
        btn_tumunu_sifirla.clicked.connect(self._tum_presetleri_sifirla)
        ust.addWidget(btn_tumunu_sifirla)
        v.addLayout(ust)

        sentez_kutu = QGroupBox("1. Neural Sentez, Hız, Örnekleme (Sampling) ve Token Sınırları (Açıklama İçin ℹ️ İkonuna Tıklayın)")
        g1 = QGridLayout(sentez_kutu)
        g1.setSpacing(8)

        self.spn_p_hiz = QDoubleSpinBox()
        self.spn_p_hiz.setRange(0.75, 1.25)
        self.spn_p_hiz.setSingleStep(0.02)

        self.spn_p_temp = QDoubleSpinBox()
        self.spn_p_temp.setRange(0.45, 0.78)
        self.spn_p_temp.setSingleStep(0.02)

        self.spn_p_topk = QSpinBox()
        self.spn_p_topk.setRange(10, 100)

        self.spn_p_topp = QDoubleSpinBox()
        self.spn_p_topp.setRange(0.50, 1.00)
        self.spn_p_topp.setSingleStep(0.02)

        self.spn_p_min_tok = QSpinBox()
        self.spn_p_min_tok.setRange(8, 200)

        self.spn_p_max_tok = QSpinBox()
        self.spn_p_max_tok.setRange(80, 1200)

        self.cmb_p_kelime_turu = QComboBox()
        self.cmb_p_kelime_turu.addItems(["genel", "isim", "fiil"])

        self.cmb_p_format = QComboBox()
        self.cmb_p_format.addItems(["wav", "mp3"])

        self.spn_p_birlesik_bosluk = QSpinBox()
        self.spn_p_birlesik_bosluk.setRange(100, 1500)
        self.spn_p_birlesik_bosluk.setSingleStep(50)
        self.spn_p_birlesik_bosluk.setSuffix(" ms")

        g1.addWidget(self._etiket_ve_info_olustur("Okuma Hızı (Atempo):", "hiz", self.spn_p_hiz), 0, 0)
        g1.addWidget(self.spn_p_hiz, 0, 1)
        g1.addWidget(self._etiket_ve_info_olustur("Sıcaklık (Temperature):", "temperature", self.spn_p_temp), 0, 2)
        g1.addWidget(self.spn_p_temp, 0, 3)
        g1.addWidget(self._etiket_ve_info_olustur("Top-K Örnekleme:", "top_k", self.spn_p_topk), 0, 4)
        g1.addWidget(self.spn_p_topk, 0, 5)

        g1.addWidget(self._etiket_ve_info_olustur("Top-P (Nucleus):", "top_p", self.spn_p_topp), 1, 0)
        g1.addWidget(self.spn_p_topp, 1, 1)
        g1.addWidget(self._etiket_ve_info_olustur("Min Yeni Token:", "min_tokens", self.spn_p_min_tok), 1, 2)
        g1.addWidget(self.spn_p_min_tok, 1, 3)
        g1.addWidget(self._etiket_ve_info_olustur("Maks Yeni Token:", "max_tokens", self.spn_p_max_tok), 1, 4)
        g1.addWidget(self.spn_p_max_tok, 1, 5)

        g1.addWidget(self._etiket_ve_info_olustur("Varsayılan Kelime Türü:", "kelime_turu", self.cmb_p_kelime_turu), 2, 0)
        g1.addWidget(self.cmb_p_kelime_turu, 2, 1)
        g1.addWidget(self._etiket_ve_info_olustur("Varsayılan Format:", "varsayilan_format", self.cmb_p_format), 2, 2)
        g1.addWidget(self.cmb_p_format, 2, 3)
        g1.addWidget(self._etiket_ve_info_olustur("Birleştirme Boşluğu:", "birlesik_bosluk_ms", self.spn_p_birlesik_bosluk), 2, 4)
        g1.addWidget(self.spn_p_birlesik_bosluk, 2, 5)

        chk_bar = QHBoxLayout()
        self.chk_p_cift = QCheckBox("👨+👩 Varsayılan Çift Üretim (E+K)")
        chk_bar.addWidget(self.chk_p_cift)
        chk_bar.addWidget(self._etiket_ve_info_olustur("", "cift_uretim_erkek_kadin", self.chk_p_cift))

        self.chk_p_hikmet = QCheckBox("🌿 Hikmetli Tefekkür Durağı (،) Ekle")
        chk_bar.addWidget(self.chk_p_hikmet)
        chk_bar.addWidget(self._etiket_ve_info_olustur("", "hikmetli_durak_ekle", self.chk_p_hikmet))

        self.chk_p_dinamik = QCheckBox("🎭 Soru/Ünlem Dinamik Tonlama Aktif")
        chk_bar.addWidget(self.chk_p_dinamik)
        chk_bar.addWidget(self._etiket_ve_info_olustur("", "dinamik_tonlama", self.chk_p_dinamik))

        chk_bar.addStretch()
        g1.addLayout(chk_bar, 3, 0, 1, 6)
        v.addWidget(sentez_kutu)

        dsp_kutu = QGroupBox("2. 5-Katmanlı 24kHz Stüdyo DSP Mastering ve Gürültü Kapısı Parametreleri (Açıklama İçin ℹ️ İkonuna Tıklayın)")
        g2 = QGridLayout(dsp_kutu)
        g2.setSpacing(8)

        self.spn_dsp_hp = QDoubleSpinBox()
        self.spn_dsp_hp.setRange(40.0, 200.0)
        self.spn_dsp_hp.setSuffix(" Hz")

        self.spn_dsp_lp = QDoubleSpinBox()
        self.spn_dsp_lp.setRange(6000.0, 11800.0)
        self.spn_dsp_lp.setSuffix(" Hz")

        self.spn_dsp_gate = QDoubleSpinBox()
        self.spn_dsp_gate.setDecimals(3)
        self.spn_dsp_gate.setRange(0.000, 0.080)
        self.spn_dsp_gate.setSingleStep(0.004)

        self.spn_dsp_aktif_esik = QDoubleSpinBox()
        self.spn_dsp_aktif_esik.setDecimals(3)
        self.spn_dsp_aktif_esik.setRange(0.005, 0.080)
        self.spn_dsp_aktif_esik.setSingleStep(0.004)

        self.spn_dsp_bas_pay = QDoubleSpinBox()
        self.spn_dsp_bas_pay.setRange(10.0, 250.0)
        self.spn_dsp_bas_pay.setSuffix(" ms")

        self.spn_dsp_son_pay = QDoubleSpinBox()
        self.spn_dsp_son_pay.setRange(30.0, 450.0)
        self.spn_dsp_son_pay.setSuffix(" ms")

        self.spn_dsp_drive = QDoubleSpinBox()
        self.spn_dsp_drive.setRange(1.00, 1.40)
        self.spn_dsp_drive.setSingleStep(0.02)

        self.spn_dsp_fade = QDoubleSpinBox()
        self.spn_dsp_fade.setRange(2.0, 60.0)
        self.spn_dsp_fade.setSuffix(" ms")

        self.spn_dsp_tepe = QDoubleSpinBox()
        self.spn_dsp_tepe.setDecimals(3)
        self.spn_dsp_tepe.setRange(0.500, 0.980)
        self.spn_dsp_tepe.setSingleStep(0.010)

        g2.addWidget(self._etiket_ve_info_olustur("High-Pass (Dip Filtre):", "hp_freq", self.spn_dsp_hp), 0, 0)
        g2.addWidget(self.spn_dsp_hp, 0, 1)
        g2.addWidget(self._etiket_ve_info_olustur("Low-Pass (Tiz Filtre):", "lp_freq", self.spn_dsp_lp), 0, 2)
        g2.addWidget(self.spn_dsp_lp, 0, 3)
        g2.addWidget(self._etiket_ve_info_olustur("RMS Gate Eşiği:", "gate_esigi", self.spn_dsp_gate), 0, 4)
        g2.addWidget(self.spn_dsp_gate, 0, 5)

        g2.addWidget(self._etiket_ve_info_olustur("Kırpma (Trim) Eşiği:", "aktif_esik_katsayi", self.spn_dsp_aktif_esik), 1, 0)
        g2.addWidget(self.spn_dsp_aktif_esik, 1, 1)
        g2.addWidget(self._etiket_ve_info_olustur("Başlangıç Payı (Pad):", "bas_pay_ms", self.spn_dsp_bas_pay), 1, 2)
        g2.addWidget(self.spn_dsp_bas_pay, 1, 3)
        g2.addWidget(self._etiket_ve_info_olustur("Bitiş Payı (Pad):", "son_pay_ms", self.spn_dsp_son_pay), 1, 4)
        g2.addWidget(self.spn_dsp_son_pay, 1, 5)

        g2.addWidget(self._etiket_ve_info_olustur("Tanh Drive (Doygunluk):", "drive", self.spn_dsp_drive), 2, 0)
        g2.addWidget(self.spn_dsp_drive, 2, 1)
        g2.addWidget(self._etiket_ve_info_olustur("Fade In/Out Süresi:", "fade_ms", self.spn_dsp_fade), 2, 2)
        g2.addWidget(self.spn_dsp_fade, 2, 3)
        g2.addWidget(self._etiket_ve_info_olustur("Tepe Normalizasyon:", "tepe_normalizasyon", self.spn_dsp_tepe), 2, 4)
        g2.addWidget(self.spn_dsp_tepe, 2, 5)
        v.addWidget(dsp_kutu)

        genel_kutu = QGroupBox("3. Genel Çıktı Klasörü ve Otomatik Oynatma Tercihleri")
        g3 = QHBoxLayout(genel_kutu)
        self.edt_genel_cikti_klasor = QLineEdit(str(self.config_manager.get_default_output_dir()))
        g3.addWidget(self._etiket_ve_info_olustur("Varsayılan Çıktı Klasörü:", "varsayilan_cikti_klasoru", self.edt_genel_cikti_klasor))
        g3.addWidget(self.edt_genel_cikti_klasor, stretch=1)

        btn_genel_klasor_sec = QPushButton("📁 Gözat...")
        btn_genel_klasor_sec.clicked.connect(self._genel_cikti_klasoru_sec)
        g3.addWidget(btn_genel_klasor_sec)

        self.chk_toplu_bitis_oynat = QCheckBox("🔊 Toplu İşlem Bitince Son Sesi Otomatik Çal")
        self.chk_toplu_bitis_oynat.setToolTip("Toplu seslendirme tamamlandığında üretilen son sesi bilgi amaçlı otomatik çalar.")
        self.chk_toplu_bitis_oynat.setChecked(
            bool(self.config_manager.user_settings.get("otomatik_oynat_toplu_bitis", False))
        )
        g3.addWidget(self.chk_toplu_bitis_oynat)
        v.addWidget(genel_kutu)

        btn_preset_kaydet = QPushButton("💾 Tüm Preset, DSP ve Klasör Ayarlarını Kaydet (1. Sekme İle Senkronize)")
        btn_preset_kaydet.setFixedHeight(36)
        btn_preset_kaydet.setToolTip("Yaptığınız değişiklikleri kaydeder ve 1. Sekmedeki hız/sıcaklık/format ayarlarına anında yansıtır.")
        btn_preset_kaydet.setStyleSheet("background-color: #059669; color: white; font-weight: bold;")
        btn_preset_kaydet.clicked.connect(self._preset_ayarlarini_kaydet)
        v.addWidget(btn_preset_kaydet)
        v.addStretch()

        self._preset_ayarlari_forma_yukle()
        return sayfa

    # ------------------------------------------------------------------
    # TEMA, GÖRÜNÜM MODU VE SENKRONİZASYON METOTLARI
    # ------------------------------------------------------------------
    def _tema_degistir(self) -> None:
        yeni_tema = "aydinlik" if self.tema_modu == "koyu" else "koyu"
        self._temayi_uygula(yeni_tema)

    def _temayi_uygula(self, tema_kodu: str) -> None:
        self.tema_modu = tema_kodu
        self.config_manager.user_settings["tema_modu"] = tema_kodu
        self.config_manager.save_user_settings()

        self.setStyleSheet(studyo_tema_qss_olustur(tema_kodu))
        koyu_mu = (tema_kodu != "aydinlik")

        if hasattr(self, "btn_tema"):
            self.btn_tema.setText("☀️" if koyu_mu else "🌙")
            self.btn_tema.setToolTip(
                "Aydınlık Moda Geç (☀️)" if koyu_mu else "Koyu Stüdyo Moduna Geç (🌙)"
            )

        if hasattr(self, "waveform_widget"):
            self.waveform_widget.tema_ayarla(koyu_mu)

        self._arapca_font_boyutunu_uygula(oturum_arapca_font_boyutu_getir())
        self._yesil_vakif_kutusu_stilini_uygula()

        if hasattr(self, "sekme_4_toplu"):
            self.sekme_4_toplu.tema_guncelle(tema_kodu)
        if hasattr(self, "sekme_5_diyalog"):
            self.sekme_5_diyalog.tema_guncelle(tema_kodu)

    def _gorunum_modu_degistir(self) -> None:
        self._gorunum_modunu_uygula(not self.uzman_mod)

    def _gorunum_modunu_uygula(self, uzman_mi: bool) -> None:
        self.uzman_mod = uzman_mi
        self.config_manager.user_settings["uzman_mod_aktif"] = uzman_mi
        self.config_manager.save_user_settings()

        if uzman_mi:
            self.btn_gorunum_modu.setText("🟣 Görünüm: UZMAN MOD")
            self.btn_gorunum_modu.setStyleSheet("background-color: #0284c7; color: white; padding: 5px 10px; font-weight: bold;")
        else:
            self.btn_gorunum_modu.setText("🟢 Görünüm: KOLAY MOD")
            self.btn_gorunum_modu.setStyleSheet("background-color: #059669; color: white; padding: 5px 10px; font-weight: bold;")

        self.ana_tabs.setTabVisible(2, uzman_mi)
        if hasattr(self, "wid_tekli_uzman_ayar"):
            self.wid_tekli_uzman_ayar.setVisible(uzman_mi)
        if hasattr(self, "sekme_4_toplu"):
            self.sekme_4_toplu.uzman_mod_guncelle(uzman_mi)

    def gpu_durumunu_guncelle(self) -> None:
        bilgi = gpu_vram_durumu_getir()
        if bilgi.get("aktif"):
            kisa_ad = str(bilgi.get("cihaz_adi", "GPU")).replace("NVIDIA GeForce ", "").replace(" Laptop GPU", "")
            self.lbl_gpu_durum.setText(f"🚀 {kisa_ad} | Boş: {bilgi.get('bos_gb', 0)}/{bilgi.get('toplam_gb', 0)} GB")
        else:
            self.lbl_gpu_durum.setText("💻 CPU Modu")
        self.lbl_gpu_durum.setToolTip(f"{bilgi.get('metin', '')}\n{bilgi.get('oneri_metni', '')}")

    def _gpu_optimize_diyalogu_ac(self) -> None:
        dlg = GpuKademeSecimDialog(self.config_manager, self.studyo_motor, parent=self)
        dlg.exec()
        self.gpu_durumunu_guncelle()

    def _kurulum_sihirbazini_ac(self) -> None:
        dlg = SetupWizardDialog(self.config_manager, parent=self)
        if dlg.exec() == QDialog.Accepted:
            secilen_motor = self.config_manager.user_settings.get("aktif_motor_tercihi", "SPARK_ARABIC")
            idx = self.cmb_tekli_motor.findData(secilen_motor)
            if idx >= 0:
                self.cmb_tekli_motor.setCurrentIndex(idx)
            self._referans_kombolarini_doldur()
            self.gpu_durumunu_guncelle()

    def _kullanim_kilavuzunu_ac(self) -> None:
        dlg = KullanimKilavuzuDialog(self.config_manager, parent=self)
        dlg.exec()

    def _guncelleme_penceresini_ac(self) -> None:
        dlg = GuncellemeKontrolDialog(self.config_manager, parent=self)
        dlg.exec()

    def _tekli_mod_degisti(self) -> None:
        mod_kodu = self.cmb_tekli_mod.currentData() or "cumle"
        preset = self.config_manager.get_preset(mod_kodu)
        fmt = str(preset.get("varsayilan_format", "wav")).upper()
        idx_f = self.cmb_cikti_format.findText(fmt)
        if idx_f >= 0:
            self.cmb_cikti_format.setCurrentIndex(idx_f)

        if hasattr(self, "cmb_preset_sec") and not self._mod_senkron_kilidi:
            self._mod_senkron_kilidi = True
            try:
                idx_p = self.cmb_preset_sec.findData(mod_kodu)
                if idx_p >= 0:
                    self.cmb_preset_sec.setCurrentIndex(idx_p)
                    self._preset_ayarlari_forma_yukle()
            finally:
                self._mod_senkron_kilidi = False

        varsayilan_ton_haritasi = {
            "tek_kelime": "tek_kelime_sozluk",
            "cumle": "otomatik",
            "atasozu": "babacan_hikmetli",
            "diyalog": "canli_diyalog",
            "uzun_metin": "oykuleyici_dingin",
        }
        hedef_ton = varsayilan_ton_haritasi.get(mod_kodu, "otomatik")
        idx_t = self.cmb_tekli_tonlama.findData(hedef_ton)
        if idx_t >= 0:
            self.cmb_tekli_tonlama.blockSignals(True)
            self.cmb_tekli_tonlama.setCurrentIndex(idx_t)
            self.cmb_tekli_tonlama.blockSignals(False)

        tek_kelime_mi = (mod_kodu == "tek_kelime")
        self.lbl_vakif_turu.setVisible(tek_kelime_mi)
        self.cmb_vakif_turu.setVisible(tek_kelime_mi)
        self._tekli_tonlama_degisti()
        self._canli_vakif_onizleme_guncelle()

    def _preset_secimi_degisti_3_sekme(self) -> None:
        self._preset_ayarlari_forma_yukle()
        if hasattr(self, "cmb_tekli_mod") and not self._mod_senkron_kilidi:
            self._mod_senkron_kilidi = True
            try:
                kod = self.cmb_preset_sec.currentData() or "cumle"
                idx_m = self.cmb_tekli_mod.findData(kod)
                if idx_m >= 0:
                    self.cmb_tekli_mod.setCurrentIndex(idx_m)
            finally:
                self._mod_senkron_kilidi = False

    def _tekli_tonlama_degisti(self) -> None:
        if not hasattr(self, "spn_tekli_hiz"):
            return
        mod_kodu = self.cmb_tekli_mod.currentData() or "cumle"
        duygu_kodu = self.cmb_tekli_tonlama.currentData() or "otomatik"
        preset = self.config_manager.get_preset(mod_kodu)
        arapca = self.txt_arapca_girdi.toPlainText().strip() if hasattr(self, "txt_arapca_girdi") else ""
        detay = duygu_ve_tonlama_detayli_hesapla(arapca, preset, duygu_kodu)
        self.spn_tekli_hiz.setValue(detay["hiz"])
        self.spn_tekli_temp.setValue(detay["temp"])
        self.cmb_tekli_tonlama.setToolTip(
            f"Seçili Tonlama: {detay['algilanan_kip']}\n"
            f"Açıklama: {detay['aciklama']}\n"
            f"Hesaplanan Hız: {detay['hiz']}x | Temp: {detay['temp']} | Top-P: {detay['top_p']} | Top-K: {detay['top_k']}"
        )
        self._canli_vakif_onizleme_guncelle()

    def _tekli_motor_secimi_degisti(self) -> None:
        kod = self.cmb_tekli_motor.currentData() or "SPARK_ARABIC"
        self.config_manager.user_settings["aktif_motor_tercihi"] = kod
        self.config_manager.save_user_settings()

        if kod == "FAST_DIRECT_TTS":
            self.chk_referans_kullan.setChecked(False)
            self.chk_referans_kullan.setEnabled(False)
        else:
            self.chk_referans_kullan.setEnabled(True)
            self.chk_referans_kullan.setChecked(True)

        if hasattr(self, "sekme_4_toplu") and hasattr(self.sekme_4_toplu, "cmb_toplu_motor"):
            idx_4 = self.sekme_4_toplu.cmb_toplu_motor.findData(kod)
            if idx_4 >= 0:
                self.sekme_4_toplu.cmb_toplu_motor.blockSignals(True)
                self.sekme_4_toplu.cmb_toplu_motor.setCurrentIndex(idx_4)
                self.sekme_4_toplu.cmb_toplu_motor.blockSignals(False)

        if hasattr(self, "sekme_5_diyalog"):
            for cmb_5 in (
                getattr(self.sekme_5_diyalog, "cmb_diyalog_motor", None),
                getattr(self.sekme_5_diyalog, "cmb_metin_motor", None),
            ):
                if isinstance(cmb_5, QComboBox):
                    idx_5 = cmb_5.findData(kod)
                    if idx_5 >= 0:
                        cmb_5.blockSignals(True)
                        cmb_5.setCurrentIndex(idx_5)
                        cmb_5.blockSignals(False)

        if self.studyo_motor is not None and (self.tekli_worker is None or not self.tekli_worker.isRunning()):
            self.studyo_motor.aktif_motoru_degistir(kod)
            self.gpu_durumunu_guncelle()

    def _referans_veya_cift_secimi_guncelle(self) -> None:
        cift_mi = self.chk_cift_uretim.isChecked()
        self.lbl_tek_ses.setVisible(not cift_mi)
        self.cmb_tek_ses.setVisible(not cift_mi)
        self.lbl_cift_erkek.setVisible(cift_mi)
        self.cmb_cift_erkek.setVisible(cift_mi)
        self.lbl_cift_kadin.setVisible(cift_mi)
        self.cmb_cift_kadin.setVisible(cift_mi)

    def _referans_kombolarini_doldur(self) -> None:
        eski_tek = self.cmb_tek_ses.currentData()
        eski_e = self.cmb_cift_erkek.currentData()
        eski_k = self.cmb_cift_kadin.currentData()

        self.cmb_tek_ses.clear()
        self.cmb_cift_erkek.clear()
        self.cmb_cift_kadin.clear()

        for ses in self.config_manager.voice_pool:
            ad = ses.get("ad", ses["id"])
            vid = ses["id"]
            self.cmb_tek_ses.addItem(ad, vid)
            if ses.get("cinsiyet", "E").upper() == "K":
                self.cmb_cift_kadin.addItem(ad, vid)
            else:
                self.cmb_cift_erkek.addItem(ad, vid)

        if eski_tek:
            idx_t = self.cmb_tek_ses.findData(eski_tek)
            if idx_t >= 0:
                self.cmb_tek_ses.setCurrentIndex(idx_t)
        if eski_e:
            idx_e = self.cmb_cift_erkek.findData(eski_e)
            if idx_e >= 0:
                self.cmb_cift_erkek.setCurrentIndex(idx_e)
        if eski_k:
            idx_k = self.cmb_cift_kadin.findData(eski_k)
            if idx_k >= 0:
                self.cmb_cift_kadin.setCurrentIndex(idx_k)

        if hasattr(self, "sekme_4_toplu"):
            self.sekme_4_toplu._referans_listelerini_doldur()
        if hasattr(self, "sekme_5_diyalog") and hasattr(self.sekme_5_diyalog, "_referans_listelerini_doldur"):
            self.sekme_5_diyalog._referans_listelerini_doldur()

    def _canli_vakif_onizleme_guncelle(self) -> None:
        arapca = self.txt_arapca_girdi.toPlainText().strip()
        mod_kodu = self.cmb_tekli_mod.currentData() or "cumle"
        duygu_kodu = self.cmb_tekli_tonlama.currentData() or "otomatik"
        preset = self.config_manager.get_preset(mod_kodu)
        ton_detay = duygu_ve_tonlama_detayli_hesapla(arapca, preset, duygu_kodu)
        hikmetli = ton_detay["hikmetli_durak"]

        kelime_turu = (
            self.cmb_vakif_turu.currentData()
            if mod_kodu == "tek_kelime"
            else str(preset.get("kelime_turu", "genel"))
        )
        akustik = arapca_akustik_metin_hazirla(arapca, kelime_turu=kelime_turu, hikmetli_durak_ekle=hikmetli)
        self.edt_akustik_onizleme.setText(akustik)

        if hasattr(self, "lbl_hareke_durum"):
            analiz = arapca_hareke_analizi_yap(arapca)
            self.lbl_hareke_durum.setText(analiz["etiket"])
            self.lbl_hareke_durum.setStyleSheet(
                f"font-size: 8.6pt; font-weight: bold; color: {analiz['renk']}; padding: 2px 4px;"
            )

    def _metne_hareke_ekle(self, karakter: str) -> None:
        cursor = self.txt_arapca_girdi.textCursor()
        cursor.insertText(karakter)
        self.txt_arapca_girdi.setFocus()

    def _tekli_ornek_metin_getir(self) -> None:
        mod_kodu = self.cmb_tekli_mod.currentData() or "cumle"
        ornekler = {
            "tek_kelime": "مَدْرَسَةٌ",
            "cumle": "بِدَايَةً لَا بُدَّ أَنْ تَعْلَمَ أَنَّ الْعَرَبَ عِنْدَهُمْ لُغَةٌ رَسْمِيَّةٌ وَهِيَ الْفَصِيحَةُ، وَتُسْتَخْدَمُ فِي الْأَوْرَاقِ الرَّسْمِيَّةِ.",
            "atasozu": "مَنْ جَدَّ وَجَدَ، وَمَنْ زَرَعَ حَصَدَ.",
            "diyalog": "اَلسَّلَامُ عَلَيْكُمْ يَا أَحْمَدُ، كَيْفَ حَالُكَ الْيَوْمَ؟",
            "uzun_metin": "اَلْعِلْمُ نُورٌ يُضِيءُ طَرِيقَ الْإِنْسَانِ فِي الْحَيَاةِ، وَالْقِرَاءَةُ الْمُسْتَمِرَّةُ تَفْتَحُ لَنَا أَبْوَابَ الْحِكْمَةِ.",
        }
        self.txt_arapca_girdi.setPlainText(ornekler.get(mod_kodu, ornekler["cumle"]))

    def _secili_referans_sesini_dinle(self) -> None:
        ref_id = self.cmb_cift_erkek.currentData() if self.chk_cift_uretim.isChecked() else self.cmb_tek_ses.currentData()
        yol = self.config_manager.resolve_voice_path(ref_id)
        self.ses_dosyasini_cal(str(yol))

    def _secili_referans_metnini_goster(self) -> None:
        ref_id = self.cmb_cift_erkek.currentData() if self.chk_cift_uretim.isChecked() else self.cmb_tek_ses.currentData()
        metin = self.config_manager.get_voice_prompt_text(ref_id)
        if not metin:
            QMessageBox.information(
                self,
                "Referans Ses Arapça Metni (Prompt Text)",
                f"Seçili Karakter: {ref_id}\n\n"
                "Bu özel referans ses için metin (Prompt Text) tanımlanmamış.\n"
                "Motor yalnızca ses rengini kopyalayan 'Saf Akustik Kimlik Klonlama' modunda çalışacaktır.",
            )
        else:
            QMessageBox.information(
                self,
                "Referans Ses Arapça Metni (Prompt Text)",
                f"Seçili Karakter: {ref_id}\n\n{metin}",
            )

    # ------------------------------------------------------------------
    # TEKLİ SENTEZ BAŞLATMA, OTURUM HAREKE UYARISI VE ZAMAN DAMGASI
    # ------------------------------------------------------------------
    def _tekli_sentez_baslat(self) -> None:
        arapca = self.txt_arapca_girdi.toPlainText().strip()
        if not arapca:
            QMessageBox.warning(self, "Metin Boş", "Lütfen seslendirilecek bir Arapça metin girin.")
            return

        if self.tekli_worker is not None and self.tekli_worker.isRunning():
            self.tekli_worker.durdur()
            if not self.tekli_worker.wait(2000):
                QMessageBox.information(self, "Meşgul", "Önceki sentez durduruluyor, lütfen 1 saniye sonra tekrar deneyin.")
                return

        secilen_motor = self.cmb_tekli_motor.currentData() or "SPARK_ARABIC"
        referans_kullan = self.chk_referans_kullan.isChecked()

        if secilen_motor == "SPARK_ARABIC" and referans_kullan and oturumda_hareke_uyarisi_aktif_mi():
            analiz = arapca_hareke_analizi_yap(arapca)
            if not analiz["spark_uygun"]:
                dlg = HarekeUyariVeOnayDialog(arapca, koyu_tema=(self.tema_modu != "aydinlik"), parent=self)
                if dlg.exec() != QDialog.Accepted or dlg.secim_sonucu == "IPTAL":
                    return
                if dlg.secim_sonucu == "HAREKELE_VE_SPARK":
                    arapca = dlg.onaylanan_metin
                    self.txt_arapca_girdi.setPlainText(arapca)
                    self._canli_vakif_onizleme_guncelle()
                elif dlg.secim_sonucu == "DIREKT_TTS_GEC":
                    secilen_motor = "FAST_DIRECT_TTS"
                    referans_kullan = False

        self.ses_oynatici.durdur()

        akustik = self.edt_akustik_onizleme.text().strip() or arapca_akustik_metin_hazirla(arapca)
        mod_kodu = self.cmb_tekli_mod.currentData() or "cumle"
        duygu_kodu = self.cmb_tekli_tonlama.currentData() or "otomatik"
        dosya_adi = self.edt_dosya_adi.text().strip() or "studyo_kayit_001"

        if self.chk_zaman_damgasi_ekle.isChecked():
            damga = datetime.now().strftime("%Y%m%d_%H%M%S")
            dosya_adi = f"{dosya_adi}_{damga}"

        uzanti = self.cmb_cikti_format.currentText()
        ozel_hiz = self.spn_tekli_hiz.value() if self.uzman_mod else None
        ozel_temp = self.spn_tekli_temp.value() if self.uzman_mod else None

        self.btn_seslendir.setEnabled(False)
        self.btn_alternatif_uret.setEnabled(False)
        self.btn_tekli_durdur.setEnabled(True)
        self.progress_tekli.setValue(4)
        self.progress_tekli.setFormat("⏳ Sentez başlatılıyor...")
        self.lbl_tekli_sonuc.setText("🎙️ Ses dalgaları hazırlanıyor...")

        worker = TekliSentezWorker(
            ana_pencere=self,
            arapca_metin=arapca,
            akustik_metin=akustik,
            mod_kodu=mod_kodu,
            duygu_kodu=duygu_kodu,
            secilen_motor_tipi=secilen_motor,
            referans_kullan=referans_kullan,
            cift_uretim=self.chk_cift_uretim.isChecked(),
            tek_ref_id=self.cmb_tek_ses.currentData() or "ref_erkek_1",
            erkek_ref_id=self.cmb_cift_erkek.currentData() or "ref_erkek_1",
            kadin_ref_id=self.cmb_cift_kadin.currentData() or "ref_kadin_1",
            dosya_adi_temel=dosya_adi,
            uzanti=uzanti,
            ozel_hiz=ozel_hiz,
            ozel_temp=ozel_temp,
        )
        self.tekli_worker = worker
        self._bekleyen_tekli_isciler.append(worker)

        worker.ilerleme_sinyali.connect(self._tekli_ilerleme_guncelle)
        worker.log_sinyali.connect(self._teknik_log_ekle)
        worker.tamamlandi_sinyali.connect(self._tekli_sentez_tamamlandi)
        worker.finished.connect(lambda w=worker: self._tekli_isci_temizle(w))
        worker.start()

    def _tekli_isci_temizle(self, w: QThread) -> None:
        if w in self._bekleyen_tekli_isciler:
            self._bekleyen_tekli_isciler.remove(w)
        self.btn_seslendir.setEnabled(True)
        self.btn_alternatif_uret.setEnabled(True)
        self.btn_tekli_durdur.setEnabled(False)
        self.gpu_durumunu_guncelle()

    def _tekli_sentez_durdur(self) -> None:
        if self.tekli_worker is not None:
            self.tekli_worker.durdur()
        if self.studyo_motor is not None:
            self.studyo_motor.durdur()
        self.btn_tekli_durdur.setEnabled(False)
        self.btn_seslendir.setEnabled(True)
        self.btn_alternatif_uret.setEnabled(True)
        self.progress_tekli.setFormat("⏹️ Durduruldu")
        self.lbl_tekli_sonuc.setText("⏹️ İşlem durduruldu — Yeni üretime hazır.")

    def _alternatif_tonlamayla_uret(self) -> None:
        mevcut_idx = self.cmb_tekli_tonlama.currentIndex()
        yeni_idx = (mevcut_idx + 1) % max(1, self.cmb_tekli_tonlama.count())
        self.cmb_tekli_tonlama.setCurrentIndex(yeni_idx)
        self._tekli_sentez_baslat()

    def _tekli_ilerleme_guncelle(self, yuzde: int, mesaj: str) -> None:
        self.progress_tekli.setValue(yuzde)
        self.progress_tekli.setFormat(f"%p% — {mesaj[:42]}")
        self.lbl_tekli_sonuc.setText(mesaj)

    def _tekli_sentez_tamamlandi(self, basarili: bool, mesaj: str, erkek_veya_tek_yol: str, kadin_yol: str) -> None:
        self.btn_seslendir.setEnabled(True)
        self.btn_alternatif_uret.setEnabled(True)
        self.btn_tekli_durdur.setEnabled(False)
        self.lbl_tekli_sonuc.setText(mesaj)

        if basarili and erkek_veya_tek_yol and os.path.exists(erkek_veya_tek_yol):
            self.progress_tekli.setValue(100)
            self.progress_tekli.setFormat("✅ Tamamlandı (%100)")
            self.son_erkek_veya_tek_ses = erkek_veya_tek_yol
            self.son_kadin_ses = kadin_yol
            self.btn_tekil_dinle.setEnabled(True)
            self.btn_farkli_kaydet.setEnabled(True)
            self.btn_kadin_dinle.setEnabled(bool(kadin_yol and os.path.exists(kadin_yol)))

            if self.chk_otomatik_numaralandir.isChecked():
                mevcut_ad = self.edt_dosya_adi.text().strip()
                m = re.search(r"^(.*?)(\d+)$", mevcut_ad)
                if m:
                    onek, sayi_str = m.group(1), m.group(2)
                    yeni_sayi = str(int(sayi_str) + 1).zfill(len(sayi_str))
                    self.edt_dosya_adi.setText(f"{onek}{yeni_sayi}")
                else:
                    self.edt_dosya_adi.setText(f"{mevcut_ad}_002")

            self.ses_dosyasini_cal(erkek_veya_tek_yol)
        else:
            self.progress_tekli.setFormat("Durduruldu / Uyarılı")
            if "durduruldu" not in mesaj.lower():
                QMessageBox.warning(self, "Sentez Uyarısı", mesaj)

    # ------------------------------------------------------------------
    # SES ÇALMA, DALGA FORMU VE DOSYA İŞLEMLERİ
    # ------------------------------------------------------------------
    def ses_dosyasini_cal(self, dosya_yolu: str) -> None:
        if not dosya_yolu or not os.path.exists(dosya_yolu):
            return
        kelime_sayisi = max(1, len(self.txt_arapca_girdi.toPlainText().split()))
        self.waveform_widget.ses_dosyasini_yukle(dosya_yolu, kelime_sayisi=kelime_sayisi)
        ok, durum = self.ses_oynatici.cal(dosya_yolu)
        self.lbl_durum_cubugu.setText(durum)

    def _son_uretilen_sesi_dinle(self) -> None:
        if self.son_erkek_veya_tek_ses and os.path.exists(self.son_erkek_veya_tek_ses):
            self.ses_dosyasini_cal(self.son_erkek_veya_tek_ses)
        else:
            QMessageBox.information(self, "Ses Yok", "Henüz üretilmiş bir ses dosyası bulunmuyor.")

    def _oynatmayi_durdur(self) -> None:
        self.ses_oynatici.durdur()
        self.lbl_durum_cubugu.setText("⏹️ Ses oynatma durduruldu.")

    def _tekli_cikti_klasorunu_ac(self) -> None:
        hedef = self.config_manager.get_default_output_dir() / "tekli_studyo"
        hedef.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(hedef.resolve()))
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(hedef.resolve())))

    def _uretilen_sesi_farkli_kaydet(self) -> None:
        if not self.son_erkek_veya_tek_ses or not os.path.exists(self.son_erkek_veya_tek_ses):
            return
        kaynak = Path(self.son_erkek_veya_tek_ses)
        hedef, _ = QFileDialog.getSaveFileName(
            self,
            "Üretilen Sesi Farklı Kaydet",
            str(Path.home() / "Desktop" / kaynak.name),
            f"Ses Dosyası (*{kaynak.suffix})",
        )
        if hedef:
            shutil.copy2(str(kaynak), str(hedef))
            QMessageBox.information(self, "Kaydedildi", f"Ses dosyası kaydedildi:\n{hedef}")

    def _teknik_log_ekle(self, mesaj: str) -> None:
        self.txt_teknik_log.append(mesaj)

    def _teknik_log_penceresi_ac(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("📋 Stüdyo Teknik İşlem Kayıtları (Log)")
        dlg.resize(740, 440)
        v = QVBoxLayout(dlg)
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(self.txt_teknik_log.toPlainText())
        v.addWidget(txt)
        btn = QPushButton("Kapat")
        btn.clicked.connect(dlg.accept)
        v.addWidget(btn)
        dlg.exec()

    # ------------------------------------------------------------------
    # REFERANS HAVUZU VE TAM PRESET/DSP METOTLARI
    # ------------------------------------------------------------------
    def _referans_havuzu_tablosunu_yenile(self) -> None:
        havuz = self.config_manager.voice_pool
        self.tablo_ses_havuzu.setRowCount(len(havuz))
        arapca_font = profesyonel_arapca_font_olustur(16)

        for r_idx, ses in enumerate(havuz):
            vid = ses.get("id", "")
            yol = self.config_manager.resolve_voice_path(vid)
            var_mi = yol.exists() and yol.stat().st_size > 1000

            self.tablo_ses_havuzu.setItem(r_idx, 0, QTableWidgetItem(vid))
            self.tablo_ses_havuzu.setItem(r_idx, 1, QTableWidgetItem(ses.get("ad", vid)))
            self.tablo_ses_havuzu.setItem(
                r_idx, 2, QTableWidgetItem(f"{ses.get('cinsiyet', 'E')} / {ses.get('kategori', '')}")
            )

            durum_it = QTableWidgetItem("✅ Hazır (24kHz)" if var_mi else "❌ Dosya Eksik")
            durum_it.setForeground(QColor("#10b981") if var_mi else QColor("#ef4444"))
            self.tablo_ses_havuzu.setItem(r_idx, 3, durum_it)

            metin_it = QTableWidgetItem(ses.get("ref_metin", ""))
            metin_it.setFont(arapca_font)
            metin_it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tablo_ses_havuzu.setItem(r_idx, 4, metin_it)

            btn_dinle = QPushButton("🔊 Dinle")
            btn_dinle.setEnabled(var_mi)
            btn_dinle.clicked.connect(lambda checked=False, p=str(yol): self.ses_dosyasini_cal(p))
            self.tablo_ses_havuzu.setCellWidget(r_idx, 5, btn_dinle)

    def _tum_referanslari_on_temizle(self) -> None:
        sayac = 0
        for ses in self.config_manager.voice_pool:
            yol = self.config_manager.resolve_voice_path(ses["id"])
            if yol.exists():
                try:
                    referans_sesi_on_temizle(yol)
                    sayac += 1
                except Exception as e:
                    self._teknik_log_ekle(f"⚠️ Ön-temizlik hatası ({yol.name}): {e}")
        self._referans_havuzu_tablosunu_yenile()
        QMessageBox.information(
            self,
            "24kHz Ön-Temizlik Tamamlandı",
            f"Toplam {sayac} referans ses dosyası doğal nefes ve vurguları korunarak 24kHz önbelleğe alındı.",
        )

    def _ozel_referans_ses_ekle_diyalogu(self) -> None:
        dlg = OzelReferansSesEkleDialog(self.config_manager, self.ses_oynatici, parent=self)
        if dlg.exec() == QDialog.Accepted and dlg.eklenen_kayit:
            self._referans_havuzu_tablosunu_yenile()
            self._referans_kombolarini_doldur()
            QMessageBox.information(
                self,
                "Özel Ses Eklendi",
                f"'{dlg.eklenen_kayit['ad']}' 24kHz PCM_16 WAV formatına dönüştürülerek tüm sekmelerdeki ses havuzuna eklendi.",
            )

    def _secili_ozel_sesi_sil(self) -> None:
        row = self.tablo_ses_havuzu.currentRow()
        if row < 0:
            return
        vid = self.tablo_ses_havuzu.item(row, 0).text() if self.tablo_ses_havuzu.item(row, 0) else ""
        if not self.config_manager.remove_custom_voice(vid):
            QMessageBox.warning(self, "Bilgi", "8 temel stüdyo referans sesi silinemez; yalnızca özel eklenen sesler silinebilir.")
            return
        self._referans_havuzu_tablosunu_yenile()
        self._referans_kombolarini_doldur()

    def _referans_tablo_metinlerini_kaydet(self) -> None:
        for r in range(self.tablo_ses_havuzu.rowCount()):
            vid = self.tablo_ses_havuzu.item(r, 0).text() if self.tablo_ses_havuzu.item(r, 0) else ""
            metin = self.tablo_ses_havuzu.item(r, 4).text() if self.tablo_ses_havuzu.item(r, 4) else ""
            if vid:
                self.config_manager.update_voice_prompt_text(vid, metin.strip())
        self._referans_havuzu_tablosunu_yenile()
        QMessageBox.information(self, "Kaydedildi", "Referans ses metinleri başarıyla güncellendi.")

    def _genel_cikti_klasoru_sec(self) -> None:
        secilen = QFileDialog.getExistingDirectory(self, "Varsayılan Çıktı Klasörü Seç", self.edt_genel_cikti_klasor.text())
        if secilen:
            self.edt_genel_cikti_klasor.setText(secilen)

    def _preset_ayarlari_forma_yukle(self) -> None:
        kod = self.cmb_preset_sec.currentData() or "cumle"
        p = self.config_manager.get_preset(kod)
        dsp = p.get("dsp", {})

        self.spn_p_hiz.setValue(float(p.get("hiz", 0.92)))
        self.spn_p_temp.setValue(float(p.get("temperature", 0.64)))
        self.spn_p_topk.setValue(int(p.get("top_k", 50)))
        self.spn_p_topp.setValue(float(p.get("top_p", 0.94)))
        self.spn_p_min_tok.setValue(int(p.get("min_tokens", 25)))
        self.spn_p_max_tok.setValue(int(p.get("max_tokens", 550)))

        idx_kt = self.cmb_p_kelime_turu.findText(str(p.get("kelime_turu", "genel")))
        if idx_kt >= 0:
            self.cmb_p_kelime_turu.setCurrentIndex(idx_kt)

        idx_fmt = self.cmb_p_format.findText(str(p.get("varsayilan_format", "wav")).lower())
        if idx_fmt >= 0:
            self.cmb_p_format.setCurrentIndex(idx_fmt)

        self.spn_p_birlesik_bosluk.setValue(int(p.get("birlesik_bosluk_ms", 350)))
        self.chk_p_cift.setChecked(bool(p.get("cift_uretim_erkek_kadin", True)))
        self.chk_p_hikmet.setChecked(bool(p.get("hikmetli_durak_ekle", False)))
        self.chk_p_dinamik.setChecked(bool(p.get("dinamik_tonlama", True)))

        self.spn_dsp_hp.setValue(float(dsp.get("hp_freq", 80.0)))
        self.spn_dsp_lp.setValue(float(dsp.get("lp_freq", 11200.0)))
        self.spn_dsp_gate.setValue(float(dsp.get("gate_esigi", 0.020)))
        self.spn_dsp_aktif_esik.setValue(float(dsp.get("aktif_esik_katsayi", 0.018)))
        self.spn_dsp_bas_pay.setValue(float(dsp.get("bas_pay_ms", 55.0)))
        self.spn_dsp_son_pay.setValue(float(dsp.get("son_pay_ms", 250.0)))
        self.spn_dsp_drive.setValue(float(dsp.get("drive", 1.06)))
        self.spn_dsp_fade.setValue(float(dsp.get("fade_ms", 12.0)))
        self.spn_dsp_tepe.setValue(float(dsp.get("tepe_normalizasyon", 0.891)))

    def _preset_ayarlarini_kaydet(self) -> None:
        kod = self.cmb_preset_sec.currentData() or "cumle"
        yeni = {
            "hiz": round(self.spn_p_hiz.value(), 2),
            "temperature": round(self.spn_p_temp.value(), 2),
            "top_k": int(self.spn_p_topk.value()),
            "top_p": round(self.spn_p_topp.value(), 2),
            "min_tokens": int(self.spn_p_min_tok.value()),
            "max_tokens": int(min(1200, max(self.spn_p_min_tok.value() + 20, self.spn_p_max_tok.value()))),
            "kelime_turu": self.cmb_p_kelime_turu.currentText(),
            "varsayilan_format": self.cmb_p_format.currentText(),
            "birlesik_bosluk_ms": int(self.spn_p_birlesik_bosluk.value()),
            "cift_uretim_erkek_kadin": self.chk_p_cift.isChecked(),
            "hikmetli_durak_ekle": self.chk_p_hikmet.isChecked(),
            "dinamik_tonlama": self.chk_p_dinamik.isChecked(),
            "dsp": {
                "hp_freq": round(self.spn_dsp_hp.value(), 1),
                "lp_freq": round(self.spn_dsp_lp.value(), 1),
                "gate_esigi": round(self.spn_dsp_gate.value(), 3),
                "aktif_esik_katsayi": round(self.spn_dsp_aktif_esik.value(), 3),
                "bas_pay_ms": round(self.spn_dsp_bas_pay.value(), 1),
                "son_pay_ms": round(self.spn_dsp_son_pay.value(), 1),
                "drive": round(self.spn_dsp_drive.value(), 2),
                "fade_ms": round(self.spn_dsp_fade.value(), 1),
                "tepe_normalizasyon": round(self.spn_dsp_tepe.value(), 3),
            },
        }
        self.config_manager.user_settings["varsayilan_cikti_klasoru"] = self.edt_genel_cikti_klasor.text().strip() or "cikti_sesler"
        self.config_manager.user_settings["otomatik_oynat_toplu_bitis"] = self.chk_toplu_bitis_oynat.isChecked()
        self.config_manager.save_user_preset(kod, yeni)

        if hasattr(self, "sekme_4_toplu"):
            self.sekme_4_toplu.edt_toplu_cikti.setText(str(self.config_manager.get_default_output_dir()))

        if self.cmb_tekli_mod.currentData() == kod:
            fmt = str(yeni["varsayilan_format"]).upper()
            idx_f = self.cmb_cikti_format.findText(fmt)
            if idx_f >= 0:
                self.cmb_cikti_format.setCurrentIndex(idx_f)
        self._tekli_tonlama_degisti()

        QMessageBox.information(
            self,
            "Kaydedildi ve Senkronize Edildi",
            f"'{kod}' modu için tüm akustik, DSP ve klasör ayarları kaydedildi ve 1. Sekmeye yansıtıldı.",
        )

    def _secili_preseti_sifirla(self) -> None:
        kod = self.cmb_preset_sec.currentData() or "cumle"
        self.config_manager.reset_preset_to_factory(kod)
        self._preset_ayarlari_forma_yukle()
        self._tekli_tonlama_degisti()
        QMessageBox.information(self, "Sıfırlandı", "Seçili mod fabrika ayarlarına döndürüldü.")

    def _tum_presetleri_sifirla(self) -> None:
        cevap = QMessageBox.question(
            self,
            "Tüm Modları Sıfırla",
            "5 içerik modunun tamamını varsayılan fabrika ayarlarına döndürmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if cevap == QMessageBox.Yes:
            self.config_manager.reset_all_to_factory()
            self._preset_ayarlari_forma_yukle()
            self._tekli_tonlama_degisti()
            QMessageBox.information(self, "Sıfırlandı", "Tüm modlar fabrika ayarlarına döndürüldü.")

    # ------------------------------------------------------------------
    # GÜVENLİ KAPATMA (closeEvent — Yetim QThread ve Çökme Korumalı)
    # ------------------------------------------------------------------
    def _iscileri_guvenli_durdur_ve_bekle(self, worker: Optional[QThread], bekleme_ms: int = 5000) -> bool:
        if worker is None:
            return True
        try:
            if not worker.isRunning():
                return True
            if hasattr(worker, "durdur"):
                worker.durdur()
            else:
                worker.quit()
            if not worker.wait(bekleme_ms):
                worker.terminate()
                worker.wait(800)
            return not worker.isRunning()
        except RuntimeError:
            return True

    def closeEvent(self, event: QCloseEvent) -> None:
        calisan_var = (
            (self.tekli_worker is not None and self.tekli_worker.isRunning())
            or (hasattr(self, "sekme_4_toplu") and self.sekme_4_toplu.batch_worker is not None and self.sekme_4_toplu.batch_worker.isRunning())
            or (hasattr(self, "sekme_5_diyalog") and self.sekme_5_diyalog.ozel_worker is not None and self.sekme_5_diyalog.ozel_worker.isRunning())
        )

        if calisan_var:
            cevap = QMessageBox.question(
                self,
                "Devam Eden Seslendirme İşlemi Var",
                "Şu anda arka planda devam eden bir seslendirme işlemi var.\n"
                "İşlemi güvenli şekilde durdurup uygulamadan çıkmak istiyor musunuz?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if cevap != QMessageBox.Yes:
                event.ignore()
                return

        self.ses_oynatici.durdur()

        if self.studyo_motor is not None:
            self.studyo_motor.durdur()

        toplu_w = self.sekme_4_toplu.batch_worker if hasattr(self, "sekme_4_toplu") else None
        ozel_w = self.sekme_5_diyalog.ozel_worker if hasattr(self, "sekme_5_diyalog") else None

        aday_isciler = [
            (self.tekli_worker, 5000),
            (toplu_w, 5000),
            (ozel_w, 5000),
            (self._guncelleme_worker, 1500),
        ] + [(w, 3000) for w in list(getattr(self, "_bekleyen_tekli_isciler", []))]

        sonuclar = [self._iscileri_guvenli_durdur_ve_bekle(w, sure) for w, sure in aday_isciler]
        hepsi_durdu = all(sonuclar)

        if hepsi_durdu and self.studyo_motor is not None:
            self.studyo_motor.bosalt()

        super().closeEvent(event)