import re

# 1. Update tools.js
with open('static/js/tools.js', 'r', encoding='utf-8') as f:
    tools_js = f.read()

tools_js = tools_js.replace("const res = await API.transcribeSrt(file);", "const res = await API.transcribeSrt(file, this.getGeminiKey());")

with open('static/js/tools.js', 'w', encoding='utf-8') as f:
    f.write(tools_js)

# 2. Update api.js
with open('static/js/api.js', 'r', encoding='utf-8') as f:
    api_js = f.read()

old_srt = """  async transcribeSrt(file) {
    const formData = new FormData();
    formData.append('file', file);"""

new_srt = """  async transcribeSrt(file, geminiApiKey = '') {
    const formData = new FormData();
    formData.append('file', file);
    if (geminiApiKey) formData.append('gemini_api_key', geminiApiKey);"""

api_js = api_js.replace(old_srt, new_srt)

with open('static/js/api.js', 'w', encoding='utf-8') as f:
    f.write(api_js)

# 3. Update main.py
with open('app/main.py', 'r', encoding='utf-8') as f:
    main_py = f.read()

old_py = """@app.post("/api/transcribe/srt")
async def transcribe_srt_endpoint(file: UploadFile = File(...)):
    try:
        content_bytes = await file.read()
        srt_text = content_bytes.decode("utf-8", errors="replace")
        config = load_config()
        gemini_key = config.get("gemini_api_key")
        openrouter_key = config.get("openrouter_api_key")"""

new_py = """@app.post("/api/transcribe/srt")
async def transcribe_srt_endpoint(file: UploadFile = File(...), gemini_api_key: str = Form(None)):
    try:
        content_bytes = await file.read()
        srt_text = content_bytes.decode("utf-8", errors="replace")
        config = load_config()
        gemini_key = gemini_api_key or config.get("gemini_api_key")
        openrouter_key = config.get("openrouter_api_key")"""

main_py = main_py.replace(old_py, new_py)

with open('app/main.py', 'w', encoding='utf-8') as f:
    f.write(main_py)

print("Patched srt endpoints successfully")
