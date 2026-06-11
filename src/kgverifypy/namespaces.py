from kgraphpy.namespaces import CGMES_CIM, CGMES_EU, STANDARD_NAMESPACES, PERSISTENT_NAMESPACES, CGMES_NAMESPACES
from rdflib import Graph, URIRef
import logging

logger = logging.getLogger("primary")


def align_cgmes_namespaces(graph: Graph, context: dict) -> None:
    """Align the namespaces in the context with those in the graph if they match CGMES namespaces.

    This allows the same context to be used for graphs with the CGMES exception namespaces (loaded from CIMXML files),
    as well as for graphs with the standard CIM and EU namespaces.

    CGMES namespaces:
        CGMES_CIM (prefix 'cim'): http://iec.ch/TC57/CIM100#
        CGMES_EU (prefix 'eu'): http://iec.ch/TC57/CIM100-EuropeanExtension/1/0#
    
    Parameters:
        graph (Graph): The RDFLib Graph containing the data and namespaces.
        context (dict): The JSON-LD context dictionary to be aligned. Expected to have a "@context" key with a dictionary value.
    """
    if not isinstance(context, dict) or not isinstance(context.get("@context"), dict):
        logger.error(f"Context has unexpected structure. No alignment performed.")
        return
    
    namespaces = graph.namespace_manager
    if namespaces.store.namespace("cim") == URIRef(CGMES_CIM):
        context["@context"]["cim"] = CGMES_CIM

    if namespaces.store.namespace("eu") == URIRef(CGMES_EU):
        context["@context"]["eu"] = CGMES_EU
    

def _get_ns_map(graph):
    return {str(ns): prefix for prefix, ns in graph.namespace_manager.namespaces()}


def compare_namespaces(graphs: dict[str, Graph | None]) -> list[dict]:
    """Compare the namespaces used in multiple RDFLib Graphs and generate a report.

    Example input:
    graphs = {
        "data": Graph,
        "rdfs": Graph (optional),
        "shacl": Graph
    }

    Parameters:
        graphs (dict): A dictionary mapping graph names to RDFLib Graph instances.

    Returns:        
        list: A list of dictionaries, each containing:
                - "uri": The namespace URI being compared.
                - "presence": A dictionary mapping graph names to the prefix used for the namespace, or None if not present.
                - "missing": A list of graph names where the namespace is missing.
    """

    ns_maps = {name: _get_ns_map(g) for name, g in graphs.items() if g is not None}

    all_uris = set().union(*(m.keys() for m in ns_maps.values()))

    report = []

    for uri in sorted(all_uris):
        row = {
            "uri": uri,
            "presence": {},
            "missing": []
        }

        for name, ns_map in ns_maps.items():
            if uri in ns_map:
                row["presence"][name] = ns_map[uri]
            else:
                row["presence"][name] = None
                row["missing"].append(name)

        report.append(row)

    return report




if __name__ == "__main__":
    print("Namespace module for KGVerifyPy.")