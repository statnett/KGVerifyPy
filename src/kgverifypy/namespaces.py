from kgraphpy.namespaces import CGMES_CIM, CIM, EU, CGMES_EU
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
    

if __name__ == "__main__":
    print("Namespace module for KGVerifyPy.")