"""Simple Tkinter GUI for selecting CIM/SHACL files and showing output."""

import tkinter as tk
from tkinter import filedialog, ttk, messagebox, scrolledtext
import threading
from typing import Callable, Optional
from pathlib import Path
from rdflib.namespace import SH
from kgverifypy.file_handling import load_json, save_json
from kgverifypy.validation_service import ShaclValidationService
from kgverifypy.csv_utilities import collect_violations, write_shacl_violations_to_csv
from kgverifypy.data_handler import DataHandler
from kgverifypy.namespaces import compare_namespaces

FILE_CONFIG_PATH = Path(__file__).parent / "file_config.json"
DEFAULT_MAIN_GEOMETRY = "760x700"
DEFAULT_MAIN_MIN_SIZE = (680, 600)
DEFAULT_OUTPUT_GEOMETRY = "760x560"
DEFAULT_OUTPUT_MIN_SIZE = (680, 420)
DEFAULT_VALIDATION_OUTPUT = "../validation_results.json"
UI_FONT = ("TkDefaultFont", 14)	# 12
OUTPUT_FONT = ("TkDefaultFont", 16) # 13


class CollapsibleSection(ttk.Frame):
	def __init__(self, parent: ttk.Frame, title: str = "Section") -> None:
		super().__init__(parent)

		self.title = title
		self.open = False
		self.style = ttk.Style(self)
		self.style.configure("Toolbutton", font=UI_FONT)

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
		self.datahandler = DataHandler()
		self.file_config = load_json(FILE_CONFIG_PATH) if FILE_CONFIG_PATH.exists() else {}
		self.root = tk.Tk()
		self._configure_root_window()
		self._configure_styles()

		self.shacl_format = tk.StringVar(value="ttl")
		self.data_format = tk.StringVar(value="cimxml")
		self.validation_output_path = tk.StringVar(value=DEFAULT_VALIDATION_OUTPUT)
		self.validation_output_format = tk.StringVar(value="json-ld")
		self.add_datatypes_var = tk.BooleanVar(value=False)
		self.custom_url_var = tk.StringVar()
		self.csv_report_var = tk.BooleanVar(value=False)

		self.validation_service = ShaclValidationService()

		self._build_ui()
		self._restore_from_config()
		self.datahandler.load_files()
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
		self.style.configure("scrolltext", font=UI_FONT)

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
		
		# For adding RDFS files
		rdfs_section = CollapsibleSection(frame, title="Add RDFS files")
		rdfs_section.grid(row=row, column=0, sticky="ew", pady=(20, 10))
		self.rdfs_section(rdfs_section.content, 0)
		row += 1

		# For adding datatypes from context
		datatype_section = CollapsibleSection(frame, title="Datatype enrichment options")
		datatype_section.grid(row=row, column=0, sticky="ew", pady=(0, 20))
		self._datatype_section(datatype_section.content, 0)
		row += 1
		
		ttk.Button(frame, text="Check namespaces", command=self.show_namespace_report).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(5, 15))
		row += 1

		row = self._shacl_output_section(frame, row)

		ttk.Button(frame, text="Run SHACL validation", command=self.run).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(14, 0))

	def _restore_from_config(self) -> None:
		if not self.file_config:
			return
		
		data_cfg = self.file_config.get("data", {})
		data_format = data_cfg.get("format", "cimxml")
		self.data_format.set(data_format)
		self.datahandler.data_format = data_format

		shacl_cfg = self.file_config.get("shacl", {})
		shacl_format = shacl_cfg.get("format", "ttl")
		self.shacl_format.set(shacl_format)
		self.datahandler.shacl_format = shacl_format

	def _file_selection_section(self, frame: ttk.Frame, start_row: int) -> int:
		row = start_row

		# Data files
		ttk.Label(frame, text="Data files:").grid(row=row, column=0, sticky="w", pady=(10, 6))
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
		ttk.Label(frame, text="SHACL files:").grid(row=row, column=0, sticky="w", pady=(10, 6))
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
		row += 1

		return row
	
	def show_namespace_report(self):
		graphs = {
			"data": self.datahandler.data_graph,
			"shacl": self.datahandler.shacl_graph
		}

		if self.datahandler.rdfs_graph is not None:
			graphs["rdfs"] = self.datahandler.rdfs_graph

		report = compare_namespaces(graphs)

		if all_namespaces_match(report):
			messagebox.showinfo("Namespace Check", "✅ All namespaces match.")
			return

		matrix_text = format_namespace_matrix(report, list(graphs.keys()))

		# Popup window with scroll
		win = tk.Toplevel()
		win.title("Namespace Differences")

		text_area = scrolledtext.ScrolledText(win, wrap=tk.WORD, width=110, height=30, font=("Courier", 20))
		text_area.insert(tk.END, matrix_text)
		text_area.config(state=tk.DISABLED)
		text_area.pack(padx=10, pady=10)

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

		ttk.Entry(frame, textvariable=self.validation_output_path).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(6, 6))
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

	def _save_config_info(self, filestr: str, dataset: str, format: Optional[str] = None) -> None:
		if format:
			self.file_config[dataset]["format"] = format
		self.file_config[dataset]["last_directory"] = str(Path(filestr).parent)
		save_json(self.file_config, FILE_CONFIG_PATH)

	def load_dir_from_config(self, dataset: str) -> str:
		if self.file_config and dataset in self.file_config:
			return self.file_config[dataset].get("last_directory", str(Path.home()))
		return str(Path.home())
	
	def select_data_files(self) -> None:
		initial_dir = self.load_dir_from_config("data")
		files = filedialog.askopenfilenames(initialdir=initial_dir, title="Select data files")
		if files:
			filelist = list(files)
			self.datahandler.data_files = filelist
			self.data_var.set(f"{len(self.datahandler.data_files)} files selected")
			self.datahandler.data_format = self.data_format.get()
			self._save_config_info(filelist[0], "data", self.data_format.get())
			self.datahandler.load_files()

	def select_rdfs_files(self) -> None:
		initial_dir = self.load_dir_from_config("rdfs")
		files = filedialog.askopenfilenames(initialdir=initial_dir, title="Select RDFS files")
		if files:	# RDFS files are optional so last filepaths are not recorded.
			filelist = list(files)
			self.datahandler.rdfs_files = filelist
			self.rdfs_var.set(f"{len(self.datahandler.rdfs_files)} files selected")
			self._save_config_info(filelist[0], "rdfs")
			self.datahandler.load_files()

	def select_shacl_file(self) -> None:
		initial_dir = self.load_dir_from_config("shacl")
		file = filedialog.askopenfilename(initialdir=initial_dir, title="Select shacl file")
		if file:
			self.datahandler.shacl_file = file
			self.shacl_var.set(file)
			self.datahandler.shacl_format = self.shacl_format.get()
			self._save_config_info(file, "shacl", self.shacl_format.get())
			self.datahandler.load_files()

	def select_datatype_file(self) -> None:
		initial_dir = self.load_dir_from_config("datatypes")
		file = filedialog.askopenfilename(initialdir=initial_dir, title="Select context file for datatype enrichment")
		if file:
			self.datahandler.datatype_file = file
			self.datatype_file_var.set(file)
			self._save_config_info(file, "datatypes")
			self.datahandler.load_files()

	def run(self) -> None:
		top = tk.Toplevel(self.root)
		top.title("Run output")
		top.geometry(DEFAULT_OUTPUT_GEOMETRY)
		top.minsize(*DEFAULT_OUTPUT_MIN_SIZE)

		progress = ttk.Progressbar(top, mode="indeterminate")
		progress.pack(fill="x", padx=10, pady=(0, 10))
		try:
			self._show_output_message(top, "Running SHACL validation...\n")
			self._prepare_data_graph()
			self._report_focus_nodes(top)
			self._run_shacl_validation_async(top, progress)
		except Exception as e:
			self._show_output_message(top, f"An error occurred:\n {str(e)}")

	def _show_output_message(self, top: tk.Toplevel, message: str, padding: int = 2) -> None:
		ttk.Label(top, text=message, padding=padding, font=OUTPUT_FONT).pack(fill="both", expand=True)

	def _prepare_data_graph(self) -> None:
		if self.datahandler.data_graph is None:
			return
		
		context_data = self.datahandler.datatypes if self.datahandler.datatype_file else None
		self.validation_service.prepare_data_for_validation(self.datahandler.data_graph, self.datahandler.rdfs_graph, add_datatypes=self.add_datatypes_var.get(), context_data=context_data)
			
	def _report_focus_nodes(self, top: tk.Toplevel) -> None:
		summary = self.validation_service.summarize_focus_nodes(self.datahandler.data_graph, self.datahandler.shacl_graph)
		if summary is None:
			return

		focus_message = (
			f"Total number of shapes: {summary.total_shapes}\n"
			f"Shapes with explicit focus nodes in graph: {summary.shapes_with_focus_nodes}\n"
		)
		self._show_output_message(top, focus_message)

	def _run_shacl_validation_async(self, top, progress):
		progress.start()

		def worker():
			try:
				result = self.validation_service.validate_graphs(
					self.datahandler.data_graph,
					self.datahandler.shacl_graph,
					self.datahandler.rdfs_graph
				)

				# Pass result back to UI thread
				top.after(0, lambda: self._on_validation_done(top, progress, result))

			except Exception as e:
				top.after(0, lambda: self._on_validation_error(top, progress, e))

		threading.Thread(target=worker, daemon=True).start()


	def _on_validation_done(self, top, progress, result):
		progress.stop()
		progress.destroy()

		if result is None:
			self._show_output_message(top, "Data graph or SHACL graph not loaded.")
			return

		graph_count = len(self.datahandler.data_graph) if self.datahandler.data_graph else 0

		self._show_output_message(top, f"SHACL validation performed on {graph_count} triples.")
		self._show_output_message(top, f"Conforms: {result.conforms}")

		if result.summary_validation_results:
			message = "Summary of validation results (error type and count):\n"
			for error_type, count in result.summary_validation_results:
				message += f"{error_type}: {count}\n"
			self._show_output_message(top, message)

		if result.results_graph is not None and SH.result in result.results_graph.predicates():
			output_path = self.validation_output_path.get().strip() or DEFAULT_VALIDATION_OUTPUT
			output_format = self.validation_output_format.get()

			saved = self.validation_service.serialize_results(result.results_graph, output_path, output_format)
			if saved:
				self._show_output_message(top, f"Validation report saved to: {output_path}")

			if self.csv_report_var.get():
				csv_result = collect_violations(result.results_graph)
				csv_output_path = output_path.rsplit(".", 1)[0] + ".csv"
				write_shacl_violations_to_csv(csv_result, csv_output_path)
				self._show_output_message(top, f"Validation report saved as CSV to: {csv_output_path}")

	def _on_validation_error(self, top, progress, error):
		progress.stop()
		progress.destroy()
		self._show_output_message(top, f"An error occurred:\n{str(error)}")
		
	def _run_shacl_validation(self, top: tk.Toplevel) -> None:
		result = self.validation_service.validate_graphs(self.datahandler.data_graph, self.datahandler.shacl_graph, self.datahandler.rdfs_graph)
		if result is None:
			self._show_output_message(top, "Data graph or SHACL graph not loaded.")
			return

		graph_count = len(self.datahandler.data_graph) if self.datahandler.data_graph else 0
		self._show_output_message(top, f"SHACL validation performed on {graph_count} triples.")
		self._show_output_message(top, f"Conforms: {result.conforms}", padding=2)

		if result.summary_validation_results:
			message = "Summary of validation results (error type and count):\n"
			for error_type, count in result.summary_validation_results:
				message += f"{error_type}: {count}\n"

			self._show_output_message(top, message, padding=4)

		if result.results_graph is not None and SH.result in result.results_graph.predicates():	# If there are any results to report save it to file.
			output_path = self.validation_output_path.get().strip() or DEFAULT_VALIDATION_OUTPUT
			output_format = self.validation_output_format.get()
			saved = self.validation_service.serialize_results(result.results_graph, output_path, output_format)
			if saved:
				self._show_output_message(top, f"Validation report saved to: {output_path}", padding=0)

			if self.csv_report_var.get():
				csv_result = collect_violations(result.results_graph)
				csv_output_path = output_path.rsplit(".", 1)[0] + ".csv"
				write_shacl_violations_to_csv(csv_result, csv_output_path)
				self._show_output_message(top, f"Validation report saved as CSV to: {csv_output_path}", padding=0)

	def _graph_counts_for_debugging(self, top: tk.Toplevel) -> None:
		data_count = len(self.datahandler.data_graph) if self.datahandler.data_graph else 0
		rdfs_count = len(self.datahandler.rdfs_graph) if self.datahandler.rdfs_graph else 0
		shacl_count = len(self.datahandler.shacl_graph) if self.datahandler.shacl_graph else 0

		message = (
			f"Data Graph length: {data_count}\n"
			f"RDFS Graph length: {rdfs_count}\n"
			f"SHACL Graph length: {shacl_count}\n\n"
		)
		self._show_output_message(top, message)


def all_namespaces_match(report: list[dict]) -> bool:
	"""Check if all namespaces match across graphs based on the report generated by compare_namespaces.
	
	Parameters:
		report (list): The report generated by compare_namespaces, which is a list of dictionaries containing namespace comparison results.

	Returns:
		bool: True if all namespaces match (i.e., no missing namespaces in any graph), False otherwise.
	"""
	return all(len(row["missing"]) == 0 for row in report)


def format_namespace_matrix(report: list[dict], graph_names: list[str]) -> str:
	"""Format the namespace comparison report into a readable matrix format for display.
	
	Parameters:
		report (list): The report generated by kgverifypy.namespaces.compare_namespaces, which is a list of dictionaries containing namespace comparison results.
		graph_names (list): A list of graph names corresponding to the graphs compared in the report, used for labeling the columns in the matrix.

	Returns:
		str: A formatted string representing the namespace comparison matrix.
	"""
	max_uri_len = max(len(row["uri"]) for row in report) if report else 0
	col_width = 10

	lines = []

	header = "Namespace".ljust(max_uri_len) + " | " + " | ".join(name.upper().center(col_width) for name in graph_names)
	lines.append(header)
	lines.append("-" * len(header))

	for row in report:
		if row["missing"]:
			uri_part = row["uri"].ljust(max_uri_len)

			cols = []
			for name in graph_names:
				prefix = row["presence"].get(name)
				if prefix:
					cols.append(f"✔ {prefix}".center(col_width))
				else:
					cols.append("✘".center(col_width))

			line = uri_part + " | " + " | ".join(cols)
			lines.append(line)	

	return "\n".join(lines)


def main() -> None:
	CIMShaclGUI()


if __name__ == "__main__":
	main()