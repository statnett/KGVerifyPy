from rdflib import Graph, Dataset
from pathlib import Path
from kgraphpy.graph import CIMGraph
from kgraphpy.utilities import load_graphs_from_cimxml
from typing import Sequence, Union

def make_graphs_from(files: Union[str, Path, Sequence[Union[str, Path]]], format: str = "xml") -> Graph:
    """Create a Graph from one or more files.
    
    Parameters:
        files (str|Path|Sequence[str|Path]): One or more file paths to load into the graph.
        format (str): The format to use when parsing the files. Default is "xml".

    Returns:
        Graph: A Graph containing the data from the provided files.
    """
    if isinstance(files, (str, Path)):
        files = [files]

    g = Graph()
    for file in files:
        g.parse(file, format=format)
    
    return g


def merge_trig_graphs(files: Union[str, Path, Sequence[Union[str, Path]]]) -> Graph:
    """Merge multiple TriG files into a single Graph.

    If any of the files contain more than one graph, the resulting graph will contain 
    all of the triples from all of the graphs in all of the files.
    
    Parameters:
        files (str|Path|Sequence[str|Path]): One or more file paths to load into the graph.

    Returns:
        Graph: A Graph containing the merged data from the provided TriG files.
    """
    if isinstance(files, (str, Path)):
        files = [files]

    ds = Dataset()
    for file in files:
        ds.parse(file, format="trig")
    
    g = Graph()
    for prefix, namespace in ds.namespace_manager.store.namespaces():
        g.bind(prefix, namespace)
    for graph in ds.graphs():
        g += graph

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
