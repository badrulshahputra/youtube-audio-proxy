from fastapi import FastAPI, HTTPException, Query
import yt_dlp

app = FastAPI(title="Music Audio Stream Proxy for ESP32")

# 1. Konfigurasi YouTube (Android + Mweb)
YOUTUBE_OPTS = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch1:',
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'mweb']
        }
    },
    'socket_timeout': 15,
}

# 2. Konfigurasi SoundCloud (Sandaran Direct 128kbps MP3)
SC_OPTS = {
    'format': 'http_mp3/bestaudio[protocol=http]/bestaudio[protocol=https]/bestaudio',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'scsearch1:',
    'socket_timeout': 12,
}

def extract_direct_stream(entry):
    """Mencari pautan stream terus yang BUKAN playlist .m3u8 (Pantas & serasi ESP32 / Browser)"""
    formats = entry.get('formats', [])
    # 1. Keutamaan: Audio-only direct stream (cth: .128.mp3 atau audio googlevideo)
    for f in reversed(formats):
        proto = f.get('protocol', '')
        url = f.get('url', '')
        acodec = f.get('acodec', 'none')
        vcodec = f.get('vcodec', 'none')
        if url and acodec != 'none' and vcodec == 'none' and 'm3u8' not in proto and 'm3u8' not in url:
            return url

    # 2. Pilihan kedua: Sebarang direct stream bukan m3u8
    for f in reversed(formats):
        proto = f.get('protocol', '')
        url = f.get('url', '')
        acodec = f.get('acodec', 'none')
        if url and acodec != 'none' and 'm3u8' not in proto and 'm3u8' not in url:
            return url

    # 3. Fallback jika tiada direct format
    return entry.get('url')

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

    # --- Fasa 1: Cuba cari di YouTube dahulu ---
    try:
        with yt_dlp.YoutubeDL(YOUTUBE_OPTS) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if 'entries' in info and len(info['entries']) > 0:
                video = info['entries'][0]
                audio_url = extract_direct_stream(video)
                title = video.get('title', query)
                if audio_url and 'm3u8' not in audio_url:
                    return {
                        "status": "success",
                        "source": "youtube",
                        "title": title,
                        "url": audio_url
                    }
    except Exception as yt_err:
        print(f"[LOG] YouTube extractor: {yt_err}. Mengaktifkan SoundCloud...")

    # --- Fasa 2: Sandaran Automatik ke SoundCloud (Direct MP3) ---
    try:
        with yt_dlp.YoutubeDL(SC_OPTS) as ydl:
            info = ydl.extract_info(f"scsearch1:{query}", download=False)
            if 'entries' in info and len(info['entries']) > 0:
                track = info['entries'][0]
                audio_url = extract_direct_stream(track)
                title = track.get('title', query)
                if audio_url:
                    return {
                        "status": "success",
                        "source": "soundcloud",
                        "title": title,
                        "url": audio_url
                    }
    except Exception as sc_err:
        print(f"[LOG] SoundCloud extractor: {sc_err}")

    raise HTTPException(status_code=404, detail="Lagu tidak ditemui")
