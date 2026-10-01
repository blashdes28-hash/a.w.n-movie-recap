import json
import secrets
import string
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LICENSE_FILE = DATA_DIR / "licenses.json"

def _generate_random_key(prefix: str = "AWN") -> str:
    """Generates a secure, human-readable license key in AWN-XXXX-XXXX-XXXX format."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789" # Excludes ambiguous 0/O, 1/I
    part1 = "".join(secrets.choice(alphabet) for _ in range(4))
    part2 = "".join(secrets.choice(alphabet) for _ in range(4))
    part3 = "".join(secrets.choice(alphabet) for _ in range(4))
    return f"{prefix}-{part1}-{part2}-{part3}"

def load_licenses_db() -> Dict[str, Any]:
    """Loads licenses database from JSON file or creates default with master key."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not LICENSE_FILE.exists():
        default_db = {
            "version": "1.0",
            "licenses": {
                "AWN-VIP-PRO-2026": {
                    "key": "AWN-VIP-PRO-2026",
                    "plan": "Lifetime VIP (Admin Master)",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "expires_at": None,
                    "status": "unused",
                    "bound_device_id": None,
                    "bound_device_info": None,
                    "activated_at": None,
                    "last_seen_at": None,
                    "notes": "Admin Master License"
                }
            }
        }
        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump(default_db, f, indent=2, ensure_ascii=False)
        return default_db

    try:
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"version": "1.0", "licenses": {}}

def save_licenses_db(db: Dict[str, Any]) -> None:
    """Saves licenses database to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(LICENSE_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

def verify_and_activate_license(
    license_key: str,
    device_id: str,
    device_info: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validates license key and enforces strict 1 License Key = 1 Device rule.
    """
    key = license_key.strip().upper()
    if not key:
        return {"valid": False, "error": "License key is required (လိုင်စင်ကီး ထည့်သွင်းပါ)"}

    if not device_id or not device_id.strip():
        return {"valid": False, "error": "Device identification failed (စက် ID မတွေ့ရှိပါ)"}

    device_id = device_id.strip()
    db = load_licenses_db()
    licenses = db.setdefault("licenses", {})

    if key not in licenses:
        return {"valid": False, "error": "Invalid License Key! (လိုင်စင်ကီး မှားယွင်းနေပါသည်)"}

    lic = licenses[key]

    # Check revocation
    if lic.get("status") == "revoked":
        return {"valid": False, "error": "This license key has been revoked. (ဤလိုင်စင်ကီးကို ပိတ်သိမ်းထားပါသည်)"}

    bound_id = lic.get("bound_device_id")
    dur_days = lic.get("duration_days")
    expires_at_str = lic.get("expires_at")

    # Check expiration (if already activated, or if fixed hard expiry without duration_days)
    if expires_at_str and (bound_id or not dur_days):
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.now(timezone.utc) > expires_at:
                lic["status"] = "expired"
                save_licenses_db(db)
                return {"valid": False, "error": "This license has expired. (လိုင်စင်သက်တမ်း ကုန်ဆုံးသွားပါပြီ)"}
        except Exception:
            pass

    now_iso = datetime.now(timezone.utc).isoformat()

    # Enforce strict 1 device per license key rule - One Time Activation
    if bound_id and bound_id != device_id:
        return {
            "valid": False,
            "error": "This license key has already been activated and consumed on another device! It cannot be used twice. (ဤလိုင်စင်ကီးကို အခြားစက်တစ်ခုတွင် အသုံးပြုထားပြီးဖြစ်၍ ထပ်မံသုံး၍မရပါ - 1 Key = 1 Device Only)"
        }

    # First time activation on this device
    if not bound_id:
        lic["bound_device_id"] = device_id
        lic["bound_device_info"] = device_info or "Unknown Device"
        lic["activated_at"] = now_iso
        lic["status"] = "active"
        # If license has duration_days (e.g. 1 day access), the countdown starts upon first activation
        dur_days = lic.get("duration_days")
        if dur_days and dur_days > 0:
            lic["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=dur_days)).isoformat()

    lic["last_seen_at"] = now_iso
    save_licenses_db(db)

    return {
        "valid": True,
        "message": "Device activated successfully! (စက်အသုံးပြုခွင့် အောင်မြင်ပါသည်)",
        "license_key": key,
        "plan": lic.get("plan", "Standard"),
        "expires_at": lic.get("expires_at"),
        "bound_device_id": device_id,
        "activated_at": lic.get("activated_at")
    }

def check_device_license(license_key: str, device_id: str) -> Dict[str, Any]:
    """Checks if a device currently has a valid active license."""
    key = license_key.strip().upper()
    device_id = device_id.strip() if device_id else ""
    db = load_licenses_db()
    licenses = db.get("licenses", {})

    if key not in licenses:
        return {"valid": False, "reason": "License not found"}

    lic = licenses[key]
    if lic.get("status") == "revoked":
        return {"valid": False, "reason": "License revoked"}

    expires_at_str = lic.get("expires_at")
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.now(timezone.utc) > expires_at:
                return {"valid": False, "reason": "License expired"}
        except Exception:
            pass

    if lic.get("bound_device_id") != device_id:
        return {"valid": False, "reason": "Device mismatch"}

    # Update last seen
    lic["last_seen_at"] = datetime.now(timezone.utc).isoformat()
    save_licenses_db(db)

    return {
        "valid": True,
        "license_key": key,
        "plan": lic.get("plan"),
        "expires_at": lic.get("expires_at")
    }

def generate_new_licenses(
    plan: str = "Lifetime VIP",
    count: int = 1,
    expires_days: Optional[int] = None,
    notes: str = ""
) -> List[Dict[str, Any]]:
    """Generates new license keys."""
    db = load_licenses_db()
    licenses = db.setdefault("licenses", {})
    created_list = []

    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(days=expires_days)).isoformat() if expires_days and expires_days > 0 else None

    for _ in range(max(1, min(count, 50))):
        key = _generate_random_key()
        while key in licenses:
            key = _generate_random_key()

        entry = {
            "key": key,
            "plan": plan,
            "created_at": now.isoformat(),
            "expires_at": expires_at,
            "duration_days": expires_days if expires_days and expires_days > 0 else None,
            "status": "unused",
            "bound_device_id": None,
            "bound_device_info": None,
            "activated_at": None,
            "last_seen_at": None,
            "notes": notes
        }
        licenses[key] = entry
        created_list.append(entry)

    save_licenses_db(db)
    return created_list

def list_all_licenses() -> List[Dict[str, Any]]:
    """Returns list of all licenses sorted by creation date."""
    db = load_licenses_db()
    licenses = list(db.get("licenses", {}).values())
    licenses.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return licenses

def reset_device_binding(license_key: str) -> bool:
    """Unbinds device from a license key so it can be re-used on a new device."""
    key = license_key.strip().upper()
    db = load_licenses_db()
    licenses = db.get("licenses", {})
    if key in licenses:
        licenses[key]["bound_device_id"] = None
        licenses[key]["bound_device_info"] = None
        licenses[key]["status"] = "unused"
        save_licenses_db(db)
        return True
    return False

def revoke_license_key(license_key: str) -> bool:
    """Revokes a license key."""
    key = license_key.strip().upper()
    db = load_licenses_db()
    licenses = db.get("licenses", {})
    if key in licenses:
        licenses[key]["status"] = "revoked"
        save_licenses_db(db)
        return True
    return False

def delete_license_key(license_key: str) -> bool:
    """Permanently deletes a license key."""
    key = license_key.strip().upper()
    db = load_licenses_db()
    licenses = db.get("licenses", {})
    if key in licenses:
        del licenses[key]
        save_licenses_db(db)
        return True
    return False

# --- Admin Authentication & Access Control ---

ADMIN_CONFIG_FILE = DATA_DIR / "admin_config.json"

def get_admin_password() -> str:
    """Returns the secret admin password."""
    if ADMIN_CONFIG_FILE.exists():
        try:
            with open(ADMIN_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("admin_password", "awnadmin2026")
        except Exception:
            pass
    return "awnadmin2026"

def set_admin_password(new_pass: str) -> bool:
    """Sets a new secret admin password."""
    p = new_pass.strip()
    if not p:
        return False
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(ADMIN_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"admin_password": p}, f, indent=2)
    return True

def verify_admin_password(password: str) -> bool:
    """Safely verifies the given admin password."""
    if not password:
        return False
    expected = get_admin_password()
    return secrets.compare_digest(password.strip(), expected)


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

