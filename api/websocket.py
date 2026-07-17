import asyncio
import contextlib
import json
import os
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.config import config

ws_router = APIRouter(prefix="/api/ws", tags=["websocket"])


@ws_router.websocket("/stream/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str) -> None:
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
            except TimeoutError:
                await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        with contextlib.suppress(Exception):
            await websocket.send_json({"type": "error", "message": str(e)})


@ws_router.websocket("/live-transcribe")
async def websocket_live_transcribe(websocket: WebSocket) -> None:
    await websocket.accept()
    session_id = str(uuid.uuid4())[:8]
    await websocket.send_json(
        {
            "type": "info",
            "session": session_id,
            "message": "Kirim audio chunk (WAV/MP3) untuk transkripsi real-time",
        }
    )

    audio_chunks = []
    try:
        while True:
            data = await websocket.receive_bytes()
            audio_chunks.append(data)
            await websocket.send_json(
                {
                    "type": "progress",
                    "bytes_received": sum(len(c) for c in audio_chunks),
                    "chunks": len(audio_chunks),
                }
            )

    except WebSocketDisconnect:
        if audio_chunks:
            temp_dir = os.path.join(config.UPLOAD_DIR, "live")
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, f"live_{session_id}.wav")
            with open(temp_path, "wb") as f:
                for chunk in audio_chunks:
                    f.write(chunk)

            try:
                import sys

                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from risalah.audio_processor import process_audio
                from risalah.transcriber import transcribe_all

                temp_dir = os.path.dirname(temp_path)
                meta = process_audio(temp_path, chunk_minutes=60, output_dir=temp_dir)
                transcript = transcribe_all(meta["chunks"], "whisper")
                if transcript:
                    full_text = "\n".join(
                        s["text"] for c in transcript for s in c.get("segments", [])
                    )
                    await websocket.send_json({"type": "transcript", "text": full_text})
                else:
                    await websocket.send_json(
                        {"type": "error", "message": "Transkripsi gagal menghasilkan teks"}
                    )
            except Exception as e:
                with contextlib.suppress(Exception):
                    await websocket.send_json({"type": "error", "message": str(e)})

            with contextlib.suppress(Exception):
                os.remove(temp_path)
