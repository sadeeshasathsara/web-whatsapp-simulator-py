import time
import random
from pathlib import Path
from typing import List, Optional, Callable, Set
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from .core.browser import BrowserManager
from .core.stealth import human_delay, human_type
from .core.popups import dismiss_any_popups
from .models import ChatMessage, ChatSummary

DEFAULT_SESSION_DIR = Path.cwd() / "whatsapp_session"

class WhatsAppClient:
    """
    High-level, reusable WhatsApp automation client.
    Can be used by CLIs, background bots, notification services, or web backends.
    """

    def __init__(
        self,
        session_dir: Optional[Path] = None,
        browser: str = "chrome",
        dev_mode: bool = False,
        on_qr_needed: Optional[Callable[[], None]] = None,
        on_login_success: Optional[Callable[[], None]] = None
    ):
        self.session_dir = Path(session_dir) if session_dir else DEFAULT_SESSION_DIR
        self.browser_name = browser
        self.dev_mode = dev_mode
        self.on_qr_needed = on_qr_needed
        self.on_login_success = on_login_success

        self.browser_manager = BrowserManager(
            session_dir=self.session_dir,
            browser_channel=self.browser_name,
            dev_mode=self.dev_mode
        )
        self.page = None
        self.active_chat: Optional[str] = None
        self._message_listeners: List[Callable[[ChatMessage], None]] = []
        self._seen_message_ids: Set[str] = set()
        self._my_sent_messages: Set[str] = set()

    def connect(self) -> bool:
        """Launches the browser, navigates to WhatsApp Web, and checks login."""
        self.page = self.browser_manager.start()

        # Expose Python event listener for DOM mutations
        self.page.expose_function("onNewWhatsAppMessage", self._handle_browser_message)

        self.page.goto("https://web.whatsapp.com")
        return self._ensure_login()

    def _ensure_login(self) -> bool:
        chat_list_loc = self.page.locator('#pane-side, div[data-tab="3"], header[data-testid="chatlist-header"]')
        qr_loc = self.page.locator('canvas[aria-label="Scan me!"], div[data-ref], [data-testid="qrcode"], canvas')

        combined = chat_list_loc.or_(qr_loc)
        try:
            combined.first.wait_for(state="visible", timeout=35000)
        except PlaywrightTimeoutError:
            return False

        if qr_loc.first.is_visible() and not chat_list_loc.first.is_visible():
            if not self.dev_mode:
                self.browser_manager.set_window_visible(True)
                self.page.bring_to_front()

            if self.on_qr_needed:
                self.on_qr_needed()

            try:
                chat_list_loc.first.wait_for(state="visible", timeout=180000)
                if not self.dev_mode:
                    self.browser_manager.set_window_visible(False)
                if self.on_login_success:
                    self.on_login_success()
                return True
            except PlaywrightTimeoutError:
                return False
        else:
            if self.on_login_success:
                self.on_login_success()
            return True

    def get_recent_chats(self) -> List[ChatSummary]:
        """Extracts recent conversation summaries from the WhatsApp Web sidebar."""
        dismiss_any_popups(self.page)
        js_code = """
        () => {
            const pane = document.querySelector('#pane-side');
            if (!pane) return [];
            
            const rows = pane.querySelectorAll('div[role="listitem"], div[tabindex="-1"]');
            const results = [];
            const seen = new Set();
            
            rows.forEach(row => {
                const titleEl = row.querySelector('span[title], div[title], span[dir="auto"]');
                if (!titleEl) return;
                const name = (titleEl.getAttribute('title') || titleEl.innerText || '').trim();
                if (!name || seen.has(name) || name.length > 50) return;
                seen.add(name);
                
                const msgEl = row.querySelector('span[dir="ltr"], div[class*="_ak8k"] span, div[class*="_ak8j"] span');
                let lastMsg = msgEl ? msgEl.innerText.replace(/\\s+/g, ' ').trim() : '';
                if (lastMsg.length > 40) lastMsg = lastMsg.substring(0, 37) + '...';
                
                const timeEl = row.querySelector('div[class*="_ak8i"], span[class*="_ak8i"]');
                const timeStr = timeEl ? timeEl.innerText.trim() : '';
                
                results.push({ name: name, last_message: lastMsg, time: timeStr });
            });
            return results.slice(0, 20);
        }
        """
        try:
            data = self.page.evaluate(js_code) or []
            return [ChatSummary(**d) for d in data]
        except Exception:
            return []

    def open_chat_by_name(self, contact_name: str) -> bool:
        """Clicks the contact directly in the sidebar without reloading the page."""
        dismiss_any_popups(self.page)
        try:
            row = self.page.locator(f'#pane-side span[title="{contact_name}"], #pane-side div[role="listitem"]:has-text("{contact_name}")').first
            if row.is_visible():
                row.click()
                human_delay(0.6, 1.2)
                self.active_chat = contact_name
                self._attach_chat_observer()
                return True
        except Exception:
            pass
        opened = self._search_and_open(contact_name)
        if opened:
            self.active_chat = contact_name
            self._attach_chat_observer()
        return opened

    def open_chat_by_number(self, phone_number: str) -> bool:
        """Opens a direct conversation with a phone number (zero full-page reloads)."""
        clean_number = "".join(ch for ch in phone_number if ch.isdigit())
        if not clean_number or len(clean_number) < 7:
            return False

        dismiss_any_popups(self.page)
        if self._search_and_open(f"+{clean_number}") or self._search_and_open(clean_number):
            self.active_chat = f"+{clean_number}"
            self._attach_chat_observer()
            return True

        # In-page SPA client-side anchor click
        js_router_click = """
        (phone) => {
            const a = document.createElement('a');
            a.href = `https://web.whatsapp.com/send?phone=${phone}`;
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();
            setTimeout(() => a.remove(), 500);
        }
        """
        self.page.evaluate(js_router_click, clean_number)

        input_box_loc = self.page.locator('footer div[contenteditable="true"][role="textbox"], div[contenteditable="true"][data-tab="10"]')
        invalid_popup_loc = self.page.locator('div[data-testid="popup-contents"], div[role="dialog"]')

        try:
            target_loc = input_box_loc.or_(invalid_popup_loc)
            target_loc.first.wait_for(state="visible", timeout=25000)

            if invalid_popup_loc.first.is_visible():
                ok_btn = self.page.locator('div[role="dialog"] button, div[data-testid="popup-contents"] button').first
                if ok_btn.is_visible():
                    ok_btn.click()
                return False

            self.active_chat = f"+{clean_number}"
            self._attach_chat_observer()
            return True
        except PlaywrightTimeoutError:
            return False

    def _search_and_open(self, query: str) -> bool:
        dismiss_any_popups(self.page)
        search_box_loc = self.page.locator('div[contenteditable="true"][data-tab="3"], div[role="textbox"][aria-label*="Search"]')
        try:
            search_box = search_box_loc.first
            if not search_box.is_visible():
                return False

            search_box.click()
            human_delay(0.2, 0.4)
            self.page.keyboard.press("Control+A")
            self.page.keyboard.press("Backspace")

            for ch in query:
                self.page.keyboard.type(ch)
                time.sleep(random.uniform(0.03, 0.08))

            human_delay(1.2, 2.0)
            result_item = self.page.locator('#pane-side div[role="listitem"], div[aria-label*="Search results"] div[role="listitem"]').first
            if result_item.is_visible():
                result_item.click()
                human_delay(0.6, 1.2)
                self._clear_search()
                return True

            self._clear_search()
            return False
        except Exception:
            self._clear_search()
            return False

    def _clear_search(self):
        try:
            cancel_btn = self.page.locator('button[aria-label="Cancel search"], span[data-icon="x-alt"], span[data-icon="back"]').first
            if cancel_btn.is_visible():
                cancel_btn.click()
            else:
                self.page.keyboard.press("Escape")
            time.sleep(0.3)
        except Exception:
            pass

    def get_messages(self) -> List[ChatMessage]:
        """Extracts recent messages in the active chat."""
        js_code = """
        () => {
            const msgs = [];
            const bubbles = document.querySelectorAll('div[data-id], div[class*="message-in"], div[class*="message-out"]');
            bubbles.forEach(b => {
                const textEl = b.querySelector('.selectable-text, .copyable-text span, span[dir="ltr"], span._ao3e');
                const text = textEl ? textEl.innerText.trim() : '';
                if (!text) return;
                if (text.includes('end-to-end encrypted') || 
                    text.includes('Messages and calls are end-to-end') || 
                    text.includes('Waiting for this message') ||
                    text.includes('Use WhatsApp on your phone') ||
                    text.includes('Your messages are end-to-end encrypted')) {
                    return;
                }
                
                const dataId = b.getAttribute('data-id') || '';
                const isOut = dataId.startsWith('true_') || b.classList.contains('message-out') || !!b.closest('.message-out');
                const timeEl = b.querySelector('span[data-testid*="msg-meta"], div[class*="_amk6"]');
                const timeStr = timeEl ? timeEl.innerText.trim() : '';
                
                msgs.push({
                    message_id: dataId || text,
                    is_me: isOut,
                    text: text,
                    time: timeStr
                });
            });
            return msgs.slice(-10);
        }
        """
        try:
            raw = self.page.evaluate(js_code) or []
            return [
                ChatMessage(
                    text=m["text"],
                    sender="You" if m["is_me"] else (self.active_chat or "Contact"),
                    is_me=m["is_me"],
                    time=m["time"],
                    message_id=m["message_id"]
                )
                for m in raw
            ]
        except Exception:
            return []

    def send_message(self, message: str) -> bool:
        """Sends a message in the currently active conversation."""
        if not self.page:
            return False

        clean_text = message.strip()
        if not clean_text:
            return False

        input_box_loc = self.page.locator('footer div[contenteditable="true"][role="textbox"], div[contenteditable="true"][data-tab="10"]')
        try:
            input_box = input_box_loc.first
            input_box.click()
            human_delay(0.2, 0.4)

            human_type(self.page, clean_text)
            human_delay(0.2, 0.5)

            # Record outgoing to prevent echo
            self._my_sent_messages.add(clean_text)

            self.page.keyboard.press("Enter")
            human_delay(1.0, 1.8)
            return True
        except Exception:
            return False

    def on_message(self, callback: Callable[[ChatMessage], None]):
        """Registers a callback for real-time incoming messages."""
        self._message_listeners.append(callback)

    def _handle_browser_message(self, msg: dict):
        text = msg.get("text", "").strip()
        if not text:
            return

        if text in self._my_sent_messages:
            self._my_sent_messages.remove(text)
            return

        msg_id = msg.get("id") or (text + msg.get("time", ""))
        if msg_id in self._seen_message_ids:
            return
        self._seen_message_ids.add(msg_id)

        chat_msg = ChatMessage(
            text=text,
            sender=self.active_chat or "Contact",
            is_me=False,
            time=msg.get("time", ""),
            message_id=msg_id
        )

        for listener in self._message_listeners:
            try:
                listener(chat_msg)
            except Exception:
                pass

    def _attach_chat_observer(self):
        observer_js = """
        () => {
            if (window._chatObserver) window._chatObserver.disconnect();
            const panel = document.querySelector('div[data-testid="conversation-panel-messages"], #main, div[role="region"]') || document.body;
            window._chatObserver = new MutationObserver((mutations) => {
                for (let m of mutations) {
                    for (let node of m.addedNodes) {
                        if (!node || node.nodeType !== 1) continue;
                        let bubble = null;
                        if (node.getAttribute && (node.getAttribute('data-id') || node.classList.contains('message-in') || node.classList.contains('message-out'))) {
                            bubble = node;
                        } else if (node.querySelector) {
                            bubble = node.querySelector('div[data-id], div.message-in, div.message-out');
                        }
                        if (bubble) {
                            const dataId = bubble.getAttribute('data-id') || '';
                            const isOut = dataId.startsWith('true_') || bubble.classList.contains('message-out') || !!bubble.closest('.message-out');
                            if (isOut) return;
                            
                            const textEl = bubble.querySelector('.selectable-text, .copyable-text span, span[dir="ltr"], span._ao3e');
                            const text = textEl ? textEl.innerText.trim() : '';
                            if (!text || text.includes('end-to-end encrypted') || text.includes('Messages and calls are end-to-end')) return;
                            
                            const timeEl = bubble.querySelector('span[data-testid*="msg-meta"], div[class*="_amk6"]');
                            const timeStr = timeEl ? timeEl.innerText.trim() : '';
                            
                            if (window.onNewWhatsAppMessage) {
                                window.onNewWhatsAppMessage({
                                    id: dataId || text,
                                    is_me: false,
                                    text: text,
                                    time: timeStr
                                });
                            }
                        }
                    }
                }
            });
            window._chatObserver.observe(panel, { childList: true, subtree: true });
        }
        """
        try:
            self.page.evaluate(observer_js)
        except Exception:
            pass

    def close_active_chat(self):
        """Detaches observer and unsets active conversation."""
        self.active_chat = None
        if self.page:
            try:
                self.page.evaluate("() => { if (window._chatObserver) window._chatObserver.disconnect(); }")
            except Exception:
                pass

    def close(self):
        """Cleanly closes browser session."""
        self.close_active_chat()
        self.browser_manager.stop()
