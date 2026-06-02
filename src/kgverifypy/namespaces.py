from kgraphpy.namespaces import CGMES_CIM, CIM, EU, CGMES_EU
from rdflib import Graph, URIRef


def align_cgmes_namespaces(graph: Graph, context: dict) -> None:
    namespaces = graph.namespace_manager
    if namespaces.store.namespace("cim") == URIRef(CGMES_CIM):
        context["@context"]["cim"] = CGMES_CIM

    if namespaces.store.namespace("eu") == URIRef(CGMES_EU):
        context["@context"]["eu"] = CGMES_EU