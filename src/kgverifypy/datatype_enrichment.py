from rdflib import Graph
from kgraphpy.jsonld_utilities import load_json_from_url, extract_datatype_map, enrich_graph_datatypes, DEFAULT_CONTEXT_LINK
from kgverifypy.namespaces import align_cgmes_namespaces
from typing import Optional

def add_datatypes_from_context(graph: Graph, context_data: Optional[dict] = None) -> None:
    if graph is None or len(graph) == 0:
        return
    
    if context_data is None:
        context_data = load_json_from_url(DEFAULT_CONTEXT_LINK)
    
    align_cgmes_namespaces(graph, context_data)
    datatype_map = extract_datatype_map(context_data)
    enrich_graph_datatypes(graph, datatype_map)


if __name__ == "__main__":
    print("Datatype enrichment module.")