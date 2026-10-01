import os
import re
import urllib.parse
import uuid
import json
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
import imageio_ffmpeg
import subprocess

from app.tts_engine import format_srt_time, format_vtt_time
from app.chinese_recap_processor import preprocess_chinese_drama_text, transliterate_chinese_name

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

# Common Chinese Movie Recap Tropes & Natural Colloquial Burmese Phrases
CHINESE_RECAP_PATTERNS = [
    # Tropes & Archetypes
    (r"这个男人叫([^，。\s]+)", r"ဒီလူရဲ့ နာမည်ကတော့ \1 လို့ ခေါ်ပြီး"),
    (r"这个女人叫([^，。\s]+)", r"ဒီကောင်မလေးရဲ့ နာမည်ကတော့ \1 လို့ ခေါ်ပြီး"),
    (r"这个男人", "ဒီလူဟာ"),
    (r"这个女人", "ဒီကောင်မလေးဟာ"),
    (r"小帅", "ရှောင်ရွှိုက်"),
    (r"小美", "ရှောင်မေ့"),
    (r"大壮", "တာကျွမ့်"),
    (r"阿强", "အာချန်"),
    (r"老王", "ဝမ်ကြီး"),
    (r"大海", "တာဟိုင်"),
    
    # Dramatic Narrative Transitions
    (r"万万没想到", "လုံးဝ မထင်မှတ်ထားတဲ့ အနေအထားမှာ"),
    (r"男人没想到", "သူဟာ မထင်မှတ်ထားဘဲ"),
    (r"女人没想到", "သူမဟာ မထင်မှတ်ထားဘဲ"),
    (r"就在这时", "ဒီအချိန်မှာပဲ ရုတ်တရက်"),
    (r"下一秒", "နောက်တစ်စက္ကန့်မှာတင်"),
    (r"不可思议", "မယုံနိုင်စရာ ကောင်းလောက်အောင်"),
    (r"原来", "တကယ်တော့"),
    (r"大结局", "ဇာတ်သိမ်းပိုင်းမှာတော့"),
    (r"注意看", "သေချာ ကြည့်လိုက်ပါ"),
    (r"欢迎关注", "Like နဲ့ Follow လုပ်ထားဖို့ မမေ့နဲ့နော်"),
    (r"精彩内容", "စိတ်လှုပ်ရှားဖွယ် ဇာတ်ကွက်များ"),
    (r"下一集", "နောက်အပိုင်း"),

    # Movie Recap Roles & Terminology
    (r"特工", "အထူးအေးဂျင့်"),
    (r"杀手", "ကြေးစားလူသတ်သမား"),
    (r"保镖", "သက်တော်စောင့်"),
    (r"总裁", "ကုမ္ပဏီဥက္ကဋ္ဌ"),
    (r"首富", "သူဌေးကြီး"),
    (r"毒枭", "မူးယစ်ရာဇာ"),
    (r"绑架", "ပြန်ပေးဆွဲ"),
    (r"人质", "ဓားစာခံ"),
    (r"警察", "ရဲအရာရှိ"),
    (r"卧底", "လျှို့ဝှက်စုံထောက်"),
    (r"神秘任务", "လျှို့ဝှက်ဆန်းကြယ်တဲ့ တာဝန်"),
    (r"任务", "တာဝန်")
]

# Post-processing: Converts textbook literary/bookish Burmese into fluent spoken recap tone
LITERARY_TO_SPOKEN_RECAP = [
    # Names & Pronouns
    (r"ဤလူ၏အမည်မှာ\s*([A-Za-z]+|\S+)\s*ဖြစ်ပြီး", r"ဒီလူရဲ့ နာမည်ကတော့ \1 ဖြစ်ပြီး"),
    (r"ဤလူ၏", "ဒီလူရဲ့"),
    (r"ဤလူ", "ဒီလူဟာ"),
    (r"ဤယောက်ျား", "ဒီလူဟာ"),
    (r"ဤအမျိုးသမီး", "ဒီအမျိုးသမီးဟာ"),
    (r"ဤမိန်းကလေး", "ဒီကောင်မလေးဟာ"),
    (r"ဤကား", "ဒီဇာတ်ကား"),
    (r"ယနေ့တွင်", "ဒီနေ့မှာတော့"),
    (r"ယခုအခါတွင်", "အခုအချိန်မှာတော့"),
    (r"ယခုအခါ", "အခုတော့"),
    (r"ထိုအချိန်တွင်", "အဲဒီအချိန်မှာပဲ"),
    (r"ထို့နောက်", "အဲဒီနောက်"),
    (r"သူသည်", "သူဟာ"),
    (r"သူမသည်", "သူမဟာ"),
    (r"သူတို့သည်", "သူတို့ဟာ"),

    # Literary particles to spoken particles
    (r"၏(?=[\s\u1000-\u109f])", "ရဲ့"),
    (r"သော(?=[\s\u1000-\u109f])", "တဲ့"),
    (r"၌(?=[\s\u1000-\u109f])", "မှာ"),
    (r"တွင်(?=[\s\u1000-\u109f])", "မှာ"),
    
    # Bookish Verbs to Conversational Endings
    (r"ဖြစ်ခဲ့ဖူးသည်[။]?", "ဖြစ်ခဲ့တာပါ။"),
    (r"ခဲ့ဖူးသည်[။]?", "ခဲ့တာပါ။"),
    (r"ခဲ့သည်[။]?", "ခဲ့ပါတယ်။"),
    (r"ရှိခဲ့သည်[။]?", "ရှိခဲ့တာပါ။"),
    (r"ကြသည်[။]?", "ကြပါတော့တယ်။"),
    (r"နေသည်[။]?", "နေတာပါ။"),
    (r"ရပေလိမ့်မည်[။]?", "ရတော့မှာပါ။"),
    (r"မည်ဖြစ်သည်[။]?", "မှာ ဖြစ်ပါတယ်။"),
    (r"သည်။", "ပါတယ်။"),
    (r"ပါသည်[။]?", "ပါတယ်ခင်ဗျာ။"),

    # Transliteration of common Chinese Pinyin names
    (r"Xiaoshuai", "ရှောင်ရွှိုက်"),
    (r"xiao shuai", "ရှောင်ရွှိုက်"),
    (r"Xiaomei", "ရှောင်မေ့"),
    (r"xiao mei", "ရှောင်မေ့"),
    (r"Dazhuang", "တာကျွမ့်"),
    (r"da zhuang", "တာကျွမ့်"),
    (r"Aqiang", "အာချန်"),
    (r"Ah Qiang", "အာချန်"),
    (r"Lao Wang", "ဝမ်ကြီး"),
    (r"lao wang", "ဝမ်ကြီး"),

    # Common stiffness fixes in machine translation
    (r"မစ်ရှင်တစ်ခုကို", "တာဝန်တစ်ခုကို"),
    (r"မစ်ရှင်", "တာဝန်"),
    (r"ပိုက်စိပ်တိုက် တပ်ဆင်ထားပြီးဖြစ်သည်။", "ပိုက်ကွန်လို အကွက်ချ စောင့်ဆိုင်းနေကြတာပါ"),
    (r"ပိုက်စိပ်တိုက်", "အကွက်ချ"),
    (r"မထင်မှတ်ဘဲ", "မထင်မှတ်ထားဘဲ"),
    (r"မမျှော်လင့်ဘဲ", "မထင်မှတ်ထားဘဲ ရုတ်တရက်"),
    (r"ဖြစ်ဖြစ်ခဲ့တာ", "ဖြစ်ခဲ့တာ")
]

def naturalize_burmese_recap(text: str) -> str:
    """
    Polishes raw or machine-translated Burmese into natural, engaging,
    colloquial spoken Burmese movie recap narration style.
    """
    if not text:
        return ""
    t = text.strip()
    
    # Apply literary-to-spoken transformations
    for pattern, replacement in LITERARY_TO_SPOKEN_RECAP:
        t = re.sub(pattern, replacement, t)
        
    # Clean up double punctuation or spaces
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"([။၊]){2,}", r"\1", t)
    
    # Ensure natural sentence ending if missing and not ending with ellipsis or comma
    if t.endswith("...") or t.endswith("…"):
        pass
    elif t.endswith("၊"):
        pass
    elif not (t.endswith("။") or t.endswith("!") or t.endswith("?")):
        t += "။"
        
    t = re.sub(r"\.\.\.။", "...", t)
    t = re.sub(r"…။", "…", t)
    t = re.sub(r"([။၊]){2,}", r"\1", t)
    return t


def translate_chinese_raw_google(text: str) -> str:
    """Translates Chinese text to natural Burmese using reliable multi-tier endpoints."""
    if not text or not text.strip():
        return ""
    try:
        # 1. Pre-process Chinese drama tropes and character names
        pre = preprocess_chinese_drama_text(text)
        has_chinese = bool(re.search(r"[\u4e00-\u9fa5]", pre))
        if not has_chinese:
            return naturalize_burmese_recap(pre)

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

        # Tier 1: clients5 Google API (send clean original Chinese)
        url_c5 = "https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=zh-CN&tl=my&q=" + urllib.parse.quote(text.strip())
        res = requests.get(url_c5, headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                translated = str(data[0]).strip()
                if re.search(r"[\u1000-\u109f]", translated):
                    return naturalize_burmese_recap(translated)

        # Tier 2: GTX Google API
        url_gtx = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=zh-CN&tl=my&dt=t&q=" + urllib.parse.quote(text.strip())
        res_gtx = requests.get(url_gtx, headers=headers, timeout=8)
        if res_gtx.status_code == 200:
            data = res_gtx.json()
            translated = "".join([part[0] for part in data[0] if part and part[0]])
            if re.search(r"[\u1000-\u109f]", translated):
                return naturalize_burmese_recap(translated)

    except Exception as e:
        print(f"Translation error for '{text[:20]}': {e}")


    # Fallback Tier: Pinyin-to-Myanmar syllable transliteration so Chinese characters never leak through
    try:
        burmese_translit = transliterate_chinese_name(text)
        if re.search(r"[\u1000-\u109f]", burmese_translit):
            return naturalize_burmese_recap(burmese_translit)
    except Exception:
        pass

    return ""

def translate_chinese_to_english(text: str) -> str:
    """Translates Chinese text to English for bilingual subtitles."""
    if not text or not text.strip():
        return ""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        url = "https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=zh-CN&tl=en&q=" + urllib.parse.quote(text.strip())
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                return str(data[0]).strip()
    except Exception as e:
        print(f"English translation error: {e}")
    return ""

from concurrent.futures import ThreadPoolExecutor

def batch_translate_segments_gemini(
    segments: List[Dict[str, Any]],
    gemini_key: Optional[str] = None,
    openrouter_key: Optional[str] = None,
    style: str = "recap"
) -> List[Dict[str, Any]]:
    """
    Uses Gemini AI (or OpenRouter) to translate Chinese subtitle segments in parallel with full movie context.
    Produces viral television/TikTok movie recap storytelling tone with flawless Burmese grammar.
    """
    if not segments:
        return segments

    active_gemini_key = gemini_key.strip() if gemini_key else None
    active_openrouter_key = openrouter_key.strip() if openrouter_key else None

    if not active_gemini_key and not active_openrouter_key:
        return segments

    batch_size = 25
    batches = [segments[i:i+batch_size] for i in range(0, len(segments), batch_size)]

    few_shot_sample = """[
  {"id": 1, "my_text": "ဂိုဏ်းတူအစ်ကိုကြီးက ရေသူမျိုးနွယ် (ကျောင်းရန်) တစ်ယောက်ပါ။", "en_text": "Senior Brother is actually of the Merfolk."},
  {"id": 2, "my_text": "ကျွန်မကို ကယ်တင်ရင်းနဲ့... မိစ္ဆာသတ္တဝါရဲ့ အဆိပ်မိသွားခဲ့တာ။", "en_text": "While saving me, he was poisoned by an evil demon."},
  {"id": 3, "my_text": "မိုးကြိုးသိုင်းပညာမှာလည်း ကျွန်မထက် အဆပေါင်းများစွာ သာနေခဲ့တယ်။", "en_text": "In lightning arts, he was also far superior to me."},
  {"id": 4, "my_text": "မင်း စောင့်ကြည့်နေလိုက်ပါ။ ငါ မင်းကို အနိုင်ယူပြမယ်။", "en_text": "Just you wait. I will defeat you with my own hands."}
]"""

    def translate_single_batch(batch):
        items_payload = [{"id": s["index"], "text": s["zh_text"]} for s in batch]
        
        prompt = f"""You are the world's best Chinese-to-Burmese movie recap narrator and screenwriter (မြန်မာ ရုပ်ရှင်ဇာတ်လမ်းပြော အထူးကျွမ်းကျင်သူ).
Translate the following Chinese movie recap subtitle lines into natural, gripping, colloquial spoken Burmese (ရုပ်ရှင်ဇာတ်လမ်းပြော စကားပြောဟန်) and English.

CRITICAL RULES FOR NATURAL BURMESE RECAP:
1. Strictly use spoken/colloquial storytelling Burmese (စကားပြောဟန်):
   - Use natural conversational particles: "ဒီ", "ရဲ့", "တဲ့", "မှာ", "ပါတယ်", "ခဲ့တာပါ", "ပါတော့တယ်", "နေတာပါ", "တာပေါ့", "သွားပြီပေါ့", "စောင့်ကြည့်နေလိုက်ပါ", "လို့".
   - NEVER use stiff, literary bookish particles: NO "ဤ", NO "၏", NO "သော", NO "သည်။", NO "ဖြစ်ခဲ့ဖူးသည်", NO "သူသည်".
2. Chinese Drama / Xianxia / Wuxia / Romance Terminology:
   - "大师兄" -> "ဂိုဏ်းတူအစ်ကိုကြီး", "二师姐" -> "ဂိုဏ်းတူဒုတိယအစ်မကြီး", "大师姐" -> "ဂိုဏ်းတူအစ်မကြီး", "师弟师妹" -> "ဂိုဏ်းတူညီငယ်တွေ"
   - "宗门" -> "ဂိုဏ်း" / "သိုင်းဂိုဏ်း", "首席大师兄" -> "လူတိုင်း အလေးစားရဆုံး နံပါတ်တစ် ဂိုဏ်းတူအစ်ကိုကြီး"
   - "鲛人" -> "ရေသူမျိုးနွယ် (ကျောင်းရန်)", "魔修" -> "မိစ္ဆာသတ္တဝါ" / "မိစ္ဆာကျင့်ကြံသူ"
   - "剧毒" -> "အဆိပ်", "中了...剧毒" -> "...ရဲ့ အဆိပ်မိသွားခဲ့တာ"
   - "修炼天赋" / "天赋" -> "ပါရမီဓာတ်ခံ", "雷法" -> "မိုးကြိုးသိုင်းပညာ", "执法长老" -> "ဆရာသခင်"
   - "走着瞧" -> "မင်း စောင့်ကြည့်နေလိုက်ပါ", "发誓" -> "သစ္စာဓိဋ္ဌာန်ပြုခဲ့တယ်", "赢你" -> "မင်းကို အနိုင်ယူပြမယ်"
   - "小帅" -> "ရှောင်ရွှိုက်", "小美" -> "ရှောင်မေ့", "大壮" -> "တာကျွမ့်", "阿强" -> "အာချန်"

FEW-SHOT EXAMPLES:
{few_shot_sample}

Lines to translate:
{json.dumps(items_payload, ensure_ascii=False)}

Output Format: Return ONLY a valid JSON array of objects with "id", "my_text", and "en_text". No markdown fences.
"""
        raw_text = None
        # 1. Try Gemini API with candidate models
        if active_gemini_key:
            candidate_gemini_models = [
                "gemini-3.5-flash-lite",
                "gemini-3.1-flash-lite",
                "gemini-3.8-flash",
                "gemini-flash-lite-latest",
                "gemini-flash-latest"
            ]
            for model_name in candidate_gemini_models:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={active_gemini_key}"
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048}
                    }
                    res = requests.post(url, json=payload, timeout=20)
                    if res.status_code == 200:
                        data = res.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            raw_text = "".join([p.get("text", "") for p in parts]).strip()
                            if raw_text:
                                break
                    elif res.status_code in (404, 503, 429):
                        continue
                except Exception as e:
                    print(f"Gemini API error with {model_name}: {e}")

        # 2. Try OpenRouter fallback
        if not raw_text and active_openrouter_key:
            for or_model in ["google/gemini-2.5-flash", "google/gemini-flash-1.5", "meta-llama/llama-3.3-70b-instruct"]:
                try:
                    url = "https://openrouter.ai/api/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {active_openrouter_key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "model": or_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3
                    }
                    res = requests.post(url, headers=headers, json=payload, timeout=25)
                    if res.status_code == 200:
                        data = res.json()
                        raw_text = data["choices"][0]["message"]["content"].strip()
                        if raw_text:
                            break
                except Exception as e:
                    print(f"OpenRouter error with {or_model}: {e}")

        # 3. Parse JSON response
        success_batch = False
        if raw_text:
            try:
                clean_json = raw_text.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.startswith("```"):
                    clean_json = clean_json[3:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                
                parsed = json.loads(clean_json.strip())
                trans_map = {item["id"]: item for item in parsed if "id" in item}
                for s in batch:
                    item = trans_map.get(s["index"])
                    if item:
                        if item.get("my_text"):
                            s["my_text"] = naturalize_burmese_recap(item["my_text"])
                        if item.get("en_text"):
                            s["en_text"] = item["en_text"].strip()
                success_batch = True
            except Exception as e:
                print(f"Error parsing AI JSON response: {e}")

        # 4. Fallback to local enhanced drama naturalizer for untranslated segments
        if not success_batch:
            for s in batch:
                if not s.get("my_text"):
                    s["my_text"] = translate_chinese_raw_google(s["zh_text"])

    max_workers = min(len(batches), 5) if len(batches) > 0 else 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(translate_single_batch, batches))

    return segments


def extract_audio_from_video(video_path: Path, output_wav: Path) -> bool:
    """Extracts a 16kHz mono WAV audio file from a video for Whisper transcription."""
    cmd = [
        FFMPEG_EXE, "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output_wav)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return res.returncode == 0

# Cache whisper model instance so it only loads once in memory
_WHISPER_MODEL = None

def get_whisper_model(model_size: str = "base"):
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        from faster_whisper import WhisperModel
        print(f"Loading faster-whisper model '{model_size}' on CPU...")
        _WHISPER_MODEL = WhisperModel(model_size, device="cpu", compute_type="int8")
        print("Whisper model loaded successfully!")
    return _WHISPER_MODEL

def transcribe_and_translate_video(
    video_path: Path,
    output_dir: Path,
    source_lang: str = "zh",
    gemini_key: Optional[str] = None,
    openrouter_key: Optional[str] = None,
    whisper_model_size: str = "base",
    style: str = "recap"
) -> Dict[str, Any]:
    """
    Full pipeline:
    1. Extracts audio from video
    2. Transcribes Chinese speech using Gemini (Whisper fallback removed)
    3. Translates each segment to natural colloquial Burmese while strictly preserving timestamps
    4. Generates Burmese SRT, Chinese SRT, and Bilingual SRT
    """
    if not gemini_key or not gemini_key.strip():
        raise RuntimeError("Gemini API key is required for transcription. Local Whisper has been disabled.")

    output_dir.mkdir(parents=True, exist_ok=True)
    job_uid = uuid.uuid4().hex[:10]
    
    # 1. Extract audio
    wav_path = output_dir / f"extracted_{job_uid}.wav"
    extracted = extract_audio_from_video(video_path, wav_path)
    if not extracted or not wav_path.exists():
        raise RuntimeError("Failed to extract audio track from video.")

    # 2. Transcribe with Gemini
    import google.generativeai as genai
    genai.configure(api_key=gemini_key.strip())
    
    try:
        audio_file = genai.upload_file(path=str(wav_path))
        # Try multiple models since some keys don't support gemini-1.5-flash
        candidate_models = ["gemini-1.5-flash", "gemini-flash-lite-latest", "gemini-1.5-flash-latest", "gemini-1.5-pro"]
        response = None
        last_error = None
        for model_name in candidate_models:
            try:
                model = genai.GenerativeModel(model_name)
                prompt = "Transcribe the following audio. Return the exact response in SRT format. Only output the SRT content, no markdown blocks."
                response = model.generate_content([prompt, audio_file])
                break # Success
            except Exception as e:
                last_error = repr(e)
                continue
                
        if not response:
            raise RuntimeError(f"Transcription failed on all models. Last error: {last_error}")

        try:
            srt_content = response.text.strip()
        except ValueError as e:
            # Handle safety block exception
            raise RuntimeError(f"Gemini response blocked by safety filters or empty. Details: {repr(e)}")
            
        if srt_content.startswith("```srt"):
            srt_content = srt_content[6:]
        if srt_content.startswith("```"):
            srt_content = srt_content[3:]
        if srt_content.endswith("```"):
            srt_content = srt_content[:-3]
        srt_content = srt_content.strip()
    finally:
        try:
            wav_path.unlink()
        except Exception:
            pass

    # Parse SRT into segments
    segments = parse_srt_string(srt_content)
    if not segments:
        raise RuntimeError(f"Failed to parse SRT from Gemini response. Raw: {srt_content[:200]}")

    # 3. Natural Translation into Burmese Recap Style and English Translation
    if (gemini_key and gemini_key.strip()) or (openrouter_key and openrouter_key.strip()):
        # High quality Gemini / OpenRouter contextual recap translator (already populates both my_text & en_text)
        segments = batch_translate_segments_gemini(segments, gemini_key=gemini_key, openrouter_key=openrouter_key, style=style)
    else:
        # High speed parallel offline naturalizer + Google
        def trans_offline(s):
            s["my_text"] = translate_chinese_raw_google(s["zh_text"])
            s["en_text"] = translate_chinese_to_english(s["zh_text"])
        with ThreadPoolExecutor(max_workers=5) as ex:
            list(ex.map(trans_offline, segments))

    # 4. Generate SRT and VTT files
    burmese_srt_file = f"burmese_sub_{job_uid}.srt"
    chinese_srt_file = f"chinese_sub_{job_uid}.srt"
    bilingual_srt_file = f"bilingual_sub_{job_uid}.srt"
    burmese_vtt_file = f"burmese_sub_{job_uid}.vtt"

    burmese_srt = []
    chinese_srt = []
    bilingual_srt = []
    burmese_vtt = ["WEBVTT\n"]

    for s in segments:
        time_header = f"{s['start_str']} --> {s['end_str']}"
        burmese_srt.append(f"{s['index']}\n{time_header}\n{s['my_text']}\n")
        chinese_srt.append(f"{s['index']}\n{time_header}\n{s['zh_text']}\n")
        bilingual_srt.append(f"{s['index']}\n{time_header}\n{s['my_text']}\n{s.get('en_text') or s['zh_text']}\n")
        burmese_vtt.append(f"{s['index']}\n{s['vtt_start']} --> {s['vtt_end']}\n{s['my_text']}\n")

    with open(output_dir / burmese_srt_file, "w", encoding="utf-8") as f:
        f.write("\n".join(burmese_srt))
    with open(output_dir / chinese_srt_file, "w", encoding="utf-8") as f:
        f.write("\n".join(chinese_srt))
    with open(output_dir / bilingual_srt_file, "w", encoding="utf-8") as f:
        f.write("\n".join(bilingual_srt))
    with open(output_dir / burmese_vtt_file, "w", encoding="utf-8") as f:
        f.write("\n".join(burmese_vtt))

    return {
        "job_id": job_uid,
        "language": source_lang,
        "duration": 0,
        "segments": segments,
        "burmese_srt": burmese_srt_file,
        "chinese_srt": chinese_srt_file,
        "bilingual_srt": bilingual_srt_file,
        "burmese_vtt": burmese_vtt_file,
        "burmese_srt_url": f"/media/output/{burmese_srt_file}",
        "chinese_srt_url": f"/media/output/{chinese_srt_file}",
        "bilingual_srt_url": f"/media/output/{bilingual_srt_file}",
        "burmese_vtt_url": f"/media/output/{burmese_vtt_file}"
    }

def parse_srt_string(srt_content: str) -> List[Dict[str, Any]]:
    """Parses SRT format into structured segment list, extremely tolerant of Gemini output quirks."""
    segments = []
    
    # Ultra-permissive regex to catch timestamps, even if everything is on a single line
    # Matches: index (spaces/newlines) start (-> or -->) end (spaces/newlines) text
    pattern = re.compile(
        r'(\d+)\s+'                                              # 1: Index
        r'([\d:,\.]+)\s*[-=]+>\s*([\d:,\.]+)\s*'                 # 2: Start, 3: End
        r'(.*?)(?=\s+\d+\s+[\d:,\.]+[-=\s]+>|\Z)',               # 4: Text (lookahead for next segment or end)
        re.DOTALL
    )
    
    def parse_time(ts: str) -> float:
        # Extract all numbers from the timestamp
        nums = re.findall(r'\d+', ts)
        if len(nums) >= 4:
            # HH, MM, SS, MS
            return float(nums[0])*3600 + float(nums[1])*60 + float(nums[2]) + float(nums[3])/1000.0
        elif len(nums) == 3:
            # Either HH, MM, SS or MM, SS, MS
            # If the last part has 3 digits (e.g. 626), it's highly likely milliseconds
            if len(nums[2]) >= 3:
                return float(nums[0])*60 + float(nums[1]) + float(nums[2])/1000.0
            else:
                return float(nums[0])*3600 + float(nums[1])*60 + float(nums[2])
        elif len(nums) == 2:
            return float(nums[0])*60 + float(nums[1])
        return 0.0

    def format_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        ms = int((s - int(s)) * 1000)
        return f"{h:02d}:{m:02d}:{int(s):02d},{ms:03d}"

    def format_vtt_time(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        ms = int((s - int(s)) * 1000)
        return f"{h:02d}:{m:02d}:{int(s):02d}.{ms:03d}"

    for match in pattern.finditer(srt_content):
        idx = int(match.group(1))
        start_sec = parse_time(match.group(2).strip())
        end_sec = parse_time(match.group(3).strip())
        text = match.group(4).strip()
        
        # Skip empty text segments
        if not text:
            continue
            
        segments.append({
            "index": idx,
            "start": round(start_sec, 3),
            "end": round(end_sec, 3),
            "start_str": format_time(start_sec),
            "end_str": format_time(end_sec),
            "vtt_start": format_vtt_time(start_sec),
            "vtt_end": format_vtt_time(end_sec),
            "start_time": start_sec,
            "end_time": end_sec,
            "zh_text": text,
            "my_text": "",
            "en_text": ""
        })
    
    return segments

def translate_srt_content(
    srt_content: str,
    output_dir: Path,
    gemini_key: Optional[str] = None,
    openrouter_key: Optional[str] = None,
    style: str = "recap"
) -> Dict[str, Any]:
    """Translates existing Chinese SRT file content to natural colloquial Burmese with identical timestamps."""
    segments = parse_srt_string(srt_content)
    if not segments:
        raise ValueError("Invalid or empty SRT file.")

    if (gemini_key and gemini_key.strip()) or (openrouter_key and openrouter_key.strip()):
        segments = batch_translate_segments_gemini(segments, gemini_key=gemini_key, openrouter_key=openrouter_key, style=style)
    else:
        def trans_offline_srt(s):
            s["my_text"] = translate_chinese_raw_google(s["zh_text"])
            s["en_text"] = translate_chinese_to_english(s["zh_text"])
        with ThreadPoolExecutor(max_workers=5) as ex:
            list(ex.map(trans_offline_srt, segments))

    job_uid = uuid.uuid4().hex[:10]
    burmese_srt_file = f"burmese_sub_{job_uid}.srt"
    bilingual_srt_file = f"bilingual_sub_{job_uid}.srt"

    burmese_srt = []
    bilingual_srt = []
    for s in segments:
        header = f"{s['start_str']} --> {s['end_str']}"
        burmese_srt.append(f"{s['index']}\n{header}\n{s['my_text']}\n")
        bilingual_srt.append(f"{s['index']}\n{header}\n{s['my_text']}\n{s.get('en_text') or s['zh_text']}\n")

    with open(output_dir / burmese_srt_file, "w", encoding="utf-8") as f:
        f.write("\n".join(burmese_srt))
    with open(output_dir / bilingual_srt_file, "w", encoding="utf-8") as f:
        f.write("\n".join(bilingual_srt))

    return {
        "job_id": job_uid,
        "segments": segments,
        "burmese_srt": burmese_srt_file,
        "bilingual_srt": bilingual_srt_file,
        "burmese_srt_url": f"/media/output/{burmese_srt_file}",
        "bilingual_srt_url": f"/media/output/{bilingual_srt_file}"
    }

def polish_segments_to_natural_burmese(
    segments: List[Dict[str, Any]],
    gemini_key: Optional[str] = None,
    openrouter_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Re-polishes any segment list into hyper-natural Burmese recap style.
    GUARANTEE: NEVER overwrites Burmese with raw Chinese text.
    """
    if (gemini_key and gemini_key.strip()) or (openrouter_key and openrouter_key.strip()):
        return batch_translate_segments_gemini(segments, gemini_key=gemini_key, openrouter_key=openrouter_key)

    for s in segments:
        current_my = s.get("my_text", "").strip()
        zh = s.get("zh_text", "").strip()

        # If current_my already contains Burmese characters, polish the Burmese text directly
        has_burmese = bool(re.search(r"[\u1000-\u109f]", current_my))
        if has_burmese:
            s["my_text"] = naturalize_burmese_recap(current_my)
        else:
            # If Burmese text was empty, translate from Chinese
            if zh:
                trans = translate_chinese_raw_google(zh)
                if trans and re.search(r"[\u1000-\u109f]", trans):
                    s["my_text"] = trans
                elif current_my:
                    s["my_text"] = current_my

        # Also populate English text if missing for bilingual subtitle editing
        if not s.get("en_text") and zh:
            s["en_text"] = translate_chinese_to_english(zh)

    return segments
