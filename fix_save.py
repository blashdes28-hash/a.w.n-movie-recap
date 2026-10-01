with open('static/js/tools.js', 'r', encoding='utf-8') as f:
    js = f.read()

js = js.replace("await API.saveSettings({ gemini_api_key: key });", "")

with open('static/js/tools.js', 'w', encoding='utf-8') as f:
    f.write(js)

import json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

if config.get("gemini_api_key") and "AQ." in config.get("gemini_api_key"):
    config["gemini_api_key"] = ""
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    print("Cleared bad key from config.json")
