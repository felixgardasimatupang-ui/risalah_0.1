import os
import json
import asyncio
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File
from api.config import config
from api.tasks import update_job_status, get_job_status

ws_router = APIRouter(prefix="/api/ws", tags=["websocket"])


@ws_router.websocket("/stream/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str):
    await websocket.accept()
    try:
        import redis as redis_lib
        r = redis_lib.from_url(config.REDIS_URL)
        pubsub = r.pubsub()
        pubsub.subscribe(f"job:{job_id}:updates")

        raw = r.get(f"job:{job_id}")
        if raw:
            data = json.loads(raw)
            await websocket.send_json({"type": "status", **data})
            if data.get("status") in ("completed", "failed", "cancelled"):
                await websocket.close()
                return

        while True:
            msg = pubsub.get_message(timeout=30)
            if msg and msg["type"] == "message":
                data = json.loads(msg["data"])
                await websocket.send_json({"type": "progress", **data})
                if data.get("status") in ("completed", "failed", "cancelled"):
                    await websocket.close()
                    return
            try:
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, lambda: None),
                    timeout=30,
                )
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


@ws_router.websocket("/live-transcribe")
async def websocket_live_transcribe(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())[:8]
    await websocket.send_json({"type": "info", "session": session_id,
                               "message": "Kirim audio chunk (WAV/MP3) untuk transkripsi real-time"})

    audio_chunks = []
    try:
        while True:
            data = await websocket.receive_bytes()
            audio_chunks.append(data)
            await websocket.send_json({
                "type": "progress",
                "bytes_received": sum(len(c) for c in audio_chunks),
                "chunks": len(audio_chunks),
            })

    except WebSocketDisconnect:
        if audio_chunks:
            temp_dir = os.path.join(config.UPLOAD_DIR, "live")
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, f"live_{session_id}.wav")
            with open(temp_path, "wb") as f:
                for chunk in audio_chunks:
                    f.write(chunk)

            try:
                import google.generativeai as genai
                genai.configure(api_key=config.GEMINI_API_KEY)
                model = genai.GenerativeModel("gemini-2.0-flash")

                audio_file = genai.upload_file(temp_path)
                prompt = (
                    "Transkripsikan audio ini dalam Bahasa Indonesia.\n"
                    "Format: [MM:SS] PEMBICARA: teks\n"
                    "Gunakan [Pembicara 1], [Pembicara 2] jika tidak yakin.\n"
                    "Koreksi istilah pemerintahan."
                )
                response = model.generate_content([prompt, audio_file], stream=True)

                for chunk in response:
                    if chunk.text:
                        try:
                            await websocket.send_json({
                                "type": "transcript",
                                "text": chunk.text,
                            })
                        except Exception:
                            pass

                try:
                    genai.delete_file(audio_file.name)
                except Exception:
                    pass
            except Exception as e:
                try:
                    await websocket.send_json({"type": "error", "message": str(e)})
                except Exception:
                    pass

            try:
                os.remove(temp_path)
            except Exception:
                pass
