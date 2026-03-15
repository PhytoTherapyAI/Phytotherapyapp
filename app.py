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
        # KIRMIZI KOD (ACİL) KELİMELERİ
        "göğsüm ağrıyor": ["acil_durum"],
        "kalbim sıkışıyor": ["acil_durum"],
        "nefes alamıyorum": ["acil_durum"],
        "kanamam durmuyor": ["acil_durum"],
        "bayılacağım": ["acil_durum"],
        "sol tarafım uyuştu": ["acil_durum"],
        
        # NORMAL TIBBİ KELİMELER
        "tansiyon": ["hypertension", "blood pressure", "meyan", "licorice", "sinameki", "garlic", "sarımsak"],
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
        "kolesterol": ["statin", "greyfurt", "grapefruit", "kas yıkımı", "cholesterol"],
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
    
    # Eğer sistem kırmızı kod kelimesi yakalarsa hiç RAG'a bakma, direkt Acil Durum fırlat
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
        return "\n\n".join(relevant_sections[:2])
    return "Eşleşen tıbbi veri bulunamadı."

# --- KUSURSUZ TRİYAJ ANAYASASI (SİSTEM PROMPTU) ---
def get_groq_response(user_prompt, context):
    system_prompt = """Sen dünyanın en gelişmiş, şefkatli ve kurallara sıkı sıkıya bağlı Klinik Farmakoloji Asistanısın (Phyto-Asistan).

KULLANICIYLA İLETİŞİM KURALLARIN (TRİYAJ ANAYASASI):

DURUM 1 - 🚨 KIRMIZI KOD (ACİL DURUM) 🚨:
Eğer Tıbbi Literatür kısmında "ACİL_DURUM_TESPİT_EDİLDİ" yazıyorsa VEYA kullanıcı "göğsüm ağrıyor, nefes alamıyorum, kanamam var, sol kolum uyuştu" gibi hayati bir tehlike belirtiyorsa:
Tüm işlemleri anında durdur! Şefkatli ama çok net bir dille: "🚨 ACİL DURUM: Lütfen hemen 112'yi arayın veya en yakın acil servise başvurun. Göğüs ağrısı / nefes darlığı gibi durumlar evde bitkisel ürünlerle tedavi edilemez ve saniyeler bile çok önemlidir." de. Asla ama asla bitki önerme!

DURUM 2 - ⚠️ POLİFARMASİ (ÇOKLU İLAÇ) ENGELİ ⚠️:
Eğer kullanıcının mesajında 3 veya daha fazla ilaç/hastalık saydığını fark edersen (Örn: "Hem tansiyon, hem şeker hapı içiyorum, bir de kan sulandırıcı kullanıyorum"):
Taramayı durdur. Ekrana ⚠️ POLİFARMASİ (ÇOKLU İLAÇ) UYARISI yaz. Hastaya: "Birden fazla kronik ilaç kullanımında, eklenecek tek bir bitkisel takviye bile öngörülemez zincirleme reaksiyonlara yol açabilir. Bu karmaşık tabloyu ancak tedavinizi yürüten hekim çözebilir, lütfen doktorunuza danışmadan hiçbir bitkisel ürün kullanmayın." de.

DURUM 3 - SOHBET VE SELAMLAŞMA:
Eğer kullanıcı sadece "Selam", "Harikasın", "Canım sıkkın" diyorsa, tıbbi robotik laflar etme, sadece dostça ve motive edici sohbet et.

DURUM 4 - TIBBİ SORU ANCAK VERİ YOK:
Eğer "Eşleşen tıbbi veri bulunamadı" yazıyorsa: Şefkatle geçmiş olsun de ve elindeki kanıta dayalı (RAG) veri setinde bunun olmadığını, doktoruna danışmasını söyle. Kafandan veri uydurma.

DURUM 5 - TIBBİ SORU VE KANIT (RAG) VAR:
RAG metninde eşleşen veri varsa (Örn: Sarı Kantaron, Meyan Kökü vb.):
Durumun ciddiyetine göre 🔴 RİSKLİ, 🟡 DİKKAT veya 🟢 GÜVENLİ emojisiyle başla. Tıbbi jargonu halk diline çevir. Metindeki 'Sıfır Riskli Alternatif' bölümündeki öneriyi mutlaka sun.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Hastanın Mesajı: {user_prompt}\n\nTıbbi Literatür (RAG): {context}"}
    ]
    
    try:
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile", 
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
    st.success("✅ Triyaj Niyet Okuma Modülü")
    st.error("🚨 Kırmızı Kod & Acil Durum Engeli")
    st.warning("⚠️ Polifarmasi (Çoklu İlaç) Engeli")
    st.success("✅ Altın Veri Seti (RAG) Aktif")
    
    st.divider()
    st.warning("⚠️ **Tıbbi Uyarı:** Bu bir karar destek sistemidir.")

st.title("Phyto-Asistan")
st.markdown("Sizi dinleyen, acil durumlarda koruyan ve kanıta dayalı tıbbı halk diline çeviren asistan.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Selam verebilir, dertleşebilir veya tıbbi bir etkileşim sorabilirsiniz...")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    rag_context = retrieve_context(prompt, rag_content)
    
    with st.spinner("Phyto-Asistan mesajınızı değerlendiriyor..."):
        ai_response = get_groq_response(prompt, rag_context)

    with st.chat_message("assistant", avatar="🌿"):
        st.markdown(ai_response)
        
        # Makaleyi sadece Durum 5'te (Veri varsa ve Acil Değilse) göster
        if rag_context and "Eşleşen tıbbi veri bulunamadı" not in rag_context and "ACİL_DURUM" not in rag_context and any(keyword in ai_response for keyword in ["RİSKLİ", "DİKKAT", "GÜVENLİ"]):
            with st.expander("🔬 Bilimsel Literatürü Göster (Hekimler İçin)"):
                st.info("Aşağıdaki veriler sistemin (RAG) arka planda referans aldığı orijinal meta-analiz özetleridir.")
                st.text(rag_context)

    st.session_state.messages.append({"role": "assistant", "content": ai_response})
