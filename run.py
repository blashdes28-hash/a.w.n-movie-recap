import os
import sys
import socket

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import uvicorn

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    default_port = 7860 if "SPACE_ID" in os.environ else 8000
    port = int(os.environ.get("PORT", default_port))
    host = "0.0.0.0"
    local_ip = get_local_ip()
    
    print("=" * 60)
    print("ACT RECAP - Burmese Movie Recap Web Studio")
    print(f"Computer access : http://localhost:{port} or http://127.0.0.1:{port}")
    print(f"Phone access    : http://{local_ip}:{port}")
    print("=" * 60)
    
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
