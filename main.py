from fastapi import FastAPI, HTTPException, Query
import yt_dlp
import re

app = FastAPI()

def clean_url(raw_text: str) -> str:
    """提取纯净的 HTTP/HTTPS 网址，过滤中文和分享口令"""
    match = re.search(r'https?://[a-zA-Z0-9./?=_%&\-_:]+', raw_text)
    return match.group(0) if match else raw_text.strip()

@app.get("/api/parse")
def parse_video(url: str = Query(..., description="目标视频链接或文案")):
    target_url = clean_url(url)
    
    # 注入移动客户端伪装，绕过 YouTube 与各类平台的 Bot 检测
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'web']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            
            title = info.get('title', '已提取影视视频')
            audio_url = info.get('url')
            
            formats = info.get('formats', [])
            play_url = audio_url
            for f in formats:
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    play_url = f.get('url')
                    break

            if not audio_url:
                raise Exception("未能提取到有效音频流")

            return {
                "code": 200,
                "title": title,
                "audio_url": audio_url,
                "play_url": play_url
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解析失败: {str(e)}")
