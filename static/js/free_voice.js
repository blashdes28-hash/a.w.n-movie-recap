// Free Voice TTS Studio Module
const FreeVoice = {
  currentAudio: null,
  lastGenerated: null,

  init() {
    this.bindEvents();
  },

  bindEvents() {
    const genBtn = document.getElementById('btn-fv-generate');
    const input = document.getElementById('fv-text-input');

    if (genBtn) {
      genBtn.addEventListener('click', () => this.generateVoice());
    }

    if (input) {
      input.addEventListener('input', () => {
        const len = input.value.length;
        const words = input.value.trim() ? input.value.trim().split(/\s+/).length : 0;
        const countEl = document.getElementById('fv-char-count');
        if (countEl) {
          countEl.innerText = `${len} characters • ~${Math.round(len / 15)} sec estimated narration`;
        }
      });
    }

    // Free Voice Sample presets
    const samples = document.querySelectorAll('.fv-sample-chip');
    samples.forEach(chip => {
      chip.addEventListener('click', () => {
        const txt = chip.getAttribute('data-sample');
        if (input && txt) {
          input.value = txt;
          input.dispatchEvent(new Event('input'));
        }
      });
    });
  },

  async generateVoice() {
    const input = document.getElementById('fv-text-input');
    const text = input ? input.value.trim() : '';
    if (!text) {
      App.showToast('ကျေးဇူးပြု၍ အသံဖလှယ်မည့် စာသား ရိုက်ထည့်ပါ', 'warning');
      return;
    }

    const voice = document.getElementById('fv-select-voice')?.value || 'my-MM-ThihaNeural';
    const speed = document.getElementById('fv-select-speed')?.value || '+0%';
    const pitch = document.getElementById('fv-select-pitch')?.value || '+0Hz';

    const btn = document.getElementById('btn-fv-generate');
    if (btn) {
      btn.innerHTML = `<span class="animate-spin">⏳</span> အသံဖန်တီးနေသည်...`;
      btn.disabled = true;
    }

    try {
      const res = await API.generateTTS(text, voice, speed, pitch);
      this.lastGenerated = res;

      // Update Audio Player
      const playerContainer = document.getElementById('fv-player-container');
      const audioTag = document.getElementById('fv-audio-tag');
      const durationLabel = document.getElementById('fv-duration-label');
      const dlMp3 = document.getElementById('fv-dl-mp3');
      const dlSrt = document.getElementById('fv-dl-srt');
      const sendStudioBtn = document.getElementById('fv-btn-to-studio');

      if (playerContainer) playerContainer.classList.remove('hidden');
      if (audioTag) {
        audioTag.src = res.audio_url;
        audioTag.play();
      }
      if (durationLabel) {
        durationLabel.innerText = `Duration: ${res.duration_str} (${res.subtitles.length} subtitle captions)`;
      }
      if (dlMp3) {
        dlMp3.href = res.audio_url;
        dlMp3.download = res.audio_file;
      }
      if (dlSrt) {
        dlSrt.href = res.srt_url;
        dlSrt.download = res.srt_file;
      }
      if (sendStudioBtn) {
        sendStudioBtn.onclick = () => {
          App.switchTab('recap-studio');
          const studioScript = document.getElementById('studio-script-textarea');
          if (studioScript) studioScript.value = text;
          App.showToast('✅ Script imported into Recap Studio!', 'success');
        };
      }

      App.showToast('🎉 မြန်မာ အသံဇာတ်ပြော အောင်မြင်စွာ ဖန်တီးပြီးပါပြီ!', 'success');

    } catch (e) {
      App.showToast('⚠️ TTS Error: ' + e.message, 'error');
    } finally {
      if (btn) {
        btn.innerHTML = `<span>🎙</span> မြန်မာအသံ ထုတ်ယူမည် (Generate Free Voice)`;
        btn.disabled = false;
      }
    }
  }
};
