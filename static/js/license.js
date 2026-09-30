// A.W.N Movie Recap Studio - License & Device Control System
// 1 License Key = 1 Device Binding

const LicenseManager = {
  currentDeviceId: null,
  activeLicenseData: null,
  isUnlocked: false,

  init() {
    this.currentDeviceId = this.getOrCreateDeviceId();
    this.updateDeviceDisplay();
    this.verifyDeviceLicense();
  },

  getOrCreateDeviceId() {
    let id = localStorage.getItem('awn_device_id');
    if (!id || id.length < 10) {
      if (typeof crypto !== 'undefined' && crypto.randomUUID) {
        id = 'DEV-' + crypto.randomUUID().replace(/-/g, '').substring(0, 16).toUpperCase();
      } else {
        id = 'DEV-' + Math.random().toString(36).substring(2, 10).toUpperCase() + Date.now().toString(36).toUpperCase();
      }
      localStorage.setItem('awn_device_id', id);
    }
    return id;
  },

  updateDeviceDisplay() {
    const devDisplays = document.querySelectorAll('.awn-device-id-display');
    devDisplays.forEach(el => {
      el.textContent = this.currentDeviceId;
    });
  },

  async verifyDeviceLicense() {
    const storedKey = localStorage.getItem('awn_license_key');
    const activationModal = document.getElementById('license-activation-modal');

    if (!storedKey) {
      this.lockApp(activationModal);
      return;
    }

    try {
      const res = await API.checkLicense(storedKey, this.currentDeviceId);
      if (res && res.valid) {
        this.activeLicenseData = res;
        this.unlockApp(activationModal);
        this.updateLicenseBadge(res);
      } else {
        console.warn('License verification check failed:', res);
        this.lockApp(activationModal, res.reason || 'License expired or bound to another device');
      }
    } catch (e) {
      console.error('License check error:', e);
      // Offline fallback: if previously activated, grant temporary grace access
      if (localStorage.getItem('awn_license_activated') === 'true') {
        this.unlockApp(activationModal);
      } else {
        this.lockApp(activationModal, 'Could not verify license status');
      }
    }
  },

  lockApp(modal, reason) {
    this.isUnlocked = false;
    if (modal) {
      modal.classList.remove('hidden');
    }
    const errBox = document.getElementById('activation-error-msg');
    if (errBox && reason) {
      errBox.textContent = `သတိပေးချက်: ${reason}`;
      errBox.classList.remove('hidden');
    }
  },

  unlockApp(modal) {
    this.isUnlocked = true;
    if (modal) {
      modal.classList.add('hidden');
    }
    const badge = document.getElementById('nav-license-status');
    if (badge) {
      badge.textContent = 'PRO ACTIVE';
      badge.className = 'px-1.5 py-0.2 rounded text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
    }
  },

  updateLicenseBadge(licData) {
    const planText = document.getElementById('current-plan-display');
    if (planText) {
      planText.textContent = licData.plan || 'Pro License';
    }
    const expText = document.getElementById('license-expiry-display');
    if (expText) {
      if (licData.expires_at) {
        const d = new Date(licData.expires_at);
        expText.textContent = `Expires: ${d.toLocaleDateString()}`;
      } else {
        expText.textContent = 'Lifetime VIP Active';
      }
    }
  },

  async handleActivationSubmit(e) {
    if (e) e.preventDefault();
    const keyInput = document.getElementById('activation-key-input');
    const submitBtn = document.getElementById('btn-activate-license');
    const errBox = document.getElementById('activation-error-msg');

    if (errBox) errBox.classList.add('hidden');

    const key = keyInput ? keyInput.value.trim().toUpperCase() : '';
    if (!key) {
      if (errBox) {
        errBox.textContent = 'ကျေးဇူးပြု၍ လိုင်စင်ကီး ထည့်သွင်းပါ (Please enter license key)';
        errBox.classList.remove('hidden');
      }
      return;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = `<span class="animate-spin inline-block mr-2">⟳</span> စစ်ဆေးနေပါသည်...`;
    }

    try {
      const deviceInfo = `${navigator.userAgent.includes('Mobile') ? 'Mobile' : 'PC'} (${navigator.platform || 'Unknown'})`;
      const res = await API.activateLicense(key, this.currentDeviceId, deviceInfo);

      if (res && res.valid) {
        localStorage.setItem('awn_license_key', key);
        localStorage.setItem('awn_license_activated', 'true');
        this.activeLicenseData = res;
        this.unlockApp(document.getElementById('license-activation-modal'));
        this.updateLicenseBadge(res);

        if (window.App && App.showToast) {
          App.showToast('🎉 စက်အသုံးပြုခွင့် လိုင်စင် အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ!', 'success');
        }
      } else {
        throw new Error(res.error || 'Activation failed');
      }
    } catch (err) {
      if (errBox) {
        errBox.textContent = `❌ ${err.message}`;
        errBox.classList.remove('hidden');
      }
      if (window.App && App.showToast) {
        App.showToast(`❌ ${err.message}`, 'error');
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `<span>🚀</span> Activate Device (အသုံးပြုခွင့် ဖွင့်မည်)`;
      }
    }
  },

  copyDeviceId() {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(this.currentDeviceId);
      if (window.App && App.showToast) {
        App.showToast('📋 Device ID ကို Copy ကူးပြီးပါပြီ!', 'info');
      }
    }
  },

  // --- License Key Generator & Management Admin Page ---
  async loadLicensesList() {
    const tbody = document.getElementById('license-table-body');
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-400 text-xs">လိုင်စင်စာရင်းများ ရယူနေပါသည်...</td></tr>`;

    try {
      const data = await API.getLicenses();
      const list = data.licenses || [];
      if (list.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-400 text-xs">လိုင်စင်ကီး မရှိသေးပါ။ အသစ် ထုတ်ယူပါ (Generate Keys)။</td></tr>`;
        return;
      }

      let rows = '';
      list.forEach(lic => {
        let statusBadge = '';
        if (lic.status === 'active') {
          statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">Active (အသုံးပြုဆဲ)</span>`;
        } else if (lic.status === 'unused') {
          statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] bg-blue-500/20 text-blue-300 border border-blue-500/40">Unused (အသစ်)</span>`;
        } else if (lic.status === 'revoked') {
          statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] bg-rose-500/20 text-rose-300 border border-rose-500/40">Revoked (ပိတ်ထား)</span>`;
        } else {
          statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/40">${lic.status}</span>`;
        }

        const boundDevice = lic.bound_device_id 
          ? `<span class="font-mono text-emerald-400 text-[11px]" title="${lic.bound_device_info || ''}">${lic.bound_device_id.substring(0, 14)}...</span>` 
          : `<span class="text-slate-500 text-[11px]">— No Device —</span>`;

        const exp = lic.expires_at ? new Date(lic.expires_at).toLocaleDateString() : '<span class="text-indigo-300">Lifetime VIP</span>';

        rows += `
          <tr class="border-b border-slate-800/60 hover:bg-slate-800/30 transition text-xs">
            <td class="p-3 font-mono font-bold text-white flex items-center gap-1.5">
              <span>${lic.key}</span>
              <button onclick="LicenseManager.copyText('${lic.key}')" class="text-slate-400 hover:text-white text-[11px]" title="Copy Key">📋</button>
            </td>
            <td class="p-3 text-slate-300">${lic.plan}</td>
            <td class="p-3">${statusBadge}</td>
            <td class="p-3">${boundDevice}</td>
            <td class="p-3 text-slate-400 text-[11px]">${exp}</td>
            <td class="p-3 text-right whitespace-nowrap">
              <div class="flex items-center justify-end gap-1.5">
                ${lic.bound_device_id ? `
                  <button onclick="LicenseManager.resetDevice('${lic.key}')" class="px-2 py-1 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[11px] hover:bg-amber-500/30 transition" title="စက်အသစ်သို့ လွှဲပြောင်းရန် Device ချိတ်ဆက်မှု ဖြုတ်မည်">
                    🔄 Reset Device
                  </button>
                ` : ''}
                <button onclick="LicenseManager.deleteKey('${lic.key}')" class="px-2 py-1 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[11px] hover:bg-rose-500/30 transition" title="ဖျက်မည်">
                  ✕
                </button>
              </div>
            </td>
          </tr>
        `;
      });

      tbody.innerHTML = rows;
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-rose-400 text-xs">Error loading licenses: ${e.message}</td></tr>`;
    }
  },

  async generateKeys() {
    const plan = document.getElementById('gen-plan-select').value;
    const count = parseInt(document.getElementById('gen-count-input').value, 10) || 1;
    const durationDays = document.getElementById('gen-duration-select').value;
    const notes = document.getElementById('gen-notes-input').value.trim();
    const btn = document.getElementById('btn-generate-keys');
    const resultBox = document.getElementById('gen-results-box');

    if (btn) btn.disabled = true;

    try {
      const res = await API.generateLicenses(plan, count, durationDays === 'lifetime' ? null : parseInt(durationDays, 10), notes);
      if (res && res.created) {
        if (resultBox) {
          resultBox.classList.remove('hidden');
          const keysText = res.created.map(k => k.key).join('\n');
          document.getElementById('gen-results-textarea').value = keysText;
        }
        if (window.App && App.showToast) {
          App.showToast(`✨ ${res.created.length} လိုင်စင်ကီး ထုတ်လုပ်ပြီးပါပြီ!`, 'success');
        }
        this.loadLicensesList();
      }
    } catch (e) {
      if (window.App && App.showToast) {
        App.showToast(`Error generating keys: ${e.message}`, 'error');
      }
    } finally {
      if (btn) btn.disabled = false;
    }
  },

  async resetDevice(key) {
    if (!confirm(`Are you sure you want to unbind device from ${key}?\nဤလိုင်စင်ကီးမှ စက်ချိတ်ဆက်မှုကို ဖြုတ်ပါက အခြားစက်အသစ်တွင် ပြန်လည် အသုံးပြုနိုင်ပါမည်။`)) return;
    try {
      await API.resetLicenseDevice(key);
      if (window.App && App.showToast) {
        App.showToast('✅ Device binding reset successfully!', 'success');
      }
      this.loadLicensesList();
    } catch (e) {
      alert('Error: ' + e.message);
    }
  },

  async deleteKey(key) {
    if (!confirm(`Delete license key ${key} permanently?`)) return;
    try {
      await API.deleteLicense(key);
      if (window.App && App.showToast) {
        App.showToast('🗑 License key deleted', 'info');
      }
      this.loadLicensesList();
    } catch (e) {
      alert('Error: ' + e.message);
    }
  },

  copyText(text) {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text);
      if (window.App && App.showToast) {
        App.showToast(`📋 Copied: ${text}`, 'info');
      }
    }
  }
};

window.LicenseManager = LicenseManager;
