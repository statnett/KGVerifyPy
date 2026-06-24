"""GUI utilities for KGVerifyPy."""

import tkinter as tk
from tkinter import ttk
import time
from typing import Callable, Optional, Generator


class CollapsibleSection(ttk.Frame):
	"""Make a collapsible section."""

	def __init__(self, parent: ttk.Frame, title: str = "Section") -> None:
		super().__init__(parent)

		self.title: str = title
		self.open: bool = False
		self.style: ttk.Style = ttk.Style(self)
		self.style.configure("Toolbutton", font=("TkDefaultFont", 14))

		self.header_btn: ttk.Button = ttk.Button(
			self,
			text=f"[+] {self.title}",
			command=self.toggle,
			style="Toolbutton",
		)
		self.header_btn.pack(fill="x")

		self.content: ttk.Frame = ttk.Frame(self)
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
		self.top: tk.Toplevel = tk.Toplevel(parent)
		self.top.title(title)
		self.top.geometry("320x140")
		self.top.transient(parent)
		self.top.grab_set()

		if message:
			ttk.Label(self.top, text=message).pack(pady=(8, 4))

		self.progress: ttk.Progressbar = ttk.Progressbar(
			self.top,
			mode="indeterminate",
			length=260
		)
		self.progress.pack(pady=5)

		self.time_label: ttk.Label = ttk.Label(self.top, text="Elapsed: 0.0 s")
		self.time_label.pack(pady=5)
		self.time_fn: Callable[[], float] = time_fn

		# internal state
		self._job: Optional[str] = None
		self.start_time: float = time.time()

	# Timer
	def _format_elapsed(self) -> str:
		"""Format the elapsed time since the timer was started into a human-readable string.
		
		Returns:
			str: The elapsed time in the format of "Elapsed: X s", "Elapsed: Y min Z s", or "Elapsed: H h M min" depending on the duration.
		"""
		elapsed: float = self.time_fn() - self.start_time

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
	
	# Public methods
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


class ToolTip:
	"""Create tooltips for widgets and text substrings."""

	def __init__(self, delay: int = 400) -> None:
		self.tooltip: tk.Toplevel | None = None
		self.delay: int = delay  # milliseconds
		self.after_id: str | None = None

	def _show_now(self, widget: tk.Widget, x: int, y: int, text: str) -> None:
		"""Show the tooltip immediately at the specified position with the given text.
		
		Parameters:
			widget (tk.Widget): The widget to which the tooltip is attached.
			x (int): The x-coordinate for the tooltip's position.
			y (int): The y-coordinate for the tooltip's position.
			text (str): The text to display in the tooltip.
		"""
		self.hide()

		self.tooltip = tk.Toplevel(widget)
		self.tooltip.overrideredirect(True)
		self.tooltip.geometry(f"+{x+10}+{y+10}")

		label: tk.Label = tk.Label(
			self.tooltip,
			text=text,
			background="lightyellow",
			relief="solid",
			borderwidth=1,
			padx=3,
			pady=1
		)
		label.pack()


	def hide(self) -> None:
		"""Hide the tooltip and cancel any pending show."""
		if self.after_id:
			try:
				self.tooltip_widget.after_cancel(self.after_id)
			except Exception:	# Keeping the gui from crashing if the tooltip is not working properly.
				pass
			self.after_id = None

		if self.tooltip:
			self.tooltip.destroy()
			self.tooltip = None


	def show(self, widget: tk.Widget, x: int, y: int, text: str) -> None:
		"""Show the tooltip after a delay.
		
		Parameters:
			widget (tk.Widget): The widget to which the tooltip is attached.
			x (int): The x-coordinate for the tooltip's position.
			y (int): The y-coordinate for the tooltip's position.
			text (str): The text to display in the tooltip.
		"""
		self.hide()  # cancel previous widget's tooltip if any

		self.tooltip_widget: tk.Widget = widget

		def delayed():
			self._show_now(widget, x, y, text)

		self.after_id: str|None = widget.after(self.delay, delayed)


	def attach(self, widget: tk.Widget, text: str) -> None:
		"""Attach a tooltip to a widget, showing it on hover and hiding it on leave.
		
		Parameters:
			widget (tk.Widget): The widget to which the tooltip is attached.
			text (str): The text to display in the tooltip.
		"""
		def enter(e):
			self.show(widget, e.x_root, e.y_root, text)

		def leave(e):
			self.hide()

		widget.bind("<Enter>", enter)
		widget.bind("<Leave>", leave)


	def apply_to_text(self, text_widget: tk.Text, start_index: str, tag_map: dict) -> None:
		"""Apply tooltips to specific substrings in a Tkinter Text widget.
		
		Parameters:
			text_widget (tk.Text): The Text widget to which the tooltips will be applied.
			start_index (str): The index in the Text widget from which to start searching for substrings.
			tag_map (dict): A dictionary mapping substrings to their corresponding tooltip texts.
		"""
		for substring, tooltip_text in tag_map.items():
			for start, end in self._find_all(text_widget, substring, start_index):
				tag_name: str = self._create_tag(text_widget, start, end)
				text_widget.tag_config(tag_name, underline=False, foreground="#444444")
				self._bind_behaviours(text_widget, tag_name, tooltip_text)


	def _find_all(self, text_widget: tk.Text, substring: str, start_index: str) -> Generator[tuple[str, str], None, None]:
		"""Find all occurrences of a substring in a Tkinter Text widget starting from a given index.
		
		Parameters:
			text_widget (tk.Text): The Text widget in which to search for the substring.
			substring (str): The substring to search for.
			start_index (str): The index in the Text widget from which to start searching.

		Yields:
			tuple[str, str]: A tuple containing the start and end indices of each occurrence of the substring.
		"""
		idx = start_index
		while True:
			idx = text_widget.search(substring, idx, stopindex=tk.END)
			if not idx:
				break
			end = f"{idx}+{len(substring)}c"
			yield idx, end
			idx = end	# Prevents infinite loop


	def _create_tag(self, text_widget: tk.Text, start: str, end: str) -> str:
		"""Create a unique tag for a specific range in a Tkinter Text widget.
		
		Parameters:
			text_widget (tk.Text): The Text widget in which to create the tag.
			start (str): The start index of the range.
			end (str): The end index of the range.

		Returns:
			str: The name of the created tag.
		"""
		tag_name = f"tt_{start.replace('.', '_')}"
		text_widget.tag_add(tag_name, start, end)
		return tag_name
	

	def _bind_behaviours(self, text_widget: tk.Text, tag_name: str, tooltip_text: str) -> None:
		"""Bind mouse events to a specific tag in a Tkinter Text widget to show and hide tooltips.
		
		Parameters:
			text_widget (tk.Text): The Text widget in which to bind the events.
			tag_name (str): The name of the tag to which the events will be bound.
			tooltip_text (str): The text of the tooltip to be shown.
		"""
		text_widget.tag_bind(
			tag_name,
			"<Motion>",
			lambda e, t=tooltip_text: self.show(text_widget, e.x_root, e.y_root, t),
		)

		text_widget.tag_bind(tag_name, "<Leave>", lambda e: self.hide())


	# To make tooltips also clickable, this can be used instead of _bind_behaviours.
	# def _bind_behaviours_with_click(self, text_widget, tag_name, tooltip_text, enable_click):
	# 	text_widget.tag_bind(
	# 		tag_name,
	# 		"<Motion>",
	# 		lambda e, t=tooltip_text: self.show(text_widget, e.x_root, e.y_root, t),
	# 	)

	# 	text_widget.tag_bind(tag_name, "<Leave>", lambda e: self.hide())

	# 	if enable_click:
	# 		text_widget.tag_bind(
	# 			tag_name,
	# 			"<Button-1>",
	# 			lambda e, t=tooltip_text: self.show_popup(t),
	# 		)
	# def show_popup(self, text):
	# 	messagebox.showinfo("Help", text)



if __name__ == "__main__":
	print("Utilities for KGVerifyPy GUI.")