from rdflib import Graph
from kgverifypy.file_handling import make_graphs_from, merge_trig_graphs, load_json
from typing import Callable, TypeVar

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