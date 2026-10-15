# WhatsApp Stealth Simulator & Interactive CLI

A modern, stealth WhatsApp automation simulator and interactive terminal client built on Playwright and Prompt Toolkit.

## Architecture

This project is separated into a **standalone, reusable Python SDK** and a **CLI application**:

```
quick-borg/
├── src/
│   └── whatsapp/                # Reusable Python Library / SDK
│       ├── __init__.py          # Public exports (WhatsAppClient, ChatMessage, ChatSummary)
│       ├── client.py            # High-level client API
│       ├── models.py            # Data classes (ChatMessage, ChatSummary)
│       └── core/                # Core automation engines
│           ├── browser.py       # Playwright lifecycle, CDP, and stealth positioning
│           ├── stealth.py       # Anti-detect scripts & human typing simulation
│           └── popups.py        # Automatic modal & notification banner dismissal
├── cli/                         # CLI Terminal Application
│   ├── main.py                  # CLI entrypoint & argument parsing
│   └── ui/                      # Terminal UI
│       ├── formatters.py        # Clean message formatting (`name (time) >> message`)
│       └── terminal.py          # Interactive menus and live chat loop
├── run.py                       # Root launcher script
├── pyproject.toml               # Standard packaging (enables `pip install .`)
└── requirements.txt             # Dependencies
```

---

## 1. Running the Interactive CLI

### Standard Run (Hidden Window):
Runs the browser positioned off-screen with full codecs and zero bot flags:
```bash
python run.py
```

### Dev Mode (Visible Browser):
Opens the browser on-screen for debugging and observing interactions:
```bash
python run.py --dev
```

### Single-Message Mode:
Send a message directly via command-line arguments:
```bash
python run.py --phone +1234567890 --message "Hello from Python!"
```

---

## 2. Using as a Python Library in Other Applications

You can install this project as a library:
```bash
pip install -e .
```

Then import and use `WhatsAppClient` anywhere in your code:

```python
from whatsapp import WhatsAppClient, ChatMessage

# Initialize client
client = WhatsAppClient(dev_mode=False)
client.connect()

# 1. Listen for real-time incoming messages
def on_message_received(msg: ChatMessage):
    print(f"New message from {msg.sender}: {msg.text}")

client.on_message(on_message_received)

# 2. Open a chat and send a message
client.open_chat_by_number("+1234567890")
client.send_message("Automated alert from my custom Python service!")

# 3. Read message history
messages = client.get_messages()
for m in messages:
    print(f"{m.sender} ({m.time}): {m.text}")

# 4. Clean shutdown
client.close()
```

---

## Features
- **Anti-Detect / Stealth**: Strips `navigator.webdriver`, mimics real Chrome/Edge profiles, full audio/video codecs.
- **Off-Screen Execution**: Runs headed without cluttering the screen or triggering headless bot detection.
- **Real-Time Streaming**: Uses DOM mutation observers to push incoming replies instantly.
- **Zero Page Reloads**: Navigates chats via sidebar clicks and client-side SPA routing.
- **Popup Auto-Dismisser**: Automatically closes "Get WhatsApp for Windows" or notification banners.
