import os
import sys
import time
import argparse
from pathlib import Path

# Enable UTF-8 encoding and ANSI virtual terminal processing on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass
os.system('')

import nest_asyncio
nest_asyncio.apply()

# Ensure src/ is on sys.path when running locally without pip install
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rich.console import Console
from rich.panel import Panel
from rich import box

from whatsapp import WhatsAppClient
from cli.ui.terminal import run_main_menu

console = Console(force_terminal=True, legacy_windows=False)


def on_qr_prompt():
    console.print(Panel.fit(
        "[bold yellow]QR CODE DETECTED - FIRST TIME LOGIN REQUIRED[/bold yellow]\n\n"
        "1. Look at the browser window showing the QR code.\n"
        "2. Open WhatsApp on your phone:\n"
        "   • [cyan]Android:[/] Tap [bold]⋮[/] (top-right) -> [bold]Linked Devices[/] -> [bold]Link a Device[/]\n"
        "   • [cyan]iPhone:[/]  Go to [bold]Settings[/] -> [bold]Linked Devices[/] -> [bold]Link a Device[/]\n"
        "3. Point your camera at the screen to scan the QR code.",
        border_style="yellow",
        title="Scan QR Code",
        box=box.ROUNDED
    ))
    console.print("[bold green]Waiting for you to scan QR code from your phone...[/]")


def on_login_ok():
    console.print("[bold green]✔ Active session found! Reconnected automatically.[/]\n")


def main():
    parser = argparse.ArgumentParser(description="Beautiful Stealth WhatsApp CLI")
    parser.add_argument("--phone", "-p", help="Recipient phone number with country code (non-interactive mode)")
    parser.add_argument("--message", "-m", help="Message text to send (non-interactive mode)")
    parser.add_argument("--browser", choices=["chrome", "msedge", "chromium"], default="chrome",
                        help="Browser channel (default: chrome)")
    parser.add_argument("--dev", action="store_true",
                        help="Show browser window on screen for debugging and inspection")
    args = parser.parse_args()

    session_dir = ROOT_DIR / "whatsapp_session"

    if args.dev:
        console.print(f"[bold yellow][DEV MODE][/] Showing {args.browser.upper()} browser on screen...")
    else:
        console.print(f"[bold dim][*] Starting {args.browser.upper()} in background (hidden window). Use --dev to show on screen.[/]")

    client = WhatsAppClient(
        session_dir=session_dir,
        browser=args.browser,
        dev_mode=args.dev,
        on_qr_needed=on_qr_prompt,
        on_login_success=on_login_ok
    )

    with console.status("[bold cyan]Connecting to WhatsApp Web...", spinner="dots"):
        connected = client.connect()

    if not connected:
        console.print("[bold red]Failed to connect or log in to WhatsApp Web.[/]")
        client.close()
        return

    # Direct one-shot CLI mode if arguments provided
    if args.phone and args.message:
        if client.open_chat_by_number(args.phone):
            client.send_message(args.message)
            time.sleep(2)
            console.print(f"[bold green]✔ Sent to {args.phone}:[/] {args.message}")
        else:
            console.print(f"[bold red]Could not send message to {args.phone}.[/]")
    else:
        # Full interactive terminal menu
        run_main_menu(client)

    client.close()
    console.print("[bold green]✔ Session closed safely. Goodbye![/]")


if __name__ == "__main__":
    main()
