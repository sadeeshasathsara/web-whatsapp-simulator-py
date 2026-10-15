import os
from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright, BrowserContext, Page, Playwright

from .stealth import STEALTH_INIT_SCRIPT

class BrowserManager:
    """Manages Playwright lifecycle, persistent sessions, and window visibility."""

    def __init__(self, session_dir: Path, browser_channel: str = "chrome", dev_mode: bool = False):
        self.session_dir = Path(session_dir)
        self.browser_channel = browser_channel
        self.dev_mode = dev_mode
        self.playwright: Optional[Playwright] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def start(self) -> Page:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.playwright = sync_playwright().start()

        channel = self.browser_channel if self.browser_channel in ["chrome", "msedge"] else None

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-default-browser-check",
        ]

        if self.dev_mode:
            launch_args.append("--start-maximized")
            viewport = None
        else:
            # Run off-screen to remain completely invisible while retaining full GPU & codecs
            launch_args.extend(["--window-position=-32000,-32000", "--window-size=1280,800"])
            viewport = {"width": 1280, "height": 800}

        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.session_dir),
            channel=channel,
            headless=False,
            args=launch_args,
            viewport=viewport,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.page.add_init_script(STEALTH_INIT_SCRIPT)
        return self.page

    def set_window_visible(self, visible: bool):
        """Uses Chrome DevTools Protocol to move window on or off-screen dynamically."""
        if not self.page or not self.context:
            return
        try:
            client = self.context.new_cdp_session(self.page)
            win = client.send("Browser.getWindowForTarget")
            if visible:
                client.send("Browser.setWindowBounds", {
                    "windowId": win["windowId"],
                    "bounds": {"left": 100, "top": 100, "width": 1100, "height": 800, "windowState": "normal"}
                })
            else:
                client.send("Browser.setWindowBounds", {
                    "windowId": win["windowId"],
                    "bounds": {"left": -32000, "top": -32000, "windowState": "normal"}
                })
            client.detach()
        except Exception:
            pass

    def stop(self):
        if self.context:
            self.context.close()
            self.context = None
        if self.playwright:
            self.playwright.stop()
            self.playwright = None
        self.page = None
