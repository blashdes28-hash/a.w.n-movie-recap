import subprocess
import time
import re
import sys
import os

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def main():
    print("=" * 65)
    print("  A.W.N MOVIE RECAP STUDIO - PUBLIC ONLINE LAUNCHER")
    print("=" * 65)
    
    # 1. Start server process
    print("[1/2] Starting application server...")
    server_process = subprocess.Popen([sys.executable, "run.py"])
    time.sleep(3)
    
    # 2. Start cloudflared tunnel
    print("[2/2] Launching Cloudflare Secure HTTPS Tunnel...")
    cloudflared_bin = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloudflared.exe")
    if not os.path.exists(cloudflared_bin):
        print(f"Error: {cloudflared_bin} not found! Please ensure cloudflared.exe is present.")
        return

    tunnel_process = subprocess.Popen(
        [cloudflared_bin, "tunnel", "--url", "http://127.0.0.1:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    public_url = None
    for line in tunnel_process.stdout:
        match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
        if match:
            public_url = match.group(0)
            try:
                with open("public_url.txt", "w", encoding="utf-8") as pf:
                    pf.write(public_url.strip())
            except Exception:
                pass
            print("\n" + "=" * 65)
            print("🎉 YOUR WEB STUDIO IS NOW LIVE & PUBLIC ONLINE!")
            print("=" * 65)
            print(f"🌐 Public Web URL   : {public_url}")
            print(f"🔑 Secret Admin URL : {public_url}/admin")
            print("=" * 65)
            print("📱 You can open this link from ANY phone (4G/5G) or PC in the world!")
            print("💡 Keep this window open while using the app.")
            print("=" * 65 + "\n")
            sys.stdout.flush()
            break

    try:
        for line in tunnel_process.stdout:
            pass
        tunnel_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down public server...")
        try:
            server_process.terminate()
            tunnel_process.terminate()
        except Exception:
            pass

if __name__ == "__main__":
    main()
