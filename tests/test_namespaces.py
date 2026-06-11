import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import NamespaceManager
from kgraphpy.namespaces import CGMES_CIM, CGMES_EU, CIM
from copy import deepcopy
from typing import Any
from src.kgverifypy.namespaces import align_cgmes_namespaces, compare_namespaces


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
    
# Unit tests compare_namespaces
def test_compare_namespaces_emptygraphs() -> None:
    graph1 = Graph()
    graph1.namespace_manager = NamespaceManager(graph1, "none")  # Clear any default namespaces
    
    graph2 = Graph()
    graph2.namespace_manager = NamespaceManager(graph2, "none")  # Clear any default namespaces
    
    report = compare_namespaces({"data": graph1, "shacl": graph2})
    assert report == []  # No namespaces, so empty report 


@pytest.mark.parametrize(
    "ns1, ns2, expected_missing",
    [
        pytest.param(("cim", CGMES_CIM), ("cim", CGMES_CIM), ([], []), id="Same namespace"),
        pytest.param(("cim", CGMES_CIM), ("cim", CIM), (["shacl"], ["data"]), id="Different namespaces, same prefix"),
        pytest.param(("cim", CGMES_CIM), ("cim2", CGMES_CIM), ([], []), id="Same namespace, different prefix"),
        pytest.param(("cim", CGMES_CIM), ("cim2", CIM), (["shacl"], ["data"]), id="Different namespaces, different prefix"),
    ]
)
def test_compare_namespaces_basic(ns1, ns2, expected_missing) -> None:
    graph1 = Graph()
    graph1.namespace_manager = NamespaceManager(graph1, "none")  # Clear any default namespaces
    graph1.bind(ns1[0], ns1[1])
    
    graph2 = Graph()
    graph2.namespace_manager = NamespaceManager(graph2, "none")  # Clear any default namespaces
    graph2.bind(ns2[0], ns2[1])
    
    report = compare_namespaces({"data": graph1, "shacl": graph2})

    for row in report:
        if row["uri"] == ns1[1]:
            assert row["presence"]["data"] == ns1[0]
            assert row["missing"] == expected_missing[0]
        elif row["uri"] == ns2[1]:
            assert row["presence"]["shacl"] == ns2[0]
            assert row["missing"] == expected_missing[1]

def test_compare_namespaces_threegraphs() -> None:
    graph1 = Graph()
    graph1.namespace_manager = NamespaceManager(graph1, "none")
    graph1.bind("cim", CGMES_CIM)

    graph2 = Graph()
    graph2.namespace_manager = NamespaceManager(graph2, "none")
    graph2.bind("cim", CIM)

    graph3 = Graph()
    graph3.namespace_manager = NamespaceManager(graph3, "none")
    graph3.bind("eu", CGMES_EU)

    report = compare_namespaces({"data": graph1, "shacl": graph2, "rdfs": graph3})
    
    assert all(isinstance(row["uri"], str) for row in report)  # URIs should be strings
    assert len(report) == 3
    assert report[0]["uri"] == CGMES_CIM
    assert report[0]["presence"]["data"] == "cim"
    assert report[0]["presence"]["shacl"] is None
    assert report[0]["presence"]["rdfs"] is None
    assert report[0]["missing"] == ["shacl", "rdfs"]
    assert report[1]["uri"] == CGMES_EU
    assert report[1]["presence"]["data"] is None
    assert report[1]["presence"]["shacl"] is None
    assert report[1]["presence"]["rdfs"] == "eu"
    assert report[1]["missing"] == ["data", "shacl"]
    assert report[2]["uri"] == CIM
    assert report[2]["presence"]["data"] is None
    assert report[2]["presence"]["shacl"] == "cim"
    assert report[2]["presence"]["rdfs"] is None
    assert report[2]["missing"] == ["data", "rdfs"]


def test_compare_namespaces_with_none_graph() -> None:
    graph1 = Graph()
    graph1.namespace_manager = NamespaceManager(graph1, "none")
    graph1.bind("cim", CGMES_CIM)

    report = compare_namespaces({"data": graph1, "shacl": None})

    assert len(report) == 1
    assert report[0]["presence"]["data"] == "cim"
    assert "shacl" not in report[0]["presence"]  # skipped entirely


def test_one_graph_empty_one_non_empty() -> None:
    g1 = Graph()
    g1.namespace_manager = NamespaceManager(g1, "none")

    g2 = Graph()
    g2.namespace_manager = NamespaceManager(g2, "none")
    g2.bind("cim", CGMES_CIM)

    report = compare_namespaces({"data": g1, "shacl": g2})

    assert len(report) == 1
    row = report[0]

    assert row["presence"]["data"] is None
    assert row["presence"]["shacl"] == "cim"
    assert row["missing"] == ["data"]

if __name__ == "__main__":
    pytest.main()