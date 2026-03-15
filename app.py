import streamlit as st

# Sayfa Ayarları (Sekme adı ve geniş görünüm)
st.set_page_config(page_title="Phytotherapy.ai", page_icon="🌿", layout="wide")

# Sol Menü (Sidebar) - Kamera ve Profil Alanı
with st.sidebar:
    st.title("🌿 Phytotherapy.ai")
    st.markdown("**Kanıta Dayalı Fitoterapi Asistanı**")
    st.divider()
    
    st.markdown("### 📸 Akıllı Eczane Dolabı")
    st.info("Yakında: Reçetenizi veya ilaç kutunuzu buraya yükleyebileceksiniz.")
    uploaded_file = st.file_uploader("Fotoğraf Yükle (Faz 3'te aktif olacak)", type=["jpg", "png", "pdf"])
    
    st.divider()
    st.warning("⚠️ **Tıbbi Uyarı:** Bu sistem sadece meta-analiz düzeyindeki kanıtlarla karar destek hizmeti sunar. Acil durumlarda 112'yi arayınız.")

# Ana Ekran - Sohbet Arayüzü
st.title("Phyto-Asistan'a Hoş Geldiniz")
st.markdown("Dünyanın ilk sıfır halüsinasyonlu, kanıta dayalı bitki-ilaç etkileşim asistanı.")

# Sohbet Geçmişini Hafızada Tutma
if "messages" not in st.session_state:
    st.session_state.messages = []

# Eski mesajları ekrana basma (varsa)
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Kullanıcıdan Mesaj Alma Çubuğu
prompt = st.chat_input("Örn: Warfarin kullanıyorum, Ginkgo Biloba alabilir miyim?")

if prompt:
    # Kullanıcının mesajını ekrana bas ve hafızaya al
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Botun Şimdilik Vereceği Sahte Cevap (RAG bağlanana kadar)
    asistan_cevabi = "⏳ *Merhaba! Arayüzümüz başarıyla kuruldu. Arka plandaki RAG veritabanımız (Altın Veri Seti) bir sonraki adımda sisteme entegre edilecek ve sorularınıza kanıta dayalı tıp literatürüyle cevap vermeye başlayacağım.*"
    
    with st.chat_message("assistant", avatar="🌿"):
        st.markdown(asistan_cevabi)
    st.session_state.messages.append({"role": "assistant", "content": asistan_cevabi})
