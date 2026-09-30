// Settings and Configuration Module
const SettingsView = {
  init() {
    this.loadSettings();
    this.bindEvents();
  },

  async loadSettings() {
    try {
      const cfg = await API.getSettings();
      if (!cfg) return;

      const geminiInput = document.getElementById('setting-gemini-key');
      const orInput = document.getElementById('setting-or-key');
      const tgTokenInput = document.getElementById('setting-tg-token');
      const tgChatIdInput = document.getElementById('setting-tg-chat-id');
      const defaultVoice = document.getElementById('setting-default-voice');
      const autoTg = document.getElementById('setting-auto-tg');
      const wmText = document.getElementById('setting-wm-text');

      if (geminiInput) geminiInput.value = cfg.gemini_api_key || '';
      if (orInput) orInput.value = cfg.openrouter_api_key || '';
      if (tgTokenInput) tgTokenInput.value = cfg.telegram_bot_token || '';
      if (tgChatIdInput) tgChatIdInput.value = cfg.telegram_chat_id || '';
      if (defaultVoice) defaultVoice.value = cfg.default_voice || 'my-MM-ThihaNeural';
      if (autoTg) autoTg.checked = cfg.telegram_auto_send ?? true;
      if (wmText) wmText.value = cfg.watermark_text || '@actrecap';

    } catch (e) {
      console.error("Failed to load settings:", e);
    }
  },

  bindEvents() {
    const saveBtn = document.getElementById('btn-save-settings');
    const testTgBtn = document.getElementById('btn-test-tg-settings');

    if (saveBtn) {
      saveBtn.addEventListener('click', () => this.save());
    }

    if (testTgBtn) {
      testTgBtn.addEventListener('click', () => this.testTelegramConnection());
    }
  },

  async save() {
    const geminiKey = document.getElementById('setting-gemini-key')?.value.trim();
    const orKey = document.getElementById('setting-or-key')?.value.trim();
    const tgToken = document.getElementById('setting-tg-token')?.value.trim();
    const tgChatId = document.getElementById('setting-tg-chat-id')?.value.trim();
    const defaultVoice = document.getElementById('setting-default-voice')?.value;
    const autoTg = document.getElementById('setting-auto-tg')?.checked;
    const wmText = document.getElementById('setting-wm-text')?.value.trim();

    const payload = {
      gemini_api_key: geminiKey,
      openrouter_api_key: orKey,
      telegram_bot_token: tgToken,
      telegram_chat_id: tgChatId,
      default_voice: defaultVoice,
      telegram_auto_send: autoTg,
      watermark_text: wmText
    };

    try {
      await API.saveSettings(payload);
      App.showToast('✅ Configurations saved successfully!', 'success');
    } catch (e) {
      App.showToast('⚠️ Error saving settings: ' + e.message, 'error');
    }
  },

  async testTelegramConnection() {
    const token = document.getElementById('setting-tg-token')?.value.trim();
    const chatId = document.getElementById('setting-tg-chat-id')?.value.trim();

    if (!token) {
      App.showToast('ကျေးဇူးပြု၍ Telegram Bot Token အရင်ဖြည့်ပါ', 'warning');
      return;
    }

    const testBtn = document.getElementById('btn-test-tg-settings');
    if (testBtn) testBtn.innerHTML = 'Testing...';

    try {
      const res = await API.testTelegram(token, chatId);
      if (res.success) {
        App.showToast(`✅ Connected to @${res.username}! ${res.warning || ''}`, 'success');
      } else {
        App.showToast(`⚠️ Connection failed: ${res.error}`, 'error');
      }
    } catch (e) {
      App.showToast(`⚠️ Error: ${e.message}`, 'error');
    } finally {
      if (testBtn) testBtn.innerHTML = 'Test Connection';
    }
  }
};
