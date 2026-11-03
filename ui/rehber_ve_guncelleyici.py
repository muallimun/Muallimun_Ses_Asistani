#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MUALLİMUN AI SES STÜDYOSU PRO - BAŞLANGIÇ TURU, KULLANIM KILAVUZU, GITHUB GÜNCELLEYİCİ VE TEMA MOTORU
Dosya: ui/rehber_ve_guncelleyici.py
Özellikler:
  1. Merkezi Aydınlık (Light) ve Karanlık (Dark) Stüdyo Teması QSS Üreticisi
  2. İlk Açılış 5 Adımlı Etkileşimli Başlangıç Turu + Canlı Sistem Sağlığı Denetim Kartı
  3. 6 Sekmeli Kapsamlı Tanıtım Rehberi ve Kullanım Kılavuzu (+ HTML Olarak Dışa Aktarma)
  4. GitHub Üzerinden Arka Planda Otomatik Yeni Versiyon Kontrolü (version.json & Releases API)
"""

import os
import re
import json
import shutil
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QFont, QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QTabWidget,
    QTextBrowser,
    QStackedWidget,
    QFrame,
    QLineEdit,
    QFileDialog,
    QMessageBox,
)

from core.config_manager import ConfigManager, PROJECT_ROOT
from core.studyo_motoru import gpu_vram_durumu_getir

APP_VERSION = "1.2.0"


# ==============================================================================
# 1. MERKEZİ AYDINLIK / KARANLIK STÜDYO TEMASI (QSS) ÜRETİCİSİ
# ==============================================================================
def studyo_tema_qss_olustur(tema_kodu: str = "koyu") -> str:
    """
    'koyu' (Gece Mavisi Profesyonel Stüdyo) ve 'aydinlik' (Göz Yormayan Fildişi/Kitap Kağıdı)
    temaları için yüksek kontrastlı, erişilebilir merkezi QSS üretir.
    """
    if tema_kodu == "aydinlik":
        return """
            QMainWindow, QDialog, QWidget {
                background-color: #f1f5f9;
                color: #0f172a;
                font-family: 'Segoe UI';
                font-size: 9.5pt;
            }
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
                color: #0369a1;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #0284c7;
            }
            QTabWidget::pane {
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #e2e8f0;
                color: #475569;
                border: 1px solid #cbd5e1;
                padding: 8px 16px;
                margin-right: 4px;
                border-top-left-radius: 7px;
                border-top-right-radius: 7px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #0284c7;
                border-top: 3px solid #0284c7;
            }
            QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #94a3b8;
                border-radius: 6px;
                padding: 4px 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #0f172a;
                selection-background-color: #0284c7;
                selection-color: #ffffff;
            }
            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f8fafc;
                color: #0f172a;
                gridline-color: #cbd5e1;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #e2e8f0;
                color: #0f172a;
                padding: 6px;
                border: 1px solid #cbd5e1;
                font-weight: bold;
            }
            QPushButton {
                background-color: #e2e8f0;
                color: #0f172a;
                border: 1px solid #94a3b8;
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #cbd5e1;
            }
            QPushButton:disabled {
                background-color: #e2e8f0;
                color: #94a3b8;
                border-color: #cbd5e1;
            }
            QCheckBox {
                spacing: 6px;
                color: #0f172a;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #0284c7;
                background-color: #ffffff;
            }
            QCheckBox::indicator:checked {
                background-color: #10b981;
                border-color: #059669;
            }
            QProgressBar {
                border: 1px solid #94a3b8;
                border-radius: 6px;
                text-align: center;
                background-color: #e2e8f0;
                color: #0f172a;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 5px;
            }
            QToolTip {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #0284c7;
                padding: 6px;
                border-radius: 5px;
            }
            QMenu {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #94a3b8;
                padding: 4px;
            }
            QMenu::item:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
        """

    # Varsayılan: Koyu Stüdyo Teması
    return """
        QMainWindow, QDialog, QWidget {
            background-color: #0b0f19;
            color: #f8fafc;
            font-family: 'Segoe UI';
            font-size: 9.5pt;
        }
        QGroupBox {
            background-color: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
            color: #38bdf8;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: #38bdf8;
        }
        QTabWidget::pane {
            border: 1px solid #1e293b;
            border-radius: 8px;
            background-color: #0f172a;
        }
        QTabBar::tab {
            background-color: #111827;
            color: #94a3b8;
            border: 1px solid #1e293b;
            padding: 8px 16px;
            margin-right: 4px;
            border-top-left-radius: 7px;
            border-top-right-radius: 7px;
            font-weight: bold;
        }
        QTabBar::tab:selected {
            background-color: #0f172a;
            color: #38bdf8;
            border-top: 3px solid #0ea5e9;
        }
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background-color: #090d16;
            color: #f8fafc;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 4px 8px;
        }
        QComboBox QAbstractItemView {
            background-color: #0f172a;
            color: #f8fafc;
            selection-background-color: #0284c7;
            selection-color: #ffffff;
        }
        QTableWidget {
            background-color: #090d16;
            alternate-background-color: #0f172a;
            color: #f8fafc;
            gridline-color: #1e293b;
            border: 1px solid #1e293b;
            border-radius: 6px;
        }
        QHeaderView::section {
            background-color: #111827;
            color: #38bdf8;
            padding: 6px;
            border: 1px solid #1e293b;
            font-weight: bold;
        }
        QPushButton {
            background-color: #1e293b;
            color: #f8fafc;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 5px 12px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #334155;
        }
        QPushButton:disabled {
            background-color: #0f172a;
            color: #475569;
            border-color: #1e293b;
        }
        QCheckBox {
            spacing: 6px;
            color: #e2e8f0;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 2px solid #38bdf8;
            background-color: #090d16;
        }
        QCheckBox::indicator:checked {
            background-color: #10b981;
            border-color: #34d399;
        }
        QProgressBar {
            border: 1px solid #334155;
            border-radius: 6px;
            text-align: center;
            background-color: #090d16;
            color: #f8fafc;
            font-weight: bold;
        }
        QProgressBar::chunk {
            background-color: #10b981;
            border-radius: 5px;
        }
        QToolTip {
            background-color: #0f172a;
            color: #f8fafc;
            border: 1px solid #38bdf8;
            padding: 6px;
            border-radius: 5px;
        }
        QMenu {
            background-color: #0f172a;
            color: #f8fafc;
            border: 1px solid #38bdf8;
            padding: 4px;
        }
        QMenu::item:selected {
            background-color: #0284c7;
            color: #ffffff;
        }
    """


# ==============================================================================
# 2. İLK AÇILIŞ ADIM ADIM BAŞLANGIÇ TURU VE SİSTEM SAĞLIĞI SİHİRBAZI
# ==============================================================================
class BaslangicTuruDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("🎓 Muallimun AI Ses Stüdyosu Pro — Adım Adım Başlangıç Turu ve Sistem Hazırlığı")
        self.setMinimumSize(820, 540)
        self.resize(880, 580)

        tema = self.config_manager.user_settings.get("tema_modu", "koyu")
        self.setStyleSheet(studyo_tema_qss_olustur(tema))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Üst Başlık ve Adım Göstergesi
        ust_bar = QHBoxLayout()
        self.lbl_baslik = QLabel("🎓 Hoş Geldiniz — 5 Adımda Stüdyo Başlangıç Turu")
        self.lbl_baslik.setStyleSheet("font-size: 13pt; font-weight: bold; color: #10b981;")
        ust_bar.addWidget(self.lbl_baslik)
        ust_bar.addStretch()

        self.lbl_adim_sayac = QLabel("Adım 1 / 5")
        self.lbl_adim_sayac.setStyleSheet(
            "background-color: #0284c7; color: white; padding: 4px 12px; border-radius: 12px; font-weight: bold;"
        )
        ust_bar.addWidget(self.lbl_adim_sayac)
        layout.addLayout(ust_bar)

        self.stack = QStackedWidget()
        self._sayfalari_olustur()
        layout.addWidget(self.stack, stretch=1)

        # Alt Gezinme Çubuğu
        alt_bar = QHBoxLayout()
        self.chk_bir_daha_gosterme = QCheckBox("Açılışta bu başlangıç turunu bir daha otomatik gösterme")
        self.chk_bir_daha_gosterme.setChecked(True)
        alt_bar.addWidget(self.chk_bir_daha_gosterme)
        alt_bar.addStretch()

        self.btn_geri = QPushButton("⬅️ Önceki Adım")
        self.btn_geri.setFixedHeight(34)
        self.btn_geri.clicked.connect(self._onceki_adim)
        alt_bar.addWidget(self.btn_geri)

        self.btn_ileri = QPushButton("Sonraki Adım ➡️")
        self.btn_ileri.setFixedHeight(34)
        self.btn_ileri.setStyleSheet("background-color: #0284c7; color: white; padding: 6px 16px; font-weight: bold;")
        self.btn_ileri.clicked.connect(self._sonraki_adim)
        alt_bar.addWidget(self.btn_ileri)

        self.btn_bitir = QPushButton("🚀 Stüdyoyu Kullanmaya Başla")
        self.btn_bitir.setFixedHeight(34)
        self.btn_bitir.setStyleSheet("background-color: #059669; color: white; padding: 6px 18px; font-weight: bold;")
        self.btn_bitir.clicked.connect(self._turu_tamamla)
        alt_bar.addWidget(self.btn_bitir)

        layout.addLayout(alt_bar)
        self._buton_durumlarini_guncelle()

    def _sistem_sagligi_html_uret(self) -> str:
        gpu_bilgi = gpu_vram_durumu_getir()
        ffmpeg_var = bool(shutil.which("ffmpeg"))
        mevcut_ref = sum(
            1 for s in self.config_manager.voice_pool
            if self.config_manager.resolve_voice_path(s["id"]).exists()
        )
        toplam_ref = len(self.config_manager.voice_pool)

        gpu_durum = (
            f"<span style='color:#10b981; font-weight:bold;'>✅ Aktif ({gpu_bilgi['cihaz_adi']} — Boş VRAM: {gpu_bilgi.get('bos_gb', 0)}/{gpu_bilgi.get('toplam_gb', 0)} GB)</span>"
            if gpu_bilgi["aktif"]
            else "<span style='color:#f59e0b; font-weight:bold;'>💻 CPU Modu (Harici CUDA GPU Bulunamadı)</span>"
        )
        ffmpeg_durum = (
            "<span style='color:#10b981; font-weight:bold;'>✅ Kurulu (192kbps MP3, Limiter ve Hız Ayarı Hazır)</span>"
            if ffmpeg_var
            else "<span style='color:#ef4444; font-weight:bold;'>⚠️ Eksik (Yalnızca WAV üretilebilir; MP3 için Modeller & Kurulum'dan FFmpeg kurun)</span>"
        )
        ref_durum = (
            f"<span style='color:#10b981; font-weight:bold;'>✅ {mevcut_ref} / {toplam_ref} Referans Ses Dosyası Hazır</span>"
            if mevcut_ref >= 8
            else f"<span style='color:#f59e0b; font-weight:bold;'>⚠️ {mevcut_ref} / {toplam_ref} Referans Ses Bulundu</span>"
        )

        return f"""
        <div style='line-height: 1.55; font-size: 10.5pt;'>
            <h3 style='color:#0284c7; margin-bottom:6px;'>🩺 Adım 1: Canlı Sistem Sağlığı ve Donanım Kontrolü</h3>
            <p><b>Muallimun AI Ses Stüdyosu Pro</b>, Arapça eğitim materyallerini (sözlük kelimeleri, gramer cümleleri, atasözleri,
            çoklu karakter diyalogları ve okuma metinlerini) vakıf/vasıl kurallarına uygun olarak seslendirmek için tasarlanmıştır.</p>
            <table width='100%' cellpadding='8' cellspacing='0' style='border: 1px solid #334155; border-radius: 6px; margin-top: 8px;'>
                <tr>
                    <td width='32%'><b>🚀 Grafik İşlemci (GPU / VRAM):</b></td>
                    <td>{gpu_durum}</td>
                </tr>
                <tr>
                    <td><b>⚙️ Önerilen Çalışma Kademesi:</b></td>
                    <td><span style='color:#38bdf8; font-weight:bold;'>{gpu_bilgi['profil_detay']['ad']}</span></td>
                </tr>
                <tr>
                    <td><b>🎞️ FFmpeg Ses Motoru:</b></td>
                    <td>{ffmpeg_durum}</td>
                </tr>
                <tr>
                    <td><b>🎙️ Stüdyo Referans Ses Havuzu:</b></td>
                    <td>{ref_durum}</td>
                </tr>
                <tr>
                    <td><b>⭐ Varsayılan Ana Ses Motoru:</b></td>
                    <td><span style='color:#10b981; font-weight:bold;'>IbrahimSalah/Arabic-TTS-Spark (24kHz BiCodec Klonlama)</span></td>
                </tr>
            </table>
            <p style='margin-top:10px;'>💡 <b>İpucu:</b> Üst bardaki <b>☀️ Aydınlık / 🌙 Koyu</b> butonuyla istediğiniz zaman göz konforunuza uygun temaya geçebilirsiniz.</p>
        </div>
        """

    def _sayfa_widget_olustur(self, html_icerik: str) -> QWidget:
        sayfa = QWidget()
        v = QVBoxLayout(sayfa)
        v.setContentsMargins(4, 4, 4, 4)
        tarayici = QTextBrowser()
        tarayici.setOpenExternalLinks(True)
        tarayici.setHtml(html_icerik)
        v.addWidget(tarayici)
        return sayfa

    def _sayfalari_olustur(self) -> None:
        # Sayfa 1: Sistem Sağlığı
        self.stack.addWidget(self._sayfa_widget_olustur(self._sistem_sagligi_html_uret()))

        # Sayfa 2: Ses Motoru Seçimi Rehberi
        sayfa2_html = """
        <div style='line-height: 1.6; font-size: 10.5pt;'>
            <h3 style='color:#0284c7;'>🧠 Adım 2: Hangi Ses Motorunu Ne Zaman Kullanmalıyım?</h3>
            <p>Uygulamada farklı ihtiyaçlara göre <b>3 seslendirme motoru</b> bulunur:</p>
            <ul>
                <li><b style='color:#10b981;'>1. ⭐ Spark-TTS (24kHz BiCodec — Önerilen Ana Stüdyo Motoru):</b><br>
                Tam harekeli Arapça metinlerde <b>en yüksek mahreç, hareke ve ses klonlama kalitesini</b> sunar.
                8 stüdyo sesini (Yetişkin Erkek/Kadın, Çocuk Erkek/Kız) veya kendi eklediğiniz sesi birebir klonlar.
                Model bir kez indirildikten sonra <b>tamamen çevrimdışı (internetsiz)</b> çalışır.</li>
                <br>
                <li><b style='color:#38bdf8;'>2. ⚡ Hızlı Direkt Neural TTS (Çevrimiçi Hazır Ses + 24kHz DSP):</b><br>
                İnternet bağlantısı üzerinden hazır Arapça neural sesleri kullanır. Ekran kartı belleği (VRAM) harcamaz,
                ~1 saniyede hızlı ön-izleme yapar ve harekesiz metinleri de okuyabilir. <i>(Referans WAV dosyasını klonlamaz).</i></li>
                <br>
                <li><b style='color:#f59e0b;'>3. 🗣️ Coqui XTTS v2 (Alternatif Çok Dilli Motor):</b><br>
                Genel amaçlı çok dilli bir modeldir. Arapça hareke hassasiyeti ve ses doğallığı <b>Spark-TTS kadar yüksek değildir</b>;
                yalnızca alternatif/deneysel amaçla sunulmuştur.</li>
            </ul>
        </div>
        """
        self.stack.addWidget(self._sayfa_widget_olustur(sayfa2_html))

        # Sayfa 3: Tekli Stüdyo ve Vakıf Kuralları
        sayfa3_html = """
        <div style='line-height: 1.6; font-size: 10.5pt;'>
            <h3 style='color:#0284c7;'>🎙️ Adım 3: Tekli Seslendirme Stüdyosu ve Canlı Vakıflı Okunuş</h3>
            <p><b>1. Seslendirme Stüdyosu</b> sekmesinde tek bir kelime, cümle veya atasözünü anında sentezleyebilirsiniz:</p>
            <ol>
                <li><b>İçerik Türü ve Tonlama Seçin:</b> Tek Kelime, Cümle veya Atasözü modlarından birini seçtiğinizde hız ve DSP ayarları otomatik hazırlanır.</li>
                <li><b>Arapça Metni Girin:</b> Hızlı Hareke Klavyesi ile eksik harekeleri tamamlayabilirsiniz.</li>
                <li><b>🔍 Canlı Vakıflı Okunuş Kutusu:</b> Stüdyo motoru Arapça imla kurallarına göre cümle sonundaki
                <i>tâ-i merbûtayı (ة -> هْ)</i>, <i>fetha tenvini (ـًا -> ـَا)</i> ve <i>son harekeyi sükûna</i> otomatik dönüştürür.
                Dilerseniz yeşil kutudaki okunuş metnini elle de düzenleyebilirsiniz.</li>
                <li><b>Teknik Ses Kontrolü (QA):</b> Üretilen sesin süresi, tepe seviyesi (dBFS) ve sinyal enerjisi dalga formu üzerinde otomatik denetlenir.</li>
            </ol>
        </div>
        """
        self.stack.addWidget(self._sayfa_widget_olustur(sayfa3_html))

        # Sayfa 4: Toplu Seslendirme ve Seçmeli Satır Üretimi
        sayfa4_html = """
        <div style='line-height: 1.6; font-size: 10.5pt;'>
            <h3 style='color:#0284c7;'>📦 Adım 4: Toplu Seslendirme ve Seçmeli Satır / Aralık Üretimi</h3>
            <p><b>4. Toplu Seslendirme</b> sekmesi yüzlerce kelimelik sözlükleri veya cümle listelerini otomatik üretir:</p>
            <ul>
                <li><b>📥 Hazır Şablon İndirin:</b> Excel (<code>.xlsx</code>), JSON, CSV veya TXT formatında örnek şablon indirip kendi listenizi hazırlayabilirsiniz.</li>
                <li><b>☑️ Seçmeli Satır Seç & Üret:</b> Binlerce satırlık bir dosyada tüm listeyi beklemek yerine,
                <b>Seçmeli Satır Seç & Üret</b> butonuna tıklayarak arama yapabilir, tek tek satırları işaretleyebilir veya
                <b>Belirli Satır Aralığını (Örn: 1 - 50)</b> seçerek yalnızca o kısmı üretebilirsiniz.</li>
                <li><b>🔍 Kuyruk Filtresi ve Canlı Vurgu:</b> Seslendirme sırasında o an okunan satır ekranda parlak renkle vurgulanır.
                Üstteki filtreyle sadece seçilenleri veya sadece hatalı satırları listeleyebilirsiniz.</li>
                <li><b>⏭️ Akıllı Checkpoint v2:</b> İşlem durdurulsa bile daha önce üretilmiş sağlam dosyalar atlanarak kaldığı yerden devam edilir.</li>
            </ul>
        </div>
        """
        self.stack.addWidget(self._sayfa_widget_olustur(sayfa4_html))

        # Sayfa 5: Çoklu Rol Diyalog ve Uzun Metin Stüdyosu
        sayfa5_html = """
        <div style='line-height: 1.6; font-size: 10.5pt;'>
            <h3 style='color:#0284c7;'>🎭 Adım 5: Çoklu Rol Diyalog (8 Karakter) ve Uzun Metin Stüdyosu</h3>
            <p><b>5. Diyalog & Uzun Metin</b> sekmesi ders kitaplarındaki karşılıklı konuşmaları ve okuma parçalarını üretir:</p>
            <ul>
                <li><b>🎲 8 Sesten Otomatik Rol Ata:</b> Diyalogdaki konuşmacıların isimlerine (Öğretmen, Anne, Baba, Çocuk vb.) ve cinsiyetlerine göre
                çakışmasız ses karakteri dağıtır. Butona her bastığınızda yeni bir ses kombinasyonu oluşturulur.</li>
                <li><b>📚 Çoklu Seç & Üret (Ayrı Klasörlerde Dosyalama):</b> Çoklu diyalog JSON dosyası yüklediğinizde tüm diyalogları veya
                seçtiğiniz bir kısmını tek seferde seslendirebilirsiniz. Her diyalog kendi klasöründe (<code>cikti_sesler/diyaloglar/dlg_001/</code>)
                hem satır satır hem de birleştirilmiş <code>diyalog_tamami.mp3</code> olarak kaydedilir.</li>
                <li><b>📖 Uzun Metin Bölücü:</b> Uzun Arapça paragrafları harf-i cer ve edatları satır sonunda tek bırakmadan doğal cümlelere böler
                ve nefes aralıklarıyla tek bir <code>tamami.mp3</code> dosyasında birleştirir.</li>
            </ul>
        </div>
        """
        self.stack.addWidget(self._sayfa_widget_olustur(sayfa5_html))

    def _onceki_adim(self) -> None:
        idx = self.stack.currentIndex()
        if idx > 0:
            self.stack.setCurrentIndex(idx - 1)
            self._buton_durumlarini_guncelle()

    def _sonraki_adim(self) -> None:
        idx = self.stack.currentIndex()
        if idx < self.stack.count() - 1:
            self.stack.setCurrentIndex(idx + 1)
            self._buton_durumlarini_guncelle()

    def _buton_durumlarini_guncelle(self) -> None:
        idx = self.stack.currentIndex()
        toplam = self.stack.count()
        self.lbl_adim_sayac.setText(f"Adım {idx + 1} / {toplam}")
        self.btn_geri.setEnabled(idx > 0)
        self.btn_ileri.setVisible(idx < toplam - 1)
        self.btn_bitir.setVisible(idx == toplam - 1)

    def _turu_tamamla(self) -> None:
        self.config_manager.user_settings["ilk_acilis_turu_gosterildi"] = self.chk_bir_daha_gosterme.isChecked()
        self.config_manager.save_user_settings()
        self.accept()


# ==============================================================================
# 3. KAPSAMLI TANITIM REHBERİ VE KULLANIM KILAVUZU PENCERESİ
# ==============================================================================
class KullanimKilavuzuDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("📘 Muallimun AI Ses Stüdyosu Pro — Kapsamlı Tanıtım Rehberi ve Kullanım Kılavuzu")
        self.setMinimumSize(940, 620)
        self.resize(1040, 680)

        tema = self.config_manager.user_settings.get("tema_modu", "koyu")
        self.setStyleSheet(studyo_tema_qss_olustur(tema))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        ust = QHBoxLayout()
        lbl = QLabel("📘 MUALLİMUN AI SES STÜDYOSU PRO — KULLANIM KILAVUZU VE TEKNİK REHBER")
        lbl.setStyleSheet("font-size: 12pt; font-weight: bold; color: #0284c7;")
        ust.addWidget(lbl)
        ust.addStretch()

        btn_tur_ac = QPushButton("🎓 5 Adımlı Başlangıç Turunu Aç")
        btn_tur_ac.clicked.connect(self._baslangic_turunu_ac)
        ust.addWidget(btn_tur_ac)

        btn_disa_aktar = QPushButton("💾 Kılavuzu HTML Olarak Kaydet")
        btn_disa_aktar.setStyleSheet("background-color: #059669; color: white;")
        btn_disa_aktar.clicked.connect(self._kilavuzu_html_kaydet)
        ust.addWidget(btn_disa_aktar)
        layout.addLayout(ust)

        self.tabs = QTabWidget()
        self._sekmeleri_hazirla()
        layout.addWidget(self.tabs, stretch=1)

        alt = QHBoxLayout()
        alt.addWidget(QLabel(f"Sürüm: v{APP_VERSION} • Muallimun Dijital Eğitim Teknolojileri (muallimun.net)"))
        alt.addStretch()
        btn_kapat = QPushButton("Kapat")
        btn_kapat.setFixedWidth(110)
        btn_kapat.clicked.connect(self.accept)
        alt.addWidget(btn_kapat)
        layout.addLayout(alt)

    def _baslangic_turunu_ac(self) -> None:
        dlg = BaslangicTuruDialog(self.config_manager, parent=self)
        dlg.exec()

    def _sekme_ekle(self, baslik: str, html: str) -> None:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(6, 6, 6, 6)
        b = QTextBrowser()
        b.setOpenExternalLinks(True)
        b.setHtml(html)
        v.addWidget(b)
        self.tabs.addTab(w, baslik)

    def _sekmeleri_hazirla(self) -> None:
        self._sekme_ekle(
            "1. 🌟 Genel Bakış & Modeller",
            """
            <div style='line-height:1.6; font-size:10pt;'>
                <h2 style='color:#0284c7;'>Muallimun AI Ses Stüdyosu Pro Nedir?</h2>
                <p>Arapça ders kitapları, dijital sözlükler, etkileşimli flipbook'lar ve e-öğrenme portalları için
                <b>24kHz stüdyo kalitesinde, hareke ve vakıf/vasıl kurallarına duyarlı</b> yapay zeka dublaj ve seslendirme stüdyosudur.</p>
                <h3>Desteklenen Seslendirme Motorları</h3>
                <ol>
                    <li><b>⭐ Spark-TTS (IbrahimSalah/Arabic-TTS-Spark — Önerilen Ana Motor):</b>
                    24kHz BiCodec mimarisiyle referans sesi ve Arapça referans metni işleyerek konuşmacıyı klonlar.
                    Tam harekeli eğitim materyallerinde en yüksek telaffuz doğruluğunu verir. Yerel GPU veya CPU'da çevrimdışı çalışır.</li>
                    <li><b>⚡ Hızlı Direkt Neural TTS (Edge Neural + 5-Katmanlı DSP):</b>
                    İnternet üzerinden hazır Arapça neural sesleri kullanır. VRAM tüketmez, hızlı ön-izleme ve harekesiz metinler için idealdir.</li>
                    <li><b>🗣️ Coqui XTTS v2 (Alternatif Motor):</b>
                    Genel amaçlı çok dilli modeldir. Arapça ses doğallığı Spark-TTS kadar yüksek olmadığı için yalnızca alternatif olarak tutulmuştur.</li>
                </ol>
            </div>
            """,
        )

        self._sekme_ekle(
            "2. 🕌 Arapça Vakıf & Fonetik",
            """
            <div style='line-height:1.6; font-size:10pt;'>
                <h2 style='color:#0284c7;'>Fasih Arapça Vakıf ve Vasıl Ön-İşleme Motoru</h2>
                <p>Arapça metinler seslendirilirken cümle ortasında <b>vasıl (i'rab harekesini koruma)</b>,
                durak ve cümle sonlarında ise <b>vakıf (sükûn / med üzerinde durma)</b> uygulanır:</p>
                <ul>
                    <li><b>Tâ-i Merbûta Dönüşümü:</b> Cümle veya durak sonundaki <code>مَدْرَسَةٌ</code> kelimesi vakıf halinde <code>مَدْرَسَهْ</code> olarak okunur.</li>
                    <li><b>Tenvin-i Fetha (Medd-i İvaz):</b> <code>كِتَابًا</code> kelimesi durakta <code>كِتَابَا</code> şeklinde elif meddiyle okunur.</li>
                    <li><b>Son Hareke Sükûnu:</b> İsim ve cümle sonlarındaki harekeler durakta sükûna (<code>ـْ</code>) çevrilir; tekil fiil modunda ise bina harekesi korunur.</li>
                    <li><b>Bölünmez Arapça Edat Koruması:</b> Uzun paragraflar bölünürken <code>فِي، مِنْ، إِلَى، عَلَى، أَنْ، لَا</code> gibi harf-i cer ve edatlar
                    hem harekeli hem harekesiz metinlerde satır sonunda tek başına bırakılmaz.</li>
                </ul>
            </div>
            """,
        )

        self._sekme_ekle(
            "3. 📦 Toplu Üretim & Şablonlar",
            """
            <div style='line-height:1.6; font-size:10pt;'>
                <h2 style='color:#0284c7;'>Toplu Seslendirme, Seçmeli Kuyruk ve Şablon Formatları</h2>
                <p><b>4. Toplu Seslendirme</b> sekmesinde Excel (<code>.xlsx</code>), JSON, CSV veya TXT dosyalarını yükleyebilirsiniz:</p>
                <ul>
                    <li><b>Ses Seçimi Kodları (<code>ses_secimi</code> sütunu):</b>
                        <ul>
                            <li><code>IKISI</code> : Hem Erkek hem Kadın sesiyle çift üretim yapar (<code>erkek/</code> ve <code>kadin/</code> klasörlerine).</li>
                            <li><code>E1</code>, <code>E2</code> : Yetişkin Erkek 1 ve 2</li>
                            <li><code>K1</code>, <code>K2</code> : Yetişkin Kadın 1 ve 2</li>
                            <li><code>EC1</code>, <code>EC2</code> : Erkek Çocuk / Genç 1 ve 2</li>
                            <li><code>KC1</code>, <code>KC2</code> : Kız Çocuk / Genç 1 ve 2</li>
                            <li><code>DIREKT</code> : Çevrimiçi Hızlı Direkt TTS</li>
                        </ul>
                    </li>
                    <li><b>☑️ Seçmeli Satır Seç & Üret:</b> Büyük listelerde istediğiniz satırları veya <b>1 - 50</b> gibi belirli bir aralığı seçerek üretebilirsiniz.</li>
                    <li><b>⏭️ İçerik-Adresli Checkpoint v2:</b> Metin, ses karakteri veya motor değiştiğinde bunu algılar; değişmeyen ve diskte sağlam duran dosyaları atlar.</li>
                </ul>
            </div>
            """,
        )

        self._sekme_ekle(
            "4. 🎭 Diyalog & Uzun Metin",
            """
            <div style='line-height:1.6; font-size:10pt;'>
                <h2 style='color:#0284c7;'>Çoklu Rol Diyalog (8 Karakter) ve Uzun Metin Stüdyosu</h2>
                <ul>
                    <li><b>🎲 8 Sesten Otomatik Rol Ata:</b> Konuşmacıların adlarına ve cinsiyetlerine göre çakışmasız rol dağıtır.
                    Her tıklamada farklı bir ses kombinasyonu (rotasyon) uygular.</li>
                    <li><b>📚 Çoklu Seç & Üret:</b> JSON dosyasındaki tüm diyalogları veya seçtiklerinizi sırayla seslendirir;
                    her diyaloğu kendi ID klasöründe (<code>cikti_sesler/diyaloglar/&lt;diyalog_id&gt;/</code>) hem satır satır hem de
                    <code>diyalog_tamami.mp3</code> olarak birleştirilmiş halde kaydeder.</li>
                    <li><b>✖️ Kaynağı Kaldır:</b> Yüklediğiniz JSON veya metin dosyasını arayüzden temizlemek istediğinizde tek tıkla sıfırlar.</li>
                </ul>
            </div>
            """,
        )

        self._sekme_ekle(
            "5. 🎚️ DSP Mastering & Teknik QA",
            """
            <div style='line-height:1.6; font-size:10pt;'>
                <h2 style='color:#0284c7;'>5-Katmanlı Stüdyo DSP Mastering ve Teknik Ses Kontrolü</h2>
                <ol>
                    <li><b>DC Offset & Butterworth Filtre (80Hz HP / 11.2kHz LP):</b> Dip uğultularını ve tiz metalik parazitleri temizler.</li>
                    <li><b>Yumuşak RMS Gürültü Kapısı (Noise Gate):</b> Kelime sonundaki hafif Arapça harfleri (<code>ه، ح، ث، س</code>) yutmadan nefes aralarını temizler.</li>
                    <li><b>Aktif Konuşma Kırpma (Trim & Pad):</b> Başta ve sonda dengeli stüdyo boşluğu bırakır.</li>
                    <li><b>Algısal Ses Yüksekliği (Loudness) & True-Peak Limiter:</b> Birleştirilen diyaloglarda konuşmacıların ses seviyelerini dengeler ve MP3 kırpılmasını (clipping) önler.</li>
                    <li><b>Teknik Ses Kontrolü (QA):</b> Dalga formu üzerinde sesin süresini, tepe dBFS değerini ve sessizlik/enerji durumunu denetler.</li>
                </ol>
            </div>
            """,
        )

        self._sekme_ekle(
            "6. ⌨️ Kısayollar & Sorun Giderme",
            """
            <div style='line-height:1.6; font-size:10pt;'>
                <h2 style='color:#0284c7;'>Klavye Kısayolları ve Sık Karşılaşılan Sorunlar</h2>
                <table width='100%' cellpadding='6' cellspacing='0' style='border:1px solid #334155;'>
                    <tr><td><b>Ctrl + Enter</b></td><td>Tekli Stüdyoda metni anında seslendirir</td></tr>
                    <tr><td><b>Esc</b></td><td>Aktif seslendirme işlemini güvenli şekilde durdurur</td></tr>
                    <tr><td><b>F1</b></td><td>Kullanım Kılavuzunu açar</td></tr>
                </table>
                <h3>Sık Sorulan Sorular</h3>
                <ul>
                    <li><b>4 GB VRAM ekran kartında bellek dolar mı?</b><br>
                    Hayır. Motorlar arası geçişte pasif model GPU'dan otomatik silinir ve Kademe 3 (Hafif Laptop Modu) BiCodec önbelleğini dinamik yönetir.</li>
                    <li><b>MP3 üretimi neden FFmpeg ister?</b><br>
                    Gerçek 192kbps MP3 kodlaması ve true-peak limiter için FFmpeg kullanılır. FFmpeg yoksa sahte MP3 yazılmaz, WAV formatı kullanılır.</li>
                </ul>
            </div>
            """,
        )

    def _kilavuzu_html_kaydet(self) -> None:
        hedef, _ = QFileDialog.getSaveFileName(
            self,
            "Kullanım Kılavuzunu HTML Olarak Kaydet",
            str(Path.home() / "Desktop" / "Muallimun_Studyo_Pro_Kullanim_Kilavuzu.html"),
            "HTML Belgesi (*.html)",
        )
        if not hedef:
            return
        try:
            parcalar = [
                "<!DOCTYPE html><html lang='tr'><head><meta charset='utf-8'>",
                "<title>Muallimun AI Ses Stüdyosu Pro — Kullanım Kılavuzu</title>",
                "<style>body{font-family:'Segoe UI',sans-serif;max-width:920px;margin:30px auto;padding:20px;background:#0f172a;color:#f8fafc;line-height:1.6;}",
                "h1,h2,h3{color:#38bdf8;} .bolum{background:#111827;border:1px solid #1e293b;border-radius:8px;padding:18px;margin-bottom:20px;}</style></head><body>",
                f"<h1>🎙️ Muallimun AI Ses Stüdyosu Pro (v{APP_VERSION}) — Kapsamlı Kullanım Kılavuzu</h1>",
            ]
            for i in range(self.tabs.count()):
                baslik = self.tabs.tabText(i)
                sayfa = self.tabs.widget(i)
                tarayici = sayfa.findChild(QTextBrowser)
                icerik = tarayici.toHtml() if tarayici else ""
                parcalar.append(f"<div class='bolum'><h2>{baslik}</h2>{icerik}</div>")
            parcalar.append("</body></html>")
            with open(hedef, "w", encoding="utf-8") as f:
                f.write("\n".join(parcalar))
            QMessageBox.information(self, "Kılavuz Kaydedildi", f"Kullanım kılavuzu başarıyla kaydedildi:\n{hedef}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kılavuz kaydedilemedi:\n{e}")


# ==============================================================================
# 4. GITHUB YENİ VERSİYON VE GÜNCELLEME KONTROLÜ (ARKA PLAN QTHREAD + DİYALOG)
# ==============================================================================
def _surum_tuple_cevir(surum_str: str) -> Tuple[int, ...]:
    rakamlar = re.findall(r"\d+", str(surum_str or "0.0.0"))
    return tuple(int(x) for x in rakamlar[:4]) if rakamlar else (0, 0, 0)


class GitHubGuncellemeKontrolWorker(QThread):
    sonuc_sinyali = Signal(bool, dict)

    def __init__(self, github_repo: str, mevcut_surum: str = APP_VERSION):
        super().__init__()
        self.github_repo = str(github_repo or "muallimun/Muallimun_Ses_Asistani").strip().strip("/")
        self.mevcut_surum = mevcut_surum

    def run(self) -> None:
        headers = {
            "User-Agent": f"MuallimunStudyoPro/{self.mevcut_surum}",
            "Accept": "application/vnd.github.v3+json",
        }
        # 1. Önce repodaki version.json dosyasını kontrol et
        raw_url = f"https://raw.githubusercontent.com/{self.github_repo}/main/version.json"
        api_url = f"https://api.github.com/repos/{self.github_repo}/releases/latest"

        try:
            req = urllib.request.Request(raw_url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                veri = json.loads(resp.read().decode("utf-8"))
                uzak_surum = str(veri.get("version", self.mevcut_surum)).lstrip("vV")
                yeni_var = _surum_tuple_cevir(uzak_surum) > _surum_tuple_cevir(self.mevcut_surum)
                self.sonuc_sinyali.emit(True, {
                    "yeni_surum_var": yeni_var,
                    "mevcut_surum": self.mevcut_surum,
                    "uzak_surum": uzak_surum,
                    " yayin_notlari": str(veri.get("notes", "")),
                    "indir_url": str(veri.get("download_url", f"https://github.com/{self.github_repo}/releases")),
                })
                return
        except Exception:
            pass

        # 2. Yedek: GitHub Releases API kontrolü
        try:
            req2 = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req2, timeout=6) as resp2:
                veri2 = json.loads(resp2.read().decode("utf-8"))
                uzak_surum = str(veri2.get("tag_name", self.mevcut_surum)).lstrip("vV")
                yeni_var = _surum_tuple_cevir(uzak_surum) > _surum_tuple_cevir(self.mevcut_surum)
                self.sonuc_sinyali.emit(True, {
                    "yeni_surum_var": yeni_var,
                    "mevcut_surum": self.mevcut_surum,
                    "uzak_surum": uzak_surum,
                    "yayin_notlari": str(veri2.get("body", "")),
                    "indir_url": str(veri2.get("html_url", f"https://github.com/{self.github_repo}/releases")),
                })
        except Exception as e:
            self.sonuc_sinyali.emit(False, {
                "hata": str(e),
                "mevcut_surum": self.mevcut_surum,
                "indir_url": f"https://github.com/{self.github_repo}",
            })


class GuncellemeKontrolDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, otomatik_bildirim_mi: bool = False, bilgisiz_bilgi: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.worker: Optional[GitHubGuncellemeKontrolWorker] = None
        self.indir_url = f"https://github.com/{self.config_manager.user_settings.get('github_repo', 'muallimun/Muallimun_Ses_Asistani')}"

        self.setWindowTitle("🔄 GitHub Sürüm ve Güncelleme Kontrolü")
        self.setMinimumSize(620, 380)
        self.resize(660, 420)

        tema = self.config_manager.user_settings.get("tema_modu", "koyu")
        self.setStyleSheet(studyo_tema_qss_olustur(tema))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        lbl_ust = QLabel(f"📦 Mevcut Uygulama Sürümü: <b>v{APP_VERSION}</b>")
        lbl_ust.setStyleSheet("font-size: 11pt; color: #10b981;")
        layout.addWidget(lbl_ust)

        repo_bar = QHBoxLayout()
        repo_bar.addWidget(QLabel("GitHub Deposu:"))
        self.edt_repo = QLineEdit(self.config_manager.user_settings.get("github_repo", "muallimun/Muallimun_Ses_Asistani"))
        repo_bar.addWidget(self.edt_repo, stretch=1)

        self.btn_denetle = QPushButton("🔍 Şimdi Kontrol Et")
        self.btn_denetle.setStyleSheet("background-color: #0284c7; color: white;")
        self.btn_denetle.clicked.connect(self.guncelleme_sorgula)
        repo_bar.addWidget(self.btn_denetle)
        layout.addLayout(repo_bar)

        self.lbl_durum = QLabel("⏳ Sürüm durumu sorgulanmaya hazır.")
        self.lbl_durum.setStyleSheet("font-weight: bold; font-size: 10pt;")
        layout.addWidget(self.lbl_durum)

        self.txt_notlar = QTextBrowser()
        self.txt_notlar.setPlaceholderText("Yeni sürüm değişiklik notları (Changelog) burada görüntülenir...")
        layout.addWidget(self.txt_notlar, stretch=1)

        alt_bar = QHBoxLayout()
        self.chk_oto_kontrol = QCheckBox("Uygulama açılışında yeni sürümü otomatik kontrol et")
        self.chk_oto_kontrol.setChecked(bool(self.config_manager.user_settings.get("otomatik_guncelleme_kontrolu", True)))
        self.chk_oto_kontrol.toggled.connect(self._oto_ayar_kaydet)
        alt_bar.addWidget(self.chk_oto_kontrol)
        alt_bar.addStretch()

        self.btn_github_ac = QPushButton("🌐 GitHub Sayfasını / İndirmeyi Aç")
        self.btn_github_ac.setStyleSheet("background-color: #059669; color: white; padding: 6px 14px;")
        self.btn_github_ac.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.indir_url)))
        alt_bar.addWidget(self.btn_github_ac)

        btn_kapat = QPushButton("Kapat")
        btn_kapat.clicked.connect(self.accept)
        alt_bar.addWidget(btn_kapat)
        layout.addLayout(alt_bar)

        if bilgisiz_bilgi is not None:
            self._sonuc_goster(True, bilgisiz_bilgi)
        elif not otomatik_bildirim_mi:
            self.guncelleme_sorgula()

    def _oto_ayar_kaydet(self, aktif: bool) -> None:
        self.config_manager.user_settings["otomatik_guncelleme_kontrolu"] = aktif
        self.config_manager.save_user_settings()

    def guncelleme_sorgula(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        repo = self.edt_repo.text().strip() or "muallimun/Muallimun_Ses_Asistani"
        self.config_manager.user_settings["github_repo"] = repo
        self.config_manager.save_user_settings()

        self.btn_denetle.setEnabled(False)
        self.lbl_durum.setText("⏳ GitHub üzerinden yeni sürüm kontrol ediliyor...")
        self.worker = GitHubGuncellemeKontrolWorker(github_repo=repo, mevcut_surum=APP_VERSION)
        self.worker.sonuc_sinyali.connect(self._sonuc_goster)
        self.worker.start()

    def _sonuc_goster(self, basarili: bool, bilgi: Dict[str, Any]) -> None:
        self.btn_denetle.setEnabled(True)
        self.indir_url = str(bilgi.get("indir_url", self.indir_url))

        if not basarili:
            self.lbl_durum.setText("ℹ️ GitHub deposuna şu an ulaşılamadı veya henüz sürüm (Release) yayınlanmadı.")
            self.txt_notlar.setHtml(
                f"<p>GitHub deponuz (<code>{self.edt_repo.text().strip()}</code>) yayına alındığında ve kök dizine "
                f"<code>version.json</code> eklendiğinde yeni sürümler otomatik olarak burada görünecektir.</p>"
            )
            return

        uzak = bilgi.get("uzak_surum", APP_VERSION)
        notlar = bilgi.get("yayin_notlari") or bilgi.get(" yayin_notlari") or "Değişiklik notu belirtilmemiş."
        if bilgi.get("yeni_surum_var"):
            self.lbl_durum.setText(f"🎉 Yeni Sürüm Mevcut: v{uzak} (Mevcut: v{APP_VERSION})")
            self.lbl_durum.setStyleSheet("color: #10b981; font-weight: bold; font-size: 10.5pt;")
            self.txt_notlar.setHtml(f"<h3>🚀 v{uzak} Yenilikleri:</h3><pre style='white-space:pre-wrap;'>{notlar}</pre>")
        else:
            self.lbl_durum.setText(f"✅ Uygulamanız Güncel! (v{APP_VERSION})")
            self.txt_notlar.setHtml(f"<p>En güncel sürümü (<b>v{APP_VERSION}</b>) kullanıyorsunuz.</p><pre>{notlar}</pre>")