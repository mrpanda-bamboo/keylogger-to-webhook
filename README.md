# keylogger-to-webhook

A Windows 11-compatible keylogger designed to exfiltrate system metadata and real-time keyboard data via Discord webhooks.

## Purpose

This keylogger captures real-time keyboard input and system information, sending them through Discord webhooks. It is designed to operate discreetly in the background while collecting comprehensive system metadata and keystroke logs.

## Key Features

- **Real-time Keystroke Logging**: Captures all keyboard input with timestamps
- **System Information Collection**: Gathers detailed system metadata (hostname, IP addresses, OS version, uptime)
- **Clipboard Monitoring**: Tracks clipboard content changes
- **Discord Webhook Integration**: Sends logs via Discord webhooks for remote exfiltration
- **Single Instance Protection**: Prevents multiple instances from running simultaneously
- **Smart Buffering**: Batches keystrokes and sends them at regular intervals or when buffer exceeds size limit
- **Alive Status Pings**: Periodically confirms the keylogger is still running
- **Cross-platform Support**: Supports both Windows and Unix-like systems

## Core Functions

### System Information & Identification

- **`prevent_double_execution()`**: Ensures only one instance runs at a time using file locks
- **`get_active_mac()`**: Retrieves the active network interface MAC address
- **`get_public_ip()`**: Fetches the public IP address from ipify.org
- **`get_local_ip()`**: Determines the active local network IP address
- **`get_system_info()`**: Collects comprehensive system metadata (hostname, user, IPs, OS version, uptime)

### Keystroke Processing

- **`beautify_key(key)`**: Converts raw key codes into human-readable format (e.g., "shift", "enter")
- **`convert_ctrl_char(char)`**: Converts control characters to readable format
- **`on_press(key)`**: Event handler for key press events; logs keystrokes with modifiers (Ctrl, Shift, Alt)
- **`on_release(key)`**: Event handler for key release events; updates held modifier keys state

### Data Transmission

- **`sender_thread()`**: Background thread that sends queued messages via Discord webhook
- **`send_buffer()`**: Periodically flushes accumulated keystrokes to the webhook (every minute)
- **`check_instant_flush()`**: Immediately sends buffer if it exceeds 1000 characters
- **`periodic_systeminfo()`**: Sends system information every 30 minutes (1800 seconds)
- **`periodic_alive_ping()`**: Sends alive status confirmation every 60 seconds

### Monitoring

- **`monitor_clipboard()`**: Continuously monitors clipboard contents and sends changes via webhook

## Configuration

Before running, set your Discord webhook URL:

```python
WEBHOOK_URL = "YOUR_WEBHOOK_URL_HERE"
```

## Requirements

- Python 3.x
- `pynput` - Keyboard listener library
- `requests` - HTTP requests library
- `psutil` - System and process utilities
- `pyperclip` - Clipboard access

## Data Sent to Webhook

The keylogger sends the following information:

1. **System Information**: Hostname, username, local/public IP, OS information, system uptime
2. **Keystroke Logs**: All pressed keys with timestamps and modifier keys
3. **Clipboard Changes**: Text copied/cut to clipboard
4. **Alive Status**: Periodic confirmation that the keylogger is running

## How It Works

1. Prevents multiple instances from running
2. Collects initial system information and sends it to webhook
3. Starts listening to keyboard events
4. Buffers keystrokes in memory
5. Sends accumulated logs every minute or when buffer reaches size limit
6. Monitors clipboard for changes
7. Periodically sends system info and alive status pings
8. Continues indefinitely in the background
