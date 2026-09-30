const RecapStudio = {
  activeStepTab: 'ai-voice',
  currentJobId: null,
  pollTimer: null,
  activeProjectId: null,
  attachedSourceVideo: null,
  attachedSourceVideoUrl: null,

  init() {
    this.bindStepTabs();
    this.bindStudioEvents();
    this.loadInitialSettings();
  },

  setSourceVideo(filename, url = null) {
    this.attachedSourceVideo = filename;
    this.attachedSourceVideoUrl = url || (filename ? `/media/uploads/${filename}` : null);
    
    // Update UI badge if exists
    const badge = document.getElementById('studio-attached-video-badge');
    if (badge) {
      if (filename) {
        badge.innerHTML = `
          <div class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs">
            <span>🎬</span>
            <span class="font-medium truncate max-w-[220px]">${filename}</span>
            <span class="text-[10px] bg-emerald-500/30 px-1.5 py-0.5 rounded text-white font-semibold">Active Video</span>
          </div>
        `;
        badge.classList.remove('hidden');
      } else {
        badge.classList.add('hidden');
      }
    }
  },

  bindStepTabs() {
    const tabs = document.querySelectorAll('.studio-step-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const step = tab.getAttribute('data-step');
        this.switchStep(step);
      });
    });
  },

  switchStep(stepName) {
    this.activeStepTab = stepName;
    document.querySelectorAll('.studio-step-tab').forEach(t => {
      const active = t.getAttribute('data-step') === stepName;
      if (active) {
        t.className = 'studio-step-tab px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 text-white shadow-md shadow-blue-500/30 transition flex items-center gap-1.5 cursor-pointer';
      } else {
        t.className = 'studio-step-tab px-3.5 py-1.5 text-xs font-medium rounded-lg bg-slate-800/80 hover:bg-slate-750 text-slate-300 border border-slate-700/60 transition flex items-center gap-1.5 cursor-pointer';
      }
    });

    // Toggle panels
    document.querySelectorAll('.studio-step-panel').forEach(p => {
      p.classList.add('hidden');
    });
    const activePanel = document.getElementById(`panel-${stepName}`);
    if (activePanel) {
      activePanel.classList.remove('hidden');
    }
  },

  bindStudioEvents() {
    // Create recap button
    const createBtn = document.getElementById('btn-create-recap');
    if (createBtn) {
      createBtn.addEventListener('click', () => this.startRecapCreation());
    }

    // Voice audition button
    const testVoiceBtn = document.getElementById('btn-test-voice');
    if (testVoiceBtn) {
      testVoiceBtn.addEventListener('click', () => this.testBurmeseVoice());
    }

    // Telegram connect / test button
    const tgBtn = document.getElementById('btn-studio-tg-connect');
    if (tgBtn) {
      tgBtn.addEventListener('click', () => App.openTelegramModal());
    }

    // Video aspect ratio buttons
    const ratioBtns = document.querySelectorAll('.aspect-ratio-btn');
    ratioBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        ratioBtns.forEach(b => b.classList.remove('border-blue-500', 'bg-blue-500/20', 'text-blue-300'));
        btn.classList.add('border-blue-500', 'bg-blue-500/20', 'text-blue-300');
        const ratio = btn.getAttribute('data-ratio');
        const preview = document.getElementById('studio-preview-box');
        if (preview) {
          if (ratio === '9:16') {
            preview.style.aspectRatio = '9 / 16';
            preview.style.maxWidth = '320px';
          } else {
            preview.style.aspectRatio = '16 / 9';
            preview.style.maxWidth = '100%';
          }
        }
      });
    });

    // Subtitle preview live update
    const subColorInput = document.getElementById('studio-sub-color');
    const subSizeInput = document.getElementById('studio-sub-size');
    const liveSubSample = document.getElementById('studio-live-subtitle');

    if (subColorInput && liveSubSample) {
      subColorInput.addEventListener('input', (e) => {
        liveSubSample.style.color = e.target.value;
      });
    }
    if (subSizeInput && liveSubSample) {
      const updatePreviewSize = () => {
        const val = parseInt(subSizeInput.value) || 26;
        const box = document.getElementById('studio-preview-box');
        if (box && liveSubSample) {
          const boxHeight = box.clientHeight || 300;
          // The backend scales font_size based on 1080p base height
          const pxSize = (val / 1080) * boxHeight;
          liveSubSample.style.fontSize = Math.max(8, pxSize) + 'px';
        }
        const label = document.getElementById('sub-size-val');
        if (label) label.innerText = val + 'px';
      };
      subSizeInput.addEventListener('input', updatePreviewSize);
      const box = document.getElementById('studio-preview-box');
      if(box) new ResizeObserver(updatePreviewSize).observe(box);
      setTimeout(updatePreviewSize, 100);
    }

    // Video upload input listener in Studio
    const videoUploadInput = document.getElementById('studio-video-upload');
    if (videoUploadInput) {
      videoUploadInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        App.showToast('⏳ ဗီဒီယိုဖိုင် တင်သွင်းနေပါသည်...', 'info');
        try {
          const res = await API.uploadFile(file);
          if (res && res.filename) {
            this.setSourceVideo(res.filename, res.url);
            App.showToast('✅ ဗီဒီယိုဖိုင် အောင်မြင်စွာ ချိတ်ဆက်ပြီးပါပြီ!', 'success');
          }
        } catch (err) {
          App.showToast('Video upload failed: ' + err.message, 'error');
        }
      });
    }
  },

  async loadInitialSettings() {
    try {
      const cfg = await API.getSettings();
      if (cfg) {
        if (cfg.telegram_bot_token && cfg.telegram_chat_id) {
          const badge = document.getElementById('tg-connection-status');
          if (badge) {
            badge.innerHTML = `<span class="text-emerald-400 font-medium">✓ ချိတ်ဆက်ပြီးပါပြီ (@connected)</span>`;
          }
        }
      }
    } catch (e) {
      console.warn("Could not load studio settings:", e);
    }
  },

  async testBurmeseVoice() {
    const voiceSelect = document.getElementById('select-burmese-voice');
    const voice = voiceSelect ? voiceSelect.value : 'my-MM-ThihaNeural';
    const testBtn = document.getElementById('btn-test-voice');
    
    if (testBtn) testBtn.innerHTML = '⏳ နားထောင်နေသည်...';

    try {
      const res = await API.previewVoice("မင်္ဂလာပါ၊ ဒါကတော့ ACT RECAP ရဲ့ မြန်မာ အသံဇာတ်ပြော စမ်းသပ်မှု ဖြစ်ပါတယ်။", voice);
      const audio = new Audio(res.audio_url);
      audio.play();
      audio.onended = () => {
        if (testBtn) testBtn.innerHTML = '🔊 စမ်းသပ်နားထောင်မည်';
      };
    } catch (e) {
      App.showToast('Voice preview failed: ' + e.message, 'error');
      if (testBtn) testBtn.innerHTML = '🔊 စမ်းသပ်နားထောင်မည်';
    }
  },

  async startRecapCreation() {
    const titleInput = document.getElementById('studio-movie-title');
    const scriptInput = document.getElementById('studio-script-textarea');

    const title = titleInput ? titleInput.value.trim() : 'ရုပ်ရှင် ဇာတ်လမ်းပြော';
    const script = scriptInput ? scriptInput.value.trim() : '';

    if (!script) {
      App.showToast('ကျေးဇူးပြု၍ ဇာတ်ညွှန်း (Script) အရင် ထည့်သွင်းပေးပါ', 'warning');
      this.switchStep('ai-voice');
      scriptInput?.focus();
      return;
    }

    // Show rendering modal
    this.openRenderModal(title);

    try {
      // 1. Create or update project
      const voice = document.getElementById('select-burmese-voice')?.value || 'my-MM-ThihaNeural';
      const speed = document.getElementById('select-voice-speed')?.value || '+0%';
      const pitch = document.getElementById('select-voice-pitch')?.value || '+0Hz';

      const projectData = {
        title: title || 'Movie Recap',
        movie_name: title,
        script: script,
        voice: voice,
        rate: speed,
        pitch: pitch,
        source_video_file: this.attachedSourceVideo,
        status: 'draft'
      };

      const project = await API.createProject(projectData);
      this.activeProjectId = project.id;

      // 2. Collect render options
      const watermarkText = document.getElementById('studio-wm-text')?.value || '@actrecap';
      const watermarkPos = document.getElementById('studio-wm-pos')?.value || 'top-right';
      const watermarkOpacity = parseFloat(document.getElementById('studio-wm-opacity')?.value || '0.8');
      const subColor = document.getElementById('studio-sub-color')?.value || '#ffffff';
      const subSize = parseInt(document.getElementById('studio-sub-size')?.value || '24');
      const fontName = document.getElementById('studio-sub-font')?.value || 'Pyidaungsu';
      const antiCopyright = document.getElementById('studio-toggle-anticopyright')?.checked ?? true;
      const mirrorFlip = document.getElementById('studio-toggle-mirror')?.checked ?? false;
      const bgmEnabled = document.getElementById('studio-toggle-bgm')?.checked ?? true;
      const bgmVol = parseFloat(document.getElementById('studio-bgm-volume')?.value || '0.12');
      const aspect = document.querySelector('.aspect-ratio-btn.border-blue-500')?.getAttribute('data-ratio') || '16:9';

      const renderPayload = {
        project_id: project.id,
        source_video_file: this.attachedSourceVideo,
        watermark_text: watermarkText,
        watermark_pos: watermarkPos,
        watermark_opacity: watermarkOpacity,
        title_text: title,
        sub_color: subColor,
        sub_font_size: subSize,
        font_name: fontName,
        anti_copyright: antiCopyright,
        mirror_flip: mirrorFlip,
        bgm_enabled: bgmEnabled,
        bgm_volume: bgmVol,
        aspect_ratio: aspect
      };

      // 3. Trigger Render API
      const renderRes = await API.renderProject(project.id, renderPayload);
      this.currentJobId = renderRes.job_id;

      // 4. Poll status
      this.pollRenderProgress(this.currentJobId);

    } catch (e) {
      console.error(e);
      this.updateRenderModalStatus('error', 0, '⚠️ Error: ' + e.message);
    }
  },

  pollRenderProgress(jobId) {
    if (this.pollTimer) clearInterval(this.pollTimer);

    this.pollTimer = setInterval(async () => {
      try {
        const res = await API.getRenderStatus(jobId);
        if (!res) return;

        this.updateRenderModalStatus(res.status, res.progress, res.step, res.output_video);

        if (res.status === 'completed' || res.status === 'error') {
          clearInterval(this.pollTimer);
          if (res.status === 'completed') {
            App.showToast('🎉 Recap video rendered successfully!', 'success');
            // Refresh projects
            Projects.loadProjects();
          }
        }
      } catch (e) {
        console.error("Poll error:", e);
      }
    }, 1500);
  },

  openRenderModal(title) {
    const modal = document.getElementById('render-progress-modal');
    if (!modal) return;

    modal.classList.remove('hidden');
    document.getElementById('render-modal-title').innerText = title;
    this.updateRenderModalStatus('processing', 5, 'Starting ACT Recap Engine...');
  },

  updateRenderModalStatus(status, progress, stepText, outputVideo = null) {
    const bar = document.getElementById('render-modal-progress-bar');
    const pct = document.getElementById('render-modal-pct');
    const step = document.getElementById('render-modal-step');
    const actionArea = document.getElementById('render-modal-actions');

    if (bar) bar.style.width = `${progress}%`;
    if (pct) pct.innerText = `${progress}%`;
    if (step) step.innerText = stepText || '';

    if (status === 'completed' && outputVideo) {
      if (actionArea) {
        actionArea.innerHTML = `
          <div class="mt-4 p-4 rounded-xl bg-slate-800/80 border border-slate-700 flex flex-col gap-3">
            <video src="/media/output/${outputVideo}" controls autoplay class="w-full rounded-lg max-h-56 bg-black"></video>
            <div class="flex items-center justify-between gap-2 mt-2">
              <a href="/media/output/${outputVideo}" download class="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs flex items-center gap-1.5 transition">
                ⬇ Download MP4 Video
              </a>
              <button onclick="RecapStudio.sendCurrentToTelegram()" class="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-medium text-xs flex items-center gap-1.5 transition">
                ✈ Send to Telegram PM
              </button>
              <button onclick="document.getElementById('render-progress-modal').classList.add('hidden')" class="px-3 py-2 rounded-lg bg-slate-700 text-slate-300 text-xs hover:bg-slate-600 transition">
                Close
              </button>
            </div>
          </div>
        `;
      }
    }
  },

  async sendCurrentToTelegram() {
    if (!this.activeProjectId) return;
    try {
      App.showToast('✈ Sending video to Telegram PM...', 'info');
      const res = await API.sendToTelegram(this.activeProjectId);
      if (res.success) {
        App.showToast('✅ Telegram သို့ ဗီဒီယို ပေးပို့ပြီးပါပြီ!', 'success');
      } else {
        App.showToast('⚠️ Telegram failed: ' + (res.error || 'Check bot settings'), 'error');
      }
    } catch (e) {
      App.showToast('⚠️ Error: ' + e.message, 'error');
    }
  }
};
