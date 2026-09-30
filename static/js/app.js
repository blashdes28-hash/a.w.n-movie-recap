// Main Application Controller
const App = {
  currentTab: 'script-assistant',

  init() {
    this.bindNavigation();
    this.bindModals();
    this.checkSystemStatus();

    // Initialize License & Device Control
    if (window.LicenseManager) {
      LicenseManager.init();
    }

    // Initialize submodules
    ScriptAssistant.init();
    RecapStudio.init();
    FreeVoice.init();
    Projects.init();
    SettingsView.init();
    Tools.init();

    // Default open Subtitles & Studio view
    this.switchTab('transcribe');
  },

  bindNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        const tab = item.getAttribute('data-tab');
        if (tab) {
          this.switchTab(tab);
        }
      });
    });

    // Top search bar
    const searchInput = document.getElementById('top-search-input');
    const searchBtn = document.getElementById('btn-top-search');
    if (searchInput && searchBtn) {
      const doSearch = () => {
        const query = searchInput.value.trim();
        if (!query) return;
        this.switchTab('script-assistant');
        const chatInput = document.getElementById('assistant-chat-input');
        if (chatInput) {
          chatInput.value = `'${query}' ဇာတ်ကားအတွက် ဆွဲဆောင်မှုရှိတဲ့ ရုပ်ရှင်အကျဉ်းချုပ် ဇာတ်ညွှန်း ရေးပေးပါ`;
          ScriptAssistant.sendMessage();
        }
      };
      searchBtn.addEventListener('click', doSearch);
      searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') doSearch();
      });
    }
  },

  toggleSidebar(forceState) {
    const sidebar = document.getElementById('main-sidebar');
    const backdrop = document.getElementById('sidebar-backdrop');
    if (!sidebar) return;

    const isCurrentlyClosed = sidebar.classList.contains('-translate-x-full');
    const shouldOpen = (typeof forceState === 'boolean') ? forceState : isCurrentlyClosed;

    if (shouldOpen) {
      sidebar.classList.remove('-translate-x-full');
      if (backdrop) backdrop.classList.remove('hidden');
      document.body.classList.add('sidebar-open');
    } else {
      sidebar.classList.add('-translate-x-full');
      if (backdrop) backdrop.classList.add('hidden');
      document.body.classList.remove('sidebar-open');
    }
  },

  switchTab(tabName) {
    this.currentTab = tabName;

    // Auto close mobile drawer on tab switch
    this.toggleSidebar(false);

    // Update sidebar navigation styling
    document.querySelectorAll('.nav-item').forEach(item => {
      const t = item.getAttribute('data-tab');
      if (t === tabName) {
        item.classList.add('bg-blue-600/20', 'text-blue-400', 'border-blue-500/40');
        item.classList.remove('text-slate-400', 'border-transparent');
      } else {
        item.classList.remove('bg-blue-600/20', 'text-blue-400', 'border-blue-500/40');
        item.classList.add('text-slate-400', 'border-transparent');
      }
    });

    // Update mobile bottom nav active status
    document.querySelectorAll('.mobile-nav-btn').forEach(btn => {
      const t = btn.getAttribute('data-tab');
      if (t === tabName) {
        btn.classList.add('text-blue-400', 'font-bold');
        btn.classList.remove('text-slate-400');
      } else if (t) {
        btn.classList.remove('text-blue-400', 'font-bold');
        btn.classList.add('text-slate-400');
      }
    });

    // Hide all tab views and show the selected one
    document.querySelectorAll('.view-tab').forEach(v => {
      v.classList.add('hidden');
    });

    const targetView = document.getElementById(`view-${tabName}`);
    if (targetView) {
      targetView.classList.remove('hidden');
    }

    if (tabName === 'projects' || tabName === 'dashboard') {
      Projects.loadProjects();
    }
    if (tabName === 'settings') {
      SettingsView.loadSettings();
    }
    if (tabName === 'licenses' && window.LicenseManager) {
      LicenseManager.loadLicensesList();
    }
    if (tabName === 'gemini-key' && window.Tools) {
      Tools.loadGeminiKeyForPage();
    }
  },

  bindModals() {
    // Upgrade Plan Modal
    const upgradeBtns = document.querySelectorAll('.btn-open-upgrade');
    const upgradeModal = document.getElementById('upgrade-plan-modal');
    upgradeBtns.forEach(b => {
      b.addEventListener('click', () => {
        if (upgradeModal) upgradeModal.classList.remove('hidden');
      });
    });

    // Close modals on clicking overlay or close button
    document.querySelectorAll('.modal-overlay').forEach(modal => {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) {
          modal.classList.add('hidden');
        }
      });
    });

    document.querySelectorAll('.btn-close-modal').forEach(btn => {
      btn.addEventListener('click', () => {
        const modal = btn.closest('.modal-overlay');
        if (modal) modal.classList.add('hidden');
      });
    });
  },

  openTelegramModal() {
    const modal = document.getElementById('telegram-connect-modal');
    if (modal) modal.classList.remove('hidden');
  },

  async checkSystemStatus() {
    try {
      const status = await API.getStatus();
      const dot = document.getElementById('sys-status-dot');
      const text = document.getElementById('sys-status-text');
      if (status.status === 'online') {
        if (dot) dot.className = 'w-2 h-2 rounded-full bg-emerald-400 animate-pulse';
        if (text) text.innerText = 'Edge TTS Engine Active • 100% Free';
      }
    } catch (e) {
      console.warn("Status check failed:", e);
    }
  },

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    const colors = {
      success: 'bg-emerald-950/90 border-emerald-500/50 text-emerald-200',
      error: 'bg-rose-950/90 border-rose-500/50 text-rose-200',
      warning: 'bg-amber-950/90 border-amber-500/50 text-amber-200',
      info: 'bg-slate-900/90 border-blue-500/50 text-slate-200'
    };

    toast.className = `flex items-center gap-2.5 px-4 py-3 rounded-xl border text-xs font-medium shadow-2xl backdrop-blur-md transition-all duration-300 transform translate-y-2 opacity-0 ${colors[type] || colors.info}`;
    toast.innerHTML = `
      <span>${type === 'success' ? '✓' : (type === 'error' ? '✕' : (type === 'warning' ? '⚠' : 'ℹ'))}</span>
      <span>${message}</span>
    `;

    container.appendChild(toast);
    
    // Animate in
    requestAnimationFrame(() => {
      toast.classList.remove('translate-y-2', 'opacity-0');
    });

    // Remove after 3.5s
    setTimeout(() => {
      toast.classList.add('opacity-0', 'translate-y-2');
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }
};

window.addEventListener('DOMContentLoaded', () => {
  App.init();
});
