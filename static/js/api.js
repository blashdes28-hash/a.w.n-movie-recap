// API client for ACT RECAP
const API = {
  async getStatus() {
    const res = await fetch('/api/status');
    return await res.json();
  },

  async getSettings() {
    const res = await fetch('/api/settings');
    return await res.json();
  },

  async saveSettings(data) {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await res.json();
  },

  async getVoices() {
    const res = await fetch('/api/tts/voices');
    return await res.json();
  },

  async previewVoice(text, voice) {
    const res = await fetch('/api/tts/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice })
    });
    return await res.json();
  },

  async generateTTS(text, voice = 'my-MM-ThihaNeural', rate = '+0%', pitch = '+0Hz') {
    const res = await fetch('/api/tts/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice, rate, pitch })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'TTS generation failed');
    }
    return await res.json();
  },

  async chatScript(message, history = [], model = 'gemini-2.5-flash') {
    const res = await fetch('/api/script/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history, model })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Chat request failed');
    }
    return await res.json();
  },

  async translateText(text) {
    const res = await fetch('/api/translate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    return await res.json();
  },

  async getProjects() {
    const res = await fetch('/api/projects');
    return await res.json();
  },

  async getProject(id) {
    const res = await fetch(`/api/projects/${id}`);
    return await res.json();
  },

  async createProject(data) {
    const res = await fetch('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await res.json();
  },

  async updateProject(id, data) {
    const res = await fetch(`/api/projects/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await res.json();
  },

  async deleteProject(id) {
    const res = await fetch(`/api/projects/${id}`, { method: 'DELETE' });
    return await res.json();
  },

  async renderProject(projectId, renderSettings) {
    const res = await fetch(`/api/projects/${projectId}/render`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(renderSettings)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Render initiation failed');
    }
    return await res.json();
  },

  async getRenderStatus(jobId) {
    const res = await fetch(`/api/render/status/${jobId}`);
    return await res.json();
  },

  async testTelegram(botToken, chatId) {
    const res = await fetch('/api/telegram/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bot_token: botToken, chat_id: chatId })
    });
    return await res.json();
  },

  async sendToTelegram(projectId) {
    const res = await fetch(`/api/projects/${projectId}/send-telegram`, {
      method: 'POST'
    });
    return await res.json();
  },

  async uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });
    return await res.json();
  },

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

  transcribeVideo(file, sourceLang = 'zh', whisperModel = 'base', geminiApiKey = '') {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_lang', sourceLang);
    formData.append('whisper_model', whisperModel);
    if (geminiApiKey) {
      formData.append('gemini_api_key', geminiApiKey);
    }
    const res = await fetch('/api/transcribe/video', {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      let errText = 'Transcription failed';
      try {
        const err = await res.json();
        errText = err.detail || errText;
      } catch (e) {
        errText = `HTTP Error ${res.status}: ${res.statusText}`;
      }
      throw new Error(errText);
    }
    return await res.json();
  },

  async transcribeExistingVideo(videoFile, sourceLang = 'zh', whisperModel = 'base', geminiApiKey = '') {
    const res = await fetch('/api/transcribe/existing-video', {
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
      try {
        const err = await res.json();
        errText = err.detail || errText;
      } catch (e) {
        errText = `HTTP Error ${res.status}: ${res.statusText}`;
      }
      throw new Error(errText);
    }
    return await res.json();
  },


  async transcribeSrt(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/transcribe/srt', {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'SRT Translation failed');
    }
    return await res.json();
  },

  async exportCustomSrt(segments) {
    const res = await fetch('/api/transcribe/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ segments })
    });
    return await res.json();
  },

  async polishSegments(segments) {
    const res = await fetch('/api/transcribe/polish', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ segments })
    });
    return await res.json();
  },

  async getFonts() {
    const res = await fetch('/api/fonts');
    return await res.json();
  },

  async uploadFont(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/fonts/upload', {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Font upload failed');
    }
    return await res.json();
  },

  async downloadRednoteVideo(url) {
    const res = await fetch('/api/rednote/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'RedNote video download failed');
    }
    return await res.json();
  },

  async muteVideo(videoFile) {
    const res = await fetch('/api/video/mute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_file: videoFile })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to create muted video');
    }
    return await res.json();
  },

  async uploadLogo(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/logo/upload', {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Logo upload failed');
    }
    return await res.json();
  },

  async downloadYouTubeBgm(url) {
    const res = await fetch('/api/audio/youtube-bgm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'YouTube audio extraction failed');
    }
    return await res.json();
  },

  async uploadBgm(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/audio/upload-bgm', {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'BGM upload failed');
    }
    return await res.json();
  },

  async getBgmPresets() {
    const res = await fetch('/api/audio/presets');
    if (!res.ok) return [];
    return await res.json();
  },

  async generateCaption(title, segments) {
    const res = await fetch('/api/caption/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, segments })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Caption generation failed');
    }
    return await res.json();
  },

  async burnSubtitledVideo(arg1, segments, subMode = 'my', fontName = 'Pyidaungsu', fontSize = 34, subColor = '#ffffff', styleType = 'box', positionType = 'bottom', yPercent = 0.86) {
    let payload = {};
    if (typeof arg1 === 'object' && arg1 !== null && !Array.isArray(arg1)) {
      payload = {
        video_file: arg1.videoFile,
        segments: arg1.segments,
        sub_mode: arg1.subMode || 'my',
        font_name: arg1.fontName || 'Pyidaungsu',
        font_size: arg1.fontSize || 34,
        sub_color: arg1.subColor || '#ffffff',
        style_type: arg1.styleType || 'box',
        position_type: arg1.positionType || 'bottom',
        y_percent: arg1.yPercent !== undefined ? arg1.yPercent : 0.86,
        aspect_ratio: arg1.aspectRatio || 'original',
        resize_mode: arg1.resizeMode || 'fit_blur',
        blur_enabled: !!arg1.blurEnabled,
        blur_y_percent: arg1.blurYPercent !== undefined ? arg1.blurYPercent : 0.56,
        blur_height_percent: arg1.blurHeightPercent !== undefined ? arg1.blurHeightPercent : 0.08,
        logo_file: arg1.logoFile || null,
        logo_pos: arg1.logoPos || 'top-right',
        logo_size_percent: arg1.logoSizePercent !== undefined ? arg1.logoSizePercent : 0.18,
        logo_opacity: arg1.logoOpacity !== undefined ? arg1.logoOpacity : 0.85,
        orig_audio_volume: arg1.origAudioVolume !== undefined ? arg1.origAudioVolume : 1.0,
        bgm_file: arg1.bgmFile || null,
        bgm_volume: arg1.bgmVolume !== undefined ? arg1.bgmVolume : 0.35,
        bgm_loop: arg1.bgmLoop !== undefined ? arg1.bgmLoop : true,
        export_quality: arg1.exportQuality || 'very_high'
      };
    } else {
      payload = {
        video_file: arg1,
        segments: segments,
        sub_mode: subMode,
        font_name: fontName,
        font_size: fontSize,
        sub_color: subColor,
        style_type: styleType,
        position_type: positionType,
        y_percent: yPercent,
        export_quality: 'very_high'
      };
    }

    const res = await fetch('/api/transcribe/burn-video', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Burning subtitles to video failed');
    }
    return await res.json();
  },

  async pollBurnStatus(jobId) {
    const res = await fetch(`/api/transcribe/burn-status/${jobId}`);
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to check burn status');
    }
    return await res.json();
  },

  // --- License Management APIs ---
  async activateLicense(licenseKey, deviceId, deviceInfo) {
    const res = await fetch('/api/license/activate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        license_key: licenseKey,
        device_id: deviceId,
        device_info: deviceInfo || navigator.userAgent
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'License activation failed');
    }
    return await res.json();
  },

  async checkLicense(licenseKey, deviceId) {
    const res = await fetch('/api/license/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        license_key: licenseKey,
        device_id: deviceId
      })
    });
    return await res.json();
  },

  async generateLicenses(plan, count, expiresDays, notes) {
    const res = await fetch('/api/license/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        plan: plan || 'Lifetime VIP',
        count: parseInt(count, 10) || 1,
        expires_days: expiresDays ? parseInt(expiresDays, 10) : null,
        notes: notes || ''
      })
    });
    return await res.json();
  },

  async getLicenses() {
    const res = await fetch('/api/license/list');
    return await res.json();
  },

  async resetLicenseDevice(licenseKey) {
    const res = await fetch('/api/license/reset-device', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ license_key: licenseKey })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to reset device binding');
    }
    return await res.json();
  },

  async revokeLicense(licenseKey) {
    const res = await fetch('/api/license/revoke', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ license_key: licenseKey })
    });
    return await res.json();
  },

  async deleteLicense(licenseKey) {
    const res = await fetch('/api/license/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ license_key: licenseKey })
    });
    return await res.json();
  },

  // --- Gemini API Key Diagnostic ---
  async testGemini(apiKey) {
    const key = apiKey || Tools.getGeminiKey();
    const res = await fetch('/api/gemini/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gemini_api_key: key, api_key: key })
    });
    return await res.json();
  }
};

window.API = API;
