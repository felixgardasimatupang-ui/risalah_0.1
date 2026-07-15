import os
import sys
from pydub import AudioSegment
import whisper
import torch

def potong_dan_transkrip_lokal(file_audio_input, folder_output="hasil_transkrip_lokal"):
    # Membuat folder output jika belum ada
    if not os.path.exists(folder_output):
        os.makedirs(folder_output)
        
    print("🎵 Memuat file audio asli...")
    if not os.path.exists(file_audio_input):
        print(f"❌ Error: File audio '{file_audio_input}' tidak ditemukan.")
        return
        
    audio = AudioSegment.from_file(file_audio_input)
    
    # 30 menit dalam satuan milidetik (30 * 60 * 1000)
    durasi_30_menit = 1800000 
    panjang_audio = len(audio)
    
    chunk_ke = 1
    start_time = 0
    
    # Deteksi akselerasi GPU (MPS) untuk Apple Silicon Mac
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"💻 Menggunakan device: {device.upper()} untuk komputasi AI.")
    
    # Load model Whisper untuk transkripsi
    print("🤖 Memuat AI Transkripsi (Whisper Model: base)...")
    # Pilihan model: tiny, base, small, medium, large
    model = whisper.load_model("base", device=device)
    
    while start_time < panjang_audio:
        end_time = min(start_time + durasi_30_menit, panjang_audio)
        
        # 1. Proses Pemotongan dan Ekspor ke MP3
        potongan = audio[start_time:end_time]
        nama_file_mp3 = f"potongan_menit_{int(start_time/60000)}_ke_{int(end_time/60000)}.mp3"
        path_mp3 = os.path.join(folder_output, nama_file_mp3)
        
        print(f"\n💾 [Bagian {chunk_ke}] Mengekspor ke format MP3: {nama_file_mp3}...")
        potongan.export(path_mp3, format="mp3")
        
        # 2. Jalankan Transkripsi menggunakan Whisper Lokal
        print(f"📝 [Bagian {chunk_ke}] Memulai transkrip lokal (Bahasa Indonesia)...")
        try:
            # Mengatur language ke "id" (Indonesian) untuk transkripsi yang lebih akurat
            result = model.transcribe(path_mp3, language="id")
            
            # 3. Simpan Hasil Transkrip Teks ke File
            nama_file_txt = f"transkrip_bagian_{chunk_ke}.txt"
            path_txt = os.path.join(folder_output, nama_file_txt)
            
            with open(path_txt, "w", encoding="utf-8") as f:
                f.write(result["text"].strip())
                
            print(f"✅ Selesai! File teks disimpan di: {path_txt}")
            
        except Exception as e:
            print(f"❌ Terjadi kesalahan saat mentranskrip: {e}")
        
        start_time += durasi_30_menit
        chunk_ke += 1

    print("\n🎉 Hore! Semua isi file audio Anda telah berhasil diproses secara lokal.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Penggunaan: .venv/bin/python transcribe_local.py <nama_file_audio> [folder_output]")
        print("Contoh: .venv/bin/python transcribe_local.py rekaman_rapat_besar.mp4")
        sys.exit(1)
        
    audio_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "hasil_transkrip_lokal"
    potong_dan_transkrip_lokal(audio_file, output_dir)
