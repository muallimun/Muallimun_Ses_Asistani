#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MUALLİMUN AI SES STÜDYOSU PRO - MODÜL, MODEL REHBERİ VE TIKLA-KUR YÖNETİM MERKEZİ (ui/setup_wizard.py)
Özellikler:
  1. 3 Gerçek Seslendirme Motoru Rehberi (⭐ Spark-TTS Önerilen, ⚡ Hızlı Direkt TTS, 🗣️ Coqui XTTS v2)
  2. Gerçekçi Model Yetenek Rozetleri (Yerel GPU / Çevrimiçi Servis / Hareke & Klonlama Bilgilendirmesi)
  3. EXE Dağıtımı İçin Gömülü Python (runtime/python.exe) Destekli 'Tıkla-Kur / Onar' İşçisi
  4. Aydınlık ve Karanlık Stüdyo Teması (Light / Dark Mode) Tam Uyumu
"""

import os
import sys
import shutil
import subprocess
import importlib
import importlib.metadata
from pathlib import Path
from typing import List, Dict, Any, Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor, QCloseEvent
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTabWidget,
    QRadioButton,
    QButtonGroup,
    QMessageBox,
    QFrame,
)

from core.config_manager import ConfigManager, PROJECT_ROOT
from core.studyo_motoru import (
    SPARK_HF_MODEL_ID,
    gpu_vram_durumu_getir,
    referans_sesi_on_temizle,
)
from ui.rehber_ve_guncelleyici import profesyonel_arapca_font_olustur


def _python_yorumlayici_bul() -> str:
    """
    Uygulama normal Python ile çalışırken 'sys.executable' döndürür.
    PyInstaller ile .EXE yapıldığında ise uygulama klasöründeki gömülü
    'runtime/python.exe' veya sistemdeki Python yorumlayıcısını bulur;
    böylece EXE içinden 'pip install' çağrıldığında arayüz kendini tekrar açmaz.
    """
    if not getattr(sys, "frozen", False):
        return sys.executable

    adaylar = [
        PROJECT_ROOT / "runtime" / "python.exe",
        Path(sys.executable).resolve().parent / "runtime" / "python.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python" / "Python312" / "python.exe",
    ]
    for aday in adaylar:
        if aday.exists():
            return str(aday)

    sistem_py = shutil.which("python") or shutil.which("py")
    if sistem_py:
        return sistem_py
    raise RuntimeError(
        "Paket kurulumu için gömülü Python (runtime/python.exe) veya sistem Python yorumlayıcısı bulunamadı."
    )


# ==============================================================================
# 1. DESTEKLENEN 3 SES MODELİ VE GERÇEKÇİ KULLANIM REHBERİ
# ==============================================================================
SES_MODELLERI_REHBERI: List[Dict[str, Any]] = [
    {
        "kod": "SPARK_ARABIC",
        "ad": "1. ⭐ IbrahimSalah/Arabic-TTS-Spark (24kHz BiCodec — Önerilen Ana Ses Klonlama Motoru)",
        "rozet": "⭐ EN YÜKSEK KALİTE — ÖNERİLEN (Yerel GPU / Çevrimdışı)",
        "rozet_renk": "#10b981",
        "hf_repo": "IbrahimSalah/Arabic-TTS-Spark",
        "gereksinim": "NVIDIA GPU (4GB+ VRAM) veya CPU • Çevrimdışı Çalışır",
        "amac": "8 Stüdyo Karakterini veya Özel Sesinizi Klonlayarak Harekeli Arapça Eğitim Materyali Üretimi",
        "aciklama": (
            "Referans ses ile referans Arapça metni (Prompt Text) birlikte işleyerek konuşmacının ses rengini klonlar. "
            "Tam harekeli Arapça kelimeler, gramer cümleleri, atasözleri ve diyaloglar için en doğal mahreç ve ses kalitesini sunar."
        ),
        "tooltip": (
            "⭐ ÖNERİLEN ANA STÜDYO MOTORU:\n"
            "• Harekeli Arapça metinlerde en yüksek telaffuz ve ses klonlama kalitesini sağlar.\n"
            "• Model bir kez indirildikten sonra internet gerektirmeden yerel ekran kartınızda çalışır."
        ),
        "pip_paketler": ["transformers==4.48.3", "accelerate==1.2.1", "huggingface_hub", "einops", "einx", "omegaconf", "soxr"],
    },
    {
        "kod": "FAST_DIRECT_TTS",
        "ad": "2. ⚡ Hızlı Direkt Neural TTS (Çevrimiçi Hazır Ses Servisi + 24kHz Stüdyo DSP)",
        "rozet": "🌐 ÇEVRİMİÇİ HIZLI SERVİS (İnternet Gerekir • 0 MB VRAM)",
        "rozet_renk": "#0284c7",
        "hf_repo": "edge-tts",
        "gereksinim": "İnternet Bağlantısı • Ekran Kartı (VRAM) Gerekmez",
        "amac": "Hızlı Ön-İzleme, Harekesiz/Harekeli Metinler ve Ekran Kartsız Bilgisayarlarda Seri Üretim",
        "aciklama": (
            "Yerel GPU modeli yüklemeden Microsoft Edge çevrimiçi neural ses servisini (Hamed, Shakir, Zariyah, Salma) kullanır "
            "ve çıktıyı 24kHz Stüdyo DSP'den geçirir. Referans WAV dosyasını klonlamaz; seçilen role uygun hazır Arapça ses kullanır."
        ),
        "tooltip": (
            "⚡ HIZLI DİREKT NEURAL TTS:\n"
            "• İnternet bağlantısı gerektirir; ekran kartı belleği (VRAM) kullanmaz.\n"
            "• Referans ses klonlaması yapmaz, hazır standart Arapça neural sesleri kullanır."
        ),
        "pip_paketler": ["edge-tts"],
    },
    {
        "kod": "XTTS_STUDIO",
        "ad": "3. 🗣️ Coqui XTTS v2 Studio (Opsiyonel / Alternatif Çok Dilli Klonlama Motoru)",
        "rozet": "⚠️ ALTERNATİF / DENEYSEL (Arapça Kalitesi Spark-TTS Kadar Yüksek Değildir)",
        "rozet_renk": "#f59e0b",
        "hf_repo": "tts_models/multilingual/multi-dataset/xtts_v2",
        "gereksinim": "NVIDIA GPU (4GB+ VRAM) + coqui-tts Paketi",
        "amac": "Metin Dökümü Olmayan Kısa Seslerden Deneysel Ses Rengi Kopyalama",
        "aciklama": (
            "17 dili destekleyen genel amaçlı bir modeldir. Ancak Arapça hareke hassasiyeti, mahreç netliği ve tonlama doğallığı "
            "1. sıradaki Spark-TTS kadar yüksek değildir. Arapça ders materyalleri için 1. model (Spark-TTS) önerilir."
        ),
        "tooltip": (
            "⚠️ GERÇEKÇİ KALİTE NOTU:\n"
            "Coqui XTTS v2 genel amaçlı çok dilli bir model olduğu için Arapça hareke ve mahreç kalitesi\n"
            "Spark-TTS kadar doğal değildir. Yalnızca alternatif/deneysel amaçla sunulmuştur."
        ),
        "pip_paketler": ["coqui-tts", "transformers==4.48.3", "accelerate==1.2.1", "six"],
    },
]

# ==============================================================================
# 2. MODÜL VE KÜTÜPHANE TABLOSU TANIMLARI (8 TEMEL BİLEŞEN)
# ==============================================================================
MODUL_KONTROL_LISTESI: List[Dict[str, Any]] = [
    {
        "id": "torch_cuda",
        "ad": "PyTorch + CUDA (GPU Hızlandırıcı)",
        "import_adi": "torch",
        "dist_adi": "torch",
        "aciklama": "NVIDIA ekran kartı üzerinde yapay zeka ses sentezini çalıştıran ana motor.",
        "kurulum_tipi": "torch_cu121",
        "zorunlu": True,
    },
    {
        "id": "torchaudio",
        "ad": "Torchaudio (BiCodec MelSpectrogram)",
        "import_adi": "torchaudio",
        "dist_adi": "torchaudio",
        "aciklama": "Spark-TTS BiCodec ses çözücüsü için MelSpectrogram ve Resample modülü.",
        "kurulum_tipi": "torchaudio_cu121",
        "zorunlu": True,
    },
    {
        "id": "transformers",
        "ad": "Transformers 4.48.3 ve HuggingFace Hub",
        "import_adi": "transformers",
        "dist_adi": "transformers",
        "aciklama": "IbrahimSalah/Arabic-TTS-Spark modelini indiren ve çalıştıran uyumlu model çatısı.",
        "kurulum_tipi": "pip",
        "pip_paketler": ["transformers==4.48.3", "accelerate==1.2.1", "huggingface_hub"],
        "zorunlu": True,
    },
    {
        "id": "studyo_dsp",
        "ad": "5-Katmanlı Stüdyo DSP Paketleri",
        "import_adi": "scipy",
        "dist_adi": "scipy",
        "aciklama": "SoundFile, SciPy, Librosa ve Soxr (24kHz filtreleme, gürültü kapısı ve yüksek kaliteli resample).",
        "kurulum_tipi": "pip",
        "pip_paketler": ["soundfile", "scipy", "librosa", "soxr", "einops", "einx", "omegaconf"],
        "zorunlu": True,
    },
    {
        "id": "edge_tts",
        "ad": "Edge-TTS (⚡ Çevrimiçi Hızlı Direkt TTS)",
        "import_adi": "edge_tts",
        "dist_adi": "edge-tts",
        "aciklama": "İnternet üzerinden hızlı Arapça ses üretimi sağlayan çevrimiçi neural motor.",
        "kurulum_tipi": "pip",
        "pip_paketler": ["edge-tts"],
        "zorunlu": True,
    },
    {
        "id": "openpyxl",
        "ad": "OpenPyXL (Excel .xlsx Şablon Motoru)",
        "import_adi": "openpyxl",
        "dist_adi": "openpyxl",
        "aciklama": "Toplu seslendirme için renkli ve açılır listeli Excel (.xlsx) şablonları üretir.",
        "kurulum_tipi": "pip",
        "pip_paketler": ["openpyxl"],
        "zorunlu": True,
    },
    {
        "id": "coqui_tts",
        "ad": "Coqui TTS (Opsiyonel XTTS v2 Motoru)",
        "import_adi": "TTS",
        "dist_adi": "coqui-tts",
        "aciklama": "Alternatif XTTS v2 çok dilli ses klonlama motoru (Transformers 4.48.3 kilidi korunarak kurulur).",
        "kurulum_tipi": "pip",
        "pip_paketler": ["coqui-tts", "transformers==4.48.3", "accelerate==1.2.1", "six"],
        "zorunlu": False,
    },
    {
        "id": "ffmpeg",
        "ad": "FFmpeg (MP3 Dönüştürücü, Limiter ve Hız/Atempo)",
        "import_adi": "ffmpeg_bin",
        "dist_adi": "ffmpeg",
        "aciklama": "Üretilen sesleri kırpılmasız 192kbps MP3 formatına çevirmek ve hızını ayarlamak için sistem aracı.",
        "kurulum_tipi": "ffmpeg",
        "zorunlu": True,
    },
]


# ==============================================================================
# 3. ARKA PLAN KURULUM VE İNDİRME İŞÇİSİ (GÖMÜLÜ PYTHON DESTEKLİ QTHREAD)
# ==============================================================================
class TekilKurulumWorker(QThread):
    ilerleme_sinyali = Signal(int, str)
    log_sinyali = Signal(str)
    tamamlandi_sinyali = Signal(bool, str)

    def __init__(
        self,
        gorev_tipi: str,
        config_manager: ConfigManager,
        pip_paketler: Optional[List[str]] = None,
        hf_repo_id: Optional[str] = None,
    ):
        super().__init__()
        self.gorev_tipi = gorev_tipi
        self.config_manager = config_manager
        self.pip_paketler = pip_paketler or []
        self.hf_repo_id = hf_repo_id
        self._durdur_istegi = False
        self._aktif_proc: Optional[subprocess.Popen] = None

    def durdur(self) -> None:
        self._durdur_istegi = True
        if self._aktif_proc is not None:
            try:
                self._aktif_proc.terminate()
            except Exception:
                pass

    def _komut_calistir(self, komut: List[str]) -> None:
        self._aktif_proc = subprocess.Popen(
            komut,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        son_satirlar: List[str] = []
        if self._aktif_proc.stdout is not None:
            for satir in self._aktif_proc.stdout:
                if self._durdur_istegi:
                    self._aktif_proc.terminate()
                    raise RuntimeError("Kurulum işlemi kullanıcı tarafından durduruldu.")
                temiz = satir.strip()
                if temiz:
                    son_satirlar.append(temiz)
                    self.log_sinyali.emit(f"   {temiz}")
        self._aktif_proc.wait()
        if self._durdur_istegi:
            raise RuntimeError("Kurulum işlemi kullanıcı tarafından durduruldu.")
        if self._aktif_proc.returncode != 0:
            ozet_hata = "\n".join(son_satirlar[-4:]) if son_satirlar else f"Hata kodu: {self._aktif_proc.returncode}"
            raise RuntimeError(ozet_hata)

    def run(self) -> None:
        try:
            py_exe = _python_yorumlayici_bul()

            if self.gorev_tipi == "torch_cu121":
                self.ilerleme_sinyali.emit(20, "PyTorch CUDA (2.5.1+cu121) kuruluyor / onarılıyor...")
                self.log_sinyali.emit("📦 Çakışan torchvision kaldırılıp torch==2.5.1+cu121 kuruluyor...")
                subprocess.call([py_exe, "-m", "pip", "uninstall", "-y", "torchvision"])
                self._komut_calistir([
                    py_exe, "-m", "pip", "install",
                    "torch==2.5.1+cu121", "torchaudio==2.5.1+cu121",
                    "--index-url", "https://download.pytorch.org/whl/cu121"
                ])
                self.ilerleme_sinyali.emit(100, "PyTorch + Torchaudio CUDA hazır!")
                self.tamamlandi_sinyali.emit(True, "PyTorch 2.5.1+cu121 ve Torchaudio başarıyla kuruldu.")
                return

            if self.gorev_tipi == "torchaudio_cu121":
                import torch
                t_ver = torch.__version__.split("+")[0]
                cuda_ek = "+cu121" if "+cu121" in torch.__version__ else ""
                paket = f"torchaudio=={t_ver}{cuda_ek}"
                self.ilerleme_sinyali.emit(30, f"{paket} kuruluyor...")
                self.log_sinyali.emit(f"📦 Mevcut PyTorch korunarak {paket} kuruluyor...")
                komut = [py_exe, "-m", "pip", "install", paket, "--no-deps"]
                if cuda_ek:
                    komut += ["--index-url", "https://download.pytorch.org/whl/cu121"]
                self._komut_calistir(komut)
                self.ilerleme_sinyali.emit(100, "Torchaudio hazır!")
                self.tamamlandi_sinyali.emit(True, f"{paket} başarıyla kuruldu!")
                return

            if self.gorev_tipi == "pip" and self.pip_paketler:
                paket_metni = ", ".join(self.pip_paketler)
                self.ilerleme_sinyali.emit(25, f"Paketler kuruluyor: {paket_metni}")
                self.log_sinyali.emit(f"📦 Pip ile kuruluyor: {paket_metni}")
                self._komut_calistir([py_exe, "-m", "pip", "install", *self.pip_paketler])

                import torch
                if shutil.which("nvidia-smi") and not torch.cuda.is_available():
                    self.log_sinyali.emit("⚡ CUDA PyTorch kilidi korunuyor (torch==2.5.1+cu121)...")
                    self._komut_calistir([
                        py_exe, "-m", "pip", "install",
                        "torch==2.5.1+cu121", "torchaudio==2.5.1+cu121", "--no-deps",
                        "--index-url", "https://download.pytorch.org/whl/cu121"
                    ])

                self.ilerleme_sinyali.emit(100, "Paket kurulumu tamamlandı!")
                self.tamamlandi_sinyali.emit(True, f"Kurulum başarıyla tamamlandı: {paket_metni}")
                return

            if self.gorev_tipi == "ffmpeg":
                self.ilerleme_sinyali.emit(30, "FFmpeg winget üzerinden kontrol ediliyor / kuruluyor...")
                self.log_sinyali.emit("🎞️ Windows Paket Yöneticisi (winget) ile FFmpeg kuruluyor...")
                subprocess.call([
                    "winget", "install", "--id=Gyan.FFmpeg", "-e",
                    "--accept-source-agreements", "--accept-package-agreements"
                ])
                self.ilerleme_sinyali.emit(100, "FFmpeg işlemi tamamlandı.")
                self.tamamlandi_sinyali.emit(
                    True,
                    "FFmpeg kurulum komutu tamamlandı (Etkili olması için uygulamayı yeniden başlatabilirsiniz)."
                )
                return

            if self.gorev_tipi in ("model_indir", "ref_temizle"):
                repo = str(self.hf_repo_id or "").strip()
                self.ilerleme_sinyali.emit(25, "Referans sesler 24kHz DSP ön-temizliğinden geçiriliyor...")
                temizlenen_sayisi = 0
                eksik_yerlesik_sesler: List[str] = []

                for ses_kaydi in self.config_manager.voice_pool:
                    if self._durdur_istegi:
                        raise RuntimeError("İşlem kullanıcı tarafından durduruldu.")
                    yol = self.config_manager.resolve_voice_path(ses_kaydi["id"])
                    if yol.exists() and yol.stat().st_size > 1000:
                        referans_sesi_on_temizle(yol)
                        temizlenen_sayisi += 1
                        self.log_sinyali.emit(f"   🎵 Ön-temizlendi: {yol.name}")
                    elif ses_kaydi.get("yerlesik", False):
                        eksik_yerlesik_sesler.append(ses_kaydi.get("dosya", ses_kaydi["id"]))

                if eksik_yerlesik_sesler:
                    self.log_sinyali.emit(
                        f"   ℹ️ Not: {len(eksik_yerlesik_sesler)} yerleşik ses dosyası dizinde bulunamadı ({', '.join(eksik_yerlesik_sesler[:4])})."
                    )

                # Yalnızca açıkça bir HuggingFace repo kimliği verilmişse model indirme/doğrulama yap!
                if repo and "/" in repo and not repo.startswith("tts_models"):
                    self.ilerleme_sinyali.emit(60, f"HuggingFace modeli indiriliyor / doğrulanıyor: {repo}")
                    self.log_sinyali.emit(f"📥 Model dosyaları kontrol ediliyor: {repo}")
                    from huggingface_hub import snapshot_download
                    yerel_yol = snapshot_download(repo_id=repo)
                    self.log_sinyali.emit(f"✅ Model çevrimdışı kullanıma hazır: {yerel_yol}")
                    self.ilerleme_sinyali.emit(100, "Model ve referans sesler hazır!")
                    self.tamamlandi_sinyali.emit(
                        True,
                        f"'{repo}' modeli ve {temizlenen_sayisi} referans ses önbelleği başarıyla doğrulandı!",
                    )
                else:
                    self.ilerleme_sinyali.emit(100, "Referans ses ön-temizliği tamamlandı!")
                    self.tamamlandi_sinyali.emit(
                        True,
                        f"Toplam {temizlenen_sayisi} referans ses dosyası 24kHz standardında ön-temizlikten geçirilip önbelleğe alındı!",
                    )
                return

        except Exception as e:
            self.log_sinyali.emit(f"❌ İşlem durduruldu / hata:\n{e}")
            self.tamamlandi_sinyali.emit(False, str(e))


# ==============================================================================
# 4. KURULUM, MODEL SEÇİMİ VE MODÜL YÖNETİM DİYALOĞU (AYDINLIK / KOYU TEMA UYUMLU)
# ==============================================================================
class SetupWizardDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.ana_pencere = parent
        self.worker: Optional[TekilKurulumWorker] = None

        self.setWindowTitle("⚙️ Muallimun Stüdyo — Ses Modelleri Rehberi, Kütüphane (Tıkla-Kur) ve Referans Denetimi")
        self.setMinimumSize(980, 600)
        self.resize(1100, 640)

        self._arayuzu_olustur()
        self._tema_stili_uygula()
        self.sistem_durumunu_yenile()

    def _tema_stili_uygula(self) -> None:
        tema = self.config_manager.user_settings.get("tema_modu", "koyu")
        if tema == "aydinlik":
            self.setStyleSheet("""
                QDialog { background-color: #f8fafc; color: #0f172a; font-family: 'Segoe UI'; font-size: 9.5pt; }
                QToolTip { background-color: #ffffff; color: #0f172a; border: 1px solid #0284c7; padding: 5px; border-radius: 4px; }
                QTabWidget::pane { border: 1px solid #cbd5e1; border-radius: 8px; background-color: #ffffff; }
                QTabBar::tab {
                    background-color: #e2e8f0; color: #475569; border: 1px solid #cbd5e1;
                    padding: 8px 16px; margin-right: 4px; border-top-left-radius: 7px; border-top-right-radius: 7px; font-weight: bold;
                }
                QTabBar::tab:selected { background-color: #ffffff; color: #0284c7; border-top: 2px solid #0284c7; }
                QFrame#modelKart { background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 8px; }
                QFrame#modelKartOnerilen { background-color: #ecfdf5; border: 2px solid #10b981; border-radius: 8px; }
                QLabel, QRadioButton { background-color: transparent; color: #0f172a; }
                QRadioButton { spacing: 8px; font-weight: bold; font-size: 10pt; color: #0369a1; }
                QRadioButton::indicator { width: 18px; height: 18px; border-radius: 10px; border: 2px solid #0284c7; background-color: #ffffff; }
                QRadioButton::indicator:checked { background-color: #10b981; border: 3px solid #0284c7; }
                QPushButton { background-color: #0284c7; color: white; border: none; border-radius: 6px; padding: 6px 12px; font-weight: bold; }
                QPushButton:hover { background-color: #0369a1; }
                QPushButton:disabled { background-color: #cbd5e1; color: #64748b; }
                QTableWidget { background-color: #ffffff; color: #0f172a; gridline-color: #e2e8f0; border: 1px solid #cbd5e1; border-radius: 6px; }
                QHeaderView::section { background-color: #f1f5f9; color: #0369a1; padding: 6px; border: 1px solid #cbd5e1; font-weight: bold; }
                QTextEdit { background-color: #0f172a; color: #a7f3d0; border: 1px solid #cbd5e1; border-radius: 6px; font-family: Consolas, monospace; font-size: 9pt; }
                QProgressBar { border: 1px solid #cbd5e1; border-radius: 5px; text-align: center; background-color: #e2e8f0; color: #0f172a; font-weight: bold; }
                QProgressBar::chunk { background-color: #10b981; border-radius: 4px; }
            """)
        else:
            self.setStyleSheet("""
                QDialog { background-color: #0b0f19; color: #f8fafc; font-family: 'Segoe UI'; font-size: 9.5pt; }
                QToolTip { background-color: #0f172a; color: #f8fafc; border: 1px solid #38bdf8; padding: 5px; border-radius: 4px; }
                QTabWidget::pane { border: 1px solid #1e293b; border-radius: 8px; background-color: #0f172a; }
                QTabBar::tab {
                    background-color: #111827; color: #94a3b8; border: 1px solid #1e293b;
                    padding: 8px 16px; margin-right: 4px; border-top-left-radius: 7px; border-top-right-radius: 7px; font-weight: bold;
                }
                QTabBar::tab:selected { background-color: #0f172a; color: #38bdf8; border-top: 2px solid #0ea5e9; }
                QFrame#modelKart { background-color: #111827; border: 1px solid #1e293b; border-radius: 8px; }
                QFrame#modelKartOnerilen { background-color: #0c192c; border: 2px solid #10b981; border-radius: 8px; }
                QLabel, QRadioButton { background-color: transparent; color: #e2e8f0; }
                QRadioButton { spacing: 8px; font-weight: bold; font-size: 10pt; color: #38bdf8; }
                QRadioButton::indicator { width: 18px; height: 18px; border-radius: 10px; border: 2px solid #38bdf8; background-color: #090d16; }
                QRadioButton::indicator:checked { background-color: #10b981; border: 3px solid #38bdf8; }
                QPushButton { background-color: #0284c7; color: white; border: none; border-radius: 6px; padding: 6px 12px; font-weight: bold; }
                QPushButton:hover { background-color: #0369a1; }
                QPushButton:disabled { background-color: #334155; color: #94a3b8; }
                QTableWidget { background-color: #090d16; color: #f8fafc; gridline-color: #1e293b; border: 1px solid #1e293b; border-radius: 6px; }
                QHeaderView::section { background-color: #111827; color: #38bdf8; padding: 6px; border: 1px solid #1e293b; font-weight: bold; }
                QTextEdit { background-color: #020617; color: #a7f3d0; border: 1px solid #1e293b; border-radius: 6px; font-family: Consolas, monospace; font-size: 9pt; }
                QProgressBar { border: 1px solid #334155; border-radius: 5px; text-align: center; background-color: #090d16; color: white; font-weight: bold; }
                QProgressBar::chunk { background-color: #10b981; border-radius: 4px; }
            """)

    def _arayuzu_olustur(self) -> None:
        ana_layout = QVBoxLayout(self)
        ana_layout.setContentsMargins(12, 10, 12, 10)
        ana_layout.setSpacing(8)

        ust_bar = QHBoxLayout()
        self.lbl_gpu = QLabel("🚀 GPU: Kontrol ediliyor...")
        self.lbl_gpu.setToolTip("Bilgisayarınızdaki aktif grafik işlemci (GPU), kullanılan model belleği ve gerçek boş VRAM durumu.")
        self.lbl_gpu.setStyleSheet("color: #10b981; font-weight: bold; font-size: 9.5pt;")

        self.lbl_onerilen_bilgi = QLabel("")
        self.lbl_onerilen_bilgi.setToolTip("Donanım gücünüze ve boş VRAM miktarına göre önerilen çalışma kademesi.")
        self.lbl_onerilen_bilgi.setStyleSheet(
            "background-color: #1e293b; color: #38bdf8; padding: 4px 10px; border-radius: 5px; font-weight: bold; font-size: 9pt;"
        )
        ust_bar.addWidget(self.lbl_gpu)
        ust_bar.addStretch()
        ust_bar.addWidget(self.lbl_onerilen_bilgi)
        ana_layout.addLayout(ust_bar)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._sekme_1_model_secim_merkezi(), "🧠 1. Ses Modelleri Seçimi && Rehberi")
        self.tabs.setTabToolTip(
            0, "⭐ Önerilen Spark-TTS klonlama motoru ile çevrimiçi Hızlı Direkt TTS arasında seçim yapın."
        )
        self.tabs.addTab(self._sekme_2_kutuphane_tikla_kur(), "📦 2. Modül && Kütüphane Durumu (Tıkla-Kur)")
        self.tabs.setTabToolTip(
            1, "Eksik veya onarılması gereken Python kütüphanelerini ve FFmpeg aracını tek tıkla kurun."
        )
        self.tabs.addTab(self._sekme_3_referans_ses_denetimi(), "🎵 3. 8 Stüdyo Referans Sesi Denetimi")
        self.tabs.setTabToolTip(
            2, "8 stüdyo referans sesinin varlığını kontrol edin, dinleyin ve 24kHz ön-temizlikten geçirin."
        )
        ana_layout.addWidget(self.tabs, stretch=1)

        prog_bar_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(24)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        prog_bar_layout.addWidget(self.progress_bar, stretch=1)

        self.btn_islem_durdur = QPushButton("⏹️ İşlemi Durdur")
        self.btn_islem_durdur.setFixedHeight(24)
        self.btn_islem_durdur.setEnabled(False)
        self.btn_islem_durdur.setStyleSheet("background-color: #dc2626; color: white; padding: 2px 12px;")
        self.btn_islem_durdur.clicked.connect(self._aktif_islemi_durdur)
        prog_bar_layout.addWidget(self.btn_islem_durdur)
        ana_layout.addLayout(prog_bar_layout)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFixedHeight(78)
        self.txt_log.setPlaceholderText("Kurulum ve model doğrulama çıktıları burada görünür...")
        ana_layout.addWidget(self.txt_log)

        btn_layout = QHBoxLayout()
        self.btn_yenile = QPushButton("🔄 Tüm Durumları Yenile")
        self.btn_yenile.clicked.connect(self.sistem_durumunu_yenile)

        self.btn_varsayilan_spark = QPushButton("⭐ Önerilen Spark-TTS Modelini Varsayılan Yap")
        self.btn_varsayilan_spark.setStyleSheet("background-color: #0284c7; padding: 7px 14px;")
        self.btn_varsayilan_spark.clicked.connect(self._spark_varsayilan_sec)

        self.btn_kapat = QPushButton("Seçimi Kaydet ve Stüdyoya Dön ➡️")
        self.btn_kapat.setStyleSheet("background-color: #059669; padding: 7px 18px;")
        self.btn_kapat.clicked.connect(self._kaydet_ve_kapat)

        btn_layout.addWidget(self.btn_yenile)
        btn_layout.addWidget(self.btn_varsayilan_spark)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_kapat)
        ana_layout.addLayout(btn_layout)

    def _spark_varsayilan_sec(self) -> None:
        for btn in self.model_radio_grup.buttons():
            if btn.property("model_kodu") == "SPARK_ARABIC":
                btn.setChecked(True)
                break
        self.config_manager.user_settings["aktif_motor_tercihi"] = "SPARK_ARABIC"
        self.config_manager.save_user_settings()
        self.txt_log.append("⭐ 'IbrahimSalah/Arabic-TTS-Spark' ana stüdyo motoru olarak seçildi.")

    def _sekme_1_model_secim_merkezi(self) -> QWidget:
        sayfa = QWidget()
        dis_layout = QVBoxLayout(sayfa)
        dis_layout.setContentsMargins(12, 8, 12, 8)
        dis_layout.setSpacing(8)

        aciklama = QLabel(
            "💡 <b>Stüdyo Seslendirme Motoru Rehberi:</b> En yüksek Arapça telaffuz, hareke hassasiyeti ve ses klonlama kalitesi için "
            "<b>1. ⭐ Spark-TTS (Önerilen)</b> modelini; ekran kartı kullanmadan çevrimiçi hızlı üretim için "
            "<b>2. ⚡ Hızlı Direkt Neural TTS</b> modunu seçebilirsiniz:"
        )
        aciklama.setWordWrap(True)
        dis_layout.addWidget(aciklama)

        self.model_radio_grup = QButtonGroup(self)
        aktif_motor = self.config_manager.user_settings.get("aktif_motor_tercihi", "SPARK_ARABIC")
        if aktif_motor not in ("SPARK_ARABIC", "FAST_DIRECT_TTS", "XTTS_STUDIO"):
            aktif_motor = "SPARK_ARABIC"

        for idx, m in enumerate(SES_MODELLERI_REHBERI):
            kart = QFrame()
            kart.setObjectName("modelKartOnerilen" if m["kod"] == "SPARK_ARABIC" else "modelKart")
            kart.setToolTip(m.get("tooltip", ""))
            k_v = QVBoxLayout(kart)
            k_v.setContentsMargins(12, 8, 12, 8)
            k_v.setSpacing(4)

            ust_satir = QHBoxLayout()
            ust_satir.setSpacing(8)

            rb = QRadioButton(m["ad"])
            rb.setCursor(Qt.PointingHandCursor)
            rb.setProperty("model_kodu", m["kod"])
            rb.setToolTip(m.get("tooltip", ""))
            if m["kod"] == aktif_motor:
                rb.setChecked(True)
            self.model_radio_grup.addButton(rb, idx)
            ust_satir.addWidget(rb, stretch=1)

            lbl_rozet = QLabel(m["rozet"])
            lbl_rozet.setStyleSheet(
                f"background-color: {m['rozet_renk']}; color: #ffffff; padding: 3px 9px; "
                "border-radius: 4px; font-size: 8pt; font-weight: bold;"
            )
            ust_satir.addWidget(lbl_rozet)

            btn_model_kur = QPushButton("📥 Doğrula / Kur")
            btn_model_kur.setFixedHeight(26)
            btn_model_kur.setFixedWidth(130)
            btn_model_kur.clicked.connect(lambda checked=False, model_bilgi=m: self._secili_modeli_kur(model_bilgi))
            ust_satir.addWidget(btn_model_kur)
            k_v.addLayout(ust_satir)

            orta_satir = QHBoxLayout()
            orta_satir.setContentsMargins(24, 0, 0, 0)
            orta_satir.setSpacing(8)

            lbl_amac = QLabel(f"🎯 <b>Kullanım Amacı:</b> <span style='color:#10b981; font-weight:bold;'>{m['amac']}</span>")
            lbl_amac.setWordWrap(True)
            lbl_amac.setStyleSheet("font-size: 8.8pt;")
            orta_satir.addWidget(lbl_amac, stretch=1)

            lbl_req = QLabel(f"⚙️ {m['gereksinim']}")
            lbl_req.setStyleSheet(
                "background-color: #1e293b; color: #fbbf24; padding: 2px 8px; border-radius: 4px; font-size: 8pt; font-weight: bold;"
            )
            orta_satir.addWidget(lbl_req)
            k_v.addLayout(orta_satir)

            lbl_detay = QLabel(f"ℹ️ {m['aciklama']}")
            lbl_detay.setWordWrap(True)
            lbl_detay.setStyleSheet("font-size: 8.5pt; margin-left: 24px;")
            k_v.addWidget(lbl_detay)

            dis_layout.addWidget(kart)

        dis_layout.addStretch()
        return sayfa

    def _sekme_2_kutuphane_tikla_kur(self) -> QWidget:
        sayfa = QWidget()
        layout = QVBoxLayout(sayfa)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        ust_bilgi = QHBoxLayout()
        lbl = QLabel(
            "Sisteminizdeki tüm ses, yapay zeka ve DSP modüllerinin kurulum durumunu aşağıda görebilir, "
            "eksik olanları <b>'⚡ Tıkla Kur'</b> butonuyla tek tek kurabilirsiniz:"
        )
        lbl.setWordWrap(True)
        ust_bilgi.addWidget(lbl, stretch=1)

        btn_hepsini_dogrula = QPushButton("⚡ Ana Spark-TTS Modelini ve Referans Sesleri Doğrula")
        btn_hepsini_dogrula.setStyleSheet("background-color: #059669; padding: 7px 14px;")
        btn_hepsini_dogrula.clicked.connect(
            lambda: self._gorev_baslat("model_indir", hf_repo_id=SPARK_HF_MODEL_ID)
        )
        ust_bilgi.addWidget(btn_hepsini_dogrula)
        layout.addLayout(ust_bilgi)

        self.tablo_moduller = QTableWidget(len(MODUL_KONTROL_LISTESI), 5)
        self.tablo_moduller.verticalHeader().setDefaultSectionSize(36)
        self.tablo_moduller.setHorizontalHeaderLabels([
            "Modül / Kütüphane Adı",
            "Durum ve Sürüm",
            "Ne İşe Yarar? (Kullanım Amacı)",
            "Tür",
            "İşlem",
        ])
        self.tablo_moduller.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tablo_moduller.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tablo_moduller.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tablo_moduller.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tablo_moduller.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.tablo_moduller, stretch=1)

        return sayfa

    def _sekme_3_referans_ses_denetimi(self) -> QWidget:
        sayfa = QWidget()
        layout = QVBoxLayout(sayfa)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        ust = QHBoxLayout()
        ust.addWidget(QLabel("Stüdyo Referans Ses Havuzu ve 24kHz Ön-Temizlik Durumu:"))
        ust.addStretch()
        btn_on_temizle = QPushButton("✨ Tüm Referans Sesleri 24kHz Ön-Temizlikten Geçir")
        btn_on_temizle.setToolTip("Model indirmeden yalnızca mevcut referans ses dosyalarını 24kHz standardında ön-temizlikten geçirir.")
        btn_on_temizle.setStyleSheet("background-color: #059669;")
        btn_on_temizle.clicked.connect(lambda: self._gorev_baslat("ref_temizle", hf_repo_id=None))
        ust.addWidget(btn_on_temizle)
        layout.addLayout(ust)

        self.tablo_ref = QTableWidget(0, 5)
        self.tablo_ref.verticalHeader().setDefaultSectionSize(38)
        self.tablo_ref.setHorizontalHeaderLabels([
            "Ses Adı / Rol", "Dosya Adı", "Durum", "Referans Seste Okunan Arapça Metin (Prompt Text)", "Dinle"
        ])
        self.tablo_ref.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tablo_ref.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tablo_ref.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tablo_ref.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tablo_ref.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.tablo_ref, stretch=1)

        return sayfa

    def _modul_durumu_sorgula(self, m: Dict[str, Any]) -> tuple[bool, str]:
        imp = m["import_adi"]
        dist_adi = m.get("dist_adi", imp)

        if imp == "ffmpeg_bin":
            yol = shutil.which("ffmpeg")
            return (True, "✅ Kurulu (PATH)") if yol else (False, "⚠️ Eksik (MP3 İçin Gerekli)")

        if imp == "torch":
            try:
                import torch
                ver = torch.__version__
                if torch.cuda.is_available():
                    return True, f"✅ {ver} (CUDA Aktif)"
                return False, f"⚠️ {ver} (Sadece CPU)"
            except Exception:
                return False, "❌ Kurulu Değil"

        if imp == "torchaudio":
            try:
                import torchaudio
                ver = getattr(torchaudio, "__version__", "Aktif")
                try:
                    importlib.metadata.version("torchaudio")
                    return True, f"✅ {ver} (Resmi Paket)"
                except Exception:
                    return True, "✅ Dahili MelSpectrogram Aktif"
            except Exception:
                return False, "❌ Eksik"

        try:
            mod = importlib.import_module(imp)
            ver = getattr(mod, "__version__", None)
            if not ver:
                for aday_dist in (dist_adi, "edge-tts", "coqui-tts", "TTS"):
                    try:
                        ver = importlib.metadata.version(aday_dist)
                        break
                    except Exception:
                        pass
            return True, f"✅ {ver or 'Kurulu'}"
        except Exception:
            return False, "⚪ Kurulu Değil"

    def sistem_durumunu_yenile(self) -> None:
        gpu_bilgi = gpu_vram_durumu_getir()
        self.lbl_gpu.setText(gpu_bilgi["metin"])
        prof_detay = gpu_bilgi.get("profil_detay", {})
        self.lbl_onerilen_bilgi.setText(f"Önerilen Kademe: {prof_detay.get('ad', 'Otomatik')}")

        for r_idx, m in enumerate(MODUL_KONTROL_LISTESI):
            kurulu_mu, durum_metni = self._modul_durumu_sorgula(m)
            zorunlu_mu = bool(m.get("zorunlu", True))

            ad_item = QTableWidgetItem(m["ad"])
            ad_item.setToolTip(m["aciklama"])
            self.tablo_moduller.setItem(r_idx, 0, ad_item)

            durum_item = QTableWidgetItem(durum_metni)
            if "✅" in durum_metni:
                durum_item.setForeground(QColor("#10b981"))
            elif "⚠️" in durum_metni:
                durum_item.setForeground(QColor("#f59e0b"))
            else:
                durum_item.setForeground(QColor("#ef4444") if zorunlu_mu else QColor("#94a3b8"))
            self.tablo_moduller.setItem(r_idx, 1, durum_item)

            aciklama_item = QTableWidgetItem(m["aciklama"])
            aciklama_item.setToolTip(m["aciklama"])
            self.tablo_moduller.setItem(r_idx, 2, aciklama_item)
            self.tablo_moduller.setItem(
                r_idx, 3, QTableWidgetItem("Zorunlu" if zorunlu_mu else "Opsiyonel")
            )

            btn_kur = QPushButton("🔄 Onar" if kurulu_mu else "⚡ Tıkla Kur")
            btn_kur.setFixedHeight(26)
            if not kurulu_mu:
                btn_kur.setStyleSheet("background-color: #059669; color: white;")
            btn_kur.clicked.connect(lambda checked=False, modul_bilgi=m: self._tekil_modul_kur(modul_bilgi))
            self.tablo_moduller.setCellWidget(r_idx, 4, btn_kur)

        havuz = self.config_manager.voice_pool
        self.tablo_ref.setRowCount(len(havuz))
        arapca_font = profesyonel_arapca_font_olustur(15)

        for row_idx, ses in enumerate(havuz):
            yol = self.config_manager.resolve_voice_path(ses["id"])
            var_mi = yol.exists() and yol.stat().st_size > 1000
            dosya_adi_str = str(ses.get("dosya") or ses.get("dosya_adi") or yol.name)

            self.tablo_ref.setItem(row_idx, 0, QTableWidgetItem(ses.get("ad", ses["id"])))
            self.tablo_ref.setItem(row_idx, 1, QTableWidgetItem(dosya_adi_str))

            durum_item = QTableWidgetItem("✅ Hazır" if var_mi else "❌ Dosya Eksik")
            durum_item.setForeground(QColor("#10b981") if var_mi else QColor("#ef4444"))
            self.tablo_ref.setItem(row_idx, 2, durum_item)

            metin_item = QTableWidgetItem(ses.get("ref_metin", ""))
            metin_item.setFont(arapca_font)
            metin_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            metin_item.setToolTip(ses.get("ref_metin", ""))
            self.tablo_ref.setItem(row_idx, 3, metin_item)

            btn_dinle = QPushButton("🔊 Dinle")
            btn_dinle.setFixedHeight(26)
            btn_dinle.setEnabled(var_mi)
            btn_dinle.clicked.connect(lambda checked=False, p=str(yol): self._ses_cal(p))
            self.tablo_ref.setCellWidget(row_idx, 4, btn_dinle)

    def _tekil_modul_kur(self, modul_bilgi: Dict[str, Any]) -> None:
        ktip = modul_bilgi["kurulum_tipi"]
        paketler = modul_bilgi.get("pip_paketler", [])
        self._gorev_baslat(ktip, pip_paketler=paketler)

    def _secili_modeli_kur(self, model_bilgi: Dict[str, Any]) -> None:
        kod = model_bilgi["kod"]
        if kod == "SPARK_ARABIC":
            self._gorev_baslat("model_indir", hf_repo_id=model_bilgi["hf_repo"])
        else:
            self._gorev_baslat("pip", pip_paketler=model_bilgi["pip_paketler"])

    def _gorev_baslat(
        self,
        gorev_tipi: str,
        pip_paketler: Optional[List[str]] = None,
        hf_repo_id: Optional[str] = None,
    ) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "İşlem Sürüyor", "Lütfen mevcut kurulum işleminin bitmesini bekleyin.")
            return

        self.btn_yenile.setEnabled(False)
        self.btn_islem_durdur.setEnabled(True)
        self.txt_log.clear()
        self.txt_log.append(f"⏳ İşlem başlatıldı: {gorev_tipi}...")

        self.worker = TekilKurulumWorker(
            gorev_tipi=gorev_tipi,
            config_manager=self.config_manager,
            pip_paketler=pip_paketler,
            hf_repo_id=hf_repo_id,
        )
        self.worker.ilerleme_sinyali.connect(self._ilerleme_guncelle)
        self.worker.log_sinyali.connect(self.txt_log.append)
        self.worker.tamamlandi_sinyali.connect(self._gorev_tamamlandi)
        self.worker.start()

    def _aktif_islemi_durdur(self) -> None:
        if self.worker and self.worker.isRunning():
            self.btn_islem_durdur.setEnabled(False)
            self.txt_log.append("⏹️ Durdurma isteği gönderildi...")
            self.worker.durdur()

    def _ilerleme_guncelle(self, yuzde: int, mesaj: str) -> None:
        self.progress_bar.setValue(yuzde)
        self.progress_bar.setFormat(f"%p% - {mesaj}")

    def _gorev_tamamlandi(self, basarili: bool, mesaj: str) -> None:
        self.btn_yenile.setEnabled(True)
        self.btn_islem_durdur.setEnabled(False)
        self.sistem_durumunu_yenile()
        if basarili:
            QMessageBox.information(self, "İşlem Tamamlandı", mesaj)
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Durduruldu / Uyarılı")
            QMessageBox.warning(self, "Kurulum Bilgilendirmesi", mesaj)

    def _ses_cal(self, dosya_yolu: str) -> None:
        if self.ana_pencere and hasattr(self.ana_pencere, "ses_dosyasini_cal"):
            self.ana_pencere.ses_dosyasini_cal(dosya_yolu)
        elif sys.platform == "win32" and os.path.exists(dosya_yolu):
            try:
                import winsound
                winsound.PlaySound(dosya_yolu, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:
                pass

    def _kaydet_ve_kapat(self) -> None:
        secili_btn = self.model_radio_grup.checkedButton()
        if secili_btn:
            secili_kod = secili_btn.property("model_kodu")
            self.config_manager.user_settings["aktif_motor_tercihi"] = secili_kod
            self.config_manager.user_settings["acilis_varsayilan_spark_koru"] = (secili_kod == "SPARK_ARABIC")
        self.config_manager.save_user_settings()
        self.accept()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.durdur()
            if not self.worker.wait(4000):
                self.worker.terminate()
                self.worker.wait(500)
        super().closeEvent(event)