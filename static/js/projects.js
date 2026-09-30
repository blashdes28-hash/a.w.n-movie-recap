// Projects Gallery and Manager Module
const Projects = {
  list: [],

  init() {
    this.loadProjects();
  },

  async loadProjects() {
    const container = document.getElementById('projects-grid');
    if (!container) return;

    try {
      this.list = await API.getProjects();
      this.render();
      this.updateDashboardStats();
    } catch (e) {
      console.error("Failed to load projects:", e);
    }
  },

  render() {
    const container = document.getElementById('projects-grid');
    if (!container) return;

    if (!this.list || this.list.length === 0) {
      container.innerHTML = `
        <div class="col-span-full text-center py-16 text-slate-500 glass-panel p-8">
          <div class="text-4xl mb-3">🎬</div>
          <p class="text-base text-slate-400 font-medium">ပရောဂျက် မရှိသေးပါ (No projects yet)</p>
          <p class="text-xs text-slate-500 mt-1">Script Assistant သို့မဟုတ် Recap Studio မှ စတင်ဖန်တီးနိုင်ပါသည်။</p>
          <button onclick="App.switchTab('script-assistant')" class="mt-4 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md transition">
            + Create New Recap
          </button>
        </div>
      `;
      return;
    }

    container.innerHTML = this.list.map(p => {
      const isRendered = p.status === 'rendered' && p.video_file;
      const isAudioReady = p.audio_file;
      const dateStr = new Date((p.updated_at || p.created_at) * 1000).toLocaleDateString('my-MM', {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
      });

      const badgeColor = isRendered ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' :
                        (p.status === 'rendering' ? 'bg-amber-500/20 text-amber-300 border-amber-500/30 animate-pulse' :
                        'bg-blue-500/20 text-blue-300 border-blue-500/30');

      const statusText = isRendered ? 'Rendered MP4' : (p.status === 'rendering' ? 'Rendering...' : 'Draft / Audio');

      return `
        <div class="glass-panel hover:border-slate-600 transition flex flex-col justify-between overflow-hidden group">
          <div class="p-4">
            <div class="flex items-start justify-between gap-2 mb-2">
              <span class="px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${badgeColor}">
                ${statusText}
              </span>
              <span class="text-[11px] text-slate-500">${dateStr}</span>
            </div>
            
            <h3 class="text-sm font-bold text-white line-clamp-1 group-hover:text-blue-400 transition mb-1">
              ${this.escapeHtml(p.title || p.movie_name || 'Movie Recap')}
            </h3>
            
            <p class="text-xs text-slate-400 line-clamp-2 leading-relaxed mb-3">
              ${this.escapeHtml(p.script || 'No script text')}
            </p>

            <div class="flex items-center gap-3 text-[11px] text-slate-400 pt-2 border-t border-slate-800">
              <span class="flex items-center gap-1">🎙 ${p.voice?.includes('Thiha') ? 'သီဟ' : 'နီလာ'}</span>
              <span>•</span>
              <span class="flex items-center gap-1">⏱ ${p.duration_str || '00:00'}</span>
            </div>
          </div>

          <div class="bg-slate-900/60 px-4 py-2.5 border-t border-slate-800/80 flex items-center justify-between gap-1.5">
            <div class="flex items-center gap-1">
              ${isRendered ? `
                <button onclick="Projects.previewVideo('${p.id}')" class="px-2.5 py-1 text-xs rounded bg-blue-600 hover:bg-blue-500 text-white font-medium transition flex items-center gap-1">
                  ▶ ကြည့်မည်
                </button>
                <a href="/media/output/${p.video_file}" download class="px-2 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-slate-200 transition" title="Download Video">
                  ⬇ MP4
                </a>
              ` : `
                <button onclick="Projects.openInStudio('${p.id}')" class="px-2.5 py-1 text-xs rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition">
                  ✏ Edit in Studio
                </button>
              `}
              
              ${isAudioReady ? `
                <a href="/media/output/${p.audio_file}" download class="px-2 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-slate-200 transition" title="Download Narration Audio">
                  🎵 MP3
                </a>
              ` : ''}
            </div>

            <div class="flex items-center gap-1">
              <button onclick="Projects.sendToTelegram('${p.id}')" class="px-2 py-1 text-xs rounded bg-sky-600/30 hover:bg-sky-600/50 text-sky-300 transition" title="Send to Telegram">
                ✈
              </button>
              <button onclick="Projects.deleteProject('${p.id}')" class="px-2 py-1 text-xs rounded bg-rose-600/20 hover:bg-rose-600/40 text-rose-300 transition" title="Delete">
                🗑
              </button>
            </div>
          </div>
        </div>
      `;
    }).join('');
  },

  updateDashboardStats() {
    const totalEl = document.getElementById('stat-total-projects');
    const renderedEl = document.getElementById('stat-rendered-recaps');
    const audioEl = document.getElementById('stat-audio-count');

    if (totalEl) totalEl.innerText = this.list.length;
    if (renderedEl) {
      const renderedCount = this.list.filter(p => p.status === 'rendered').length;
      renderedEl.innerText = renderedCount;
    }
    if (audioEl) {
      const audioCount = this.list.filter(p => p.audio_file).length;
      audioEl.innerText = audioCount;
    }
  },

  previewVideo(id) {
    const p = this.list.find(x => x.id === id);
    if (!p || !p.video_file) return;

    const modal = document.getElementById('video-preview-modal');
    const video = document.getElementById('preview-modal-video');
    const title = document.getElementById('preview-modal-title');
    const dlBtn = document.getElementById('preview-modal-download');

    if (modal && video) {
      video.src = `/media/output/${p.video_file}`;
      if (title) title.innerText = p.title || 'Movie Recap Preview';
      if (dlBtn) dlBtn.href = `/media/output/${p.video_file}`;
      modal.classList.remove('hidden');
      video.play();
    }
  },

  openInStudio(id) {
    const p = this.list.find(x => x.id === id);
    if (!p) return;

    App.switchTab('recap-studio');
    const titleInput = document.getElementById('studio-movie-title');
    const scriptInput = document.getElementById('studio-script-textarea');
    if (titleInput) titleInput.value = p.title || p.movie_name || '';
    if (scriptInput) scriptInput.value = p.script || '';
    App.showToast('✅ Project loaded into Recap Studio', 'info');
  },

  async sendToTelegram(id) {
    try {
      App.showToast('✈ Sending to Telegram PM...', 'info');
      const res = await API.sendToTelegram(id);
      if (res.success) {
        App.showToast('✅ Sent to Telegram PM successfully!', 'success');
      } else {
        App.showToast('⚠️ Telegram: ' + (res.error || 'Failed'), 'error');
      }
    } catch (e) {
      App.showToast('⚠️ Error: ' + e.message, 'error');
    }
  },

  async deleteProject(id) {
    if (!confirm('Are you sure you want to delete this recap project?')) return;
    try {
      await API.deleteProject(id);
      App.showToast('🗑 Project deleted', 'info');
      this.loadProjects();
    } catch (e) {
      App.showToast('⚠️ Error: ' + e.message, 'error');
    }
  },

  escapeHtml(str) {
    return (str || '')
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
};
