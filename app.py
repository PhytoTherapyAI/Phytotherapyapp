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
        return ""
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip() != ""])

rag_content = load_rag_data("RAG.docx")

# --- KELİME SÖZLÜĞÜ (Acil Durumlar Eklendi) ---
def map_keywords(user_input):
    input_lower = user_input.lower()
    mapping = {
        "göğsüm ağrıyor": ["acil_durum"],
        "kalbim sıkışıyor": ["acil_durum"],
        "nefes alamıyorum": ["acil_durum"],
        "kanamam durmuyor": ["acil_durum"],
        "tansiyon": ["hypertension", "blood pressure", "meyan", "licorice", "sinameki", "garlic", "sarımsak"],
        "kramp": ["statin", "greyfurt", "grapefruit", "kas yıkımı", "myopathy"],
        "baş dönmesi": ["tansiyon", "hypertension", "blood pressure"],
        "çarpıntı": ["kalp", "digoxin", "cardiovascular", "hypertension", "potasyum", "hypokalemia"],
        "şeker": ["diabetes", "kan şekeri", "ginseng", "hypoglycemic", "glucose"],
        "kan sulandırıcı": ["warfarin", "anticoagulant", "kanama", "bleeding", "ginkgo", "sarımsak", "garlic"],
        "doğum kontrol": ["contraceptive", "sarı kantaron", "st. john", "cyp3a4", "estradiol"],
        "uyku": ["valerian", "kedi otu", "sedative", "sinir", "anxiety", "insomnia"],
        "stres": ["anxiety", "valerian", "kedi otu", "sarı kantaron", "depression"],
        "sıkıntı": ["anxiety", "valerian", "kedi otu", "sarı kantaron", "depression"],
        "depresyon": ["depression", "sarı kantaron", "st. john"],
        "ağrı": ["analgesic", "pain", "valerian", "kedi otu"],
        "kolesterol": ["statin", "greyfurt", "grapefruit", "kas yıkımı", "cholesterol", "myopathy"],
        "bağışıklık": ["ekinezya", "echinacea", "immün", "organ nakli", "immunosuppressive"],
        "kabızlık": ["sinameki", "senna", "laksatif", "potasyum", "hypokalemia"]
    }
    
    search_terms = []
    for key, values in mapping.items():
        if key in input_lower:
            search_terms.extend(values)
    search_terms.extend(input_lower.split())
    return list(set(search_terms))

def retrieve_context(user_input, content):
    search_terms = map_keywords(user_input)
    
    if "acil_durum" in search_terms:
        return "ACİL_DURUM_TESPİT_EDİLDİ"
        
    if not content:
        return "Veri seti bulunamadı."
        
    sections = content.split("### BÖLÜM")
    relevant_sections = []
    for section in sections:
        section_lower = section.lower()
        if any(term in section_lower for term in search_terms if len(term) > 3):
            relevant_sections.append(section)
            
    if relevant_sections:
        return "\n\n".join(relevant_sections[:3]) # Kapsamı biraz genişlettik
    return "Eşleşen tıbbi veri bulunamadı."

# --- BEYİN 1: HASTA İÇİN ŞEFKATLİ ASİSTAN ---
def get_patient_response(user_prompt, context):
    system_prompt = """Sen dünyanın en gelişmiş, şefkatli Klinik Farmakoloji Asistanısın.

GÖREVLERİN:
1. İLAÇ YAN ETKİSİ KONTROLÜ: Hastanın anlattığı şikayet (örn: kas krampları), kullandığı ilacın (örn: statin, diüretik) iyi bilinen bir yan etkisi olabilir mi? Eğer öyleyse hastaya şefkatle şunu söyle: "Şikayetleriniz, kullandığınız [İlaç Adı] ilacının bilinen bir yan etkisi olabilir. Doz ayarlaması veya ilaç değişimi için lütfen hekiminizle görüşün."
2. ACİL DURUM KONTROLÜ: 'ACİL_DURUM_TESPİT_EDİLDİ' yazıyorsa derhal 112'ye yönlendir.
3. ÇOKLU İLAÇ (POLİFARMASİ): Hasta 3 veya daha fazla kronik ilaç kullanıyorsa (Örn: Diüretik + Statin + Metformin), bitkisel takviyelerin bu kadar çok ilaçla tehlikeli zincirleme reaksiyonlar yapabileceğini belirt ve doktora danışmadan ot içmemesini söyle.
4. RAG VERİSİ (Bitki): Eşleşen veri varsa (Örn: Statin ve Greyfurt etkileşimi), 🔴 RİSKLİ, 🟡 DİKKAT veya 🟢 GÜVENLİ emojisiyle uyarı yap. Tıbbi dili halk diline çevir.
5. SIFIR RİSK: Her zaman RAG metnindeki sıfır riskli alternatifi öner.
Asla kafandan tıbbi teşhis koyma, sadece rehberlik et."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Hastanın Mesajı: {user_prompt}\n\nTıbbi Literatür (RAG): {context}"}
    ]
    
    try:
        chat_completion = client.chat.completions.create(
            messages=messages, model="llama-3.3-70b-versatile", temperature=0.3, max_tokens=1024
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"❌ Yanıt hatası: {e}"

# --- BEYİN 2: DOKTOR İÇİN KONSÜLTASYON MEKTUBU ---
def get_doctor_letter(user_prompt, context):
    system_prompt = """Sen uzman bir klinik farmakologsun. Hastanın kullandığı ilaçlar, şikayetleri ve RAG veritabanından çekilen makalelere dayanarak, hastanın tedavisini yürüten hekime yönelik kısa, akademik ve doğrudan bir 'Konsültasyon Bilgi Notu' yaz.

KURALLAR:
1. Sayın Meslektaşım, şeklinde başla.
2. Hastanın olası ilaç yan etkisini (Örn: Statin kaynaklı miyopati) veya polifarmasi riskini tıbbi bir dille özetle.
3. Eğer RAG verisinde hastanın durumuyla ilgili bitki/ilaç etkileşimi varsa (CYP enzimleri, farmakokinetik mekanizmalar vb. kullanarak) bilimsel olarak açıkla.
4. MUTLAKA RAG metnindeki makalelerin "PMID" numaralarını referans göstererek yaz (Örn: "PMID: 26299317 referanslı çalışmaya göre...").
5. RAG verisi yoksa veya eşleşmiyorsa, mektubu sadece hastanın şikayetleri ve ilaç yan etkileri üzerine kur.
Mektup kısa, net ve saygılı bir tonda olmalı."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Hastanın Beyanı: {user_prompt}\n\nRAG Verisi (Buradaki PMID'leri kullan): {context}"}
    ]
    
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
    st.success("✅ Triyaj & Yan Etki Radarı")
    st.success("✅ Çift LLM (Hasta & Hekim Mektubu)")
    st.success("✅ Altın Veri Seti (RAG) Aktif")
    st.divider()
    st.warning("⚠️ **Tıbbi Uyarı:** Karar destek sistemidir.")

st.title("Phyto-Asistan")
st.markdown("Sizi dinleyen, yan etkileri tespit eden ve doktorunuza tıbbi rapor hazırlayan asistan.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Selam verebilir, şikayetinizi ve ilaçlarınızı yazabilirsiniz...")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    rag_context = retrieve_context(prompt, rag_content)
    
    with st.spinner("Phyto-Asistan mesajınızı değerlendiriyor..."):
        # Hasta için cevabı al
        patient_response = get_patient_response(prompt, rag_context)

    with st.chat_message("assistant", avatar="🌿"):
        st.markdown(patient_response)
        
        # Doktor için mektubu al ve genişletici panele koy (Eğer sohbet değilse)
        if len(prompt.split()) > 2 and "ACİL_DURUM" not in rag_context:
            with st.spinner("Hekim için konsültasyon notu hazırlanıyor..."):
                doctor_letter = get_doctor_letter(prompt, rag_context)
            
            with st.expander("🩺 Hekiminiz İçin Tıbbi Konsültasyon Notu (PMID Referanslı)"):
                st.info("Bu bölüm hekiminize göstermeniz için akademik dille hazırlanmıştır.")
                st.write(doctor_letter)

    st.session_state.messages.append({"role": "assistant", "content": patient_response})
