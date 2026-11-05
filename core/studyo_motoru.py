#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MUALLİMUN AI SES STÜDYOSU PRO - ÇEKİRDEK SES, FONETİK VAKIF/VASIL VE DSP MASTERING MOTORU
Desteklenen Motorlar:
  1. SPARK_ARABIC    : 🎙️ IbrahimSalah/Arabic-TTS-Spark (24kHz BiCodec — ⭐ Önerilen Ana Stüdyo Motoru)
  2. FAST_DIRECT_TTS : ⚡ Hızlı Direkt Neural TTS (Çevrimiçi Edge Neural 24kHz + Stüdyo DSP)
  3. XTTS_STUDIO     : 🗣️ Coqui XTTS v2 Studio (Opsiyonel Çok Dilli Ses Klonlama Motoru)
"""

import os
import re
import gc
import sys
import time
import uuid
import math
import types
import shutil
import asyncio
import hashlib
import logging
import warnings
import functools
import threading
import subprocess
import unicodedata
import importlib.util
import importlib.machinery
from contextlib import nullcontext
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Callable
import numpy as np

# ==============================================================================
# 0. TORCHVISION 'nms' KALKANI VE TEMEL SABİTLER
# ==============================================================================
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_NO_TORCHVISION"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["COQUI_TOS_AGREED"] = "1"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

warnings.filterwarnings("ignore", category=UserWarning)
logging.getLogger("transformers").setLevel(logging.ERROR)

sys.modules["torchvision"] = None

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
    CORE_DIR = BASE_DIR / "core"
else:
    CORE_DIR = Path(__file__).resolve().parent
    BASE_DIR = CORE_DIR.parent if CORE_DIR.name == "core" else CORE_DIR

# EXE yanında bulunan taşınabilir ffmpeg.exe'nin shutil.which("ffmpeg") tarafından otomatik bulunmasını sağlar
if str(BASE_DIR) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = str(BASE_DIR) + os.pathsep + os.environ.get("PATH", "")

# Konsolsuz (--noconsole) EXE modunda print() ve HuggingFace indirme çubuklarının çökmesini önler
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

# v8: Doğal nefes korumalı, Raised-Cosine Crossfade destekli referans önbelleği
REF_CACHE_DIR = BASE_DIR / ".studyo_ref_cache_v8"

# ==============================================================================
# 1. 8 STÜDYO REFERANS SES DOSYASI VE OKUTULAN ARAPÇA REFERANS METİNLERİ
# ==============================================================================
REF_METIN_1 = (
    "اَلْعِلْمُ نُورٌ يُضِيءُ طَرِيقَ الْإِنْسَانِ فِي الْحَيَاةِ، "
    "وَالْقِرَاءَةُ الْمُسْتَمِرَّةُ تَفْتَحُ لَنَا أَبْوَابَ الْمَعْرِفَةِ وَالْحِكْمَةِ كُلَّ يَوْمٍ."
)

REF_METIN_2 = (
    "ذَهَبَ الطُّلَّابُ فِي الصَّبَاحِ الْبَاكِرِ إِلَى الْمَكْتَبَةِ الْكَبِيرَةِ، "
    "وَقَرَؤُوا كُتُبًا مُفِيدَةً عَنْ تَارِيخِ الْحَضَارَةِ الْإِسْلَامِيَّةِ."
)

REFERANS_SES_HAVUZU = {
    "yetiskin_E": ["ref_erkek_1.wav", "ref_erkek_2.wav"],
    "cocuk_E":    ["ref_erkek_cocuk_1.wav", "ref_erkek_cocuk_2.wav"],
    "yetiskin_K": ["ref_kadin_1.wav", "ref_kadin_2.wav"],
    "cocuk_K":    ["ref_kiz_cocuk_1.wav", "ref_kiz_cocuk_2.wav"],
}

TUM_8_REFERANS_SES = [
    "ref_erkek_1.wav", "ref_erkek_2.wav",
    "ref_erkek_cocuk_1.wav", "ref_erkek_cocuk_2.wav",
    "ref_kadin_1.wav", "ref_kadin_2.wav",
    "ref_kiz_cocuk_1.wav", "ref_kiz_cocuk_2.wav",
]

YERLESIK_8_SES_STEMLERI = {
    "ref_erkek_1", "ref_erkek_2",
    "ref_erkek_cocuk_1", "ref_erkek_cocuk_2",
    "ref_kadin_1", "ref_kadin_2",
    "ref_kiz_cocuk_1", "ref_kiz_cocuk_2",
}

ANA_REF_ERKEK = "ref_erkek_1.wav"
ANA_REF_KADIN = "ref_kadin_1.wav"

SPARK_HF_MODEL_ID = "IbrahimSalah/Arabic-TTS-Spark"
AKTIF_MOTOR_TERCIHI = "SPARK_ARABIC"

DIREKT_TTS_SES_HARITASI: Dict[str, Dict[str, str]] = {
    "ref_erkek_1":       {"voice": "ar-SA-HamedNeural",   "pitch": "+0Hz",  "rate": "-5%"},
    "ref_erkek_2":       {"voice": "ar-EG-ShakirNeural",  "pitch": "-2Hz",  "rate": "-4%"},
    "ref_kadin_1":       {"voice": "ar-SA-ZariyahNeural", "pitch": "+0Hz",  "rate": "-5%"},
    "ref_kadin_2":       {"voice": "ar-EG-SalmaNeural",   "pitch": "+0Hz",  "rate": "-4%"},
    "ref_erkek_cocuk_1": {"voice": "ar-SA-HamedNeural",   "pitch": "+26Hz", "rate": "+2%"},
    "ref_erkek_cocuk_2": {"voice": "ar-EG-ShakirNeural",  "pitch": "+22Hz", "rate": "+0%"},
    "ref_kiz_cocuk_1":   {"voice": "ar-SA-ZariyahNeural", "pitch": "+24Hz", "rate": "+2%"},
    "ref_kiz_cocuk_2":   {"voice": "ar-EG-SalmaNeural",   "pitch": "+20Hz", "rate": "+0%"},
}

YETISKIN_ROLLER = [
    "anne", "baba", "bey", "hanım", "hanim", "öğretmen", "ogretmen", "doktor", "satıcı", "satici",
    "bakkal", "görevli", "gorevli", "sekreter", "profesör", "profesor", "ihtiyar", "mühendis", "muhendis",
    "rehber", "teknisyen", "balıkçı", "balikci", "kuaför", "kuafor", "hostes", "ressam",
    "müşteri", "musteri", "kütüphaneci", "kutuphaneci", "eczacı", "eczaci", "müdür", "mudur", "memur", "imam",
    "dede", "nine", "amca", "teyze", "hala", "dayı", "dayi", "komşu", "komsu",
    "polis", "şoför", "sofor", "garson", "aşçı", "asci", "çiftçi", "ciftci", "kasap", "terzi",
    "dişçi", "disci", "hemşire", "hemsire", "ev sahibi", "emlakçı", "emlakci", "avukat", "hakim", "uzman", "muallim"
]

# "öğrenci" yetişkin/genç sınıf diyaloglarında da geçtiği için yalnızca net çocuk ifadeleri çocuk sesine atanır
COCUK_ROLLER = [
    "çocuk", "cocuk", "oğul", "ogul", "kızım", "kizim", "oğlum", "oglum",
    "torun", "küçük", "kucuk", "bebek", "kardeş", "kardes", "yavrum"
]

BOLUNMEZ_ARAPCA_EDATLAR = {
    "فِي", "مِنْ", "إِلَى", "عَلَى", "عَنْ", "مَعَ", "بَيْنَ", "تَحْتَ", "فَوْقَ",
    "أَمَامَ", "خَلْفَ", "حَوْلَ", "عِنْدَ", "مُنْذُ", "حَتَّى", "أَنْ", "إِنْ",
    "إِنَّ", "أَنَّ", "كَأَنَّ", "لَكِنَّ", "لَعَلَّ", "لَيْتَ", "لَا", "مَا", "لَمْ",
    "لَنْ", "قَدْ", "سَوْفَ", "يَا", "أَيُّهَا", "أَيَّتُهَا", "هَذَا", "هَذِهِ",
    "ذَلِكَ", "تِلْكَ", "الَّذِي", "الَّتِي", "الَّذِينَ", "كُلُّ", "كُلَّ", "بَعْضُ", "غَيْرُ",
    "لَابُدَّ", "بُدَّ"
}


def arapca_harekeleri_soy(metin: str) -> str:
    """Arapça metindeki harekeleri ve keşideyi (tatweel) karşılaştırma amacıyla soyar."""
    return re.sub(r"[\u0640\u064B-\u065F\u0670]", "", str(metin or "")).strip()


BOLUNMEZ_ARAPCA_EDATLAR_HAREKESIZ = {arapca_harekeleri_soy(e) for e in BOLUNMEZ_ARAPCA_EDATLAR}

_TR_HARF_HARITASI = str.maketrans({"İ": "i", "I": "ı", "Ğ": "ğ", "Ü": "ü", "Ş": "ş", "Ö": "ö", "Ç": "ç"})


def tr_kucult(metin: str) -> str:
    """Türkçe büyük İ/I harflerini bozmadan küçük harfe çevirir."""
    return str(metin or "").translate(_TR_HARF_HARITASI).lower().replace("i\u0307", "i").strip()


def rol_tahmin_et(konusmaci_adi: str, cinsiyet: str = "E") -> str:
    cins = "K" if str(cinsiyet or "E").strip().upper().startswith("K") else "E"
    kucuk = tr_kucult(konusmaci_adi)
    if any(k in kucuk for k in YETISKIN_ROLLER):
        return f"yetiskin_{cins}"
    if any(k in kucuk for k in COCUK_ROLLER):
        return f"cocuk_{cins}"
    return f"yetiskin_{cins}"


def yerlesik_ref_ses_mi(yol_veya_ad: str | Path) -> bool:
    """Verilen ses dosyasının yerleşik 8 hazır stüdyo sesinden biri olup olmadığını döndürür."""
    stem = Path(str(yol_veya_ad or "")).stem.lower()
    temiz_stem = re.sub(r"_[0-9a-f]{12}$", "", stem)
    return temiz_stem in YERLESIK_8_SES_STEMLERI


def _eski_gecici_onbellek_dosyalarini_temizle(maks_yas_saniye: int = 3600) -> None:
    """REF_CACHE_DIR içinde kalan geçici (_play_, _decode_, _direkt_tts_, _tmp_) dosyaları temizler."""
    if not REF_CACHE_DIR.exists():
        return
    simdi = time.time()
    gecici_onekler = ("_play_", "_decode_", "_direkt_tts_", "_tmp_")
    try:
        for p in REF_CACHE_DIR.iterdir():
            if p.is_file() and p.name.startswith(gecici_onekler):
                try:
                    if (simdi - p.stat().st_mtime) > maks_yas_saniye:
                        p.unlink()
                except OSError:
                    pass
    except Exception:
        pass


# ==============================================================================
# 1.A. İŞ PARÇACIĞI GÜVENLİ İPTAL ANAHTARI (CancelToken)
# ==============================================================================
class CancelToken:
    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def reset(self) -> None:
        self._event.clear()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()


DONANIM_PROFILLERI: Dict[str, Dict[str, Any]] = {
    "PRO_STUDYO_12GB_USTU": {
        "kod": "PRO_STUDYO_12GB_USTU",
        "ad": "🚀 Kademe 1: Pro Stüdyo Tam Kapasite (10 GB / 12 GB+ VRAM)",
        "max_token_ust_sinir": 1150,
        "kelime_token_carpani": 52,
        "bolme_esigi_kelime": 34,
        "parca_maks_kelime": 18,
        "her_uretimde_cache_temizle": False,
        "aciklama": "Uzun cümleleri tek nefeste, yüksek bellek bütçesiyle üretir.",
    },
    "DENGELI_8GB": {
        "kod": "DENGELI_8GB",
        "ad": "⚖️ Kademe 2: Dengeli Stüdyo Performansı (7 GB – 10 GB VRAM)",
        "max_token_ust_sinir": 950,
        "kelime_token_carpani": 48,
        "bolme_esigi_kelime": 26,
        "parca_maks_kelime": 16,
        "her_uretimde_cache_temizle": False,
        "aciklama": "Orta ve uzun cümleleri tek nefeste okur, çok uzun paragrafları doğal böler.",
    },
    "HAFIF_4_6GB": {
        "kod": "HAFIF_4_6GB",
        "ad": "⚡ Kademe 3: Hafif ve Hızlı Laptop Modu (4 GB – 6 GB VRAM)",
        "max_token_ust_sinir": 820,
        "kelime_token_carpani": 45,
        "bolme_esigi_kelime": 22,
        "parca_maks_kelime": 14,
        "her_uretimde_cache_temizle": True,
        "aciklama": "22 kelimeye kadar olan cümleleri tek nefeste okur; 4 GB – 6 GB VRAM ekran kartlarını korur.",
    },
    "CPU_MODU": {
        "kod": "CPU_MODU",
        "ad": "💻 Kademe 4: CPU (İşlemci) Modu (GPU Kullanmadan Üretim)",
        "max_token_ust_sinir": 650,
        "kelime_token_carpani": 42,
        "bolme_esigi_kelime": 18,
        "parca_maks_kelime": 12,
        "her_uretimde_cache_temizle": False,
        "aciklama": "Ekran kartı belleğini kullanmadan işlemci (CPU) üzerinde güvenli üretim yapar.",
    },
}

_OZEL_REF_METIN_HARITASI: Dict[str, str] = {}
_OZEL_REF_KATEGORI_HARITASI: Dict[str, Dict[str, str]] = {}


def ozel_referans_metni_kaydet(ses_yolu_veya_ad: str, arapca_metin: str) -> None:
    temiz = str(arapca_metin or "").strip()
    anahtar_ad = os.path.basename(str(ses_yolu_veya_ad)).lower()
    anahtar_stem = Path(str(ses_yolu_veya_ad)).stem.lower()
    anahtar_tam = str(ses_yolu_veya_ad)
    if temiz:
        _OZEL_REF_METIN_HARITASI[anahtar_ad] = temiz
        _OZEL_REF_METIN_HARITASI[anahtar_stem] = temiz
        _OZEL_REF_METIN_HARITASI[anahtar_tam] = temiz
    else:
        _OZEL_REF_METIN_HARITASI.pop(anahtar_ad, None)
        _OZEL_REF_METIN_HARITASI.pop(anahtar_stem, None)
        _OZEL_REF_METIN_HARITASI.pop(anahtar_tam, None)


def ozel_referans_kategori_kaydet(ses_yolu_veya_ad: str, cinsiyet: str = "E", kategori: str = "yetiskin_E") -> None:
    """Özel eklenen referans seslerin cinsiyet ve rol kategorisini Direkt TTS eşleştirmesi için kaydeder."""
    cins = "K" if str(cinsiyet or "E").upper().startswith("K") else "E"
    kat = str(kategori or f"yetiskin_{cins}").strip()
    bilgi = {"cinsiyet": cins, "kategori": kat}
    anahtar_ad = os.path.basename(str(ses_yolu_veya_ad)).lower()
    anahtar_stem = Path(str(ses_yolu_veya_ad)).stem.lower()
    anahtar_tam = str(ses_yolu_veya_ad)
    _OZEL_REF_KATEGORI_HARITASI[anahtar_ad] = bilgi
    _OZEL_REF_KATEGORI_HARITASI[anahtar_stem] = bilgi
    _OZEL_REF_KATEGORI_HARITASI[anahtar_tam] = bilgi


def referans_metni_getir(
    wav_dosya_adi: str,
    ozel_metin: Optional[str] = None,
    ozel_ref_metin: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Referans sese ait Arapça metni döndürür.
    KRİTİK KORUMA:
    - Yerleşik 8 hazır ses için her zaman kendi REF_METIN_1 veya REF_METIN_2 metnini döndürür.
    - Kullanıcı tarafından eklenen özel seslerde ('ozel_...') metin boş bırakılmışsa
      ASLA 'REF_METIN_1' döndürmez; '' (boş metin) döndürür.
    """
    secilen_ozel = ozel_metin if ozel_metin is not None else ozel_ref_metin
    if secilen_ozel is not None and str(secilen_ozel).strip():
        return str(secilen_ozel).strip()

    tam_str = str(wav_dosya_adi)
    ad = os.path.basename(tam_str).lower()
    stem = Path(tam_str).stem.lower()
    temiz_stem = re.sub(r"_[0-9a-f]{12}$", "", stem)

    for aday in (tam_str, ad, stem, temiz_stem):
        if aday in _OZEL_REF_METIN_HARITASI:
            return _OZEL_REF_METIN_HARITASI[aday]

    if yerlesik_ref_ses_mi(tam_str):
        if "_2" in ad:
            return REF_METIN_2
        return REF_METIN_1

    return ""


import torch
import soundfile as sf
from scipy import signal


def _yuksek_kalite_resample(veri: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Anti-aliasing filtreli yüksek kaliteli yeniden örnekleme (soxr / resample_poly)."""
    if orig_sr == target_sr or veri.size == 0:
        return veri.astype(np.float32)
    try:
        import soxr
        return soxr.resample(veri, orig_sr, target_sr, quality="VHQ").astype(np.float32)
    except Exception:
        ortak = math.gcd(int(orig_sr), int(target_sr))
        up = int(target_sr) // ortak
        down = int(orig_sr) // ortak
        return signal.resample_poly(veri, up, down).astype(np.float32)


# ==============================================================================
# 1.B. PYTORCH VE DAHİLİ TORCHAUDIO (MelSpectrogram) KÖPRÜSÜ
# ==============================================================================
try:
    import torch._higher_order_ops.utils as _hop_utils
    if not hasattr(_hop_utils, "setup_compilation_env"):
        _hop_utils.setup_compilation_env = lambda *args, **kwargs: nullcontext()
except Exception:
    pass

try:
    import torch._dynamo._trace_wrapped_higher_order_op as _dyn_hop
    if not hasattr(_dyn_hop, "TransformGetItemToIndex"):
        _dyn_hop.TransformGetItemToIndex = type("TransformGetItemToIndex", (), {})
except Exception:
    pass


def _dahili_torchaudio_koprusunu_kur():
    try:
        import torchaudio
        import torchaudio.transforms as TT
        if hasattr(TT, "MelSpectrogram") and hasattr(TT, "Resample"):
            return
    except Exception:
        pass

    sahte_ta = types.ModuleType("torchaudio")
    sahte_ta.__version__ = torch.__version__
    sahte_ta.__spec__ = importlib.machinery.ModuleSpec("torchaudio", loader=None)

    sahte_transforms = types.ModuleType("torchaudio.transforms")
    sahte_transforms.__spec__ = importlib.machinery.ModuleSpec("torchaudio.transforms", loader=None)

    sahte_functional = types.ModuleType("torchaudio.functional")
    sahte_functional.__spec__ = importlib.machinery.ModuleSpec("torchaudio.functional", loader=None)

    def _ta_load(filepath, *args, **kwargs):
        data, sr = sf.read(str(filepath), dtype="float32")
        if data.ndim == 1:
            tensor = torch.from_numpy(data).unsqueeze(0)
        else:
            tensor = torch.from_numpy(data.T)
        return tensor, int(sr)

    def _ta_save(filepath, src, sample_rate, *args, **kwargs):
        arr = src.detach().cpu().numpy()
        if arr.ndim > 1 and arr.shape[0] <= 2:
            arr = arr.T
        sf.write(str(filepath), arr, int(sample_rate), subtype="PCM_16")

    class _Resample(torch.nn.Module):
        def __init__(self, orig_freq: int = 16000, new_freq: int = 16000, *args, **kwargs):
            super().__init__()
            self.orig_freq = int(orig_freq)
            self.new_freq = int(new_freq)

        def forward(self, waveform: torch.Tensor) -> torch.Tensor:
            if self.orig_freq == self.new_freq:
                return waveform
            device = waveform.device
            dtype = waveform.dtype
            np_wav = waveform.detach().cpu().float().numpy()
            son_boyut = np_wav.shape[-1]
            yeni_boyut = int(round(son_boyut * float(self.new_freq) / float(self.orig_freq)))
            yeniden = signal.resample(np_wav, yeni_boyut, axis=-1)
            return torch.from_numpy(yeniden).to(device=device, dtype=dtype)

    class _SpectrogramSub(torch.nn.Module):
        def __init__(self, win_length: int):
            super().__init__()
            self.register_buffer("window", torch.hann_window(win_length), persistent=True)

    class _MelScaleSub(torch.nn.Module):
        def __init__(self, fb_tensor: torch.Tensor):
            super().__init__()
            self.register_buffer("fb", fb_tensor, persistent=True)

    class _MelSpectrogram(torch.nn.Module):
        def __init__(
            self,
            sample_rate: int = 16000,
            n_fft: int = 400,
            win_length: Optional[int] = None,
            hop_length: Optional[int] = None,
            f_min: float = 0.0,
            f_max: Optional[float] = None,
            pad: int = 0,
            n_mels: int = 128,
            window_fn: Callable = torch.hann_window,
            power: float = 2.0,
            normalized: bool = False,
            wkwargs: Optional[dict] = None,
            center: bool = True,
            pad_mode: str = "reflect",
            onesided: Optional[bool] = None,
            norm: Optional[str] = None,
            mel_scale: str = "htk",
            **kwargs,
        ):
            super().__init__()
            self.sample_rate = int(sample_rate)
            self.n_fft = int(n_fft)
            self.win_length = int(win_length) if win_length is not None else self.n_fft
            self.hop_length = int(hop_length) if hop_length is not None else self.win_length // 2
            self.pad = int(pad)
            self.power = float(power) if power is not None else 1.0
            self.normalized = bool(normalized)
            self.center = bool(center)
            self.pad_mode = pad_mode
            self.n_mels = int(n_mels)
            self.f_min = float(f_min)
            self.f_max = float(f_max) if f_max is not None else float(self.sample_rate // 2)

            import librosa
            mel_np = librosa.filters.mel(
                sr=self.sample_rate,
                n_fft=self.n_fft,
                n_mels=self.n_mels,
                fmin=self.f_min,
                fmax=self.f_max,
                htk=(mel_scale == "htk"),
                norm=norm,
            )
            fb_tensor = torch.from_numpy(mel_np.T).float()
            self.spectrogram = _SpectrogramSub(self.win_length)
            self.mel_scale = _MelScaleSub(fb_tensor)

        def forward(self, waveform: torch.Tensor) -> torch.Tensor:
            orig_shape = waveform.shape
            if waveform.ndim == 1:
                waveform = waveform.unsqueeze(0)
            elif waveform.ndim == 3:
                waveform = waveform.reshape(-1, orig_shape[-1])

            if self.pad > 0:
                waveform = torch.nn.functional.pad(waveform, (self.pad, self.pad), mode="constant")

            win = self.spectrogram.window.to(device=waveform.device, dtype=waveform.dtype)
            spec_c = torch.stft(
                waveform,
                n_fft=self.n_fft,
                hop_length=self.hop_length,
                win_length=self.win_length,
                window=win,
                center=self.center,
                pad_mode=self.pad_mode,
                normalized=self.normalized,
                onesided=True,
                return_complex=True,
            )
            spec = spec_c.abs()
            if self.power != 1.0:
                spec = spec.pow(self.power)

            fb = self.mel_scale.fb.to(device=spec.device, dtype=spec.dtype)
            mel_spec = torch.matmul(spec.transpose(-1, -2), fb).transpose(-1, -2)

            if len(orig_shape) == 1:
                return mel_spec.squeeze(0)
            elif len(orig_shape) == 3:
                return mel_spec.reshape(orig_shape[0], orig_shape[1], self.n_mels, -1)
            return mel_spec

    sahte_ta.load = _ta_load
    sahte_ta.save = _ta_save
    sahte_transforms.Resample = _Resample
    sahte_transforms.MelSpectrogram = _MelSpectrogram
    sahte_functional.resample = lambda waveform, orig_freq, new_freq, *a, **kw: _Resample(orig_freq, new_freq)(waveform)
    sahte_ta.transforms = sahte_transforms
    sahte_ta.functional = sahte_functional

    sys.modules["torchaudio"] = sahte_ta
    sys.modules["torchaudio.transforms"] = sahte_transforms
    sys.modules["torchaudio.functional"] = sahte_functional


_dahili_torchaudio_koprusunu_kur()


# ==============================================================================
# 2. TRANSFORMERS DynamicCache YAMASI
# ==============================================================================
try:
    import transformers
    transformers.logging.set_verbosity_error()
    from transformers.cache_utils import DynamicCache

    def _guvenli_get_seq_length(self, layer_idx=0):
        try:
            if hasattr(self, "key_cache") and len(self.key_cache) > layer_idx:
                kc = self.key_cache[layer_idx]
                if kc is not None and hasattr(kc, "shape") and len(kc.shape) >= 2:
                    return int(kc.shape[-2])
            if hasattr(self, "_seen_tokens") and self._seen_tokens is not None:
                return int(self._seen_tokens)
            if hasattr(self, "value_cache") and len(self.value_cache) > layer_idx:
                vc = self.value_cache[layer_idx]
                if vc is not None and hasattr(vc, "shape") and len(vc.shape) >= 2:
                    return int(vc.shape[-2])
            return 0
        except Exception:
            return 0

    DynamicCache.get_seq_length = _guvenli_get_seq_length

    if not hasattr(DynamicCache, "seen_tokens"):
        DynamicCache.seen_tokens = property(lambda self: self.get_seq_length())
    if not hasattr(DynamicCache, "get_usable_length"):
        DynamicCache.get_usable_length = lambda self, new_seq_length, layer_idx=0: self.get_seq_length(layer_idx)
    if not hasattr(DynamicCache, "get_max_length"):
        DynamicCache.get_max_length = lambda self: None
except Exception:
    pass


# ==============================================================================
# 3. 4 KADEMELİ GPU / GERÇEK BOŞ VRAM ANALİZİ VE DONANIM OPTİMİZASYONU
# ==============================================================================
def vram_miktarina_gore_kademe_belirle(toplam_gb: float, cuda_aktif: bool = True, bos_gb: Optional[float] = None) -> str:
    if not cuda_aktif or toplam_gb <= 0.1:
        return "CPU_MODU"
    etkin_gb = bos_gb if (bos_gb is not None and bos_gb > 0.5) else toplam_gb
    if toplam_gb >= 9.6 and etkin_gb >= 6.5:
        return "PRO_STUDYO_12GB_USTU"
    if toplam_gb >= 6.8 and etkin_gb >= 4.2:
        return "DENGELI_8GB"
    return "HAFIF_4_6GB"


def gpu_vram_durumu_getir() -> Dict[str, Any]:
    if not torch.cuda.is_available():
        prof = DONANIM_PROFILLERI["CPU_MODU"]
        return {
            "aktif": False,
            "cihaz_adi": "CPU Modu (CUDA Bulunamadı)",
            "kullanilan_gb": 0.0,
            "ayrilan_gb": 0.0,
            "bos_gb": 0.0,
            "toplam_gb": 0.0,
            "yuzde": 0,
            "onerilen_profil": "CPU_MODU",
            "profil_detay": prof,
            "oneri_metni": f"{prof['ad']} — {prof['aciklama']}",
            "metin": "💻 CPU Modu",
        }
    try:
        cihaz_adi = torch.cuda.get_device_name(0)
        props = torch.cuda.get_device_properties(0)
        toplam_gb = props.total_memory / (1024 ** 3)
        kullanilan_gb = torch.cuda.memory_allocated(0) / (1024 ** 3)
        ayrilan_gb = torch.cuda.memory_reserved(0) / (1024 ** 3)

        try:
            bos_byte, top_byte = torch.cuda.mem_get_info(0)
            bos_gb = bos_byte / (1024 ** 3)
            sistem_kullanilan_gb = max(kullanilan_gb, (top_byte - bos_byte) / (1024 ** 3))
        except Exception:
            bos_gb = max(0.0, toplam_gb - ayrilan_gb)
            sistem_kullanilan_gb = kullanilan_gb

        yuzde = min(100, int(round((sistem_kullanilan_gb / max(0.1, toplam_gb)) * 100)))
        kademe_kodu = vram_miktarina_gore_kademe_belirle(toplam_gb, cuda_aktif=True, bos_gb=bos_gb)
        prof = DONANIM_PROFILLERI[kademe_kodu]

        return {
            "aktif": True,
            "cihaz_adi": cihaz_adi,
            "kullanilan_gb": round(kullanilan_gb, 2),
            "ayrilan_gb": round(ayrilan_gb, 2),
            "bos_gb": round(bos_gb, 2),
            "toplam_gb": round(toplam_gb, 2),
            "yuzde": yuzde,
            "onerilen_profil": kademe_kodu,
            "profil_detay": prof,
            "oneri_metni": f"{prof['ad']} — {prof['aciklama']}",
            "metin": f"🚀 {cihaz_adi} | Model VRAM: {kullanilan_gb:.2f} GB (Boş: {bos_gb:.1f}/{toplam_gb:.1f} GB)",
        }
    except Exception as e:
        prof = DONANIM_PROFILLERI["CPU_MODU"]
        return {
            "aktif": False,
            "cihaz_adi": "CUDA Hatası",
            "kullanilan_gb": 0.0,
            "ayrilan_gb": 0.0,
            "bos_gb": 0.0,
            "toplam_gb": 0.0,
            "yuzde": 0,
            "onerilen_profil": "CPU_MODU",
            "profil_detay": prof,
            "oneri_metni": "⚠️ GPU okunamadı",
            "metin": f"⚠️ GPU Hatası: {e}",
        }


def gpu_bellegini_optimize_et(
    studyo_motor: Optional["MuallimunStudyoSesMotoru"] = None,
    zorunlu_kademe_kodu: Optional[str] = None,
) -> Dict[str, Any]:
    bilgi = gpu_vram_durumu_getir()
    if zorunlu_kademe_kodu and zorunlu_kademe_kodu in DONANIM_PROFILLERI:
        secilen_kod = zorunlu_kademe_kodu
    else:
        secilen_kod = bilgi["onerilen_profil"]

    gc.collect()
    if torch.cuda.is_available():
        try:
            torch.backends.cudnn.benchmark = False
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.cuda.synchronize()
            torch.cuda.empty_cache()
            if hasattr(torch.cuda, "ipc_collect"):
                torch.cuda.ipc_collect()
        except Exception:
            pass
    else:
        try:
            cekirdek = max(2, (os.cpu_count() or 4) - 1)
            torch.set_num_threads(cekirdek)
        except Exception:
            pass

    if studyo_motor is not None:
        studyo_motor.donanim_kademesini_uygula(secilen_kod, kullanici_zorunlu=(zorunlu_kademe_kodu is not None))

    guncel = gpu_vram_durumu_getir()
    guncel["uygulanan_profil"] = secilen_kod
    guncel["profil_detay"] = DONANIM_PROFILLERI[secilen_kod]
    return guncel


# ==============================================================================
# 4. FASİH ARAPÇA FONETİK VAKIF & VASIL ÖN-İŞLEME MOTORU
# ==============================================================================
def hareke_siralamasini_normallestir(metin: str) -> str:
    if not metin:
        return ""
    metin = unicodedata.normalize("NFC", str(metin))
    metin = metin.replace("\u0640", "")
    # Hareke + Şedde -> Şedde + Hareke
    metin = re.sub(r"([\u064B-\u0650\u0652\u0670])(\u0651)", r"\2\1", metin)
    metin = metin.replace("آَ", "آ").replace("آُ", "آ").replace("آِ", "آ")
    metin = re.sub(r"([\u064B-\u0652])\1+", r"\1", metin)

    # Med harflerinin üzerindeki yanlış sükûnları temizle (فِيْ -> فِي)
    metin = re.sub(r"\u0650\u064A\u0652", "\u0650\u064A", metin)
    metin = re.sub(r"\u064F\u0648\u0652", "\u064F\u0648", metin)
    metin = metin.replace("اْ", "ا")

    # Cümle ortası (noktalama sonrası hariç) ve tek/çift önekli (وَالْ، فَبِالْ، وَبِالْ، وَلِلْ) vasıl hemzesi normalizasyonu
    metin = re.sub(r"(?<![.،؛؟!?,:;…\n]\s)(?<=\s)اَل(?=[ْ\u0621-\u064A])", "ال", metin)
    metin = re.sub(r"([وفبلك][\u064E\u0650\u064F]?)اَل(?=[ْ\u0621-\u064A])", r"\1ال", metin)
    metin = re.sub(r"([وف][\u064E\u0650\u064F]?[بلك][\u064E\u0650\u064F]?)اَل(?=[ْ\u0621-\u064A])", r"\1ال", metin)
    return metin


def kelime_sonunu_vakif_yap(kelime: str, kelime_turu: str = "genel") -> str:
    m = re.match(r"^(.*?)([.،؛؟!?,:;…»\"\']*)$", kelime)
    if not m:
        return kelime
    govde, noktalama = m.group(1), m.group(2)
    if not govde:
        return kelime
    govde = hareke_siralamasini_normallestir(govde)

    hareke_var_mi = bool(re.search(r"[\u064B-\u0652]", govde))
    if not hareke_var_mi:
        return govde + noktalama

    # Tek kelime modunda kullanıcı özellikle 'Fiil (Son Harekeyi Koru)' seçtiyse:
    # (Ancak fiilde yanlışlıkla tenvin varsa tenvini düşür)
    if kelime_turu == "fiil":
        govde = re.sub(r"[\u064B-\u064D]+$", "\u0652", govde)
        return govde + noktalama

    # 1. Medd-i İvaz (كِتَابًا -> كِتَابَا)
    if re.search(r"\u064B([\u0627\u0649])$", govde):
        govde = re.sub(r"\u064B([\u0627\u0649])$", "\u064E\\1", govde)
        return govde + noktalama
    if re.search(r"([\u0627\u0649])\u064B$", govde):
        govde = re.sub(r"([\u0627\u0649])\u064B$", "\u064E\\1", govde)
        return govde + noktalama
    if re.search(r"\u0621\u064B$", govde):
        govde = re.sub(r"\u0621\u064B$", "\u0621\u064E\u0627", govde)
        return govde + noktalama
    # 2. Tâ-i Merbûta -> Sükûnlu Hâ (مَدْرَسَةٌ -> مَدْرَسَهْ)
    if re.search(r"\u0629[\u064B-\u0652]*$", govde):
        govde = re.sub(r"\u0629[\u064B-\u0652]*$", "\u0647\u0652", govde)
        return govde + noktalama
    # 3. Şeddeli son harf vakfı
    if re.search(r"\u0651[\u064B-\u0650]+$", govde):
        govde = re.sub(r"\u0651[\u064B-\u0650]+$", "\u0651", govde)
        return govde + noktalama
    # 4. Med / illet harfiyle biten isim ve fiiller (يَدْعُو، يَرْمِي، تَفْقِدُهُمَا)
    if re.search(r"[\u0627\u0648\u064A\u0649]$", govde):
        return govde + noktalama
    # 5. Sahih harfle biten tüm isim ve fiillerde son kısa harekeyi/tenvini sükûna çevir (كَتَبَ -> كَتَبْ، يَكْتُبُ -> يَكْتُبْ)
    govde = re.sub(r"[\u064B-\u0650]+$", "\u0652", govde)
    return govde + noktalama


def arapca_akustik_metin_hazirla(
    metin: str,
    kelime_turu: str = "genel",
    hikmetli_durak_ekle: bool = False,
    ara_parca_mi: bool = False,
) -> str:
    temiz = hareke_siralamasini_normallestir(metin.strip())
    temiz = (
        temiz.replace("«", "")
        .replace("»", "")
        .replace('"', "")
        .replace("“", "")
        .replace("”", "")
        .replace("(", "")
        .replace(")", "")
    )
    temiz = re.sub(r"(?<!\d):(?!\d)", "،", temiz)

    if hikmetli_durak_ekle and "،" not in temiz:
        kelime_sayisi = len(temiz.split())
        if kelime_sayisi >= 5:
            for baglac in [" وَلَا ", " بَلْ ", " وَإِنَّمَا ", " فَلَا ", " فَإِنَّهُ ", " ولا ", " بل ", " وإنما "]:
                if baglac in temiz:
                    temiz = temiz.replace(baglac, f"،{baglac}", 1)
                    break

    temiz = re.sub(r"\s{2,}", " ", temiz).strip()
    if not temiz:
        return temiz

    kelimeler = temiz.split(" ")
    islenmis = []
    for i, klm in enumerate(kelimeler):
        son_kelime_mi = (i == len(kelimeler) - 1)
        durak_var_mi = bool(re.search(r"[.،؛؟!?,:;…]$", klm))
        if (son_kelime_mi and not ara_parca_mi) or durak_var_mi:
            tur_param = kelime_turu if (len(kelimeler) == 1 and son_kelime_mi) else "genel"
            islenmis.append(kelime_sonunu_vakif_yap(klm, kelime_turu=tur_param))
        else:
            islenmis.append(klm)

    sonuc = " ".join(islenmis)
    if ara_parca_mi:
        if not re.search(r"[.،؛؟!?,:;…]$", sonuc):
            sonuc += "،"
    else:
        sonuc = re.sub(r"[،؛,:;]+$", ".", sonuc)
        if not re.search(r"[.؟!…]$", sonuc):
            sonuc += "."
    return sonuc


def _referans_prompt_metni_hazirla(ref_metin: str, yerlesik_mi: bool = False) -> str:
    """
    Referans seste okunan Arapça metni (Prompt Text) Spark-TTS için hazırlar.
    - Yerleşik 8 seste REF_METIN_1 / REF_METIN_2 olduğu gibi korunur.
    - Kullanıcı özel seslerinde cümle ortasındaki noktalar ('.', '؟', '!', '؛') virgüle ('،') çevrilir ki
      LLM referans metnin ortasında erken EOS (cümle bitişi) üretip cızırtıya girmesin!
    """
    temiz = str(ref_metin or "").strip()
    if not temiz:
        return ""
    if yerlesik_mi:
        return temiz

    temiz = hareke_siralamasini_normallestir(temiz)
    temiz = re.sub(r"[«»\"“”()]", "", temiz)
    govde = re.sub(r"[.،؛؟!?,:;…]+$", "", temiz).strip()
    govde = re.sub(r"[.؟!?;:؛]+\s*", "، ", govde)
    govde = re.sub(r"\s{2,}", " ", govde).strip()
    if not govde:
        return ""
    return govde + "."


# ==============================================================================
# 5. ÖZEL REFERANS SES İÇ BOŞLUK SIKIŞTIRICI, CIZIRTI DENETLEYİCİ VE DSP MASTERING
# ==============================================================================
def _ozel_referans_ses_ic_bosluk_sikistir(
    audio: np.ndarray,
    sample_rate: int = 24000,
    maks_ic_bosluk_ms: float = 420.0,
    hedef_ic_bosluk_ms: float = 220.0,
    maks_toplam_sure_sn: float = 12.0,
) -> np.ndarray:
    """
    Kullanıcının eklediği özel referans seslerde doğal nefes ve konuşma ritmini koruyarak
    aşırı uzun (280 ms üstü) ölü sessizlik koridorlarını 150 ms doğal nefes payına sıkıştırır,
    birleştirme noktalarında 15 ms Raised-Cosine yumuşatma uygular ve sondaki ölü kuyruğu kırpar.
    """
    veri = np.asarray(audio, dtype=np.float32).flatten()
    if veri.size < int(sample_rate * 0.4):
        return veri

    veri = veri - np.mean(veri)
    tepe = float(np.max(np.abs(veri)))
    if tepe < 1e-5:
        return veri
    veri = (veri / tepe) * 0.891

    win_len = max(1, int(sample_rate * 0.020))
    kernel = np.ones(win_len, dtype=np.float32) / float(win_len)
    rms = np.sqrt(np.convolve(veri ** 2, kernel, mode="same")[:veri.size] + 1e-12)
    rms_tepe = float(np.max(rms)) if np.max(rms) > 1e-6 else 1.0

    # Nefes ve hafif son harfleri korumak için hassas eşik (%2.5)
    aktif_maske = rms > (rms_tepe * 0.025)
    if not np.any(aktif_maske):
        return veri

    maks_bosluk_ornek = int(sample_rate * (maks_ic_bosluk_ms / 1000.0))
    hedef_bosluk_ornek = int(sample_rate * (hedef_ic_bosluk_ms / 1000.0))
    min_ada_ornek = int(sample_rate * 0.075)

    fark = np.diff(aktif_maske.astype(np.int8))
    baslar = list(np.where(fark == 1)[0] + 1)
    sonlar = list(np.where(fark == -1)[0] + 1)
    if aktif_maske[0]:
        baslar.insert(0, 0)
    if aktif_maske[-1]:
        sonlar.append(veri.size)

    ham_adalar: List[Tuple[int, int]] = []
    for b, s in zip(baslar, sonlar):
        if s - b >= min_ada_ornek:
            ham_adalar.append((b, s))

    if not ham_adalar:
        return veri

    birlesik_adalar: List[List[int]] = [[ham_adalar[0][0], ham_adalar[0][1]]]
    for b, s in ham_adalar[1:]:
        if b - birlesik_adalar[-1][1] <= maks_bosluk_ornek:
            birlesik_adalar[-1][1] = s
        else:
            birlesik_adalar.append([b, s])

    parcalar: List[np.ndarray] = []
    ara_sessizlik = np.zeros(hedef_bosluk_ornek, dtype=np.float32)
    # 22 ms Raised-Cosine yumuşak geçiş (Zero-crossing tıklamalarını önler)
    fade_n = max(1, int(sample_rate * 0.022))
    giris_egrisi = 0.5 * (1.0 - np.cos(np.linspace(0.0, math.pi, fade_n, dtype=np.float32)))
    cikis_egrisi = 0.5 * (1.0 + np.cos(np.linspace(0.0, math.pi, fade_n, dtype=np.float32)))

    bas_pad = int(sample_rate * 0.060)
    son_pad = int(sample_rate * 0.095)

    for idx, (b, s) in enumerate(birlesik_adalar):
        b_pay = max(0, b - (bas_pad if idx == 0 else int(sample_rate * 0.035)))
        s_pay = min(veri.size, s + (son_pad if idx == len(birlesik_adalar) - 1 else int(sample_rate * 0.045)))
        dilim = veri[b_pay:s_pay].copy()
        if dilim.size > fade_n * 3:
            dilim[:fade_n] *= giris_egrisi
            dilim[-fade_n:] *= cikis_egrisi
        parcalar.append(dilim)
        if idx < len(birlesik_adalar) - 1:
            parcalar.append(ara_sessizlik)

    sikistirilmis = np.concatenate(parcalar).astype(np.float32)

    maks_ornek = int(sample_rate * maks_toplam_sure_sn)
    if sikistirilmis.size > maks_ornek:
        sikistirilmis = sikistirilmis[:maks_ornek].copy()
        son_fade = min(int(sample_rate * 0.075), sikistirilmis.size // 4)
        if son_fade > 0:
            son_e = 0.5 * (1.0 + np.cos(np.linspace(0.0, math.pi, son_fade, dtype=np.float32)))
            sikistirilmis[-son_fade:] *= son_e

    son_tepe = float(np.max(np.abs(sikistirilmis)))
    if son_tepe > 1e-6:
        sikistirilmis = (sikistirilmis / son_tepe) * 0.891
    return sikistirilmis


def _ses_cizirti_veya_bozuk_mu(wav_np: np.ndarray, sample_rate: int = 24000) -> bool:
    """
    Üretilen sesin sabit genlikli cızırtı / osilasyon döngüsüne girip girmediğini tespit eder.
    - 0.15 sn altındaki aşırı kısa çıktılar bozuk/boş kabul edilir.
    - 0.15 sn - 0.45 sn arasındaki çıktılar kısa tek kelime ('كِتَابٌ' vb.) olabileceği için
      yeterli sinyal enerjisi varsa geçerli kabul edilir (yanlış alarm önlenir).
    """
    veri = np.asarray(wav_np, dtype=np.float32).flatten()
    if veri.size < int(sample_rate * 0.15):
        return True

    if veri.size < int(sample_rate * 0.45):
        return float(np.max(np.abs(veri))) < 1e-4

    cerceve_boyu = max(1, int(sample_rate * 0.025))
    tam_boy = (veri.size // cerceve_boyu) * cerceve_boyu
    if tam_boy < cerceve_boyu * 8:
        return False

    matris = veri[:tam_boy].reshape(-1, cerceve_boyu)
    cerceve_rms = np.sqrt(np.mean(matris ** 2, axis=1) + 1e-12)
    tepe_rms = float(np.max(cerceve_rms))
    if tepe_rms < 1e-4:
        return True

    aktif_rms = cerceve_rms[cerceve_rms > (tepe_rms * 0.12)]
    if aktif_rms.size < 6:
        return True

    ortalama = float(np.mean(aktif_rms))
    std = float(np.std(aktif_rms))
    degisim_katsayisi = std / max(1e-6, ortalama)

    sure_sn = float(veri.size) / float(sample_rate)
    if sure_sn > 1.2 and degisim_katsayisi < 0.18:
        return True

    return False


def _ses_dogallik_puani_hesapla(wav_np: np.ndarray, sample_rate: int = 24000) -> float:
    """Best-of-2 seçimi için sesin zarf dinamizmini (CV) ve geçerliliğini puanlar."""
    veri = np.asarray(wav_np, dtype=np.float32).flatten()
    if veri.size < int(sample_rate * 0.15):
        return 0.0
    cerceve_boyu = max(1, int(sample_rate * 0.025))
    tam_boy = (veri.size // cerceve_boyu) * cerceve_boyu
    if tam_boy < cerceve_boyu * 4:
        return 0.5
    matris = veri[:tam_boy].reshape(-1, cerceve_boyu)
    cerceve_rms = np.sqrt(np.mean(matris ** 2, axis=1) + 1e-12)
    tepe_rms = float(np.max(cerceve_rms))
    if tepe_rms < 1e-4:
        return 0.0
    aktif_rms = cerceve_rms[cerceve_rms > (tepe_rms * 0.12)]
    if aktif_rms.size < 4:
        return 0.1
    cv = float(np.std(aktif_rms)) / max(1e-6, float(np.mean(aktif_rms)))
    return cv


def _token_tekrar_dongusu_var_mi(token_dizisi: List[int]) -> bool:
    """Üretilen semantik tokenlarda aynı 1-4 tokenlık kalıbın arka arkaya 16+ kez tekrarlanıp tekrarlanmadığını denetler."""
    if len(token_dizisi) < 35:
        return False
    sayac = 1
    for i in range(1, len(token_dizisi)):
        if token_dizisi[i] == token_dizisi[i - 1]:
            sayac += 1
            if sayac >= 16:
                return True
        else:
            sayac = 1
    son_dilim = token_dizisi[-60:] if len(token_dizisi) >= 60 else token_dizisi
    if len(son_dilim) >= 45 and len(set(son_dilim)) <= 4:
        return True
    return False


def studyo_dsp_mastering(
    wav_np: np.ndarray,
    sample_rate: int = 24000,
    tek_kelime_mi: bool = False,
    referans_on_temizlik_mi: bool = False,
    ozel_referans_mi: bool = False,
    dsp_ayar: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    """
    5-Katmanlı 24kHz Stüdyo DSP Mastering (Anti-Aliasing Sıralamalı):
      1. DC Offset Temizliği
      2. Sıfır Fazlı Butterworth High-Pass Filtre (sosfiltfilt)
      3. Doğal Nefes Korumalı Yumuşak RMS Gate
      4. Asimetrik Başlangıç ve Bitiş Kırpma (Preset son_pay_ms değerine saygılı: 80ms - 450ms)
      5. Harmonik Sıcaklık (Tanh Drive: 1.00 - 1.22) -> Anti-Aliasing Butterworth Low-Pass Filtre (LPF, Drive'dan SONRA!)
      6. Kosinüs Eğrili (Raised-Cosine) Giriş ve 150ms Doğal Çıkış + 120ms Sessizlik Yastığı
    """
    audio = np.asarray(wav_np, dtype=np.float32)
    if audio.ndim > 1:
        audio = np.mean(audio, axis=-1)
    audio = audio.flatten()
    if audio.size < 200:
        return audio

    if not np.all(np.isfinite(audio)):
        audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)

    audio = audio - np.mean(audio)

    if referans_on_temizlik_mi:
        if ozel_referans_mi:
            return _ozel_referans_ses_ic_bosluk_sikistir(audio, sample_rate=sample_rate)
        abs_ref = np.abs(audio)
        peak_ref = float(np.max(abs_ref)) if np.max(abs_ref) > 1e-6 else 1.0
        aktif_ref = np.where(abs_ref > (peak_ref * 0.005))[0]
        if aktif_ref.size > 0:
            bas_r = max(0, int(aktif_ref[0]) - int(sample_rate * 0.080))
            son_r = min(audio.size, int(aktif_ref[-1]) + int(sample_rate * 0.160))
            audio = audio[bas_r:son_r]
        max_r = float(np.max(np.abs(audio)))
        if max_r > 1e-6:
            audio = (audio / max_r) * 0.891
        return audio.astype(np.float32)

    dsp_ayar = dsp_ayar or {}
    hp_istek = float(dsp_ayar.get("hp_freq", 75.0))
    lp_istek = float(dsp_ayar.get("lp_freq", 11200.0))
    varsayilan_gate = 0.018 if tek_kelime_mi else 0.014
    gate_katsayi = float(dsp_ayar.get("gate_esigi", varsayilan_gate))
    bas_aktif_esik = float(dsp_ayar.get("aktif_esik_katsayi", 0.018))
    son_aktif_esik = min(0.005, bas_aktif_esik * 0.25)

    varsayilan_bas_ms = 45.0 if tek_kelime_mi else 55.0
    varsayilan_son_ms = 220.0 if tek_kelime_mi else 260.0
    bas_pay_sn = max(0.030, min(0.250, float(dsp_ayar.get("bas_pay_ms", varsayilan_bas_ms)) / 1000.0))
    # Preset ve tonlama profillerinin son_pay_ms (80ms - 450ms) değerine tam saygı gösterilir
    son_pay_sn = max(0.080, min(0.450, float(dsp_ayar.get("son_pay_ms", varsayilan_son_ms)) / 1000.0))

    drive = float(dsp_ayar.get("drive", 1.06))
    bas_fade_sn = max(0.008, min(0.060, float(dsp_ayar.get("fade_ms", 12.0)) / 1000.0))
    son_fade_sn = 0.120 if tek_kelime_mi else 0.150
    tepe_norm = float(dsp_ayar.get("tepe_normalizasyon", 0.891))

    nyq = sample_rate * 0.5

    # 1. Sıfır Fazlı Butterworth High-Pass Filtre (Dip uğultusu ve plosive temizliği)
    try:
        hp_freq = min(max(45.0, hp_istek), nyq * 0.8)
        sos_hp = signal.butter(2, hp_freq, btype="highpass", fs=sample_rate, output="sos")
        audio = signal.sosfiltfilt(sos_hp, audio).astype(np.float32)
    except Exception:
        pass

    # 2. Doğal Nefes Korumalı Yumuşak RMS Gürültü Kapısı
    if gate_katsayi > 0.005:
        win_len = max(1, min(int(sample_rate * 0.025), audio.size // 2))
        kernel = np.ones(win_len, dtype=np.float32) / float(win_len)
        rms = np.sqrt(np.convolve(audio ** 2, kernel, mode="same")[:audio.size] + 1e-12)
        peak_rms = float(np.max(rms)) if np.max(rms) > 1e-6 else 1.0
        gate_esigi = peak_rms * min(0.026, gate_katsayi)
        ham_oran = np.clip((rms - gate_esigi * 0.25) / (gate_esigi * 0.75 + 1e-9), 0.0, 1.0)
        kazanc = 0.22 + 0.78 * (ham_oran ** 1.15)
        yumusatma_penceresi = max(1, min(int(sample_rate * 0.060), audio.size // 2))
        yumusak_kazanc = np.convolve(
            kazanc,
            np.ones(yumusatma_penceresi, dtype=np.float32) / float(yumusatma_penceresi),
            mode="same"
        )[:audio.size]
        audio = (audio * yumusak_kazanc).astype(np.float32)

    # 3. Asimetrik Başlangıç ve Bitiş Kırpma
    abs_audio = np.abs(audio)
    peak = float(np.max(abs_audio)) if np.max(abs_audio) > 1e-6 else 1.0
    bas_indisler = np.where(abs_audio > (peak * bas_aktif_esik))[0]
    son_indisler = np.where(abs_audio > (peak * son_aktif_esik))[0]

    if bas_indisler.size > 0 and son_indisler.size > 0:
        bas_pay = int(sample_rate * bas_pay_sn)
        son_pay = int(sample_rate * son_pay_sn)
        bas = max(0, int(bas_indisler[0]) - bas_pay)
        son = min(audio.size, int(son_indisler[-1]) + son_pay)
        if son > bas + 400:
            audio = audio[bas:son]

    # 4. Harmonik Sıcaklık (%65 Dry + %35 Wet Tanh Drive: 1.00 - 1.14) — Low-Pass Filtreden ÖNCE uygulanır!
    max_deger = float(np.max(np.abs(audio)))
    if max_deger > 1e-6:
        audio = audio / max_deger
        etkin_drive = min(1.14, max(1.0, drive))
        if etkin_drive > 1.01:
            wet = np.tanh(audio * etkin_drive) / np.tanh(etkin_drive)
            audio = (0.65 * audio + 0.35 * wet).astype(np.float32)

    # 5. Anti-Aliasing 2. Derece Butterworth Low-Pass Filtre (Peltek ve ıslıklı harf netliğini korur)
    try:
        etkin_lp = 11500.0 if abs(lp_istek - 11200.0) < 10.0 else lp_istek
        lp_freq = min(max(6000.0, etkin_lp), nyq * 0.96)
        sos_lp = signal.butter(2, lp_freq, btype="lowpass", fs=sample_rate, output="sos")
        audio = signal.sosfiltfilt(sos_lp, audio).astype(np.float32)
    except Exception:
        pass

    # 6. Kosinüs Eğrili (Raised-Cosine) Giriş (Fade-In) ve Doğal Çıkış (Fade-Out)
    bas_fade_n = min(int(sample_rate * bas_fade_sn), audio.size // 6)
    if bas_fade_n > 0:
        giris_egrisi = 0.5 * (1.0 - np.cos(np.linspace(0.0, math.pi, bas_fade_n, dtype=np.float32)))
        audio[:bas_fade_n] *= giris_egrisi

    son_fade_n = min(int(sample_rate * son_fade_sn), audio.size // 3)
    if son_fade_n > 0:
        cikis_egrisi = 0.5 * (1.0 + np.cos(np.linspace(0.0, math.pi, son_fade_n, dtype=np.float32)))
        audio[-son_fade_n:] *= cikis_egrisi

    son_max = float(np.max(np.abs(audio)))
    if son_max > 1e-6:
        audio = (audio / son_max) * tepe_norm

    kapanis_sessizligi = np.zeros(int(sample_rate * 0.120), dtype=np.float32)
    audio = np.concatenate([audio, kapanis_sessizligi]).astype(np.float32)
    return audio


def referans_sesi_on_temizle(orijinal_wav_yolu: str | Path) -> str:
    orijinal_yol = Path(orijinal_wav_yolu)
    if not orijinal_yol.exists():
        alternatif = BASE_DIR / orijinal_yol.name
        ozel_alternatif = BASE_DIR / "referans_sesler_ozel" / orijinal_yol.name
        if alternatif.exists():
            orijinal_yol = alternatif
        elif ozel_alternatif.exists():
            orijinal_yol = ozel_alternatif
        else:
            # Eğer 8 yerleşik sesten biri diskte eksikse çökme yerine mevcut yerleşik sese (ref_erkek_1 / ref_kadin_1) zarif geçiş yap
            isim_kucuk = orijinal_yol.name.lower()
            yedek_ad = ANA_REF_KADIN if ("kadin" in isim_kucuk or "kiz" in isim_kucuk) else ANA_REF_ERKEK
            yedek_yol = BASE_DIR / yedek_ad
            if yedek_yol.exists():
                print(f"   ℹ️ '{orijinal_yol.name}' bulunamadı, yerleşik yedek ses kullanılıyor: '{yedek_ad}'")
                orijinal_yol = yedek_yol
            else:
                raise FileNotFoundError(
                    f"Seçilen referans ses dosyası bulunamadı: '{orijinal_yol.name}'. "
                    "Lütfen '2. Referans Sesler' sekmesinden ses dosyasını kontrol edin."
                )

    orijinal_yol = orijinal_yol.resolve()
    yerlesik_mi = yerlesik_ref_ses_mi(orijinal_yol)
    stat = orijinal_yol.stat()
    kimlik_imzasi = f"{orijinal_yol}|{stat.st_mtime_ns}|{stat.st_size}|v8|{int(yerlesik_mi)}"
    kisa_hash = hashlib.sha1(kimlik_imzasi.encode("utf-8")).hexdigest()[:12]

    REF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    hedef_cache_yol = REF_CACHE_DIR / f"{orijinal_yol.stem}_{kisa_hash}.wav"
    if hedef_cache_yol.exists() and hedef_cache_yol.stat().st_size > 1000:
        return str(hedef_cache_yol)

    try:
        veri, sr = sf.read(str(orijinal_yol), dtype="float32")
    except Exception:
        if not shutil.which("ffmpeg"):
            raise RuntimeError(f"Referans ses okunamadı ve FFmpeg kurulu değil: {orijinal_yol.name}")
        gecici_wav = REF_CACHE_DIR / f"_tmp_{uuid.uuid4().hex[:8]}.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(orijinal_yol), "-ar", "24000", "-ac", "1", str(gecici_wav)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            creationflags=(subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0),
        )
        veri, sr = sf.read(str(gecici_wav), dtype="float32")
        if gecici_wav.exists():
            os.remove(gecici_wav)

    if veri.ndim > 1:
        veri = np.mean(veri, axis=-1)
    hedef_sr = 24000
    if sr != hedef_sr:
        veri = _yuksek_kalite_resample(veri, sr, hedef_sr)

    temiz_veri = studyo_dsp_mastering(
        veri,
        sample_rate=hedef_sr,
        tek_kelime_mi=False,
        referans_on_temizlik_mi=True,
        ozel_referans_mi=(not yerlesik_mi),
    )
    sf.write(str(hedef_cache_yol), temiz_veri, hedef_sr, subtype="PCM_16")
    return str(hedef_cache_yol)


def sesi_diske_kaydet(
    wav_np: np.ndarray,
    cikti_yolu: str | Path,
    sample_rate: int = 24000,
    hiz: float = 1.0,
    wav_formatini_zorla: bool = False,
) -> bool:
    cikti_str = str(cikti_yolu)
    hedef_dir = os.path.dirname(os.path.abspath(cikti_str))
    os.makedirs(hedef_dir, exist_ok=True)

    wav_istendi = wav_formatini_zorla or cikti_str.lower().endswith(".wav")
    ffmpeg_var = bool(shutil.which("ffmpeg"))
    hiz_degisimi_var = (hiz < 0.88 or hiz > 1.03) and (0.75 <= hiz <= 1.25)

    benzersiz_ek = uuid.uuid4().hex[:8]
    gecici_wav = f"{cikti_str}.{benzersiz_ek}.tmp.wav"

    if wav_istendi and not hiz_degisimi_var:
        sf.write(gecici_wav, wav_np, sample_rate, subtype="PCM_16")
        os.replace(gecici_wav, cikti_str)
        return True

    if not ffmpeg_var and wav_istendi:
        sf.write(gecici_wav, wav_np, sample_rate, subtype="PCM_16")
        os.replace(gecici_wav, cikti_str)
        return True

    if not ffmpeg_var and not wav_istendi:
        try:
            gecici_mp3 = f"{cikti_str}.{benzersiz_ek}.tmp.mp3"
            sf.write(gecici_mp3, wav_np, sample_rate, format="MP3")
            os.replace(gecici_mp3, cikti_str)
            return True
        except Exception:
            raise RuntimeError(
                "MP3 formatında dışa aktarım için sistemde 'FFmpeg' kurulu olmalıdır. "
                "Lütfen çıktı formatını 'WAV' seçin veya 'Modeller & Kurulum' ekranından FFmpeg kurun."
            )

    sf.write(gecici_wav, wav_np, sample_rate, subtype="PCM_16")
    try:
        filtre_zinciri = []
        if hiz_degisimi_var:
            filtre_zinciri.append(f"atempo={hiz:.2f}")
        # level=0 tüm FFmpeg sürümleriyle uyumludur (level=disabled bazı sürümlerde boolean hatası verir)
        filtre_zinciri.append("alimiter=limit=0.891:attack=5:release=50:level=0")

        komut = ["ffmpeg", "-y", "-i", gecici_wav, "-af", ",".join(filtre_zinciri)]
        if wav_istendi:
            gecici_hedef = f"{cikti_str}.{benzersiz_ek}.out.wav"
            komut += ["-ar", str(sample_rate), "-ac", "1", "-sample_fmt", "s16", gecici_hedef]
        else:
            gecici_hedef = f"{cikti_str}.{benzersiz_ek}.out.mp3"
            komut += ["-ar", str(sample_rate), "-ac", "1", "-b:a", "192k", "-write_xing", "0", gecici_hedef]

        res = subprocess.run(
            komut,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
            creationflags=(subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0),
        )
        if res.returncode == 0 and os.path.exists(gecici_hedef) and os.path.getsize(gecici_hedef) > 800:
            os.replace(gecici_hedef, cikti_str)
            if os.path.exists(gecici_wav):
                os.remove(gecici_wav)
            return True
        else:
            if wav_istendi and os.path.exists(gecici_wav):
                os.replace(gecici_wav, cikti_str)
                return True
            hata_detay = (res.stderr or "")[-200:].strip()
            raise RuntimeError(f"FFmpeg ses dönüştürme hatası: {hata_detay}")
    finally:
        for p in [gecici_wav, f"{cikti_str}.{benzersiz_ek}.out.wav", f"{cikti_str}.{benzersiz_ek}.out.mp3"]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


# ==============================================================================
# 6. SATIR SONU VE HAREKESİZ EDAT KORUMALI AKILLI BÖLÜCÜ & SES BİRLEŞTİRİCİ
# ==============================================================================
def uzun_metni_cumlelere_bol(arapca_paragraf: str, maks_kelime: int = 14) -> List[str]:
    ham_metin = str(arapca_paragraf or "").strip()
    if not ham_metin:
        return []

    satir_bloklari = [re.sub(r"[ \t]+", " ", s.strip()) for s in ham_metin.splitlines() if s.strip()]
    ham_cumleler: List[str] = []
    for blok in satir_bloklari:
        parcalar = re.split(r"(?<=[.؟!?\u061F…])\s+", blok)
        for p in parcalar:
            if p.strip():
                ham_cumleler.append(p.strip())

    sonuc_parcalar: List[str] = []

    for cumle in ham_cumleler:
        kelimeler = cumle.split()
        if len(kelimeler) <= maks_kelime:
            sonuc_parcalar.append(cumle)
        else:
            alt_parcalar = re.split(r"(?<=[،؛,;])\s+", cumle)
            tampon: List[str] = []
            for alt in alt_parcalar:
                alt = alt.strip()
                if not alt:
                    continue
                if len(" ".join(tampon + [alt]).split()) <= maks_kelime:
                    tampon.append(alt)
                else:
                    if tampon:
                        sonuc_parcalar.append(" ".join(tampon))
                        tampon = []
                    alt_kelimeler = alt.split()
                    if len(alt_kelimeler) > maks_kelime:
                        gecici_grup: List[str] = []
                        for klm in alt_kelimeler:
                            gecici_grup.append(klm)
                            son_klm_temiz = klm.rstrip(".،؛؟!?,:;…")
                            son_klm_harekesiz = arapca_harekeleri_soy(son_klm_temiz)
                            edat_mi = (
                                son_klm_temiz in BOLUNMEZ_ARAPCA_EDATLAR
                                or son_klm_harekesiz in BOLUNMEZ_ARAPCA_EDATLAR_HAREKESIZ
                            )
                            if len(gecici_grup) >= maks_kelime and not edat_mi:
                                sonuc_parcalar.append(" ".join(gecici_grup))
                                gecici_grup = []
                        if gecici_grup:
                            if sonuc_parcalar and len(gecici_grup) <= 2:
                                sonuc_parcalar[-1] = sonuc_parcalar[-1] + " " + " ".join(gecici_grup)
                            else:
                                sonuc_parcalar.append(" ".join(gecici_grup))
                    else:
                        tampon = [alt]
            if tampon:
                sonuc_parcalar.append(" ".join(tampon))

    return sonuc_parcalar


def _ses_dosyasini_guvenli_oku_np(dosya_yolu: str, hedef_sr: int = 24000) -> np.ndarray:
    dosya_str = str(dosya_yolu)
    uzanti = Path(dosya_str).suffix.lower()

    if uzanti == ".mp3" and shutil.which("ffmpeg"):
        REF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        gecici_wav = REF_CACHE_DIR / f"_decode_{uuid.uuid4().hex[:8]}.wav"
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", dosya_str, "-ar", str(hedef_sr), "-ac", "1", str(gecici_wav)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                creationflags=(subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0),
            )
            veri, sr = sf.read(str(gecici_wav), dtype="float32")
        finally:
            try:
                if gecici_wav.exists():
                    gecici_wav.unlink()
            except OSError:
                pass
    else:
        try:
            veri, sr = sf.read(dosya_str, dtype="float32")
        except Exception:
            if not shutil.which("ffmpeg"):
                raise RuntimeError(f"Ses dosyası okunamadı: {dosya_yolu}")
            REF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            gecici_wav = REF_CACHE_DIR / f"_decode_{uuid.uuid4().hex[:8]}.wav"
            subprocess.run(
                ["ffmpeg", "-y", "-i", dosya_str, "-ar", str(hedef_sr), "-ac", "1", str(gecici_wav)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                creationflags=(subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0),
            )
            veri, sr = sf.read(str(gecici_wav), dtype="float32")
            try:
                gecici_wav.unlink()
            except OSError:
                pass

    if veri.ndim > 1:
        veri = np.mean(veri, axis=-1)
    veri = veri.flatten()
    if sr != hedef_sr and veri.size > 0:
        veri = _yuksek_kalite_resample(veri, sr, hedef_sr)
    return veri.astype(np.float32)


def sesleri_studyo_kalitesinde_birlestir(
    girdi_dosyalari: List[str | Path],
    cikti_dosyasi: str | Path,
    bosluk_ms: int = 260,
    mikro_fade_ms: int = 25,
    birlestirilmis_seviye_dengele: bool = True,
) -> bool:
    if not girdi_dosyalari:
        return False

    hedef_sr = 24000
    parcalar: List[np.ndarray] = []
    bosluk_sn = max(0.0, float(bosluk_ms) / 1000.0)
    sessizlik = np.zeros(int(hedef_sr * bosluk_sn), dtype=np.float32)

    try:
        for i, dosya in enumerate(girdi_dosyalari):
            dosya_str = str(dosya)
            if not os.path.exists(dosya_str) or os.path.getsize(dosya_str) < 400:
                return False

            veri = _ses_dosyasini_guvenli_oku_np(dosya_str, hedef_sr=hedef_sr)
            if veri.size == 0:
                continue

            # Duygusal vurgu kontrastını ezmeden nazik seviye dengeleme (-3 dB ile +3.2 dB arası)
            if birlestirilmis_seviye_dengele and veri.size > 200:
                rms = float(np.sqrt(np.mean(veri ** 2) + 1e-12))
                hedef_rms = 0.14
                if rms > 1e-4:
                    kazanc = max(0.70, min(1.45, hedef_rms / rms))
                    veri = veri * kazanc
                tepe = float(np.max(np.abs(veri)))
                if tepe > 0.891:
                    veri = (veri / tepe) * 0.891

            fade_n = min(int(hedef_sr * (float(mikro_fade_ms) / 1000.0)), veri.size // 4)
            if fade_n > 0:
                giris_e = 0.5 * (1.0 - np.cos(np.linspace(0.0, math.pi, fade_n, dtype=np.float32)))
                cikis_e = 0.5 * (1.0 + np.cos(np.linspace(0.0, math.pi, fade_n, dtype=np.float32)))
                veri[:fade_n] *= giris_e
                veri[-fade_n:] *= cikis_e

            parcalar.append(veri.astype(np.float32))
            if i < len(girdi_dosyalari) - 1 and sessizlik.size > 0:
                parcalar.append(sessizlik)

        if not parcalar:
            return False

        birlesik_ses = np.concatenate(parcalar).astype(np.float32)
        genel_tepe = float(np.max(np.abs(birlesik_ses)))
        if genel_tepe > 0.891:
            birlesik_ses = (birlesik_ses / genel_tepe) * 0.891

        sesi_diske_kaydet(birlesik_ses, cikti_yolu=str(cikti_dosyasi), sample_rate=hedef_sr, hiz=1.0)
        return os.path.exists(str(cikti_dosyasi)) and os.path.getsize(str(cikti_dosyasi)) > 1000
    except Exception as e:
        print(f"   ⚠️ Stüdyo ses birleştirme hatası: {e}")
        return False


# ==============================================================================
# 7. TOKEN BAZLI ANINDA DURDURMA VE CANLI İLERLEME KRİTERİ
# ==============================================================================
try:
    from transformers import StoppingCriteria, StoppingCriteriaList

    class _StudyoDurdurmaVeIlerlemeKriteri(StoppingCriteria):
        def __init__(
            self,
            motor: "MuallimunStudyoSesMotoru",
            baslangic_len: int,
            hedef_tok: int,
            ilerleme_cb: Optional[Callable[[int, str], None]] = None,
            cancel_token: Optional[CancelToken] = None,
            tekrar_kontrolu_aktif: bool = False,
        ):
            super().__init__()
            self.motor = motor
            self.baslangic_len = baslangic_len
            self.hedef_tok = max(20, hedef_tok)
            self.ilerleme_cb = ilerleme_cb
            self.cancel_token = cancel_token
            self.tekrar_kontrolu_aktif = tekrar_kontrolu_aktif
            self.tekrar_tespit_edildi = False
            self.son_yuzde = 10

        def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
            if self.motor.iptal_edildi_mi(self.cancel_token):
                return True
            uretilen = int(input_ids.shape[-1]) - self.baslangic_len

            if self.tekrar_kontrolu_aktif and uretilen >= 40 and (uretilen % 10 == 0):
                son_tokenlar = input_ids[0, self.baslangic_len:].tolist()
                if _token_tekrar_dongusu_var_mi(son_tokenlar):
                    self.tekrar_tespit_edildi = True
                    return True

            if self.ilerleme_cb and uretilen > 0 and (uretilen % 5 == 0):
                yuzde = min(92, 15 + int((uretilen / float(self.hedef_tok)) * 77))
                if yuzde > self.son_yuzde:
                    self.son_yuzde = yuzde
                    try:
                        self.ilerleme_cb(yuzde, f"🎙️ Akustik ses dalgaları örülüyor... (%{yuzde})")
                    except Exception:
                        pass
            return False
except Exception:
    StoppingCriteria = object
    StoppingCriteriaList = list


# ==============================================================================
# 8. ANA STÜDYO SES MOTORU SINIFI (SPARK-TTS + DİREKT HIZLI TTS + XTTS v2)
# ==============================================================================
class MuallimunStudyoSesMotoru:
    def __init__(
        self,
        motor_tercihi: str = AKTIF_MOTOR_TERCIHI,
        log_callback: Optional[Callable[[str], None]] = None,
        zorunlu_kademe: Optional[str] = None,
    ):
        self._sentez_kilidi = threading.RLock()
        self.cuda_mevcut = torch.cuda.is_available()
        self.kullanici_cpu_zorladi = (zorunlu_kademe == "CPU_MODU")
        self.device = "cpu" if (not self.cuda_mevcut or self.kullanici_cpu_zorladi) else "cuda"

        self.motor_tipi = motor_tercihi if motor_tercihi in ("SPARK_ARABIC", "FAST_DIRECT_TTS", "XTTS_STUDIO") else "SPARK_ARABIC"
        self.processor = None
        self.spark_model = None
        self.llm_submodule = None
        self.eos_token_ids: List[int] = []
        self.pad_token_id: int = 151643
        self.xtts_model = None
        self.latent_onbellek: Dict[str, Any] = {}
        self._audio_token_cache: Dict[Any, Tuple[torch.Tensor, torch.Tensor]] = {}
        self._active_ref_key: Optional[str] = None
        self.log_callback = log_callback
        self._durdur_event = threading.Event()
        self.son_hata_mesaji: str = ""

        self.aktif_kademe_kodu = "PRO_STUDYO_12GB_USTU"
        self.dusuk_vram_modu = False
        self.max_token_ust_sinir = 1150
        self.kelime_token_carpani = 52
        self.bolme_esigi_kelime = 34
        self.parca_maks_kelime = 18

        _dahili_torchaudio_koprusunu_kur()
        _eski_gecici_onbellek_dosyalarini_temizle()

        self._log("=" * 68)
        self._log(f"🎛️  MUALLİMUN STÜDYO SES MOTORU BAŞLATILIYOR ({self.motor_tipi})")
        if self.device == "cuda":
            gpu_adi = torch.cuda.get_device_name(0)
            vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            bos_gb = None
            try:
                bos_byte, _ = torch.cuda.mem_get_info(0)
                bos_gb = bos_byte / (1024 ** 3)
            except Exception:
                pass
            secilecek_kademe = (
                zorunlu_kademe
                if (zorunlu_kademe and zorunlu_kademe in DONANIM_PROFILLERI)
                else vram_miktarina_gore_kademe_belirle(vram_gb, cuda_aktif=True, bos_gb=bos_gb)
            )
            self.donanim_kademesini_uygula(secilecek_kademe, kullanici_zorunlu=(zorunlu_kademe is not None))
            self._log(f"🚀 GPU: {gpu_adi} ({vram_gb:.1f} GB VRAM)")
            self._log(f"⚙️ Seçilen Donanım Kademesi: {DONANIM_PROFILLERI[self.aktif_kademe_kodu]['ad']}")
        else:
            self.donanim_kademesini_uygula("CPU_MODU", kullanici_zorunlu=True)
            self._log("💻 CPU Modu aktif: İşlemci çekirdekleri optimize edildi.")
        self._log("=" * 68)

        if self.motor_tipi == "FAST_DIRECT_TTS":
            self._log("⚡ 'Hızlı Direkt Neural TTS (Çevrimiçi 24kHz + Stüdyo DSP)' hazır! (VRAM: 0 MB)")
            return

        if self.motor_tipi == "XTTS_STUDIO":
            self._xtts_motorunu_yukle()
            return

        self._spark_motorunu_yukle()

    @property
    def durdur_istegi(self) -> bool:
        return self._durdur_event.is_set()

    @durdur_istegi.setter
    def durdur_istegi(self, deger: bool) -> None:
        if deger:
            self._durdur_event.set()
        else:
            self._durdur_event.clear()

    def durdur(self) -> None:
        self._durdur_event.set()

    def iptal_edildi_mi(self, cancel_token: Optional[CancelToken] = None) -> bool:
        if self._durdur_event.is_set():
            return True
        if cancel_token is not None and cancel_token.is_cancelled:
            return True
        return False

    def bosalt(self, sadece_pasif_modelleri: bool = False) -> None:
        if not self._sentez_kilidi.acquire(timeout=3.0):
            return
        try:
            if not sadece_pasif_modelleri or self.motor_tipi != "SPARK_ARABIC":
                if self.spark_model is not None:
                    try:
                        self.spark_model.to("cpu")
                    except Exception:
                        pass
                    self.spark_model = None
                    self.processor = None
                    self.llm_submodule = None
                    self._audio_token_cache.clear()

            if not sadece_pasif_modelleri or self.motor_tipi != "XTTS_STUDIO":
                if self.xtts_model is not None:
                    try:
                        self.xtts_model.to("cpu")
                    except Exception:
                        pass
                    self.xtts_model = None
                    self.latent_onbellek.clear()

            gc.collect()
            if torch.cuda.is_available():
                try:
                    torch.cuda.synchronize()
                    torch.cuda.empty_cache()
                    if hasattr(torch.cuda, "ipc_collect"):
                        torch.cuda.ipc_collect()
                except Exception:
                    pass
        finally:
            self._sentez_kilidi.release()

    def aktif_motoru_degistir(self, yeni_motor_tipi: str) -> None:
        hedef = yeni_motor_tipi if yeni_motor_tipi in ("SPARK_ARABIC", "FAST_DIRECT_TTS", "XTTS_STUDIO") else "SPARK_ARABIC"
        with self._sentez_kilidi:
            if hedef != self.motor_tipi:
                self.motor_tipi = hedef
                self.bosalt(sadece_pasif_modelleri=True)

    def _edge_tts_kontrol_et(self) -> None:
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            raise RuntimeError(
                "Hızlı Direkt TTS için 'edge-tts' paketi kurulu değil. "
                "Lütfen 'Modeller & Kurulum' ekranından 'Edge-TTS' modülünü kurun."
            )

    def _xtts_motorunu_yukle(self) -> bool:
        with self._sentez_kilidi:
            if self.xtts_model is not None:
                self._xtts_gpt_inference_yamasi_uygula()
                return True

            self.motor_tipi = "XTTS_STUDIO"
            self.bosalt(sadece_pasif_modelleri=True)

            try:
                from TTS.api import TTS
                self._log("📥 Coqui XTTS v2 Stüdyo Modeli yükleniyor...")

                orig_load = torch.load
                try:
                    torch.load = lambda *a, **kw: orig_load(*a, **{**kw, "weights_only": False})
                    tts_wrapper = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(self.device)
                finally:
                    torch.load = orig_load

                self.xtts_model = tts_wrapper.synthesizer.tts_model
                self._xtts_gpt_inference_yamasi_uygula()
                self._log("✅ Coqui XTTS v2 Hazır!")
                return True
            except Exception as e:
                self.son_hata_mesaji = f"Coqui XTTS v2 yüklenemedi: {e}"
                self._log(f"⚠️ Coqui XTTS v2 yüklenemedi ({e})")
                return False

    def _xtts_gpt_inference_yamasi_uygula(self) -> None:
        try:
            from transformers.cache_utils import DynamicCache
            from transformers.models.gpt2.modeling_gpt2 import GPT2Model
            from TTS.tts.layers.xtts.gpt_inference import GPT2InferenceModel

            if not getattr(GPT2Model, "_muallimun_gpt2_cache_patched", False):
                orig_gpt2_fwd = GPT2Model.forward

                @functools.wraps(orig_gpt2_fwd)
                def _patched_gpt2_fwd(model_self, input_ids=None, past_key_values=None, *args, **kwargs):
                    if past_key_values is not None:
                        if hasattr(past_key_values, "get_seq_length"):
                            if past_key_values.get_seq_length() == 0:
                                past_key_values = None
                            elif hasattr(past_key_values, "to_legacy_cache"):
                                past_key_values = past_key_values.to_legacy_cache()
                        elif isinstance(past_key_values, (tuple, list)) and (
                            len(past_key_values) == 0 or past_key_values[0] is None
                        ):
                            past_key_values = None

                    out = orig_gpt2_fwd(
                        model_self, input_ids=input_ids, past_key_values=past_key_values, *args, **kwargs
                    )
                    if (
                        hasattr(out, "past_key_values")
                        and out.past_key_values is not None
                        and isinstance(out.past_key_values, (tuple, list))
                    ):
                        cache_obj = DynamicCache.from_legacy_cache(out.past_key_values)
                        out.past_key_values = cache_obj
                        if isinstance(out, dict):
                            out["past_key_values"] = cache_obj
                    return out

                GPT2Model.forward = _patched_gpt2_fwd
                GPT2Model._muallimun_gpt2_cache_patched = True

            GPT2InferenceModel._validate_model_kwargs = lambda self, model_kwargs: None

            if not getattr(GPT2InferenceModel, "_muallimun_xtts_cls_patched", False):
                orig_cls_fwd = GPT2InferenceModel.forward

                @functools.wraps(orig_cls_fwd)
                def _xtts_cls_safe_fwd(model_self, input_ids=None, past_key_values=None, *args, **kwargs):
                    if past_key_values is not None:
                        if isinstance(past_key_values, (tuple, list)):
                            if len(past_key_values) == 0 or past_key_values[0] is None:
                                past_key_values = None
                            else:
                                past_key_values = DynamicCache.from_legacy_cache(past_key_values)
                        elif hasattr(past_key_values, "get_seq_length") and past_key_values.get_seq_length() == 0:
                            past_key_values = None

                    out = orig_cls_fwd(
                        model_self, input_ids=input_ids, past_key_values=past_key_values, *args, **kwargs
                    )
                    if (
                        hasattr(out, "past_key_values")
                        and out.past_key_values is not None
                        and isinstance(out.past_key_values, (tuple, list))
                    ):
                        cache_obj = DynamicCache.from_legacy_cache(out.past_key_values)
                        out.past_key_values = cache_obj
                        if isinstance(out, dict):
                            out["past_key_values"] = cache_obj
                    return out

                GPT2InferenceModel.forward = _xtts_cls_safe_fwd
                GPT2InferenceModel._muallimun_xtts_cls_patched = True

            def _xtts_kesin_prepare_inputs(
                model_self, input_ids, past_key_values=None, attention_mask=None, use_cache=None, **kwargs
            ):
                past_len = 0
                if past_key_values is not None:
                    if isinstance(past_key_values, (tuple, list)):
                        if len(past_key_values) > 0 and past_key_values[0] is not None:
                            past_key_values = DynamicCache.from_legacy_cache(past_key_values)
                        else:
                            past_key_values = None
                    if past_key_values is not None and hasattr(past_key_values, "get_seq_length"):
                        past_len = int(past_key_values.get_seq_length())

                if past_len > 0:
                    input_ids = input_ids[:, -1].unsqueeze(-1)
                else:
                    past_key_values = None

                position_ids = kwargs.get("position_ids", None)
                if attention_mask is not None and position_ids is None:
                    position_ids = attention_mask.long().cumsum(-1) - 1
                    position_ids.masked_fill_(attention_mask == 0, 1)
                    if past_len > 0:
                        position_ids = position_ids[:, -1].unsqueeze(-1)
                else:
                    position_ids = None

                return {
                    "input_ids": input_ids,
                    "past_key_values": past_key_values,
                    "use_cache": use_cache,
                    "position_ids": position_ids,
                    "attention_mask": attention_mask,
                    "token_type_ids": kwargs.get("token_type_ids", None),
                }

            GPT2InferenceModel.prepare_inputs_for_generation = _xtts_kesin_prepare_inputs

            if self.xtts_model is not None and hasattr(self.xtts_model, "gpt"):
                if getattr(self.xtts_model.gpt, "gpt_inference", None) is None and hasattr(
                    self.xtts_model.gpt, "init_gpt_for_inference"
                ):
                    self.xtts_model.gpt.init_gpt_for_inference()
                gpt_inf = getattr(self.xtts_model.gpt, "gpt_inference", None)
                if gpt_inf is not None:
                    gpt_inf._validate_model_kwargs = lambda model_kwargs: None
        except Exception as e:
            self._log(f"⚠️ XTTS uyumluluk yaması uyarısı: {e}")

    def _spark_motorunu_yukle(self) -> bool:
        with self._sentez_kilidi:
            if self.spark_model is not None:
                try:
                    self.spark_model.to(self.device)
                except Exception:
                    pass
                return True

            self.motor_tipi = "SPARK_ARABIC"
            self.bosalt(sadece_pasif_modelleri=True)

            try:
                from transformers import AutoProcessor, AutoModel
                self._log(f"📥 '{SPARK_HF_MODEL_ID}' (24kHz BiCodec) modeli {self.device.upper()} belleğine yükleniyor...")
                self.processor = AutoProcessor.from_pretrained(SPARK_HF_MODEL_ID, trust_remote_code=True)
                self.spark_model = AutoModel.from_pretrained(
                    SPARK_HF_MODEL_ID, trust_remote_code=True
                ).eval().to(self.device)

                if hasattr(self.processor, "link_model"):
                    self.processor.link_model(self.spark_model)

                self._spark_v5_uyumluluk_ve_onbellek_yamasi()

                if self.device == "cuda":
                    torch.cuda.empty_cache()

                self._log(f"✅ 'IbrahimSalah/Arabic-TTS-Spark' Hazır! (EOS Kilitleri: {self.eos_token_ids})")
                return True
            except Exception as e:
                self.processor = None
                self.spark_model = None
                self.son_hata_mesaji = f"Spark-TTS modeli yüklenemedi: {e}"
                self._log(f"⚠️ {self.son_hata_mesaji}")
                return False

    def donanim_kademesini_uygula(self, kademe_kodu: str, kullanici_zorunlu: bool = False) -> Dict[str, Any]:
        if kademe_kodu == "CPU_MODU":
            if kullanici_zorunlu or not self.cuda_mevcut:
                self.kullanici_cpu_zorladi = True
                self.device = "cpu"
                if self.spark_model is not None:
                    try:
                        self.spark_model.to("cpu")
                        if self.cuda_mevcut:
                            torch.cuda.empty_cache()
                    except Exception:
                        pass
            else:
                vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
                kademe_kodu = vram_miktarina_gore_kademe_belirle(vram_gb, cuda_aktif=True)
        elif self.cuda_mevcut:
            self.kullanici_cpu_zorladi = False
            self.device = "cuda"

        prof = DONANIM_PROFILLERI.get(kademe_kodu, DONANIM_PROFILLERI["HAFIF_4_6GB"])
        self.aktif_kademe_kodu = prof["kod"]
        self.max_token_ust_sinir = int(prof["max_token_ust_sinir"])
        self.kelime_token_carpani = int(prof["kelime_token_carpani"])
        self.bolme_esigi_kelime = int(prof["bolme_esigi_kelime"])
        self.parca_maks_kelime = int(prof["parca_maks_kelime"])
        self.dusuk_vram_modu = bool(prof["her_uretimde_cache_temizle"])
        return prof

    def _log(self, mesaj: str) -> None:
        print(mesaj)
        if self.log_callback is not None:
            try:
                self.log_callback(mesaj)
            except Exception:
                pass

    def _spark_v5_uyumluluk_ve_onbellek_yamasi(self) -> None:
        cfg = self.spark_model.config
        llm_cfg = getattr(cfg, "llm_config", None) or getattr(cfg, "text_config", None)

        for name, mod in self.spark_model.named_modules():
            if mod is self.spark_model:
                continue
            m_cfg = getattr(mod, "config", None)
            if m_cfg is not None and hasattr(m_cfg, "num_hidden_layers"):
                if (
                    getattr(m_cfg, "vocab_size", 0) > 30000
                    or "qwen" in type(mod).__name__.lower()
                    or name in ("llm", "model", "language_model", "text_model")
                ):
                    self.llm_submodule = mod
                    llm_cfg = m_cfg
                    break

        if isinstance(llm_cfg, dict):
            for k, v in llm_cfg.items():
                if not hasattr(cfg, k) or getattr(cfg, k) is None:
                    setattr(cfg, k, v)
        elif llm_cfg is not None:
            for k in dir(llm_cfg):
                if k.startswith("__"):
                    continue
                try:
                    v = getattr(llm_cfg, k)
                    if not callable(v) and (not hasattr(cfg, k) or getattr(cfg, k) is None):
                        setattr(cfg, k, v)
                except Exception:
                    pass

        aday_eos = []
        tok = getattr(self.processor, "tokenizer", None)
        if tok is not None:
            if getattr(tok, "eos_token_id", None) is not None:
                eid = tok.eos_token_id
                aday_eos.extend(eid if isinstance(eid, list) else [eid])
            try:
                vocab = tok.get_vocab()
                for t_str, t_id in vocab.items():
                    t_low = t_str.lower()
                    if t_low in (
                        "<|im_end|>",
                        "<|endoftext|>",
                        "<|end_semantic_token|>",
                        "<|end_of_semantic|>",
                        "<|end_audio|>",
                    ):
                        aday_eos.append(int(t_id))
            except Exception:
                pass

        if not aday_eos:
            aday_eos = [151643, 151645]

        self.eos_token_ids = sorted(list({int(x) for x in aday_eos if x is not None and int(x) >= 0}))
        self.pad_token_id = int(getattr(tok, "pad_token_id", None) or self.eos_token_ids[0])

        eksik_varsayilanlar = {
            "num_hidden_layers": 24,
            "hidden_size": 896,
            "num_attention_heads": 14,
            "num_key_value_heads": 2,
            "intermediate_size": 4864,
            "max_position_embeddings": 32768,
            "vocab_size": 166000,
            "rms_norm_eps": 1e-6,
            "rope_theta": 1000000.0,
            "sliding_window": 32768,
            "use_sliding_window": False,
            "max_window_layers": 24,
            "hidden_act": "silu",
            "is_encoder_decoder": False,
            "use_cache": True,
            "eos_token_id": self.eos_token_ids,
            "pad_token_id": self.pad_token_id,
        }
        for k, v in eksik_varsayilanlar.items():
            if not hasattr(cfg, k) or getattr(cfg, k) is None or k in ("eos_token_id", "pad_token_id"):
                try:
                    setattr(cfg, k, v)
                except Exception:
                    pass

        if not hasattr(cfg, "head_dim") or getattr(cfg, "head_dim") is None:
            try:
                setattr(cfg, "head_dim", int(cfg.hidden_size // cfg.num_attention_heads))
            except Exception:
                pass

        if hasattr(self.spark_model, "generation_config") and self.spark_model.generation_config is not None:
            try:
                self.spark_model.generation_config.eos_token_id = self.eos_token_ids
                self.spark_model.generation_config.pad_token_id = self.pad_token_id
                self.spark_model.generation_config.use_cache = True
            except Exception:
                pass

        for hedef_mod in (self.spark_model, self.llm_submodule):
            if hedef_mod is not None and hasattr(hedef_mod, "prepare_inputs_for_generation"):
                orig_prep = hedef_mod.prepare_inputs_for_generation

                def _make_safe_prep(fn):
                    @functools.wraps(fn)
                    def _guvenli_prepare_inputs(input_ids, past_key_values=None, **kwargs):
                        bos_cache = (
                            past_key_values is not None
                            and hasattr(past_key_values, "get_seq_length")
                            and past_key_values.get_seq_length() == 0
                        )
                        if bos_cache:
                            res = fn(input_ids, past_key_values=None, **kwargs)
                            res["past_key_values"] = past_key_values
                            return res
                        return fn(input_ids, past_key_values=past_key_values, **kwargs)
                    return _guvenli_prepare_inputs

                hedef_mod.prepare_inputs_for_generation = _make_safe_prep(orig_prep)

        if hasattr(self.spark_model, "tokenize_audio"):
            orig_tokenize_audio = self.spark_model.tokenize_audio

            def _cached_tokenize_audio(wav_tensor, wav_ref, *args, **kwargs):
                key = self._active_ref_key
                if key is not None and key in self._audio_token_cache:
                    g_tok, s_tok = self._audio_token_cache[key]
                    return g_tok.to(self.device), s_tok.to(self.device)
                if hasattr(self.spark_model, "bicodec") and self.spark_model.bicodec is not None:
                    self.spark_model.bicodec.to(self.device)
                g_tok, s_tok = orig_tokenize_audio(wav_tensor, wav_ref, *args, **kwargs)
                if key is not None:
                    if len(self._audio_token_cache) >= 24:
                        ilk_anahtar = next(iter(self._audio_token_cache))
                        self._audio_token_cache.pop(ilk_anahtar, None)
                    self._audio_token_cache[key] = (g_tok.detach().cpu(), s_tok.detach().cpu())
                if self.dusuk_vram_modu and self.device == "cuda":
                    torch.cuda.empty_cache()
                return g_tok, s_tok

            self.spark_model.tokenize_audio = _cached_tokenize_audio

    def referans_hazirla_ve_kilitle(
        self,
        ref_wav_yolu: Optional[str | Path] = None,
        ozel_ref_metin: Optional[str] = None,
        referans_ses_kullan: bool = True,
    ) -> Tuple[str, str]:
        if not referans_ses_kullan or not ref_wav_yolu or "_varsayilan_sentetik_ref" in str(ref_wav_yolu):
            varsayilan_yol = BASE_DIR / ANA_REF_ERKEK
            temiz_ref_yol = referans_sesi_on_temizle(varsayilan_yol)
            return temiz_ref_yol, REF_METIN_1

        temiz_ref_yol = referans_sesi_on_temizle(ref_wav_yolu)
        yerlesik_mi = yerlesik_ref_ses_mi(ref_wav_yolu)

        if ozel_ref_metin is not None:
            ozel_referans_metni_kaydet(str(ref_wav_yolu), ozel_ref_metin)
            ozel_referans_metni_kaydet(temiz_ref_yol, ozel_ref_metin)

        ref_metin = referans_metni_getir(str(ref_wav_yolu), ozel_metin=ozel_ref_metin)
        ref_metin = _referans_prompt_metni_hazirla(ref_metin, yerlesik_mi=yerlesik_mi)

        if not yerlesik_mi and ref_metin:
            if ref_metin.strip() in (REF_METIN_1.strip(), REF_METIN_2.strip()):
                self._log("   ℹ️ Özel seste fabrika metni algılandı; saf ses klonlama moduna geçildi.")
                ref_metin = ""
            else:
                try:
                    bilgi_sf = sf.info(str(temiz_ref_yol))
                    ref_sure_sn = float(bilgi_sf.frames) / float(max(1, bilgi_sf.samplerate))
                    ref_kelime_sayisi = len(ref_metin.split())
                    if ref_sure_sn > 0.5:
                        kelime_sn_orani = ref_kelime_sayisi / ref_sure_sn
                        if kelime_sn_orani > 4.2 or kelime_sn_orani < 0.7:
                            self._log(
                                f"   ℹ️ Özel referans ses süresi ({ref_sure_sn:.1f} sn) ile referans metin ({ref_kelime_sayisi} kelime) uyumsuz; saf akustik klonlama kullanılıyor."
                            )
                            ref_metin = ""
                except Exception:
                    pass

        if self.motor_tipi == "XTTS_STUDIO":
            if self.xtts_model is None:
                self._xtts_motorunu_yukle()
            if self.xtts_model is not None and temiz_ref_yol not in self.latent_onbellek:
                try:
                    self.xtts_model.to(self.device)
                except Exception:
                    pass
                gpt_latent, spk_emb = self.xtts_model.get_conditioning_latents(
                    audio_path=[temiz_ref_yol],
                    gpt_cond_len=30,
                    gpt_cond_chunk_len=6,
                    max_ref_length=15,
                    sound_norm_refs=True,
                )
                if len(self.latent_onbellek) >= 16:
                    ilk = next(iter(self.latent_onbellek))
                    self.latent_onbellek.pop(ilk, None)
                self.latent_onbellek[temiz_ref_yol] = (
                    gpt_latent.detach().cpu(),
                    spk_emb.detach().cpu(),
                )
        return temiz_ref_yol, ref_metin

    def _direkt_tts_sentezle_np(
        self,
        akustik_metin: str,
        ref_wav_yolu: Optional[str | Path],
        hiz: float,
        tek_kelime_mi: bool,
        dsp_ayar: Optional[Dict[str, Any]],
        ilerleme_callback: Optional[Callable[[int, str], None]] = None,
        cancel_token: Optional[CancelToken] = None,
    ) -> np.ndarray:
        if self.iptal_edildi_mi(cancel_token):
            return np.array([], dtype=np.float32)

        self._edge_tts_kontrol_et()
        import edge_tts

        if ilerleme_callback:
            ilerleme_callback(30, "⚡ Hızlı Direkt Neural TTS (Çevrimiçi) sentezleniyor...")

        ref_str = str(ref_wav_yolu or "ref_erkek_1")
        ref_stem = Path(ref_str).stem.lower()
        temiz_stem = re.sub(r"_[0-9a-f]{12}$", "", ref_stem)

        if temiz_stem in DIREKT_TTS_SES_HARITASI:
            secilen_ayar = DIREKT_TTS_SES_HARITASI[temiz_stem]
        else:
            for k_anahtar, k_deger in DIREKT_TTS_SES_HARITASI.items():
                if temiz_stem.startswith(k_anahtar):
                    secilen_ayar = k_deger
                    break
            else:
                # Özel sesler için önce kayıtlı kategori/cinsiyet haritasına bak, yoksa dosya adına bak
                kat_bilgi = (
                    _OZEL_REF_KATEGORI_HARITASI.get(ref_str)
                    or _OZEL_REF_KATEGORI_HARITASI.get(os.path.basename(ref_str).lower())
                    or _OZEL_REF_KATEGORI_HARITASI.get(ref_stem)
                    or _OZEL_REF_KATEGORI_HARITASI.get(temiz_stem)
                )
                if kat_bilgi:
                    kat = kat_bilgi.get("kategori", "")
                    cins = kat_bilgi.get("cinsiyet", "E")
                    if kat == "cocuk_K":
                        secilen_ayar = DIREKT_TTS_SES_HARITASI["ref_kiz_cocuk_1"]
                    elif kat == "cocuk_E":
                        secilen_ayar = DIREKT_TTS_SES_HARITASI["ref_erkek_cocuk_1"]
                    elif cins == "K" or kat == "yetiskin_K":
                        secilen_ayar = DIREKT_TTS_SES_HARITASI["ref_kadin_1"]
                    else:
                        secilen_ayar = DIREKT_TTS_SES_HARITASI["ref_erkek_1"]
                elif "cocuk" in temiz_stem or "çocuk" in temiz_stem:
                    if any(k in temiz_stem for k in ("kiz", "kız", "kadin", "kadın", "female", "irem")):
                        secilen_ayar = DIREKT_TTS_SES_HARITASI["ref_kiz_cocuk_1"]
                    else:
                        secilen_ayar = DIREKT_TTS_SES_HARITASI["ref_erkek_cocuk_1"]
                elif any(k in temiz_stem for k in ("kiz", "kız", "kadin", "kadın", "female", "irem")):
                    secilen_ayar = DIREKT_TTS_SES_HARITASI["ref_kadin_1"]
                else:
                    secilen_ayar = DIREKT_TTS_SES_HARITASI["ref_erkek_1"]

        voice_name = secilen_ayar["voice"]
        pitch_str = secilen_ayar["pitch"]
        hiz_fark_yuzde = int(round((hiz - 1.0) * 100))
        rate_str = f"{hiz_fark_yuzde:+d}%"

        REF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        is_uuid = uuid.uuid4().hex[:10]
        gecici_mp3 = REF_CACHE_DIR / f"_direkt_tts_{is_uuid}.mp3"
        gecici_wav = REF_CACHE_DIR / f"_direkt_tts_{is_uuid}.wav"

        async def _indir():
            comm = edge_tts.Communicate(
                text=akustik_metin,
                voice=voice_name,
                rate=rate_str,
                pitch=pitch_str,
            )
            await comm.save(str(gecici_mp3))

        timeout_sn = max(30.0, min(120.0, len(akustik_metin) / 25.0))
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(asyncio.wait_for(_indir(), timeout=timeout_sn))
        except Exception as e:
            for p in (gecici_mp3, gecici_wav):
                try:
                    if p.exists():
                        p.unlink()
                except OSError:
                    pass
            if self.iptal_edildi_mi(cancel_token):
                return np.array([], dtype=np.float32)
            raise RuntimeError(
                "Hızlı Direkt TTS çevrimiçi servisine ulaşılamadı. Lütfen internet bağlantınızı kontrol edin "
                "veya çevrimdışı çalışan '⭐ Spark-TTS' motorunu seçin."
            ) from e
        finally:
            loop.close()

        if self.iptal_edildi_mi(cancel_token):
            for p in (gecici_mp3, gecici_wav):
                try:
                    if p.exists():
                        p.unlink()
                except OSError:
                    pass
            return np.array([], dtype=np.float32)

        if ilerleme_callback:
            ilerleme_callback(75, "🎚️ 24kHz 5-Katmanlı Stüdyo DSP uygulanıyor...")

        try:
            veri = _ses_dosyasini_guvenli_oku_np(str(gecici_mp3), hedef_sr=24000)
        finally:
            for p in (gecici_mp3, gecici_wav):
                try:
                    if p.exists():
                        p.unlink()
                except OSError:
                    pass

        return studyo_dsp_mastering(
            veri,
            sample_rate=24000,
            tek_kelime_mi=tek_kelime_mi,
            dsp_ayar=dsp_ayar,
        )

    def _spark_tek_deneme_calistir(
        self,
        akustik_metin: str,
        temiz_ref_yol: str,
        ref_metin: Optional[str],
        min_tok: int,
        max_tok: int,
        baz_temp: float,
        secilen_top_k: int,
        secilen_top_p: float,
        kelime_sayisi: int,
        ozel_ses_mi: bool,
        ilerleme_callback: Optional[Callable[[int, str], None]],
        cancel_token: Optional[CancelToken],
        repetition_penalty_degeri: Optional[float] = None,
    ) -> Tuple[np.ndarray, int, bool]:
        if hasattr(self.spark_model, "bicodec") and self.spark_model.bicodec is not None:
            self.spark_model.bicodec.to(self.device)

        if ref_metin and str(ref_metin).strip():
            try:
                inputs = self.processor(
                    text=akustik_metin,
                    prompt_speech_path=temiz_ref_yol,
                    prompt_text=ref_metin,
                    return_tensors="pt",
                ).to(self.device)
            except TypeError:
                inputs = self.processor(
                    text=akustik_metin,
                    prompt_speech_path=temiz_ref_yol,
                    return_tensors="pt",
                ).to(self.device)
        else:
            inputs = self.processor(
                text=akustik_metin,
                prompt_speech_path=temiz_ref_yol,
                return_tensors="pt",
            ).to(self.device)

        if self.dusuk_vram_modu and self.device == "cuda" and hasattr(self.spark_model, "bicodec"):
            try:
                self.spark_model.bicodec.to("cpu")
                torch.cuda.empty_cache()
            except Exception:
                pass

        global_tokens_prompt = inputs.pop("global_token_ids_prompt", None)
        input_ids_len = int(inputs["input_ids"].shape[-1])

        kriter_nesnesi = _StudyoDurdurmaVeIlerlemeKriteri(
            motor=self,
            baslangic_len=input_ids_len,
            hedef_tok=min(max_tok, max(60, kelime_sayisi * 32)),
            ilerleme_cb=ilerleme_callback,
            cancel_token=cancel_token,
            tekrar_kontrolu_aktif=True,
        )
        durdurma_kriteri = StoppingCriteriaList([kriter_nesnesi])

        gen_kwargs = dict(
            **inputs,
            min_new_tokens=min_tok,
            max_new_tokens=max_tok,
            eos_token_id=self.eos_token_ids,
            pad_token_id=self.pad_token_id,
            do_sample=True,
            temperature=baz_temp,
            top_k=secilen_top_k,
            top_p=secilen_top_p,
            stopping_criteria=durdurma_kriteri,
        )
        if repetition_penalty_degeri is not None and repetition_penalty_degeri > 1.0:
            gen_kwargs["repetition_penalty"] = float(repetition_penalty_degeri)

        try:
            output_ids = self.spark_model.generate(**gen_kwargs, use_cache=True)
        except torch.cuda.OutOfMemoryError:
            if self.device == "cuda":
                torch.cuda.empty_cache()
            gen_kwargs["max_new_tokens"] = max(120, int(max_tok * 0.7))
            output_ids = self.spark_model.generate(**gen_kwargs, use_cache=True)

        if self.iptal_edildi_mi(cancel_token):
            del inputs, output_ids
            return np.array([], dtype=np.float32), 24000, False

        if ilerleme_callback:
            ilerleme_callback(93, "🔊 BiCodec 24kHz ses dalgası çözülüyor...")

        if hasattr(self.spark_model, "bicodec") and self.spark_model.bicodec is not None:
            self.spark_model.bicodec.to(self.device)

        decoded = self.processor.decode(
            generated_ids=output_ids,
            global_token_ids_prompt=global_tokens_prompt,
            input_ids_len=input_ids_len,
        )

        aday_wav = decoded.get("audio")
        ham_np = np.array([], dtype=np.float32)
        sr = 24000
        if aday_wav is not None:
            if isinstance(aday_wav, torch.Tensor):
                aday_wav = aday_wav.detach().cpu().numpy()
            ham_np = np.asarray(aday_wav, dtype=np.float32).flatten()
            sr = int(decoded.get("sampling_rate", 24000))

        del inputs, output_ids, decoded

        bozuk_mu = kriter_nesnesi.tekrar_tespit_edildi
        if ozel_ses_mi and not bozuk_mu and ham_np.size > 0:
            bozuk_mu = _ses_cizirti_veya_bozuk_mu(ham_np, sample_rate=sr)

        return ham_np, sr, bozuk_mu

    def _tek_parca_sentezle_np(
        self,
        akustik_metin: str,
        temiz_ref_yol: str,
        ref_metin: str,
        hiz: float,
        temperature: float,
        tek_kelime_mi: bool,
        min_tokens_override: Optional[int],
        max_tokens_override: Optional[int],
        dsp_ayar: Optional[Dict[str, Any]],
        referans_ses_kullan: bool = True,
        ilerleme_callback: Optional[Callable[[int, str], None]] = None,
        cancel_token: Optional[CancelToken] = None,
        top_p_override: Optional[float] = None,
        top_k_override: Optional[int] = None,
    ) -> np.ndarray:
        if self.iptal_edildi_mi(cancel_token):
            return np.array([], dtype=np.float32)

        if self.motor_tipi == "FAST_DIRECT_TTS" or not referans_ses_kullan:
            return self._direkt_tts_sentezle_np(
                akustik_metin=akustik_metin,
                ref_wav_yolu=temiz_ref_yol,
                hiz=hiz,
                tek_kelime_mi=tek_kelime_mi,
                dsp_ayar=dsp_ayar,
                ilerleme_callback=ilerleme_callback,
                cancel_token=cancel_token,
            )

        if self.motor_tipi == "XTTS_STUDIO":
            yuklendi = self._xtts_motorunu_yukle()
            if not yuklendi:
                raise RuntimeError(self.son_hata_mesaji or "Coqui XTTS v2 modeli yüklenemedi.")
            if temiz_ref_yol not in self.latent_onbellek:
                self.referans_hazirla_ve_kilitle(temiz_ref_yol, ozel_ref_metin=ref_metin, referans_ses_kullan=True)

        if self.motor_tipi == "SPARK_ARABIC":
            if self.spark_model is None:
                if ilerleme_callback:
                    ilerleme_callback(8, "📥 Spark-TTS 24kHz modeli belleğe yükleniyor...")
                if not self._spark_motorunu_yukle():
                    raise RuntimeError(self.son_hata_mesaji or "Spark-TTS modeli belleğe yüklenemedi.")
            else:
                try:
                    self.spark_model.to(self.device)
                except Exception:
                    pass

        yerlesik_mi = yerlesik_ref_ses_mi(temiz_ref_yol)
        ozel_ses_mi = not yerlesik_mi

        kelime_sayisi = max(1, len(akustik_metin.split()))
        if tek_kelime_mi or kelime_sayisi == 1:
            min_tok = min_tokens_override if min_tokens_override is not None else 12
            max_tok = max_tokens_override if max_tokens_override is not None else 140
        else:
            makul_min = min(32, max(10, kelime_sayisi * 4))
            min_tok = min(min_tokens_override, makul_min) if min_tokens_override is not None else makul_min
            makul_max = min(self.max_token_ust_sinir, max(150, kelime_sayisi * 42))
            if ozel_ses_mi:
                max_tok = makul_max
            else:
                max_tok = min(max_tokens_override, makul_max) if max_tokens_override is not None else makul_max
        min_tok = min(min_tok, max(10, max_tok - 10))
        secilen_top_k = int(top_k_override) if top_k_override is not None else 50
        secilen_top_p = float(top_p_override) if top_p_override is not None else 0.95

        ham_np = np.array([], dtype=np.float32)
        sr = 24000

        with torch.inference_mode():
            if self.motor_tipi == "SPARK_ARABIC" and self.spark_model is not None:
                self._active_ref_key = str(temiz_ref_yol)
                baz_temp = max(0.50, min(0.76, float(temperature) if temperature >= 0.45 else 0.64))

                if ilerleme_callback:
                    ilerleme_callback(14, "🎛️ Referans ses kimliği ve tonlama aktarılıyor...")

                ham_np, sr, bozuk_mu = self._spark_tek_deneme_calistir(
                    akustik_metin=akustik_metin,
                    temiz_ref_yol=temiz_ref_yol,
                    ref_metin=ref_metin if ref_metin else None,
                    min_tok=min_tok,
                    max_tok=max_tok,
                    baz_temp=baz_temp,
                    secilen_top_k=secilen_top_k,
                    secilen_top_p=secilen_top_p,
                    kelime_sayisi=kelime_sayisi,
                    ozel_ses_mi=ozel_ses_mi,
                    ilerleme_callback=ilerleme_callback,
                    cancel_token=cancel_token,
                    repetition_penalty_degeri=None,
                )

                # 2. DENEME (Best-of-2 Korumalı): Özel seste cızırtı/osilasyon algılanırsa
                # Saf Akustik Klonlama + hafif repetition_penalty (1.06) ile 2. üretimi yap ve daha doğal olanı seç!
                if ozel_ses_mi and bozuk_mu and not self.iptal_edildi_mi(cancel_token):
                    self._log(
                        "   🛡️ Özel referans seste semantik hizalama cızırtısı algılandı; Saf Akustik Klonlama moduna geçiliyor..."
                    )
                    if ilerleme_callback:
                        ilerleme_callback(22, "🛡️ Özel ses için Saf Akustik Klonlama uygulanıyor...")

                    ham_np_2, sr_2, bozuk_mu_2 = self._spark_tek_deneme_calistir(
                        akustik_metin=akustik_metin,
                        temiz_ref_yol=temiz_ref_yol,
                        ref_metin=None,
                        min_tok=min_tok,
                        max_tok=max(110, int(max_tok * 0.88)),
                        baz_temp=max(0.54, min(0.65, baz_temp)),
                        secilen_top_k=min(38, secilen_top_k),
                        secilen_top_p=min(0.89, secilen_top_p),
                        kelime_sayisi=kelime_sayisi,
                        ozel_ses_mi=True,
                        ilerleme_callback=ilerleme_callback,
                        cancel_token=cancel_token,
                        repetition_penalty_degeri=1.06,
                    )

                    if ham_np_2.size > 0:
                        if not bozuk_mu_2:
                            ham_np, sr = ham_np_2, sr_2
                        else:
                            puan_1 = _ses_dogallik_puani_hesapla(ham_np, sample_rate=sr)
                            puan_2 = _ses_dogallik_puani_hesapla(ham_np_2, sample_rate=sr_2)
                            if puan_2 >= puan_1 or ham_np.size < 1200:
                                ham_np, sr = ham_np_2, sr_2

            elif self.xtts_model is not None:
                if ilerleme_callback:
                    ilerleme_callback(35, "🗣️ Coqui XTTS v2 ses dalgası sentezleniyor...")
                self._xtts_gpt_inference_yamasi_uygula()
                try:
                    self.xtts_model.to(self.device)
                except Exception:
                    pass
                gpt_latent_cpu, spk_emb_cpu = self.latent_onbellek[temiz_ref_yol]
                gpt_latent = gpt_latent_cpu.to(self.device)
                spk_emb = spk_emb_cpu.to(self.device)
                out = self.xtts_model.inference(
                    text=akustik_metin,
                    language="ar",
                    gpt_cond_latent=gpt_latent,
                    speaker_embedding=spk_emb,
                    temperature=max(0.25, min(0.65, float(temperature))),
                    speed=hiz,
                    repetition_penalty=3.5,
                    length_penalty=1.05,
                    top_k=secilen_top_k,
                    top_p=secilen_top_p,
                    enable_text_splitting=True,
                )
                ham_np = np.asarray(out["wav"], dtype=np.float32).flatten()
                sr = int(out.get("sample_rate", 24000)) if isinstance(out, dict) else 24000

            if self.dusuk_vram_modu and self.device == "cuda":
                torch.cuda.empty_cache()

        if self.iptal_edildi_mi(cancel_token) or ham_np.size < 1200:
            return np.array([], dtype=np.float32)

        if sr != 24000 and ham_np.size > 0:
            ham_np = _yuksek_kalite_resample(ham_np, sr, 24000)
            sr = 24000

        if ilerleme_callback:
            ilerleme_callback(97, "🎚️ Doğal Sönümlenmeli Stüdyo DSP Mastering uygulanıyor...")

        return studyo_dsp_mastering(
            ham_np,
            sample_rate=sr,
            tek_kelime_mi=tek_kelime_mi,
            dsp_ayar=dsp_ayar,
        )

    def uret_ve_kaydet(
        self,
        arapca_metin: str,
        ref_wav_yolu: Optional[str | Path] = None,
        cikti_yolu: str | Path = "cikti.wav",
        hiz: float = 0.92,
        temperature: float = 0.65,
        kelime_turu: str = "genel",
        tek_kelime_mi: bool = False,
        hikmetli_durak_ekle: bool = False,
        wav_formatini_zorla: bool = False,
        ozel_ref_metin: Optional[str] = None,
        onceden_hazirlanmis_akustik_metin: Optional[str] = None,
        min_tokens_override: Optional[int] = None,
        max_tokens_override: Optional[int] = None,
        dsp_ayar: Optional[Dict[str, Any]] = None,
        referans_ses_kullan: bool = True,
        ilerleme_callback: Optional[Callable[[int, str], None]] = None,
        cancel_token: Optional[CancelToken] = None,
        top_p_override: Optional[float] = None,
        top_k_override: Optional[int] = None,
    ) -> bool:
        with self._sentez_kilidi:
            try:
                if self.iptal_edildi_mi(cancel_token):
                    self.son_hata_mesaji = "İşlem kullanıcı tarafından durduruldu."
                    return False

                self.son_hata_mesaji = ""
                if ilerleme_callback:
                    ilerleme_callback(5, "⏳ Metin ve ses motoru hazırlanıyor...")

                if not referans_ses_kullan or self.motor_tipi == "FAST_DIRECT_TTS":
                    if onceden_hazirlanmis_akustik_metin and onceden_hazirlanmis_akustik_metin.strip():
                        akustik_metin = onceden_hazirlanmis_akustik_metin.strip()
                    else:
                        akustik_metin = arapca_akustik_metin_hazirla(
                            arapca_metin, kelime_turu=kelime_turu, hikmetli_durak_ekle=hikmetli_durak_ekle
                        )
                    islenmis_wav = self._direkt_tts_sentezle_np(
                        akustik_metin=akustik_metin,
                        ref_wav_yolu=ref_wav_yolu,
                        hiz=hiz,
                        tek_kelime_mi=tek_kelime_mi,
                        dsp_ayar=dsp_ayar,
                        ilerleme_callback=ilerleme_callback,
                        cancel_token=cancel_token,
                    )
                    if islenmis_wav.size < 1000:
                        self.son_hata_mesaji = "Hızlı Direkt TTS ses verisi üretemedi."
                        return False
                    sesi_diske_kaydet(
                        islenmis_wav,
                        cikti_yolu=cikti_yolu,
                        sample_rate=24000,
                        hiz=1.0,
                        wav_formatini_zorla=wav_formatini_zorla,
                    )
                    if ilerleme_callback:
                        ilerleme_callback(100, "✅ Hızlı Direkt TTS ile ses üretildi!")
                    return os.path.exists(str(cikti_yolu)) and os.path.getsize(str(cikti_yolu)) > 800

                temiz_ref_yol, ref_metin = self.referans_hazirla_ve_kilitle(
                    ref_wav_yolu=ref_wav_yolu,
                    ozel_ref_metin=ozel_ref_metin,
                    referans_ses_kullan=referans_ses_kullan,
                )

                if onceden_hazirlanmis_akustik_metin and onceden_hazirlanmis_akustik_metin.strip():
                    akustik_metin = hareke_siralamasini_normallestir(onceden_hazirlanmis_akustik_metin.strip())
                    akustik_metin = re.sub(r"[،؛,:;]+$", ".", akustik_metin)
                    if not re.search(r"[.؟!…]$", akustik_metin):
                        akustik_metin += "."
                else:
                    akustik_metin = arapca_akustik_metin_hazirla(
                        arapca_metin,
                        kelime_turu=kelime_turu,
                        hikmetli_durak_ekle=hikmetli_durak_ekle,
                    )

                kelimeler = akustik_metin.split()

                if not tek_kelime_mi and len(kelimeler) > self.bolme_esigi_kelime:
                    alt_cumleler = uzun_metni_cumlelere_bol(akustik_metin, maks_kelime=self.parca_maks_kelime)
                    if len(alt_cumleler) > 1:
                        self._log(
                            f"⚡ [{self.aktif_kademe_kodu}] Uzun paragraf {len(alt_cumleler)} doğal cümleye bölündü..."
                        )
                        parca_dizileri: List[np.ndarray] = []
                        nefes_boslugu = np.zeros(int(24000 * 0.05), dtype=np.float32)

                        for idx, alt_c in enumerate(alt_cumleler, start=1):
                            if self.iptal_edildi_mi(cancel_token):
                                self.son_hata_mesaji = "İşlem kullanıcı tarafından durduruldu."
                                self._log("⏹️ İşlem kullanıcı tarafından durduruldu.")
                                return False

                            son_parca_mi = (idx == len(alt_cumleler))
                            alt_akustik = arapca_akustik_metin_hazirla(
                                alt_c,
                                kelime_turu="genel",
                                hikmetli_durak_ekle=False,
                                ara_parca_mi=not son_parca_mi,
                            )
                            self._log(f"🎙️ Bölüm {idx}/{len(alt_cumleler)} sentezleniyor: {alt_akustik}")

                            def _parca_progress(p_yuzde: int, p_mesaj: str, b_idx=idx, b_top=len(alt_cumleler)):
                                if ilerleme_callback:
                                    genel_yuzde = int(((b_idx - 1 + (p_yuzde / 100.0)) / float(b_top)) * 95)
                                    ilerleme_callback(genel_yuzde, f"[Bölüm {b_idx}/{b_top}] {p_mesaj}")

                            # Bölünmüş alt cümlelerde min/max token override None verilir ki
                            # her parça kendi kelime uzunluğuna göre doğal token bütçesi alsın
                            parca_np = self._tek_parca_sentezle_np(
                                akustik_metin=alt_akustik,
                                temiz_ref_yol=temiz_ref_yol,
                                ref_metin=ref_metin,
                                hiz=hiz,
                                temperature=temperature,
                                tek_kelime_mi=False,
                                min_tokens_override=None,
                                max_tokens_override=None,
                                dsp_ayar=dsp_ayar,
                                referans_ses_kullan=referans_ses_kullan,
                                ilerleme_callback=_parca_progress,
                                cancel_token=cancel_token,
                                top_p_override=top_p_override,
                                top_k_override=top_k_override,
                            )
                            if parca_np.size < 1000:
                                self.son_hata_mesaji = f"{idx}. bölüm üretilemedi veya durduruldu."
                                return False
                            parca_dizileri.append(parca_np)
                            if not son_parca_mi:
                                parca_dizileri.append(nefes_boslugu)

                        birlesik_np = np.concatenate(parca_dizileri).astype(np.float32)
                        sesi_diske_kaydet(
                            birlesik_np,
                            cikti_yolu=cikti_yolu,
                            sample_rate=24000,
                            hiz=hiz if self.motor_tipi == "SPARK_ARABIC" else 1.0,
                            wav_formatini_zorla=wav_formatini_zorla,
                        )
                        if ilerleme_callback:
                            ilerleme_callback(100, "✅ Ses üretimi tamamlandı!")
                        return os.path.exists(str(cikti_yolu)) and os.path.getsize(str(cikti_yolu)) > 1000

                islenmis_wav = self._tek_parca_sentezle_np(
                    akustik_metin=akustik_metin,
                    temiz_ref_yol=temiz_ref_yol,
                    ref_metin=ref_metin,
                    hiz=hiz,
                    temperature=temperature,
                    tek_kelime_mi=tek_kelime_mi,
                    min_tokens_override=min_tokens_override,
                    max_tokens_override=max_tokens_override,
                    dsp_ayar=dsp_ayar,
                    referans_ses_kullan=referans_ses_kullan,
                    ilerleme_callback=ilerleme_callback,
                    cancel_token=cancel_token,
                    top_p_override=top_p_override,
                    top_k_override=top_k_override,
                )

                if self.iptal_edildi_mi(cancel_token):
                    self.son_hata_mesaji = "İşlem kullanıcı tarafından durduruldu."
                    self._log("⏹️ İşlem kullanıcı tarafından durduruldu.")
                    return False

                if islenmis_wav.size < 1200:
                    self.son_hata_mesaji = "Model yeterli uzunlukta ses verisi üretemedi."
                    self._log(f"   ⚠️ Yetersiz ses verisi ({cikti_yolu}), atlandı.")
                    return False

                sesi_diske_kaydet(
                    islenmis_wav,
                    cikti_yolu=cikti_yolu,
                    sample_rate=24000,
                    hiz=hiz if self.motor_tipi == "SPARK_ARABIC" else 1.0,
                    wav_formatini_zorla=wav_formatini_zorla,
                )

                if ilerleme_callback:
                    ilerleme_callback(100, "✅ Ses üretimi tamamlandı!")

                return os.path.exists(str(cikti_yolu)) and os.path.getsize(str(cikti_yolu)) > 1000

            except Exception as e:
                self.son_hata_mesaji = str(e)
                self._log(f"   ⚠️ Stüdyo ses üretim hatası ({cikti_yolu}): {e}")
                return False