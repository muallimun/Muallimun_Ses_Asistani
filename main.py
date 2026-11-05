#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MUALLİMUN AI SES STÜDYOSU PRO - GÜVENLİ UYGULAMA BAŞLATICI (main.py)
Özellikler:
  1. Çalışma zamanında habersiz 'pip uninstall' veya sonsuz yeniden başlatma döngüsü yapmaz.
  2. Torchvision çakışma kalkanını ve yüksek DPI ekran ölçeklendirmesini güvenli şekilde başlatır.
  3. Uygulama sürüm bilgisini (APP_VERSION) ve merkezi hata yakalayıcıyı tanımlar.
"""

import os
import sys
import warnings
import importlib.util
import importlib.machinery
from pathlib import Path

# Konsolsuz (--noconsole) EXE modunda erken print() çağrılarının çökmesini önler
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# Uygulama Sürüm ve GitHub Güncelleme Sabitleri
APP_VERSION = "1.2.0"
GITHUB_REPO_DEFAULT = "muallimun/Muallimun_Ses_Asistani"

# ==============================================================================
# 0. ÇAKIŞAN TORCHVISION PAKETİNİ GÜVENLİ DEVRE DIŞI BIRAKMA
# ==============================================================================
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_NO_TORCHVISION"] = "1"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

sys.modules["torchvision"] = None

_orig_find_spec = importlib.util.find_spec


def _guvenli_find_spec(name, package=None):
    if name == "torchvision" or name.startswith("torchvision."):
        return None
    if name == "torchaudio" or name.startswith("torchaudio."):
        mod = sys.modules.get(name)
        if mod is not None and getattr(mod, "__spec__", None) is not None:
            return mod.__spec__
        try:
            return _orig_find_spec(name, package)
        except Exception:
            return importlib.machinery.ModuleSpec(name, loader=None)
    return _orig_find_spec(name, package)


importlib.util.find_spec = _guvenli_find_spec
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def temel_ortam_kontrolu() -> bool:
    """
    Uygulama açılışında ortamı bozmadan yalnızca temel GUI kütüphanesinin (PySide6)
    varlığını kontrol eder. Eksikse kullanıcıya anlaşılır talimat verir.
    """
    eksikler = []
    for mod_adi, pip_adi in [("PySide6", "PySide6"), ("numpy", "numpy"), ("soundfile", "soundfile"), ("scipy", "scipy")]:
        try:
            __import__(mod_adi)
        except ImportError:
            eksikler.append(pip_adi)

    if eksikler:
        paket_str = " ".join(eksikler)
        print("=" * 72)
        print("⚠️  EKSİK TEMEL KÜTÜPHANELER TESPİT EDİLDİ")
        print(f"   Eksik paketler: {', '.join(eksikler)}")
        print(f"   Kurmak için terminalde şu komutu çalıştırın:\n   {sys.executable} -m pip install {paket_str}")
        print("=" * 72)
        return False
    return True


def main() -> int:
    if not temel_ortam_kontrolu():
        return 1

    import tempfile
    from PySide6.QtCore import Qt, QLockFile
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication, QMessageBox

    # Yüksek DPI (125% / 150% laptop ekran ölçeklendirmesi) uyumluluğu
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Muallimun AI Ses Stüdyosu Pro")
    app.setOrganizationName("Muallimun Dijital Eğitim Teknolojileri")
    app.setApplicationVersion(APP_VERSION)
    app.setFont(QFont("Segoe UI", 9))

    # 1. Tekil Çalıştırma Kilidi (Uygulamanın üst üste iki kez açılmasını ve VRAM çakışmasını önler)
    kilit_yolu = os.path.join(tempfile.gettempdir(), "muallimun_studyo_pro_v120.lock")
    tekil_kilit = QLockFile(kilit_yolu)
    tekil_kilit.setStaleLockTime(0)
    if not tekil_kilit.tryLock(100):
        QMessageBox.warning(
            None,
            "Muallimun AI Ses Stüdyosu Pro Açık",
            "Muallimun AI Ses Stüdyosu Pro şu anda zaten çalışıyor!\n\n"
            "Lütfen görev çubuğundaki (Taskbar) açık olan stüdyo penceresini kullanın.",
        )
        return 0

    # 2. Windows Named Mutex (Inno Setup kurulum sihirbazının açık uygulamayı tespit etmesi için)
    _win_mutex = None
    if sys.platform == "win32":
        try:
            import ctypes
            _win_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "MuallimunStudyoPro_Running_Mutex")
            app._win_mutex = _win_mutex
        except Exception:
            pass

    from core.config_manager import ConfigManager
    from ui.main_window import MuallimunStudyoMainWindow

    config_manager = ConfigManager()
    pencere = MuallimunStudyoMainWindow(config_manager=config_manager)
    pencere.show()

    sonuc = app.exec()
    tekil_kilit.unlock()
    return sonuc


if __name__ == "__main__":
    sys.exit(main())