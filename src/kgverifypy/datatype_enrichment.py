from rdflib import Graph
from kgraphpy.jsonld_utilities import load_json_from_url, extract_datatype_map, enrich_graph_datatypes, DEFAULT_CONTEXT_LINK
from kgverifypy.namespaces import align_cgmes_namespaces
from typing import Optional

def add_datatypes_from_context(graph: Graph, context_url: Optional[str] = None) -> None:
    if context_url is None:
        context_url = DEFAULT_CONTEXT_LINK

    context_data = load_json_from_url(context_url)
    align_cgmes_namespaces(graph, context_data)
    datatype_map = extract_datatype_map(context_data)
    enrich_graph_datatypes(graph, datatype_map)


