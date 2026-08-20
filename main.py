from fastapi import FastAPI, HTTPException, Query
import yt_dlp

app = FastAPI()

@app.get("/api/parse")
def parse_video(url: str = Query(..., description="目标视频链接")):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', '已提取视频')
            audio_url = info.get('url')
            
            formats = info.get('formats', [])
            play_url = audio_url
            for f in formats:
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    play_url = f.get('url')
                    break

            return {
                "code": 200,
                "title": title,
                "audio_url": audio_url,
                "play_url": play_url
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解析失败: {str(e)}")
