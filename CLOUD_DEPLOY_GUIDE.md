# 🌐 ACT RECAP STUDIO - ၂၄ နာရီ Free Cloud ပေါ်တွင် အမြဲ Run ထားနည်း (100% Free)

ဤလမ်းညွှန်ချက်သည် မိမိကွန်ပျူတာ ဖွင့်စရာမလိုဘဲ ဖုန်း (Android/iOS) သို့မဟုတ် မည်သည့်နေရာမှမဆို အမြဲတမ်း ၂၄ နာရီ အသုံးပြုနိုင်စေရန် **Hugging Face Spaces (Docker)** ပေါ်တွင် အခမဲ့ Host လုပ်နည်း ဖြစ်ပါသည်။

---

## 🌟 အဘယ်ကြောင့် Hugging Face Spaces ကို အသုံးပြုသင့်သနည်း?
1. **100% အခမဲ့ဖြစ်ခြင်း:** Credit Card / Bank Card လုံးဝ မလိုပါ။
2. **၂၄ နာရီ မအိပ်ဘဲ Run ပေးခြင်း:** 24/7 Always Online (Free Tier မှာ ၁၆ GB RAM နှင့် 2 CPU အခမဲ့ ရရှိပါသည်)။
3. **FFmpeg & Whisper အပြည့်အဝ ထောက်ပံ့ခြင်း:** Docker စနစ်ဖြင့် ထည့်သွင်းထားပြီးဖြစ်၍ ဗီဒီယို တည်းဖြတ်ခြင်း၊ သီချင်းထည့်ခြင်း၊ စာတန်းထိုးခြင်း အားလုံး ကောင်းမွန်စွာ အလုပ်လုပ်ပါသည်။
4. **HTTPS Link အလိုအလျောက် ရရှိခြင်း:** `https://your-name-recap-studio.hf.space` ကဲ့သို့ ကိုယ်ပိုင် Web Link ရရှိပါမည်။

---

## 🚀 Hugging Face Spaces ပေါ်သို့ အဆင့် ၃ ဆင့်ဖြင့် Deploy လုပ်နည်း

### အဆင့် (၁) - Hugging Face အကောင့် ဖွင့်ပါ
1. [https://huggingface.co](https://huggingface.co) သို့ သွားပြီး **Sign Up** ပြုလုပ်ပါ။ (အခမဲ့)
2. Email confirm လုပ်ပါ။

### အဆင့် (၂) - Space အသစ် ဖန်တီးပါ
1. ညာဘက်အပေါ်ထောင့်ရှိ မိမိ Profile ပုံကို နှိပ်ပြီး **"New Space"** ကို နှိပ်ပါ (သို့မဟုတ် [https://huggingface.co/new-space](https://huggingface.co/new-space) သို့ သွားပါ)။
2. **Space name:** ဥပမာ `movie-recap-studio` ဟု ပေးပါ။
3. **License:** `mit` သို့မဟုတ် `openrail` ရွေးပါ။
4. **Select the Space SDK:** ⭐ **Docker** ကို မဖြစ်မနေ ရွေးချယ်ပါ။
5. **Docker template:** **Blank** ကို ရွေးပါ။
6. **Space hardware:** **CPU basic • 2 vCPU • 16 GB RAM • Free** ကို ရွေးပါ။
7. **Create Space** ခလုတ်ကို နှိပ်ပါ။

### အဆင့် (၃) - ဖိုင်များ Upload တင်ပါ
Space ဖန်တီးပြီးပါက **Files** tab သို့ သွားပါ:
1. **Add file** -> **Upload files** ကို နှိပ်ပါ။
2. မိမိစက်ရှိ `movie recap tool` ဖိုဒါထဲမှ ဖိုင်အားလုံးကို ဆွဲထည့် (Drag & Drop) ပါ:
   - `Dockerfile`
   - `requirements.txt`
   - `run.py`
   - `app/` (ဖိုဒါတစ်ခုလုံး)
   - `static/` (ဖိုဒါတစ်ခုလုံး)
   - `fonts/` (ဖိုဒါတစ်ခုလုံး)
3. အောက်ခြေရှိ **"Commit changes to main"** ခလုတ်ကို နှိပ်ပါ။
4. Space သည် မိနစ်အနည်းငယ်အတွင်း Docker Image ကို Build လုပ်ပြီး **"Running"** အခြေအနေသို့ ရောက်ရှိသွားပါမည်။

### အဆင့် (၄) - စတင်အသုံးပြုခြင်း
- Space စာမျက်နှာအပေါ်ရှိ `Embed this Space` သို့မဟုတ် Direct URL (ဥပမာ `https://username-movie-recap-studio.hf.space`) ကို ကူးယူပြီး ဖုန်း browser မှတစ်ဆင့် အချိန်မရွေး ၂၄ နာရီ အသုံးပြုနိုင်ပါပြီ!

---

## 🔒 Gemini API Key ထည့်သွင်းနည်း (Persistent Setting)
Space ၏ **Settings** -> **Variables and secrets** သို့ သွားပြီး:
- **New secret** နှိပ်ပါ:
  - Name: `GEMINI_API_KEY`
  - Value: မိမိ၏ Gemini API Key ထည့်ပါ
- ၎င်းသည် Cloud ပေါ်တွင် လုံခြုံစွာ သိမ်းဆည်းပေးထားမည်ဖြစ်ပြီး အလိုအလျောက် အလုပ်လုပ်မည်ဖြစ်ပါသည်။

---

## ⚡ Option 2: လက်ရှိ စက်မှ ၂၄ နာရီ Public Link ဖွင့်ထားနည်း
မိမိကွန်ပျူတာတွင် အမြဲဖွင့်ထားလိုပါက:
1. `start_public.bat` (သို့မဟုတ် `python start_public.py`) ကို Run ထားပါ။
2. ဖော်ပြပေးသော `https://xxxx.trycloudflare.com` link ဖြင့် ကမ္ဘာ့မည်သည့်နေရာမှမဆို အသုံးပြုနိုင်ပါသည်။
