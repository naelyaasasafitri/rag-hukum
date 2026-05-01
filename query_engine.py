"""
query_engine.py — Engine pencarian berbasis Pinecone + Gemini
Berjalan di Streamlit Cloud (tidak butuh ChromaDB lokal)
"""

from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.indices.postprocessor import SentenceTransformerRerank
from llama_index.core.llms import CustomLLM, LLMMetadata, CompletionResponse
from llama_index.core.llms.callbacks import llm_completion_callback
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from pinecone import Pinecone
import google.generativeai as genai
import streamlit as st
from typing import Any

# ══════════════════════════════════════════════════════════════════════════
# KONFIGURASI — dibaca dari Streamlit Secrets
# ══════════════════════════════════════════════════════════════════════════

def get_config():
    """
    Baca konfigurasi dari st.secrets (Streamlit Cloud)
    atau environment variable (lokal).
    """
    import os
    try:
        # Streamlit Cloud — baca dari secrets
        return {
            "gemini_key"   : st.secrets["GEMINI_KEY"],
            "pinecone_key" : st.secrets["PINECONE_KEY"],
            "pinecone_index": st.secrets.get("PINECONE_INDEX", "hukum"),
        }
    except:
        # Lokal — baca dari environment variable
        return {
            "gemini_key"    : os.getenv("GEMINI_KEY", "ISI_GEMINI_KEY"),
            "pinecone_key"  : os.getenv("PINECONE_KEY", "ISI_PINECONE_KEY"),
            "pinecone_index": os.getenv("PINECONE_INDEX", "hukum"),
        }


EMBED_MODEL  = "intfloat/multilingual-e5-base"
GEMINI_MODEL = "gemini-2.5-flash"
TOP_K        = 8

SYSTEM_PROMPT = """
Kamu adalah Asisten Hukum Indonesia yang membantu menjawab pertanyaan
berdasarkan dokumen hukum yang telah diberikan sebagai konteks.

ATURAN WAJIB:
1. Jawab HANYA berdasarkan dokumen yang tersedia dalam konteks.
2. Selalu sebutkan sumber jawaban: nama UU/peraturan, nomor pasal, dan ayat.
3. Jika informasi tidak ditemukan dalam dokumen, katakan dengan jelas:
   "Informasi ini tidak tersedia dalam dokumen yang saya miliki."
4. JANGAN mengarang atau menambahkan informasi dari luar dokumen.
5. JANGAN memberikan opini hukum atau saran hukum pribadi.
6. Jika pertanyaan membutuhkan interpretasi mendalam, sarankan konsultasi
   dengan advokat atau konsultan hukum profesional.

FORMAT JAWABAN:
- Gunakan bahasa Indonesia yang jelas dan mudah dipahami.
- Sertakan kutipan pasal yang relevan jika memungkinkan.
- Pisahkan sumber referensi di bagian akhir jawaban.
"""

# ══════════════════════════════════════════════════════════════════════════
# CUSTOM LLM — Gemini via google-generativeai
# ══════════════════════════════════════════════════════════════════════════

class GeminiLLM(CustomLLM):
    model_name    : str = GEMINI_MODEL
    context_window: int = 100000
    num_output    : int = 2048

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            context_window=self.context_window,
            num_output=self.num_output,
            model_name=self.model_name,
        )

    @llm_completion_callback()
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=SYSTEM_PROMPT,
        )
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=self.num_output,
                temperature=0.1,
            )
        )
        return CompletionResponse(text=response.text)

    @llm_completion_callback()
    def stream_complete(self, prompt: str, **kwargs: Any):
        yield self.complete(prompt, **kwargs)


# ══════════════════════════════════════════════════════════════════════════
# SETUP ENGINE
# ══════════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner="🔄 Memuat sistem...")
def buat_query_engine():
    """
    Inisialisasi query engine dengan Pinecone.
    Di-cache oleh Streamlit supaya tidak reload setiap request.
    """
    config = get_config()

    # Setup Gemini
    genai.configure(api_key=config["gemini_key"])

    # Setup embedding
    Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)
    Settings.llm         = GeminiLLM()

    # Setup Pinecone
    pc             = Pinecone(api_key=config["pinecone_key"])
    pinecone_index = pc.Index(config["pinecone_index"])
    vector_store   = PineconeVectorStore(pinecone_index=pinecone_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Load index
    index     = VectorStoreIndex.from_vector_store(
        vector_store,
        storage_context=storage_context,
    )
    retriever = index.as_retriever(similarity_top_k=TOP_K)
    reranker  = SentenceTransformerRerank(
        model="cross-encoder/ms-marco-MiniLM-L-2-v2",
        top_n=4,
    )

    return RetrieverQueryEngine.from_args(
        retriever=retriever,
        node_postprocessors=[reranker],
        response_mode="tree_summarize",
        verbose=False,
    )


# ══════════════════════════════════════════════════════════════════════════
# FUNGSI UTAMA
# ══════════════════════════════════════════════════════════════════════════

def tanya(pertanyaan: str) -> dict:
    try:
        engine   = buat_query_engine()
        response = engine.query(pertanyaan)

        sumber = []
        if hasattr(response, "source_nodes"):
            for node in response.source_nodes:
                meta = node.metadata
                sumber.append({
                    "dokumen"     : meta.get("sumber", "Tidak diketahui"),
                    "nomor_pasal" : meta.get("nomor_pasal", "-"),
                    "tipe_konten" : meta.get("tipe_konten", "teks"),
                    "skor"        : round(node.score, 3) if node.score else None,
                    "cuplikan"    : node.text[:200] + "..." if len(node.text) > 200 else node.text,
                })

        return {
            "jawaban" : str(response),
            "sumber"  : sumber,
            "berhasil": True,
            "error"   : None,
        }

    except Exception as e:
        return {
            "jawaban" : "Maaf, terjadi kesalahan saat memproses pertanyaan Anda.",
            "sumber"  : [],
            "berhasil": False,
            "error"   : str(e),
        }