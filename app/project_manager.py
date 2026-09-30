import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROJECTS_FILE = DATA_DIR / "projects.json"

def _ensure_file():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PROJECTS_FILE.exists():
        with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)

def list_projects() -> List[Dict[str, Any]]:
    _ensure_file()
    try:
        with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
            projects = json.load(f)
            # Sort newest first
            projects.sort(key=lambda p: p.get("updated_at", 0), reverse=True)
            return projects
    except Exception as e:
        print(f"Error loading projects: {e}")
        return []

def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    projects = list_projects()
    for p in projects:
        if p["id"] == project_id:
            return p
    return None

def create_project(data: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_file()
    projects = list_projects()
    
    now = time.time()
    new_project = {
        "id": uuid.uuid4().hex[:10],
        "title": data.get("title", "ဇာတ်ကား အကျဉ်းချုပ် ဇာတ်ညွှန်း"),
        "movie_name": data.get("movie_name", ""),
        "script": data.get("script", ""),
        "voice": data.get("voice", "my-MM-ThihaNeural"),
        "rate": data.get("rate", "+0%"),
        "pitch": data.get("pitch", "+0Hz"),
        "status": data.get("status", "draft"),
        "duration": data.get("duration", 0.0),
        "duration_str": data.get("duration_str", "00:00"),
        "audio_file": data.get("audio_file"),
        "srt_file": data.get("srt_file"),
        "vtt_file": data.get("vtt_file"),
        "video_file": data.get("video_file"),
        "thumbnail_file": data.get("thumbnail_file"),
        "source_video_file": data.get("source_video_file"),
        "settings": data.get("settings", {}),
        "created_at": now,
        "updated_at": now
    }
    
    projects.append(new_project)
    with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(projects, f, indent=2, ensure_ascii=False)
        
    return new_project

def update_project(project_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    _ensure_file()
    projects = list_projects()
    for idx, p in enumerate(projects):
        if p["id"] == project_id:
            p.update(updates)
            p["updated_at"] = time.time()
            with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
                json.dump(projects, f, indent=2, ensure_ascii=False)
            return p
    return None

def delete_project(project_id: str) -> bool:
    _ensure_file()
    projects = list_projects()
    filtered = [p for p in projects if p["id"] != project_id]
    if len(filtered) < len(projects):
        with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump(filtered, f, indent=2, ensure_ascii=False)
        return True
    return False
