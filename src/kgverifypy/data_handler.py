from rdflib import Graph
from kgverifypy.file_handling import make_graphs_from, merge_trig_graphs, load_json, save_json

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

    def load_files(self) -> None:
        if self.data_files:
            if self.data_format == "trig":
                self.data_graph = merge_trig_graphs(self.data_files)
            else:
                self.data_graph = make_graphs_from(self.data_files, format=self.data_format)
        else:
            self.data_graph = None

        if self.rdfs_files:
            self.rdfs_graph = make_graphs_from(self.rdfs_files, format="xml")
        else:
            self.rdfs_graph = None

        if self.shacl_file:
            self.shacl_graph = make_graphs_from(self.shacl_file, format=self.shacl_format)
        else:
            self.shacl_graph = None

        if self.datatype_file:
            self.datatypes = load_json(self.datatype_file)
        else:
            self.datatypes = None


if __name__ == "__main__":
    print("Data handler module.")