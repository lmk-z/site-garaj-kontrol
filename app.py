
import streamlit as st
import pandas as pd
import pytesseract
import cv2
import numpy as np
from PIL import Image

st.set_page_config(page_title="Site Garaj Kontrol", page_icon="🚗", layout="centered")

st.title("🚗 Site Garajı Canlı Plaka Kontrolü")
st.write("Garajda tur atarken aracın fotoğrafını çekin, sistem anında Excel ile karşılaştırsın.")

# Excel Dosyasını Otomatik veya Yüklemeli Alalım
uploaded_file = st.file_uploader("Site Araç Listesi Excel Dosyasını Yükleyin (site_arac_listesi.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    
    @st.cache_data
    def veri_tabanini_hazirla(excel_df):
        plaka_to_daire = {}
        for idx, row in excel_df.iterrows():
            blok = row['Blok']
            daire = row['Daire']
            kisi_tipi = row.iloc[2]
            arac_bilgisi = str(row['Araç Bilgileri'])
            
            plakalar = arac_bilgisi.split('\n')
            for p in plakalar:
                temiz_p = p.replace(' ', '').replace('(', '').replace(')', '').upper().strip()
                if len(temiz_p) >= 5:
                    plaka_to_daire[temiz_p] = {
                        'Blok': blok,
                        'Daire': daire,
                        'Tip': kisi_tipi,
                        'Ham_Veri': p
                    }
        return plaka_to_daire

    kayitli_araclar = veri_tabanini_hazirla(df)
    st.success(f"✅ Veritabanı yüklendi! Toplam {len(kayitli_araclar)} araç aktif.")

    # Oturum durumu
    if 'tarananlar' not in st.session_state:
        st.session_state.tarananlar = set()
    if 'daire_sayaclari' not in st.session_state:
        st.session_state.daire_sayaclari = {}

    st.divider()
    
    # Telefon kamerasını doğrudan açan bileşen (Mobilde doğrudan kamera veya galeri seçeneği sunar)
    kamera_fotosu = st.camera_input("📸 Plakayı Çek ve Tara")

    if kamera_fotosu is not None:
        bytes_data = kamera_fotosu.getvalue()
        np_img = np.frombuffer(bytes_data, np.uint8)
        img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Tesseract OCR ile oku
        tesseract_text = pytesseract.image_to_string(gray, lang='tur+eng')
        
        kelimeler = tesseract_text.split()
        bulunanlar = []
        for kelime in kelimeler:
            temiz = kelime.replace('-', '').replace(' ', '').upper()
            if len(temiz) >= 5:
                bulunanlar.append(temiz)

        benzersiz_bulunanlar = list(set(bulunanlar))
        
        if benzersiz_bulunanlar:
            for plaka in benzersiz_bulunanlar:
                if plaka not in st.session_state.tarananlar:
                    st.session_state.tarananlar.add(plaka)
                    
                    if plaka in kayitli_araclar:
                        bilgi = kayitli_araclar[plaka]
                        daire_key = f"Blok: {bilgi['Blok']} - Daire: {bilgi['Daire']}"
                        st.success(f"✅ **KAYITLI** | Plaka: `{plaka}` -> **{daire_key}** ({bilgi['Tip']})")
                        
                        if daire_key not in st.session_state.daire_sayaclari:
                            st.session_state.daire_sayaclari[daire_key] = []
                        st.session_state.daire_sayaclari[daire_key].append(plaka)
                    else:
                        st.error(f"❌ **KAYITSIZ / YABANCI** | Plaka: `{plaka}` -> Listede bulunamadı!")
                else:
                    st.info(f"ℹ️ `{plaka}` plakası bu oturumda zaten tarandı.")
        else:
            st.warning("⚠️ Net bir plaka okunamadı. Kamerayı biraz daha yaklaştırıp tekrar deneyin.")

    # Canlı İhlal Raporu
    st.divider()
    st.subheader("📊 Canlı Kural İhlali Raporu")
    st.write(f"Şu ana kadar taranan benzersiz araç sayısı: {len(st.session_state.tarananlar)}")

    if st.session_state.daire_sayaclari:
        ihlal_var = False
        for daire, araclari in st.session_state.daire_sayaclari.items():
            if len(araclari) > 1:
                ihlal_var = True
                st.warning(f"⚠️ **{daire}**: Garajda tespit edilen araç sayısı: {len(araclari)} ({araclari}) -> **KURAL İHLALİ!**")
        
        if not ihlal_var:
            st.info("Harika! Birden fazla aracı olan (ihlal yapan) daire tespit edilmedi.")
            
    if st.button("🔄 Oturumu Sıfırla"):
        st.session_state.tarananlar.clear()
        st.session_state.daire_sayaclari.clear()
        st.rerun()
else:
    st.info("💡 Başlamak için lütfen yukarıdan Excel dosyanızı (`site_arac_listesi.xlsx`) yükleyin.")
