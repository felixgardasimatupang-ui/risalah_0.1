import json
import os
import sys
import tempfile
import time

import requests
import streamlit as st
from dotenv import load_dotenv

from risalah.job_cache import cache_jobs, get_cached_jobs

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
    return _api_req("GET", "/health", timeout=5)


def _api_req(method, path, **kwargs):
    try:
        r = requests.request(method, f"{API_BASE}{path}", timeout=kwargs.pop("timeout", 10), **kwargs)
        if r.ok:
            return r.json()
        return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except requests.ConnectionError:
        return {"error": "Server API tidak terhubung"}
    except requests.Timeout:
        return {"error": "Request timeout"}
    except Exception as e:
        return {"error": str(e)}


def upload_file(file_bytes, filename):
    return _api_req("POST", "/upload", files={"file": (filename, file_bytes)}, timeout=60)


def start_job(file_path, file_name, engine, chunk_minutes, title, classification, doc_number, lang="id"):
    return _api_req(
        "POST", "/transcribe",
        data={
            "file_path": file_path,
            "file_name": file_name,
            "engine": engine,
            "chunk_minutes": chunk_minutes,
            "title": title,
            "classification": classification,
            "doc_number": doc_number,
            "lang": lang,
        },
        timeout=15,
    )


def get_jobs():
    try:
        d = _api_req("GET", "/jobs?limit=50", timeout=5)
        if d and "error" not in d:
            jobs = d.get("jobs", [])
            cache_jobs(jobs)
            return jobs
    except Exception:
        pass
    return get_cached_jobs()


def get_job(job_id):
    try:
        d = _api_req("GET", f"/jobs/{job_id}", timeout=5)
        if d and "error" not in d:
            cache_jobs([d])
            return d
    except Exception:
        pass
    cached = get_cached_jobs()
    for j in cached:
        if j["id"] == job_id:
            return j
    return None


def download_result(job_id):
    """Return DOCX bytes for a completed job."""
    try:
        r = requests.get(f"{API_BASE}/download/{job_id}", timeout=10)
        if r.ok:
            return r.content
    except Exception:
        pass
    return None


def download_pdf_result(job_id):
    """Return PDF bytes for a completed job."""
    try:
        r = requests.get(f"{API_BASE}/download/{job_id}/pdf", timeout=15)
        if r.ok:
            return r.content
    except Exception:
        pass
    return None


@st.cache_resource
def _load_whisper_model():
    import whisper

    return whisper.load_model("base", device="cpu")


def _transcribe_audio(audio_bytes):
    """Transcribe recorded audio bytes with Whisper."""
    from risalah.id_terms import normalize_indonesian

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp.write(audio_bytes)
    tmp_path = tmp.name
    tmp.close()

    try:
        model = _load_whisper_model()
        result = model.transcribe(tmp_path, language="id", fp16=False)
        text = normalize_indonesian(result["text"].strip())
        return text, result.get("segments", [])
    finally:
        os.unlink(tmp_path)


health = api_health()
if not health:
    cached = get_cached_jobs(limit=1)
    if cached:
        st.sidebar.warning("⚠️ API offline. Menampilkan data dari cache lokal.")
    else:
        st.sidebar.error("Server API tidak terhubung. Jalankan: uvicorn api.app:app --reload")
elif health.get("status") == "degraded":
    st.sidebar.warning("API berjalan tanpa Redis. Queue & progress real-time tidak aktif.")
else:
    st.sidebar.success("Server API terhubung")
    st.sidebar.json(health)

st.sidebar.markdown("---")
lang = st.sidebar.selectbox("Bahasa / Language", ["id", "en"], index=0, help="id=Indonesia, en=English")
st.session_state["lang"] = lang
st.sidebar.markdown("---")
st.sidebar.markdown("### Navigasi")
page = st.sidebar.radio("Menu", ["Upload & Transkripsi", "Rekam Langsung", "Riwayat Job", "Dokumen Pendukung", "Panduan"])

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
                        err = result.get("error") if isinstance(result, dict) else None
                        if err:
                            st.error(f"Upload gagal: {err}")
                        elif result:
                            job = start_job(
                                result["file_path"],
                                result["file_name"],
                                engine,
                                chunk_minutes,
                                title,
                                classification,
                                doc_number,
                                st.session_state.get("lang", "id"),
                            )
                            err2 = job.get("error") if isinstance(job, dict) else None
                            if err2:
                                st.error(f"Submit gagal: {err2}")
                            elif job:
                                st.success(f"Job {job['id']} dimulai!")
                                st.session_state["active_job"] = job["id"]
                            else:
                                st.error("Gagal submit job: respon kosong")
                        else:
                            st.error("Gagal upload file: respon kosong")
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
                                st.session_state.get("lang", "id"),
                            )
                            err = job.get("error") if isinstance(job, dict) else None
                            if err:
                                st.error(f"Submit folder gagal: {err}")
                            elif job:
                                st.success(f"Job folder {job['id']} dimulai!")
                                st.session_state["active_job"] = job["id"]
                            else:
                                st.error("Gagal submit job folder: respon kosong")
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

elif page == "Rekam Langsung":
    st.markdown(
        '<div class="main-header"><h2>🎤 Rekam & Transkripsi Langsung</h2></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        "Rekam audio langsung dari browser. Transkripsi instan dengan Whisper + koreksi Bahasa Indonesia."
    )

    audio_bytes = st.audio_input("Klik mikrofon untuk mulai merekam", key="live_mic")

    if audio_bytes:
        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.audio(audio_bytes, format="audio/wav")
        with col_b:
            if st.button("🎯 Transkrip Sekarang", type="primary", use_container_width=True):
                with st.status("⏳ Memproses...") as status:
                    st.write("Mentranskripsi dengan Whisper...")
                    text, segments = _transcribe_audio(audio_bytes)
                    status.update(label="✅ Selesai!", state="complete")

                st.session_state["live_text"] = text
                st.session_state["live_segments"] = segments

        if st.session_state.get("live_text"):
            st.divider()
            edited = st.text_area(
                "📝 Hasil Transkripsi (dapat diedit langsung)",
                st.session_state["live_text"],
                height=200,
            )

            cc1, cc2, cc3 = st.columns(3)
            with cc1:
                st.download_button(
                    "📋 Salin sebagai TXT",
                    edited,
                    file_name="transkrip_langsung.txt",
                    use_container_width=True,
                )
            with cc2:
                st.button("📋 Salin ke Clipboard", use_container_width=True, disabled=True)
            with cc3:
                st.page_link(
                    "ui/app.py",
                    label="📄 Buat Risalah DOCX",
                    disabled=True,
                    use_container_width=True,
                )

            if st.session_state.get("live_segments"):
                with st.expander("📊 Lihat Segmen Waktu"):
                    for seg in st.session_state["live_segments"]:
                        start = seg.get("start", 0)
                        end = seg.get("end", 0)
                        text_seg = seg.get("text", "")
                        st.caption(f"[{start:.1f}s → {end:.1f}s]  {text_seg}")
    else:
        st.info("👆 Klik ikon mikrofon di atas. Izinkan akses mikrofon. Rekam, lalu stop.")

elif page == "Riwayat Job":
    st.markdown('<div class="main-header"><h2>📂 Riwayat Job</h2></div>', unsafe_allow_html=True)

    search_q = st.text_input("🔍 Cari job (nama file atau pesan)", placeholder="Ketik untuk filter...")
    jobs = get_jobs()
    _total_jobs = len(jobs)
    if search_q:
        q = search_q.lower()
        jobs = [j for j in jobs if q in (j.get("file_name", "") + j.get("message", "") + j.get("preview_text", "")).lower()]

    if not jobs:
        st.info("Tidak ada job" if not search_q else f"Tidak ditemukan job untuk \"{search_q}\"")
    else:
        st.caption(f"{len(jobs)} job ditemukan" + (f" (dari {_total_jobs} total)" if search_q else ""))
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
                    with st.popover("📥 Export / Share", use_container_width=True):
                        docx_data = download_result(j["id"])
                        if docx_data:
                            st.download_button(
                                "📄 DOCX",
                                docx_data,
                                file_name=os.path.basename(j["result_path"]),
                                key=f"dl_{j['id']}",
                                use_container_width=True,
                            )
                            pdf_data = download_pdf_result(j["id"])
                            if pdf_data:
                                base = os.path.splitext(os.path.basename(j["result_path"]))[0]
                                st.download_button(
                                    "📕 PDF",
                                    pdf_data,
                                    file_name=f"{base}.pdf",
                                    mime="application/pdf",
                                    key=f"pdf_{j['id']}",
                                    use_container_width=True,
                                )
                        preview = j.get("preview_text", "")
                        if preview:
                            st.download_button(
                                "📃 TXT",
                                preview,
                                file_name=f"{j.get('file_name', j['id'][:12])}.txt",
                                key=f"txt_{j['id']}",
                                use_container_width=True,
                            )
                        st.divider()
                        st.caption("📧 Share via Email")
                        share_to = st.text_input("Email tujuan", key=f"em_{j['id']}")
                        if st.button("Kirim", key=f"send_{j['id']}", use_container_width=True):
                            if share_to and docx_data:
                                from risalah.email_utils import send_docx_email
                                ok, msg = send_docx_email(
                                    share_to,
                                    f"Risalah Rapat: {j.get('file_name', '')}",
                                    f"Berikut risalah rapat {j.get('file_name', '')}.\n\n{preview[:1000] if preview else ''}",
                                    docx_data,
                                    filename=j.get("file_name", "risalah.docx"),
                                )
                                if ok:
                                    st.success(msg)
                                else:
                                    st.error(f"Gagal: {msg}")
                            else:
                                st.warning("Isi email tujuan")
                elif j["status"] == "running":
                    if st.button("⏹", key=f"cancel_{j['id']}"):
                        requests.delete(f"{API_BASE}/jobs/{j['id']}", timeout=5)
                        st.rerun()
            preview = j.get("preview_text", "")
            if preview:
                with st.expander("📝 Preview"):
                    st.text(preview[:2000])
                if j["status"] == "completed":
                    with st.expander("✏️ Edit & Download"):
                        edited = st.text_area("Edit teks", preview, height=300, key=f"ed_{j['id']}")
                        metadata = {
                            "acara": j.get("file_name", "Rapat"),
                            "tanggal": j.get("created_at", "")[:10],
                        }
                        if st.button("⬇️ Download DOCX (Hasil Edit)", key=f"ed_dl_{j['id']}"):
                            from risalah.docx_generator import render_edited_to_docx
                            buf = render_edited_to_docx(edited, metadata, title="RISALAH RAPAT")
                            fname = j.get("file_name", j["id"][:12]).replace(" ", "_")
                            st.download_button(
                                "📄 Simpan DOCX",
                                buf,
                                file_name=f"{fname}_edited.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"ed_save_{j['id']}",
                                use_container_width=True,
                            )
            st.divider()

        if jobs:
            st.caption(f"🗄 Cache lokal: {len(jobs)} job tersimpan")

elif page == "Dokumen Pendukung":
    st.markdown(
        '<div class="main-header"><h2>📎 Dokumen Pendukung</h2></div>',
        unsafe_allow_html=True,
    )

    def _load_scan():
        p = os.path.join(PROJECT_ROOT, "output", "scan_results.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        return None

    scan = _load_scan()
    if not scan:
        st.info("Belum ada hasil scan. Jalankan pipeline mode folder untuk melihat dokumen pendukung.")
    else:
        st.caption(f"Folder: `{scan['folder']}` | Scan: {scan['scan_time'][:19]} | {scan['total_files']} file")

        icons = {"audio": "🎵", "image": "🖼", "document": "📄", "text": "📝", "spreadsheet": "📊"}

        for _type, label in [("audio", "Audio"), ("document", "Dokumen"), ("image", "Gambar"),
                              ("text", "Teks"), ("spreadsheet", "Spreadsheet")]:
            files = scan.get(f"{_type}_files", [])
            if not files:
                continue
            with st.expander(f"{icons.get(_type, '📁')} {label} ({len(files)})"):
                for f in files:
                    sz = f.get("size_bytes", 0)
                    sz_str = f"{sz/1024:.1f} KB" if sz > 0 else "0 B"
                    st.markdown(f"- `{f['name']}` ({sz_str})")

        # Show extracted text if available
        ext_path = os.path.join(PROJECT_ROOT, "output", "extracted_text", "extracted_text.json")
        if os.path.exists(ext_path):
            with open(ext_path, encoding="utf-8") as f:
                ext = json.load(f)
            combined = ext.get("all_text_combined", "").strip()
            with st.expander(f"📄 Teks Terekstrak ({len(combined)} chars)", expanded=False):
                st.text(combined[:10000] if len(combined) > 10000 else combined)
                if len(combined) > 10000:
                    st.caption(f"... dan {len(combined) - 10000} karakter lagi")

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

    ### Rekam Langsung (Baru! 🎤)

    - Rekam audio langsung dari browser via mikrofon
    - Transkripsi instan dengan Whisper (model base)
    - Koreksi otomatis Bahasa Indonesia (318 istilah pemerintah + slang)
    - Hasil bisa diedit, disalin sebagai TXT
    - Cocok untuk catatan rapat singkat atau ide cepat

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
