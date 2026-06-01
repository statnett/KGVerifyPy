"""Simple Tkinter GUI for selecting CIM/SHACL files and showing output."""

import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable

from rdflib import Graph

from kgverifypy.file_handling import make_graph_from
from kgverifypy.validation_service import ShaclValidationService

DEFAULT_MAIN_GEOMETRY = "760x420"
DEFAULT_MAIN_MIN_SIZE = (680, 380)
DEFAULT_OUTPUT_GEOMETRY = "560x280"
DEFAULT_OUTPUT_MIN_SIZE = (480, 240)
DEFAULT_VALIDATION_OUTPUT = "../validation_results.json"
UI_FONT = ("TkDefaultFont", 12)
OUTPUT_FONT = ("TkDefaultFont", 13)

class CIMShaclGUI:
	"""GUI for selecting multiple files and displaying a run summary."""

	def __init__(self) -> None:
		self.root = tk.Tk()
		self._configure_root_window()
		self._configure_styles()

		self.data_files: list[str] = []
		self.rdfs_files: list[str] = []
		self.shacl_file: str = ""
		self.shacl_format = tk.StringVar(value="ttl")
		self.validation_output_path = tk.StringVar(value=DEFAULT_VALIDATION_OUTPUT)
		self.validation_output_format = tk.StringVar(value="json-ld")

		self.rdfs_graph: Graph | None = None
		self.data_graph: Graph | None = None
		self.shacl_graph: Graph | None = None
		self.validation_service = ShaclValidationService()

		self._build_ui()
		self.root.mainloop()

	def _configure_root_window(self) -> None:
		self.root.title("CIM pySHACL GUI")
		self.root.geometry(DEFAULT_MAIN_GEOMETRY)
		self.root.minsize(*DEFAULT_MAIN_MIN_SIZE)

	def _configure_styles(self) -> None:
		# Increase default text size for the whole GUI.
		self.style = ttk.Style(self.root)
		self.style.configure("TLabel", font=UI_FONT)
		self.style.configure("TButton", font=UI_FONT)
		self.style.configure("TRadiobutton", font=UI_FONT)
		self.style.configure("TEntry", font=UI_FONT)

	def _build_ui(self) -> None:
		frame = ttk.Frame(self.root, padding=12)
		frame.grid(row=0, column=0, sticky="nsew")

		self.root.columnconfigure(0, weight=1)
		self.root.rowconfigure(0, weight=1)
		frame.columnconfigure(0, weight=1)

		self.data_var = tk.StringVar(value="No files selected")
		self.rdfs_var = tk.StringVar(value="No files selected")
		self.shacl_var = tk.StringVar(value="No files selected")

		row = 0
		row = self._add_file_picker_row(frame, row, "data files:", self.data_var, self.select_data_files)
		row = self._add_file_picker_row(frame, row, "rdfs files:", self.rdfs_var, self.select_rdfs_files)

		ttk.Label(frame, text="shacl files:").grid(row=row, column=0, sticky="w", pady=(10, 6))
		row += 1

		shacl_format_frame = ttk.Frame(frame)
		shacl_format_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 6))
		ttk.Radiobutton(shacl_format_frame, text="TTL", variable=self.shacl_format, value="ttl").pack(side="left", padx=(0, 12))
		ttk.Radiobutton(shacl_format_frame, text="RDF", variable=self.shacl_format, value="xml").pack(side="left")
		row += 1

		ttk.Entry(frame, textvariable=self.shacl_var, state="readonly").grid(row=row, column=0, sticky="ew", padx=(0, 8))
		ttk.Button(frame, text="Browse", command=self.select_shacl_file).grid(row=row, column=1, sticky="ew")
		row += 1

		ttk.Label(frame, text="Validation output file path:").grid(row=row, column=0, sticky="w", pady=(10, 6))
		row += 1
		ttk.Entry(frame, textvariable=self.validation_output_path).grid(row=row, column=0, columnspan=2, sticky="ew")
		row += 1

		ttk.Label(frame, text="Validation output format:").grid(row=row, column=0, sticky="w", pady=(10, 6))
		row += 1

		validation_format_frame = ttk.Frame(frame)
		validation_format_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
		ttk.Radiobutton(validation_format_frame, text="JSON-LD", variable=self.validation_output_format, value="json-ld").pack(side="left", padx=(0, 12))
		ttk.Radiobutton(validation_format_frame, text="TTL", variable=self.validation_output_format, value="ttl").pack(side="left", padx=(0, 12))
		ttk.Radiobutton(validation_format_frame, text="RDF", variable=self.validation_output_format, value="xml").pack(side="left")
		row += 1

		ttk.Button(frame, text="Run", command=self.run).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(14, 0))

	def _add_file_picker_row(
		self,
		frame: ttk.Frame,
		start_row: int,
		label_text: str,
		value_var: tk.StringVar,
		command: Callable[[], None],
	) -> int:
		ttk.Label(frame, text=label_text).grid(row=start_row, column=0, sticky="w", pady=(10 if start_row else 0, 6))
		ttk.Entry(frame, textvariable=value_var, state="readonly").grid(row=start_row + 1, column=0, sticky="ew", padx=(0, 8))
		ttk.Button(frame, text="Browse", command=command).grid(row=start_row + 1, column=1, sticky="ew")
		return start_row + 2

	def _select_files(self, title: str) -> list[str]:
		files = filedialog.askopenfilenames(title=title)
		return list(files)

	def select_data_files(self) -> None:
		files = self._select_files("Select data files")
		if files:
			self.data_files = files
			self.data_graph = make_graph_from(self.data_files, format="cimxml")
			self.data_var.set(f"{len(self.data_files)} files selected")

	def select_rdfs_files(self) -> None:
		files = self._select_files("Select rdfs files")
		if files:
			self.rdfs_files = files
			self.rdfs_graph = make_graph_from(self.rdfs_files, format="xml")
			self.rdfs_var.set(f"{len(self.rdfs_files)} files selected")

	def select_shacl_file(self) -> None:
		file = filedialog.askopenfilename(title="Select shacl file")
		if file:
			self.shacl_file = file
			self.shacl_graph = make_graph_from(self.shacl_file, format=self.shacl_format.get())
			self.shacl_var.set("1 file selected")

	def run(self) -> None:
		data_count = len(self.data_graph) if self.data_graph else 0
		rdfs_count = len(self.rdfs_graph) if self.rdfs_graph else 0
		shacl_count = len(self.shacl_graph) if self.shacl_graph else 0

		top = tk.Toplevel(self.root)
		top.title("Run output")
		top.geometry(DEFAULT_OUTPUT_GEOMETRY)
		top.minsize(*DEFAULT_OUTPUT_MIN_SIZE)

		message = (
			f"Data Graph length: {data_count}\n"
			f"RDFS Graph length: {rdfs_count}\n"
			f"SHACL Graph length: {shacl_count}\n\n"
			f"Run: {data_count + rdfs_count} triples with {shacl_count} shapes"
		)
		self._show_output_message(top, message)
		self._report_focus_nodes(top)
		self._run_shacl_validation(top)

	def _show_output_message(self, top: tk.Toplevel, message: str) -> None:
		ttk.Label(top, text=message, padding=2, font=OUTPUT_FONT).pack(fill="both", expand=True)

	def _report_focus_nodes(self, top: tk.Toplevel) -> None:
		summary = self.validation_service.summarize_focus_nodes(self.data_graph, self.shacl_graph)
		if summary is None:
			return

		focus_message = (
			f"Total number of shapes: {summary.total_shapes}\n"
			f"Shapes with focus nodes in graph: {summary.shapes_with_focus_nodes}\n"
		)
		self._show_output_message(top, focus_message)

	def _run_shacl_validation(self, top: tk.Toplevel) -> None:
		result = self.validation_service.validate_graphs(self.data_graph, self.shacl_graph, self.rdfs_graph)
		if result is None:
			self._show_output_message(top, "Data graph or SHACL graph not loaded.")
			return

		self._show_output_message(top, f"SHACL validation performed on {len(self.data_graph)} triples.")
		self._show_output_message(top, f"Conforms: {result.conforms}")

		output_path = self.validation_output_path.get().strip() or DEFAULT_VALIDATION_OUTPUT
		output_format = self.validation_output_format.get()
		saved = self.validation_service.serialize_results(result.results_graph, output_path, output_format)
		if saved:
			self._show_output_message(top, f"Validation report saved to: {output_path}")

def main() -> None:
	CIMShaclGUI()


if __name__ == "__main__":
	main()