import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call
from rdflib import Graph, URIRef, Literal, Node, BNode
from rdflib.namespace import RDF, SH, XSD
from typing import Callable
from src.kgverifypy.csv_utilities import (
    PREDICATE_MAP,
    ConstraintViolation, 
    extract_violations_from_graph, 
    collect_violations, 
    write_shacl_violations_to_csv,
    resolve_node,
    is_rdf_list,
    resolve_rdf_list
)

PATCH_LOCATION = "src.kgverifypy.csv_utilities"

# Test to ensure that all fields in ConstraintViolation are present in the PREDICATE_MAP
def test_all_fields_present() -> None:
    g = Graph()
    subject = URIRef("http://example.org/subject")

    violation = extract_violations_from_graph(g, subject)

    assert set(vars(violation).keys()) == set(PREDICATE_MAP.keys())


# Unit tests extract_violations_from_graph
def test_extract_violations_from_graph_emptygraph() -> None:
    g = Graph()
    subject = URIRef("http://example.org/subject")
    violation = extract_violations_from_graph(g, subject)

    assert isinstance(violation, ConstraintViolation)
    assert violation.subject_uuid == "N/A"
    assert violation.predicate == "N/A"
    assert violation.object == "N/A"
    assert violation.constraint_component == "N/A"
    assert violation.shape == "N/A"
    assert violation.severity == "N/A"
    assert violation.message == "N/A"

def test_extract_violations_from_graph_withsomevalues() -> None:
    g = Graph()
    subject = URIRef("http://example.org/subject") 
    g.add((subject, RDF.type, SH.ValidationResult)) # Noise
    g.add((subject, SH.focusNode, URIRef("http://example.org/focusNode")))
    g.add((subject, SH.resultPath, URIRef("http://example.org/predicate")))
    g.add((subject, SH.value, URIRef("http://example.org/object1")))
    g.add((subject, SH.value, URIRef("http://example.org/object2")))
    violation = extract_violations_from_graph(g, subject)

    assert violation.subject_uuid == "http://example.org/focusNode"
    assert violation.predicate == "http://example.org/predicate"
    assert violation.object == "http://example.org/object1, http://example.org/object2"
    assert violation.constraint_component == "N/A"
    assert violation.shape == "N/A"
    assert violation.severity == "N/A"
    assert violation.message == "N/A"


def test_extract_violations_from_graph_allvalues() -> None:
    g = Graph()
    subject = URIRef("http://example.org/subject")
    g.add((subject, SH.focusNode, URIRef("http://example.org/focusNode")))
    g.add((subject, SH.resultPath, URIRef("http://example.org/predicate")))
    g.add((subject, SH.value, URIRef("http://example.org/object1")))
    g.add((subject, SH.sourceConstraintComponent, URIRef("http://example.org/constraintComponent")))
    g.add((subject, SH.sourceShape, URIRef("http://example.org/shape")))
    g.add((subject, SH.resultSeverity, URIRef("http://example.org/severity")))
    g.add((subject, SH.resultMessage, Literal("Violation message")))
    violation = extract_violations_from_graph(g, subject)

    assert isinstance(violation, ConstraintViolation)
    assert violation.subject_uuid == "http://example.org/focusNode"
    assert violation.predicate == "http://example.org/predicate"
    assert violation.object == "http://example.org/object1"
    assert violation.constraint_component == "http://example.org/constraintComponent"
    assert violation.shape == "http://example.org/shape"
    assert violation.severity == "http://example.org/severity"
    assert violation.message == "Violation message"


@pytest.mark.parametrize(
        "object",
        [
            pytest.param(Literal("Literal value"), id="Literal string value"),
            pytest.param(Literal(""), id="Literal empty string value"),
            pytest.param(Literal(42), id="Literal integer value"),
            pytest.param(Literal(42, datatype=XSD.integer), id="Literal integer value with datatype"),
        ]
)
def test_extract_violations_from_graph_edgecases(object: Node) -> None:
    g = Graph()
    subject = URIRef("http://example.org/subject")
    g.add((subject, SH.focusNode, object))

    violation = extract_violations_from_graph(g, subject)

    if isinstance(object, Literal) and object.datatype is not None:
        assert violation.subject_uuid == str(object.value)
    else:
        assert violation.subject_uuid == str(object)


def test_extract_violations_from_graph_mixedvaluetypes() -> None:
    g = Graph()
    subject = URIRef("http://example.org/subject")
    B = BNode()  # Create a single BNode instance for testing
    g.add((subject, SH.value, Literal("text")))
    g.add((subject, SH.value, B))
    g.add((B, SH.value, Literal("nested text")))


    violation = extract_violations_from_graph(g, subject)

    parts = violation.object.split(", ")
    assert len(parts) == 2
    assert parts[0] == "text"
    assert parts[1] == f"{SH.value}: nested text"

def test_extract_violations_from_graph_nomatchingsubject() -> None:
    g = Graph()
    subject = URIRef("http://example.org/subject")
    other = URIRef("http://example.org/other")

    g.add((other, SH.value, Literal("foo")))

    violation = extract_violations_from_graph(g, subject)

    assert violation.object == "N/A"

# Unit tests resolve_node
@patch(f"{PATCH_LOCATION}.is_rdf_list")
@patch(f"{PATCH_LOCATION}.resolve_rdf_list")
def test_resolve_node_seen(mock_resolve: MagicMock, mock_is_list: MagicMock) -> None:
    g = Graph()
    bnode = BNode()

    result = resolve_node(g, bnode, {bnode})
    
    assert result == []
    mock_is_list.assert_not_called()
    mock_resolve.assert_not_called()


@pytest.mark.parametrize(
    "node",
    [
        pytest.param(Literal("Literal value"), id="Literal string value"),
        pytest.param(URIRef("http://example.org/resource"), id="URIRef value"),
        pytest.param("http://example.org/resource", id="String value"),
    ]
)
@patch(f"{PATCH_LOCATION}.is_rdf_list")
@patch(f"{PATCH_LOCATION}.resolve_rdf_list")
def test_resolve_node_notbnode(mock_resolve: MagicMock, mock_is_list: MagicMock, node: Node) -> None:
    g = Graph()

    result = resolve_node(g, node)
    
    assert result == [str(node)]
    mock_is_list.assert_not_called()
    mock_resolve.assert_not_called()


@pytest.mark.parametrize("is_rdf_list_value", [True, False])
@patch(f"{PATCH_LOCATION}.is_rdf_list")
@patch(f"{PATCH_LOCATION}.resolve_rdf_list", return_value=["item1", "item2"])
def test_resolve_node_rdflist(mock_resolve: MagicMock, mock_is_list: MagicMock, is_rdf_list_value: bool) -> None:
    mock_is_list.return_value = is_rdf_list_value
    g = Graph()
    bnode = BNode()
    g.add((bnode, SH.value, Literal("item1")))
    g.add((bnode, SH.value, Literal("item2")))

    result = resolve_node(g, bnode)

    mock_is_list.assert_called_once_with(g, bnode)
    if is_rdf_list_value:
        assert result == ["item1 / item2"]
        mock_resolve.assert_called_once_with(g, bnode)
    else:
        assert result == [f"{SH.value}: item1, item2"]
        mock_resolve.assert_not_called()


@patch(f"{PATCH_LOCATION}.is_rdf_list", return_value=False)
@patch(f"{PATCH_LOCATION}.resolve_rdf_list")
def test_resolve_node_multiplelayers(mock_resolve: MagicMock, mock_is_list: MagicMock) -> None:
    g = Graph()
    bnode = BNode()
    bnode2 = BNode()
    g.add((bnode, SH.value, bnode2))
    g.add((bnode2, SH.value, Literal("Literal value")))

    result = resolve_node(g, bnode)

    assert result == [f"{SH.value}: {SH.value}: Literal value"] # All predicates touched are included in the output
    mock_resolve.assert_not_called()
    mock_is_list.assert_has_calls([call(g, bnode), call(g, bnode2)])


@patch(f"{PATCH_LOCATION}.is_rdf_list")
@patch(f"{PATCH_LOCATION}.resolve_rdf_list")
def test_resolve_node_circularnodes(mock_resolve: MagicMock, mock_is_list: MagicMock) -> None:
    g = Graph()
    bnode = BNode()
    bnode2 = BNode()
    g.add((bnode, SH.value, bnode2))
    g.add((bnode2, SH.value, bnode)) # Circular reference

    result = resolve_node(g, bnode)

    assert result == [""] # No results found because the bnodes don't lead anywhere
    # The function does not get stuck in an infinite loop due to the seen set
    mock_resolve.assert_called_once_with(g, bnode)
    mock_is_list.assert_called_once_with(g, bnode)

# Unit tests is_rdf_list
@pytest.mark.parametrize("is_rdf_list_value", [True, False])
def test_is_rdf_list_bnodes(is_rdf_list_value: bool) -> None:
    g = Graph()
    bnode = BNode()
    if is_rdf_list_value:
        g.add((bnode, RDF.first, Literal("item1")))
        g.add((bnode, RDF.rest, RDF.nil))
    else:
        g.add((bnode, SH.value, Literal("not a list")))

    assert is_rdf_list(g, bnode) is is_rdf_list_value


@pytest.mark.parametrize("is_rdf_list_value", [True, False])
def test_is_rdf_list_notbnodes(is_rdf_list_value: bool) -> None:
    g = Graph()
    node = URIRef("http://example.org/resource")
    if is_rdf_list_value:
        g.add((node, RDF.first, Literal("item1")))
        g.add((node, RDF.rest, RDF.nil))
    else:
        g.add((node, SH.value, Literal("not a list")))

    assert is_rdf_list(g, node) is False  # Only BNodes can be RDF lists, so it always return False for non-BNodes


# Unit tests resolve_rdf_list
def test_resolve_rdf_list_simple() -> None:
    g = Graph()
    bnode1 = BNode()
    bnode2 = BNode()
    g.add((bnode1, RDF.first, Literal("item1")))
    g.add((bnode1, RDF.rest, bnode2))
    g.add((bnode2, RDF.first, Literal("item2")))
    g.add((bnode2, RDF.rest, RDF.nil))

    result = resolve_rdf_list(g, bnode1)

    assert result == ["item1", "item2"]


@pytest.mark.parametrize(
    "triples, expected",
    [
        pytest.param(
            lambda b: [
                (b[0], RDF.first, Literal("a")),
                (b[0], RDF.rest, b[1]),
                (b[1], RDF.first, Literal("b")),
                (b[1], RDF.rest, RDF.nil),
            ],
            ["a", "b"],
            id="simple_two_items",
        ),
        pytest.param(
            lambda b: [
                (b[0], RDF.first, Literal("only")),
                (b[0], RDF.rest, RDF.nil),
            ],
            ["only"],
            id="single_item",
        ),
        pytest.param(
            lambda b: [
                (b[0], RDF.rest, RDF.nil),
            ],
            [],
            id="missing_first",
        ),
        pytest.param(
            lambda b: [
                (b[0], RDF.first, Literal("only")),
            ],
            ["only"],
            id="missing_rest",
        ),
        pytest.param(
            lambda b: [
                (b[0], RDF.first, Literal("a")),
                (b[0], RDF.rest, b[1]),
                (b[1], RDF.first, Literal("b")),
                (b[1], RDF.rest, b[0]),
            ],
            ["a", "b"],
            id="cycle_two_nodes",
        ),
        pytest.param(
            lambda b: [
                (b[0], RDF.first, Literal("x")),
                (b[0], RDF.rest, b[0]),
            ],
            ["x"],
            id="self_cycle",
        ),
        pytest.param(
            lambda b: [
                (b[0], RDF.first, URIRef("http://example.org")),
                (b[0], RDF.rest, b[1]),
                (b[1], RDF.first, Literal("text")),
                (b[1], RDF.rest, RDF.nil),
            ],
            ["http://example.org", "text"],
            id="mixed_uri_literal",
        ),
        pytest.param(
            lambda b: [
                (b[0], RDF.first, b[1]),
                (b[0], RDF.rest, RDF.nil),
                (b[1], RDF.first, Literal("a")),
                (b[1], RDF.rest, RDF.nil),
            ],
            ["a"],
            id="nested_list",
        ),
        pytest.param(
            lambda b: [],
            [],
            id="nil_input",
        ),
    ],
)
def test_resolve_rdf_list_parametrized(triples: Callable[[list[BNode]], list[tuple[Node, URIRef, Node]]], expected: list[str]) -> None:
    g = Graph()
    bnodes = [BNode(), BNode(), BNode()]

    built_triples = triples(bnodes)
    for triple in built_triples:
        g.add(triple)

    start = RDF.nil if not built_triples else bnodes[0]

    result = resolve_rdf_list(g, start)

    assert result == expected


# Unit tests collect_violations
@pytest.mark.parametrize(
    "triples",
    [
        pytest.param([], id="Empty graph"),
        pytest.param([(URIRef("http://example.org/subject"), RDF.type, SH.ValidationReport)], id="Graph without ValidationResult type"),
    ]
)
def test_collect_violations_emptyresult(triples: list[tuple[Node, URIRef, Node]]) -> None:
    g = Graph()
    for triple in triples:
        g.add(triple)
    
    violations = collect_violations(g)
    assert violations == []


@patch(f"{PATCH_LOCATION}.extract_violations_from_graph")
def test_collect_violations_extractcalls(mock_extract: MagicMock) -> None:
    mock_extract.side_effect = ["v1", "v2"]
    g = Graph()
    subject1 = URIRef("http://example.org/subject1")
    subject2 = URIRef("http://example.org/subject2")
    g.add((subject1, RDF.type, SH.ValidationResult))
    g.add((subject2, RDF.type, SH.ValidationResult))

    result = collect_violations(g)

    assert mock_extract.call_count == 2
    mock_extract.assert_any_call(g, subject1)
    mock_extract.assert_any_call(g, subject2)

    assert result == ["v1", "v2"]


# Unit tests write_shacl_violations_to_csv
@patch("builtins.open", new_callable=mock_open)
def test_write_shacl_violations_to_csv_emptylist(mock_file: MagicMock) -> None:
    write_shacl_violations_to_csv([], "output.csv")

    mock_file.assert_not_called()


@pytest.mark.parametrize(
    "filepath",
    [
        pytest.param("output.csv", id="String file path"),
        pytest.param(Path("output.csv"), id="Path object file path")
    ]
)
@patch("builtins.open", new_callable=mock_open)
def test_write_shacl_violations_to_csv_writing(mock_file: MagicMock, filepath: str | Path) -> None:
    violations = [
        ConstraintViolation(
            subject_uuid="s",
            predicate="p",
            object="o",
            constraint_component="c",
            shape="sh",
            severity="sev",
            message="msg"
        )
    ]

    write_shacl_violations_to_csv(violations, filepath)

    mock_file.assert_called_once_with(filepath, 'w', newline='', encoding='utf-8')
    handle = mock_file()
    handle.write.assert_called()

    written = "".join(call.args[0] for call in handle.write.call_args_list)
    assert "subject_uuid;predicate;object;constraint_component;shape;severity;message" in written
    assert "s;p;o;c;sh;sev;msg" in written


@patch("builtins.open", new_callable=mock_open)
def test_write_shacl_violations_to_csv_multiplerows(mock_file: MagicMock) -> None:
    v1 = ConstraintViolation(
        subject_uuid="s1",
        predicate="p1",
        object="o1",
        constraint_component="c1",
        shape="sh1",
        severity="sev1",
        message="msg1"
    )
    v2 = ConstraintViolation(
        subject_uuid="s2",
        predicate="p2",
        object="o2",
        constraint_component="c2",
        shape="sh2",
        severity="sev2",
        message="msg2"
    )
    violations = [v1, v2]

    write_shacl_violations_to_csv(violations, "output.csv")

    handle = mock_file()
    assert handle.write.call_count == 3  # header + 2 rows


@patch("builtins.open", new_callable=mock_open)
def test_write_shacl_violations_to_csv_specialcharacters(mock_file: MagicMock) -> None:
    violations = [
        ConstraintViolation(
            subject_uuid="s;1",
            predicate="p\nline",
            object='o"quote',
            constraint_component="cc",
            shape="sh",
            severity="sev",
            message="msg",
        )
    ]

    write_shacl_violations_to_csv(violations, "output.csv")

    handle = mock_file()

    assert '"s;1";"p\nline";"o""quote";cc;sh;sev;msg\r\n' in handle.write.call_args_list[1][0][0]  # Check the first data row for proper escaping

@patch("builtins.open", new_callable=mock_open)
def test_write_shacl_violations_to_csv_invalidtype(mock_file: MagicMock) -> None:
    with pytest.raises(TypeError):
        # Pylance silenced to test invalid input type handling
        write_shacl_violations_to_csv([{"not": "dataclass"}], "output.csv") # type: ignore

    mock_file.assert_called_once() 

if __name__ == "__main__":
    pytest.main()