from fastapi import FastAPI, HTTPException, Query
import yt_dlp
import requests
import re
import urllib.parse

app = FastAPI()

def clean_url(raw_text: str) -> str:
    match = re.search(r'https?://[a-zA-Z0-9./?=_%&\-_:]+', raw_text)
    return match.group(0) if match else raw_text.strip()

@app.get("/api/parse")
def parse_video(url: str = Query(..., description="目标视频链接或文案")):
    target_url = clean_url(url)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Referer': target_url
    }

    # ================= 1. 针对常规影视网站 (如各类在线影院) 进行网页嗅探 =================
    try:
        res = requests.get(target_url, headers=headers, timeout=8)
        html = res.text

        # 尝试从网页源码/播放器配置变量中提取 m3u8/mp4 地址
        m3u8_matches = re.findall(r'https?://[a-zA-Z0-9._\-/]+\.m3u8[a-zA-Z0-9._\-/?=&%]*', html)
        if m3u8_matches:
            real_m3u8 = urllib.parse.unquote(m3u8_matches[0])
            title_match = re.search(r'<title>(.*?)</title>', html)
            title = title_match.group(1).split('-')[0].strip() if title_match else "在线影视视频"
            return {
                "code": 200,
                "title": title,
                "audio_url": real_m3u8,
                "play_url": real_m3u8
            }
    except Exception:
        pass

    # ================= 2. 抖音 / TikTok 专属解析 =================
    if "douyin.com" in target_url or "iesdouyin.com" in target_url:
        try:
            m_headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X)'}
            r = requests.get(target_url, headers=m_headers, allow_redirects=True, timeout=10)
            vid_match = re.search(r'video/(\d+)', r.url) or re.search(r'/share/video/(\d+)', r.text)
            if vid_match:
                video_id = vid_match.group(1)
                direct_mp4 = f"https://aweme.snssdk.com/aweme/v1/play/?video_id={video_id}&ratio=1080p&line=0"
                return {
                    "code": 200,
                    "title": "抖音视频",
                    "audio_url": direct_mp4,
                    "play_url": direct_mp4
                }
        except Exception:
            pass

    # ================= 3. 通用与 YouTube 提取 =================
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            title = info.get('title', '已提取影视视频')
            audio_url = info.get('url')
            play_url = audio_url

            formats = info.get('formats', [])
            for f in formats:
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    play_url = f.get('url')
                    break

            if not audio_url:
                raise Exception("未能提取到有效流媒体直链")

            return {
                "code": 200,
                "title": title,
                "audio_url": audio_url,
                "play_url": play_url
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解析失败: {str(e)}")
