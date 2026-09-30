# ACT RECAP - Burmese Movie Recap Studio (Web Version)

A full-featured web application for creating viral **Burmese Movie Recap Videos** (မြန်မာ ရုပ်ရှင်ဇာတ်လမ်း အကျဉ်းချုပ် ဗီဒီယိုများ), inspired by ACT Recap / ACTP Movie Studio.

---

## 🌟 Key Features

1. **TOOLS > Script Assistant (AI Screenplay Writer)**:
   - Interactive AI chatbot specifically tuned for Burmese movie recap storytelling.
   - Built-in live audio/video player with real-time synchronized Burmese subtitle captions.
   - Quick action prompt chips:
     - 🎬 *Full Movie Recap* (ဇာတ်ကား အစအဆုံး အကျဉ်းချုပ်)
     - 🔥 *Viral Intro Hook* (ဆွဲဆောင်မှုရှိသော အဖွင့်စကား)
     - 😱 *Plot Twist / Climax* (သည်းထိတ်ရင်ဖို အလှည့်အပြောင်း)
     - 😂 *Funny Commentary Style* (ဟာသနှော ဇာတ်ပြော)
   - One-click **"Studio သို့ပို့" (Send to Studio)** and **"စမ်းနားထောင်" (Listen TTS)**.

2. **Recap Studio Pipeline**:
   - **AI & Voice**:
     - Microsoft Edge Neural Burmese Voices:
       - `my-MM-ThihaNeural` (သီဟ - Male / Crisp narration)
       - `my-MM-NilarNeural` (နီလာ - Female / Warm storytelling)
     - Speech rate (`-10%`, `+0%`, `+10%`, `+20%`) and pitch controls.
     - Live voice audition button (`🔊 စမ်းသပ်နားထောင်မည်`).
   - **Telegram Account Integration**:
     - Automatically sends completed recap videos and narration audio directly to your Telegram personal chat or channel upon rendering completion (`Render ပြီးတိုင်း Video ကို Telegram PM ကို တိုက်ရိုက်ပို့ပေးပါမည်`).
   - **Subtitles Engine**:
     - Custom Burmese subtitle styling with native Unicode font (`C:/Windows/Fonts/mmrtext.ttf`).
     - Customizable font size, text colors (White, Yellow, Cyan), stroke outlines, and position.
   - **Title & Hook Banner**:
     - Top banner header (e.g. `PART 1 | ဇာတ်လမ်း အကျဉ်းချုပ်`).
   - **Watermark & Logo**:
     - Custom channel watermark text (e.g. `@actrecap`) with adjustable opacity and corner positions.
   - **Anti-Copyright & Cinematic Effects**:
     - 1.05x anti-copyright speed adjustment.
     - Horizontal mirror flip.
     - Synthetic cinematic background music (BGM) with automatic audio ducking under speech.

3. **Free Voice Studio**:
   - Standalone Burmese TTS tool with character counter, instant generation, waveform player, and direct MP3 & SRT download.

4. **Transcribe Tool**:
   - Upload any video or audio to extract timestamps and create synchronized Burmese subtitles.

5. **Stream Clip (BETA)**:
   - Video highlight trimmer & vertical 9:16 auto-cropper for TikTok / YouTube Shorts.

6. **Translate Tool**:
   - Translates foreign movie plots and subtitles into colloquial, entertaining Burmese recap narration style.

7. **Projects Manager & Gallery**:
   - Filter, preview, download (MP4 / MP3 / SRT), or push any project to Telegram with one click.

---

## 🚀 How to Run

### Method 1: Double-click
Double-click `start.bat` in this folder.

### Method 2: Terminal / Command Prompt
```bash
python run.py
```
Then open your browser at:
👉 **http://localhost:8000**

---

## ⚙️ Configuration (Optional)
In the **Settings** tab in the web UI, you can optionally configure:
- **Google Gemini API Key**: For AI script assistance. If left empty, ACT's built-in offline recap engine is used automatically.
- **Telegram Bot Token & Chat ID**: For automatic delivery to your Telegram app.
