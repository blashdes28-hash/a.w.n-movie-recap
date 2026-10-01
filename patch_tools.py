import re

with open('static/js/api.js', 'r', encoding='utf-8') as f:
    api_js = f.read()

new_api = """
  async transcribeVideoAsync(file, sourceLang = 'zh', whisperModel = 'base', geminiApiKey = '') {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_lang', sourceLang);
    formData.append('whisper_model', whisperModel);
    if (geminiApiKey) {
      formData.append('gemini_api_key', geminiApiKey);
    }
    const res = await fetch('/api/transcribe/video-async', {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      let errText = 'Transcription failed';
      try { const err = await res.json(); errText = err.detail || errText; } catch(e) { errText = `HTTP Error ${res.status}: ${res.statusText}`; }
      throw new Error(errText);
    }
    return await res.json(); // returns {job_id, status}
  },

  async transcribeExistingVideoAsync(videoFile, sourceLang = 'zh', whisperModel = 'base', geminiApiKey = '') {
    const res = await fetch('/api/transcribe/existing-video-async', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_file: videoFile,
        source_lang: sourceLang,
        whisper_model: whisperModel,
        gemini_api_key: geminiApiKey
      })
    });
    if (!res.ok) {
      let errText = 'Transcription failed';
      try { const err = await res.json(); errText = err.detail || errText; } catch(e) { errText = `HTTP Error ${res.status}: ${res.statusText}`; }
      throw new Error(errText);
    }
    return await res.json(); // returns {job_id, status}
  },

  async checkTranscribeStatus(jobId) {
    const res = await fetch(`/api/transcribe/status/${jobId}`);
    if (!res.ok) throw new Error("Status check failed");
    return await res.json();
  },
"""

api_js = api_js.replace("transcribeVideo(file", new_api + "\n  transcribeVideo(file")
with open('static/js/api.js', 'w', encoding='utf-8') as f:
    f.write(api_js)

print('Patched api.js')

with open('static/js/tools.js', 'r', encoding='utf-8') as f:
    tools_js = f.read()

polling_logic_existing = """
      let jobRes = await API.transcribeExistingVideoAsync(videoFilename, srcLang, whisperModel, geminiApiKey);
      const jobId = jobRes.job_id;
      let res;
      while (true) {
          await new Promise(r => setTimeout(r, 5000));
          const statusObj = await API.checkTranscribeStatus(jobId);
          if (statusObj.status === 'done') {
              res = statusObj.result;
              break;
          } else if (statusObj.status === 'error') {
              throw new Error(statusObj.error || "Unknown error during background processing");
          }
      }
"""

polling_logic_new = """
      let jobRes = await API.transcribeVideoAsync(file, srcLang, whisperModel, geminiApiKey);
      const jobId = jobRes.job_id;
      let res;
      while (true) {
          await new Promise(r => setTimeout(r, 5000));
          const statusObj = await API.checkTranscribeStatus(jobId);
          if (statusObj.status === 'done') {
              res = statusObj.result;
              break;
          } else if (statusObj.status === 'error') {
              throw new Error(statusObj.error || "Unknown error during background processing");
          }
      }
"""

tools_js = tools_js.replace(
    "const res = await API.transcribeExistingVideo(videoFilename, srcLang, whisperModel, geminiApiKey);",
    polling_logic_existing
)
tools_js = tools_js.replace(
    "const res = await API.transcribeVideo(file, srcLang, whisperModel, geminiApiKey);",
    polling_logic_new
)

with open('static/js/tools.js', 'w', encoding='utf-8') as f:
    f.write(tools_js)

print('Patched tools.js')
