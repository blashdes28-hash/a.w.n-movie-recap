/**
 * AuthManager - Google Sign-In + Gemini API Key management
 * Saves key per Google account email in localStorage
 */

// Called by Google Sign-In SDK after user authenticates
function handleGoogleCredentialResponse(response) {
  try {
    // Decode JWT to get user info
    const payload = JSON.parse(atob(response.credential.split('.')[1]));
    const email = payload.email || '';
    const name = payload.name || 'User';
    const picture = payload.picture || '';

    // Save session
    localStorage.setItem('awn_google_email', email);
    localStorage.setItem('awn_google_name', name);
    localStorage.setItem('awn_google_picture', picture);
    localStorage.setItem('awn_google_signed_in', '1');

    AuthManager.onSignedIn(email, name, picture);
  } catch (e) {
    console.error('Google sign-in decode error:', e);
  }
}

const AuthManager = {
  currentEmail: null,

  init() {
    const signedIn = localStorage.getItem('awn_google_signed_in');
    const email = localStorage.getItem('awn_google_email');
    const name = localStorage.getItem('awn_google_name');
    const picture = localStorage.getItem('awn_google_picture');

    if (signedIn && email) {
      this.currentEmail = email;
      // Check if they already have a key saved
      const savedKey = this.getSavedKey(email);
      if (savedKey) {
        // All good - auto enter the app
        this.applyKeyAndEnter(savedKey, email, name);
        return true; // skip showing modal
      } else {
        // Signed in but no key yet - show step 2
        this.onSignedIn(email, name, picture, /*skipStep1=*/true);
        return false;
      }
    }
    return false; // show modal with step 1
  },

  onSignedIn(email, name, picture, skipStep1 = false) {
    this.currentEmail = email;

    // Update UI
    document.getElementById('auth-user-name').textContent = name || email;
    document.getElementById('auth-user-email').textContent = email;

    const avatarEl = document.getElementById('auth-user-avatar');
    if (picture) {
      avatarEl.innerHTML = `<img src="${picture}" class="w-full h-full rounded-full object-cover" onerror="this.parentElement.textContent='${(name||'U')[0]}'">`;
    } else {
      avatarEl.textContent = (name || 'U')[0].toUpperCase();
    }

    // Check if they already have a key
    const savedKey = this.getSavedKey(email);
    if (savedKey) {
      document.getElementById('auth-gemini-key-input').value = savedKey;
    }

    // Switch to step 2
    document.getElementById('auth-step-signin').classList.add('hidden');
    document.getElementById('auth-step-apikey').classList.remove('hidden');

    // Show modal if not already visible
    const modal = document.getElementById('license-activation-modal');
    if (modal.classList.contains('hidden')) {
      modal.classList.remove('hidden');
    }
  },

  getSavedKey(email) {
    if (!email) return null;
    return localStorage.getItem(`awn_gemini_key_${email}`) || null;
  },

  saveKeyForEmail(email, key) {
    if (!email || !key) return;
    localStorage.setItem(`awn_gemini_key_${email}`, key);
    // Also save as global for api.js to pick up
    localStorage.setItem('awn_gemini_api_key', key);
  },

  async saveKeyAndEnter() {
    const keyInput = document.getElementById('auth-gemini-key-input');
    const errorEl = document.getElementById('auth-key-error');
    const key = keyInput.value.trim();

    if (!key) {
      errorEl.textContent = 'API Key ထည့်ပေးပါ (Please enter your Gemini API Key)';
      errorEl.classList.remove('hidden');
      return;
    }

    errorEl.classList.add('hidden');

    // Test the key quickly
    const btn = event.currentTarget || document.querySelector('#auth-step-apikey button');
    const origText = btn ? btn.innerHTML : '';
    if (btn) btn.innerHTML = '<span class="animate-spin">⏳</span> Testing key...';

    try {
      const res = await fetch('/api/gemini/test-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gemini_api_key: key })
      });
      const data = await res.json();

      if (!res.ok || data.status !== 'ok') {
        throw new Error(data.detail || data.error || 'Key အလုပ်မလုပ်ပါ');
      }

      // Save and enter
      const email = this.currentEmail || localStorage.getItem('awn_google_email') || 'guest';
      this.saveKeyForEmail(email, key);
      this.applyKeyAndEnter(key, email);

    } catch (err) {
      if (btn) btn.innerHTML = origText;
      errorEl.textContent = `❌ ${err.message}`;
      errorEl.classList.remove('hidden');
    }
  },

  skipKeySetup() {
    const email = this.currentEmail || localStorage.getItem('awn_google_email') || 'guest';
    this.applyKeyAndEnter(null, email);
  },

  applyKeyAndEnter(key, email, name) {
    if (key) {
      localStorage.setItem('awn_gemini_api_key', key);
      // Push into existing GeminiKey UI if available
      const keyInputs = document.querySelectorAll('#gemini-api-key-input, #gemini-key-input');
      keyInputs.forEach(el => { if (el) el.value = key; });
    }

    // Update nav display
    if (name || email) {
      const displayName = name || email.split('@')[0];
      const navStatus = document.getElementById('nav-license-status');
      if (navStatus) navStatus.textContent = displayName.substring(0, 10);
    }

    // Hide modal
    document.getElementById('license-activation-modal').classList.add('hidden');

    // Mark as activated
    localStorage.setItem('awn_activated', '1');
    localStorage.setItem('awn_google_signed_in', '1');
  },

  signOut() {
    localStorage.removeItem('awn_google_signed_in');
    localStorage.removeItem('awn_google_email');
    localStorage.removeItem('awn_google_name');
    localStorage.removeItem('awn_google_picture');
    localStorage.removeItem('awn_activated');
    // Reload to show sign-in screen again
    location.reload();
  }
};
