"""Windows Anti-Sleep and Screen Keep-Awake Engine for MKE Overnight Operation."""
from __future__ import annotations

import ctypes
import datetime as dt
import threading
import time
from typing import Dict, Any

# Windows Execution State Flags
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
ES_AWAYMODE_REQUIRED = 0x00000040

# Virtual Key / Mouse constants
VK_F15 = 0x7E  # F15 is a non-intrusive standard virtual key
MOUSEEVENTF_MOVE = 0x0001


class KeepAwakeController:
    """Controls Windows power state and virtual nudges to keep PC awake 24/7."""

    def __init__(self, interval_minutes: int = 15) -> None:
        self.interval_seconds = max(30, interval_minutes * 60)
        self.is_running = False
        self.last_nudge_time: str | None = None
        self.nudge_count = 0
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self._set_windows_state(True)

    def stop(self) -> None:
        if not self.is_running:
            return
        self.is_running = False
        self._stop_event.set()
        self._set_windows_state(False)

    def _set_windows_state(self, keep_awake: bool) -> None:
        try:
            if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "kernel32"):
                if keep_awake:
                    flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED | ES_AWAYMODE_REQUIRED
                else:
                    flags = ES_CONTINUOUS
                ctypes.windll.kernel32.SetThreadExecutionState(flags)
        except Exception:
            pass

    def _simulate_touch(self) -> None:
        """Simulate subtle user activity to prevent screensaver / lock screen."""
        try:
            if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "user32"):
                # Method A: Subtle relative mouse move (+1, 0) then (-1, 0)
                ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, 1, 0, 0, 0)
                time.sleep(0.05)
                ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, -1, 0, 0, 0)

                # Method B: Non-intrusive key press (F15)
                ctypes.windll.user32.keybd_event(VK_F15, 0, 0, 0)
                time.sleep(0.02)
                ctypes.windll.user32.keybd_event(VK_F15, 0, 2, 0)  # KEYEVENTF_KEYUP
        except Exception:
            pass

        self.last_nudge_time = dt.datetime.now(dt.timezone.utc).isoformat()
        self.nudge_count += 1

    def _loop(self) -> None:
        # Initial touch on start
        self._simulate_touch()
        while not self._stop_event.is_set():
            # Refresh Windows kernel state continuously every loop
            self._set_windows_state(True)
            # Wait for the next interval or until stopped
            if self._stop_event.wait(timeout=self.interval_seconds):
                break
            self._simulate_touch()

    def get_status(self) -> Dict[str, Any]:
        return {
            "enabled": self.is_running,
            "interval_minutes": self.interval_seconds // 60,
            "nudge_count": self.nudge_count,
            "last_nudge_time": self.last_nudge_time,
            "mode": "Windows API (SetThreadExecutionState + Relative Mouse/Key Nudge)",
        }


# Global singleton controller
keep_awake_service = KeepAwakeController(interval_minutes=15)
