"""Simple Tkinter GUI for selecting CIM/SHACL files and showing output."""

import tkinter as tk
from tkinter import filedialog, ttk
from typing import Callable
from pathlib import Path
from rdflib import Graph
from rdflib.namespace import SH
from kgverifypy.file_handling import make_graphs_from, merge_trig_graphs, load_json, save_json
from kgverifypy.validation_service import ShaclValidationService
from kgverifypy.csv_utilites import collect_violations, write_violations_to_csv

FILE_CONFIG_PATH = Path(__file__).parent / "file_config.json"
DEFAULT_MAIN_GEOMETRY = "760x680"
DEFAULT_MAIN_MIN_SIZE = (680, 560)
DEFAULT_OUTPUT_GEOMETRY = "760x560"
DEFAULT_OUTPUT_MIN_SIZE = (680, 420)
DEFAULT_VALIDATION_OUTPUT = "../validation_results.json"
UI_FONT = ("TkDefaultFont", 12)
OUTPUT_FONT = ("TkDefaultFont", 13)



class CollapsibleSection(ttk.Frame):
	def __init__(self, parent, title="Section"):
		super().__init__(parent)

		self.title = title
		self.open = False

		self.header_btn = ttk.Button(
			self,
			text=f"[+] {self.title}",
			command=self.toggle,
			style="Toolbutton",
		)
		self.header_btn.pack(fill="x")

		self.content = ttk.Frame(self)
		self.content.columnconfigure(0, weight=1)

	def toggle(self):
		self.open = not self.open

		if self.open:
			self.header_btn.config(text=f"[-] {self.title}")
			self.content.pack(fill="x", padx=10, pady=5)
		else:
			self.header_btn.config(text=f"[+] {self.title}")
			self.content.forget()

class CIMShaclGUI:
	"""GUI for selecting multiple files and displaying a run summary."""

	def __init__(self) -> None:
		self.file_config = load_json(FILE_CONFIG_PATH) if FILE_CONFIG_PATH.exists() else {}
		self.root = tk.Tk()
		self._configure_root_window()
		self._configure_styles()

		self.data_files: list[str] = []
		self.rdfs_files: list[str] = []
		self.shacl_file: str = ""
		self.datatype_file: str = ""
		self.shacl_format = tk.StringVar(value="ttl")
		self.data_format = tk.StringVar(value="cimxml")
		self.validation_output_path = tk.StringVar(value=DEFAULT_VALIDATION_OUTPUT)
		self.validation_output_format = tk.StringVar(value="json-ld")
		self.add_datatypes_var = tk.BooleanVar(value=False)
		self.custom_url_var = tk.StringVar()
		self.csv_report_var = tk.BooleanVar(value=False)

		self.rdfs_graph: Graph | None = None
		self.data_graph: Graph | None = None
		self.shacl_graph: Graph | None = None
		self.validation_service = ShaclValidationService()

		self._build_ui()
		self._restore_from_config()
		self.load_files()
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
		self.style.configure("TCheckbutton", font=UI_FONT)

	def _build_ui(self) -> None:
		frame = ttk.Frame(self.root, padding=12)
		frame.grid(row=0, column=0, sticky="nsew")

		self.root.columnconfigure(0, weight=1)
		self.root.rowconfigure(0, weight=1)
		frame.columnconfigure(0, weight=1)

		self.data_var = tk.StringVar(value=self.file_config.get("data_files", "No files selected") if self.file_config else "No files selected")
		self.shacl_var = tk.StringVar(value=self.file_config.get("shacl_files", "No files selected") if self.file_config else "No files selected")

		row = 0
		row = self._file_selection_section(frame, row)
		row += 1
		
		# For adding rdfs files
		rdfs_section = CollapsibleSection(frame, title="Add rdfs files")
		rdfs_section.grid(row=row, column=0, sticky="ew", pady=(20, 10))
		self.rdfs_section(rdfs_section.content, 0)
		row += 1

		# For adding datatypes from context
		datatype_section = CollapsibleSection(frame, title="Datatype enrichment options")
		datatype_section.grid(row=row, column=0, sticky="ew", pady=(0, 20))
		self._datatype_section(datatype_section.content, 0)
		row += 1
		
		row = self._shacl_output_section(frame, row)

		ttk.Button(frame, text="Run", command=self.run).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(14, 0))

	def _restore_from_config(self) -> None:
		if not self.file_config:
			return
		
		data_files = self.file_config.get("data_files", [])
		if data_files:
			self.data_files = data_files
			self.data_var.set(f"{len(self.data_files)} files selected")

		shacl_files = self.file_config.get("shacl_files", [])
		if shacl_files:
			self.shacl_file = shacl_files[0]
			self.shacl_var.set(self.shacl_file)

	def _file_selection_section(self, frame: ttk.Frame, start_row: int) -> int:
		row = start_row

		# Data files
		ttk.Label(frame, text="data files:").grid(row=row, column=0, sticky="w", pady=(10, 6))
		row += 1
		
		data_format_frame = ttk.Frame(frame)
		data_format_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 6))
		ttk.Radiobutton(data_format_frame, text="CIMXML", variable=self.data_format, value="cimxml").pack(side="left", padx=(0, 12))
		ttk.Radiobutton(data_format_frame, text="RDF/XML", variable=self.data_format, value="xml").pack(side="left", padx=(0, 12))
		ttk.Radiobutton(data_format_frame, text="JSON-LD", variable=self.data_format, value="json-ld").pack(side="left", padx=(0, 12))
		ttk.Radiobutton(data_format_frame, text="TRIG", variable=self.data_format, value="trig").pack(side="left", padx=(0, 12))
		ttk.Radiobutton(data_format_frame, text="TTL", variable=self.data_format, value="ttl").pack(side="left")
		row += 1

		row = self._add_file_picker_row(frame, row, self.data_var, self.select_data_files)

		# SHACL files
		ttk.Label(frame, text="shacl files:").grid(row=row, column=0, sticky="w", pady=(10, 6))
		row += 1

		shacl_format_frame = ttk.Frame(frame)
		shacl_format_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 6))
		ttk.Radiobutton(shacl_format_frame, text="TTL", variable=self.shacl_format, value="ttl").pack(side="left", padx=(0, 12))
		ttk.Radiobutton(shacl_format_frame, text="RDF", variable=self.shacl_format, value="xml").pack(side="left")
		row += 1

		row = self._add_file_picker_row(frame, row, self.shacl_var, self.select_shacl_file)
		row += 1

		return row
	
	def rdfs_section(self, frame: ttk.Frame, start_row: int) -> int:
		row = start_row

		self.rdfs_var = tk.StringVar(value="No files selected")

		# ttk.Label(frame, text="rdfs files:").grid(row=row, column=0, sticky="w", pady=(10, 6))
		row = self._add_file_picker_row(frame, row, self.rdfs_var, self.select_rdfs_files)
		row += 1
		return row

	def _datatype_section(self, frame: ttk.Frame, start_row: int) -> int:
		row = start_row

		self.datatype_file_var = tk.StringVar(value="If left empty a default context will be used")

		check = ttk.Checkbutton(frame, text="Add datatypes", variable=self.add_datatypes_var)
		check.grid(row=row, column=0, sticky="w")
		row += 1

		ttk.Label(frame, text="Custom context file:").grid(row=row, column=0, sticky="w", pady=(10, 6))
		row += 1
		row = self._add_file_picker_row(frame, row, self.datatype_file_var, self.select_datatype_file)
		# ttk.Entry(frame, textvariable=self.custom_url_var).grid(row=row, column=0, columnspan=2, sticky="ew")		
		row += 1

		return row

	def _shacl_output_section(self, frame: ttk.Frame, start_row: int) -> int:
		row = start_row

		ttk.Label(frame, text="Validation output file path:").grid(row=row, column=0, sticky="w", pady=(10, 6))
		row += 1

		validation_format_frame = ttk.Frame(frame)
		validation_format_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
		ttk.Radiobutton(validation_format_frame, text="JSON-LD", variable=self.validation_output_format, value="json-ld").pack(side="left", padx=(0, 12))
		ttk.Radiobutton(validation_format_frame, text="TTL", variable=self.validation_output_format, value="ttl").pack(side="left", padx=(0, 12))
		ttk.Radiobutton(validation_format_frame, text="RDF", variable=self.validation_output_format, value="xml").pack(side="left")
		row += 1

		ttk.Entry(frame, textvariable=self.validation_output_path).grid(row=row, column=0, columnspan=2, sticky="ew")
		row += 1

		check = ttk.Checkbutton(frame, text="CSV report", variable=self.csv_report_var)
		check.grid(row=row, column=0, sticky="w", pady=(10, 6))
		row += 1

		return row
	
	def _add_file_picker_row(
		self,
		frame: ttk.Frame,
		start_row: int,
		value_var: tk.StringVar,
		command: Callable[[], None],
	) -> int:
		ttk.Entry(frame, textvariable=value_var, state="readonly").grid(row=start_row, column=0, sticky="ew", padx=(0, 8))
		ttk.Button(frame, text="Browse", command=command).grid(row=start_row, column=1, sticky="ew")
		return start_row + 1

	def _select_files(self, title: str) -> list[str]:
		initial_dir = self.file_config.get("last_used_directory", str(Path.home())) if self.file_config else str(Path.home())
		files = filedialog.askopenfilenames(initialdir=initial_dir, title=title)
		self.file_config["last_used_directory"] = str(Path(files[0]).parent) if files else initial_dir
		save_json(self.file_config, FILE_CONFIG_PATH)
		return list(files)

	def select_data_files(self) -> None:
		files = self._select_files("Select data files")
		if files:
			self.data_files = files
			# if self.data_format.get() == "trig":
			# 	self.data_graph = merge_trig_graphs(self.data_files)
			# else:
			# 	self.data_graph = make_graphs_from(self.data_files, format=self.data_format.get())
			self.data_var.set(f"{len(self.data_files)} files selected")
			self.file_config["data_files"] = self.data_files
			save_json(self.file_config, FILE_CONFIG_PATH)
			self.load_files()

	def select_rdfs_files(self) -> None:
		files = self._select_files("Select rdfs files")
		if files:
			self.rdfs_files = files
			# self.rdfs_graph = make_graphs_from(self.rdfs_files, format="xml")
			self.rdfs_var.set(f"{len(self.rdfs_files)} files selected")
			self.load_files()

	def select_shacl_file(self) -> None:
		initial_dir = self.file_config.get("last_used_directory", str(Path.home())) if self.file_config else str(Path.home())
		file = filedialog.askopenfilename(initialdir=initial_dir, title="Select shacl file")
		if file:
			self.shacl_file = file
			# self.shacl_graph = make_graphs_from(self.shacl_file, format=self.shacl_format.get())
			self.shacl_var.set(file)
			self.file_config["shacl_files"] = [self.shacl_file]
			self.file_config["last_used_directory"] = str(Path(file).parent)
			save_json(self.file_config, FILE_CONFIG_PATH)
			self.load_files()

	def select_datatype_file(self) -> None:
		file = filedialog.askopenfilename(title="Select context file for datatype enrichment")
		if file:
			self.datatype_file = file
			# self.datatypes: dict = load_json(self.datatype_file)
			self.datatype_file_var.set(file)
			self.load_files()

	def load_files(self) -> None:
		if self.data_files:
			if self.data_format.get() == "trig":
				self.data_graph = merge_trig_graphs(self.data_files)
			else:
				self.data_graph = make_graphs_from(self.data_files, format=self.data_format.get())
		
		if self.rdfs_files:
			self.rdfs_graph = make_graphs_from(self.rdfs_files, format="xml")

		if self.shacl_file:
			self.shacl_graph = make_graphs_from(self.shacl_file, format=self.shacl_format.get())

		if self.datatype_file:
			self.datatypes = load_json(self.datatype_file)

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
			# f"Run: {data_count + rdfs_count} triples with {shacl_count} shapes"
		)
		try:
			self._prepare_data_graph()
			self._show_output_message(top, message)
			self._report_focus_nodes(top)
			self._run_shacl_validation(top)
		except Exception as e:
			self._show_output_message(top, f"An error occurred:\n {str(e)}")

	def _show_output_message(self, top: tk.Toplevel, message: str, padding: int = 2) -> None:
		ttk.Label(top, text=message, padding=padding, font=OUTPUT_FONT).pack(fill="both", expand=True)

	def _prepare_data_graph(self) -> None:
		if self.data_graph is None:
			return
		
		context_data = self.datatypes if self.datatype_file else None
		self.validation_service.prepare_data_for_validation(self.data_graph, self.rdfs_graph, add_datatypes=self.add_datatypes_var.get(), context_data=context_data)
			
	def _report_focus_nodes(self, top: tk.Toplevel) -> None:
		summary = self.validation_service.summarize_focus_nodes(self.data_graph, self.shacl_graph)
		if summary is None:
			return

		focus_message = (
			f"Total number of shapes: {summary.total_shapes}\n"
			f"Shapes with explicit focus nodes in graph: {summary.shapes_with_focus_nodes}\n"
		)
		self._show_output_message(top, focus_message)

	def _run_shacl_validation(self, top: tk.Toplevel) -> None:
		result = self.validation_service.validate_graphs(self.data_graph, self.shacl_graph, self.rdfs_graph)
		if result is None:
			self._show_output_message(top, "Data graph or SHACL graph not loaded.")
			return

		graph_count = len(self.data_graph) if self.data_graph else 0
		self._show_output_message(top, f"SHACL validation performed on {graph_count} triples.")
		self._show_output_message(top, f"Conforms: {result.conforms}", padding=2)

		if result.summary_validation_results:
			message = "Summary of validation results (error type and count):\n"
			for error_type, count in result.summary_validation_results:
				message += f"{error_type}: {count}\n"

			self._show_output_message(top, message, padding=4)

		if result.results_graph is not None and SH.result in result.results_graph.predicates():	# If there are any results to report save it to file.
		# if result.conforms == False:
			output_path = self.validation_output_path.get().strip() or DEFAULT_VALIDATION_OUTPUT
			output_format = self.validation_output_format.get()
			saved = self.validation_service.serialize_results(result.results_graph, output_path, output_format)
			if saved:
				self._show_output_message(top, f"Validation report saved to: {output_path}", padding=0)

			if self.csv_report_var.get():
				csv_result = collect_violations(result.results_graph)
				csv_output_path = output_path.rsplit(".", 1)[0] + ".csv"
				write_violations_to_csv(csv_result, csv_output_path)
				self._show_output_message(top, f"Validation report saved as CSV to: {csv_output_path}", padding=0)

def main() -> None:
	CIMShaclGUI()


if __name__ == "__main__":
	main()