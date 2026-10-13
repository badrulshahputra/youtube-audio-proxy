from fastapi import FastAPI, HTTPException, Query
import yt_dlp

app = FastAPI(title="Music Audio Stream Proxy for ESP32")

# 1. Konfigurasi SoundCloud (Pantas ~1.5 - 3 saat & 100% Direct 128kbps MP3 Penuh)
SC_OPTS = {
    'format': 'http_mp3/bestaudio[protocol=http]/bestaudio[protocol=https]',
    'noplaylist': True,
    'quiet': True,
    'socket_timeout': 10,
    'ignoreerrors': True,
}

# 2. Konfigurasi YouTube (Sandaran)
YOUTUBE_OPTS = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'socket_timeout': 12,
    'ignoreerrors': True,
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'ios', 'mweb']
        }
    },
}

def is_valid_full_stream(url: str, duration: float = 0) -> bool:
    """Tapis keluar playlist .m3u8 dan fail preview/sample 30 saat SoundCloud"""
    if not url:
        return False
    if 'm3u8' in url:
        return False
    # Tapis preview/sample 30 saat
    if 'preview' in url.lower() or 'cf-preview-media' in url:
        return False
    if duration and duration < 45:
        return False
    return True

def extract_direct_stream(entry):
    """Mencari pautan stream MP3/audio PENUH (Bukan preview 30s & Bukan .m3u8)"""
    if not entry:
        return None

    duration = entry.get('duration', 0)
    # Jika trek adalah sampel di bawah 45 saat, tolak terus trek ini
    if duration and duration < 45:
        return None

    # 1. Semak url utama jika direct mp3 penuh
    main_url = entry.get('url', '')
    if main_url and is_valid_full_stream(main_url, duration):
        if '.128.mp3' in main_url or '.mp3' in main_url:
            return main_url

    formats = entry.get('formats', [])
    # 2. Cari format http_mp3 secara spesifik yang sah & penuh
    for f in formats:
        fid = f.get('format_id', '')
        furl = f.get('url', '')
        if 'http_mp3' in fid and is_valid_full_stream(furl, duration):
            return furl

    # 3. Cari sebarang direct non-m3u8 & non-preview stream
    for f in formats:
        furl = f.get('url', '')
        proto = f.get('protocol', '')
        if furl and 'm3u8' not in proto and is_valid_full_stream(furl, duration):
            return furl

    return None

@app.get("/")
def home():
    return {
        "status": "online",
        "service": "ESP32 Music Audio Proxy",
        "usage": "/stream?q=Tajuk+Lagu"
    }

@app.get("/stream")
def get_audio_stream(q: str = Query(..., description="Kata kunci carian lagu")):
    if not q or len(q.strip()) == 0:
        raise HTTPException(status_code=400, detail="Kata kunci carian diperlukan")

    query = q.strip()

    # --- Fasa 1: Cari di SoundCloud (Imbas 5 trek, abaikan DRM & tolak preview 30s) ---
    try:
        with yt_dlp.YoutubeDL(SC_OPTS) as ydl:
            info = ydl.extract_info(f"scsearch5:{query}", download=False)
            entries = info.get('entries', []) if info else []
            for track in entries:
                if not track:
                    continue
                audio_url = extract_direct_stream(track)
                if audio_url:
                    title = track.get('title', query)
                    duration = track.get('duration', 0)
                    print(f"[LOG] Jumpa Lagu Penuh di SoundCloud: {title} (Durasi: {duration}s)")
                    return {
                        "status": "success",
                        "source": "soundcloud",
                        "title": title,
                        "url": audio_url
                    }
    except Exception as sc_err:
        print(f"[LOG] SoundCloud extractor: {sc_err}. Cuba YouTube...")

    # --- Fasa 2: Sandaran ke YouTube jika tiada lagu penuh di SoundCloud ---
    try:
        with yt_dlp.YoutubeDL(YOUTUBE_OPTS) as ydl:
            info = ydl.extract_info(f"ytsearch3:{query}", download=False)
            entries = info.get('entries', []) if info else []
            for video in entries:
                if not video:
                    continue
                audio_url = extract_direct_stream(video)
                if audio_url:
                    title = video.get('title', query)
                    duration = video.get('duration', 0)
                    print(f"[LOG] Jumpa Lagu Penuh di YouTube: {title} (Durasi: {duration}s)")
                    return {
                        "status": "success",
                        "source": "youtube",
                        "title": title,
                        "url": audio_url
                    }
    except Exception as yt_err:
        print(f"[LOG] YouTube extractor: {yt_err}")

    raise HTTPException(status_code=404, detail="Lagu penuh tidak ditemui")
