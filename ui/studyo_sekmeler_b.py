#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MUALLİMUN AI SES STÜDYOSU PRO - ANA PENCERE BÖLÜM B (SEKME 4 VE SEKME 5)
Özellikler:
  1. Kilitlenmeyen Güvenli QThread Yaşam Döngüsü (CancelToken + finished Sinyali Koruması)
  2. 4 Sütunlu, Renk Vurgulu Seçmeli Kelime/Cümle/Diyalog Seçim Tablosu (Onay Kutusu Çakışması Giderildi)
  3. Adım 3 Kuyruk Filtresi (Sadece Seçilenler / Hatalılar / Tamamlananlar) ve Canlı Okunan Satır Vurgusu
  4. Tabloda Arapça Metin Düzenlendiğinde Otomatik Canlı Vakıf Yenileme (Denetim F06)
  5. Spark-TTS Varsayılan Motor Önceliği ve Aydınlık/Karanlık Tema (Light/Dark Mode) Desteği
"""

import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QFont, QColor, QDesktopServices
from PySide6.QtWidgets import (
    QWidget,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QCheckBox,
    QTextEdit,
    QLineEdit,
    QSpinBox,
    QTabWidget,
    QGroupBox,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QMessageBox,
    QProgressBar,
)

from core.config_manager import PROJECT_ROOT
from core.studyo_motoru import (
    CancelToken,
    arapca_akustik_metin_hazirla,
    uzun_metni_cumlelere_bol,
    sesleri_studyo_kalitesinde_birlestir,
    YETISKIN_ROLLER,
    COCUK_ROLLER,
    tr_kucult,
)
from core.batch_worker import (
    DUYGU_TONU_PROFILLERI,
    duygu_ve_tonlama_hesapla,
    OrnekSablonOlusturucu,
    VeriIceAktarici,
    CheckpointYoneticisi,
    StudyoBatchWorker,
    ses_secimi_kodunu_cozumle,
    guvenli_kimlik_temizle,
    guvenli_hedef_yol_cozumle,
)

# ==============================================================================
# DAĞITIM PAKETİ İÇİN GÖMÜLÜ MİNİ DEMO VERİLERİ
# ==============================================================================
GOMULU_DEMO_DIYALOGLAR: List[Dict[str, Any]] = [
    {
        "id": "demo_diyalog_01",
        "seviye": "A1",
        "baslik_tr": "Örnek Diyalog: Tanışma (Demo)",
        "satirlar": [
            {
                "sira": 1,
                "konusmaci": "Ömer",
                "cinsiyet": "E",
                "arapca": "اَلسَّلَامُ عَلَيْكُمْ، أَنَا عُمَرُ. مَا اسْمُكِ؟",
                "turkce": "Selamün aleyküm, ben Ömer. Senin adın ne?",
            },
            {
                "sira": 2,
                "konusmaci": "Leyla",
                "cinsiyet": "K",
                "arapca": "وَعَلَيْكُمُ السَّلَامُ، اِسْمِي لَيْلَى.",
                "turkce": "Aleykümselam, benim adım Leyla.",
            },
            {
                "sira": 3,
                "konusmaci": "Ömer",
                "cinsiyet": "E",
                "arapca": "تَشَرَّفْتُ بِمَعْرِفَتِكِ يَا لَيْلَى!",
                "turkce": "Tanıştığımıza memnun oldum Leyla!",
            },
        ],
    },
    {
        "id": "demo_diyalog_02",
        "seviye": "A2",
        "baslik_tr": "Örnek Diyalog: Sınıfta (Demo)",
        "satirlar": [
            {
                "sira": 1,
                "konusmaci": "Öğretmen",
                "cinsiyet": "E",
                "arapca": "صَبَاحُ الْخَيْرِ يَا طُلَّابِي، أَيْنَ كِتَابُكَ يَا عَلِيُّ؟",
                "turkce": "Günaydın öğrencilerim, kitabın nerede Ali?",
            },
            {
                "sira": 2,
                "konusmaci": "Ali",
                "cinsiyet": "E",
                "arapca": "كِتَابِي عَلَى الْمَكْتَبِ يَا أُسْتَاذِي.",
                "turkce": "Kitabım sıranın üzerinde öğretmenim.",
            },
        ],
    },
]

GOMULU_DEMO_METINLER: List[Dict[str, Any]] = [
    {
        "id": "demo_metin_01",
        "baslik_tr": "Örnek Okuma Metni: İlim ve Hikmet (Demo)",
        "satirlar": [
            {"sira": 1, "arapca": "اَلْعِلْمُ نُورٌ يُضِيءُ طَرِيقَ الْإِنْسَانِ فِي الْحَيَاةِ."},
            {"sira": 2, "arapca": "وَالْقِرَاءَةُ الْمُسْتَمِرَّةُ تَفْتَحُ لَنَا أَبْوَابَ الْمَعْرِفَةِ وَالْحِكْمَةِ كُلَّ يَوْمٍ."},
            {"sira": 3, "arapca": "فَمَنْ جَدَّ وَجَدَ، وَمَنْ زَرَعَ حَصَدَ."},
        ],
    }
]


def _kompakt_combobox_ayarla(cmb: QComboBox, min_genislik: int = 115) -> None:
    cmb.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
    cmb.setMinimumContentsLength(10)
    cmb.setMinimumWidth(min_genislik)


def _klasoru_sistemde_ac(klasor_yolu: Path) -> None:
    """Belirtilen çıktı klasörünü oluşturur ve Windows Gezgini'nde açar."""
    try:
        klasor_yolu.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(klasor_yolu.resolve()))
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(klasor_yolu.resolve())))
    except Exception as e:
        print(f"Klasör açma hatası: {e}")


def _motor_secici_doldur(cmb: QComboBox, varsayilan_kod: str = "SPARK_ARABIC") -> None:
    """Tüm sekmelerde Spark-TTS'i birinci ve önerilen motor olarak doldurur."""
    cmb.clear()
    cmb.addItem("🎙️ ⭐ Spark-TTS (Önerilen Klonlama)", "SPARK_ARABIC")
    cmb.addItem("⚡ Hızlı Direkt TTS (Çevrimiçi Hazır Ses)", "FAST_DIRECT_TTS")
    cmb.addItem("🗣️ Coqui XTTS v2 (Alternatif - Düşük Kalite)", "XTTS_STUDIO")
    cmb.setToolTip(
        "• ⭐ Spark-TTS (Önerilen): Harekeli Arapçada en yüksek mahreç ve ses klonlama kalitesi (Yerel GPU/CPU).\n"
        "• ⚡ Hızlı Direkt TTS: İnternet üzerinden hazır seslerle ~1 saniyede hızlı üretim (Klonlama yapmaz).\n"
        "• 🗣️ Coqui XTTS v2: Alternatif çok dilli model (Arapça ses kalitesi Spark-TTS kadar yüksek değildir)."
    )
    idx = cmb.findData(varsayilan_kod if varsayilan_kod in ("SPARK_ARABIC", "FAST_DIRECT_TTS", "XTTS_STUDIO") else "SPARK_ARABIC")
    cmb.setCurrentIndex(idx if idx >= 0 else 0)


def diyalog_icin_otomatik_rol_haritasi_olustur(
    voice_pool: List[Dict[str, Any]],
    satirlar: List[Dict[str, Any]],
    rotasyon_sayaci: int = 0,
) -> Dict[str, str]:
    """
    Diyalogdaki her konuşmacıya cinsiyetine ve rolüne uygun çakışmasız ses atar.
    Tanınmayan özel isimlerde varsayılan olarak YETİŞKİN seslerini önceliklendirir.
    """
    erkek_yetiskin = [v["id"] for v in voice_pool if v.get("kategori") == "yetiskin_E"]
    erkek_cocuk = [v["id"] for v in voice_pool if v.get("kategori") == "cocuk_E"]
    kadin_yetiskin = [v["id"] for v in voice_pool if v.get("kategori") == "yetiskin_K"]
    kadin_cocuk = [v["id"] for v in voice_pool if v.get("kategori") == "cocuk_K"]

    tum_erkek = erkek_yetiskin + erkek_cocuk
    tum_kadin = kadin_yetiskin + kadin_cocuk
    if not tum_erkek:
        tum_erkek = ["ref_erkek_1"]
    if not tum_kadin:
        tum_kadin = ["ref_kadin_1"]

    konusmaci_ses_haritasi: Dict[str, str] = {}
    kullanilan_sesler: List[str] = []

    for s_idx, s in enumerate(satirlar):
        konusmaci = str(s.get("konusmaci", f"Kisi_{s_idx}")).strip()
        if konusmaci in konusmaci_ses_haritasi:
            continue

        cinsiyet_str = str(s.get("cinsiyet", "E")).strip().upper()
        kadin_mi = cinsiyet_str.startswith("K")
        isim_kucuk = tr_kucult(konusmaci)

        kesin_cocuk = any(r in isim_kucuk for r in COCUK_ROLLER) and not any(r in isim_kucuk for r in YETISKIN_ROLLER)

        if kadin_mi:
            if kesin_cocuk and kadin_cocuk:
                havuz = kadin_cocuk + kadin_yetiskin
            else:
                havuz = kadin_yetiskin + kadin_cocuk if kadin_yetiskin else tum_kadin
        else:
            if kesin_cocuk and erkek_cocuk:
                havuz = erkek_cocuk + erkek_yetiskin
            else:
                havuz = erkek_yetiskin + erkek_cocuk if erkek_yetiskin else tum_erkek

        kaydirma = (rotasyon_sayaci + len(konusmaci_ses_haritasi)) % max(1, len(havuz))
        donmus_havuz = havuz[kaydirma:] + havuz[:kaydirma]

        adaylar = [vid for vid in donmus_havuz if vid not in kullanilan_sesler]
        if not adaylar:
            adaylar = donmus_havuz

        secilen_id = adaylar[0]
        kullanilan_sesler.append(secilen_id)
        konusmaci_ses_haritasi[konusmaci] = secilen_id

    return konusmaci_ses_haritasi


def _tablo_satirini_vurgula(
    tablo: QTableWidget,
    aktif_row: int,
    durum_tipi: str = "aktif",
    koyu_tema: bool = True,
    metin_sutunlari: Tuple[int, ...] = (0, 1, 2, 3, 5),
) -> None:
    """
    Seslendirilen satırı ekranda belirgin şekilde vurgular ve tabloyu o satıra kaydırır.
    durum_tipi: 'aktif' (canlı okunuyor), 'tamam' (üretildi), 'hata' (hatalı), 'secili' (kuyrukta seçili), 'normal'
    """
    if aktif_row < 0 or aktif_row >= tablo.rowCount():
        return

    renk_haritasi = {
        "aktif": (QColor("#78350f"), QColor("#fef3c7")) if koyu_tema else (QColor("#fef08a"), QColor("#713f12")),
        "tamam": (QColor("#064e3b"), QColor("#ecfdf5")) if koyu_tema else (QColor("#dcfce7"), QColor("#14532d")),
        "hata": (QColor("#7f1d1d"), QColor("#fef2f2")) if koyu_tema else (QColor("#fee2e2"), QColor("#7f1d1d")),
        "secili": (QColor("#1e3a8a"), QColor("#e0f2fe")) if koyu_tema else (QColor("#dbeafe"), QColor("#1e3a8a")),
        "normal": (QColor("#090d16"), QColor("#f8fafc")) if koyu_tema else (QColor("#ffffff"), QColor("#0f172a")),
    }
    bg_color, fg_color = renk_haritasi.get(durum_tipi, renk_haritasi["normal"])

    for col in range(tablo.columnCount()):
        item = tablo.item(aktif_row, col)
        if item is not None:
            item.setBackground(bg_color)
            if col in metin_sutunlari:
                item.setForeground(fg_color)

    if durum_tipi == "aktif":
        ilk_item = tablo.item(aktif_row, 0) or tablo.item(aktif_row, 1)
        if ilk_item:
            tablo.scrollToItem(ilk_item, QAbstractItemView.PositionAtCenter)


# ==============================================================================
# 4 SÜTUNLU ÇOKLU KAYIT / KELİME / CÜMLE / DİYALOG SEÇİM PENCERESİ
# (Screenshot_5_3.png'deki onay kutusu çakışması ve görünmezlik sorunu çözüldü)
# ==============================================================================
class CokluKayitSecimDialog(QDialog):
    def __init__(
        self,
        kayit_listesi: List[Dict[str, Any]],
        baslik: str = "Seçmeli Seslendirme",
        aciklama_metni: Optional[str] = None,
        varsayilan_hepsi_secili: bool = True,
        onceden_secili_indisler: Optional[Set[int]] = None,
        koyu_tema: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self.kayit_listesi = kayit_listesi
        self.koyu_tema = koyu_tema
        self.secilen_indisler: List[int] = []
        self._secim_durumlari: Dict[int, bool] = {}

        for idx in range(len(self.kayit_listesi)):
            if onceden_secili_indisler is not None and len(onceden_secili_indisler) > 0:
                self._secim_durumlari[idx] = (idx in onceden_secili_indisler)
            else:
                self._secim_durumlari[idx] = varsayilan_hepsi_secili

        self.setWindowTitle(f"☑️ {baslik}")
        self.setMinimumSize(780, 520)
        self.resize(860, 580)

        self._tema_uygula()
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        ust_bilgi = aciklama_metni or (
            "💡 <b>Seslendirilecek Satırları Seçin:</b> Tablodaki herhangi bir satıra tıklayarak seçebilir, "
            "arama kutusuyla filtreleyebilir veya <b>Belirli Satır Aralığını (Örn: 1 - 50)</b> işaretleyebilirsiniz."
        )
        lbl_aciklama = QLabel(ust_bilgi)
        lbl_aciklama.setWordWrap(True)
        layout.addWidget(lbl_aciklama)

        # 1. Satır: Arama ve Tümünü Seç / Temizle Barı
        ust_bar = QHBoxLayout()
        self.edt_ara = QLineEdit()
        self.edt_ara.setPlaceholderText("🔍 Sıra no, ID, Arapça metin veya Türkçe anlama göre filtrele...")
        self.edt_ara.textChanged.connect(self._filtrele)
        ust_bar.addWidget(self.edt_ara, stretch=1)

        btn_tumu = QPushButton("☑️ Görünenlerin Tümünü Seç")
        btn_tumu.clicked.connect(lambda: self._gorunenleri_isaretle(True))
        ust_bar.addWidget(btn_tumu)

        btn_kaldir = QPushButton("☐ Seçimi Temizle")
        btn_kaldir.setStyleSheet("background-color: #475569; color: white;")
        btn_kaldir.clicked.connect(lambda: self._gorunenleri_isaretle(False))
        ust_bar.addWidget(btn_kaldir)
        layout.addLayout(ust_bar)

        # 2. Satır: Hızlı Satır Aralığı Seçici
        aralik_bar = QHBoxLayout()
        aralik_bar.addWidget(QLabel("📏 <b>Satır Aralığı Seç:</b>  Başlangıç:"))
        toplam_adet = max(1, len(self.kayit_listesi))

        self.spn_baslangic = QSpinBox()
        self.spn_baslangic.setRange(1, toplam_adet)
        self.spn_baslangic.setValue(1)
        aralik_bar.addWidget(self.spn_baslangic)

        aralik_bar.addWidget(QLabel("Bitiş:"))
        self.spn_bitis = QSpinBox()
        self.spn_bitis.setRange(1, toplam_adet)
        self.spn_bitis.setValue(min(50, toplam_adet))
        aralik_bar.addWidget(self.spn_bitis)

        btn_aralik_sec = QPushButton("🎯 Sadece Bu Aralığı İşaretle")
        btn_aralik_sec.setStyleSheet("background-color: #0284c7; color: white; font-weight: bold;")
        btn_aralik_sec.clicked.connect(self._araligi_isaretle)
        aralik_bar.addWidget(btn_aralik_sec)
        aralik_bar.addStretch()
        layout.addLayout(aralik_bar)

        # 3. Satır: 4 Sütunlu Net Seçim Tablosu (Onay kutusu asla satır numarasının üstüne binmez!)
        self.tablo = QTableWidget(len(self.kayit_listesi), 4)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.verticalHeader().setDefaultSectionSize(38)
        self.tablo.setSelectionMode(QAbstractItemView.NoSelection)
        self.tablo.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tablo.setHorizontalHeaderLabels([
            "Durum",
            "Sıra & ID",
            "Arapça Metin / Diyalog Başlığı",
            "Türkçe Anlamı / Detay",
        ])
        self.tablo.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tablo.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tablo.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tablo.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)

        arapca_font = QFont("Traditional Arabic", 14)

        for idx, k in enumerate(self.kayit_listesi):
            k_id = str(k.get("id", f"kayit_{idx+1:04d}"))
            if "satirlar" in k and isinstance(k["satirlar"], list):
                ana_metin = str(k.get("baslik_tr", k_id))
                detay_metin = f"{len(k['satirlar'])} satırlık çoklu kayıt"
                ar_mi = False
            else:
                ana_metin = str(k.get("arapca", "")).strip()
                detay_metin = str(k.get("turkce", "")).strip()
                ar_mi = True

            durum_item = QTableWidgetItem()
            durum_item.setTextAlignment(Qt.AlignCenter)
            durum_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            self.tablo.setItem(idx, 0, durum_item)

            id_item = QTableWidgetItem(f"#{idx + 1}  [{k_id}]")
            id_item.setFont(QFont("Consolas", 9, QFont.Bold))
            self.tablo.setItem(idx, 1, id_item)

            metin_item = QTableWidgetItem(ana_metin)
            if ar_mi:
                metin_item.setFont(arapca_font)
                metin_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tablo.setItem(idx, 2, metin_item)

            detay_item = QTableWidgetItem(detay_metin)
            self.tablo.setItem(idx, 3, detay_item)

            self._satir_gorunumunu_guncelle(idx)

        self.tablo.cellClicked.connect(self._hucre_tiklandi)
        layout.addWidget(self.tablo, stretch=1)

        # 4. Satır: Alt Onay Barı
        alt_bar = QHBoxLayout()
        self.lbl_secili_sayac = QLabel("")
        self.lbl_secili_sayac.setStyleSheet("color: #10b981; font-weight: bold; font-size: 10pt;")
        alt_bar.addWidget(self.lbl_secili_sayac)
        alt_bar.addStretch()

        btn_sadece_filtrele = QPushButton("🔍 Kuyrukta Sadece Seçilenleri Göster")
        btn_sadece_filtrele.setToolTip("Üretimi hemen başlatmadan sadece seçtiğiniz satırları ana tabloda filtreler.")
        btn_sadece_filtrele.setStyleSheet("background-color: #0284c7; color: white; padding: 7px 14px; font-weight: bold;")
        btn_sadece_filtrele.clicked.connect(self._sadece_sec_ve_kapat)
        alt_bar.addWidget(btn_sadece_filtrele)

        btn_baslat = QPushButton("🚀 Seçili Kayıtları Seslendirmeye Başla")
        btn_baslat.setStyleSheet("background-color: #059669; color: white; padding: 7px 16px; font-weight: bold;")
        btn_baslat.clicked.connect(self._onayla_ve_uret)
        alt_bar.addWidget(btn_baslat)

        btn_iptal = QPushButton("İptal")
        btn_iptal.clicked.connect(self.reject)
        alt_bar.addWidget(btn_iptal)
        layout.addLayout(alt_bar)

        self.hemen_uret_istendi: bool = False
        self._sayaci_guncelle()

    def _tema_uygula(self) -> None:
        if not self.koyu_tema:
            self.setStyleSheet("""
                QDialog { background-color: #f8fafc; color: #0f172a; font-family: 'Segoe UI'; font-size: 9.5pt; }
                QTableWidget { background-color: #ffffff; color: #0f172a; gridline-color: #cbd5e1; border: 1px solid #cbd5e1; border-radius: 6px; }
                QHeaderView::section { background-color: #f1f5f9; color: #0369a1; padding: 6px; border: 1px solid #cbd5e1; font-weight: bold; }
                QLineEdit, QSpinBox { background-color: #ffffff; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 5px; padding: 4px 8px; }
                QPushButton { background-color: #0284c7; color: white; border: none; border-radius: 5px; padding: 6px 12px; font-weight: bold; }
            """)
        else:
            self.setStyleSheet("""
                QDialog { background-color: #0b0f19; color: #f8fafc; font-family: 'Segoe UI'; font-size: 9.5pt; }
                QTableWidget { background-color: #090d16; color: #f8fafc; gridline-color: #1e293b; border: 1px solid #1e293b; border-radius: 6px; }
                QHeaderView::section { background-color: #111827; color: #38bdf8; padding: 6px; border: 1px solid #1e293b; font-weight: bold; }
                QLineEdit, QSpinBox { background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 5px; padding: 4px 8px; }
                QPushButton { background-color: #0284c7; color: white; border: none; border-radius: 5px; padding: 6px 12px; font-weight: bold; }
            """)

    def _satir_gorunumunu_guncelle(self, row: int) -> None:
        secili = self._secim_durumlari.get(row, False)
        durum_item = self.tablo.item(row, 0)
        if durum_item:
            durum_item.setText("☑️ SEÇİLİ" if secili else "☐ Seç")

        if secili:
            bg = QColor("#064e3b") if self.koyu_tema else QColor("#d1fae5")
            fg = QColor("#ecfdf5") if self.koyu_tema else QColor("#065f46")
        else:
            bg = QColor("#090d16") if self.koyu_tema else QColor("#ffffff")
            fg = QColor("#cbd5e1") if self.koyu_tema else QColor("#334155")

        for c in range(self.tablo.columnCount()):
            it = self.tablo.item(row, c)
            if it:
                it.setBackground(bg)
                it.setForeground(fg)

    def _hucre_tiklandi(self, row: int, _col: int) -> None:
        self._secim_durumlari[row] = not self._secim_durumlari.get(row, False)
        self._satir_gorunumunu_guncelle(row)
        self._sayaci_guncelle()

    def _filtrele(self, metin: str) -> None:
        aranan = tr_kucult(metin)
        for r in range(self.tablo.rowCount()):
            satir_metni = " ".join(
                (self.tablo.item(r, c).text() if self.tablo.item(r, c) else "") for c in range(1, 4)
            )
            gizle = bool(aranan and aranan not in tr_kucult(satir_metni) and metin.strip() not in satir_metni)
            self.tablo.setRowHidden(r, gizle)

    def _gorunenleri_isaretle(self, secili_mi: bool) -> None:
        for r in range(self.tablo.rowCount()):
            if not self.tablo.isRowHidden(r):
                self._secim_durumlari[r] = secili_mi
                self._satir_gorunumunu_guncelle(r)
        self._sayaci_guncelle()

    def _araligi_isaretle(self) -> None:
        bas = min(self.spn_baslangic.value(), self.spn_bitis.value()) - 1
        bit = max(self.spn_baslangic.value(), self.spn_bitis.value()) - 1
        for r in range(self.tablo.rowCount()):
            self._secim_durumlari[r] = (bas <= r <= bit)
            self._satir_gorunumunu_guncelle(r)
        self._sayaci_guncelle()

    def _sayaci_guncelle(self) -> None:
        secili = sum(1 for v in self._secim_durumlari.values() if v)
        self.lbl_secili_sayac.setText(f"✅ Toplam {len(self.kayit_listesi)} kayıttan {secili} tanesi seçildi")

    def _secimleri_topla(self) -> bool:
        self.secilen_indisler = sorted([r for r, secili in self._secim_durumlari.items() if secili])
        if not self.secilen_indisler:
            QMessageBox.warning(self, "Seçim Yok", "Lütfen en az bir kayıt işaretleyin.")
            return False
        return True

    def _sadece_sec_ve_kapat(self) -> None:
        if self._secimleri_topla():
            self.hemen_uret_istendi = False
            self.accept()

    def _onayla_ve_uret(self) -> None:
        if self._secimleri_topla():
            self.hemen_uret_istendi = True
            self.accept()


# ==============================================================================
# DİYALOG VE UZUN METİN STÜDYOSU ARKA PLAN İŞÇİLERİ (CANCELTOKEN & GÜVENLİ BİTİŞ)
# ==============================================================================
class DiyalogVeMetinOzelWorker(QThread):
    satir_durum_sinyali = Signal(int, str, str)
    ilerleme_sinyali = Signal(int, int, str)
    log_sinyali = Signal(str)
    tamamlandi_sinyali = Signal(bool, str, str)

    def __init__(
        self,
        ana_pencere,
        satirlar: List[Dict[str, Any]],
        mod_kodu: str,
        secilen_motor_tipi: str,
        cikti_klasoru: Path,
        birlesik_dosya_adi: str,
        bosluk_ms: int,
        hiz: float,
        temperature: float,
        referans_ses_kullan: bool = True,
    ):
        super().__init__()
        self.ana_pencere = ana_pencere
        self.satirlar = satirlar
        self.mod_kodu = mod_kodu
        self.secilen_motor_tipi = secilen_motor_tipi
        self.cikti_klasoru = cikti_klasoru
        self.birlesik_dosya_adi = birlesik_dosya_adi
        self.bosluk_ms = bosluk_ms
        self.hiz = hiz
        self.temperature = temperature
        self.referans_ses_kullan = referans_ses_kullan
        self.cancel_token = CancelToken()
        self._durdur = False

    def durdur(self) -> None:
        self._durdur = True
        self.cancel_token.cancel()
        if self.ana_pencere.studyo_motor is not None:
            self.ana_pencere.studyo_motor.durdur()

    def run(self) -> None:
        try:
            self.ilerleme_sinyali.emit(3, 100, "⏳ Ses motoru hazırlanıyor...")
            motor = self.ana_pencere.motoru_getir_veya_yukle(
                log_fn=self.log_sinyali.emit,
                zorunlu_motor_tipi=self.secilen_motor_tipi,
            )
            motor.durdur_istegi = False
            cfg = self.ana_pencere.config_manager
            preset = cfg.get_preset(self.mod_kodu)
            dsp_ayar = preset.get("dsp", {})

            self.cikti_klasoru.mkdir(parents=True, exist_ok=True)
            toplam = max(1, len(self.satirlar))

            for idx, satir in enumerate(self.satirlar):
                if self._durdur or self.cancel_token.is_cancelled or motor.durdur_istegi:
                    self.satir_durum_sinyali.emit(idx, "⏹️ Durduruldu", "")
                    self.tamamlandi_sinyali.emit(False, "⏹️ İşlem kullanıcı tarafından durduruldu.", "")
                    return

                arapca = str(satir.get("arapca", "")).strip()
                akustik = str(satir.get("akustik", "")).strip()
                ref_id = str(satir.get("ref_id", "ref_erkek_1")).strip()
                dosya_adi = guvenli_kimlik_temizle(str(satir.get("dosya_adi", f"satir_{idx + 1:02d}.mp3")))
                if not dosya_adi.lower().endswith((".mp3", ".wav")):
                    dosya_adi += ".mp3"

                satir_ref_kullan = (
                    self.referans_ses_kullan
                    and (ref_id != "REFERANSSIZ")
                    and (self.secilen_motor_tipi != "FAST_DIRECT_TTS")
                )
                ref_yol = str(cfg.resolve_voice_path(ref_id if ref_id != "REFERANSSIZ" else "ref_erkek_1"))
                ref_metin = cfg.get_voice_prompt_text(ref_id if ref_id != "REFERANSSIZ" else "ref_erkek_1")

                satir_hedef = guvenli_hedef_yol_cozumle(self.cikti_klasoru, dosya_adi)

                satir_hiz, satir_temp, _, _ = duygu_ve_tonlama_hesapla(
                    arapca, preset, "otomatik" if self.mod_kodu == "diyalog" else "oykuleyici_dingin"
                )
                if self.mod_kodu != "diyalog":
                    satir_hiz = self.hiz
                    satir_temp = self.temperature

                self.satir_durum_sinyali.emit(idx, "🎙️ Üretiliyor...", "")
                self.ilerleme_sinyali.emit(idx, toplam, f"Satır {idx + 1}/{toplam} sentezleniyor...")

                def _alt_ilerleme(p_yuzde: int, p_mesaj: str, s_idx=idx):
                    if not self._durdur and not self.cancel_token.is_cancelled:
                        genel_tamam = int(((s_idx + (p_yuzde / 100.0)) / float(toplam)) * 100)
                        self.ilerleme_sinyali.emit(genel_tamam, 100, f"[{s_idx + 1}/{toplam}] {p_mesaj}")

                ok = motor.uret_ve_kaydet(
                    arapca_metin=arapca,
                    ref_wav_yolu=ref_yol,
                    cikti_yolu=satir_hedef,
                    hiz=satir_hiz,
                    temperature=satir_temp,
                    kelime_turu="genel",
                    tek_kelime_mi=False,
                    hikmetli_durak_ekle=False,
                    wav_formatini_zorla=satir_hedef.suffix.lower() == ".wav",
                    ozel_ref_metin=ref_metin,
                    onceden_hazirlanmis_akustik_metin=akustik,
                    dsp_ayar=dsp_ayar,
                    referans_ses_kullan=satir_ref_kullan,
                    ilerleme_callback=_alt_ilerleme,
                    cancel_token=self.cancel_token,
                )

                if self._durdur or self.cancel_token.is_cancelled or motor.durdur_istegi:
                    self.satir_durum_sinyali.emit(idx, "⏹️ Durduruldu", "")
                    self.tamamlandi_sinyali.emit(False, "⏹️ İşlem kullanıcı tarafından durduruldu.", "")
                    return

                if not ok:
                    detay = getattr(motor, "son_hata_mesaji", "")
                    self.satir_durum_sinyali.emit(idx, f"❌ Hatalı: {detay[:25]}", "")
                    self.tamamlandi_sinyali.emit(False, f"{idx + 1}. satır üretilemedi: {detay}".strip(), "")
                    return

                self.satir_durum_sinyali.emit(idx, "✅ Hazır", str(satir_hedef))

            # Klasördeki tüm satırları sırayla toplayıp birleştir (Denetim L-03)
            mevcut_satir_dosyalari = sorted([
                str(p) for p in self.cikti_klasoru.iterdir()
                if p.is_file() and p.name.startswith("satir_") and p.stat().st_size > 800
            ])

            birlesik_hedef = guvenli_hedef_yol_cozumle(self.cikti_klasoru, self.birlesik_dosya_adi)
            self.ilerleme_sinyali.emit(98, 100, f"{self.bosluk_ms}ms doğal boşlukla birleştiriliyor...")
            self.log_sinyali.emit(f"🔗 {len(mevcut_satir_dosyalari)} parça birleştiriliyor -> {birlesik_hedef.name}")

            birlesim_ok = sesleri_studyo_kalitesinde_birlestir(
                girdi_dosyalari=mevcut_satir_dosyalari,
                cikti_dosyasi=birlesik_hedef,
                bosluk_ms=self.bosluk_ms,
                mikro_fade_ms=10,
                birlestirilmis_seviye_dengele=True,
            )

            if birlesim_ok:
                self.ilerleme_sinyali.emit(100, 100, "✅ Tamamlandı!")
                self.tamamlandi_sinyali.emit(
                    True,
                    f"Tüm satırlar üretildi ve '{birlesik_hedef.name}' olarak birleştirildi!",
                    str(birlesik_hedef),
                )
            else:
                self.tamamlandi_sinyali.emit(False, "Satırlar üretildi ancak birleştirme sırasında hata oluştu.", "")
        except Exception as e:
            self.tamamlandi_sinyali.emit(False, f"Stüdyo hatası: {e}", "")


class CokluGrupSentezWorker(QThread):
    ilerleme_sinyali = Signal(int, int, str)
    log_sinyali = Signal(str)
    tamamlandi_sinyali = Signal(bool, str, str)

    def __init__(
        self,
        ana_pencere,
        secilen_gruplar: List[Dict[str, Any]],
        mod_kodu: str,
        secilen_motor_tipi: str,
        ust_cikti_klasoru: Path,
        birlesik_dosya_adi: str,
        bosluk_ms: int,
        varsayilan_anlatici_id: str = "ref_erkek_1",
    ):
        super().__init__()
        self.ana_pencere = ana_pencere
        self.secilen_gruplar = secilen_gruplar
        self.mod_kodu = mod_kodu
        self.secilen_motor_tipi = secilen_motor_tipi
        self.ust_cikti_klasoru = ust_cikti_klasoru
        self.birlesik_dosya_adi = birlesik_dosya_adi
        self.bosluk_ms = bosluk_ms
        self.varsayilan_anlatici_id = varsayilan_anlatici_id
        self.cancel_token = CancelToken()
        self._durdur = False

    def durdur(self) -> None:
        self._durdur = True
        self.cancel_token.cancel()
        if self.ana_pencere.studyo_motor is not None:
            self.ana_pencere.studyo_motor.durdur()

    def run(self) -> None:
        try:
            self.ilerleme_sinyali.emit(2, 100, "⏳ Ses motoru hazırlanıyor...")
            motor = self.ana_pencere.motoru_getir_veya_yukle(
                log_fn=self.log_sinyali.emit,
                zorunlu_motor_tipi=self.secilen_motor_tipi,
            )
            motor.durdur_istegi = False
            cfg = self.ana_pencere.config_manager
            preset = cfg.get_preset(self.mod_kodu)
            dsp_ayar = preset.get("dsp", {})
            ref_kullan = (self.secilen_motor_tipi != "FAST_DIRECT_TTS")

            toplam_grup = max(1, len(self.secilen_gruplar))
            basarili_grup = 0
            son_birlesik_yol = ""

            for g_idx, grup in enumerate(self.secilen_gruplar):
                if self._durdur or self.cancel_token.is_cancelled or motor.durdur_istegi:
                    self.tamamlandi_sinyali.emit(
                        False, f"⏹️ İşlem durduruldu ({basarili_grup}/{toplam_grup} klasör tamamlandı).", son_birlesik_yol
                    )
                    return

                grup_id = guvenli_kimlik_temizle(grup.get("id", f"{self.mod_kodu}_{g_idx + 1:03d}"))
                grup_klasor = guvenli_hedef_yol_cozumle(self.ust_cikti_klasoru, grup_id)
                grup_klasor.mkdir(parents=True, exist_ok=True)

                ham_satirlar = grup.get("satirlar", [])
                if not ham_satirlar:
                    continue

                rol_haritasi = (
                    diyalog_icin_otomatik_rol_haritasi_olustur(cfg.voice_pool, ham_satirlar, rotasyon_sayaci=g_idx)
                    if self.mod_kodu == "diyalog"
                    else {}
                )

                uretilen_dosyalar: List[str] = []
                satir_toplam = max(1, len(ham_satirlar))

                for s_idx, s in enumerate(ham_satirlar):
                    if self._durdur or self.cancel_token.is_cancelled or motor.durdur_istegi:
                        self.tamamlandi_sinyali.emit(
                            False, f"⏹️ İşlem durduruldu ({basarili_grup}/{toplam_grup} klasör tamamlandı).", son_birlesik_yol
                        )
                        return

                    arapca = str(s.get("arapca", "")).strip()
                    if not arapca:
                        continue
                    akustik = arapca_akustik_metin_hazirla(arapca, kelime_turu="genel", hikmetli_durak_ekle=False)

                    if self.mod_kodu == "diyalog":
                        konusmaci = str(s.get("konusmaci", f"Kisi_{s_idx}")).strip()
                        cins = str(s.get("cinsiyet", "E")).strip().upper()
                        ref_id = rol_haritasi.get(konusmaci, "ref_erkek_1")
                        dosya_adi = f"satir_{s_idx + 1:02d}_{cins}.mp3"
                    else:
                        ref_id = self.varsayilan_anlatici_id
                        dosya_adi = f"satir_{s_idx + 1:02d}.mp3"

                    ref_yol = str(cfg.resolve_voice_path(ref_id))
                    ref_metin = cfg.get_voice_prompt_text(ref_id)
                    satir_hedef = guvenli_hedef_yol_cozumle(grup_klasor, dosya_adi)

                    satir_hiz, satir_temp, _, _ = duygu_ve_tonlama_hesapla(
                        arapca, preset, "otomatik" if self.mod_kodu == "diyalog" else "oykuleyici_dingin"
                    )

                    genel_yuzde = int(((g_idx + (s_idx / float(satir_toplam))) / float(toplam_grup)) * 100)
                    self.ilerleme_sinyali.emit(
                        genel_yuzde,
                        100,
                        f"[{g_idx + 1}/{toplam_grup} - {grup_id}] Satır {s_idx + 1}/{satir_toplam}",
                    )

                    ok = motor.uret_ve_kaydet(
                        arapca_metin=arapca,
                        ref_wav_yolu=ref_yol,
                        cikti_yolu=satir_hedef,
                        hiz=satir_hiz,
                        temperature=satir_temp,
                        kelime_turu="genel",
                        tek_kelime_mi=False,
                        hikmetli_durak_ekle=False,
                        wav_formatini_zorla=False,
                        ozel_ref_metin=ref_metin,
                        onceden_hazirlanmis_akustik_metin=akustik,
                        dsp_ayar=dsp_ayar,
                        referans_ses_kullan=ref_kullan,
                        cancel_token=self.cancel_token,
                    )
                    if ok:
                        uretilen_dosyalar.append(str(satir_hedef))

                if uretilen_dosyalar:
                    birlesik_hedef = guvenli_hedef_yol_cozumle(grup_klasor, self.birlesik_dosya_adi)
                    if sesleri_studyo_kalitesinde_birlestir(
                        girdi_dosyalari=uretilen_dosyalar,
                        cikti_dosyasi=birlesik_hedef,
                        bosluk_ms=self.bosluk_ms,
                        mikro_fade_ms=10,
                        birlestirilmis_seviye_dengele=True,
                    ):
                        basarili_grup += 1
                        son_birlesik_yol = str(birlesik_hedef)

            self.ilerleme_sinyali.emit(100, 100, f"✅ {basarili_grup}/{toplam_grup} klasör tamamlandı!")
            self.tamamlandi_sinyali.emit(
                basarili_grup > 0,
                f"Seçilen {toplam_grup} kayıttan {basarili_grup} tanesi ayrı klasörlerde seslendirildi ve birleştirildi!\n"
                f"Ana Klasör: {self.ust_cikti_klasoru}",
                son_birlesik_yol,
            )
        except Exception as e:
            self.tamamlandi_sinyali.emit(False, f"Toplu grup sentez hatası: {e}", "")


# ==============================================================================
# SEKME 4: TOPLU DOSYA SESLENDİRME (KUYRUK FİLTRESİ, SATIR VURGUSU & GÜVENLİ DURDURMA)
# ==============================================================================
class TopluSeslendirmeSekmesi(QWidget):
    def __init__(self, ana_pencere):
        super().__init__(ana_pencere)
        self.ana_pencere = ana_pencere
        self.config_manager = ana_pencere.config_manager
        self.batch_worker: Optional[StudyoBatchWorker] = None
        self._bekleyen_eski_isciler: List[QThread] = []
        self.yuklu_kayitlar: List[Dict[str, Any]] = []
        self.secili_satir_indisleri: Set[int] = set()
        self.aktif_okunan_satir: int = -1
        self.aktif_kaynak_dosya: str = "demo_listesi"
        self.uzman_mod: bool = False
        self.koyu_tema: bool = (self.config_manager.user_settings.get("tema_modu", "koyu") != "aydinlik")
        self._tablo_yukleniyor: bool = False

        self._arayuzu_olustur()
        self.uzman_mod_guncelle(False)

    def _arayuzu_olustur(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(6)

        ust_kartlar_h = QHBoxLayout()
        ust_kartlar_h.setSpacing(10)

        # SOL KART: ADIM 1 — VERİ YÜKLEME VE ŞABLON İNDİRME
        adim1_grup = QGroupBox("Adım 1 — Veri Dosyası Yükleyin veya Hazır Şablon İndirin")
        adim1_v = QVBoxLayout(adim1_grup)
        adim1_v.setContentsMargins(10, 8, 10, 8)
        adim1_v.setSpacing(6)

        a1_satir1 = QHBoxLayout()
        a1_satir1.setSpacing(6)
        a1_satir1.addWidget(QLabel("İçerik Türü:"))
        self.cmb_toplu_mod = QComboBox()
        _kompakt_combobox_ayarla(self.cmb_toplu_mod, 145)
        for kod in ["tek_kelime", "cumle", "atasozu", "diyalog", "uzun_metin"]:
            p = self.config_manager.get_preset(kod)
            self.cmb_toplu_mod.addItem(p["baslik"], kod)
        self.cmb_toplu_mod.setCurrentIndex(1)
        self.cmb_toplu_mod.currentIndexChanged.connect(self._toplu_mod_degisti)
        a1_satir1.addWidget(self.cmb_toplu_mod, stretch=1)

        btn_demo_yukle = QPushButton("✨ Örnek Demo Yükle")
        btn_demo_yukle.setFixedHeight(28)
        btn_demo_yukle.clicked.connect(self._gomulu_demo_setini_yukle)
        a1_satir1.addWidget(btn_demo_yukle)
        adim1_v.addLayout(a1_satir1)

        a1_satir2 = QHBoxLayout()
        a1_satir2.setSpacing(6)
        btn_dosya_ac = QPushButton("📂 Bilgisayardan Dosya Yükle")
        btn_dosya_ac.setFixedHeight(28)
        btn_dosya_ac.setStyleSheet(
            "background-color: #059669; color: white; border: none; padding: 4px 12px; font-weight: bold;"
        )
        btn_dosya_ac.clicked.connect(self._dosyadan_ice_aktar_diyalogu)
        a1_satir2.addWidget(btn_dosya_ac, stretch=1)

        a1_satir2.addWidget(QLabel("Şablon:"))
        self.cmb_sablon_format = QComboBox()
        _kompakt_combobox_ayarla(self.cmb_sablon_format, 105)
        self.cmb_sablon_format.addItem("📊 Excel (.xlsx)", ".xlsx")
        self.cmb_sablon_format.addItem("🧩 JSON (.json)", ".json")
        self.cmb_sablon_format.addItem("📄 CSV (.csv)", ".csv")
        self.cmb_sablon_format.addItem("📝 Metin (.txt)", ".txt")
        a1_satir2.addWidget(self.cmb_sablon_format)

        btn_sablon_indir = QPushButton("📥 Şablon İndir")
        btn_sablon_indir.setFixedHeight(28)
        btn_sablon_indir.setStyleSheet("background-color: #0284c7; color: white; border: none; padding: 4px 10px;")
        btn_sablon_indir.clicked.connect(self._ornek_sablon_indir)
        a1_satir2.addWidget(btn_sablon_indir)
        adim1_v.addLayout(a1_satir2)

        ust_kartlar_h.addWidget(adim1_grup, stretch=1)

        # SAĞ KART: ADIM 2 — SES MOTORU VE KARAKTER SEÇİMİ
        adim2_grup = QGroupBox("Adım 2 — Seslendirme Motoru ve Varsayılan Karakter Seçimi")
        adim2_v = QVBoxLayout(adim2_grup)
        adim2_v.setContentsMargins(10, 8, 10, 8)
        adim2_v.setSpacing(6)

        a2_satir1 = QHBoxLayout()
        a2_satir1.setSpacing(8)
        a2_satir1.addWidget(QLabel("Motor:"))
        self.cmb_toplu_motor = QComboBox()
        _kompakt_combobox_ayarla(self.cmb_toplu_motor, 175)
        aktif_m = self.config_manager.user_settings.get("aktif_motor_tercihi", "SPARK_ARABIC")
        _motor_secici_doldur(self.cmb_toplu_motor, aktif_m)
        a2_satir1.addWidget(self.cmb_toplu_motor, stretch=1)

        self.chk_toplu_cift = QCheckBox("👨+👩 Erkek + Kadın Çift Üretim")
        self.chk_toplu_cift.setChecked(True)
        self.chk_toplu_cift.setStyleSheet("font-weight: bold; color: #0284c7;")
        self.chk_toplu_cift.toggled.connect(self._toplu_cift_secimi_degisti)
        a2_satir1.addWidget(self.chk_toplu_cift)
        adim2_v.addLayout(a2_satir1)

        a2_satir2 = QHBoxLayout()
        a2_satir2.setSpacing(6)
        self.lbl_toplu_erkek = QLabel("👨 Erkek:")
        self.cmb_toplu_erkek_ref = QComboBox()
        _kompakt_combobox_ayarla(self.cmb_toplu_erkek_ref, 130)
        a2_satir2.addWidget(self.lbl_toplu_erkek)
        a2_satir2.addWidget(self.cmb_toplu_erkek_ref, stretch=1)

        self.lbl_toplu_kadin = QLabel("👩 Kadın:")
        self.cmb_toplu_kadin_ref = QComboBox()
        _kompakt_combobox_ayarla(self.cmb_toplu_kadin_ref, 130)
        a2_satir2.addWidget(self.lbl_toplu_kadin)
        a2_satir2.addWidget(self.cmb_toplu_kadin_ref, stretch=1)
        adim2_v.addLayout(a2_satir2)

        ust_kartlar_h.addWidget(adim2_grup, stretch=1)
        layout.addLayout(ust_kartlar_h)

        # UZMAN MOD İNCE AYAR ŞERİDİ
        self.uzman_ayar_kutusu = QGroupBox("Uzman Mod — Duygu Tonu, Çıktı Klasörü ve Checkpoint Ayarları")
        uz_grid = QHBoxLayout(self.uzman_ayar_kutusu)
        uz_grid.setContentsMargins(10, 6, 10, 6)
        uz_grid.setSpacing(8)

        uz_grid.addWidget(QLabel("Tonlama:"))
        self.cmb_toplu_duygu = QComboBox()
        _kompakt_combobox_ayarla(self.cmb_toplu_duygu, 140)
        for d_kod, d_bilgi in DUYGU_TONU_PROFILLERI.items():
            self.cmb_toplu_duygu.addItem(d_bilgi["ad"], d_kod)
        uz_grid.addWidget(self.cmb_toplu_duygu, stretch=1)

        self.chk_mevcut_atla = QCheckBox("⏭️ Mevcutları Atla (Checkpoint)")
        self.chk_mevcut_atla.setChecked(True)
        uz_grid.addWidget(self.chk_mevcut_atla)

        uz_grid.addWidget(QLabel("Çıktı Klasörü:"))
        self.edt_toplu_cikti = QLineEdit(str(self.config_manager.get_default_output_dir()))
        self.edt_toplu_cikti.setMinimumWidth(130)
        uz_grid.addWidget(self.edt_toplu_cikti, stretch=1)

        btn_klasor_sec = QPushButton("📁 Değiştir...")
        btn_klasor_sec.setFixedHeight(26)
        btn_klasor_sec.clicked.connect(self._cikti_klasoru_sec)
        uz_grid.addWidget(btn_klasor_sec)

        self.btn_vakif_yenile = QPushButton("🔄 Vakıfları Güncelle")
        self.btn_vakif_yenile.setFixedHeight(26)
        self.btn_vakif_yenile.clicked.connect(self._tablodaki_vakiflari_yenile)
        uz_grid.addWidget(self.btn_vakif_yenile)

        self.btn_checkpoint_sifirla = QPushButton("🗑️ Geçmişi Sıfırla")
        self.btn_checkpoint_sifirla.setFixedHeight(26)
        self.btn_checkpoint_sifirla.clicked.connect(self._checkpoint_gecmisini_temizle)
        uz_grid.addWidget(self.btn_checkpoint_sifirla)

        layout.addWidget(self.uzman_ayar_kutusu)

        # ADIM 3: SESLENDİRME KUYRUĞU ÜST FİLTRE VE ARAÇ BARI
        tablo_ust_bar = QHBoxLayout()
        tablo_ust_bar.setContentsMargins(2, 0, 2, 0)
        tablo_ust_bar.setSpacing(6)

        self.lbl_kuyruk_sayac = QLabel("📋 Adım 3 — Seslendirme Kuyruğu (0 kayıt)")
        self.lbl_kuyruk_sayac.setStyleSheet("font-weight: bold; color: #0284c7;")
        tablo_ust_bar.addWidget(self.lbl_kuyruk_sayac)
        tablo_ust_bar.addStretch()

        tablo_ust_bar.addWidget(QLabel("🔍 Görünüm:"))
        self.cmb_kuyruk_filtre = QComboBox()
        _kompakt_combobox_ayarla(self.cmb_kuyruk_filtre, 150)
        self.cmb_kuyruk_filtre.addItem("📋 Tüm Kayıtları Göster", "TUMU")
        self.cmb_kuyruk_filtre.addItem("🎯 Sadece Seçilenleri Göster", "SECILENLER")
        self.cmb_kuyruk_filtre.addItem("❌ Sadece Hatalıları Göster", "HATALILAR")
        self.cmb_kuyruk_filtre.addItem("✅ Tamamlananları Göster", "TAMAMLANANLAR")
        self.cmb_kuyruk_filtre.addItem("⏳ Bekleyenleri Göster", "BEKLEYENLER")
        self.cmb_kuyruk_filtre.currentIndexChanged.connect(self._kuyruk_filtresini_uygula)
        tablo_ust_bar.addWidget(self.cmb_kuyruk_filtre)

        self.btn_hatalilari_tekrarla = QPushButton("🔄 Hatalıları Yeniden Üret")
        self.btn_hatalilari_tekrarla.setFixedHeight(26)
        self.btn_hatalilari_tekrarla.setToolTip("Tabloda ❌ Hata veren satırları tek tıkla yeniden sentezler.")
        self.btn_hatalilari_tekrarla.clicked.connect(self._hatali_satirlari_yeniden_uret)
        tablo_ust_bar.addWidget(self.btn_hatalilari_tekrarla)

        btn_satir_ekle = QPushButton("➕ Satır Ekle")
        btn_satir_ekle.setFixedHeight(26)
        btn_satir_ekle.clicked.connect(self._tabloya_bos_satir_ekle)
        tablo_ust_bar.addWidget(btn_satir_ekle)

        btn_tablo_temizle = QPushButton("✖️ Kaynağı Kaldır")
        btn_tablo_temizle.setFixedHeight(26)
        btn_tablo_temizle.setStyleSheet("background-color: #475569; color: white;")
        btn_tablo_temizle.clicked.connect(self._tabloyu_temizle)
        tablo_ust_bar.addWidget(btn_tablo_temizle)
        layout.addLayout(tablo_ust_bar)

        self.tablo_kuyruk = QTableWidget(0, 8)
        self.tablo_kuyruk.verticalHeader().setDefaultSectionSize(38)
        baslik_bilgileri = [
            ("ID / Sıra", "Kaydın benzersiz dosya adı veya sıra numarası."),
            ("Arapça Metin (Düzenlenebilir)", "Seslendirilecek Arapça metin (Düzenlendiğinde vakıflı okunuş otomatik güncellenir)."),
            ("Canlı Vakıflı Okunuş", "Motorun okuyacağı vakıflı/sükûnlu metin (Uzman Modda görünür)."),
            ("Türkçe Anlamı / Not", "Bilgi amaçlı Türkçe çeviri veya ders notu."),
            ("Ses Seçimi (Karakter)", "Bu satırın hangi ses karakteriyle okunacağı."),
            ("Durum", "Satırın sentezlenme durumu (Seçili, Hazır, Üretiliyor, Tamamlandı, Hata)."),
            ("Üretilen Sesi Dinle", "Üretilen Erkek ve Kadın seslerini anında dinleme butonları."),
            ("İşlem", "Yalnızca bu satırı tek başına üretme veya yeniden üretme butonu."),
        ]
        self.tablo_kuyruk.setHorizontalHeaderLabels([b[0] for b in baslik_bilgileri])
        for c_i, (_, ipucu) in enumerate(baslik_bilgileri):
            if self.tablo_kuyruk.horizontalHeaderItem(c_i):
                self.tablo_kuyruk.horizontalHeaderItem(c_i).setToolTip(ipucu)

        self.tablo_kuyruk.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tablo_kuyruk.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tablo_kuyruk.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tablo_kuyruk.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tablo_kuyruk.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tablo_kuyruk.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.tablo_kuyruk.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.tablo_kuyruk.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.tablo_kuyruk.cellChanged.connect(self._kuyruk_hucre_duzenlendi)
        layout.addWidget(self.tablo_kuyruk, stretch=1)

        # ADIM 4: ALT BAŞLATMA, SEÇMELİ ÜRETME, DURDURMA, İLERLEME VE ÇIKTI KLASÖRÜ BARI
        alt_btn_bar = QHBoxLayout()
        alt_btn_bar.setSpacing(6)

        self.btn_toplu_baslat = QPushButton("🚀 Tümünü Seslendir")
        self.btn_toplu_baslat.setFixedHeight(36)
        self.btn_toplu_baslat.setStyleSheet(
            "background-color: #059669; color: white; border: none; padding: 4px 14px; font-weight: bold;"
        )
        self.btn_toplu_baslat.clicked.connect(lambda: self.toplu_islemi_baslat(sadece_secili_indisler=None))

        self.btn_toplu_secmeli = QPushButton("☑️ Seçmeli Satır Seç & Üret...")
        self.btn_toplu_secmeli.setFixedHeight(36)
        self.btn_toplu_secmeli.setStyleSheet(
            "background-color: #7c3aed; color: white; border: none; padding: 4px 12px; font-weight: bold;"
        )
        self.btn_toplu_secmeli.clicked.connect(self._secmeli_satirlari_sec_ve_uret_diyalogu)

        self.btn_toplu_duraklat = QPushButton("⏸️ Duraklat")
        self.btn_toplu_duraklat.setFixedHeight(36)
        self.btn_toplu_duraklat.setEnabled(False)
        self.btn_toplu_duraklat.clicked.connect(self._duraklat_veya_devam_et)

        self.btn_toplu_durdur = QPushButton("⏹️ DURDUR")
        self.btn_toplu_durdur.setFixedHeight(36)
        self.btn_toplu_durdur.setEnabled(False)
        self.btn_toplu_durdur.setStyleSheet(
            "background-color: #dc2626; color: white; border: none; padding: 4px 12px; font-weight: bold;"
        )
        self.btn_toplu_durdur.clicked.connect(self._toplu_islemi_durdur)

        self.progress_toplu = QProgressBar()
        self.progress_toplu.setFixedHeight(26)
        self.progress_toplu.setMinimumWidth(220)
        self.progress_toplu.setRange(0, 100)
        self.progress_toplu.setValue(0)
        self.progress_toplu.setFormat("Hazır (%p%)")

        self.btn_toplu_klasor_ac = QPushButton("📂 Çıktı Klasörünü Aç")
        self.btn_toplu_klasor_ac.setFixedHeight(36)
        self.btn_toplu_klasor_ac.setStyleSheet(
            "background-color: #0284c7; color: white; border: none; padding: 4px 12px; font-weight: bold;"
        )
        self.btn_toplu_klasor_ac.clicked.connect(self._toplu_cikti_klasorunu_ac)

        alt_btn_bar.addWidget(self.btn_toplu_baslat)
        alt_btn_bar.addWidget(self.btn_toplu_secmeli)
        alt_btn_bar.addWidget(self.btn_toplu_duraklat)
        alt_btn_bar.addWidget(self.btn_toplu_durdur)
        alt_btn_bar.addWidget(self.progress_toplu, stretch=1)
        alt_btn_bar.addWidget(self.btn_toplu_klasor_ac)
        layout.addLayout(alt_btn_bar)

        self._referans_listelerini_doldur()
        self._gomulu_demo_setini_yukle()

    def tema_guncelle(self, tema_kodu: str) -> None:
        self.koyu_tema = (tema_kodu != "aydinlik")
        for r in range(self.tablo_kuyruk.rowCount()):
            durum_txt = self.tablo_kuyruk.item(r, 5).text() if self.tablo_kuyruk.item(r, 5) else ""
            if r == self.aktif_okunan_satir:
                _tablo_satirini_vurgula(self.tablo_kuyruk, r, "aktif", self.koyu_tema)
            elif "✅" in durum_txt:
                _tablo_satirini_vurgula(self.tablo_kuyruk, r, "tamam", self.koyu_tema)
            elif "❌" in durum_txt:
                _tablo_satirini_vurgula(self.tablo_kuyruk, r, "hata", self.koyu_tema)
            elif r in self.secili_satir_indisleri:
                _tablo_satirini_vurgula(self.tablo_kuyruk, r, "secili", self.koyu_tema)
            else:
                _tablo_satirini_vurgula(self.tablo_kuyruk, r, "normal", self.koyu_tema)

    def _kuyruk_hucre_duzenlendi(self, row: int, col: int) -> None:
        """Arapça metin (col 1) düzenlendiğinde Canlı Vakıflı Okunuş (col 2) sütununu otomatik günceller (Denetim F06)."""
        if self._tablo_yukleniyor or col != 1:
            return
        ar_item = self.tablo_kuyruk.item(row, 1)
        if not ar_item:
            return
        yeni_arapca = ar_item.text().strip()
        mod_kodu = self.cmb_toplu_mod.currentData() or "cumle"
        preset = self.config_manager.get_preset(mod_kodu)
        hikmetli = bool(preset.get("hikmetli_durak_ekle", False))
        kelime_turu = self.yuklu_kayitlar[row].get("kelime_turu", "genel") if row < len(self.yuklu_kayitlar) else "genel"
        yeni_akustik = arapca_akustik_metin_hazirla(yeni_arapca, kelime_turu=kelime_turu, hikmetli_durak_ekle=hikmetli)

        self._tablo_yukleniyor = True
        try:
            if self.tablo_kuyruk.item(row, 2):
                self.tablo_kuyruk.item(row, 2).setText(yeni_akustik)
            if row < len(self.yuklu_kayitlar):
                self.yuklu_kayitlar[row]["arapca"] = yeni_arapca
                self.yuklu_kayitlar[row]["akustik_metin"] = yeni_akustik
                self.yuklu_kayitlar[row]["kaynak_metin_ozeti"] = hashlib.sha1(yeni_arapca.encode("utf-8")).hexdigest()[:10]
        finally:
            self._tablo_yukleniyor = False

    def _kuyruk_filtresini_uygula(self) -> None:
        filtre = self.cmb_kuyruk_filtre.currentData() or "TUMU"
        gorunen_sayisi = 0
        for r in range(self.tablo_kuyruk.rowCount()):
            durum_txt = self.tablo_kuyruk.item(r, 5).text() if self.tablo_kuyruk.item(r, 5) else ""
            gizle = False
            if filtre == "SECILENLER":
                gizle = (r not in self.secili_satir_indisleri)
            elif filtre == "HATALILAR":
                gizle = ("❌" not in durum_txt)
            elif filtre == "TAMAMLANANLAR":
                gizle = ("✅" not in durum_txt and "⏭️" not in durum_txt)
            elif filtre == "BEKLEYENLER":
                gizle = ("✅" in durum_txt or "⏭️" in durum_txt)

            self.tablo_kuyruk.setRowHidden(r, gizle)
            if not gizle:
                gorunen_sayisi += 1

        secili_bilgi = f" | 🎯 {len(self.secili_satir_indisleri)} seçili" if self.secili_satir_indisleri else ""
        self.lbl_kuyruk_sayac.setText(
            f"📋 Adım 3 — Seslendirme Kuyruğu ({gorunen_sayisi}/{len(self.yuklu_kayitlar)} görünür{secili_bilgi} — {os.path.basename(self.aktif_kaynak_dosya)})"
        )

    def _hatali_satirlari_yeniden_uret(self) -> None:
        hatali_indisler = []
        for r in range(self.tablo_kuyruk.rowCount()):
            durum_txt = self.tablo_kuyruk.item(r, 5).text() if self.tablo_kuyruk.item(r, 5) else ""
            if "❌" in durum_txt:
                hatali_indisler.append(r)
        if not hatali_indisler:
            QMessageBox.information(self, "Hatalı Satır Yok", "Kuyrukta yeniden üretilecek hatalı (❌) satır bulunamadı.")
            return
        self.secili_satir_indisleri = set(hatali_indisler)
        self.toplu_islemi_baslat(sadece_secili_indisler=hatali_indisler)

    def _secmeli_satirlari_sec_ve_uret_diyalogu(self) -> None:
        if not self.yuklu_kayitlar:
            QMessageBox.warning(self, "Liste Boş", "Lütfen önce bir veri dosyası yükleyin veya satır ekleyin.")
            return

        self._tablodaki_guncel_verileri_senkronize_et()
        dlg = CokluKayitSecimDialog(
            self.yuklu_kayitlar,
            baslik="Seçmeli Kelime / Cümle Seslendirme",
            varsayilan_hepsi_secili=False,
            onceden_secili_indisler=self.secili_satir_indisleri,
            koyu_tema=self.koyu_tema,
            parent=self,
        )
        if dlg.exec() == QDialog.Accepted and dlg.secilen_indisler:
            self.secili_satir_indisleri = set(dlg.secilen_indisler)
            self._tablo_yukleniyor = True
            try:
                for r in range(self.tablo_kuyruk.rowCount()):
                    durum_it = self.tablo_kuyruk.item(r, 5)
                    if r in self.secili_satir_indisleri:
                        if durum_it and ("Hazır" in durum_it.text() or "Durduruldu" in durum_it.text()):
                            durum_it.setText("🎯 Seçili (Sırada)")
                        _tablo_satirini_vurgula(self.tablo_kuyruk, r, "secili", self.koyu_tema)
                    else:
                        if durum_it and "Seçili" in durum_it.text():
                            durum_it.setText("⏳ Hazır")
                        _tablo_satirini_vurgula(self.tablo_kuyruk, r, "normal", self.koyu_tema)
            finally:
                self._tablo_yukleniyor = False

            # Seçilenlerin net görülmesi için görünüm filtresini 'Sadece Seçilenler' yap
            idx_f = self.cmb_kuyruk_filtre.findData("SECILENLER")
            if idx_f >= 0:
                self.cmb_kuyruk_filtre.setCurrentIndex(idx_f)
            self._kuyruk_filtresini_uygula()

            if dlg.hemen_uret_istendi:
                self.toplu_islemi_baslat(sadece_secili_indisler=dlg.secilen_indisler)

    def _toplu_cikti_klasorunu_ac(self) -> None:
        ana_kok = Path(self.edt_toplu_cikti.text().strip() or str(self.config_manager.get_default_output_dir()))
        mod_kodu = self.cmb_toplu_mod.currentData() or "cumle"
        alt_klasor = ana_kok / mod_kodu
        hedef = alt_klasor if alt_klasor.exists() else ana_kok
        _klasoru_sistemde_ac(hedef)

    def uzman_mod_guncelle(self, uzman_mi: bool) -> None:
        self.uzman_mod = uzman_mi
        self.uzman_ayar_kutusu.setVisible(uzman_mi)
        self.tablo_kuyruk.setColumnHidden(2, not uzman_mi)

    def _toplu_cift_secimi_degisti(self, cift_mi: bool) -> None:
        self.lbl_toplu_kadin.setVisible(cift_mi)
        self.cmb_toplu_kadin_ref.setVisible(cift_mi)

    def _referans_listelerini_doldur(self) -> None:
        self.cmb_toplu_erkek_ref.clear()
        self.cmb_toplu_kadin_ref.clear()
        for ses in self.config_manager.voice_pool:
            etiket = f"{ses.get('ad', ses['id'])}"
            if ses.get("cinsiyet", "E").upper() == "K":
                self.cmb_toplu_kadin_ref.addItem(etiket, ses["id"])
            else:
                self.cmb_toplu_erkek_ref.addItem(etiket, ses["id"])

    def _satir_ses_secici_olustur(self, secili_deger: str = "otomatik") -> QComboBox:
        cmb = QComboBox()
        _kompakt_combobox_ayarla(cmb, 130)
        cmb.addItem("⚙️ Otomatik (Üst Ayar)", "otomatik")
        cmb.addItem("👨+👩 İkisi (Çift Üretim)", "IKISI")
        cmb.addItem("⚡ Direkt Hızlı TTS", "_varsayilan_sentetik_ref")

        kisa_etiketler = {
            "ref_erkek_1": "👨 Erkek 1 (E1)",
            "ref_erkek_2": "👨 Erkek 2 (E2)",
            "ref_kadin_1": "👩 Kadın 1 (K1)",
            "ref_kadin_2": "👩 Kadın 2 (K2)",
            "ref_erkek_cocuk_1": "👦 E.Çocuk 1 (EC1)",
            "ref_erkek_cocuk_2": "👦 E.Çocuk 2 (EC2)",
            "ref_kiz_cocuk_1": "👧 K.Çocuk 1 (KC1)",
            "ref_kiz_cocuk_2": "👧 K.Çocuk 2 (KC2)",
        }
        for ses in self.config_manager.voice_pool:
            vid = ses["id"]
            etiket = kisa_etiketler.get(vid, f"🎙️ {ses.get('ad', vid)}")
            cmb.addItem(etiket, vid)

        cozumlenmis = ses_secimi_kodunu_cozumle(secili_deger)
        idx = cmb.findData(cozumlenmis)
        if idx >= 0:
            cmb.setCurrentIndex(idx)
        return cmb

    def _toplu_mod_degisti(self) -> None:
        mod_kodu = self.cmb_toplu_mod.currentData()
        preset = self.config_manager.get_preset(mod_kodu)
        cift_mi = bool(preset.get("cift_uretim_erkek_kadin", True))
        self.chk_toplu_cift.setChecked(cift_mi)
        self._toplu_cift_secimi_degisti(cift_mi)

    def _cikti_klasoru_sec(self) -> None:
        klasor = QFileDialog.getExistingDirectory(self, "Toplu Çıktı Klasörü Seç", self.edt_toplu_cikti.text())
        if klasor:
            self.edt_toplu_cikti.setText(klasor)

    def _ornek_sablon_indir(self) -> None:
        mod_kodu = self.cmb_toplu_mod.currentData() or "cumle"
        uzanti = self.cmb_sablon_format.currentData() or ".xlsx"
        varsayilan_ad = f"muallimun_ornek_sablon_{mod_kodu}{uzanti}"

        filtre_haritasi = {
            ".xlsx": "Excel Dosyası (*.xlsx);;JSON Dosyası (*.json);;CSV Tablosu (*.csv);;Metin Dosyası (*.txt)",
            ".json": "JSON Dosyası (*.json);;Excel Dosyası (*.xlsx);;CSV Tablosu (*.csv);;Metin Dosyası (*.txt)",
            ".csv": "CSV Tablosu (*.csv);;Excel Dosyası (*.xlsx);;JSON Dosyası (*.json);;Metin Dosyası (*.txt)",
            ".txt": "Metin Dosyası (*.txt);;Excel Dosyası (*.xlsx);;JSON Dosyası (*.json);;CSV Tablosu (*.csv)",
        }

        hedef_yol, _ = QFileDialog.getSaveFileName(
            self,
            "Örnek Şablonu Kaydet",
            str(Path.home() / "Desktop" / varsayilan_ad),
            filtre_haritasi.get(uzanti, "Tüm Dosyalar (*.*)"),
        )
        if not hedef_yol:
            return
        try:
            kaydedilen = OrnekSablonOlusturucu.sablon_kaydet(mod_kodu, hedef_yol)
            QMessageBox.information(
                self,
                "Örnek Şablon İndirildi",
                f"Örnek şablon başarıyla kaydedildi:\n{kaydedilen}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Şablon Hatası", f"Şablon oluşturulurken hata oluştu:\n{e}")

    def _dosyadan_ice_aktar_diyalogu(self) -> None:
        dosya, _ = QFileDialog.getOpenFileName(
            self,
            "Veri Dosyası Seç (CSV / Excel .xlsx / JSON / TXT)",
            str(Path.home() / "Desktop"),
            "Veri Dosyaları (*.json *.csv *.xlsx *.txt)",
        )
        if dosya:
            self.dosya_yukle(dosya)

    def _gomulu_demo_setini_yukle(self) -> None:
        mod_kodu = self.cmb_toplu_mod.currentData() or "cumle"
        ham_ornekler = OrnekSablonOlusturucu.ORNEK_VERILER.get(mod_kodu, OrnekSablonOlusturucu.ORNEK_VERILER["cumle"])
        self.yuklu_kayitlar = VeriIceAktarici._duz_sozluk_listesini_normallestir(ham_ornekler, mod_kodu)
        self.aktif_kaynak_dosya = f"demo_{mod_kodu}"
        self.secili_satir_indisleri.clear()
        self._tabloyu_kayitlardan_doldur()

    def dosya_yukle(self, dosya_yolu: str) -> None:
        try:
            varsayilan_mod = self.cmb_toplu_mod.currentData() or "cumle"
            kayitlar, algilanan_mod = VeriIceAktarici.dosyadan_yukle(dosya_yolu, varsayilan_mod=varsayilan_mod)
            if not kayitlar:
                QMessageBox.warning(self, "Boş Dosya", "Seçilen dosyada seslendirilecek Arapça kayıt bulunamadı.")
                return

            self.aktif_kaynak_dosya = dosya_yolu
            self.yuklu_kayitlar = kayitlar
            self.secili_satir_indisleri.clear()

            idx_mod = self.cmb_toplu_mod.findData(algilanan_mod)
            if idx_mod >= 0:
                self.cmb_toplu_mod.setCurrentIndex(idx_mod)

            idx_f = self.cmb_kuyruk_filtre.findData("TUMU")
            if idx_f >= 0:
                self.cmb_kuyruk_filtre.setCurrentIndex(idx_f)

            self._tabloyu_kayitlardan_doldur()
        except Exception as e:
            QMessageBox.critical(self, "İçe Aktarma Hatası", f"Dosya okunurken hata oluştu:\n{e}")

    def _dinleme_hucresi_olustur(self, erkek_veya_tek_yol: str = "", kadin_yol: str = "") -> QWidget:
        kutu = QWidget()
        h = QHBoxLayout(kutu)
        h.setContentsMargins(4, 2, 4, 2)
        h.setSpacing(4)

        erkek_var = bool(erkek_veya_tek_yol and os.path.exists(erkek_veya_tek_yol))
        kadin_var = bool(kadin_yol and os.path.exists(kadin_yol))

        if not erkek_var and not kadin_var:
            lbl = QLabel("Henüz Üretilmedi")
            lbl.setStyleSheet("color: #64748b; font-size: 8.5pt;")
            lbl.setAlignment(Qt.AlignCenter)
            h.addWidget(lbl)
            return kutu

        if erkek_var:
            etiket = "🔊 Erkek" if kadin_var else "🔊 Dinle"
            btn_e = QPushButton(etiket)
            btn_e.setFixedHeight(26)
            btn_e.setStyleSheet("background-color: #0284c7; color: white; border: none; padding: 2px 8px;")
            btn_e.clicked.connect(lambda checked=False, p=erkek_veya_tek_yol: self.ana_pencere.ses_dosyasini_cal(p))
            h.addWidget(btn_e)

        if kadin_var:
            btn_k = QPushButton("🔊 Kadın")
            btn_k.setFixedHeight(26)
            btn_k.setStyleSheet("background-color: #db2777; color: white; border: none; padding: 2px 8px;")
            btn_k.clicked.connect(lambda checked=False, p=kadin_yol: self.ana_pencere.ses_dosyasini_cal(p))
            h.addWidget(btn_k)

        return kutu

    def _tabloyu_kayitlardan_doldur(self) -> None:
        self._tablo_yukleniyor = True
        try:
            mod_kodu = self.cmb_toplu_mod.currentData() or "cumle"
            preset = self.config_manager.get_preset(mod_kodu)
            hikmetli = bool(preset.get("hikmetli_durak_ekle", False))

            self.tablo_kuyruk.setRowCount(len(self.yuklu_kayitlar))
            arapca_font = QFont("Traditional Arabic", 15)

            for r_idx, k in enumerate(self.yuklu_kayitlar):
                item_id = str(k.get("id", f"satir_{r_idx + 1:04d}"))
                arapca = str(k.get("arapca", ""))
                turkce = str(k.get("turkce", ""))
                kelime_turu = str(k.get("kelime_turu", "genel"))
                referans_ses = str(k.get("referans_ses", "otomatik"))

                akustik = arapca_akustik_metin_hazirla(
                    arapca, kelime_turu=kelime_turu, hikmetli_durak_ekle=hikmetli
                )
                k["akustik_metin"] = akustik
                k["kaynak_metin_ozeti"] = hashlib.sha1(arapca.encode("utf-8")).hexdigest()[:10]

                self.tablo_kuyruk.setItem(r_idx, 0, QTableWidgetItem(item_id))

                ar_item = QTableWidgetItem(arapca)
                ar_item.setFont(arapca_font)
                ar_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tablo_kuyruk.setItem(r_idx, 1, ar_item)

                ak_item = QTableWidgetItem(akustik)
                ak_item.setFont(arapca_font)
                ak_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                ak_item.setForeground(QColor("#10b981"))
                self.tablo_kuyruk.setItem(r_idx, 2, ak_item)

                self.tablo_kuyruk.setItem(r_idx, 3, QTableWidgetItem(turkce))
                self.tablo_kuyruk.setCellWidget(r_idx, 4, self._satir_ses_secici_olustur(referans_ses))
                self.tablo_kuyruk.setItem(r_idx, 5, QTableWidgetItem("⏳ Hazır"))

                self.tablo_kuyruk.setCellWidget(r_idx, 6, self._dinleme_hucresi_olustur("", ""))

                btn_tek_uret = QPushButton("🎙️ Üret")
                btn_tek_uret.setFixedHeight(26)
                btn_tek_uret.clicked.connect(lambda checked=False, row=r_idx: self.toplu_islemi_baslat(sadece_secili_indisler=[row]))
                self.tablo_kuyruk.setCellWidget(r_idx, 7, btn_tek_uret)

            self.tablo_kuyruk.setColumnHidden(2, not self.uzman_mod)
            self._kuyruk_filtresini_uygula()
        finally:
            self._tablo_yukleniyor = False

    def _tabloya_bos_satir_ekle(self) -> None:
        self._tablodaki_guncel_verileri_senkronize_et()
        yeni_sira = len(self.yuklu_kayitlar) + 1
        mod_kodu = self.cmb_toplu_mod.currentData() or "cumle"
        yeni_kayit = {
            "id": f"{mod_kodu}_{yeni_sira:04d}",
            "sira": yeni_sira,
            "arapca": "اَلْعِلْمُ نَافِعٌ.",
            "turkce": "İlim faydalıdır.",
            "kelime_turu": "isim" if mod_kodu == "tek_kelime" else "genel",
            "duygu_tonu": "otomatik",
            "cinsiyet": "IKISI",
            "referans_ses": "otomatik",
            "mod": mod_kodu,
        }
        self.yuklu_kayitlar.append(yeni_kayit)
        self._tabloyu_kayitlardan_doldur()

    def _tablodaki_vakiflari_yenile(self) -> None:
        self._tablo_yukleniyor = True
        try:
            mod_kodu = self.cmb_toplu_mod.currentData() or "cumle"
            preset = self.config_manager.get_preset(mod_kodu)
            hikmetli = bool(preset.get("hikmetli_durak_ekle", False))

            for r_idx in range(self.tablo_kuyruk.rowCount()):
                ar_item = self.tablo_kuyruk.item(r_idx, 1)
                if not ar_item:
                    continue
                arapca = ar_item.text().strip()
                kelime_turu = self.yuklu_kayitlar[r_idx].get("kelime_turu", "genel") if r_idx < len(self.yuklu_kayitlar) else "genel"
                akustik = arapca_akustik_metin_hazirla(arapca, kelime_turu=kelime_turu, hikmetli_durak_ekle=hikmetli)
                if self.tablo_kuyruk.item(r_idx, 2):
                    self.tablo_kuyruk.item(r_idx, 2).setText(akustik)
                if r_idx < len(self.yuklu_kayitlar):
                    self.yuklu_kayitlar[r_idx]["akustik_metin"] = akustik
        finally:
            self._tablo_yukleniyor = False

    def _tabloyu_temizle(self) -> None:
        if self.batch_worker and self.batch_worker.isRunning():
            self._toplu_islemi_durdur()
        self.yuklu_kayitlar.clear()
        self.secili_satir_indisleri.clear()
        self.aktif_okunan_satir = -1
        self.aktif_kaynak_dosya = "bos_liste"
        self.tablo_kuyruk.setRowCount(0)
        self.lbl_kuyruk_sayac.setText("📋 Adım 3 — Seslendirme Kuyruğu (Kaynak kaldırıldı — 0 kayıt)")
        self.progress_toplu.setValue(0)
        self.progress_toplu.setFormat("Hazır (%p%)")

    def _tablodaki_guncel_verileri_senkronize_et(self) -> None:
        mod_kodu = self.cmb_toplu_mod.currentData() or "cumle"
        preset = self.config_manager.get_preset(mod_kodu)
        hikmetli = bool(preset.get("hikmetli_durak_ekle", False))

        for r_idx in range(min(self.tablo_kuyruk.rowCount(), len(self.yuklu_kayitlar))):
            if self.tablo_kuyruk.item(r_idx, 0):
                self.yuklu_kayitlar[r_idx]["id"] = guvenli_kimlik_temizle(self.tablo_kuyruk.item(r_idx, 0).text().strip())
            if self.tablo_kuyruk.item(r_idx, 1):
                yeni_ar = self.tablo_kuyruk.item(r_idx, 1).text().strip()
                eski_ozet = self.yuklu_kayitlar[r_idx].get("kaynak_metin_ozeti", "")
                yeni_ozet = hashlib.sha1(yeni_ar.encode("utf-8")).hexdigest()[:10]
                self.yuklu_kayitlar[r_idx]["arapca"] = yeni_ar
                if eski_ozet != yeni_ozet:
                    kelime_turu = self.yuklu_kayitlar[r_idx].get("kelime_turu", "genel")
                    yeni_ak = arapca_akustik_metin_hazirla(yeni_ar, kelime_turu=kelime_turu, hikmetli_durak_ekle=hikmetli)
                    self.yuklu_kayitlar[r_idx]["akustik_metin"] = yeni_ak
                    self.yuklu_kayitlar[r_idx]["kaynak_metin_ozeti"] = yeni_ozet
                    if self.tablo_kuyruk.item(r_idx, 2):
                        self.tablo_kuyruk.item(r_idx, 2).setText(yeni_ak)
                elif self.tablo_kuyruk.item(r_idx, 2):
                    self.yuklu_kayitlar[r_idx]["akustik_metin"] = self.tablo_kuyruk.item(r_idx, 2).text().strip()

            if self.tablo_kuyruk.item(r_idx, 3):
                self.yuklu_kayitlar[r_idx]["turkce"] = self.tablo_kuyruk.item(r_idx, 3).text().strip()

            cmb_ses = self.tablo_kuyruk.cellWidget(r_idx, 4)
            if isinstance(cmb_ses, QComboBox):
                self.yuklu_kayitlar[r_idx]["referans_ses"] = str(cmb_ses.currentData() or "otomatik")

    def _asili_uretim_satirlarini_sifirla(self) -> None:
        """Screenshot_4_5.png'deki gibi '🎙️ Üretiliyor...' durumunda asılı kalan satırları '⏹️ Durduruldu' yapar."""
        self._tablo_yukleniyor = True
        try:
            for r in range(self.tablo_kuyruk.rowCount()):
                it = self.tablo_kuyruk.item(r, 5)
                if it and "🎙️" in it.text():
                    it.setText("⏹️ Durduruldu")
                    it.setForeground(QColor("#f59e0b"))
                if r == self.aktif_okunan_satir:
                    _tablo_satirini_vurgula(self.tablo_kuyruk, r, "normal", self.koyu_tema)
            self.aktif_okunan_satir = -1
        finally:
            self._tablo_yukleniyor = False

    def toplu_islemi_baslat(self, sadece_secili_indisler: Optional[List[int]] = None) -> None:
        if not self.yuklu_kayitlar:
            QMessageBox.warning(self, "Liste Boş", "Lütfen önce bir veri dosyası yükleyin veya satır ekleyin.")
            return

        # Eğer önceki işçi hâlâ GPU adımını bitiriyorsa güvenli şekilde bitmesini bekle (Kilitlenmeyi önler!)
        if self.batch_worker is not None and self.batch_worker.isRunning():
            self.batch_worker.durdur()
            if not self.batch_worker.wait(2500):
                QMessageBox.information(
                    self,
                    "GPU Serbest Bırakılıyor",
                    "Önceki işlem durduruluyor, ekran kartı belleği 1-2 saniye içinde hazır olacaktır. Lütfen tekrar tıklayın.",
                )
                return

        self._tablodaki_guncel_verileri_senkronize_et()
        secilen_motor_tipi = self.cmb_toplu_motor.currentData() or "SPARK_ARABIC"
        motor = self.ana_pencere.motoru_getir_veya_yukle(zorunlu_motor_tipi=secilen_motor_tipi)
        motor.durdur_istegi = False
        mod_kodu = self.cmb_toplu_mod.currentData() or "cumle"

        self.btn_toplu_baslat.setEnabled(False)
        self.btn_toplu_secmeli.setEnabled(False)
        self.btn_toplu_duraklat.setEnabled(True)
        self.btn_toplu_durdur.setEnabled(True)
        self.progress_toplu.setValue(2)
        self.progress_toplu.setFormat("Üretim başlatılıyor... (%p%)")

        worker = StudyoBatchWorker(
            motor=motor,
            config_manager=self.config_manager,
            kayitlar=self.yuklu_kayitlar,
            mod_kodu=mod_kodu,
            cikti_kok_klasor=self.edt_toplu_cikti.text().strip() or str(self.config_manager.get_default_output_dir()),
            cift_uretim_erkek_kadin=self.chk_toplu_cift.isChecked(),
            secilen_erkek_ref_id=self.cmb_toplu_erkek_ref.currentData() or "ref_erkek_1",
            secilen_kadin_ref_id=self.cmb_toplu_kadin_ref.currentData() or "ref_kadin_1",
            secilen_duygu_tonu=self.cmb_toplu_duygu.currentData() or "otomatik",
            mevcut_sesleri_atla=self.chk_mevcut_atla.isChecked() if sadece_secili_indisler is None else False,
            kaynak_dosya_adi=self.aktif_kaynak_dosya,
            sadece_secili_indisler=sadece_secili_indisler,
            zorunlu_motor_tipi=secilen_motor_tipi,
        )
        self.batch_worker = worker
        self._bekleyen_eski_isciler.append(worker)

        worker.ilerleme_sinyali.connect(self._toplu_ilerleme_guncelle)
        worker.satir_durum_sinyali.connect(self._toplu_satir_durum_guncelle)
        worker.tamamlandi_sinyali.connect(self._toplu_islem_tamamlandi)
        worker.finished.connect(lambda w=worker: self._isci_bellekten_temizle(w))
        worker.start()

    def _isci_bellekten_temizle(self, w: QThread) -> None:
        if w in self._bekleyen_eski_isciler:
            self._bekleyen_eski_isciler.remove(w)
        self.btn_toplu_baslat.setEnabled(True)
        self.btn_toplu_secmeli.setEnabled(True)
        self.btn_toplu_duraklat.setEnabled(False)
        self.btn_toplu_durdur.setEnabled(False)

    def _toplu_ilerleme_guncelle(self, tamamlanan: int, toplam: int, yuzde_metni: str) -> None:
        yuzde = int(round((tamamlanan / max(1, toplam)) * 100))
        self.progress_toplu.setValue(yuzde)
        self.progress_toplu.setFormat(f"Tamamlanan: {tamamlanan} / {toplam} ({yuzde_metni})")

    def _toplu_satir_durum_guncelle(
        self, satir_idx: int, durum: str, akustik_metin: str, erkek_veya_tek_yol: str, kadin_yol: str
    ) -> None:
        if satir_idx < 0 or satir_idx >= self.tablo_kuyruk.rowCount():
            return

        self._tablo_yukleniyor = True
        try:
            # Önceki aktif satırın vurgusunu normale veya tamamlanan rengine döndür
            if self.aktif_okunan_satir >= 0 and self.aktif_okunan_satir != satir_idx:
                eski_durum = (
                    self.tablo_kuyruk.item(self.aktif_okunan_satir, 5).text()
                    if self.tablo_kuyruk.item(self.aktif_okunan_satir, 5)
                    else ""
                )
                eski_tip = "tamam" if "✅" in eski_durum else ("hata" if "❌" in eski_durum else "normal")
                _tablo_satirini_vurgula(self.tablo_kuyruk, self.aktif_okunan_satir, eski_tip, self.koyu_tema)

            if self.tablo_kuyruk.item(satir_idx, 2) and akustik_metin:
                self.tablo_kuyruk.item(satir_idx, 2).setText(akustik_metin)

            durum_item = QTableWidgetItem(durum)
            durum_item.setToolTip(durum)
            self.tablo_kuyruk.setItem(satir_idx, 5, durum_item)

            if "🎙️" in durum:
                self.aktif_okunan_satir = satir_idx
                _tablo_satirini_vurgula(self.tablo_kuyruk, satir_idx, "aktif", self.koyu_tema)
            elif "✅" in durum or "⏭️" in durum:
                _tablo_satirini_vurgula(self.tablo_kuyruk, satir_idx, "tamam", self.koyu_tema)
            elif "❌" in durum:
                _tablo_satirini_vurgula(self.tablo_kuyruk, satir_idx, "hata", self.koyu_tema)
            else:
                _tablo_satirini_vurgula(self.tablo_kuyruk, satir_idx, "normal", self.koyu_tema)

            if (erkek_veya_tek_yol and os.path.exists(erkek_veya_tek_yol)) or (kadin_yol and os.path.exists(kadin_yol)):
                self.tablo_kuyruk.setCellWidget(
                    satir_idx, 6, self._dinleme_hucresi_olustur(erkek_veya_tek_yol, kadin_yol)
                )
                btn_yeniden = self.tablo_kuyruk.cellWidget(satir_idx, 7)
                if isinstance(btn_yeniden, QPushButton):
                    btn_yeniden.setText("🔄 Yeniden")

                if erkek_veya_tek_yol and os.path.exists(erkek_veya_tek_yol):
                    self.ana_pencere.son_erkek_veya_tek_ses = erkek_veya_tek_yol
                if kadin_yol and os.path.exists(kadin_yol):
                    self.ana_pencere.son_kadin_ses = kadin_yol
        finally:
            self._tablo_yukleniyor = False

    def _duraklat_veya_devam_et(self) -> None:
        if not self.batch_worker:
            return
        if self.batch_worker._duraklat_istegi:
            self.batch_worker.devam_et()
            self.btn_toplu_duraklat.setText("⏸️ Duraklat")
        else:
            self.batch_worker.duraklat()
            self.btn_toplu_duraklat.setText("▶️ Devam Et")

    def _toplu_islemi_durdur(self) -> None:
        if self.batch_worker is not None:
            self.batch_worker.durdur()
        if self.ana_pencere.studyo_motor is not None:
            self.ana_pencere.studyo_motor.durdur()

        self._asili_uretim_satirlarini_sifirla()
        self.btn_toplu_durdur.setEnabled(False)
        self.btn_toplu_duraklat.setEnabled(False)
        self.btn_toplu_duraklat.setText("⏸️ Duraklat")
        self.btn_toplu_baslat.setEnabled(True)
        self.btn_toplu_secmeli.setEnabled(True)
        self.progress_toplu.setFormat("⏹️ Durduruldu — Yeni işleme hazır")

    def _checkpoint_gecmisini_temizle(self) -> None:
        if not self.yuklu_kayitlar:
            return
        mod_kodu = self.cmb_toplu_mod.currentData() or "cumle"
        secilen_motor = self.cmb_toplu_motor.currentData() or "SPARK_ARABIC"
        cp = CheckpointYoneticisi()
        job_hash = cp.is_ozeti_olustur(
            kaynak_dosya_adi=self.aktif_kaynak_dosya,
            mod_kodu=mod_kodu,
            kayit_sayisi=len(self.yuklu_kayitlar),
            motor_tipi=secilen_motor,
            erkek_ref=self.cmb_toplu_erkek_ref.currentData() or "ref_erkek_1",
            kadin_ref=self.cmb_toplu_kadin_ref.currentData() or "ref_kadin_1",
            cift_uretim=self.chk_toplu_cift.isChecked(),
        )
        cp.is_gecmisini_temizle(job_hash)
        QMessageBox.information(self, "Geçmiş Sıfırlandı", "Bu veri setine ait Checkpoint geçmişi temizlendi.")

    def _toplu_islem_tamamlandi(self, ozet: Dict[str, Any]) -> None:
        self._asili_uretim_satirlarini_sifirla()
        self.btn_toplu_baslat.setEnabled(True)
        self.btn_toplu_secmeli.setEnabled(True)
        self.btn_toplu_duraklat.setEnabled(False)
        self.btn_toplu_duraklat.setText("⏸️ Duraklat")
        self.btn_toplu_durdur.setEnabled(False)

        if ozet.get("durduruldu_mu"):
            self.progress_toplu.setFormat("⏹️ Durduruldu — Yeni işleme hazır")
            return

        self.progress_toplu.setValue(100)
        self.progress_toplu.setFormat(
            f"✅ Tamamlandı | Üretilen: {ozet.get('basarili')} • Atlanan: {ozet.get('atlanan')} • Hatalı: {ozet.get('hatali')} ({ozet.get('gecen_saniye')} sn)"
        )

        if self.config_manager.user_settings.get("otomatik_oynat_toplu_bitis", False):
            if self.ana_pencere.son_erkek_veya_tek_ses and os.path.exists(self.ana_pencere.son_erkek_veya_tek_ses):
                self.ana_pencere.ses_dosyasini_cal(self.ana_pencere.son_erkek_veya_tek_ses)


# ==============================================================================
# SEKME 5: DİYALOG & UZUN METİN STÜDYOSU (CANLI SATIR VURGUSU & GÜVENLİ DURDURMA)
# ==============================================================================
class DiyalogUzunMetinSekmesi(QWidget):
    def __init__(self, ana_pencere):
        super().__init__(ana_pencere)
        self.ana_pencere = ana_pencere
        self.config_manager = ana_pencere.config_manager
        self.ozel_worker: Optional[QThread] = None
        self._bekleyen_ozel_isciler: List[QThread] = []
        self.diyalog_listesi: List[Dict[str, Any]] = list(GOMULU_DEMO_DIYALOGLAR)
        self.metin_listesi: List[Dict[str, Any]] = list(GOMULU_DEMO_METINLER)
        self.son_birlesik_diyalog_yolu: str = ""
        self.son_birlesik_metin_yolu: str = ""
        self._rol_rotasyon_sayaci: int = 0
        self.koyu_tema: bool = (self.config_manager.user_settings.get("tema_modu", "koyu") != "aydinlik")
        self._diyalog_tablo_yukleniyor: bool = False

        self._arayuzu_olustur()
        self._diyalog_ve_metin_secicilerini_yenile()

    def _arayuzu_olustur(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        self.alt_tabs = QTabWidget()
        layout.addWidget(self.alt_tabs)

        self.alt_tabs.addTab(self._alt_sekme_diyalog_olustur(), "🎭 A) Çoklu Rol Diyalog Stüdyosu (8 Karakter)")
        self.alt_tabs.addTab(self._alt_sekme_uzun_metin_olustur(), "📖 B) Uzun Metin / Paragraf Stüdyosu")

    def tema_guncelle(self, tema_kodu: str) -> None:
        self.koyu_tema = (tema_kodu != "aydinlik")

    def _alt_sekme_diyalog_olustur(self) -> QWidget:
        sayfa = QWidget()
        layout = QVBoxLayout(sayfa)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        adim1_kutu = QGroupBox("Adım 1 — Diyalog Seçin, Ses Motorunu Belirleyin ve Karakter Rollerini Atayın")
        ust_bar = QHBoxLayout(adim1_kutu)
        ust_bar.setContentsMargins(10, 8, 10, 6)
        ust_bar.setSpacing(6)

        ust_bar.addWidget(QLabel("Diyalog:"))
        self.cmb_hazir_diyalog = QComboBox()
        _kompakt_combobox_ayarla(self.cmb_hazir_diyalog, 150)
        self.cmb_hazir_diyalog.currentIndexChanged.connect(self._secili_diyalogu_tabloya_yukle)
        ust_bar.addWidget(self.cmb_hazir_diyalog, stretch=1)

        btn_harici_dlg = QPushButton("📂 JSON Aç")
        btn_harici_dlg.setFixedHeight(28)
        btn_harici_dlg.setStyleSheet("background-color: #059669; color: white; border: none;")
        btn_harici_dlg.clicked.connect(self._disaridan_diyalog_json_ac)
        ust_bar.addWidget(btn_harici_dlg)

        btn_dlg_kaynak_kaldir = QPushButton("✖️ Kaynağı Kaldır")
        btn_dlg_kaynak_kaldir.setFixedHeight(28)
        btn_dlg_kaynak_kaldir.setStyleSheet("background-color: #475569; color: white; border: none;")
        btn_dlg_kaynak_kaldir.clicked.connect(self._diyalog_kaynagini_kaldir)
        ust_bar.addWidget(btn_dlg_kaynak_kaldir)

        btn_dlg_demo = QPushButton("✨ Demo")
        btn_dlg_demo.setFixedHeight(28)
        btn_dlg_demo.clicked.connect(self._diyalog_demo_yukle)
        ust_bar.addWidget(btn_dlg_demo)

        ust_bar.addWidget(QLabel("Motor:"))
        self.cmb_diyalog_motor = QComboBox()
        _kompakt_combobox_ayarla(self.cmb_diyalog_motor, 155)
        aktif_m = self.config_manager.user_settings.get("aktif_motor_tercihi", "SPARK_ARABIC")
        _motor_secici_doldur(self.cmb_diyalog_motor, aktif_m)
        ust_bar.addWidget(self.cmb_diyalog_motor)

        btn_oto_rol = QPushButton("🎲 8 Sesten Otomatik Rol Ata")
        btn_oto_rol.setFixedHeight(28)
        btn_oto_rol.setStyleSheet("background-color: #0284c7; color: white; border: none;")
        btn_oto_rol.clicked.connect(lambda: self._diyalog_cakismasiz_ses_ata(kullanici_tikladi=True))
        ust_bar.addWidget(btn_oto_rol)

        btn_replik_ekle = QPushButton("➕ Replik")
        btn_replik_ekle.setFixedHeight(28)
        btn_replik_ekle.clicked.connect(self._diyalog_bos_replik_ekle)
        ust_bar.addWidget(btn_replik_ekle)

        btn_replik_sil = QPushButton("➖ Sil")
        btn_replik_sil.setFixedHeight(28)
        btn_replik_sil.clicked.connect(self._diyalog_secili_replik_sil)
        ust_bar.addWidget(btn_replik_sil)
        layout.addWidget(adim1_kutu)

        lbl_a2 = QLabel("📋 <b>Adım 2 — Diyalog Replikleri ve Konuşmacı Sesleri (Hücrelere Çift Tıklayarak Düzenleyebilirsiniz):</b>")
        lbl_a2.setStyleSheet("color: #0284c7; font-size: 9pt;")
        layout.addWidget(lbl_a2)

        self.tablo_diyalog = QTableWidget(0, 7)
        self.tablo_diyalog.verticalHeader().setDefaultSectionSize(38)
        self.tablo_diyalog.setHorizontalHeaderLabels([
            "Sıra",
            "Konuşmacı",
            "Cinsiyet",
            "Atanan Ses Karakteri",
            "Arapça Replik",
            "Canlı Vakıflı Okunuş",
            "Dinle",
        ])
        self.tablo_diyalog.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tablo_diyalog.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tablo_diyalog.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tablo_diyalog.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tablo_diyalog.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.tablo_diyalog.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.tablo_diyalog.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.tablo_diyalog.cellChanged.connect(self._diyalog_hucre_duzenlendi)
        layout.addWidget(self.tablo_diyalog, stretch=1)

        alt_bar = QHBoxLayout()
        alt_bar.setSpacing(6)
        alt_bar.addWidget(QLabel("Klasör:"))
        self.edt_diyalog_id = QLineEdit("demo_diyalog_01")
        self.edt_diyalog_id.setFixedWidth(95)
        alt_bar.addWidget(self.edt_diyalog_id)

        alt_bar.addWidget(QLabel("Boşluk:"))
        self.spn_diyalog_bosluk = QSpinBox()
        self.spn_diyalog_bosluk.setRange(100, 1500)
        self.spn_diyalog_bosluk.setSingleStep(50)
        self.spn_diyalog_bosluk.setValue(450)
        self.spn_diyalog_bosluk.setSuffix(" ms")
        alt_bar.addWidget(self.spn_diyalog_bosluk)

        self.btn_diyalog_uret = QPushButton("🎬 Seçiliyi Üret")
        self.btn_diyalog_uret.setFixedHeight(34)
        self.btn_diyalog_uret.setStyleSheet(
            "background-color: #059669; color: white; border: none; padding: 4px 10px; font-weight: bold;"
        )
        self.btn_diyalog_uret.clicked.connect(self._diyalog_sentez_ve_birlestir_baslat)
        alt_bar.addWidget(self.btn_diyalog_uret)

        self.btn_diyalog_coklu_uret = QPushButton("📚 Çoklu Seç & Üret...")
        self.btn_diyalog_coklu_uret.setFixedHeight(34)
        self.btn_diyalog_coklu_uret.setStyleSheet(
            "background-color: #7c3aed; color: white; border: none; padding: 4px 10px; font-weight: bold;"
        )
        self.btn_diyalog_coklu_uret.clicked.connect(self._coklu_diyalog_sec_ve_uret_diyalogu)
        alt_bar.addWidget(self.btn_diyalog_coklu_uret)

        self.btn_diyalog_durdur = QPushButton("⏹️ DURDUR")
        self.btn_diyalog_durdur.setFixedHeight(34)
        self.btn_diyalog_durdur.setEnabled(False)
        self.btn_diyalog_durdur.setStyleSheet("background-color: #dc2626; color: white; border: none; padding: 4px 10px;")
        self.btn_diyalog_durdur.clicked.connect(self._ozel_islemi_durdur)
        alt_bar.addWidget(self.btn_diyalog_durdur)

        self.progress_diyalog = QProgressBar()
        self.progress_diyalog.setFixedHeight(26)
        self.progress_diyalog.setMinimumWidth(220)
        self.progress_diyalog.setRange(0, 100)
        self.progress_diyalog.setValue(0)
        self.progress_diyalog.setFormat("Hazır (%p%)")
        alt_bar.addWidget(self.progress_diyalog, stretch=1)

        self.btn_diyalog_tam_dinle = QPushButton("🔊 Tümünü Dinle")
        self.btn_diyalog_tam_dinle.setFixedHeight(34)
        self.btn_diyalog_tam_dinle.setEnabled(False)
        self.btn_diyalog_tam_dinle.clicked.connect(lambda: self.ana_pencere.ses_dosyasini_cal(self.son_birlesik_diyalog_yolu))
        alt_bar.addWidget(self.btn_diyalog_tam_dinle)

        self.btn_diyalog_klasor_ac = QPushButton("📂 Klasörü Aç")
        self.btn_diyalog_klasor_ac.setFixedHeight(34)
        self.btn_diyalog_klasor_ac.setStyleSheet(
            "background-color: #0284c7; color: white; border: none; padding: 4px 10px; font-weight: bold;"
        )
        self.btn_diyalog_klasor_ac.clicked.connect(self._diyalog_cikti_klasorunu_ac)
        alt_bar.addWidget(self.btn_diyalog_klasor_ac)

        layout.addLayout(alt_bar)
        return sayfa

    def _alt_sekme_uzun_metin_olustur(self) -> QWidget:
        sayfa = QWidget()
        layout = QVBoxLayout(sayfa)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        adim1_kutu = QGroupBox("Adım 1 — Okuma Metnini Seçin, Anlatıcıyı Belirleyin ve Cümlelere Bölün")
        ust_bar = QHBoxLayout(adim1_kutu)
        ust_bar.setContentsMargins(10, 8, 10, 6)
        ust_bar.setSpacing(6)

        ust_bar.addWidget(QLabel("Metin:"))
        self.cmb_hazir_metin = QComboBox()
        _kompakt_combobox_ayarla(self.cmb_hazir_metin, 140)
        self.cmb_hazir_metin.currentIndexChanged.connect(self._secili_metni_yukle)
        ust_bar.addWidget(self.cmb_hazir_metin, stretch=1)

        btn_harici_metin = QPushButton("📂 Dosya Aç")
        btn_harici_metin.setFixedHeight(28)
        btn_harici_metin.setStyleSheet("background-color: #059669; color: white; border: none;")
        btn_harici_metin.clicked.connect(self._disaridan_metin_dosyasi_ac)
        ust_bar.addWidget(btn_harici_metin)

        btn_metin_kaynak_kaldir = QPushButton("✖️ Kaynağı Kaldır")
        btn_metin_kaynak_kaldir.setFixedHeight(28)
        btn_metin_kaynak_kaldir.setStyleSheet("background-color: #475569; color: white; border: none;")
        btn_metin_kaynak_kaldir.clicked.connect(self._metin_kaynagini_kaldir)
        ust_bar.addWidget(btn_metin_kaynak_kaldir)

        btn_metin_demo = QPushButton("✨ Demo")
        btn_metin_demo.setFixedHeight(28)
        btn_metin_demo.clicked.connect(self._metin_demo_yukle)
        ust_bar.addWidget(btn_metin_demo)

        ust_bar.addWidget(QLabel("Motor:"))
        self.cmb_metin_motor = QComboBox()
        _kompakt_combobox_ayarla(self.cmb_metin_motor, 155)
        aktif_m = self.config_manager.user_settings.get("aktif_motor_tercihi", "SPARK_ARABIC")
        _motor_secici_doldur(self.cmb_metin_motor, aktif_m)
        ust_bar.addWidget(self.cmb_metin_motor)

        ust_bar.addWidget(QLabel("Anlatıcı:"))
        self.cmb_metin_anlatici = QComboBox()
        _kompakt_combobox_ayarla(self.cmb_metin_anlatici, 135)
        for ses in self.config_manager.voice_pool:
            self.cmb_metin_anlatici.addItem(f"{ses.get('ad')}", ses["id"])
        ust_bar.addWidget(self.cmb_metin_anlatici)

        btn_bol = QPushButton("✂️ Cümlelere Böl")
        btn_bol.setFixedHeight(28)
        btn_bol.setStyleSheet("background-color: #0284c7; color: white; border: none;")
        btn_bol.clicked.connect(self._uzun_metni_parcalara_ayir_ve_tabloya_yaz)
        ust_bar.addWidget(btn_bol)
        layout.addWidget(adim1_kutu)

        self.txt_uzun_paragraf = QTextEdit()
        self.txt_uzun_paragraf.setLayoutDirection(Qt.RightToLeft)
        self.txt_uzun_paragraf.setFont(QFont("Traditional Arabic", 18))
        self.txt_uzun_paragraf.setMaximumHeight(78)
        self.txt_uzun_paragraf.setPlaceholderText("اِلْصَقِ النَّصَّ الْعَرَبِيَّ الطَّوِيلَ أَوِ الْفِقْرَةَ هُنَا...")
        layout.addWidget(self.txt_uzun_paragraf)

        self.tablo_metin_cumleler = QTableWidget(0, 5)
        self.tablo_metin_cumleler.verticalHeader().setDefaultSectionSize(38)
        self.tablo_metin_cumleler.setHorizontalHeaderLabels([
            "No",
            "Orijinal Cümle",
            "Vakıflı Akustik Metin (Düzenlenebilir)",
            "Durum",
            "Dinle",
        ])
        self.tablo_metin_cumleler.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tablo_metin_cumleler.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tablo_metin_cumleler.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tablo_metin_cumleler.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tablo_metin_cumleler.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.tablo_metin_cumleler, stretch=1)

        alt_bar = QHBoxLayout()
        alt_bar.setSpacing(6)
        alt_bar.addWidget(QLabel("Klasör:"))
        self.edt_metin_id = QLineEdit("demo_metin_01")
        self.edt_metin_id.setFixedWidth(95)
        alt_bar.addWidget(self.edt_metin_id)

        alt_bar.addWidget(QLabel("Nefes:"))
        self.spn_metin_bosluk = QSpinBox()
        self.spn_metin_bosluk.setRange(100, 1500)
        self.spn_metin_bosluk.setSingleStep(50)
        self.spn_metin_bosluk.setValue(300)
        self.spn_metin_bosluk.setSuffix(" ms")
        alt_bar.addWidget(self.spn_metin_bosluk)

        self.btn_metin_uret = QPushButton("🎧 Seçiliyi Üret")
        self.btn_metin_uret.setFixedHeight(34)
        self.btn_metin_uret.setStyleSheet(
            "background-color: #059669; color: white; border: none; padding: 4px 10px; font-weight: bold;"
        )
        self.btn_metin_uret.clicked.connect(self._uzun_metin_sentez_ve_birlestir_baslat)
        alt_bar.addWidget(self.btn_metin_uret)

        self.btn_metin_coklu_uret = QPushButton("📚 Çoklu Seç & Üret...")
        self.btn_metin_coklu_uret.setFixedHeight(34)
        self.btn_metin_coklu_uret.setStyleSheet(
            "background-color: #7c3aed; color: white; border: none; padding: 4px 10px; font-weight: bold;"
        )
        self.btn_metin_coklu_uret.clicked.connect(self._coklu_metin_sec_ve_uret_diyalogu)
        alt_bar.addWidget(self.btn_metin_coklu_uret)

        self.btn_metin_durdur = QPushButton("⏹️ DURDUR")
        self.btn_metin_durdur.setFixedHeight(34)
        self.btn_metin_durdur.setEnabled(False)
        self.btn_metin_durdur.setStyleSheet("background-color: #dc2626; color: white; border: none; padding: 4px 10px;")
        self.btn_metin_durdur.clicked.connect(self._ozel_islemi_durdur)
        alt_bar.addWidget(self.btn_metin_durdur)

        self.progress_metin = QProgressBar()
        self.progress_metin.setFixedHeight(26)
        self.progress_metin.setMinimumWidth(220)
        self.progress_metin.setRange(0, 100)
        self.progress_metin.setValue(0)
        self.progress_metin.setFormat("Hazır (%p%)")
        alt_bar.addWidget(self.progress_metin, stretch=1)

        self.btn_metin_tam_dinle = QPushButton("🔊 Tümünü Dinle")
        self.btn_metin_tam_dinle.setFixedHeight(34)
        self.btn_metin_tam_dinle.setEnabled(False)
        self.btn_metin_tam_dinle.clicked.connect(lambda: self.ana_pencere.ses_dosyasini_cal(self.son_birlesik_metin_yolu))
        alt_bar.addWidget(self.btn_metin_tam_dinle)

        self.btn_metin_klasor_ac = QPushButton("📂 Klasörü Aç")
        self.btn_metin_klasor_ac.setFixedHeight(34)
        self.btn_metin_klasor_ac.setStyleSheet(
            "background-color: #0284c7; color: white; border: none; padding: 4px 10px; font-weight: bold;"
        )
        self.btn_metin_klasor_ac.clicked.connect(self._metin_cikti_klasorunu_ac)
        alt_bar.addWidget(self.btn_metin_klasor_ac)

        layout.addLayout(alt_bar)
        return sayfa

    def _diyalog_hucre_duzenlendi(self, row: int, col: int) -> None:
        if self._diyalog_tablo_yukleniyor or col != 4:
            return
        ar_item = self.tablo_diyalog.item(row, 4)
        if not ar_item:
            return
        yeni_ak = arapca_akustik_metin_hazirla(ar_item.text().strip(), kelime_turu="genel", hikmetli_durak_ekle=False)
        self._diyalog_tablo_yukleniyor = True
        try:
            if self.tablo_diyalog.item(row, 5):
                self.tablo_diyalog.item(row, 5).setText(yeni_ak)
        finally:
            self._diyalog_tablo_yukleniyor = False

    def _ozel_isci_hazirla_ve_bekle(self) -> bool:
        if self.ozel_worker is not None and self.ozel_worker.isRunning():
            if hasattr(self.ozel_worker, "durdur"):
                self.ozel_worker.durdur()
            if not self.ozel_worker.wait(2500):
                QMessageBox.information(
                    self,
                    "GPU Serbest Bırakılıyor",
                    "Önceki işlem durduruluyor, lütfen 1-2 saniye sonra tekrar tıklayın.",
                )
                return False
        return True

    def _ozel_isci_bitti_temizle(self, w: QThread) -> None:
        if w in self._bekleyen_ozel_isciler:
            self._bekleyen_ozel_isciler.remove(w)
        self.btn_diyalog_uret.setEnabled(True)
        self.btn_diyalog_coklu_uret.setEnabled(True)
        self.btn_diyalog_durdur.setEnabled(False)
        self.btn_metin_uret.setEnabled(True)
        self.btn_metin_coklu_uret.setEnabled(True)
        self.btn_metin_durdur.setEnabled(False)

    def _ozel_islemi_durdur(self) -> None:
        if self.ozel_worker is not None and hasattr(self.ozel_worker, "durdur"):
            self.ozel_worker.durdur()
        if self.ana_pencere.studyo_motor is not None:
            self.ana_pencere.studyo_motor.durdur()

        for r in range(self.tablo_diyalog.rowCount()):
            _tablo_satirini_vurgula(self.tablo_diyalog, r, "normal", self.koyu_tema, metin_sutunlari=(0, 1, 2, 4))
        for r in range(self.tablo_metin_cumleler.rowCount()):
            _tablo_satirini_vurgula(self.tablo_metin_cumleler, r, "normal", self.koyu_tema, metin_sutunlari=(0, 1, 3))

        self.btn_diyalog_uret.setEnabled(True)
        self.btn_diyalog_coklu_uret.setEnabled(True)
        self.btn_diyalog_durdur.setEnabled(False)
        self.progress_diyalog.setFormat("⏹️ Durduruldu — Yeni işleme hazır")

        self.btn_metin_uret.setEnabled(True)
        self.btn_metin_coklu_uret.setEnabled(True)
        self.btn_metin_durdur.setEnabled(False)
        self.progress_metin.setFormat("⏹️ Durduruldu — Yeni işleme hazır")

    def _diyalog_cikti_klasorunu_ac(self) -> None:
        ust = self.config_manager.get_default_output_dir() / "diyaloglar"
        dlg_id = guvenli_kimlik_temizle(self.edt_diyalog_id.text().strip(), varsayilan="")
        alt = ust / dlg_id if dlg_id else ust
        _klasoru_sistemde_ac(alt if alt.exists() else ust)

    def _metin_cikti_klasorunu_ac(self) -> None:
        ust = self.config_manager.get_default_output_dir() / "metinler"
        m_id = guvenli_kimlik_temizle(self.edt_metin_id.text().strip(), varsayilan="")
        alt = ust / m_id if m_id else ust
        _klasoru_sistemde_ac(alt if alt.exists() else ust)

    def _diyalog_kaynagini_kaldir(self) -> None:
        self._ozel_islemi_durdur()
        self.diyalog_listesi.clear()
        self.cmb_hazir_diyalog.blockSignals(True)
        self.cmb_hazir_diyalog.clear()
        self.cmb_hazir_diyalog.blockSignals(False)
        self.tablo_diyalog.setRowCount(0)
        self.edt_diyalog_id.setText("")
        self.progress_diyalog.setValue(0)
        self.progress_diyalog.setFormat("Kaynak kaldırıldı (Liste boş)")

    def _diyalog_demo_yukle(self) -> None:
        self._ozel_islemi_durdur()
        self.diyalog_listesi = list(GOMULU_DEMO_DIYALOGLAR)
        self._diyalog_ve_metin_secicilerini_yenile()

    def _metin_kaynagini_kaldir(self) -> None:
        self._ozel_islemi_durdur()
        self.metin_listesi.clear()
        self.cmb_hazir_metin.blockSignals(True)
        self.cmb_hazir_metin.clear()
        self.cmb_hazir_metin.blockSignals(False)
        self.txt_uzun_paragraf.clear()
        self.tablo_metin_cumleler.setRowCount(0)
        self.edt_metin_id.setText("")
        self.progress_metin.setValue(0)
        self.progress_metin.setFormat("Kaynak kaldırıldı (Metin boş)")

    def _metin_demo_yukle(self) -> None:
        self._ozel_islemi_durdur()
        self.metin_listesi = list(GOMULU_DEMO_METINLER)
        self._diyalog_ve_metin_secicilerini_yenile()

    def _diyalog_ve_metin_secicilerini_yenile(self) -> None:
        self.cmb_hazir_diyalog.blockSignals(True)
        self.cmb_hazir_diyalog.clear()
        for i, d in enumerate(self.diyalog_listesi):
            self.cmb_hazir_diyalog.addItem(f"{d.get('id')} - {d.get('baslik_tr', '')}", i)
        self.cmb_hazir_diyalog.blockSignals(False)
        if self.diyalog_listesi:
            self.cmb_hazir_diyalog.setCurrentIndex(0)
            self._secili_diyalogu_tabloya_yukle()

        self.cmb_hazir_metin.blockSignals(True)
        self.cmb_hazir_metin.clear()
        for i, m in enumerate(self.metin_listesi):
            self.cmb_hazir_metin.addItem(f"{m.get('id')} - {m.get('baslik_tr', '')}", i)
        self.cmb_hazir_metin.blockSignals(False)
        if self.metin_listesi:
            self.cmb_hazir_metin.setCurrentIndex(0)
            self._secili_metni_yukle()

    def _disaridan_diyalog_json_ac(self) -> None:
        dosya, _ = QFileDialog.getOpenFileName(
            self,
            "Diyalog JSON Dosyası Seç",
            str(Path.home() / "Desktop"),
            "JSON Dosyaları (*.json)",
        )
        if not dosya:
            return
        try:
            with open(dosya, "r", encoding="utf-8-sig") as f:
                veri = json.load(f)
            if isinstance(veri, list) and veri and isinstance(veri[0], dict) and "satirlar" in veri[0]:
                self.diyalog_listesi = veri
                self._diyalog_ve_metin_secicilerini_yenile()
                QMessageBox.information(
                    self,
                    "Diyaloglar Yüklendi",
                    f"Toplam {len(veri)} diyalog başarıyla yüklendi.\n\n"
                    "• Tek bir diyaloğu üretmek için '🎬 Seçiliyi Üret' butonuna,\n"
                    "• İstediğiniz diyalogları seçip ayrı klasörlerde üretmek için '📚 Çoklu Seç & Üret...' butonuna basabilirsiniz.",
                )
            else:
                QMessageBox.warning(self, "Format Uyarısı", "Seçilen JSON dosyası çoklu diyalog formatında değil.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya okunamadı:\n{e}")

    def _disaridan_metin_dosyasi_ac(self) -> None:
        dosya, _ = QFileDialog.getOpenFileName(
            self,
            "Okuma Metni Dosyası Seç (.json / .txt)",
            str(Path.home() / "Desktop"),
            "Metin Dosyaları (*.json *.txt)",
        )
        if not dosya:
            return
        try:
            if dosya.lower().endswith(".json"):
                with open(dosya, "r", encoding="utf-8-sig") as f:
                    veri = json.load(f)
                if isinstance(veri, list) and veri and isinstance(veri[0], dict) and "satirlar" in veri[0]:
                    self.metin_listesi = veri
                    self._diyalog_ve_metin_secicilerini_yenile()
                    QMessageBox.information(self, "Yüklendi", f"{len(veri)} okuma metni başarıyla yüklendi.")
            else:
                with open(dosya, "r", encoding="utf-8-sig") as f:
                    icerik = f.read().strip()
                self.edt_metin_id.setText(guvenli_kimlik_temizle(Path(dosya).stem))
                self.txt_uzun_paragraf.setPlainText(icerik)
                self._uzun_metni_parcalara_ayir_ve_tabloya_yaz()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya okunamadı:\n{e}")

    def _secili_diyalogu_tabloya_yukle(self) -> None:
        idx = self.cmb_hazir_diyalog.currentData()
        if idx is None or idx < 0 or idx >= len(self.diyalog_listesi):
            return
        dlg = self.diyalog_listesi[idx]
        self.edt_diyalog_id.setText(guvenli_kimlik_temizle(str(dlg.get("id", "demo_diyalog_01"))))

        self._diyalog_tablo_yukleniyor = True
        try:
            satirlar = dlg.get("satirlar", [])
            self.tablo_diyalog.setRowCount(len(satirlar))
            arapca_font = QFont("Traditional Arabic", 15)

            for r_idx, s in enumerate(satirlar):
                sira = str(s.get("sira", r_idx + 1))
                konusmaci = str(s.get("konusmaci", "Ömer"))
                cinsiyet = str(s.get("cinsiyet", "E")).upper()
                arapca = str(s.get("arapca", ""))
                akustik = arapca_akustik_metin_hazirla(arapca, kelime_turu="genel", hikmetli_durak_ekle=False)

                self.tablo_diyalog.setItem(r_idx, 0, QTableWidgetItem(sira))
                self.tablo_diyalog.setItem(r_idx, 1, QTableWidgetItem(konusmaci))
                self.tablo_diyalog.setItem(r_idx, 2, QTableWidgetItem(cinsiyet))

                cmb_ses = QComboBox()
                _kompakt_combobox_ayarla(cmb_ses, 155)
                for ses in self.config_manager.voice_pool:
                    cmb_ses.addItem(f"{ses.get('ad')}", ses["id"])
                self.tablo_diyalog.setCellWidget(r_idx, 3, cmb_ses)

                ar_item = QTableWidgetItem(arapca)
                ar_item.setFont(arapca_font)
                ar_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tablo_diyalog.setItem(r_idx, 4, ar_item)

                ak_item = QTableWidgetItem(akustik)
                ak_item.setFont(arapca_font)
                ak_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                ak_item.setForeground(QColor("#10b981"))
                self.tablo_diyalog.setItem(r_idx, 5, ak_item)

                btn_dinle = QPushButton("🎧 Referans")
                btn_dinle.clicked.connect(lambda checked=False, row=r_idx: self._diyalog_satir_referansini_dinle(row))
                self.tablo_diyalog.setCellWidget(r_idx, 6, btn_dinle)

            self._diyalog_cakismasiz_ses_ata(kullanici_tikladi=False)
        finally:
            self._diyalog_tablo_yukleniyor = False

    def _diyalog_satir_referansini_dinle(self, row_idx: int) -> None:
        cmb = self.tablo_diyalog.cellWidget(row_idx, 3)
        if isinstance(cmb, QComboBox):
            ref_id = cmb.currentData()
            yol = self.config_manager.resolve_voice_path(ref_id)
            self.ana_pencere.ses_dosyasini_cal(str(yol))

    def _diyalog_cakismasiz_ses_ata(self, kullanici_tikladi: bool = False) -> None:
        if self.tablo_diyalog.rowCount() == 0:
            return

        if kullanici_tikladi:
            self._rol_rotasyon_sayaci += 1

        gecici_satirlar = []
        for r_idx in range(self.tablo_diyalog.rowCount()):
            konusmaci = (self.tablo_diyalog.item(r_idx, 1).text() if self.tablo_diyalog.item(r_idx, 1) else f"Kisi_{r_idx}").strip()
            cinsiyet = (self.tablo_diyalog.item(r_idx, 2).text() if self.tablo_diyalog.item(r_idx, 2) else "E").strip().upper()
            gecici_satirlar.append({"konusmaci": konusmaci, "cinsiyet": cinsiyet})

        harita = diyalog_icin_otomatik_rol_haritasi_olustur(
            self.config_manager.voice_pool,
            gecici_satirlar,
            rotasyon_sayaci=self._rol_rotasyon_sayaci,
        )

        ses_ad_sozlugu = {v["id"]: v.get("ad", v["id"]) for v in self.config_manager.voice_pool}

        for r_idx in range(self.tablo_diyalog.rowCount()):
            konusmaci = gecici_satirlar[r_idx]["konusmaci"]
            cmb = self.tablo_diyalog.cellWidget(r_idx, 3)
            if isinstance(cmb, QComboBox) and konusmaci in harita:
                idx_ses = cmb.findData(harita[konusmaci])
                if idx_ses >= 0:
                    cmb.setCurrentIndex(idx_ses)

        if kullanici_tikladi:
            ozet_parcalar = [f"{k} -> {ses_ad_sozlugu.get(vid, vid)}" for k, vid in harita.items()]
            ozet_metin = " | ".join(ozet_parcalar)
            self.progress_diyalog.setFormat(f"🎲 Yeni Roller: {ozet_metin[:55]}")

    def _diyalog_bos_replik_ekle(self) -> None:
        self._diyalog_tablo_yukleniyor = True
        try:
            r_idx = self.tablo_diyalog.rowCount()
            self.tablo_diyalog.insertRow(r_idx)
            self.tablo_diyalog.setItem(r_idx, 0, QTableWidgetItem(str(r_idx + 1)))
            self.tablo_diyalog.setItem(r_idx, 1, QTableWidgetItem("Ömer"))
            self.tablo_diyalog.setItem(r_idx, 2, QTableWidgetItem("E"))

            cmb_ses = QComboBox()
            _kompakt_combobox_ayarla(cmb_ses, 155)
            for ses in self.config_manager.voice_pool:
                cmb_ses.addItem(f"{ses.get('ad')}", ses["id"])
            self.tablo_diyalog.setCellWidget(r_idx, 3, cmb_ses)

            ar = "اَلسَّلَامُ عَلَيْكُمْ وَرَحْمَةُ اللَّهِ."
            ak = arapca_akustik_metin_hazirla(ar)
            self.tablo_diyalog.setItem(r_idx, 4, QTableWidgetItem(ar))
            self.tablo_diyalog.setItem(r_idx, 5, QTableWidgetItem(ak))
            btn = QPushButton("🎧 Referans")
            btn.clicked.connect(lambda checked=False, row=r_idx: self._diyalog_satir_referansini_dinle(row))
            self.tablo_diyalog.setCellWidget(r_idx, 6, btn)
        finally:
            self._diyalog_tablo_yukleniyor = False

    def _diyalog_secili_replik_sil(self) -> None:
        secili = self.tablo_diyalog.currentRow()
        if secili >= 0:
            self.tablo_diyalog.removeRow(secili)

    def _diyalog_sentez_ve_birlestir_baslat(self) -> None:
        if self.tablo_diyalog.rowCount() == 0:
            QMessageBox.warning(self, "Tablo Boş", "Seslendirilecek diyalog repliği bulunamadı.")
            return

        if not self._ozel_isci_hazirla_ve_bekle():
            return

        satirlar: List[Dict[str, Any]] = []
        for r_idx in range(self.tablo_diyalog.rowCount()):
            cins = (self.tablo_diyalog.item(r_idx, 2).text() if self.tablo_diyalog.item(r_idx, 2) else "E").strip().upper()
            arapca = (self.tablo_diyalog.item(r_idx, 4).text() if self.tablo_diyalog.item(r_idx, 4) else "").strip()
            if not arapca:
                continue
            yeni_ak = arapca_akustik_metin_hazirla(arapca, kelime_turu="genel", hikmetli_durak_ekle=False)
            if self.tablo_diyalog.item(r_idx, 5):
                self.tablo_diyalog.item(r_idx, 5).setText(yeni_ak)
            cmb = self.tablo_diyalog.cellWidget(r_idx, 3)
            ref_id = cmb.currentData() if isinstance(cmb, QComboBox) else "ref_erkek_1"
            satirlar.append({
                "arapca": arapca,
                "akustik": yeni_ak,
                "ref_id": ref_id,
                "dosya_adi": f"satir_{r_idx + 1:02d}_{cins}.mp3",
            })

        dlg_id = guvenli_kimlik_temizle(self.edt_diyalog_id.text().strip(), varsayilan="demo_diyalog_01")
        cikti_klasor = guvenli_hedef_yol_cozumle(self.config_manager.get_default_output_dir() / "diyaloglar", dlg_id)
        preset = self.config_manager.get_preset("diyalog")
        secilen_motor = self.cmb_diyalog_motor.currentData() or "SPARK_ARABIC"

        self.btn_diyalog_uret.setEnabled(False)
        self.btn_diyalog_coklu_uret.setEnabled(False)
        self.btn_diyalog_durdur.setEnabled(True)
        self.progress_diyalog.setValue(2)
        self.progress_diyalog.setFormat("Başlatılıyor... (%p%)")

        worker = DiyalogVeMetinOzelWorker(
            ana_pencere=self.ana_pencere,
            satirlar=satirlar,
            mod_kodu="diyalog",
            secilen_motor_tipi=secilen_motor,
            cikti_klasoru=cikti_klasor,
            birlesik_dosya_adi="diyalog_tamami.mp3",
            bosluk_ms=int(self.spn_diyalog_bosluk.value()),
            hiz=float(preset.get("hiz", 0.94)),
            temperature=float(preset.get("temperature", 0.66)),
            referans_ses_kullan=(secilen_motor != "FAST_DIRECT_TTS"),
        )
        self.ozel_worker = worker
        self._bekleyen_ozel_isciler.append(worker)
        worker.ilerleme_sinyali.connect(self._diyalog_ilerleme_guncelle)
        worker.satir_durum_sinyali.connect(self._diyalog_satir_durumu_guncelle)
        worker.tamamlandi_sinyali.connect(self._diyalog_birlestirme_tamamlandi)
        worker.finished.connect(lambda w=worker: self._ozel_isci_bitti_temizle(w))
        worker.start()

    def _coklu_diyalog_sec_ve_uret_diyalogu(self) -> None:
        if not self.diyalog_listesi:
            QMessageBox.warning(self, "Diyalog Yok", "Lütfen önce '📂 JSON Aç' ile bir diyalog dosyası yükleyin.")
            return

        dlg = CokluKayitSecimDialog(
            self.diyalog_listesi,
            baslik="Çoklu Diyalog Seçimi — Ayrı Klasörlerde Toplu Seslendirme",
            varsayilan_hepsi_secili=True,
            koyu_tema=self.koyu_tema,
            parent=self,
        )
        if dlg.exec() != QDialog.Accepted or not dlg.secilen_indisler:
            return

        # İlk seçilen diyaloğu ekranda göster
        ilk_idx = dlg.secilen_indisler[0]
        if 0 <= ilk_idx < self.cmb_hazir_diyalog.count():
            self.cmb_hazir_diyalog.setCurrentIndex(ilk_idx)

        if not dlg.hemen_uret_istendi:
            return

        if not self._ozel_isci_hazirla_ve_bekle():
            return

        secilenler = [self.diyalog_listesi[i] for i in dlg.secilen_indisler]
        secilen_motor = self.cmb_diyalog_motor.currentData() or "SPARK_ARABIC"
        ust_klasor = self.config_manager.get_default_output_dir() / "diyaloglar"

        self.btn_diyalog_uret.setEnabled(False)
        self.btn_diyalog_coklu_uret.setEnabled(False)
        self.btn_diyalog_durdur.setEnabled(True)
        self.progress_diyalog.setValue(2)
        self.progress_diyalog.setFormat("Çoklu üretim başlatılıyor... (%p%)")

        worker = CokluGrupSentezWorker(
            ana_pencere=self.ana_pencere,
            secilen_gruplar=secilenler,
            mod_kodu="diyalog",
            secilen_motor_tipi=secilen_motor,
            ust_cikti_klasoru=ust_klasor,
            birlesik_dosya_adi="diyalog_tamami.mp3",
            bosluk_ms=int(self.spn_diyalog_bosluk.value()),
        )
        self.ozel_worker = worker
        self._bekleyen_ozel_isciler.append(worker)
        worker.ilerleme_sinyali.connect(self._diyalog_ilerleme_guncelle)
        worker.tamamlandi_sinyali.connect(self._diyalog_birlestirme_tamamlandi)
        worker.finished.connect(lambda w=worker: self._ozel_isci_bitti_temizle(w))
        worker.start()

    def _diyalog_ilerleme_guncelle(self, tamam: int, toplam: int, mesaj: str) -> None:
        yuzde = int(round((tamam / float(max(1, toplam))) * 100))
        self.progress_diyalog.setValue(yuzde)
        self.progress_diyalog.setFormat(f"%p% — {mesaj[:45]}")

    def _diyalog_satir_durumu_guncelle(self, idx: int, durum: str, dosya_yolu: str) -> None:
        if idx < 0 or idx >= self.tablo_diyalog.rowCount():
            return
        if "🎙️" in durum:
            for r in range(self.tablo_diyalog.rowCount()):
                if r != idx:
                    _tablo_satirini_vurgula(self.tablo_diyalog, r, "normal", self.koyu_tema, metin_sutunlari=(0, 1, 2, 4))
            _tablo_satirini_vurgula(self.tablo_diyalog, idx, "aktif", self.koyu_tema, metin_sutunlari=(0, 1, 2, 4))
        elif "✅" in durum:
            _tablo_satirini_vurgula(self.tablo_diyalog, idx, "tamam", self.koyu_tema, metin_sutunlari=(0, 1, 2, 4))
        elif "❌" in durum:
            _tablo_satirini_vurgula(self.tablo_diyalog, idx, "hata", self.koyu_tema, metin_sutunlari=(0, 1, 2, 4))

        if dosya_yolu and os.path.exists(dosya_yolu):
            btn = QPushButton("🔊 Dinle")
            btn.setStyleSheet("background-color: #0284c7; color: white; border: none;")
            btn.clicked.connect(lambda checked=False, p=dosya_yolu: self.ana_pencere.ses_dosyasini_cal(p))
            self.tablo_diyalog.setCellWidget(idx, 6, btn)

    def _diyalog_birlestirme_tamamlandi(self, basarili: bool, mesaj: str, birlesik_yol: str) -> None:
        self.btn_diyalog_uret.setEnabled(True)
        self.btn_diyalog_coklu_uret.setEnabled(True)
        self.btn_diyalog_durdur.setEnabled(False)
        if basarili and birlesik_yol and os.path.exists(birlesik_yol):
            self.progress_diyalog.setValue(100)
            self.progress_diyalog.setFormat("✅ Tamamlandı (%100)")
            self.son_birlesik_diyalog_yolu = birlesik_yol
            self.ana_pencere.son_erkek_veya_tek_ses = birlesik_yol
            self.btn_diyalog_tam_dinle.setEnabled(True)
            self.ana_pencere.ses_dosyasini_cal(birlesik_yol)
        else:
            self.progress_diyalog.setFormat("⏹️ Durduruldu / Yeni işleme hazır")
            if "durduruldu" not in mesaj.lower():
                QMessageBox.warning(self, "Diyalog Uyarısı", mesaj)

    def _secili_metni_yukle(self) -> None:
        idx = self.cmb_hazir_metin.currentData()
        if idx is None or idx < 0 or idx >= len(self.metin_listesi):
            return
        metin = self.metin_listesi[idx]
        self.edt_metin_id.setText(guvenli_kimlik_temizle(str(metin.get("id", "demo_metin_01"))))
        cumleler = [str(s.get("arapca", "")).strip() for s in metin.get("satirlar", []) if s.get("arapca")]
        self.txt_uzun_paragraf.setPlainText("\n".join(cumleler))
        self._uzun_metni_parcalara_ayir_ve_tabloya_yaz()

    def _uzun_metni_parcalara_ayir_ve_tabloya_yaz(self) -> None:
        paragraf = self.txt_uzun_paragraf.toPlainText().strip()
        cumleler = uzun_metni_cumlelere_bol(paragraf)
        self.tablo_metin_cumleler.setRowCount(len(cumleler))
        arapca_font = QFont("Traditional Arabic", 15)

        for r_idx, c in enumerate(cumleler):
            akustik = arapca_akustik_metin_hazirla(c, kelime_turu="genel", hikmetli_durak_ekle=False)
            self.tablo_metin_cumleler.setItem(r_idx, 0, QTableWidgetItem(f"{r_idx + 1}"))

            orij_item = QTableWidgetItem(c)
            orij_item.setFont(arapca_font)
            orij_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tablo_metin_cumleler.setItem(r_idx, 1, orij_item)

            ak_item = QTableWidgetItem(akustik)
            ak_item.setFont(arapca_font)
            ak_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            ak_item.setForeground(QColor("#10b981"))
            self.tablo_metin_cumleler.setItem(r_idx, 2, ak_item)

            self.tablo_metin_cumleler.setItem(r_idx, 3, QTableWidgetItem("⏳ Hazır"))
            btn = QPushButton("-")
            btn.setEnabled(False)
            self.tablo_metin_cumleler.setCellWidget(r_idx, 4, btn)

    def _uzun_metin_sentez_ve_birlestir_baslat(self) -> None:
        if self.tablo_metin_cumleler.rowCount() == 0:
            self._uzun_metni_parcalara_ayir_ve_tabloya_yaz()
        if self.tablo_metin_cumleler.rowCount() == 0:
            QMessageBox.warning(self, "Metin Boş", "Lütfen seslendirilecek bir Arapça metin girin.")
            return

        if not self._ozel_isci_hazirla_ve_bekle():
            return

        anlatici_id = self.cmb_metin_anlatici.currentData() or "ref_erkek_1"
        secilen_motor = self.cmb_metin_motor.currentData() or "SPARK_ARABIC"
        satirlar: List[Dict[str, Any]] = []
        for r_idx in range(self.tablo_metin_cumleler.rowCount()):
            arapca = (self.tablo_metin_cumleler.item(r_idx, 1).text() if self.tablo_metin_cumleler.item(r_idx, 1) else "").strip()
            akustik = (self.tablo_metin_cumleler.item(r_idx, 2).text() if self.tablo_metin_cumleler.item(r_idx, 2) else "").strip()
            if not arapca:
                continue
            satirlar.append({
                "arapca": arapca,
                "akustik": akustik or arapca_akustik_metin_hazirla(arapca),
                "ref_id": anlatici_id,
                "dosya_adi": f"satir_{r_idx + 1:02d}.mp3",
            })

        m_id = guvenli_kimlik_temizle(self.edt_metin_id.text().strip(), varsayilan="demo_metin_01")
        cikti_klasor = guvenli_hedef_yol_cozumle(self.config_manager.get_default_output_dir() / "metinler", m_id)
        preset = self.config_manager.get_preset("uzun_metin")

        self.btn_metin_uret.setEnabled(False)
        self.btn_metin_coklu_uret.setEnabled(False)
        self.btn_metin_durdur.setEnabled(True)
        self.progress_metin.setValue(2)
        self.progress_metin.setFormat("Başlatılıyor... (%p%)")

        worker = DiyalogVeMetinOzelWorker(
            ana_pencere=self.ana_pencere,
            satirlar=satirlar,
            mod_kodu="uzun_metin",
            secilen_motor_tipi=secilen_motor,
            cikti_klasoru=cikti_klasor,
            birlesik_dosya_adi="tamami.mp3",
            bosluk_ms=int(self.spn_metin_bosluk.value()),
            hiz=float(preset.get("hiz", 0.92)),
            temperature=float(preset.get("temperature", 0.62)),
            referans_ses_kullan=(secilen_motor != "FAST_DIRECT_TTS"),
        )
        self.ozel_worker = worker
        self._bekleyen_ozel_isciler.append(worker)
        worker.ilerleme_sinyali.connect(self._metin_ilerleme_guncelle)
        worker.satir_durum_sinyali.connect(self._metin_satir_durumu_guncelle)
        worker.tamamlandi_sinyali.connect(self._metin_birlestirme_tamamlandi)
        worker.finished.connect(lambda w=worker: self._ozel_isci_bitti_temizle(w))
        worker.start()

    def _coklu_metin_sec_ve_uret_diyalogu(self) -> None:
        if not self.metin_listesi:
            QMessageBox.warning(self, "Metin Yok", "Lütfen önce '📂 Dosya Aç' ile çoklu okuma metni JSON dosyası yükleyin.")
            return

        dlg = CokluKayitSecimDialog(
            self.metin_listesi,
            baslik="Çoklu Okuma Metni Seçimi — Ayrı Klasörlerde Toplu Seslendirme",
            varsayilan_hepsi_secili=True,
            koyu_tema=self.koyu_tema,
            parent=self,
        )
        if dlg.exec() != QDialog.Accepted or not dlg.secilen_indisler:
            return

        ilk_idx = dlg.secilen_indisler[0]
        if 0 <= ilk_idx < self.cmb_hazir_metin.count():
            self.cmb_hazir_metin.setCurrentIndex(ilk_idx)

        if not dlg.hemen_uret_istendi:
            return

        if not self._ozel_isci_hazirla_ve_bekle():
            return

        secilenler = [self.metin_listesi[i] for i in dlg.secilen_indisler]
        secilen_motor = self.cmb_metin_motor.currentData() or "SPARK_ARABIC"
        anlatici_id = self.cmb_metin_anlatici.currentData() or "ref_erkek_1"
        ust_klasor = self.config_manager.get_default_output_dir() / "metinler"

        self.btn_metin_uret.setEnabled(False)
        self.btn_metin_coklu_uret.setEnabled(False)
        self.btn_metin_durdur.setEnabled(True)
        self.progress_metin.setValue(2)
        self.progress_metin.setFormat("Çoklu üretim başlatılıyor... (%p%)")

        worker = CokluGrupSentezWorker(
            ana_pencere=self.ana_pencere,
            secilen_gruplar=secilenler,
            mod_kodu="uzun_metin",
            secilen_motor_tipi=secilen_motor,
            ust_cikti_klasoru=ust_klasor,
            birlesik_dosya_adi="tamami.mp3",
            bosluk_ms=int(self.spn_metin_bosluk.value()),
            varsayilan_anlatici_id=anlatici_id,
        )
        self.ozel_worker = worker
        self._bekleyen_ozel_isciler.append(worker)
        worker.ilerleme_sinyali.connect(self._metin_ilerleme_guncelle)
        worker.tamamlandi_sinyali.connect(self._metin_birlestirme_tamamlandi)
        worker.finished.connect(lambda w=worker: self._ozel_isci_bitti_temizle(w))
        worker.start()

    def _metin_ilerleme_guncelle(self, tamam: int, toplam: int, mesaj: str) -> None:
        yuzde = int(round((tamam / float(max(1, toplam))) * 100))
        self.progress_metin.setValue(yuzde)
        self.progress_metin.setFormat(f"%p% — {mesaj[:45]}")

    def _metin_satir_durumu_guncelle(self, idx: int, durum: str, dosya_yolu: str) -> None:
        if idx < 0 or idx >= self.tablo_metin_cumleler.rowCount():
            return
        self.tablo_metin_cumleler.setItem(idx, 3, QTableWidgetItem(durum))
        if "🎙️" in durum:
            for r in range(self.tablo_metin_cumleler.rowCount()):
                if r != idx:
                    _tablo_satirini_vurgula(self.tablo_metin_cumleler, r, "normal", self.koyu_tema, metin_sutunlari=(0, 1, 3))
            _tablo_satirini_vurgula(self.tablo_metin_cumleler, idx, "aktif", self.koyu_tema, metin_sutunlari=(0, 1, 3))
        elif "✅" in durum:
            _tablo_satirini_vurgula(self.tablo_metin_cumleler, idx, "tamam", self.koyu_tema, metin_sutunlari=(0, 1, 3))
        elif "❌" in durum:
            _tablo_satirini_vurgula(self.tablo_metin_cumleler, idx, "hata", self.koyu_tema, metin_sutunlari=(0, 1, 3))

        if dosya_yolu and os.path.exists(dosya_yolu):
            btn = QPushButton("🔊 Dinle")
            btn.setStyleSheet("background-color: #0284c7; color: white; border: none;")
            btn.clicked.connect(lambda checked=False, p=dosya_yolu: self.ana_pencere.ses_dosyasini_cal(p))
            self.tablo_metin_cumleler.setCellWidget(idx, 4, btn)

    def _metin_birlestirme_tamamlandi(self, basarili: bool, mesaj: str, birlesik_yol: str) -> None:
        self.btn_metin_uret.setEnabled(True)
        self.btn_metin_coklu_uret.setEnabled(True)
        self.btn_metin_durdur.setEnabled(False)
        if basarili and birlesik_yol and os.path.exists(birlesik_yol):
            self.progress_metin.setValue(100)
            self.progress_metin.setFormat("✅ Tamamlandı (%100)")
            self.son_birlesik_metin_yolu = birlesik_yol
            self.ana_pencere.son_erkek_veya_tek_ses = birlesik_yol
            self.btn_metin_tam_dinle.setEnabled(True)
            self.ana_pencere.ses_dosyasini_cal(birlesik_yol)
        else:
            self.progress_metin.setFormat("⏹️ Durduruldu / Yeni işleme hazır")
            if "durduruldu" not in mesaj.lower():
                QMessageBox.warning(self, "Metin Uyarısı", mesaj)