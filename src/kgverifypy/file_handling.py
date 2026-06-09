import os
from rdflib import Graph, Dataset
from pathlib import Path
from typing import Sequence, Union
import json
import logging

logger = logging.getLogger("primary")

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


def load_json(json_file_path: str | Path) -> dict:
    """Load data from a json file and return it as a dictionary.
    
    Parameters:
        json_file_path (str|Path): The path to the JSON file.
    Returns:
        dict: The data loaded from the JSON file.
    """
    if os.path.exists(json_file_path) and os.path.isfile(json_file_path):
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    else:
        logger.error(f"JSON file not found: {json_file_path}")
        return {}

def save_json(data: dict, json_file_path: str | Path) -> None:
    """Save a dictionary as a JSON file.
    
    Parameters:
        data (dict): The data to save as JSON.
        json_file_path (str|Path): The path to the JSON file where the data should be saved.
    """
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)



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
