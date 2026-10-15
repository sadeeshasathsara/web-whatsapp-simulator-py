import time
import random

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = {
    app: { isInstalled: false },
    runtime: {},
    loadTimes: function() {},
    csi: function() {}
};
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);
"""

def human_delay(min_sec: float = 0.2, max_sec: float = 0.5):
    """Sleeps for a random duration to mimic natural human reaction pauses."""
    time.sleep(random.uniform(min_sec, max_sec))


def human_type(page, text: str):
    """Types characters with variable keystroke timing."""
    for char in text:
        page.keyboard.type(char)
        time.sleep(random.uniform(0.03, 0.08))
        if random.random() < 0.05:
            time.sleep(random.uniform(0.10, 0.22))
