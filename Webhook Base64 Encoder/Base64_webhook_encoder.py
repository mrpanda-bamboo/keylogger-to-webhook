import base64
import os
import sys
import msvcrt

webhook = input("Enter your Discord webhook URL: ").strip()
if not webhook.startswith("http"):
    print("❌ Invalid webhook URL!")
    print("Press any key to exit...")
    msvcrt.getch()
    sys.exit(1)

encoded = base64.b64encode(webhook.encode()).decode()

base_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)
full_path = os.path.join(base_dir, "cache.db")

try:
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(encoded)
    print(f"✅ Webhook saved to: {full_path}")
except Exception as e:
    print(f"❌ Failed to save: {e}")

print("Done. Press any key to close...")
msvcrt.getch()
