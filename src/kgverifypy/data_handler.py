from rdflib import Graph
from kgverifypy.file_handling import make_graphs_from, merge_trig_graphs, load_json
from typing import Callable, TypeVar, Optional
from dataclasses import dataclass

@dataclass(frozen=True)
class DatasetConfig:
    title: str  # Title to display in the UI file entry for the data
    config_key: str # Key to use when loading and saving the file path in the file_config
    multiple: bool  # Whether to allow multiple files to be selected
    var_attr: str   # Name of the StringVar attribute in the GUI to update with the selected file(s)
    set_method: str # Name of the method to call to set the file(s) in the DataHandler
    load_method: str # Name of the method to call to load the file(s) in the DataHandler
    format_attr: Optional[str] = None # Name of the attribute in the DataHandler to set the format
    threaded: bool = False # Whether to load the file(s) in a separate thread
    loading_title: str = "" # Title to display in the loading dialog when loading the file(s) in a separate thread
    loading_message: str = "" # Message to display in the loading dialog when loading the file(s) in a separate thread


T = TypeVar('T')

class DataHandler:
    def __init__(self) -> None:
        self.data_files: list[str] = []
        self.rdfs_files: list[str] = []
        self.shacl_file: str = ""
        self.datatype_file: str = ""

        self.data_format: str = "cimxml"
        self.shacl_format: str = "ttl"

        self.data_graph: Graph|None = None
        self.rdfs_graph: Graph|None = None
        self.shacl_graph: Graph|None = None
        self.datatypes: dict|None = None

    # Setters
    def set_data_files(self, files: list[str], format: str) -> None:
        self.data_files = files
        self.data_format = format

    def set_shacl_file(self, file: str, format: str) -> None:
        self.shacl_file = file
        self.shacl_format = format

    def set_rdfs_files(self, files: list[str]) -> None:
        self.rdfs_files = files

    def set_datatype_file(self, file: str) -> None:
        self.datatype_file = file

    # Loaders
    def load_data_files(self) -> None:
        if not self.data_files:
            self.data_graph = None
            return

        if self.data_format == "trig":
            self.data_graph = merge_trig_graphs(self.data_files)
        else:
            self.data_graph = make_graphs_from(self.data_files, format=self.data_format)


    def load_shacl_file(self) -> None:
        if not self.shacl_file:
            self.shacl_graph = None
            return

        self.shacl_graph = make_graphs_from(self.shacl_file, format=self.shacl_format)


    def load_rdfs_files(self) -> None:
        if not self.rdfs_files:
            self.rdfs_graph = None
            return

        self.rdfs_graph = make_graphs_from(self.rdfs_files, format="xml")


    def load_datatypes(self) -> None:
        if not self.datatype_file:
            self.datatypes = None
            return

        self.datatypes = load_json(self.datatype_file)



    def _load_multiple_graph_files(self, files: list[str], format: str) -> None | Graph:
        """Loads multiple graph files using different loaders based on the format.
        
        Parameters:
            files (list[str]): List of file paths to load.
            format (str): The format of the files to load.
        
        Returns:
            Graph|None: The merged graph if files are loaded, otherwise None.
        """
        if not files:
            return None
        if format == "trig":
            return merge_trig_graphs(files)
        else:            
            return make_graphs_from(files, format=format)


    def _load_file_with_loader(self, file: str, loader: Callable[..., T], **kwargs) -> T | None:
        """Loads a single file using a specified loader function.

        Parameters:
            file (str): The file path to load.
            loader (Callable[..., T]): The loader function to use.
            **kwargs: Additional keyword arguments to pass to the loader.

        Returns:
            T|None: The loaded data if the file is valid, otherwise None.
        """
        if file and file.strip():
            return loader(file, **kwargs)
        return None

    def load_files(self) -> None:
        """Loads all configured files into their respective graphs or data structures."""
        self.data_graph = self._load_multiple_graph_files(self.data_files, self.data_format)
        self.rdfs_graph = self._load_multiple_graph_files(self.rdfs_files, "xml")
        self.shacl_graph = self._load_file_with_loader(self.shacl_file, make_graphs_from, format=self.shacl_format)
        self.datatypes = self._load_file_with_loader(self.datatype_file, load_json)


if __name__ == "__main__":
    print("Data handler module.")