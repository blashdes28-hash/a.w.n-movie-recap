with open('app/license_manager.py', 'r', encoding='utf-8') as f:
    original = f.read()

new_func = """
def find_license_by_device(device_id: str) -> dict:
    device_id = device_id.strip()
    if not device_id: return {"valid": False, "reason": "No device ID"}
    
    db = load_licenses_db()
    licenses = db.get("licenses", {})
    
    for key, lic in licenses.items():
        if lic.get("bound_device_id") == device_id:
            if lic.get("status") == "revoked":
                continue
            
            expires_at_str = lic.get("expires_at")
            if expires_at_str:
                try:
                    from datetime import datetime, timezone
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if datetime.now(timezone.utc) > expires_at:
                        continue # Expired
                except Exception:
                    pass
                    
            # Valid active license found!
            return {"valid": True, "license_key": key, "plan": lic.get("plan")}
            
    return {"valid": False, "reason": "No active license found for this device"}
"""

if "def find_license_by_device" not in original:
    original += "\n" + new_func + "\n"
    with open('app/license_manager.py', 'w', encoding='utf-8') as f:
        f.write(original)
    print("Added find_license_by_device")
