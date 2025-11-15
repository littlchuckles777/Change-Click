"""Change-Click Automation Tool.

This module provides a small background utility that listens for
press-and-hold events on the Mouse 5 button (typically the second side
button on modern mice). When the button is held, the utility captures the
colours of a cluster of pixels around the primary monitor's centre.
If any of those pixels change while the button remains depressed, the tool
synthesises a natural looking "x" key press.

The implementation focuses on:

* Remaining responsive while capturing only the essential pixels.
* Working system wide (no foreground window requirements).
* Avoiding suspicious behaviour by randomising the key press cadence.
"""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass
from typing import List, Sequence, Tuple

import mss
from mss.base import ScreenShot
from pynput import keyboard, mouse

# Type alias for RGB tuples.
RGB = Tuple[int, int, int]


@dataclass(frozen=True)
class SamplePoint:
    """Represents the coordinates of a pixel to sample."""

    x: int
    y: int


class PixelSampler:
    """Samples colours from the centre region of the primary monitor."""

    def __init__(self, cluster_offsets: Sequence[Tuple[int, int]] | None = None) -> None:
        self._thread_local: threading.local = threading.local()
        self._primary_monitor = self._primary_monitor_geometry()
        self._cluster_offsets = cluster_offsets or self._default_offsets()
        self._sample_points: List[SamplePoint] = self._compute_sample_points()

    def _default_offsets(self) -> List[Tuple[int, int]]:
        """Return pixel offsets that cover the central area with 10 points."""

        return [
            (0, 0),
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
            (-1, -1),
            (1, -1),
            (-1, 1),
            (1, 1),
            (0, 2),
        ]

    def _primary_monitor_geometry(self) -> dict:
        with mss.mss() as sct:
            return dict(sct.monitors[1])

    def _compute_sample_points(self) -> List[SamplePoint]:
        centre_x = self._primary_monitor["left"] + self._primary_monitor["width"] // 2
        centre_y = self._primary_monitor["top"] + self._primary_monitor["height"] // 2
        return [SamplePoint(centre_x + dx, centre_y + dy) for dx, dy in self._cluster_offsets]

    def sample(self) -> List[RGB]:
        """Capture the RGB colours for the configured sample points."""

        colours: List[RGB] = []
        sct = self._thread_local_mss()
        for point in self._sample_points:
            region = {
                "left": point.x,
                "top": point.y,
                "width": 1,
                "height": 1,
            }
            screenshot: ScreenShot = sct.grab(region)
            colours.append(screenshot.pixel(0, 0))
        return colours

    def _thread_local_mss(self) -> mss.mss:
        """Return an mss instance that is safe to use on the current thread."""

        if not hasattr(self._thread_local, "sct"):
            self._thread_local.sct = mss.mss()
        return self._thread_local.sct


class ChangeDetector:
    """Determines whether a set of sampled pixels has changed meaningfully."""

    def __init__(self, tolerance: int = 18, minimum_changed_pixels: int = 1) -> None:
        self._tolerance = tolerance
        self._minimum_changed_pixels = minimum_changed_pixels

    def has_changed(self, baseline: Sequence[RGB], current: Sequence[RGB]) -> bool:
        changes = 0
        for base, cur in zip(baseline, current):
            delta = sum(abs(a - b) for a, b in zip(base, cur))
            if delta > self._tolerance:
                changes += 1
                if changes >= self._minimum_changed_pixels:
                    return True
        return False


class NaturalKeySender:
    """Sends keyboard events with subtle random delays to appear human-like."""

    def __init__(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        self._controller = keyboard.Controller()
        self._key = key
        self._lock = threading.Lock()

    def tap(self) -> None:
        with self._lock:
            time.sleep(random.uniform(0.03, 0.08))
            self._controller.press(self._key)
            time.sleep(random.uniform(0.01, 0.04))
            self._controller.release(self._key)


class ChangeClickController:
    """Coordinates sampling, change detection, and key emission."""

    def __init__(
        self,
        sampler: PixelSampler | None = None,
        detector: ChangeDetector | None = None,
        sender: NaturalKeySender | None = None,
        poll_interval: float = 0.02,
    ) -> None:
        self._sampler = sampler or PixelSampler()
        self._detector = detector or ChangeDetector()
        self._sender = sender or NaturalKeySender(keyboard.KeyCode.from_char("x"))
        self._poll_interval = poll_interval

        self._baseline: List[RGB] | None = None
        self._monitoring = False
        self._monitor_thread: threading.Thread | None = None
        self._state_lock = threading.Lock()

    def start(self) -> None:
        with mouse.Listener(on_click=self._handle_click) as listener:
            listener.join()

    # Listener callbacks -------------------------------------------------

    def _handle_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        if button != mouse.Button.x2:
            return
        if pressed:
            self._begin_monitoring()
        else:
            self._stop_monitoring()

    # Monitoring logic ---------------------------------------------------

    def _begin_monitoring(self) -> None:
        with self._state_lock:
            if self._monitoring:
                return
            self._baseline = self._sampler.sample()
            self._monitoring = True
            self._monitor_thread = threading.Thread(target=self._watch_for_changes, daemon=True)
            self._monitor_thread.start()

    def _stop_monitoring(self) -> None:
        with self._state_lock:
            self._monitoring = False
            self._baseline = None

    def _watch_for_changes(self) -> None:
        while True:
            with self._state_lock:
                if not self._monitoring or self._baseline is None:
                    break
                baseline = list(self._baseline)
            current = self._sampler.sample()
            if self._detector.has_changed(baseline, current):
                self._sender.tap()
                with self._state_lock:
                    self._baseline = current
            time.sleep(self._poll_interval)


def main() -> None:
    controller = ChangeClickController()
    try:
        controller.start()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
