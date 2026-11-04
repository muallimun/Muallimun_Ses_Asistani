#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MUALLİMUN AI SES STÜDYOSU PRO - TOPLU SESLENDİRME, 8 TONLAMA PROFİLİ, ZENGİN ŞABLON VE CHECKPOINT V2 MOTORU
Özellikler:
  1. 8 Akustik Tonlama Profili (Sözlük/Tek Kelime, Muallim, Babacan, Diyalog, Soru, Hitabet, Öyküleyici, Otomatik)
  2. Zenginleştirilmiş Şablonlar (4 Ayrı Çoklu Diyalog, 4 Ayrı Uzun Okuma Parçası, Cümle, Atasözü, Sözlük)
  3. Kaynak Dosyadaki Özel Ses İsimlendirme Desteği (ses_dosyasi, dosya_adi, ses_erkek, ses_kadin, audio)
  4. Path Traversal Korumalı Güvenli Çıktı Yolu Çözümleyici ve İçerik-Adresli SQLite Checkpoint v2
"""

import os
import re
import csv
import time
import json
import sqlite3
import hashlib
from contextlib import closing
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set

from PySide6.QtCore import QThread, Signal

from core.config_manager import PROJECT_ROOT, ConfigManager
from core.studyo_motoru import (
    MuallimunStudyoSesMotoru,
    CancelToken,
    arapca_akustik_metin_hazirla,
    sesleri_studyo_kalitesinde_birlestir,
    rol_tahmin_et,
    tr_kucult,
)

# ==============================================================================
# 1. GÜVENLİ DOSYA ADI VE YOL DOĞRULAYICI (PATH TRAVERSAL KORUMASI)
# ==============================================================================
WINDOWS_AYRILMIS_ADLAR = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def guvenli_kimlik_temizle(ham_deger: str, varsayilan: str = "kayit") -> str:
    temiz = str(ham_deger or "").strip()
    temiz = re.sub(r"[\\/:*?\"<>|\r\n\t]+", "_", temiz)
    temiz = temiz.replace("..", "_").strip(" ._")
    if not temiz:
        temiz = varsayilan
    kok_ad = temiz.split(".")[0].upper()
    if kok_ad in WINDOWS_AYRILMIS_ADLAR:
        temiz = f"_{temiz}"
    return temiz[:90]


def guvenli_goreli_dosya_yolu_temizle(ham_yol: str, varsayilan_uzanti: str = ".mp3") -> str:
    ham = str(ham_yol or "").strip().replace("\\", "/")
    if not ham:
        return ""
    ham = re.sub(r"^[a-zA-Z]:", "", ham).lstrip("/")

    parcalar = []
    for p in ham.split("/"):
        p_temiz = p.strip()
        if not p_temiz or p_temiz in (".", ".."):
            continue
        parcalar.append(guvenli_kimlik_temizle(p_temiz, varsayilan="ses"))

    if not parcalar:
        return ""

    son_parca = parcalar[-1]
    uzanti_kucuk = Path(son_parca).suffix.lower()
    if uzanti_kucuk not in (".wav", ".mp3"):
        uz = varsayilan_uzanti if varsayilan_uzanti.startswith(".") else f".{varsayilan_uzanti}"
        parcalar[-1] = f"{son_parca}{uz}"

    return "/".join(parcalar)


def guvenli_hedef_yol_cozumle(cikti_kok: Path, goreli_hedef: str | Path) -> Path:
    kok = cikti_kok.resolve()
    ham_str = str(goreli_hedef or "").strip().replace("\\", "/")
    ham_str = re.sub(r"^[a-zA-Z]:", "", ham_str).lstrip("/")

    parcalar = []
    for p in ham_str.split("/"):
        if not p or p in (".", ".."):
            continue
        parcalar.append(guvenli_kimlik_temizle(p, varsayilan="dosya"))

    if not parcalar:
        parcalar = ["cikti_ses.wav"]

    aday_hedef = (kok / Path(*parcalar)).resolve()
    try:
        aday_hedef.relative_to(kok)
    except ValueError:
        raise ValueError(f"Güvenlik ihlali: Hedef yol çıktı klasörü dışına çıkamaz ({goreli_hedef})")

    return aday_hedef


# ==============================================================================
# 2. 8 STÜDYO DUYGU / TONLAMA PROFİLİ (GERÇEK AKUSTİK, SAMPLING VE DSP ETKİLİ)
# ==============================================================================
DUYGU_TONU_PROFILLERI: Dict[str, Dict[str, Any]] = {
    "otomatik": {
        "kod": "otomatik",
        "ad": "✨ Otomatik (Noktalama ve Metne Göre Doğal Tonlama)",
        "hiz_carpani": 1.00,
        "temp_farki": 0.00,
        "top_p": 0.92,
        "top_k": 45,
        "drive_farki": 0.00,
        "son_pay_ek_ms": 0.0,
        "hikmetli_durak_zorla": False,
        "aciklama": "Soru (؟), ünlem (!), tek kelime ve cümle uzunluğuna göre hızı, sıcaklığı ve vurguyu otomatik ayarlar.",
    },
    "tek_kelime_sozluk": {
        "kod": "tek_kelime_sozluk",
        "ad": "🔤 Sözlük & Tek Kelime (Harf ve Mahreç Odaklı Net Okuma)",
        "hiz_carpani": 0.91,
        "temp_farki": -0.08,
        "top_p": 0.85,
        "top_k": 30,
        "drive_farki": +0.03,
        "son_pay_ek_ms": +25.0,
        "hikmetli_durak_zorla": False,
        "aciklama": "Sözlük maddeleri, tekil kelimeler ve kavramlar için sıfır sapmalı, mahreçleri keskin ve vakıf sonu belirgin okuma.",
    },
    "muallim_net": {
        "kod": "muallim_net",
        "ad": "🎓 Akademik Muallim (Tane Tane & Net Ders Tonu)",
        "hiz_carpani": 0.94,
        "temp_farki": -0.05,
        "top_p": 0.88,
        "top_k": 38,
        "drive_farki": +0.02,
        "son_pay_ek_ms": +20.0,
        "hikmetli_durak_zorla": False,
        "aciklama": "Gramer örnekleri ve ders kitabı cümleleri için tane tane, sakin ve anlaşılır öğretmen tonu.",
    },
    "babacan_hikmetli": {
        "kod": "babacan_hikmetli",
        "ad": "🌿 Babacan & Hikmetli Nasihat Tonu (Tefekkür Duraklı)",
        "hiz_carpani": 0.89,
        "temp_farki": -0.04,
        "top_p": 0.89,
        "top_k": 40,
        "drive_farki": +0.05,
        "son_pay_ek_ms": +45.0,
        "hikmetli_durak_zorla": True,
        "aciklama": "Atasözleri, vecizeler ve hikmetli sözler için ağırbaşlı, sıcak tınılı ve tefekkür duraklı okuma.",
    },
    "canli_diyalog": {
        "kod": "canli_diyalog",
        "ad": "🎭 Canlı & Enerjik Diyalog Vurgusu",
        "hiz_carpani": 1.03,
        "temp_farki": +0.05,
        "top_p": 0.95,
        "top_k": 55,
        "drive_farki": 0.00,
        "son_pay_ek_ms": -10.0,
        "hikmetli_durak_zorla": False,
        "aciklama": "Karşılıklı konuşma ve diyalog replikleri için doğal, akıcı ve canlı konuşma tonu.",
    },
    "soru_merak": {
        "kod": "soru_merak",
        "ad": "❓ Soru & Merak Vurgusu (Yükselen Tonlama)",
        "hiz_carpani": 1.02,
        "temp_farki": +0.06,
        "top_p": 0.95,
        "top_k": 55,
        "drive_farki": +0.01,
        "son_pay_ek_ms": +15.0,
        "hikmetli_durak_zorla": False,
        "aciklama": "Soru edatları (هَلْ، مَاذَا، كَيْفَ، أَيْنَ) içeren cümlelerde soru vurgusunu belirginleştirir.",
    },
    "coskulu_hitabet": {
        "kod": "coskulu_hitabet",
        "ad": "❗ Coşkulu & Vurgulu Hitabet Tonu",
        "hiz_carpani": 0.98,
        "temp_farki": +0.07,
        "top_p": 0.96,
        "top_k": 60,
        "drive_farki": +0.06,
        "son_pay_ek_ms": +30.0,
        "hikmetli_durak_zorla": True,
        "aciklama": "Ünlem, nida (يَا أَيُّهَا) ve hitabet cümleleri için dolgun ve güçlü vurgu.",
    },
    "oykuleyici_dingin": {
        "kod": "oykuleyici_dingin",
        "ad": "📖 Dingin Öyküleyici (Uzun Metin & Hikaye Anlatımı)",
        "hiz_carpani": 0.93,
        "temp_farki": -0.02,
        "top_p": 0.90,
        "top_k": 42,
        "drive_farki": +0.01,
        "son_pay_ek_ms": +35.0,
        "hikmetli_durak_zorla": True,
        "aciklama": "Okuma parçaları ve uzun paragraflar için dinleyiciyi yormayan, dengeli anlatıcı temposu.",
    },
}

SES_KISA_KOD_HARITASI: Dict[str, str] = {
    "OTOMATIK": "otomatik",
    "AUTO": "otomatik",
    "IKISI": "IKISI",
    "İKİSİ": "IKISI",
    "CIFT": "IKISI",
    "ÇİFT": "IKISI",
    "E+K": "IKISI",
    "DIREKT": "_varsayilan_sentetik_ref",
    "FAST": "_varsayilan_sentetik_ref",
    "E1": "ref_erkek_1",
    "ERKEK1": "ref_erkek_1",
    "REF_ERKEK_1": "ref_erkek_1",
    "E2": "ref_erkek_2",
    "ERKEK2": "ref_erkek_2",
    "REF_ERKEK_2": "ref_erkek_2",
    "K1": "ref_kadin_1",
    "KADIN1": "ref_kadin_1",
    "REF_KADIN_1": "ref_kadin_1",
    "K2": "ref_kadin_2",
    "KADIN2": "ref_kadin_2",
    "REF_KADIN_2": "ref_kadin_2",
    "EC1": "ref_erkek_cocuk_1",
    "REF_ERKEK_COCUK_1": "ref_erkek_cocuk_1",
    "EC2": "ref_erkek_cocuk_2",
    "REF_ERKEK_COCUK_2": "ref_erkek_cocuk_2",
    "KC1": "ref_kiz_cocuk_1",
    "REF_KIZ_COCUK_1": "ref_kiz_cocuk_1",
    "KC2": "ref_kiz_cocuk_2",
    "REF_KIZ_COCUK_2": "ref_kiz_cocuk_2",
}


def ses_secimi_kodunu_cozumle(secim_kodu: str) -> str:
    ham = str(secim_kodu or "").strip()
    if not ham:
        return "otomatik"
    ust = ham.upper().replace(" ", "")
    if ust in SES_KISA_KOD_HARITASI:
        return SES_KISA_KOD_HARITASI[ust]
    return ham


def duygu_ve_tonlama_detayli_hesapla(
    arapca_metin: str,
    preset: Dict[str, Any],
    secilen_duygu_kodu: str = "otomatik",
) -> Dict[str, Any]:
    """
    Seçilen tonlama profiline ve metnin yapısına göre yalnızca hız/sıcaklığı değil;
    top_p, top_k, DSP drive, son nefes payı ve hikmetli durak parametrelerini de hesaplar.
    """
    baz_hiz = float(preset.get("hiz", 0.92))
    baz_temp = float(preset.get("temperature", 0.64))
    dinamik_mi = bool(preset.get("dinamik_tonlama", True))
    metin = str(arapca_metin or "").strip()
    kelime_sayisi = len(metin.split())

    profil = DUYGU_TONU_PROFILLERI.get(secilen_duygu_kodu, DUYGU_TONU_PROFILLERI["otomatik"])
    hiz = baz_hiz * float(profil.get("hiz_carpani", 1.0))
    temp = baz_temp + float(profil.get("temp_farki", 0.0))
    top_p = float(profil.get("top_p", preset.get("top_p", 0.92)))
    top_k = int(profil.get("top_k", preset.get("top_k", 45)))
    algilanan_kip = profil["ad"]
    hikmetli_durak = bool(preset.get("hikmetli_durak_ekle", False)) or bool(profil.get("hikmetli_durak_zorla", False))

    dsp_kopya = dict(preset.get("dsp", {}))
    dsp_kopya["drive"] = round(
        max(1.0, min(1.22, float(dsp_kopya.get("drive", 1.06)) + float(profil.get("drive_farki", 0.0)))), 2
    )
    dsp_kopya["son_pay_ms"] = round(
        max(80.0, min(360.0, float(dsp_kopya.get("son_pay_ms", 240.0)) + float(profil.get("son_pay_ek_ms", 0.0)))), 1
    )

    if secilen_duygu_kodu == "otomatik" and dinamik_mi:
        if kelime_sayisi == 1:
            hiz = max(0.86, baz_hiz * 0.92)
            temp = max(0.50, baz_temp - 0.06)
            top_p, top_k = 0.86, 32
            algilanan_kip = "🔤 Tek Kelime / Sözlük Tonu"
        elif "؟" in metin or "?" in metin:
            hiz = min(1.06, baz_hiz * 1.02)
            temp = min(0.74, baz_temp + 0.05)
            top_p, top_k = 0.95, 55
            algilanan_kip = "❓ Soru & Merak Tonlaması"
        elif "!" in metin:
            hiz = min(1.05, baz_hiz * 1.01)
            temp = min(0.75, baz_temp + 0.06)
            top_p, top_k = 0.95, 55
            algilanan_kip = "❗ Ünlem / Vurgulu Tonlama"
        elif kelime_sayisi >= 12:
            hiz = max(0.86, baz_hiz * 0.96)
            temp = max(0.54, baz_temp - 0.02)
            hikmetli_durak = True
            algilanan_kip = "📖 Uzun Cümle (Dengeli Soluk)"
        else:
            algilanan_kip = "✨ Doğal Muallim Tonu"

    hiz = round(max(0.75, min(1.25, hiz)), 2)
    temp = round(max(0.45, min(0.78, temp)), 2)
    return {
        "hiz": hiz,
        "temp": temp,
        "top_p": top_p,
        "top_k": top_k,
        "dsp": dsp_kopya,
        "hikmetli_durak": hikmetli_durak,
        "algilanan_kip": algilanan_kip,
        "aciklama": profil.get("aciklama", ""),
    }


def duygu_ve_tonlama_hesapla(
    arapca_metin: str,
    preset: Dict[str, Any],
    secilen_duygu_kodu: str = "otomatik",
) -> Tuple[float, float, str, str]:
    detay = duygu_ve_tonlama_detayli_hesapla(arapca_metin, preset, secilen_duygu_kodu)
    return detay["hiz"], detay["temp"], detay["algilanan_kip"], detay["aciklama"]


# ==============================================================================
# 3. ZENGİNLEŞTİRİLMİŞ ÖRNEK ŞABLONLAR (4 DİYALOG + 4 UZUN METİN + SÖZLÜK & CÜMLE)
# ==============================================================================
ORNEK_COKLU_DIYALOGLAR_JSON: List[Dict[str, Any]] = [
    {
        "id": "dlg_001",
        "seviye": "A1",
        "baslik_tr": "1. Diyalog: Tanışma ve Selamlaşma",
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
                "arapca": "وَعَلَيْكُمُ السَّلَامُ، اِسْمِي لَيْلَى. كَيْفَ حَالُكَ؟",
                "turkce": "Aleykümselam, benim adım Leyla. Nasılsın?",
            },
            {
                "sira": 3,
                "konusmaci": "Ömer",
                "cinsiyet": "E",
                "arapca": "أَنَا بِخَيْرٍ وَالْحَمْدُ لِلَّهِ، تَشَرَّفْتُ بِمَعْرِفَتِكِ يَا لَيْلَى!",
                "turkce": "İyiyim elhamdülillah, tanıştığımıza memnun oldum Leyla!",
            },
        ],
    },
    {
        "id": "dlg_002",
        "seviye": "A2",
        "baslik_tr": "2. Diyalog: Sınıfta ve Kütüphanede",
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
                "konusmaci": "Öğrenci Ali",
                "cinsiyet": "E",
                "arapca": "كِتَابِي عَلَى الْمَكْتَبِ يَا أُسْتَاذِي.",
                "turkce": "Kitabım sıranın üzerinde öğretmenim.",
            },
            {
                "sira": 3,
                "konusmaci": "Öğretmen",
                "cinsiyet": "E",
                "arapca": "أَحْسَنْتَ يَا عَلِيُّ، اِفْتَحِ الصَّفْحَةَ الْعَاشِرَةَ وَاقْرَأِ الدَّرْسَ.",
                "turkce": "Aferin Ali, onuncu sayfayı aç ve dersi oku.",
            },
        ],
    },
    {
        "id": "dlg_003",
        "seviye": "B1",
        "baslik_tr": "3. Diyalog: Kitapçıda ve Çarşıda",
        "satirlar": [
            {
                "sira": 1,
                "konusmaci": "Müşteri Fatma",
                "cinsiyet": "K",
                "arapca": "مَسَاءُ الْخَيْرِ، أُرِيدُ مُعْجَمًا عَرَبِيًّا جَدِيدًا مِنْ فَضْلِكَ.",
                "turkce": "İyi akşamlar, yeni bir Arapça sözlük istiyorum lütfen.",
            },
            {
                "sira": 2,
                "konusmaci": "Satıcı",
                "cinsiyet": "E",
                "arapca": "مَسَاءُ النُّورِ، تَفَضَّلِي هَذَا الْمُعْجَمُ شَامِلٌ وَمُفِيدٌ جِدًّا لِلطُّلَّابِ.",
                "turkce": "İyi akşamlar, buyurun bu sözlük öğrenciler için kapsamlı ve çok faydalıdır.",
            },
            {
                "sira": 3,
                "konusmaci": "Müşteri Fatma",
                "cinsiyet": "K",
                "arapca": "شُكْرًا جَزِيلًا، سَأَشْتَرِي هَذَا الْمُعْجَمَ وَكِتَابَ الْقَوَاعِدِ أَيْضًا.",
                "turkce": "Çok teşekkür ederim, bu sözlüğü ve gramer kitabını da satın alacağım.",
            },
        ],
    },
    {
        "id": "dlg_004",
        "seviye": "B1",
        "baslik_tr": "4. Diyalog: Aile Bireyleri ve Meslekler",
        "satirlar": [
            {
                "sira": 1,
                "konusmaci": "Anne",
                "cinsiyet": "K",
                "arapca": "مَاذَا تُرِيدِينَ أَنْ تَكُونِي فِي الْمُسْتَقْبَلِ يَا ابْنَتِي زَيْنَبُ؟",
                "turkce": "Gelecekte ne olmak istiyorsun kızım Zeynep?",
            },
            {
                "sira": 2,
                "konusmaci": "Kızım Zeynep",
                "cinsiyet": "K",
                "arapca": "أُرِيدُ أَنْ أَكُونَ مُعَلِّمَةً نَاجِحَةً مِثْلَكِ يَا أُمِّي الْعَزِيزَةُ.",
                "turkce": "Senin gibi başarılı bir öğretmen olmak istiyorum sevgili annem.",
            },
            {
                "sira": 3,
                "konusmaci": "Baba",
                "cinsiyet": "E",
                "arapca": "بَارَكَ اللَّهُ فِيكِ يَا ابْنَتِي، اَلتَّعْلِيمُ مِهْنَةٌ شَرِيفَةٌ وَعَظِيمَةٌ.",
                "turkce": "Allah seni mübarek kılsın kızım, öğretmenlik şerefli ve yüce bir meslektir.",
            },
        ],
    },
]

ORNEK_COKLU_METINLER_JSON: List[Dict[str, Any]] = [
    {
        "id": "metin_001",
        "baslik_tr": "1. Okuma Metni: İlim ve Hikmet",
        "satirlar": [
            {"sira": 1, "arapca": "اَلْعِلْمُ نُورٌ يُضِيءُ طَرِيقَ الْإِنْسَانِ فِي الْحَيَاةِ."},
            {"sira": 2, "arapca": "وَالْقِرَاءَةُ الْمُسْتَمِرَّةُ تَفْتَحُ لَنَا أَبْوَابَ الْمَعْرِفَةِ وَالْحِكْمَةِ كُلَّ يَوْمٍ."},
            {"sira": 3, "arapca": "فَمَنْ جَدَّ وَجَدَ، وَمَنْ زَرَعَ حَصَدَ، وَمَنْ سَارَ عَلَى الدَّرْبِ وَصَلَ."},
        ],
    },
    {
        "id": "metin_002",
        "baslik_tr": "2. Okuma Metni: Fasih Arapça ve Önemi",
        "satirlar": [
            {"sira": 1, "arapca": "بِدَايَةً لَا بُدَّ أَنْ تَعْلَمَ أَنَّ الْعَرَبَ عِنْدَهُمْ لُغَةٌ رَسْمِيَّةٌ وَهِيَ الْفَصِيحَةُ."},
            {"sira": 2, "arapca": "وَتُسْتَخْدَمُ هَذِهِ اللُّغَةُ الْفَصِيحَةُ فِي الْأَوْرَاقِ الرَّسْمِيَّةِ وَالْكُتُبِ الْعِلْمِيَّةِ وَالْإِعْلَامِ."},
            {"sira": 3, "arapca": "وَمَنْ يَتَعَلَّمِ الْعَرَبِيَّةَ الْفُصْحَى يَسْتَطِيعُ أَنْ يَفْهَمَ الْقُرْآنَ الْكَرِيمَ وَالتُّرَاثَ الْإِسْلَامِيَّ."},
        ],
    },
    {
        "id": "metin_003",
        "baslik_tr": "3. Okuma Metni: İslam Medeniyetinde Kütüphaneler",
        "satirlar": [
            {"sira": 1, "arapca": "كَانَتِ الْمَكْتَبَاتُ فِي الْحَضَارَةِ الْإِسْلَامِيَّةِ مَرَاكِزَ عَظِيمَةً لِلْعِلْمِ وَالْبَحْثِ."},
            {"sira": 2, "arapca": "وَكَانَ الْعُلَمَاءُ وَالطُّلَّابُ يَجْتَمِعُونَ فِيهَا لِقِرَاءَةِ الْمَخْطُوطَاتِ وَمُنَاقَشَةِ الْمَسَائِلِ الْعِلْمِيَّةِ."},
            {"sira": 3, "arapca": "وَلِذَلِكَ انْتَشَرَتِ الْعُلُومُ وَالْمَعَارِفُ فِي جَمِيعِ أَنْحَاءِ الْعَالَمِ."},
        ],
    },
    {
        "id": "metin_004",
        "baslik_tr": "4. Okuma Metni: Günlük Hayat ve Zamanın Değeri",
        "satirlar": [
            {"sira": 1, "arapca": "اَلْوَقْتُ ثَمِينٌ جِدًّا فِي حَيَاةِ الْإِنْسَانِ الْمُؤْمِنِ وَالطَّالِبِ الْمُجْتَهِدِ."},
            {"sira": 2, "arapca": "يَسْتَيْقِظُ الطَّالِبُ النَّشِيطُ فِي الصَّبَاحِ الْبَاكِرِ وَيُرَتِّبُ أَعْمَالَهُ الْيَوْمِيَّةَ بِنِظَامٍ."},
            {"sira": 3, "arapca": "فَالنَّجَاحُ الْحَقِيقِيُّ يَحْتَاجُ إِلَى الصَّبْرِ وَالْعَمَلِ الْمُتَوَاصِلِ دُونَ كَسَلٍ."},
        ],
    },
]


class OrnekSablonOlusturucu:
    ORNEK_VERILER: Dict[str, List[Dict[str, Any]]] = {
        "tek_kelime": [
            {"id": "kelime_0001", "arapca": "كِتَابٌ", "turkce": "Kitap", "kelime_turu": "isim", "ses_secimi": "IKISI", "ses_dosyasi": ""},
            {"id": "kelime_0002", "arapca": "مَدْرَسَةٌ", "turkce": "Okul", "kelime_turu": "isim", "ses_secimi": "IKISI", "ses_dosyasi": ""},
            {"id": "kelime_0003", "arapca": "مُعَلِّمٌ", "turkce": "Öğretmen", "kelime_turu": "isim", "ses_secimi": "E1", "ses_dosyasi": ""},
            {"id": "kelime_0004", "arapca": "مَكْتَبَةٌ", "turkce": "Kütüphane", "kelime_turu": "isim", "ses_secimi": "K1", "ses_dosyasi": ""},
            {"id": "kelime_0005", "arapca": "يَكْتُبُ", "turkce": "Yazıyor", "kelime_turu": "fiil", "ses_secimi": "E1", "ses_dosyasi": ""},
            {"id": "kelime_0006", "arapca": "يَقْرَأُ", "turkce": "Okuyor", "kelime_turu": "fiil", "ses_secimi": "K1", "ses_dosyasi": ""},
        ],
        "cumle": [
            {
                "id": "cumle_0001",
                "arapca": "اَلْعِلْمُ نَافِعٌ وَالْجَهْلُ ضَارٌّ.",
                "turkce": "İlim faydalıdır, cehalet zararlıdır.",
                "ses_secimi": "IKISI",
                "ses_dosyasi": "",
            },
            {
                "id": "cumle_0002",
                "arapca": "أُمِّي مُعَلِّمَةٌ نَشِيطَةٌ تُحِبُّ عَمَلَهَا كَثِيرًا.",
                "turkce": "Annem işini çok seven çalışkan bir öğretmendir.",
                "ses_secimi": "K1",
                "ses_dosyasi": "",
            },
            {
                "id": "cumle_0003",
                "arapca": "بِدَايَةً لَا بُدَّ أَنْ تَعْلَمَ أَنَّ الْعَرَبَ عِنْدَهُمْ لُغَةٌ رَسْمِيَّةٌ وَهِيَ الْفَصِيحَةُ، وَتُسْتَخْدَمُ فِي الْأَوْرَاقِ الرَّسْمِيَّةِ.",
                "turkce": "Başlangıç olarak bilmelisin ki Arapların resmi bir dili vardır, o da Fasih Arapçadır ve resmi belgelerde kullanılır.",
                "ses_secimi": "E1",
                "ses_dosyasi": "",
            },
            {
                "id": "cumle_0004",
                "arapca": "هَلْ قَرَأْتَ هَذَا الْكِتَابَ الْجَدِيدَ يَا أَحْمَدُ؟",
                "turkce": "Bu yeni kitabı okudun mu Ahmet?",
                "ses_secimi": "E2",
                "ses_dosyasi": "",
            },
            {
                "id": "cumle_0005",
                "arapca": "ذَهَبَ الطُّلَّابُ فِي الصَّبَاحِ الْبَاكِرِ إِلَى الْمَكْتَبَةِ الْكَبِيرَةِ.",
                "turkce": "Öğrenciler sabah erkenden büyük kütüphaneye gittiler.",
                "ses_secimi": "IKISI",
                "ses_dosyasi": "",
            },
        ],
        "atasozu": [
            {
                "id": "ata_0001",
                "arapca": "مَنْ جَدَّ وَجَدَ، وَمَنْ زَرَعَ حَصَدَ.",
                "turkce": "Çalışan kazanır, eken biçer.",
                "ses_secimi": "IKISI",
                "ses_dosyasi": "",
            },
            {
                "id": "ata_0002",
                "arapca": "اَلْعِلْمُ فِي الصِّغَرِ كَالنَّقْشِ عَلَى الْحَجَرِ.",
                "turkce": "Küçükken öğrenilen ilim taşa kazınan yazı gibidir.",
                "ses_secimi": "E1",
                "ses_dosyasi": "",
            },
            {
                "id": "ata_0003",
                "arapca": "إِذَا كَانَ الْكَلَامُ مِنْ فِضَّةٍ فَالسُّكُوتُ مِنْ ذَهَبٍ.",
                "turkce": "Söz gümüşse sükût altındır.",
                "ses_secimi": "K1",
                "ses_dosyasi": "",
            },
            {
                "id": "ata_0004",
                "arapca": "اَلْوَقْتُ كَالسَّيْفِ إِنْ لَمْ تَقْطَعْهُ قَطَعَكَ.",
                "turkce": "Vakit kılıç gibidir, sen onu kesmezsen o seni keser.",
                "ses_secimi": "E2",
                "ses_dosyasi": "",
            },
        ],
        "diyalog": [
            {
                "id": f"{g['id']}_satir_{s['sira']:02d}",
                "grup_id": g["id"],
                "sira": s["sira"],
                "konusmaci": s["konusmaci"],
                "cinsiyet": s["cinsiyet"],
                "arapca": s["arapca"],
                "turkce": s["turkce"],
                "ses_secimi": "otomatik",
                "ses_dosyasi": "",
            }
            for g in ORNEK_COKLU_DIYALOGLAR_JSON
            for s in g["satirlar"]
        ],
        "uzun_metin": [
            {
                "id": f"{m['id']}_satir_{s['sira']:02d}",
                "grup_id": m["id"],
                "sira": s["sira"],
                "arapca": s["arapca"],
                "turkce": m["baslik_tr"],
                "ses_secimi": "E1",
                "ses_dosyasi": "",
            }
            for m in ORNEK_COKLU_METINLER_JSON
            for s in m["satirlar"]
        ],
    }

    @classmethod
    def sablon_kaydet(cls, mod_kodu: str, hedef_yol: str | Path) -> str:
        hedef = Path(hedef_yol).resolve()
        hedef.parent.mkdir(parents=True, exist_ok=True)
        ornekler = cls.ORNEK_VERILER.get(mod_kodu, cls.ORNEK_VERILER["cumle"])
        uzanti = hedef.suffix.lower()

        if uzanti == ".json":
            if mod_kodu == "diyalog":
                json_veri = ORNEK_COKLU_DIYALOGLAR_JSON
            elif mod_kodu == "uzun_metin":
                json_veri = ORNEK_COKLU_METINLER_JSON
            else:
                json_veri = ornekler
            with open(hedef, "w", encoding="utf-8") as f:
                json.dump(json_veri, f, ensure_ascii=False, indent=2)
            return str(hedef)

        if uzanti == ".txt":
            with open(hedef, "w", encoding="utf-8") as f:
                for k in ornekler:
                    f.write(f"{k['arapca']}\n")
            return str(hedef)

        if uzanti == ".csv":
            alanlar = list(ornekler[0].keys())
            with open(hedef, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=alanlar, delimiter=";")
                writer.writeheader()
                for k in ornekler:
                    writer.writerow(k)
            return str(hedef)

        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.worksheet.datavalidation import DataValidation

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Muallimun_{mod_kodu}"

        alanlar = list(ornekler[0].keys())
        ws.append(alanlar)

        baslik_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        baslik_font = Font(name="Segoe UI", size=11, bold=True, color="38BDF8")

        for col_idx in range(1, len(alanlar) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = baslik_fill
            cell.font = baslik_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        arapca_font = Font(name="Traditional Arabic", size=16)
        normal_font = Font(name="Segoe UI", size=11)

        for r_idx, kayit in enumerate(ornekler, start=2):
            for c_idx, alan in enumerate(alanlar, start=1):
                deger = kayit.get(alan, "")
                hucre = ws.cell(row=r_idx, column=c_idx, value=deger)
                if alan == "arapca":
                    hucre.font = arapca_font
                    hucre.alignment = Alignment(horizontal="right", vertical="center")
                else:
                    hucre.font = normal_font
                    hucre.alignment = Alignment(horizontal="left", vertical="center")

        if "ses_secimi" in alanlar:
            ses_col_idx = alanlar.index("ses_secimi") + 1
            col_harf = openpyxl.utils.get_column_letter(ses_col_idx)
            dv = DataValidation(
                type="list",
                formula1='"otomatik,IKISI,E1,E2,K1,K2,EC1,EC2,KC1,KC2,DIREKT"',
                allow_blank=True,
            )
            ws.add_data_validation(dv)
            dv.add(f"{col_harf}2:{col_harf}500")

        for col in ws.columns:
            en_uzun = max(len(str(cell.value or "")) for cell in col)
            harf = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[harf].width = max(16, min(55, en_uzun + 6))

        wb.save(str(hedef))
        return str(hedef)


# ==============================================================================
# 4. VERİ İÇE AKTARICI (JSON, CSV, EXCEL .XLSX, TXT — ÖZEL SES DOSYASI ADI DESTEKLİ)
# ==============================================================================
class VeriIceAktarici:
    @classmethod
    def dosyadan_yukle(
        cls, dosya_yolu: str | Path, varsayilan_mod: str = "cumle"
    ) -> Tuple[List[Dict[str, Any]], str]:
        yol = Path(dosya_yolu).resolve()
        if not yol.exists():
            raise FileNotFoundError(f"Veri dosyası bulunamadı: {yol}")

        uzanti = yol.suffix.lower()
        algilanan_mod = cls._dosya_adindan_mod_tahmin_et(yol.stem, varsayilan_mod)

        if uzanti == ".json":
            return cls._json_yukle(yol, algilanan_mod)
        if uzanti == ".csv":
            return cls._csv_yukle(yol, algilanan_mod)
        if uzanti == ".xlsx":
            return cls._excel_yukle(yol, algilanan_mod)
        if uzanti == ".xls":
            raise ValueError(
                "Eski '.xls' formatı yerine lütfen dosyayı modern Excel '.xlsx' veya '.csv' olarak kaydedip yükleyin."
            )
        if uzanti == ".txt":
            return cls._txt_yukle(yol, algilanan_mod)

        raise ValueError(f"Desteklenmeyen dosya uzantısı: {uzanti}")

    @staticmethod
    def _dosya_adindan_mod_tahmin_et(dosya_stem: str, varsayilan: str) -> str:
        ad = tr_kucult(dosya_stem)
        if any(k in ad for k in ["kelime", "sozluk", "sözlük", "vocab", "word"]):
            return "tek_kelime"
        if any(k in ad for k in ["atasoz", "atasöz", "hikmet", "vecize", "proverb"]):
            return "atasozu"
        if any(k in ad for k in ["diyalog", "dialogue", "konusma", "konuşma"]):
            return "diyalog"
        if any(k in ad for k in ["metin", "paragraf", "hikaye", "okuma"]):
            return "uzun_metin"
        if any(k in ad for k in ["cumle", "cümle", "sentence"]):
            return "cumle"
        return varsayilan

    @classmethod
    def _json_yukle(cls, yol: Path, varsayilan_mod: str) -> Tuple[List[Dict[str, Any]], str]:
        with open(yol, "r", encoding="utf-8-sig") as f:
            veri = json.load(f)

        if isinstance(veri, dict):
            for anahtar in ("kelimeler", "cumleler", "atasozleri", "diyaloglar", "metinler", "items", "data", "kayitlar"):
                if anahtar in veri and isinstance(veri[anahtar], list):
                    veri = veri[anahtar]
                    break
            else:
                veri = [veri]

        if not isinstance(veri, list):
            raise ValueError("JSON dosyası geçerli bir kayıt listesi içermiyor.")

        sozluk_listesi = [x for x in veri if isinstance(x, dict)]
        if not sozluk_listesi:
            raise ValueError("JSON dosyasında seslendirilecek nesne (sözlük) kaydı bulunamadı.")

        if "satirlar" in sozluk_listesi[0] and isinstance(sozluk_listesi[0]["satirlar"], list):
            duz_liste: List[Dict[str, Any]] = []
            ilk_satir = sozluk_listesi[0]["satirlar"][0] if sozluk_listesi[0]["satirlar"] else {}
            mod_kodu = "diyalog" if (isinstance(ilk_satir, dict) and "konusmaci" in ilk_satir) else "uzun_metin"

            for g_idx, grup in enumerate(sozluk_listesi, start=1):
                grup_id = guvenli_kimlik_temizle(grup.get("id", f"{mod_kodu}_{g_idx:03d}"))
                baslik = str(grup.get("baslik_tr", "")).strip()
                for s_idx, satir in enumerate(grup.get("satirlar", []), start=1):
                    if not isinstance(satir, dict):
                        continue
                    arapca = str(satir.get("arapca", "")).strip()
                    if not arapca:
                        continue
                    cins = str(satir.get("cinsiyet", "E")).strip().upper()
                    duz_liste.append({
                        "id": str(satir.get("id") or f"{grup_id}_satir_{s_idx:02d}"),
                        "grup_id": grup_id,
                        "sira": int(satir.get("sira", s_idx)),
                        "konusmaci": str(satir.get("konusmaci", "")).strip(),
                        "cinsiyet": cins,
                        "arapca": arapca,
                        "turkce": str(satir.get("turkce", baslik)).strip(),
                        "kelime_turu": "genel",
                        "referans_ses": str(satir.get("ses_secimi", satir.get("referans_ses", "otomatik"))),
                        "ses_dosyasi": str(satir.get("ses_dosyasi") or satir.get("dosya_adi") or satir.get("audio") or ""),
                        "ses_erkek": str(satir.get("ses_erkek") or satir.get("erkek_dosya") or ""),
                        "ses_kadin": str(satir.get("ses_kadin") or satir.get("kadin_dosya") or ""),
                        "mod": mod_kodu,
                    })
            return cls._duz_sozluk_listesini_normallestir(duz_liste, mod_kodu), mod_kodu

        return cls._duz_sozluk_listesini_normallestir(sozluk_listesi, varsayilan_mod), varsayilan_mod

    @classmethod
    def _csv_yukle(cls, yol: Path, varsayilan_mod: str) -> Tuple[List[Dict[str, Any]], str]:
        with open(yol, "r", encoding="utf-8-sig", newline="") as f:
            ornek_metin = f.read(4096)
            f.seek(0)
            ayrac = ";" if ornek_metin.count(";") >= ornek_metin.count(",") else ","

            reader = csv.reader(f, delimiter=ayrac, quotechar='"')
            tum_satirlar = [[h.strip() for h in r] for r in reader if any(h.strip() for h in r)]

        if not tum_satirlar:
            return [], varsayilan_mod

        ilk = [k.lower() for k in tum_satirlar[0]]
        baslik_var = any(
            k in ilk
            for k in ("id", "arapca", "arabic", "metin", "kelime", "turkce", "anlam", "ses_dosyasi", "dosya_adi")
        )

        ham_kayitlar: List[Dict[str, Any]] = []
        if baslik_var:
            basliklar = ilk
            for r in tum_satirlar[1:]:
                sozluk = {basliklar[i]: (r[i] if i < len(r) else "") for i in range(len(basliklar))}
                ham_kayitlar.append(sozluk)
        else:
            for idx, r in enumerate(tum_satirlar, start=1):
                if len(r) >= 3 and re.search(r"[\u0600-\u06FF]", r[1]):
                    ham_kayitlar.append({"id": f"{varsayilan_mod}_{idx:04d}", "arapca": r[1], "turkce": r[2]})
                elif len(r) >= 2 and re.search(r"[\u0600-\u06FF]", r[0]):
                    ham_kayitlar.append({"id": f"{varsayilan_mod}_{idx:04d}", "arapca": r[0], "turkce": r[1]})
                else:
                    ham_kayitlar.append({"id": f"{varsayilan_mod}_{idx:04d}", "arapca": r[0], "turkce": ""})

        return cls._duz_sozluk_listesini_normallestir(ham_kayitlar, varsayilan_mod), varsayilan_mod

    @classmethod
    def _excel_yukle(cls, yol: Path, varsayilan_mod: str) -> Tuple[List[Dict[str, Any]], str]:
        import openpyxl

        wb = openpyxl.load_workbook(str(yol), read_only=True, data_only=True)
        try:
            ws = wb.active
            satirlar = list(ws.iter_rows(values_only=True))
            if not satirlar:
                return [], varsayilan_mod

            basliklar = [str(h or "").strip().lower() for h in satirlar[0]]
            ham_kayitlar: List[Dict[str, Any]] = []
            for r in satirlar[1:]:
                if not r or not any(r):
                    continue
                sozluk = {
                    basliklar[i]: (str(r[i]).strip() if (i < len(r) and r[i] is not None) else "")
                    for i in range(len(basliklar))
                }
                ham_kayitlar.append(sozluk)
            return cls._duz_sozluk_listesini_normallestir(ham_kayitlar, varsayilan_mod), varsayilan_mod
        finally:
            wb.close()

    @classmethod
    def _txt_yukle(cls, yol: Path, varsayilan_mod: str) -> Tuple[List[Dict[str, Any]], str]:
        with open(yol, "r", encoding="utf-8-sig") as f:
            satirlar = [s.strip() for s in f.read().splitlines() if s.strip()]
        varsayilan_grup = guvenli_kimlik_temizle(yol.stem) if varsayilan_mod in ("uzun_metin", "diyalog") else ""
        ham = [
            {"id": f"{varsayilan_mod}_{i:04d}", "grup_id": varsayilan_grup, "sira": i, "arapca": s, "turkce": ""}
            for i, s in enumerate(satirlar, start=1)
        ]
        return cls._duz_sozluk_listesini_normallestir(ham, varsayilan_mod), varsayilan_mod

    @classmethod
    def _duz_sozluk_listesini_normallestir(
        cls, ham_liste: List[Dict[str, Any]], mod_kodu: str
    ) -> List[Dict[str, Any]]:
        norm_liste: List[Dict[str, Any]] = []
        gorulen_idler: Dict[str, int] = {}

        for idx, k in enumerate(ham_liste, start=1):
            if not isinstance(k, dict):
                continue

            arapca = str(
                k.get("arapca")
                or k.get("arabic")
                or k.get("metin")
                or k.get("kelime")
                or k.get("text")
                or ""
            ).strip()
            if not arapca:
                continue

            turkce = str(
                k.get("turkce")
                or k.get("anlam")
                or k.get("anlami")
                or k.get("cevirisi")
                or k.get("translation")
                or k.get("not")
                or ""
            ).strip()

            ozel_tek_dosya = str(
                k.get("ses_dosyasi")
                or k.get("dosya_adi")
                or k.get("filename")
                or k.get("file_name")
                or k.get("audio")
                or k.get("ses_yolu")
                or k.get("hedef_dosya")
                or ""
            ).strip()

            ozel_erkek_dosya = str(
                k.get("ses_erkek")
                or k.get("erkek_dosya")
                or k.get("erkek_ses")
                or k.get("audio_male")
                or ""
            ).strip()

            ozel_kadin_dosya = str(
                k.get("ses_kadin")
                or k.get("kadin_dosya")
                or k.get("kadin_ses")
                or k.get("audio_female")
                or ""
            ).strip()

            varsayilan_id_adayi = Path(ozel_tek_dosya).stem if ozel_tek_dosya else f"{mod_kodu}_{idx:04d}"
            ham_id = str(k.get("id") or k.get("kod") or varsayilan_id_adayi).strip()
            temiz_id = guvenli_kimlik_temizle(ham_id, varsayilan=f"{mod_kodu}_{idx:04d}")
            if temiz_id in gorulen_idler:
                gorulen_idler[temiz_id] += 1
                temiz_id = f"{temiz_id}_{gorulen_idler[temiz_id]}"
            else:
                gorulen_idler[temiz_id] = 1

            kelime_turu = str(
                k.get("kelime_turu") or k.get("tur") or ("isim" if mod_kodu == "tek_kelime" else "genel")
            ).strip().lower()
            ref_secim = ses_secimi_kodunu_cozumle(
                str(k.get("referans_ses") or k.get("ses_secimi") or k.get("voice") or "otomatik")
            )
            grup_id = guvenli_kimlik_temizle(str(k.get("grup_id") or ""), varsayilan="")

            norm_liste.append({
                "id": temiz_id,
                "grup_id": grup_id,
                "sira": int(k.get("sira", idx)) if str(k.get("sira", idx)).isdigit() else idx,
                "konusmaci": str(k.get("konusmaci", "")).strip(),
                "cinsiyet": str(k.get("cinsiyet", "IKISI")).strip().upper(),
                "arapca": arapca,
                "akustik_metin": str(k.get("akustik_metin", "")).strip(),
                "kaynak_metin_ozeti": hashlib.sha1(arapca.encode("utf-8")).hexdigest()[:10],
                "turkce": turkce,
                "kelime_turu": kelime_turu,
                "referans_ses": ref_secim,
                "ses_dosyasi": ozel_tek_dosya,
                "ses_erkek": ozel_erkek_dosya,
                "ses_kadin": ozel_kadin_dosya,
                "mod": str(k.get("mod", mod_kodu)),
            })

        return norm_liste


# ==============================================================================
# 5. İÇERİK-ADRESLİ CHECKPOINT V2 YÖNETİCİSİ (SQLITE WAL + PARMAK İZİ DOĞRULAMA)
# ==============================================================================
class CheckpointYoneticisi:
    def __init__(self, db_yolu: Optional[Path] = None):
        self.db_yolu = db_yolu or (PROJECT_ROOT / "config" / "studyo_checkpoints.db")
        self.db_yolu.parent.mkdir(parents=True, exist_ok=True)
        self._tabloyu_hazirla()

    def _baglanti_ac(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_yolu), timeout=15.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _tabloyu_hazirla(self) -> None:
        with closing(self._baglanti_ac()) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tamamlanan_satirlar_v2 (
                    job_hash TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    parmak_izi TEXT NOT NULL,
                    durum TEXT NOT NULL,
                    erkek_yol TEXT,
                    kadin_yol TEXT,
                    hata_mesaji TEXT,
                    guncelleme_zamani REAL,
                    PRIMARY KEY (job_hash, item_id)
                )
            """)
            conn.commit()

    def eski_isleri_temizle(self, gun: int = 30) -> None:
        """Veritabanının sınırsız büyümesini önlemek için 30 günden eski kayıtları temizler."""
        try:
            esik_zaman = time.time() - (max(1, int(gun)) * 86400)
            with closing(self._baglanti_ac()) as conn:
                conn.execute(
                    "DELETE FROM tamamlanan_satirlar_v2 WHERE guncelleme_zamani IS NOT NULL AND guncelleme_zamani < ?",
                    (esik_zaman,),
                )
                conn.commit()
        except Exception as e:
            print(f"⚠️ Eski checkpoint temizlik uyarısı: {e}")

    @staticmethod
    def is_ozeti_olustur(
        kaynak_dosya_adi: str,
        mod_kodu: str,
        kayit_sayisi: int,
        motor_tipi: str = "SPARK_ARABIC",
        erkek_ref: str = "ref_erkek_1",
        kadin_ref: str = "ref_kadin_1",
        cift_uretim: bool = True,
    ) -> str:
        temiz_kaynak = os.path.basename(str(kaynak_dosya_adi or "liste"))
        ham = f"{temiz_kaynak}|{mod_kodu}|{kayit_sayisi}|{motor_tipi}|{erkek_ref}|{kadin_ref}|{int(cift_uretim)}|v2"
        return hashlib.sha1(ham.encode("utf-8")).hexdigest()[:20]

    @staticmethod
    def satir_parmak_izi_olustur(
        arapca: str,
        akustik: str,
        motor_tipi: str,
        ref_bilgisi: str,
        uzanti: str,
        ek_parametreler: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Satırın metin, motor, referans ses ve sentez/DSP parametrelerini kapsayan
        deterministik parmak izini oluşturur.
        """
        ek_str = ""
        if ek_parametreler:
            try:
                ek_str = "|" + json.dumps(ek_parametreler, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            except Exception:
                ek_str = ""
        veri = f"{arapca.strip()}|{akustik.strip()}|{motor_tipi}|{ref_bilgisi}|{uzanti.lower()}{ek_str}"
        return hashlib.sha256(veri.encode("utf-8")).hexdigest()[:16]

    def tamamlananlari_getir(self, job_hash: str) -> Dict[str, Dict[str, Any]]:
        sonuc: Dict[str, Dict[str, Any]] = {}
        try:
            with closing(self._baglanti_ac()) as conn:
                cur = conn.execute(
                    "SELECT item_id, parmak_izi, erkek_yol, kadin_yol FROM tamamlanan_satirlar_v2 "
                    "WHERE job_hash = ? AND durum = 'tamamlandi'",
                    (job_hash,),
                )
                for item_id, parmak_izi, e_yol, k_yol in cur.fetchall():
                    sonuc[str(item_id)] = {
                        "parmak_izi": str(parmak_izi or ""),
                        "erkek_yol": str(e_yol or ""),
                        "kadin_yol": str(k_yol or ""),
                    }
        except Exception as e:
            print(f"⚠️ Checkpoint okuma uyarısı: {e}")
        return sonuc

    def kayit_guncelle(
        self,
        job_hash: str,
        item_id: str,
        parmak_izi: str,
        durum: str,
        erkek_yol: str = "",
        kadin_yol: str = "",
        hata_mesaji: str = "",
    ) -> None:
        try:
            with closing(self._baglanti_ac()) as conn:
                conn.execute(
                    """
                    INSERT INTO tamamlanan_satirlar_v2
                        (job_hash, item_id, parmak_izi, durum, erkek_yol, kadin_yol, hata_mesaji, guncelleme_zamani)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(job_hash, item_id) DO UPDATE SET
                        parmak_izi=excluded.parmak_izi,
                        durum=excluded.durum,
                        erkek_yol=excluded.erkek_yol,
                        kadin_yol=excluded.kadin_yol,
                        hata_mesaji=excluded.hata_mesaji,
                        guncelleme_zamani=excluded.guncelleme_zamani
                    """,
                    (job_hash, item_id, parmak_izi, durum, erkek_yol, kadin_yol, hata_mesaji, time.time()),
                )
                conn.commit()
        except Exception as e:
            print(f"⚠️ Checkpoint yazma uyarısı: {e}")

    def is_gecmisini_temizle(self, job_hash: str) -> None:
        try:
            with closing(self._baglanti_ac()) as conn:
                conn.execute("DELETE FROM tamamlanan_satirlar_v2 WHERE job_hash = ?", (job_hash,))
                conn.commit()
        except Exception as e:
            print(f"⚠️ Checkpoint temizleme uyarısı: {e}")


# ==============================================================================
# 6. TOPLU SESLENDİRME ARKA PLAN İŞÇİSİ (ÖZEL DOSYA ADI & GRUP İÇİ BİRLEŞTİRME)
# ==============================================================================
class StudyoBatchWorker(QThread):
    ilerleme_sinyali = Signal(int, int, str)
    satir_durum_sinyali = Signal(int, str, str, str, str)
    log_sinyali = Signal(str)
    hata_sinyali = Signal(str)
    tamamlandi_sinyali = Signal(dict)

    def __init__(
        self,
        motor: MuallimunStudyoSesMotoru,
        config_manager: ConfigManager,
        kayitlar: List[Dict[str, Any]],
        mod_kodu: str,
        cikti_kok_klasor: str | Path,
        cift_uretim_erkek_kadin: bool = True,
        secilen_erkek_ref_id: str = "ref_erkek_1",
        secilen_kadin_ref_id: str = "ref_kadin_1",
        secilen_duygu_tonu: str = "otomatik",
        mevcut_sesleri_atla: bool = True,
        kaynak_dosya_adi: str = "arayuz_listesi",
        sadece_secili_indisler: Optional[List[int]] = None,
        zorunlu_motor_tipi: Optional[str] = None,
        gruplari_birlestir: bool = True,
    ):
        super().__init__()
        self.motor = motor
        self.config_manager = config_manager
        self.kayitlar = kayitlar
        self.mod_kodu = mod_kodu
        self.cikti_kok_klasor = Path(cikti_kok_klasor).resolve()
        self.cift_uretim_erkek_kadin = cift_uretim_erkek_kadin
        self.secilen_erkek_ref_id = secilen_erkek_ref_id
        self.secilen_kadin_ref_id = secilen_kadin_ref_id
        self.secilen_duygu_tonu = secilen_duygu_tonu
        self.mevcut_sesleri_atla = mevcut_sesleri_atla
        self.kaynak_dosya_adi = kaynak_dosya_adi
        self.sadece_secili_indisler = set(sadece_secili_indisler) if sadece_secili_indisler is not None else None
        self.zorunlu_motor_tipi = zorunlu_motor_tipi or self.motor.motor_tipi
        self.gruplari_birlestir = bool(gruplari_birlestir)

        self.cancel_token = CancelToken()
        self._durdur_istegi = False
        self._duraklat_istegi = False

    def duraklat(self) -> None:
        self._duraklat_istegi = True

    def devam_et(self) -> None:
        self._duraklat_istegi = False

    def durdur(self) -> None:
        self._durdur_istegi = True
        self._duraklat_istegi = False
        self.cancel_token.cancel()
        if self.motor is not None:
            self.motor.durdur()

    def _deterministik_konusmaci_sesi_sec(self, grup_id: str, konusmaci: str, cinsiyet: str) -> str:
        hedef_kat = rol_tahmin_et(konusmaci, cinsiyet)
        cins = "K" if str(cinsiyet or "E").upper().startswith("K") else "E"
        adaylar = [
            v["id"] for v in self.config_manager.voice_pool
            if v.get("kategori") == hedef_kat
        ]
        if not adaylar:
            adaylar = [
                v["id"] for v in self.config_manager.voice_pool
                if v.get("cinsiyet") == cins
            ]
        if not adaylar:
            return self.secilen_kadin_ref_id if cins == "K" else self.secilen_erkek_ref_id

        imza = f"{grup_id}|{tr_kucult(konusmaci)}|{cins}"
        secim_idx = int(hashlib.sha1(imza.encode("utf-8")).hexdigest()[:8], 16) % len(adaylar)
        return adaylar[secim_idx]

    def _satir_hedef_yollarini_hesapla(
        self,
        mod_alt_klasor: Path,
        kayit: Dict[str, Any],
        item_id: str,
        grup_id: str,
        sira_no: int,
        uzanti: str,
        cift_uretim_mi: bool,
    ) -> Tuple[Path, Path]:
        ozel_tek = guvenli_goreli_dosya_yolu_temizle(str(kayit.get("ses_dosyasi", "")), uzanti)
        ozel_erkek = guvenli_goreli_dosya_yolu_temizle(str(kayit.get("ses_erkek", "")), uzanti)
        ozel_kadin = guvenli_goreli_dosya_yolu_temizle(str(kayit.get("ses_kadin", "")), uzanti)

        if cift_uretim_mi:
            if ozel_erkek:
                e_yol = guvenli_hedef_yol_cozumle(mod_alt_klasor, ozel_erkek)
            elif ozel_tek:
                e_yol = guvenli_hedef_yol_cozumle(mod_alt_klasor, f"erkek/{ozel_tek}")
            else:
                e_yol = guvenli_hedef_yol_cozumle(mod_alt_klasor, f"erkek/{item_id}{uzanti}")

            if ozel_kadin:
                k_yol = guvenli_hedef_yol_cozumle(mod_alt_klasor, ozel_kadin)
            elif ozel_tek:
                k_yol = guvenli_hedef_yol_cozumle(mod_alt_klasor, f"kadin/{ozel_tek}")
            else:
                k_yol = guvenli_hedef_yol_cozumle(mod_alt_klasor, f"kadin/{item_id}{uzanti}")

            return e_yol, k_yol

        if ozel_tek:
            hedef_goreli = f"{grup_id}/{ozel_tek}" if (grup_id and "/" not in ozel_tek) else ozel_tek
            tek_yol = guvenli_hedef_yol_cozumle(mod_alt_klasor, hedef_goreli)
        elif ozel_erkek:
            tek_yol = guvenli_hedef_yol_cozumle(mod_alt_klasor, ozel_erkek)
        elif ozel_kadin:
            tek_yol = guvenli_hedef_yol_cozumle(mod_alt_klasor, ozel_kadin)
        elif grup_id:
            tek_yol = guvenli_hedef_yol_cozumle(mod_alt_klasor, f"{grup_id}/satir_{sira_no:02d}{uzanti}")
        else:
            tek_yol = guvenli_hedef_yol_cozumle(mod_alt_klasor, f"{item_id}{uzanti}")

        return tek_yol, Path("")

    def run(self) -> None:
        baslangic_zaman = time.time()
        toplam_hedef = len(self.sadece_secili_indisler) if self.sadece_secili_indisler is not None else len(self.kayitlar)
        basarili_sayac = 0
        atlanan_sayac = 0
        hatali_sayac = 0
        birlestirilen_grup_sayac = 0

        try:
            self.motor.durdur_istegi = False
            if self.zorunlu_motor_tipi and self.motor.motor_tipi != self.zorunlu_motor_tipi:
                self.motor.aktif_motoru_degistir(self.zorunlu_motor_tipi)

            preset = self.config_manager.get_preset(self.mod_kodu)
            tek_kelime_mi = bool(preset.get("tek_kelime_mi", self.mod_kodu == "tek_kelime"))
            uzanti = ".wav" if str(preset.get("varsayilan_format", "wav")).lower() == "wav" else ".mp3"
            min_tok_ovr = preset.get("min_tokens")
            max_tok_ovr = preset.get("max_tokens")

            cp = CheckpointYoneticisi()
            cp.eski_isleri_temizle(gun=30)
            job_hash = cp.is_ozeti_olustur(
                kaynak_dosya_adi=self.kaynak_dosya_adi,
                mod_kodu=self.mod_kodu,
                kayit_sayisi=len(self.kayitlar),
                motor_tipi=self.motor.motor_tipi,
                erkek_ref=self.secilen_erkek_ref_id,
                kadin_ref=self.secilen_kadin_ref_id,
                cift_uretim=self.cift_uretim_erkek_kadin,
            )
            onceden_tamamlananlar = cp.tamamlananlari_getir(job_hash) if self.mevcut_sesleri_atla else {}

            mod_alt_klasor = guvenli_hedef_yol_cozumle(self.cikti_kok_klasor, self.mod_kodu)
            mod_alt_klasor.mkdir(parents=True, exist_ok=True)

            islenen_grup_idleri: Set[str] = set()
            grup_uretilen_dosyalar: Dict[str, List[str]] = {}
            islenen_sayac = 0

            for idx, kayit in enumerate(self.kayitlar):
                if self.sadece_secili_indisler is not None and idx not in self.sadece_secili_indisler:
                    continue

                while self._duraklat_istegi and not self._durdur_istegi and not self.cancel_token.is_cancelled:
                    time.sleep(0.15)

                if self._durdur_istegi or self.cancel_token.is_cancelled or self.motor.durdur_istegi:
                    self.satir_durum_sinyali.emit(idx, "⏹️ Durduruldu", "", "", "")
                    break

                try:
                    item_id = guvenli_kimlik_temizle(kayit.get("id", f"satir_{idx + 1:04d}"))
                    grup_id = guvenli_kimlik_temizle(kayit.get("grup_id", ""), varsayilan="")
                    sira_no = int(kayit.get("sira", idx + 1)) if str(kayit.get("sira", idx + 1)).isdigit() else (idx + 1)
                    arapca = str(kayit.get("arapca", "")).strip()
                    if not arapca:
                        atlanan_sayac += 1
                        islenen_sayac += 1
                        yuzde_str = f"%{int(round((islenen_sayac / max(1, toplam_hedef)) * 100))}"
                        self.ilerleme_sinyali.emit(islenen_sayac, toplam_hedef, yuzde_str)
                        continue

                    ton_detay = duygu_ve_tonlama_detayli_hesapla(arapca, preset, self.secilen_duygu_tonu)
                    satir_hiz = ton_detay["hiz"]
                    satir_temp = ton_detay["temp"]
                    satir_top_p = ton_detay["top_p"]
                    satir_top_k = ton_detay["top_k"]
                    dsp_ayar = ton_detay["dsp"]
                    hikmetli = ton_detay["hikmetli_durak"]

                    sentez_ek_kimlik = {
                        "hiz": satir_hiz,
                        "temp": satir_temp,
                        "top_p": satir_top_p,
                        "top_k": satir_top_k,
                        "duygu": self.secilen_duygu_tonu,
                        "dsp": dsp_ayar,
                    }

                    kelime_turu = str(kayit.get("kelime_turu", preset.get("kelime_turu", "genel")))
                    guncel_metin_ozeti = hashlib.sha1(arapca.encode("utf-8")).hexdigest()[:10]
                    eski_ozet = str(kayit.get("kaynak_metin_ozeti", ""))
                    mevcut_akustik = str(kayit.get("akustik_metin", "")).strip()

                    if not mevcut_akustik or (eski_ozet and eski_ozet != guncel_metin_ozeti):
                        akustik = arapca_akustik_metin_hazirla(
                            arapca, kelime_turu=kelime_turu, hikmetli_durak_ekle=hikmetli
                        )
                        kayit["akustik_metin"] = akustik
                        kayit["kaynak_metin_ozeti"] = guncel_metin_ozeti
                    else:
                        akustik = mevcut_akustik

                    satir_ref_secimi = ses_secimi_kodunu_cozumle(str(kayit.get("referans_ses", "otomatik")))

                    if satir_ref_secimi == "IKISI":
                        satir_cift_mi = True
                    elif satir_ref_secimi not in ("otomatik", ""):
                        satir_cift_mi = False
                    elif grup_id and self.mod_kodu in ("diyalog", "uzun_metin"):
                        satir_cift_mi = False
                    else:
                        satir_cift_mi = self.cift_uretim_erkek_kadin

                    if grup_id:
                        islenen_grup_idleri.add(grup_id)
                        if grup_id not in grup_uretilen_dosyalar:
                            grup_uretilen_dosyalar[grup_id] = []

                    if satir_cift_mi:
                        erkek_hedef, kadin_hedef = self._satir_hedef_yollarini_hesapla(
                            mod_alt_klasor, kayit, item_id, grup_id, sira_no, uzanti, cift_uretim_mi=True
                        )
                        erkek_hedef.parent.mkdir(parents=True, exist_ok=True)
                        kadin_hedef.parent.mkdir(parents=True, exist_ok=True)

                        parmak_izi = cp.satir_parmak_izi_olustur(
                            arapca,
                            akustik,
                            self.motor.motor_tipi,
                            f"{self.secilen_erkek_ref_id}+{self.secilen_kadin_ref_id}",
                            uzanti,
                            ek_parametreler=sentez_ek_kimlik,
                        )

                        erkek_var = erkek_hedef.exists() and erkek_hedef.stat().st_size > 1000
                        kadin_var = kadin_hedef.exists() and kadin_hedef.stat().st_size > 1000
                        cp_kayit = onceden_tamamlananlar.get(item_id)
                        parmak_izi_ayni = (cp_kayit is not None and cp_kayit.get("parmak_izi") == parmak_izi)

                        if self.mevcut_sesleri_atla and erkek_var and kadin_var and parmak_izi_ayni:
                            atlanan_sayac += 1
                            islenen_sayac += 1
                            self.satir_durum_sinyali.emit(
                                idx, "⏭️ Atlandı (Mevcut)", akustik, str(erkek_hedef), str(kadin_hedef)
                            )
                            yuzde_str = f"%{int(round((islenen_sayac / max(1, toplam_hedef)) * 100))}"
                            self.ilerleme_sinyali.emit(islenen_sayac, toplam_hedef, yuzde_str)
                            continue

                        self.satir_durum_sinyali.emit(idx, "🎙️ Çift Ses Üretiliyor...", akustik, "", "")
                        ref_kullan = (self.motor.motor_tipi != "FAST_DIRECT_TTS")

                        e_yol = str(self.config_manager.resolve_voice_path(self.secilen_erkek_ref_id))
                        e_metin = self.config_manager.get_voice_prompt_text(self.secilen_erkek_ref_id)
                        ok_e = self.motor.uret_ve_kaydet(
                            arapca_metin=arapca,
                            ref_wav_yolu=e_yol,
                            cikti_yolu=erkek_hedef,
                            hiz=satir_hiz,
                            temperature=satir_temp,
                            kelime_turu=kelime_turu,
                            tek_kelime_mi=tek_kelime_mi,
                            hikmetli_durak_ekle=hikmetli,
                            wav_formatini_zorla=(erkek_hedef.suffix.lower() == ".wav"),
                            ozel_ref_metin=e_metin,
                            onceden_hazirlanmis_akustik_metin=akustik,
                            min_tokens_override=min_tok_ovr,
                            max_tokens_override=max_tok_ovr,
                            dsp_ayar=dsp_ayar,
                            referans_ses_kullan=ref_kullan,
                            cancel_token=self.cancel_token,
                            top_p_override=satir_top_p,
                            top_k_override=satir_top_k,
                        )

                        if self._durdur_istegi or self.cancel_token.is_cancelled or self.motor.durdur_istegi:
                            self.satir_durum_sinyali.emit(idx, "⏹️ Durduruldu", akustik, "", "")
                            break

                        k_yol = str(self.config_manager.resolve_voice_path(self.secilen_kadin_ref_id))
                        k_metin = self.config_manager.get_voice_prompt_text(self.secilen_kadin_ref_id)
                        ok_k = self.motor.uret_ve_kaydet(
                            arapca_metin=arapca,
                            ref_wav_yolu=k_yol,
                            cikti_yolu=kadin_hedef,
                            hiz=satir_hiz,
                            temperature=satir_temp,
                            kelime_turu=kelime_turu,
                            tek_kelime_mi=tek_kelime_mi,
                            hikmetli_durak_ekle=hikmetli,
                            wav_formatini_zorla=(kadin_hedef.suffix.lower() == ".wav"),
                            ozel_ref_metin=k_metin,
                            onceden_hazirlanmis_akustik_metin=akustik,
                            min_tokens_override=min_tok_ovr,
                            max_tokens_override=max_tok_ovr,
                            dsp_ayar=dsp_ayar,
                            referans_ses_kullan=ref_kullan,
                            cancel_token=self.cancel_token,
                            top_p_override=satir_top_p,
                            top_k_override=satir_top_k,
                        )

                        if self._durdur_istegi or self.cancel_token.is_cancelled or self.motor.durdur_istegi:
                            self.satir_durum_sinyali.emit(idx, "⏹️ Durduruldu", akustik, "", "")
                            break

                        if ok_e and ok_k:
                            basarili_sayac += 1
                            cp.kayit_guncelle(
                                job_hash, item_id, parmak_izi, "tamamlandi", str(erkek_hedef), str(kadin_hedef)
                            )
                            self.satir_durum_sinyali.emit(
                                idx, "✅ Tamamlandı (E+K)", akustik, str(erkek_hedef), str(kadin_hedef)
                            )
                        else:
                            hatali_sayac += 1
                            gercek_hata = self.motor.son_hata_mesaji or "E/K sentez hatası"
                            cp.kayit_guncelle(job_hash, item_id, parmak_izi, "hatali", hata_mesaji=gercek_hata)
                            self.satir_durum_sinyali.emit(idx, f"❌ Hata: {gercek_hata[:38]}", akustik, "", "")

                    else:
                        if satir_ref_secimi not in ("otomatik", "", "IKISI"):
                            hedef_ref_id = satir_ref_secimi
                        elif grup_id and kayit.get("konusmaci"):
                            hedef_ref_id = self._deterministik_konusmaci_sesi_sec(
                                grup_id, str(kayit.get("konusmaci", "")), str(kayit.get("cinsiyet", "E"))
                            )
                        else:
                            cins_kodu = str(kayit.get("cinsiyet", "E")).upper()
                            hedef_ref_id = self.secilen_kadin_ref_id if cins_kodu.startswith("K") else self.secilen_erkek_ref_id

                        tek_hedef, _ = self._satir_hedef_yollarini_hesapla(
                            mod_alt_klasor, kayit, item_id, grup_id, sira_no, uzanti, cift_uretim_mi=False
                        )
                        tek_hedef.parent.mkdir(parents=True, exist_ok=True)

                        parmak_izi = cp.satir_parmak_izi_olustur(
                            arapca,
                            akustik,
                            self.motor.motor_tipi,
                            hedef_ref_id,
                            tek_hedef.suffix,
                            ek_parametreler=sentez_ek_kimlik,
                        )
                        dosya_var = tek_hedef.exists() and tek_hedef.stat().st_size > 1000
                        cp_kayit = onceden_tamamlananlar.get(item_id)
                        parmak_izi_ayni = (cp_kayit is not None and cp_kayit.get("parmak_izi") == parmak_izi)

                        if self.mevcut_sesleri_atla and dosya_var and parmak_izi_ayni:
                            atlanan_sayac += 1
                            islenen_sayac += 1
                            if grup_id:
                                grup_uretilen_dosyalar[grup_id].append(str(tek_hedef))
                            self.satir_durum_sinyali.emit(idx, "⏭️ Atlandı (Mevcut)", akustik, str(tek_hedef), "")
                            yuzde_str = f"%{int(round((islenen_sayac / max(1, toplam_hedef)) * 100))}"
                            self.ilerleme_sinyali.emit(islenen_sayac, toplam_hedef, yuzde_str)
                            continue

                        self.satir_durum_sinyali.emit(idx, "🎙️ Üretiliyor...", akustik, "", "")
                        ref_kullan = (
                            self.motor.motor_tipi != "FAST_DIRECT_TTS"
                            and hedef_ref_id != "_varsayilan_sentetik_ref"
                        )
                        cozulen_ref = hedef_ref_id if hedef_ref_id != "_varsayilan_sentetik_ref" else self.secilen_erkek_ref_id
                        ref_yol = str(self.config_manager.resolve_voice_path(cozulen_ref))
                        ref_metin = self.config_manager.get_voice_prompt_text(cozulen_ref)

                        ok_tek = self.motor.uret_ve_kaydet(
                            arapca_metin=arapca,
                            ref_wav_yolu=ref_yol,
                            cikti_yolu=tek_hedef,
                            hiz=satir_hiz,
                            temperature=satir_temp,
                            kelime_turu=kelime_turu,
                            tek_kelime_mi=tek_kelime_mi,
                            hikmetli_durak_ekle=hikmetli,
                            wav_formatini_zorla=(tek_hedef.suffix.lower() == ".wav"),
                            ozel_ref_metin=ref_metin,
                            onceden_hazirlanmis_akustik_metin=akustik,
                            min_tokens_override=min_tok_ovr,
                            max_tokens_override=max_tok_ovr,
                            dsp_ayar=dsp_ayar,
                            referans_ses_kullan=ref_kullan,
                            cancel_token=self.cancel_token,
                            top_p_override=satir_top_p,
                            top_k_override=satir_top_k,
                        )

                        if self._durdur_istegi or self.cancel_token.is_cancelled or self.motor.durdur_istegi:
                            self.satir_durum_sinyali.emit(idx, "⏹️ Durduruldu", akustik, "", "")
                            break

                        if ok_tek:
                            basarili_sayac += 1
                            if grup_id:
                                grup_uretilen_dosyalar[grup_id].append(str(tek_hedef))
                            cp.kayit_guncelle(job_hash, item_id, parmak_izi, "tamamlandi", str(tek_hedef), "")
                            self.satir_durum_sinyali.emit(idx, "✅ Tamamlandı", akustik, str(tek_hedef), "")
                        else:
                            hatali_sayac += 1
                            gercek_hata = self.motor.son_hata_mesaji or "Sentez başarısız"
                            cp.kayit_guncelle(job_hash, item_id, parmak_izi, "hatali", hata_mesaji=gercek_hata)
                            self.satir_durum_sinyali.emit(idx, f"❌ Hata: {gercek_hata[:38]}", akustik, "", "")

                    islenen_sayac += 1
                    yuzde_str = f"%{int(round((islenen_sayac / max(1, toplam_hedef)) * 100))}"
                    self.ilerleme_sinyali.emit(islenen_sayac, toplam_hedef, yuzde_str)

                except Exception as satir_hatasi:
                    hatali_sayac += 1
                    islenen_sayac += 1
                    hata_kisa = str(satir_hatasi)
                    self.log_sinyali.emit(f"⚠️ Satır {idx + 1} hatası: {hata_kisa}")
                    self.satir_durum_sinyali.emit(idx, f"❌ Hata: {hata_kisa[:38]}", "", "", "")
                    yuzde_str = f"%{int(round((islenen_sayac / max(1, toplam_hedef)) * 100))}"
                    self.ilerleme_sinyali.emit(islenen_sayac, toplam_hedef, yuzde_str)

            if (
                self.gruplari_birlestir
                and not self._durdur_istegi
                and not self.cancel_token.is_cancelled
                and islenen_grup_idleri
            ):
                bosluk_ms = int(preset.get("birlesik_bosluk_ms", 400))
                birlesik_ad = "diyalog_tamami.mp3" if self.mod_kodu == "diyalog" else "tamami.mp3"

                for g_id in sorted(islenen_grup_idleri):
                    grup_klasor = guvenli_hedef_yol_cozumle(mod_alt_klasor, g_id)
                    if not grup_klasor.exists():
                        continue

                    # Önce bu çalıştırmada bu gruba ait üretilen/doğrulanan dosyaları al
                    mevcut_parcalar = [
                        p for p in grup_uretilen_dosyalar.get(g_id, [])
                        if os.path.exists(p) and os.path.getsize(p) > 800
                    ]
                    if len(mevcut_parcalar) < 2:
                        mevcut_parcalar = sorted(
                            [
                                str(p) for p in grup_klasor.iterdir()
                                if p.is_file()
                                and p.name != birlesik_ad
                                and p.suffix.lower() in (".mp3", ".wav")
                                and p.stat().st_size > 800
                            ]
                        )
                    if len(mevcut_parcalar) >= 2:
                        birlesik_hedef = grup_klasor / birlesik_ad
                        if sesleri_studyo_kalitesinde_birlestir(
                            girdi_dosyalari=mevcut_parcalar,
                            cikti_dosyasi=birlesik_hedef,
                            bosluk_ms=bosluk_ms,
                            mikro_fade_ms=25,
                            birlestirilmis_seviye_dengele=True,
                        ):
                            birlestirilen_grup_sayac += 1

        except Exception as genel_hata:
            self.hata_sinyali.emit(f"Toplu işlem hatası: {genel_hata}")
            self.log_sinyali.emit(f"❌ Toplu işlem genel hatası: {genel_hata}")
        finally:
            gecen = round(time.time() - baslangic_zaman, 1)
            durduruldu_mu = bool(
                self._durdur_istegi
                or self.cancel_token.is_cancelled
                or (self.motor is not None and self.motor.durdur_istegi)
            )
            ozet = {
                "toplam": toplam_hedef,
                "basarili": basarili_sayac,
                "atlanan": atlanan_sayac,
                "hatali": hatali_sayac,
                "birlestirilen_grup": birlestirilen_grup_sayac,
                "gecen_saniye": gecen,
                "durduruldu_mu": durduruldu_mu,
            }
            self.tamamlandi_sinyali.emit(ozet)