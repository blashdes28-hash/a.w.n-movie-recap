import os
import requests
from pathlib import Path
from typing import Dict, Any, Optional

def test_telegram_connection(bot_token: str, chat_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Test Telegram bot token and optionally send a ping message to chat_id.
    """
    if not bot_token or not bot_token.strip():
        return {"success": False, "error": "Bot token is empty."}
        
    try:
        # Check bot validity
        me_url = f"https://api.telegram.org/bot{bot_token.strip()}/getMe"
        res = requests.get(me_url, timeout=10)
        data = res.json()
        
        if not data.get("ok"):
            return {"success": False, "error": data.get("description", "Invalid bot token.")}
            
        bot_info = data.get("result", {})
        bot_name = bot_info.get("first_name", "Bot")
        username = bot_info.get("username", "")
        
        # If chat_id is provided, send a greeting ping
        if chat_id and chat_id.strip():
            msg_url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
            text = (
                f"🎬 *ACT RECAP - ချိတ်ဆက်မှု အောင်မြင်ပါသည်*\n\n"
                f"Bot: @{username}\n"
                f"Status: ချိတ်ဆက်ပြီးပါပြီ။\n"
                f"Render ပြီးဆုံးသည့် ဗီဒီယိုများကို ဤနေရာသို့ အလိုအလျောက် ပေးပို့ပေးပါမည်။"
            )
            msg_res = requests.post(msg_url, json={
                "chat_id": chat_id.strip(),
                "text": text,
                "parse_mode": "Markdown"
            }, timeout=10)
            msg_data = msg_res.json()
            if not msg_data.get("ok"):
                return {
                    "success": True,
                    "bot_name": bot_name,
                    "username": username,
                    "warning": f"Bot is valid, but message failed: {msg_data.get('description')}. Make sure you sent /start to @{username} first!"
                }
                
        return {
            "success": True,
            "bot_name": bot_name,
            "username": username,
            "message": f"Connected to @{username} successfully!"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def send_recap_to_telegram(
    bot_token: str,
    chat_id: str,
    project_title: str,
    video_path: Optional[Path] = None,
    audio_path: Optional[Path] = None,
    duration_str: str = "00:00"
) -> Dict[str, Any]:
    """
    Send completed recap video and notification to user's Telegram PM.
    """
    if not bot_token or not chat_id:
        return {"success": False, "error": "Telegram bot token or chat ID is missing."}
        
    caption = (
        f"🎬 *{project_title}*\n\n"
        f"⏱ Duration: {duration_str}\n"
        f"⚡ Generated with ACT RECAP Studio\n"
        f"#actrecap #movierecap #burmeserecap"
    )
    
    try:
        # If video exists and is under 50MB (standard Telegram Bot API limit)
        if video_path and video_path.exists():
            file_size_mb = video_path.stat().st_size / (1024 * 1024)
            if file_size_mb <= 49.0:
                url = f"https://api.telegram.org/bot{bot_token.strip()}/sendVideo"
                with open(video_path, "rb") as vf:
                    files = {"video": (video_path.name, vf, "video/mp4")}
                    data = {
                        "chat_id": chat_id.strip(),
                        "caption": caption,
                        "parse_mode": "Markdown",
                        "supports_streaming": "true"
                    }
                    res = requests.post(url, data=data, files=files, timeout=120)
                    res_data = res.json()
                    if res_data.get("ok"):
                        return {"success": True, "message": "Video sent to Telegram PM!"}
                    else:
                        print("Telegram sendVideo error:", res_data)
                        
        # Fallback to sending audio narration or text notification
        if audio_path and audio_path.exists():
            url = f"https://api.telegram.org/bot{bot_token.strip()}/sendAudio"
            with open(audio_path, "rb") as af:
                files = {"audio": (audio_path.name, af, "audio/mpeg")}
                data = {
                    "chat_id": chat_id.strip(),
                    "caption": f"🎙 Narration Audio: {project_title}\n{caption}",
                    "parse_mode": "Markdown",
                    "title": project_title,
                    "performer": "ACT RECAP"
                }
                res = requests.post(url, data=data, files=files, timeout=60)
                if res.json().get("ok"):
                    return {"success": True, "message": "Audio sent to Telegram PM!"}

        # Otherwise send message notification
        url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
        res = requests.post(url, json={
            "chat_id": chat_id.strip(),
            "text": f"✅ *Render Completed!*\n\n{caption}\n\nYour video is ready to download on your local ACT RECAP Studio.",
            "parse_mode": "Markdown"
        }, timeout=15)
        return {"success": res.json().get("ok", False)}
        
    except Exception as e:
        print(f"Telegram sending error: {e}")
        return {"success": False, "error": str(e)}
