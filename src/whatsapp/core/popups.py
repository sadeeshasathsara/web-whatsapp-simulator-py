import time

def dismiss_any_popups(page) -> bool:
    """
    Automatically detects and closes unexpected overlay modals or popups
    (e.g., 'Get WhatsApp for Windows', 'Turn on notifications', 'WhatsApp updated').
    """
    try:
        js_dismiss = """
        () => {
            let dismissed = false;
            
            // 1. Look for dialogs / modals
            const dialogs = document.querySelectorAll('div[role="dialog"], div[data-animate-modal-popup="true"]');
            for (let dialog of dialogs) {
                const buttons = dialog.querySelectorAll('button, div[role="button"]');
                for (let btn of buttons) {
                    const text = (btn.innerText || '').toLowerCase().trim();
                    const aria = (btn.getAttribute('aria-label') || '').toLowerCase().trim();
                    if (['ok', 'close', 'not now', 'dismiss', 'cancel', 'maybe later', 'got it'].includes(text) ||
                        ['close', 'dismiss', 'cancel'].includes(aria) ||
                        btn.querySelector('span[data-icon="x"], span[data-icon="x-alt"]')) {
                        btn.click();
                        dismissed = true;
                        break;
                    }
                }
            }
            
            // 2. Look for standalone banner close buttons
            const closeIcons = document.querySelectorAll('button[aria-label="Close"], span[data-icon="x"], span[data-icon="x-alt"]');
            for (let icon of closeIcons) {
                if (icon.closest && (icon.closest('div[role="alert"]') || icon.closest('div[data-testid="intro-banner"]') || icon.closest('div[data-testid="banner"]'))) {
                    icon.click();
                    dismissed = true;
                }
            }
            return dismissed;
        }
        """
        page.evaluate(js_dismiss)

        # 3. Press Escape as a backup if a modal backdrop is still active
        dialog_loc = page.locator('div[role="dialog"], div[data-animate-modal-popup="true"]').first
        if dialog_loc.is_visible():
            page.keyboard.press("Escape")
            time.sleep(0.3)
            return True
        return False
    except Exception:
        return False
