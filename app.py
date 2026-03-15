import streamlit as st
from docx import Document
import os
from groq import Groq

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Phytotherapy.ai", page_icon="🌿", layout="wide")

try:
    groq_api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=groq_api_key)
except Exception as e:
    st.error("⚠️ Lütfen Streamlit ayarlarından GROQ_API_KEY ekleyin.")
    st.stop()

@st.cache_data
def load_rag_data(file_path):
    if not os.path.exists(file_path):
        return "Veri dosyası bulunamadı."
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip() != ""])

full_rag_content = load_rag_data("RAG.docx")

# --- BEYİN 1: HAFIZALI VE ŞEFKATLİ ASİSTAN ---
def get_patient_response(user_prompt, database, chat_history):
    system_prompt = f"""Sen dünyanın en gelişmiş, şefkatli Klinik Farmakoloji Asistanısın. 
Hastanın önceki söylediklerini hatırlayarak (Hafıza) organik bir sohbet yürüt.

GÖREVLERİN:
1. HAFIZA KULLANIMI: Sana hastanın önceki mesajları da iletiliyor. Hasta bağlamı (context) eksik bir soru sorarsa, önceki mesajlarında bahsettiği hastalıkları veya ilaçları hatırla.
2. TRİYAJ: Göğüs ağrısı, nefes darlığı, şiddetli kanama gibi durumlarda anında 112'ye yönlendir.
3. POLİFARMASİ: Hasta toplamda 3 veya daha fazla kronik ilaç kullanıyorsa doktora danışmadan bitki kullanmamasını kesin bir dille belirt.
4. TIBBİ ANALİZ VE YAN ETKİ: Hastanın şikayeti, kullandığı ilacın yan etkisi olabilir mi? Uyar.
5. RAG VERİTABANI: Aşağıdaki [ALTIN VERİTABANI] içindeki bilgilerle eşleşme varsa 🔴 RİSKLİ, 🟡 DİKKAT veya 🟢 GÜVENLİ emojisiyle uyarı yap. Jargonu halk diline çevir. Sıfır riskli alternatifi öner. Eşleşme yoksa dürüstçe "Veri setimde yok" de.

[ALTIN VERİTABANI BAŞLANGICI]
{database}
[ALTIN VERİTABANI BİTİŞİ]
"""

    # Sistem promptunu ekle
    messages = [{"role": "system", "content": system_prompt}]
    
    # HAFIZA: Sadece son 4 mesajı (2 soru, 2 cevap) AI'ın beynine yükle ki çok token harcamasın
    recent_history = chat_history[-4:] if len(chat_history) > 4 else chat_history
    for msg in recent_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    # Hastanın yeni mesajını ekle
    messages.append({"role": "user", "content": user_prompt})
    
    try:
        chat_completion = client.chat.completions.create(
            messages=messages, model="llama-3.3-70b-versatile", temperature=0.3, max_tokens=1024
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"❌ Yanıt hatası: {e}"

# --- BEYİN 2: DOKTOR İÇİN KONSÜLTASYON MEKTUBU ---
def get_doctor_letter(user_prompt, database, chat_history):
    system_prompt = f"""Sen uzman bir klinik farmakologsun. Hastanın tüm sohbet geçmişini ve aşağıdaki [ALTIN VERİTABANI] içindeki makaleleri analiz ederek, hastanın hekimine yönelik 'Konsültasyon Bilgi Notu' yaz.

KURALLAR:
1. "Sayın Meslektaşım," diye başla.
2. Hastanın olası ilaç yan etkilerini veya polifarmasi riskini tıbbi bir dille özetle.
3. Eşleşme varsa, MUTLAKA makalenin "PMID" numarasını referans göster (Örn: "PMID: 26299317 referanslı çalışmaya göre...").

[ALTIN VERİTABANI BAŞLANGICI]
{database}
[ALTIN VERİTABANI BİTİŞİ]
"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # Doktor mektubu için de hastanın hafızasını yolluyoruz
    recent_history = chat_history[-4:] if len(chat_history) > 4 else chat_history
    for msg in recent_history:
        if msg["role"] == "user": # Sadece hastanın dediklerini baz al
            messages.append({"role": "user", "content": msg["content"]})
            
    messages.append({"role": "user", "content": user_prompt})
    
    try:
        chat_completion = client.chat.completions.create(
            messages=messages, model="llama-3.3-70b-versatile", temperature=0.2, max_tokens=800
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return "Doktor mektubu oluşturulamadı."

# --- ARAYÜZ ---
with st.sidebar:
    st.title("🌿 Phytotherapy.ai")
    st.markdown("**Kanıta Dayalı Fitoterapi Asistanı**")
    st.divider()
    st.markdown("### 🧠 Sistem Beyni")
    st.success("✅ Full-Context AI Mimarisi")
    st.success("✅ Kısa Süreli Hafıza (Memory)")
    st.success("✅ Çift LLM (Hasta & Hekim)")
    st.divider()
    st.warning("⚠️ **Tıbbi Uyarı:** Karar destek sistemidir.")

st.title("Phyto-Asistan")
st.markdown("Sizi dinleyen, geçmişi unutmayan ve doktorunuza tıbbi rapor hazırlayan asistan.")

# Hafızayı Başlat (Session State)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Eski mesajları ekrana bas
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Selam verebilir, şikayetinizi ve ilaçlarınızı yazabilirsiniz...")

if prompt:
    # 1. Hastanın yeni mesajını ekrana bas ve hafızaya kaydet
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 2. AI'a cevap üretmesi için gönder (Burada geçmiş mesajları da gönderiyoruz)
    with st.spinner("Phyto-Asistan geçmişinizi hatırlıyor ve değerlendiriyor..."):
        patient_response = get_patient_response(prompt, full_rag_content, st.session_state.messages)

    # 3. AI cevabını ekrana bas ve hafızaya kaydet
    with st.chat_message("assistant", avatar="🌿"):
        st.markdown(patient_response)
        
        # Doktor Mektubu
        if len(prompt.split()) > 2 and "112" not in patient_response:
            with st.spinner("Hekim için konsültasyon notu hazırlanıyor..."):
                doctor_letter = get_doctor_letter(prompt, full_rag_content, st.session_state.messages)
            
            with st.expander("🩺 Hekiminiz İçin Tıbbi Konsültasyon Notu (PMID Referanslı)"):
                st.info("Bu bölüm hekiminize göstermeniz için akademik dille hazırlanmıştır.")
                st.write(doctor_letter)

    # En son kullanıcının mesajını ve asistanın cevabını hafıza listesine kalıcı ekle
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.messages.append({"role": "assistant", "content": patient_response})
