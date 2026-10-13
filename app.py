from fastapi import FastAPI, HTTPException, Query
import yt_dlp

app = FastAPI(title="YouTube Audio Stream Proxy for ESP32")

# Konfigurasi extractor_args Android/iOS untuk melepasi sekatan bot pelayan awan
YDL_OPTIONS = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch1:',
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'ios']
        }
    },
    'socket_timeout': 15,
}

@app.get("/")
def home():
    return {
        "status": "online",
        "service": "ESP32 YouTube Audio Proxy",
        "usage": "/stream?q=Tajuk+Lagu"
    }

@app.get("/stream")
def get_audio_stream(q: str = Query(..., description="Kata kunci carian lagu")):
    if not q or len(q.strip()) == 0:
        raise HTTPException(status_code=400, detail="Kata kunci carian diperlukan")

    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            search_query = f"ytsearch1:{q.strip()}"
            info = ydl.extract_info(search_query, download=False)

            if 'entries' in info and len(info['entries']) > 0:
                video = info['entries'][0]
                audio_url = video.get('url')
                title = video.get('title', q)

                # Jika direct url berada dalam senarai formats
                if not audio_url and 'formats' in video:
                    for f in reversed(video['formats']):
                        if f.get('acodec') != 'none' and f.get('url'):
                            audio_url = f.get('url')
                            break

                if audio_url:
                    return {
                        "status": "success",
                        "title": title,
                        "url": audio_url
                    }

            raise HTTPException(status_code=404, detail="Lagu tidak ditemui di YouTube")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
