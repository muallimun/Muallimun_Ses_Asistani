#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MUALLİMUN AI SES STÜDYOSU PRO - MERKEZİ YAPILANDIRMA VE FABRİKA AYARLARI YÖNETİCİSİ
Dosya: core/config_manager.py
Özellikler:
  1. 8 Yerleşik Stüdyo Referans Sesi ile Kullanıcı Özel Referans Seslerinin İzole Yönetimi
  2. Özel Referans Seslerde Boş Metin Girildiğinde Yanlışlıkla REF_METIN_1 Atanmasını Engelleyen Koruma
  3. Özel Referans Sesleri 24kHz İç Boşluk Sıkıştırmalı (Silence-Compacted) WAV Formatında Kaydetme
  4. 5 İçerik Modu (Preset) ve 18+ DSP Mastering Parametresinin Atomik ve Kalıcı Yönetimi
"""

import os
import sys
import json
import uuid
import shutil
import copy
from pathlib import Path
from typing import Dict, Any, List, Optional

if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

from core.studyo_motoru import (
    REF_METIN_1,
    REF_METIN_2,
    ozel_referans_metni_kaydet,
    ozel_referans_kategori_kaydet,
    hareke_siralamasini_normallestir,
)


class ConfigManager:
    """
    Stüdyo fabrika ayarlarını, kullanıcı ince ayarlarını (DSP, Hız, Temperature, Token sınırları)
    ve 8+N Referans Ses Havuzunu yöneten merkezi yapılandırma sınıfı.
    """

    YERLESIK_8_SES_IDLERI = {
        "ref_erkek_1",
        "ref_erkek_2",
        "ref_kadin_1",
        "ref_kadin_2",
        "ref_erkek_cocuk_1",
        "ref_erkek_cocuk_2",
        "ref_kiz_cocuk_1",
        "ref_kiz_cocuk_2",
    }

    FACTORY_VOICE_POOL: List[Dict[str, Any]] = [
        {
            "id": "ref_erkek_1",
            "ad": "Yetişkin Erkek 1 (Ana Muallim)",
            "dosya": "ref_erkek_1.wav",
            "cinsiyet": "E",
            "kategori": "yetiskin_E",
            "ref_metin": REF_METIN_1,
            "yerlesik": True,
        },
        {
            "id": "ref_erkek_2",
            "ad": "Yetişkin Erkek 2 (Anlatıcı / Diyalog)",
            "dosya": "ref_erkek_2.wav",
            "cinsiyet": "E",
            "kategori": "yetiskin_E",
            "ref_metin": REF_METIN_2,
            "yerlesik": True,
        },
        {
            "id": "ref_kadin_1",
            "ad": "Yetişkin Kadın 1 (Ana Muallime)",
            "dosya": "ref_kadin_1.wav",
            "cinsiyet": "K",
            "kategori": "yetiskin_K",
            "ref_metin": REF_METIN_1,
            "yerlesik": True,
        },
        {
            "id": "ref_kadin_2",
            "ad": "Yetişkin Kadın 2 (Anlatıcı / Diyalog)",
            "dosya": "ref_kadin_2.wav",
            "cinsiyet": "K",
            "kategori": "yetiskin_K",
            "ref_metin": REF_METIN_2,
            "yerlesik": True,
        },
        {
            "id": "ref_erkek_cocuk_1",
            "ad": "Erkek Çocuk / Genç 1",
            "dosya": "ref_erkek_cocuk_1.wav",
            "cinsiyet": "E",
            "kategori": "cocuk_E",
            "ref_metin": REF_METIN_1,
            "yerlesik": True,
        },
        {
            "id": "ref_erkek_cocuk_2",
            "ad": "Erkek Çocuk / Genç 2",
            "dosya": "ref_erkek_cocuk_2.wav",
            "cinsiyet": "E",
            "kategori": "cocuk_E",
            "ref_metin": REF_METIN_2,
            "yerlesik": True,
        },
        {
            "id": "ref_kiz_cocuk_1",
            "ad": "Kız Çocuk / Genç 1",
            "dosya": "ref_kiz_cocuk_1.wav",
            "cinsiyet": "K",
            "kategori": "cocuk_K",
            "ref_metin": REF_METIN_1,
            "yerlesik": True,
        },
        {
            "id": "ref_kiz_cocuk_2",
            "ad": "Kız Çocuk / Genç 2",
            "dosya": "ref_kiz_cocuk_2.wav",
            "cinsiyet": "K",
            "kategori": "cocuk_K",
            "ref_metin": REF_METIN_2,
            "yerlesik": True,
        },
    ]

    FACTORY_PRESETS: Dict[str, Dict[str, Any]] = {
        "tek_kelime": {
            "kod": "tek_kelime",
            "baslik": "1. Tek Kelime (Sözlük & Görsel Kelime)",
            "aciklama": "Sözlük kelimeleri için net vakıf, sıfır dip gürültüsü ve hızlı sönümlenme.",
            "hiz": 0.90,
            "temperature": 0.58,
            "top_k": 40,
            "top_p": 0.90,
            "min_tokens": 12,
            "max_tokens": 140,
            "tek_kelime_mi": True,
            "kelime_turu": "isim",
            "hikmetli_durak_ekle": False,
            "varsayilan_format": "wav",
            "cift_uretim_erkek_kadin": True,
            "dinamik_tonlama": False,
            "birlesik_bosluk_ms": 300,
            "dsp": {
                "hp_freq": 80.0,
                "lp_freq": 11200.0,
                "gate_esigi": 0.024,
                "aktif_esik_katsayi": 0.020,
                "bas_pay_ms": 45.0,
                "son_pay_ms": 220.0,
                "drive": 1.06,
                "fade_ms": 10.0,
                "tepe_normalizasyon": 0.891,
            },
        },
        "cumle": {
            "kod": "cumle",
            "baslik": "2. Cümle (Eğitim & Gramer Cümleleri)",
            "aciklama": "Soru, ünlem ve haber cümleleri için doğal tonlamalı ve vakıflı stüdyo okuması.",
            "hiz": 0.92,
            "temperature": 0.64,
            "top_k": 50,
            "top_p": 0.94,
            "min_tokens": 25,
            "max_tokens": 550,
            "tek_kelime_mi": False,
            "kelime_turu": "genel",
            "hikmetli_durak_ekle": False,
            "varsayilan_format": "mp3",
            "cift_uretim_erkek_kadin": True,
            "dinamik_tonlama": True,
            "birlesik_bosluk_ms": 350,
            "dsp": {
                "hp_freq": 80.0,
                "lp_freq": 11200.0,
                "gate_esigi": 0.020,
                "aktif_esik_katsayi": 0.018,
                "bas_pay_ms": 55.0,
                "son_pay_ms": 250.0,
                "drive": 1.06,
                "fade_ms": 12.0,
                "tepe_normalizasyon": 0.891,
            },
        },
        "atasozu": {
            "kod": "atasozu",
            "baslik": "3. Atasözü / Hikmetli Söz",
            "aciklama": "Vecize ve atasözleri için ağırbaşlı, tefekkür duraklı ve vurgulu okuma.",
            "hiz": 0.89,
            "temperature": 0.62,
            "top_k": 45,
            "top_p": 0.92,
            "min_tokens": 30,
            "max_tokens": 600,
            "tek_kelime_mi": False,
            "kelime_turu": "genel",
            "hikmetli_durak_ekle": True,
            "varsayilan_format": "wav",
            "cift_uretim_erkek_kadin": True,
            "dinamik_tonlama": True,
            "birlesik_bosluk_ms": 420,
            "dsp": {
                "hp_freq": 75.0,
                "lp_freq": 11200.0,
                "gate_esigi": 0.020,
                "aktif_esik_katsayi": 0.018,
                "bas_pay_ms": 60.0,
                "son_pay_ms": 260.0,
                "drive": 1.07,
                "fade_ms": 12.0,
                "tepe_normalizasyon": 0.891,
            },
        },
        "diyalog": {
            "kod": "diyalog",
            "baslik": "4. Diyalog (Çoklu Karakter Konuşması)",
            "aciklama": "8 referans sesten otomatik rol atamalı, konuşmacı bazlı ve birleştirilmiş diyalog üretimi.",
            "hiz": 0.94,
            "temperature": 0.66,
            "top_k": 50,
            "top_p": 0.95,
            "min_tokens": 25,
            "max_tokens": 650,
            "tek_kelime_mi": False,
            "kelime_turu": "genel",
            "hikmetli_durak_ekle": False,
            "varsayilan_format": "mp3",
            "cift_uretim_erkek_kadin": False,
            "dinamik_tonlama": True,
            "birlesik_bosluk_ms": 450,
            "dsp": {
                "hp_freq": 80.0,
                "lp_freq": 11200.0,
                "gate_esigi": 0.020,
                "aktif_esik_katsayi": 0.018,
                "bas_pay_ms": 55.0,
                "son_pay_ms": 240.0,
                "drive": 1.06,
                "fade_ms": 12.0,
                "tepe_normalizasyon": 0.891,
            },
        },
        "uzun_metin": {
            "kod": "uzun_metin",
            "baslik": "5. Uzun Metin / Okuma Parçası",
            "aciklama": "Paragrafları harf-i cer ve edatları bölmeden cümlelere ayırır, seslendirir ve birleştirir.",
            "hiz": 0.92,
            "temperature": 0.62,
            "top_k": 45,
            "top_p": 0.92,
            "min_tokens": 30,
            "max_tokens": 750,
            "tek_kelime_mi": False,
            "kelime_turu": "genel",
            "hikmetli_durak_ekle": False,
            "varsayilan_format": "mp3",
            "cift_uretim_erkek_kadin": False,
            "dinamik_tonlama": True,
            "birlesik_bosluk_ms": 350,
            "dsp": {
                "hp_freq": 80.0,
                "lp_freq": 11200.0,
                "gate_esigi": 0.020,
                "aktif_esik_katsayi": 0.018,
                "bas_pay_ms": 55.0,
                "son_pay_ms": 250.0,
                "drive": 1.06,
                "fade_ms": 12.0,
                "tepe_normalizasyon": 0.891,
            },
        },
    }

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or PROJECT_ROOT
        self.config_dir = self.project_root / "config"
        self.custom_voices_dir = self.project_root / "referans_sesler_ozel"
        self.user_settings_path = self.config_dir / "user_settings.json"
        self.factory_presets_path = self.config_dir / "factory_presets.json"

        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.custom_voices_dir.mkdir(parents=True, exist_ok=True)

        # Fabrika preset dosyasını (config/factory_presets.json) kodla tek kaynak olarak senkronize tut
        try:
            self._save_json(self.factory_presets_path, self.FACTORY_PRESETS)
        except Exception:
            pass

        self.user_settings: Dict[str, Any] = self._load_user_settings()
        self.voice_pool: List[Dict[str, Any]] = self._build_voice_pool()
        self._senkronize_ozel_ses_metinleri()

    def _default_user_settings(self) -> Dict[str, Any]:
        return {
            "ilk_kurulum_tamamlandi": False,
            "ilk_acilis_turu_gosterildi": False,
            "uzman_mod_aktif": False,
            "tema_modu": "koyu",
            "otomatik_guncelleme_kontrolu": True,
            "github_repo": "muallimun/Muallimun_Ses_Asistani",
            "aktif_motor_tercihi": "SPARK_ARABIC",
            "zorunlu_donanim_kademesi": "OTOMATIK",
            "varsayilan_cikti_klasoru": str(self.project_root / "cikti_sesler"),
            "varsayilan_erkek_ses": "ref_erkek_1",
            "varsayilan_kadin_ses": "ref_kadin_1",
            "otomatik_oynat_tekli": True,
            "otomatik_oynat_toplu_bitis": False,
            "presets": copy.deepcopy(self.FACTORY_PRESETS),
            "custom_voices": [],
            "voice_text_overrides": {},
        }

    def _load_user_settings(self) -> Dict[str, Any]:
        defaults = self._default_user_settings()
        if not self.user_settings_path.exists():
            self._save_json(self.user_settings_path, defaults)
            return defaults

        try:
            with open(self.user_settings_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            for k, v in defaults.items():
                if k not in loaded:
                    loaded[k] = v
            for p_key, p_val in self.FACTORY_PRESETS.items():
                if p_key not in loaded.get("presets", {}):
                    loaded["presets"][p_key] = copy.deepcopy(p_val)
                else:
                    for sub_k, sub_v in p_val.items():
                        if sub_k not in loaded["presets"][p_key]:
                            loaded["presets"][p_key][sub_k] = copy.deepcopy(sub_v)
                    for dsp_k, dsp_v in p_val["dsp"].items():
                        if dsp_k not in loaded["presets"][p_key]["dsp"]:
                            loaded["presets"][p_key]["dsp"][dsp_k] = dsp_v
            return loaded
        except Exception:
            return defaults

    def _save_json(self, path: Path, data: Dict[str, Any]) -> None:
        """Veri kaybını ve JSON bozulmasını önleyen atomik (tmp -> fsync -> replace) kayıt."""
        path.parent.mkdir(parents=True, exist_ok=True)
        gecici_yol = path.with_suffix(path.suffix + f".{uuid.uuid4().hex[:6]}.tmp")
        try:
            with open(gecici_yol, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            os.replace(str(gecici_yol), str(path))
        except Exception:
            if gecici_yol.exists():
                try:
                    gecici_yol.unlink()
                except OSError:
                    pass
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def save_user_settings(self) -> None:
        self._save_json(self.user_settings_path, self.user_settings)
        self.voice_pool = self._build_voice_pool()
        self._senkronize_ozel_ses_metinleri()

    def _build_voice_pool(self) -> List[Dict[str, Any]]:
        pool = copy.deepcopy(self.FACTORY_VOICE_POOL)
        overrides = self.user_settings.get("voice_text_overrides", {})
        for v in pool:
            if v["id"] in overrides and str(overrides[v["id"]]).strip():
                v["ref_metin"] = str(overrides[v["id"]]).strip()

        for custom in self.user_settings.get("custom_voices", []):
            c_copy = copy.deepcopy(custom)
            cid = c_copy.get("id", "")
            if cid in overrides:
                c_copy["ref_metin"] = str(overrides[cid]).strip()
            else:
                c_copy["ref_metin"] = str(c_copy.get("ref_metin", "")).strip()

            pool.append(c_copy)
        return pool

    def _senkronize_ozel_ses_metinleri(self) -> None:
        """
        Tüm ses havuzundaki referans metinleri ve özel seslerin cinsiyet/kategori
        bilgilerini ses motoru önbelleğiyle senkronize eder.
        """
        for v in self.voice_pool:
            vid = str(v.get("id", "")).strip()
            dosya_adi = str(v.get("dosya", "")).strip()
            metin = str(v.get("ref_metin", "")).strip()
            cinsiyet = str(v.get("cinsiyet", "E")).strip().upper()
            kategori = str(v.get("kategori", f"yetiskin_{cinsiyet}")).strip()

            if dosya_adi:
                tam_yol = self.resolve_voice_path(vid)
                # Metin boşaltılmışsa ('') da çağrılır ki eski önbellek kaydı silinsin
                ozel_referans_metni_kaydet(vid, metin)
                ozel_referans_metni_kaydet(dosya_adi, metin)
                ozel_referans_metni_kaydet(str(tam_yol), metin)

                ozel_referans_kategori_kaydet(vid, cinsiyet, kategori)
                ozel_referans_kategori_kaydet(dosya_adi, cinsiyet, kategori)
                ozel_referans_kategori_kaydet(str(tam_yol), cinsiyet, kategori)

    def get_preset(self, preset_code: str) -> Dict[str, Any]:
        presets = self.user_settings.get("presets", {})
        if preset_code in presets:
            return copy.deepcopy(presets[preset_code])
        return copy.deepcopy(self.FACTORY_PRESETS["cumle"])

    def save_user_preset(self, preset_code: str, updated_preset: Dict[str, Any]) -> None:
        if "presets" not in self.user_settings:
            self.user_settings["presets"] = copy.deepcopy(self.FACTORY_PRESETS)
        self.user_settings["presets"][preset_code] = copy.deepcopy(updated_preset)
        self.save_user_settings()

    def reset_preset_to_factory(self, preset_code: str) -> Dict[str, Any]:
        if preset_code in self.FACTORY_PRESETS:
            self.user_settings["presets"][preset_code] = copy.deepcopy(self.FACTORY_PRESETS[preset_code])
            self.save_user_settings()
            return copy.deepcopy(self.FACTORY_PRESETS[preset_code])
        return copy.deepcopy(self.FACTORY_PRESETS["cumle"])

    def reset_all_to_factory(self) -> None:
        self.user_settings["presets"] = copy.deepcopy(self.FACTORY_PRESETS)
        self.save_user_settings()

    def resolve_voice_path(self, voice_id_or_filename: str) -> Path:
        temiz_girdi = str(voice_id_or_filename or "").strip()
        if not temiz_girdi:
            return self.project_root / "ref_erkek_1.wav"

        for v in self.voice_pool:
            if v["id"] == temiz_girdi or v["dosya"] == temiz_girdi:
                dosya = os.path.basename(str(v["dosya"]))
                if v.get("yerlesik", False):
                    return self.project_root / dosya
                ozel_yol = self.custom_voices_dir / dosya
                if ozel_yol.exists():
                    return ozel_yol
                return self.custom_voices_dir / dosya

        sadece_dosya = os.path.basename(temiz_girdi)
        aday1 = self.project_root / sadece_dosya
        if aday1.exists() and aday1.is_file():
            return aday1
        aday2 = self.custom_voices_dir / sadece_dosya
        if aday2.exists() and aday2.is_file():
            return aday2
        return self.project_root / "ref_erkek_1.wav"

    def is_builtin_voice(self, voice_id: str) -> bool:
        if voice_id in self.YERLESIK_8_SES_IDLERI:
            return True
        for v in self.voice_pool:
            if v.get("id") == voice_id:
                return bool(v.get("yerlesik", False))
        return False

    def get_voice_prompt_text(self, voice_id: str) -> str:
        """
        Seçilen referans sesin Arapça metnini (Prompt Text) döndürür.
        KRİTİK DÜZELTME:
        - Yerleşik 8 hazır ses için her zaman kendi REF_METIN_1 veya REF_METIN_2 metnini döndürür.
        - Kullanıcı tarafından eklenen özel seslerde ('ozel_...') metin boş bırakılmışsa
          ASLA 'REF_METIN_1' döndürmez; '' (boş metin) döndürür ki Spark-TTS yanlışlıkla
          REF_METIN_1'i sesli olarak okumasın!
        """
        for v in self.voice_pool:
            if v.get("id") == voice_id:
                metin = str(v.get("ref_metin", "")).strip()
                if v.get("yerlesik", False) or voice_id in self.YERLESIK_8_SES_IDLERI:
                    return metin or (REF_METIN_2 if "_2" in voice_id else REF_METIN_1)
                return hareke_siralamasini_normallestir(metin) if metin else ""

        if voice_id in self.YERLESIK_8_SES_IDLERI:
            return REF_METIN_2 if "_2" in voice_id else REF_METIN_1
        return ""

    def add_custom_voice(
        self,
        kaynak_dosya_yolu: str,
        gorunen_ad: str,
        cinsiyet: str,
        kategori: str,
        ref_metin: str,
    ) -> Dict[str, Any]:
        """
        Kullanıcının seçtiği referans ses dosyasını (WAV/MP3/FLAC/OGG):
        - İç sessizliklerini doğal nefes aralığına sıkıştırarak,
        - Sondaki düz sessizlik kuyruğunu kırparak,
        - 24000 Hz Mono PCM_16 WAV formatına dönüştürerek
        'referans_sesler_ozel/' klasörüne kaydeder.
        """
        kaynak = Path(kaynak_dosya_yolu)
        if not kaynak.exists():
            raise FileNotFoundError(f"Referans ses dosyası bulunamadı: {kaynak_dosya_yolu}")

        temiz_isim = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in kaynak.stem.lower())
        benzersiz_kod = uuid.uuid4().hex[:8]
        yeni_id = f"ozel_{temiz_isim[:18]}_{benzersiz_kod}"
        hedef_dosya_adi = f"{yeni_id}.wav"
        hedef_wav = self.custom_voices_dir / hedef_dosya_adi

        from core.studyo_motoru import referans_sesi_on_temizle, _ses_dosyasini_guvenli_oku_np
        import soundfile as sf

        try:
            temiz_gecici_yol = referans_sesi_on_temizle(kaynak)
            shutil.copy2(temiz_gecici_yol, hedef_wav)
        except Exception:
            veri = _ses_dosyasini_guvenli_oku_np(str(kaynak), hedef_sr=24000)
            if veri.size < 2400:
                raise ValueError("Seçilen ses dosyası çok kısa veya geçersiz.")
            sf.write(str(hedef_wav), veri, 24000, subtype="PCM_16")

        if not hedef_wav.exists() or hedef_wav.stat().st_size < 1000:
            raise RuntimeError("Referans ses dosyası 24kHz WAV formatına dönüştürülemedi.")

        temiz_ref_metin = hareke_siralamasini_normallestir(str(ref_metin or "").strip())

        yeni_kayit = {
            "id": yeni_id,
            "ad": gorunen_ad.strip() or f"Özel Ses ({kaynak.stem})",
            "dosya": hedef_dosya_adi,
            "cinsiyet": "K" if cinsiyet.upper().startswith("K") else "E",
            "kategori": kategori,
            "ref_metin": temiz_ref_metin,
            "yerlesik": False,
        }

        if "custom_voices" not in self.user_settings:
            self.user_settings["custom_voices"] = []
        self.user_settings["custom_voices"].append(yeni_kayit)
        self.save_user_settings()
        return yeni_kayit

    def remove_custom_voice(self, voice_id: str) -> bool:
        custom_list = self.user_settings.get("custom_voices", [])
        yeni_liste = []
        silindi = False
        for c in custom_list:
            if c.get("id") == voice_id:
                silindi = True
                dosya_adi = c.get("dosya", "")
                dosya_yolu = self.custom_voices_dir / dosya_adi
                ozel_referans_metni_kaydet(voice_id, "")
                ozel_referans_metni_kaydet(dosya_adi, "")
                ozel_referans_metni_kaydet(str(dosya_yolu), "")
                if dosya_yolu.exists():
                    try:
                        dosya_yolu.unlink()
                    except OSError:
                        pass
            else:
                yeni_liste.append(c)

        if silindi:
            self.user_settings["custom_voices"] = yeni_liste
            if "voice_text_overrides" in self.user_settings:
                self.user_settings["voice_text_overrides"].pop(voice_id, None)
            self.save_user_settings()
        return silindi

    def update_voice_prompt_text(self, voice_id: str, yeni_metin: str) -> None:
        """
        Referans sesin Arapça metnini günceller.
        Özel seslerde ('ozel_...') kullanıcı metni silip boş bırakırsa boş olarak kaydeder;
        yerleşik 8 seste ise boş bırakılırsa fabrika metnini korur.
        """
        if "voice_text_overrides" not in self.user_settings:
            self.user_settings["voice_text_overrides"] = {}

        temiz = hareke_siralamasini_normallestir(str(yeni_metin or "").strip())
        yerlesik_mi = self.is_builtin_voice(voice_id)

        if yerlesik_mi and not temiz:
            temiz = REF_METIN_2 if "_2" in voice_id else REF_METIN_1

        self.user_settings["voice_text_overrides"][voice_id] = temiz

        for c in self.user_settings.get("custom_voices", []):
            if c.get("id") == voice_id:
                c["ref_metin"] = temiz

        self.save_user_settings()

    def get_default_output_dir(self) -> Path:
        raw = self.user_settings.get("varsayilan_cikti_klasoru", "")
        p = Path(raw) if raw else (self.project_root / "cikti_sesler")
        p.mkdir(parents=True, exist_ok=True)
        return p