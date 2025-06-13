from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from googleapiclient.discovery import build
from yt_dlp import YoutubeDL
import io
import re

app = FastAPI()

# ✅ Allow CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔐 Hardcoded YouTube API Key (replace with your key)
YOUTUBE_API_KEY = "AIzaSyXXXXXX_REPLACE_WITH_YOUR_KEY"

# 🔧 Clean URL
def clean_youtube_url(url: str) -> str:
    return re.split(r"[&?]", url)[0]

# ✅ /api/info - Get video info
@app.get("/api/info")
async def get_info(url: str = Query(...)):
    url = clean_youtube_url(url)
    try:
        with YoutubeDL({}) as ydl:
            info = ydl.extract_info(url, download=False)
            video_info = {
                "title": info.get("title", ""),
                "thumbnail": info.get("thumbnail", ""),
                "size": "Unknown",  # yt-dlp doesn’t provide size directly here
                "format": "MP4"
            }
            return video_info
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ✅ /api/search - Search YouTube
@app.get("/api/search")
async def youtube_search(content: str = Query(...), max_results: int = Query(5)):
    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(
            part="snippet",
            q=content,
            type="video",
            maxResults=max_results
        )
        response = request.execute()

        results = []
        for item in response.get("items", []):
            video_id = item["id"]["videoId"]
            results.append({
                "title": item["snippet"]["title"],
                "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                "videoId": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "size": "Unknown",
                "format": "MP4"
            })
        return results

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ✅ /api/download - Download video/audio
@app.get("/api/download")
async def download_video(url: str = Query(...), format: str = Query("MP4")):
    url = clean_youtube_url(url)
    try:
        ydl_opts = {
            'format': 'bestaudio/best' if format.upper() == 'MP3' else 'bestvideo+bestaudio/best',
            'quiet': True,
            'outtmpl': '-',  # prevent file write
            'noplaylist': True
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get("title", "video").replace(" ", "_").replace("/", "_")
            buffer = io.BytesIO()

            def stream():
                ydl.download([url])
                yield from buffer.getvalue()

            headers = {
                "Content-Disposition": f"attachment; filename={title}.{format.lower()}"
            }

            return StreamingResponse(stream(), headers=headers, media_type="application/octet-stream")

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
