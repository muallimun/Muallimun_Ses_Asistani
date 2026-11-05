#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MUALLİMUN AI SES STÜDYOSU PRO - REHBER, TAM KAPSAMLI OTOMATİK HAREKELEME, PARAMETRE BİLGİ KARTLARI VE GÜNCELLEYİCİ
Dosya: ui/rehber_ve_guncelleyici.py
Özellikler:
  1. Profesyonel Arapça Font Seçici (Amiri / Scheherazade / Mushaf / Simplified Arabic) ve Oturum Font Boyutu Hafızası
  2. Oturum Boyunca Hareke Uyarısını Susturma ('☐ Bu oturum boyunca bir daha gösterme' — Yeniden Başlatınca Sıfırlanır)
  3. Vasıl Hemzesi ve Med Harfi Korumalı Hassas Hareke Analizcisi + 2 Aşamalı Hibrit Harekeleme Motoru (Önbellek & Devre Kesicili)
  4. 3. Sekmedeki 18+ İnce Ayar İçin Renkli, Anlaşılır 'ParametreBilgiDialog' (ℹ️ Info Penceresi)
  5. Büyük Puntolu, Kart Tasarımlı 6 Sekmeli Kullanım Kılavuzu ve GitHub Otomatik Versiyon Kontrolü
"""

import os
import re
import time
import uuid
import json
import shutil
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QComboBox,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QStackedWidget,
    QLineEdit,
    QFileDialog,
    QMessageBox,
)

from core.config_manager import ConfigManager, PROJECT_ROOT
from core.studyo_motoru import (
    gpu_vram_durumu_getir,
    arapca_harekeleri_soy,
    hareke_siralamasini_normallestir,
)

APP_VERSION = "1.2.0"
VARSAYILAN_GITHUB_REPO = "muallimun/Muallimun_Ses_Asistani"

# ==============================================================================
# OTURUM (SESSION) BELLEĞİ DEĞİŞKENLERİ
# (Diske kaydedilmez; uygulama kapatılıp yeniden açıldığında varsayılana döner)
# ==============================================================================
_OTURUMDA_HAREKE_UYARISI_GOSTERME: bool = False
_OTURUM_ARAPCA_FONT_BOYUTU: int = 24
_SECILEN_ARAPCA_FONT_AILESI: Optional[str] = None


def oturumda_hareke_uyarisi_aktif_mi() -> bool:
    """Kullanıcı 'Bu oturum boyunca bir daha gösterme' seçmediyse True döndürür."""
    return not _OTURUMDA_HAREKE_UYARISI_GOSTERME


def oturumda_hareke_uyarisini_sustur(sustur: bool = True) -> None:
    """Aktif uygulama oturumu boyunca hareke uyarı penceresini susturur veya açar."""
    global _OTURUMDA_HAREKE_UYARISI_GOSTERME
    _OTURUMDA_HAREKE_UYARISI_GOSTERME = bool(sustur)


def oturum_arapca_font_boyutu_getir() -> int:
    """Oturum boyunca seçilen Arapça metin yazı boyutunu döndürür."""
    return _OTURUM_ARAPCA_FONT_BOYUTU


def oturum_arapca_font_boyutu_ayarla(yeni_boyut: int) -> int:
    """Arapça metin yazı boyutunu 14 pt ile 44 pt arasında sınırlandırarak oturum belleğine kaydeder."""
    global _OTURUM_ARAPCA_FONT_BOYUTU
    _OTURUM_ARAPCA_FONT_BOYUTU = max(14, min(44, int(yeni_boyut)))
    return _OTURUM_ARAPCA_FONT_BOYUTU


def profesyonel_arapca_font_ailesi_bul() -> str:
    """
    Sistemde yüklü olan en net, harekeleri birbirine karıştırmayan Mushaf / Amiri / Naskh
    kalitesindeki Arapça font ailesini tespit eder.
    """
    global _SECILEN_ARAPCA_FONT_AILESI
    if _SECILEN_ARAPCA_FONT_AILESI:
        return _SECILEN_ARAPCA_FONT_AILESI

    oncelikli_fontlar = [
        "Amiri",
        "Amiri Quran",
        "Scheherazade New",
        "Scheherazade",
        "Noto Naskh Arabic",
        "KFGQPC Uthman Taha Naskh",
        "UthmanicHafs",
        "Sakkal Majalla",
        "Arabic Typesetting",
        "Simplified Arabic",
        "Dubai",
        "Segoe UI",
        "Traditional Arabic",
    ]
    try:
        mevcut_aileler = {f.lower(): f for f in QFontDatabase.families()}
        for aday in oncelikli_fontlar:
            if aday.lower() in mevcut_aileler:
                _SECILEN_ARAPCA_FONT_AILESI = mevcut_aileler[aday.lower()]
                return _SECILEN_ARAPCA_FONT_AILESI
    except Exception:
        pass

    _SECILEN_ARAPCA_FONT_AILESI = "Simplified Arabic"
    return _SECILEN_ARAPCA_FONT_AILESI


def profesyonel_arapca_font_olustur(punto: Optional[int] = None, kalin: bool = False) -> QFont:
    """
    Harekeli Arapça metinlerde harflerin ve harekelerin çakışmaması için
    yüksek okunabilirlikli ve anti-alias destekli QFont nesnesi oluşturur.
    """
    aile = profesyonel_arapca_font_ailesi_bul()
    boyut = int(punto) if punto is not None else _OTURUM_ARAPCA_FONT_BOYUTU
    font = QFont(aile, boyut)
    if kalin:
        font.setBold(True)
    font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
    font.setLetterSpacing(QFont.PercentageSpacing, 103.0)
    return font


# ==============================================================================
# 0. 3. SEKMEDEKİ 18+ İNCE AYAR İÇİN ANLAŞILIR BİLGİ REHBERİ VE RENKLİ PENCERE
# ==============================================================================
DSP_VE_PRESET_PARAMETRE_REHBERI: Dict[str, Dict[str, str]] = {
    "preset_modu": {
        "baslik": "🎛️ Düzenlenecek İçerik Modu (Preset)",
        "kategori": "Genel Mod Seçimi",
        "ozet": "Hangi içerik türünün (Tek Kelime, Cümle, Atasözü, Diyalog veya Uzun Metin) ses ve filtre ayarlarını düzenleyeceğinizi seçer.",
        "ne_ise_yarar": (
            "Uygulamadaki 5 içerik türünün her biri farklı okuma hızı ve ses temizleme ayarlarına sahiptir. "
            "Örneğin 'Tek Kelime' modu daha tane tane ve net okurken, 'Diyalog' modu daha canlı ve akıcı okur."
        ),
        "artirilirsa": "Seçtiğiniz modun kayıtlı ayarları ekrana yüklenir.",
        "azaltilirsa": "'Seçili Modu Fabrika Ayarlarına Sıfırla' butonuyla ilk kurulum değerlerine dönebilirsiniz.",
        "onerilen": "Düzenlemek istediğiniz içerik türünü seçip alttaki 'Kaydet' butonuna basın.",
    },
    "hiz": {
        "baslik": "⚡ Okuma Hızı (Atempo / Speed)",
        "kategori": "1. Neural Sentez ve Tempo",
        "ozet": "Seslendirmenin ne kadar hızlı veya yavaş okunacağını belirler (Sesin kalınlığını/inceliğini bozmaz).",
        "ne_ise_yarar": (
            "Arapça ders materyallerinde öğrencilerin harfleri ve harekeleri rahatça duyabilmesi için konuşma hızını ayarlar. "
            "0.89x – 0.96x aralığında ses sündürme filtresi devreye girmeden referans konuşmacının en doğal ritmi korunur."
        ),
        "artirilirsa": "Konuşma hızlanır (Örn: 1.05x canlı ve hızlı konuşma sağlar).",
        "azaltilirsa": "Konuşma yavaşlar, kelimeler daha tane tane duyulur (Örn: 0.85x – 0.90x).",
        "onerilen": "Tek Kelime: 0.90 | Cümle: 0.92 | Atasözü: 0.89 | Diyalog: 0.94 | Uzun Metin: 0.92",
    },
    "temperature": {
        "baslik": "🌡️ Sıcaklık (Temperature — Tonlama Doğallığı)",
        "kategori": "1. Neural Sentez ve Tempo",
        "ozet": "Yapay zekanın ses tonlamasındaki duygusal çeşitliliği ve esnekliği kontrol eder.",
        "ne_ise_yarar": (
            "Düşük değerlerde model her kelimeyi düz, ciddi ve standart bir spiker gibi okur. "
            "Yüksek değerlerde ise ses tonu inişli çıkışlı, duygulu ve daha insani olur."
        ),
        "artirilirsa": "Ses daha canlı, coşkulu ve vurgulu çıkar (Ancak 0.78 üstünde telaffuz hataları başlayabilir).",
        "azaltilirsa": "Ses daha sakin, kararlı ve sözlük spikeri gibi net çıkar (0.50 altı sesi mekanikleştirebilir).",
        "onerilen": "Tek Kelime: 0.54 – 0.58 | Cümle: 0.62 – 0.65 | Diyalog: 0.66 – 0.70",
    },
    "top_k": {
        "baslik": "🎯 Top-K Örnekleme (Ses Havuzu Genişliği)",
        "kategori": "1. Neural Sentez ve Tempo",
        "ozet": "Modelin her ses adımında en olası kaç farklı ses tonu arasından seçim yapacağını sınırlar.",
        "ne_ise_yarar": (
            "Yapay zeka sesi oluştururken her milisaniyede yüzlerce olası ses dalgası üretir. "
            "Top-K ayarı, en kaliteli ilk K adet ses adayını tutup geri kalan zayıf adayları eler."
        ),
        "artirilirsa": "Tonlama zenginliği artar, diyaloglar daha doğal duyulur (Örn: 50 – 60).",
        "azaltilirsa": "Model sadece en güvenli sesleri seçer; tek kelimeler çok net okunur (Örn: 30 – 40).",
        "onerilen": "Tek Kelime: 35 – 40 | Cümle ve Metin: 45 – 50 | Diyalog: 50 – 55",
    },
    "top_p": {
        "baslik": "🔮 Top-P / Nucleus (Olasılık Eşiği)",
        "kategori": "1. Neural Sentez ve Tempo",
        "ozet": "Ses üretiminde doğallık ile netlik arasındaki hassas dengeyi kurar.",
        "ne_ise_yarar": (
            "Toplam olasılığı belirlenen yüzdelik dilime (Örn: %94 = 0.94) ulaşan en güçlü ses dalgalarını seçer. "
            "Sıcaklık (Temperature) ayarıyla birlikte çalışarak sesin pürüzsüz çıkmasını sağlar."
        ),
        "artirilirsa": "Ses geçişleri daha esnek ve teatral olur (0.94 – 0.96).",
        "azaltilirsa": "Ses daha kontrollü, sade ve ders odaklı olur (0.85 – 0.90).",
        "onerilen": "Tek Kelime: 0.88 – 0.90 | Cümle: 0.92 – 0.94 | Diyalog: 0.95",
    },
    "min_tokens": {
        "baslik": "📏 Min Yeni Token (En Kısa Ses Uzunluğu Sınırı)",
        "kategori": "1. Neural Sentez ve Tempo",
        "ozet": "Modelin cümleyi yarıda kesip erken susmasını önleyen alt güvenlik sınırıdır.",
        "ne_ise_yarar": (
            "Bazen yapay zeka uzun bir cümlenin ilk birkaç kelimesinden sonra cümle bitti sanıp durabilir. "
            "Min Token ayarı, modelin en az bu kadar ses parçası üretmeden durmamasını sağlar."
        ),
        "artirilirsa": "Uzun cümlelerin erken kesilmesi önlenir.",
        "azaltilirsa": "Tek kelimelerin ve kısa repliklerin biter bitmez hemen durmasını sağlar.",
        "onerilen": "Tek Kelime: 12 – 15 | Cümle ve Diyalog: 25 | Uzun Metin: 30",
    },
    "max_tokens": {
        "baslik": "📐 Maks Yeni Token (En Uzun Ses Bütçesi)",
        "kategori": "1. Neural Sentez ve Tempo",
        "ozet": "Tek bir cümlenin alabileceği en yüksek ses uzunluğu kapasitesidir.",
        "ne_ise_yarar": (
            "Uzun Arapça cümlelerin son kelimelerinin yutulmaması için yeterli üst sınır tanımlar; "
            "aynı zamanda ekran kartı belleğinin (VRAM) taşmasını engeller."
        ),
        "artirilirsa": "15-20 kelimelik uzun cümleler bölünmeden tek nefeste tamamlanır (Örn: 650 – 850).",
        "azaltilirsa": "Ekran kartı belleği daha az kullanılır; tek kelimeler için 140 yeterlidir.",
        "onerilen": "Tek Kelime: 140 | Cümle: 550 – 650 | Diyalog: 650 | Uzun Metin: 750",
    },
    "kelime_turu": {
        "baslik": "🕌 Varsayılan Kelime Türü (Vakıf / Durak Kuralı)",
        "kategori": "1. Neural Sentez ve Tempo",
        "ozet": "Kelime veya cümle sonlarında durulurken Arapça vakıf (sükûn) kuralının nasıl uygulanacağını belirler.",
        "ne_ise_yarar": (
            "• 'genel' ve 'isim': Durak sonunda son harekeyi sükûn yapar, yuvarlak tâ'yı (ة) 'h' (هْ) sesine çevirir.\n"
            "• 'fiil': Tekil fiil çekimlerinde (Örn: يَكْتُبُ) son harekenin duyulması istendiğinde harekeyi korur."
        ),
        "artirilirsa": "'isim / genel' seçildiğinde doğal Arapça durak (vakıf) kuralları tam uygulanır.",
        "azaltilirsa": "'fiil' seçildiğinde tek kelimelik fiillerin son harekesi sükûn yapılmaz.",
        "onerilen": "Cümle, Diyalog ve Metinlerde: 'genel' | Tek Kelimede: 'isim' veya 'fiil'",
    },
    "varsayilan_format": {
        "baslik": "💿 Varsayılan Çıktı Formatı (WAV / MP3)",
        "kategori": "1. Neural Sentez ve Tempo",
        "ozet": "Üretilen ses dosyalarının sıkıştırmasız WAV mı yoksa küçük boyutlu MP3 mü olacağını belirler.",
        "ne_ise_yarar": (
            "• WAV: 24kHz 16-bit kayıpsız stüdyo kalitesidir (Dosya boyutu biraz daha büyüktür).\n"
            "• MP3: 192kbps yüksek kaliteli sıkıştırılmış formattır; web siteleri, flipbook ve mobil uygulamalar için idealdir."
        ),
        "artirilirsa": "WAV seçildiğinde sıfır kayıplı ham stüdyo sesi kaydedilir.",
        "azaltilirsa": "MP3 seçildiğinde dosya boyutu %80 küçülür, web ve mobil hızlanır.",
        "onerilen": "Tek Kelime: WAV veya MP3 | Cümle, Diyalog ve Uzun Metin: MP3",
    },
    "birlesik_bosluk_ms": {
        "baslik": "⏱️ Birleştirme Boşluğu (Nefes Süresi — ms)",
        "kategori": "1. Neural Sentez ve Tempo",
        "ozet": "Diyalog replikleri veya uzun metin cümleleri tek dosyada birleştirilirken araya konulan sessizlik süresidir.",
        "ne_ise_yarar": (
            "Cümleler peş peşe eklendiğinde spikerin doğal nefes alması kadar boşluk bırakır. "
            "1000 ms = 1 saniyedir (Örn: 400 ms = saniyenin onda dördü kadar doğal duraksama)."
        ),
        "artirilirsa": "Cümleler ve konuşmacılar arasındaki bekleme süresi uzar, dinleyici cümleyi daha rahat sindirir (Örn: 450 – 600 ms).",
        "azaltilirsa": "Cümleler birbirine daha hızlı bağlanır (Örn: 250 – 300 ms).",
        "onerilen": "Uzun Metin Cümle Arası: 300 – 350 ms | Diyalog Replik Arası: 400 – 500 ms",
    },
    "cift_uretim_erkek_kadin": {
        "baslik": "👨+👩 Varsayılan Çift Üretim (Erkek + Kadın)",
        "kategori": "1. Neural Sentez ve Tempo",
        "ozet": "Toplu seslendirmede her kelime veya cümlenin hem Erkek hem Kadın sesiyle ayrı ayrı üretilmesini sağlar.",
        "ne_ise_yarar": (
            "İşaretli olduğunda toplu üretimde otomatik olarak 'erkek/' ve 'kadin/' klasörleri açılır "
            "ve her kayıt iki farklı karakterle seslendirilir."
        ),
        "artirilirsa": "İşaretlenirse çift üretim aktif olur.",
        "azaltilirsa": "İşaret kaldırılırsa yalnızca seçili tek karakterle üretim yapılır (Süre yarı yarıya kısalır).",
        "onerilen": "Kelime ve Cümle listelerinde: Açık | Diyalog ve Uzun Metinlerde: Kapalı",
    },
    "hikmetli_durak_ekle": {
        "baslik": "🌿 Hikmetli Tefekkür Durağı (،) Ekle",
        "kategori": "1. Neural Sentez ve Tempo",
        "ozet": "Uzun cümlelerde ve atasözlerinde bağlaçlardan önce otomatik kısa nefes durağı ekler.",
        "ne_ise_yarar": (
            "Arapça cümle içindeki 'وَلَا، بَلْ، وَإِنَّمَا' gibi geçiş bağlaçlarından önce "
            "doğal bir virgül durağı koyarak anlam vurgusunu güçlendirir."
        ),
        "artirilirsa": "İşaretlendiğinde atasözleri ve uzun cümleler daha anlamlı ve vakur okunur.",
        "azaltilirsa": "İşaret kaldırıldığında yalnızca sizin yazdığınız noktalama işaretlerinde durulur.",
        "onerilen": "Atasözü ve Uzun Metin modlarında: Açık | Kısa Cümlelerde: İsteğe bağlı",
    },
    "dinamik_tonlama": {
        "baslik": "🎭 Soru / Ünlem Dinamik Tonlama Aktif",
        "kategori": "1. Neural Sentez ve Tempo",
        "ozet": "Cümledeki soru (؟) ve ünlem (!) işaretlerini algılayıp ses tonunu otomatik canlandırır.",
        "ne_ise_yarar": (
            "Tonlama 'Otomatik' seçiliyken cümlenin soru mu, ünlem mi yoksa uzun bir açıklama mı olduğunu "
            "analiz ederek hız ve sıcaklık değerlerini cümleye göre otomatik uyarlar."
        ),
        "artirilirsa": "İşaretli olduğunda soru ve ünlem cümleleri daha doğal bir vurguyla okunur.",
        "azaltilirsa": "İşaret kaldırıldığında tüm cümleler sabit hız ve sıcaklıkla okunur.",
        "onerilen": "Tüm modlarda Açık tutulması önerilir.",
    },
    "hp_freq": {
        "baslik": "🔊 High-Pass (Dip Gürültü Filtresi — Hz)",
        "kategori": "2. 5-Katmanlı Stüdyo DSP Mastering",
        "ozet": "Sesteki kalın dip uğultularını, mikrofon patlamalarını (p/b harfleri) ve boğukluğu temizler.",
        "ne_ise_yarar": (
            "Belirlenen frekansın (Örn: 75–85 Hz) altındaki insan sesine ait olmayan mekanik uğultuları "
            "Butterworth stüdyo filtresiyle keser, sesi berraklaştırır."
        ),
        "artirilirsa": "Ses daha ince ve temiz duyulur (Ancak 130 Hz üstüne çıkılırsa erkek seslerinin bas dolgunluğu azalır).",
        "azaltilirsa": "Erkek sesleri daha bas ve tok çıkar (Ancak 60 Hz altında hafif dip uğultusu kalabilir).",
        "onerilen": "Standart Stüdyo Değeri: 75 Hz – 85 Hz",
    },
    "lp_freq": {
        "baslik": "🔉 Low-Pass (Tiz Parazit Filtresi — Hz)",
        "kategori": "2. 5-Katmanlı Stüdyo DSP Mastering",
        "ozet": "Yapay zeka seslerinde oluşabilen aşırı tiz, metalik cızırtıları yumuşatır.",
        "ne_ise_yarar": (
            "Belirlenen frekansın (Örn: 11200 Hz) üzerindeki kulak tırmalayıcı dijital parazitleri süzerek "
            "sese doğal ve kadifemsi bir stüdyo mikrofonu karakteri kazandırır."
        ),
        "artirilirsa": "S, Ş, الث, الص gibi harflerin tiz parlaklığı artar (11500 Hz).",
        "azaltilirsa": "Metalik tizlik azalır, ses daha yumuşak olur (Ancak 8000 Hz altına inilirse ses boğuklaşır).",
        "onerilen": "Standart Stüdyo Değeri: 11200 Hz – 11500 Hz",
    },
    "gate_esigi": {
        "baslik": "🚪 RMS Gate Eşiği (Nefes ve Arka Plan Gürültü Kapısı)",
        "kategori": "2. 5-Katmanlı Stüdyo DSP Mastering",
        "ozet": "Kelime aralarındaki hafif hışırtıları ve boşluk parazitlerini yumuşakça azaltır.",
        "ne_ise_yarar": (
            "Konuşmacı sustuğu anda devreye girerek arka plandaki ince tıslamayı azaltır. "
            "Arapça kelime sonlarındaki hafif harfleri (هْ، حْ، ثْ، سْ) ve doğal nefesleri yutmamak için yumuşak geçişli çalışır."
        ),
        "artirilirsa": "Kelime araları daha sessiz olur.",
        "azaltilirsa": "Kelime sonundaki en hafif fısıltı harfleri ve doğal nefesler tamamen korunur (0.015 – 0.025).",
        "onerilen": "Cümle ve Diyalog: 0.020 – 0.028 | Tek Kelime: 0.024 – 0.028",
    },
    "aktif_esik_katsayi": {
        "baslik": "✂️ Kırpma / Trim Eşiği (Başlangıç Algılama)",
        "kategori": "2. 5-Katmanlı Stüdyo DSP Mastering",
        "ozet": "Ses dosyasının başındaki gereksiz uzun boşluğu nereden kırpacağını belirler.",
        "ne_ise_yarar": (
            "Yapay zeka ses ürettiğinde başta bazen boşluk bırakabilir. "
            "Bu ayar konuşmanın başladığı tam noktayı bulur; cümle sonu ise son harfin kesilmemesi için çok hassas (0.005) korunur."
        ),
        "artirilirsa": "Başlangıç daha sıkı kırpılır.",
        "azaltilirsa": "Başlangıçtaki nefes alışları korunur.",
        "onerilen": "Standart Stüdyo Değeri: 0.018 – 0.024",
    },
    "bas_pay_ms": {
        "baslik": "⏮️ Başlangıç Payı (Ön Boşluk / Pad — ms)",
        "kategori": "2. 5-Katmanlı Stüdyo DSP Mastering",
        "ozet": "Ses dosyası çalmaya başladığında ilk harfin yutulmaması için en başa bırakılan koruma boşluğudur.",
        "ne_ise_yarar": (
            "Bazı medya oynatıcılar veya web tarayıcıları sesi açarken ilk 20-30 milisaniyeyi yutabilir. "
            "Başlangıç payı, ilk harfin her cihazda net duyulmasını garanti eder."
        ),
        "artirilirsa": "Tuşa basıldıktan sonra ses biraz daha sakin başlar (Örn: 65 – 90 ms).",
        "azaltilirsa": "Tuşa basılır basılmaz ses anında başlar (Örn: 40 – 55 ms).",
        "onerilen": "Tek Kelime: 45 ms | Cümle ve Diyalog: 55 – 65 ms",
    },
    "son_pay_ms": {
        "baslik": "⏭️ Bitiş Payı (Son Vakıf Nefes Payı — ms)",
        "kategori": "2. 5-Katmanlı Stüdyo DSP Mastering",
        "ozet": "Son kelimenin sükûnunun ve yankısının aniden kesilmemesi için dosya sonuna bırakılan doğal paydır.",
        "ne_ise_yarar": (
            "Arapçada vakıf (durak) harflerinin doğal tınısının sönümlenmesi ve yumuşak çıkış (fade-out) için "
            "cümle sonunda rahat bir kapanış süresi bırakır."
        ),
        "artirilirsa": "Cümle sonu daha dingin ve doğal biter, son kelime asla aniden kesilmez (Örn: 240 – 320 ms).",
        "azaltilirsa": "Ses dosyası daha erken kapanır (Örn: 120 – 180 ms).",
        "onerilen": "Tek Kelime: 180 – 220 ms | Cümle ve Metin: 240 – 300 ms",
    },
    "drive": {
        "baslik": "🔥 Tanh Drive (Harmonik Ses Dolgunluğu ve Sıcaklık)",
        "kategori": "2. 5-Katmanlı Stüdyo DSP Mastering",
        "ozet": "Sese hafif radyo/stüdyo mikrofonu sıcaklığı ve dolgunluğu katar.",
        "ne_ise_yarar": (
            "Cılız kalan ses dalgalarını nazikçe güçlendirerek konuşmacının sesini daha tok ve anlaşılır hale getirir. "
            "Anti-aliasing Low-Pass filtreden önce uygulandığı için seste metalik sertlik oluşturmaz."
        ),
        "artirilirsa": "Ses daha tok ve dolgun çıkar (Örn: 1.10 – 1.18).",
        "azaltilirsa": "1.00 yapıldığında hiçbir doygunluk eklenmez, tamamen saf sinyal kalır.",
        "onerilen": "Standart Stüdyo Değeri: 1.05 – 1.12",
    },
    "fade_ms": {
        "baslik": "🌊 Fade In / Out Süresi (Yumuşak Giriş/Çıkış — ms)",
        "kategori": "2. 5-Katmanlı Stüdyo DSP Mastering",
        "ozet": "Ses başlarken ve biterken 'çıt / tık' sesi çıkmasını önleyen yumuşak kosinüs geçişidir.",
        "ne_ise_yarar": (
            "Sesin girişini yumuşatır; cümle çıkışında ise son kelimenin doğal sönümlenmesi için "
            "kosinüs eğrisi (Raised-Cosine Fade-Out) otomatik uygulanır."
        ),
        "artirilirsa": "Giriş ve çıkış daha yumuşak olur (12 – 20 ms).",
        "azaltilirsa": "Daha hızlı giriş sağlar (8 – 10 ms).",
        "onerilen": "Standart Stüdyo Değeri: 10 ms – 12 ms",
    },
    "tepe_normalizasyon": {
        "baslik": "📊 Tepe Normalizasyon (Standart Ses Yüksekliği Sınırı)",
        "kategori": "2. 5-Katmanlı Stüdyo DSP Mastering",
        "ozet": "Üretilen tüm ses dosyalarının aynı standart ses yüksekliğinde (seviyesinde) çıkmasını sağlar.",
        "ne_ise_yarar": (
            "0.891 değeri profesyonel yayıncılıkta '-1.0 dBFS' tavanına karşılık gelir. "
            "Böylece ne çok kısık ne de hoparlörü patlatacak kadar yüksek ses oluşur."
        ),
        "artirilirsa": "Genel ses yüksekliği biraz daha artar (0.95 üstü MP3 dönüşümünde kırpılma yapabilir).",
        "azaltilirsa": "Genel ses yüksekliği daha sakin olur (Örn: 0.80).",
        "onerilen": "Standart Stüdyo Değeri: 0.891 (-1.0 dBFS)",
    },
    "varsayilan_cikti_klasoru": {
        "baslik": "📁 Varsayılan Çıktı Klasörü ve Otomatik Oynatma",
        "kategori": "3. Genel Klasör ve Oynatma Tercihleri",
        "ozet": "Üretilen tüm ses dosyalarının bilgisayarınızda kaydedileceği ana klasörü belirler.",
        "ne_ise_yarar": (
            "Tekli stüdyo, toplu seslendirme, diyaloglar ve uzun metinler bu ana klasörün altındaki "
            "düzenli alt klasörlere ('tekli_studyo/', 'diyaloglar/', 'metinler/') kaydedilir."
        ),
        "artirilirsa": "'Gözat...' butonuyla farklı bir disk veya klasör seçebilirsiniz.",
        "azaltilirsa": "'Toplu İşlem Bitince Son Sesi Otomatik Çal' kutusuyla bitiş uyarısını açıp kapatabilirsiniz.",
        "onerilen": "Proje içindeki 'cikti_sesler' klasörü veya Masaüstünüzdeki özel bir klasör.",
    },
}


class ParametreBilgiDialog(QDialog):
    """
    3. Sekmedeki (Stüdyo DSP & Preset İnce Ayar) 18+ parametrenin yanındaki ℹ️ ikonuna
    tıklandığında açılan, renkli ve anlaşılır bilgi penceresi.
    """
    def __init__(self, secili_anahtar: str = "hiz", koyu_tema: bool = True, parent=None):
        super().__init__(parent)
        self.koyu_tema = koyu_tema
        self.setWindowTitle("ℹ️ Stüdyo İnce Ayar ve DSP Parametre Rehberi (Anlaşılır Açıklamalar)")
        self.setMinimumSize(700, 470)
        self.resize(750, 510)
        self.setStyleSheet(studyo_tema_qss_olustur("koyu" if koyu_tema else "aydinlik"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        ust_bar = QHBoxLayout()
        lbl_sec = QLabel("🔍 <b>İncelemek İstediğiniz Ayar:</b>")
        ust_bar.addWidget(lbl_sec)

        self.cmb_parametre = QComboBox()
        for k, v in DSP_VE_PRESET_PARAMETRE_REHBERI.items():
            self.cmb_parametre.addItem(f"{v['baslik']}  —  [{v['kategori']}]", k)
        idx = self.cmb_parametre.findData(secili_anahtar)
        if idx >= 0:
            self.cmb_parametre.setCurrentIndex(idx)
        self.cmb_parametre.currentIndexChanged.connect(self._icerigi_guncelle)
        ust_bar.addWidget(self.cmb_parametre, stretch=1)
        layout.addLayout(ust_bar)

        self.tarayici = QTextBrowser()
        self.tarayici.setOpenExternalLinks(True)
        layout.addWidget(self.tarayici, stretch=1)

        alt_bar = QHBoxLayout()
        lbl_not = QLabel("💡 İpucu: Üstteki açılır listeden diğer tüm ince ayarların ne işe yaradığına da bakabilirsiniz.")
        lbl_not.setStyleSheet("color: #64748b; font-size: 9pt;")
        alt_bar.addWidget(lbl_not)
        alt_bar.addStretch()

        btn_kapat = QPushButton("Anladım / Kapat")
        btn_kapat.setFixedHeight(34)
        btn_kapat.setStyleSheet("background-color: #0284c7; color: white; padding: 6px 18px; font-weight: bold;")
        btn_kapat.clicked.connect(self.accept)
        alt_bar.addWidget(btn_kapat)
        layout.addLayout(alt_bar)

        self._icerigi_guncelle()

    def _icerigi_guncelle(self) -> None:
        anahtar = self.cmb_parametre.currentData() or "hiz"
        bilgi = DSP_VE_PRESET_PARAMETRE_REHBERI.get(anahtar, DSP_VE_PRESET_PARAMETRE_REHBERI["hiz"])

        kart_bg = "#111827" if self.koyu_tema else "#ffffff"
        kart_border = "#1e293b" if self.koyu_tema else "#cbd5e1"
        artir_bg = "#064e3b" if self.koyu_tema else "#d1fae5"
        artir_fg = "#ecfdf5" if self.koyu_tema else "#065f46"
        azalt_bg = "#1e3a8a" if self.koyu_tema else "#dbeafe"
        azalt_fg = "#e0f2fe" if self.koyu_tema else "#1e3a8a"
        oneri_bg = "#451a03" if self.koyu_tema else "#fef3c7"
        oneri_fg = "#fde68a" if self.koyu_tema else "#92400e"

        html = f"""
        <div style='font-family: "Segoe UI", sans-serif; font-size: 11pt; line-height: 1.65; padding: 4px;'>
            <div style='background-color: #0284c7; color: white; padding: 12px 16px; border-radius: 8px; margin-bottom: 12px;'>
                <div style='font-size: 9pt; opacity: 0.9;'>{bilgi['kategori']}</div>
                <div style='font-size: 14pt; font-weight: bold;'>{bilgi['baslik']}</div>
            </div>

            <div style='background-color: {kart_bg}; border: 1px solid {kart_border}; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px;'>
                <div style='color: #10b981; font-weight: bold; font-size: 11.5pt; margin-bottom: 4px;'>🎯 Kısaca Ne İşe Yarar?</div>
                <div><b>{bilgi['ozet']}</b></div>
                <p style='margin-top: 8px; margin-bottom: 2px;'>{bilgi['ne_ise_yarar']}</p>
            </div>

            <table width='100%' cellspacing='8' cellpadding='0' style='margin-bottom: 8px;'>
                <tr>
                    <td width='50%' style='background-color: {artir_bg}; color: {artir_fg}; border: 1px solid #10b981; border-radius: 8px; padding: 12px;'>
                        <div style='font-weight: bold; font-size: 11pt; margin-bottom: 4px;'>📈 Değeri Artırırsanız / Açarsanız:</div>
                        <div>{bilgi['artirilirsa']}</div>
                    </td>
                    <td width='50%' style='background-color: {azalt_bg}; color: {azalt_fg}; border: 1px solid #38bdf8; border-radius: 8px; padding: 12px;'>
                        <div style='font-weight: bold; font-size: 11pt; margin-bottom: 4px;'>📉 Değeri Azaltırsanız / Kapatırsanız:</div>
                        <div>{bilgi['azaltilirsa']}</div>
                    </td>
                </tr>
            </table>

            <div style='background-color: {oneri_bg}; color: {oneri_fg}; border: 1px solid #f59e0b; border-radius: 8px; padding: 10px 14px;'>
                <b>⭐ Önerilen Stüdyo Değeri:</b> {bilgi['onerilen']}
            </div>
        </div>
        """
        self.tarayici.setHtml(html)


# ==============================================================================
# 1. HASSAS ARAPÇA HAREKE ANALİZCİSİ VE 2 AŞAMALI TAM HAREKELEME MOTORU
# ==============================================================================
ARAPCA_HARF_REGEX = re.compile(r"[\u0621-\u063A\u0641-\u064A]")
ARAPCA_HAREKE_REGEX = re.compile(r"[\u064B-\u0652\u0670]")
HARF_VE_HAREKE_CIFT_REGEX = re.compile(r"([\u0621-\u063A\u0641-\u064A])([\u064B-\u0652\u0670]*)")

YEREL_EGITIM_HAREKE_SOZLUGU: Dict[str, str] = {
    "بداية": "بِدَايَةً",
    "لابد": "لَا بُدَّ",
    "بد": "بُدَّ",
    "تعلم": "تَعْلَمَ",
    "يتعلم": "يَتَعَلَّمُ",
    "العرب": "الْعَرَبَ",
    "عرب": "عَرَبٌ",
    "عندهم": "عِنْدَهُمْ",
    "عنده": "عِنْدَهُ",
    "عندها": "عِنْدَهَا",
    "عندك": "عِنْدَكَ",
    "عندي": "عِنْدِي",
    "لغة": "لُغَةٌ",
    "اللغة": "اللُّغَةُ",
    "رسمية": "رَسْمِيَّةٌ",
    "الرسمية": "الرَّسْمِيَّةِ",
    "وهي": "وَهِيَ",
    "وهو": "وَهُوَ",
    "فهي": "فَهِيَ",
    "فهو": "فَهُوَ",
    "الفصيحة": "الْفَصِيحَةُ",
    "فصيحة": "فَصِيحَةٌ",
    "الفصحى": "الْفُصْحَى",
    "العربية": "الْعَرَبِيَّةُ",
    "عربية": "عَرَبِيَّةٌ",
    "تستخدم": "تُسْتَخْدَمُ",
    "وتستخدم": "وَتُسْتَخْدَمُ",
    "يستخدم": "يُسْتَخْدَمُ",
    "الأوراق": "الْأَوْرَاقِ",
    "الاوراق": "الْأَوْرَاقِ",
    "أوراق": "أَوْرَاقٌ",
    "اوراق": "أَوْرَاقٌ",
    "ورقة": "وَرَقَةٌ",
    "امتطى": "امْتَطَى",
    "رجلان": "رَجُلَانِ",
    "حصانا": "حِصَانًا",
    "فعلى": "فَعَلَى",
    "أحدهما": "أَحَدِهِمَا",
    "احدهما": "أَحَدِهِمَا",
    "الخلف": "الْخَلْفِ",
    "شيئان": "شَيْئَانِ",
    "تعرف": "تَعْرِفُ",
    "فضلهما": "فَضْلَهُمَا",
    "إلا": "إِلَّا",
    "الا": "إِلَّا",
    "حين": "حِينَ",
    "تفقدهما": "تَفْقِدُهُمَا",
    "الشباب": "الشَّبَابُ",
    "والعافية": "وَالْعَافِيَةُ",
    "العافية": "الْعَافِيَةُ",
    "السلام": "اَلسَّلَامُ",
    "عليكم": "عَلَيْكُمْ",
    "وعليكم": "وَعَلَيْكُمُ",
    "ورحمة": "وَرَحْمَةُ",
    "الله": "اللَّهِ",
    "وبركاته": "وَبَرَكَاتُهُ",
    "صباح": "صَبَاحُ",
    "الخير": "الْخَيْرِ",
    "النور": "النُّورِ",
    "مساء": "مَسَاءُ",
    "مرحبا": "مَرْحَبًا",
    "اهلا": "أَهْلًا",
    "أهلا": "أَهْلًا",
    "وسهلا": "وَسَهْلًا",
    "شكرا": "شُكْرًا",
    "جزيلا": "جَزِيلًا",
    "عفوا": "عَفْوًا",
    "نعم": "نَعَمْ",
    "لا": "لَا",
    "من": "مِنْ",
    "فضلك": "فَضْلِكَ",
    "تفضل": "تَفَضَّلْ",
    "تفضلي": "تَفَضَّلِي",
    "تشرفت": "تَشَرَّفْتُ",
    "بمعرفتك": "بِمَعْرِفَتِكَ",
    "انا": "أَنَا",
    "أنا": "أَنَا",
    "انت": "أَنْتَ",
    "أنت": "أَنْتَ",
    "انتم": "أَنْتُمْ",
    "أنتم": "أَنْتُمْ",
    "هو": "هُوَ",
    "هي": "هِيَ",
    "هم": "هُمْ",
    "نحن": "نَحْنُ",
    "هذا": "هَذَا",
    "هذه": "هَذِهِ",
    "ذلك": "ذَلِكَ",
    "ولذلك": "وَلِذَلِكَ",
    "تلك": "تِلْكَ",
    "هؤلاء": "هَؤُلَاءِ",
    "الذي": "الَّذِي",
    "التي": "الَّتِي",
    "الذين": "الَّذِينَ",
    "هل": "هَلْ",
    "ما": "مَا",
    "ماذا": "مَاذَا",
    "لماذا": "لِمَاذَا",
    "كيف": "كَيْفَ",
    "اين": "أَيْنَ",
    "أين": "أَيْنَ",
    "متى": "مَتَى",
    "كم": "كَمْ",
    "في": "فِي",
    "الى": "إِلَى",
    "إلى": "إِلَى",
    "على": "عَلَى",
    "عن": "عَنْ",
    "مع": "مَعَ",
    "بين": "بَيْنَ",
    "تحت": "تَحْتَ",
    "فوق": "فَوْقَ",
    "امام": "أَمَامَ",
    "أمام": "أَمَامَ",
    "خلف": "خَلْفَ",
    "عند": "عِنْدَ",
    "منذ": "مُنْذُ",
    "حتى": "حَتَّى",
    "ان": "أَنْ",
    "أن": "أَنْ",
    "إن": "إِنَّ",
    "أنّ": "أَنَّ",
    "إنّ": "إِنَّ",
    "انما": "إِنَّمَا",
    "لكن": "لَكِنَّ",
    "كل": "كُلُّ",
    "جميع": "جَمِيعِ",
    "بعض": "بَعْضُ",
    "غير": "غَيْرُ",
    "دون": "دُونَ",
    "مثل": "مِثْلَ",
    "مثلك": "مِثْلَكِ",
    "يا": "يَا",
    "ايها": "أَيُّهَا",
    "أيها": "أَيُّهَا",
    "الآن": "الْآنَ",
    "اليوم": "الْيَوْمَ",
    "غدا": "غَدًا",
    "امس": "أَمْسِ",
    "أمس": "أَمْسِ",
    "جدا": "جِدًّا",
    "كثيرا": "كَثِيرًا",
    "قليلا": "قَلِيلًا",
    "دائما": "دَائِمًا",
    "ايضا": "أَيْضًا",
    "أيضا": "أَيْضًا",
    "هنا": "هُنَا",
    "هناك": "هُنَاكَ",
    "علم": "عِلْمٌ",
    "العلم": "اَلْعِلْمُ",
    "علوم": "عُلُومٌ",
    "العلوم": "الْعُلُومُ",
    "العلمية": "الْعِلْمِيَّةِ",
    "نور": "نُورٌ",
    "نافع": "نَافِعٌ",
    "ضار": "ضَارٌّ",
    "الجهل": "الْجَهْلُ",
    "كتاب": "كِتَابٌ",
    "الكتاب": "الْكِتَابُ",
    "كتابي": "كِتَابِي",
    "كتابك": "كِتَابُكَ",
    "الكتب": "الْكُتُبِ",
    "معجم": "مُعْجَمٌ",
    "معجما": "مُعْجَمًا",
    "المعجم": "الْمُعْجَمُ",
    "القواعد": "الْقَوَاعِدِ",
    "مدرسة": "مَدْرَسَةٌ",
    "المدرسة": "الْمَدْرَسَةُ",
    "صف": "صَفٌّ",
    "الصف": "الصَّفُّ",
    "الصفحة": "الصَّفْحَةَ",
    "الدرس": "الدَّرْسَ",
    "مكتب": "مَكْتَبٌ",
    "المكتب": "الْمَكْتَبِ",
    "مكتبة": "مَكْتَبَةٌ",
    "المكتبة": "الْمَكْتَبَةِ",
    "المكتبات": "الْمَكْتَبَاتُ",
    "قلم": "قَلَمٌ",
    "القلم": "الْقَلَمُ",
    "دفتر": "دَفْتَرٌ",
    "حقيبة": "حَقِيبَةٌ",
    "الحقيبة": "الْحَقِيبَةُ",
    "كرسي": "كُرْسِيٌّ",
    "الكرسي": "الْكُرْسِيِّ",
    "طاولة": "طَاوِلَةٌ",
    "باب": "بَابٌ",
    "أبواب": "أَبْوَابَ",
    "ابواب": "أَبْوَابَ",
    "نافذة": "نَافِذَةٌ",
    "معلم": "مُعَلِّمٌ",
    "المعلم": "الْمُعَلِّمُ",
    "معلمة": "مُعَلِّمَةٌ",
    "المعلمة": "الْمُعَلِّمَةُ",
    "استاذ": "أُسْتَاذٌ",
    "أستاذ": "أُسْتَاذٌ",
    "استاذي": "أُسْتَاذِي",
    "أستاذي": "أُسْتَاذِي",
    "طالب": "طَالِبٌ",
    "الطالب": "الطَّالِبُ",
    "طالبة": "طَالِبَةٌ",
    "الطلاب": "الطُّلَّابُ",
    "طلابي": "طُلَّابِي",
    "تلميذ": "تِلْمِيذٌ",
    "صديق": "صَدِيقٌ",
    "صديقي": "صَدِيقِي",
    "اسرة": "أُسْرَةٌ",
    "أسرة": "أُسْرَةٌ",
    "اب": "أَبٌ",
    "أب": "أَبٌ",
    "ابي": "أَبِي",
    "أبي": "أَبِي",
    "ام": "أُمٌّ",
    "أم": "أُمٌّ",
    "امي": "أُمِّي",
    "أمي": "أُمِّي",
    "اخ": "أَخٌ",
    "أخ": "أَخٌ",
    "اخت": "أُخْتٌ",
    "أخت": "أُخْتٌ",
    "ابن": "اِبْنٌ",
    "ابنتي": "ابْنَتِي",
    "بنت": "بِنْتٌ",
    "ولد": "وَلَدٌ",
    "الولد": "الْوَلَدُ",
    "طفل": "طِفْلٌ",
    "الاطفال": "الْأَطْفَالُ",
    "الأطفال": "الْأَطْفَالُ",
    "رجل": "رَجُلٌ",
    "امرأة": "اِمْرَأَةٌ",
    "انسان": "إِنْسَانٌ",
    "الإنسان": "الْإِنْسَانِ",
    "بيت": "بَيْتٌ",
    "البيت": "الْبَيْتُ",
    "منزل": "مَنْزِلٌ",
    "غرفة": "غُرْفَةٌ",
    "مدينة": "مَدِينَةٌ",
    "المدينة": "الْمَدِينَةِ",
    "قرية": "قَرْيَةٌ",
    "مسجد": "مَسْجِدٌ",
    "المسجد": "الْمَسْجِدِ",
    "سوق": "سُوقٌ",
    "السوق": "السُّوقِ",
    "مطار": "مَطَارٌ",
    "المطار": "الْمَطَارُ",
    "طريق": "طَرِيقَ",
    "الحياة": "الْحَيَاةِ",
    "القراءة": "الْقِرَاءَةُ",
    "المستمرة": "الْمُسْتَمِرَّةُ",
    "المعرفة": "الْمَعْرِفَةِ",
    "الحكمة": "الْحِكْمَةِ",
    "القرآن": "الْقُرْآنَ",
    "الكريم": "الْكَرِيمَ",
    "التراث": "التُّرَاثَ",
    "الإسلامي": "الْإِسْلَامِيَّ",
    "الإسلامية": "الْإِسْلَامِيَّةِ",
    "الحضارة": "الْحَضَارَةِ",
    "الوقت": "اَلْوَقْتُ",
    "ثمين": "ثَمِينٌ",
    "النجاح": "النَّجَاحُ",
    "الصبر": "الصَّبْرِ",
    "العمل": "الْعَمَلِ",
    "الناس": "النَّاسُ",
    "خير": "خَيْرُ",
    "بخير": "بِخَيْرٍ",
    "الحمد": "الْحَمْدُ",
    "لله": "لِلَّهِ",
    "حالك": "حَالُكَ",
    "حالكم": "حَالُكُمْ",
    "اسمك": "اسْمُكَ",
    "اسمي": "اِسْمِي",
    "عمر": "عُمَرُ",
    "علي": "عَلِيٌّ",
    "احمد": "أَحْمَدُ",
    "أحمد": "أَحْمَدُ",
    "محمد": "مُحَمَّدٌ",
    "فاطمة": "فَاطِمَةُ",
    "ليلى": "لَيْلَى",
    "خديجة": "خَدِيجَةُ",
    "زينب": "زَيْنَبُ",
    "تركيا": "تُرْكِيَا",
    "اسطنبول": "إِسْطَنْبُولَ",
    "إسطنبول": "إِسْطَنْبُولَ",
    "قونيا": "قُونِيَا",
    "ذهب": "ذَهَبَ",
    "يذهب": "يَذْهَبُ",
    "تذهب": "تَذْهَبُ",
    "جلس": "جَلَسَ",
    "يجلس": "يَجْلِسُ",
    "كتب": "كَتَبَ",
    "يكتب": "يَكْتُبُ",
    "تكتب": "تَكْتُبُ",
    "قرأ": "قَرَأَ",
    "قرأت": "قَرَأْتَ",
    "يقرأ": "يَقْرَأُ",
    "تقرأ": "تَقْرَأُ",
    "اقرأ": "اقْرَأِ",
    "قال": "قَالَ",
    "يقول": "يَقُولُ",
    "تكلم": "تَكَلَّمَ",
    "يتكلم": "يَتَكَلَّمُ",
    "حب": "حَبَّ",
    "يحب": "يُحِبُّ",
    "تحب": "تُحِبُّ",
    "احب": "أُحِبُّ",
    "أحب": "أُحِبُّ",
    "فتح": "فَتَحَ",
    "افتح": "اِفْتَحِ",
    "يفتح": "يَفْتَحُ",
    "تفتح": "تَفْتَحُ",
    "يضيء": "يُضِيءُ",
    "اريد": "أُرِيدُ",
    "أريد": "أُرِيدُ",
    "تريد": "تُرِيدُ",
    "تريدين": "تُرِيدِينَ",
    "يستطيع": "يَسْتَطِيعُ",
    "يحتاج": "يَحْتَاجُ",
    "وجد": "وَجَدَ",
    "جد": "جَدَّ",
    "زرع": "زَرَعَ",
    "حصد": "حَصَدَ",
    "سار": "سَارَ",
    "وصل": "وَصَلَ",
    "يعلم": "يَعْلَمُ",
    "فهم": "فَهِمَ",
    "يفهم": "يَفْهَمُ",
    "درس": "دَرَسَ",
    "يدرس": "يَدْرُسُ",
    "عمل": "عَمِلَ",
    "يعمل": "يَعْمَلُ",
    "عملها": "عَمَلَهَا",
    "عمله": "عَمَلَهُ",
    "كبير": "كَبِيرٌ",
    "كبيرة": "كَبِيرَةٌ",
    "الكبيرة": "الْكَبِيرَةِ",
    "صغير": "صَغِيرٌ",
    "صغيرة": "صَغِيرَةٌ",
    "جديد": "جَدِيدٌ",
    "جديدا": "جَدِيدًا",
    "الجديد": "الْجَدِيدَ",
    "قديم": "قَدِيمٌ",
    "جميل": "جَمِيلٌ",
    "جميلة": "جَمِيلَةٌ",
    "بعيد": "بَعِيدٌ",
    "بعيدة": "بَعِيدَةٌ",
    "قريب": "قَرِيبٌ",
    "قريبة": "قَرِيبَةٌ",
    "نشيط": "نَشِيطٌ",
    "نشيطة": "نَشِيطَةٌ",
    "ناجحة": "نَاجِحَةً",
    "مفتوح": "مَفْتُوحٌ",
    "مفتوحة": "مَفْتُوحَةٌ",
    "مغلق": "مُغْلَقٌ",
    "مغلقة": "مُغْلَقَةٌ",
    "سريع": "سَرِيعٌ",
    "طويل": "طَوِيلٌ",
    "طويلة": "طَوِيلَةٌ",
    "مفيد": "مُفِيدٌ",
    "مفيدة": "مُفِيدَةً",
    "شامل": "شَامِلٌ",
}

HARFI_CER_LISTESI = {"فِي", "مِنْ", "إِلَى", "عَلَى", "عَنْ", "بِ", "لِ", "كَ", "في", "من", "إلى", "الى", "على", "عن", "فَعَلَى", "فعلى"}
INNE_GRUBU_LISTESI = {"إِنَّ", "أَنَّ", "كَأَنَّ", "لَكِنَّ", "لَعَلَّ", "لَيْتَ", "إن", "أن", "لكن", "لعل"}
NASB_EDATLARI = {"أَنْ", "لَنْ", "كَيْ", "حَتَّى", "أن", "لن", "كي"}


def _kelime_hareke_orani_hesapla(kelime: str, cumle_sonu_mu: bool = False) -> Tuple[int, int, bool]:
    """
    Bir kelimedeki:
      (harekeli_harf_sayisi, hedef_harf_sayisi, son_harf_veya_ic_harf_eksik_mi)
    değerlerini döndürür.
    """
    temiz = kelime.strip(".،؛؟!?,:;…\"'()«»-")
    if not temiz:
        return 0, 0, False

    ciftler = HARF_VE_HAREKE_CIFT_REGEX.findall(temiz)
    if not ciftler:
        return 0, 0, False

    yalin = arapca_harekeleri_soy(temiz)
    el_var = yalin.startswith("ال") and len(ciftler) > 2
    baglacli_el_var = yalin.startswith(("وال", "فال", "بال", "كال")) and len(ciftler) > 3

    vasil_hemzesi_var = (
        len(ciftler) >= 3
        and ciftler[0][0] == "ا"
        and not ciftler[0][1]
        and ("\u0652" in ciftler[1][1] or "\u0651" in ciftler[1][1])
    )

    hedef_harf_sayisi = 0
    harekeli_harf_sayisi = 0
    eksik_var = False

    for idx, (harf, hareke_grubu) in enumerate(ciftler):
        son_harf_mi = (idx == len(ciftler) - 1)
        sonraki_harf = ciftler[idx + 1][0] if (idx + 1 < len(ciftler)) else ""

        if idx in (0, 1) and el_var and harf in ("ا", "ل"):
            continue
        if idx in (1, 2) and baglacli_el_var and harf in ("ا", "ل"):
            continue
        if idx == 0 and vasil_hemzesi_var:
            continue

        if harf in ("ا", "ى", "آ") and not hareke_grubu:
            continue
        if idx > 0 and harf in ("و", "ي") and not hareke_grubu and not son_harf_mi:
            continue

        hedef_harf_sayisi += 1
        gecerli_hareke_var = bool(hareke_grubu and hareke_grubu != "\u0651")

        if gecerli_hareke_var:
            harekeli_harf_sayisi += 1
        else:
            if not (cumle_sonu_mu and son_harf_mi) and sonraki_harf not in ("ا", "ى"):
                eksik_var = True
            elif son_harf_mi and not cumle_sonu_mu:
                eksik_var = True

    return harekeli_harf_sayisi, max(1, hedef_harf_sayisi), eksik_var


def arapca_hareke_analizi_yap(metin: str) -> Dict[str, Any]:
    """
    Hem harf bazlı gerçek hareke oranını hem de son/iç harfi harekesiz bırakılmış
    kelime sayısını hesaplar.
    """
    temiz = str(metin or "").strip()
    if not temiz:
        return {
            "oran": 0,
            "eksik_kelime_sayisi": 0,
            "durum": "bos",
            "etiket": "⚪ Metin Boş",
            "renk": "#64748b",
            "spark_uygun": False,
        }

    kelimeler = [k for k in temiz.split() if ARAPCA_HARF_REGEX.search(k)]
    if not kelimeler:
        return {
            "oran": 0,
            "eksik_kelime_sayisi": 0,
            "durum": "bos",
            "etiket": "⚪ Arapça Harf Yok",
            "renk": "#64748b",
            "spark_uygun": False,
        }

    toplam_harekeli_harf = 0
    toplam_hedef_harf = 0
    eksik_kelime_sayisi = 0

    for idx, klm in enumerate(kelimeler):
        son_klm_mi = (idx == len(kelimeler) - 1) or bool(re.search(r"[.،؛؟!?,:;…]$", klm))
        h_var, h_hedef, klm_eksik = _kelime_hareke_orani_hesapla(klm, cumle_sonu_mu=son_klm_mi)
        toplam_harekeli_harf += h_var
        toplam_hedef_harf += h_hedef
        if klm_eksik or (h_hedef >= 2 and (h_var / float(h_hedef)) < 0.80):
            eksik_kelime_sayisi += 1

    oran = min(100, int(round((toplam_harekeli_harf / float(max(1, toplam_hedef_harf))) * 100)))

    if oran >= 84 and eksik_kelime_sayisi == 0:
        return {
            "oran": oran,
            "eksik_kelime_sayisi": 0,
            "durum": "tam",
            "etiket": f"🟢 Tam Harekeli (%{oran}) — Spark-TTS İçin İdeal",
            "renk": "#10b981",
            "spark_uygun": True,
        }
    elif oran >= 20:
        ek_not = f" ({eksik_kelime_sayisi} kelimede eksik hareke var)" if eksik_kelime_sayisi > 0 else ""
        return {
            "oran": oran,
            "eksik_kelime_sayisi": eksik_kelime_sayisi,
            "durum": "kismi",
            "etiket": f"🟡 Kısmi Harekeli (%{oran}){ek_not} — '✨ Otomatik Harekele'ye Basın",
            "renk": "#f59e0b",
            "spark_uygun": False,
        }
    else:
        return {
            "oran": oran,
            "eksik_kelime_sayisi": eksik_kelime_sayisi,
            "durum": "harekesiz",
            "etiket": f"🔴 Harekesiz Metin (%{oran}) — Spark-TTS İçin Harekeleme Zorunlu!",
            "renk": "#ef4444",
            "spark_uygun": False,
        }


class ArapcaHarekelemeMotoru:
    """
    Eksik Harf Bırakmayan, Önbellekli ve Devre Kesicili (Circuit Breaker)
    2 Aşamalı Hibrit Otomatik Harekeleme Motoru.
    """
    SOZLUK_YOLU = PROJECT_ROOT / "config" / "tashkeel_sozluk.json"
    _MISHKAL_ONBELLEK: Dict[str, str] = {}
    _MISHKAL_ARDISIK_HATA: int = 0
    _MISHKAL_DEVRE_KESICI_BITIS: float = 0.0

    @classmethod
    def kullanici_sozlugunu_yukle(cls) -> Dict[str, str]:
        if cls.SOZLUK_YOLU.exists():
            try:
                with open(cls.SOZLUK_YOLU, "r", encoding="utf-8-sig") as f:
                    veri = json.load(f)
                if isinstance(veri, dict):
                    return veri
            except Exception:
                pass
        return {}

    @classmethod
    def kullanici_sozlugune_ogret(cls, harekesiz_veya_orijinal: str, harekeli_metin: str) -> None:
        sozluk = cls.kullanici_sozlugunu_yukle()
        kelimeler = str(harekeli_metin or "").split()
        degisti = False
        for klm in kelimeler:
            temiz_klm = hareke_siralamasini_normallestir(klm.strip(".،؛؟!?,:;…\"'()«»"))
            h_var, h_hedef, klm_eksik = _kelime_hareke_orani_hesapla(temiz_klm, cumle_sonu_mu=False)
            if not klm_eksik and h_hedef >= 2 and (h_var / float(h_hedef)) >= 0.85:
                anahtar = arapca_harekeleri_soy(temiz_klm)
                if len(anahtar) >= 2 and sozluk.get(anahtar) != temiz_klm:
                    sozluk[anahtar] = temiz_klm
                    degisti = True

        if degisti:
            try:
                cls.SOZLUK_YOLU.parent.mkdir(parents=True, exist_ok=True)
                gecici = cls.SOZLUK_YOLU.with_suffix(f".{uuid.uuid4().hex[:6]}.tmp")
                with open(gecici, "w", encoding="utf-8") as f:
                    json.dump(sozluk, f, ensure_ascii=False, indent=2)
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except OSError:
                        pass
                os.replace(str(gecici), str(cls.SOZLUK_YOLU))
            except Exception:
                pass

    @classmethod
    def _cevrimici_mishkal_harekele(cls, metin: str, zorla: bool = False) -> Optional[str]:
        anahtar = metin.strip()
        if not anahtar:
            return None
        if anahtar in cls._MISHKAL_ONBELLEK:
            return cls._MISHKAL_ONBELLEK[anahtar]

        simdi = time.time()
        if not zorla and simdi < cls._MISHKAL_DEVRE_KESICI_BITIS:
            return None

        try:
            params = urllib.parse.urlencode({"text": anahtar, "action": "TashkeelText"})
            url = f"https://tahadz.com/mishkal/ajaxGet?{params}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": f"MuallimunStudyoPro/{APP_VERSION}", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
                veri = json.loads(raw)
                sonuc = str(veri.get("result", "")).strip()
                cls._MISHKAL_ARDISIK_HATA = 0
                if sonuc and len(ARAPCA_HAREKE_REGEX.findall(sonuc)) > len(ARAPCA_HAREKE_REGEX.findall(anahtar)):
                    norm_sonuc = hareke_siralamasini_normallestir(re.sub(r"\s{2,}", " ", sonuc))
                    if len(cls._MISHKAL_ONBELLEK) >= 256:
                        ilk_k = next(iter(cls._MISHKAL_ONBELLEK))
                        cls._MISHKAL_ONBELLEK.pop(ilk_k, None)
                    cls._MISHKAL_ONBELLEK[anahtar] = norm_sonuc
                    return norm_sonuc
        except Exception:
            cls._MISHKAL_ARDISIK_HATA += 1
            if cls._MISHKAL_ARDISIK_HATA >= 2:
                # Ardışık 2 ağ hatasında 120 saniye boyunca devre kesiciyi aç (toplu işlemleri bekletmez)
                cls._MISHKAL_DEVRE_KESICI_BITIS = time.time() + 120.0
        return None

    @classmethod
    def _eksik_harfleri_tamamla(cls, govde: str, onceki_yalin: str = "", cumle_basi_mi: bool = False) -> str:
        if not govde:
            return govde

        govde = hareke_siralamasini_normallestir(govde)
        kullanici_sozluk = cls.kullanici_sozlugunu_yukle()
        yalin = arapca_harekeleri_soy(govde)

        h_var, h_hedef, klm_eksik = _kelime_hareke_orani_hesapla(govde, cumle_sonu_mu=False)
        if not klm_eksik and h_hedef >= 1 and (h_var / float(h_hedef)) >= 0.90:
            return govde

        if yalin in kullanici_sozluk:
            aday = kullanici_sozluk[yalin]
        elif yalin in YEREL_EGITIM_HAREKE_SOZLUGU:
            aday = YEREL_EGITIM_HAREKE_SOZLUGU[yalin]
        else:
            aday = govde

        ciftler = HARF_VE_HAREKE_CIFT_REGEX.findall(aday)
        if not ciftler:
            return aday

        el_var = yalin.startswith("ال") and len(ciftler) > 2
        vasil_hemzesi_var = (
            len(ciftler) >= 3
            and ciftler[0][0] == "ا"
            and not ciftler[0][1]
            and ("\u0652" in ciftler[1][1] or "\u0651" in ciftler[1][1])
        )
        sonuc_parcalar: List[str] = []

        for i, (harf, mevcut_h) in enumerate(ciftler):
            son_harf_mi = (i == len(ciftler) - 1)
            sonraki_harf = ciftler[i + 1][0] if (i + 1 < len(ciftler)) else ""
            sonraki_med_mi = sonraki_harf in ("ا", "و", "ي", "ى") and (i + 1 < len(ciftler) and not ciftler[i + 1][1])

            if mevcut_h == "\u0651":
                mevcut_h = "\u0651\u064E"

            if mevcut_h and not son_harf_mi:
                sonuc_parcalar.append(harf + mevcut_h)
                continue

            if el_var and i == 0 and harf == "ا":
                sonuc_parcalar.append(harf + ("\u064E" if cumle_basi_mi else ""))
                continue
            if el_var and i == 1 and harf == "ل":
                sonuc_parcalar.append(harf + (mevcut_h or "\u0652"))
                continue
            if vasil_hemzesi_var and i == 0:
                sonuc_parcalar.append(harf)
                continue

            if harf in ("ا", "ى", "آ") and not mevcut_h:
                sonuc_parcalar.append(harf)
                continue
            if i > 0 and harf in ("و", "ي") and not mevcut_h and not son_harf_mi:
                sonuc_parcalar.append(harf)
                continue

            if son_harf_mi:
                if mevcut_h and yalin in YEREL_EGITIM_HAREKE_SOZLUGU and onceki_yalin not in HARFI_CER_LISTESI:
                    sonuc_parcalar.append(harf + mevcut_h)
                elif onceki_yalin in HARFI_CER_LISTESI:
                    son_ek = "\u0650" if (el_var or yalin.endswith(("ه", "ها", "هم", "هما", "ك", "كم"))) else "\u064D"
                    sonuc_parcalar.append(harf + ("\u0651" + son_ek if "\u0651" in mevcut_h else son_ek))
                elif onceki_yalin in INNE_GRUBU_LISTESI or onceki_yalin in NASB_EDATLARI:
                    son_ek = "\u064E" if (el_var or yalin.startswith(("ي", "ت", "ن", "أ"))) else "\u064B"
                    sonuc_parcalar.append(harf + ("\u0651" + son_ek if "\u0651" in mevcut_h else son_ek))
                elif mevcut_h:
                    sonuc_parcalar.append(harf + mevcut_h)
                elif harf == "ة":
                    sonuc_parcalar.append(harf + ("\u064F" if el_var else "\u064C"))
                elif el_var or yalin.startswith(("ي", "ت", "ن", "أ")):
                    sonuc_parcalar.append(harf + "\u064F")
                else:
                    sonuc_parcalar.append(harf + "\u064C")
                continue

            if sonraki_med_mi:
                if sonraki_harf in ("ا", "ى"):
                    sonuc_parcalar.append(harf + "\u064E")
                elif sonraki_harf == "و":
                    sonuc_parcalar.append(harf + "\u064F")
                elif sonraki_harf == "ي":
                    sonuc_parcalar.append(harf + "\u0650")
                continue

            bas_ofset = 2 if el_var else 0
            if (i - bas_ofset) % 2 == 0:
                sonuc_parcalar.append(harf + "\u064E")
            else:
                sonuc_parcalar.append(harf + ("\u0652" if i < len(ciftler) - 2 else "\u0650"))

        return hareke_siralamasini_normallestir("".join(sonuc_parcalar))

    @classmethod
    def metni_otomatik_harekele(
        cls, metin: str, cevrimici_dene: bool = True, cevrimici_zorla: bool = False
    ) -> Tuple[str, str]:
        ham = str(metin or "").strip()
        if not ham:
            return "", "Boş metin"

        ham_duzeltilmis = re.sub(r"ل[\u064B-\u0652]*ا\s*ب[\u064B-\u0652]*د[\u064B-\u0652]*", "لَا بُدَّ", ham)

        baz_metin = ham_duzeltilmis
        kaynak_etiketi = "📚 Yerel Eğitim Sözlüğü + Tam İ'rab Motoru"

        mevcut_analiz = arapca_hareke_analizi_yap(ham_duzeltilmis)
        if cevrimici_zorla or (cevrimici_dene and mevcut_analiz["oran"] < 75):
            yalin_girdi = arapca_harekeleri_soy(ham_duzeltilmis)
            cevrimici_sonuc = cls._cevrimici_mishkal_harekele(yalin_girdi, zorla=cevrimici_zorla)
            if cevrimici_sonuc:
                baz_metin = cevrimici_sonuc
                kaynak_etiketi = "✨ Çevrimiçi Neural Tashkeel + Tam İ'rab Tamamlayıcı"

        satirlar = baz_metin.splitlines()
        tamamlanmis_satirlar: List[str] = []

        for satir in satirlar:
            kelimeler = satir.split(" ")
            yeni_kelimeler: List[str] = []
            onceki_yalin = ""

            for k_idx, klm in enumerate(kelimeler):
                if not klm.strip():
                    continue
                m = re.match(r"^([«\"'()]*)([^\s.،؛؟!?,:;…»\"'()]+)([.،؛؟!?,:;…»\"'()]*)$", klm)
                if not m:
                    yeni_kelimeler.append(klm)
                    continue
                on_ek, govde, son_noktalama = m.group(1), m.group(2), m.group(3)
                tam_govde = cls._eksik_harfleri_tamamla(
                    govde, onceki_yalin=onceki_yalin, cumle_basi_mi=(k_idx == 0)
                )
                yeni_kelimeler.append(f"{on_ek}{tam_govde}{son_noktalama}")
                onceki_yalin = arapca_harekeleri_soy(govde)

            tamamlanmis_satirlar.append(" ".join(yeni_kelimeler))

        sonuc_metin = hareke_siralamasini_normallestir("\n".join(tamamlanmis_satirlar))
        sonuc_metin = (
            sonuc_metin.replace("أَنَّ تَعَلُّمَ", "أَنْ تَعْلَمَ")
            .replace("أَنَّ تَعَلُّمٌ", "أَنْ تَعْلَمَ")
            .replace("أَنَّ تَعْلَمَ", "أَنْ تَعْلَمَ")
        )
        return sonuc_metin, kaynak_etiketi


# ==============================================================================
# 2. SPARK-TTS HAREKESİZ METİN UYARI VE ONAYLI HAREKELEME PENCERESİ
# ('☐ Bu oturum boyunca bir daha gösterme' + '🌐 Mishkal Dene' + Geniş Butonlar)
# ==============================================================================
class HarekeUyariVeOnayDialog(QDialog):
    def __init__(self, orijinal_metin: str, koyu_tema: bool = True, parent=None):
        super().__init__(parent)
        self.orijinal_metin = orijinal_metin
        self.onaylanan_metin = orijinal_metin
        self.secim_sonucu = "IPTAL"

        self.setWindowTitle("⚠️ Harekesiz / Eksik Harekeli Metin Tespit Edildi")
        self.setMinimumSize(860, 520)
        self.resize(910, 560)
        self.setStyleSheet(studyo_tema_qss_olustur("koyu" if koyu_tema else "aydinlik"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        analiz = arapca_hareke_analizi_yap(orijinal_metin)
        uyari_baslik = QLabel(
            f"⚠️ <b>Harekesiz / Eksik Harekeli Metin Tespit Edildi ({analiz['etiket']})</b>"
        )
        uyari_baslik.setWordWrap(True)
        uyari_baslik.setStyleSheet("font-size: 11.5pt; color: #f59e0b;")
        layout.addWidget(uyari_baslik)

        aciklama = QLabel(
            "Seçili olan <b>⭐ Spark-TTS (24kHz BiCodec)</b> ses klonlama motoru yalnızca <b>tam harekeli Arapça metinlerle</b> "
            "eğitilmiştir; harekesiz kelimelerde erken durabilir veya yanlış sesler üretebilir.<br>"
            "Aşağıda metninizin <b>Tam Harekelenmiş</b> halini görebilir, dilerseniz düzenleyip onaylayabilirsiniz:"
        )
        aciklama.setWordWrap(True)
        layout.addWidget(aciklama)

        oto_metin, kaynak_bilgi = ArapcaHarekelemeMotoru.metni_otomatik_harekele(orijinal_metin)

        ust_arac = QHBoxLayout()
        self.lbl_kaynak = QLabel(f"🔍 Harekeleme Kaynağı: <b>{kaynak_bilgi}</b>")
        self.lbl_kaynak.setStyleSheet("color: #10b981; font-size: 9.5pt;")
        ust_arac.addWidget(self.lbl_kaynak)
        ust_arac.addStretch()

        btn_mishkal = QPushButton("🌐 Çevrimiçi (Mishkal) Dene")
        btn_mishkal.setFixedHeight(26)
        btn_mishkal.setToolTip("Metni çevrimiçi Mishkal Neural Tashkeel servisiyle yeniden harekeler.")
        btn_mishkal.setStyleSheet("background-color: #0284c7; color: white; border: none; padding: 2px 10px;")
        btn_mishkal.clicked.connect(self._mishkal_ile_yeniden_dene)
        ust_arac.addWidget(btn_mishkal)

        harekeler = [
            ("Fetha (ـَ)", "\u064E"),
            ("Kesra (ـِ)", "\u0650"),
            ("Damme (ـُ)", "\u064F"),
            ("Sükûn (ـْ)", "\u0652"),
            ("Şedde (ـّ)", "\u0651"),
            ("Tenvin (ـٌ)", "\u064C"),
        ]
        for etiket, ch in harekeler:
            b = QPushButton(etiket)
            b.setFixedHeight(26)
            b.clicked.connect(lambda checked=False, k=ch: self._hareke_ekle(k))
            ust_arac.addWidget(b)
        layout.addLayout(ust_arac)

        self.txt_harekeli = QTextEdit()
        self.txt_harekeli.setLayoutDirection(Qt.RightToLeft)
        self.txt_harekeli.setFont(profesyonel_arapca_font_olustur())
        self.txt_harekeli.setPlainText(oto_metin)
        layout.addWidget(self.txt_harekeli, stretch=1)

        ipucu_ve_oturum_bar = QHBoxLayout()
        self.chk_oturum_boyunca_gosterme = QCheckBox("Bu oturum boyunca bir daha gösterme")
        self.chk_oturum_boyunca_gosterme.setChecked(not oturumda_hareke_uyarisi_aktif_mi())
        self.chk_oturum_boyunca_gosterme.setStyleSheet("font-weight: bold; color: #0284c7;")
        self.chk_oturum_boyunca_gosterme.setToolTip(
            "İşaretlendiğinde uygulama kapatılana kadar bu uyarı penceresi tekrar gösterilmez.\n"
            "Uygulama yeniden başlatıldığında varsayılan uyarı davranışı otomatik olarak geri yüklenir."
        )
        ipucu_ve_oturum_bar.addWidget(self.chk_oturum_boyunca_gosterme)
        ipucu_ve_oturum_bar.addStretch()

        ipucu = QLabel("💡 <i>Onayladığınız kelimeler Stüdyo Telaffuz Sözlüğüne otomatik kaydedilir.</i>")
        ipucu.setStyleSheet("color: #64748b; font-size: 9pt;")
        ipucu_ve_oturum_bar.addWidget(ipucu)
        layout.addLayout(ipucu_ve_oturum_bar)

        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        btn_onayla_spark = QPushButton("✨ 1. Harekeli Metni Onayla ve Spark-TTS ile Seslendir")
        btn_onayla_spark.setFixedHeight(38)
        btn_onayla_spark.setStyleSheet(
            "background-color: #059669; color: white; border: none; padding: 6px 14px; font-weight: bold;"
        )
        btn_onayla_spark.clicked.connect(self._onayla_spark)
        btn_bar.addWidget(btn_onayla_spark, stretch=2)

        btn_direkt_tts = QPushButton("⚡ 2. 'Hızlı Direkt TTS' ile Oku")
        btn_direkt_tts.setFixedHeight(38)
        btn_direkt_tts.setStyleSheet(
            "background-color: #0284c7; color: white; border: none; padding: 6px 12px; font-weight: bold;"
        )
        btn_direkt_tts.clicked.connect(self._direkt_tts_sec)
        btn_bar.addWidget(btn_direkt_tts, stretch=1)

        btn_mevcut = QPushButton("▶️ 3. Harekelenmeden Devam Et")
        btn_mevcut.setFixedHeight(38)
        btn_mevcut.clicked.connect(self._mevcut_devam)
        btn_bar.addWidget(btn_mevcut, stretch=1)

        btn_iptal = QPushButton("İptal")
        btn_iptal.setFixedHeight(38)
        btn_iptal.clicked.connect(self.reject)
        btn_bar.addWidget(btn_iptal)

        layout.addLayout(btn_bar)

    def _mishkal_ile_yeniden_dene(self) -> None:
        yeni_metin, yeni_kaynak = ArapcaHarekelemeMotoru.metni_otomatik_harekele(
            self.orijinal_metin, cevrimici_dene=True, cevrimici_zorla=True
        )
        if yeni_metin:
            self.txt_harekeli.setPlainText(yeni_metin)
            self.lbl_kaynak.setText(f"🔍 Harekeleme Kaynağı: <b>{yeni_kaynak}</b>")

    def _oturum_tercihini_uygula(self) -> None:
        if self.chk_oturum_boyunca_gosterme.isChecked():
            oturumda_hareke_uyarisini_sustur(True)

    def _hareke_ekle(self, karakter: str) -> None:
        cur = self.txt_harekeli.textCursor()
        cur.insertText(karakter)
        self.txt_harekeli.setFocus()

    def _onayla_spark(self) -> None:
        self._oturum_tercihini_uygula()
        self.onaylanan_metin = self.txt_harekeli.toPlainText().strip() or self.orijinal_metin
        ArapcaHarekelemeMotoru.kullanici_sozlugune_ogret(self.orijinal_metin, self.onaylanan_metin)
        self.secim_sonucu = "HAREKELE_VE_SPARK"
        self.accept()

    def _direkt_tts_sec(self) -> None:
        self._oturum_tercihini_uygula()
        self.onaylanan_metin = self.orijinal_metin
        self.secim_sonucu = "DIREKT_TTS_GEC"
        self.accept()

    def _mevcut_devam(self) -> None:
        self._oturum_tercihini_uygula()
        self.onaylanan_metin = self.orijinal_metin
        self.secim_sonucu = "MEVCUT_DEVAM"
        self.accept()


# ==============================================================================
# 3. MERKEZİ AYDINLIK / KARANLIK STÜDYO TEMASI (QSS) ÜRETİCİSİ
# ==============================================================================
def studyo_tema_qss_olustur(tema_kodu: str = "koyu") -> str:
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
                padding: 7px 13px;
                margin-right: 3px;
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
                padding: 5px 10px;
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
            padding: 7px 13px;
            margin-right: 3px;
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
            padding: 5px 10px;
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
# 4. İLK AÇILIŞ ADIM ADIM BAŞLANGIÇ TURU VE SİSTEM SAĞLIĞI SİHİRBAZI
# ==============================================================================
class BaslangicTuruDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("🎓 Muallimun AI Ses Stüdyosu Pro — Adım Adım Başlangıç Turu ve Sistem Hazırlığı")
        self.setMinimumSize(860, 560)
        self.resize(920, 600)

        tema = self.config_manager.user_settings.get("tema_modu", "koyu")
        self.setStyleSheet(studyo_tema_qss_olustur(tema))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        ust_bar = QHBoxLayout()
        self.lbl_baslik = QLabel("🎓 Hoş Geldiniz — 5 Adımda Stüdyo Başlangıç Turu")
        self.lbl_baslik.setStyleSheet("font-size: 13.5pt; font-weight: bold; color: #10b981;")
        ust_bar.addWidget(self.lbl_baslik)
        ust_bar.addStretch()

        self.lbl_adim_sayac = QLabel("Adım 1 / 5")
        self.lbl_adim_sayac.setStyleSheet(
            "background-color: #0284c7; color: white; padding: 5px 14px; border-radius: 12px; font-weight: bold;"
        )
        ust_bar.addWidget(self.lbl_adim_sayac)
        layout.addLayout(ust_bar)

        self.stack = QStackedWidget()
        self._sayfalari_olustur()
        layout.addWidget(self.stack, stretch=1)

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
        <div style='line-height: 1.65; font-size: 11.5pt; padding: 8px;'>
            <h2 style='color:#0284c7; margin-top:0;'>🩺 Adım 1: Canlı Sistem Sağlığı ve Donanım Kontrolü</h2>
            <p><b>Muallimun AI Ses Stüdyosu Pro</b>, Arapça eğitim materyallerini (sözlük kelimeleri, gramer cümleleri, atasözleri,
            çoklu karakter diyalogları ve uzun okuma metinlerini) vakıf/vasıl kurallarına uygun olarak seslendirmek için tasarlanmıştır.</p>
            <table width='100%' cellpadding='10' cellspacing='0' style='border: 1px solid #334155; border-radius: 8px; margin-top: 10px;'>
                <tr>
                    <td width='34%'><b>🚀 Grafik İşlemci (GPU / VRAM):</b></td>
                    <td>{gpu_durum}</td>
                </tr>
                <tr>
                    <td><b>⚙️ Önerilen Çalışma Kademesi:</b></td>
                    <td><span style='color:#0284c7; font-weight:bold;'>{gpu_bilgi['profil_detay']['ad']}</span></td>
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
            <p style='margin-top:14px;'>💡 <b>Hızlı İpucu:</b> Üst bardaki <b>☀️ / 🌙</b> ikon butonuyla istediğiniz zaman Aydınlık ve Karanlık tema arasında geçiş yapabilirsiniz.</p>
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
        self.stack.addWidget(self._sayfa_widget_olustur(self._sistem_sagligi_html_uret()))

        sayfa2_html = """
        <div style='line-height: 1.65; font-size: 11.5pt; padding: 8px;'>
            <h2 style='color:#0284c7; margin-top:0;'>🧠 Adım 2: Ses Motorları ve Harekeleme Kuralı (Çok Önemli!)</h2>
            <p>Uygulamada farklı ihtiyaçlara göre <b>3 seslendirme motoru</b> bulunur:</p>
            <ul>
                <li><b style='color:#10b981;'>1. ⭐ Spark-TTS (24kHz BiCodec — Önerilen Ana Stüdyo Motoru):</b><br>
                Tam harekeli Arapça metinlerde <b>en yüksek mahreç, hareke ve ses klonlama kalitesini</b> sunar.
                8 stüdyo sesini veya kendi eklediğiniz sesi birebir klonlar ve tamamen çevrimdışı çalışır.<br>
                <span style='color:#ef4444; font-weight:bold;'>⚠️ Kritik Kural:</span> Spark-TTS yalnızca <b>tam harekeli metinleri</b> doğru okuyabilir;
                harekesiz veya yarım harekeli metin girildiğinde uygulama sizi otomatik uyarır ve <b>✨ Otomatik Harekele</b> aracıyla eksik harfleri tamamlar.</li>
                <br>
                <li><b style='color:#0284c7;'>2. ⚡ Hızlı Direkt Neural TTS (Çevrimiçi Hazır Ses + 24kHz DSP):</b><br>
                İnternet üzerinden hazır Arapça neural sesleri kullanır. Hem harekeli hem harekesiz metinleri ~1 saniyede okur.</li>
                <br>
                <li><b style='color:#f59e0b;'>3. 🗣️ Coqui XTTS v2 (Alternatif Çok Dilli Motor):</b><br>
                Genel amaçlı çok dilli modeldir. Arapça ses doğallığı Spark-TTS kadar yüksek değildir; yalnızca alternatif amaçlıdır.</li>
            </ul>
        </div>
        """
        self.stack.addWidget(self._sayfa_widget_olustur(sayfa2_html))

        sayfa3_html = """
        <div style='line-height: 1.65; font-size: 11.5pt; padding: 8px;'>
            <h2 style='color:#0284c7; margin-top:0;'>🎙️ Adım 3: Tekli Stüdyo, Yazı Boyutu (+/-) ve 8 Tonlama Profili</h2>
            <p><b>1. Seslendirme Stüdyosu</b> sekmesinde tek bir kelime, cümle veya atasözünü anında sentezleyebilirsiniz:</p>
            <ol>
                <li><b>🔍 Arapça Yazı Boyutu (+ / -):</b> Metin kutusunun üstündeki <b>A+</b> ve <b>A-</b> butonlarıyla harekeli Arapça metni
                göz konforunuza göre büyütebilir veya küçültebilirsiniz.</li>
                <li><b>🎭 8 Akustik Tonlama Profili:</b> <i>Sözlük & Tek Kelime</i>, <i>Akademik Muallim</i>, <i>Babacan Nasihat</i>,
                <i>Canlı Diyalog</i>, <i>Soru Vurgusu</i>, <i>Coşkulu Hitabet</i> ve <i>Dingin Öyküleyici</i> profilleri hız, sıcaklık ve DSP parametrelerini otomatik ayarlar.</li>
                <li><b>✨ Otomatik Harekele Butonu:</b> Harekesiz veya eksik harekeli bir Arapça cümle yapıştırdığınızda
                <b>✨ Otomatik Harekele</b> butonuna basarak tüm kelimeleri eksiksiz harekeleyebilirsiniz.</li>
            </ol>
        </div>
        """
        self.stack.addWidget(self._sayfa_widget_olustur(sayfa3_html))

        sayfa4_html = """
        <div style='line-height: 1.65; font-size: 11.5pt; padding: 8px;'>
            <h2 style='color:#0284c7; margin-top:0;'>📦 Adım 4: Toplu Seslendirme, Özel Dosya Adı ve Seçmeli Kuyruk</h2>
            <p><b>4. Toplu Seslendirme</b> sekmesi Excel (<code>.xlsx</code>), JSON, CSV ve TXT listelerini topluca seslendirir:</p>
            <ul>
                <li><b>🏷️ Kaynak Dosyadaki Özel İsimlendirme Desteği:</b> Yüklediğiniz JSON, CSV veya Excel dosyasında
                <code>ses_dosyasi</code>, <code>dosya_adi</code>, <code>ses_erkek</code> veya <code>ses_kadin</code> sütunları varsa
                üretilen ses dosyaları birebir o isimlerle kaydedilir!</li>
                <li><b>☑️ Seçmeli Satır Seç & Üret:</b> Binlerce satırlık dosyada arama yaparak, tek tek işaretleyerek veya
                <b>Satır Aralığı (Örn: 1 - 50)</b> belirterek sadece istediğiniz satırları üretebilirsiniz.</li>
                <li><b>🔗 Grup Cümlelerini Birleştir:</b> Diyalog veya Uzun Metin gruplarında her grubun kendi cümlelerini kendi klasöründe
                tek bir birleşik ses dosyası (<code>tamami.mp3</code>) olarak da birleştirir.</li>
            </ul>
        </div>
        """
        self.stack.addWidget(self._sayfa_widget_olustur(sayfa4_html))

        sayfa5_html = """
        <div style='line-height: 1.65; font-size: 11.5pt; padding: 8px;'>
            <h2 style='color:#0284c7; margin-top:0;'>🎭 Adım 5: Çoklu Rol Diyalog (8 Karakter) ve Uzun Metin Stüdyosu</h2>
            <p><b>5. Diyalog & Uzun Metin</b> sekmesi ders kitaplarındaki karşılıklı konuşmaları ve okuma parçalarını üretir:</p>
            <ul>
                <li><b>🎲 8 Sesten Otomatik Rol Ata:</b> Diyalogdaki konuşmacıların isimlerine (Öğretmen, Anne, Baba, Çocuk vb.) ve cinsiyetlerine göre
                çakışmasız ses karakteri dağıtır.</li>
                <li><b>📚 Çoklu Seç & Üret (Ayrı Klasörlerde Dosyalama):</b> Çoklu diyalog JSON dosyası yüklediğinizde seçtiğiniz tüm diyalogları
                kendi klasörlerinde (<code>cikti_sesler/diyaloglar/dlg_001/</code>) hem satır satır hem de birleştirilmiş olarak üretir.</li>
                <li><b>📖 Uzun Metin Cümle Bölücü ve İsteğe Bağlı Birleştirme:</b> Uzun Arapça paragrafları cümlelere bölerek seslendirir;
                alt bardaki <b>🔗 Cümleleri Birleştir (tamami.mp3)</b> seçeneğiyle tek parça okuma metni oluşturur.</li>
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
# 5. KAPSAMLI TANITIM REHBERİ VE KULLANIM KILAVUZU PENCERESİ
# ==============================================================================
class KullanimKilavuzuDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("📘 Muallimun AI Ses Stüdyosu Pro — Kapsamlı Tanıtım Rehberi ve Kullanım Kılavuzu")
        self.setMinimumSize(1040, 650)
        self.resize(1140, 720)

        tema = self.config_manager.user_settings.get("tema_modu", "koyu")
        self.koyu_mu = (tema != "aydinlik")
        self.setStyleSheet(
            studyo_tema_qss_olustur(tema)
            + "\nQTabBar::tab { padding: 7px 11px; font-size: 9.3pt; }"
        )

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

        btn_disa_aktar = QPushButton("🌐 Çevrimiçi Web Kılavuzunu Aç (muallimun.com)")
        btn_disa_aktar.setCursor(Qt.PointingHandCursor)
        btn_disa_aktar.setToolTip("https://muallimun.com/muallimun_ses_studyosu/ adresindeki görsel stüdyo rehberini tarayıcıda açar.")
        btn_disa_aktar.setStyleSheet("background-color: #059669; color: white;")
        btn_disa_aktar.clicked.connect(self._kilavuzu_html_kaydet)
        ust.addWidget(btn_disa_aktar)
        layout.addLayout(ust)

        self.tabs = QTabWidget()
        self.tabs.tabBar().setUsesScrollButtons(False)
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

    def _sekme_ekle(self, baslik: str, ic_html: str) -> None:
        kart_bg = "#111827" if self.koyu_mu else "#f8fafc"
        kart_border = "#1e293b" if self.koyu_mu else "#cbd5e1"
        uyari_bg = "#451a03" if self.koyu_mu else "#fef3c7"
        uyari_fg = "#fde68a" if self.koyu_mu else "#92400e"
        bilgi_bg = "#064e3b" if self.koyu_mu else "#d1fae5"
        bilgi_fg = "#ecfdf5" if self.koyu_mu else "#065f46"

        sarili_html = f"""
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; font-size: 11.5pt; line-height: 1.7; margin: 10px; }}
            h2 {{ color: #0284c7; font-size: 15pt; margin-top: 4px; margin-bottom: 10px; border-bottom: 2px solid {kart_border}; padding-bottom: 6px; }}
            h3 {{ color: #10b981; font-size: 12.5pt; margin-top: 14px; margin-bottom: 6px; }}
            .kart {{ background-color: {kart_bg}; border: 1px solid {kart_border}; border-radius: 8px; padding: 14px 18px; margin-bottom: 14px; }}
            .uyari {{ background-color: {uyari_bg}; color: {uyari_fg}; border: 1px solid #f59e0b; border-radius: 8px; padding: 12px 16px; margin-bottom: 14px; }}
            .ipucu {{ background-color: {bilgi_bg}; color: {bilgi_fg}; border: 1px solid #10b981; border-radius: 8px; padding: 12px 16px; margin-bottom: 14px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 8px; margin-bottom: 12px; font-size: 11pt; }}
            th {{ background-color: #0284c7; color: #ffffff; padding: 8px 12px; text-align: left; }}
            td {{ border: 1px solid {kart_border}; padding: 8px 12px; }}
            code {{ font-family: Consolas, monospace; font-weight: bold; color: #0284c7; }}
        </style>
        <body>{ic_html}</body>
        """
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(6, 6, 6, 6)
        b = QTextBrowser()
        b.setOpenExternalLinks(True)
        b.setHtml(sarili_html)
        v.addWidget(b)
        self.tabs.addTab(w, baslik)

    def _sekmeleri_hazirla(self) -> None:
        self._sekme_ekle(
            "1. 🌟 Genel && Modeller",
            """
            <h2>Muallimun AI Ses Stüdyosu Pro Nedir?</h2>
            <div class='kart'>
                <p><b>Muallimun AI Ses Stüdyosu Pro</b>; Arapça ders kitapları, dijital sözlükler, etkileşimli flipbook'lar,
                mobil eğitim uygulamaları ve e-öğrenme portalları için <b>24kHz stüdyo kalitesinde, hareke ve vakıf/vasıl kurallarına duyarlı</b>
                yapay zeka dublaj ve seslendirme üretmek amacıyla geliştirilmiştir.</p>
            </div>

            <div class='uyari'>
                <b>⚠️ KRİTİK KALİTE KURALI (Spark-TTS ve Tam Harekeli Metin Zorunluluğu):</b><br>
                Varsayılan ana motorumuz olan <b>⭐ Spark-TTS (IbrahimSalah/Arabic-TTS-Spark)</b> yalnızca <b>tam harekeli Arapça metinlerle</b>
                eğitilmiştir. Harekesiz veya yarım harekeli bir metin girildiğinde model kelimenin harekelerini tahmin edemez.<br>
                • Metninizde eksik hareke varsa üst bardaki <b>✨ Otomatik Harekele</b> butonuna basarak tüm harfleri eksiksiz harekeleyin,<br>
                • Veya harekesiz metinleri doğrudan okutmak için <b>⚡ Hızlı Direkt Neural TTS</b> motorunu seçin.
            </div>

            <h3>Desteklenen 3 Seslendirme Motoru Karşılaştırması</h3>
            <table>
                <tr>
                    <th width='26%'>Ses Motoru</th>
                    <th width='22%'>Çalışma Ortamı</th>
                    <th width='24%'>Hareke & Klonlama</th>
                    <th>En Uygun Kullanım Senaryosu</th>
                </tr>
                <tr>
                    <td><b>1. ⭐ Spark-TTS (Önerilen Ana Motor)</b></td>
                    <td>Yerel GPU / CPU (Çevrimdışı)</td>
                    <td><b>Tam Harekeli Metin Zorunlu</b> • Birebir Ses Klonlama</td>
                    <td>Harekeli ders kitapları, sözlük kelimeleri, gramer cümleleri, atasözleri ve 8 karakterli diyaloglar.</td>
                </tr>
                <tr>
                    <td><b>2. ⚡ Hızlı Direkt Neural TTS</b></td>
                    <td>Çevrimiçi Servis (0 MB VRAM)</td>
                    <td>Harekeli ve Harekesiz Okur • Hazır Ses Kullanır</td>
                    <td>Harekesiz metinler, hızlı ön-izleme ve ekran kartı olmayan bilgisayarlarda seri üretim.</td>
                </tr>
                <tr>
                    <td><b>3. 🗣️ Coqui XTTS v2</b></td>
                    <td>Yerel GPU / CPU (Çevrimdışı)</td>
                    <td>Alternatif / Deneysel</td>
                    <td>Genel amaçlı 17 dilli modeldir; Arapça mahreç ve hareke kalitesi Spark-TTS kadar yüksek değildir.</td>
                </tr>
            </table>
            """,
        )

        self._sekme_ekle(
            "2. 🕌 Vakıf && Harekeleme",
            """
            <h2>Fasih Arapça Vakıf/Vasıl Motoru, 8 Tonlama Profili ve Otomatik Harekeleme</h2>
            <div class='kart'>
                <h3>1. ✨ 2 Aşamalı Eksiksiz Otomatik Harekeleme (Auto-Tashkeel)</h3>
                <p>Harekesiz veya kısmi harekeli bir Arapça cümle girdiğinizde <b>✨ Otomatik Harekele</b> butonu:</p>
                <ol>
                    <li>Önce <b>Öğrenen Stüdyo Sözlüğü (<code>config/tashkeel_sozluk.json</code>)</b> ve <b>Çevrimiçi Mishkal Neural Tashkeel</b> servisini çalıştırır,</li>
                    <li>Ardından <b>2. Aşama İ'rab Tamamlayıcı</b> ile cümlede harekesiz bırakılan tüm harfleri ve kelime sonlarını
                    (Harf-i Cer sonrası kesra, İnne/Nasb sonrası fetha, Elif-Lam ve Tâ-i Merbûta kuralları) eksiksiz tamamlar.</li>
                </ol>
            </div>

            <div class='kart'>
                <h3>2. 🎭 8 Akustik Tonlama Profili Ses Çıktısını Nasıl Etkiler?</h3>
                <table>
                    <tr>
                        <th width='32%'>Tonlama Profili</th>
                        <th>Akustik ve DSP Etkisi</th>
                    </tr>
                    <tr>
                        <td><b>🔤 Sözlük & Tek Kelime</b></td>
                        <td>Düşük sıcaklık (<code>0.52</code>), dar örnekleme (<code>top_k=30</code>) ve net vakıf sükûnu ile mahreç odaklı okur.</td>
                    </tr>
                    <tr>
                        <td><b>🎓 Akademik Muallim</b></td>
                        <td>Tane tane ders anlatım hızı (<code>0.94x</code>) ve dengeli vurgu sağlar.</td>
                    </tr>
                    <tr>
                        <td><b>🌿 Babacan & Hikmetli Nasihat</b></td>
                        <td>Ağırbaşlı tempo (<code>0.89x</code>), bağlaçlardan önce otomatik tefekkür durağı (<code>،</code>) ve sıcak tını uygular.</td>
                    </tr>
                    <tr>
                        <td><b>🎭 Canlı Diyalog / ❓ Soru / ❗ Hitabet</b></td>
                        <td>Soru, ünlem ve karşılıklı konuşmalarda tonlama dinamizmini ve vurguyu artırır.</td>
                    </tr>
                </table>
            </div>
            """,
        )

        self._sekme_ekle(
            "3. 📦 Toplu && Şablonlar",
            """
            <h2>Toplu Seslendirme, Özel Dosya İsimlendirme ve Seçmeli Kuyruk</h2>
            <div class='ipucu'>
                <b>🏷️ Kaynak Dosyadan Otomatik Özel İsimlendirme:</b><br>
                Bilgisayarınızdan yüklediğiniz Excel (<code>.xlsx</code>), JSON veya CSV dosyasında oluşacak ses dosyasına ait bir isim sütunu varsa
                uygulama dosyaları <b>birebir o isimle</b> kaydeder!
            </div>

            <div class='kart'>
                <h3>Desteklenen Sütun / Alan İsimleri (JSON, CSV ve Excel)</h3>
                <table>
                    <tr>
                        <th>Alan / Sütun Adı</th>
                        <th>Zorunlu mu?</th>
                        <th>Ne İşe Yarar?</th>
                    </tr>
                    <tr>
                        <td><code>arapca</code> (veya <code>metin</code>, <code>kelime</code>)</td>
                        <td>✅ Zorunlu</td>
                        <td>Seslendirilecek Arapça kelime veya cümle.</td>
                    </tr>
                    <tr>
                        <td><code>ses_dosyasi</code> (veya <code>dosya_adi</code>, <code>filename</code>)</td>
                        <td>İsteğe Bağlı</td>
                        <td>Tekil üretimde çıkacak ses dosyasının özel adı (Örn: <code>unite1_kelime05.mp3</code>). Yoksa <code>id</code> kullanılır.</td>
                    </tr>
                    <tr>
                        <td><code>ses_erkek</code> / <code>ses_kadin</code></td>
                        <td>İsteğe Bağlı</td>
                        <td>Çift üretimde (Erkek+Kadın) erkek ve kadın ses dosyalarına verilecek özel dosya adları.</td>
                    </tr>
                    <tr>
                        <td><code>id</code> (veya <code>kod</code>, <code>sira</code>)</td>
                        <td>Önerilir</td>
                        <td>Özel dosya adı belirtilmemişse ses dosyasının kaydedileceği benzersiz kimlik (Örn: <code>cumle_0001</code>).</td>
                    </tr>
                    <tr>
                        <td><code>ses_secimi</code> (veya <code>referans_ses</code>)</td>
                        <td>İsteğe Bağlı</td>
                        <td><code>IKISI</code> (Çift üretim), <code>E1</code>, <code>E2</code>, <code>K1</code>, <code>K2</code>, <code>EC1</code>, <code>EC2</code>, <code>KC1</code>, <code>KC2</code>, <code>DIREKT</code>.</td>
                    </tr>
                </table>
            </div>
            """,
        )

        self._sekme_ekle(
            "4. 🎭 Diyalog && Metin",
            """
            <h2>Çoklu Rol Diyalog (8 Karakter) ve Uzun Metin / Paragraf Stüdyosu</h2>
            <div class='kart'>
                <h3>🎭 A) Çoklu Rol Diyalog Stüdyosu (4 Hazır Diyalog Şablonu)</h3>
                <ul>
                    <li><b>🎲 8 Sesten Otomatik Rol Ata:</b> Diyalogdaki konuşmacıların adlarını (Öğretmen, Anne, Baba, Ömer, Leyla, Çocuk vb.)
                    ve cinsiyetlerini (<code>E</code> / <code>K</code>) analiz ederek 8 stüdyo karakterinden çakışmasız rol dağıtır.</li>
                    <li><b>📚 Çoklu Seç & Üret:</b> Birden fazla diyalog içeren JSON dosyanızda istediğiniz diyalogları seçip tek seferde üretebilirsiniz.
                    Her diyalog yalnızca kendi klasörü içinde (<code>cikti_sesler/diyaloglar/&lt;diyalog_id&gt;/</code>) hem satır satır hem de
                    <code>diyalog_tamami.mp3</code> olarak kaydedilir; farklı diyaloglar birbirine karıştırılmaz.</li>
                </ul>
            </div>

            <div class='kart'>
                <h3>📖 B) Uzun Metin / Paragraf Stüdyosu (4 Hazır Okuma Parçası)</h3>
                <ul>
                    <li><b>✂️ Harf-i Cer Korumalı Cümle Bölücü:</b> Uzun Arapça paragrafları satır sonlarını ve noktalama işaretlerini koruyarak
                    doğal cümlelere ayırır; edatları satır sonunda asla tek başına bırakmaz.</li>
                    <li><b>🔗 Cümleleri Birleştir (<code>tamami.mp3</code>):</b> Alt bardaki onay kutusu işaretli olduğunda,
                    cümle cümle seslendirme biter bitmez o metnin cümleleri belirlediğiniz nefes boşluğuyla tek bir ses dosyası olarak birleştirilir.</li>
                </ul>
            </div>
            """,
        )

        self._sekme_ekle(
            "5. 🎚️ DSP && Kalite (QA)",
            """
            <h2>5-Katmanlı 24kHz Stüdyo DSP Mastering ve Doğal Cümle Sonu Sönümlenmesi</h2>
            <div class='kart'>
                <h3>Sentez Sonrası Uygulanan Akustik Katmanlar</h3>
                <ol>
                    <li><b>Saf Referans Klonlama:</b> Referans sesin doğal nefesleri, vurguları ve konuşma ritmi sıkıştırılmadan doğrudan BiCodec modeline aktarılır.</li>
                    <li><b>DC Offset & Sıfır Fazlı Butterworth HPF:</b> Sesin doğal gövdesini koruyarak dip uğultularını temizler.</li>
                    <li><b>Anti-Aliasing Harmonik Sıcaklık (Tanh Drive -> LPF):</b> Tanh doygunluğu Low-Pass filtreden önce uygulanarak üst harmonik cızırtılar süzülür.</li>
                    <li><b>Kosinüs Eğrili Doğal Çıkış (Raised-Cosine Fade-Out) ve Sessizlik Yastığı:</b> Cümle sonunda son kelimenin aniden kesilmesini önler;
                    150 ms yumuşak sönümlenme ve 120 ms doğal nefes boşluğu bırakır.</li>
                    <li><b>FFmpeg True-Peak Limiter (<code>-1.0 dBFS</code>):</b> MP3 kodlama sırasında sesin çatlamasını (clipping) önler.</li>
                </ol>
            </div>

            <div class='ipucu'>
                <b>📊 Gerçek Teknik Ses Kontrolü (QA) Neleri Denetler?</b><br>
                Dalga formu ekranı üretilen her ses dosyasının <b>RMS ses enerjisini (sessiz/boş kayıt denetimi &gt; -44 dBFS)</b>,
                <b>Tepe seviyesini (dBFS)</b>, <b>Kelime başına düşen süreyi</b> ve <b>örnek bütünlüğünü</b> ölçer.
            </div>
            """,
        )

        self._sekme_ekle(
            "6. ⌨️ Kısayollar && SSS",
            """
            <h2>Klavye Kısayolları ve Sık Karşılaşılan Sorunların Çözümü</h2>
            <div class='kart'>
                <table>
                    <tr>
                        <th width='28%'>Klavye Kısayolu</th>
                        <th>İşlevi</th>
                    </tr>
                    <tr>
                        <td><b>Ctrl + Enter</b></td>
                        <td>1. Sekmede (Tekli Stüdyo) yazılan Arapça metni anında seslendirir.</td>
                    </tr>
                    <tr>
                        <td><b>Esc (Escape)</b></td>
                        <td>Devam eden seslendirme işlemini güvenli şekilde durdurur.</td>
                    </tr>
                    <tr>
                        <td><b>Ctrl + + / Ctrl + -</b></td>
                        <td>Arapça metin yazı boyutunu büyütür veya küçültür.</td>
                    </tr>
                    <tr>
                        <td><b>F1</b></td>
                        <td>Kapsamlı Kullanım Kılavuzu penceresini açar.</td>
                    </tr>
                </table>
            </div>

            <div class='kart'>
                <h3>Sık Sorulan Sorular (SSS)</h3>
                <ul>
                    <li><b>Soru: Hareke uyarı penceresini geçici olarak nasıl kapatabilirim?</b><br>
                    <b>Cevap:</b> Uyarı penceresindeki <b>☐ Bu oturum boyunca bir daha gösterme</b> kutucuğunu işaretleyin. Uygulamayı kapatıp yeniden açtığınızda uyarı koruması tekrar aktif olur.</li>
                    <li><b>Soru: Arapça metin puntosunu nasıl büyütebilirim?</b><br>
                    <b>Cevap:</b> Metin kutusunun üst barındaki <b>➕ A+</b> ve <b>➖ A-</b> butonlarıyla yazı boyutunu istediğiniz gibi ayarlayabilirsiniz.</li>
                </ul>
            </div>
            """,
        )

    def _kilavuzu_html_kaydet(self) -> None:
        QDesktopServices.openUrl(QUrl("https://muallimun.com/muallimun_ses_studyosu/"))


# ==============================================================================
# 6. GITHUB YENİ VERSİYON VE GÜNCELLEME KONTROLÜ (ARKA PLAN QTHREAD + DİYALOG)
# ==============================================================================
def _surum_tuple_cevir(surum_str: str) -> Tuple[int, ...]:
    rakamlar = re.findall(r"\d+", str(surum_str or "0.0.0"))
    return tuple(int(x) for x in rakamlar[:4]) if rakamlar else (0, 0, 0)


class GitHubGuncellemeKontrolWorker(QThread):
    sonuc_sinyali = Signal(bool, dict)

    def __init__(self, github_repo: str = VARSAYILAN_GITHUB_REPO, mevcut_surum: str = APP_VERSION):
        super().__init__()
        self.github_repo = str(github_repo or VARSAYILAN_GITHUB_REPO).strip().strip("/")
        self.mevcut_surum = mevcut_surum

    def run(self) -> None:
        headers = {
            "User-Agent": f"MuallimunStudyoPro/{self.mevcut_surum}",
            "Accept": "application/vnd.github.v3+json",
        }
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
                    "yayin_notlari": str(veri.get("notes", "")),
                    "indir_url": str(veri.get("download_url", f"https://github.com/{self.github_repo}/releases")),
                })
                return
        except Exception:
            pass

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
    def __init__(
        self,
        config_manager: ConfigManager,
        otomatik_bildirim_mi: bool = False,
        bilgisiz_bilgi: Optional[Dict[str, Any]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.config_manager = config_manager
        self.worker: Optional[GitHubGuncellemeKontrolWorker] = None
        repo_varsayilan = self.config_manager.user_settings.get("github_repo", VARSAYILAN_GITHUB_REPO)
        self.indir_url = f"https://github.com/{repo_varsayilan}"

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
        self.edt_repo = QLineEdit(repo_varsayilan)
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
        repo = self.edt_repo.text().strip() or VARSAYILAN_GITHUB_REPO
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
        notlar = bilgi.get("yayin_notlari") or "Değişiklik notu belirtilmemiş."
        if bilgi.get("yeni_surum_var"):
            self.lbl_durum.setText(f"🎉 Yeni Sürüm Mevcut: v{uzak} (Mevcut: v{APP_VERSION})")
            self.lbl_durum.setStyleSheet("color: #10b981; font-weight: bold; font-size: 10.5pt;")
            self.txt_notlar.setHtml(f"<h3>🚀 v{uzak} Yenilikleri:</h3><pre style='white-space:pre-wrap;'>{notlar}</pre>")
        else:
            self.lbl_durum.setText(f"✅ Uygulamanız Güncel! (v{APP_VERSION})")
            self.txt_notlar.setHtml(f"<p>En güncel sürümü (<b>v{APP_VERSION}</b>) kullanıyorsunuz.</p><pre>{notlar}</pre>")