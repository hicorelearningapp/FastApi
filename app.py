from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from googleapiclient.discovery import build
import subprocess
import re
import os

app = FastAPI()

# ✅ Allow CORS (for React frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or ["http://localhost:3000"] for your frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔐 Hardcoded YouTube API key
YOUTUBE_API_KEY = "AIzaSyDOO3plPmJvlJ1e4wHkOde5sGsytuyK2No"

# 🔧 Utility to clean YouTube URL
def clean_youtube_url(url: str) -> str:
    return re.split(r"[&?]", url)[0]


# ✅ /api/info - Get video info from URL
@app.get("/api/info")
async def get_info(url: str = Query(...)):
    url = clean_youtube_url(url)
    try:
        result = subprocess.run(
            ["yt-dlp", "-j", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        import json
        info = json.loads(result.stdout)

        return {
            "title": info.get("title", ""),
            "thumbnail": info.get("thumbnail", ""),
            "size": "Unknown",
            "format": "MP4"
        }

    except subprocess.CalledProcessError as e:
        return JSONResponse(status_code=500, content={"error": "Failed to fetch video info"})


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
        ext = format.lower()
        title = "video"

        ydl_cmd = [
            "yt-dlp",
            "-f", "bestaudio/best" if format.upper() == "MP3" else "best",
            "-o", "-",  # output to stdout
            url
        ]

        if format.upper() == "MP3":
            ydl_cmd += [
                "--extract-audio",
                "--audio-format", "mp3"
            ]

        process = subprocess.Popen(
            ydl_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        headers = {
            "Content-Disposition": f'attachment; filename="{title}.{ext}"'
        }

        return StreamingResponse(
            process.stdout,
            media_type="application/octet-stream",
            headers=headers
        )

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
