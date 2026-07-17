import json
import os
import sys
import time

import requests
import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

load_dotenv()

API_BASE = os.getenv("API_URL", "http://localhost:8000/api")

st.set_page_config(
    page_title="Risalah Rapat",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .stApp { background: #f5f5f5; }
    .main-header { text-align: center; padding: 1rem; background: white; border-radius: 10px; margin-bottom: 1rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .job-card { background: white; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border-left: 4px solid #1f77b4; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .status-badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 0.8em; font-weight: 600; }
    .status-completed { background: #d4edda; color: #155724; }
    .status-running { background: #fff3cd; color: #856404; }
    .status-failed { background: #f8d7da; color: #721c24; }
    .status-pending { background: #e2e3e5; color: #383d41; }
    div[data-testid="stSidebarNav"] { display: none; }
</style>
""",
    unsafe_allow_html=True,
)


def api_health():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None


def upload_file(file_bytes, filename):
    r = requests.post(f"{API_BASE}/upload", files={"file": (filename, file_bytes)}, timeout=60)
    if r.ok:
        return r.json()
    return None


def start_job(file_path, file_name, engine, chunk_minutes, title, classification, doc_number):
    r = requests.post(
        f"{API_BASE}/transcribe",
        data={
            "file_path": file_path,
            "file_name": file_name,
            "engine": engine,
            "chunk_minutes": chunk_minutes,
            "title": title,
            "classification": classification,
            "doc_number": doc_number,
        },
        timeout=10,
    )
    if r.ok:
        return r.json()
    return None


def get_jobs():
    try:
        r = requests.get(f"{API_BASE}/jobs?limit=50", timeout=5)
        if r.ok:
            return r.json().get("jobs", [])
    except Exception:
        pass
    return []


def get_job(job_id):
    try:
        r = requests.get(f"{API_BASE}/jobs/{job_id}", timeout=5)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None


def download_result(job_id):
    r = requests.get(f"{API_BASE}/download/{job_id}", timeout=10)
    if r.ok:
        return r.content
    return None


health = api_health()
if not health:
    st.sidebar.error("Server API tidak terhubung. Jalankan: uvicorn api.app:app --reload")
elif health.get("status") == "degraded":
    st.sidebar.warning("API berjalan tanpa Redis. Queue & progress real-time tidak aktif.")
else:
    st.sidebar.success("Server API terhubung")
    st.sidebar.json(health)

st.sidebar.markdown("---")
st.sidebar.markdown("### Navigasi")
page = st.sidebar.radio("Menu", ["Upload & Transkripsi", "Riwayat Job", "Panduan"])

if page == "Upload & Transkripsi":
    st.markdown(
        '<div class="main-header"><h1>📋 Risalah Rapat</h1><p>Upload audio/folder → DOCX risalah format pemerintah</p></div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("### Upload Audio")
        uploaded_file = st.file_uploader(
            "Pilih file audio (MP3, WAV, M4A, FLAC, dll)",
            type=["mp3", "wav", "m4a", "flac", "ogg", "mp4", "wma", "aac"],
        )

        st.markdown("### Atau masukkan path folder")
        folder_path = st.text_input(
            "Path folder (untuk mode folder)", placeholder="/path/to/folder"
        )

        st.markdown("### Konfigurasi")
        cc1, cc2 = st.columns(2)
        with cc1:
            engine = st.selectbox(
                "Engine Transkripsi",
                ["whisper", "assemblyai"],
                index=0,
                help="whisper=lokal, assemblyai=cloud",
            )
            chunk_minutes = st.slider("Durasi per chunk (menit)", 10, 60, 30)
            classification = st.selectbox("Klasifikasi", ["BIASA", "TERBATAS", "RAHASIA"], index=0)
        with cc2:
            title = st.text_input("Judul Risalah", "RISALAH RAPAT")
            doc_number = st.text_input("Nomor Dokumen", "_______________")

        if st.button("🚀 Proses Sekarang", type="primary", use_container_width=True):
            if not uploaded_file and not folder_path:
                st.error("Upload file atau masukkan path folder")
            else:
                with st.spinner("Upload & submit job..."):
                    if uploaded_file:
                        result = upload_file(uploaded_file.getvalue(), uploaded_file.name)
                        if result:
                            job = start_job(
                                result["file_path"],
                                result["file_name"],
                                engine,
                                chunk_minutes,
                                title,
                                classification,
                                doc_number,
                            )
                            if job:
                                st.success(f"Job {job['id']} dimulai!")
                                st.session_state["active_job"] = job["id"]
                            else:
                                st.error("Gagal submit job")
                        else:
                            st.error("Gagal upload file")
                    elif folder_path:
                        if os.path.exists(folder_path):
                            job = start_job(
                                folder_path,
                                os.path.basename(folder_path),
                                engine,
                                chunk_minutes,
                                title,
                                classification,
                                doc_number,
                            )
                            if job:
                                st.success(f"Job folder {job['id']} dimulai!")
                                st.session_state["active_job"] = job["id"]
                            else:
                                st.error("Gagal submit job folder")
                        else:
                            st.error(f"Folder tidak ditemukan: {folder_path}")

    with col2:
        st.markdown("### Progress Real-time")
        placeholder = st.empty()

        active_job = st.session_state.get("active_job")
        if active_job:
            import requests as req
            import sseclient

            try:
                response = req.get(f"{API_BASE}/stream/{active_job}", stream=True, timeout=60)
                client = sseclient.SSEClient(response)
                for event in client.events():
                    if event.data:
                        data = json.loads(event.data)
                        status = data.get("status", "")
                        progress = data.get("progress", 0)
                        message = data.get("message", "")

                        with placeholder.container():
                            st.markdown(f"**Job:** `{active_job}`")
                            st.progress(progress / 100)
                            st.markdown(f"**Status:** `{status.upper()}`")
                            st.markdown(f"**{message}**")
                            st.caption(f"{progress}%")

                            if status == "completed":
                                st.balloons()
                                st.success("✅ Risalah selesai!")
                                result_path = data.get("result_path", "")
                                if result_path:
                                    docx_data = download_result(active_job)
                                    if docx_data:
                                        docx_name = os.path.basename(result_path)
                                        st.download_button(
                                            "📥 Download DOCX",
                                            docx_data,
                                            file_name=docx_name,
                                            use_container_width=True,
                                        )
                                preview = data.get("preview_text", "")
                                if preview:
                                    with st.expander("Lihat Preview"):
                                        st.text(preview[:3000])
                                break
                            elif status == "failed":
                                st.error(f"❌ Gagal: {message}")
                                break
                            elif status == "cancelled":
                                st.warning("⏹ Job dibatalkan")
                                break

                    time.sleep(0.1)
            except Exception:
                with placeholder.container():
                    st.info("Menghubungkan ke stream progress...")
                    status = get_job(active_job)
                    if status:
                        st.json(status)
        else:
            with placeholder.container():
                st.info("Upload file & klik Proses untuk memulai")

    st.markdown("---")
    st.markdown("### Riwayat Cepat")
    recent = get_jobs()[:5]
    if recent:
        for j in recent:
            cls = f"status-{j.get('status', 'pending')}"
            st.markdown(
                f'<div class="job-card">'
                f"<strong>{j.get('file_name', j['id'][:12])}</strong> "
                f'<span class="status-badge {cls}">{j["status"].upper()}</span> '
                f"<br><small>{j.get('message', '')} | {j.get('progress', 0)}%</small>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("Belum ada job")

elif page == "Riwayat Job":
    st.markdown('<div class="main-header"><h2>📂 Riwayat Job</h2></div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown("**File**")
    with col2:
        st.markdown("**Status**")
    with col3:
        st.markdown("**Aksi**")

    jobs = get_jobs()
    if not jobs:
        st.info("Belum ada job")
    else:
        for j in jobs:
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.markdown(f"**{j.get('file_name', j['id'][:12])}**")
                st.caption(f"{j.get('created_at', '')[:19]} | {j.get('message', '')}")
            with c2:
                cls = f"status-{j.get('status', 'pending')}"
                st.markdown(
                    f'<span class="status-badge {cls}">{j["status"].upper()}</span>',
                    unsafe_allow_html=True,
                )
            with c3:
                if j["status"] == "completed" and j.get("result_path"):
                    docx_data = download_result(j["id"])
                    if docx_data:
                        st.download_button(
                            "📥",
                            docx_data,
                            file_name=os.path.basename(j["result_path"]),
                            key=f"dl_{j['id']}",
                        )
                elif j["status"] == "running":
                    if st.button("⏹", key=f"cancel_{j['id']}"):
                        requests.delete(f"{API_BASE}/jobs/{j['id']}", timeout=5)
                        st.rerun()
            st.divider()

elif page == "Panduan":
    st.markdown(
        '<div class="main-header"><h2>📖 Panduan Penggunaan</h2></div>', unsafe_allow_html=True
    )

    st.markdown("""
    ### Cara Menggunakan

    1. **Upload Audio** — pilih file MP3/WAV/M4A/FLAC/OGG/MP4
    2. **Atau Folder** — masukkan path folder yang berisi audio + dokumen pendukung
    3. **Konfigurasi** — pilih engine transkripsi & format risalah
    4. **Proses** — pipeline otomatis berjalan
    5. **Download** — dapatkan DOCX risalah format pemerintah

    ### Engine Transkripsi

    | Engine | Kecepatan | Akurasi | Biaya |
    |--------|-----------|---------|-------|
    | Whisper | Sedang | Tinggi | Gratis (lokal) |
    | Gemini | Cepat | Tinggi | Gratis (kuota) |
    | AssemblyAI | Lambat | Sangat Tinggi | Berbayar |

    ### Mode Folder

    Pipeline akan:
    - Scan semua file audio & dokumen
    - OCR gambar (via Gemini)
    - Ekstrak teks dari PDF, DOCX, XLSX, TXT
    - Transkripsi semua audio
    - Gabungkan ke satu risalah

    ### Klasifikasi Dokumen

    - **BIASA** — dokumen publik
    - **TERBATAS** — internal instansi
    - **RAHASIA** — confidential

    ### API Endpoints

    | Method | Endpoint | Fungsi |
    |--------|----------|--------|
    | GET | `/api/health` | Cek status server |
    | POST | `/api/upload` | Upload file audio |
    | POST | `/api/transcribe` | Start job transkripsi |
    | GET | `/api/jobs` | List semua job |
    | GET | `/api/jobs/{id}` | Detail job |
    | DELETE | `/api/jobs/{id}` | Cancel job |
    | GET | `/api/download/{id}` | Download DOCX |
    | GET | `/api/stream/{id}` | SSE progress stream |
    | WS | `/api/ws/stream/{id}` | WebSocket progress |

    ### Contoh cURL

    ```bash
    # Upload file
    curl -X POST http://localhost:8000/api/upload -F "file=@rapat.mp3"

    # Transkripsi
    curl -X POST http://localhost:8000/api/transcribe \\
      -d "file_path=/path/to/rapat.mp3" \\
      -d "engine=whisper" \\
      -d "title=RISALAH RAPAT"

    # Cek progress
    curl http://localhost:8000/api/stream/{job_id}

    # Download hasil
    curl -O http://localhost:8000/api/download/{job_id}
    ```

    ### Teknologi

    - **FastAPI** — REST API + WebSocket
    - **Celery + Redis** — Queue & background job
    - **Streamlit** — Web UI
    - **Whisper / Gemini / AssemblyAI** — Transkripsi
    - **Pyannote** — Speaker diarization
    - **python-docx** — DOCX generation
    """)
