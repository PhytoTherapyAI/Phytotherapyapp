import streamlit as st
from docx import Document
import os
import google.generativeai as genai

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Phytotherapy.ai", page_icon="🌿", layout="wide")

# --- GEMINI API BAĞLANTISI ---
try:
    gemini_api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=gemini_api_key)
    # Gemini 1.5 Pro veya Flash kullanabiliriz. Pro daha zekidir, Flash daha hızlıdır.
    model_name = 'gemini-1.5-pro' 
except Exception as e:
    st.error("⚠️ Lütfen Streamlit ayarlarından GEMINI_API_KEY ekleyin.")
    st.stop()

# --- VERİ İŞLEME FONKSİYONU ---
@st.cache_data
def load_rag_data(file_path):
    if not os.path.exists(file_path):
        return "Veri dosyası bulunamadı."
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip() != ""])

full_rag_content = load_rag_data("RAG.docx")

# --- SESSION STATE (HAFIZA VE EKRAN KONTROLÜ) ---
if "onboarding_complete" not in st.session_state:
    st.session_state.onboarding_complete = False
if "patient_data" not in st.session_state:
    st.session_state.patient_data = {}
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- BEYİN 1: HASTA İÇİN ŞEFKATLİ ASİSTAN ---
def get_patient_response(user_prompt, database, patient_data, chat_history):
    # Triyaj bilgilerini sistem promptuna enjekte ediyoruz!
    triage_info = f"""
    [HASTAYA AİT TRİYAJ (ANAMNEZ) BİLGİLERİ]
    - Ana Şikayet / Geliş Sebebi: {patient_data.get('sikayet', 'Belirtilmedi')}
    - Mevcut Kullanılan İlaçlar: {patient_data.get('ilaclar', 'Belirtilmedi')}
    - Bilinen Alerjiler: {patient_data.get('alerji', 'Belirtilmedi')}
    """

    system_instruction = f"""Sen dünyanın en gelişmiş, şefkatli Klinik Farmakoloji Asistanısın (Phyto-Asistan).
Senin hafızana hastanın triyaj bilgileri kaydedildi. Bu bilgileri ASLA unutma.

GÖREVLERİN:
1. TRİYAJ BİLGİSİNİ KULLAN: Hasta seninle konuşurken, onun 'Mevcut Kullanılan İlaçlar' listesindeki ilaçları bildiğini belli et. (Örn: "Triyaj formunda belirttiğiniz statin ilacı...")
2. ACİL DURUM KONTROLÜ: Eğer şikayet göğüs ağrısı, nefes darlığı gibi acil bir durumsa anında 112'ye yönlendir.
3. POLİFARMASİ: Triyaj formundaki 'Kullanılan İlaçlar' listesinde 3 veya daha fazla kronik ilaç varsa, bitkisel ürünlerin tehlikesini anlat ve doktora danışmasını söyle.
4. YAN ETKİ RADARI: Hastanın şikayeti, kullandığı ilaçların bilinen bir yan etkisi olabilir mi? Kendi klinik farmakoloji bilgini kullanarak hastayı uyar.
5. RAG VERİTABANI: Aşağıdaki [ALTIN VERİTABANI] içindeki bilgilerle hastanın durumunu karşılaştır. Eşleşme varsa 🔴 RİSKLİ, 🟡 DİKKAT veya 🟢 GÜVENLİ emojisiyle uyarı yap. Sıfır riskli alternatifi öner. Veri yoksa uydurma. Asla rolünden çıkma.

{triage_info}

[ALTIN VERİTABANI BAŞLANGICI]
{database}
[ALTIN VERİTABANI BİTİŞİ]
"""

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_instruction
    )
    
    # Geçmiş mesajları Gemini formatına çevir
    formatted_history = []
    for msg in chat_history:
        role = "user" if msg["role"] == "user" else "model"
        formatted_history.append({"role": role, "parts": [msg["content"]]})
        
    chat = model.start_chat(history=formatted_history)
    
    try:
        response = chat.send_message(user_prompt)
        return response.text
    except Exception as e:
        return f"❌ Yanıt hatası: {e}"

# --- BEYİN 2: DOKTOR İÇİN KONSÜLTASYON MEKTUBU ---
def get_doctor_letter(user_prompt, database, patient_data, chat_history):
    triage_info = f"""
    [HASTA TRİYAJ BİLGİLERİ]
    - Şikayet: {patient_data.get('sikayet', 'Belirtilmedi')}
    - İlaçlar: {patient_data.get('ilaclar', 'Belirtilmedi')}
    - Alerjiler: {patient_data.get('alerji', 'Belirtilmedi')}
    """

    system_instruction = f"""Sen uzman bir klinik farmakologsun. Triyaj bilgilerini ve [ALTIN VERİTABANI]'nı kullanarak hekime 'Konsültasyon Bilgi Notu' yaz.
KURALLAR:
1. "Sayın Meslektaşım," diye başla.
2. Triyaj formundaki ilaçların birbirleriyle veya yeni şikayetle olan ilişkisini (Polifarmasi / Yan Etki) akademik dille özetle.
3. [ALTIN VERİTABANI] ile eşleşme varsa, MUTLAKA makalenin "PMID" numarasını referans göster (Örn: "PMID: 26299317 referanslı çalışmaya göre...").

{triage_info}

[ALTIN VERİTABANI BAŞLANGICI]
{database}
[ALTIN VERİTABANI BİTİŞİ]
"""
    model = genai.GenerativeModel(model_name=model_name, system_instruction=system_instruction)
    
    # Sadece hastanın dediklerini baz al
    prompt_context = f"Son Hastanın Mesajı: {user_prompt}"
    
    try:
        response = model.generate_content(prompt_context)
        return response.text
    except Exception as e:
        return "Doktor mektubu oluşturulamadı."

# ==========================================
# ARAYÜZ KONTROLÜ (TRİYAJ MI? SOHBET Mİ?)
# ==========================================

if not st.session_state.onboarding_complete:
    # ------------------------------------------
    # 1. EKRAN: TRİYAJ VE HASTA KABUL FORMU
    # ------------------------------------------
    st.title("🩺 Phytotherapy.ai | Hasta Kabul")
    st.markdown("Lütfen Phyto-Asistan ile görüşmeden önce tıbbi bilgilerinizi giriniz. Bu bilgiler size en doğru analizi sunmamız için kullanılacaktır.")
    
    with st.container():
        col1, col2 = st.columns(2)
        
        with col1:
            sikayet = st.text_area("🔴 Ana Şikayetiniz Nedir?", placeholder="Örn: Kaslarımda kramp var, uykusuzluk çekiyorum...", height=100)
            alerji = st.text_input("⚠️ Bilinen Bir Alerjiniz Var mı?", placeholder="Örn: Penisilin, Fıstık, Yok")
            
        with col2:
            ilaclar = st.text_area("💊 Akıllı Ecza Dolabı (Kullandığınız İlaçlar)", placeholder="Örn: Statin, Metformin, Diüretik...", height=100)
            st.info("📸 **Yakında:** Reçete veya ilaç kutunuzu buraya yükleyebileceksiniz (Faz 3).")
            uploaded_file = st.file_uploader("Kamera/OCR Yükleme Alanı", type=["jpg", "png", "pdf"])
            
    st.divider()
    
    # Formu Gönder ve Sohbete Geç
    if st.button("🚀 Asistanı Başlat ve Analize Geç", type="primary", use_container_width=True):
        st.session_state.patient_data = {
            "sikayet": sikayet,
            "ilaclar": ilaclar,
            "alerji": alerji
        }
        # Sistemin hafızasına ilk mesaj olarak giriş yap
        st.session_state.messages = [] 
        st.session_state.onboarding_complete = True
        st.rerun() # Sayfayı yenile ve sohbet ekranına geç

else:
    # ------------------------------------------
    # 2. EKRAN: ANA SOHBET ARAYÜZÜ
    # ------------------------------------------
    with st.sidebar:
        st.title("🌿 Phytotherapy.ai")
        st.success("✅ Triyaj Dosyası Alındı")
        st.info(f"**İlaçlar:** {st.session_state.patient_data.get('ilaclar', 'Yok')}")
        st.info(f"**Alerji:** {st.session_state.patient_data.get('alerji', 'Yok')}")
        
        st.divider()
        st.markdown("### 🧠 Sistem Beyni")
        st.success("✅ Google Gemini 1.5 Pro")
        st.success("✅ Çift LLM Mimarisi")
        
        st.divider()
        if st.button("🔄 Triyajı Sıfırla (Yeni Hasta)"):
            st.session_state.onboarding_complete = False
            st.session_state.patient_data = {}
            st.session_state.messages = []
            st.rerun()

    st.title("Phyto-Asistan Sizinle")
    st.markdown(f"**Dosyanız İncelendi.** Size nasıl yardımcı olabilirim?")

    # Eski mesajları ekrana bas
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Otomatik İlk Karşılama (Sadece bir kere)
    if len(st.session_state.messages) == 0:
        first_prompt = "Merhaba, ben geldim. Triyaj formumu doldurdum, şikayetlerimi ve ilaçlarımı inceledin mi? Bana ne önerirsin?"
        with st.chat_message("user"):
            st.markdown("*(Triyaj formu sisteme iletildi)*")
        st.session_state.messages.append({"role": "user", "content": first_prompt})
        
        with st.spinner("Dosyanız Phyto-Asistan tarafından analiz ediliyor..."):
            initial_response = get_patient_response(first_prompt, full_rag_content, st.session_state.patient_data, [])
        
        with st.chat_message("assistant", avatar="🌿"):
            st.markdown(initial_response)
        st.session_state.messages.append({"role": "assistant", "content": initial_response})
        st.rerun()

    # Kullanıcıdan Yeni Mesaj Alma
    prompt = st.chat_input("Hekime danışacağınız başka bir konu var mı?")

    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.spinner("Phyto-Asistan geçmişinizi değerlendiriyor..."):
            patient_response = get_patient_response(prompt, full_rag_content, st.session_state.patient_data, st.session_state.messages)

        with st.chat_message("assistant", avatar="🌿"):
            st.markdown(patient_response)
            
            # Doktor Mektubu
            if len(prompt.split()) > 2 and "112" not in patient_response:
                with st.spinner("Hekim için konsültasyon notu hazırlanıyor..."):
                    doctor_letter = get_doctor_letter(prompt, full_rag_content, st.session_state.patient_data, st.session_state.messages)
                
                with st.expander("🩺 Hekiminiz İçin Tıbbi Konsültasyon Notu (PMID Referanslı)"):
                    st.info("Bu bölüm hekiminize göstermeniz için akademik dille hazırlanmıştır.")
                    st.write(doctor_letter)

        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({"role": "assistant", "content": patient_response})
