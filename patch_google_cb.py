with open('static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

html = html.replace("LicenseManager.refreshDisplayedDeviceId();",
                    "LicenseManager.refreshDisplayedDeviceId();\n      const inputSection = document.getElementById('modal-license-input-section');\n      if (inputSection) inputSection.style.display = 'flex';")

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
