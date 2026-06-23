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
	"""Create dialog with progress bar and timer for long-running tasks."""
	def __init__(self, parent: tk.Tk, title: str="Processing...", message: Optional[str] = None, time_fn: Callable[[], float] = time.time) -> None:
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
		self.time_fn = time_fn

		# internal state
		self._job = None
		self.start_time = time.time()

	# ---------- TIMER ----------
	def _format_elapsed(self) -> str:
		"""Format the elapsed time since the timer was started into a human-readable string.
		
		Returns:
			str: The elapsed time in the format of "Elapsed: X s", "Elapsed: Y min Z s", or "Elapsed: H h M min" depending on the duration.
		"""
		elapsed = self.time_fn() - self.start_time

		if elapsed < 60:
			return f"Elapsed: {elapsed:.1f} s"
		elif elapsed < 3600:
			mins = int(elapsed // 60)
			return f"Elapsed: {mins} min {int(elapsed % 60)} s"
		else:
			hours = int(elapsed // 3600)
			mins = int((elapsed % 3600) // 60)
			return f"Elapsed: {hours} h {mins} min"

	def _tick(self) -> None:
		"""Update the elapsed time label and schedule the next update after 100 milliseconds."""
		self.time_label.config(text=self._format_elapsed())
		self._job = self.top.after(100, self._tick)
	
	# ---------- CONTROL ----------
	def start(self) -> None:
		"""Start the timer and progress bar."""
		self.start_time = time.time()
		self.progress.start(10)
		self._tick()

	def stop(self) -> None:
		"""Stop timer and progress WITHOUT closing window."""
		self.progress.stop()

		if self._job:
			self.top.after_cancel(self._job)
			self._job = None

		# Ensures time freezes correctly in window.
		if self.start_time:
			self.time_label.config(text=self._format_elapsed())

	def close(self) -> None:
		"""Stop everything and close window."""
		self.stop()
		self.top.destroy()

	def get_elapsed_text(self) -> str:
		"""Return the formatted elapsed time text.
		
		Returns:
			str: The formatted elapsed time text.
		"""
		if self.start_time:
			return self._format_elapsed()
		return "Elapsed: 0.0 s"


if __name__ == "__main__":
	print("Utilities for KGVerifyPy GUI.")