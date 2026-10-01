with open('static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

html = html.replace('id="g_id_onload"', 'class="g_id_onload"')

body_tag = '<body class="bg-[#07090e] text-slate-100 flex flex-col h-screen overflow-hidden antialiased select-none">'
new_onload = body_tag + '\n  <div id="g_id_onload" data-client_id="14597319158-vg961519fou8195u1g3qoea9bh40nfkv.apps.googleusercontent.com" data-context="signin" data-ux_mode="popup" data-callback="handleGoogleCredentialResponse" data-auto_prompt="false"></div>\n'

if body_tag in html:
    html = html.replace(body_tag, new_onload)
else:
    print("body tag not found exactly")

with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
