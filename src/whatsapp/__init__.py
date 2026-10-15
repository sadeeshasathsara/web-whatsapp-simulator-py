"""
WhatsApp Automation & Stealth Simulator Library
"""

from .client import WhatsAppClient
from .models import ChatMessage, ChatSummary
from .core.browser import BrowserManager

__all__ = ["WhatsAppClient", "ChatMessage", "ChatSummary", "BrowserManager"]
__version__ = "0.1.0"
