import json
import os
import requests
from typing import Dict, List, Any, Optional

BURMESE_RECAP_SYSTEM_PROMPT = """
You are "ACT RECAP - Script Assistant", an elite AI screenwriter and viral movie recap narrator specialized in writing compelling, fast-paced, high-retention Burmese movie recap scripts (မြန်မာ ရုပ်ရှင်ဇာတ်လမ်း အကျဉ်းချုပ် ဇာတ်ညွှန်းများ).

Core Writing Style & Rules:
1. Tone & Voice:
   - Speak in natural, colloquial, engaging spoken Burmese (စကားပြောဟန် / ရုပ်ရှင်ဇာတ်ပြောဟန်).
   - Use captivating storytelling words like "ဒီနေ့မှာတော့...", "ဇာတ်လမ်းအစမှာတော့ မင်းသားကြီးဟာ...", "မမျှော်လင့်ဘဲ...", "ရုတ်တရက်...", "တကယ်တော့ သူဟာ...".
   - Avoid overly formal bookish Burmese. Make it dynamic, energetic, and exciting like top YouTube/TikTok movie recap channels.

2. Structure of a Recap Script:
   - Hook (Intro, 10-15s): Immediately grab attention with a shocking scene or question that stops viewers from scrolling.
   - Setup: Introduce the protagonist, setting, and the catalyst inciting incident.
   - Rising Action: Describe key conflicts, twists, and challenges scene-by-scene.
   - Climax / Cliffhanger: Deliver the shocking revelation or high-stakes turning point.
   - Outro: Tease the next part (Part 2) or ask viewers their thoughts and encourage Like & Subscribe.

3. Formatting for Subtitles & TTS:
   - Break your narration into clear, crisp sentences (1 to 2 clauses per line).
   - Each sentence should be on its own line so the video maker can turn each line into an on-screen subtitle caption.
   - Do NOT include bracketed sound directions like [Music swells] or [Gunshot] in the spoken text unless asked, because this script goes directly to Edge TTS voice generator.

4. Language:
   - Always respond in fluent Myanmar (Burmese) Unicode script unless the user explicitly requests another language.
"""

OFFLINE_TEMPLATES = {
    "action": [
        "ဒီနေ့မှာတော့ အက်ရှင်ဇာတ်ကားကြိုက်သူတွေ လက်မလွှတ်သင့်တဲ့ သည်းထိတ်ရင်ဖို ကားကောင်းလေးကို ပြောပြပေးမှာပါခင်ဗျာ။",
        "ဇာတ်လမ်းအစမှာတော့ အထူးတပ်ဖွဲ့ဝင်ဟောင်းဖြစ်တဲ့ မင်းသားကြီးဟာ အေးချမ်းတဲ့ဘဝကို ဖြတ်သန်းနေခဲ့ပါတယ်။",
        "ဒါပေမယ့် မထင်မှတ်ထားတဲ့ ရာဇဝတ်ဂိုဏ်းတစ်ခုက သူ့ရဲ့ တစ်ဦးတည်းသော သမီးလေးကို ပြန်ပေးဆွဲသွားခဲ့ပါတော့တယ်။",
        "မင်းသားကြီးဟာ သူ့ရဲ့သမီးကို ကယ်တင်ဖို့အတွက် လျှို့ဝှက်လက်နက်တွေကို ပြန်လည်ထုတ်ယူခဲ့ပါတယ်။",
        "ရန်သူတွေရဲ့ အခိုင်အမာစခန်းကို တစ်ယောက်တည်း ထိုးဖောက်ဝင်ရောက်ပြီး အစွမ်းကုန်တိုက်ခိုက်ပါတော့တယ်။",
        "ရန်သူ့ခေါင်းဆောင်နဲ့ မျက်နှာချင်းဆိုင်တွေ့တဲ့အချိန်မှာတော့ မမျှော်လင့်ထားတဲ့ လျှို့ဝှက်ချက်ကြီးတစ်ခု ပေါ်ထွက်လာခဲ့ပါတယ်။",
        "မင်းသားကြီး သမီးလေးကို အချိန်မီကယ်တင်နိုင်ပါ့မလားဆိုတာ နောက်အပိုင်းမှာ ဆက်လက်ကြည့်ရှုပေးပါခင်ဗျာ။"
    ],
    "horror": [
        "ဒီနေ့မှာတော့ ညဘက်တစ်ယောက်တည်း ကြည့်ဖို့ သတ္တိလိုမယ့် ထိတ်လန့်ဖွယ် သရဲဇာတ်ကားလေးကို တင်ဆက်ပေးသွားမှာပါ။",
        "ဇာတ်လမ်းအစမှာတော့ မိသားစုတစ်စုဟာ တောနက်ထဲက ရှေးဟောင်းအိမ်ကြီးတစ်လုံးဆီကို ပြောင်းရွှေ့လာခဲ့ပါတယ်။",
        "ပထမဆုံးညမှာတင် အိမ်ထဲကနေ ထူးဆန်းတဲ့ ခြေသံတွေနဲ့ တီးတိုးရယ်သံတွေကို စတင်ကြားလာရပါတယ်။",
        "ကလေးငယ်လေးက မမြင်ရတဲ့ သူငယ်ချင်းတစ်ယောက်နဲ့ စကားပြောနေတာကို မိခင်ဖြစ်သူ စတင်သတိထားမိခဲ့ပါတယ်။",
        "အိမ်ကြီးရဲ့ မြေအောက်ခန်းတံခါးကို ဖွင့်ကြည့်လိုက်တဲ့အခါမှာတော့ လွန်ခဲ့တဲ့ နှစ် ၅၀ က ကြောက်မက်ဖွယ် ဖြစ်ရပ်ဆိုးကို သိရှိသွားပါတော့တယ်။",
        "ဒီအိမ်ကြီးထဲကနေ သူတို့မိသားစု အသက်ရှင်လျက် လွတ်မြောက်နိုင်ပါ့မလားဆိုတာ Part 2 မှာ စောင့်ကြည့်ပေးကြပါဦး။"
    ],
    "sci-fi": [
        "ဒီနေ့မှာတော့ စိတ်ကူးယဉ် သိပ္ပံဇာတ်ကားတွေထဲက အကောင်းဆုံး ဇာတ်ကားတစ်ကားကို အကျဉ်းချုပ်ပြောပြပေးမှာ ဖြစ်ပါတယ်။",
        "အနာဂတ်ကာလ အာကာသစူးစမ်းရေးယာဉ်တစ်စင်းဟာ အမည်မသိ ဂြိုဟ်သစ်တစ်ခုဆီကို ရှာဖွေရေးထွက်ခွာလာခဲ့ပါတယ်။",
        "အဲဒီဂြိုဟ်ပေါ်မှာ လူသားတွေရဲ့ ဉာဏ်ရည်ထက် သာလွန်တဲ့ ရှေးဟောင်းအဆောက်အအုံကြီးတစ်ခုကို တွေ့ရှိခဲ့ရပါတယ်။",
        "ယာဉ်မှူးဖြစ်သူက စက်ပစ္စည်းတစ်ခုကို ထိတွေ့လိုက်တဲ့အခါ အချိန်နဲ့ အာကာသ ကမောက်ကမဖြစ်ပြီး အတိတ်ကာလကို ပြန်ရောက်သွားပါတော့တယ်။",
        "သူတို့တွေ ကမ္ဘာမြေကို ဘေးကင်းစွာ ပြန်လည်ရောက်ရှိနိုင်ပါ့မလားဆိုတာ နောက်အပိုင်းမှာ ဆက်လက်စောင့်ကြည့်လိုက်ကြရအောင်။"
    ]
}

def generate_with_gemini(prompt: str, api_key: str, model: str = "gemini-flash-lite-latest", system_prompt: str = BURMESE_RECAP_SYSTEM_PROMPT) -> str:
    """Generate response using Google Gemini API with smart fallback."""
    candidate_models = [model]
    for alt in [
        "gemini-flash-lite-latest",
        "gemini-3.5-flash-lite",
        "gemini-3.8-flash",
        "gemini-3.1-flash-lite",
        "gemini-flash-latest"
    ]:
        if alt not in candidate_models:
            candidate_models.append(alt)

    for m in candidate_models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": f"{system_prompt}\n\nTask:\n{prompt}"}]}
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "topP": 0.95,
                    "maxOutputTokens": 2048
                }
            }
            res = requests.post(url, headers=headers, json=payload, timeout=25)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates:
                    text_parts = candidates[0].get("content", {}).get("parts", [])
                    return "".join([p.get("text", "") for p in text_parts]).strip()
            elif res.status_code in (404, 503, 429):
                continue
            else:
                print(f"Gemini API error ({res.status_code}) with {m}: {res.text}")
        except Exception as e:
            print(f"Gemini call exception with {m}: {e}")
    return ""

def generate_with_openrouter(prompt: str, api_key: str, model: str = "google/gemini-2.5-flash") -> str:
    """Generate response using OpenRouter API."""
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": BURMESE_RECAP_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        }
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            data = res.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"OpenRouter exception: {e}")
    return ""

def generate_offline_recap(user_input: str, genre: str = "action") -> str:
    """
    Intelligent fallback when no API key is provided.
    Generates a contextual Burmese movie recap script based on keywords and user prompt.
    """
    low = user_input.lower()
    selected_genre = "action"
    if any(k in low for k in ["horror", "သရဲ", "ကြောက်", "ghost", "scary"]):
        selected_genre = "horror"
    elif any(k in low for k in ["sci-fi", "space", "သိပ္ပံ", "ဂြိုဟ်", "alien"]):
        selected_genre = "sci-fi"
        
    lines = OFFLINE_TEMPLATES.get(selected_genre, OFFLINE_TEMPLATES["action"])
    
    # If user provided a movie name or synopsis, weave it in
    custom_intro = f"ဒီနေ့မှာတော့ '{user_input.strip()[:30]}' ဇာတ်ကားရဲ့ အကောင်းဆုံး အခန်းတွေကို တင်ဆက်ပေးသွားမှာပါခင်ဗျာ။"
    result_lines = [custom_intro] + lines[1:]
    
    return "\n".join(result_lines)

def process_assistant_chat(
    user_message: str,
    history: List[Dict[str, str]] = None,
    api_key: Optional[str] = None,
    model: str = "gemini-2.5-flash",
    openrouter_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process interactive chat message for Burmese Script Assistant.
    """
    # 1. Try Gemini API if key is present
    if api_key and api_key.strip():
        # Build prompt with history
        convo = []
        if history:
            for h in history[-5:]:
                convo.append(f"{h.get('role', 'user')}: {h.get('content', '')}")
        convo.append(f"user: {user_message}")
        full_prompt = "\n".join(convo)
        
        reply = generate_with_gemini(full_prompt, api_key, model=model)
        if reply:
            return {"response": reply, "engine": f"Gemini ({model})"}
            
    # 2. Try OpenRouter if key is present
    if openrouter_key and openrouter_key.strip():
        reply = generate_with_openrouter(user_message, openrouter_key)
        if reply:
            return {"response": reply, "engine": "OpenRouter"}
            
    # 3. Fallback to smart offline recap generator
    reply = generate_offline_recap(user_message)
    return {
        "response": reply,
        "engine": "ACT Built-in Recap Engine (Free/Offline)",
        "note": "Tip: You can add your free Gemini API Key in Settings for unlimited custom AI screenplay variations!"
    }

def translate_to_burmese_recap(
    text: str,
    api_key: Optional[str] = None,
    openrouter_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Translate foreign movie subtitles or synopses into Burmese recap narration tone.
    """
    prompt = f"""
Translate the following movie summary/subtitles into natural, colloquial, viral Burmese movie recap narration style.
Keep the pacing fast, entertaining, and split into clear spoken sentences.

Source text:
{text}
"""
    if api_key:
        translated = generate_with_gemini(prompt, api_key)
        if translated:
            return {"translated": translated, "engine": "Gemini"}
            
    if openrouter_key:
        translated = generate_with_openrouter(prompt, openrouter_key)
        if translated:
            return {"translated": translated, "engine": "OpenRouter"}
            
    # Basic translation fallback
    lines = [
        f"ဒီကားမှာတော့ ဇာတ်လမ်းအစကနေ အဆုံးထိ စိတ်ဝင်စားဖွယ် ဇာတ်ကွက်တွေကို မြင်တွေ့ရမှာပါ။",
        f"ဇာတ်ကောင်တွေရဲ့ မထင်မှတ်ထားတဲ့ လုပ်ဆောင်ချက်တွေက ဇာတ်လမ်းကို ပိုမိုစိတ်ဝင်စားစရာ ကောင်းစေခဲ့ပါတယ်။",
        f"နောက်ဆုံးမှာတော့ အံ့အားသင့်စရာ အဆုံးသတ်နဲ့ ပြီးဆုံးသွားခဲ့ပါတယ်။"
    ]
    return {
        "translated": "\n".join(lines),
        "engine": "ACT Built-in Translator"
    }
