import os
import sys
import assemblyai as aai
from pydub import AudioSegment
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def potong_dan_transkrip_cloud(file_audio_input, folder_output="hasil_transkrip_cloud"):
    # Membuat folder output jika belum ada
    if not os.path.exists(folder_output):
        os.makedirs(folder_output)
        
    print("🎵 Memuat file audio asli ke sistem...")
    if not os.path.exists(file_audio_input):
        print(f"❌ Error: File audio '{file_audio_input}' tidak ditemukan.")
        return
        
    audio = AudioSegment.from_file(file_audio_input)
    
    # Konfigurasi waktu: 30 menit dalam satuan milidetik (30 * 60 * 1000)
    durasi_30_menit = 1800000 
    panjang_audio = len(audio)
    
    chunk_ke = 1
    start_time = 0
    
    # Mengaktifkan fitur pembeda pembicara (Speaker Diarization)
    # Kami set language_code ke "id" untuk Bahasa Indonesia.
    config = aai.TranscriptionConfig(
        speaker_labels=True, 
        language_code="id"  
    )
    transcriber = aai.Transcriber()
    
    # Mulai proses pemotongan berantai hingga audio habis
    while start_time < panjang_audio:
        end_time = min(start_time + durasi_30_menit, panjang_audio)
        
        # 1. Proses Pemotongan dan Ekspor ke MP3
        potongan = audio[start_time:end_time]
        nama_file_mp3 = f"potongan_menit_{int(start_time/60000)}_ke_{int(end_time/60000)}.mp3"
        path_mp3 = os.path.join(folder_output, nama_file_mp3)
        
        print(f"\n💾 [Bagian {chunk_ke}] Mengekspor ke format MP3: {nama_file_mp3}...")
        potongan.export(path_mp3, format="mp3")
        
        # 2. Proses Pengiriman ke Server Cloud AssemblyAI
        print(f"🚀 [Bagian {chunk_ke}] Mengirim audio ke Cloud API...")
        try:
            transcript = transcriber.transcribe(path_mp3, config=config)
            
            # Cek jika ada error dari server
            if transcript.status == aai.TranscriptStatus.error:
                print(f"❌ Gagal memproses transkrip: {transcript.error}")
                start_time += durasi_30_menit
                chunk_ke += 1
                continue
            
            # 3. Format dan Simpan Hasil Transkrip Berdasarkan Pembicara
            nama_file_txt = f"transkrip_pembicara_bagian_{chunk_ke}.txt"
            path_txt = os.path.join(folder_output, nama_file_txt)
            
            print(f"📝 [Bagian {chunk_ke}] Menyusun format nama pembicara...")
            with open(path_txt, "w", encoding="utf-8") as f:
                # Blok 'utterances' di bawah ini otomatis memisahkan kalimat tiap orang berbeda
                for utterance in transcript.utterances:
                    # Menghasilkan format -> Pembicara A: "Halo semuanya..."
                    baris_teks = f"Pembicara {utterance.speaker}: {utterance.text}\n"
                    f.write(baris_teks)
                    
            print(f"✅ Selesai! File teks disimpan di: {path_txt}")
            
        except Exception as e:
            print(f"❌ Terjadi kesalahan jaringan / sistem: {e}")
        
        # Melanjutkan ke 30 menit berikutnya
        start_time += durasi_30_menit
        chunk_ke += 1
        
    print("\n🎉 Hore! Semua isi file audio Anda telah berhasil dipotong dan ditranskrip.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Penggunaan: .venv/bin/python transcribe.py <nama_file_audio> [folder_output]")
        print("Contoh: .venv/bin/python transcribe.py rekaman_rapat_besar.mp4")
        sys.exit(1)
        
    # Check AssemblyAI API Key
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key or api_key == "your_assemblyai_api_key_here":
        print("❌ Error: ASSEMBLYAI_API_KEY tidak ditemukan di file .env atau masih menggunakan default template.")
        print("Silakan buka file .env dan masukkan API Key AssemblyAI Anda.")
        sys.exit(1)
        
    aai.settings.api_key = api_key
    
    audio_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "hasil_transkrip_cloud"
    potong_dan_transkrip_cloud(audio_file, output_dir)
