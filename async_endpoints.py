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
