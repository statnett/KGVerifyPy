from rdflib import Graph
from pathlib import Path
from kgraphpy.utilities import load_graphs_from_cimxml
from typing import Sequence

def make_ontology_graph(files: Sequence[str|Path]) -> Graph:
    g = Graph()
    for file in files:
        g.parse(file, format="xml")
    return g

def make_data_graph_from_cimxml(files: Sequence[str|Path]) -> Graph:
    pr_list = load_graphs_from_cimxml(files)

    data = Graph()
    for pr in pr_list:
        for prefix, namespace in pr.graph.namespace_manager.store.namespaces():
            data.bind(prefix, namespace)
        data += pr.graph

    return data

def make_shacl_graph(file: str|Path) -> Graph:
    g = Graph()
    g.parse(file, format="ttl")
    return g

if __name__ == "__main__":
    print("File handling module for KGVerifyPy.")
