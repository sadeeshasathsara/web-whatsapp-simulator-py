import time

def format_message_line(sender: str, text: str, time_str: str = "") -> str:
    """Formats a message as: name (time) >> message here"""
    t = time_str.strip() if time_str and time_str.strip() else time.strftime("%I:%M %p").lstrip("0")
    return f"{sender} ({t}) >> {text}"
