#!/usr/bin/env python3
"""AI Event Editor - main entry point."""

import sys
import os
import ctypes

sys.path.insert(0, os.path.dirname(__file__))

# Set DPI awareness BEFORE any tkinter imports (maximize/multi-monitor safe).
# Prefer Per-Monitor (V2) awareness; fall back gracefully.
try:
    user32 = ctypes.windll.user32
    shcore = ctypes.windll.shcore

    # Windows 10+: Per-monitor v2 awareness (best behavior on maximize)
    # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = (HANDLE)-4
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        # Older API: 2 = PROCESS_PER_MONITOR_DPI_AWARE
        try:
            shcore.SetProcessDpiAwareness(2)
        except Exception:
            # Legacy fallback
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass
except Exception:
    pass

import customtkinter as ctk

# CustomTkinter compatibility mode for problematic Windows setups.
# This avoids additional DPI reconfiguration after startup.
try:
    ctk.deactivate_automatic_dpi_awareness()
except Exception:
    pass

# Set appearance BEFORE creating any widgets
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
ctk.set_widget_scaling(1.0)
ctk.set_window_scaling(1.0)

print("[main] Starting AI Event Editor...")
print(f"[main] CustomTkinter {ctk.__version__}, Python {sys.version}")
print(f"[main] Appearance: dark, Theme: blue")


def main():
    from src.app import App
    app = App()
    print("[main] Entering mainloop")
    app.mainloop()


if __name__ == "__main__":
    main()
