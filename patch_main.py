import uuid, shutil, os
from pathlib import Path

with open('app/main.py', 'r', encoding='utf-8') as f:
    original = f.read()

with open('async_endpoints.py', 'r', encoding='utf-8') as f:
    new_endpoints = f.read()

export_idx = original.find('@app.post("/api/transcribe/export")')
if export_idx != -1:
    updated = original[:export_idx] + new_endpoints + '\n' + original[export_idx:]
    with open('app/main.py', 'w', encoding='utf-8') as f:
        f.write(updated)
    print('Inserted endpoints')
else:
    print('Could not find insertion point')
