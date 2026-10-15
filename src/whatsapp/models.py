from dataclasses import dataclass
from typing import Optional

@dataclass
class ChatMessage:
    """Represents an individual WhatsApp message."""
    text: str
    sender: str
    is_me: bool
    time: str = ""
    message_id: Optional[str] = None

@dataclass
class ChatSummary:
    """Represents a conversation row from the WhatsApp sidebar."""
    name: str
    last_message: str = ""
    time: str = ""
