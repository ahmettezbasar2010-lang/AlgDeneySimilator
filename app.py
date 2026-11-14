# app.py
import os
import re
import io
import json
import base64
import html as hx
import unicodedata
import tempfilegit --version
import urllib.request
import urllib.error
from datetime import datetime
from urllib.parse import quote

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# SAYFA YAPILANDIRMASI VE STİLLER
# ============================================================
st.set_page_config(page_title="Uzay Yaşam Destek Simülatörü", layout="wide", page_icon="🌱")

st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #c9d1d9; }
    .stSidebar { background-color: #161b22; border-right: 1px solid #30363d; }
    .metric-card {
        background-color: #161b22; border: 1px solid #30363d; border-radius: 10px;
        padding: 22px; box-shadow: 0 4px 16px rgba(0,0,0,0.4);
    }
    .badge-green {
        background-color: rgba(46, 160, 67, 0.15); color: #3fb950;
        border: 1px solid rgba(46, 160, 67, 0.4); padding: 5px 12px; border-radius: 20px;
        font-weight: bold; font-size: 14px; display: inline-block; margin-top: 8px;
    }
    .industrial-header {
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        border: 1px solid #30363d; padding: 30px; border-radius: 12px;
        margin-bottom: 25px; box-shadow: 0 8px 24px rgba(0,0,0,0.5);
    }
    .micro-card {
        background:#161b22; padding:20px; border-radius:10px; text-align:center;
        border:1px solid #30363d; margin:15px 0;
    }
    .micro-card svg { max-width:360px; width:100%; height:auto; }
    .micro-card p { color:#8b949e; font-size:13px; margin:8px 0 0 0; }
    .tanitim-card {
        background:#161b22; padding:18px; border-radius:8px; border:1px solid #30363d;
        border-left:4px solid #58a6ff; color:#c9d1d9; font-size:15px; line-height:1.6; margin:15px 0;
    }
    .sci-card { background:#161b22; border:1px solid #30363d; border-radius:10px; padding:14px 16px; margin-bottom:10px; }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# DİL VE AYARLAR (sağ üst)
# ============================================================
LANG = "tr"


def tx(tr, en):
    return en if LANG == "en" else tr


SOUND_CORE = """(function(){ if (window.__clickInstalled) return; window.__clickInstalled = true; var ac = null;
document.addEventListener('click', function(){ var v = window.__clickVol || 0; if (!v) return;
  try { var Ctx = window.AudioContext || window.webkitAudioContext; if (!ac) ac = new Ctx();
    if (ac.state === 'suspended') ac.resume();
    var t = ac.currentTime, o = ac.createOscillator(), g = ac.createGain();
    o.type = 'sine'; o.frequency.setValueAtTime(1400, t); o.frequency.exponentialRampToValueAtTime(600, t + 0.04);
    g.gain.setValueAtTime(v * 0.06, t); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.05);
    o.connect(g); g.connect(ac.destination); o.start(t); o.stop(t + 0.06);
  } catch (e) {}
}, true); })();"""


def sound_html(vol):
    v = max(0.0, min(1.0, vol / 100.0))
    return ("<script>(function(){var p=window.parent;p.__clickVol=%s;"
            "if(!p.__clickInstalled){p.__clickInstalled=true;var s=p.document.createElement('script');"
            "s.textContent=%s;p.document.head.appendChild(s);}})();</script>") % (v, json.dumps(SOUND_CORE))


col_h, col_s = st.columns([7, 2])
with col_s:
    with st.popover("⚙ Ayarlar / Settings"):
        lang_pick = st.radio("Dil / Language", ["Türkçe", "English"], key="lang_sel", horizontal=True)
        sound_on = st.toggle("Tıklama sesi / Click sound", value=True, key="snd_on")
        snd_v = st.slider("Ses seviyesi / Volume", 0, 100, 15, key="snd_vol", disabled=not sound_on)
LANG = "en" if lang_pick == "English" else "tr"
SND = snd_v if sound_on else 0
components.html(sound_html(SND), height=0)

with col_h:
    st.markdown(f"""
    <div class="industrial-header">
        <h1 style="color:#fff;margin:0;font-size:38px;font-weight:800;letter-spacing:0.5px;">{tx("Uzay Yaşam Destek Simülatörü", "Space Life Support Simulator")}</h1>
        <p style="color:#8b949e;margin:8px 0 0 0;font-size:16px;">{tx("NASA Space Apps Challenge & TÜBİTAK 2204 Projesi | Endüstriyel Biyoreaktör Dijital İkizi", "NASA Space Apps Challenge & TÜBİTAK 2204 Project | Industrial Bioreactor Digital Twin")}</p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# 30 TÜRLÜK BİLİMSEL VERİTABANI
# ============================================================
algae_db = {
    "Synechococcus elongatus": {
        "max_verim": 1.1, "opt_temp_min": 30, "opt_temp_max": 35, "opt_ph": "7.5-8.2", "ideal_isik": "Turuncu/Kırmızı", "grup": "Siyanobakteri",
        "boyut_deger": 1.5, "boyut": "1.0 - 2.0 µm", "habitat": "Tatlı su gölleri ve okyanus yüzeyi", "renk": "Mavi-Yeşil",
        "yasam_dongusu": "İkili bölünme (Binary fission) ile hızlı eşeysiz çoğalma.",
        "tanitim": "Tatlı sularda ve okyanus yüzeyinde serbest yaşayan prokaryotik siyanobakteridir. Yüksek karbon fiksasyonu ve fotosentetik oksijen üretim kapasitesi sayesinde ECLSS uzay yaşam destek sistemlerinin en kritik adaylarından biridir.",
        "dosya_adi": "synechococcus.png", "tip": "cubuk", "renk_kod": "#2ea043"
    },
    "Scenedesmus obliquus": {
        "max_verim": 0.95, "opt_temp_min": 20, "opt_temp_max": 28, "opt_ph": "6.8-7.5", "ideal_isik": "Geniş Spektrum", "grup": "Yeşil Alg",
        "boyut_deger": 15.0, "boyut": "10 - 25 µm", "habitat": "Tatlı su göletleri", "renk": "Klorofil Yeşili",
        "yasam_dongusu": "4 veya 8 hücreli cenobium kolonileri oluşturarak çoğalma.",
        "tanitim": "Tatlı su ekosistemlerinde yaygın bulunan, endüstriyel baca gazı filtrasyonu ve CO2 zenginleştirme sistemlerinde üstün performans gösteren koloni oluşturucu yeşil algtir. Stres altında hücre içi lipit biriktirir.",
        "dosya_adi": "scenedesmus.png", "tip": "koloni", "renk_kod": "#3fb950"
    },
    "Chlorella vulgaris": {
        "max_verim": 1.0, "opt_temp_min": 25, "opt_temp_max": 30, "opt_ph": "6.5-7.0", "ideal_isik": "Kırmızı/Mavi LED", "grup": "Yeşil Alg",
        "boyut_deger": 5.0, "boyut": "2 - 10 µm", "habitat": "Tatlı su ve sulak alanlar", "renk": "Koyu Yeşil",
        "yasam_dongusu": "Ana hücre içinde 4-8 adet otoşor oluşumu ve hücre duvarı patlaması.",
        "tanitim": "Uzay biyolojisi ve kapalı ekosistem deneylerinin altın standardı olan model mikroalgtir. Yüksek protein profili ve olağanüstü hızlı bölünme hızıyla astronotların oksijen ve besin döngüsünü destekler.",
        "dosya_adi": "chlorella.png", "tip": "kure", "renk_kod": "#238636"
    },
    "Chlorella pyrenoidosa": {
        "max_verim": 0.9, "opt_temp_min": 25, "opt_temp_max": 28, "opt_ph": "6.8-7.2", "ideal_isik": "Dengeli PAR LED", "grup": "Yeşil Alg",
        "boyut_deger": 5.5, "boyut": "3 - 8 µm", "habitat": "Tatlı su gölleri", "renk": "Canlı Yeşil",
        "yasam_dongusu": "Mitoz bölünme ve fotosentetik özümseme döngüsü.",
        "tanitim": "Tatlı su ekosistemlerinde yaşayan ve gaz transfer verimliliği açısından fotobiyoreaktör mühendisliğinde sıkça tercih edilen mikroalgtir. Atmosferik karbondioksiti absorbe ederek yüksek saflıkta oksijen üretir.",
        "dosya_adi": "", "tip": "kure", "renk_kod": "#2ea043"
    },
    "Nannochloropsis oculata": {
        "max_verim": 0.8, "opt_temp_min": 20, "opt_temp_max": 25, "opt_ph": "8.0-8.5", "ideal_isik": "Yüksek Yoğunluk", "grup": "Eustigmatophyte",
        "boyut_deger": 3.0, "boyut": "2 - 4 µm", "habitat": "Deniz ve tuzlu lagünler", "renk": "Altın Yeşimi",
        "yasam_dongusu": "Basit hücre bölünmesi ve EPA sentezleme döngüsü.",
        "tanitim": "Hücre çapının aşırı küçük olması sayesinde reaktör içinde mükemmel ışık penetrasyonu sağlayan denizel mikroalgtir. Yoğun kültürlerde dahi gölgeleme etkisini en aza indirir.",
        "dosya_adi": "nannochloropsis.png", "tip": "kure", "renk_kod": "#d29922"
    },
    "Arthrospira platensis (Spirulina)": {
        "max_verim": 0.95, "opt_temp_min": 35, "opt_temp_max": 38, "opt_ph": "9.0-11.0", "ideal_isik": "Turuncu/Kırmızı", "grup": "Siyanobakteri",
        "boyut_deger": 300.0, "boyut": "100 - 500 µm", "habitat": "Alkali soda gölleri", "renk": "Koyu Mavi-Yeşil",
        "yasam_dongusu": "Hormogonya parçalanması ve spiral iplikçik uzaması.",
        "tanitim": "Yüksek alkali ortamlarda yaşadığı için steril kültür imkanı sunan siyanobakteridir. Fikosiyanin pigmenti turuncu-kırmızı ışığı fevkalade absorbe ederek fotosentez verimini zirveye taşır.",
        "dosya_adi": "spirulina.png", "tip": "spiral", "renk_kod": "#1f6feb"
    },
    "Dunaliella salina": {
        "max_verim": 0.75, "opt_temp_min": 25, "opt_temp_max": 32, "opt_ph": "7.5-9.0", "ideal_isik": "Yüksek Şiddet", "grup": "Yeşil Alg",
        "boyut_deger": 12.0, "boyut": "10 - 15 µm", "habitat": "Aşırı tuzlu deniz tuzlaları", "renk": "Turuncu-Kırmızı / Yeşil",
        "yasam_dongusu": "Biflagellat hareketli evre ve osmotik kistleşme.",
        "tanitim": "Sert hücre duvarı olmayan, aşırı tuzlu ortamlarda osmotik dengesini koruyabilen ekstremofilik algtir. Güneş ışığı ve tuz stresinde beta-karoten biriktirerek antioksidan kapasite sunar.",
        "dosya_adi": "dunaliella.png", "tip": "kamcili", "renk_kod": "#f0883e"
    },
    "Porphyridium cruentum": {
        "max_verim": 0.7, "opt_temp_min": 20, "opt_temp_max": 25, "opt_ph": "7.5-8.0", "ideal_isik": "Yeşil/Sarı", "grup": "Kırmızı Alg",
        "boyut_deger": 9.0, "boyut": "8 - 10 µm", "habitat": "Deniz kıyıları", "renk": "Derin Kırmızı",
        "yasam_dongusu": "Polisakkarit kapsül salgılama ve monospor üretimi.",
        "tanitim": "Hücre dışına salgıladığı yoğun müsilaj tabakası ve fikoeritrin pigmenti sayesinde derin katmanlarda dahi yeşil ışığı fotosentez enerjisine dönüştürebilen kırmızı alg türüdür.",
        "dosya_adi": "porphyridium.png", "tip": "kapsullu", "renk_kod": "#da3633"
    },
    "Chlamydomonas reinhardtii": {
        "max_verim": 0.7, "opt_temp_min": 22, "opt_temp_max": 25, "opt_ph": "7.0-7.2", "ideal_isik": "Mavi-Kırmızı", "grup": "Yeşil Alg",
        "boyut_deger": 15.0, "boyut": "10 - 20 µm", "habitat": "Nemli toprak ve sulak alanlar", "renk": "Çimen Yeşili",
        "yasam_dongusu": "Kamçılı yüzme evresi ve eşeyli gamet oluşumu.",
        "tanitim": "İki kamçısı sayesinde sıvı içinde aktif hareket edebilen, moleküler biyoloji çalışmalarında dünya çapında model olarak kabul edilen kamçılı yeşil algtir.",
        "dosya_adi": "chlamydomonas.png", "tip": "kamcili", "renk_kod": "#2ea043"
    },
    "Haematococcus pluvialis": {
        "max_verim": 0.6, "opt_temp_min": 20, "opt_temp_max": 26, "opt_ph": "7.0-7.4", "ideal_isik": "Mavi/Yeşil - UV", "grup": "Yeşil Alg",
        "boyut_deger": 35.0, "boyut": "20 - 50 µm", "habitat": "Tatlı su kaya havuzları", "renk": "Kan Kırmızısı / Yeşil",
        "yasam_dongusu": "Kamçılı formdan kalın çeperli astaksantin kistine geçiş.",
        "tanitim": "Çevresel stresle karşılaştığında astaksantin üreterek kırmızı kist evresine geçen ve uzay radyasyonuna karşı olağanüstü direnç sergileyen mikroalgtir.",
        "dosya_adi": "haematococcus.png", "tip": "kist", "renk_kod": "#f85149"
    },
    "Spirulina maxima": {"max_verim": 0.85, "opt_temp_min": 32, "opt_temp_max": 37, "opt_ph": "9.2-10.5", "ideal_isik": "Turuncu/Kırmızı", "grup": "Siyanobakteri", "boyut_deger": 400.0, "boyut": "400 µm", "habitat": "Orta Amerika alkali gölleri", "renk": "Koyu Mavi-Yeşil", "yasam_dongusu": "Spiral filament uzaması.", "tanitim": "Orta Amerika'nın alkali soda göllerine adapte olmuş, yüksek protein içeriğiyle öne çıkan spiral formlu siyanobakteridir.", "dosya_adi": "", "tip": "spiral", "renk_kod": "#1f6feb"},
    "Anabaena azollae": {"max_verim": 0.65, "opt_temp_min": 24, "opt_temp_max": 30, "opt_ph": "6.8-7.8", "ideal_isik": "Geniş Spektrum", "grup": "Siyanobakteri", "boyut_deger": 5.0, "boyut": "4-6 µm", "habitat": "Pirinç tarlaları", "renk": "Zeytin Yeşili", "yasam_dongusu": "Heterosist hücrelerinde azot fiksasyonu.", "tanitim": "Su eğrelti otları ile ortak yaşayarak atmosfer azotunu bitkinin kullanabileceği forma dönüştüren simbiyotik siyanobakteridir.", "dosya_adi": "", "tip": "filament", "renk_kod": "#859f50"},
    "Nostoc commune": {"max_verim": 0.55, "opt_temp_min": 18, "opt_temp_max": 26, "opt_ph": "7.0-8.0", "ideal_isik": "Gün Işığı", "grup": "Siyanobakteri", "boyut_deger": 1000.0, "boyut": "Makro koloni", "habitat": "Toprak ve tundralar", "renk": "Kahverengi", "yasam_dongusu": "Jelatinöz makro koloniler ve akinet oluşumu.", "tanitim": "Kuraklığa ve dona karşı koruyucu kılıf geliştirerek karasal ekosistemlerde yıllarca uykuda kalabilen dirençli siyanobakteridir.", "dosya_adi": "", "tip": "koloni", "renk_kod": "#89574e"},
    "Synechocystis sp. PCC 6803": {"max_verim": 1.0, "opt_temp_min": 30, "opt_temp_max": 34, "opt_ph": "7.5-8.2", "ideal_isik": "Kırmızı/Mavi", "grup": "Siyanobakteri", "boyut_deger": 2.2, "boyut": "1.5-3 µm", "habitat": "Tatlı su", "renk": "Mavi-Yeşil", "yasam_dongusu": "Simetrik ikili bölünme.", "tanitim": "Genom dizilimi tamamen çözülmüş, fotosentez ve solunum etkileşimlerini incelemek için kullanılan model siyanobakteridir.", "dosya_adi": "", "tip": "kure", "renk_kod": "#3fb950"},
    "Prochlorococcus marinus": {"max_verim": 0.5, "opt_temp_min": 22, "opt_temp_max": 28, "opt_ph": "8.0-8.3", "ideal_isik": "Mavi LED", "grup": "Siyanobakteri", "boyut_deger": 0.6, "boyut": "0.5-0.7 µm", "habitat": "Açık okyanuslar", "renk": "Sarı-Yeşil", "yasam_dongusu": "Derin deniz fotik zonunda adaptasyon.", "tanitim": "Dünyadaki en küçük ve okyanuslarda en yüksek birey sayısına sahip fotosentetik organizmadır.", "dosya_adi": "", "tip": "kure", "renk_kod": "#d29922"},
    "Botryococcus braunii": {"max_verim": 0.45, "opt_temp_min": 23, "opt_temp_max": 28, "opt_ph": "6.5-7.5", "ideal_isik": "Yüksek Yoğunluk", "grup": "Yeşil Alg", "boyut_deger": 200.0, "boyut": "50-500 µm", "habitat": "Tatlı su gölleri", "renk": "Sarımsı Kahverengi", "yasam_dongusu": "Hücre dışı matrikste hidrokarbon biriktirme.", "tanitim": "Hücre duvarı dışında akaryakıt benzeri hidrokarbon damlacıkları sentezleyebilen koloni yapılı yeşil algtir.", "dosya_adi": "", "tip": "koloni", "renk_kod": "#e3b341"},
    "Chlorella sorokiniana": {"max_verim": 1.2, "opt_temp_min": 32, "opt_temp_max": 38, "opt_ph": "6.8-7.4", "ideal_isik": "Kırmızı/Mavi", "grup": "Yeşil Alg", "boyut_deger": 3.5, "boyut": "2-5 µm", "habitat": "Sıcak tatlı su", "renk": "Parlak Yeşil", "yasam_dongusu": "Yüksek sıcaklıkta hızlı hücre döngüsü.", "tanitim": "Endüstriyel sıcaklıklara ve yoğun ışığa dayanıklı, türler arasında en hızlı ikiye bölünme oranına sahip varyetedir.", "dosya_adi": "", "tip": "kure", "renk_kod": "#2ea043"},
    "Scenedesmus acutus": {"max_verim": 1.05, "opt_temp_min": 22, "opt_temp_max": 29, "opt_ph": "7.0-7.6", "ideal_isik": "Geniş Spektrum", "grup": "Yeşil Alg", "boyut_deger": 13.0, "boyut": "8-18 µm", "habitat": "Tatlı su göletleri", "renk": "Çimen Yeşili", "yasam_dongusu": "İğsi hücrelerin 4lü gruplar halinde açılması.", "tanitim": "Uç kısımları iğsi formda olan ve atık su arıtımı ile biyokütle üretiminde yüksek verim sunan tatlı su yeşil algidir.", "dosya_adi": "", "tip": "koloni", "renk_kod": "#3fb950"},
    "Tetraselmis chuii": {"max_verim": 0.75, "opt_temp_min": 20, "opt_temp_max": 26, "opt_ph": "7.5-8.5", "ideal_isik": "Mavi/Yeşil", "grup": "Prasinophyte", "boyut_deger": 12.0, "boyut": "10-14 µm", "habitat": "Kıyı deniz suları", "renk": "Soluk Yeşil", "yasam_dongusu": "Dört kamçılı motil evre.", "tanitim": "Dört kamçısı bulunan ve deniz suyu kültürlerinde yüksek lipid profili ile bilinen dayanıklı prasinofittir.", "dosya_adi": "", "tip": "kamcili", "renk_kod": "#56d364"},
    "Phaeodactylum tricornutum": {"max_verim": 0.8, "opt_temp_min": 18, "opt_temp_max": 24, "opt_ph": "7.8-8.4", "ideal_isik": "Geniş Spektrum", "grup": "Diatom", "boyut_deger": 25.0, "boyut": "20-30 µm", "habitat": "Kıyı suları", "renk": "Kahverengi", "yasam_dongusu": "Üç farklı morfolojik form değiştirme yeteneği.", "tanitim": "Silisli hücre duvarına zorunlu bağımlı olmayan ve koşullara göre form değiştirebilen esnek diatom türüdür.", "dosya_adi": "", "tip": "diatom", "renk_kod": "#b08800"},
    "Isochrysis galbana": {"max_verim": 0.7, "opt_temp_min": 20, "opt_temp_max": 27, "opt_ph": "8.0-8.5", "ideal_isik": "Mavi LED", "grup": "Haptophyte", "boyut_deger": 5.0, "boyut": "4-6 µm", "habitat": "Ilıman deniz", "renk": "Altın Kahverengi", "yasam_dongusu": "Haptonem ile beslenme ve çoğalma.", "tanitim": "EPA ve DHA gibi değerli omega-3 yağ asitleri açısından zengin, uzay besin zinciri entegrasyonuna uygun denizel mikroalgtir.", "dosya_adi": "", "tip": "kamcili", "renk_kod": "#e3b341"},
    "Skeletonema costatum": {"max_verim": 0.9, "opt_temp_min": 15, "opt_temp_max": 22, "opt_ph": "8.0-8.8", "ideal_isik": "Dengeli PAR", "grup": "Diatom", "boyut_deger": 8.5, "boyut": "5-12 µm", "habitat": "Deniz kıyıları", "renk": "Altın Sarı", "yasam_dongusu": "Silis köprüleriyle silindirik zincir oluşturma.", "tanitim": "Hücreler arası silis köprüleriyle zincirler oluşturan ve kıyı ekosistemlerinde birincil oksijen katkısı sağlayan diatomdur.", "dosya_adi": "", "tip": "zincir", "renk_kod": "#d29922"},
    "Auxenochlorella protothecoides": {"max_verim": 0.95, "opt_temp_min": 25, "opt_temp_max": 30, "opt_ph": "6.0-7.0", "ideal_isik": "Kırmızı/Mavi", "grup": "Yeşil Alg", "boyut_deger": 5.0, "boyut": "3-7 µm", "habitat": "Toprak ve tatlı su", "renk": "Açık Yeşil", "yasam_dongusu": "Organik karbonla heterotrofik büyüme.", "tanitim": "Hem ışıkla fotosentez yapabilen hem de glikoz varlığında ışıksız ortamda rekor düzeyde çoğalabilen esnek algtir.", "dosya_adi": "", "tip": "kure", "renk_kod": "#56d364"},
    "Monoraphidium griffithii": {"max_verim": 0.6, "opt_temp_min": 20, "opt_temp_max": 26, "opt_ph": "7.0-7.8", "ideal_isik": "Geniş Spektrum", "grup": "Yeşil Alg", "boyut_deger": 30.0, "boyut": "20-40 µm", "habitat": "Tatlı su gölleri", "renk": "Sarımsı Yeşil", "yasam_dongusu": "Kavisli iğsi hücrelerin serbest yayılımı.", "tanitim": "Tatlı su göllerinde serbest asılı yaşayan, ince ve kavisli iğsi hücre morfolojisine sahip yeşil algdır.", "dosya_adi": "", "tip": "isi", "renk_kod": "#3fb950"},
    "Chlorella emersonii": {"max_verim": 1.0, "opt_temp_min": 26, "opt_temp_max": 32, "opt_ph": "6.5-7.2", "ideal_isik": "Kırmızı LED", "grup": "Yeşil Alg", "boyut_deger": 5.5, "boyut": "3-8 µm", "habitat": "Tatlı su ve toprak", "renk": "Koyu Yeşil", "yasam_dongusu": "Stres altında nişasta biriktirme.", "tanitim": "Nitrojen kısıtı altında hücre içinde yüksek yoğunlukta karbonhidrat biriktirme kapasitesiyle biyo-enerji çalışmalarında kullanılan varyetedir.", "dosya_adi": "", "tip": "kure", "renk_kod": "#238636"},
    "Aphanizomenon flos-aquae": {"max_verim": 0.7, "opt_temp_min": 22, "opt_temp_max": 28, "opt_ph": "7.5-8.5", "ideal_isik": "Gün Işığı", "grup": "Siyanobakteri", "boyut_deger": 300.0, "boyut": "200-400 µm", "habitat": "Ötrofik göller", "renk": "Mavi-Yeşil", "yasam_dongusu": "Gaz vakuolüyle yüzeye çıkma.", "tanitim": "Tatlı su göllerinde filamentli demetler oluşturan, doğal azot bağlama yeteneği yüksek siyanobakteri türüdür.", "dosya_adi": "", "tip": "filament", "renk_kod": "#1f6feb"},
    "Arthrospira fusiformis": {"max_verim": 0.8, "opt_temp_min": 33, "opt_temp_max": 39, "opt_ph": "9.5-11.0", "ideal_isik": "Turuncu/Kırmızı", "grup": "Siyanobakteri", "boyut_deger": 250.0, "boyut": "150-400 µm", "habitat": "Doğu Afrika soda gölleri", "renk": "Parlak Mavi", "yasam_dongusu": "Yüksek pH altında spiral trichome uzaması.", "tanitim": "Doğu Afrika Rift Vadisi'nin ekstrem soda göllerine adapte olmuş, alkali koşullarda maksimum biyokütle üreten Spirulina akrabasıdır.", "dosya_adi": "", "tip": "spiral", "renk_kod": "#58a6ff"},
    "Dictyochloris braunii": {"max_verim": 0.55, "opt_temp_min": 20, "opt_temp_max": 25, "opt_ph": "6.8-7.5", "ideal_isik": "Yeşil Spektrum", "grup": "Yeşil Alg", "boyut_deger": 22.0, "boyut": "15-30 µm", "habitat": "Toprak ve ağaç kabukları", "renk": "Zeytin Yeşili", "yasam_dongusu": "Çok çekirdekli evre ve zoospor üretimi.", "tanitim": "Nemli toprak yüzeylerinde ve ağaç kabuklarında kolonize olan, çok çekirdekli yapı evreleri gösteren karasal mikroalgtir.", "dosya_adi": "", "tip": "kure", "renk_kod": "#859f50"},
    "Haematococcus lacustris": {"max_verim": 0.6, "opt_temp_min": 20, "opt_temp_max": 25, "opt_ph": "7.0-7.3", "ideal_isik": "Mavi/UV", "grup": "Yeşil Alg", "boyut_deger": 37.0, "boyut": "25-50 µm", "habitat": "Tatlı su havuzları", "renk": "Kan Kırmızısı", "yasam_dongusu": "Güneş ve UV altında astaksantin kist formasyonu.", "tanitim": "Astaksantin üretim verimliliği en yüksek olan, geçici kaya havuzlarında yaşayıp kırmızı kist evresiyle bilinen tatlı su mikroalgtir.", "dosya_adi": "", "tip": "kist", "renk_kod": "#da3633"},
    "Synechococcus sp. WH8102": {"max_verim": 1.1, "opt_temp_min": 28, "opt_temp_max": 33, "opt_ph": "7.8-8.2", "ideal_isik": "Mavi/Turuncu", "grup": "Siyanobakteri", "boyut_deger": 1.2, "boyut": "0.8-1.5 µm", "habitat": "Subtropikal denizler", "renk": "Deniz Mavisi", "yasam_dongusu": "Demir kıtlığına karşı özel protein geliştirme.", "tanitim": "Subtropikal ve tropikal deniz ekosistemleri için özel optimize edilmiş, yüksek üreme hızına sahip model denizel siyanobakteridir.", "dosya_adi": "", "tip": "cubuk", "renk_kod": "#388bfd"}
}

# ============================================================
# SABİTLER VE ÇEVİRİ TABLOLARI
# ============================================================
ALG_NAMES = list(algae_db.keys())
LIGHTS = ["Kırmızı/Mavi LED", "Turuncu/Kırmızı", "Beyaz/Gün Işığı", "Geniş Spektrum",
          "Yüksek Yoğunluk", "Dengeli PAR LED", "Yeşil/Sarı", "Mavi-Kırmızı"]
IMG_DIR = "algler_gorseller"
HUMAN_O2_NEED = 780.0
AI_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5")
DEF_NOT = "Parametreler yaklaşık literatür değerleridir; kendi türünüz için deneysel doğrulama yapın."
DEF_NOT_EN = "Parameters are approximate literature values; validate experimentally for your own strain."

LIGHT_EN = {
    "Kırmızı/Mavi LED": "Red/Blue LED", "Turuncu/Kırmızı": "Orange/Red", "Beyaz/Gün Işığı": "White/Daylight",
    "Geniş Spektrum": "Broad spectrum", "Yüksek Yoğunluk": "High intensity", "Dengeli PAR LED": "Balanced PAR LED",
    "Yeşil/Sarı": "Green/Yellow", "Mavi-Kırmızı": "Blue/Red", "Mavi/Yeşil - UV": "Blue/Green - UV",
    "Gün Işığı": "Daylight", "Yüksek Şiddet": "High irradiance", "Mavi LED": "Blue LED", "Kırmızı LED": "Red LED",
    "Mavi/UV": "Blue/UV", "Yeşil Spektrum": "Green spectrum", "Mavi/Turuncu": "Blue/Orange",
    "Mavi/Yeşil": "Blue/Green", "Dengeli PAR": "Balanced PAR", "Kırmızı/Mavi": "Red/Blue",
}
GRP_EN = {"Siyanobakteri": "Cyanobacteria", "Yeşil Alg": "Green alga", "Kırmızı Alg": "Red alga",
          "Diatom": "Diatom", "Eustigmatophyte": "Eustigmatophyte", "Prasinophyte": "Prasinophyte",
          "Haptophyte": "Haptophyte"}
GUV = {"dusuk": ("düşük", "low"), "düşük": ("düşük", "low"), "orta": ("orta", "medium"),
       "yuksek": ("yüksek", "high"), "yüksek": ("yüksek", "high"), "çok düşük": ("çok düşük", "very low")}


def lt(s):
    return LIGHT_EN.get(s, s) if LANG == "en" else s


def gr(s):
    return GRP_EN.get(s, s) if LANG == "en" else s


def guv(g):
    pair = GUV.get(str(g).lower(), (str(g), str(g)))
    return pair[1] if LANG == "en" else pair[0]


# Türkçe / yaygın yazımları PubChem'in anlayacağı İngilizce adlara çevirir
TR_ALIAS = {
    "glikoz": "glucose", "glukoz": "glucose", "dekstroz": "dextrose", "sakkaroz": "sucrose",
    "tuz": "sodium chloride", "sodyum klorür": "sodium chloride", "potasyum klorür": "potassium chloride",
    "magnezyum sülfat": "magnesium sulfate", "kalsiyum klorür": "calcium chloride",
    "demir sülfat": "ferrous sulfate", "demir klorür": "iron(III) chloride",
    "sodyum bikarbonat": "sodium bicarbonate", "sodyum karbonat": "sodium carbonate",
    "potasyum fosfat": "dipotassium hydrogen phosphate", "potasyum sülfat": "potassium sulfate",
    "sodyum sülfat": "sodium sulfate", "sodyum nitrat": "sodium nitrate", "potasyum nitrat": "potassium nitrate",
    "amonyum klorür": "ammonium chloride", "amonyum sülfat": "ammonium sulfate", "üre": "urea",
    "kurşun": "lead", "kurşun nitrat": "lead nitrate", "kadmiyum": "cadmium", "kadmiyum klorür": "cadmium chloride",
    "civa": "mercury", "civa klorür": "mercuric chloride", "bakır sülfat": "copper(II) sulfate",
    "çinko sülfat": "zinc sulfate", "kobalt klorür": "cobalt chloride", "nikel klorür": "nickel chloride",
    "mangan klorür": "manganese chloride", "borik asit": "boric acid", "sitrik asit": "citric acid",
    "askorbik asit": "ascorbic acid", "kobalamin": "cyanocobalamin", "biyotin": "biotin", "tiamin": "thiamine",
    "gliserol": "glycerol", "hidrojen peroksit": "hydrogen peroxide", "kloramfenikol": "chloramphenicol",
    "fenol": "phenol", "etanol": "ethanol", "atrazin": "atrazine", "sodyum silikat": "sodium silicate",
    "glisin": "glycine",
}

# Deneylerde en sık kullanılan 50 madde: (Türkçe ad, İngilizce ad, formül, molekül ağırlığı g/mol)
PRESETS = [
    ("Sodyum nitrat", "Sodium nitrate", "NaNO3", 84.99),
    ("Potasyum nitrat", "Potassium nitrate", "KNO3", 101.10),
    ("Amonyum klorür", "Ammonium chloride", "NH4Cl", 53.49),
    ("Üre", "Urea", "CH4N2O", 60.06),
    ("Dipotasyum hidrojen fosfat", "Dipotassium hydrogen phosphate", "K2HPO4", 174.18),
    ("Potasyum dihidrojen fosfat", "Potassium dihydrogen phosphate", "KH2PO4", 136.09),
    ("Disodyum hidrojen fosfat", "Disodium hydrogen phosphate", "Na2HPO4", 141.96),
    ("Magnezyum sülfat", "Magnesium sulfate", "MgSO4·7H2O", 246.47),
    ("Kalsiyum klorür", "Calcium chloride", "CaCl2", 110.98),
    ("Kalsiyum nitrat", "Calcium nitrate", "Ca(NO3)2·4H2O", 236.15),
    ("Magnezyum klorür", "Magnesium chloride", "MgCl2", 95.21),
    ("Sodyum klorür", "Sodium chloride", "NaCl", 58.44),
    ("Potasyum klorür", "Potassium chloride", "KCl", 74.55),
    ("Sodyum sülfat", "Sodium sulfate", "Na2SO4", 142.04),
    ("Potasyum sülfat", "Potassium sulfate", "K2SO4", 174.26),
    ("Amonyum sülfat", "Ammonium sulfate", "(NH4)2SO4", 132.14),
    ("Sodyum bikarbonat", "Sodium bicarbonate", "NaHCO3", 84.01),
    ("Sodyum karbonat", "Sodium carbonate", "Na2CO3", 105.99),
    ("Sodyum asetat", "Sodium acetate", "C2H3NaO2", 82.03),
    ("Glikoz", "Glucose", "C6H12O6", 180.16),
    ("Sakkaroz", "Sucrose", "C12H22O11", 342.30),
    ("Gliserol", "Glycerol", "C3H8O3", 92.09),
    ("Sitrik asit", "Citric acid", "C6H8O7", 192.12),
    ("Sodyum silikat", "Sodium silicate", "Na2SiO3", 122.06),
    ("Disodyum EDTA", "Disodium EDTA", "C10H14N2Na2O8", 336.21),
    ("Demir(II) sülfat", "Iron(II) sulfate", "FeSO4·7H2O", 278.01),
    ("Demir(III) klorür", "Iron(III) chloride", "FeCl3", 162.20),
    ("Borik asit", "Boric acid", "H3BO3", 61.83),
    ("Mangan(II) klorür", "Manganese chloride", "MnCl2·4H2O", 197.91),
    ("Çinko sülfat", "Zinc sulfate", "ZnSO4·7H2O", 287.56),
    ("Bakır(II) sülfat", "Copper sulfate", "CuSO4·5H2O", 249.69),
    ("Kobalt(II) klorür", "Cobalt chloride", "CoCl2·6H2O", 237.93),
    ("Sodyum molibdat", "Sodium molybdate", "Na2MoO4·2H2O", 241.95),
    ("Nikel(II) klorür", "Nickel chloride", "NiCl2·6H2O", 237.69),
    ("Sodyum selenit", "Sodium selenite", "Na2SeO3", 172.94),
    ("Potasyum iyodür", "Potassium iodide", "KI", 166.00),
    ("Krom(III) klorür", "Chromium chloride", "CrCl3", 158.36),
    ("Siyanokobalamin (B12)", "Cyanocobalamin", "C63H88CoN14O14P", 1355.37),
    ("Tiamin (B1)", "Thiamine", "C12H17ClN4OS·HCl", 337.27),
    ("Biyotin (B7)", "Biotin", "C10H16N2O3S", 244.31),
    ("Glisin", "Glycine", "C2H5NO2", 75.07),
    ("Kurşun(II) nitrat", "Lead nitrate", "Pb(NO3)2", 331.20),
    ("Kadmiyum klorür", "Cadmium chloride", "CdCl2", 183.31),
    ("Civa(II) klorür", "Mercury chloride", "HgCl2", 271.50),
    ("Atrazin", "Atrazine", "C8H14ClN5", 215.68),
    ("Hidrojen peroksit", "Hydrogen peroxide", "H2O2", 34.01),
    ("Kloramfenikol", "Chloramphenicol", "C11H12Cl2N2O5", 323.13),
    ("Fenol", "Phenol", "C6H6O", 94.11),
    ("Etanol", "Ethanol", "C2H6O", 46.07),
    ("Askorbik asit (C vitamini)", "Ascorbic acid", "C6H8O6", 176.12),
]
assert len(PRESETS) == 50

# ============================================================
# ARAŞTIRILMIŞ ETKİ TABLOSU (genel literatür özeti, basitleştirilmiş)
# ============================================================
HALOTOLERANT = {"Dunaliella salina", "Tetraselmis chuii", "Nannochloropsis oculata",
                "Phaeodactylum tricornutum", "Isochrysis galbana", "Skeletonema costatum",
                "Arthrospira platensis (Spirulina)", "Arthrospira fusiformis", "Spirulina maxima"}
HETEROTROF = {"Auxenochlorella protothecoides", "Chlorella vulgaris"}

KNOWN = [
    {"aliases": ["NaNO3", "sodyum nitrat", "sodium nitrate", "nitrat", "nitrate", "KNO3", "potasyum nitrat", "potassium nitrate"],
     "tur": "besin", "ks": 60,
     "ozet": "Başlıca azot kaynağı. Protein, klorofil ve nükleik asit sentezi için gereklidir; azot kısıtında üretim düşer.",
     "ozet_en": "Main nitrogen source. Needed for protein, chlorophyll and nucleic acid synthesis; production falls under nitrogen limitation.",
     "not": "Temel ortamda azot yeterliyse ilave etkisi sınırlıdır (Liebig'in minimum yasası).",
     "not_en": "If the base medium already has enough nitrogen, the added effect is limited (Liebig's law of the minimum)."},
    {"aliases": ["K2HPO4", "potasyum fosfat", "potassium phosphate", "dipotassium hydrogen phosphate", "fosfat", "phosphate",
                 "KH2PO4", "potassium dihydrogen phosphate", "Na2HPO4", "disodium hydrogen phosphate"],
     "tur": "besin", "ks": 10,
     "ozet": "Fosfor kaynağı; ATP, DNA ve membran lipidleri için gereklidir.",
     "ozet_en": "Phosphorus source; required for ATP, DNA and membrane lipids."},
    {"aliases": ["NaHCO3", "sodyum bikarbonat", "sodium bicarbonate", "bikarbonat", "bicarbonate"],
     "tur": "besin", "ks": 300,
     "ozet": "İnorganik karbon kaynağı ve tampon. pH'ı stabilize eder, fotosentezde karbon sağlar.",
     "ozet_en": "Inorganic carbon source and buffer. Stabilises pH and supplies carbon for photosynthesis."},
    {"aliases": ["Na2CO3", "sodyum karbonat", "sodium carbonate"],
     "tur": "besin", "ks": 300,
     "ozet": "Alkali tampon ve karbon kaynağı; yüksek pH gerektiren türlerde (ör. Spirulina) kullanılır.",
     "ozet_en": "Alkaline buffer and carbon source; used for high-pH species such as Spirulina."},
    {"aliases": ["MgSO4", "magnezyum sülfat", "magnesium sulfate", "MgCl2", "magnezyum klorür", "magnesium chloride"],
     "tur": "besin", "ks": 20,
     "ozet": "Klorofilin merkez atomu Mg ve birçok enzimin kofaktörüdür.",
     "ozet_en": "Mg is the central atom of chlorophyll and a cofactor for many enzymes."},
    {"aliases": ["CaCl2", "kalsiyum klorür", "calcium chloride"],
     "tur": "besin", "ks": 10,
     "ozet": "Hücre duvarı ve hücre içi sinyalleşme için gereklidir.",
     "ozet_en": "Needed for cell wall and intracellular signalling."},
    {"aliases": ["K2SO4", "potasyum sülfat", "potassium sulfate"],
     "tur": "besin", "ks": 30,
     "ozet": "Potasyum ve kükürt kaynağı; ozmotik dengede rol oynar.",
     "ozet_en": "Potassium and sulphur source; plays a role in osmotic balance."},
    {"aliases": ["NH4Cl", "ammonium chloride", "amonyum klorür", "urea", "üre", "(NH4)2SO4", "ammonium sulfate", "amonyum sülfat"],
     "tur": "besin", "ks": 80,
     "ozet": "Azot kaynağı; amonyum hızlı alınır ancak yüksek dozda pH'ı düşürür ve bazı türleri baskılar.",
     "ozet_en": "Nitrogen source; ammonium is taken up quickly but high doses lower pH and inhibit some species."},
    {"aliases": ["FeSO4", "demir sülfat", "ferrous sulfate", "iron(II) sulfate", "iron sulfate", "ferric ammonium citrate", "demir amonyum sitrat"],
     "tur": "besin", "ks": 0.5,
     "ozet": "Fotosentez elektron taşıma zincirinin (ferredoksin, sitokromlar) bileşenidir; eksikliği verimi ciddi düşürür, fazlası serbest radikal üretebilir.",
     "ozet_en": "Component of the photosynthetic electron transport chain (ferredoxin, cytochromes); deficiency severely lowers yield, excess can generate free radicals."},
    {"aliases": ["EDTA", "etilendiamin tetraasetik asit", "disodium EDTA", "Na2EDTA"],
     "tur": "notr",
     "ozet": "Şelatlayıcı: serbest Fe ve diğer metalleri çözünür tutarak biyoyararlılığını artırır; kendisi doğrudan büyümeyi değiştirmez.",
     "ozet_en": "Chelator: keeps free Fe and other metals soluble, improving bioavailability; does not directly change growth."},
    {"aliases": ["sitrik asit", "citric acid"],
     "tur": "notr",
     "ozet": "Tampon ve demir şelatlayıcı olarak BG-11 gibi ortamlarda kullanılır.",
     "ozet_en": "Used as a buffer and iron chelator in media such as BG-11."},
    {"aliases": ["glukoz", "glikoz", "glucose", "dextrose", "dekstroz", "D-glucose"],
     "tur": "karbon", "kh": 2000,
     "ozet": "Heterotrofik büyümeyi destekler; fotoototrof türlerde ışık yetersizliği ve kontaminasyon riski doğurur.",
     "ozet_en": "Supports heterotrophic growth; in phototrophic species it causes light shortage and contamination risk."},
    {"aliases": ["NaCl", "sodyum klorür", "sodium chloride", "tuz", "salt", "KCl", "potassium chloride", "potasyum klorür",
                 "Na2SO4", "sodium sulfate", "sodyum sülfat"],
     "tur": "tuz",
     "ozet": "Osmotik stres: halotolerant türler için düşük dozlar uygundur, yüksek dozlar büyümeyi baskılar.",
     "ozet_en": "Osmotic stress: low doses suit halotolerant species, high doses suppress growth."},
    {"aliases": ["Pb", "kurşun", "lead", "Pb(NO3)2", "kurşun nitrat", "lead nitrate"],
     "tur": "toksik", "ec50": 0.5,
     "ozet": "Ağır metal; fotosentez, enzim ve membran hasarına yol açar. Yüksek toksisite.",
     "ozet_en": "Heavy metal; damages photosynthesis, enzymes and membranes. High toxicity."},
    {"aliases": ["Cd", "kadmiyum", "cadmium", "CdCl2", "cadmium chloride", "kadmiyum klorür"],
     "tur": "toksik", "ec50": 0.1,
     "ozet": "Çok toksik ağır metal; enzim inhibisyonu ve oksidatif stres oluşturur.",
     "ozet_en": "Very toxic heavy metal; causes enzyme inhibition and oxidative stress."},
    {"aliases": ["Cu", "bakır", "copper", "CuSO4", "bakır sülfat", "copper sulfate", "copper(II) sulfate"],
     "tur": "toksik", "ec50": 0.1,
     "ozet": "Düşük dozda mikro besin, yüksek dozda fotosentez inhibitörüdür.",
     "ozet_en": "Essential micronutrient at low dose; photosynthesis inhibitor at high dose."},
    {"aliases": ["Hg", "civa", "mercury", "HgCl2", "mercury chloride", "civa klorür", "mercuric chloride"],
     "tur": "toksik", "ec50": 0.05,
     "ozet": "Güçlü toksik; tiyol grupları içeren enzimleri bloke eder.",
     "ozet_en": "Strongly toxic; blocks thiol-containing enzymes."},
    {"aliases": ["atrazin", "atrazine"],
     "tur": "toksik", "ec50": 1.0,
     "ozet": "Triazin herbisiti; fotosistem II elektron taşınımını engeller.",
     "ozet_en": "Triazine herbicide; blocks electron transport at photosystem II.",
     "not": "EC50 değeri kaba bir aralıktır; tür ve maruz kalma süresine bağlıdır.",
     "not_en": "The EC50 value is a rough range; it depends on species and exposure time."},
    {"aliases": ["B12", "kobalamin", "cyanocobalamin", "vitamin B12", "siyanokobalamin"],
     "tur": "besin", "ks": 0.0005,
     "ozet": "Bazı alg türleri B12'ye bağımlıdır, bazıları sentezleyebilir; gereksinim türe özgüdür.",
     "ozet_en": "Some algae require B12, others synthesise it; the requirement is species-specific."},
    {"aliases": ["H2O2", "hidrojen peroksit", "hydrogen peroxide"],
     "tur": "toksik", "ec50": 20,
     "ozet": "Güçlü oksidan; hücre zarını ve pigmentleri oksitler. Düşük dozda kontaminasyon kontrolünde kullanılabilir.",
     "ozet_en": "Strong oxidant; damages membranes and pigments. Low doses are sometimes used for contamination control.",
     "not": "EC50 kaba bir aralıktır; kültür yoğunluğu ve maruz kalma süresine bağlıdır.",
     "not_en": "The EC50 is a rough range; it depends on culture density and exposure time."},
    {"aliases": ["kloramfenikol", "chloramphenicol"],
     "tur": "toksik", "ec50": 10,
     "ozet": "Antibiyotik; bakteriyel ve kloroplast protein sentezini engelleyebilir. Kontaminasyon kontrolünde kullanılır ancak alg büyümesini de azaltabilir.",
     "ozet_en": "Antibiotic; can inhibit bacterial and chloroplast protein synthesis. Used against contamination but may also reduce algal growth.",
     "not": "Etki türe ve konsantrasyona çok bağlıdır; değer yalnızca kaba bir yönlendirmedir.",
     "not_en": "The effect depends strongly on species and concentration; the value is only a rough guide."},
    {"aliases": ["askorbik asit", "ascorbic acid", "vitamin C", "vitamin C (askorbik asit)"],
     "tur": "notr",
     "ozet": "Antioksidan; oksidatif stresi azaltabilir, bazı türlerde küçük bir büyüme artışı görülebilir.",
     "ozet_en": "Antioxidant; may reduce oxidative stress and give a small growth gain in some species."},
    {"aliases": ["ZnSO4", "zinc sulfate", "çinko sülfat", "MnCl2", "manganese chloride", "mangan klorür",
                 "CoCl2", "cobalt chloride", "kobalt klorür", "NiCl2", "nickel chloride", "nikel klorür",
                 "Na2MoO4", "sodium molybdate", "sodyum molibdat", "H3BO3", "boric acid", "borik asit",
                 "Na2SeO3", "sodium selenite", "sodyum selenit", "KI", "potassium iodide", "potasyum iyodür",
                 "CrCl3", "chromium chloride", "krom klorür", "FeCl3", "iron(III) chloride", "demir klorür"],
     "tur": "mikro",
     "ozet": "Eser element: düşük dozda enzim kofaktörü olarak gerekli, yüksek dozda toksiktir.",
     "ozet_en": "Trace element: essential enzyme cofactor at low doses, toxic at high doses.",
     "not": "Eser element dozu türe ve ortama çok duyarlıdır; BG-11 gibi standart tarifler referans alınmalıdır.",
     "not_en": "Trace element doses are very sensitive to species and medium; use standard recipes such as BG-11 as reference."},
]
for _e in KNOWN:
    _e.setdefault("not", DEF_NOT)
    _e.setdefault("not_en", DEF_NOT_EN)

KNOWN_INDEX = {}
for _e in KNOWN:
    for _a in _e["aliases"]:
        KNOWN_INDEX[re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", _a).encode("ascii", "ignore").decode().lower())] = _e


def nkey(s):
    t = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", t)


def known_factor(e, conc, alg):
    t = e["tur"]
    if t == "besin":
        return 1 + 0.25 * conc / (e["ks"] + conc)
    if t == "toksik":
        return 1 / (1 + (conc / e["ec50"]) ** 2)
    if t == "tuz":
        ec = 8000 if alg in HALOTOLERANT else 3000
        return 1 / (1 + (conc / ec) ** 2)
    if t == "karbon":
        if alg in HETEROTROF:
            return 1 + 0.6 * conc / (conc + e["kh"])
        return 1 - 0.1 * conc / (conc + 1000)
    if t == "mikro":
        return (1 + 0.2 * conc / (conc + 0.05)) / (1 + (conc / 50) ** 2)
    return 1.0


# ============================================================
# PUBCHEM VE YAPAY ZEKA
# ============================================================
@st.cache_data(show_spinner=False, ttl=86400)
def pubchem_fetch(query):
    url = ("https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
           + quote(query, safe="") + "/property/MolecularFormula,MolecularWeight,IUPACName,CanonicalSMILES/JSON")
    with urllib.request.urlopen(url, timeout=12) as r:
        data = json.load(r)
    p = data["PropertyTable"]["Properties"][0]
    return {"cid": p.get("CID"), "formul": p.get("MolecularFormula", ""),
            "mw": float(p.get("MolecularWeight", 0) or 0),
            "iupac": p.get("IUPACName", ""), "smiles": p.get("CanonicalSMILES", "")}


def pubchem_lookup(query):
    try:
        return {"ok": True, **pubchem_fetch(query)}
    except urllib.error.HTTPError as e:
        return {"ok": False, "code": e.code}
    except Exception:
        return {"ok": False, "code": 0}


SCHEMA_TR = ('{"etki": "artirici | engelleyici | notr | toksik", '
             '"carpan": <0.0-2.0 arası sayı; temel büyüme hızına çarpan, 1.0 = etkisiz>, '
             '"guven": "dusuk | orta | yuksek", '
             '"aciklama": "<en fazla 2 cümle>", '
             '"uyari": "<en fazla 1 cümle, belirsizlik notu>"}')


@st.cache_data(show_spinner=False, ttl=600)
def ai_predict(alg, group, name, formul, mw, conc, lang):
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return {"hata": "ANTHROPIC_API_KEY tanımlı değil"}
    ans = "English" if lang == "en" else "Türkçe"
    prompt = (
        "Sen alg biyoteknolojisi uzmanısın. Aşağıdaki fotobiyoreaktörde yetiştirilen mikroalg/siyanobakteri "
        "türüne, belirtilen konsantrasyonda eklenen kimyasalın büyüme hızı üzerindeki etkisini tahmin et.\n\n"
        f"Tür: {alg} (grup: {group})\n"
        f"Madde: {name}\n"
        f"Kimyasal formül: {formul or 'bilinmiyor'}\n"
        f"Molekül ağırlığı: {mw or 'bilinmiyor'} g/mol\n"
        f"Konsantrasyon: {conc} mg/L\n\n"
        "Yalnızca JSON döndür, başka metin, açıklama veya markdown kullanma. Şema: " + SCHEMA_TR + "\n"
        f"'aciklama' ve 'uyari' alanlarını {ans} dilinde yaz.\n"
        "Bilmediğin bir maddeyse guven değerini \"dusuk\" yap ve carpan'ı 1.0'a yakın tut."
    )
    body = json.dumps({"model": AI_MODEL, "max_tokens": 500,
                       "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body, method="POST",
        headers={"content-type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            resp = json.load(r)
        text = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
        js = json.loads(text[text.find("{"): text.rfind("}") + 1])
        carpan = min(2.0, max(0.0, float(js.get("carpan", 1.0))))
        return {"carpan": carpan, "guven": js.get("guven", "dusuk"),
                "aciklama": js.get("aciklama", ""), "uyari": js.get("uyari", "")}
    except urllib.error.HTTPError as e:
        return {"hata": f"API {e.code}"}
    except Exception as e:
        return {"hata": f"{e}"}


def heuristic_predict(formul, conc):
    f = formul or ""
    elements = set(re.findall(r"[A-Z][a-z]?", f))
    if re.search(r"(Pb|Cd|Hg|Cu|Zn|Ni|Co|Cr|As|Ag|Mn)", f):
        return {"kaynak": "rule", "carpan": 1 / (1 + conc ** 2),
                "ozet": tx("Formülde ağır metal olabilecek bir element var; toksisite olası.",
                           "The formula contains an element that may be a heavy metal; toxicity is possible."),
                "guven": "düşük",
                "uyari": tx("Kaba tahmin. Bazı metaller (ör. Fe, Zn) besin olarak gereklidir; tam etki için veri gerekir.",
                            "Rough estimate. Some metals (e.g. Fe, Zn) are essential nutrients; a full assessment needs data.")}
    if elements and elements <= {"C", "H", "O"}:
        return {"kaynak": "rule", "carpan": 1.0,
                "ozet": tx("Organik bileşik; olası karbon kaynağı. Heterotrofik türlerde kullanılabilir, fotoototrofta etkisi sınırlıdır.",
                           "Organic compound; a possible carbon source. Usable by heterotrophic species, limited effect on phototrophs."),
                "guven": "düşük", "uyari": tx("Yalnızca formüle dayanan yorum.", "Interpretation based on the formula only.")}
    if "N" in elements:
        return {"kaynak": "rule", "carpan": 1.0,
                "ozet": tx("Azot içeriyor; olası azot kaynağı. Etkisi konsantrasyona ve temel ortama bağlıdır.",
                           "Contains nitrogen; a possible nitrogen source. Its effect depends on concentration and base medium."),
                "guven": "düşük", "uyari": tx("Yalnızca formüle dayanan yorum.", "Interpretation based on the formula only.")}
    return {"kaynak": "rule", "carpan": 1.0,
            "ozet": tx("Bilinen bir etki bulunamadı; yalnızca formüle bakılarak yorum yapılabiliyor.",
                       "No known effect found; only a formula-based interpretation is possible."),
            "guven": "çok düşük",
            "uyari": tx("Bu madde için güvenilir tahmin yapılamadı. Deneysel test gerekir.",
                        "A reliable estimate could not be made for this substance. Experimental testing is required.")}


def evaluate(it, alg, info):
    entry = KNOWN_INDEX.get(nkey(it["sorgu"])) or KNOWN_INDEX.get(nkey(it["en"]))
    if entry:
        f = known_factor(entry, float(it["mgL"]), alg)
        return {"kaynak": "lit", "carpan": f, "ozet": tx(entry["ozet"], entry["ozet_en"]),
                "guven": "orta", "uyari": tx(entry["not"], entry["not_en"])}
    if os.environ.get("ANTHROPIC_API_KEY"):
        ai = ai_predict(alg, info["grup"], it["ad"], it["formul"], it["mw"], float(it["mgL"]), LANG)
        if "carpan" in ai:
            return {"kaynak": "ai", "carpan": ai["carpan"], "ozet": ai.get("aciklama", ""),
                    "guven": ai.get("guven", "dusuk"),
                    "uyari": ai.get("uyari") or tx("AI tahmini, deneysel doğrulama gerektirir.",
                                                   "AI estimate; requires experimental validation.")}
        h = heuristic_predict(it["formul"], float(it["mgL"]))
        h["uyari"] = tx(f"AI tahmini alınamadı ({ai.get('hata')}). ", f"AI estimate unavailable ({ai.get('hata')}). ") + h["uyari"]
        return h
    return heuristic_predict(it["formul"], float(it["mgL"]))


KAYNAK = {"lit": ("Araştırılmış", "Literature-based", "#3fb950"),
          "ai": ("Yapay Zeka Tahmini", "AI estimate", "#d29922"),
          "rule": ("Kural Tabanlı Tahmin", "Rule-based estimate", "#8b949e")}


def ev_card(it, ev):
    lab_tr, lab_en, c = KAYNAK.get(ev["kaynak"], ("?", "?", "#8b949e"))
    pct = (ev["carpan"] - 1) * 100
    sign = "+" if pct >= 0 else ""
    return (f'<div class="sci-card">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">'
            f'<b style="color:#fff;">{hx.escape(it["ad"])}</b>'
            f'<span style="color:{c};border:1px solid {c};padding:2px 8px;border-radius:12px;font-size:12px;white-space:nowrap;">'
            f'{tx(lab_tr, lab_en)}</span></div>'
            f'<div style="color:#8b949e;font-size:12px;margin:4px 0 8px;">{hx.escape(it["formul"] or "—")} · '
            f'{float(it["mgL"]):.1f} mg/L · {tx("Güven", "Confidence")}: {guv(ev["guven"])}</div>'
            f'<div style="color:#c9d1d9;font-size:14px;line-height:1.5;">{hx.escape(ev["ozet"])}</div>'
            f'<div style="margin-top:8px;font-size:13px;color:{c};font-weight:700;">'
            f'{tx("Büyüme çarpanı", "Growth factor")}: x{ev["carpan"]:.2f} ({sign}{pct:.1f}%)</div>'
            f'<div style="color:#8b949e;font-size:12px;margin-top:6px;">⚠ {hx.escape(ev["uyari"])}</div></div>')


def recommendations(info, volume, temp, light, tf, lf, o2, fa, items, evals):
    recs = []
    lo, hi = info["opt_temp_min"], info["opt_temp_max"]
    if not lo <= temp <= hi:
        recs.append(tx(f"Sıcaklık {temp}°C, bu tür için optimum aralığın ({lo}–{hi}°C) dışında. Aralığa getirmek büyüme hızını artırabilir (şu an sıcaklık çarpanı x{tf:.2f}).",
                       f"Temperature {temp}°C is outside this species' optimum range ({lo}–{hi}°C). Moving into range may raise growth (current temperature factor x{tf:.2f})."))
    if lf < 1:
        recs.append(tx(f"Seçilen ışık spektrumu bu tür için ideal değil. Önerilen: {info['ideal_isik']}.",
                       f"The selected light spectrum is not ideal for this species. Suggested: {lt(info['ideal_isik'])}."))
    recs.append(tx(f"Optimum pH {info['opt_ph']} aralığında tutulmalı; bikarbonat/CO₂ ile tamponlayıp pH sensörüyle sürekli izleyin.",
                   f"Keep pH within {info['opt_ph']}; buffer with bicarbonate/CO₂ and monitor continuously with a pH sensor."))
    if volume > 0 and 0 < o2 < HUMAN_O2_NEED:
        need = HUMAN_O2_NEED / (o2 / volume)
        recs.append(tx(f"Mevcut koşullarda bir astronotun günlük O₂ ihtiyacını ({HUMAN_O2_NEED:.0f} g) karşılamak için yaklaşık {need:,.0f} L reaktör gerekir.",
                       f"Under current conditions, about {need:,.0f} L of reactor is needed to cover one astronaut's daily O₂ need ({HUMAN_O2_NEED:.0f} g)."))
    toks = [it["ad"] for it, ev in zip(items, evals) if ev["carpan"] < 0.8]
    if toks:
        recs.append(tx("Büyümeyi %20'den fazla baskılayan madde(ler): " + ", ".join(toks) + ". Bu konsantrasyonları düşürüp doz-yanıt testi yapın.",
                       "Substance(s) suppressing growth by more than 20%: " + ", ".join(toks) + ". Lower these concentrations and run a dose-response test."))
    if items and fa > 1.05:
        recs.append(tx("Ekli maddeler büyümeyi artırıyor. Gerçek etkiyi görmek için aynı koşulda 'madde yok' kontrol grubu çalıştırın.",
                       "Added substances increase growth. To see the true effect, run a 'no substance' control under the same conditions."))
    if not items:
        recs.append(tx("Sol panelden bir madde ekleyerek doz-yanıt karşılaştırması yapabilirsiniz; ilk deney için 3 farklı konsantrasyon önerilir.",
                       "Add a substance from the left panel to compare dose-response; for a first experiment, 3 different concentrations are suggested."))
    recs += [
        tx("Deney tasarımı: her koşulu en az 3 tekrarla çalıştırın ve aynı anda yalnızca bir değişkeni değiştirin.",
           "Experimental design: run each condition in at least 3 replicates and change only one variable at a time."),
        tx("Ölçüm: haftada en az üç kez OD₆₈₀ (biyokütle), pH ve kuru ağırlık ölçün; simülasyon tahminlerini bu verilerle kalibre edin.",
           "Measurement: record OD₆₈₀ (biomass), pH and dry weight at least three times a week; calibrate the simulation with these data."),
        tx("Işık: fotoperiyot (ör. 16:8) ve yüzey ışık yoğunluğunu (µmol·m⁻²·s⁻¹) deney kaydına ekleyin; ışık sınırlamasını ayırt etmek için kritik.",
           "Light: record photoperiod (e.g. 16:8) and surface irradiance (µmol·m⁻²·s⁻¹) in the log; essential for separating light limitation."),
        tx("Kontaminasyon: ortamı otoklavlayın veya 0,22 µm filtreleyin; mikroskopla düzenli kontrol edin, kontamine kültürü hemen ayırın.",
           "Contamination: autoclave or 0.22 µm filter the medium; check regularly under a microscope and isolate contaminated cultures immediately."),
    ]
    return recs


# ============================================================
# ALG SEÇİCİ (hover önizlemeli, tooltip ana sayfada gösterilir)
# ============================================================
PICKER_HTML = r"""
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
html,body{margin:0;background:transparent;font-family:sans-serif;}
#list{overflow-y:auto;display:flex;flex-direction:column;gap:5px;padding:2px 6px 2px 2px;box-sizing:border-box;}
.it{flex:0 0 auto;background:#161b22;border:1px solid #30363d;border-radius:8px;padding:7px 11px;color:#c9d1d9;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;transition:background .15s,border-color .15s;}
.it:hover,.it.active{background:#21262d;border-color:#8b949e;color:#fff;}
#list::-webkit-scrollbar{width:6px;}
#list::-webkit-scrollbar-thumb{background:#30363d;border-radius:4px;}
</style></head>
<body>
<div id="list"></div>
<script>
var items = [], active = null, vol = 0, H = 240, ac = null;
var P = document;
try { P = window.parent.document; } catch (e) {}
var tip = P.getElementById("alg-tip-global");
if (!tip) {
  tip = P.createElement("div");
  tip.id = "alg-tip-global";
  tip.style.cssText = "display:none;position:fixed;width:230px;z-index:99999;background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:8px;box-shadow:0 10px 30px rgba(0,0,0,.6);pointer-events:none;font-family:sans-serif;";
  P.body.appendChild(tip);
}
function send(type, data) {
  var msg = {isStreamlitMessage: true, type: type};
  for (var k in data) msg[k] = data[k];
  window.parent.postMessage(msg, "*");
}
function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function frameOff() {
  try { var r = window.frameElement.getBoundingClientRect(); return [r.left, r.top]; }
  catch (e) { return [0, 0]; }
}
function place(e) {
  var o = frameOff(), pw = window.parent.innerWidth, ph = window.parent.innerHeight;
  var h = tip.offsetHeight || 200;
  var x = o[0] + e.clientX + 14, y = o[1] + e.clientY + 10;
  if (x + 230 > pw) x = Math.max(4, o[0] + e.clientX - 244);
  if (y + h > ph) y = Math.max(4, ph - h - 4);
  tip.style.left = x + "px";
  tip.style.top = y + "px";
}
function playClick() {
  if (!vol) return;
  try {
    var Ctx = window.AudioContext || window.webkitAudioContext;
    if (!ac) ac = new Ctx();
    if (ac.state === "suspended") ac.resume();
    var t = ac.currentTime, o = ac.createOscillator(), g = ac.createGain();
    o.type = "sine";
    o.frequency.setValueAtTime(1400, t);
    o.frequency.exponentialRampToValueAtTime(600, t + 0.04);
    g.gain.setValueAtTime(vol * 0.06, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.05);
    o.connect(g); g.connect(ac.destination); o.start(t); o.stop(t + 0.06);
  } catch (e) {}
}
function render() {
  tip.style.display = "none";
  var list = document.getElementById("list");
  list.style.height = H + "px";
  list.innerHTML = "";
  items.forEach(function (it) {
    var d = document.createElement("div");
    d.className = "it" + (it.name === active ? " active" : "");
    d.textContent = (it.name === active ? "▶ " : "") + it.name;
    d.onmouseenter = function (e) {
      tip.innerHTML = '<img src="' + it.img + '" alt="" style="width:100%;height:150px;object-fit:cover;border-radius:6px;display:block;background:#0b1118;">' +
        '<span style="display:block;margin-top:6px;color:#e6edf3;font-size:13px;line-height:1.3;">' + esc(it.name) +
        '<br><small style="color:#8b949e;">' + esc(it.group) + ' · ' + esc(it.size) + '</small></span>';
      tip.style.display = "block";
      place(e);
    };
    d.onmousemove = place;
    d.onmouseleave = function () { tip.style.display = "none"; };
    d.onclick = function () {
      tip.style.display = "none";
      playClick();
      send("streamlit:setComponentValue", {value: it.name, dataType: "json"});
    };
    list.appendChild(d);
  });
}
window.addEventListener("message", function (ev) {
  var d = ev.data;
  if (d && d.type === "streamlit:render") {
    var a = d.args || {};
    items = a.items || [];
    active = a.active;
    H = a.h || 240;
    vol = (a.vol || 0) / 100;
    send("streamlit:setFrameHeight", {height: H + 12});
    render();
  }
});
send("streamlit:componentReady", {apiVersion: 1});
send("streamlit:setFrameHeight", {height: 252});
</script>
</body></html>
"""

PICKER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_alg_picker")
os.makedirs(PICKER_DIR, exist_ok=True)
_idx_path = os.path.join(PICKER_DIR, "index.html")
_old_html = None
if os.path.exists(_idx_path):
    with open(_idx_path, encoding="utf-8") as _f:
        _old_html = _f.read()
if _old_html != PICKER_HTML:
    with open(_idx_path, "w", encoding="utf-8") as _f:
        _f.write(PICKER_HTML)

_alg_picker_component = components.declare_component("alg_picker", path=PICKER_DIR)


def alg_picker(names, active, key, height=240, vol=0):
    items = [{"name": n, "group": gr(algae_db[n]["grup"]), "size": algae_db[n]["boyut"],
              "img": preview_src(n)} for n in names]
    return _alg_picker_component(items=items, active=active, h=height, vol=vol, key=key, default=active)


# ============================================================
# GÖRSEL VE YARDIMCI FONKSİYONLAR
# ============================================================
def qp_get(key, default):
    try:
        v = st.query_params.get(key, default)
        return v if isinstance(v, str) else default
    except Exception:
        return default


def clamp_int(v, lo, hi, default, step=1):
    try:
        x = int(float(v))
    except (TypeError, ValueError):
        return default
    x = int(round(x / step) * step)
    return min(hi, max(lo, x))


def slugify(text):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def find_image(name, data):
    cands = []
    if data.get("dosya_adi"):
        cands.append(data["dosya_adi"])
    base = os.path.join(IMG_DIR, slugify(name))
    cands += [base + e for e in (".jpg", ".jpeg", ".png", ".webp")]
    for c in cands:
        if c and os.path.exists(c):
            return c
    return None


@st.cache_data(show_spinner=False)
def image_data_uri(path, max_side=280):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def micro_svg(tip, c, label=""):
    gid = "g" + c.strip("#")
    fill = f"url(#{gid})"
    defs = (f'<defs><radialGradient id="{gid}" cx="35%" cy="30%" r="75%">'
            f'<stop offset="0" stop-color="#ffffff" stop-opacity="0.55"/>'
            f'<stop offset="0.4" stop-color="{c}"/>'
            f'<stop offset="1" stop-color="#05110a"/></radialGradient>'
            f'<clipPath id="fov"><circle cx="120" cy="90" r="86"/></clipPath></defs>')
    if tip == "kure":
        cells = [(96, 82, 24), (138, 76, 20), (112, 116, 19), (150, 118, 17)]
        body = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{c}" stroke-width="2"/>'
                       for x, y, r in cells)
    elif tip == "cubuk":
        body = (f'<rect x="58" y="76" width="124" height="28" rx="14" fill="{fill}" stroke="{c}" stroke-width="2"/>'
                f'<rect x="72" y="81" width="90" height="5" rx="2.5" fill="#ffffff" opacity="0.35"/>')
    elif tip == "spiral":
        pts = " ".join(f"{50 + 140 * t:.1f},{90 + 26 * np.sin(2 * np.pi * 3.2 * t):.1f}"
                       for t in np.linspace(0, 1, 120))
        body = (f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="10" '
                f'stroke-linecap="round" stroke-linejoin="round"/>'
                f'<polyline points="{pts}" fill="none" stroke="#ffffff" stroke-opacity="0.35" '
                f'stroke-width="3" stroke-linecap="round"/>')
    elif tip == "koloni":
        body = "".join(f'<rect x="{x}" y="{y}" width="34" height="34" rx="9" fill="{fill}" stroke="{c}" stroke-width="2"/>'
                       for x, y in [(86, 52), (124, 52), (86, 92), (124, 92)])
    elif tip == "kamcili":
        body = (f'<path d="M150,86 C172,48 196,124 226,66" fill="none" stroke="{c}" stroke-width="3" stroke-linecap="round"/>'
                f'<path d="M150,94 C170,130 192,62 214,118" fill="none" stroke="{c}" stroke-width="3" stroke-linecap="round" opacity="0.8"/>'
                f'<ellipse cx="112" cy="90" rx="40" ry="28" fill="{fill}" stroke="{c}" stroke-width="2"/>')
    elif tip == "kist":
        dots = "".join(f'<circle cx="{x}" cy="{y}" r="4" fill="#ff7b72" opacity="0.85"/>'
                       for x, y in [(100, 76), (118, 96), (138, 80), (108, 108), (132, 110), (122, 70)])
        body = f'<circle cx="120" cy="90" r="50" fill="#3b0d10" stroke="{c}" stroke-width="9"/>' + dots
    elif tip == "diatom":
        pores = ("".join(f'<circle cx="{x}" cy="90" r="2.6" fill="{c}"/>' for x in range(64, 181, 12))
                 + "".join(f'<circle cx="{x}" cy="{y}" r="2" fill="{c}" opacity="0.7"/>'
                           for x in range(70, 171, 12) for y in (74, 106)))
        body = (f'<ellipse cx="120" cy="90" rx="78" ry="38" fill="{fill}" fill-opacity="0.35" '
                f'stroke="{c}" stroke-width="5"/>' + pores)
    elif tip == "filament":
        body = "".join(f'<rect x="{x}" y="76" width="24" height="28" rx="8" fill="{fill}" stroke="{c}" stroke-width="2"/>'
                       for x in [48, 74, 100, 126, 152, 178])
        body += '<circle cx="138" cy="90" r="9" fill="#f0f6fc" stroke="' + c + '" stroke-width="2"/>'
    elif tip == "zincir":
        body = "".join(f'<rect x="{x}" y="82" width="32" height="20" rx="6" fill="{fill}" stroke="{c}" stroke-width="2"/>'
                       for x in [52, 82, 112, 142, 172])
    elif tip == "isi":
        body = f'<path d="M58,70 Q130,40 186,122 Q120,84 58,70 Z" fill="{fill}" stroke="{c}" stroke-width="2"/>'
    else:
        body = f'<circle cx="120" cy="90" r="40" fill="{fill}" stroke="{c}" stroke-width="2"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 180">{defs}'
            f'<rect width="240" height="180" fill="#0b1118"/>'
            f'<circle cx="120" cy="90" r="86" fill="#0d1117" stroke="#30363d" stroke-width="2"/>'
            f'<g clip-path="url(#fov)">{body}</g>'
            f'<text x="120" y="172" text-anchor="middle" fill="#8b949e" font-size="9" '
            f'font-family="sans-serif">{label}</text></svg>')


@st.cache_data(show_spinner=False)
def preview_src(name):
    d = algae_db[name]
    path = find_image(name, d)
    if path:
        try:
            return image_data_uri(path)
        except Exception:
            pass
    svg = micro_svg(d["tip"], d["renk_kod"], d["boyut"])
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode()


def temp_light_factors(info, temp, light):
    if info["opt_temp_min"] <= temp <= info["opt_temp_max"]:
        tf = 1.0
    else:
        dev = min(abs(temp - info["opt_temp_min"]), abs(temp - info["opt_temp_max"]))
        tf = max(0.2, 1.0 - dev * 0.15)
    lf = 1.0 if (light.lower() in info["ideal_isik"].lower() or "geniş" in light.lower()) else 0.75
    return tf, lf


def metric_card(label, value, unit, badge, color, unit_size=18):
    return (f'<div class="metric-card">'
            f'<p style="color:#8b949e;margin:0;font-size:13px;font-weight:700;">{label}</p>'
            f'<h1 style="color:{color};margin:10px 0;font-size:42px;font-weight:800;">{value}'
            f' <span style="font-size:{unit_size}px;color:#8b949e;">{unit}</span></h1>'
            f'<span class="badge-green">{badge}</span></div>')


def growth_curve(rel_rate, volume, days=30):
    K, N0 = 1.5, 0.05
    r = 0.5 * rel_rate
    t = np.arange(0, days + 1)
    N = K / (1 + ((K - N0) / N0) * np.exp(-r * t))
    return t, N * volume


def add_item(ad, sorgu, en, formul, mw, mgl):
    st.session_state.additives.append({
        "id": st.session_state.next_id, "ad": ad, "sorgu": sorgu, "en": en,
        "formul": formul, "mw": mw, "mgL": float(mgl)})
    st.session_state.next_id += 1


def preset_label(i):
    tr_, en_, f_, _ = PRESETS[i]
    return f"{tx(tr_, en_)} ({f_})"


# ============================================================
# SESSION STATE
# ============================================================
for _k, _v in {"additives": [], "next_id": 1, "found": None, "found_q": "", "found_en": "", "log": []}.items():
    st.session_state.setdefault(_k, _v)

alg_default = qp_get("alg", ALG_NAMES[0])
if alg_default not in algae_db:
    alg_default = ALG_NAMES[0]
light_default = qp_get("isik", LIGHTS[0])
if light_default not in LIGHTS:
    light_default = LIGHTS[0]
if "sel" not in st.session_state:
    st.session_state.sel = alg_default

# ============================================================
# YAN MENÜ: ALG, ORTAM VE MADDE EKLEME
# ============================================================
with st.sidebar:
    st.markdown(f"### {tx('Reaktör Konsolu', 'Reactor Console')}")
    st.markdown(f"**{tx('Alg / Siyanobakteri Seçin:', 'Select alga / cyanobacterium:')}**")
    sim_pick = alg_picker(ALG_NAMES, st.session_state.sel, key=f"sim_pick_{st.session_state.sel}",
                          height=230, vol=SND)
    st.caption(tx("Bir türün üzerine gelin, mikroskop önizlemesi açılır.",
                  "Hover over a species to preview its microscope image."))

    reactor_volume = st.slider(tx("Biyoreaktör Hacmi (Litre):", "Bioreactor volume (L):"), 0, 1000,
                               clamp_int(qp_get("hacim", 300), 0, 1000, 300, 50), step=50)
    user_temp = st.slider(tx("Ortam Sıcaklığı (°C):", "Ambient temperature (°C):"), 15, 42,
                          clamp_int(qp_get("sicaklik", 28), 15, 42, 28))
    user_light = st.selectbox(tx("Işık Spektrumu:", "Light spectrum:"), LIGHTS,
                              index=LIGHTS.index(light_default), format_func=lt)

    st.markdown("---")
    st.markdown(f"### {tx('Ortama Madde Ekle', 'Add Substance to Medium')}")
    st.caption(tx("PubChem'de dünyadaki bileşikleri arayın ya da aşağıdaki hazır listeden seçin.",
                  "Search compounds worldwide in PubChem, or pick one from the preset list below."))

    with st.form("search_form"):
        q = st.text_input(tx("Bileşik adı, formül veya CAS no", "Compound name, formula or CAS no"),
                          placeholder=tx("örn. glikoz, sodyum klorür, caffeine",
                                         "e.g. glucose, sodium chloride, caffeine"))
        do_search = st.form_submit_button(tx("Ara", "Search"), use_container_width=True)

    if do_search and q.strip():
        qs = q.strip()
        en = TR_ALIAS.get(qs.lower(), qs)
        st.session_state.found = pubchem_lookup(en)
        st.session_state.found_q = qs
        st.session_state.found_en = en

    found = st.session_state.found
    if found and found.get("ok"):
        st.success(tx(f"{st.session_state.found_q} bulundu", f"{st.session_state.found_q} found"))
        st.caption(f"{tx('Formül', 'Formula')}: {found['formul']} · {tx('MA', 'MW')}: "
                   f"{found['mw']:.2f} g/mol · CID: {found['cid']}")
        with st.expander(tx("IUPAC adı ve SMILES", "IUPAC name and SMILES")):
            st.write(found["iupac"])
            st.code(found["smiles"] or "—")
        conc_s = st.number_input(tx("Konsantrasyon (mg/L)", "Concentration (mg/L)"),
                                 min_value=0.0, max_value=100000.0, value=10.0, step=1.0, key="conc_search")
        if st.button(tx("Ortama ekle", "Add to medium"), type="primary", use_container_width=True, key="btn_add"):
            add_item(st.session_state.found_q, st.session_state.found_q, st.session_state.found_en,
                     found["formul"], found["mw"], conc_s)
            st.session_state.found = None
    elif found:
        if found.get("code") == 404:
            st.warning(tx("Bulunamadı. İngilizce adını deneyin (ör. glucose, sodium chloride).",
                          "Not found. Try the English name (e.g. glucose, sodium chloride)."))
        else:
            st.warning(tx("Bağlantı veya PubChem hatası. Tekrar deneyin.",
                          "Connection or PubChem error. Please try again."))

    st.markdown(f"**{tx('Hazır liste: deneylerde en sık kullanılan 50 madde', 'Preset list: 50 most-used substances in experiments')}**")
    pidx = st.selectbox(tx("Madde seçin", "Choose a substance"), range(len(PRESETS)),
                        format_func=preset_label, key="preset_idx")
    conc_p = st.number_input(tx("Konsantrasyon (mg/L)", "Concentration (mg/L)"), min_value=0.0,
                             max_value=100000.0, value=10.0, step=1.0, key="conc_preset")
    if st.button(tx("Seçili maddeyi ekle", "Add selected substance"), use_container_width=True, key="btn_preset"):
        tr_, en_, f_, mw_ = PRESETS[pidx]
        add_item(tx(tr_, en_), en_, en_, f_, mw_, conc_p)

    if st.session_state.additives:
        st.markdown(f"**{tx('Ortamdaki maddeler', 'Substances in medium')}**")
        remove_ids = []
        for it in st.session_state.additives:
            c1, c2 = st.columns([4, 1])
            with c1:
                it["mgL"] = st.number_input(f"{it['ad'][:28]} (mg/L)", min_value=0.0, max_value=100000.0,
                                            value=float(it["mgL"]), step=1.0, key=f"mg_{it['id']}")
            with c2:
                st.write("")
                if st.button("✕", key=f"del_{it['id']}"):
                    remove_ids.append(it["id"])
        if remove_ids:
            st.session_state.additives = [x for x in st.session_state.additives if x["id"] not in remove_ids]
            st.rerun()

if sim_pick and sim_pick != st.session_state.sel:
    st.session_state.sel = sim_pick
    st.rerun()

selected_algae = st.session_state.sel

# ============================================================
# GÖRÜNÜM SEÇİMİ
# ============================================================
VIEW_LABELS = [tx("Canlı Simülasyon & Endüstriyel Reaktör", "Live Simulation & Industrial Reactor"),
               tx("Biyolojik Ansiklopedi", "Biological Encyclopedia")]
view_default = 1 if qp_get("gorunum", "") == "ansiklopedi" else 0
view_idx = st.radio(tx("Görünüm", "View"), [0, 1], format_func=lambda i: VIEW_LABELS[i],
                    index=view_default, horizontal=True, label_visibility="collapsed", key="view_sel")

# ============================================================
# 3B MODEL
# ============================================================
class MeshBuilder:
    FACES = [(0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6), (0, 4, 5), (0, 5, 1),
             (1, 5, 6), (1, 6, 2), (2, 6, 7), (2, 7, 3), (3, 7, 4), (3, 4, 0)]

    def __init__(self, s):
        self.s = s
        self.v, self.c, self.i, self.j, self.k = [], [], [], [], []

    def _add(self, pts, color):
        base = len(self.v)
        self.v.extend([[p[0] * self.s, p[1] * self.s, p[2] * self.s] for p in pts])
        self.c.extend([color] * len(pts))
        return base

    def box(self, x0, x1, y0, y1, z0, z1, color):
        pts = [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
               [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]]
        b = self._add(pts, color)
        for a, bb, cc in self.FACES:
            self.i.append(b + a); self.j.append(b + bb); self.k.append(b + cc)

    def cylinder(self, cx, cy, z0, z1, r, color, res=28, caps=True):
        ang = np.linspace(0, 2 * np.pi, res, endpoint=False)
        bot = [[cx + r * np.cos(t), cy + r * np.sin(t), z0] for t in ang]
        top = [[cx + r * np.cos(t), cy + r * np.sin(t), z1] for t in ang]
        b = self._add(bot + top + [[cx, cy, z0], [cx, cy, z1]], color)
        n = res
        cb, ct = b + 2 * n, b + 2 * n + 1
        for k in range(n):
            k2 = (k + 1) % n
            b1, b2, t1, t2 = b + k, b + k2, b + n + k, b + n + k2
            self.i += [b1, b1]; self.j += [b2, t2]; self.k += [t2, t1]
            if caps:
                self.i += [cb, ct]; self.j += [b2, t1]; self.k += [b1, t2]


def mesh_trace(mb, opacity=1.0, lighting=None):
    V = np.asarray(mb.v, float)
    return go.Mesh3d(x=V[:, 0], y=V[:, 1], z=V[:, 2], i=mb.i, j=mb.j, k=mb.k,
                     vertexcolor=mb.c, opacity=opacity, flatshading=False,
                     lighting=lighting or dict(ambient=0.55, diffuse=0.7, specular=0.5, roughness=0.3),
                     hoverinfo="skip", showlegend=False)


def line_traces(groups, width=6):
    out = []
    for color, segs in groups.items():
        xs, ys, zs = [], [], []
        for seg in segs:
            xs += seg[:, 0].tolist() + [None]
            ys += seg[:, 1].tolist() + [None]
            zs += seg[:, 2].tolist() + [None]
        out.append(go.Scatter3d(x=xs, y=ys, z=zs, mode="lines",
                                line=dict(color=color, width=width), hoverinfo="skip", showlegend=False))
    return out


def circle_pts(cx, cy, z, r, s, n=90):
    a = np.linspace(0, 2 * np.pi, n)
    return np.column_stack([(cx + r * np.cos(a)) * s, (cy + r * np.sin(a)) * s, np.full(n, z * s)])


@st.cache_resource(show_spinner=False, max_entries=24)
def build_reactor_figure(volume, bio_color, group, algae_name):
    rng = np.random.default_rng(42)
    s = float(max(0.7, min(2.2, (volume / 100.0) ** (1 / 3))))
    R, VB, VT, LB, LT = 2.25, 1.15, 8.55, 1.65, 7.95
    RL = R * 0.94

    opaque, glass, liquid = MeshBuilder(s), MeshBuilder(s), MeshBuilder(s)
    lines = {}

    def line(color, pts):
        lines.setdefault(color, []).append(np.asarray(pts, float) * s)

    def ring(cx, cy, z, r, color):
        lines.setdefault(color, []).append(circle_pts(cx, cy, z, r, s))

    opaque.box(-3.15, 3.25, -2.65, 2.65, 0.15, 0.48, "#303844")
    opaque.box(-3.0, 3.1, -2.5, 2.5, 0.48, 0.60, "#697586")
    for x in (-2.8, 2.8):
        for y in (-2.3, 2.3):
            opaque.box(x - 0.12, x + 0.12, y - 0.12, y + 0.12, 0.02, 0.17, "#161b22")
    for x in (-2.72, 2.72):
        for y in (-2.25, 2.25):
            opaque.box(x - 0.085, x + 0.085, y - 0.085, y + 0.085, 0.55, 9.15, "#758397")
    for z in (0.8, 1.05, 8.75, 9.0):
        for y in (-2.25, 2.25):
            opaque.box(-2.75, 2.75, y - 0.07, y + 0.07, z, z + 0.13, "#596574")
        for x in (-2.72, 2.72):
            opaque.box(x - 0.07, x + 0.07, -2.25, 2.25, z, z + 0.13, "#596574")
    bolts = np.array([(x, -2.34, z) for x in (-2.72, 2.72) for z in (1.0, 8.8)]) * s

    glass.cylinder(0, 0, VB, VT, R, "#8eb8cc", caps=False)
    liquid.cylinder(0, 0, LB, LT, RL, bio_color)
    for a in (0.28, np.pi - 0.28):
        x, y = (R + 0.025) * np.cos(a), (R + 0.025) * np.sin(a)
        line("#b9e8ff", [[x, y, VB + 0.35], [x, y, VT - 0.35]])
    for z in (VB, VT):
        opaque.cylinder(0, 0, z - 0.15, z + 0.15, R + 0.16, "#586575")
        ring(0, 0, z - 0.15, R + 0.17, "#c2ccd8")
        ring(0, 0, z + 0.15, R + 0.17, "#a3b3c5")
    opaque.cylinder(0, 0, VT + 0.16, VT + 0.36, R - 0.05, "#3d4857")
    opaque.cylinder(0, 0, VT + 0.36, VT + 0.48, 0.72, "#566477")
    opaque.cylinder(0, 0, 0.62, 0.95, 0.78, "#4a5665")

    opaque.cylinder(0.65, 0, VT + 0.42, VT + 1.05, 0.12, "#b9c6d4")
    line("#9caec1", [[0.65, 0, VT + 1.05], [0.65, 0, VT + 1.32], [1.25, 0, VT + 1.32], [1.25, 0, VT + 0.88]])
    opaque.box(1.05, 1.45, -0.22, 0.22, VT + 0.78, VT + 1.02, "#39485a")
    line("#e5edf5", [[1.05, 0, VT + 0.9], [1.45, 0, VT + 0.9]])

    line("#d8a657", [[-4.1, -0.55, 1.2], [-3.55, -0.55, 1.2], [-2.8, -0.55, 1.2],
                     [-2.35, -0.55, 1.2], [-2.05, -0.55, 1.45], [-1.75, -0.55, 1.45]])
    opaque.box(-2.45, -2.20, -0.72, -0.38, 1.08, 1.42, "#9c7741")
    opaque.box(-1.95, -1.72, -0.70, -0.40, 1.32, 1.58, "#b3c0cd")
    opaque.cylinder(0, 0, 1.48, 1.66, 1.35, "#465568")
    ring(0, 0, 1.64, 1.28, "#aebdcb")

    opaque.box(-5.45, -3.15, -1.65, 1.65, 1.00, 7.45, "#202a37")
    opaque.box(-5.30, -5.20, -1.38, 1.38, 1.25, 7.20, "#303d4c")
    opaque.box(-5.16, -5.10, -0.95, 0.95, 5.10, 6.55, "#071521")
    opaque.box(-5.19, -5.15, -1.00, 1.00, 5.04, 5.12, "#73879a")

    bx, by, bz, bs = [], [], [], []
    for col in range(11):
        ang = col * 2 * np.pi / 11
        rad = 0.35 + (col % 3) * 0.22
        cx, cy = rad * np.cos(ang), rad * np.sin(ang)
        for j in range(5):
            bx.append((cx + rng.uniform(-0.07, 0.07)) * s)
            by.append((cy + rng.uniform(-0.07, 0.07)) * s)
            bz.append((1.85 + j * 1.18 + rng.uniform(-0.22, 0.22)) * s)
            bs.append(rng.uniform(2.5, 5.5))

    n_cells = 46
    kx, ky, kz, ks = [], [], [], []
    for _ in range(n_cells):
        ang = rng.uniform(0, 2 * np.pi)
        rad = np.sqrt(rng.uniform(0, 1)) * 1.72 * s
        kx.append(rad * np.cos(ang)); ky.append(rad * np.sin(ang))
        kz.append(rng.uniform(LB + 0.35, LT - 0.35) * s)
        ks.append(max(3, int(rng.uniform(0.075, 0.14) * s * 50)))

    traces = [
        mesh_trace(glass, opacity=0.16,
                   lighting=dict(ambient=0.35, diffuse=0.65, specular=1.0, roughness=0.08)),
        mesh_trace(liquid, opacity=0.6,
                   lighting=dict(ambient=0.65, diffuse=0.65, specular=0.35, roughness=0.4)),
        mesh_trace(opaque),
    ]
    traces += line_traces(lines)
    traces.append(go.Scatter3d(x=bolts[:, 0], y=bolts[:, 1], z=bolts[:, 2], mode="markers",
                               marker=dict(size=5, color="#c5d0dc"), hoverinfo="skip", showlegend=False))
    traces.append(go.Scatter3d(x=bx, y=by, z=bz, mode="markers",
                               marker=dict(size=bs, color="#d9f7ff", opacity=0.75),
                               hoverinfo="skip", showlegend=False))
    traces.append(go.Scatter3d(x=kx, y=ky, z=kz, mode="markers",
                               marker=dict(size=ks, color=bio_color, opacity=0.95),
                               hoverinfo="skip", showlegend=False))

    base_angle = np.arctan2(-2.15, 1.65)
    r_xy = float(np.hypot(1.65, 2.15))
    frames = []
    for i in range(60):
        a = base_angle + 2 * np.pi * i / 60
        frames.append(go.Frame(
            layout=dict(scene=dict(camera=dict(eye=dict(
                x=float(r_xy * np.cos(a)), y=float(r_xy * np.sin(a)), z=1.15)))),
            name=f"f{i}"))

    fig = go.Figure(data=traces, frames=frames)
    fig.update_layout(
        template="plotly_dark",
        title=dict(text=f"<b>INDUSTRIAL PHOTOBIOREACTOR</b><br><sup>{algae_name} | {group} | {volume} L</sup>",
                   x=0.5, y=0.97, xanchor="center", font=dict(size=18, color="#e6edf3")),
        scene=dict(
            xaxis=dict(visible=False, range=[-6.2 * s, 4.0 * s]),
            yaxis=dict(visible=False, range=[-3.6 * s, 3.6 * s]),
            zaxis=dict(visible=False, range=[0, 10.5 * s]),
            bgcolor="#0d1117", aspectmode="manual",
            aspectratio=dict(x=1.15, y=0.85, z=1.5),
            camera=dict(eye=dict(x=1.65, y=-2.15, z=1.15), center=dict(x=0, y=0, z=0),
                        up=dict(x=0, y=0, z=1)),
            dragmode="orbit"),
        paper_bgcolor="#0d1117",
        margin=dict(l=0, r=0, t=85, b=0),
        height=680,
        updatemenus=[dict(
            type="buttons", showactive=False, x=0.5, y=0, xanchor="center", yanchor="top",
            buttons=[
                dict(label="▶ " + tx("Yavaş Döndür", "Slow rotate"), method="animate",
                     args=[None, dict(frame=dict(duration=120, redraw=False), fromcurrent=True,
                                      transition=dict(duration=0), mode="immediate")]),
                dict(label="❚❚ " + tx("Durdur", "Stop"), method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")]),
            ])])
    return fig


@st.fragment
def render_model(volume, name, info):
    st.markdown(f"### {tx('Biyoreaktör Modeli', 'Bioreactor Model')}")
    st.caption(tx("Modeli sürükleyerek döndürebilir, yakınlaştırabilirsiniz. 3B model ağır olduğu için isteğe bağlı yüklenir.",
                  "Drag to rotate and zoom. The 3D model is heavy, so it loads on demand."))
    if not st.session_state.get("model_loaded", False):
        if st.button(tx("▶ 3B Biyoreaktör Modelini Yükle", "▶ Load 3D Bioreactor Model"), type="primary"):
            st.session_state["model_loaded"] = True
            st.rerun(scope="fragment")
        return
    with st.spinner(tx("3B biyoreaktör modeli hazırlanıyor...", "Preparing 3D bioreactor model...")):
        fig = build_reactor_figure(volume, info["renk_kod"], gr(info["grup"]), name)
    st.plotly_chart(fig, use_container_width=True, config={
        "displaylogo": False, "scrollZoom": True, "responsive": True,
        "toImageButtonOptions": {"format": "png", "filename": "biyoreaktor_dijital_ikiz", "scale": 2},
    })


# ============================================================
# ANSİKLOPEDİ
# ============================================================
def render_detail(name):
    d = algae_db[name]
    st.markdown(f"### {name}")
    st.markdown(f"**{tx('Sınıf:', 'Class:')}** {gr(d['grup'])} | "
                f"**{tx('Pigment/Renk:', 'Pigment/Colour:')}** {d['renk']}")
    path = find_image(name, d)
    if path:
        st.image(path, caption=tx(f"{name} - Mikroskopik Görünüm", f"{name} - Microscopic view"),
                 use_container_width=True)
    else:
        svg = micro_svg(d["tip"], d["renk_kod"], d["boyut"])
        st.markdown(f'<div class="micro-card">{svg}<p>{tx("Morfolojik Model (kendi çizimimiz)", "Morphological model (our drawing)")}</p></div>',
                    unsafe_allow_html=True)
    st.markdown(f'<div class="tanitim-card">{d["tanitim"]}</div>', unsafe_allow_html=True)
    st.markdown("\n".join([
        f"- **{tx('Mikroskobik Boyut:', 'Microscopic size:')}** {d['boyut']}",
        f"- **{tx('Doğal Yaşam Alanı:', 'Natural habitat:')}** {d['habitat']}",
        f"- **{tx('Yaşam Döngüsü & Üreme:', 'Life cycle & reproduction:')}** {d['yasam_dongusu']}",
        f"- **{tx('Maksimum Verim:', 'Maximum yield:')}** {d['max_verim']} g/L/{tx('gün', 'day')}",
        f"- **{tx('Optimum Sıcaklık:', 'Optimum temperature:')}** {d['opt_temp_min']}°C - {d['opt_temp_max']}°C",
        f"- **{tx('Optimum pH:', 'Optimum pH:')}** {d['opt_ph']}",
        f"- **{tx('İdeal Işık Spektrumu:', 'Ideal light spectrum:')}** {lt(d['ideal_isik'])}",
    ]))


SORT_TR = ["Varsayılan Sıra", "En Yüksek Verimden En Düşüğe", "İsme Göre (A - Z)",
           "Boyuta Göre (En Büyükten Küçüğe)", "Boyuta Göre (En Küçükten Büyüğe)"]
SORT_EN = ["Default order", "Highest to lowest yield", "By name (A–Z)",
           "By size (largest first)", "By size (smallest first)"]


def render_encyclopedia(selected):
    st.markdown(f"### {tx('Siyanobakteri ve Mikroalg Veritabanı', 'Cyanobacteria and Microalgae Database')}")
    st.markdown(tx("Bir türün üzerine gelince mikroskop önizlemesi açılır. Türe tıklayınca detaylı profil aynı sayfada görünür.",
                   "Hover over a species to see a microscope preview. Click it to view its full profile on this page."))
    col_list, col_detail = st.columns([1, 1.5])
    with col_list:
        sidx = st.selectbox(tx("Sıralama Kriteri:", "Sort by:"), range(5),
                            format_func=lambda i: tx(SORT_TR[i], SORT_EN[i]), key="sort_opt")
        keys = list(algae_db.keys())
        if sidx == 1:
            keys = sorted(keys, key=lambda x: algae_db[x]["max_verim"], reverse=True)
        elif sidx == 2:
            keys = sorted(keys)
        elif sidx == 3:
            keys = sorted(keys, key=lambda x: algae_db[x]["boyut_deger"], reverse=True)
        elif sidx == 4:
            keys = sorted(keys, key=lambda x: algae_db[x]["boyut_deger"])
        enc_pick = alg_picker(keys, selected, key=f"enc_pick_{selected}", height=560, vol=SND)
    if enc_pick and enc_pick != st.session_state.sel:
        st.session_state.sel = enc_pick
        st.rerun()
    with col_detail:
        render_detail(selected)


# ============================================================
# BİLİMSEL ANALİZ PANELİ (SAĞ)
# ============================================================
def render_science(selected, info, volume, temp, light, items, evals, fa, tf, lf, o2, biomass):
    st.markdown(f"### {tx('Bilimsel Analiz Paneli', 'Scientific Analysis Panel')}")
    if not items:
        st.info(tx("Sol panelden ortama bir bileşik ekleyin. Her madde için araştırılmış etki veya yapay zeka tahmini burada görünür.",
                   "Add a compound to the medium from the left panel. The literature-based effect or AI estimate for each substance appears here."))
    else:
        for it, ev in zip(items, evals):
            st.markdown(ev_card(it, ev), unsafe_allow_html=True)
        names = [it["ad"][:28] for it in items]
        vals = [ev["carpan"] for ev in evals]
        colors = ["#3fb950" if v >= 1 else "#f85149" for v in vals]
        fig = go.Figure(go.Bar(x=vals, y=names, orientation="h", marker_color=colors,
                               text=[f"x{v:.2f}" for v in vals], textposition="outside"))
        fig.add_vline(x=1.0, line_dash="dot", line_color="#8b949e")
        fig.update_layout(template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
                          height=max(160, 70 + 45 * len(items)), margin=dict(l=0, r=30, t=10, b=10),
                          xaxis=dict(range=[0, max(1.5, max(vals) * 1.3)], title=tx("Büyüme çarpanı", "Growth factor")))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"**{tx('Toplam büyüme çarpanı', 'Total growth factor')}:** x{fa:.2f} ({(fa - 1) * 100:+.1f}%)")

    st.markdown(f"### {tx('Öneriler', 'Recommendations')}")
    for r in recommendations(info, volume, temp, light, tf, lf, o2, fa, items, evals):
        st.markdown(f"- {r}")

    st.markdown(f"### {tx('Deney Günlüğü', 'Experiment Log')}")
    if st.button(tx("Bu koşulları deney kaydına ekle", "Add these conditions to the log"),
                 use_container_width=True, key="log_add"):
        st.session_state.log.append({
            tx("Zaman", "Time"): datetime.now().strftime("%Y-%m-%d %H:%M"),
            tx("Tür", "Species"): selected,
            tx("Hacim_L", "Volume_L"): volume,
            tx("Sıcaklık_C", "Temp_C"): temp,
            tx("Işık", "Light"): light,
            tx("Maddeler", "Substances"): "; ".join(f"{it['ad']} {it['mgL']} mg/L" for it in items) or tx("yok", "none"),
            tx("Çarpan", "Factor"): round(fa, 3),
            tx("Biyokütle_g_gün", "Biomass_g_day"): round(biomass, 2),
            tx("O2_g_gün", "O2_g_day"): round(o2, 2),
            tx("Karşılama_%", "Coverage_%"): round(o2 / HUMAN_O2_NEED * 100, 1),
        })
    if st.session_state.log:
        df = pd.DataFrame(st.session_state.log)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(tx("CSV indir", "Download CSV"), df.to_csv(index=False).encode("utf-8-sig"),
                           file_name="deney_kaydi.csv", mime="text/csv", use_container_width=True)
        if st.button(tx("Kaydı temizle", "Clear log"), key="log_clear"):
            st.session_state.log = []
            st.rerun()


# ============================================================
# ANA GÖRÜNÜM
# ============================================================
info = algae_db[selected_algae]
items = st.session_state.additives
if items:
    with st.spinner(tx("Maddeler değerlendiriliyor...", "Evaluating substances...")):
        evals = [evaluate(it, selected_algae, info) for it in items]
else:
    evals = []

fa = 1.0
for ev in evals:
    fa *= min(2.0, max(0.0, ev["carpan"]))
fa = min(fa, 2.5)

tf, lf = temp_light_factors(info, user_temp, user_light)
rate = info["max_verim"] * tf * lf * fa
biomass = reactor_volume * rate
o2 = biomass * 1.35
fulfillment = o2 / HUMAN_O2_NEED * 100
eff_pct = int(tf * lf * 100)

if view_idx == 0:
    main, side = st.columns([2.1, 1])
    with main:
        st.markdown(f"### {tx('Sistem Analizi:', 'System analysis:')} `{selected_algae}`")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(metric_card(tx("GÜNLÜK TOPLAM BİYOKÜTLE", "DAILY TOTAL BIOMASS"), f"{biomass:.1f}", "g/gün",
                                    f"%{eff_pct} {tx('Çevresel Uyum Verimi', 'Environmental Fit Efficiency')}", "#ffffff"),
                        unsafe_allow_html=True)
        with c2:
            st.markdown(metric_card(tx("GÜNLÜK FOTOSENTETİK OKSİJEN", "DAILY PHOTOSYNTHETIC OXYGEN"), f"{o2:.1f}", "g/gün",
                                    tx("Stoökiometrik Oran: x1.35", "Stoichiometric ratio: x1.35"), "#58a6ff"),
                        unsafe_allow_html=True)
        with c3:
            st.markdown(metric_card(tx("İNSAN YAŞAM DESTEK ORANI", "HUMAN LIFE SUPPORT RATIO"), f"%{fulfillment:.1f}",
                                    tx("(1 Yetişkin)", "(1 adult)"),
                                    f"{fulfillment - 100:+.1f}% {tx('Hedef Farkı', 'vs. target')}", "#3fb950", 16),
                        unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"### {tx('Astronot Günlük Oksijen Karşılama Seviyesi', 'Astronaut Daily Oxygen Coverage')}")
        st.progress(min(1.0, o2 / HUMAN_O2_NEED))
        status = tx("1 İnsanın İhtiyacı Karşılandı", "One person's need is covered") if o2 >= HUMAN_O2_NEED \
            else tx("Ek Reaktör Hacmi Gerekli", "More reactor volume required")
        st.caption(tx(f"Günlük Hedef: 780g O₂ | Üretilen: {o2:.1f}g O₂ ({status})",
                      f"Daily target: 780 g O₂ | Produced: {o2:.1f} g O₂ ({status})"))

        t, n_with = growth_curve(tf * lf * fa, reactor_volume)
        _, n_base = growth_curve(tf * lf, reactor_volume)
        gfig = go.Figure()
        gfig.add_trace(go.Scatter(x=t, y=n_base, name=tx("Temel ortam", "Base medium"),
                                  line=dict(dash="dot", color="#8b949e")))
        gfig.add_trace(go.Scatter(x=t, y=n_with, name=tx("Ekli maddelerle", "With added substances"),
                                  line=dict(color="#3fb950", width=3)))
        gfig.update_layout(template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
                           height=300, margin=dict(l=10, r=10, t=40, b=10),
                           title=tx("Tahmini Büyüme Eğrisi (30 gün, basit lojistik model)",
                                    "Estimated growth curve (30 days, simple logistic model)"),
                           xaxis_title=tx("Gün", "Day"), yaxis_title=tx("Toplam biyokütle (g)", "Total biomass (g)"),
                           legend=dict(orientation="h", y=-0.3))
        st.plotly_chart(gfig, use_container_width=True)
        st.caption(tx("Bu eğri kalibre edilmemiş bir modeldir; yalnızca göreli karşılaştırma için kullanın.",
                      "This curve is an uncalibrated model; use it for relative comparison only."))
    with side:
        render_science(selected_algae, info, reactor_volume, user_temp, user_light,
                       items, evals, fa, tf, lf, o2, biomass)
    st.markdown("---")
    render_model(reactor_volume, selected_algae, info)
else:
    render_encyclopedia(selected_algae)