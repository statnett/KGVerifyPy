from rdflib import Graph
from pathlib import Path
from kgraphpy.graph import CIMGraph
from kgraphpy.utilities import load_graphs_from_cimxml
from typing import Sequence, Union

def make_graph_from(files: Union[str, Path, Sequence[Union[str, Path]]], format: str = "xml") -> Graph:
    if isinstance(files, (str, Path)):
        files = [files]

    g = Graph()
    for file in files:
        g.parse(file, format=format)
    
    return g


# Not used, but may be needed in the future if we want to do things that are done via a CIMProcessor.
# def make_data_graph_from_cimxml_old(files: Union[str, Path, Sequence[Union[str, Path]]]) -> Graph:
#     pr_list = load_graphs_from_cimxml(files)

#     data = Graph()
#     for pr in pr_list:
#         for prefix, namespace in pr.graph.namespace_manager.store.namespaces():
#             data.bind(prefix, namespace)
#         data += pr.graph

#     return data


if __name__ == "__main__":
    print("File handling module for KGVerifyPy.")
