from fastapi import FastAPI, HTTPException, Query
import yt_dlp

app = FastAPI(title="Music Audio Stream Proxy for ESP32")

# 1. Konfigurasi SoundCloud (Keutamaan Utama: Sangat Pantas ~1.5 saat & Direct 128kbps MP3)
SC_OPTS = {
    'format': 'http_mp3/bestaudio[protocol=http]/bestaudio[protocol=https]',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'scsearch1:',
    'socket_timeout': 12,
}

# 2. Konfigurasi YouTube (Sandaran jika tiada di SoundCloud)
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

def extract_direct_stream(entry):
    """Mencari pautan stream terus yang BUKAN playlist .m3u8 (Pantas, stabil & elak crash ESP32)"""
    # 1. Pautan yang dipilih yt-dlp secara automatik (Direct MP3)
    main_url = entry.get('url', '')
    if main_url and 'm3u8' not in main_url and ('.128.mp3' in main_url or '.mp3' in main_url):
        return main_url

    formats = entry.get('formats', [])
    # 2. Cari format http_mp3 secara spesifik
    for f in formats:
        fid = f.get('format_id', '')
        furl = f.get('url', '')
        if 'http_mp3' in fid and furl and 'm3u8' not in furl:
            return furl

    # 3. Cari sebarang direct non-m3u8 stream
    for f in formats:
        furl = f.get('url', '')
        proto = f.get('protocol', '')
        if furl and 'm3u8' not in furl and 'm3u8' not in proto:
            return furl

    return main_url

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

    # --- Fasa 1: Cari di SoundCloud dahulu (Pantas ~1.5 saat & 100% Direct MP3) ---
    try:
        with yt_dlp.YoutubeDL(SC_OPTS) as ydl:
            info = ydl.extract_info(f"scsearch1:{query}", download=False)
            if 'entries' in info and len(info['entries']) > 0:
                track = info['entries'][0]
                audio_url = extract_direct_stream(track)
                title = track.get('title', query)
                if audio_url:
                    print(f"[LOG] Jumpa di SoundCloud: {title}")
                    return {
                        "status": "success",
                        "source": "soundcloud",
                        "title": title,
                        "url": audio_url
                    }
    except Exception as sc_err:
        print(f"[LOG] SoundCloud extractor: {sc_err}. Cuba YouTube...")

    # --- Fasa 2: Sandaran ke YouTube jika tiada di SoundCloud ---
    try:
        with yt_dlp.YoutubeDL(YOUTUBE_OPTS) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if 'entries' in info and len(info['entries']) > 0:
                video = info['entries'][0]
                audio_url = extract_direct_stream(video)
                title = video.get('title', query)
                if audio_url:
                    print(f"[LOG] Jumpa di YouTube: {title}")
                    return {
                        "status": "success",
                        "source": "youtube",
                        "title": title,
                        "url": audio_url
                    }
    except Exception as yt_err:
        print(f"[LOG] YouTube extractor: {yt_err}")

    raise HTTPException(status_code=404, detail="Lagu tidak ditemui")
