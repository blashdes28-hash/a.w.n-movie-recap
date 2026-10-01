with open('app/main.py', 'r', encoding='utf-8') as f:
    original = f.read()

new_endpoint = """
class DeviceCheckRequest(BaseModel):
    device_id: str

@app.post("/api/license/check-by-device")
def check_by_device_endpoint(req: DeviceCheckRequest):
    from app.license_manager import find_license_by_device
    res = find_license_by_device(req.device_id)
    return res
"""

original = original.replace("class LicenseActivateRequest", new_endpoint + "\nclass LicenseActivateRequest")

with open('app/main.py', 'w', encoding='utf-8') as f:
    f.write(original)
print("Patched main.py")
