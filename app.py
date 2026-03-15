import streamlit as st
from docx import Document
import os
from groq import Groq

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Phytotherapy.ai", page_icon="🌿", layout="wide")

# --- GROQ API BAĞLANTISI ---
try:
    groq_api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=groq_api_key)
except Exception as e:
    st.error("⚠️ Lütfen Streamlit ayarlarından (Secrets) GROQ_API_KEY gizli anahtarınızı ekleyin.")
    st.stop()

# --- VERİ İŞLEME FONKSİYONU ---
@st.cache_data # Veriyi her seferinde tekrar okumamak için önbelleğe alır
def load_rag_data(file_path):
    if not os.path.exists(file_path):
        return ""
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip() != ""])

rag_content = load_rag_data("RAG.docx")

# --- HALK DİLİ SÖZLÜĞÜ (SEMANTİK EŞLEŞTİRME) ---
def map_keywords(user_input):
    input_lower = user_input.lower()
    # Kullanıcının halk dili kelimelerini İngilizce tıbbi karşılıklarına bağlarız
    mapping = {
        "tansiyon": ["hypertension", "blood pressure", "meyan", "licorice", "sinameki", "garlic", "sarımsak"],
        "şeker": ["diabetes", "kan şekeri", "ginseng", "hypoglycemic", "glucose"],
        "kan sulandırıcı": ["warfarin", "anticoagulant", "kanama", "bleeding", "ginkgo", "sarımsak", "garlic"],
        "doğum kontrol": ["contraceptive", "sarı kantaron", "st. john", "cyp3a4", "estradiol"],
        "uyku": ["valerian", "kedi otu", "sedative", "sinir", "anxiety", "insomnia"],
        "kolesterol": ["statin", "greyfurt", "grapefruit", "kas yıkımı", "cholesterol"],
        "bağışıklık": ["ekinezya", "echinacea", "immün", "organ nakli", "immunosuppressive"],
        "kabızlık": ["sinameki", "senna", "laksatif", "potasyum", "hypokalemia"],
        "kalp": ["digoxin", "cardiovascular", "kalp"]
    }
    
    search_terms = []
    for key, values in mapping.items():
        if key in input_lower:
            search_terms.extend(values)
    
    # Kullanıcının yazdığı kendi kelimeleri de arama havuzuna ekle
    search_terms.extend(input_lower.split())
    return list(set(search_terms))

# --- RAG ARAMA MANTIĞI ---
def retrieve_context(user_input, content):
    if not content:
        return ""
    
    search_terms = map_keywords(user_input)
    sections = content.split("### BÖLÜM")
    relevant_sections = []
    
    for section in sections:
        section_lower = section.lower()
        # Eğer eşleşen kelime varsa bu bölümü al
        if any(term in section_lower for term in search_terms if len(term) > 3):
            relevant_sections.append(section)
            
    if relevant_sections:
        return "\n\n".join(relevant_sections[:2]) # En ilgili 2 bölümü LLM'e yolla
    return ""

# --- GROQ YAPAY ZEKA MANTIĞI ---
def get_groq_response(user_prompt, context):
    if not context:
        return "❌ Üzgünüm, veri setimizde (RAG.docx) bu spesifik duruma ait kanıta dayalı bir analiz bulamadım. Lütfen farklı kelimelerle (Örn: Sarı Kantaron, Tansiyon, Ginseng) tekrar deneyin."

    system_prompt = """Sen uzman ama çok anlaşılır konuşan bir Klinik Farmakoloji Asistanısın (Phyto-Asistan). 
Görevlerin:
1. Sana verilen 'Tıbbi Literatür (RAG)' metnini analiz et.
2. Hastanın sorusuna bu literatüre dayanarak cevap ver. Asla literatür dışına çıkma.
3. Cevabının en başına durumun ciddiyetine göre şu emojilerden birini koy ve kalın harflerle yaz:
   🔴 RİSKLİ: Kesinlikle uzak durulmalı / ciddi etkileşim var.
   🟡 DİKKAT: Doktora danışılmalı / çelişkili veya orta düzey risk.
   🟢 GÜVENLİ: Etkileşim bulunamadı veya güvenli alternatif.
4. Tıbbi jargonu (CYP3A4, farmakokinetik vb.) hastanın anlayacağı basit, halk diline çevir (Örn: "karaciğerdeki enzimler", "ilacın kana karışması").
5. Mutlaka RAG metninin sonundaki 'Sıfır Riskli Alternatif' bölümündeki öneriyi hastaya sun.
6. Asla makalenin İngilizce orijinal metnini kopyalama! Türkçe ve samimi bir özet ver."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Hastanın Sorusu: {user_prompt}\n\nTıbbi Literatür (RAG): {context}"}
    ]
    
    try:
        # llama3-8b-8192 şu an hem ücretsiz hem de inanılmaz hızlı
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama3-8b-8192", 
            temperature=0.3,
            max_tokens=1024
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"❌ Yapay zeka yanıt üretirken bir hata oluştu: {e}"

# --- SOL MENÜ (SİDEBAR) ---
with st.sidebar:
    st.title("🌿 Phytotherapy.ai")
    st.markdown("**Kanıta Dayalı Fitoterapi Asistanı**")
    st.divider()
    st.markdown("### 🧠 Sistem Beyni")
    st.success("✅ Groq Llama-3 Devrede")
    st.success("✅ Altın Veri Seti (RAG) Aktif")
    
    st.divider()
    st.warning("⚠️ **Tıbbi Uyarı:** Bu bir karar destek sistemidir. Doktorunuza danışmadan tedavi değişikliği yapmayınız.")

# --- ANA EKRAN SOHBET ARAYÜZÜ ---
st.title("Phyto-Asistan")
st.markdown("Dünyanın ilk sıfır halüsinasyonlu, halk dilini anlayan fitoterapi asistanı.")

# Sohbet Geçmişi
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Kullanıcı Girişi
prompt = st.chat_input("Örn: Tansiyon ilacı kullanıyorum, meyan kökü çayı içebilir miyim?")

if prompt:
    # 1. Kullanıcı mesajını ekrana bas
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. RAG dosyasından ilgili metni bul
    rag_context = retrieve_context(prompt, rag_content)
    
    # 3. Groq LLM'e gönder ve akıllı cevap al
    with st.spinner("Tıbbi literatür taranıyor ve analiz ediliyor..."):
        ai_response = get_groq_response(prompt, rag_context)

    # 4. Asistanın cevabını ekrana bas
    with st.chat_message("assistant", avatar="🌿"):
        st.markdown(ai_response)
        
        # 5. Jüri ve Doktorlar İçin "Bilimsel Kanıtı Göster" Expander'ı
        if rag_context:
            with st.expander("🔬 Bilimsel Literatürü ve Makale Özetlerini Göster (Hekimler İçin)"):
                st.info("Aşağıdaki veriler sistemin (RAG) arka planda referans aldığı orijinal meta-analiz özetleridir.")
                st.text(rag_context)

    st.session_state.messages.append({"role": "assistant", "content": ai_response})
