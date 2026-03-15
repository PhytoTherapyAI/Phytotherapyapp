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
@st.cache_data
def load_rag_data(file_path):
    if not os.path.exists(file_path):
        return ""
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip() != ""])

rag_content = load_rag_data("RAG.docx")

# --- GENİŞLETİLMİŞ HALK DİLİ SÖZLÜĞÜ (HİSLER VE SEMPTOMLAR) ---
def map_keywords(user_input):
    input_lower = user_input.lower()
    # Hastanın söyleyebileceği en uçuk kelimeleri bile tıbbi literatüre bağlarız
    mapping = {
        # Kalp ve Tansiyon Grubu
        "tansiyon": ["hypertension", "blood pressure", "meyan", "licorice", "sinameki", "garlic", "sarımsak"],
        "baş dönmesi": ["tansiyon", "hypertension", "blood pressure"],
        "çarpıntı": ["kalp", "digoxin", "cardiovascular", "hypertension", "potasyum", "hypokalemia"],
        "göğsüm sıkışıyor": ["kalp", "digoxin", "cardiovascular", "hypertension", "anxiety"],
        
        # Şeker Grubu
        "şeker": ["diabetes", "kan şekeri", "ginseng", "hypoglycemic", "glucose"],
        "ağzım kuruyor": ["diabetes", "kan şekeri", "ginseng"],
        "çok su içiyorum": ["diabetes", "kan şekeri", "ginseng"],
        "tatlı krizi": ["diabetes", "kan şekeri", "ginseng"],
        
        # Kan Sulandırıcı Grubu
        "kan sulandırıcı": ["warfarin", "anticoagulant", "kanama", "bleeding", "ginkgo", "sarımsak", "garlic"],
        "morarma": ["warfarin", "anticoagulant", "kanama", "bleeding"],
        "kanım cıvık": ["warfarin", "anticoagulant", "kanama", "bleeding"],
        "pıhtı": ["warfarin", "anticoagulant", "kanama", "bleeding"],
        
        # Hormon ve Doğum Kontrol Grubu
        "doğum kontrol": ["contraceptive", "sarı kantaron", "st. john", "cyp3a4", "estradiol"],
        "korunma": ["contraceptive", "sarı kantaron", "st. john"],
        "adet düzensizliği": ["contraceptive", "sarı kantaron", "st. john"],
        
        # Psikoloji, Depresyon, Uyku ve Stres Grubu (En Çok Genişletilen)
        "uyku": ["valerian", "kedi otu", "sedative", "sinir", "anxiety", "insomnia"],
        "uyuyamıyorum": ["valerian", "kedi otu", "sedative", "sinir", "anxiety", "insomnia"],
        "stres": ["anxiety", "valerian", "kedi otu", "sarı kantaron", "depression"],
        "sıkıntı": ["anxiety", "valerian", "kedi otu", "sarı kantaron", "depression"],
        "bunalım": ["depression", "sarı kantaron", "st. john"],
        "depresyon": ["depression", "sarı kantaron", "st. john"],
        "ağlamak istiyorum": ["depression", "sarı kantaron", "st. john", "anxiety"],
        "canım hiçbir şey istemiyor": ["depression", "sarı kantaron", "st. john"],
        "enerjim yok": ["depression", "sarı kantaron", "st. john", "ginseng"],
        "mutsuzum": ["depression", "sarı kantaron", "st. john"],
        "kafama takıyorum": ["anxiety", "valerian", "kedi otu", "sarı kantaron"],
        "panik": ["anxiety", "valerian", "kedi otu"],
        "korku": ["anxiety", "valerian", "kedi otu"],
        "sinirliyim": ["anxiety", "valerian", "kedi otu"],
        
        # Ağrı Grubu
        "ağrı": ["analgesic", "pain", "valerian", "kedi otu"],
        "her yerim ağrıyor": ["analgesic", "pain", "valerian", "kedi otu"],
        "migren": ["analgesic", "pain", "valerian", "kedi otu"],
        
        # Diğer Sistemler
        "kolesterol": ["statin", "greyfurt", "grapefruit", "kas yıkımı", "cholesterol"],
        "damar tıkanıklığı": ["statin", "greyfurt", "grapefruit", "cholesterol"],
        "bağışıklık": ["ekinezya", "echinacea", "immün", "organ nakli", "immunosuppressive"],
        "çok hastalanıyorum": ["ekinezya", "echinacea", "immün"],
        "kabızlık": ["sinameki", "senna", "laksatif", "potasyum", "hypokalemia"],
        "tuvalete çıkamıyorum": ["sinameki", "senna", "laksatif", "potasyum", "hypokalemia"]
    }
    
    search_terms = []
    for key, values in mapping.items():
        if key in input_lower:
            search_terms.extend(values)
    
    # Kullanıcının yazdığı orijinal kelimeleri de ekle
    search_terms.extend(input_lower.split())
    return list(set(search_terms))

# --- RAG ARAMA MANTIĞI ---
def retrieve_context(user_input, content):
    if not content:
        return "Veri seti bulunamadı."
    
    search_terms = map_keywords(user_input)
    sections = content.split("### BÖLÜM")
    relevant_sections = []
    
    for section in sections:
        section_lower = section.lower()
        if any(term in section_lower for term in search_terms if len(term) > 3):
            relevant_sections.append(section)
            
    if relevant_sections:
        return "\n\n".join(relevant_sections[:2])
    return "Eşleşen tıbbi veri bulunamadı."

# --- EMPATİ YÜKLÜ YAPAY ZEKA MANTIĞI ---
def get_groq_response(user_prompt, context):
    system_prompt = """Sen uzman, inanılmaz şefkatli, hastayı motive eden ve çok anlaşılır konuşan bir Klinik Farmakoloji Asistanısın (Phyto-Asistan). 
Görevlerin:
1. İLK ADIM (EMPATİ): Hastanın sorusunu/şikayetini duyduğunda cevaba direkt tıbbi bilgiyle başlama! Önce ona şefkatle yaklaş, "Geçmiş olsun, yalnız değilsiniz, bu hissettiğiniz durumlar çözülebilir, sağlığınız bizim için çok değerli" gibi onu rahatlatacak, moral verecek ve içini ısıtacak 1-2 cümlelik sıcak bir giriş yap.
2. EŞLEŞEN VERİ YOKSA: Eğer 'Tıbbi Literatür (RAG)' kısmında "Eşleşen tıbbi veri bulunamadı" yazıyorsa, hastaya samimi bir dille şunu söyle: "Şu anki uzmanlık veri setimde bu şikayetinize dair bir bitki-ilaç etkileşimi bulunmuyor. Ancak sağlığınız riske atılamayacak kadar kıymetli, lütfen bu durumu en kısa sürede hekiminizle paylaşın." Sakın kendi kafandan tedavi uydurma.
3. EŞLEŞEN VERİ VARSA: Literatüre (RAG verisine) dayanarak cevap ver. Asla literatür dışına çıkma.
4. UYARI EMOJİLERİ: Tıbbi açıklamaya geçerken durumun ciddiyetine göre şu emojilerden birini koy:
   🔴 RİSKLİ: Kesinlikle uzak durulmalı / ciddi etkileşim var.
   🟡 DİKKAT: Doktora danışılmalı / çelişkili veya orta düzey risk.
   🟢 GÜVENLİ: Etkileşim bulunamadı veya güvenli alternatif.
5. Tıbbi jargonu teyzelerin bile anlayacağı basit, şefkatli halk diline çevir.
6. SIFIR RİSKLİ ALTERNATİF: Veri varsa mutlaka RAG metninin sonundaki 'Sıfır Riskli Alternatif' bölümündeki öneriyi hastaya sunarak "Sizin için daha güvenli bir yol var" mesajı ver.
7. Asla makalenin İngilizce metnini kopyalama! Türkçe, samimi ve motive edici bir sohbet dilinde özet ver."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Hastanın Sorusu: {user_prompt}\n\nTıbbi Literatür (RAG): {context}"}
    ]
    
    try:
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile", 
            temperature=0.4, # AI'ın biraz daha yaratıcı ve şefkatli kelimeler seçmesi için artırdık
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
    st.success("✅ Groq Llama-3.3 Devrede")
    st.success("✅ Altın Veri Seti (RAG) Aktif")
    st.success("💖 Empati Modülü Aktif")
    
    st.divider()
    st.warning("⚠️ **Tıbbi Uyarı:** Bu bir karar destek sistemidir. Doktorunuza danışmadan tedavi değişikliği yapmayınız.")

# --- ANA EKRAN SOHBET ARAYÜZÜ ---
st.title("Phyto-Asistan")
st.markdown("Size şefkatle yaklaşan, halk dilini anlayan ilk fitoterapi asistanı.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Örn: Canım hiçbir şey yapmak istemiyor, içim daralıyor. Ne içebilirim?")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    rag_context = retrieve_context(prompt, rag_content)
    
    with st.spinner("Şikayetiniz dinleniyor ve tıbbi literatür taranıyor..."):
        ai_response = get_groq_response(prompt, rag_context)

    with st.chat_message("assistant", avatar="🌿"):
        st.markdown(ai_response)
        
        if rag_context and "Eşleşen tıbbi veri bulunamadı" not in rag_context:
            with st.expander("🔬 Bilimsel Literatürü Göster (Hekimler İçin)"):
                st.info("Aşağıdaki veriler sistemin (RAG) arka planda referans aldığı orijinal meta-analiz özetleridir.")
                st.text(rag_context)

    st.session_state.messages.append({"role": "assistant", "content": ai_response})
