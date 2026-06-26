import pytest
from rdflib import Graph, URIRef
from kgraphpy.namespaces import CGMES_CIM, CGMES_EU, CIM
from copy import deepcopy
from typing import Any
from src.kgverifypy.namespaces import align_cgmes_namespaces, compare_namespaces, all_namespaces_match, format_namespace_matrix


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
@pytest.mark.parametrize(
    "ns_map, expected_report", 
    [
        pytest.param({}, [], id="Empty namespace map"),
        pytest.param({"data": {}, "shacl": {}}, [], id="Two empty graphs"),
        pytest.param(
            {"data": {CGMES_CIM: "cim"}, "shacl": {}}, 
            [{"uri": CGMES_CIM, "presence": {"data": "cim", "shacl": None}, "missing": ["shacl"]}], 
            id="One graph with namespace, one empty"),
    ]
)
def test_compare_namespaces_emptyinput(ns_map: dict[str, dict[str, str]], expected_report: list) -> None:
    report = compare_namespaces(ns_map)
    assert report == expected_report


@pytest.mark.parametrize(
    "ns1, ns2, expected_missing",
    [
        pytest.param(("cim", CGMES_CIM), ("cim", CGMES_CIM), ([], []), id="Same namespace"),
        pytest.param(("cim", CGMES_CIM), ("cim", CIM), (["shacl"], ["data"]), id="Different namespaces, same prefix"),
        pytest.param(("cim", CGMES_CIM), ("cim2", CGMES_CIM), ([], []), id="Same namespace, different prefix"),
        pytest.param(("cim", CGMES_CIM), ("cim2", CIM), (["shacl"], ["data"]), id="Different namespaces, different prefix"),
    ]
)
def test_compare_namespaces_basic(ns1: tuple[str, str], ns2: tuple[str, str], expected_missing: tuple[list[str], list[str]]) -> None:
    
    ns_map = {
        "data": {ns1[1]: ns1[0]},
        "shacl": {ns2[1]: ns2[0]}
    }
    report = compare_namespaces(ns_map)

    for row in report:
        if row["uri"] == ns1[1]:
            assert row["presence"]["data"] == ns1[0]
            assert row["missing"] == expected_missing[0]
        elif row["uri"] == ns2[1]:
            assert row["presence"]["shacl"] == ns2[0]
            assert row["missing"] == expected_missing[1]

def test_compare_namespaces_threegraphs() -> None:
    ns_maps = {
        "data": {str(CGMES_CIM): "cim"},
        "shacl": {str(CIM): "cim"},
        "rdfs": {str(CGMES_EU): "eu"}
    }

    report = compare_namespaces(ns_maps)
    
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


def test_compare_namespaces_withnonegraph() -> None:
    ns_map = {"data": {"cim": CGMES_CIM}, "shacl": None}

    with pytest.raises(AttributeError):
        report = compare_namespaces(ns_map)

        assert report is None  # Report should not be generated due to the error


# Unit tests all_namespaces_match
def test_all_namespaces_match() -> None:
    report = []
    assert all_namespaces_match(report) is True

    report = [
        {"uri": "http://example.org/ns1", "missing": []},
        {"uri": "http://example.org/ns2", "missing": []}
    ]
    assert all_namespaces_match(report) is True

    report_with_missing = [
        {"uri": "http://example.org/ns1", "missing": []},
        {"uri": "http://example.org/ns2", "missing": ["graph1"]}
    ]
    assert all_namespaces_match(report_with_missing) is False

# Unit tests format_namespace_matrix
def test_format_namespace_matrix_basic():
    report = [
        {
            "uri": "ns1",
            "missing": True,
            "presence": {"g1": "p1"}
        },
        {
            "uri": "ns2",
            "missing": True,
            "presence": {}
        },
    ]
    graph_names = ["g1", "g2"]

    result = format_namespace_matrix(report, graph_names)

    expected = (
        "Namespace |     G1     |     G2    \n"
        "-----------------------------------\n"
        "ns1 |    ✔ p1    |     ✘     \n"
        "ns2 |     ✘      |     ✘     "
    )

    assert result == expected


def test_format_namespace_matrix_notmissing():
    report = [
        {
            "uri": "ns1",
            "missing": ["g2"],
            "presence": {"g1": "p1"}
        },
        {
            "uri": "ns2",
            "missing": [],
            "presence": {}
        },
    ]
    graph_names = ["g1", "g2"]

    result = format_namespace_matrix(report, graph_names)

    expected = (
        "Namespace |     G1     |     G2    \n"
        "-----------------------------------\n"
        "ns1 |    ✔ p1    |     ✘     "
    )

    assert result == expected


def test_format_namespace_matrix_emptyreport():
    assert format_namespace_matrix([], ["g1"]) == "Namespace |     G1    \n----------------------"

def test_format_namespace_matrix_nomissingrows():
    report = [{"uri": "ns", "missing": False, "presence": {}}]
    result = format_namespace_matrix(report, ["g1"])
    assert "ns" not in result

if __name__ == "__main__":
    pytest.main()