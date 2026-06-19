import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import logging

logger = logging.getLogger("primary")

class CollapsibleSection(ttk.Frame):
	"""Make a collapsible section."""
	def __init__(self, parent: ttk.Frame, title: str = "Section") -> None:
		super().__init__(parent)

		self.title = title
		self.open = False
		self.style = ttk.Style(self)
		self.style.configure("Toolbutton", font=("TkDefaultFont", 14))

		self.header_btn = ttk.Button(
			self,
			text=f"[+] {self.title}",
			command=self.toggle,
			style="Toolbutton",
		)
		self.header_btn.pack(fill="x")

		self.content = ttk.Frame(self)
		self.content.columnconfigure(0, weight=1)

	def toggle(self) -> None:
		"""Toggle the visibility of the content frame and update the header button text accordingly."""
		self.open = not self.open

		if self.open:
			self.header_btn.config(text=f"[-] {self.title}")
			self.content.pack(fill="x", padx=10, pady=5)
		else:
			self.header_btn.config(text=f"[+] {self.title}")
			self.content.forget()


class ProgressTimerDialog:
	def __init__(self, parent, title="Processing...", message=None):
		self.top = tk.Toplevel(parent)
		self.top.title(title)
		self.top.geometry("320x140")
		self.top.transient(parent)
		self.top.grab_set()

		if message:
			ttk.Label(self.top, text=message).pack(pady=(8, 4))

		self.progress = ttk.Progressbar(
			self.top,
			mode="indeterminate",
			length=260
		)
		self.progress.pack(pady=5)

		self.time_label = ttk.Label(self.top, text="Elapsed: 0.0 s")
		self.time_label.pack(pady=5)

		# internal state
		self._job = None
		self.start_time = time.time()

	# ---------- TIMER ----------
	def _format_elapsed(self):
		elapsed = time.time() - self.start_time

		if elapsed < 60:
			return f"Elapsed: {elapsed:.1f} s"
		elif elapsed < 3600:
			mins = int(elapsed // 60)
			return f"Elapsed: {mins} min {int(elapsed % 60)} s"
		else:
			hours = int(elapsed // 3600)
			mins = int((elapsed % 3600) // 60)
			return f"Elapsed: {hours} h {mins} min"

	def _tick(self):
		self.time_label.config(text=self._format_elapsed())
		self._job = self.top.after(100, self._tick)

	# ---------- CONTROL ----------
	def start(self):
		self.start_time = time.time()
		self.progress.start(10)
		self._tick()

	def stop(self):
		"""Stops timer and progress WITHOUT closing window"""
		self.progress.stop()

		if self._job:
			self.top.after_cancel(self._job)
			self._job = None

		# One final update so the time freezes correctly
		if self.start_time:
			self.time_label.config(text=self._format_elapsed())

	def close(self):
		"""Stops everything and closes window"""
		self.stop()
		self.top.destroy()

	def get_elapsed_text(self):
		if self.start_time:
			return self._format_elapsed()
		return "Elapsed: 0.0 s"


def safe_gui_call(title="Error"):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                # Full traceback goes to log
                logger.exception("Unhandled exception in GUI action")

                # Short message to user (must be in main thread)
                self.root.after(
                    0,
                    lambda e=e: messagebox.showerror(title, str(e))
                )
        return wrapper
    return decorator


def safe_gui_thread(title="Error"):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            def run():
                try:
                    func(self, *args, **kwargs)
                except Exception as e:
                    logger.exception("Unhandled exception in background task")

                    self.root.after(
                        0,
                        lambda e=e: messagebox.showerror(title, str(e))
                    )

            thread = threading.Thread(target=run, daemon=True)
            thread.start()
            return thread

        return wrapper
    return decorator

@dataclass(frozen=True)
class FileSelectorConfig:
    title: str
    config_key: str
    multiple: bool
    var_attr: str
    set_method: str
    load_method: str
    format_attr: Optional[str] = None
    threaded: bool = False
    loading_title: str = ""
    loading_message: str = ""

if __name__ == "__main__":
	print("Utilities for KGVerifyPy GUI.")