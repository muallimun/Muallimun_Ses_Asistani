# -*- mode: python ; coding: utf-8 -*-
"""
Muallimun AI Ses Stüdyosu Pro - PyInstaller 6.x (--onedir / --noconsole) Derleme Yapılandırması
"""

import os
import shutil
from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_submodules,
    copy_metadata,
)

PROJECT_DIR = Path(SPECPATH).resolve()

datas = []
binaries = []
hiddenimports = [
    # Uygulama içi modüller
    "core",
    "core.config_manager",
    "core.studyo_motoru",
    "core.batch_worker",
    "ui",
    "ui.main_window",
    "ui.studyo_sekmeler_b",
    "ui.setup_wizard",
    "ui.rehber_ve_guncelleyici",
    # Yapay zeka ve Spark-TTS dinamik (trust_remote_code) bağımlılıkları
    "torch",
    "torchaudio",
    "transformers",
    "accelerate",
    "huggingface_hub",
    "safetensors",
    "safetensors.torch",
    "tokenizers",
    "einops",
    "einops.layers",
    "einops.layers.torch",
    "einx",
    "omegaconf",
    # 24kHz Stüdyo DSP, Resample ve Ses G/Ç modülleri
    "soxr",
    "soundfile",
    "_soundfile_data",
    "scipy",
    "scipy.signal",
    "scipy.fft",
    "scipy.special",
    "scipy.ndimage",
    "scipy.linalg",
    "librosa",
    "librosa.filters",
    "librosa.core",
    # Çevrimiçi TTS, Excel ve Sistem modülleri
    "edge_tts",
    "aiohttp",
    "aiosignal",
    "frozenlist",
    "multidict",
    "yarl",
    "certifi",
    "openpyxl",
    "openpyxl.styles",
    "openpyxl.worksheet.datavalidation",
    "openpyxl.utils",
    "sqlite3",
    "winsound",
    "unicodedata",
]

# 1. C uzantılı ve dinamik veri içeren kritik paketleri zorla topla
for pkg in ("soxr", "soundfile", "_soundfile_data", "einx", "einops", "omegaconf", "edge_tts", "openpyxl"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

# 2. Librosa ve Transformers alt modüllerini/verilerini topla
for pkg in ("librosa", "transformers", "accelerate", "huggingface_hub"):
    try:
        datas += collect_data_files(pkg)
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

# 3. importlib.metadata.version() kontrollerinin çökmemesi için paket üstverilerini kopyala
METADATA_PACKAGES = [
    "torch",
    "torchaudio",
    "transformers",
    "accelerate",
    "huggingface_hub",
    "safetensors",
    "tokenizers",
    "tqdm",
    "regex",
    "requests",
    "packaging",
    "filelock",
    "numpy",
    "scipy",
    "soundfile",
    "librosa",
    "soxr",
    "einops",
    "einx",
    "omegaconf",
    "edge-tts",
    "openpyxl",
    "coqui-tts",
    "TTS",
]
for dist_name in METADATA_PACKAGES:
    try:
        datas += copy_metadata(dist_name)
    except Exception:
        pass

# 4. Çakışan torchvision ve gereksiz ağır Qt/Python modüllerini dışla
EXCLUDES = [
    "torchvision",
    "matplotlib",
    "tkinter",
    "notebook",
    "ipython",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DExtras",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtSql",
    "PySide6.QtTest",
]

icon_file = str(PROJECT_DIR / "app_icon.ico") if (PROJECT_DIR / "app_icon.ico").exists() else None

a = Analysis(
    ["main.py"],
    pathex=[str(PROJECT_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=list(set(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,          # --onedir modu için True olmalıdır
    name="MuallimunStudyoPro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                      # CUDA ve PyTorch DLL bozulmalarını önlemek için UPX kapalı
    console=False,                  # Siyah CMD konsol penceresini tamamen kapatır (--noconsole)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MuallimunStudyoPro",
)

# ==============================================================================
# DERLEME SONRASI OTOMATİK STÜDYO DOSYA YERLEŞTİRİCİ
# (Dosyaları _internal yerine doğrudan MuallimunStudyoPro.exe yanına kopyalar)
# ==============================================================================
DIST_APP_DIR = Path(DISTPATH) / "MuallimunStudyoPro"
if DIST_APP_DIR.exists():
    print("\n📦 Stüdyo çalışma dosyaları EXE dizinine yerleştiriliyor...")

    # 1. Kök dizin dosyaları (ffmpeg.exe, app_icon.ico, 8 referans WAV, bilgi dosyaları)
    kok_dosyalar = ["ffmpeg.exe", "app_icon.ico", "version.json", "README.md", "LICENSE"]
    for wav_yol in PROJECT_DIR.glob("ref_*.wav"):
        kok_dosyalar.append(wav_yol.name)

    for dosya_adi in kok_dosyalar:
        kaynak = PROJECT_DIR / dosya_adi
        if kaynak.exists():
            shutil.copy2(kaynak, DIST_APP_DIR / dosya_adi)
            print(f"   ✅ Kopyalandı: {dosya_adi}")

    # 2. Temiz config/ klasörü (.bak, kişisel user_settings.json ve eski .db hariç)
    hedef_config = DIST_APP_DIR / "config"
    hedef_config.mkdir(parents=True, exist_ok=True)
    for cfg_dosya in ("factory_presets.json", "voice_pool.json", "tashkeel_sozluk.json"):
        kaynak_cfg = PROJECT_DIR / "config" / cfg_dosya
        if kaynak_cfg.exists():
            shutil.copy2(kaynak_cfg, hedef_config / cfg_dosya)
            print(f"   ✅ Config kopyalandı: config/{cfg_dosya}")

    # 3. Boş çalışma klasörlerini hazırla
    (DIST_APP_DIR / "cikti_sesler").mkdir(parents=True, exist_ok=True)
    (DIST_APP_DIR / "referans_sesler_ozel").mkdir(parents=True, exist_ok=True)
    print("✨ 'dist\\MuallimunStudyoPro' klasörü çalıştırmaya ve Inno Setup'a hazır!\n")