"""Tkinter GUI for running SHACL validations."""

import tkinter as tk
from tkinter import filedialog, ttk, messagebox, scrolledtext
import threading
import queue
from typing import Callable, Optional
from pathlib import Path
from rdflib.namespace import SH
from kgverifypy.file_handling import load_json, save_json
from kgverifypy.validation_service import ShaclValidationService
from kgverifypy.csv_utilities import collect_violations, write_shacl_violations_to_csv
from kgverifypy.data_handler import DataHandler
from kgverifypy.namespaces import compare_namespaces, all_namespaces_match, format_namespace_matrix
from kgverifypy.gui_utilites import CollapsibleSection, ProgressTimerDialog, safe_gui_call, safe_gui_thread

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
		self.datahandler = DataHandler()
		self.file_config = load_json(FILE_CONFIG_PATH)
		self.root = root or tk.Tk()
		self._configure_root_window()
		self._configure_styles()
		self._init_variables()
		self.validation_service = ShaclValidationService()
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
		self.style = ttk.Style(self.root)
		self.style.configure("TLabel", font=UI_FONT)
		self.style.configure("TButton", font=UI_FONT)
		self.style.configure("TRadiobutton", font=UI_FONT)
		self.style.configure("TEntry", font=UI_FONT)
		self.style.configure("TCheckbutton", font=UI_FONT)

	def _init_variables(self) -> None:
		"""Initialize the Tkinter variables used in the GUI."""
		self.data_format = tk.StringVar(value="cimxml")
		self.shacl_format = tk.StringVar(value="ttl")
		self.data_var = tk.StringVar(value="No files selected")
		self.shacl_var = tk.StringVar(value="No files selected")
		self.rdfs_var = tk.StringVar(value="No files selected")
		self.datatype_var = tk.StringVar(value="If left empty a default context will be used")
		self.validation_output_path = tk.StringVar(value=DEFAULT_VALIDATION_OUTPUT)
		self.validation_output_format = tk.StringVar(value="json-ld")
		self.add_datatypes_var = tk.BooleanVar(value=False)
		self.custom_url_var = tk.StringVar()
		self.csv_report_var = tk.BooleanVar(value=False)

	def _restore_format_from_file_config(self) -> None:
		"""Restore the last used data and SHACL formats from the file configuration, if available."""
		if not self.file_config:
			return
		
		data_cfg = self.file_config.get("data", {})
		data_format = data_cfg.get("format", "cimxml") if data_cfg else "cimxml"
		self.data_format.set(data_format)
		self.datahandler.data_format = data_format

		shacl_cfg = self.file_config.get("shacl", {})
		shacl_format = shacl_cfg.get("format", "ttl") if shacl_cfg else "ttl"
		self.shacl_format.set(shacl_format)
		self.datahandler.shacl_format = shacl_format

	# Gui building methods

	def _build_gui(self) -> None:
		"""Build the GUI layout and components."""
		frame = ttk.Frame(self.root, padding=12)
		frame.grid(row=0, column=0, sticky="nsew")

		self.root.columnconfigure(0, weight=1)
		self.root.rowconfigure(0, weight=1)
		frame.columnconfigure(0, weight=1)

		row = 0

		# row gets incremented in the section methods so that the next section is placed correctly below the previous one.
		row = self._file_selection_section(frame, row, "Data", self.data_format, self.data_var, [("CIMXML", "cimxml"), ("RDF/XML", "xml"), ("JSON-LD", "json-ld"), ("TRIG", "trig"), ("TTL", "ttl")], self.select_data_files)
		row = self._file_selection_section(frame, row, "SHACL", self.shacl_format, self.shacl_var, [("TTL", "ttl"), ("RDF/XML", "xml")], self.select_shacl_file)
		row = self._add_collapsible_section(frame, row, "Add RDFS files", self._rdfs_section)
		row = self._add_collapsible_section(frame, row, "Datatype enrichment options", self._datatype_section)
		
		ttk.Button(frame, text="Check namespaces", command=self.show_namespace_report).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(15, 15))

		row = self._validation_output_section(frame, row + 1)

		ttk.Button(frame, text="Run SHACL validation", command=self.start_validation).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(15, 0))

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
		row = start_row

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
		row = start_row
		row = self._add_file_picker_row(frame, row, self.rdfs_var, self.select_rdfs_files)		
		return row +1

	def _datatype_section(self, frame: ttk.Frame, start_row: int) -> int:
		"""Build the datatype enrichment options section.
		
		Parameters:
			frame (ttk.Frame): The parent frame to build the section in.
			start_row (int): The row index to start placing the section components.

		Returns:
			int: The next row index after the section components, to allow for correct placement of subsequent sections.
		"""
		row = start_row

		check = ttk.Checkbutton(frame, text="Add datatypes", variable=self.add_datatypes_var)
		check.grid(row=row, column=0, sticky="w")
		
		ttk.Label(frame, text="Custom context file:").grid(row=row +1, column=0, sticky="w", pady=(10, 6))
		row = self._add_file_picker_row(frame, row +1, self.datatype_var, self.select_datatype_file)

		return row +1
	
	def _validation_output_section(self, frame: ttk.Frame, start_row: int) -> int:
		"""Build the validation output options section.
		
		Parameters:
			frame (ttk.Frame): The parent frame to build the section in.
			start_row (int): The row index to start placing the section components.

		Returns:
			int: The next row index after the section components, to allow for correct placement of subsequent sections.
		"""
		row = start_row

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

	def _save_config_info(self, filestr: str, dataset: str, format: Optional[str] = None) -> None:
		if format:
			self.file_config[dataset]["format"] = format
		self.file_config[dataset]["last_directory"] = str(Path(filestr).parent)
		save_json(self.file_config, FILE_CONFIG_PATH)

	def _load_dir_from_config(self, dataset: str) -> str:
		if self.file_config and dataset in self.file_config:
			return self.file_config[dataset].get("last_directory", str(Path.home()))
		return str(Path.home())
	
	def _check_thread(self, thread: threading.Thread) -> None:
		if thread.is_alive():
			self.root.after(100, lambda: self._check_thread(thread))
		else:
			self.loading_window.close()

	@safe_gui_thread(title="Error loading data files")
	def _load_data_files_thread(self):
		self.datahandler.load_data_files()
		
	def select_data_files(self) -> None:
		initial_dir = self._load_dir_from_config("data")
		files = filedialog.askopenfilenames(initialdir=initial_dir, title="Select data files")
		
		if not files:
			return
		
		filelist = list(files)
		self.datahandler.data_files = filelist
		self.data_var.set(f"{len(self.datahandler.data_files)} files selected")
		self.datahandler.data_format = self.data_format.get()
		self._save_config_info(filelist[0], "data", self.data_format.get())

		self.loading_window = ProgressTimerDialog(self.root, title="Loading data files...", message="Large files may take a while")
		self.loading_window.start()
		thread = threading.Thread(target=self._load_data_files_thread, daemon=True)
		thread.start()
		self._check_thread(thread)

	@safe_gui_call(title="Error loading SHACL file")
	def select_shacl_file(self) -> None:
		initial_dir = self._load_dir_from_config("shacl")
		file = filedialog.askopenfilename(initialdir=initial_dir, title="Select shacl file")
		if file:
			self.datahandler.shacl_file = file
			self.shacl_var.set(file)
			self.datahandler.shacl_format = self.shacl_format.get()
			self._save_config_info(file, "shacl", self.shacl_format.get())
			self.datahandler.load_shacl_file()

	@safe_gui_call(title="Error loading RDFS files")
	def select_rdfs_files(self) -> None:
		initial_dir = self._load_dir_from_config("rdfs")
		files = filedialog.askopenfilenames(initialdir=initial_dir, title="Select RDFS files")
		if files:
			filelist = list(files)
			self.datahandler.rdfs_files = filelist
			self.rdfs_var.set(f"{len(self.datahandler.rdfs_files)} files selected")
			self._save_config_info(filelist[0], "rdfs")
			self.datahandler.load_rdfs_files()

	@safe_gui_call(title="Error loading datatype context file")
	def select_datatype_file(self) -> None:
		initial_dir = self._load_dir_from_config("datatypes")
		file = filedialog.askopenfilename(initialdir=initial_dir, title="Select context file for datatype enrichment")
		if file:
			self.datahandler.datatype_file = file
			self.datatype_var.set(file)
			self._save_config_info(file, "datatypes")
			self.datahandler.load_datatypes()

	def _prepare_data_graph(self) -> None:
		if self.datahandler.data_graph is None:
			return
		
		context_data = self.datahandler.datatypes if self.datahandler.datatype_file else None
		self.validation_service.prepare_data_for_validation(self.datahandler.data_graph, self.datahandler.rdfs_graph, add_datatypes=self.add_datatypes_var.get(), context_data=context_data)

	# Output methods

	def _show_output_message(self, message: str) -> None:
		self.output.config(state=tk.NORMAL)
		self.output.insert(tk.END, message + "\n")
		self.output.see(tk.END)
		self.output.config(state=tk.DISABLED)


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

		text_area = scrolledtext.ScrolledText(win, wrap=tk.WORD, width=110, height=30, font=("Courier", 15), bg="#f0f0f0", fg="#202020", insertbackground="#202020", relief=tk.SUNKEN, borderwidth=2)
		text_area.insert(tk.END, matrix_text)
		text_area.config(state=tk.DISABLED)
		text_area.pack(padx=10, pady=10)

			
	def _report_focus_nodes(self) -> None:
		summary = self.validation_service.summarize_focus_nodes(self.datahandler.data_graph, self.datahandler.shacl_graph)
		if summary is None:
			return

		focus_message = (
			f"Total number of shapes: {summary.total_shapes}\n"
			f"Shapes with explicit focus nodes in graph: {summary.shapes_with_focus_nodes}\n"
		)
		self._show_output_message(focus_message)


	def start_validation(self) -> None:
		self.validation_dialog = ProgressTimerDialog(self.root, title="Running SHACL validation...", message="Large graphs may take a while")
		self.validation_dialog.start()
		self.validation_dialog.top.geometry(DEFAULT_OUTPUT_GEOMETRY)
		self.validation_dialog.top.minsize(*DEFAULT_OUTPUT_MIN_SIZE)

		frame = tk.Frame(self.validation_dialog.top)
		frame.pack(fill="both", expand=True, padx=10, pady=10)
		self.output = tk.Text(frame, wrap=tk.WORD, font=OUTPUT_FONT, bg="#f0f0f0", fg="#202020", insertbackground="#202020", relief=tk.SUNKEN, borderwidth=2)
		self.output.pack(fill="both", pady=5)
		self.output.config(state=tk.DISABLED)

		try:
			self._prepare_data_graph()
			self._report_focus_nodes()
			self._process_shacl_validation_async()
		except Exception as e:
			self._show_output_message(f"An error occurred:\n {str(e)}")


	def _check_validation_queue(self):
		try:
			status, payload = self.validation_queue.get_nowait()

			if status == "done":
				self._on_validation_done(payload)
			else:
				self._on_validation_error(payload)

		except Exception:
			# nothing yet → check again in 100ms
			self.validation_dialog.top.after(100, self._check_validation_queue)

	def _process_shacl_validation_async(self):
		self.validation_queue = queue.Queue()

		def worker():

			try:
				result = self.validation_service.validate_graphs(
					self.datahandler.data_graph,
					self.datahandler.shacl_graph,
					self.datahandler.rdfs_graph
				)
				self.validation_queue.put(("done", result))

			except Exception as e:
				self.validation_queue.put(("error", e))

		threading.Thread(target=worker, daemon=True).start()
		self._check_validation_queue()


	def _on_validation_done(self, result):

		if hasattr(self, "validation_dialog") and self.validation_dialog:
			self.validation_dialog.stop()

		if result is None:
			self._show_output_message("Data graph or SHACL graph not loaded.")
			return

		graph_count = len(self.datahandler.data_graph) if self.datahandler.data_graph else 0

		self._show_output_message(f"SHACL validation completed on {graph_count} triples.")
		self._show_output_message(f"Conforms: {result.conforms}")
		self._show_output_message(" ")	# Add some spacing before summary of results.

		if result.summary_validation_results:
			message = "Summary of validation results (error type and count):\n"
			for error_type, count in result.summary_validation_results:
				message += f"{error_type}: {count}\n"
			self._show_output_message(message)

		if result.results_graph is not None and SH.result in result.results_graph.predicates():
			output_path = self.validation_output_path.get().strip() or DEFAULT_VALIDATION_OUTPUT
			output_format = self.validation_output_format.get()

			saved = self.validation_service.serialize_results(result.results_graph, output_path, output_format)
			if saved:
				self._show_output_message(f"Validation report saved to: {output_path}")

			if self.csv_report_var.get():
				csv_result = collect_violations(result.results_graph)
				csv_output_path = output_path.rsplit(".", 1)[0] + ".csv"
				write_shacl_violations_to_csv(csv_result, csv_output_path)
				self._show_output_message(f"Validation report saved as CSV to: {csv_output_path}")

	def _on_validation_error(self, error):
		if hasattr(self, "validation_dialog") and self.validation_dialog:
			self.validation_dialog.stop()

		self._show_output_message(f"An error occurred:\n{str(error)}")
		
	# Debugging methods kept in case they are needed again in the future, but not currently used in the GUI.

	def _graph_counts_for_debugging(self, top: tk.Toplevel) -> None:
		data_count = len(self.datahandler.data_graph) if self.datahandler.data_graph else 0
		rdfs_count = len(self.datahandler.rdfs_graph) if self.datahandler.rdfs_graph else 0
		shacl_count = len(self.datahandler.shacl_graph) if self.datahandler.shacl_graph else 0

		message = (
			f"Data Graph length: {data_count}\n"
			f"RDFS Graph length: {rdfs_count}\n"
			f"SHACL Graph length: {shacl_count}\n\n"
		)
		self._show_output_message(message)



if __name__ == "__main__":
	print("GUI for SHACL validation")