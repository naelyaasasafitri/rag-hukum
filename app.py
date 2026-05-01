"""
app.py — Interface chat Streamlit untuk Asisten Hukum Indonesia
Jalankan dengan: streamlit run app.py
"""

import streamlit as st
from query_engine import tanya

# ══════════════════════════════════════════════════════════════════════════
# KONFIGURASI HALAMAN
# ══════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Asisten Hukum Indonesia",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════
# CUSTOM CSS
# ══════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
    /* Font & warna utama */
    @import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;600&family=DM+Sans:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    h1, h2, h3 {
        font-family: 'Lora', serif !important;
    }

    /* Header utama */
    .header-box {
        background: linear-gradient(135deg, #1a2744 0%, #2d4a8a 100%);
        padding: 2rem 2.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }

    .header-box h1 {
        font-size: 1.8rem;
        margin: 0 0 0.3rem 0;
        color: white !important;
    }

    .header-box p {
        margin: 0;
        opacity: 0.75;
        font-size: 0.9rem;
    }

    /* Chat bubble user */
    .chat-user {
        background: #eef2ff;
        border-left: 4px solid #3b5bdb;
        padding: 0.9rem 1.2rem;
        border-radius: 0 10px 10px 0;
        margin: 0.8rem 0;
    }

    /* Chat bubble assistant */
    .chat-assistant {
        background: #f8f9fa;
        border-left: 4px solid #2b8a3e;
        padding: 0.9rem 1.2rem;
        border-radius: 0 10px 10px 0;
        margin: 0.8rem 0;
    }

    /* Badge sumber */
    .badge-sumber {
        display: inline-block;
        background: #e8f4fd;
        color: #1971c2;
        font-size: 0.72rem;
        padding: 2px 8px;
        border-radius: 20px;
        margin: 2px;
        border: 1px solid #a5d8ff;
    }

    /* Badge tabel */
    .badge-tabel {
        background: #fff3bf;
        color: #e67700;
        border-color: #ffd43b;
    }

    /* Sidebar */
    .sidebar-info {
        background: #f1f3f5;
        padding: 1rem;
        border-radius: 8px;
        font-size: 0.85rem;
        color: #495057;
    }

    /* Disclaimer */
    .disclaimer {
        background: #fff9db;
        border: 1px solid #ffd43b;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        font-size: 0.8rem;
        color: #664d03;
        margin-top: 1rem;
    }

    /* Tombol clear */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-family: 'DM Sans', sans-serif;
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════

if "messages" not in st.session_state:
    st.session_state.messages = []

if "total_pertanyaan" not in st.session_state:
    st.session_state.total_pertanyaan = 0


# ══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### ⚖️ Asisten Hukum")
    st.markdown("---")

    st.markdown("""
    <div class="sidebar-info">
    <b>Cara Penggunaan:</b><br><br>
    1. Ketik pertanyaan hukummu di kolom chat<br>
    2. AI akan mencari jawaban dari dokumen hukum yang tersedia<br>
    3. Sumber referensi ditampilkan di bawah setiap jawaban
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Statistik sesi
    st.markdown(f"**📊 Sesi ini:**")
    st.metric("Pertanyaan diajukan", st.session_state.total_pertanyaan)

    st.markdown("---")

    # Contoh pertanyaan
    st.markdown("**💡 Contoh Pertanyaan:**")
    contoh = [
        "Apa sanksi pidana bagi pelanggar Pasal 5?",
        "Siapa yang dimaksud dengan pihak ketiga?",
        "Bagaimana prosedur pengajuan gugatan?",
        "Apa syarat sah perjanjian menurut hukum?",
    ]
    for c in contoh:
        if st.button(c, key=f"contoh_{c}"):
            st.session_state._input_dari_contoh = c

    st.markdown("---")

    # Tombol clear chat
    if st.button("🗑️ Hapus Riwayat Chat", type="secondary"):
        st.session_state.messages = []
        st.session_state.total_pertanyaan = 0
        st.rerun()

    st.markdown("""
    <div class="disclaimer">
    ⚠️ <b>Disclaimer:</b> Jawaban AI bersifat informatif dan bukan merupakan
    nasihat hukum resmi. Konsultasikan dengan advokat untuk keputusan hukum.
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# HEADER UTAMA
# ══════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="header-box">
    <h1>⚖️ Asisten Hukum Indonesia</h1>
    <p>Tanyakan apapun tentang dokumen hukum yang tersedia. Jawaban selalu disertai referensi pasal.</p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# TAMPILKAN RIWAYAT CHAT
# ══════════════════════════════════════════════════════════════════════════

def render_sumber(sumber_list: list):
    """Tampilkan badge sumber referensi"""
    if not sumber_list:
        return

    with st.expander(f"📚 Lihat {len(sumber_list)} referensi dokumen", expanded=False):
        for i, s in enumerate(sumber_list, 1):
            is_tabel = s.get("tipe_konten") == "tabel"
            badge_class = "badge-tabel" if is_tabel else "badge-sumber"
            ikon = "📊" if is_tabel else "📄"

            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(
                    f'<span class="{badge_class}">{ikon} {s["dokumen"]}</span> '
                    f'<span class="badge-sumber">Hal. {s["halaman"]}</span>',
                    unsafe_allow_html=True
                )
                if s.get("cuplikan"):
                    st.caption(f'*"{s["cuplikan"]}"*')
            with col2:
                if s.get("skor"):
                    st.caption(f"Relevansi: {int(s['skor']*100)}%")

            if i < len(sumber_list):
                st.markdown("---")


# Tampilkan pesan yang sudah ada
for pesan in st.session_state.messages:
    if pesan["role"] == "user":
        with st.chat_message("user"):
            st.markdown(pesan["content"])
    else:
        with st.chat_message("assistant"):
            st.markdown(pesan["content"])
            if pesan.get("sumber"):
                render_sumber(pesan["sumber"])


# ══════════════════════════════════════════════════════════════════════════
# PESAN SAMBUTAN (jika chat kosong)
# ══════════════════════════════════════════════════════════════════════════

if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown("""
        Halo! Saya adalah Asisten Hukum Indonesia. 👋

        Saya siap membantu menjawab pertanyaan berdasarkan dokumen hukum
        yang tersedia dalam sistem ini.

        **Yang bisa saya bantu:**
        - Mencari isi pasal atau ayat tertentu
        - Menjelaskan definisi istilah hukum dalam dokumen
        - Menemukan sanksi atau ketentuan yang berlaku
        - Membandingkan isi antar pasal

        Silakan ajukan pertanyaan Anda! ⚖️
        """)


# ══════════════════════════════════════════════════════════════════════════
# INPUT CHAT
# ══════════════════════════════════════════════════════════════════════════

# Cek apakah ada input dari tombol contoh pertanyaan
input_awal = st.session_state.pop("_input_dari_contoh", None)

pertanyaan = st.chat_input(
    "Tanyakan sesuatu tentang hukum...",
    key="chat_input"
) or input_awal

if pertanyaan:
    # Tampilkan pertanyaan user
    with st.chat_message("user"):
        st.markdown(pertanyaan)

    st.session_state.messages.append({
        "role"   : "user",
        "content": pertanyaan,
    })

    st.session_state.total_pertanyaan += 1

    # Proses jawaban
    with st.chat_message("assistant"):
        with st.spinner("🔍 Mencari di dokumen hukum..."):
            hasil = tanya(pertanyaan)

        if hasil["berhasil"]:
            st.markdown(hasil["jawaban"])
            render_sumber(hasil["sumber"])

            st.session_state.messages.append({
                "role"   : "assistant",
                "content": hasil["jawaban"],
                "sumber" : hasil["sumber"],
            })

        else:
            pesan_error = f"⚠️ Terjadi kesalahan: `{hasil['error']}`\n\nCoba ajukan pertanyaan kembali."
            st.error(pesan_error)

            st.session_state.messages.append({
                "role"   : "assistant",
                "content": pesan_error,
                "sumber" : [],
            })
