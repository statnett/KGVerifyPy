import pytest
from rdflib import Graph, URIRef
from kgraphpy.namespaces import CGMES_CIM, CGMES_EU, CIM
from copy import deepcopy
from typing import Any
from src.kgverifypy.namespaces import align_cgmes_namespaces


# Unit tests align_cgmes_namespaces
def test_cgmes_namespaces_are_as_expected() -> None:
    # Sanity check that the CGMES namespaces are what we expect
    assert CGMES_CIM == "http://iec.ch/TC57/CIM100#"
    assert CGMES_EU == "http://iec.ch/TC57/CIM100-EuropeanExtension/1/0#"

def test_align_cgmes_namespaces_emptycontext() -> None:
    graph = Graph()
    graph.bind("cim", CGMES_CIM)
    graph.bind("eu", CGMES_EU)

    context = {"@context": {}}
    align_cgmes_namespaces(graph, context)

    # The prefixes are added if they don't exist in the context
    assert context["@context"]["cim"] == CGMES_CIM
    assert context["@context"]["eu"] == CGMES_EU


def test_align_cgmes_namespaces_differentnamespace() -> None:
    graph = Graph()
    graph.bind("cim", CGMES_CIM)
    graph.bind("eu", CGMES_EU)
    graph.add((CGMES_CIM.Subject, CGMES_EU.Predicate, CGMES_CIM.Object))

    context = {"@context": {
        "cim": "http://example.com/other/cim",
        "eu": f"{CGMES_EU}",
        "foo": "http://example.com/foo",
        "cim:localname": {"@id": "cim:localname", "@type": "@id"}
    }}
    align_cgmes_namespaces(graph, context)

    assert context["@context"]["cim"] == CGMES_CIM  # Cim was corrected
    assert context["@context"]["eu"] == CGMES_EU    # Eu was already correct
    assert context["@context"]["foo"] == "http://example.com/foo"   # Other namespaces are untouched
    assert context["@context"]["cim:localname"] == {"@id": "cim:localname", "@type": "@id"}  # Localname is untouched
    # The graph is unchanged
    assert graph.namespace_manager.store.namespace("cim") == URIRef(CGMES_CIM)
    assert graph.namespace_manager.store.namespace("eu") == URIRef(CGMES_EU)
    assert (CGMES_CIM.Subject, CGMES_EU.Predicate, CGMES_CIM.Object) in graph

def test_align_cgmes_namespaces_unexpectedcontextstructure(caplog: pytest.LogCaptureFixture) -> None:
    graph = Graph()
    graph.bind("cim", CGMES_CIM)
    graph.bind("eu", CGMES_EU)

    context = {"context": {
        "cim": "http://example.com/other/cim",
        "foo": "http://example.com/foo"
    }}
    align_cgmes_namespaces(graph, context)

    assert context["context"]["cim"] == "http://example.com/other/cim"  # No correction
    assert context["context"]["foo"] == "http://example.com/foo"
    assert "Context has unexpected structure. No alignment performed." in caplog.text

@pytest.mark.parametrize("context", [
    pytest.param(None, id="None context"),
    pytest.param("@context", id="String context"),
    pytest.param({"@context": "not a dict"}, id="Content not a dict"),
    pytest.param({"@context": None}, id="None value"),
])
def test_align_cgmes_namespaces_nochanges(context: Any, caplog: pytest.LogCaptureFixture) -> None:
    graph = Graph()
    graph.bind("cim", CGMES_CIM)
    graph.bind("eu", CGMES_EU)

    old_context = deepcopy(context) if isinstance(context, dict) else context

    # Pylance silenced to test wrong input type
    align_cgmes_namespaces(graph, context)  # type: ignore

    assert context == old_context  # Context should be unchanged
    assert "Context has unexpected structure. No alignment performed." in caplog.text
    
def test_align_cgmes_namespaces_graphnotmatching() -> None:
    graph = Graph()
    graph.bind("cim", CIM)

    context = {"@context": {
        "cim": "http://example.com/other/cim",
        "foo": "http://example.com/foo"
    }}
    align_cgmes_namespaces(graph, context)

    # No changes when graph does not match CGMES namespaces
    assert context["@context"]["cim"] == "http://example.com/other/cim"
    assert context["@context"]["foo"] == "http://example.com/foo"

def test_align_cgmes_namespaces_nestedcontext() -> None:
    graph = Graph()
    graph.bind("cim", CGMES_CIM)
    graph.bind("eu", CGMES_EU)

    context = {"@context": {"nested": {"cim": "https://example.com/cim"}}}
    align_cgmes_namespaces(graph, context)

    # Top level prefixes are added, but nested contexts are not modified
    assert context == {"@context": {
        "cim": f"{CGMES_CIM}",
        "eu": f"{CGMES_EU}",
        "nested": {"cim": "https://example.com/cim"}
        }}
    

if __name__ == "__main__":
    pytest.main()