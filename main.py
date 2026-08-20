from fastapi import FastAPI, HTTPException, Query
import yt_dlp
import requests
import re

app = FastAPI()

def clean_url(raw_text: str) -> str:
    match = re.search(r'https?://[a-zA-Z0-9./?=_%&\-_:]+', raw_text)
    return match.group(0) if match else raw_text.strip()

@app.get("/api/parse")
def parse_video(url: str = Query(..., description="目标视频链接或文案")):
    target_url = clean_url(url)
    
    # ================= 1. 抖音专属解析逻辑 =================
    if "douyin.com" in target_url or "iesdouyin.com" in target_url:
        try:
            # 请求重定向获取最终 URL
            headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15'
            }
            res = requests.get(target_url, headers=headers, allow_redirects=True, timeout=10)
            final_url = res.url
            html = res.text

            # 抓取纯数字 video id
            vid_match = re.search(r'video/(\d+)', final_url)
            if not vid_match:
                vid_match = re.search(r'/share/video/(\d+)', html)

            if vid_match:
                video_id = vid_match.group(1)
                # 字节直出无水印直链
                direct_mp4 = f"https://aweme.snssdk.com/aweme/v1/play/?video_id={video_id}&ratio=1080p&line=0"
                
                title = "抖音精选视频"
                title_match = re.search(r'<title>(.*?)</title>', html)
                if title_match:
                    title = title_match.group(1).replace("- 抖音", "").strip()

                return {
                    "code": 200,
                    "title": title,
                    "audio_url": direct_mp4,
                    "play_url": direct_mp4
                }
        except Exception as e:
            pass

    # ================= 2. YouTube 与其他通用平台 (移动客户端破盾) =================
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'extractor_args': {
            'youtube': {
                'player_client': ['mweb', 'android_creator', 'ios'],
                'player_skip': ['webpage', 'configs']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8'
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
