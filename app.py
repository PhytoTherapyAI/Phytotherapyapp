import streamlit as st
from docx import Document
import os

# Sayfa Ayarları
st.set_page_config(page_title="Phytotherapy.ai", page_icon="🌿", layout="wide")

# --- VERİ İŞLEME FONKSİYONU ---
def load_rag_data(file_path):
    if not os.path.exists(file_path):
        return "Veri dosyası bulunamadı."
    
    doc = Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return "\n".join(full_text)

# Veriyi yükle
rag_content = load_rag_data("RAG.docx")

# --- ARAYÜZ ---
with st.sidebar:
    st.title("🌿 Phytotherapy.ai")
    st.markdown("**Kanıta Dayalı Fitoterapi Asistanı**")
    st.divider()
    st.markdown("### 🔍 Analiz Durumu")
    if "Veri dosyası" not in rag_content:
        st.success("✅ RAG Veri Seti Yüklendi")
        st.caption("10 Bölüm ve 20+ Meta-Analiz aktif.")
    else:
        st.error("❌ Veri Seti Eksik")
    
    st.divider()
    st.warning("⚠️ **Tıbbi Uyarı:** Bu bir karar destek sistemidir. Doktorunuza danışmadan tedavi değişikliği yapmayınız.")

st.title("Phyto-Asistan Canlıda!")
st.info("Şu an hazırladığın RAG.docx dosyasındaki bilgilere göre cevap veriyorum.")

# Sohbet Geçmişi
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- SORU-CEVAP MANTIĞI ---
prompt = st.chat_input("Örn: Doğum kontrol hapı ve Sarı Kantaron etkileşimi nedir?")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Basit ama etkili bir RAG Arama Mantığı
    # Kullanıcının sorduğu kelimeyi Word dosyasında arar ve ilgili bölümü getirir
    response = ""
    keywords = prompt.lower().split()
    
    # Word dosyasını bölümlere ayırarak tarayalım
    sections = rag_content.split("BÖLÜM")
    found_info = []
    
    for section in sections:
        # Eğer kullanıcının sorduğu kelime bu bölümde geçiyorsa
        if any(keyword in section.lower() for keyword in keywords if len(keyword) > 3):
            found_info.append(section)
    
    if found_info:
        context = "\n".join(found_info[:2]) # En ilgili 2 bölümü al
        asistan_cevabi = f"🔍 **Literatür Taraması Sonucu:**\n\n{context}\n\n---\n**💡 Not:** Bu bilgiler hazırladığınız meta-analiz özetlerinden (RAG.docx) çekilmiştir."
    else:
        asistan_cevabi = "❌ Üzgünüm, bu spesifik etkileşim hakkında hazırladığımız veri setinde (RAG.docx) bir eşleşme bulamadım. Lütfen Sarı Kantaron, Greyfurt, Meyan Kökü gibi anahtar kelimelerle tekrar deneyin."

    with st.chat_message("assistant", avatar="🌿"):
        st.markdown(asistan_cevabi)
    st.session_state.messages.append({"role": "assistant", "content": asistan_cevabi})
