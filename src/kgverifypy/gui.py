"""Tkinter GUI for running SHACL validations."""

import tkinter as tk
from tkinter import filedialog, ttk, messagebox, scrolledtext
import threading
import queue
from typing import Callable, Optional, TYPE_CHECKING
from rdflib import Graph
from pathlib import Path
from rdflib.namespace import SH
from kgverifypy.file_handling import load_json, save_json
from kgverifypy.validation_service import ShaclValidationService, ShaclValidationResult
from kgverifypy.csv_utilities import collect_violations, write_shacl_violations_to_csv
from kgverifypy.data_handler import DataHandler, DatasetConfig
from kgverifypy.namespaces import compare_namespaces, all_namespaces_match, format_namespace_matrix
from kgverifypy.gui_utilites import CollapsibleSection, ProgressTimerDialog, ToolTip
from kgverifypy.information import TOOLTIP_TEXTS
import logging

if TYPE_CHECKING:
	from kgverifypy.validation_service import FocusNodeSummary
	from kgverifypy.csv_utilities import ConstraintViolation

logger = logging.getLogger("primary")

# Variables
FILE_CONFIG_PATH = Path(__file__).parent / "file_config.json"
DEFAULT_MAIN_GEOMETRY = "760x700"
DEFAULT_MAIN_MIN_SIZE = (680, 600)
DEFAULT_OUTPUT_GEOMETRY = "760x560"
DEFAULT_OUTPUT_MIN_SIZE = (680, 420)
DEFAULT_VALIDATION_OUTPUT = "../validation_results.json"
UI_FONT = ("TkDefaultFont", 12)
OUTPUT_FONT = ("TkDefaultFont", 13)


class CIMShaclGUI:
	"""GUI for running SHACL validations."""

	def __init__(self, root: Optional[tk.Tk] = None) -> None:
		self.datahandler: DataHandler = DataHandler()
		self.file_config: dict = load_json(FILE_CONFIG_PATH)
		self.root: tk.Tk = root or tk.Tk()
		self._configure_root_window()
		self._configure_styles()
		self._init_variables()
		self.tooltip: ToolTip = ToolTip(delay=400)
		self.validation_service: ShaclValidationService = ShaclValidationService()
		self._restore_format_from_file_config()

		self._build_gui()

	def run(self) -> None:
		"""Start the Tkinter main loop to run the GUI."""
		self.root.mainloop()
	
	def _configure_root_window(self) -> None:
		"""Configure the main window of the GUI."""
		self.root.title("CIM pySHACL GUI")
		self.root.geometry(DEFAULT_MAIN_GEOMETRY)
		self.root.minsize(*DEFAULT_MAIN_MIN_SIZE)

	def _configure_styles(self) -> None:
		"""Configure the various styles for the GUI."""
		self.style: ttk.Style = ttk.Style(self.root)
		self.style.configure("TLabel", font=UI_FONT)
		self.style.configure("TButton", font=UI_FONT)
		self.style.configure("TRadiobutton", font=UI_FONT)
		self.style.configure("TEntry", font=UI_FONT)
		self.style.configure("TCheckbutton", font=UI_FONT)

	def _init_variables(self) -> None:
		"""Initialize the Tkinter variables used in the GUI."""
		self.data_format: tk.StringVar = tk.StringVar(value="cimxml")
		self.shacl_format: tk.StringVar = tk.StringVar(value="ttl")
		self.data_var: tk.StringVar = tk.StringVar(value="No files selected")
		self.shacl_var: tk.StringVar = tk.StringVar(value="No files selected")
		self.rdfs_var: tk.StringVar = tk.StringVar(value="No files selected")
		self.datatype_var: tk.StringVar = tk.StringVar(value="If left empty a default context will be used")
		self.validation_output_path: tk.StringVar = tk.StringVar(value=DEFAULT_VALIDATION_OUTPUT)
		self.validation_output_format: tk.StringVar = tk.StringVar(value="json-ld")
		self.add_datatypes_var: tk.BooleanVar = tk.BooleanVar(value=False)
		self.custom_url_var: tk.StringVar = tk.StringVar()
		self.csv_report_var: tk.BooleanVar = tk.BooleanVar(value=False)

	def _restore_format_from_file_config(self) -> None:
		"""Restore the last used data and SHACL formats from the file configuration, if available."""
		if not self.file_config:
			return
		
		data_cfg: dict = self.file_config.get("data", {})
		data_format: str = data_cfg.get("format", "cimxml") if data_cfg else "cimxml"
		self.data_format.set(data_format)
		self.datahandler.data_format = data_format

		shacl_cfg: dict = self.file_config.get("shacl", {})
		shacl_format: str = shacl_cfg.get("format", "ttl") if shacl_cfg else "ttl"
		self.shacl_format.set(shacl_format)
		self.datahandler.shacl_format = shacl_format

	# Gui building methods

	def _build_gui(self) -> None:
		"""Build the GUI layout and components."""
		frame: ttk.Frame = ttk.Frame(self.root, padding=12)
		frame.grid(row=0, column=0, sticky="nsew")

		self.root.columnconfigure(0, weight=1)
		self.root.rowconfigure(0, weight=1)
		frame.columnconfigure(0, weight=1)

		row: int = 0

		# row gets incremented in the section methods so that the next section is placed correctly below the previous one.
		row = self._file_selection_section(frame, row, "Data", self.data_format, self.data_var, [("CIMXML", "cimxml"), ("RDF/XML", "xml"), ("JSON-LD", "json-ld"), ("TRIG", "trig"), ("TTL", "ttl")], self._select_data_files)
		row = self._file_selection_section(frame, row, "SHACL", self.shacl_format, self.shacl_var, [("TTL", "ttl"), ("RDF/XML", "xml")], self._select_shacl_file)
		row = self._add_collapsible_section(frame, row, "Add RDFS files", self._rdfs_section)
		row = self._add_collapsible_section(frame, row, "Datatype enrichment options", self._datatype_section)
		
		ttk.Button(frame, text="Check namespaces", command=self._show_namespace_report).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(15, 15))

		row = self._validation_output_section(frame, row + 1)

		ttk.Button(frame, text="Run SHACL validation", command=self._start_validation).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(15, 0))

	def _file_selection_section(self, frame: ttk.Frame, start_row: int, title: str, format_var: tk.StringVar, file_var: tk.StringVar, format_options: list[tuple[str, str]], select_command: Callable[[], None]) -> int:
		"""Build a file selection section with radiobuttons.
		
		Parameters:
			frame (ttk.Frame): The parent frame to build the section in.
			start_row (int): The row index to start placing the section components.
			title (str): The title of the section (e.g., "Data" or "SHACL").
			format_var (tk.StringVar): The StringVar to bind the selected format radiobuttons to.
			file_var (tk.StringVar): The StringVar to bind the selected file path to.
			format_options (list[tuple[str, str]]): A list of tuples containing the display text and value for each format option.
			select_command (Callable[[], None]): The command function to call when the "Browse" button is clicked.
		
		Returns:
			int: The next row index after the section components, to allow for correct placement of subsequent sections.
		"""
		row: int = start_row

		ttk.Label(frame, text=f"{title} files:").grid(row=row, column=0, sticky="w", pady=(10, 6))
		row = self._make_radio_group(frame, row +1, format_var, format_options)
		row = self._add_file_picker_row(frame, row, file_var, select_command)

		return row +1
		
	def _rdfs_section(self, frame: ttk.Frame, start_row: int) -> int:
		"""Build the RDFS file selection section.
		
		Parameters:
			frame (ttk.Frame): The parent frame to build the section in.
			start_row (int): The row index to start placing the section components.
		
		Returns:
			int: The next row index after the section components, to allow for correct placement of subsequent sections.
		"""
		row: int = start_row
		label = ttk.Label(frame, text="RDFS files (optional):")
		label.grid(row=row, column=0, sticky="w", pady=(10, 6))
		self.tooltip.attach(label, TOOLTIP_TEXTS["RDFS"])
		row = self._add_file_picker_row(frame, row+1, self.rdfs_var, self._select_rdfs_files)		
		return row +1

	def _datatype_section(self, frame: ttk.Frame, start_row: int) -> int:
		"""Build the datatype enrichment options section.
		
		Parameters:
			frame (ttk.Frame): The parent frame to build the section in.
			start_row (int): The row index to start placing the section components.

		Returns:
			int: The next row index after the section components, to allow for correct placement of subsequent sections.
		"""
		row: int = start_row

		check = ttk.Checkbutton(frame, text="Add datatypes", variable=self.add_datatypes_var)
		check.grid(row=row, column=0, sticky="w")
		self.tooltip.attach(check, TOOLTIP_TEXTS["ADD_DATATYPES"])
		ttk.Label(frame, text="Custom context file:").grid(row=row +1, column=0, sticky="w", pady=(10, 6))
		row = self._add_file_picker_row(frame, row +1, self.datatype_var, self._select_datatype_file)

		return row +1
	
	def _validation_output_section(self, frame: ttk.Frame, start_row: int) -> int:
		"""Build the validation output options section.
		
		Parameters:
			frame (ttk.Frame): The parent frame to build the section in.
			start_row (int): The row index to start placing the section components.

		Returns:
			int: The next row index after the section components, to allow for correct placement of subsequent sections.
		"""
		row: int = start_row

		ttk.Label(frame, text="Validation output file path:").grid(row=row +1, column=0, sticky="w", pady=(10, 6))
		row = self._make_radio_group(frame, row +2, self.validation_output_format, [("JSON-LD", "json-ld"), ("TTL", "ttl"), ("RDF/XML", "xml")])
		ttk.Entry(frame, textvariable=self.validation_output_path).grid(row=row +3, column=0, columnspan=2, sticky="ew", pady=(6, 6))

		check = ttk.Checkbutton(frame, text="CSV report", variable=self.csv_report_var)
		check.grid(row=row +4, column=0, sticky="w", pady=(10, 6))

		return row +5
	
	def _add_collapsible_section(self, frame: ttk.Frame, start_row: int, title: str, builder_fn: Callable[[ttk.Frame, int], int]) -> int:
		"""Add a collapsible section to the GUI and use the provided builder function to populate its content.
		
		Parameters:
			frame (ttk.Frame): The parent frame to build the section in.
			start_row (int): The row index to start placing the section components.
			title (str): The title of the collapsible section.
			builder_fn (Callable[[ttk.Frame, int], int]): A function that takes a ttk.Frame and a starting row index, builds the content of the section, and returns the next row index after the content.

		Returns:
			int: The next row index after the section components, to allow for correct placement of subsequent sections.
		"""
		section = CollapsibleSection(frame, title=title)
		section.grid(row=start_row, column=0, sticky="ew", pady=(10, 10))
		builder_fn(section.content, 0)
		return start_row + 1

	def _make_radio_group(self, frame: ttk.Frame, start_row: int, variable: tk.StringVar, options: list[tuple[str, str]]) -> int:
		"""Create a group of radiobuttons for selecting options.
		
		Parameters:
			frame (ttk.Frame): The parent frame to build the radio buttons in.
			start_row (int): The row index for the radio buttons.
			variable (tk.StringVar): The StringVar to bind the selected radio button value to.
			options (list[tuple[str, str]]): A list of tuples containing the display text and value for each radio button option.

		Returns:
			int: The next row index after the radio buttons, to allow for correct placement of subsequent components.
		"""
		radio_frame = ttk.Frame(frame)
		radio_frame.grid(row=start_row, column=0, columnspan=2, sticky="ew", pady=(0, 6))

		for text, value in options:
			ttk.Radiobutton(radio_frame, text=text, variable=variable, value=value).pack(side="left", padx=(0, 12))

		return start_row + 1

	def _add_file_picker_row(self, frame: ttk.Frame, start_row: int, value_var: tk.StringVar, command: Callable[[], None]) -> int:
		"""Add a file picker row with an entry displaying the selected file and a "Browse" button.
		
		Parameters:
			frame (ttk.Frame): The parent frame to build the file picker row in.
			start_row (int): The row index to start placing the file picker components.
			value_var (tk.StringVar): The StringVar to bind the selected file path to.
			command (Callable[[], None]): The function to call when the "Browse" button is clicked.

		Returns:
			int: The next row index after the file picker components, to allow for correct placement of subsequent components.
		"""
		ttk.Entry(frame, textvariable=value_var, state="readonly").grid(row=start_row, column=0, sticky="ew", padx=(0, 8))
		ttk.Button(frame, text="Browse", command=command).grid(row=start_row, column=1, sticky="ew")
		return start_row + 1


	# Data handling methods
	def _safe_execute(self, func: Callable, *, title: str) -> None:
		"""Helper method for safely executing a function that may raise exceptions, and showing an error message in the GUI if an exception occurs.
		
		The full exception stack will be logged.

		Parameters:
			func (Callable): The function to execute safely.
			title (str): The title to use for the error message box if an exception occurs.
		"""
		try:
			func()
		except Exception as e:
			logger.exception("Error occured when loading files.")
			self.root.after(0, lambda e=e: messagebox.showerror(title, str(e)))

	def _select_files_by(self, dataset: str) -> None:
		"""Generalized method for selecting files for a given dataset type using the configuration defined in DATASET_SELECTORS.
		
		Parameters:
			dataset (str): The dataset type key to select files for "data", "shacl", "rdfs" or "datatypes".
		"""
		try:
			dataset_config: DatasetConfig = DATASET_SELECTORS[dataset]
		except KeyError:
			return

		initial_dir: str = _load_dir_from_config(self.file_config, dataset_config.config_key)
		dialog: Callable[..., str | tuple[str, ...]] = filedialog.askopenfilenames if dataset_config.multiple else filedialog.askopenfilename		
		result: str | tuple[str, ...] = dialog(initialdir=initial_dir, title=dataset_config.title)

		if not result:
			return

		files: list[str]|str = list(result) if isinstance(result, tuple) else result

		if dataset_config.threaded:
			self._run_threaded(dataset, files, dataset_config)
		else:
			self._safe_execute(
				lambda: self._execute_selection(files, dataset_config),
				title=f"Error loading {dataset} files"
			)

	def _execute_selection(self, files: str | list[str], dataset_config: DatasetConfig) -> None:
		"""Execute the file selection logic for a given dataset type.
		
			- Load files with the correct loader via the DataHandler
			- Update the GUI variables
			- Save format choice and last directory in the file configuration
		
		Parameters:
			files (str | list[str]): The selected file path(s) as a string or list of strings. This cannot be None or empty.
			dataset_config (DatasetConfig): The configuration for the dataset type being processed.
		"""
		fmt: str|None = None

		if dataset_config.format_attr:
			fmt_getter: tk.StringVar = getattr(self, dataset_config.format_attr)
			fmt = fmt_getter.get()

		setter: Callable[..., None] = getattr(self.datahandler, dataset_config.set_method)
		if fmt is not None:
			setter(files, fmt)
		else:
			setter(files)

		var: tk.StringVar = getattr(self, dataset_config.var_attr)
		if isinstance(files, list) and len(files) > 1:
			var.set(f"{len(files)} files selected")
		else:
			var.set(files) if isinstance(files, str) else var.set(files[0])

		first = files[0] if isinstance(files, list) else files
		_save_config_info(self.file_config, first, dataset_config.config_key, fmt)

		getattr(self.datahandler, dataset_config.load_method)()	# Running the appropriate load method.


	def _run_threaded(self, dataset: str, files: str | list[str], dataset_config: DatasetConfig) -> None:
		"""Run the file selection and loading logic in a separate thread, showing a progress dialog while the loading is in progress.
		
		Parameters:
			dataset (str): The dataset type key to select files for "data", "shacl", "rdfs" or "datatypes".
			files (str | list[str]): The selected file path(s) as a string or list of strings. This cannot be None or empty.
			dataset_config (DatasetConfig): The configuration for the dataset type being processed.
		"""
		self.loading_window: ProgressTimerDialog = ProgressTimerDialog(
			self.root,
			title=dataset_config.loading_title,
			message=dataset_config.loading_message,
		)
		self.loading_window.start()

		def task():
			self._safe_execute(
				lambda: self._execute_selection(files, dataset_config),
				title=f"Error loading {dataset} files"
			)

		thread: threading.Thread = threading.Thread(target=task, daemon=True)
		thread.start()

		self._check_thread(thread)


	def _check_thread(self, thread: threading.Thread) -> None:
		"""Check if the background thread is still running, and if not, close the loading window.
		
		Parameters:
			thread (threading.Thread): The background thread to check.
		"""
		if thread.is_alive():
			self.root.after(100, lambda: self._check_thread(thread))
		else:
			self.loading_window.close()

	def _select_data_files(self):
		"""Handler for selecting data files."""
		self._select_files_by("data")

	def _select_shacl_file(self):
		"""Handler for selecting SHACL files."""
		self._select_files_by("shacl")

	def _select_rdfs_files(self):
		"""Handler for selecting RDFS files."""
		self._select_files_by("rdfs")

	def _select_datatype_file(self):
		"""Handler for selecting datatype context files."""
		self._select_files_by("datatypes")

	def _prepare_data_graph(self) -> None:
		"""Prepare the data graph for validation by applying any selected enrichment options."""
		if self.datahandler.data_graph is None:
			return
		
		context_data: dict | None = self.datahandler.datatypes if self.datahandler.datatype_file else None
		self.validation_service.prepare_data_for_validation(self.datahandler.data_graph, self.datahandler.rdfs_graph, add_datatypes=self.add_datatypes_var.get(), context_data=context_data)

	# Output methods

	def _show_output_message(self, message: str, tag_map: dict[str, str]|None = None) -> None:
		"""Helper method to show a message in the output text area of the validation dialog.
		
		Parameters:
			message (str): The message to display in the output area.
		"""
		self.output.config(state=tk.NORMAL)
		start_index: str = self.output.index(tk.END)
		self.output.insert(tk.END, message + "\n")
		if tag_map:
			self.tooltip.apply_to_text(self.output, start_index, tag_map)
		self.output.see(tk.END)
		self.output.config(state=tk.DISABLED)


	def _show_namespace_report(self) -> None: 
		"""Generate and display a report comparing the namespaces used in the data graphs, SHACL graphs and RDFS graphs."""
		graphs: dict[str, Graph|None] = {
			"data": self.datahandler.data_graph,
			"shacl": self.datahandler.shacl_graph
		}

		if self.datahandler.rdfs_graph is not None:
			graphs["rdfs"] = self.datahandler.rdfs_graph

		report: list[dict[str, str]] = compare_namespaces(graphs)

		if all_namespaces_match(report):
			messagebox.showinfo("Namespace Check", "✅ All namespaces match.")
			return

		matrix_text: str = format_namespace_matrix(report, list(graphs.keys()))

		win: tk.Toplevel = tk.Toplevel()
		win.title("Namespace Differences")
		text_area: scrolledtext.ScrolledText = scrolledtext.ScrolledText(win, wrap=tk.WORD, width=110, height=30, font=("Courier", 15), bg="#f0f0f0", fg="#202020", insertbackground="#202020", relief=tk.SUNKEN, borderwidth=2)
		text_area.insert(tk.END, matrix_text)
		text_area.config(state=tk.DISABLED)
		text_area.pack(padx=10, pady=10)

			
	def _start_validation(self) -> None:
		"""Start the SHACL validation process with a progressbar and timer."""
		self.validation_dialog: ProgressTimerDialog = ProgressTimerDialog(self.root, title="Running SHACL validation...", message="Large graphs may take a while")
		self.validation_dialog.start()
		self.validation_dialog.top.geometry(DEFAULT_OUTPUT_GEOMETRY)
		self.validation_dialog.top.minsize(*DEFAULT_OUTPUT_MIN_SIZE)

		frame: tk.Frame = tk.Frame(self.validation_dialog.top)
		frame.pack(fill="both", expand=True, padx=10, pady=10)
		self.output: tk.Text = tk.Text(frame, wrap=tk.WORD, font=OUTPUT_FONT, bg="#f0f0f0", fg="#202020", insertbackground="#202020", relief=tk.SUNKEN, borderwidth=2)
		self.output.pack(fill="both", pady=5)
		self.output.config(state=tk.DISABLED)

		try:
			self._prepare_data_graph()
			self._report_focus_nodes()
			self._process_shacl_validation_async()
		except Exception as e:
			self._show_output_message(f"An error occurred:\n {str(e)}")


	def _report_focus_nodes(self) -> None:
		"""Report the total number of shapes and how many have explicit focus nodes in the data graph."""
		summary: FocusNodeSummary | None = self.validation_service.calculate_focus_nodes(self.datahandler.data_graph, self.datahandler.shacl_graph)
		if summary is None:
			return

		tooltip_line = "Shapes with explicit focus nodes in graph"

		focus_message: str = (
			f"Total number of shapes: {summary.total_shapes}\n"
			f"{tooltip_line}: {summary.shapes_with_focus_nodes}\n"
		)
		self._show_output_message(focus_message, tag_map={tooltip_line: TOOLTIP_TEXTS["FOCUS_NODES"]})

	def _process_shacl_validation_async(self) -> None:
		"""Run the SHACL validation in a separate thread and use a queue to get the results back to the main thread."""
		self.validation_queue: queue.Queue = queue.Queue()

		def worker():

			try:
				result: ShaclValidationResult | None = self.validation_service.validate_graphs(
					self.datahandler.data_graph,
					self.datahandler.shacl_graph,
					self.datahandler.rdfs_graph
				)
				self.validation_queue.put(("done", result))

			except Exception as e:
				self.validation_queue.put(("error", e))

		threading.Thread(target=worker, daemon=True).start()
		self._check_validation_queue()


	def _check_validation_queue(self) -> None:
		"""Check the validation queue for results from the background validation thread, and update the GUI accordingly."""
		try:
			status, payload = self.validation_queue.get_nowait()

			if status == "done":
				self._on_validation_done(payload)
			else:
				self._on_validation_error(payload)

		except Exception:
			# nothing yet → check again in 100ms
			self.validation_dialog.top.after(100, self._check_validation_queue)


	def _on_validation_done(self, result: ShaclValidationResult | None) -> None:
		"""Handle the completion of the SHACL validation process, updating the GUI with results and saving output files as needed.
		
		Parameters:
			result (ShaclValidationResult | None): The result of the SHACL validation process, or None if validation could not be performed due to missing graphs.
		"""
		if hasattr(self, "validation_dialog") and self.validation_dialog:
			self.validation_dialog.stop()

		if result is None:
			self._show_output_message("Data graph or SHACL graph not loaded.")
			return

		self._report_basic_validation_results(result)
		self._report_validation_summary(result)
		self._output_validation_results_to_file(result)


	def _report_basic_validation_results(self, result: ShaclValidationResult) -> None:
		"""Report the basic results of the SHACL validation, including the number of triples in the data graph and whether the data conforms to the SHACL shapes.
		
		Parameters:
			result (ShaclValidationResult): The result of the SHACL validation process, containing information about the validation outcome and the results graph.
		"""
		graph_count: int = len(self.datahandler.data_graph) if self.datahandler.data_graph else 0

		self._show_output_message(f"SHACL validation completed on {graph_count} triples.")
		self._show_output_message(f"Conforms: {result.conforms}")
		self._show_output_message(" ")	# Add some spacing before the next section.

	def _report_validation_summary(self, result: ShaclValidationResult) -> None:
		"""Report the types of validation errors and their counts if any were found.
		
		Parameters:
			result (ShaclValidationResult): The result of the SHACL validation process, including a summary of validation results if violations were found.
		"""
		if not result.summary_validation_results:
			return
		
		message: str = "Summary of validation results (error type and count):\n"
		for error_type, count in result.summary_validation_results:
			message += f"{error_type}: {count}\n"

		self._show_output_message(message)

	def _output_validation_results_to_file(self, result: ShaclValidationResult) -> None:
		"""Output the validation results to a file in the selected format, and optionally save a CSV report of violations.
		
		If the result does not contain violations (i.e. triples with the predicate sh:result), no output file will be saved.

		Parameters:
			result (ShaclValidationResult): The result of the SHACL validation process, including the results graph with validation results that can be serialized to a file.
		"""
		result_graph: Graph | None = result.results_graph

		if result_graph is None or SH.result not in result_graph.predicates():
			return
		
		output_path: str = self.validation_output_path.get().strip() or DEFAULT_VALIDATION_OUTPUT
		output_format: str = self.validation_output_format.get()

		self._save_validation_results_to_graph(result_graph, output_path, output_format)

		if self.csv_report_var.get():
			self._save_csv_report(result_graph, output_path)


	def _save_validation_results_to_graph(self, result_graph: Graph, output_path: str, output_format: str) -> None:
		"""Save the validation results graph to a file in the specified format, and show a message in the GUI with the output path.
		
		Parameters:
			result_graph (Graph): The RDF graph containing the validation results to be saved.
			output_path (str): The file path where the validation results should be saved.
			output_format (str): The format in which to save the validation results (e.g., "json-ld", "ttl", "xml").
		"""
		saved: bool = self.validation_service.serialize_results(result_graph, output_path, output_format)
		if saved:
			self._show_output_message(f"Validation report saved to: {output_path}")


	def _save_csv_report(self, result_graph: Graph, output_path: str) -> None:
		"""Save a CSV report of SHACL violations extracted from the validation results graph, and show a message in the GUI with the CSV output path.
		
		Parameters:
			result_graph (Graph): The RDF graph containing the validation results from which to extract SHACL violations for the CSV report.
			output_path (str): The base file path where the CSV report should be saved (the .csv extension will be added automatically).
		"""
		csv_result: list[ConstraintViolation] = collect_violations(result_graph)
		csv_output_path: str = output_path.rsplit(".", 1)[0] + ".csv"
		write_shacl_violations_to_csv(csv_result, csv_output_path)
		self._show_output_message(f"Validation report saved as CSV to: {csv_output_path}")


	def _on_validation_error(self, error: Exception) -> None:
		"""Handle an error that occurred during the SHACL validation process, showing an error message in the GUI.
		
		Parameters:
			error (Exception): The exception that was raised during the validation process.
		"""
		if hasattr(self, "validation_dialog") and self.validation_dialog:
			self.validation_dialog.stop()

		self._show_output_message(f"An error occurred:\n{str(error)}")
		

	# Debugging methods kept in case they are needed again in the future, but not currently used in the GUI.

	def _graph_counts_for_debugging(self, top: tk.Toplevel) -> None:
		data_count: int = len(self.datahandler.data_graph) if self.datahandler.data_graph else 0
		rdfs_count: int = len(self.datahandler.rdfs_graph) if self.datahandler.rdfs_graph else 0
		shacl_count: int = len(self.datahandler.shacl_graph) if self.datahandler.shacl_graph else 0

		message: str = (
			f"Data Graph length: {data_count}\n"
			f"RDFS Graph length: {rdfs_count}\n"
			f"SHACL Graph length: {shacl_count}\n\n"
		)
		self._show_output_message(message)


def _save_config_info(file_config: dict[str, dict[str, str]], filestr: str, dataset: str, format: Optional[str] = None) -> None:
	"""Helper function to save the last used directory and format for a given dataset type (data, shacl, rdfs, datatypes) to the file configuration.
	
	Parameters:
		file_config (dict[str, dict[str, str]]): The current file configuration dictionary to update.
		filestr (str): The file path string from which to extract the directory to save in the config.
		dataset (str): The dataset type key to update in the config (e.g., "data", "shacl", "rdfs", "datatypes").
		format (Optional[str]): The format string to save in the config for the given dataset type. If None, the format will not be updated in the config.
	"""
	# Will recreate the file_config file the first time the gui is used, if it is accidentally deleted or corrupted
	if file_config is None:
		file_config = {}
	if not file_config.get(dataset):
		file_config[dataset] = {}

	if format:
		file_config[dataset]["format"] = format
	file_config[dataset]["last_directory"] = str(Path(filestr).parent)
	save_json(file_config, FILE_CONFIG_PATH)

def _load_dir_from_config(file_config: dict[str, dict[str, str]], dataset: str) -> str:
	"""Helper function to load the last used directory for a given dataset type from the file configuration.
	
	Parameters:
		file_config (dict[str, dict[str, str]]): The file configuration dictionary to read from.
		dataset (str): The dataset type key to look up in the config (e.g., "data", "shacl", "rdfs", "datatypes").

	Returns:
		str: The last used directory for the given dataset type if available in the config, otherwise the user's home directory.
	"""
	if file_config and dataset in file_config:
		return file_config[dataset].get("last_directory", str(Path.home()))
	return str(Path.home())



DATASET_SELECTORS: dict[str, DatasetConfig] = {
    "data": DatasetConfig(
        title="Select data files",
        config_key="data",
        multiple=True,
        var_attr="data_var",
        set_method="set_data_files",
        load_method="load_data_files",
        format_attr="data_format",
        threaded=True,
        loading_title="Loading data files...",
        loading_message="Large files may take a while",
    ),

    "shacl": DatasetConfig(
        title="Select shacl file",
        config_key="shacl",
        multiple=False,
        var_attr="shacl_var",
        set_method="set_shacl_file",
        load_method="load_shacl_file",
        format_attr="shacl_format",
    ),

    "rdfs": DatasetConfig(
        title="Select RDFS files",
        config_key="rdfs",
        multiple=True,
        var_attr="rdfs_var",
        set_method="set_rdfs_files",
        load_method="load_rdfs_files",

    ),

    "datatypes": DatasetConfig(
        title="Select context file for datatype enrichment",
        config_key="datatypes",
        multiple=False,
        var_attr="datatype_var",
        set_method="set_datatype_file",
        load_method="load_datatypes",
    ),
}

if __name__ == "__main__":
	print("GUI for SHACL validation")