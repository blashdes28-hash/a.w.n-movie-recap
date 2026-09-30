import re
import uuid
from pathlib import Path
from typing import Dict, Any
import yt_dlp
from app.video_renderer import FFMPEG_EXE

def download_audio_from_youtube_or_url(url: str, output_dir: Path) -> Dict[str, Any]:
    """Downloads audio from YouTube or any supported audio URL using yt-dlp."""
    output_dir.mkdir(parents=True, exist_ok=True)
    job_uid = uuid.uuid4().hex[:8]
    out_tmpl = str(output_dir / f"bgm_{job_uid}.%(ext)s")
    
    ydl_opts = {
        "ffmpeg_location": FFMPEG_EXE,
        "format": "bestaudio/best",
        "outtmpl": out_tmpl,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title") or "YouTube Music"
        duration = float(info.get("duration") or 0.0)
        
    mp3_filename = f"bgm_{job_uid}.mp3"
    mp3_path = output_dir / mp3_filename
    
    # If filename differs due to extension
    if not mp3_path.exists():
        candidates = list(output_dir.glob(f"bgm_{job_uid}.*"))
        if candidates:
            mp3_path = candidates[0]
            mp3_filename = mp3_path.name

    if not mp3_path.exists():
        raise RuntimeError("Failed to extract audio from link.")
        
    return {
        "success": True,
        "title": title,
        "filename": mp3_filename,
        "url": f"/media/uploads/{mp3_filename}",
        "duration": duration,
        "size_mb": round(mp3_path.stat().st_size / (1024 * 1024), 2)
    }
