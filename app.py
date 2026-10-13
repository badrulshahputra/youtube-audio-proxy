from fastapi import FastAPI, HTTPException, Query
import yt_dlp

app = FastAPI(title="Music Audio Stream Proxy for ESP32")

# 1. Konfigurasi Utama: YouTube (Mobile Web + Android Client)
YOUTUBE_OPTS = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch1:',
    'extractor_args': {
        'youtube': {
            'player_client': ['mweb', 'android']
        }
    },
    'socket_timeout': 15,
}

# 2. Konfigurasi Sandaran: SoundCloud (Pantas & Bebas Sekatan IP Pusat Data)
SC_OPTS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'scsearch1:',
    'socket_timeout': 12,
}

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
                audio_url = video.get('url')
                title = video.get('title', query)

                if not audio_url and 'formats' in video:
                    for f in reversed(video['formats']):
                        if f.get('acodec') != 'none' and f.get('url'):
                            audio_url = f.get('url')
                            break

                if audio_url:
                    return {
                        "status": "success",
                        "source": "youtube",
                        "title": title,
                        "url": audio_url
                    }
    except Exception as yt_err:
        print(f"[LOG] YouTube extractor issue: {yt_err}. Mengaktifkan sandaran SoundCloud...")

    # --- Fasa 2: Sandaran Automatik ke SoundCloud jika YouTube menyekat ---
    try:
        with yt_dlp.YoutubeDL(SC_OPTS) as ydl:
            info = ydl.extract_info(f"scsearch1:{query}", download=False)
            if 'entries' in info and len(info['entries']) > 0:
                track = info['entries'][0]
                audio_url = track.get('url')
                title = track.get('title', query)

                if audio_url:
                    return {
                        "status": "success",
                        "source": "soundcloud",
                        "title": title,
                        "url": audio_url
                    }
    except Exception as sc_err:
        print(f"[LOG] SoundCloud extractor issue: {sc_err}")

    raise HTTPException(status_code=404, detail="Lagu tidak ditemui")
