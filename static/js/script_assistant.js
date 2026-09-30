// Script Assistant Module
const ScriptAssistant = {
  chatHistory: [],
  currentAudio: null,
  currentSubtitles: [],
  subtitlesIndex: 0,
  isPlaying: false,

  init() {
    this.bindEvents();
    this.setupQuickPrompts();
  },

  bindEvents() {
    const sendBtn = document.getElementById('btn-assistant-send');
    const input = document.getElementById('assistant-chat-input');
    
    if (sendBtn && input) {
      sendBtn.addEventListener('click', () => this.sendMessage());
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });
    }

    // Video player controls
    const playBtn = document.getElementById('player-play-btn');
    const seekBackBtn = document.getElementById('player-seek-back');
    const seekForwardBtn = document.getElementById('player-seek-forward');

    if (playBtn) {
      playBtn.addEventListener('click', () => this.togglePlayback());
    }
    if (seekBackBtn) {
      seekBackBtn.addEventListener('click', () => this.seekBy(-5));
    }
    if (seekForwardBtn) {
      seekForwardBtn.addEventListener('click', () => this.seekBy(5));
    }
  },

  setupQuickPrompts() {
    const pills = document.querySelectorAll('.quick-prompt-pill');
    const input = document.getElementById('assistant-chat-input');
    pills.forEach(pill => {
      pill.addEventListener('click', () => {
        const prompt = pill.getAttribute('data-prompt');
        if (input && prompt) {
          input.value = prompt;
          input.focus();
        }
      });
    });
  },

  async sendMessage(customText = null) {
    const input = document.getElementById('assistant-chat-input');
    const message = customText || (input ? input.value.trim() : '');
    if (!message) return;

    if (input) input.value = '';

    // Append user message
    this.appendMessage('user', message);

    // Show typing loader
    const loaderId = this.showLoadingIndicator();

    try {
      const activeModel = document.getElementById('select-script-model')?.value || 'gemini-2.5-flash';
      const res = await API.chatScript(message, this.chatHistory, activeModel);
      
      this.removeLoadingIndicator(loaderId);

      const reply = res.response || 'ဇာတ်ညွှန်းကို ထုတ်ယူရာတွင် အခက်အခဲ ရှိခဲ့ပါသည်။';
      this.appendMessage('assistant', reply, res.engine);

      // Update history
      this.chatHistory.push({ role: 'user', content: message });
      this.chatHistory.push({ role: 'assistant', content: reply });

      // Automatically synthesize speech preview for the central player
      this.loadNarrationToPlayer(reply);

    } catch (err) {
      this.removeLoadingIndicator(loaderId);
      this.appendMessage('assistant', `⚠️ Error: ${err.message}. ကျေးဇူးပြု၍ ပြန်လည်ကြိုးစားပါ။`);
    }
  },

  appendMessage(role, text, engine = null) {
    const container = document.getElementById('assistant-chat-messages');
    if (!container) return;

    const msgDiv = document.createElement('div');
    msgDiv.className = `flex flex-col ${role === 'user' ? 'items-end' : 'items-start'} mb-4 transition-all`;

    if (role === 'user') {
      msgDiv.innerHTML = `
        <div class="max-w-[85%] rounded-2xl rounded-tr-sm bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-3 text-white text-sm shadow-md font-medium leading-relaxed">
          ${this.escapeHtml(text)}
        </div>
        <span class="text-[11px] text-slate-500 mt-1 mr-1">You</span>
      `;
    } else {
      const msgId = 'msg_' + Math.random().toString(36).substr(2, 9);
      msgDiv.innerHTML = `
        <div class="max-w-[90%] rounded-2xl rounded-tl-sm bg-slate-800/90 border border-slate-700/60 px-4 py-3.5 text-slate-100 text-sm shadow-lg leading-relaxed font-sans">
          <div class="whitespace-pre-wrap leading-relaxed text-slate-200" id="${msgId}-text">${this.escapeHtml(text)}</div>
          
          <div class="mt-3 pt-2.5 border-t border-slate-700/50 flex flex-wrap items-center justify-between gap-2">
            <span class="text-[11px] text-cyan-400 font-medium flex items-center gap-1">
              <span class="inline-block w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
              ${engine || 'ACT AI Assistant'}
            </span>
            <div class="flex items-center gap-1.5">
              <button onclick="ScriptAssistant.loadNarrationToPlayer('${msgId}')" class="px-2.5 py-1 text-xs rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 border border-blue-500/30 flex items-center gap-1 transition">
                ▶ စမ်းနားထောင်
              </button>
              <button onclick="ScriptAssistant.applyToStudio('${msgId}')" class="px-2.5 py-1 text-xs rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/30 flex items-center gap-1 transition">
                🎬 Studio သို့ပို့
              </button>
              <button onclick="ScriptAssistant.copyText('${msgId}')" class="px-2 py-1 text-xs rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 transition" title="Copy">
                📋
              </button>
            </div>
          </div>
        </div>
        <span class="text-[11px] text-slate-500 mt-1 ml-1">Script Assistant</span>
      `;
    }

    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
  },

  showLoadingIndicator() {
    const container = document.getElementById('assistant-chat-messages');
    if (!container) return null;

    const id = 'loader_' + Date.now();
    const div = document.createElement('div');
    div.id = id;
    div.className = 'flex items-center gap-2 text-slate-400 text-xs py-2 px-3 bg-slate-800/40 rounded-xl max-w-fit mb-3';
    div.innerHTML = `
      <span class="animate-spin text-sm">⚡</span>
      <span>ဇာတ်ညွှန်း ရေးသားနေပါသည် (Generating Burmese script)...</span>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
  },

  removeLoadingIndicator(id) {
    if (!id) return;
    const el = document.getElementById(id);
    if (el) el.remove();
  },

  async loadNarrationToPlayer(textOrId) {
    let scriptText = textOrId;
    if (textOrId.startsWith('msg_')) {
      const el = document.getElementById(textOrId + '-text');
      if (el) scriptText = el.innerText;
    }

    if (!scriptText) return;

    // Show indicator on player
    const banner = document.getElementById('player-subtitle-overlay');
    if (banner) {
      banner.innerText = 'အသံဖိုင် စတင်ဖန်တီးနေပါသည်...';
      banner.classList.remove('hidden');
    }

    try {
      const voice = document.getElementById('select-burmese-voice')?.value || 'my-MM-ThihaNeural';
      const speed = document.getElementById('select-voice-speed')?.value || '+0%';
      const pitch = document.getElementById('select-voice-pitch')?.value || '+0Hz';

      const res = await API.generateTTS(scriptText, voice, speed, pitch);
      
      this.currentSubtitles = res.subtitles || [];
      
      // Stop old audio if playing
      if (this.currentAudio) {
        this.currentAudio.pause();
      }

      this.currentAudio = new Audio(res.audio_url);
      
      // Update audio durations
      this.currentAudio.addEventListener('timeupdate', () => {
        this.syncPlayerSubtitles();
      });

      this.currentAudio.addEventListener('ended', () => {
        this.isPlaying = false;
        this.updatePlayButton();
      });

      // Start playing
      this.currentAudio.play();
      this.isPlaying = true;
      this.updatePlayButton();

      // Show toast
      App.showToast('✅ ဇာတ်လမ်းပြော အသံဖိုင် အဆင်သင့်ဖြစ်ပါပြီ', 'success');

    } catch (e) {
      console.error(e);
      if (banner) banner.innerText = 'အသံဖန်တီးရာတွင် အမှားဖြစ်ခဲ့ပါသည်။';
      App.showToast('⚠️ Voice synthesis error: ' + e.message, 'error');
    }
  },

  syncPlayerSubtitles() {
    if (!this.currentAudio) return;
    const currentTime = this.currentAudio.currentTime;
    const duration = this.currentAudio.duration || 1;

    // Update progress bar
    const progressEl = document.getElementById('player-progress-fill');
    const timeEl = document.getElementById('player-time-display');
    if (progressEl) {
      const pct = (currentTime / duration) * 100;
      progressEl.style.width = pct + '%';
    }
    if (timeEl) {
      const curM = Math.floor(currentTime / 60);
      const curS = Math.floor(currentTime % 60);
      const durM = Math.floor(duration / 60);
      const durS = Math.floor(duration % 60);
      timeEl.innerText = `${curM}:${curS < 10 ? '0' : ''}${curS} / ${durM}:${durS < 10 ? '0' : ''}${durS}`;
    }

    // Find active subtitle
    const currentSub = this.currentSubtitles.find(s => currentTime >= s.start && currentTime <= s.end);
    const banner = document.getElementById('player-subtitle-overlay');
    if (banner) {
      if (currentSub) {
        banner.innerText = currentSub.text;
        banner.classList.remove('hidden');
      }
    }
  },

  togglePlayback() {
    if (!this.currentAudio) {
      // If no audio is loaded, pick latest message or sample
      const firstMsg = document.querySelector('[id$="-text"]');
      if (firstMsg) {
        this.loadNarrationToPlayer(firstMsg.innerText);
        return;
      }
      this.sendMessage("ဒီနေ့အတွက် အကောင်းဆုံး ဇာတ်လမ်းပြော ရေးပေးပါ");
      return;
    }

    if (this.isPlaying) {
      this.currentAudio.pause();
      this.isPlaying = false;
    } else {
      this.currentAudio.play();
      this.isPlaying = true;
    }
    this.updatePlayButton();
  },

  seekBy(delta) {
    if (!this.currentAudio) return;
    this.currentAudio.currentTime = Math.max(0, Math.min(this.currentAudio.duration, this.currentAudio.currentTime + delta));
  },

  updatePlayButton() {
    const playBtn = document.getElementById('player-play-btn');
    if (playBtn) {
      playBtn.innerHTML = this.isPlaying ? '❚❚' : '▶';
    }
  },

  applyToStudio(msgId) {
    const el = document.getElementById(msgId + '-text');
    if (!el) return;
    const script = el.innerText;
    
    // Switch to Recap Studio tab and set script
    App.switchTab('recap-studio');
    const studioScriptInput = document.getElementById('studio-script-textarea');
    if (studioScriptInput) {
      studioScriptInput.value = script;
      studioScriptInput.focus();
    }
    App.showToast('✅ ဇာတ်ညွှန်းကို Recap Studio သို့ ထည့်သွင်းပြီးပါပြီ', 'success');
  },

  copyText(msgId) {
    const el = document.getElementById(msgId + '-text');
    if (!el) return;
    navigator.clipboard.writeText(el.innerText).then(() => {
      App.showToast('📋 Copied to clipboard!', 'info');
    });
  },

  escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
};
