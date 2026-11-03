#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MUALLİMUN AI SES STÜDYOSU PRO - MERKEZİ YAPILANDIRMA, PRESET VE SES HAVUZU YÖNETİCİSİ
Özellikler:
  1. Spark-TTS ('SPARK_ARABIC') Ana Stüdyo Motoru Varsayılan Garantisi
  2. Atomik JSON Kaydı (.tmp -> fsync -> os.replace) ve Otomatik Yedek (.bak) Kurtarma
  3. Özel Referans Seslerde Benzersiz Kimlik (Çakışmasız UUID) ve Gerçek 24kHz PCM_16 WAV Dönüşümü
  4. Aydınlık/Karanlık Tema, İlk Açılış Rehber Turu ve GitHub Sürüm Kontrolü Ayarları
"""

import os
import json
import uuid
import shutil
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

import numpy as np
import soundfile as sf
from scipy import signal

from core.studyo_motoru import (
    REF_METIN_1,
    REF_METIN_2,
    ozel_referans_metni_kaydet,
)

CORE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CORE_DIR.parent if CORE_DIR.name == "core" else CORE_DIR
SCHEMA_VERSION = 2

# ==============================================================================
# 1. DEĞİŞTİRİLEMEZ FABRİKA PRESETLERİ (5 EĞİTİM MODU)
# ==============================================================================
FABRIKA_PRESETLERI: Dict[str, Dict[str, Any]] = {
    "tek_kelime": {
        "kod": "tek_kelime",
        "baslik": "1. Tek Kelime (Sözlük & Görsel Kelime)",
        "aciklama": "Sözlük maddeleri ve görsel kartlar için net, vakıflı ve kısa soluklu stüdyo okuması.",
        "hiz": 0.90,
        "temperature": 0.58,
        "top_k": 40,
        "top_p": 0.90,
        "min_tokens": 15,
        "max_tokens": 140,
        "kelime_turu": "isim",
        "tek_kelime_mi": True,
        "hikmetli_durak_ekle": False,
        "cift_uretim_erkek_kadin": True,
        "dinamik_tonlama": False,
        "varsayilan_format": "wav",
        "birlesik_bosluk_ms": 300,
        "dsp": {
            "hp_freq": 85.0,
            "lp_freq": 11200.0,
            "gate_esigi": 0.032,
            "aktif_esik_katsayi": 0.025,
            "bas_pay_ms": 40.0,
            "son_pay_ms": 140.0,
            "drive": 1.12,
            "fade_ms": 8.0,
            "tepe_normalizasyon": 0.891,
        },
    },
    "cumle": {
        "kod": "cumle",
        "baslik": "2. Cümle (Eğitim & Gramer Cümleleri)",
        "aciklama": "Ders kitabı etkinlikleri ve gramer örnekleri için dengeli, anlaşılır muallim tonu.",
        "hiz": 0.92,
        "temperature": 0.64,
        "top_k": 50,
        "top_p": 0.94,
        "min_tokens": 25,
        "max_tokens": 550,
        "kelime_turu": "genel",
        "tek_kelime_mi": False,
        "hikmetli_durak_ekle": False,
        "cift_uretim_erkek_kadin": True,
        "dinamik_tonlama": True,
        "varsayilan_format": "mp3",
        "birlesik_bosluk_ms": 350,
        "dsp": {
            "hp_freq": 85.0,
            "lp_freq": 11200.0,
            "gate_esigi": 0.028,
            "aktif_esik_katsayi": 0.024,
            "bas_pay_ms": 55.0,
            "son_pay_ms": 170.0,
            "drive": 1.12,
            "fade_ms": 10.0,
            "tepe_normalizasyon": 0.891,
        },
    },
    "atasozu": {
        "kod": "atasozu",
        "baslik": "3. Atasözü / Hikmetli Söz",
        "aciklama": "Vecizeler, hikmetli sözler ve beyitler için ağırbaşlı, tefekkür duraklı okuma.",
        "hiz": 0.89,
        "temperature": 0.62,
        "top_k": 45,
        "top_p": 0.92,
        "min_tokens": 30,
        "max_tokens": 600,
        "kelime_turu": "genel",
        "tek_kelime_mi": False,
        "hikmetli_durak_ekle": True,
        "cift_uretim_erkek_kadin": True,
        "dinamik_tonlama": True,
        "varsayilan_format": "wav",
        "birlesik_bosluk_ms": 420,
        "dsp": {
            "hp_freq": 80.0,
            "lp_freq": 11200.0,
            "gate_esigi": 0.026,
            "aktif_esik_katsayi": 0.024,
            "bas_pay_ms": 60.0,
            "son_pay_ms": 190.0,
            "drive": 1.14,
            "fade_ms": 12.0,
            "tepe_normalizasyon": 0.891,
        },
    },
    "diyalog": {
        "kod": "diyalog",
        "baslik": "4. Diyalog (Çoklu Karakter Konuşması)",
        "aciklama": "Karşılıklı konuşma metinleri için soru ve ünlem vurgularına duyarlı canlı diyalog modu.",
        "hiz": 0.94,
        "temperature": 0.66,
        "top_k": 50,
        "top_p": 0.95,
        "min_tokens": 25,
        "max_tokens": 650,
        "kelime_turu": "genel",
        "tek_kelime_mi": False,
        "hikmetli_durak_ekle": False,
        "cift_uretim_erkek_kadin": False,
        "dinamik_tonlama": True,
        "varsayilan_format": "mp3",
        "birlesik_bosluk_ms": 450,
        "dsp": {
            "hp_freq": 85.0,
            "lp_freq": 11200.0,
            "gate_esigi": 0.028,
            "aktif_esik_katsayi": 0.024,
            "bas_pay_ms": 50.0,
            "son_pay_ms": 160.0,
            "drive": 1.12,
            "fade_ms": 10.0,
            "tepe_normalizasyon": 0.891,
        },
    },
    "uzun_metin": {
        "kod": "uzun_metin",
        "baslik": "5. Uzun Metin / Okuma Parçası",
        "aciklama": "Paragrafları doğal nefes aralıklarıyla cümlelere bölüp tek parça olarak birleştiren öyküleme modu.",
        "hiz": 0.92,
        "temperature": 0.62,
        "top_k": 45,
        "top_p": 0.92,
        "min_tokens": 30,
        "max_tokens": 750,
        "kelime_turu": "genel",
        "tek_kelime_mi": False,
        "hikmetli_durak_ekle": False,
        "cift_uretim_erkek_kadin": False,
        "dinamik_tonlama": True,
        "varsayilan_format": "mp3",
        "birlesik_bosluk_ms": 350,
        "dsp": {
            "hp_freq": 85.0,
            "lp_freq": 11200.0,
            "gate_esigi": 0.028,
            "aktif_esik_katsayi": 0.024,
            "bas_pay_ms": 55.0,
            "son_pay_ms": 175.0,
            "drive": 1.12,
            "fade_ms": 10.0,
            "tepe_normalizasyon": 0.891,
        },
    },
}

# ==============================================================================
# 2. VARSAYILAN 8 STÜDYO REFERANS SES HAVUZU
# ==============================================================================
VARSAYILAN_SES_HAVUZU: List[Dict[str, Any]] = [
    {
        "id": "ref_erkek_1",
        "ad": "Yetişkin Erkek 1 (Ana Muallim)",
        "dosya_adi": "ref_erkek_1.wav",
        "cinsiyet": "E",
        "kategori": "yetiskin_E",
        "ref_metin": REF_METIN_1,
        "ozel_mi": False,
    },
    {
        "id": "ref_erkek_2",
        "ad": "Yetişkin Erkek 2 (Anlatıcı / Diyalog)",
        "dosya_adi": "ref_erkek_2.wav",
        "cinsiyet": "E",
        "kategori": "yetiskin_E",
        "ref_metin": REF_METIN_2,
        "ozel_mi": False,
    },
    {
        "id": "ref_kadin_1",
        "ad": "Yetişkin Kadın 1 (Ana Muallime)",
        "dosya_adi": "ref_kadin_1.wav",
        "cinsiyet": "K",
        "kategori": "yetiskin_K",
        "ref_metin": REF_METIN_1,
        "ozel_mi": False,
    },
    {
        "id": "ref_kadin_2",
        "ad": "Yetişkin Kadın 2 (Anlatıcı / Diyalog)",
        "dosya_adi": "ref_kadin_2.wav",
        "cinsiyet": "K",
        "kategori": "yetiskin_K",
        "ref_metin": REF_METIN_2,
        "ozel_mi": False,
    },
    {
        "id": "ref_erkek_cocuk_1",
        "ad": "Erkek Çocuk / Genç 1",
        "dosya_adi": "ref_erkek_cocuk_1.wav",
        "cinsiyet": "E",
        "kategori": "cocuk_E",
        "ref_metin": REF_METIN_1,
        "ozel_mi": False,
    },
    {
        "id": "ref_erkek_cocuk_2",
        "ad": "Erkek Çocuk / Genç 2",
        "dosya_adi": "ref_erkek_cocuk_2.wav",
        "cinsiyet": "E",
        "kategori": "cocuk_E",
        "ref_metin": REF_METIN_2,
        "ozel_mi": False,
    },
    {
        "id": "ref_kiz_cocuk_1",
        "ad": "Kız Çocuk / Genç 1",
        "dosya_adi": "ref_kiz_cocuk_1.wav",
        "cinsiyet": "K",
        "kategori": "cocuk_K",
        "ref_metin": REF_METIN_1,
        "ozel_mi": False,
    },
    {
        "id": "ref_kiz_cocuk_2",
        "ad": "Kız Çocuk / Genç 2",
        "dosya_adi": "ref_kiz_cocuk_2.wav",
        "cinsiyet": "K",
        "kategori": "cocuk_K",
        "ref_metin": REF_METIN_2,
        "ozel_mi": False,
    },
]

GECERLI_MOTOR_KODLARI = {"SPARK_ARABIC", "FAST_DIRECT_TTS", "XTTS_STUDIO"}


def _atomik_json_yaz(hedef_yol: Path, veri: Any) -> None:
    """
    JSON dosyasını önce geçici dosyaya yazar, diske flush/fsync eder,
    mevcut dosyanın '.bak' yedeğini alır ve atomik olarak hedef dosyayla değiştirir.
    """
    hedef_yol.parent.mkdir(parents=True, exist_ok=True)
    gecici_yol = hedef_yol.with_suffix(hedef_yol.suffix + f".{os.getpid()}.tmp")
    yedek_yol = hedef_yol.with_suffix(hedef_yol.suffix + ".bak")

    icerik = json.dumps(veri, ensure_ascii=False, indent=2)
    with open(gecici_yol, "w", encoding="utf-8") as f:
        f.write(icerik)
        f.flush()
        os.fsync(f.fileno())

    if hedef_yol.exists() and hedef_yol.stat().st_size > 10:
        try:
            shutil.copy2(str(hedef_yol), str(yedek_yol))
        except Exception:
            pass

    os.replace(str(gecici_yol), str(hedef_yol))


def _guvenli_json_oku(hedef_yol: Path, varsayilan_veri: Any) -> Any:
    """
    JSON dosyasını okur. Bozuksa '.bak' yedeğinden kurtarmayı dener;
    bozuk dosyayı silmek yerine '.corrupt' olarak saklar.
    """
    yedek_yol = hedef_yol.with_suffix(hedef_yol.suffix + ".bak")
    if hedef_yol.exists():
        try:
            with open(hedef_yol, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Yapılandırma dosyası bozuk ({hedef_yol.name}): {e}")
            try:
                bozuk_kopya = hedef_yol.with_suffix(hedef_yol.suffix + ".corrupt")
                shutil.copy2(str(hedef_yol), str(bozuk_kopya))
            except Exception:
                pass
            if yedek_yol.exists():
                try:
                    with open(yedek_yol, "r", encoding="utf-8-sig") as fb:
                        kurtarilan = json.load(fb)
                    print(f"✅ Yedek dosyadan ({yedek_yol.name}) başarıyla kurtarıldı!")
                    _atomik_json_yaz(hedef_yol, kurtarilan)
                    return kurtarilan
                except Exception:
                    pass
    return json.loads(json.dumps(varsayilan_veri))


class ConfigManager:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir).resolve() if base_dir else PROJECT_ROOT
        self.config_dir = self.base_dir / "config"
        self.custom_voices_dir = self.base_dir / "referans_sesler_ozel"

        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.custom_voices_dir.mkdir(parents=True, exist_ok=True)

        self.factory_presets_path = self.config_dir / "factory_presets.json"
        self.user_settings_path = self.config_dir / "user_settings.json"
        self.voice_pool_path = self.config_dir / "voice_pool.json"

        self.factory_presets: Dict[str, Dict[str, Any]] = json.loads(json.dumps(FABRIKA_PRESETLERI))
        self.user_settings: Dict[str, Any] = {}
        self.voice_pool: List[Dict[str, Any]] = []

        self._yukle_veya_olustur()

    def _varsayilan_kullanici_ayarlari(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "aktif_motor_tercihi": "SPARK_ARABIC",
            "acilis_varsayilan_spark_koru": True,
            "zorunlu_donanim_kademesi": "OTOMATIK",
            "uzman_mod_aktif": False,
            "tema_modu": "koyu",
            "auto_qa_aktif": True,
            "otomatik_oynat_toplu_bitis": False,
            "ilk_acilis_turu_gosterildi": False,
            "otomatik_guncelleme_kontrolu": True,
            "github_repo": "muallimun/Muallimun_Ses_Asistani",
            "aktif_preset": "cumle",
            "aktif_erkek_ref": "ref_erkek_1",
            "aktif_kadin_ref": "ref_kadin_1",
            "varsayilan_cikti_klasoru": "cikti_sesler",
            "kullanici_presetleri": {},
        }

    def _yukle_veya_olustur(self) -> None:
        # 1. Fabrika presetlerini yalnızca dosya yoksa oluştur (Salt-okunur kurulum dostu)
        if not self.factory_presets_path.exists():
            try:
                _atomik_json_yaz(self.factory_presets_path, FABRIKA_PRESETLERI)
            except Exception:
                pass

        # 2. Kullanıcı ayarlarını yükle ve şema göçünü (migration) uygula
        varsayilan = self._varsayilan_kullanici_ayarlari()
        okunan = _guvenli_json_oku(self.user_settings_path, varsayilan)
        if not isinstance(okunan, dict):
            okunan = dict(varsayilan)

        # Eksik anahtarları tamamla
        for k, v in varsayilan.items():
            if k not in okunan:
                okunan[k] = v

        # Eski GEMINI_API anahtarlarını temizle ve Spark-TTS varsayılanını koru
        okunan.pop("gemini_api_key", None)
        if okunan.get("aktif_motor_tercihi") not in GECERLI_MOTOR_KODLARI:
            okunan["aktif_motor_tercihi"] = "SPARK_ARABIC"
        if okunan.get("acilis_varsayilan_spark_koru", True):
            okunan["aktif_motor_tercihi"] = "SPARK_ARABIC"

        # Başka bilgisayardan kalan geçersiz mutlak çıktı yolunu taşınabilir göreli yola çevir
        kayitli_cikti = str(okunan.get("varsayilan_cikti_klasoru", "cikti_sesler")).strip()
        if kayitli_cikti:
            aday_yol = Path(kayitli_cikti)
            if aday_yol.is_absolute() and not aday_yol.exists():
                okunan["varsayilan_cikti_klasoru"] = "cikti_sesler"
            elif "Muallimun.Net" in kayitli_cikti and not Path(kayitli_cikti).exists():
                okunan["varsayilan_cikti_klasoru"] = "cikti_sesler"

        okunan["schema_version"] = SCHEMA_VERSION
        self.user_settings = okunan
        self.save_user_settings()

        # 3. Ses havuzunu yükle ve 8 fabrika sesinin varlığını garanti et
        okunan_havuz = _guvenli_json_oku(self.voice_pool_path, VARSAYILAN_SES_HAVUZU)
        if not isinstance(okunan_havuz, list) or not okunan_havuz:
            okunan_havuz = json.loads(json.dumps(VARSAYILAN_SES_HAVUZU))

        mevcut_idler = {str(s.get("id")) for s in okunan_havuz if isinstance(s, dict)}
        for vs in VARSAYILAN_SES_HAVUZU:
            if vs["id"] not in mevcut_idler:
                okunan_havuz.insert(0, dict(vs))

        self.voice_pool = okunan_havuz
        for ses in self.voice_pool:
            if ses.get("ref_metin"):
                ozel_referans_metni_kaydet(ses.get("dosya_adi", ses["id"]), ses["ref_metin"])
        self.save_voice_pool()

    def get_default_output_dir(self) -> Path:
        """Taşınabilir ve güvenli varsayılan çıktı kök klasörünü döndürür."""
        ayar_str = str(self.user_settings.get("varsayilan_cikti_klasoru", "cikti_sesler")).strip()
        if not ayar_str or ayar_str == "cikti_sesler":
            hedef = self.base_dir / "cikti_sesler"
        else:
            aday = Path(ayar_str)
            hedef = aday if aday.is_absolute() else (self.base_dir / aday)
        try:
            hedef.mkdir(parents=True, exist_ok=True)
            return hedef.resolve()
        except Exception:
            yedek = self.base_dir / "cikti_sesler"
            yedek.mkdir(parents=True, exist_ok=True)
            return yedek.resolve()

    def get_preset(self, mod_kodu: str) -> Dict[str, Any]:
        kod = mod_kodu if mod_kodu in self.factory_presets else "cumle"
        fabrika = json.loads(json.dumps(self.factory_presets[kod]))
        kullanici_ozel = self.user_settings.get("kullanici_presetleri", {}).get(kod, {})
        if isinstance(kullanici_ozel, dict):
            for k, v in kullanici_ozel.items():
                if k == "dsp" and isinstance(v, dict):
                    fabrika.setdefault("dsp", {}).update(v)
                else:
                    fabrika[k] = v
        return fabrika

    def save_user_preset(self, mod_kodu: str, yeni_ayarlar: Dict[str, Any]) -> None:
        if "kullanici_presetleri" not in self.user_settings or not isinstance(
            self.user_settings["kullanici_presetleri"], dict
        ):
            self.user_settings["kullanici_presetleri"] = {}
        self.user_settings["kullanici_presetleri"][mod_kodu] = yeni_ayarlar
        self.save_user_settings()

    def reset_preset_to_factory(self, mod_kodu: str) -> Dict[str, Any]:
        kullanici_presetleri = self.user_settings.get("kullanici_presetleri", {})
        if isinstance(kullanici_presetleri, dict) and mod_kodu in kullanici_presetleri:
            del kullanici_presetleri[mod_kodu]
            self.save_user_settings()
        return self.get_preset(mod_kodu)

    def reset_all_to_factory(self) -> None:
        self.user_settings["kullanici_presetleri"] = {}
        self.user_settings["aktif_motor_tercihi"] = "SPARK_ARABIC"
        self.user_settings["zorunlu_donanim_kademesi"] = "OTOMATIK"
        self.save_user_settings()

    def save_user_settings(self) -> None:
        try:
            _atomik_json_yaz(self.user_settings_path, self.user_settings)
        except Exception as e:
            print(f"⚠️ Kullanıcı ayarları kaydedilemedi: {e}")

    def save_voice_pool(self) -> None:
        try:
            _atomik_json_yaz(self.voice_pool_path, self.voice_pool)
        except Exception as e:
            print(f"⚠️ Ses havuzu kaydedilemedi: {e}")

    def get_voice_by_id(self, voice_id: str) -> Optional[Dict[str, Any]]:
        hedef = str(voice_id or "").strip()
        for ses in self.voice_pool:
            if ses.get("id") == hedef or ses.get("dosya_adi") == hedef:
                return ses
        return None

    def resolve_voice_path(self, voice_id_or_filename: str) -> Path:
        """
        Referans sesin fiziksel yolunu yalnızca proje içi güvenli dizinlerde arar.
        """
        aranan = str(voice_id_or_filename or "ref_erkek_1").strip()
        ses_kaydi = self.get_voice_by_id(aranan)
        dosya_adi = ses_kaydi.get("dosya_adi", aranan) if ses_kaydi else aranan
        if not dosya_adi.lower().endswith(".wav"):
            dosya_adi_wav = f"{dosya_adi}.wav"
        else:
            dosya_adi_wav = dosya_adi

        adaylar = [
            self.base_dir / dosya_adi,
            self.base_dir / dosya_adi_wav,
            self.custom_voices_dir / dosya_adi,
            self.custom_voices_dir / dosya_adi_wav,
            self.base_dir / "referans_sesler" / dosya_adi_wav,
        ]
        if Path(aranan).is_absolute() and Path(aranan).exists():
            return Path(aranan).resolve()

        for aday in adaylar:
            if aday.exists() and aday.is_file():
                return aday.resolve()

        return (self.base_dir / dosya_adi_wav).resolve()

    def get_voice_prompt_text(self, voice_id_or_filename: str) -> str:
        ses = self.get_voice_by_id(voice_id_or_filename)
        if ses and ses.get("ref_metin"):
            return str(ses["ref_metin"]).strip()
        ad = str(voice_id_or_filename).lower()
        return REF_METIN_2 if "_2" in ad else REF_METIN_1

    def update_voice_prompt_text(self, voice_id: str, yeni_metin: str) -> bool:
        temiz = str(yeni_metin or "").strip()
        if not temiz:
            return False
        for ses in self.voice_pool:
            if ses.get("id") == voice_id:
                ses["ref_metin"] = temiz
                ozel_referans_metni_kaydet(ses.get("dosya_adi", voice_id), temiz)
                ozel_referans_metni_kaydet(str(self.resolve_voice_path(voice_id)), temiz)
                self.save_voice_pool()
                return True
        return False

    def add_custom_voice(
        self,
        kaynak_dosya_yolu: str,
        gorunen_ad: str,
        cinsiyet: str = "E",
        kategori: str = "yetiskin_E",
        ref_metin: str = "",
    ) -> Dict[str, Any]:
        """
        Kullanıcının seçtiği referans sesi doğrular, gerçek 24kHz Mono PCM_16 WAV
        formatına dönüştürür ve çakışmasız benzersiz ID ile ses havuzuna ekler.
        """
        kaynak = Path(kaynak_dosya_yolu).resolve()
        if not kaynak.exists():
            raise FileNotFoundError(f"Seçilen ses dosyası bulunamadı: {kaynak}")

        # Benzersiz kimlik (Sil-ekle sonrasında asla eski dosya üzerine yazmaz)
        kisa_uuid = uuid.uuid4().hex[:8]
        temiz_stem = "".join(c if c.isalnum() else "_" for c in kaynak.stem.lower())[:20].strip("_") or "ses"
        yeni_id = f"ozel_{temiz_stem}_{kisa_uuid}"
        hedef_dosya_adi = f"{yeni_id}.wav"
        hedef_yol = self.custom_voices_dir / hedef_dosya_adi

        # Kaynak sesi gerçekten decode edip 24kHz Mono PCM_16 WAV olarak kaydet
        try:
            veri, sr = sf.read(str(kaynak), dtype="float32")
        except Exception:
            if not shutil.which("ffmpeg"):
                raise RuntimeError(
                    f"'{kaynak.name}' dosyasını WAV formatına dönüştürmek için FFmpeg gereklidir."
                )
            gecici_wav = self.custom_voices_dir / f"_tmp_{kisa_uuid}.wav"
            res = subprocess.run(
                ["ffmpeg", "-y", "-i", str(kaynak), "-ar", "24000", "-ac", "1", "-sample_fmt", "s16", str(gecici_wav)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            if res.returncode != 0 or not gecici_wav.exists():
                raise RuntimeError(f"Ses dosyası dönüştürülemedi: {res.stderr[-200:] if res.stderr else ''}")
            veri, sr = sf.read(str(gecici_wav), dtype="float32")
            try:
                gecici_wav.unlink()
            except OSError:
                pass

        if veri.ndim > 1:
            veri = np.mean(veri, axis=-1)
        veri = veri.flatten()

        sure_sn = float(veri.size) / float(max(1, sr))
        if sure_sn < 1.5:
            raise ValueError("Referans ses kaydı çok kısa (En az 2-3 saniye net konuşma içermelidir).")

        hedef_sr = 24000
        if sr != hedef_sr:
            veri = signal.resample_poly(veri, hedef_sr, sr).astype(np.float32)

        sf.write(str(hedef_yol), veri, hedef_sr, subtype="PCM_16")

        cins = "K" if str(cinsiyet).upper().startswith("K") else "E"
        kat = kategori if kategori in ("yetiskin_E", "yetiskin_K", "cocuk_E", "cocuk_K") else f"yetiskin_{cins}"
        secilen_metin = str(ref_metin or "").strip() or REF_METIN_1

        yeni_kayit = {
            "id": yeni_id,
            "ad": str(gorunen_ad or kaynak.stem).strip(),
            "dosya_adi": hedef_dosya_adi,
            "cinsiyet": cins,
            "kategori": kat,
            "ref_metin": secilen_metin,
            "ozel_mi": True,
        }
        self.voice_pool.append(yeni_kayit)
        ozel_referans_metni_kaydet(hedef_dosya_adi, secilen_metin)
        ozel_referans_metni_kaydet(str(hedef_yol), secilen_metin)
        self.save_voice_pool()
        return yeni_kayit

    def remove_custom_voice(self, voice_id: str) -> bool:
        for idx, ses in enumerate(self.voice_pool):
            if ses.get("id") == voice_id:
                if not ses.get("ozel_mi", False):
                    return False
                dosya_adi = ses.get("dosya_adi", "")
                aday_yol = self.custom_voices_dir / dosya_adi
                if aday_yol.exists():
                    try:
                        aday_yol.unlink()
                    except OSError:
                        pass
                self.voice_pool.pop(idx)
                self.save_voice_pool()
                return True
        return False