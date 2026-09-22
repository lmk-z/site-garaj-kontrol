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
    if st.session_state["password"] == "yonetici123":  # Şifrenizi buradan değiştirebilirsiniz
      st.session_state["password_correct"] = True
      del st.session_state["password"]
    else:
      st.session_state["password_correct"] = False

  if "password_correct" not in st.session_state:
    st.text_input(
        "🔑 Lütfen Yönetici Şifresini Girin",
        type="password",
        on_change=password_entered,
        key="password",
    )
    return False
  elif not st.session_state["password_correct"]:
    st.text_input(
        "🔑 Lütfen Yönetici Şifresini Girin",
        type="password",
        on_change=password_entered,
        key="password",
    )
    st.error("😕 Şifre hatalı. Lütfen tekrar deneyin.")
    return False
  else:
    return True


if not check_password():
  st.stop()

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

  # Doğrudan arka kamerayı açan parametre (environment) eklendi
  kamera_fotosu = st.camera_input(
      "📸 Plakayı Çek ve Tara", facing_mode="environment"
  )

  if kamera_fotosu is not None:
    bytes_data = kamera_fotosu.getvalue()
    np_img = np.frombuffer(bytes_data, np.uint8)
    img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    tesseract_text = pytesseract.image_to_string(gray, lang="tur+eng")

    kelimeler = tesseract_text.split()
    bulunanlar = []
    for kelime in kelimeler:
      temiz = kelime.replace("-", "").replace(" ", "").upper()
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
            st.success(
                f"✅ **KAYITLI** | Plaka: `{plaka}` -> **{daire_key}**"
                f" ({bilgi['Tip']})"
            )

            if daire_key not in st.session_state.daire_sayaclari:
              st.session_state.daire_sayaclari[daire_key] = []
            st.session_state.daire_sayaclari[daire_key].append(plaka)
          else:
            st.error(
                f"❌ **KAYITSIZ / YABANCI** | Plaka: `{plaka}` -> Listede"
                " bulunamadı!"
            )
        else:
          st.info(f"ℹ️ `{plaka}` plakası bu oturumda zaten tarandı.")
    else:
      st.warning(
          "⚠️ Net bir plaka okunamadı. Kamerayı biraz daha yaklaştırıp tekrar"
          " deneyin."
      )

  st.divider()
  st.subheader("📊 Canlı Kural İhlali Raporu")
  st.write(
      f"Şu ana kadar taranan benzersiz araç sayısı:"
      f" {len(st.session_state.tarananlar)}"
  )

  if st.session_state.daire_sayaclari:
    ihlal_var = False
    for daire, araclari in st.session_state.daire_sayaclari.items():
      if len(araclari) > 1:
        ihlal_var = True
        st.warning(
            f"⚠️ **{daire}**: Garajda tespit edilen araç sayısı:"
            f" {len(araclari)} ({araclari}) -> **KURAL İHLALİ!**"
        )

    if not ihlal_var:
      st.info(
          "Harika! Birden fazla aracı olan (ihlal yapan) daire tespit"
          " edilmedi."
      )

  if st.button("🔄 Oturumu Sıfırla"):
    st.session_state.tarananlar.clear()
    st.session_state.daire_sayaclari.clear()
    st.rerun()
else:
  st.info(
      "💡 Başlamak için lütfen yukarıdan Excel dosyanızı"
      " (`site_arac_listesi.xlsx`) yükleyin."
  )
