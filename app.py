import cv2
import numpy as np
import pandas as pd
import pytesseract
import streamlit as st

st.set_page_config(
    page_title="Site Garaj Kontrol", page_icon="🔐", layout="centered"
)


# --- ŞİFRE KORUMA FONKSİYONU ---
def check_password():
  """Returns `True` if the user had the correct password."""

  def password_entered():
    if st.session_state["password"] == "SiteYonetici8a":  # Buradaki şifreyi değiştirebilirsiniz!
      st.session_state["password_correct"] = True
      del st.session_state["password"]  # Şifreyi hafıradan sil
    else:
      st.session_state["password_correct"] = False

  if "password_correct" not in st.session_state:
    # İlk açılışta şifre kutusunu göster
    st.text_input(
        "🔑 Lütfen Yönetici Şifresini Girin",
        type="password",
        on_change=password_entered,
        key="password",
    )
    return False
  elif not st.session_state["password_correct"]:
    # Yanlış şifre girildiyse
    st.text_input(
        "🔑 Lütfen Yönetici Şifresini Girin",
        type="password",
        on_change=password_entered,
        key="password",
    )
    st.error("😕 Şifre hatalı. Lütfen tekrar deneyin.")
    return False
  else:
    # Şifre doğru
    return True


if not check_password():
  st.stop()  # Şifre girilene kadar uygulamanın geri kalanını durdur

# --- UYGULAMA ANA GÖVDESİ ---
st.title("🚗 Site Garajı Canlı Plaka Kontrolü")
st.write(
    "Garajda tur atarken aracın fotoğrafını çekin, sistem anında Excel ile"
    " karşılaştırsın."
)

uploaded_file = st.file_uploader(
    "Site Araç Listesi Excel Dosyasını Yükleyin (site_arac_listesi.xlsx)",
    type=["xlsx"],
)

if uploaded_file is not None:
  df = pd.read_excel(uploaded_file)


  @st.cache_data
  def veri_tabanini_hazirla(excel_df):
    plaka_to_daire = {}
    for idx, row in excel_df.iterrows():
      blok = row["Blok"]
      daire = row["Daire"]
      kisi_tipi = row.iloc[2]
      arac_bilgisi = str(row["Araç Bilgileri"])

      plakalar = arac_bilgisi.split("\n")
      for p in plakalar:
        temiz_p = (
            p.replace(" ", "").replace("(", "").replace(")", "").upper().strip()
        )
        if len(temiz_p) >= 5:
          plaka_to_daire[temiz_p] = {
              "Blok": blok,
              "Daire": daire,
              "Tip": kisi_tipi,
              "Ham_Veri": p,
          }
    return plaka_to_daire


  kayitli_araclar = veri_tabanini_hazirla(df)
  st.success(
      f"✅ Veritabanı yüklendi! Toplam {len(kayitli_araclar)} araç aktif."
  )

  if "tarananlar" not in st.session_state:
    st.session_state.tarananlar = set()
  if "daire_sayaclari" not in st.session_state:
    st.session_state.daire_sayaclari = {}

  st.divider()

  kamera_fotosu = st.camera_input("📸 Plakayı Çek ve Tara")

  if kamera_fotosu is not None:
    bytes_data = kamera_fotosu.getvalue()
    np_img = np.frombuffer(bytes_data, np.uint8)
    img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if 'tarananlar' not in st.session_state: # (kodun devamı aynı)
