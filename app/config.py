import os
import json
from pathlib import Path
from typing import Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config.json"
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"

DEFAULT_CONFIG: Dict[str, Any] = {
    "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
    "gemini_model": "gemini-2.5-flash",
    "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
    "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
    "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
    "telegram_auto_send": True,
    "default_voice": "my-MM-ThihaNeural",
    "default_tts_provider": "Edge TTS (Free)",
    "default_transcription": "OpenRouter",
    "default_script_model": "Default (Gemini 2.5 Flash)",
    "voice_speed": "+0%",
    "voice_pitch": "+0Hz",
    "default_resolution": "1080p",
    "default_aspect_ratio": "16:9",
    "watermark_text": "@actrecap",
    "watermark_opacity": 0.7,
    "watermark_position": "top-right",
    "subtitle_font": "Noto Sans Myanmar",
    "subtitle_font_size": 28,
    "subtitle_color": "#ffffff",
    "subtitle_outline_color": "#000000",
    "subtitle_outline_width": 3,
    "subtitle_bg_box": True,
    "subtitle_position": "bottom",
    "anti_copyright_speed": 1.05,
    "mirror_effect": False,
    "bgm_volume": 0.15,
    "ducking_factor": 0.05
}

def load_config() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(data)
            return merged
    except Exception as e:
        print(f"Error reading config: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        current = load_config() if CONFIG_FILE.exists() else DEFAULT_CONFIG.copy()
        current.update(config_data)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
        return current
    except Exception as e:
        print(f"Error saving config: {e}")
        return config_data
