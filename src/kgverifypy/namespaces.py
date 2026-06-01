from cim_plugin.namespaces import CGMES_CIM, CIM, EU, CGMES_EU
from rdflib import Graph


def align_namespaces(graph: Graph, context: dict) -> None:
    namespaces = graph.namespace_manager
    if namespaces.store.namespace("cim") == CGMES_CIM:
        context["@context"]["cim"] = CGMES_CIM

    if namespaces.store.namespace("eu") == CGMES_EU:
        context["@context"]["eu"] = CGMES_EU