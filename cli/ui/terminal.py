import time
from prompt_toolkit import prompt
from prompt_toolkit.patch_stdout import patch_stdout
import questionary
from rich.console import Console
from rich.panel import Panel
from rich import box

from whatsapp import WhatsAppClient, ChatMessage
from .formatters import format_message_line

console = Console(force_terminal=True, legacy_windows=False)


def handle_incoming_cli_message(msg: ChatMessage):
    """Prints incoming messages cleanly above active prompt."""
    line = format_message_line(msg.sender, msg.text, msg.time)
    print(f"\n{line}", flush=True)


def chat_session_loop(client: WhatsAppClient, contact_display_name: str):
    """
    Interactive sub-shell for chatting inside a contact:
      name (time) >> message here
      You (time) >> <blinking cursor>
    """
    print(f"\n===================================================================", flush=True)
    print(f"  Chatting with: {contact_display_name}  (type :back to exit)", flush=True)
    print(f"===================================================================\n", flush=True)

    # Print initial message history
    history = client.get_messages()
    if history:
        for m in history:
            print(format_message_line(m.sender, m.text, m.time), flush=True)
        print("", flush=True)

    with patch_stdout():
        while True:
            try:
                now_time = time.strftime("%I:%M %p").lstrip("0")
                user_input = prompt(f"You ({now_time}) >> ")
            except (KeyboardInterrupt, EOFError):
                break

            if not user_input or user_input.strip().lower() in [":exit", ":back", "/exit", "/back", "exit", "back"]:
                print("\nExiting chat session...\n", flush=True)
                time.sleep(0.5)
                break

            clean_input = user_input.strip()
            if not clean_input:
                continue

            client.send_message(clean_input)

    client.close_active_chat()


def run_main_menu(client: WhatsAppClient):
    """Renders the main contact list selection menu using questionary."""
    client.on_message(handle_incoming_cli_message)

    while True:
        console.clear()
        console.print(Panel.fit(
            "[bold green]WHATSAPP TERMINAL[/bold green] [dim]• Stealth Mode Active[/dim]\n"
            "[cyan]Session:[/] Connected   [cyan]Engine:[/] Anti-Detect Chromium / Edge",
            box=box.ROUNDED,
            border_style="green"
        ))

        recent_chats = client.get_recent_chats()

        choices = []
        if recent_chats:
            choices.append(questionary.Separator("── Recent Conversations ──"))
            for chat in recent_chats:
                preview = f" - [dim]{chat.last_message}[/dim]" if chat.last_message else ""
                time_info = f" ({chat.time})" if chat.time else ""
                label = f"💬 {chat.name}{time_info}{preview}"
                choices.append(questionary.Choice(title=label, value=("open_chat", chat.name)))

        choices.append(questionary.Separator("── Actions ──"))
        choices.append(questionary.Choice(title="➕ Start new chat with a phone number", value=("new_number", None)))
        choices.append(questionary.Choice(title="🔄 Refresh chat list", value=("refresh", None)))
        choices.append(questionary.Choice(title="🚪 Exit", value=("exit", None)))

        try:
            selection = questionary.select(
                "Select a contact or action:",
                choices=choices,
                use_indicator=True,
                qmark="❯"
            ).ask()
        except KeyboardInterrupt:
            break

        if not selection or selection[0] == "exit":
            console.print("\n[bold yellow]Exiting WhatsApp CLI. Browser closing cleanly...[/]")
            break

        action, data = selection

        if action == "open_chat":
            contact_name = data
            with console.status(f"[bold cyan]Opening chat with {contact_name}...", spinner="dots"):
                opened = client.open_chat_by_name(contact_name)
            if opened:
                chat_session_loop(client, contact_name)
            else:
                console.print(f"[bold red]Could not open chat with {contact_name}.[/]")
                time.sleep(1.5)

        elif action == "new_number":
            phone = questionary.text(
                "Enter phone number with country code (e.g. +1234567890):",
                qmark="📞"
            ).ask()

            if phone and phone.strip():
                clean_phone = "".join(ch for ch in phone if ch.isdigit())
                if client.open_chat_by_number(clean_phone):
                    chat_session_loop(client, f"+{clean_phone}")
                else:
                    time.sleep(2)

        elif action == "refresh":
            continue
