import re

with open('static/js/license.js', 'r', encoding='utf-8') as f:
    js = f.read()

new_logic = """
  async verifyWithGoogleAuth() {
    const activationModal = document.getElementById('modal-license-gate') || document.getElementById('license-activation-modal');
    if (!activationModal) return;

    // 1. If Google signed in, check if backend has a license for this device (e.g. after clearing cache)
    let email = localStorage.getItem('awn_google_email');
    if (email) {
      window.currentUserEmail = email;
      try {
        const res = await fetch('/api/license/check-by-device', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ device_id: this.currentDeviceId })
        });
        if (res.ok) {
          const data = await res.json();
          if (data.valid && data.license_key) {
            localStorage.setItem('awn_license_key', data.license_key);
            localStorage.setItem('awn_license_activated', 'true');
            // Assume lifetime if no expiry returned here, or we let verifyDeviceLicense check it
          }
        }
      } catch (e) {
        console.warn("Could not check device license from backend", e);
      }
    }

    // 2. Check local license key
    const storedKey = localStorage.getItem('awn_license_key');
    const licenseExpiry = localStorage.getItem('awn_license_expiry');
    const isActivated = localStorage.getItem('awn_license_activated') === 'true';

    if (isActivated && storedKey) {
      if (!licenseExpiry) {
        this.isUnlocked = true;
        activationModal.classList.add('hidden');
        return;
      }
      const expDate = new Date(licenseExpiry);
      if (expDate > new Date()) {
        this.isUnlocked = true;
        activationModal.classList.add('hidden');
        return;
      }
      localStorage.removeItem('awn_license_activated');
    }

    // 3. No valid license -> Show Modal
    this.showLicenseModal();
  },

  showLicenseModal() {
    const modal = document.getElementById('modal-license-gate') || document.getElementById('license-activation-modal');
    if (modal) modal.classList.remove('hidden');
    this.refreshDisplayedDeviceId();
    
    const googleSection = document.getElementById('modal-google-signin');
    const inputSection = document.getElementById('modal-license-input-section');
    const signedInNote = document.getElementById('modal-signed-in-note');
    
    const email = localStorage.getItem('awn_google_email');
    const name = localStorage.getItem('awn_google_name');

    if (email) {
      // User IS signed into Google. Hide Google button, Show License Input.
      if (googleSection) googleSection.style.display = 'none';
      if (inputSection) inputSection.style.display = 'flex';
      if (signedInNote) {
        signedInNote.textContent = `✅ Signed in as ${name || email.split('@')[0]} (${email})`;
        signedInNote.classList.remove('hidden');
      }
    } else {
      // User IS NOT signed into Google. Show Google button, Hide License Input.
      if (googleSection) googleSection.style.display = 'flex';
      if (inputSection) inputSection.style.display = 'none';
      if (signedInNote) signedInNote.classList.add('hidden');
    }
  },
"""

js = re.sub(r"verifyWithGoogleAuth\(\)\s*\{[\s\S]*?async verifyDeviceLicense\(\)\s*\{", new_logic + "\n  async verifyDeviceLicense() {", js)

with open('static/js/license.js', 'w', encoding='utf-8') as f:
    f.write(js)
