import re
import json
from typing import Dict, Any, List, Optional
import requests

DEFAULT_HASHTAGS = [
    "#MovieRecap", "#BurmeseRecap", "#ဇာတ်လမ်းအကျဉ်း", 
    "#TikTokUni", "#ရုပ်ရှင်ဇာတ်လမ်း", "#မြန်မာစာတန်းထိုး", 
    "#RedNoteDrama", "#Drama", "#Shorts", "#fyp"
]

TIKTOK_TAGS = "#fyp #tiktokuni #movierecap #recapmyanmar #actrecap #ရုပ်ရှင်ဇာတ်လမ်း #ဇာတ်လမ်းအကျဉ်း #burmeserecap #viralvideo"
YOUTUBE_TAGS = "#shorts #youtubeshorts #movierecap #burmeserecap #ဇာတ်လမ်းအကျဉ်း #myanmar #recap"
REELS_TAGS = "#reels #facebookreels #movierecap #myanmar #ဇာတ်လမ်းအကျဉ်း #recap"

COPYRIGHT_DISCLAIMER_EN = (
    "Copyright Disclaimer Under Section 107 of the Copyright Act 1976: "
    "Allowance is made for 'fair use' for purposes such as criticism, comment, recap, "
    "news reporting, teaching, scholarship, and research. Fair use is a use permitted by "
    "copyright statute that might otherwise be infringing. Non-profit, educational or personal "
    "use tips the balance in favor of fair use. All audio and video belong to their respective copyright owners."
)

def build_social_packages(b_title: str, e_title: str, hook: str, tags: List[str]) -> Dict[str, str]:
    tag_str = " ".join(tags)
    
    # 1. TikTok Package (Punchy Hook, High-reach TikTok tags)
    tiktok_copy = f"{b_title}\n\n{hook}\n.\n{TIKTOK_TAGS}"
    
    # 2. YouTube Shorts Package (SEO Title, Hook, Fair Use Disclaimer, Shorts tags)
    yt_shorts_copy = (
        f"{b_title} | Burmese Movie Recap\n\n"
        f"{hook}\n\n"
        f"📌 Copyright Safe Notice:\n{COPYRIGHT_DISCLAIMER_EN}\n\n"
        f"{YOUTUBE_TAGS}"
    )
    
    # 3. Facebook Reels Package (Reels Hook, Engagement CTA, FB tags)
    fb_reels_copy = (
        f"{b_title} 🎬\n\n"
        f"{hook}\n\n"
        f"ရုပ်ရှင်ဇာတ်လမ်း အပြည့်အစုံ ဆက်လက်ကြည့်ရှုရန် Page ကို Like & Follow လုပ်ထားပေးကြပါဦးနော်။\n\n"
        f"{REELS_TAGS}"
    )

    full_caption = f"{b_title}\n\n{hook}\n\n{tag_str}"

    return {
        "tiktok_copy": tiktok_copy,
        "yt_shorts_copy": yt_shorts_copy,
        "fb_reels_copy": fb_reels_copy,
        "copyright_disclaimer": COPYRIGHT_DISCLAIMER_EN,
        "full_caption": full_caption
    }

def generate_viral_caption_and_hashtags(
    title: Optional[str] = None,
    segments: Optional[List[Dict[str, Any]]] = None,
    gemini_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates viral Burmese titles, engaging description hooks, and high-reach hashtags
    optimized for TikTok, YouTube Shorts, and Facebook Reels.
    Uses Gemini API (or smart synthesized recap templates).
    """
    context_lines = []
    if segments:
        for s in segments[:12]:
            t = (s.get("my_text") or s.get("text") or "").strip()
            if t:
                context_lines.append(t)
    story_summary = " ".join(context_lines)
    clean_title = (title or "").replace("RedNote HD Video", "").replace("RedNote Video", "").strip()

    active_key = (gemini_key or "").strip()
    if active_key and len(active_key) > 10 and (story_summary or clean_title):
        prompt = f"""You are an elite viral social media manager and movie recap copywriter for Burmese audiences on TikTok, YouTube Shorts, and Facebook Reels.

Input Video Title / Topic: {clean_title or 'ရုပ်ရှင်ဇာတ်လမ်းအကျဉ်း'}
Transcribed Story Content:
{story_summary[:800]}

Generate an ultra-engaging viral caption package for this video.
Return STRICTLY valid JSON with no markdown wrapping, no backticks:
{{
  "burmese_title": "A short, viral, suspenseful Burmese title with emojis (e.g. ရေသူမျိုးနွယ် အစ်ကိုကြီးနဲ့ မိစ္ဆာအဆိပ် 😱)",
  "english_title": "A catchy English drama title",
  "hook": "2 sentences in natural spoken Burmese capturing suspense that hooks viewers into watching till the end",
  "hashtags": ["#MovieRecap", "#BurmeseRecap", "#ဇာတ်လမ်းအကျဉ်း", "#TikTokUni", "#ရုပ်ရှင်ဇာတ်လမ်း", "#RedNote", "#Drama", "#Shorts", "#fyp"]
}}"""

        candidate_models = [
            "gemini-flash-lite-latest",
            "gemini-3.5-flash-lite",
            "gemini-3.8-flash",
            "gemini-flash-latest"
        ]

        for m_name in candidate_models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={active_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1024}
                }
                res = requests.post(url, json=payload, timeout=12)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        raw = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                        if raw.startswith("```"):
                            raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
                            raw = re.sub(r"\n?```$", "", raw).strip()
                        parsed = json.loads(raw)
                        b_title = parsed.get("burmese_title") or clean_title or "ရုပ်ရှင်ဇာတ်လမ်းအကျဉ်း 😱"
                        e_title = parsed.get("english_title") or "Movie Recap Drama"
                        hook = parsed.get("hook") or "ဇာတ်လမ်းအစကနေ အဆုံးထိ ဘာတွေဆက်ဖြစ်မလဲ ကြည့်လိုက်ရအောင်!"
                        tags = parsed.get("hashtags") or DEFAULT_HASHTAGS
                        
                        tag_string = " ".join(tags)
                        packages = build_social_packages(b_title, e_title, hook, tags)

                        return {
                            "success": True,
                            "burmese_title": b_title,
                            "english_title": e_title,
                            "hook": hook,
                            "hashtags": tags,
                            "hashtag_string": tag_string,
                            "full_caption": packages["full_caption"],
                            "tiktok_copy": packages["tiktok_copy"],
                            "yt_shorts_copy": packages["yt_shorts_copy"],
                            "fb_reels_copy": packages["fb_reels_copy"],
                            "copyright_disclaimer": packages["copyright_disclaimer"],
                            "generated_by": m_name
                        }
            except Exception as e:
                print(f"Gemini caption generation error with {m_name}: {e}")

    # Fallback Template Generator
    lead = clean_title
    if not lead and context_lines:
        first_s = context_lines[0]
        lead = first_s[:45]
    if not lead:
        lead = "သည်းထိတ်ရင်ဖို ရုပ်ရှင်ဇာတ်လမ်းအကျဉ်း"

    b_title = f"{lead} 😱 (ရုပ်ရှင်ဇာတ်လမ်းအကျဉ်း)"
    e_title = "Trending Movie Recap Drama"
    hook = "အစကနေ အဆုံးထိ စိတ်ဝင်စားစရာ အလှည့်အပြောင်းတွေနဲ့ ပြည့်နှက်နေတဲ့ ဇာတ်လမ်းလေးကို အတူတူ ကြည့်လိုက်ကြရအောင်။"
    tag_string = " ".join(DEFAULT_HASHTAGS)
    packages = build_social_packages(b_title, e_title, hook, DEFAULT_HASHTAGS)

    return {
        "success": True,
        "burmese_title": b_title,
        "english_title": e_title,
        "hook": hook,
        "hashtags": DEFAULT_HASHTAGS,
        "hashtag_string": tag_string,
        "full_caption": packages["full_caption"],
        "tiktok_copy": packages["tiktok_copy"],
        "yt_shorts_copy": packages["yt_shorts_copy"],
        "fb_reels_copy": packages["fb_reels_copy"],
        "copyright_disclaimer": packages["copyright_disclaimer"],
        "generated_by": "smart-recap-template"
    }
