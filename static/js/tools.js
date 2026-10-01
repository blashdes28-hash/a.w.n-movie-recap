// Transcribe, Chinese-to-Burmese Timeline Studio, and Translate Tools
const Tools = {
  currentSegments: [],
  activeVideoUrl: null,
  activeVideoElement: null,
  uploadedVideoFilename: null,
  uploadedLogoFilename: null,
  uploadedLogoUrl: null,
  availableFonts: [],

  init() {
    this.bindEvents();
    this.loadAvailableFonts();
    this.loadAiStatus();
  },

  async loadAiStatus() {
    try {
      if (typeof API === 'undefined' || typeof API.getStatus !== 'function') return;
      const res = await API.getStatus();
      const badge = document.getElementById('transcribe-ai-badge');
      const input = document.getElementById('transcribe-gemini-key-input');
      
      const isConfigured = res && (res.gemini_api_configured || res.openrouter_configured);
      if (badge) {
        if (isConfigured) {
          badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> <span class="text-emerald-300 font-bold">🟢 AI Active (Gemini 2.5 Flash)</span>`;
          badge.className = "px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-950/50 border border-emerald-500/40 text-emerald-300 flex items-center gap-1.5 shadow-sm";
        } else {
          badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-amber-400"></span> <span class="text-amber-300 font-medium">🟡 Offline Recap Dictionary Active</span>`;
          badge.className = "px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-950/40 border border-amber-500/40 text-amber-300 flex items-center gap-1.5 shadow-sm";
        }
      }

      if (input && !input.value) {
        try {
          const settings = await API.getSettings();
          if (settings && settings.gemini_api_key) {
            input.value = settings.gemini_api_key;
          }
        } catch (_) {}
      }
    } catch (e) {
      console.warn("Could not load AI status:", e);
    }
  },

  async saveGeminiKey() {
    const input = document.getElementById('transcribe-gemini-key-input');
    const btn = document.getElementById('btn-save-gemini-key');
    if (!input) return;
    const key = input.value.trim();

    if (btn) {
      btn.innerHTML = `<span>⏳</span> Saving...`;
      btn.disabled = true;
    }

    try {
            if (window.currentUserEmail) {
         localStorage.setItem('gemini_key_' + window.currentUserEmail, key);
      } else {
         localStorage.setItem('gemini_key_global', key);
      }
      
      App.showToast('✅ Gemini API Key သိမ်းဆည်းပြီးပါပြီ! AI စကားပြောဟန် စနစ် အသုံးပြုနိုင်ပါပြီ။', 'success');
      await this.loadAiStatus();
    } catch (e) {
      App.showToast('⚠️ Key သိမ်းဆည်းရာတွင် အမှားဖြစ်ခဲ့ပါသည်: ' + e.message, 'error');
    } finally {
      if (btn) {
        btn.innerHTML = `<span>💾</span> Save Key`;
        btn.disabled = false;
      }
    }
  },

  toggleGeminiKeyVisibility() {
    const input = document.getElementById('transcribe-gemini-key-input');
    if (input) {
      input.type = input.type === 'password' ? 'text' : 'password';
    }
  },

  bindEvents() {
    // Video timeupdate sync with subtitle table and overlay
    const video = document.getElementById('transcribe-preview-video');
    if (video) {
      this.activeVideoElement = video;
      video.addEventListener('timeupdate', () => this.syncVideoTimeline());
    }

    // Bind download subtitled video button
    const dlSubVideoBtn = document.getElementById('btn-dl-subtitled-video');
    if (dlSubVideoBtn) {
      dlSubVideoBtn.addEventListener('click', () => this.downloadSubtitledVideo());
    }
  },

  async loadAvailableFonts() {
    try {
      if (typeof API !== 'undefined' && typeof API.getFonts === 'function') {
        const fonts = await API.getFonts();
        this.availableFonts = fonts || [];
        this.populateFontSelects(this.availableFonts);
        this.injectFontStyles(this.availableFonts);
      }
    } catch (e) {
      console.warn("Could not load fonts:", e);
    }
  },

  populateFontSelects(fonts) {
    const selects = [
      document.getElementById('transcribe-select-font'),
      document.getElementById('studio-sub-font')
    ];
    selects.forEach(sel => {
      if (!sel) return;
      const curVal = sel.value || 'Pyidaungsu';
      sel.innerHTML = fonts.map(f => `
        <option value="${f.family}" ${f.family === curVal ? 'selected' : ''}>${f.name}</option>
      `).join('');
    });
  },

  injectFontStyles(fonts) {
    let styleEl = document.getElementById('dynamic-myanmar-fonts');
    if (!styleEl) {
      styleEl = document.createElement('style');
      styleEl.id = 'dynamic-myanmar-fonts';
      document.head.appendChild(styleEl);
    }
    const fontFaces = fonts.map(f => `
      @font-face {
        font-family: '${f.family}';
        src: url('/fonts/${encodeURIComponent(f.file)}') format('truetype');
        font-display: swap;
      }
    `).join('\n');
    styleEl.innerHTML = fontFaces;
  },

  async handleFontUpload(file) {
    if (!file) return;
    try {
      App.showToast(`⏳ Font "${file.name}" တင်သွင်းနေပါသည်...`, 'info');
      const res = await API.uploadFont(file);
      if (res && res.fonts) {
        this.availableFonts = res.fonts;
        this.populateFontSelects(res.fonts);
        this.injectFontStyles(res.fonts);
        
        // Auto-select the newly uploaded font
        const sel = document.getElementById('transcribe-select-font');
        if (sel) {
          const match = res.fonts.find(f => f.file === res.filename);
          if (match) sel.value = match.family;
        }
        this.renderTimelineTable();
        this.syncVideoTimeline();
        App.showToast(`✅ Font "${file.name}" အောင်မြင်စွာ တင်သွင်းပြီးပါပြီ!`, 'success');
      }
    } catch (e) {
      App.showToast('Font upload failed: ' + e.message, 'error');
    }
  },

  onSubModeChange() {
    this.syncVideoTimeline();
  },

  onFontChange() {
    this.renderTimelineTable();
    this.syncVideoTimeline();
  },

  onStyleChange() {
    this.syncVideoTimeline();
  },

  onPositionChange(val) {
    const slider = document.getElementById('transcribe-pos-slider');
    const label = document.getElementById('transcribe-pos-label');
    if (val === 'top') {
      if (slider) slider.value = 10;
      if (label) label.textContent = '10%';
    } else if (val === 'middle') {
      if (slider) slider.value = 50;
      if (label) label.textContent = '50%';
    } else if (val === 'bottom') {
      if (slider) slider.value = 86;
      if (label) label.textContent = '86%';
    }
    this.syncVideoTimeline();
  },

  onPositionSliderChange(val) {
    const label = document.getElementById('transcribe-pos-label');
    if (label) label.textContent = val + '%';
    const posSelect = document.getElementById('transcribe-sub-pos');
    if (posSelect && posSelect.value !== 'custom') {
      posSelect.value = 'custom';
    }
    this.syncVideoTimeline();
  },

  // 0. RedNote (小红书) HD Downloader & Automatic Transcribe
  async handleRednoteDownload() {
    const input = document.getElementById('rednote-url-input');
    const btn = document.getElementById('btn-rednote-download');
    const statusEl = document.getElementById('transcribe-status');
    const rawVal = input ? input.value.trim() : '';

    if (!rawVal) {
      App.showToast('ကျေးဇူးပြု၍ RedNote link သို့မဟုတ် mobile share text ကို ထည့်သွင်းပါ', 'warning');
      return;
    }

    if (btn) {
      btn.innerHTML = `<span>⏳</span> HD ဒေါင်းလုဒ်ဆွဲနေပါသည်...`;
      btn.disabled = true;
    }
    if (statusEl) {
      statusEl.innerHTML = `<span class="animate-spin inline-block mr-1">⏳</span> RedNote မှ HD ဗီဒီယိုကို watermark ကင်းစင်စွာ ရယူနေပါသည်...`;
    }
    App.showToast('⏳ RedNote HD Video ဒေါင်းလုဒ် စတင်နေပါသည်...', 'info');

    try {
      const res = await API.downloadRednoteVideo(rawVal);
      if (!res || !res.video_file) {
        throw new Error('Video download returned invalid response');
      }

      this.uploadedVideoFilename = res.video_file;
      this.activeVideoUrl = res.video_url;
      this.currentVideoTitle = res.title || 'RedNote HD Video';

      // Update preview video player
      const video = document.getElementById('transcribe-preview-video');
      if (video && res.video_url) {
        video.src = res.video_url;
      }

      App.showToast(`🎉 RedNote "${res.title || 'HD Video'}" (${res.file_size_mb} MB) ဒေါင်းလုဒ် အောင်မြင်ပါသည်! Timeline စတင် ဖမ်းယူနေပါသည်...`, 'success');

      // Automatically trigger transcription & timeline translation
      await this.transcribeDownloadedVideo(res.video_file);

    } catch (e) {
      console.error(e);
      if (statusEl) {
        statusEl.innerHTML = `<span class="text-rose-400 font-semibold">⚠️ ဒေါင်းလုဒ် မအောင်မြင်ပါ: ${e.message}</span>`;
      }
      App.showToast('⚠️ RedNote error: ' + e.message, 'error');
    } finally {
      if (btn) {
        btn.innerHTML = `<span>⬇</span> HD ဒေါင်းလုဒ်ဆွဲပြီး စာတန်းထိုးမည်`;
        btn.disabled = false;
      }
    }
  },

  startTranscribeProgressMonitor(estimatedTotalSec = 35) {
    const modal = document.getElementById('transcribe-loading-state');
    const phaseEl = document.getElementById('transcribe-progress-phase');
    const percentEl = document.getElementById('transcribe-percent-text');
    const barEl = document.getElementById('transcribe-progress-bar');
    const etaEl = document.getElementById('transcribe-eta-text');

    if (modal) modal.classList.remove('hidden');

    if (this._progressInterval) {
      clearInterval(this._progressInterval);
    }

    const startTime = Date.now();
    let currentPercent = 4;
    
    const updateUI = (pct, phaseText, etaSec) => {
      const rounded = Math.min(98, Math.max(1, Math.round(pct)));
      if (percentEl) percentEl.textContent = `${rounded}%`;
      if (barEl) barEl.style.width = `${rounded}%`;
      if (phaseEl && phaseText) phaseEl.textContent = phaseText;
      if (etaEl) {
        if (etaSec > 60) {
          const m = Math.floor(etaSec / 60);
          const s = Math.round(etaSec % 60);
          etaEl.textContent = `~${m} မိနစ် ${s} စက္ကန့်`;
        } else {
          etaEl.textContent = `~${Math.max(1, Math.round(etaSec))} စက္ကန့်`;
        }
      }
    };

    updateUI(currentPercent, "အသံဖိုင် သီးသန့် ခွဲထုတ်နေပါသည် (Extracting Audio)...", estimatedTotalSec);

    this._progressInterval = setInterval(() => {
      const elapsedSec = (Date.now() - startTime) / 1000;
      const remainingSec = Math.max(1, estimatedTotalSec - elapsedSec);

      if (elapsedSec < 3) {
        currentPercent = 4 + (elapsedSec / 3) * 16;
        updateUI(currentPercent, "အသံဖိုင် သီးသန့် ခွဲထုတ်နေပါသည် (Extracting Audio)...", remainingSec);
      } else if (elapsedSec < estimatedTotalSec * 0.55) {
        const factor = (elapsedSec - 3) / Math.max(1, (estimatedTotalSec * 0.55 - 3));
        currentPercent = 20 + factor * 45;
        updateUI(currentPercent, "Whisper AI ဖြင့် တရုတ်စကားပြောများကို စက္ကန့်မလွဲ ဖမ်းယူနေပါသည် (Speech Recognition)...", remainingSec);
      } else if (elapsedSec < estimatedTotalSec * 0.88) {
        const factor = (elapsedSec - estimatedTotalSec * 0.55) / Math.max(1, (estimatedTotalSec * 0.33));
        currentPercent = 65 + factor * 26;
        updateUI(currentPercent, "Google Gemini AI ဖြင့် မြန်မာဇာတ်လမ်းပြော စကားပြေဟန်သို့ ပြန်ဆိုနေပါသည် (Storytelling Translation)...", remainingSec);
      } else {
        currentPercent = Math.min(97, currentPercent + 0.3);
        updateUI(currentPercent, "စာတန်းထိုး Timeline နှင့် တိုက်ဆိုင်စစ်ဆေးနေပါသည် (Finalizing Subtitles)...", Math.max(1, remainingSec));
      }
    }, 400);
  },

  finishTranscribeProgressMonitor() {
    if (this._progressInterval) {
      clearInterval(this._progressInterval);
      this._progressInterval = null;
    }
    const percentEl = document.getElementById('transcribe-percent-text');
    const barEl = document.getElementById('transcribe-progress-bar');
    const phaseEl = document.getElementById('transcribe-progress-phase');
    const etaEl = document.getElementById('transcribe-eta-text');
    const modal = document.getElementById('transcribe-loading-state');

    if (percentEl) percentEl.textContent = '100%';
    if (barEl) barEl.style.width = '100%';
    if (phaseEl) phaseEl.textContent = '✓ စာတန်းထိုးနှင့် အသံဖမ်းယူမှု အောင်မြင်စွာ ပြီးဆုံးပါပြီ (Complete)!';
    if (etaEl) etaEl.textContent = '0 စက္ကန့်';

    setTimeout(() => {
      if (modal) modal.classList.add('hidden');
    }, 900);
  },

  async transcribeDownloadedVideo(videoFilename) {
    const statusEl = document.getElementById('transcribe-status');
    const resultBox = document.getElementById('transcribe-result-box');
    const srcLang = document.getElementById('transcribe-source-lang')?.value || 'zh';
    const whisperModel = document.getElementById('transcribe-whisper-model')?.value || 'base';

    this.startTranscribeProgressMonitor(30);
    if (statusEl) {
      statusEl.innerHTML = `<span class="animate-spin inline-block mr-1">⏳</span> ဗီဒီယိုမှ စကားပြောများကို Whisper ဖြင့် ဖမ်းယူပြီး မြန်မာဘာသာသို့ ပြန်ဆိုနေပါသည်...`;
    }

    try {
      const geminiApiKey = Tools.getGeminiKey();
      
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

      this.currentSegments = res.segments || [];
      this.renderTimelineTable();

      const dlMy = document.getElementById('btn-dl-burmese-srt');
      const dlBi = document.getElementById('btn-dl-bilingual-srt');
      if (dlMy) dlMy.href = res.burmese_srt_url;
      if (dlBi) dlBi.href = res.bilingual_srt_url;

      if (resultBox) resultBox.classList.remove('hidden');
      if (statusEl) {
        statusEl.innerHTML = `<span class="text-emerald-400 font-semibold">✓ အောင်မြင်ပါသည်! စာကြောင်းရေ ${this.currentSegments.length} ကြောင်းကို အချိန်နှင့်တကွ ဘာသာပြန်ဆိုပြီးပါပြီ။</span>`;
      }
      this.finishTranscribeProgressMonitor();
      App.showToast(`✅ စာကြောင်းရေ (${this.currentSegments.length}) လိုင်းကို Timeline အတိအကျဖြင့် ဘာသာပြန်ပြီးပါပြီ!`, 'success');

      // Auto generate viral caption & hashtags
      this.generateViralCaption();
    } catch (e) {
      console.error(e);
      if (this._progressInterval) clearInterval(this._progressInterval);
      const modal = document.getElementById('transcribe-loading-state');
      if (modal) modal.classList.add('hidden');
      if (statusEl) {
        statusEl.innerHTML = `<span class="text-rose-400 font-semibold">⚠️ Transcription error: <span class="err-text"></span></span>`;
        statusEl.querySelector('.err-text').innerText = e.message || 'Network Timeout / API Error';
      }
      App.showToast('Transcription error: ' + (e.message || 'Unknown'), 'error');
    }
  },

  // Blur band event handlers
  onBlurToggleChange() {
    const isChecked = document.getElementById('transcribe-blur-enable')?.checked || false;
    const controls = document.getElementById('transcribe-blur-controls');
    if (controls) {
      if (isChecked) {
        controls.classList.remove('opacity-40', 'pointer-events-none');
      } else {
        controls.classList.add('opacity-40', 'pointer-events-none');
      }
    }
    this.updateBlurGuideOverlay();
  },

  onBlurParamsChange() {
    const yVal = document.getElementById('transcribe-blur-y-slider')?.value || '56';
    const hVal = document.getElementById('transcribe-blur-h-slider')?.value || '8';
    const yLabel = document.getElementById('transcribe-blur-y-label');
    const hLabel = document.getElementById('transcribe-blur-h-label');
    if (yLabel) yLabel.textContent = yVal + '%';
    if (hLabel) hLabel.textContent = hVal + '%';
    this.updateBlurGuideOverlay();
  },

  updateBlurGuideOverlay() {
    const overlay = document.getElementById('video-blur-guide-overlay');
    const isChecked = document.getElementById('transcribe-blur-enable')?.checked || false;
    if (!overlay) return;

    if (!isChecked) {
      overlay.classList.add('hidden');
      return;
    }

    const yVal = parseFloat(document.getElementById('transcribe-blur-y-slider')?.value || '56');
    const hVal = parseFloat(document.getElementById('transcribe-blur-h-slider')?.value || '8');

    overlay.style.top = yVal + '%';
    overlay.style.height = hVal + '%';
    overlay.classList.remove('hidden');
  },

  // Channel Logo handlers
  async handleLogoUpload(file) {
    if (!file) return;
    try {
      App.showToast(`⏳ Logo "${file.name}" တင်သွင်းနေပါသည်...`, 'info');
      const res = await API.uploadLogo(file);
      if (res && res.filename) {
        this.uploadedLogoFilename = res.filename;
        this.uploadedLogoUrl = res.url;
        
        const statusSpan = document.getElementById('transcribe-logo-status');
        if (statusSpan) statusSpan.textContent = '✓ Logo Added';

        const logoImg = document.getElementById('video-logo-img');
        if (logoImg) logoImg.src = res.url;

        this.updateLogoOverlay();
        App.showToast(`✅ Channel Logo တင်သွင်းပြီးပါပြီ! Live preview တွင် ကြည့်ရှုနိုင်ပါသည်။`, 'success');
      }
    } catch (e) {
      App.showToast('Logo upload error: ' + e.message, 'error');
    }
  },

  onLogoParamsChange() {
    const sizeVal = document.getElementById('transcribe-logo-size')?.value || '18';
    const opVal = document.getElementById('transcribe-logo-opacity')?.value || '85';
    const sizeLabel = document.getElementById('transcribe-logo-size-label');
    const opLabel = document.getElementById('transcribe-logo-opacity-label');
    if (sizeLabel) sizeLabel.textContent = sizeVal + '%';
    if (opLabel) opLabel.textContent = opVal + '%';
    this.updateLogoOverlay();
  },

  updateLogoOverlay() {
    const overlay = document.getElementById('video-logo-preview-overlay');
    if (!overlay) return;

    if (!this.uploadedLogoUrl) {
      overlay.classList.add('hidden');
      return;
    }

    const pos = document.getElementById('transcribe-logo-pos')?.value || 'top-right';
    const sizeVal = parseFloat(document.getElementById('transcribe-logo-size')?.value || '18');
    const opVal = parseFloat(document.getElementById('transcribe-logo-opacity')?.value || '85') / 100.0;

    overlay.style.top = 'auto';
    overlay.style.bottom = 'auto';
    overlay.style.left = 'auto';
    overlay.style.right = 'auto';

    if (pos === 'top-left') {
      overlay.style.top = '10px';
      overlay.style.left = '10px';
    } else if (pos === 'bottom-right') {
      overlay.style.bottom = '10px';
      overlay.style.right = '10px';
    } else if (pos === 'bottom-left') {
      overlay.style.bottom = '10px';
      overlay.style.left = '10px';
    } else {
      // top-right
      overlay.style.top = '10px';
      overlay.style.right = '10px';
    }

    overlay.style.width = sizeVal + '%';
    overlay.style.opacity = opVal;
    overlay.classList.remove('hidden');
  },

  onVideoLayoutChange() {
    const ratio = document.getElementById('transcribe-aspect-ratio')?.value || 'original';
    App.showToast(`📐 Video format set to: ${ratio.toUpperCase()}`, 'info');
  },

  // Audio Anti-Copyright & BGM Mixing handlers
  onOrigVolSliderChange(val) {
    const num = parseInt(val, 10);
    this.origAudioVolume = num / 100.0;
    const label = document.getElementById('transcribe-orig-vol-label');
    if (label) {
      label.textContent = num === 0 ? 'Muted (0%)' : num + '%';
    }
  },

  setOrigAudioVolume(pct) {
    const slider = document.getElementById('transcribe-orig-vol-slider');
    if (slider) slider.value = pct;
    this.onOrigVolSliderChange(pct);
  },

  onBgmVolSliderChange(val) {
    const num = parseInt(val, 10);
    this.bgmVolume = num / 100.0;
    const label = document.getElementById('transcribe-bgm-vol-label');
    if (label) label.textContent = num + '%';
    const audio = document.getElementById('transcribe-bgm-audio');
    if (audio) audio.volume = this.bgmVolume;
  },

  async handleYouTubeBgmDownload() {
    const input = document.getElementById('transcribe-yt-bgm-input');
    const btn = document.getElementById('btn-yt-bgm-dl');
    const url = input ? input.value.trim() : '';
    if (!url) {
      App.showToast('ကျေးဇူးပြု၍ YouTube သီချင်း Link ကို ထည့်သွင်းပါ', 'warning');
      return;
    }

    if (btn) {
      btn.innerHTML = `<span>⏳</span> ဒေါင်းလုဒ်ဆွဲနေပါသည်...`;
      btn.disabled = true;
    }
    App.showToast('⏳ YouTube မှ Audio သီချင်းကို ရယူနေပါသည်...', 'info');

    try {
      const res = await API.downloadYouTubeBgm(url);
      if (res && res.filename) {
        this.activeBgmFile = res.filename;
        this.activeBgmTitle = res.title || 'YouTube Music';
        this.updateBgmPlayer(res.url, this.activeBgmTitle);
        App.showToast(`✅ YouTube Music "${this.activeBgmTitle}" ရယူပြီးပါပြီ! BGM အဖြစ် အသုံးပြုပါမည်။`, 'success');
        if (input) input.value = '';
      }
    } catch (e) {
      App.showToast('YouTube audio error: ' + e.message, 'error');
    } finally {
      if (btn) {
        btn.innerHTML = `<span>⬇</span> ရယူမည်`;
        btn.disabled = false;
      }
    }
  },

  async handleBgmFileUpload(file) {
    if (!file) return;
    try {
      App.showToast(`⏳ BGM "${file.name}" တင်သွင်းနေပါသည်...`, 'info');
      const res = await API.uploadBgm(file);
      if (res && res.filename) {
        this.activeBgmFile = res.filename;
        this.activeBgmTitle = file.name;
        this.updateBgmPlayer(res.url, file.name);
        App.showToast(`✅ BGM "${file.name}" ထည့်သွင်းပြီးပါပြီ!`, 'success');
      }
    } catch (e) {
      App.showToast('BGM upload error: ' + e.message, 'error');
    }
  },

  onBgmPresetChange(val) {
    if (!val) {
      this.clearBgm();
      return;
    }
    this.activeBgmFile = val;
    const select = document.getElementById('transcribe-bgm-preset-select');
    const selectedText = select?.options[select.selectedIndex]?.text || 'Royalty-Free BGM';
    this.activeBgmTitle = selectedText;
    this.updateBgmPlayer(`/media/bgm/${val}`, selectedText);
    App.showToast(`✅ Preset "${selectedText}" ရွေးချယ်ပြီးပါပြီ!`, 'info');
  },

  updateBgmPlayer(audioUrl, title) {
    const wrap = document.getElementById('transcribe-bgm-player-wrap');
    const nameEl = document.getElementById('transcribe-bgm-active-name');
    const audio = document.getElementById('transcribe-bgm-audio');
    if (wrap) wrap.classList.remove('hidden');
    if (nameEl) nameEl.textContent = title;
    if (audio) {
      audio.src = audioUrl;
      audio.volume = this.bgmVolume !== undefined ? this.bgmVolume : 0.35;
    }
  },

  clearBgm() {
    this.activeBgmFile = null;
    this.activeBgmTitle = null;
    const wrap = document.getElementById('transcribe-bgm-player-wrap');
    const select = document.getElementById('transcribe-bgm-preset-select');
    const audio = document.getElementById('transcribe-bgm-audio');
    if (wrap) wrap.classList.add('hidden');
    if (select) select.value = '';
    if (audio) {
      audio.pause();
      audio.src = '';
    }
    App.showToast('BGM ဖယ်ရှားပြီးပါပြီ (မူရင်းအသံသာ အသုံးပြုပါမည်)', 'info');
  },

  // Viral Caption & Hashtags Generator
  // Control Deck Tabs (Directly under video preview)
  switchControlDeckTab(tab) {
    const tabs = ['layout', 'blur', 'logo', 'subtitle', 'audio'];
    tabs.forEach(t => {
      const btn = document.getElementById(`deck-btn-${t}`);
      const panel = document.getElementById(`deck-panel-${t}`);
      if (btn) {
        if (t === tab) {
          btn.className = 'deck-pill active px-2.5 py-1 rounded-lg bg-blue-600 text-white flex items-center gap-1 transition shadow-sm';
        } else {
          btn.className = 'deck-pill px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 hover:text-white flex items-center gap-1 transition';
        }
      }
      if (panel) {
        if (t === tab) {
          panel.classList.remove('hidden');
        } else {
          panel.classList.add('hidden');
        }
      }
    });
  },

  quickSetRatio(ratio) {
    const select = document.getElementById('transcribe-aspect-ratio');
    if (select) {
      select.value = ratio;
    }
    const ratioBtns = {
      'original': 'ratio-btn-original',
      '16:9': 'ratio-btn-16-9',
      '9:16': 'ratio-btn-9-16',
      '1:1': 'ratio-btn-1-1'
    };
    Object.entries(ratioBtns).forEach(([r, btnId]) => {
      const b = document.getElementById(btnId);
      if (b) {
        if (r === ratio) {
          b.className = 'ratio-btn active px-1.5 py-1 rounded bg-blue-600 text-white text-[10px] font-bold border border-blue-500';
        } else {
          b.className = 'ratio-btn px-1.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[10px] font-bold border border-slate-700';
        }
      }
    });

    const container = document.getElementById('transcribe-preview-container');
    if (container) {
      container.classList.remove('aspect-video', 'aspect-[9/16]', 'aspect-square');
      if (ratio === '9:16') {
        container.classList.add('aspect-[9/16]');
        container.style.maxWidth = '250px';
      } else if (ratio === '1:1') {
        container.classList.add('aspect-square');
        container.style.maxWidth = '320px';
      } else {
        container.classList.add('aspect-video');
        container.style.maxWidth = '100%';
      }
    }
    this.onVideoLayoutChange();
  },

  // Timeline Mode Toggle (ON = with timestamps, OFF = clean text only)
  toggleTimelineMode() {
    this.timelineMode = (this.timelineMode === undefined) ? false : !this.timelineMode;
    const btn = document.getElementById('btn-toggle-timeline-mode');
    const statusText = document.getElementById('timeline-toggle-status');
    const icon = document.getElementById('timeline-toggle-icon');
    const thCol = document.getElementById('th-timeline-col');

    if (this.timelineMode) {
      if (statusText) statusText.textContent = 'ON';
      if (icon) icon.textContent = '⏱️';
      if (btn) {
        btn.className = 'px-2.5 py-1 rounded-lg text-[11px] font-bold border transition flex items-center gap-1 bg-blue-600/30 text-blue-300 border-blue-500/50 shadow-sm';
      }
      if (thCol) thCol.classList.remove('hidden');
      document.querySelectorAll('#timeline-table-body td.timeline-col-cell').forEach(td => td.classList.remove('hidden'));
      App.showToast('⏱️ Timeline: ON (အချိန်မှတ်တမ်း ပါဝင်သည်)', 'info');
    } else {
      if (statusText) statusText.textContent = 'OFF';
      if (icon) icon.textContent = '🚫';
      if (btn) {
        btn.className = 'px-2.5 py-1 rounded-lg text-[11px] font-bold border transition flex items-center gap-1 bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-sm';
      }
      if (thCol) thCol.classList.add('hidden');
      document.querySelectorAll('#timeline-table-body td.timeline-col-cell').forEach(td => td.classList.add('hidden'));
      App.showToast('📄 Timeline: OFF (စာသားသီးသန့် မုဒ်)', 'info');
    }
  },

  syncSegmentsFromTableInputs() {
    const rows = document.querySelectorAll('#timeline-table-body tr');
    if (!rows || rows.length === 0) return;
    if (!this.currentSegments) this.currentSegments = [];
    rows.forEach((tr, idx) => {
      const myInput = tr.querySelector('.sub-text-my-input');
      const enInput = tr.querySelector('.sub-text-en-input');
      if (this.currentSegments[idx]) {
        if (myInput) this.currentSegments[idx].my_text = myInput.value;
        if (enInput) this.currentSegments[idx].en_text = enInput.value;
      }
    });
  },

  copyTextUniversal(text, successMsg) {
    if (!text || !text.trim()) {
      App.showToast('Copy ကူးရန် စာသား မရှိသေးပါ', 'warning');
      return;
    }

    const fallbackCopy = () => {
      try {
        const tArea = document.createElement('textarea');
        tArea.value = text;
        tArea.style.position = 'fixed';
        tArea.style.top = '0';
        tArea.style.left = '0';
        tArea.style.width = '2em';
        tArea.style.height = '2em';
        tArea.style.padding = '0';
        tArea.style.border = 'none';
        tArea.style.outline = 'none';
        tArea.style.boxShadow = 'none';
        tArea.style.background = 'transparent';
        tArea.style.opacity = '0.01';
        tArea.setAttribute('readonly', '');
        document.body.appendChild(tArea);
        tArea.focus();
        tArea.select();
        tArea.setSelectionRange(0, 999999);

        const ok = document.execCommand('copy');
        document.body.removeChild(tArea);
        if (ok) {
          App.showToast(successMsg || '📋 Copy ကူးပြီးပါပြီ!', 'success');
          if (navigator.vibrate) navigator.vibrate(40);
        } else {
          prompt('စာသားများကို ဖိ၍ Select All -> Copy နှိပ်ပါ:', text);
        }
      } catch (err) {
        prompt('စာသားများကို ဖိ၍ Select All -> Copy နှိပ်ပါ:', text);
      }
    };

    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(() => {
        App.showToast(successMsg || '📋 Copy ကူးပြီးပါပြီ!', 'success');
        if (navigator.vibrate) navigator.vibrate(40);
      }).catch(() => {
        fallbackCopy();
      });
    } else {
      fallbackCopy();
    }
  },

  copySubtitles() {
    this.syncSegmentsFromTableInputs();
    if (!this.currentSegments || this.currentSegments.length === 0) {
      App.showToast('Copy ကူးရန် စာတန်းထိုး မရှိသေးပါ', 'warning');
      return;
    }
    if (this.timelineMode === false) {
      this.copyCleanTextOnly();
    } else {
      this.copyFullSrt();
    }
  },

  copyCleanTextOnly() {
    this.syncSegmentsFromTableInputs();
    if (!this.currentSegments || this.currentSegments.length === 0) {
      App.showToast('Copy ကူးရန် စာတန်းထိုး မရှိသေးပါ', 'warning');
      return;
    }
    const lines = this.currentSegments.map(s => (s.my_text || s.text || '').trim()).filter(Boolean);
    const text = lines.join('\n');
    this.copyTextUniversal(text, `📋 မြန်မာစာသားသီးသန့် (${lines.length} ကြောင်း) ကို Copy ကူးပြီးပါပြီ!`);
  },

  copyFullSrt() {
    this.syncSegmentsFromTableInputs();
    if (!this.currentSegments || this.currentSegments.length === 0) {
      App.showToast('Copy ကူးရန် စာတန်းထိုး မရှိသေးပါ', 'warning');
      return;
    }
    let srtText = '';
    this.currentSegments.forEach((s, idx) => {
      const startStr = s.start_str || this.formatSrtTime(s.start || 0);
      const endStr = s.end_str || this.formatSrtTime(s.end || 0);
      const text = (s.my_text || s.text || '').trim();
      srtText += `${idx + 1}\n${startStr} --> ${endStr}\n${text}\n\n`;
    });
    this.copyTextUniversal(srtText.trim(), `⏱️ Timeline ပါဝင်သော .SRT (${this.currentSegments.length} ကြောင်း) ကို Copy ကူးပြီးပါပြီ!`);
  },

  copyPlatformCaption(platform) {
    const pkg = this.currentSocialPackages || {};
    let textToCopy = '';
    let name = '';

    if (platform === 'tiktok') {
      textToCopy = pkg.tiktok_copy;
      name = 'TikTok Package';
    } else if (platform === 'yt') {
      textToCopy = pkg.yt_shorts_copy;
      name = 'YouTube Shorts Package';
    } else if (platform === 'reels') {
      textToCopy = pkg.fb_reels_copy;
      name = 'Facebook Reels Package';
    } else if (platform === 'disclaimer') {
      textToCopy = pkg.copyright_disclaimer || "Copyright Disclaimer Under Section 107 of the Copyright Act 1976: Allowance is made for 'fair use' for purposes such as criticism, comment, recap, news reporting, teaching, scholarship, and research. All audio and video belong to their respective copyright owners.";
      name = 'Copyright Safe Fair Use Disclaimer';
    }

    if (!textToCopy) {
      const title = document.getElementById('caption-title-input')?.value || 'ရုပ်ရှင်ဇာတ်လမ်းအကျဉ်း 😱';
      if (platform === 'tiktok') {
        textToCopy = `${title}\n\nဇာတ်လမ်းအစကနေ အဆုံးထိ ဘာတွေဆက်ဖြစ်မလဲ ကြည့်လိုက်ကြရအောင်!\n.\n#fyp #tiktokuni #movierecap #recapmyanmar #actrecap #ရုပ်ရှင်ဇာတ်လမ်း #ဇာတ်လမ်းအကျဉ်း #viralvideo`;
        name = 'TikTok';
      } else if (platform === 'yt') {
        textToCopy = `${title} | Burmese Movie Recap\n\nဇာတ်လမ်းအစကနေ အဆုံးထိ ဘာတွေဆက်ဖြစ်မလဲ ကြည့်လိုက်ကြရအောင်!\n\n📌 Copyright Safe Notice:\nCopyright Disclaimer Under Section 107 of the Copyright Act 1976: Allowance is made for 'fair use' for purposes such as criticism, comment, recap, news reporting, teaching, scholarship, and research. All rights belong to respective owners.\n\n#shorts #youtubeshorts #movierecap #burmeserecap #ဇာတ်လမ်းအကျဉ်း #myanmar`;
        name = 'YouTube Shorts';
      } else if (platform === 'reels') {
        textToCopy = `${title} 🎬\n\nဇာတ်လမ်းအစကနေ အဆုံးထိ စိတ်ဝင်စားစရာ အလှည့်အပြောင်းတွေနဲ့ ပြည့်နှက်နေတဲ့ ဇာတ်လမ်းလေးပါ။\n\nအပြည့်အစုံ ကြည့်ရှုရန် Like & Follow လုပ်ထားပေးကြပါဦးနော်။\n\n#reels #facebookreels #movierecap #myanmar #recap`;
        name = 'Facebook Reels';
      } else {
        textToCopy = "Copyright Disclaimer Under Section 107 of the Copyright Act 1976: Allowance is made for 'fair use' for purposes such as criticism, comment, recap, news reporting, teaching, scholarship, and research. All audio and video belong to their respective copyright owners.";
        name = 'Copyright Safe Disclaimer';
      }
    }

    this.copyTextUniversal(textToCopy, `✅ ${name} ကို 1-Click Copy ကူးပြီးပါပြီ!`);
  },

  // Viral Caption & Hashtags Generator
  async generateViralCaption() {
    const btn = document.getElementById('btn-generate-caption');
    if (btn) {
      btn.innerHTML = `<span class="animate-spin inline-block mr-1">⏳</span> ဖန်တီးနေပါသည်...`;
      btn.disabled = true;
    }
    App.showToast('⏳ TikTok & YouTube အတွက် Viral Caption နှင့် Hashtags များ ဖန်တီးနေပါသည်...', 'info');

    try {
      const res = await API.generateCaption(this.currentVideoTitle || 'ရုပ်ရှင်ဇာတ်လမ်းအကျဉ်း', this.currentSegments || []);
      if (res && res.success) {
        this.currentSocialPackages = res;
        const titleEl = document.getElementById('caption-title-input');
        const hashEl = document.getElementById('caption-hashtags-input');
        const fullEl = document.getElementById('caption-full-textarea');

        if (titleEl) titleEl.value = res.burmese_title || '';
        if (hashEl) hashEl.value = res.hashtag_string || '';
        if (fullEl) fullEl.value = res.full_caption || '';

        App.showToast('✅ Viral Caption, Title နှင့် Hashtags အဆင်သင့် ဖြစ်ပါပြီ!', 'success');
      }
    } catch (e) {
      console.error(e);
      App.showToast('Caption generation error: ' + e.message, 'error');
    } finally {
      if (btn) {
        btn.innerHTML = `<span>⚡</span> Generate Viral Caption`;
        btn.disabled = false;
      }
    }
  },

  copyToClipboard(elementId, labelName) {
    const el = document.getElementById(elementId);
    if (!el || !el.value) {
      App.showToast(`Copy ကူးရန် ${labelName || 'စာသား'} မရှိသေးပါ`, 'warning');
      return;
    }
    this.copyTextUniversal(el.value, `📋 ${labelName || 'စာသား'} ကို Clipboard သို့ Copy ကူးပြီးပါပြီ!`);
  },

  // 1. Process Video -> Chinese Speech Transcription -> Burmese Timeline SRT
  async handleVideoTranscribe(file) {
    if (!file) return;

    const statusEl = document.getElementById('transcribe-status');
    const resultBox = document.getElementById('transcribe-result-box');
    const srcLang = document.getElementById('transcribe-source-lang')?.value || 'zh';
    const whisperModel = document.getElementById('transcribe-whisper-model')?.value || 'base';

    const estSec = Math.max(18, Math.min(90, Math.round((file.size / (1024 * 1024)) * 2.2)));
    this.startTranscribeProgressMonitor(estSec);

    if (statusEl) {
      statusEl.innerHTML = `<span class="animate-spin inline-block mr-1">⏳</span> ဗီဒီယိုမှ အသံဖိုင်ထုတ်ယူပြီး စကားပြောများကို စာသားပြောင်းနေပါသည် (${(file.size / 1024 / 1024).toFixed(1)} MB)...`;
    }

    try {
      const geminiApiKey = Tools.getGeminiKey();
      
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

      this.currentSegments = res.segments || [];
      this.uploadedVideoFilename = res.video_file || null;

      // Load video into preview player
      const video = document.getElementById('transcribe-preview-video');
      if (video && res.video_url) {
        video.src = res.video_url;
        this.activeVideoUrl = res.video_url;
      }

      this.renderTimelineTable();

      // Update download links
      const dlMy = document.getElementById('btn-dl-burmese-srt');
      const dlBi = document.getElementById('btn-dl-bilingual-srt');
      if (dlMy) dlMy.href = res.burmese_srt_url;
      if (dlBi) dlBi.href = res.bilingual_srt_url;

      if (resultBox) resultBox.classList.remove('hidden');
      if (statusEl) {
        statusEl.innerHTML = `<span class="text-emerald-400 font-semibold">✓ အောင်မြင်ပါသည်! စာကြောင်းရေ ${this.currentSegments.length} ကြောင်းကို အချိန်နှင့်တကွ ဘာသာပြန်ဆိုပြီးပါပြီ။</span>`;
      }

      this.currentVideoTitle = file.name.replace(/\.[^/.]+$/, "");
      this.finishTranscribeProgressMonitor();
      App.showToast(`✅ စာကြောင်းရေ (${this.currentSegments.length}) လိုင်းကို Timeline အတိအကျဖြင့် ဘာသာပြန်ပြီးပါပြီ!`, 'success');
      this.generateViralCaption();

    } catch (e) {
      console.error(e);
      if (this._progressInterval) clearInterval(this._progressInterval);
      const modal = document.getElementById('transcribe-loading-state');
      if (modal) modal.classList.add('hidden');
      if (statusEl) {
        statusEl.innerHTML = `<span class="text-rose-400 font-semibold">⚠️ အမှားဖြစ်ခဲ့ပါသည်: <span class="err-text"></span></span>`;
        statusEl.querySelector('.err-text').innerText = e.message || 'Network Timeout / API Error';
      }
      App.showToast('Transcription error: ' + (e.message || 'Unknown'), 'error');
    }
  },

  // 2. Process existing Chinese SRT -> Burmese Translation with identical timeline
  async handleSrtUpload(file) {
    if (!file) return;

    const statusEl = document.getElementById('transcribe-status');
    const resultBox = document.getElementById('transcribe-result-box');

    this.startTranscribeProgressMonitor(15);
    if (statusEl) {
      statusEl.innerHTML = `<span class="animate-spin inline-block mr-1">⏳</span> တရုတ် SRT ဖိုင်မှ timeline များကို ရယူပြီး မြန်မာဘာသာသို့ တိုက်ရိုက်ပြန်ဆိုနေပါသည်...`;
    }

    try {
      const res = await API.transcribeSrt(file, this.getGeminiKey());
      this.currentSegments = res.segments || [];
      this.renderTimelineTable();

      const dlMy = document.getElementById('btn-dl-burmese-srt');
      const dlBi = document.getElementById('btn-dl-bilingual-srt');
      if (dlMy) dlMy.href = res.burmese_srt_url;
      if (dlBi) dlBi.href = res.bilingual_srt_url;

      if (resultBox) resultBox.classList.remove('hidden');
      if (statusEl) {
        statusEl.innerHTML = `<span class="text-emerald-400 font-semibold">✓ တရုတ် SRT မှ စာကြောင်း ${this.currentSegments.length} ကြောင်းကို timeline မလွဲစေဘဲ ဘာသာပြန်ပြီးပါပြီ။</span>`;
      }
      this.currentVideoTitle = file.name.replace(/\.[^/.]+$/, "");
      this.finishTranscribeProgressMonitor();
      App.showToast('✅ SRT Timeline Translation Completed!', 'success');
      this.generateViralCaption();

    } catch (e) {
      console.error(e);
      if (statusEl) {
        statusEl.innerHTML = `<span class="text-rose-400 font-semibold">⚠️ SRT Error: <span class="err-text"></span></span>`;
        statusEl.querySelector('.err-text').innerText = e.message || 'Network Timeout / API Error';
      }
      App.showToast('SRT Error: ' + (e.message || 'Unknown'), 'error');
    } finally {
      if (progressModal) progressModal.classList.add('hidden');
    }
  },

  async loadDemoChineseSrt() {
    const demoSrt = `1
00:00:01,000 --> 00:00:03,500
我叫枫姜凝

2
00:00:03,800 --> 00:00:07,000
夜晚周是我最讨厌的人

3
00:00:07,200 --> 00:00:10,000
在我入门之前

4
00:00:10,200 --> 00:00:14,000
我才是先宗最耀眼的大师姐

5
00:00:14,200 --> 00:00:17,000
天赋比我高

6
00:00:17,200 --> 00:00:20,000
电法比我强

7
00:00:20,200 --> 00:00:24,000
楼连长相和人员

8
00:00:24,200 --> 00:00:28,000
都比我更受欢迎`;

    const blob = new Blob([demoSrt], { type: 'text/plain' });
    const file = new File([blob], 'demo_chinese_drama.srt');
    await this.handleSrtUpload(file);
  },

  // Render the interactive timeline subtitle table with free-style editing
  renderTimelineTable() {
    const tbody = document.getElementById('timeline-table-body');
    if (!tbody) return;

    if (!this.currentSegments || this.currentSegments.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-center py-6 text-slate-500">စာတန်းထိုး မရှိသေးပါ။ ဗီဒီယို သို့မဟုတ် SRT တင်သွင်းပါ။</td></tr>`;
      return;
    }

    const currentFont = document.getElementById('transcribe-select-font')?.value || 'Pyidaungsu';
    const isTimelineOn = this.timelineMode !== false;
    const hideClass = isTimelineOn ? '' : 'hidden';

    tbody.innerHTML = this.currentSegments.map((s, i) => {
      const startStr = s.start_str ? s.start_str.substring(3, 8) : this.formatSrtTime(s.start).substring(3, 8);
      const endStr = s.end_str ? s.end_str.substring(3, 8) : this.formatSrtTime(s.end).substring(3, 8);
      return `
      <tr id="segment-row-${i}" class="border-b border-slate-800/80 hover:bg-slate-800/40 transition group cursor-pointer" onclick="Tools.seekVideoTo(${s.start}, ${i})">
        <td class="timeline-col-cell py-2 px-2 font-mono text-[10px] text-blue-400 shrink-0 select-none ${hideClass}">
          <div class="flex items-center gap-1">
            <span class="w-4 h-4 rounded-full bg-blue-500/20 text-blue-300 flex items-center justify-center text-[9px] font-bold">${s.index || (i+1)}</span>
            <span>${startStr}➔${endStr}</span>
          </div>
        </td>
        <td class="py-1.5 px-2">
          <input type="text" value="${this.escapeAttr(s.my_text)}" oninput="Tools.updateSegmentText(${i}, 'my', this.value)" style="font-family: '${currentFont}', sans-serif;" class="w-full bg-transparent border-b border-transparent hover:border-slate-600 focus:border-emerald-500 text-xs text-emerald-300 font-medium focus:outline-none py-1 px-1 rounded transition" placeholder="မြန်မာဘာသာ ရိုက်ထည့်ပါ">
        </td>
        <td class="py-1.5 px-2">
          <input type="text" value="${this.escapeAttr(s.en_text)}" oninput="Tools.updateSegmentText(${i}, 'en', this.value)" class="w-full bg-transparent border-b border-transparent hover:border-slate-600 focus:border-amber-500 text-xs text-amber-200 focus:outline-none py-1 px-1 rounded transition" placeholder="English text">
        </td>
        <td class="py-1.5 px-2">
          <input type="text" value="${this.escapeAttr(s.zh_text)}" oninput="Tools.updateSegmentText(${i}, 'zh', this.value)" class="w-full bg-transparent border-b border-transparent hover:border-slate-600 focus:border-blue-500 text-xs text-slate-300 focus:outline-none py-1 px-1 rounded transition" placeholder="中文">
        </td>
        <td class="py-1.5 px-1.5 text-right shrink-0">
          <button onclick="event.stopPropagation(); Tools.playSegment(${s.start}, ${s.end})" class="px-1.5 py-0.5 rounded bg-slate-800 hover:bg-blue-600 text-slate-300 hover:text-white text-[10px] font-medium transition" title="Play this line">
            ▶
          </button>
        </td>
      </tr>
      `;
    }).join('');
  },

  updateSegmentText(index, lang, newText) {
    if (!this.currentSegments[index]) return;
    if (lang === 'zh') {
      this.currentSegments[index].zh_text = newText;
    } else if (lang === 'en') {
      this.currentSegments[index].en_text = newText;
    } else {
      this.currentSegments[index].my_text = newText;
    }
    // Update live video subtitle overlay immediately if active
    this.syncVideoTimeline();
  },

  seekVideoTo(seconds, rowIndex = null) {
    const video = document.getElementById('transcribe-preview-video');
    if (video) {
      video.currentTime = seconds;
      video.play();
    }
    if (rowIndex !== null) {
      this.highlightRow(rowIndex);
    }
  },

  playSegment(start, end) {
    const video = document.getElementById('transcribe-preview-video');
    if (!video) return;
    video.currentTime = start;
    video.play();
    
    // Stop at end
    const checkStop = () => {
      if (video.currentTime >= end) {
        video.pause();
        video.removeEventListener('timeupdate', checkStop);
      }
    };
    video.addEventListener('timeupdate', checkStop);
  },

  syncVideoTimeline() {
    const video = document.getElementById('transcribe-preview-video');
    if (!video) return;
    const cur = video.currentTime;

    // Find active segment
    const activeIdx = this.currentSegments.findIndex(s => cur >= s.start && cur <= s.end);
    const overlay = document.getElementById('video-live-subtitle-overlay');

    if (activeIdx !== -1) {
      const activeSeg = this.currentSegments[activeIdx];
      if (overlay) {
        const subMode = document.getElementById('transcribe-sub-mode')?.value || 'my';
        const styleType = document.getElementById('transcribe-sub-style')?.value || 'box';
        const posType = document.getElementById('transcribe-sub-pos')?.value || 'bottom';
        const posSliderVal = parseInt(document.getElementById('transcribe-pos-slider')?.value || '86', 10);
        const fontName = document.getElementById('transcribe-select-font')?.value || 'Pyidaungsu';
        const fontSize = parseInt(document.getElementById('transcribe-font-size')?.value || '34', 10);
        let subColor = document.getElementById('transcribe-sub-color')?.value || '#ffffff';

        if (styleType === 'yellow') {
          subColor = '#fde047';
        }

        // Apply Position to overlay
        overlay.style.position = 'absolute';
        overlay.style.left = '50%';
        if (posType === 'top') {
          overlay.style.top = '10%';
          overlay.style.bottom = 'auto';
          overlay.style.transform = 'translate(-50%, 0)';
        } else if (posType === 'middle') {
          overlay.style.top = '50%';
          overlay.style.bottom = 'auto';
          overlay.style.transform = 'translate(-50%, -50%)';
        } else if (posType === 'custom') {
          overlay.style.top = posSliderVal + '%';
          overlay.style.bottom = 'auto';
          overlay.style.transform = 'translate(-50%, -50%)';
        } else {
          // bottom
          overlay.style.top = 'auto';
          overlay.style.bottom = '10%';
          overlay.style.transform = 'translate(-50%, 0)';
        }

        // Apply Style Type
        if (styleType === 'box') {
          overlay.style.background = 'rgba(0, 0, 0, 0.85)';
          overlay.style.backdropFilter = 'blur(8px)';
          overlay.style.borderRadius = '14px';
          overlay.style.border = '1px solid rgba(255, 255, 255, 0.12)';
          overlay.style.boxShadow = '0 10px 25px rgba(0, 0, 0, 0.6)';
          overlay.style.padding = '8px 18px';
          overlay.style.width = 'auto';
          overlay.style.maxWidth = '90%';
        } else if (styleType === 'outline') {
          overlay.style.background = 'transparent';
          overlay.style.backdropFilter = 'none';
          overlay.style.borderRadius = '0';
          overlay.style.border = 'none';
          overlay.style.boxShadow = 'none';
          overlay.style.padding = '4px 10px';
          overlay.style.width = 'auto';
          overlay.style.maxWidth = '90%';
        } else if (styleType === 'banner') {
          overlay.style.background = 'rgba(0, 0, 0, 0.88)';
          overlay.style.backdropFilter = 'blur(6px)';
          overlay.style.borderRadius = '0';
          overlay.style.border = 'none';
          overlay.style.borderTop = '1px solid rgba(255, 255, 255, 0.15)';
          overlay.style.borderBottom = '1px solid rgba(255, 255, 255, 0.15)';
          overlay.style.boxShadow = '0 8px 20px rgba(0, 0, 0, 0.5)';
          overlay.style.padding = '8px 16px';
          overlay.style.width = '100%';
          overlay.style.maxWidth = '100%';
        } else if (styleType === 'yellow') {
          overlay.style.background = 'rgba(0, 0, 0, 0.86)';
          overlay.style.backdropFilter = 'blur(8px)';
          overlay.style.borderRadius = '14px';
          overlay.style.border = '1px solid rgba(253, 224, 71, 0.25)';
          overlay.style.boxShadow = '0 10px 25px rgba(0, 0, 0, 0.7)';
          overlay.style.padding = '8px 18px';
          overlay.style.width = 'auto';
          overlay.style.maxWidth = '90%';
        }

        // Text styling & stroke simulation
        const outlineCss = (styleType === 'outline') 
          ? 'text-shadow: -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000, 2px 2px 0 #000, 0 3px 6px rgba(0,0,0,0.9);'
          : 'text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000, 0 2px 4px rgba(0,0,0,0.8);';

        // True proportionate scale: backend assumes fontSize relative to 1080px base height.
        const previewFontSize = Math.max(8, Math.round((fontSize / 1080) * video.clientHeight));
        const enFontSize = Math.max(8, Math.round(previewFontSize * 0.76));

        let subHtml = '';
        if (subMode === 'my_en') {
          subHtml = `
            <div style="font-family: '${fontName}', sans-serif; color: ${subColor}; font-size: ${previewFontSize}px; ${outlineCss}" class="font-bold leading-snug">${this.escapeAttr(activeSeg.my_text || '')}</div>
            ${activeSeg.en_text ? `<div style="font-size: ${enFontSize}px; ${outlineCss}" class="text-amber-300 font-semibold mt-0.5 tracking-wide">${this.escapeAttr(activeSeg.en_text)}</div>` : ''}
          `;
        } else if (subMode === 'my_zh') {
          subHtml = `
            <div style="font-family: '${fontName}', sans-serif; color: ${subColor}; font-size: ${previewFontSize}px; ${outlineCss}" class="font-bold leading-snug">${this.escapeAttr(activeSeg.my_text || '')}</div>
            ${activeSeg.zh_text ? `<div style="font-size: ${enFontSize}px; ${outlineCss}" class="text-slate-300 opacity-80 mt-0.5">${this.escapeAttr(activeSeg.zh_text)}</div>` : ''}
          `;
        } else if (subMode === 'en') {
          subHtml = `
            <div style="color: ${subColor}; font-size: ${previewFontSize}px; ${outlineCss}" class="font-bold leading-snug">${this.escapeAttr(activeSeg.en_text || activeSeg.my_text || '')}</div>
          `;
        } else {
          subHtml = `
            <div style="font-family: '${fontName}', sans-serif; color: ${subColor}; font-size: ${previewFontSize}px; ${outlineCss}" class="font-bold leading-snug">${this.escapeAttr(activeSeg.my_text || activeSeg.zh_text || '')}</div>
          `;
        }

        overlay.innerHTML = subHtml;
        overlay.classList.remove('hidden');
      }
      this.highlightRow(activeIdx);
    } else {
      if (overlay) overlay.classList.add('hidden');
    }
  },

  highlightRow(index) {
    document.querySelectorAll('[id^="segment-row-"]').forEach(r => {
      r.classList.remove('bg-blue-600/20', 'border-blue-500/50');
    });
    const row = document.getElementById(`segment-row-${index}`);
    if (row) {
      row.classList.add('bg-blue-600/20', 'border-blue-500/50');
    }
  },

  async exportUpdatedSrt() {
    if (!this.currentSegments || this.currentSegments.length === 0) return;
    try {
      const res = await API.exportCustomSrt(this.currentSegments);
      const a = document.createElement('a');
      a.href = res.burmese_srt_url;
      a.download = res.burmese_srt_file;
      a.click();
      App.showToast('⬇ ပြင်ဆင်ပြီး မြန်မာ SRT ကို ဒေါင်းလုဒ်ဆွဲပြီးပါပြီ!', 'success');
    } catch (e) {
      App.showToast('Export failed: ' + e.message, 'error');
    }
  },

  async polishAllSegments() {
    if (!this.currentSegments || this.currentSegments.length === 0) {
      App.showToast('ဘာသာပြန်ရန် စာကြောင်းများ မရှိသေးပါ', 'warning');
      return;
    }

    const polishBtn = document.getElementById('btn-polish-natural');
    if (polishBtn) {
      polishBtn.innerHTML = `<span>⏳</span> စကားပြောဟန် ပြောင်းနေသည်...`;
      polishBtn.disabled = true;
    }

    try {
      let res;
      if (typeof API !== 'undefined' && typeof API.polishSegments === 'function') {
        res = await API.polishSegments(this.currentSegments);
      } else {
        const resp = await fetch('/api/transcribe/polish', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ segments: this.currentSegments })
        });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        res = await resp.json();
      }

      if (res && res.segments) {
        this.currentSegments = res.segments;
        this.renderTimelineTable();
        this.syncVideoTimeline();
        App.showToast('✨ ဇာတ်လမ်းပြော စကားပြောဟန် ပိုမိုသဘာဝကျအောင် ပြောင်းလဲပြီးပါပြီ!', 'success');
      }
    } catch (e) {
      console.error(e);
      App.showToast('⚠️ Polish error: ' + e.message, 'error');
    } finally {
      if (polishBtn) {
        polishBtn.innerHTML = `<span>✨</span> သဘာဝကျသော ဇာတ်ပြောဟန် ပြောင်းမည်`;
        polishBtn.disabled = false;
      }
    }
  },

  async downloadSubtitledVideo() {
    if (!this.currentSegments || this.currentSegments.length === 0) {
      App.showToast('စာတန်းထိုးရန် စာကြောင်းများ မရှိသေးပါ', 'warning');
      return;
    }

    let videoFile = this.uploadedVideoFilename;
    if (!videoFile && this.activeVideoUrl) {
      const parts = this.activeVideoUrl.split('/');
      videoFile = parts[parts.length - 1];
    }

    if (!videoFile) {
      App.showToast('ကျေးဇူးပြု၍ မူရင်း ဗီဒီယိုဖိုင် အရင် တင်သွင်းပါ (သို့မဟုတ် MP4 ရွေးချယ်ပါ)', 'warning');
      return;
    }

    const subMode = document.getElementById('transcribe-sub-mode')?.value || 'my';
    const styleType = document.getElementById('transcribe-sub-style')?.value || 'box';
    const positionType = document.getElementById('transcribe-sub-pos')?.value || 'bottom';
    const posPercent = parseFloat(document.getElementById('transcribe-pos-slider')?.value || '86') / 100.0;
    const fontName = document.getElementById('transcribe-select-font')?.value || 'Pyidaungsu';
    const fontSize = parseInt(document.getElementById('transcribe-font-size')?.value || '34', 10);
    const subColor = document.getElementById('transcribe-sub-color')?.value || '#ffffff';

    const aspectRatio = document.getElementById('transcribe-aspect-ratio')?.value || 'original';
    const resizeMode = document.getElementById('transcribe-resize-mode')?.value || 'fit_blur';
    const blurEnabled = document.getElementById('transcribe-blur-enable')?.checked || false;
    const blurYPercent = parseFloat(document.getElementById('transcribe-blur-y-slider')?.value || '56') / 100.0;
    const blurHeightPercent = parseFloat(document.getElementById('transcribe-blur-h-slider')?.value || '8') / 100.0;
    const logoFile = this.uploadedLogoFilename || null;
    const logoPos = document.getElementById('transcribe-logo-pos')?.value || 'top-right';
    const logoSizePercent = parseFloat(document.getElementById('transcribe-logo-size')?.value || '18') / 100.0;
    const logoOpacity = parseFloat(document.getElementById('transcribe-logo-opacity')?.value || '85') / 100.0;

    const origAudioVolume = this.origAudioVolume !== undefined ? this.origAudioVolume : 1.0;
    const bgmFile = this.activeBgmFile || null;
    const bgmVolume = this.bgmVolume !== undefined ? this.bgmVolume : 0.35;
    const exportQuality = document.getElementById('transcribe-export-quality')?.value || 'very_high';

    const btn = document.getElementById('btn-dl-subtitled-video');
    if (btn) {
      btn.innerHTML = `<span>⏳</span> HarfBuzz + FFmpeg ဖြင့် ဗီဒီယို ထုတ်လုပ်နေပါသည်...`;
      btn.disabled = true;
    }

    const modeLabel = subMode === 'my_en' ? 'မြန်မာ + English' : (subMode === 'my_zh' ? 'မြန်မာ + တရုတ်' : 'မြန်မာ');
    let extraFeatures = [];
    if (aspectRatio !== 'original') extraFeatures.push(aspectRatio + ' Resize');
    if (blurEnabled) extraFeatures.push('မူရင်းစာတန်းဝါးခြင်း');
    if (logoFile) extraFeatures.push('Channel Logo');
    if (origAudioVolume === 0) extraFeatures.push('Audio Muted (Anti-Copyright)');
    else if (origAudioVolume < 0.98) extraFeatures.push(`Audio ${(origAudioVolume * 100).toFixed(0)}%`);
    if (bgmFile) extraFeatures.push('Custom BGM');
    extraFeatures.push(exportQuality === 'very_high' ? 'Ultra HD (CRF 18)' : 'HD');
    const extraStr = extraFeatures.length > 0 ? ` (${extraFeatures.join(', ')})` : '';

    App.showToast(`⏳ [${fontName}] ဖောင့်ဖြင့် ${modeLabel} စာတန်းထိုး${extraStr}ကို စတင်ပေါင်းစပ်နေပါသည်...`, 'info');

    try {
      const res = await API.burnSubtitledVideo({
        videoFile: videoFile,
        segments: this.currentSegments,
        subMode: subMode,
        fontName: fontName,
        fontSize: fontSize,
        subColor: subColor,
        styleType: styleType,
        positionType: positionType,
        yPercent: posPercent,
        aspectRatio: aspectRatio,
        resizeMode: resizeMode,
        blurEnabled: blurEnabled,
        blurYPercent: blurYPercent,
        blurHeightPercent: blurHeightPercent,
        logoFile: logoFile,
        logoPos: logoPos,
        logoSizePercent: logoSizePercent,
        logoOpacity: logoOpacity,
        origAudioVolume: origAudioVolume,
        bgmFile: bgmFile,
        bgmVolume: bgmVolume,
        bgmLoop: true,
        exportQuality: exportQuality
      });

      if (res && res.job_id) {
        // Poll for progress
        const jobId = res.job_id;
        let jobDone = false;
        let finalUrl = null;
        let finalFilename = null;

        while (!jobDone) {
          await new Promise(resolve => setTimeout(resolve, 2000)); // wait 2s
          const statusRes = await API.pollBurnStatus(jobId);
          if (statusRes.status === 'error') {
            throw new Error(statusRes.error || 'Server processing error');
          }
          if (statusRes.status === 'done') {
            jobDone = true;
            finalUrl = statusRes.video_url;
            finalFilename = statusRes.video_file;
            if (btn) btn.innerHTML = `<span>🎬</span> ဆွဲနေသည် (100%)`;
          } else {
            const pct = statusRes.progress || 0;
            const msg = statusRes.message || 'Processing...';
            if (btn) btn.innerHTML = `<span class="animate-spin inline-block mr-1">⏳</span> ${msg} (${pct}%)`;
          }
        }

        if (finalUrl) {
          const a = document.createElement('a');
          a.href = finalUrl;
          a.download = finalFilename;
          a.click();
          App.showToast('🎉 စာတန်းထိုး၊ BGM နှင့် Ultra HD ပါရှိသော ဗီဒီယို (MP4) ဒေါင်းလုဒ်ဆွဲပြီးပါပြီ!', 'success');
        }
      }
    } catch (e) {
      console.error(e);
      App.showToast('⚠️ Subtitle burn error: ' + e.message, 'error');
    } finally {
      if (btn) {
        btn.innerHTML = `<span>🎬</span> Subtitle ပါ ဗီဒီယို ဒေါင်းလုဒ် (MP4)`;
        btn.disabled = false;
      }
    }
  },

  async sendTimelineToStudio() {
    if (!this.currentSegments || this.currentSegments.length === 0) return;

    // Compile all Burmese narration lines
    const burmeseScript = this.currentSegments.map(s => s.my_text).join('\n');
    App.switchTab('recap-studio');

    const studioScript = document.getElementById('studio-script-textarea');
    if (studioScript) {
      studioScript.value = burmeseScript;
    }

    // Transfer uploaded video file to RecapStudio
    let videoFile = this.uploadedVideoFilename;
    if (!videoFile && this.activeVideoUrl) {
      const parts = this.activeVideoUrl.split('/');
      videoFile = parts[parts.length - 1];
    }
    if (typeof RecapStudio !== 'undefined' && videoFile) {
      RecapStudio.setSourceVideo(videoFile, this.activeVideoUrl);
    }

    App.showToast('✅ Timeline စာသားများနှင့် ဗီဒီယိုကို Recap Studio သို့ ထည့်သွင်းပြီးပါပြီ!', 'success');
  },

  async generateBurmeseVoiceForTimeline() {
    if (!this.currentSegments || this.currentSegments.length === 0) return;
    const burmeseScript = this.currentSegments.map(s => s.my_text).join('\n');
    
    App.switchTab('free-voice');
    const fvInput = document.getElementById('fv-text-input');
    if (fvInput) {
      fvInput.value = burmeseScript;
      fvInput.dispatchEvent(new Event('input'));
    }
    App.showToast('🎙 စာသားများကို Free Voice စနစ်သို့ လွှဲပြောင်းပေးလိုက်ပါပြီ!', 'info');
  },

  // Translate tab functions
  async runTranslate() {
    const input = document.getElementById('translate-input-text');
    const output = document.getElementById('translate-output-text');
    const btn = document.getElementById('btn-run-translate');

    const text = input ? input.value.trim() : '';
    if (!text) {
      App.showToast('ကျေးဇူးပြု၍ ဘာသာပြန်လိုသော ဇာတ်လမ်းစာသား ရိုက်ထည့်ပါ', 'warning');
      return;
    }

    if (btn) btn.innerHTML = `<span>⏳</span> ဘာသာပြန်နေသည်...`;

    try {
      const res = await API.translateText(text);
      if (output) output.value = res.translated || '';
      App.showToast('✅ ဘာသာပြန်ခြင်း ပြီးမြောက်ပါပြီ!', 'success');
    } catch (e) {
      App.showToast('⚠️ Translation error: ' + e.message, 'error');
    } finally {
      if (btn) btn.innerHTML = `<span>🌐</span> Translate to Burmese Recap Style`;
    }
  },

  sendTranslatedToStudio() {
    const output = document.getElementById('translate-output-text');
    if (!output || !output.value) return;
    App.switchTab('recap-studio');
    const studioScript = document.getElementById('studio-script-textarea');
    if (studioScript) studioScript.value = output.value;
    App.showToast('✅ Translated script sent to Recap Studio!', 'success');
  },

  // --- Manual Transcribe & Video Staging Control ---
  onVideoFileSelected(file) {
    if (!file) return;
    this.stagedVideoFile = file;
    this.stagedVideoFilename = null;

    const statusBox = document.getElementById('video-selected-status');
    const nameEl = document.getElementById('selected-video-filename');
    const sizeEl = document.getElementById('selected-video-filesize');

    if (nameEl) nameEl.textContent = '🎬 ' + file.name;
    if (sizeEl) sizeEl.textContent = (file.size / (1024 * 1024)).toFixed(1) + ' MB';
    if (statusBox) statusBox.classList.remove('hidden');

    // Load local file into preview player
    const previewVideo = document.getElementById('transcribe-preview-video');
    if (previewVideo) {
      const objUrl = URL.createObjectURL(file);
      previewVideo.src = objUrl;
      this.activeVideoUrl = objUrl;
    }

    App.showToast(`📁 ဗီဒီယို "${file.name}" ကို ရွေးချယ်ပြီးပါပြီ။ အသံဖမ်းယူရန် "Want to Transcribe" ခလုတ်ကို နှိပ်ပါ (သို့မဟုတ် SRT တိုက်ရိုက်တင်သွင်းနိုင်ပါသည်)။`, 'info');
  },

  startManualTranscribe() {
    if (this.stagedVideoFilename) {
      this.transcribeDownloadedVideo(this.stagedVideoFilename);
      return;
    }
    if (this.stagedVideoFile) {
      this.handleVideoTranscribe(this.stagedVideoFile);
      return;
    }
    App.showToast('ကျေးဇူးပြု၍ ဗီဒီယိုဖိုင် အရင်ရွေးချယ်ပါ', 'warning');
  },

  clearStagedVideo() {
    this.stagedVideoFile = null;
    this.stagedVideoFilename = null;
    const statusBox = document.getElementById('video-selected-status');
    if (statusBox) statusBox.classList.add('hidden');
    const input = document.getElementById('transcribe-video-input');
    if (input) input.value = '';
  },

  // --- HD Video Downloader (RedNote, TikTok, YouTube, Facebook) ---
  async handleRednoteStandaloneDownload() {
    const input = document.getElementById('rednote-page-url-input');
    const btn = document.getElementById('btn-rednote-page-download');
    const statusEl = document.getElementById('rednote-page-status');
    const resBox = document.getElementById('rednote-page-result');
    const rawVal = input ? input.value.trim() : '';

    if (!rawVal) {
      App.showToast('ကျေးဇူးပြု၍ Video link သို့မဟုတ် mobile share text ကို ထည့်သွင်းပါ', 'warning');
      return;
    }

    let platform = 'HD Video';
    const low = rawVal.toLowerCase();
    if (low.includes('xhs') || low.includes('xiaohongshu')) platform = 'RedNote (小红书)';
    else if (low.includes('tiktok') || low.includes('douyin')) platform = 'TikTok';
    else if (low.includes('youtube') || low.includes('youtu.be')) platform = 'YouTube Shorts';
    else if (low.includes('facebook') || low.includes('fb.')) platform = 'Facebook Reels';

    if (btn) {
      btn.innerHTML = `<span>⏳</span> ${platform} ဒေါင်းလုဒ်ဆွဲနေပါသည်...`;
      btn.disabled = true;
    }
    if (statusEl) {
      statusEl.innerHTML = `<span class="animate-spin inline-block mr-1">⏳</span> ${platform} မှ HD ရုပ်ထွက် watermark ကင်းစင်စွာ ရယူနေပါသည်...`;
    }

    try {
      const res = await API.downloadRednoteVideo(rawVal);
      if (!res || !res.video_file) {
        throw new Error('Video download returned invalid response');
      }

      this.rednoteDownloadedVideo = res;
      this.uploadedVideoFilename = res.video_file;
      this.currentVideoTitle = res.title || `${platform} HD Video`;

      // Display result
      if (resBox) resBox.classList.remove('hidden');
      const titleEl = document.getElementById('rednote-result-title');
      if (titleEl) titleEl.textContent = res.title || `${platform} HD Video`;
      const sizeEl = document.getElementById('rednote-result-size');
      if (sizeEl) sizeEl.textContent = `${res.file_size_mb || '15'} MB`;

      const player = document.getElementById('rednote-page-video-player');
      if (player && res.video_url) {
        player.src = res.video_url;
      }

      const dlBtn = document.getElementById('rednote-btn-direct-download');
      if (dlBtn && res.video_url) {
        dlBtn.href = res.video_url;
        dlBtn.download = res.video_file;
      }

      if (statusEl) {
        statusEl.innerHTML = `<span class="text-emerald-400 font-semibold">✓ ${platform} HD Video (${res.file_size_mb} MB) ဒေါင်းလုဒ် အောင်မြင်ပါသည်!</span>`;
      }
      App.showToast(`🎉 ${platform} HD ဒေါင်းလုဒ် အောင်မြင်ပါသည်!`, 'success');
    } catch (e) {
      console.error(e);
      if (statusEl) {
        statusEl.innerHTML = `<span class="text-rose-400 font-semibold">⚠️ ဒေါင်းလုဒ် မအောင်မြင်ပါ: ${e.message}</span>`;
      }
      App.showToast(`⚠️ Download error: ${e.message}`, 'error');
    } finally {
      if (btn) {
        btn.innerHTML = `<span>⬇</span> Download HD Video`;
        btn.disabled = false;
      }
    }
  },

  sendRednoteToTranscribe() {
    if (!this.rednoteDownloadedVideo) return;
    const res = this.rednoteDownloadedVideo;
    this.uploadedVideoFilename = res.video_file;
    this.stagedVideoFilename = res.video_file;
    this.stagedVideoFile = null;
    this.activeVideoUrl = res.video_url;
    this.currentVideoTitle = res.title || 'RedNote HD Video';

    App.switchTab('transcribe');

    // Set preview player in transcribe
    const video = document.getElementById('transcribe-preview-video');
    if (video && res.video_url) {
      video.src = res.video_url;
    }

    // Show staged status box in transcribe
    const statusBox = document.getElementById('video-selected-status');
    const nameEl = document.getElementById('selected-video-filename');
    const sizeEl = document.getElementById('selected-video-filesize');
    if (nameEl) nameEl.textContent = '🎬 ' + (res.title || res.video_file);
    if (sizeEl) sizeEl.textContent = (res.file_size_mb || '15') + ' MB (RedNote HD)';
    if (statusBox) statusBox.classList.remove('hidden');

    App.showToast('🎬 RedNote ဗီဒီယိုကို Subtitle Studio သို့ ပို့ဆောင်ပြီးပါပြီ! Transcribe စတင်ရန် "Want to Transcribe" ခလုတ်ကို နှိပ်ပါ (သို့မဟုတ် SRT တင်သွင်းပါ)။', 'info');
  },

  async downloadRednoteMuted() {
    const videoFile = this.uploadedVideoFilename || (this.rednoteDownloadedVideo ? this.rednoteDownloadedVideo.video_file : null);
    if (!videoFile) {
      App.showToast('ကျေးဇူးပြု၍ ဗီဒီယိုအရင် ဒေါင်းလုဒ်ဆွဲပါ', 'warning');
      return;
    }
    const btn = document.getElementById('rednote-btn-mute-download');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span class="animate-spin inline-block mr-1">⏳</span> အသံပိတ်နေပါသည်...`;
    }
    try {
      const res = await API.muteVideo(videoFile);
      if (res && res.video_url) {
        const a = document.createElement('a');
        a.href = res.video_url;
        a.download = res.video_file;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        App.showToast(`🎉 အသံပိတ်ထားသော (Mute) ဗီဒီယို (${res.file_size_mb} MB) ကို ဒေါင်းလုဒ်ဆွဲပြီးပါပြီ! မူပိုင်ခွင့် ကင်းလွတ်စွာ အသုံးပြုနိုင်ပါသည်!`, 'success');
      } else {
        throw new Error('Mute video response missing url');
      }
    } catch (e) {
      console.error(e);
      App.showToast('⚠️ Mute video error: ' + e.message, 'error');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<span>🔇</span> အသံပိတ်ပြီး ဒေါင်းလုဒ် (Mute Video)`;
      }
    }
  },

  sendRednoteToRecap() {
    const videoFile = this.uploadedVideoFilename || (this.rednoteDownloadedVideo ? this.rednoteDownloadedVideo.video_file : null);
    const videoUrl = this.activeVideoUrl || (this.rednoteDownloadedVideo ? this.rednoteDownloadedVideo.video_url : null);
    if (!videoFile) {
      App.showToast('ကျေးဇူးပြု၍ ဗီဒီယိုအရင် ဒေါင်းလုဒ်ဆွဲပါ', 'warning');
      return;
    }
    App.switchTab('recap-studio');
    if (typeof RecapStudio !== 'undefined' && RecapStudio.setSourceVideo) {
      RecapStudio.setSourceVideo(videoFile, videoUrl);
    }
    const titleInput = document.getElementById('studio-movie-title');
    if (titleInput && this.currentVideoTitle) {
      titleInput.value = this.currentVideoTitle;
    }
    App.showToast('🎬 ဗီဒီယိုကို Recap Studio သို့ ပို့ဆောင်ပြီးပါပြီ! ဇာတ်လမ်းပြောစာသား ထည့်သွင်း၍ ဗီဒီယို ဖန်တီးနိုင်ပါပြီ။', 'success');
  },

  sendRednoteToTranslate() {
    App.switchTab('translate');
    App.showToast('🌐 SRT & Translate စတူဒီယိုသို့ ရောက်ရှိပါပြီ! တရုတ်စာသား သို့မဟုတ် SRT ထည့်သွင်း၍ ဘာသာပြန်နိုင်ပါသည်။', 'info');
  },

  // --- Gemini Key Page Methods ---
  async loadGeminiKeyForPage() {
    try {
              const status = await API.getSystemStatus();
        const email = window.currentUserEmail;
        let localKey = '';
        if (email) {
            localKey = localStorage.getItem('gemini_key_' + email) || '';
        }
        if (!localKey) {
            localKey = localStorage.getItem('gemini_key_global') || '';
        }
        const inputEl = document.getElementById('gemini-page-key-input');
        if (inputEl && !inputEl.value && localKey) {
            inputEl.value = localKey;
        }
      const input = document.getElementById('gemini-page-key-input');
      const badge = document.getElementById('gemini-key-status-badge');
      if (status.gemini_api_configured) {
        if (badge) {
          badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-400"></span> <span class="text-emerald-300">API Key Configured</span>`;
        }
        if (input && !input.value) {
          input.placeholder = '•••••••••••••••••••••••••••••••• (Configured)';
        }
      } else {
        if (badge) {
          badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-amber-400"></span> <span class="text-amber-300">Key Not Set</span>`;
        }
      }
    } catch (e) {
      console.error(e);
    }
  },

  toggleGeminiPageKeyVisibility() {
    const input = document.getElementById('gemini-page-key-input');
    if (input) {
      input.type = input.type === 'password' ? 'text' : 'password';
    }
  },

  // Helper: get Gemini key from any localStorage format
  getGeminiKey() {
    const email = localStorage.getItem('awn_google_email') || window.currentUserEmail || '';
    // Check all formats in priority order
    const candidates = [
      email ? `awn_gemini_key_${email}` : null,
      email ? `gemini_key_${email}` : null,
      'awn_gemini_api_key',
      'gemini_key_global',
      'gemini_api_key'
    ].filter(Boolean);
    for (const k of candidates) {
      const val = localStorage.getItem(k);
      if (val && val.trim()) return val.trim();
    }
    return '';
  },

  async saveGeminiKeyFromPage() {
    const input = document.getElementById('gemini-page-key-input');
    const key = input ? input.value.trim() : '';
    if (!key) {
      App.showToast('Gemini API Key ရိုက်ထည့်ပါ', 'warning');
      return;
    }
    // Google occasionally issues keys starting with AQ. or other prefixes now, so we removed the strict 'AIza' check.
    if (key.length < 30) {
      App.showToast('⚠️ API Key မှန်ကန်ပုံမရပါ (အရှည်မပြည့်ပါ)', 'error');
      return;
    }
    try {
      // Save with ALL key formats so any lookup finds it
      const email = localStorage.getItem('awn_google_email') || window.currentUserEmail || '';
      if (email) {
        localStorage.setItem(`awn_gemini_key_${email}`, key);
        localStorage.setItem(`gemini_key_${email}`, key);
      }
      localStorage.setItem('awn_gemini_api_key', key);
      localStorage.setItem('gemini_key_global', key);
      // Try to save to server (non-blocking)
      try {
        await fetch('/api/gemini/save-key', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ gemini_api_key: key })
        });
      } catch (_) { /* Server save optional */ }
      App.showToast('✅ Gemini API Key သိမ်းဆည်းပြီးပါပြီ!', 'success');
      this.loadGeminiKeyForPage();
    } catch (e) {
      App.showToast('Error saving key: ' + e.message, 'error');
    }
  },

  async testGeminiConnection() {
    const input = document.getElementById('gemini-page-key-input');
    const key = input ? input.value.trim() : '';
    const btn = document.getElementById('btn-test-gemini-page');
    const resultBox = document.getElementById('gemini-test-result');

    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span class="animate-spin inline-block mr-1">⟳</span> Testing...`;
    }
    if (resultBox) {
      resultBox.classList.remove('hidden');
      resultBox.className = 'p-3 rounded-xl text-xs bg-slate-800 text-slate-300 border border-slate-700';
      resultBox.innerHTML = `စမ်းသပ်ချိတ်ဆက်နေပါသည်...`;
    }

    try {
      const res = await API.testGemini(key);
      if (res && res.success) {
        if (resultBox) {
          resultBox.className = 'p-3 rounded-xl text-xs bg-emerald-950/40 text-emerald-300 border border-emerald-500/50';
          resultBox.innerHTML = `✅ ${res.message || 'Connected successfully!'}`;
        }
        App.showToast(`🎉 Gemini API အောင်မြင်စွာ ချိတ်ဆက်ပြီးပါပြီ! Model: ${res.model}`, 'success');
      } else {
        throw new Error(res.error || 'Connection failed');
      }
    } catch (e) {
      if (resultBox) {
        resultBox.className = 'p-3 rounded-xl text-xs bg-rose-950/40 text-rose-300 border border-rose-500/50';
        resultBox.innerHTML = `❌ ${e.message}`;
      }
      App.showToast(`❌ ${e.message}`, 'error');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<span>⚡</span> Test Connection`;
      }
    }
  },

  // --- Exact Timeline SRT Translate Methods ---
  async runSrtTimelineTranslate() {
    const input = document.getElementById('translate-srt-input-text');
    const output = document.getElementById('translate-srt-output-text');
    const btn = document.getElementById('btn-run-srt-translate');
    const dlBtn = document.getElementById('btn-download-translated-srt');
    const tableBody = document.getElementById('translate-srt-table-body');
    const previewBox = document.getElementById('translate-srt-preview-box');

    const text = input ? input.value.trim() : '';
    if (!text) {
      App.showToast('ကျေးဇူးပြု၍ တရုတ် SRT ဖိုင် တင်သွင်းပါ (သို့မဟုတ်) SRT စာသား ထည့်ပါ', 'warning');
      return;
    }

    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span class="animate-spin inline-block mr-1">⏳</span> Timeline အတိအကျဖြင့် ဘာသာပြန်နေပါသည်...`;
    }

    try {
      const res = await API.translateText(text);
      if (res && res.is_srt) {
        if (output) output.value = res.translated || '';
        this.translateSrtResult = res;

        if (dlBtn && res.burmese_srt_url) {
          dlBtn.href = res.burmese_srt_url;
          dlBtn.classList.remove('hidden');
        }

        // Render preview table
        if (previewBox) previewBox.classList.remove('hidden');
        if (tableBody && res.segments) {
          let rows = '';
          res.segments.forEach(s => {
            rows += `
              <tr class="border-b border-slate-800/60 hover:bg-slate-800/30 text-xs">
                <td class="p-2 text-slate-400 font-mono">${s.index}</td>
                <td class="p-2 text-blue-400 font-mono text-[11px] whitespace-nowrap">${s.start_str} → ${s.end_str}</td>
                <td class="p-2 text-slate-300">${s.zh_text || ''}</td>
                <td class="p-2 text-emerald-300 font-medium">${s.my_text || ''}</td>
              </tr>
            `;
          });
          tableBody.innerHTML = rows;
        }

        App.showToast(`🎉 စာကြောင်းရေ (${res.segments ? res.segments.length : 0}) ကြောင်းကို Timeline အတိအကျဖြင့် ဘာသာပြန်ပြီးပါပြီ!`, 'success');
      } else {
        if (output) output.value = res.translated || '';
        App.showToast('✅ ဘာသာပြန်ခြင်း ပြီးမြောက်ပါပြီ!', 'success');
      }
    } catch (e) {
      App.showToast('⚠️ Translation error: ' + e.message, 'error');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<span>⚡</span> Translate with Exact Timeline & Natural Burmese`;
      }
    }
  },

  handleTranslateSrtFileUpload(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      const input = document.getElementById('translate-srt-input-text');
      if (input) input.value = e.target.result;
      App.showToast(`📄 SRT ဖိုင် "${file.name}" ကို တင်သွင်းပြီးပါပြီ။ Translate ခလုတ်ကို နှိပ်ပါ`, 'info');
    };
    reader.readAsText(file);
  },

  sendTranslateSrtToStudio() {
    if (!this.translateSrtResult || !this.translateSrtResult.segments) {
      App.showToast('ဘာသာပြန်ထားသော SRT စာတန်းထိုး မရှိသေးပါ', 'warning');
      return;
    }
    this.currentSegments = this.translateSrtResult.segments;
    App.switchTab('transcribe');
    this.renderTimelineTable();
    const resBox = document.getElementById('transcribe-result-box');
    if (resBox) resBox.classList.remove('hidden');
    App.showToast('🎬 Translated SRT timeline ကို Subtitle Studio သို့ ထည့်သွင်းပြီးပါပြီ!', 'success');
  },

  escapeAttr(str) {
    return (str || '')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
};




