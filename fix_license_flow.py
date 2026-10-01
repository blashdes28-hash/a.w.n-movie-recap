with open('static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

html = html.replace('<form onsubmit="LicenseManager.handleActivationSubmit(event)" class="flex flex-col gap-3 text-left">',
                    '<form id="modal-license-input-section" onsubmit="LicenseManager.handleActivationSubmit(event)" class="flex flex-col gap-3 text-left">')

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

with open('static/js/license.js', 'r', encoding='utf-8') as f:
    js = f.read()

patch_code = """
  showLicenseModal() {
    const modal = document.getElementById('modal-license-gate');
    if (modal) modal.classList.remove('hidden');
    this.refreshDisplayedDeviceId();
    
    // Hide license input until Google Sign-in is done
    const inputSection = document.getElementById('modal-license-input-section');
    if (inputSection) {
      const email = localStorage.getItem('awn_google_email');
      if (!email) {
        inputSection.style.display = 'none';
      } else {
        inputSection.style.display = 'flex';
      }
    }
  },
"""

js = js.replace("  showLicenseModal() {\n    const modal = document.getElementById('modal-license-gate');\n    if (modal) modal.classList.remove('hidden');\n    this.refreshDisplayedDeviceId();\n  },", patch_code)

with open('static/js/license.js', 'w', encoding='utf-8') as f:
    f.write(js)
