"""Simple Tkinter GUI for selecting CIM/SHACL files and showing output."""

import tkinter as tk
from tkinter import filedialog, ttk
from rdflib import Graph
from kgverifypy.file_handling import make_ontology_graph, make_data_graph_from_cimxml, make_shacl_graph

class CIMShaclGUI:
	"""GUI for selecting multiple files and displaying a run summary."""

	def __init__(self) -> None:
		self.root = tk.Tk()
		self.root.title("CIM pySHACL GUI")
		self.data_files: list[str] = []
		self.rdfs_files: list[str] = []
		self.shacl_file: str = ""
		self.rdfs_graph: Graph | None = None
		self.data_graph: Graph | None = None
		self._build_ui()
		self.root.mainloop()

	def _build_ui(self) -> None:
		frame = ttk.Frame(self.root, padding=12)
		frame.grid(row=0, column=0, sticky="nsew")

		self.root.columnconfigure(0, weight=1)
		self.root.rowconfigure(0, weight=1)
		frame.columnconfigure(0, weight=1)

		ttk.Label(frame, text="data files:").grid(row=0, column=0, sticky="w", pady=(0, 6))
		self.data_var = tk.StringVar(value="No files selected")
		self.data_entry = ttk.Entry(frame, textvariable=self.data_var, state="readonly")
		self.data_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))
		ttk.Button(frame, text="Browse", command=self.select_data_files).grid(row=1, column=1, sticky="ew")

		ttk.Label(frame, text="rdfs files:").grid(row=2, column=0, sticky="w", pady=(10, 6))
		self.rdfs_var = tk.StringVar(value="No files selected")
		self.rdfs_entry = ttk.Entry(frame, textvariable=self.rdfs_var, state="readonly")
		self.rdfs_entry.grid(row=3, column=0, sticky="ew", padx=(0, 8))
		ttk.Button(frame, text="Browse", command=self.select_rdfs_files).grid(row=3, column=1, sticky="ew")

		ttk.Label(frame, text="shacl files:").grid(row=4, column=0, sticky="w", pady=(10, 6))
		self.shacl_var = tk.StringVar(value="No files selected")
		self.shacl_entry = ttk.Entry(frame, textvariable=self.shacl_var, state="readonly")
		self.shacl_entry.grid(row=5, column=0, sticky="ew", padx=(0, 8))
		ttk.Button(frame, text="Browse", command=self.select_shacl_file).grid(row=5, column=1, sticky="ew")

		run_btn = ttk.Button(frame, text="Run", command=self.run)
		run_btn.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(14, 0))

	def _select_files(self, title: str) -> list[str]:
		files = filedialog.askopenfilenames(title=title)
		return list(files)

	def select_data_files(self) -> None:
		files = self._select_files("Select data files")
		if files:
			self.data_files = files
			self.data_graph = make_data_graph_from_cimxml(self.data_files)
			self.data_var.set(f"{len(self.data_files)} files selected")

	def select_rdfs_files(self) -> None:
		files = self._select_files("Select rdfs files")
		if files:
			self.rdfs_files = files
			self.rdfs_graph = make_ontology_graph(self.rdfs_files)
			self.rdfs_var.set(f"{len(self.rdfs_files)} files selected")

	def select_shacl_file(self) -> None:
		file = filedialog.askopenfilename(title="Select shacl file")
		if file:
			self.shacl_file = file
			self.shacl_graph = make_shacl_graph(self.shacl_file)
			self.shacl_var.set("1 file selected")

	def run(self) -> None:
		data_count = len(self.data_graph) if self.data_graph else 0
		rdfs_count = len(self.rdfs_graph) if self.rdfs_graph else 0
		shacl_count = len(self.shacl_graph) if self.shacl_graph else 0

		top = tk.Toplevel(self.root)
		top.title("Run output")
		top.geometry("360x160")

		message = (
			f"Data Graph length: {data_count}\n"
			f"RDFS Graph length: {rdfs_count}\n"
			f"SHACL Graph length: {shacl_count}\n\n"
			f"Run: {data_count + rdfs_count} triples with {shacl_count} shapes"
		)
		ttk.Label(top, text=message, padding=12).pack(fill="both", expand=True)


def main() -> None:
	CIMShaclGUI()


if __name__ == "__main__":
	main()