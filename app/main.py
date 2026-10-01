import os
import shutil
import uuid
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import (
    BASE_DIR, UPLOADS_DIR, OUTPUT_DIR, DATA_DIR,
    load_config, save_config
)
from app.tts_engine import (
    VOICES, generate_narration, generate_quick_sample
)
from app.ai_assistant import (
    process_assistant_chat, translate_to_burmese_recap
)
from app.video_renderer import (
    FFMPEG_EXE, FONTS_DIR, get_available_fonts,
    start_render_job, get_job_status, burn_subtitles_to_video
)
from app.telegram_bot import (
    test_telegram_connection, send_recap_to_telegram
)
from app.project_manager import (
    list_projects, get_project, create_project, update_project, delete_project
)
from app.transcriber import (
    transcribe_and_translate_video, translate_srt_content, polish_segments_to_natural_burmese
)
from app.rednote_downloader import download_rednote_hd_video, create_muted_video
from app.license_manager import (
    verify_and_activate_license, check_device_license,
    generate_new_licenses, list_all_licenses,
    reset_device_binding, revoke_license_key, delete_license_key,
    verify_admin_password, set_admin_password, get_admin_password
)
import requests


# Ensure necessary directories
for d in [UPLOADS_DIR, OUTPUT_DIR, DATA_DIR, BASE_DIR / "static"]:
    d.mkdir(parents=True, exist_ok=True)

# In-memory job tracker for async burn jobs
BURN_JOBS: Dict[str, Any] = {}
TRANSCRIBE_JOBS: Dict[str, Any] = {}

app = FastAPI(title="A.W.N Movie Recap Studio", version="2.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static and output files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/media/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output_media")
app.mount("/media/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads_media")
(BASE_DIR / "data" / "bgm").mkdir(parents=True, exist_ok=True)
app.mount("/media/bgm", StaticFiles(directory=str(BASE_DIR / "data" / "bgm")), name="bgm_media")
app.mount("/fonts", StaticFiles(directory=str(FONTS_DIR)), name="fonts")

# --- Pydantic Request Models ---
class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "my-MM-ThihaNeural"
    rate: Optional[str] = "+0%"
    pitch: Optional[str] = "+0Hz"

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []
    model: Optional[str] = "gemini-2.5-flash"

class TranslateRequest(BaseModel):
    text: str

class LicenseActivateRequest(BaseModel):
    license_key: str
    device_id: str
    device_info: Optional[str] = None

class LicenseCheckRequest(BaseModel):
    license_key: str
    device_id: str

class LicenseGenerateRequest(BaseModel):
    plan: Optional[str] = "Lifetime VIP"
    count: Optional[int] = 1
    expires_days: Optional[int] = None
    notes: Optional[str] = ""

class LicenseKeyActionRequest(BaseModel):
    license_key: str

class AdminLoginRequest(BaseModel):
    password: str

class AdminChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class RednoteDownloadRequest(BaseModel):
    url: str

class YouTubeBgmRequest(BaseModel):
    url: str

class CaptionGenerateRequest(BaseModel):
    title: Optional[str] = None
    segments: Optional[List[Dict[str, Any]]] = None

class BurnVideoRequest(BaseModel):
    video_file: str
    segments: Optional[List[Dict[str, Any]]] = None
    sub_mode: Optional[str] = "my" # "my", "my_en", "my_zh", "en"
    sub_type: Optional[str] = None # backward compatibility
    font_name: Optional[str] = "Pyidaungsu"
    font_size: Optional[int] = 34
    sub_color: Optional[str] = "#ffffff"
    margin_v: Optional[int] = 50
    style_type: Optional[str] = "box" # "box", "outline", "banner", "yellow"
    position_type: Optional[str] = "bottom" # "bottom", "middle", "top", "custom"
    y_percent: Optional[float] = 0.86
    aspect_ratio: Optional[str] = "original" # "original", "16:9", "9:16", "1:1"
    resize_mode: Optional[str] = "fit_blur" # "fit_blur", "crop"
    blur_enabled: Optional[bool] = False
    blur_y_percent: Optional[float] = 0.56
    blur_height_percent: Optional[float] = 0.08
    logo_file: Optional[str] = None
    logo_pos: Optional[str] = "top-right"
    logo_size_percent: Optional[float] = 0.18
    logo_opacity: Optional[float] = 0.85
    orig_audio_volume: Optional[float] = 1.0 # 0.0 to 1.0 (0.0 = Mute)
    bgm_file: Optional[str] = None
    bgm_volume: Optional[float] = 0.35
    bgm_loop: Optional[bool] = True
    export_quality: Optional[str] = "very_high" # "very_high", "high", "fast"

class TranscribeExistingVideoRequest(BaseModel):
    video_file: str
    source_lang: Optional[str] = "zh"
    whisper_model: Optional[str] = "base"
    gemini_api_key: Optional[str] = None

class RenderRequest(BaseModel):
    project_id: str
    source_video_file: Optional[str] = None
    watermark_text: Optional[str] = "@actrecap"
    watermark_pos: Optional[str] = "top-right"
    watermark_opacity: Optional[float] = 0.8
    title_text: Optional[str] = None
    sub_color: Optional[str] = "&H00FFFFFF"
    sub_font_size: Optional[int] = 34
    font_name: Optional[str] = "Pyidaungsu"
    anti_copyright: Optional[bool] = True
    speed_factor: Optional[float] = 1.05
    mirror_flip: Optional[bool] = False
    bgm_enabled: Optional[bool] = True
    bgm_volume: Optional[float] = 0.12
    aspect_ratio: Optional[str] = "16:9"
    style_type: Optional[str] = "box"
    position_type: Optional[str] = "bottom"
    y_percent: Optional[float] = 0.86

class TelegramTestRequest(BaseModel):
    bot_token: str
    chat_id: Optional[str] = None

# --- API Endpoints ---

@app.get("/")
def serve_index():
    return FileResponse(str(BASE_DIR / "static" / "index.html"))

@app.get("/api/status")
def get_system_status():
    config = load_config()
    return {
        "status": "online",
        "ffmpeg": {
            "available": bool(FFMPEG_EXE and Path(FFMPEG_EXE).exists()),
            "path": FFMPEG_EXE
        },
        "gemini_api_configured": bool(config.get("gemini_api_key")),
        "openrouter_configured": bool(config.get("openrouter_api_key")),
        "telegram_configured": bool(config.get("telegram_bot_token") and config.get("telegram_chat_id")),
        "default_voice": config.get("default_voice", "my-MM-ThihaNeural")
    }

@app.get("/api/settings")
def get_settings():
    return load_config()

@app.post("/api/settings")
def update_settings(data: Dict[str, Any]):
    return save_config(data)

@app.post("/api/telegram/test")
def test_telegram(req: TelegramTestRequest):
    return test_telegram_connection(req.bot_token, req.chat_id)

@app.get("/api/tts/voices")
def get_voices():
    return VOICES

@app.post("/api/tts/preview")
async def preview_voice(req: TTSRequest):
    sample_text = req.text if req.text else "မင်္ဂလာပါ၊ ACT RECAP ရုပ်ရှင်ဇာတ်လမ်းပြော စနစ်မှ ကြိုဆိုပါတယ်။"
    voice = req.voice or "my-MM-ThihaNeural"
    try:
        audio_bytes = await generate_quick_sample(sample_text, voice)
        filename = f"preview_{uuid.uuid4().hex[:8]}.mp3"
        out_file = OUTPUT_DIR / filename
        with open(out_file, "wb") as f:
            f.write(audio_bytes)
        return {"audio_url": f"/media/output/{filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tts/generate")
async def generate_tts(req: TTSRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    try:
        result = await generate_narration(
            text=req.text,
            voice=req.voice or "my-MM-ThihaNeural",
            rate=req.rate or "+0%",
            pitch=req.pitch or "+0Hz",
            output_dir=OUTPUT_DIR
        )
        return {
            "duration": result["total_duration"],
            "duration_str": result["duration_formatted"],
            "subtitles": result["subtitles"],
            "audio_file": result["audio_file"],
            "audio_url": f"/media/output/{result['audio_file']}",
            "srt_file": result["srt_file"],
            "srt_url": f"/media/output/{result['srt_file']}",
            "vtt_file": result["vtt_file"],
            "vtt_url": f"/media/output/{result['vtt_file']}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/script/chat")
def chat_script(req: ChatRequest):
    config = load_config()
    api_key = config.get("gemini_api_key")
    openrouter_key = config.get("openrouter_api_key")
    model = req.model or config.get("gemini_model", "gemini-2.5-flash")
    
    reply = process_assistant_chat(
        user_message=req.message,
        history=req.history,
        api_key=api_key,
        model=model,
        openrouter_key=openrouter_key
    )
    return reply

@app.post("/api/translate")
def translate_text(req: TranslateRequest):
    config = load_config()
    api_key = config.get("gemini_api_key")
    openrouter_key = config.get("openrouter_api_key")
    raw_text = req.text.strip()
    # Check if input text is SRT format (with timestamp tracking)
    if "-->" in raw_text and re.search(r'\d{1,2}:\d{2}:\d{2}[,\.]\d{3}', raw_text):
        try:
            res = translate_srt_content(raw_text, OUTPUT_DIR, gemini_key=api_key, openrouter_key=openrouter_key)
            burmese_srt_path = OUTPUT_DIR / res["burmese_srt"]
            translated_content = burmese_srt_path.read_text(encoding="utf-8") if burmese_srt_path.exists() else ""
            return {
                "is_srt": True,
                "translated": translated_content,
                "segments": res.get("segments", []),
                "burmese_srt": res.get("burmese_srt"),
                "burmese_srt_url": res.get("burmese_srt_url"),
                "engine": "Gemini Timeline Engine" if api_key else "Offline Drama Engine"
            }
        except Exception as e:
            print("SRT parse failed, falling back to text translation:", e)
    return translate_to_burmese_recap(req.text, api_key=api_key, openrouter_key=openrouter_key)

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    target = UPLOADS_DIR / filename
    with open(target, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {
        "filename": filename,
        "url": f"/media/uploads/{filename}",
        "size": target.stat().st_size
    }

@app.post("/api/rednote/download")
def download_rednote_video_endpoint(req: RednoteDownloadRequest):
    try:
        if not req.url or not req.url.strip():
            raise HTTPException(status_code=400, detail="URL or share text is required.")
        result = download_rednote_hd_video(req.url.strip(), UPLOADS_DIR)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.post("/api/video/mute")
def create_muted_video_endpoint(req: Dict[str, Any]):
    """Strips audio from video to produce a silent, copyright-safe MP4 in seconds."""
    try:
        video_filename = req.get("video_file")
        if not video_filename:
            raise HTTPException(status_code=400, detail="video_file is required")
        src_path = UPLOADS_DIR / video_filename
        if not src_path.exists():
            raise HTTPException(status_code=404, detail="Video file not found")
        stem = src_path.stem
        muted_filename = f"{stem}_muted.mp4"
        muted_path = UPLOADS_DIR / muted_filename
        if not muted_path.exists():
            ok = create_muted_video(src_path, muted_path)
            if not ok:
                raise HTTPException(status_code=500, detail="Failed to create muted video")
        return {
            "success": True,
            "video_file": muted_filename,
            "video_url": f"/media/uploads/{muted_filename}",
            "file_size_mb": round(muted_path.stat().st_size / (1024 * 1024), 2)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/logo/upload")
async def upload_logo_file(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        raise HTTPException(status_code=400, detail="Only PNG, JPG, or WEBP image formats are supported for channel logos.")
    clean_name = f"logo_{uuid.uuid4().hex[:8]}{ext}"
    target = UPLOADS_DIR / clean_name
    with open(target, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {
        "filename": clean_name,
        "url": f"/media/uploads/{clean_name}",
        "size": target.stat().st_size
    }

# --- Background Music (BGM) & Audio Anti-Copyright Endpoints ---

@app.post("/api/audio/youtube-bgm")
def download_youtube_bgm_endpoint(req: YouTubeBgmRequest):
    try:
        if not req.url or not req.url.strip():
            raise HTTPException(status_code=400, detail="YouTube URL is required")
        from app.youtube_audio import download_audio_from_youtube_or_url
        res = download_audio_from_youtube_or_url(req.url.strip(), UPLOADS_DIR)
        return res
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"YouTube audio extraction failed: {str(e)}")

@app.post("/api/audio/upload-bgm")
async def upload_bgm_endpoint(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in [".mp3", ".wav", ".m4a", ".aac", ".ogg"]:
        raise HTTPException(status_code=400, detail="Only MP3, WAV, M4A, AAC, or OGG audio files are supported.")
    clean_name = f"bgm_{uuid.uuid4().hex[:8]}{ext}"
    target = UPLOADS_DIR / clean_name
    with open(target, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {
        "filename": clean_name,
        "title": file.filename,
        "url": f"/media/uploads/{clean_name}",
        "size_mb": round(target.stat().st_size / (1024 * 1024), 2)
    }

@app.get("/api/audio/presets")
def get_bgm_presets():
    presets = [
        {"id": "bgm_cinematic_drama.mp3", "name": "🎬 Dramatic Cinematic (သည်းထိတ်ရင်ဖို)", "category": "Dramatic"},
        {"id": "bgm_mystery_suspense.mp3", "name": "🕵️ Mystery Suspense (ဆန်းကြယ် လျှို့ဝှက်)", "category": "Suspense"},
        {"id": "bgm_emotional_piano.mp3", "name": "🎹 Emotional Piano (ရင်နင့်ဖွယ် ဒရာမာ)", "category": "Emotional"},
        {"id": "bgm_epic_action.mp3", "name": "⚔️ Epic Action / Xianxia (သိုင်းလောက အက်ရှင်)", "category": "Action"}
    ]
    results = []
    for p in presets:
        p["url"] = f"/media/bgm/{p['id']}"
        results.append(p)
    return results

@app.post("/api/caption/generate")
def generate_caption_endpoint(req: CaptionGenerateRequest):
    try:
        config = load_config()
        gemini_key = config.get("gemini_api_key")
        from app.caption_generator import generate_viral_caption_and_hashtags
        return generate_viral_caption_and_hashtags(title=req.title, segments=req.segments, gemini_key=gemini_key)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Caption generation failed: {str(e)}")

# --- Video to Burmese Timeline Transcription & Translation ---

@app.post("/api/transcribe/video")
async def transcribe_video_endpoint(
    file: UploadFile = File(...),
    source_lang: str = Form("zh"),
    whisper_model: str = Form("base"),
    gemini_api_key: str = Form(None)
):
    try:
        # Save uploaded video
        ext = Path(file.filename).suffix or ".mp4"
        saved_filename = f"video_{uuid.uuid4().hex[:8]}{ext}"
        saved_path = UPLOADS_DIR / saved_filename
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        config = load_config()
        # Use provided key, or fallback to config
        active_gemini_key = gemini_api_key or config.get("gemini_api_key")
        openrouter_key = config.get("openrouter_api_key")

        result = transcribe_and_translate_video(
            video_path=saved_path,
            output_dir=OUTPUT_DIR,
            source_lang=source_lang,
            gemini_key=active_gemini_key,
            openrouter_key=openrouter_key,
            whisper_model_size=whisper_model
        )
        result["video_file"] = saved_filename
        result["video_url"] = f"/media/uploads/{saved_filename}"
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/transcribe/existing-video")
def transcribe_existing_video_endpoint(req: TranscribeExistingVideoRequest):
    try:
        video_path = UPLOADS_DIR / req.video_file
        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Video file not found in uploads")

        config = load_config()
        active_gemini_key = req.gemini_api_key or config.get("gemini_api_key")
        openrouter_key = config.get("openrouter_api_key")

        result = transcribe_and_translate_video(
            video_path=video_path,
            output_dir=OUTPUT_DIR,
            source_lang=req.source_lang or "zh",
            gemini_key=active_gemini_key,
            openrouter_key=openrouter_key,
            whisper_model_size=req.whisper_model or "base"
        )
        result["video_file"] = req.video_file
        result["video_url"] = f"/media/uploads/{req.video_file}"
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transcribe/srt")
async def transcribe_srt_endpoint(file: UploadFile = File(...)):
    try:
        content_bytes = await file.read()
        srt_text = content_bytes.decode("utf-8", errors="replace")
        config = load_config()
        gemini_key = config.get("gemini_api_key")
        openrouter_key = config.get("openrouter_api_key")

        result = translate_srt_content(
            srt_content=srt_text,
            output_dir=OUTPUT_DIR,
            gemini_key=gemini_key,
            openrouter_key=openrouter_key
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/transcribe/video-async")
async def transcribe_video_async_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_lang: str = Form("zh"),
    whisper_model: str = Form("base"),
    gemini_api_key: str = Form(None)
):
    try:
        ext = Path(file.filename).suffix or ".mp4"
        saved_filename = f"video_{uuid.uuid4().hex[:8]}{ext}"
        saved_path = UPLOADS_DIR / saved_filename
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        config = load_config()
        active_gemini_key = gemini_api_key or config.get("gemini_api_key")
        openrouter_key = config.get("openrouter_api_key")
        
        job_uid = uuid.uuid4().hex[:10]
        TRANSCRIBE_JOBS[job_uid] = {"status": "processing", "result": None, "error": None}

        def run_transcribe():
            try:
                result = transcribe_and_translate_video(
                    video_path=saved_path,
                    output_dir=OUTPUT_DIR,
                    source_lang=source_lang,
                    gemini_key=active_gemini_key,
                    openrouter_key=openrouter_key,
                    whisper_model_size=whisper_model
                )
                result["video_file"] = saved_filename
                result["video_url"] = f"/media/uploads/{saved_filename}"
                TRANSCRIBE_JOBS[job_uid]["status"] = "done"
                TRANSCRIBE_JOBS[job_uid]["result"] = result
            except Exception as e:
                import traceback; traceback.print_exc()
                TRANSCRIBE_JOBS[job_uid]["status"] = "error"
                TRANSCRIBE_JOBS[job_uid]["error"] = str(e)

        background_tasks.add_task(run_transcribe)
        return {"job_id": job_uid, "status": "processing"}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/transcribe/existing-video-async")
def transcribe_existing_video_async_endpoint(
    req: TranscribeExistingVideoRequest,
    background_tasks: BackgroundTasks
):
    try:
        video_path = UPLOADS_DIR / req.video_file
        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Video file not found in uploads")

        config = load_config()
        active_gemini_key = req.gemini_api_key or config.get("gemini_api_key")
        openrouter_key = config.get("openrouter_api_key")
        
        job_uid = uuid.uuid4().hex[:10]
        TRANSCRIBE_JOBS[job_uid] = {"status": "processing", "result": None, "error": None}

        def run_transcribe():
            try:
                result = transcribe_and_translate_video(
                    video_path=video_path,
                    output_dir=OUTPUT_DIR,
                    source_lang=req.source_lang or "zh",
                    gemini_key=active_gemini_key,
                    openrouter_key=openrouter_key,
                    whisper_model_size=req.whisper_model or "base"
                )
                result["video_file"] = req.video_file
                result["video_url"] = f"/media/uploads/{req.video_file}"
                TRANSCRIBE_JOBS[job_uid]["status"] = "done"
                TRANSCRIBE_JOBS[job_uid]["result"] = result
            except Exception as e:
                import traceback; traceback.print_exc()
                TRANSCRIBE_JOBS[job_uid]["status"] = "error"
                TRANSCRIBE_JOBS[job_uid]["error"] = str(e)

        background_tasks.add_task(run_transcribe)
        return {"job_id": job_uid, "status": "processing"}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/transcribe/status/{job_id}")
def transcribe_status_endpoint(job_id: str):
    job = TRANSCRIBE_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.post("/api/transcribe/export")
def export_custom_srt_endpoint(data: Dict[str, Any]):
    segments = data.get("segments", [])
    job_uid = uuid.uuid4().hex[:10]
    burmese_srt_file = f"burmese_sub_{job_uid}.srt"
    bilingual_srt_file = f"bilingual_sub_{job_uid}.srt"

    burmese_lines = []
    bilingual_lines = []

    for s in segments:
        header = f"{s.get('start_str')} --> {s.get('end_str')}"
        second_line = s.get('en_text') or s.get('zh_text', '')
        bilingual_lines.append(f"{s.get('index', 1)}\n{header}\n{s.get('my_text', '')}\n{second_line}\n")

    with open(OUTPUT_DIR / burmese_srt_file, "w", encoding="utf-8") as f:
        f.write("\n".join(burmese_lines))
    with open(OUTPUT_DIR / bilingual_srt_file, "w", encoding="utf-8") as f:
        f.write("\n".join(bilingual_lines))

    return {
        "burmese_srt_file": burmese_srt_file,
        "bilingual_srt_file": bilingual_srt_file,
        "burmese_srt_url": f"/media/output/{burmese_srt_file}",
        "bilingual_srt_url": f"/media/output/{bilingual_srt_file}"
    }

@app.post("/api/transcribe/polish")
def polish_segments_endpoint(data: Dict[str, Any]):
    segments = data.get("segments", [])
    config = load_config()
    gemini_key = config.get("gemini_api_key")
    openrouter_key = config.get("openrouter_api_key")
    polished = polish_segments_to_natural_burmese(segments, gemini_key=gemini_key, openrouter_key=openrouter_key)
    return {"segments": polished}

@app.get("/api/fonts")
def list_fonts():
    return get_available_fonts()

@app.post("/api/fonts/upload")
async def upload_custom_font(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in [".ttf", ".otf"]:
        raise HTTPException(status_code=400, detail="Only .ttf or .otf font files are supported.")
    
    clean_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', file.filename)
    target = FONTS_DIR / clean_name
    with open(target, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {
        "message": "Font uploaded successfully",
        "filename": clean_name,
        "fonts": get_available_fonts()
    }

@app.post("/api/transcribe/burn-video")
async def burn_video_endpoint(req: BurnVideoRequest, background_tasks: BackgroundTasks):
    """Start subtitle burn as background job. Returns job_id immediately."""
    try:
        video_filename = req.video_file
        video_path = UPLOADS_DIR / video_filename
        if not video_path.exists():
            videos = sorted([f for f in UPLOADS_DIR.glob("video_*.mp4")], key=lambda p: p.stat().st_mtime, reverse=True)
            if videos:
                video_path = videos[0]
            else:
                raise HTTPException(status_code=404, detail="Source video not found in uploads")

        job_uid = uuid.uuid4().hex[:10]
        out_filename = f"subtitled_{job_uid}.mp4"
        out_path = OUTPUT_DIR / out_filename

        # Store job state
        BURN_JOBS[job_uid] = {"status": "queued", "progress": 0, "message": "ပြင်ဆင်နေသည်...", "video_url": None, "error": None}

        # Launch in background thread
        def run_burn():
            try:
                BURN_JOBS[job_uid]["status"] = "running"
                BURN_JOBS[job_uid]["progress"] = 5
                BURN_JOBS[job_uid]["message"] = "subtitle frames ရေးဆွဲနေသည်..."

                sub_mode = req.sub_mode or ("my_en" if req.sub_type == "bilingual" else "my")
                burn_subtitles_to_video(
                    video_path=video_path,
                    output_path=out_path,
                    segments=req.segments,
                    sub_mode=sub_mode,
                    font_name=req.font_name or "Pyidaungsu",
                    sub_font_size=req.font_size or 34,
                    sub_color=req.sub_color or "#ffffff",
                    margin_v=req.margin_v or 50,
                    style_type=req.style_type or "box",
                    position_type=req.position_type or "bottom",
                    y_percent=req.y_percent if req.y_percent is not None else 0.86,
                    aspect_ratio=req.aspect_ratio or "original",
                    resize_mode=req.resize_mode or "fit_blur",
                    blur_enabled=bool(req.blur_enabled),
                    blur_y_percent=float(req.blur_y_percent) if req.blur_y_percent is not None else 0.56,
                    blur_height_percent=float(req.blur_height_percent) if req.blur_height_percent is not None else 0.08,
                    logo_file=req.logo_file,
                    logo_pos=req.logo_pos or "top-right",
                    logo_size_percent=float(req.logo_size_percent) if req.logo_size_percent is not None else 0.18,
                    logo_opacity=float(req.logo_opacity) if req.logo_opacity is not None else 0.85,
                    orig_audio_volume=float(req.orig_audio_volume) if req.orig_audio_volume is not None else 1.0,
                    bgm_file=req.bgm_file,
                    bgm_volume=float(req.bgm_volume) if req.bgm_volume is not None else 0.35,
                    bgm_loop=bool(req.bgm_loop) if req.bgm_loop is not None else True,
                    export_quality=req.export_quality or "very_high",
                    progress_callback=lambda pct: BURN_JOBS[job_uid].update({"progress": pct, "message": f"Rendering ({pct}%)"})
                )
                BURN_JOBS[job_uid]["status"] = "done"
                BURN_JOBS[job_uid]["progress"] = 100
                BURN_JOBS[job_uid]["message"] = "ဒေါင်းလုဒ် အဆင်သင့်!"
                BURN_JOBS[job_uid]["video_url"] = f"/media/output/{out_filename}"
                BURN_JOBS[job_uid]["video_file"] = out_filename
                BURN_JOBS[job_uid]["file_size_mb"] = round(out_path.stat().st_size / (1024*1024), 2) if out_path.exists() else 0
            except Exception as e:
                import traceback; traceback.print_exc()
                BURN_JOBS[job_uid]["status"] = "error"
                BURN_JOBS[job_uid]["progress"] = 0
                BURN_JOBS[job_uid]["error"] = str(e)
                BURN_JOBS[job_uid]["message"] = f"Error: {str(e)[:200]}"

        background_tasks.add_task(run_burn)
        return {"job_id": job_uid, "status": "queued"}
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/transcribe/burn-status/{job_id}")
def burn_status_endpoint(job_id: str):
    """Poll burn job status and progress."""
    job = BURN_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

# --- Secret Admin Backend & License Control (1 Key = 1 Device) ---

def _require_admin_auth(x_admin_password: Optional[str] = Header(None)):
    if not x_admin_password or not verify_admin_password(x_admin_password):
        raise HTTPException(status_code=401, detail="Admin authorization required (Invalid admin credentials)")

@app.get("/admin")
def serve_secret_admin_page():
    return FileResponse(BASE_DIR / "static" / "admin.html")

@app.post("/api/admin/login")
def admin_login_endpoint(req: AdminLoginRequest):
    if not verify_admin_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid admin password (စကားဝှက် မှားယွင်းနေပါသည်)")
    return {"success": True, "token": req.password}

@app.post("/api/admin/change-password")
def admin_change_password_endpoint(req: AdminChangePasswordRequest, x_admin_password: Optional[str] = Header(None)):
    _require_admin_auth(x_admin_password or req.old_password)
    ok = set_admin_password(req.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail="Password cannot be empty")
    return {"success": True, "message": "Admin password changed successfully"}

@app.post("/api/license/activate")
def activate_license_endpoint(req: LicenseActivateRequest):
    res = verify_and_activate_license(req.license_key, req.device_id, req.device_info)
    if not res.get("valid"):
        raise HTTPException(status_code=400, detail=res.get("error", "Activation failed"))
    return res

@app.post("/api/license/check")
def check_license_endpoint(req: LicenseCheckRequest):
    res = check_device_license(req.license_key, req.device_id)
    return res

@app.post("/api/license/generate")
def generate_license_endpoint(req: LicenseGenerateRequest, x_admin_password: Optional[str] = Header(None)):
    _require_admin_auth(x_admin_password)
    new_keys = generate_new_licenses(
        plan=req.plan or "Lifetime VIP",
        count=req.count or 1,
        expires_days=req.expires_days,
        notes=req.notes or ""
    )
    return {"success": True, "created": new_keys}

@app.get("/api/license/list")
def list_licenses_endpoint(x_admin_password: Optional[str] = Header(None)):
    _require_admin_auth(x_admin_password)
    licenses = list_all_licenses()
    return {"licenses": licenses, "count": len(licenses)}

@app.post("/api/license/reset-device")
def reset_device_endpoint(req: LicenseKeyActionRequest, x_admin_password: Optional[str] = Header(None)):
    _require_admin_auth(x_admin_password)
    ok = reset_device_binding(req.license_key)
    if not ok:
        raise HTTPException(status_code=404, detail="License key not found")
    return {"success": True, "message": "Device binding reset. Key can now be activated on another device."}

@app.post("/api/license/revoke")
def revoke_license_endpoint(req: LicenseKeyActionRequest, x_admin_password: Optional[str] = Header(None)):
    _require_admin_auth(x_admin_password)
    ok = revoke_license_key(req.license_key)
    if not ok:
        raise HTTPException(status_code=404, detail="License key not found")
    return {"success": True, "message": "License revoked"}

@app.post("/api/license/delete")
def delete_license_endpoint(req: LicenseKeyActionRequest, x_admin_password: Optional[str] = Header(None)):
    _require_admin_auth(x_admin_password)
    ok = delete_license_key(req.license_key)
    if not ok:
        raise HTTPException(status_code=404, detail="License key not found")
    return {"success": True, "message": "License deleted"}

@app.post("/api/gemini/test")
def test_gemini_endpoint(data: Dict[str, Any] = None):
    data = data or {}
    # Accept both field names from frontend
    key = data.get("gemini_api_key") or data.get("api_key")
    if not key or not key.strip():
        config = load_config()
        key = config.get("gemini_api_key")
    if not key or not key.strip():
        return {"success": False, "status": "error", "error": "No Gemini API Key provided or configured."}

    candidate_models = ["gemini-1.5-flash", "gemini-flash-lite-latest", "gemini-1.5-flash-latest"]
    successful_model = None
    last_error = ""
    for model in candidate_models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key.strip()}"
            payload = {
                "contents": [{"parts": [{"text": "Hello"}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 20}
            }
            res = requests.post(url, json=payload, timeout=12)
            if res.status_code == 200:
                successful_model = model
                break
            else:
                last_error = res.text[:200]
        except Exception as e:
            last_error = str(e)

    if successful_model:
        return {
            "success": True,
            "status": "ok",
            "model": successful_model,
            "message": f"Gemini API အောင်မြင်စွာ ချိတ်ဆက်ပြီးပါပြီ! Model: {successful_model}"
        }
    return {
        "success": False,
        "status": "error",
        "error": f"Failed to connect to Google Gemini API. Please check your API key or quota. ({last_error[:100]})"
    }

@app.post("/api/gemini/save-key")
def save_gemini_key(data: Dict[str, Any]):
    """Saves the user's Gemini API key to server config (persisted in config.json)."""
    key = (data.get("gemini_api_key") or data.get("api_key") or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="API key is required")
    save_config({"gemini_api_key": key})
    return {"success": True, "message": "Gemini API Key saved successfully on server."}

# --- Projects CRUD ---

@app.get("/api/projects")
def get_all_projects():
    return list_projects()

@app.post("/api/projects")
def add_project(data: Dict[str, Any]):
    return create_project(data)

@app.get("/api/projects/{project_id}")
def get_one_project(project_id: str):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p

@app.put("/api/projects/{project_id}")
def edit_project(project_id: str, updates: Dict[str, Any]):
    p = update_project(project_id, updates)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p

@app.delete("/api/projects/{project_id}")
def remove_project(project_id: str):
    success = delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True}

# --- Video Rendering & Telegram Delivery ---

@app.post("/api/projects/{project_id}/render")
async def render_project(project_id: str, req: RenderRequest, background_tasks: BackgroundTasks):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
        
    config = load_config()
    
    # Check if narration audio exists or needs to be generated
    audio_file = p.get("audio_file")
    srt_file = p.get("srt_file")
    
    if not audio_file or not (OUTPUT_DIR / audio_file).exists():
        # Generate narration first if script is present
        script = p.get("script", "")
        if not script.strip():
            raise HTTPException(status_code=400, detail="Cannot render: Project script is empty.")
        tts_res = await generate_narration(
            text=script,
            voice=p.get("voice", "my-MM-ThihaNeural"),
            rate=p.get("rate", "+0%"),
            pitch=p.get("pitch", "+0Hz"),
            output_dir=OUTPUT_DIR
        )
        audio_file = tts_res["audio_file"]
        srt_file = tts_res["srt_file"]
        update_project(project_id, {
            "audio_file": audio_file,
            "srt_file": srt_file,
            "vtt_file": tts_res["vtt_file"],
            "duration": tts_res["total_duration"],
            "duration_str": tts_res["duration_formatted"]
        })

    narration_path = OUTPUT_DIR / audio_file
    srt_path = (OUTPUT_DIR / srt_file) if srt_file else None
    
    source_video_path = None
    vid_file = req.source_video_file or p.get("source_video_file")
    if vid_file:
        cand = UPLOADS_DIR / vid_file
        if cand.exists():
            source_video_path = cand
            update_project(project_id, {"source_video_file": vid_file})

    # Start async render job
    job_id = start_render_job(
        output_dir=OUTPUT_DIR,
        narration_audio_path=narration_path,
        srt_path=srt_path,
        source_video_path=source_video_path,
        watermark_text=req.watermark_text or config.get("watermark_text", "@actrecap"),
        watermark_pos=req.watermark_pos or config.get("watermark_position", "top-right"),
        watermark_opacity=req.watermark_opacity or config.get("watermark_opacity", 0.8),
        title_text=req.title_text or p.get("movie_name") or p.get("title"),
        sub_color=req.sub_color or config.get("subtitle_color", "&H00FFFFFF"),
        sub_font_size=req.sub_font_size or config.get("subtitle_font_size", 24),
        font_name=req.font_name or "Pyidaungsu",
        anti_copyright=req.anti_copyright if req.anti_copyright is not None else True,
        speed_factor=req.speed_factor or 1.05,
        mirror_flip=req.mirror_flip or False,
        bgm_enabled=req.bgm_enabled if req.bgm_enabled is not None else True,
        bgm_volume=req.bgm_volume or 0.12,
        aspect_ratio=req.aspect_ratio or config.get("default_aspect_ratio", "16:9"),
        style_type=req.style_type or "box",
        position_type=req.position_type or "bottom",
        y_percent=req.y_percent if req.y_percent is not None else 0.86
    )
    
    # Save active job_id into project
    update_project(project_id, {
        "status": "rendering",
        "last_render_job_id": job_id
    })

    return {
        "job_id": job_id,
        "message": "Render job queued successfully."
    }

@app.get("/api/render/status/{job_id}")
def check_render_status(job_id: str):
    status = get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # If completed, check if we need to auto-send to Telegram
    if status.get("status") == "completed" and status.get("output_video"):
        output_video = status["output_video"]
        # Look up project that had this job_id
        for p in list_projects():
            if p.get("last_render_job_id") == job_id and p.get("status") != "rendered":
                update_project(p["id"], {
                    "status": "rendered",
                    "video_file": output_video,
                    "video_url": f"/media/output/{output_video}"
                })
                # Auto send to Telegram if configured
                config = load_config()
                if config.get("telegram_auto_send") and config.get("telegram_bot_token") and config.get("telegram_chat_id"):
                    v_path = OUTPUT_DIR / output_video
                    a_path = (OUTPUT_DIR / p["audio_file"]) if p.get("audio_file") else None
                    send_recap_to_telegram(
                        bot_token=config["telegram_bot_token"],
                        chat_id=config["telegram_chat_id"],
                        project_title=p.get("title", "Movie Recap"),
                        video_path=v_path,
                        audio_path=a_path,
                        duration_str=p.get("duration_str", "00:00")
                    )
                break
                
    return status

@app.post("/api/projects/{project_id}/send-telegram")
def push_to_telegram(project_id: str):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
        
    config = load_config()
    token = config.get("telegram_bot_token")
    chat_id = config.get("telegram_chat_id")
    
    if not token or not chat_id:
        raise HTTPException(status_code=400, detail="Telegram bot token or chat ID is not configured. Please configure in Settings.")
        
    v_path = (OUTPUT_DIR / p["video_file"]) if p.get("video_file") else None
    a_path = (OUTPUT_DIR / p["audio_file"]) if p.get("audio_file") else None
    
    result = send_recap_to_telegram(
        bot_token=token,
        chat_id=chat_id,
        project_title=p.get("title", "Movie Recap"),
        video_path=v_path,
        audio_path=a_path,
        duration_str=p.get("duration_str", "00:00")
    )
    return result
