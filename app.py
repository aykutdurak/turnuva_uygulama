import streamlit as st
import random
import pandas as pd

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Turnuva Yöneticisi", layout="wide")

# --- BELLEK (SESSION STATE) YÖNETİMİ ---
# Streamlit her tıkta sayfayı yenilediği için verileri hafızada tutmalıyız.
if 'stage' not in st.session_state:
    st.session_state.stage = 'giris' # Aşamalar: giris -> oyuncu_ekle -> takim_ekle -> fikstur
if 'oyuncular' not in st.session_state:
    st.session_state.oyuncular = []
if 'fikstur' not in st.session_state:
    st.session_state.fikstur = []
if 'mac_sonuclari' not in st.session_state:
    st.session_state.mac_sonuclari = {} # {mac_id: (skor_ev, skor_dep)}

def reset_app():
    st.session_state.stage = 'giris'
    st.session_state.oyuncular = []
    st.session_state.fikstur = []
    st.session_state.mac_sonuclari = {}

# --- FONKSİYONLAR ---

def puan_durumu_hesapla():
    # Başlangıç verisi
    data = {o: {'O':0, 'G':0, 'B':0, 'M':0, 'AG':0, 'YG':0, 'AV':0, 'P':0} for o in st.session_state.oyuncular}
    
    for mac in st.session_state.fikstur:
        mid = mac['id']
        if mid in st.session_state.mac_sonuclari:
            s_ev, s_dep = st.session_state.mac_sonuclari[mid]
            
            # Skorlar girilmiş mi kontrolü (None değilse)
            if s_ev is not None and s_dep is not None:
                ev_sahibi = mac['ev_isim']
                deplasman = mac['dep_isim']
                
                # İstatistikleri işle
                data[ev_sahibi]['O'] += 1
                data[deplasman]['O'] += 1
                data[ev_sahibi]['AG'] += s_ev
                data[ev_sahibi]['YG'] += s_dep
                data[deplasman]['AG'] += s_dep
                data[deplasman]['YG'] += s_ev
                
                if s_ev > s_dep:
                    data[ev_sahibi]['P'] += 3
                    data[ev_sahibi]['G'] += 1
                    data[deplasman]['M'] += 1
                elif s_ev < s_dep:
                    data[deplasman]['P'] += 3
                    data[deplasman]['G'] += 1
                    data[ev_sahibi]['M'] += 1
                else:
                    data[ev_sahibi]['P'] += 1
                    data[deplasman]['P'] += 1
                    data[ev_sahibi]['B'] += 1
                    data[deplasman]['B'] += 1
                
                data[ev_sahibi]['AV'] = data[ev_sahibi]['AG'] - data[ev_sahibi]['YG']
                data[deplasman]['AV'] = data[deplasman]['AG'] - data[deplasman]['YG']

    # DataFrame oluştur ve sırala
    df = pd.DataFrame.from_dict(data, orient='index')
    df.index.name = 'Oyuncu'
    df = df.sort_values(by=['P', 'AV', 'AG'], ascending=False)
    return df

# --- ARAYÜZ (UI) ---

st.title("🏆 Dinamik Takımlı Turnuva")

# 1. AŞAMA: GİRİŞ
if st.session_state.stage == 'giris':
    st.info("Bu modda her oyuncu her maçta farklı takım yönetir. Oyuncu sayısına göre sistem takım sayısı isteyecektir.")
    
    col1, col2 = st.columns(2)
    with col1:
        sayi = st.number_input("Kaç kişi oynayacak?", min_value=2, max_value=20, value=4)
        if st.button("Başla"):
            st.session_state.oyuncu_sayisi = sayi
            st.session_state.stage = 'oyuncu_ekle'
            st.rerun()

# 2. AŞAMA: OYUNCU İSİMLERİ
elif st.session_state.stage == 'oyuncu_ekle':
    st.subheader(f"{st.session_state.oyuncu_sayisi} Oyuncu İsmi Giriniz")
    
    with st.form("oyuncu_form"):
        isimler = []
        cols = st.columns(2) # Mobilde alt alta, pcde yan yana görünür
        for i in range(st.session_state.oyuncu_sayisi):
            with cols[i % 2]:
                ad = st.text_input(f"{i+1}. Oyuncu Adı", key=f"oyuncu_{i}")
                isimler.append(ad)
        
        submitted = st.form_submit_button("Takım Girişine Geç")
        if submitted:
            # Boş isim kontrolü
            if all(isimler):
                st.session_state.oyuncular = isimler
                st.session_state.stage = 'takim_ekle'
                st.rerun()
            else:
                st.error("Lütfen tüm isimleri giriniz.")

# 3. AŞAMA: TAKIM HAVUZU
elif st.session_state.stage == 'takim_ekle':
    N = len(st.session_state.oyuncular)
    gerekli_takim = N * (N - 1)
    
    st.subheader("Takım Havuzu Oluşturma")
    st.warning(f"⚠️ Kural gereği **{gerekli_takim}** adet takım girmelisiniz.")
    st.info("Takımları alt alta listeli bir şekilde yapıştırabilirsiniz.")

    takimlar_text = st.text_area("Takım Listesi (Her satıra bir takım)", height=300, help="Örn:\nGalatasaray\nFenerbahçe\nReal Madrid...")
    
    if st.button("Fikstürü Oluştur"):
        girilen_takimlar = [t.strip() for t in takimlar_text.split('\n') if t.strip()]
        
        if len(girilen_takimlar) < gerekli_takim:
            st.error(f"Yetersiz Takım! Şu an {len(girilen_takimlar)} adet girdiniz. En az {gerekli_takim} gerekli.")
        else:
            # --- FİKSTÜR MANTIĞI BURADA ÇALIŞIR ---
            random.shuffle(girilen_takimlar)
            havuz = girilen_takimlar[:gerekli_takim] # Fazlası varsa kes
            
            # Eşleşmeler
            eslesmeler = []
            for i in range(N):
                for j in range(i + 1, N):
                    eslesmeler.append((st.session_state.oyuncular[i], st.session_state.oyuncular[j]))
            
            random.shuffle(eslesmeler)
            
            # Fikstür oluşturma
            maclar = []
            takim_idx = 0
            mac_id_counter = 1
            
            for p1, p2 in eslesmeler:
                tA = havuz[takim_idx]
                tB = havuz[takim_idx+1]
                takim_idx += 2
                
                # 1. Maç
                maclar.append({
                    'id': mac_id_counter,
                    'tur': 'İlk Maç',
                    'ev_isim': p1, 'ev_takim': tA,
                    'dep_isim': p2, 'dep_takim': tB
                })
                mac_id_counter += 1
                
                # 2. Maç (Rövanş - Takımlar değişiyor)
                maclar.append({
                    'id': mac_id_counter,
                    'tur': 'Rövanş',
                    'ev_isim': p2, 'ev_takim': tA, # p2, tA'yı aldı
                    'dep_isim': p1, 'dep_takim': tB  # p1, tB'yi aldı
                })
                mac_id_counter += 1
            
            st.session_state.fikstur = maclar
            st.session_state.stage = 'fikstur'
            st.rerun()

# 4. AŞAMA: FİKSTÜR VE PUAN DURUMU
elif st.session_state.stage == 'fikstur':
    
    tab1, tab2 = st.tabs(["⚽ Fikstür & Skor", "📊 Puan Durumu"])
    
    with tab1:
        st.write("Skorları girdikten sonra 'Enter'a basmanız veya dışarı tıklamanız yeterlidir.")
        
        for mac in st.session_state.fikstur:
            mid = mac['id']
            
            # Görsel ayraç (Rövanş ayrımı yerine maç kartı tasarımı)
            with st.container():
                # Kart Görünümü için CSS hilesi yerine Streamlit kolonları
                c1, c2, c3, c4, c5 = st.columns([3, 1, 0.5, 1, 3])
                
                # Ev Sahibi Bilgisi
                with c1:
                    st.markdown(f"<div style='text-align: right'><b>{mac['ev_isim']}</b><br><span style='color:gray; font-size:0.8em'>{mac['ev_takim']}</span></div>", unsafe_allow_html=True)
                
                # Skor Girişleri
                mevcut_skor = st.session_state.mac_sonuclari.get(mid, (None, None))
                
                with c2:
                    s1 = st.number_input("E", value=mevcut_skor[0], key=f"s1_{mid}", label_visibility="collapsed", step=1, min_value=0)
                with c3:
                    st.write("-")
                with c4:
                    s2 = st.number_input("D", value=mevcut_skor[1], key=f"s2_{mid}", label_visibility="collapsed", step=1, min_value=0)
                
                # Deplasman Bilgisi
                with c5:
                    st.markdown(f"<div style='text-align: left'><b>{mac['dep_isim']}</b><br><span style='color:gray; font-size:0.8em'>{mac['dep_takim']}</span></div>", unsafe_allow_html=True)
                
                # Skoru anlık kaydet
                if s1 is not None and s2 is not None:
                    st.session_state.mac_sonuclari[mid] = (s1, s2)
                
                st.divider()

    with tab2:
        st.subheader("Canlı Puan Durumu")
        df_puan = puan_durumu_hesapla()
        st.dataframe(df_puan, use_container_width=True)

    if st.button("Turnuvayı Sıfırla (Başa Dön)", type="primary"):
        reset_app()
        st.rerun()
